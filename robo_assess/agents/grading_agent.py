"""
Agent 10 — Auto-Grading
=======================

Verifies a question can be graded without human judgement. A question is
auto-gradable when it declares at least one machine-checkable grading check
(topic/service/node/tf/parameter/behaviour/simulation) **and** at least one
hidden test with a concrete assertion. Questions that would need subjective
review are flagged. Also emits the platform-facing evaluation metadata.
"""

from __future__ import annotations

from ..schemas import AgentResult, Question
from .base import BaseAgent


class AutoGradingAgent(BaseAgent):
    name = "grading_agent"

    def metadata(self, q: Question) -> dict:
        return {
            "question_id": q.question_id,
            "checks": [c.check_type.value for c in q.hidden_checks],
            "targets": {c.check_type.value: c.target for c in q.hidden_checks},
            "tests": [
                {"name": t.name, "kind": t.kind, "assertion": t.assertion}
                for t in q.hidden_tests
            ],
        }

    def run(self, questions: list[Question]) -> AgentResult:
        not_gradable = []
        meta = []
        for q in questions:
            # New-style: evaluation_criteria with points is auto-gradable
            if q.evaluation_criteria:
                total_points = sum(ec.points for ec in q.evaluation_criteria)
                gradable = len(q.evaluation_criteria) >= 3 and total_points == 100
            else:
                # Legacy: needs hidden_checks and hidden_tests
                gradable = bool(q.hidden_checks) and bool(q.hidden_tests)
            q.auto_gradable = gradable
            meta.append(self.metadata(q))
            if not gradable:
                not_gradable.append(q.question_id)
        res = self._result(metadata=meta, not_gradable=not_gradable)
        res.messages.append(
            f"{len(questions) - len(not_gradable)}/{len(questions)} auto-gradable"
        )
        return res.finish("warn" if not_gradable else "ok")
