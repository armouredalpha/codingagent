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
    name = "eval_comparator"

    def __init__(self, settings: Settings, llm: LLMClient, memory: Memory,
                 vectorstore: VectorStore, **kwargs):
        super().__init__(settings=settings, llm=llm, memory=memory, **kwargs)
        self.vectorstore = vectorstore
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

    # Minimum similarity for a reference to be considered relevant.
    # Below this the topics are too different for difficulty comparison to mean anything.
    _MIN_SIM = 0.15

    def _find_closest_refs(self, question: Question, top_k: int = 3) -> list[tuple[str, float]]:
        """Return top-k (ref_id, similarity) pairs above _MIN_SIM threshold."""
        if not self.eval_refs:
            return []

        q_text = f"{question.title} {question.scenario} {' '.join(question.tested_skills)}"
        ref_texts = [f"{r.title} {r.scenario} {' '.join(r.skills)}" for r in self.eval_refs]
        scored = [
            (ref.id, text_similarity(q_text, ref_text))
            for ref, ref_text in zip(self.eval_refs, ref_texts)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        # Only keep refs that are actually similar enough to be meaningful
        relevant = [(rid, sim) for rid, sim in scored if sim >= self._MIN_SIM]
        return relevant[:top_k]

    def _score_difficulty_match(
        self, question: Question, closest: list[tuple[str, float]]
    ) -> float | None:
        """Score difficulty match against closest refs.

        Skips LLM and returns None when no relevant references exist — the caller
        treats None as 'no_match' and does not penalise confidence.
        When refs exist, uses similarity-weighted difficulty comparison (no LLM call).
        """
        if not closest:
            return None

        # Difficulty tier weights — compare declared difficulty vs ref difficulty
        _TIER = {"easy": 1, "medium": 2, "hard": 3}
        q_tier = _TIER.get(question.difficulty.value, 2)

        weighted_score = 0.0
        total_weight = 0.0
        for ref_id, sim in closest:
            ref = next((r for r in self.eval_refs if r.id == ref_id), None)
            if not ref:
                continue
            ref_tier = _TIER.get(str(ref.difficulty).lower(), 2)
            # Score 100 if same tier, 60 if 1 tier off, 20 if 2 tiers off
            tier_diff = abs(q_tier - ref_tier)
            tier_score = [100.0, 60.0, 20.0][min(tier_diff, 2)]
            weighted_score += tier_score * sim
            total_weight += sim

        if total_weight == 0:
            return None
        return round(weighted_score / total_weight, 1)

    def _load_prompt(self, filename: str) -> str:
        path = Path(self.settings.prompts_dir) / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def run(self, question: Question) -> AgentResult:
        """Compare question against eval set and score difficulty match."""
        if not self.eval_refs:
            # No reference set configured — skip scoring entirely rather than
            # emitting a misleading neutral 50/100 that poisons downstream signals.
            comparison = EvalComparison(
                eval_match_score=0.0,
                closest_refs=[],
                difficulty_verdict="no_refs",
                style_notes="No eval references loaded; skipping comparison.",
            )
            question.eval_comparison = comparison
            return self._result(
                comparison=comparison.model_dump(),
                messages=["eval_comparator skipped: no reference set configured"],
            ).finish("skip")

        closest = self._find_closest_refs(question)
        closest_ids = [ref_id for ref_id, _ in closest]
        eval_match_score = self._score_difficulty_match(question, closest)

        if eval_match_score is None:
            difficulty_verdict = "no_match"
            style_notes = "No similar references in eval set — difficulty score not penalised."
            eval_match_score = 75.0  # neutral: don't penalise when topic has no close refs
        elif eval_match_score >= 85:
            difficulty_verdict = question.difficulty.value
            style_notes = f"Match quality: {eval_match_score}/100"
        elif eval_match_score >= 65:
            difficulty_verdict = "uncertain"
            style_notes = f"Match quality: {eval_match_score}/100 — possible tier mismatch"
        else:
            difficulty_verdict = "mismatch"
            style_notes = f"Match quality: {eval_match_score}/100 — difficulty likely wrong"

        comparison = EvalComparison(
            eval_match_score=eval_match_score,
            closest_refs=closest_ids,
            difficulty_verdict=difficulty_verdict,
            style_notes=style_notes,
        )
        question.eval_comparison = comparison

        return self._result(
            comparison=comparison.model_dump(),
            messages=[
                f"Difficulty match: {eval_match_score}/100 ({difficulty_verdict})",
                f"Closest refs: {', '.join(f'{r}({s:.2f})' for r, s in closest)}",
            ],
        )
