"""
Integration tests — PlannerAgent routing decisions.

All tests use llm=None so the judge is skipped and decisions are
100% deterministic (no LLM calls, no network).

Key cases:
  1. All questions pass  → FINALIZE
  2. One question fails  → REGENERATE (while budget/attempts remain)
  3. Max attempts spent  → FINALIZE (don't loop forever)
  4. Token budget exhausted → FINALIZE
  5. Call budget exhausted  → FINALIZE
  6. evaluate_quality correctly maps confidence + checks to pass/fail
"""
from __future__ import annotations

import pytest

from robo_assess.agents.planner import PlannerAgent, RunState
from robo_assess.schemas import (
    BloomLevel,
    CoverageMatrix,
    Difficulty,
    PlanAction,
    Question,
    QuestionQuality,
    ConfidenceBreakdown,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings():
    from robo_assess.config import Settings
    s = Settings()
    s.api_key = "fake"
    return s


def _planner():
    return PlannerAgent(settings=_settings(), llm=None)


def _q(qid: str, confidence: float = 90.0, difficulty: str = "easy") -> Question:
    q = Question(
        question_id=qid,
        title=f"Question {qid}",
        difficulty=Difficulty(difficulty),
        bloom_level=BloomLevel.APPLY,
        scenario="A warehouse robot must publish velocity.",
        tested_skills=["ROS2 publisher"],
        objective="Implement a publisher node.",
    )
    q.confidence = ConfidenceBreakdown(confidence=confidence, status="APPROVED" if confidence >= 85 else "PENDING")
    return q


def _qqa(qid: str, passed: bool, confidence: float = 90.0) -> QuestionQuality:
    return QuestionQuality(
        question_id=qid,
        passed=passed,
        confidence=confidence,
        discriminating=True,
        judge_approved=True,
        failed_checks=[] if passed else ["confidence 70 < 85"],
    )


def _state(questions, quality, attempts=0, max_attempts=2, step=0, max_steps=8,
           budget_tokens=None, budget_calls=None, tokens_spent=0, calls_spent=0):
    return RunState(
        questions=questions,
        coverage=CoverageMatrix(matrix={"ROS2 publisher": True}),
        quality=quality,
        attempts=attempts,
        max_attempts=max_attempts,
        step=step,
        max_steps=max_steps,
        budget_tokens=budget_tokens,
        budget_calls=budget_calls,
        tokens_spent=tokens_spent,
        calls_spent=calls_spent,
    )


# ---------------------------------------------------------------------------
# Routing decisions
# ---------------------------------------------------------------------------

def test_all_questions_pass_routes_to_finalize():
    p = _planner()
    qs = [_q("Q001", 91.0), _q("Q002", 88.0)]
    quality = [_qqa("Q001", True, 91.0), _qqa("Q002", True, 88.0)]
    decision = p.decide(_state(qs, quality))
    assert decision.action == PlanAction.FINALIZE
    assert decision.bar_passed == 2
    assert decision.bar_total == 2


def test_one_failing_question_routes_to_regenerate():
    p = _planner()
    qs = [_q("Q001", 91.0), _q("Q002", 60.0)]
    quality = [_qqa("Q001", True, 91.0), _qqa("Q002", False, 60.0)]
    decision = p.decide(_state(qs, quality, attempts=0, max_attempts=2))
    assert decision.action == PlanAction.REGENERATE
    assert "Q002" in decision.targets


def test_all_questions_failing_routes_to_regenerate():
    p = _planner()
    qs = [_q("Q001", 55.0), _q("Q002", 60.0)]
    quality = [_qqa("Q001", False, 55.0), _qqa("Q002", False, 60.0)]
    decision = p.decide(_state(qs, quality, attempts=0, max_attempts=3))
    assert decision.action == PlanAction.REGENERATE


def test_max_attempts_spent_routes_to_finalize():
    p = _planner()
    qs = [_q("Q001", 60.0)]
    quality = [_qqa("Q001", False, 60.0)]
    # attempts == max_attempts → finalize
    decision = p.decide(_state(qs, quality, attempts=2, max_attempts=2))
    assert decision.action == PlanAction.FINALIZE
    assert "Q001" in decision.targets


def test_max_steps_spent_routes_to_finalize():
    p = _planner()
    qs = [_q("Q001", 60.0)]
    quality = [_qqa("Q001", False, 60.0)]
    decision = p.decide(_state(qs, quality, step=8, max_steps=8))
    assert decision.action == PlanAction.FINALIZE


def test_token_budget_exhausted_routes_to_finalize():
    p = _planner()
    qs = [_q("Q001", 60.0)]
    quality = [_qqa("Q001", False, 60.0)]
    decision = p.decide(_state(
        qs, quality,
        budget_tokens=1000, tokens_spent=1200,  # over budget
    ))
    assert decision.action == PlanAction.FINALIZE
    assert "budget exhausted" in decision.reason.lower() or "token" in decision.reason.lower()


def test_call_budget_exhausted_routes_to_finalize():
    p = _planner()
    qs = [_q("Q001", 60.0)]
    quality = [_qqa("Q001", False, 60.0)]
    decision = p.decide(_state(
        qs, quality,
        budget_calls=5, calls_spent=6,
    ))
    assert decision.action == PlanAction.FINALIZE


def test_no_questions_routes_to_generate():
    """Edge case: empty question list → GENERATE."""
    p = _planner()
    decision = p.decide(_state([], quality=[], attempts=0))
    assert decision.action == PlanAction.GENERATE


def test_unvalidated_questions_routes_to_validate():
    """quality=None means questions haven't been validated yet."""
    p = _planner()
    qs = [_q("Q001", 90.0)]
    decision = p.decide(_state(qs, quality=None))
    assert decision.action == PlanAction.VALIDATE


# ---------------------------------------------------------------------------
# evaluate_quality
# ---------------------------------------------------------------------------

def test_evaluate_quality_passes_high_confidence(tmp_path):
    from robo_assess.config import Settings
    s = Settings()
    s.api_key = "fake"
    s.quality_bar.min_confidence = 85.0
    s.quality_bar.require_discriminating = False
    s.quality_bar.require_judge_approve = False
    s.quality_bar.require_in_scope = False

    p = PlannerAgent(settings=s, llm=None)
    q = _q("Q001", 92.0)
    q.similarity_score = 0.1
    coverage = CoverageMatrix(matrix={"ROS2 publisher": True})

    quality = p.evaluate_quality([q], coverage)
    assert quality[0].passed is True
    assert quality[0].question_id == "Q001"


def test_evaluate_quality_fails_low_confidence(tmp_path):
    from robo_assess.config import Settings
    s = Settings()
    s.api_key = "fake"
    s.quality_bar.min_confidence = 85.0
    s.quality_bar.require_discriminating = False
    s.quality_bar.require_judge_approve = False
    s.quality_bar.require_in_scope = False

    p = PlannerAgent(settings=s, llm=None)
    q = _q("Q001", 65.0)
    coverage = CoverageMatrix(matrix={"ROS2 publisher": True})

    quality = p.evaluate_quality([q], coverage)
    assert quality[0].passed is False
    assert any("confidence" in c.lower() for c in quality[0].failed_checks)


def test_evaluate_quality_fails_near_duplicate():
    from robo_assess.config import Settings
    s = Settings()
    s.api_key = "fake"
    s.quality_bar.min_confidence = 85.0
    s.quality_bar.require_discriminating = False
    s.quality_bar.require_judge_approve = False
    s.quality_bar.require_in_scope = False
    s.quality_bar.max_similarity = 0.75

    p = PlannerAgent(settings=s, llm=None)
    q = _q("Q001", 92.0)
    q.similarity_score = 0.90  # above threshold → near-duplicate
    coverage = CoverageMatrix(matrix={"ROS2 publisher": True})

    quality = p.evaluate_quality([q], coverage)
    assert quality[0].passed is False
    assert any("duplicate" in c.lower() or "sim" in c.lower()
               for c in quality[0].failed_checks)


def test_evaluate_quality_fails_scope_violation():
    from robo_assess.config import Settings
    s = Settings()
    s.api_key = "fake"
    s.quality_bar.min_confidence = 85.0
    s.quality_bar.require_discriminating = False
    s.quality_bar.require_judge_approve = False
    s.quality_bar.require_in_scope = True

    p = PlannerAgent(settings=s, llm=None)
    q = _q("Q001", 92.0)
    q.scope_violations = ["Nav2"]  # out-of-scope tech
    coverage = CoverageMatrix(matrix={"ROS2 publisher": True})

    quality = p.evaluate_quality([q], coverage)
    assert quality[0].passed is False
    assert any("scope" in c.lower() for c in quality[0].failed_checks)
