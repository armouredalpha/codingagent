"""
Agent 8 — Scope Compliance
=========================

Ensures questions stay inside the syllabus. Out-of-scope technologies
(Nav2, SLAM, MoveIt, OpenCV, micro-ROS, …) are rejected *unless* explicitly
listed in the syllabus.

Rule-based gating runs first and is the offline path / fallback. When a provider
is online, the questions are additionally scored by the LLM critic in batches
(``scope_critic.txt``); the LLM verdict supersedes the heuristic per question,
and any question the LLM fails to score keeps its rule-based verdict.
"""

from __future__ import annotations

from pathlib import Path

from ..guardrails import GuardrailConfig
from ..schemas import AgentResult, Question, SyllabusAnalysis
from .base import BaseAgent
from ._llm_batch import run_batched_critic

_SYSTEM_PROMPT = (
    "You are the Syllabus Compliance Agent for a ROS2 Humble assessment "
    "pipeline. Return ONLY valid JSON, no markdown, no prose."
)


def _load_prompt(prompts_dir: str) -> str | None:
    p = Path(prompts_dir) / "scope_critic.txt"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _valid_scope_verdict(v: dict) -> bool:
    return "classification" in v and "question_is_out_of_scope" in v


class ScopeComplianceAgent(BaseAgent):
    name = "scope_agent"

    def __init__(self, *args, token_counter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_counter = token_counter

    # ------------------------------------------------------------------ #
    def _rule_based(self, questions: list[Question], analysis: SyllabusAnalysis
                    ) -> dict[str, list[str]]:
        gr = GuardrailConfig.load()
        gated = gr.scope.gated_technologies
        allowed = " ".join(analysis.skills + analysis.concepts).lower()
        out: dict[str, list[str]] = {}
        for q in questions:
            haystack = " ".join(
                [q.scenario, q.objective, " ".join(q.tested_skills),
                 " ".join(q.constraints)]
            ).lower()
            violations = []
            for concept, needles in gated.items():
                present = any(nd in haystack for nd in needles)
                granted = concept in allowed or any(nd in allowed for nd in needles)
                if present and not granted:
                    violations.append(concept)
            out[q.question_id] = violations
        return out

    def _llm_verdicts(self, questions: list[Question], analysis: SyllabusAnalysis
                      ) -> dict[str, dict]:
        if self.llm is None:
            return {}
        template = _load_prompt(self.settings.prompts_dir)
        if not template:
            return {}
        template = template.replace(
            "{syllabus}", "\n".join(f"* {s}" for s in analysis.skills)
        )
        payload = [
            {
                "id": q.question_id,
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
            validate=_valid_scope_verdict,
            agent_name=self.name,
            log=self.log,
            token_counter=self.token_counter,
        )

    # ------------------------------------------------------------------ #
    def run(self, questions: list[Question], analysis: SyllabusAnalysis) -> AgentResult:
        rule_violations = self._rule_based(questions, analysis)
        verdicts = self._llm_verdicts(questions, analysis)

        flagged = []
        n_llm = 0
        for q in questions:
            v = verdicts.get(q.question_id)
            if v is not None:
                n_llm += 1
                violations = [str(c) for c in v.get("out_of_scope_concepts", [])] \
                    or [str(c) for c in v.get("violations", [])]
                out_of_scope = bool(v.get("question_is_out_of_scope", False))
            else:
                violations = rule_violations.get(q.question_id, [])
                out_of_scope = bool(violations)
            q.scope_violations = violations
            if violations or out_of_scope:
                flagged.append({"qid": q.question_id, "violations": violations})

        res = self._result(flagged=flagged)
        src = f"llm:{n_llm}/{len(questions)}" if n_llm else "rule-based"
        res.messages.append(f"{len(flagged)} scope violations ({src})")
        return res.finish("warn" if flagged else "ok")
