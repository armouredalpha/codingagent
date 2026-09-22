"""
Agent 6 — Difficulty Calibration
===============================

Re-derives the true difficulty of each question and reports mismatches against
the declared difficulty. This is the ONE difficulty engine in the pipeline —
``tools/handlers.py``'s LLM-facing ``estimate_difficulty`` tool calls
``estimate_from_source`` below rather than keeping its own duplicate heuristic.

``calibrate()`` is the rule-based estimator (distinct skills, solution LOC,
multi-file edits, Bloom level) — it is the deterministic fallback used when the
LLM critic can't score a question, and is also reused by the dataset evaluator
and the confidence agent. By default ``run()``
additionally scores the questions with the LLM critic in batches
(``difficulty_critic.txt``); the LLM verdict supersedes the heuristic per
question, and any question the LLM fails to score keeps its rule-based verdict.

``estimate_from_source()`` is a separate, lighter heuristic for a different
input shape: raw source text with no starter/Question object yet (the shape
available mid-generation, before a Question exists). It measures LOC +
cyclomatic complexity + ROS2 API surface on that one string, rather than
``calibrate()``'s TODO-marker workload signal on starter code — genuinely
different signals for different pipeline stages, not a redundant duplicate.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from ..schemas import AgentResult, BloomLevel, Difficulty, Question
from .base import BaseAgent
from ._llm_batch import run_batched_critic


def estimate_from_source(solution_code: str, declared_difficulty: str) -> dict:
    """Difficulty estimate from raw source text: LOC + cyclomatic complexity +
    ROS2 API surface. Used by tools/handlers.py's estimate_difficulty tool,
    exposed to the generation LLM as a self-check before it submits a question."""
    try:
        tree = ast.parse(solution_code)
    except SyntaxError:
        tree = None  # non-Python or unparseable — fall back to LOC only

    loc = len([l for l in solution_code.splitlines() if l.strip() and not l.strip().startswith("#")])

    ros2_apis = len(re.findall(
        r"(create_publisher|create_subscription|create_service|create_client|"
        r"create_timer|spin_once|spin|get_parameter|declare_parameter|"
        r"create_action_server|create_action_client)",
        solution_code,
    ))

    complexity = 0
    if tree:
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler)):
                complexity += 1

    if loc <= 35 and complexity <= 3 and ros2_apis <= 2:
        estimated = "easy"
    elif loc <= 90 and complexity <= 8 and ros2_apis <= 5:
        estimated = "medium"
    else:
        estimated = "hard"

    return {
        "loc": loc,
        "cyclomatic_complexity": complexity,
        "ros2_api_calls": ros2_apis,
        "estimated_difficulty": estimated,
        "declared_difficulty": declared_difficulty,
        "mismatch": estimated != declared_difficulty,
    }

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
        """Rule-based difficulty estimator.

        Difficulty is orthogonal to question type (TYPE_A/B/C). What matters
        is HOW MUCH the student writes, not total solution size:

          easy   = 0 new lines (find+fix one string value, no TODO blocks)
          medium = fix 1–2 values/expressions in existing code (no new logic)
          hard   = write 1–2 missing critical lines (# TODO markers present)

        We measure student workload from the *starter* code, not the reference
        solution — a TYPE_A question with a 200-line math library is not hard
        just because the solution is long; what makes it hard is whether the
        student must write new code lines.
        """
        # Count TODO blocks in starter code — the primary workload signal
        starter_todos = 0
        bug_markers = 0
        for f in q.files_to_edit:
            starter = f.starter_code or ""
            starter_todos += len(re.findall(r"#\s*TODO", starter, re.IGNORECASE))
            bug_markers += len(re.findall(r"#\s*BUG", starter, re.IGNORECASE))

        # CLI-only tasks (no files to edit) are always easy
        no_files = len(q.files_to_edit) == 0
        multifile = len(q.files_to_edit) > 1

        if no_files:
            d = Difficulty.EASY
            reason = "CLI-only (no files to edit)"
        elif starter_todos == 0 and not multifile:
            # No TODO blocks → student just fixes a wrong value (easy or medium)
            # Use bug marker count and task count as tiebreaker
            n_tasks = len(getattr(q, "tasks", [])) or 1
            if bug_markers <= 1 and n_tasks <= 1:
                d = Difficulty.EASY
                reason = f"0 TODOs, {bug_markers} BUG markers → string-fix only"
            else:
                d = Difficulty.MEDIUM
                reason = f"0 TODOs, {bug_markers} BUG markers, {n_tasks} tasks → value fixes"
        elif starter_todos <= 2:
            d = Difficulty.HARD
            reason = f"{starter_todos} TODO block(s) → student writes missing line(s)"
        else:
            # Many TODOs → implementation task; still hard by definition
            d = Difficulty.HARD
            reason = f"{starter_todos} TODO blocks → substantial implementation"

        if multifile and d == Difficulty.EASY:
            d = Difficulty.MEDIUM
            reason += ", multi-file → bumped to medium"

        # Bloom level can only raise difficulty, never lower it
        bloom_d = _BLOOM_DIFF[q.bloom_level]
        order = {Difficulty.EASY: 0, Difficulty.MEDIUM: 1, Difficulty.HARD: 2}
        if order[bloom_d] > order[d]:
            reason += f", bloom={q.bloom_level.value} raises to {bloom_d.value}"
            d = bloom_d

        return d, reason

    def _llm_verdicts(self, questions: list[Question]) -> dict[str, dict]:
        if self.llm is None:
            return {}
        template = _load_prompt(self.settings.prompts_dir)
        if not template:
            return {}
        def _todo_count(q: Question) -> int:
            return sum(len(re.findall(r"#\s*TODO", f.starter_code or "", re.IGNORECASE))
                       for f in q.files_to_edit)

        def _bug_count(q: Question) -> int:
            return sum(len(re.findall(r"#\s*BUG", f.starter_code or "", re.IGNORECASE))
                       for f in q.files_to_edit)

        def _starter_snippet(q: Question) -> str:
            # Send first 600 chars of first starter file for context
            for f in q.files_to_edit:
                if f.starter_code:
                    return f.starter_code[:600]
            return ""

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
                # Workload signals — use these, NOT solution_loc
                "starter_todo_count": _todo_count(q),
                "starter_bug_marker_count": _bug_count(q),
                "starter_snippet": _starter_snippet(q),
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
        patches: dict[str, dict] = {}
        n_llm = 0
        for q in questions:
            v = verdicts.get(q.question_id)
            if v is not None:
                n_llm += 1
                calibrated = Difficulty(str(v["difficulty"]).lower())
                reason = str(v.get("rationale", "")) or "llm verdict"
            else:
                calibrated, reason = self.calibrate(q)
            patches[q.question_id] = {"calibrated_difficulty": calibrated}
            if calibrated != q.difficulty:
                mismatches.append(
                    {"qid": q.question_id, "declared": q.difficulty.value,
                     "calibrated": calibrated.value, "reason": reason}
                )

        qt = []
        for m in mismatches:
            qt.append({"qid": m["qid"], "decision": "difficulty_mismatch",
                       "reason": f"declared={m['declared']} calibrated={m['calibrated']}: {m['reason']}"})
        # Also trace questions where calibration agreed (pass)
        for q in questions:
            if q.question_id not in {m["qid"] for m in mismatches}:
                cal = patches.get(q.question_id, {}).get("calibrated_difficulty", q.difficulty)
                qt.append({"qid": q.question_id, "decision": "difficulty_ok",
                           "reason": f"declared={q.difficulty.value} confirmed={getattr(cal,'value',str(cal))}"})
        res = self._result(mismatches=mismatches, patches=patches, question_traces=qt)
        src = f"llm:{n_llm}/{len(questions)}" if n_llm else "rule-based"
        res.messages.append(f"{len(mismatches)} difficulty mismatches ({src})")
        return res.finish("warn" if mismatches else "ok")
