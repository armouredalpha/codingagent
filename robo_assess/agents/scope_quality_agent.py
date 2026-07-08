"""
ScopeQualityAgent
=================

Quality scoring plus skill-drift scope check.

Scores each question on three dimensions using rule-based logic (no LLM):

  1. Realism score (0–100)
     Based on difficulty level + content signals. No AI needed.
       easy   → base 50  (fix a single value / string)
       medium → base 65  (write 5–10 lines of logic)
       hard   → base 80  (write a full ROS2 node)
     Bonuses for industrial domain, concrete ROS interfaces, measurable
     acceptance criteria, multiple skills, grading checks defined.
     Penalty for toy phrases (hello world, foo, bar, etc).

  2. Hiring signal (0–100)
     Does the question test skills that matter in industry?

  3. Market readiness
     Maps difficulty to employability level.

Plus one LLM call (batched across all questions) that verifies each question
actually exercises the syllabus skill it was assigned to, not just a
tangentially related one — catching generator drift (e.g. assigned "create
publisher" but generated a subscriber question). This was previously a
separate CoverageVerifierAgent stage; it's folded in here so scope-related
checks live in one place. Sets ``q.skill_drift`` and ``scope_violations``.
"""

from __future__ import annotations

from pathlib import Path

from ..guardrails import GuardrailConfig
from ..schemas import (
    AgentResult,
    Difficulty,
    HiringSignal,
    MarketReadiness,
    Question,
    ReadinessLevel,
    SyllabusAnalysis,
)
from .base import BaseAgent
from ._llm_batch import run_batched_critic

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

_DRIFT_SYSTEM = "You validate whether each ROS2 coding question primarily tests its assigned skill."


def _load_drift_prompt() -> str:
    p = _PROMPTS_DIR / "coverage_verifier.txt"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return 'Return JSON {"results": [{"id": "...", "passes": true, "reason": "..."}]}'


def _valid_drift_verdict(v: dict) -> bool:
    return "passes" in v

_DIFF_READINESS = {
    Difficulty.EASY: ReadinessLevel.EMPLOYABLE,
    Difficulty.MEDIUM: ReadinessLevel.JOB_READY,
    Difficulty.HARD: ReadinessLevel.INDUSTRY_READY,
}

# Base realism score per difficulty — reflects how much complexity is expected
_DIFF_BASE_REALISM = {
    Difficulty.EASY: 50,
    Difficulty.MEDIUM: 65,
    Difficulty.HARD: 80,
}


