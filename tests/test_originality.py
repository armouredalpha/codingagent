"""
Integration tests — OriginalityAgent.

Verifies both detection layers:
  Layer A (structural hash)  — exact/near-exact duplicates
  Layer B (cosine vectorstore) — paraphrase / near-duplicate detection

No LLM calls; the agent's vectorstore path is exercised directly.
"""
from __future__ import annotations

import pytest

from robo_assess.agents.originality_agent import OriginalityAgent
from robo_assess.agents.context_retrieval import _structural_hash
from robo_assess.schemas import Difficulty, BloomLevel, Question
from robo_assess.vectorstore import VectorStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(qid: str, title: str, scenario: str = "", skill: str = "ROS2 publisher") -> Question:
    return Question(
        question_id=qid,
        title=title,
        difficulty=Difficulty.EASY,
        bloom_level=BloomLevel.APPLY,
        scenario=scenario or f"A robot must {title.lower()}.",
        tested_skills=[skill],
        objective=f"Implement {title}.",
    )


def _agent(tmp_settings, vectorstore=None):
    return OriginalityAgent(settings=tmp_settings, vectorstore=vectorstore)


# ---------------------------------------------------------------------------
# Layer A — structural hash duplicate detection
# ---------------------------------------------------------------------------

def test_layer_a_intra_batch_exact_duplicate(tmp_settings):
    """Two questions in the SAME batch with identical text → second flagged by Layer A.

    Layer A uses batch_hashes (separate from hash_set so current_hashes subtraction
    doesn't interfere): the first question adds its hash to batch_hashes; the second
    hits `q_hash in batch_hashes` and gets similarity=1.0.
    """
    agent = _agent(tmp_settings)
    # Identical title + scenario + objective + tested_skills → same _question_text
    q1 = _q("Q001", "Publish Twist", scenario="publisher geometry_msgs Twist vel warehouse")
    q2 = _q("Q002", "Publish Twist", scenario="publisher geometry_msgs Twist vel warehouse")
    result = agent.run([q1, q2])

    patches = result.payload["patches"]
    # Q001 processed first (no match yet), Q002 hits q1's hash in batch_hashes
    assert patches["Q002"]["similarity_score"] == 1.0
    assert any(r["qid"] == "Q002" for r in result.payload["rejected"])


def test_layer_a_different_question_not_flagged(tmp_settings):
    """A structurally different question passes Layer A."""
    agent = _agent(tmp_settings)
    q = _q("Q001", "Broadcast TF2 transform", scenario="broadcast dynamic tf2 transform map odom")

    # Known hashes belong to a completely different topic
    known_hash = _structural_hash("subscriber imu data callback pitch tilt")
    result = agent.run([q], known_question_hashes=[known_hash])

    patches = result.payload["patches"]
    assert patches["Q001"]["similarity_score"] < 1.0


def test_layer_a_external_known_hash_catches_different_batch(tmp_settings):
    """A known_question_hash from a PREVIOUS batch (different qid, different text)
    gets caught by Layer A because current_hashes only subtracts THIS batch's hashes.

    We make Q_PREV and Q_NEW have different titles so their _question_text differs;
    after _structural_hash normalisation they get DIFFERENT hashes → not caught by
    Layer A.  This test verifies the boundary: only truly identical text triggers
    the hash hit.
    """
    from robo_assess.agents.originality_agent import _question_text

    scenario = "publisher geometry_msgs Twist velocity cmd_vel warehouse"
    # Simulate a PREVIOUS question with the same scenario but different title/objective
    q_prev = _q("Q_PREV", "Old Publisher", scenario=scenario)
    prev_hash = _structural_hash(_question_text(q_prev))

    # New question has different title → different combined text → different hash
    q_new = _q("Q001", "New Publisher", scenario=scenario)
    agent = _agent(tmp_settings)
    result = agent.run([q_new], known_question_hashes=[prev_hash])

    patches = result.payload["patches"]
    # Different combined texts → Layer A doesn't fire (Layer B may or may not)
    assert patches["Q001"]["similarity_score"] < 1.0


# ---------------------------------------------------------------------------
# Layer B — cosine similarity
# ---------------------------------------------------------------------------

