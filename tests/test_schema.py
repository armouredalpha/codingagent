"""
Integration tests — schema validation.

Verifies that Pydantic models enforce their invariants and that the
helper properties (coverage_pct, approved) behave correctly.  No LLM
calls, no file I/O.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from robo_assess.schemas import (
    AssessmentRequest,
    BloomLevel,
    CoverageMatrix,
    Difficulty,
    EvaluationCriterion,
    Question,
)


# ---------------------------------------------------------------------------
# Question model
# ---------------------------------------------------------------------------

def _minimal_question(**overrides) -> Question:
    defaults = dict(
        question_id="Q001_pub",
        title="Publish a Twist message",
        difficulty=Difficulty.EASY,
        bloom_level=BloomLevel.APPLY,
        scenario="Warehouse robot publishes velocity.",
        tested_skills=["ROS2 publisher"],
        objective="Implement a publisher node.",
    )
    defaults.update(overrides)
    return Question(**defaults)


def test_question_valid_minimal():
    q = _minimal_question()
    assert q.question_id == "Q001_pub"
    assert q.difficulty == Difficulty.EASY
    assert q.bloom_level == BloomLevel.APPLY
    assert q.approved is False  # no confidence attached yet


def test_question_approved_property_false_without_confidence():
    q = _minimal_question()
    assert q.approved is False


def test_question_approved_property_true_with_status():
    from robo_assess.schemas import ConfidenceBreakdown
    q = _minimal_question()
    q.confidence = ConfidenceBreakdown(confidence=91.0, status="APPROVED")
    assert q.approved is True


def test_question_approved_property_false_when_pending():
    from robo_assess.schemas import ConfidenceBreakdown
    q = _minimal_question()
    q.confidence = ConfidenceBreakdown(confidence=75.0, status="PENDING")
    assert q.approved is False


def test_question_difficulty_enum_accepts_string_values():
    q = _minimal_question(difficulty="medium")
    assert q.difficulty == Difficulty.MEDIUM


def test_question_invalid_difficulty_raises():
    with pytest.raises(ValidationError):
        _minimal_question(difficulty="impossible")


def test_question_defaults_populated():
    q = _minimal_question()
    assert q.constraints == []
    assert q.common_mistakes == []
    assert q.similarity_score == 0.0
    assert q.auto_gradable is True
    assert q.scope_violations == []


# ---------------------------------------------------------------------------
# CoverageMatrix
# ---------------------------------------------------------------------------

def test_coverage_matrix_properties_empty():
    cm = CoverageMatrix(matrix={})
    assert cm.coverage_pct == 0.0
    assert cm.covered == []
    assert cm.missing == []


def test_coverage_matrix_partial_coverage():
    cm = CoverageMatrix(matrix={"skill_a": True, "skill_b": False, "skill_c": True})
    assert cm.coverage_pct == pytest.approx(66.7, abs=0.1)
    assert "skill_a" in cm.covered
    assert "skill_b" in cm.missing
    assert len(cm.covered) == 2
    assert len(cm.missing) == 1


def test_coverage_matrix_full_coverage():
    cm = CoverageMatrix(matrix={"a": True, "b": True})
    assert cm.coverage_pct == 100.0
    assert cm.missing == []


# ---------------------------------------------------------------------------
# AssessmentRequest
# ---------------------------------------------------------------------------

def test_assessment_request_strips_blank_syllabus_entries():
    req = AssessmentRequest(
        topic="ROS2 Basics",
        syllabus=["publisher", "  ", "", "subscriber"],
    )
    assert req.syllabus == ["publisher", "subscriber"]


def test_assessment_request_rejects_empty_syllabus():
    with pytest.raises(ValidationError):
        AssessmentRequest(topic="ROS2 Basics", syllabus=[])


def test_assessment_request_rejects_short_topic():
    with pytest.raises(ValidationError):
        AssessmentRequest(topic="X", syllabus=["publisher"])


# ---------------------------------------------------------------------------
# EvaluationCriterion
# ---------------------------------------------------------------------------

def test_evaluation_criterion_points_range():
    ec = EvaluationCriterion(
        id="EC1", check="topic_active", target="/cmd_vel",
        points=50, description="publishes"
    )
    assert ec.points == 50

    with pytest.raises(ValidationError):
        EvaluationCriterion(
            id="EC1", check="topic_active", target="/cmd_vel",
            points=150, description="too high"
        )
