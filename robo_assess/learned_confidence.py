"""
Learned Confidence Scorer: Use reference questions to calibrate confidence.

Instead of heuristic rubric scoring, learns from:
1. Reference question quality/pass rates
2. Generated question similarity to references
3. Predicted student pass rates based on features
"""

from __future__ import annotations

import json
from typing import Any

from .schemas import Question
from .vectorstore import text_similarity


class LearnedConfidenceScorer:
    """Score confidence by comparing to reference questions."""

    def __init__(self, reference_scores: dict[str, dict[str, Any]]):
        """
        Args:
            reference_scores: Dict from StateManager.load_reference_scores()
                Keys: ref_id
                Values: {title, difficulty, scenario, skills, quality_score, expected_pass_rate, ...}
        """
        self.reference_scores = reference_scores

    def compute_features(self, question: Question) -> dict[str, Any]:
        """Extract features that predict student pass rates."""
        # Count code lines
        code_lines = 0
        if question.boilerplate_code:
            code_lines += len(question.boilerplate_code.splitlines())
        for f in question.files_to_edit:
            if f.reference_solution:
                code_lines += len(f.reference_solution.splitlines())

        return {
            "num_skills": len(question.tested_skills),
            "num_criteria": len(question.evaluation_criteria),
            "lines_of_code": code_lines,
            "bloom_level_rank": self._bloom_rank(question.bloom_level.value),
            "has_constraints": len(question.constraints) > 0,
            "scenario_complexity": len(question.scenario.split()),
            "num_common_mistakes": len(question.common_mistakes),
        }

    def _bloom_rank(self, bloom_level: str) -> int:
        """Map Bloom level to numeric rank."""
        ranks = {
            "remember": 1,
            "understand": 2,
            "apply": 3,
            "analyze": 4,
            "evaluate": 5,
            "create": 6,
        }
        return ranks.get(bloom_level.lower(), 3)

    def find_similar_references(
        self, question: Question, top_k: int = 3
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """Find top-k most similar reference questions by scenario similarity.

        Returns: [(ref_id, similarity_score, ref_data), ...]
        """
        if not self.reference_scores:
            return []

        # Embed question scenario
        gen_text = f"{question.title} {question.scenario} {' '.join(question.tested_skills)}"

        similarities = []
        for ref_id, ref_data in self.reference_scores.items():
            ref_text = f"{ref_data['title']} {ref_data['scenario']} {' '.join(ref_data.get('skills', []))}"

            # Use existing text_similarity function (cosine + jaccard blend)
            sim = text_similarity(gen_text, ref_text)
            similarities.append((ref_id, sim, ref_data))

        # Sort by similarity, return top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def predict_pass_rate(
        self,
        features: dict[str, Any],
        similar_refs: list[tuple[str, float, dict[str, Any]]],
    ) -> float:
        """Predict student pass rate (0-1) based on reference data and features.

        Logic:
        - Find average pass rate of similar references
        - Adjust for feature differences (more skills = harder)
        """
        if not similar_refs:
            return 0.5  # Neutral if no references

        # Average expected pass rate from similar references
        avg_pass_rate = sum(r[2]["expected_pass_rate"] for r in similar_refs) / len(
            similar_refs
        )

        # Adjust by features
        # Each additional skill reduces pass rate by ~5%
        skill_penalty = 0.95 ** (features["num_skills"] - 1)

        # Higher Bloom level reduces pass rate
        bloom_penalty = 1.0 if features["bloom_level_rank"] <= 3 else 0.95

        adjusted_pass_rate = avg_pass_rate * skill_penalty * bloom_penalty
        return max(0.1, min(0.95, adjusted_pass_rate))  # Clamp [0.1, 0.95]

    def score(
        self,
        question: Question,
        validators: dict[str, float],
    ) -> tuple[float, dict[str, Any]]:
        """Compute learned confidence score.

        Args:
            question: Generated question
            validators: {
                "auto_grading": 0-100,
                "originality": 0-100,
                "format_compliance": 0-100,
            }

        Returns: (confidence_score, breakdown_dict)
        """
        features = self.compute_features(question)
        similar_refs = self.find_similar_references(question, top_k=3)

        # Similarity to references (0-1 → 0-100)
        similarity_score = (
            sum(sim for _, sim, _ in similar_refs) / len(similar_refs) * 100
            if similar_refs
            else 50.0
        )

        # Expected pass rate (0-1 → 0-100)
        expected_pass_rate = self.predict_pass_rate(features, similar_refs)
        pass_rate_score = expected_pass_rate * 100

        # Weighted combination
        confidence = (
            0.30 * similarity_score
            + 0.25 * pass_rate_score
            + 0.20 * validators.get("auto_grading", 0)
            + 0.15 * validators.get("originality", 0)
            + 0.10 * validators.get("format_compliance", 0)
        )

        breakdown = {
            "raw_confidence": confidence,
            "similarity_to_references": similarity_score,
            "expected_pass_rate": pass_rate_score,
            "auto_grading": validators.get("auto_grading", 0),
            "originality": validators.get("originality", 0),
            "format_compliance": validators.get("format_compliance", 0),
        }

        # Store reference info for later analysis
        breakdown["similar_refs"] = [r[0] for r in similar_refs]
        breakdown["features"] = features

        return confidence, breakdown


def load_reference_scores_from_json(
    evaluations_dir: str,
) -> dict[str, dict[str, Any]]:
    """Load reference questions from evaluations/question.json and solution.json.

    Returns: {ref_id: {title, difficulty, scenario, skills, quality_score, expected_pass_rate, ...}}
    """
    from pathlib import Path

    evals_dir = Path(evaluations_dir)
    questions_file = evals_dir / "question.json"
    solutions_file = evals_dir / "solution.json"

    if not questions_file.exists():
        return {}

    # Load questions
    questions_data = json.loads(questions_file.read_text())
    if not isinstance(questions_data, list):
        questions_data = [questions_data]

    # Load solutions
    solutions_data = {}
    if solutions_file.exists():
        sol_data = json.loads(solutions_file.read_text())
        if isinstance(sol_data, list):
            solutions_data = {item.get("id"): item for item in sol_data}
        else:
            solutions_data = sol_data

    # Merge
    references = {}
    for q in questions_data:
        ref_id = q.get("id", "unknown")
        sol = solutions_data.get(ref_id, {})

        references[ref_id] = {
            "id": ref_id,
            "title": q.get("title", ""),
            "difficulty": q.get("difficulty", "medium"),
            "scenario": q.get("scenario", ""),
            "skills": q.get("skills", []),
            "quality_score": float(
                q.get("quality_score", 80)
            ),  # Default to 80 if not specified
            "expected_pass_rate": float(
                q.get("expected_pass_rate", 0.8)
            ),  # Default to 80% if not specified
            "num_tests_passed": sol.get("num_tests_passed", 0),
            "num_tests_total": sol.get("num_tests_total", 0),
        }

    return references