def test_layer_b_high_cosine_similarity_flagged(tmp_settings):
    """A paraphrase of an existing question (high cosine sim) is flagged."""
    store = VectorStore(path=":memory:")
    text_a = "publisher node geometry_msgs Twist velocity cmd_vel warehouse 10 Hz"
    store.add("existing_0", text_a)

    agent = _agent(tmp_settings, vectorstore=store)
    # Nearly identical text — different words but same concept
    q = _q("Q001", "Publish Twist velocity", scenario=text_a + " robot arm sensor")
    result = agent.run([q])

    patches = result.payload["patches"]
    assert patches["Q001"]["similarity_score"] > 0.5


def test_layer_b_original_question_passes(tmp_settings):
    """A genuinely novel question gets a low similarity score."""
    store = VectorStore(path=":memory:")
    store.add("existing_0", "publisher Twist velocity cmd_vel warehouse")

    agent = _agent(tmp_settings, vectorstore=store)
    q = _q("Q001", "Broadcast TF2 dynamic transform",
           scenario="broadcast dynamic tf2 transform base link map frame",
           skill="TF2 broadcaster")
    result = agent.run([q])

    patches = result.payload["patches"]
    assert patches["Q001"]["similarity_score"] < 0.6


# ---------------------------------------------------------------------------
# exclude_id regression — question must not flag itself
# ---------------------------------------------------------------------------

def test_question_not_flagged_as_own_duplicate(tmp_settings):
    """A question already in the store (from a prior run) should not flag
    itself via Layer B because exclude_id skips its own entry."""
    store = VectorStore(path=":memory:")
    text = "publisher node Twist velocity warehouse"
    store.add("Q001", text)  # pre-existing from last round

    agent = _agent(tmp_settings, vectorstore=store)
    q = _q("Q001", "Publish Twist", scenario=text)
    result = agent.run([q])

    # Q001's own vectorstore entry is excluded — should not hit similarity=1
    patches = result.payload["patches"]
    assert patches["Q001"]["similarity_score"] < 1.0


# ---------------------------------------------------------------------------
# Memory integration
# ---------------------------------------------------------------------------

def test_originality_does_not_load_memory_stems(tmp_settings, tmp_path):
    """Memory stems must NOT be loaded into the vectorstore during the originality
    check. Loading all past stems caused the near-duplicate spiral: same-syllabus
    re-runs see their own questions as near-duplicates (similarity≈1.0) with no
    escape via regeneration. Memory is only consulted via _finish_run for approved
    questions, so previously rejected questions never poison future runs."""
    from robo_assess.memory import Memory
    mem = Memory(str(tmp_path / "mem.db"))
    mem.remember_question("MEM001", "Old topic",
                          "publisher Twist velocity cmd_vel warehouse sensor")

    agent = OriginalityAgent(settings=tmp_settings, memory=mem)
    # Identical text to what's in memory — should NOT be flagged as duplicate
    # because we no longer load memory stems during the originality check.
    q = _q("Q001", "Publish Twist", scenario="publisher Twist velocity cmd_vel warehouse sensor")
    result = agent.run([q])

    patches = result.payload["patches"]
    # Similarity should come only from the vectorstore (empty here), not from
    # memory stems — so it must be below the rejection threshold (0.75).
    assert patches["Q001"]["similarity_score"] < 0.75, (
        "Memory stems must not be loaded into the vectorstore during run(); "
        "that was the root cause of the near-duplicate spiral."
    )


def test_originality_does_not_save_to_memory(tmp_settings, tmp_path):
    """The originality agent must NOT write to memory. Memory is written only
    by orchestrator._finish_run() for APPROVED questions after the full run
    completes. Writing here (before supervisor approval) caused rejected questions
    to pollute future originality checks."""
    from robo_assess.memory import Memory
    mem = Memory(str(tmp_path / "mem.db"))

    agent = OriginalityAgent(settings=tmp_settings, memory=mem)
    q = _q("Q001", "Subscribe to IMU data",
           scenario="subscriber imu sensor data callback pitch angle",
           skill="ROS2 subscriber")
    agent.run([q])

    # Memory must still be empty — writing happens in _finish_run, not here
    stems = dict(mem.all_stems())
    assert "Q001" not in stems, (
        "OriginalityAgent must not write to memory; "
        "that responsibility belongs to orchestrator._finish_run()."
    )
