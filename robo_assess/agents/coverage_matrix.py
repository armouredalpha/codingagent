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

# Minimum number of shared tokens for an immediate match (fast path).
_MIN_SHARED_TOKENS = 2
# Jaccard fallback threshold for skill names with only 1 shared token.
# 0.25 allows "publisher node" ↔ "ROS2 publisher" (Jaccard ≈ 0.33)
# while rejecting completely unrelated skills (Jaccard = 0).
_MIN_JACCARD = 0.25


# Tokens that appear in nearly every ROS2 skill name and carry no
# discriminative signal for matching (e.g. "ros2 publisher node" vs
# "ros2 subscriber node" would share "ros2" and "node" falsely).
_STOP_TOKENS = frozenset({"ros", "ros2", "node", "nodes", "using", "with", "and", "the"})


def _tokenize(text: str) -> set[str]:
    """Normalised, stop-word-filtered token set.

    Splits on whitespace and punctuation, drops tokens shorter than 3 chars,
    and removes domain stop words that appear in every ROS2 skill name.
    """
    import re
    tokens = re.split(r"[\s/\-_.,;:()]+", text.lower())
    return {t for t in tokens if len(t) >= 3 and t not in _STOP_TOKENS}


def _skills_match(tested: str, syllabus_key: str) -> bool:
    """True when ``tested`` is a good match for ``syllabus_key``.

    Uses token-set intersection first (requires ≥ _MIN_SHARED_TOKENS hits),
    then falls back to Jaccard coefficient (≥ _MIN_JACCARD) for short skill
    names that may only have one meaningful token.
    """
    a = _tokenize(tested)
    b = _tokenize(syllabus_key)
    if not a or not b:
        return False
    shared = a & b
    if len(shared) >= _MIN_SHARED_TOKENS:
        return True
    jaccard = len(shared) / len(a | b)
    return jaccard >= _MIN_JACCARD


class CoverageMatrixAgent(BaseAgent):
    name = "coverage_matrix"

    def _load_prompt(self, name: str) -> str:
        path = Path(self.settings.prompts_dir) / name
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def build(self, skills: list[str]) -> CoverageMatrix:
        return CoverageMatrix(matrix={s: False for s in skills})

    def verifies_skill(self, question: Question, selected_skill: str) -> tuple[bool, str]:
        """LLM judge: does this question PRIMARILY test ``selected_skill``?

        Used by the v2 per-question loop to confirm a generated question stays on
        the skill the picker chose. Returns ``(passed, reason)``. Falls back to a
        deterministic token-set check when the LLM is unavailable or returns
        an unparseable verdict (keeps offline/test runs green).
        """
        tested = ", ".join(question.tested_skills) or "(none)"
        template = self._load_prompt("coverage_verifier.txt")
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
            if self.llm is None:
                raise RuntimeError("No LLM configured")
            result, _ = self.llm.complete_json(
                system="You are a strict skill-coverage validator for ROS2 coding assessments.",
                user=prompt,
                temperature=0.0,
                max_tokens=100,
            )
            if isinstance(result, dict) and "passes" in result:
                return bool(result["passes"]), str(result.get("reason", ""))
        except Exception as exc:  # noqa: BLE001
            self.log.debug("verifies_skill_llm_unavailable", error=str(exc))

        # Deterministic fallback: token-set intersection between selected skill
        # and the question's tested skills / objective / title.
        haystack_text = " ".join(
            [question.title, question.objective, " ".join(question.tested_skills)]
        )
        passed = _skills_match(selected_skill, haystack_text)
        sel_tokens = _tokenize(selected_skill)
        hay_tokens = _tokenize(haystack_text)
        shared = sel_tokens & hay_tokens
        jaccard = len(shared) / len(sel_tokens | hay_tokens) if (sel_tokens | hay_tokens) else 0.0
        return passed, (
            f"token-set: {len(shared)} shared tokens, jaccard={jaccard:.2f}"
        )

    def mark(self, matrix: CoverageMatrix, skills: list[str]) -> None:
        """Mark syllabus skills as covered.

        Uses token-set matching instead of substring containment to avoid
        false positives (e.g. "tf" matching "staff" or "transform").
        """
        for tested_skill in skills:
            for key in matrix.matrix:
                if _skills_match(tested_skill, key):
                    matrix.matrix[key] = True

    def run(self, skills: list[str]) -> AgentResult:
        matrix = self.build(skills)
        res = self._result(coverage=matrix.model_dump())
        res.messages.append(f"matrix initialised for {len(skills)} skills")
        return res.finish()
