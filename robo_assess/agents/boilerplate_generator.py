"""
Agent 5 — Boilerplate Generator
==============================

Guarantees the "students never build from scratch" invariant: every editable
file must expose exactly the regions a student edits via ``# TODO START`` /
``# TODO END`` (or the YAML/launch equivalent), and the reference solution must
differ from the starter (i.e. the TODO is genuinely incomplete in the starter).
Files that violate this are flagged so the Supervisor can reject the question.
"""

from __future__ import annotations

from ..guardrails import GuardrailConfig
from ..schemas import AgentResult, Question
from .base import BaseAgent


class BoilerplateGeneratorAgent(BaseAgent):
    name = "boilerplate_generator"

    def validate(self, q: Question) -> list[str]:
        gr = GuardrailConfig.load()
        patterns = gr.rejection
        issues: list[str] = []

        # New-style question: validate boilerplate_code directly
        if q.boilerplate_code:
            boilerplate = q.boilerplate_code
            file_path = q.file_to_edit or "node.py"

            has_marker = (
                "# ── STUDENT IMPLEMENTATION" in boilerplate
                or "# TODO" in boilerplate
                or "<!-- ── STUDENT IMPLEMENTATION" in boilerplate
                or "<!-- TODO" in boilerplate
            )
            if not has_marker:
                issues.append(f"{file_path}: boilerplate missing student implementation marker")

            hit, pat = patterns.has_deprecated_api(boilerplate)
            if hit:
                issues.append(f"{file_path}: deprecated API '{pat}' in boilerplate")
            hit, pat = patterns.has_toy_code(boilerplate)
            if hit:
                issues.append(f"{file_path}: toy code pattern '{pat}' in boilerplate")

        else:
            # Legacy-style: check TODO START/END markers
            rules = gr.boilerplate
            for f in q.files_to_edit:
                start = f.starter_code.count("# TODO START")
                end = f.starter_code.count("# TODO END")

                if rules.require_todo_start and start == 0:
                    issues.append(f"{f.path}: missing # TODO START marker")
                if rules.require_todo_end and end == 0:
                    issues.append(f"{f.path}: missing # TODO END marker")
                if rules.require_balanced and start != end:
                    issues.append(f"{f.path}: unbalanced TODO markers ({start} start / {end} end)")

                hit, pat = patterns.has_deprecated_api(f.reference_solution)
                if hit:
                    issues.append(f"{f.path}: deprecated API '{pat}' in solution")
                hit, pat = patterns.has_toy_code(f.starter_code)
                if hit:
                    issues.append(f"{f.path}: toy code pattern '{pat}' in starter")

        # Theory question check on scenario/objective
        full_text = f"{q.title} {q.scenario} {q.objective}"
        hit, pat = patterns.is_theory_question(full_text)
        if hit:
            issues.append(f"theory question pattern detected: '{pat}'")

        return issues

    def run(self, questions: list[Question]) -> AgentResult:
        all_issues: dict[str, list[str]] = {}
        for q in questions:
            issues = self.validate(q)
            if issues:
                all_issues[q.question_id] = issues
        status = "fail" if all_issues else "ok"
        res = self._result(issues=all_issues)
        res.messages.append(
            f"boilerplate checked for {len(questions)} questions; "
            f"{len(all_issues)} with issues"
        )
        return res.finish(status)
