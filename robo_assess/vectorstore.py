"""
robo_assess.vectorstore
=======================

A dependency-light vector store used by the Originality Agent.

It avoids heavy ML dependencies by representing each question as a sparse
bag-of-words TF vector over a normalised token space and comparing with cosine
similarity. This is deterministic, fast, offline-friendly, and good enough to
flag near-duplicate engineering tickets (the threshold in the spec is 0.75).

The index is persisted to a JSON file so previously generated questions are
remembered across runs.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_STOP = {
    "the", "a", "an", "to", "of", "and", "or", "in", "on", "for", "with",
    "that", "this", "is", "are", "be", "by", "as", "at", "it", "so", "must",
    "should", "will", "your", "you", "robot", "ros2", "node",
}


def _tokenize(text: str) -> list[str]:
    toks = _TOKEN_RE.findall(text.lower())
    return [t for t in toks if t not in _STOP and len(t) > 1]


def _vector(text: str) -> Counter:
    return Counter(_tokenize(text))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _shingles(text: str, n: int = 4) -> set[str]:
    """Character n-grams over the normalised token stream. Catches near-identical
    or lightly-edited tickets that bag-of-words cosine can miss when word order or
    minor wording changes but the structure is the same."""
    norm = " ".join(_tokenize(text))
    if len(norm) < n:
        return {norm} if norm else set()
    return {norm[i:i + n] for i in range(len(norm) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def text_similarity(a_text: str, b_text: str) -> float:
    """Best of token-cosine and char-shingle Jaccard. Using max() means this is
    strictly more sensitive than the old token-only cosine: every duplicate the
    cosine caught is still caught, plus structurally-similar paraphrases.

    NOTE: this is still lexical, not semantic. True synonym-level dedup needs
    embeddings — see the author hand-off."""
    return max(
        cosine(_vector(a_text), _vector(b_text)),
        jaccard(_shingles(a_text), _shingles(b_text)),
    )


class VectorStore:
    def __init__(self, path: str = "vectorstore/index.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._items: list[dict] = []
        if self.path.is_file():
            try:
                self._items = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._items = []

    def add(self, qid: str, text: str) -> None:
        # Upsert by id: a regenerated question reuses its slot's id, so it must
        # REPLACE the prior version rather than accumulate a stale vector that
        # would later read as a near-duplicate of itself.
        for item in self._items:
            if item["id"] == qid:
                item["text"] = text
                return
        self._items.append({"id": qid, "text": text})

    def max_similarity(
        self, text: str, exclude_id: str | None = None
    ) -> tuple[float, str | None]:
        """Return (best_similarity, matching_id) against the stored corpus.

        ``exclude_id`` skips a question's own prior version — a regenerated
        question keeps its slot id, and it is not a duplicate of the earlier
        attempt it replaces."""
        best, best_id = 0.0, None
        for item in self._items:
            if exclude_id is not None and item["id"] == exclude_id:
                continue
            s = text_similarity(text, item["text"])
            if s > best:
                best, best_id = s, item["id"]
        return round(best, 3), best_id

    def save(self) -> None:
        self.path.write_text(json.dumps(self._items, indent=2), encoding="utf-8")

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._items)
