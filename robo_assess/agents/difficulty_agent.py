"""
Agent 6 — Difficulty Calibration
===============================

Re-derives the true difficulty of each question and reports mismatches against
the declared difficulty.

``calibrate()`` is the rule-based estimator (distinct skills, solution LOC,
multi-file edits, Bloom level) — it is the deterministic fallback used when the
LLM critic can't score a question, and is also reused by the dataset evaluator
and the confidence agent. By default ``run()``
additionally scores the questions with the LLM critic in batches
(``difficulty_critic.txt``); the LLM verdict supersedes the heuristic per
question, and any question the LLM fails to score keeps its rule-based verdict.
"""

from __future__ import annotations

from pathlib import Path

from ..schemas import AgentResult, BloomLevel, Difficulty, Question
from .base import BaseAgent
from ._llm_batch import run_batched_critic

# Bloom acts only as an UPWARD floor on the LOC/skill estimate. A coding
# scaffold is inherently at least APPLY, so APPLY must map to EASY — otherwise
# every small "apply a publisher" task is forced to MEDIUM and permanently
# disagrees with the generator (which labels easy questions APPLY). Only the
# genuinely higher-order verbs (ANALYZE/EVALUATE/CREATE) pull difficulty up.
_BLOOM_DIFF = {
    BloomLevel.REMEMBER: Difficulty.EASY,
    BloomLevel.UNDERSTAND: Difficulty.EASY,
    BloomLevel.APPLY: Difficulty.EASY,
    BloomLevel.ANALYZE: Difficulty.MEDIUM,
    BloomLevel.EVALUATE: Difficulty.HARD,
    BloomLevel.CREATE: Difficulty.HARD,
}

_SYSTEM_PROMPT = (
    "You are the Difficulty Calibration Agent for a ROS2 Humble assessment "
    "pipeline. Return ONLY valid JSON, no markdown, no prose."
)


def _load_prompt(prompts_dir: str) -> str | None:
    p = Path(prompts_dir) / "difficulty_critic.txt"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _valid_difficulty_verdict(v: dict) -> bool:
    return str(v.get("difficulty", "")).lower() in ("easy", "medium", "hard")


class DifficultyCalibrationAgent(BaseAgent):
    name = "difficulty_agent"

    def __init__(self, *args, token_counter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_counter = token_counter

    # ------------------------------------------------------------------ #
    def calibrate(self, q: Question) -> tuple[Difficulty, str]:
        n_skills = len(set(q.tested_skills))
        loc = sum(
            len(f.reference_solution.splitlines()) for f in q.files_to_edit
        )
        multifile = len(q.files_to_edit) > 1

        # CLI-only tasks (no files to edit) are always easy
        no_files = len(q.files_to_edit) == 0
        if no_files:
            d = Difficulty.EASY
        elif n_skills <= 1 and loc < 35 and not multifile:
            d = Difficulty.EASY
        elif n_skills <= 4 and loc < 80:
            d = Difficulty.MEDIUM
        else:
            d = Difficulty.HARD

        # Bloom level pulls difficulty up when it implies higher cognition
        bloom_d = _BLOOM_DIFF[q.bloom_level]
        order = {Difficulty.EASY: 0, Difficulty.MEDIUM: 1, Difficulty.HARD: 2}
        if order[bloom_d] > order[d]:
            d = bloom_d
        reason = (
            f"{n_skills} skills, ~{loc} solution LOC, "
            f"{'multi-file' if multifile else 'single-file'}, bloom={q.bloom_level.value}"
        )
        return d, reason

    def _llm_verdicts(self, questions: list[Question]) -> dict[str, dict]:
        if self.llm is None:
            return {}
        template = _load_prompt(self.settings.prompts_dir)
        if not template:
            return {}
        payload = [
            {
                "id": q.question_id,
                "title": q.title,
                "scenario": q.scenario,
                "objective": q.objective,
                "tested_skills": q.tested_skills,
                "constraints": q.constraints,
                "declared_difficulty": q.difficulty.value,
                "bloom_level": q.bloom_level.value,
                "solution_loc": sum(
                    len(f.reference_solution.splitlines()) for f in q.files_to_edit
                ),
                "files": len(q.files_to_edit),
            }
            for q in questions
        ]
        return run_batched_critic(
            llm=self.llm,
            system=_SYSTEM_PROMPT,
            template=template,
            payload=payload,
            settings=self.settings,
            validate=_valid_difficulty_verdict,
            agent_name=self.name,
            log=self.log,
            token_counter=self.token_counter,
        )

    # ------------------------------------------------------------------ #
    def run(self, questions: list[Question]) -> AgentResult:
        verdicts = self._llm_verdicts(questions)

        mismatches = []
        n_llm = 0
        for q in questions:
            v = verdicts.get(q.question_id)
            if v is not None:
                n_llm += 1
                calibrated = Difficulty(str(v["difficulty"]).lower())
                reason = str(v.get("rationale", "")) or "llm verdict"
            else:
                calibrated, reason = self.calibrate(q)
            # Persist the calibrated verdict so the Confidence agent can score
            # the *fit* between declared and true difficulty instead of treating
            # difficulty as a free constant.
            q.calibrated_difficulty = calibrated
            if calibrated != q.difficulty:
                mismatches.append(
                    {"qid": q.question_id, "declared": q.difficulty.value,
                     "calibrated": calibrated.value, "reason": reason}
                )

        res = self._result(mismatches=mismatches)
        src = f"llm:{n_llm}/{len(questions)}" if n_llm else "rule-based"
        res.messages.append(f"{len(mismatches)} difficulty mismatches ({src})")
        return res.finish("warn" if mismatches else "ok")
