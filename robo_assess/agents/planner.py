"""
Planner Agent — the autonomy core
=================================

This is what makes the system *agentic* rather than a fixed DAG. Instead of the
orchestrator running a hardcoded sequence, the planner observes the current run
state on every tick and **decides the next action**:

    GENERATE → VALIDATE → (REGENERATE ⟲ VALIDATE)* → FINALIZE | ABORT

The decision is model-in-the-loop with deterministic safety rails:

* ``evaluate_quality`` scores every question against the configured quality bar
  (confidence, executable-grading discrimination, independent judge, originality,
  scope, difficulty-fit). This is the gate that decides ship-vs-regenerate.
* ``reflect`` asks the LLM *why* the failing questions fall short and what to
  change — a Reflexion-style step whose feedback is injected into targeted
  regeneration so the loop converges instead of re-rolling blindly.
* ``decide`` picks the next action. The LLM may *advise*, but rails guarantee the
  planner never finalizes below-bar work while budget remains, never regenerates
  past budget, and never loops forever.

The whole point: set the bar HIGH on a weak local model. A question that clears
this gate on qwen2.5-coder:7b clears it trivially on Claude, so the bar transfers
upward unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..schemas import (
    CoverageMatrix,
    Difficulty,
    PlanAction,
    PlanStep,
    Question,
    QuestionQuality,
)
from ._llm_batch import run_batched_critic
from .base import BaseAgent

# Reuse the supervisor's independent-judge rubric so there is one definition of
# "is this a realistic, correctly-scoped, auto-gradable ticket".
from .supervisor import _JUDGE_SYSTEM, _valid_judge_verdict

_CRITIC_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "llm_critic.txt"


def _load_critic_prompt() -> str:
    try:
        return _CRITIC_PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


_LLM_CRITIC_TEMPLATE = _load_critic_prompt()

_DIFF_ORDER = {Difficulty.EASY: 0, Difficulty.MEDIUM: 1, Difficulty.HARD: 2}

def _load_planner_system() -> str:
    """Load planner reflect prompt from file, fall back to inline."""
    path = Path(__file__).parent.parent.parent / "prompts" / "planner_reflect.txt"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return (
            "You are the PLANNER of a robotics-assessment generation system. You are "
            "given the current state of a batch of ROS2 coding questions and the quality "
            "bar they must meet. For each FAILING question, explain crisply what is wrong "
            "and the single most important change that would make it pass. Return ONLY "
            'JSON: {"results":[{"id":"...","fix":"one concrete instruction"}]}'
        )


_PLANNER_SYSTEM = _load_planner_system()


def _valid_fix(v: dict) -> bool:
    return bool(str(v.get("fix", "")).strip())


@dataclass
class RunState:
    """Everything the planner needs to choose the next action."""

    questions: list[Question]
    coverage: CoverageMatrix
    quality: list[QuestionQuality] | None  # None ⇒ not validated since last change
    attempts: int                          # regeneration rounds spent
    max_attempts: int
    step: int
    max_steps: int
    feedback: dict[str, str] = field(default_factory=dict)

    # Budget tracking — None means no budget constraint
    tokens_spent: int = 0
    calls_spent: int = 0
    budget_tokens: int | None = None
    budget_calls: int | None = None

    def budget_exhausted(self) -> tuple[bool, str]:
        """Return (exhausted, reason). Empty reason means not exhausted."""
        if self.budget_tokens is not None and self.tokens_spent >= self.budget_tokens:
            pct = self.tokens_spent / self.budget_tokens * 100
            return True, f"token budget exhausted ({self.tokens_spent:,}/{self.budget_tokens:,} = {pct:.0f}%)"
        if self.budget_calls is not None and self.calls_spent >= self.budget_calls:
            return True, f"call budget exhausted ({self.calls_spent}/{self.budget_calls} calls)"
        return False, ""

    def tokens_remaining(self) -> int | None:
        if self.budget_tokens is None:
            return None
        return max(0, self.budget_tokens - self.tokens_spent)


class PlannerAgent(BaseAgent):
    name = "planner"

    # -- quality bar --------------------------------------------------------- #
    def _difficulty_fit(self, q: Question) -> float:
        calibrated = q.calibrated_difficulty or q.difficulty
        distance = abs(_DIFF_ORDER[q.difficulty] - _DIFF_ORDER[calibrated])
        return {0: 1.0, 1: 0.8}.get(distance, 0.3)

    def _run_judge(self, questions: list[Question]) -> dict[str, dict]:
        """Independent per-question APPROVE/REJECT verdicts. Empty (⇒ everything
        treated as approved) when no LLM is wired or the judge errors — the judge
        can only ADD rejections, never rescue a question."""
        if self.llm is None:
            return {}
        payload = [
            {
                "id": q.question_id,
                "title": q.title,
                "scenario": q.scenario,
                "objective": q.objective,
                "constraints": q.constraints,
                "tested_skills": q.tested_skills,
                "evaluation_criteria": [c.model_dump() for c in q.evaluation_criteria],
                "difficulty": q.difficulty.value,
            }
            for q in questions
        ]
        template = '{"questions": __Q__}'.replace("__Q__", "{questions}")
        try:
            return run_batched_critic(
                llm=self.llm, system=_JUDGE_SYSTEM, template=template, payload=payload,
                settings=self.settings, validate=_valid_judge_verdict,
                agent_name="planner_judge", log=self.log,
            )
        except Exception as exc:  # noqa: BLE001 — judge is advisory; never fatal
            self.log.warning("planner_judge_failed", error=str(exc))
            return {}

    def evaluate_quality(
        self, questions: list[Question], coverage: CoverageMatrix
    ) -> list[QuestionQuality]:
        bar = self.settings.quality_bar
        judge = self._run_judge(questions) if bar.require_judge_approve else {}

        out: list[QuestionQuality] = []
        for q in questions:
            checks: list[str] = []

            conf = q.confidence.confidence if q.confidence else 0.0
            if conf < bar.min_confidence:
                checks.append(f"confidence {conf:.0f} < {bar.min_confidence:.0f}")

            ge = q.grading_execution
            discriminating = bool(ge and ge.discriminating)
            if bar.require_discriminating:
                # Honest soft-gate: only a genuine FAIL counts against the bar.
                # NO_ARTIFACTS / SKIPPED_NO_RUNTIME (no reference, or no pytest on
                # this host) are recorded but do not block — consistent with the
                # ExecutableGradingAgent contract.
                if ge and ge.status == "FAIL":
                    checks.append(f"executable grading FAIL: {ge.detail}")

            if bar.require_in_scope and q.scope_violations:
                checks.append(f"out-of-scope: {', '.join(q.scope_violations)}")

            if not q.auto_gradable:
                checks.append("not auto-gradable")

            if q.similarity_score > bar.max_similarity:
                checks.append(f"near-duplicate (sim {q.similarity_score:.2f})")

            fit = self._difficulty_fit(q)
            if fit < bar.min_difficulty_fit:
                checks.append(
                    f"declared {q.difficulty.value} disagrees with calibrated "
                    f"{(q.calibrated_difficulty or q.difficulty).value}"
                )

            # skill_drift is informational only — bug-fix questions intentionally
            # test one focused sub-skill; do not block quality bar on this signal.

            jv = judge.get(q.question_id)
            judge_approved = True
            if jv and str(jv.get("verdict", "")).upper() == "REJECT":
                judge_approved = False
                if bar.require_judge_approve:
                    jr = "; ".join(str(r) for r in jv.get("reasons", [])) or "judge rejected"
                    checks.append(f"independent judge REJECT: {jr}")

            out.append(QuestionQuality(
                question_id=q.question_id,
                passed=not checks,
                confidence=conf,
                discriminating=discriminating,
                judge_approved=judge_approved,
                failed_checks=checks,
            ))
        return out

    # -- reflection (LLM feedback for regeneration) -------------------------- #
    def _llm_critic_diagnose(self, q: Question, qq: QuestionQuality) -> str | None:
        """Use llm_critic.txt for questions with 2+ failed checks (critical severity).

        Returns a structured fix directive string, or None if unavailable.
        The batch reflector handles simple (single-check) failures; the targeted
        critic handles complex multi-issue failures with more specific guidance.
        """
        if not _LLM_CRITIC_TEMPLATE or self.llm is None:
            return None
        if len(qq.failed_checks) < 2:
            return None  # simple failures handled by batch reflector

        ec = q.eval_comparison
        prompt = _LLM_CRITIC_TEMPLATE
        for k, v in [
            ("{question_id}", q.question_id),
            ("{title}", q.title),
            ("{difficulty}", q.difficulty.value),
            ("{scenario}", q.scenario or ""),
            ("{tested_skills}", ", ".join(q.tested_skills)),
            ("{confidence}", str(round(q.confidence.confidence, 1) if q.confidence else 0.0)),
            ("{eval_match_score}", str(ec.eval_match_score if ec else 0)),
            ("{originality}", str(round((1.0 - q.similarity_score) * 100, 1))),
            ("{scope_violations}", ", ".join(q.scope_violations) or "none"),
            ("{auto_gradable}", str(q.auto_gradable)),
            ("{failed_checks}", "\n".join(f"- {c}" for c in qq.failed_checks)),
        ]:
            prompt = prompt.replace(k, v)

        try:
            result, _ = self.llm.complete_json(
                system="You are a demanding senior robotics engineer diagnosing a failing assessment question.",
                user=prompt,
                temperature=0.0,
                max_tokens=400,
            )
            directives = result.get("fix_directives", [])
            severity = result.get("severity", "minor")
            if directives:
                return f"[{severity.upper()}] " + " | ".join(str(d) for d in directives[:3])
        except Exception as exc:  # noqa: BLE001
            self.log.debug("llm_critic_failed", error=str(exc))
        return None

    def reflect(
        self, questions: list[Question], quality: list[QuestionQuality]
    ) -> dict[str, str]:
        """Produce per-question regeneration instructions. Starts from the bar's
        own failed-check strings (always available, deterministic) and, when an
        LLM is present, enriches each with a concrete model-authored fix.

        Critical failures (2+ failed checks) get a targeted llm_critic diagnosis
        with structured severity + fix_directives in addition to the batch reflector.
        """
        by_id = {q.question_id: q for q in questions}
        feedback: dict[str, str] = {}
        failing = [qq for qq in quality if not qq.passed]
        for qq in failing:
            feedback[qq.question_id] = "; ".join(qq.failed_checks) or "below quality bar"

        if self.llm is None or not failing:
            return feedback

        # Targeted llm_critic for critical multi-issue failures (runs first, fast)
        for qq in failing:
            q = by_id.get(qq.question_id)
            if q is None:
                continue
            diagnosis = self._llm_critic_diagnose(q, qq)
            if diagnosis:
                feedback[qq.question_id] = f"{feedback.get(qq.question_id, '')} | CRITIC: {diagnosis}".lstrip(" | ")

        payload = [
            {
                "id": qq.question_id,
                "title": by_id[qq.question_id].title if qq.question_id in by_id else "",
                "objective": by_id[qq.question_id].objective if qq.question_id in by_id else "",
                "failed_checks": qq.failed_checks,
            }
            for qq in failing
        ]
        template = '{"questions": __Q__}'.replace("__Q__", "{questions}")
        try:
            fixes = run_batched_critic(
                llm=self.llm, system=_PLANNER_SYSTEM, template=template, payload=payload,
                settings=self.settings, validate=_valid_fix,
                agent_name="planner_reflect", log=self.log,
            )
            for qid, fx in fixes.items():
                fix = str(fx.get("fix", "")).strip()
                if fix:
                    feedback[qid] = f"{feedback.get(qid, '')}. FIX: {fix}".lstrip(". ")
        except Exception as exc:  # noqa: BLE001 — fall back to deterministic feedback
            self.log.warning("planner_reflect_failed", error=str(exc))
        return feedback

    # -- decision policy ----------------------------------------------------- #
    def decide(self, state: RunState) -> PlanStep:
        """Choose the next action. Deterministic rails are authoritative; they
        guarantee progress and termination regardless of model behaviour."""
        q = state.questions
        quality = state.quality
        bar_total = len(quality) if quality is not None else len(q)
        bar_passed = sum(1 for x in (quality or []) if x.passed)

        def step(action: PlanAction, reason: str, targets=None, source="policy") -> PlanStep:
            return PlanStep(
                step=state.step, action=action, reason=reason,
                targets=targets or [], source=source,
                bar_passed=bar_passed, bar_total=bar_total,
            )

        # 1 — nothing generated yet.
        if not q:
            return step(PlanAction.GENERATE, "no questions yet — generate the initial batch")

        # 2 — questions changed since last validation: must re-measure.
        if quality is None:
            return step(PlanAction.VALIDATE, "questions unvalidated — run the critic/grading/confidence chain")

        failing = [x.question_id for x in quality if not x.passed]

        # 3 — whole batch clears the bar: ship.
        if not failing:
            return step(PlanAction.FINALIZE, f"all {bar_total} questions meet the quality bar")

        # 4 — budget exhausted: ship best-effort rather than burn tokens forever.
        exhausted, budget_reason = state.budget_exhausted()
        if exhausted:
            return step(
                PlanAction.FINALIZE,
                f"{budget_reason}; shipping {bar_passed}/{bar_total} with {len(failing)} still below bar",
                targets=failing,
            )
        if state.attempts >= state.max_attempts or state.step >= state.max_steps:
            return step(
                PlanAction.FINALIZE,
                f"step budget spent (attempt {state.attempts}/{state.max_attempts}, "
                f"step {state.step}/{state.max_steps}); shipping {bar_passed}/{bar_total} "
                f"with {len(failing)} still below bar",
                targets=failing,
            )

        # 5 — budget remains and questions fail: regenerate only the failures.
        return step(
            PlanAction.REGENERATE,
            f"{len(failing)} question(s) below bar — regenerate with feedback",
            targets=failing,
        )
