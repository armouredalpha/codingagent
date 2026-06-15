"""
Agent 9 — Quality Judge (merged LLM critic)
==========================================

Single LLM-judge agent for the three *subjective* quality signals that were
previously three separate keyword-heuristic agents:

    * Industry Realism        -> ``realism_score``
    * Hiring Signal           -> ``hiring_signal``
    * Market Readiness        -> ``market_readiness``

These are judgement calls, so they belong with a model, not a regex. The
deterministic signals — role mapping and portfolio coverage — stay rule-based
in :class:`HiringReadinessAgent`; they are structural facts, not opinions.

Pattern (mirrors :mod:`scope_agent`): rule-based scoring runs first and is the
offline path / fallback. When a provider is online the batch is additionally
scored by the LLM critic (``quality_judge.txt``); the LLM verdict supersedes the
heuristic per question, and any question the LLM fails to score keeps its
rule-based verdict.
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
)
from .base import BaseAgent
from ._llm_batch import run_batched_critic

_SYSTEM_PROMPT = (
    "You are the Quality Judge for a ROS2 Humble hiring-assessment pipeline. "
    "You rate engineering-ticket coding questions for industrial realism, the "
    "strength of the hiring signal they give, and the market-readiness a "
    "candidate who solves them demonstrates. Return ONLY valid JSON, no markdown."
)

_DIFF_READINESS = {
    Difficulty.EASY: ReadinessLevel.EMPLOYABLE,
    Difficulty.MEDIUM: ReadinessLevel.JOB_READY,
    Difficulty.HARD: ReadinessLevel.INDUSTRY_READY,
}

# Accept either the enum value ("Job Ready") or its name ("JOB_READY").
_READINESS_BY_VALUE = {r.value.lower(): r for r in ReadinessLevel}
_READINESS_BY_NAME = {r.name.lower(): r for r in ReadinessLevel}


def _load_prompt(prompts_dir: str) -> str | None:
    p = Path(prompts_dir) / "quality_judge.txt"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _valid_verdict(v: dict) -> bool:
    return (
        "realism_score" in v
        and "hiring_signal_score" in v
        and "market_readiness" in v
    )


def _coerce_readiness(value: str, default: ReadinessLevel) -> ReadinessLevel:
    key = str(value).strip().lower()
    return _READINESS_BY_VALUE.get(key) or _READINESS_BY_NAME.get(key) or default


class QualityJudgeAgent(BaseAgent):
    name = "quality_judge"

    def __init__(self, *args, token_counter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_counter = token_counter

    # ------------------------------------------------------------------ #
    # Rule-based fallback (also the offline path)
    # ------------------------------------------------------------------ #
    def _rule_realism(self, q: Question) -> tuple[int, list[str]]:
        gr = GuardrailConfig.load()
        domains = gr.realism.required_domains
        toy_phrases = gr.realism.toy_phrases_penalty

        text = " ".join([q.scenario, q.objective, q.expected_behaviour]).lower()
        score = 50
        reasons: list[str] = []
        if any(d in text for d in domains):
            score += 15
            reasons.append("named industrial robot domain")
        if "/" in q.scenario + q.objective or any("/" in c.target for c in q.hidden_checks):
            score += 10
            reasons.append("concrete ROS interface referenced")
        if q.expected_behaviour:
            score += 10
            reasons.append("measurable acceptance criteria")
        if len(q.tested_skills) >= 2:
            score += 5
            reasons.append("integrates multiple skills")
        if q.hidden_checks or q.evaluation_criteria:
            score += 10
            reasons.append("auto-grading checks defined")
        if any(t in text for t in toy_phrases):
            score -= 30
            reasons.append("toy phrasing detected (penalty)")
        return max(0, min(100, score)), reasons

    def _rule_signal(self, q: Question) -> tuple[int, list[str]]:
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
        if q.realism_score >= 70:
            score += 12
            reasons.append("Uses realistic engineering workflow")
        if q.difficulty == Difficulty.HARD:
            score += 10
            reasons.append("End-to-end engineering task")
        return min(100, score), reasons

    def _rule_market(self, q: Question) -> tuple[ReadinessLevel, list[str]]:
        level = _DIFF_READINESS[q.difficulty]
        reasons = [f"Demonstrates {', '.join(q.tested_skills[:3])}"]
        if q.difficulty != Difficulty.EASY:
            reasons.append("Can debug and integrate ROS components")
        return level, reasons

    # ------------------------------------------------------------------ #
    # LLM critic
    # ------------------------------------------------------------------ #
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
                "difficulty": q.difficulty.value,
                "scenario": q.scenario,
                "objective": q.objective,
                "tested_skills": q.tested_skills,
                "constraints": q.constraints,
            }
            for q in questions
        ]
        return run_batched_critic(
            llm=self.llm,
            system=_SYSTEM_PROMPT,
            template=template,
            payload=payload,
            settings=self.settings,
            validate=_valid_verdict,
            agent_name=self.name,
            log=self.log,
            token_counter=self.token_counter,
        )

    # ------------------------------------------------------------------ #
    def run(self, questions: list[Question]) -> AgentResult:
        verdicts = self._llm_verdicts(questions)
        min_realism = self.settings.min_realism_score
        low_realism = []
        n_llm = 0

        for q in questions:
            # Realism first — the rule-based hiring signal reads realism_score.
            r_score, r_reasons = self._rule_realism(q)
            s_score, s_reasons = self._rule_signal(q)  # recomputed below if realism overridden
            m_level, m_reasons = self._rule_market(q)

            v = verdicts.get(q.question_id)
            if v is not None:
                n_llm += 1
                try:
                    r_score = max(0, min(100, int(v.get("realism_score", r_score))))
                    r_reasons = [str(x) for x in v.get("realism_reasons", [])] or r_reasons
                    s_score = max(0, min(100, int(v.get("hiring_signal_score", s_score))))
                    s_reasons = [str(x) for x in v.get("hiring_reasons", [])] or s_reasons
                    m_level = _coerce_readiness(v.get("market_readiness", ""), m_level)
                    m_reasons = [str(x) for x in v.get("market_reasons", [])] or m_reasons
                except (TypeError, ValueError):
                    self.log.warning("quality_verdict_coerce_failed", qid=q.question_id)
                    v = None  # fall through to the rule-based values already computed

            q.realism_score = r_score
            q.hiring_signal = HiringSignal(hiring_signal_score=s_score, reason=s_reasons)
            q.market_readiness = MarketReadiness(level=m_level, reason=m_reasons)

            if r_score < min_realism:
                low_realism.append({"qid": q.question_id, "score": r_score, "reasons": r_reasons})

        res = self._result(low_realism=low_realism)
        src = f"llm:{n_llm}/{len(questions)}" if n_llm else "rule-based"
        res.messages.append(
            f"judged {len(questions)} questions ({src}); {len(low_realism)} below realism threshold"
        )
        return res.finish("warn" if low_realism else "ok")
