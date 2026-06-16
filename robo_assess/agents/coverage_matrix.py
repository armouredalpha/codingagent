"""
Agent 3 — Coverage Matrix
=========================

Builds and maintains the skill -> tested boolean matrix. Every syllabus skill
must eventually be flagged True; the Question Generator queries ``missing`` to
prioritise uncovered skills, and the Supervisor refuses to approve a package
that leaves any skill untested.
"""

from __future__ import annotations

from pathlib import Path

from ..schemas import AgentResult, CoverageMatrix, Question
from .base import BaseAgent

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    try:
        return (_PROMPTS_DIR / name).read_text(encoding="utf-8")
    except OSError:
        return ""


class CoverageMatrixAgent(BaseAgent):
    name = "coverage_matrix"

    def build(self, skills: list[str]) -> CoverageMatrix:
        return CoverageMatrix(matrix={s: False for s in skills})

    def verifies_skill(self, question: Question, selected_skill: str) -> tuple[bool, str]:
        """LLM judge: does this question PRIMARILY test ``selected_skill``?

        Used by the v2 per-question loop to confirm a generated question stays on
        the skill the picker chose. Returns ``(passed, reason)``. Falls back to a
        deterministic string-overlap check when the LLM is unavailable or returns
        an unparseable verdict (keeps offline/test runs green).
        """
        tested = ", ".join(question.tested_skills) or "(none)"
        template = _load_prompt("coverage_verifier.txt")
        prompt = (
            template
            .replace("{selected_skill}", selected_skill)
            .replace("{title}", question.title)
            .replace("{objective}", question.objective)
            .replace("{scenario}", question.scenario)
            .replace("{tested_skills}", tested)
        ) if template else (
            "You are validating a robotics coding question.\n"
            f"The question MUST primarily assess this skill: {selected_skill}\n\n"
            f"Question title: {question.title}\n"
            f"Objective: {question.objective}\n"
            f"Scenario: {question.scenario}\n"
            f"Declared tested_skills: {tested}\n\n"
            "Does this question primarily test the required skill? "
            'Reply with JSON: {"passes": true|false, "reason": "<short reason>"}'
        )
        try:
            result, _ = self.llm.complete_json(  # type: ignore[union-attr]
                system="You are a strict skill-coverage validator for ROS2 coding assessments.",
                user=prompt,
                temperature=0.0,
                max_tokens=150,
            )
            if isinstance(result, dict) and "passes" in result:
                return bool(result["passes"]), str(result.get("reason", ""))
        except Exception as exc:  # noqa: BLE001
            self.log.debug("verifies_skill_llm_unavailable", error=str(exc))

        # Deterministic fallback: token overlap between selected skill and the
        # question's tested skills / objective / title.
        sel = selected_skill.lower()
        haystack = " ".join(
            [question.title, question.objective, " ".join(question.tested_skills)]
        ).lower()
        sel_tokens = {t for t in sel.replace("/", " ").split() if len(t) > 2}
        if not sel_tokens:
            return True, "no selected-skill tokens to check"
        hits = sum(1 for t in sel_tokens if t in haystack)
        ratio = hits / len(sel_tokens)
        passed = ratio >= 0.4
        return passed, f"token overlap {hits}/{len(sel_tokens)} ({ratio:.0%})"

    def mark(self, matrix: CoverageMatrix, skills: list[str]) -> None:
        for s in skills:
            # match the syllabus skill that this tested-skill belongs to
            for key in matrix.matrix:
                if s.lower() in key.lower() or key.lower() in s.lower():
                    matrix.matrix[key] = True

    def run(self, skills: list[str]) -> AgentResult:
        matrix = self.build(skills)
        res = self._result(coverage=matrix.model_dump())
        res.messages.append(f"matrix initialised for {len(skills)} skills")
        return res.finish()
