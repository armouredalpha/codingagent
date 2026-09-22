"""
Integration tests — Memory (SQLite).

Covers: few_shots save/retrieve, prompt_hash versioning, fallback behaviour,
student attempt recording, pass-rate tallies.
"""
from __future__ import annotations

import json

import pytest

from coding_agent.memory import Memory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "memory.db"))


def _q_json(title: str = "Publish Twist") -> str:
    return json.dumps({"question_id": f"Q_{title[:10]}", "title": title})


# ---------------------------------------------------------------------------
# few_shots basic CRUD
# ---------------------------------------------------------------------------

def test_save_and_retrieve_few_shot(mem):
    mem.save_few_shot(
        skill="ROS2 publisher", difficulty="easy", confidence_score=92.0,
        question_json=_q_json("Publish Twist"),
        starter_code="import rclpy", reference_code="# solution",
    )
    shots = mem.get_few_shots("ROS2 publisher", "easy")
    assert len(shots) == 1
    assert shots[0]["skill"] == "ROS2 publisher"
    assert shots[0]["confidence_score"] == 92.0


def test_get_few_shots_returns_highest_confidence_first(mem):
    mem.save_few_shot("ROS2 publisher", "easy", 75.0, _q_json("Low"), "c", "r")
    mem.save_few_shot("ROS2 publisher", "easy", 95.0, _q_json("High"), "c", "r")
    mem.save_few_shot("ROS2 publisher", "easy", 85.0, _q_json("Mid"), "c", "r")

    shots = mem.get_few_shots("ROS2 publisher", "easy", n=2)
    assert len(shots) == 2
    assert shots[0]["confidence_score"] >= shots[1]["confidence_score"]
    assert shots[0]["confidence_score"] == 95.0


def test_get_few_shots_empty_returns_empty_list(mem):
    shots = mem.get_few_shots("nonexistent skill", "easy")
    assert shots == []


def test_get_few_shots_n_limit_respected(mem):
    for i in range(5):
        mem.save_few_shot("ROS2 publisher", "easy", float(80 + i), _q_json(f"Q{i}"), "", "")
    shots = mem.get_few_shots("ROS2 publisher", "easy", n=2)
    assert len(shots) == 2


# ---------------------------------------------------------------------------
# prompt_hash versioning
# ---------------------------------------------------------------------------

def test_prompt_hash_filters_stale_examples(mem):
    mem.save_few_shot("ROS2 publisher", "easy", 92.0, _q_json("Old"), "", "",
                      prompt_hash="abc123")
    mem.save_few_shot("ROS2 publisher", "easy", 91.0, _q_json("New"), "", "",
                      prompt_hash="xyz999")

    shots_new = mem.get_few_shots("ROS2 publisher", "easy", prompt_hash="xyz999")
    assert len(shots_new) == 1
    assert json.loads(shots_new[0]["question_json"])["title"] == "New"


def test_null_prompt_hash_matches_any_version(mem):
    # Manually-seeded examples have prompt_hash=NULL and should match any version
    mem.save_few_shot("ROS2 publisher", "easy", 90.0, _q_json("Seed"), "", "",
                      prompt_hash=None)
    shots = mem.get_few_shots("ROS2 publisher", "easy", prompt_hash="brand_new_hash")
    assert len(shots) == 1  # NULL rows match any hash


def test_prompt_hash_fallback_to_same_difficulty(mem):
    """When exact skill match is empty, fallback returns same-difficulty examples."""
    mem.save_few_shot("ROS2 subscriber", "medium", 88.0, _q_json("Sub"), "", "",
                      prompt_hash="h1")

    shots = mem.get_few_shots("ROS2 publisher", "medium", n=2, prompt_hash="h1")
    # No exact skill match, but fallback from same difficulty
    assert len(shots) >= 1
    assert shots[0]["difficulty"] == "medium"


# ---------------------------------------------------------------------------
# question memory (all_stems)
# ---------------------------------------------------------------------------

def test_remember_and_retrieve_stems(mem):
    mem.remember_question("Q001", "Topic", "publisher node text")
    stems = mem.all_stems()
    assert ("Q001", "publisher node text") in stems


def test_remember_question_deduplicates(mem):
    mem.remember_question("Q001", "Topic", "original text")
    mem.remember_question("Q001", "Topic", "updated text")
    stems = dict(mem.all_stems())
    assert stems["Q001"] == "updated text"


# ---------------------------------------------------------------------------
# student_attempts
# ---------------------------------------------------------------------------

def test_record_attempt_and_retrieve_rates(mem):
    mem.record_attempt("Q001", "easy", passed=True, time_minutes=8.0)
    mem.record_attempt("Q002", "easy", passed=False)
    mem.record_attempt("Q003", "hard", passed=True)

    rates = mem.get_difficulty_pass_rates()
    assert "easy" in rates
    assert rates["easy"]["total"] == 2
    assert rates["easy"]["passed"] == 1
    assert "hard" in rates
    assert rates["hard"]["passed"] == 1


def test_record_attempt_optional_fields(mem):
    mem.record_attempt("Q001", "medium", passed=True)
    rates = mem.get_difficulty_pass_rates()
    assert rates["medium"]["total"] == 1


def test_get_pass_rates_empty_returns_empty_dict(mem):
    rates = mem.get_difficulty_pass_rates()
    assert rates == {}

