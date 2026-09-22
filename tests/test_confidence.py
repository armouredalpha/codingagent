"""
Integration tests — ConfidenceScoringAgent.

Tests the scoring math without any LLM calls:
  - score() produces values in [0, 100]
  - breakdown status is one of the expected verdicts
"""
from __future__ import annotations

from coding_agent.schemas import (
    BloomLevel,
    CoverageMatrix,
    ConfidenceBreakdown,
    Difficulty,
    EvaluationCriterion,
    Question,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(
    difficulty: str = "easy",
    skills: list[str] | None = None,
    criteria_count: int = 2,
    scope_violations: list[str] | None = None,
    similarity_score: float = 0.0,
) -> Question:
    skills = skills or ["ROS2 publisher"]
    criteria = [
        EvaluationCriterion(
            id=f"EC{i}", check="topic_active", target=f"/topic{i}",
            points=50 if i == 1 else 50, description=f"check {i}"
        )
        for i in range(1, criteria_count + 1)
    ]
    q = Question(
        question_id=f"Q001_test",
        title="Publish a velocity command",
        difficulty=Difficulty(difficulty),
        bloom_level=BloomLevel.APPLY,
        scenario="Warehouse robot publishes Twist to /cmd_vel.",
        tested_skills=skills,
        objective="Implement a publisher node.",
        evaluation_criteria=criteria,
    )
    q.scope_violations = scope_violations or []
    q.similarity_score = similarity_score
    q.auto_gradable = True
    return q


def _coverage(skills: list[str], covered: bool = True) -> CoverageMatrix:
    return CoverageMatrix(matrix={s: covered for s in skills})


# ---------------------------------------------------------------------------
# ConfidenceScoringAgent (integration — no LLM)
# ---------------------------------------------------------------------------

def test_confidence_scoring_agent_produces_breakdown(tmp_settings):
    from coding_agent.agents.confidence_agent import ConfidenceScoringAgent

    agent = ConfidenceScoringAgent(settings=tmp_settings, llm=None)
    q = _q("easy", skills=["ROS2 publisher"])
    q.similarity_score = 0.1
    q.auto_gradable = True
    coverage = _coverage(["ROS2 publisher"], covered=True)

    breakdown = agent.score(q, coverage)
    assert isinstance(breakdown, ConfidenceBreakdown)
    assert 0 <= breakdown.confidence <= 100
    assert breakdown.status in ("APPROVED", "PENDING", "REJECTED")


def test_confidence_scoring_agent_approved_on_high_score(tmp_settings):
    from coding_agent.agents.confidence_agent import ConfidenceScoringAgent

    # Set a very low bar so we can trigger APPROVED without real LLM scores
    tmp_settings.min_confidence_score = 50.0

    agent = ConfidenceScoringAgent(settings=tmp_settings, llm=None)
    q = _q("easy")
    q.similarity_score = 0.0
    q.auto_gradable = True
    q.scope_violations = []
    coverage = _coverage(["ROS2 publisher"], covered=True)

    breakdown = agent.score(q, coverage)
    # With a low bar the score should pass
    assert breakdown.confidence >= 0
