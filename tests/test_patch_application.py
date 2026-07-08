"""
Integration tests — thread-safe patch dict pattern.

Verifies that validator agents (difficulty, scope_quality, originality)
return patches rather than mutating Question objects in-place, and that the
orchestrator's atomic merge correctly applies all patches.

No LLM calls; agents are run with llm=None so they take the rule-based path.
"""
from __future__ import annotations

import pytest

from robo_assess.schemas import (
    BloomLevel, Difficulty, Question, SyllabusAnalysis, CoverageMatrix,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(qid: str = "Q001", difficulty: str = "easy",
       scenario: str = "", skill: str = "ROS2 publisher") -> Question:
    return Question(
        question_id=qid,
        title=f"Question {qid}",
        difficulty=Difficulty(difficulty),
        bloom_level=BloomLevel.APPLY,
        scenario=scenario or "Warehouse robot publishes Twist to /cmd_vel.",
        tested_skills=[skill],
        objective="Implement a publisher node.",
    )


def _analysis(skills=None) -> SyllabusAnalysis:
    return SyllabusAnalysis(
        skills=skills or ["ROS2 publisher"],
        concepts=["rclpy", "geometry_msgs"],
        apis=["rclpy.node.Node"],
    )


# ---------------------------------------------------------------------------
# Scope agent — patches dict, not in-place mutation
# ---------------------------------------------------------------------------

def test_scope_agent_returns_patches_not_mutation(tmp_settings):
    from robo_assess.agents.scope_agent import ScopeComplianceAgent
    q = _q("Q001", scenario="This question uses Nav2 for path planning.")
    agent = ScopeComplianceAgent(settings=tmp_settings, llm=None)
    result = agent.run([q], _analysis())

    # Must return a patches dict
    assert "patches" in result.payload
    # Original question object must NOT have been mutated
    assert q.scope_violations == []
    # Patch must contain the detected violations
    patches = result.payload["patches"]
    assert "Q001" in patches
    assert "scope_violations" in patches["Q001"]
    # Guardrails normalize technology names to lowercase ("nav2" not "Nav2")
    violations = [v.lower() for v in patches["Q001"]["scope_violations"]]
    assert "nav2" in violations


def test_scope_agent_clean_question_has_empty_violations(tmp_settings):
    from robo_assess.agents.scope_agent import ScopeComplianceAgent
    q = _q("Q001", scenario="Publish geometry_msgs Twist to /cmd_vel at 10 Hz.")
    agent = ScopeComplianceAgent(settings=tmp_settings, llm=None)
    result = agent.run([q], _analysis())
    patches = result.payload["patches"]
    assert patches["Q001"]["scope_violations"] == []


# ---------------------------------------------------------------------------
# Originality agent — patches dict
# ---------------------------------------------------------------------------

def test_originality_agent_returns_patches(tmp_settings):
    from robo_assess.agents.originality_agent import OriginalityAgent
    q = _q("Q001")
    agent = OriginalityAgent(settings=tmp_settings)
    result = agent.run([q])

    assert "patches" in result.payload
    patches = result.payload["patches"]
    assert "Q001" in patches
    assert "similarity_score" in patches["Q001"]
    # Original object must NOT be mutated
    assert q.similarity_score == 0.0


# ---------------------------------------------------------------------------
# Scope-quality agent — patches dict, skill-drift merged in (no LLM)
# ---------------------------------------------------------------------------

def test_scope_quality_agent_returns_patches(tmp_settings):
    from robo_assess.agents.scope_quality_agent import ScopeQualityAgent
    q = _q("Q001")
    agent = ScopeQualityAgent(settings=tmp_settings, llm=None)
    result = agent.run([q], _analysis(), assigned_skills={"Q001": "ROS2 publisher"})

    assert "patches" in result.payload
    patches = result.payload["patches"]
    assert "Q001" in patches
    assert "realism_score" in patches["Q001"]
    # No LLM configured -> skill-drift check is skipped, defaults to "no drift"
    assert patches["Q001"]["skill_drift"] is False
    assert patches["Q001"]["scope_violations"] == []
    # Original object must NOT be mutated
    assert q.skill_drift is False


# ---------------------------------------------------------------------------
# Atomic patch merge — orchestrator pattern
# ---------------------------------------------------------------------------

def test_atomic_patch_merge_applies_all_fields():
    """Simulates the orchestrator's patch-merge logic: collect patches from
    parallel validators, then apply them all at once after the loop."""
    q = _q("Q001")

    # Simulate two validators returning patches for the same question
    patches_a = {"Q001": {"similarity_score": 0.15, "auto_gradable": True}}
    patches_b = {"Q001": {"scope_violations": ["Nav2"], "grading_issues": ["missing check"]}}

    all_patches: dict[str, dict] = {}
    for patch_dict in [patches_a, patches_b]:
        for qid, fields in patch_dict.items():
            all_patches.setdefault(qid, {}).update(fields)

    # Apply
    q_by_id = {"Q001": q}
    for qid, fields in all_patches.items():
        obj = q_by_id.get(qid)
        if obj is None:
            continue
        for field, value in fields.items():
            setattr(obj, field, value)

    assert q.similarity_score == 0.15
    assert q.auto_gradable is True
    assert q.scope_violations == ["Nav2"]
    assert q.grading_issues == ["missing check"]


def test_patch_merge_later_validator_overwrites_earlier():
    """When two validators write the same field, the last one wins."""
    q = _q("Q001")

    patches_a = {"Q001": {"similarity_score": 0.20}}
    patches_b = {"Q001": {"similarity_score": 0.85}}

    all_patches: dict[str, dict] = {}
    for patch_dict in [patches_a, patches_b]:
        for qid, fields in patch_dict.items():
            all_patches.setdefault(qid, {}).update(fields)

    for qid, fields in all_patches.items():
        for k, v in fields.items():
            setattr(q_by_id := {"Q001": q}[qid], k, v)

    assert q.similarity_score == 0.85


def test_patch_merge_unknown_qid_skipped():
    """Patches referencing unknown question IDs are silently skipped."""
    q = _q("Q001")
    all_patches = {"Q_GHOST": {"similarity_score": 0.99}}
    q_by_id = {"Q001": q}

    for qid, fields in all_patches.items():
        obj = q_by_id.get(qid)
        if obj is None:
            continue
        for k, v in fields.items():
            setattr(obj, k, v)

    # Q001 must be unmodified
    assert q.similarity_score == 0.0
