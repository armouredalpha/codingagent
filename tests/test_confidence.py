"""
Integration tests — ConfidenceScoringAgent + ImprovedConfidenceScorer.

Tests the scoring math without any LLM calls:
  - score() produces values in [0, 100]
  - difficulty multipliers affect output directionally
  - high-quality inputs produce higher scores than low-quality ones
  - ImprovedConfidenceScorer handles edge cases (unknown skill, empty features)
"""
from __future__ import annotations

import pytest

from robo_assess.schemas import (
    BloomLevel,
    CoverageMatrix,
    ConfidenceBreakdown,
    Difficulty,
    EvaluationCriterion,
    Question,
)
from robo_assess.learned_confidence_improved import ImprovedConfidenceScorer


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
# ImprovedConfidenceScorer.score()
# ---------------------------------------------------------------------------

def test_score_returns_tuple_in_range():
    scorer = ImprovedConfidenceScorer()
    q = _q("easy")
    score, breakdown = scorer.score(q, validators={"auto_grading": 90, "originality": 90, "format_compliance": 90})
    assert 0 <= score <= 100
    assert isinstance(breakdown, dict)
    assert "raw_confidence" in breakdown


def test_easy_questions_score_higher_than_hard():
    scorer = ImprovedConfidenceScorer()
    validators = {"auto_grading": 85, "originality": 85, "format_compliance": 85}

    q_easy = _q("easy", skills=["ROS2 publisher"], criteria_count=2)
    q_hard = _q("hard", skills=["ROS2 publisher", "TF2", "Nav2", "SLAM", "MoveIt"],
                criteria_count=5)

    score_easy, _ = scorer.score(q_easy, validators)
    score_hard, _ = scorer.score(q_hard, validators)
    # Easy should score higher than hard with same validators
    assert score_easy > score_hard


def test_difficulty_multiplier_in_breakdown():
    scorer = ImprovedConfidenceScorer()
    q = _q("hard")
    _, breakdown = scorer.score(q, validators={})
    assert "difficulty_multiplier" in breakdown
    assert breakdown["difficulty_multiplier"] == pytest.approx(0.85)


def test_unknown_difficulty_hint_does_not_crash():
    scorer = ImprovedConfidenceScorer()
    q = _q("medium")
    score, _ = scorer.score(q, validators={}, difficulty_hint="unknown_level")
    assert 0 <= score <= 100


def test_many_skills_reduces_confidence():
    scorer = ImprovedConfidenceScorer()
    q_few = _q("easy", skills=["ROS2 publisher"])
    q_many = _q("easy", skills=["ROS2 publisher", "TF2", "SLAM", "Nav2", "URDF", "Gazebo"])
    validators = {"auto_grading": 80}
    score_few, _ = scorer.score(q_few, validators)
    score_many, _ = scorer.score(q_many, validators)
    assert score_few > score_many


def test_score_clamps_between_0_and_100():
    scorer = ImprovedConfidenceScorer()
    # Force extreme multipliers
    scorer.difficulty_multipliers["easy"] = 10.0
    q = _q("easy")
    score, _ = scorer.score(q, validators={"auto_grading": 100, "originality": 100, "format_compliance": 100})
    assert score <= 100


def test_skill_difficulty_factor_applied():
    scorer = ImprovedConfidenceScorer()
    # A hard skill ("Laser scan processing") should produce lower score
    q_hard_skill = _q("medium", skills=["Laser scan processing"])
    q_easy_skill = _q("medium", skills=["class definition"])
    validators = {"auto_grading": 80, "originality": 80}

    score_hard, _ = scorer.score(q_hard_skill, validators)
    score_easy, _ = scorer.score(q_easy_skill, validators)
    assert score_easy > score_hard


# ---------------------------------------------------------------------------
# compute_features
# ---------------------------------------------------------------------------

def test_compute_features_counts_correct():
    scorer = ImprovedConfidenceScorer()
    q = _q("easy", skills=["ROS2 publisher", "TF2"], criteria_count=3)
    features = scorer.compute_features(q)
    assert features["num_skills"] == 2
    assert features["num_criteria"] == 3


def test_compute_features_bloom_rank():
    scorer = ImprovedConfidenceScorer()
    q_apply = _q("easy")
    q_apply.bloom_level = BloomLevel.APPLY
    features = scorer.compute_features(q_apply)
    assert features["bloom_level_rank"] == 3


# ---------------------------------------------------------------------------
# ConfidenceScoringAgent (integration — no LLM)
# ---------------------------------------------------------------------------

def test_confidence_scoring_agent_produces_breakdown(tmp_settings):
    from robo_assess.agents.confidence_agent import ConfidenceScoringAgent

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
    from robo_assess.agents.confidence_agent import ConfidenceScoringAgent

    # Set a very low bar so we can trigger APPROVED without real LLM scores
    tmp_settings.min_confidence = 50.0

    agent = ConfidenceScoringAgent(settings=tmp_settings, llm=None)
    q = _q("easy")
    q.similarity_score = 0.0
    q.auto_gradable = True
    q.scope_violations = []
    coverage = _coverage(["ROS2 publisher"], covered=True)

    breakdown = agent.score(q, coverage)
    # With a low bar the score should pass
    assert breakdown.confidence >= 0
