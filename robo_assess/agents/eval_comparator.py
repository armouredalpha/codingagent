"""
Eval Comparator Agent
====================

Compares generated questions against reference eval sets to calibrate difficulty.
Returns: eval_match_score (0-100), closest_refs, difficulty_verdict

Target: ≥ 85 means good difficulty calibration.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import Settings
from ..llm_client import LLMClient
from ..memory import Memory
from ..schemas import EvalComparison, EvalReference, Question
from ..vectorstore import VectorStore, text_similarity
from .base import BaseAgent, AgentResult


class EvalComparatorAgent(BaseAgent):
    def __init__(self, settings: Settings, llm: LLMClient, memory: Memory,
                 vectorstore: VectorStore, **kwargs):
        super().__init__(settings=settings, llm=llm, memory=memory, **kwargs)
        self.vectorstore = vectorstore
        self.name = "eval_comparator"
        self.eval_refs: list[EvalReference] = []
        self._load_eval_sets()

    def _load_eval_sets(self) -> None:
        """Load reference questions and solutions from evaluations/ folder."""
        evals_dir = Path(self.settings.evaluations_dir)

        # Load questions.json
        questions_file = evals_dir / "question.json"
        if not questions_file.exists():
            self.log.warning("eval_sets_missing", file=str(questions_file))
            return

        try:
            questions_data = json.loads(questions_file.read_text())
            if not isinstance(questions_data, list):
                questions_data = [questions_data]
        except (json.JSONDecodeError, IOError):
            self.log.warning("eval_sets_load_error", file=str(questions_file))
            return

        # Load solutions.json
        solutions_data = {}
        solutions_file = evals_dir / "solution.json"
        if solutions_file.exists():
            try:
                sol_data = json.loads(solutions_file.read_text())
                if isinstance(sol_data, list):
                    solutions_data = {item.get("id"): item for item in sol_data}
                else:
                    solutions_data = sol_data
            except (json.JSONDecodeError, IOError):
                pass

        # Build EvalReference objects
        for q in questions_data:
            sol = solutions_data.get(q.get("id"), {})
            ref = EvalReference(
                id=q.get("id", "unknown"),
                title=q.get("title", ""),
                difficulty=q.get("difficulty", "medium"),
                scenario=q.get("scenario", ""),
                skills=q.get("skills", []),
                solution_summary=sol.get("solution_summary", "")
            )
            self.eval_refs.append(ref)

        self.log.info("eval_sets_loaded", count=len(self.eval_refs))

    def _find_closest_refs(self, question: Question, top_k: int = 3) -> list[str]:
        """Find top-k most similar eval references using text similarity."""
        if not self.eval_refs:
            return []

        q_text = f"{question.title} {question.scenario} {' '.join(question.tested_skills)}"
        similarities = []

        for ref in self.eval_refs:
            ref_text = f"{ref.title} {ref.scenario} {' '.join(ref.skills)}"
            sim = text_similarity(q_text, ref_text)
            similarities.append((ref.id, sim))

        # Sort by similarity, return top-k IDs
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [ref_id for ref_id, _ in similarities[:top_k]]

    def _score_difficulty_match(self, question: Question, closest_refs: list[str]) -> float:
        """LLM scores difficulty match (0-100)."""
        if not closest_refs:
            return 50.0  # Neutral if no references available

        # Build reference summaries
        ref_summaries = []
        for ref_id in closest_refs:
            ref = next((r for r in self.eval_refs if r.id == ref_id), None)
            if ref:
                ref_summaries.append(
                    f"[{ref.id}] {ref.title}\n"
                    f"Difficulty: {ref.difficulty}\n"
                    f"Scenario: {ref.scenario[:200]}..."
                )

        prompt = self._load_prompt("eval_comparator.txt")
        prompt = prompt.format(
            title=question.title,
            difficulty=question.difficulty.value,
            scenario=question.scenario[:300],
            skills=", ".join(question.tested_skills),
            closest_refs="\n\n".join(ref_summaries)
        )

        try:
            result, _ = self.llm.complete_json(
                system="You are a difficulty calibrator.",
                user=prompt,
                temperature=0.3,
                max_tokens=400
            )

            score = float(result.get("eval_match_score", 50))
            return min(100.0, max(0.0, score))
        except Exception:
            return 50.0

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template."""
        path = Path(self.settings.prompts_dir) / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def run(self, question: Question) -> AgentResult:
        """Compare question against eval set and score difficulty match."""
        closest_refs = self._find_closest_refs(question)
        eval_match_score = self._score_difficulty_match(question, closest_refs)

        # Determine difficulty verdict
        if eval_match_score >= 85:
            difficulty_verdict = question.difficulty.value
        elif eval_match_score >= 65:
            # Likely a different tier
            difficulty_verdict = "uncertain"
        else:
            difficulty_verdict = "mismatch"

        comparison = EvalComparison(
            eval_match_score=eval_match_score,
            closest_refs=closest_refs,
            difficulty_verdict=difficulty_verdict,
            style_notes=f"Match quality: {eval_match_score}/100"
        )

        question.eval_comparison = comparison

        return self._result(
            comparison=comparison.model_dump(),
            messages=[
                f"Difficulty match: {eval_match_score}/100",
                f"Closest refs: {', '.join(closest_refs)}"
            ]
        )
