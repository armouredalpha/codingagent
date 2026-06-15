"""
Agent 3 — Coverage Matrix
=========================

Builds and maintains the skill -> tested boolean matrix. Every syllabus skill
must eventually be flagged True; the Question Generator queries ``missing`` to
prioritise uncovered skills, and the Supervisor refuses to approve a package
that leaves any skill untested.
"""

from __future__ import annotations

from ..schemas import AgentResult, CoverageMatrix
from .base import BaseAgent


class CoverageMatrixAgent(BaseAgent):
    name = "coverage_matrix"

    def build(self, skills: list[str]) -> CoverageMatrix:
        return CoverageMatrix(matrix={s: False for s in skills})

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
