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

import re

from ..guardrails import GuardrailConfig
from ..schemas import AgentResult, Difficulty, Question
from .base import BaseAgent

_WHITESPACE_RE = re.compile(r"\s+")


def _normalise(code: str) -> str:
    """Strip comments and collapse whitespace for diff comparison."""
    lines = [
        ln for ln in code.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    return _WHITESPACE_RE.sub(" ", " ".join(lines)).strip()


def _solutions_differ(starter: str, reference: str) -> bool:
    """Return True when starter and reference are meaningfully different."""
    if not reference.strip():
        return False
    return _normalise(starter) != _normalise(reference)


class BoilerplateGeneratorAgent(BaseAgent):
    name = "boilerplate_generator"

    def validate(self, q: Question) -> list[str]:
        gr = GuardrailConfig.load()
        patterns = gr.rejection
        issues: list[str] = []

        # New-style question: validate boilerplate_code directly
        if q.boilerplate_code:
            boilerplate = q.boilerplate_code
            reference = getattr(q, "reference_code", "") or ""
            file_path = q.file_to_edit or "node.py"

            # Easy questions fix a single value/string in-place and may not use
            # explicit TODO markers — only enforce markers on medium/hard.
            if q.difficulty != Difficulty.EASY:
                has_marker = (
                    "# ── STUDENT IMPLEMENTATION" in boilerplate
                    or "# TODO" in boilerplate
                    or "<!-- ── STUDENT IMPLEMENTATION" in boilerplate
                    or "<!-- TODO" in boilerplate
                )
                if not has_marker:
                    issues.append(
                        f"{file_path}: boilerplate missing student implementation marker"
                    )

            # Ensure the starter is genuinely incomplete vs the reference
            if reference and not _solutions_differ(boilerplate, reference):
                issues.append(
                    f"{file_path}: boilerplate and reference solution are identical "
                    "— student has nothing to implement"
                )

            # Ensure reference solution actually exists
            if not reference.strip():
                issues.append(
                    f"{file_path}: reference solution is empty — "
                    "cannot verify student work"
                )

            hit, pat = patterns.has_deprecated_api(boilerplate)
            if hit:
                issues.append(f"{file_path}: deprecated API '{pat}' in boilerplate")
            hit, pat = patterns.has_toy_code(boilerplate)
            if hit:
                issues.append(f"{file_path}: toy code pattern '{pat}' in boilerplate")

        else:
            # Legacy-style: check TODO START/END markers (skip for easy questions
            # which fix a single value and don't need explicit TODO blocks).
            rules = gr.boilerplate
            for f in q.files_to_edit:
                start = f.starter_code.count("# TODO START")
                end = f.starter_code.count("# TODO END")

                if q.difficulty != Difficulty.EASY:
                    if rules.require_todo_start and start == 0:
                        issues.append(f"{f.path}: missing # TODO START marker")
                    if rules.require_todo_end and end == 0:
                        issues.append(f"{f.path}: missing # TODO END marker")
                if rules.require_balanced and start != end:
                    issues.append(
                        f"{f.path}: unbalanced TODO markers ({start} start / {end} end)"
                    )

                # Verify reference solution differs from starter
                if not _solutions_differ(f.starter_code, f.reference_solution):
                    issues.append(
                        f"{f.path}: starter and reference solution are identical "
                        "— student has nothing to implement"
                    )

                if not f.reference_solution.strip():
                    issues.append(
                        f"{f.path}: reference solution is empty"
                    )

                hit, pat = patterns.has_deprecated_api(f.reference_solution)
                if hit:
                    issues.append(f"{f.path}: deprecated API '{pat}' in solution")
                hit, pat = patterns.has_toy_code(f.starter_code)
                if hit:
                    issues.append(f"{f.path}: toy code pattern '{pat}' in starter")

        # Theory question check on scenario/objective — only flag when there is
        # no boilerplate code at all, to avoid false positives on questions that
        # happen to use explanation-flavoured language in their scenario text.
        if not q.boilerplate_code and not q.files_to_edit:
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
