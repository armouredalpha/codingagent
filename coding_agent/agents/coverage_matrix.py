"""
Coverage Matrix — reusable service
===================================

Builds and maintains the skill -> tested boolean matrix. Every syllabus skill
must eventually be flagged True; the Question Generator queries ``missing`` to
prioritise uncovered skills, and the Supervisor refuses to approve a package
that leaves any skill untested.

Plain functions, not a pipeline agent: nothing here calls an LLM or needs
settings/memory/vectorstore, so it doesn't carry BaseAgent's per-agent
logger/model-routing ceremony. Call ``build_matrix()``/``mark()`` directly.
"""

from __future__ import annotations

from ..schemas import CoverageMatrix

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


def build_matrix(skills: list[str]) -> CoverageMatrix:
    return CoverageMatrix(matrix={s: False for s in skills})


def mark(matrix: CoverageMatrix, skills: list[str]) -> None:
    """Mark syllabus skills as covered.

    Uses token-set matching instead of substring containment to avoid
    false positives (e.g. "tf" matching "staff" or "transform").
    """
    for tested_skill in skills:
        for key in matrix.matrix:
            if _skills_match(tested_skill, key):
                matrix.matrix[key] = True
