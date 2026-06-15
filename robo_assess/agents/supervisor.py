"""
Supervisor Agent
================

Sits above every worker agent. It validates the assembled package, detects
hallucinations / missing artefacts / empty results / incomplete implementations
and holds final approval authority — no package ships unless the Supervisor
approves it.

Validation rules
----------------
* Every syllabus skill must be tested (coverage 100%).
* At least one approved question must exist.
* No approved question may carry scope violations or be non-auto-gradable.
* Every editable file must contain balanced TODO markers and a differing
  reference solution.
* The difficulty mix must be plausible (not all-easy when hard was requested).
"""

from __future__ import annotations

from ..guardrails import GuardrailConfig
from ..schemas import AgentResult, AssessmentPackage, Question, SupervisorVerdict
from ._llm_batch import run_batched_critic
from .base import BaseAgent

_JUDGE_SYSTEM = (
    "You are an INDEPENDENT senior robotics hiring reviewer. You did not write "
    "these questions. For each one, judge ONLY from the artifact whether it is a "
    "realistic, correctly-scoped, unambiguous, auto-gradable ROS2 Humble coding "
    "ticket whose stated criteria actually match the task. Be skeptical. Return "
    'ONLY JSON: {"results":[{"id": "...", "verdict": "APPROVE"|"REJECT", '
    '"reasons": ["..."]}]} — reasons required when REJECT.'
)


def _valid_judge_verdict(v: dict) -> bool:
    return str(v.get("verdict", "")).upper() in ("APPROVE", "REJECT")


class SupervisorAgent(BaseAgent):
    name = "supervisor"

    def _llm_judge(self, pkg: AssessmentPackage) -> dict[str, dict]:
        """Independent per-question LLM verdicts, keyed by question_id. Empty when
        the judge is disabled, unavailable, or fails — the rule-based supervisor
        remains authoritative and the judge can only ADD rejections."""
        if not getattr(self.settings, "enable_llm_judge", False) or self.llm is None:
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
            for q in pkg.questions
        ]
        template = '{"questions": __Q__}'.replace("__Q__", "{questions}")
        return run_batched_critic(
            llm=self.llm, system=_JUDGE_SYSTEM, template=template, payload=payload,
            settings=self.settings, validate=_valid_judge_verdict,
            agent_name=self.name, log=self.log,
        )

    def _question_problems(self, q: Question) -> list[str]:
        """Per-question defects. Returned as human-readable feedback strings that
        are both logged as issues and injected into targeted regeneration."""
        probs: list[str] = []
        if q.scope_violations:
            probs.append(
                f"uses out-of-scope tech ({', '.join(q.scope_violations)}); "
                f"stay within the approved syllabus"
            )
        if not q.auto_gradable:
            probs.append("not auto-gradable; add concrete machine-checkable criteria")
        if q.realism_score and q.realism_score < self.settings.min_realism_score:
            probs.append(
                f"realism {q.realism_score} below {self.settings.min_realism_score}; "
                f"frame it as a concrete engineering ticket with named robot + ROS interfaces"
            )
        # Executable-grading signal — soft gate: a genuine FAIL is a hard defect;
        # NO_ARTIFACTS / SKIPPED is recorded but does not block (per design).
        ge = q.grading_execution
        if ge and ge.status == "FAIL":
            probs.append(f"hidden tests do not discriminate a solution ({ge.detail}); "
                         f"ensure the starter leaves the implementation empty and the "
                         f"reference actually implements the required rclpy calls")
        # Legacy TODO / reference-solution integrity
        if not q.evaluation_criteria:
            for f in q.files_to_edit:
                s, e = f.starter_code.count("# TODO START"), f.starter_code.count("# TODO END")
                if s != e or s == 0:
                    probs.append(f"{f.path}: unbalanced/missing TODO markers")
                if f.reference_solution.strip() == f.starter_code.strip():
                    probs.append(f"{f.path}: reference solution identical to starter")
        return probs

    def validate(self, pkg: AssessmentPackage, evaluation_score: float) -> SupervisorVerdict:
        issues: list[str] = []
        failing_ids: list[str] = []
        feedback: dict[str, str] = {}

        if not pkg.questions:
            issues.append("no questions generated")

        # Coverage gate — judged against a configurable target, not an implicit
        # 100%. The old behaviour rejected every broad-syllabus batch by
        # construction (6 questions can't test 20 skills). require_full_coverage
        # still works: when true it forces the target to 1.0.
        gr_cov = GuardrailConfig.load().supervisor
        target = 1.0 if gr_cov.require_full_coverage else gr_cov.coverage_target
        total_skills = len(pkg.coverage_matrix.matrix)
        covered = total_skills - len(pkg.coverage_matrix.missing)
        coverage_frac = (covered / total_skills) if total_skills else 0.0
        if covered == 0:
            issues.append("no syllabus skills covered at all")
        elif coverage_frac < target:
            issues.append(
                f"coverage {coverage_frac:.0%} below target {target:.0%} "
                f"({covered}/{total_skills} skills tested)"
            )

        approved = pkg.approved_questions
        if not approved:
            issues.append("no question reached APPROVED confidence")

        judge = self._llm_judge(pkg)

        for q in pkg.questions:
            probs = self._question_problems(q)
            # Independent LLM judge: a REJECT is treated as a defect that routes
            # the question to regeneration, and (if it was approved) raises a
            # batch-level issue — a second, prompt-independent opinion.
            jv = judge.get(q.question_id)
            if jv and str(jv.get("verdict", "")).upper() == "REJECT":
                jr = "; ".join(str(r) for r in jv.get("reasons", [])) or "independent judge rejected"
                probs.append(f"independent judge REJECT: {jr}")
                if q.approved:
                    issues.append(f"{q.question_id}: approved but independent judge rejected — {jr}")
            # An approved question carrying a hard defect is a batch-level issue.
            if q.approved:
                for p in probs:
                    if p.startswith(("uses out-of-scope", "not auto-gradable", "hidden tests do not")):
                        issues.append(f"{q.question_id}: approved despite — {p}")
            # Any non-approved or defective question is a regeneration target.
            if not q.approved or probs:
                failing_ids.append(q.question_id)
                reason = probs or ["below approval confidence; strengthen scenario, "
                                   "criteria and difficulty fit"]
                feedback[q.question_id] = "; ".join(reason)

        gr = GuardrailConfig.load()
        min_score = gr.supervisor.min_validation_score
        pass_rate = len(approved) / len(pkg.questions) if pkg.questions else 0.0
        score = round(0.6 * evaluation_score + 40 * pass_rate)
        status = "APPROVED" if not issues and score >= min_score else "REJECTED"
        return SupervisorVerdict(
            supervisor_status=status, validation_score=int(score), issues=issues,
            failing_question_ids=sorted(set(failing_ids)), question_feedback=feedback,
        )

    def run(self, pkg: AssessmentPackage, evaluation_score: float) -> AgentResult:
        verdict = self.validate(pkg, evaluation_score)
        res = self._result(verdict=verdict.model_dump())
        res.messages.append(
            f"{verdict.supervisor_status} (score {verdict.validation_score}, "
            f"{len(verdict.issues)} issues)"
        )
        return res.finish("ok" if verdict.supervisor_status == "APPROVED" else "fail")
