"""Dataset-level evaluation: aggregate metrics for a set of generated questions.

Computes coverage, difficulty distribution, confidence, and overall quality score.
"""

from __future__ import annotations

from typing import Any

from ..schemas import CoverageMatrix, Question
from ..config import Settings


def evaluate_batch(
    questions: list[Question],
    coverage: CoverageMatrix,
    settings: Settings,
) -> dict[str, Any]:
    """Evaluate overall quality of a question batch.

    Args:
        questions: Generated questions
        coverage: Coverage matrix
        settings: System configuration

    Returns:
        Dict with overall_score, coverage, difficulty distribution, and per-criteria scores.
    """
    if not questions:
        return {
            "overall_score": 0,
            "total_questions": 0,
            "approved": 0,
            "coverage": 0,
            "criteria": {},
        }

    # Count approved (high-confidence) questions
    approved = sum(
        1 for q in questions
        if q.confidence and q.confidence.confidence >= settings.quality_bar.min_confidence
    )

    # Difficulty distribution
    difficulties = {"easy": 0, "medium": 0, "hard": 0}
    for q in questions:
        diff = q.difficulty.value.lower()
        difficulties[diff] = difficulties.get(diff, 0) + 1

    # Average confidence
    avg_confidence = 0.0
    if questions:
        confidences = [
            q.confidence.confidence
            for q in questions
            if q.confidence and q.confidence.confidence is not None
        ]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)

    # Average originality (1 - similarity)
    avg_originality = 0.0
    if questions:
        similarities = [q.similarity_score for q in questions if q.similarity_score is not None]
        if similarities:
            avg_originality = (1.0 - sum(similarities) / len(similarities)) * 100

    # Grading pass rate
    grading_pass = sum(
        1 for q in questions
        if q.grading_execution and q.grading_execution.status == "PASS"
    )

    # Auto-gradable count
    auto_gradable = sum(1 for q in questions if q.auto_gradable)

    # Overall score: weighted combination
    # 35% coverage, 25% confidence, 20% difficulty balance, 10% originality, 10% auto-gradable
    coverage_score = coverage.coverage_pct if coverage else 0
    confidence_score = avg_confidence
    difficulty_balance = 100 - abs(
        (difficulties["easy"] / len(questions) - 0.3) * 100
        + (difficulties["hard"] / len(questions) - 0.2) * 100
    )  # Penalize deviation from 30/50/20 split
    originality_score = avg_originality
    gradability_score = (auto_gradable / len(questions) * 100) if questions else 0

    overall_score = (
        coverage_score * 0.35
        + confidence_score * 0.25
        + min(difficulty_balance, 100) * 0.20
        + originality_score * 0.10
        + gradability_score * 0.10
    )

    return {
        "overall_score": round(overall_score, 1),
        "total_questions": len(questions),
        "approved": approved,
        "approval_rate": round(approved / len(questions) * 100, 1) if questions else 0,
        "coverage": {
            "coverage_pct": coverage.coverage_pct if coverage else 0,
            "skills_tested": len(coverage.covered) if coverage else 0,
            "skills_total": len(coverage.matrix) if coverage else 0,
        },
        "difficulty_distribution": difficulties,
        "criteria": {
            "avg_confidence": round(confidence_score, 1),
            "avg_originality": round(originality_score, 1),
            "auto_gradable_rate": round(gradability_score, 1),
            "grading_pass_rate": round(
                grading_pass / len(questions) * 100, 1
            ) if questions else 0,
            "difficulty_balance": round(difficulty_balance, 1),
        },
    }