class ScopeQualityAgent(BaseAgent):
    """Offline-only quality scoring. No LLM calls."""

    name = "scope_quality"

    def __init__(self, *args, token_counter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_counter = token_counter
        self._drift_prompt_tpl = _load_drift_prompt()

    # ------------------------------------------------------------------ #
    # Skill-drift check (merged in from the former CoverageVerifierAgent)
    # ------------------------------------------------------------------ #
    def _check_skill_drift(
        self, questions: list[Question], assigned_skills: dict[str, str]
    ) -> dict[str, dict]:
        """Returns qid -> {"skill_drift": bool, "reason": str}. Empty dict if
        no LLM is configured or no question has an assigned skill."""
        if self.llm is None or not assigned_skills:
            return {}

        payload = [
            {
                "id": q.question_id,
                "required_skill": assigned_skills.get(q.question_id, ""),
                "title": q.title,
                "objective": q.objective or "",
                "scenario": q.scenario or "",
                "tested_skills": ", ".join(q.tested_skills),
            }
            for q in questions
            if assigned_skills.get(q.question_id)
        ]
        if not payload:
            return {}

        try:
            verdicts = run_batched_critic(
                llm=self.llm,
                system=_DRIFT_SYSTEM,
                template=self._drift_prompt_tpl,
                payload=payload,
                settings=self.settings,
                validate=_valid_drift_verdict,
                agent_name=self.name,
                log=self.log,
                token_counter=self.token_counter,
            )
        except Exception as exc:
            self.log.warning("skill_drift_batch_failed", error=str(exc))
            return {}

        out: dict[str, dict] = {}
        for q in questions:
            verdict = verdicts.get(q.question_id)
            if verdict is None:
                continue
            passes = bool(verdict.get("passes", True))
            reason = str(verdict.get("reason", ""))
            out[q.question_id] = {"skill_drift": not passes, "reason": reason}
            if not passes:
                self.log.warning(
                    "skill_drift_detected",
                    qid=q.question_id,
                    assigned=assigned_skills.get(q.question_id),
                    reason=reason,
                )
        return out

    # ------------------------------------------------------------------ #
    # Realism scoring — fully offline
    # ------------------------------------------------------------------ #
    def _rule_realism(self, q: Question) -> tuple[int, list[str]]:
        gr = GuardrailConfig.load()
        domains = gr.realism.required_domains
        toy_phrases = gr.realism.toy_phrases_penalty

        text = " ".join([
            q.scenario, q.objective,
            getattr(q, "context", ""),
            getattr(q, "question", ""),
            getattr(q, "expected_behaviour", ""),
        ]).lower()

        # Start from difficulty-based baseline
        score = _DIFF_BASE_REALISM.get(q.difficulty, 50)
        reasons: list[str] = [f"{q.difficulty.value} question (base {score})"]

        if any(d in text for d in domains):
            score += 10
            reasons.append("named industrial robot domain")
        if "/" in (q.scenario + q.objective):
            score += 8
            reasons.append("concrete ROS interface referenced")
        if getattr(q, "expected_behaviour", ""):
            score += 7
            reasons.append("measurable acceptance criteria")
        if len(q.tested_skills) >= 2:
            score += 5
            reasons.append("integrates multiple skills")
        checks = getattr(q, "hidden_checks", [])
        if checks or q.evaluation_criteria:
            score += 8
            reasons.append("auto-grading checks defined")
        if any(t in text for t in toy_phrases):
            score -= 30
            reasons.append("toy phrasing detected (penalty)")

        return max(0, min(100, score)), reasons

    # ------------------------------------------------------------------ #
    # Hiring signal — fully offline
    # ------------------------------------------------------------------ #
    def _rule_signal(self, q: Question, realism_score: int) -> tuple[int, list[str]]:
        score = 40
        reasons: list[str] = []

        if any("debug" in s.lower() for s in q.tested_skills) or "fix" in q.title.lower():
            score += 12
            reasons.append("Tests debugging ability")
        if len(set(q.tested_skills)) >= 2:
            score += 14
            reasons.append("Tests integration skills")
        if "communication" in " ".join(q.tested_skills).lower() or any(
            x in q.tested_skills for x in ("Publisher", "Subscriber", "Service")
        ):
            score += 12
            reasons.append("Tests ROS communication")
        if realism_score >= 70:
            score += 12
            reasons.append("Uses realistic engineering workflow")
        if q.difficulty == Difficulty.HARD:
            score += 10
            reasons.append("End-to-end engineering task")

        return min(100, score), reasons

    # ------------------------------------------------------------------ #
    # Market readiness — difficulty → employability level
    # ------------------------------------------------------------------ #
    def _rule_market(self, q: Question) -> tuple[ReadinessLevel, list[str]]:
        level = _DIFF_READINESS[q.difficulty]
        reasons = [f"Demonstrates {', '.join(q.tested_skills[:3])}"]
        if q.difficulty != Difficulty.EASY:
            reasons.append("Can debug and integrate ROS components")
        return level, reasons

    # ------------------------------------------------------------------ #
    # Main run — no LLM, no API calls
    # ------------------------------------------------------------------ #
    def run(
        self,
        questions: list[Question],
        analysis: SyllabusAnalysis,
        assigned_skills: dict[str, str] | None = None,
    ) -> AgentResult:
        patches: dict[str, dict] = {}
        quality_low: list[dict] = []
        scope_flagged: list[str] = []
        qt: list[dict] = []
        min_realism = self.settings.min_realism_score

        drift_results = self._check_skill_drift(questions, assigned_skills or {})

        for q in questions:
            r_score, r_reasons = self._rule_realism(q)
            s_score, s_reasons = self._rule_signal(q, r_score)
            m_level, m_reasons = self._rule_market(q)

            drift = drift_results.get(q.question_id)
            skill_drift = bool(drift and drift["skill_drift"])
            scope_violations = [drift["reason"]] if skill_drift and drift.get("reason") else []
            if skill_drift:
                scope_flagged.append(q.question_id)

            patches[q.question_id] = {
                "scope_violations": scope_violations,
                "skill_drift": skill_drift,
                "realism_score": r_score,
                "hiring_signal": HiringSignal(hiring_signal_score=s_score, reason=s_reasons),
                "market_readiness": MarketReadiness(level=m_level, reason=m_reasons),
            }

            if r_score < min_realism:
                quality_low.append({"qid": q.question_id, "score": r_score})
                qt.append({
                    "qid": q.question_id,
                    "decision": "low_realism",
                    "reason": f"realism={r_score} ({q.difficulty.value} base): {'; '.join(r_reasons[:2])}",
                })
            elif skill_drift:
                qt.append({
                    "qid": q.question_id,
                    "decision": "skill_drift",
                    "reason": scope_violations[0] if scope_violations else "assigned skill not exercised",
                })
            else:
                qt.append({
                    "qid": q.question_id,
                    "decision": "quality_ok",
                    "reason": f"realism={r_score} ({q.difficulty.value})",
                })

        res = self._result(
            scope_flagged=scope_flagged,
            quality_low=quality_low,
            patches=patches,
            question_traces=qt,
        )
        res.messages.append(
            f"quality: {len(quality_low)} below realism threshold (min={min_realism}), "
            f"{len(scope_flagged)} skill-drift violation(s)"
        )
        return res.finish("warn" if (quality_low or scope_flagged) else "ok")
