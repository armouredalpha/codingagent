"""
ContextRetrievalAgent
=====================

RAG step that runs BEFORE generation.

  1. Searches the vectorstore for the k past questions most similar to the
     current topic + difficulty combination.
  2. Extracts their structural hashes so the two-layer dedup in OriginalityAgent
     can cheaply skip already-seen question patterns.
  3. Bundles syllabus concept_refs so the generator has vocabulary to draw on.

Falls back gracefully when the vectorstore is empty (new topic) — returns an
empty exemplars list with concept_refs only.
"""

from __future__ import annotations

import hashlib
import re

from ..schemas import AgentResult, ContextPack, SyllabusAnalysis
from ..vectorstore import VectorStore
from .base import BaseAgent


def _structural_hash(text: str) -> str:
    """Normalise text and return an MD5 hash for exact/near-exact dedup.

    Normalisation: lowercase → strip punctuation → collapse whitespace →
    replace digit sequences with 'N' so "10 ticks" and "20 ticks" hash the
    same (same concept, different numbers).
    """
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)          # strip punctuation
    t = re.sub(r"\d+", "N", t)              # canonicalise numbers
    t = re.sub(r"\s+", " ", t).strip()      # collapse whitespace
    return hashlib.md5(t.encode()).hexdigest()


class ContextRetrievalAgent(BaseAgent):
    name = "context_retrieval"

    def run(
        self,
        analysis: SyllabusAnalysis,
        top_k: int = 5,
    ) -> AgentResult:
        """Return a ContextPack for the given topic + analysis.

        Parameters
        ----------
        analysis:
            SyllabusAnalysis from the current run — provides skills/concepts as
            the query vocabulary.
        top_k:
            Number of past questions to retrieve from the vectorstore.
        """
        store: VectorStore = self.vectorstore

        # Build query from topic skills + concepts
        query_parts = (analysis.skills[:5] + analysis.concepts[:5])
        query = " ".join(query_parts) if query_parts else " ".join(analysis.skills[:10])

        exemplars: list[dict] = []
        known_hashes: list[str] = []

        min_score: float = getattr(self.settings, "exemplar_min_score", 0.3)

        if store is not None and query:
            try:
                results = store.search(query, top_k=top_k)
                for r in results:
                    score = r.get("score", 0.0)
                    if score < min_score:
                        continue
                    title = r.get("title", "")
                    text = r.get("text", title)
                    exemplars.append({
                        "id": r.get("id", ""),
                        "title": title,
                        "score": round(score, 3),
                    })
                    known_hashes.append(_structural_hash(text or title))

                # Also hash all questions currently in the vectorstore so the
                # dedup layer knows about everything, not just the top-k.
                all_items = store.all_items() if hasattr(store, "all_items") else []
                for item in all_items:
                    h = _structural_hash(item.get("text", item.get("title", "")))
                    if h not in known_hashes:
                        known_hashes.append(h)

            except Exception as exc:  # noqa: BLE001
                self.log.warning("context_retrieval_search_failed", error=str(exc))

        concept_refs = list(set(analysis.concepts + analysis.apis))

        pack = ContextPack(
            exemplars=exemplars,
            concept_refs=concept_refs,
            known_question_hashes=known_hashes,
        )

        res = self._result(context_pack=pack.model_dump())
        res.messages.append(
            f"retrieved {len(exemplars)} exemplars, {len(known_hashes)} known hashes, "
            f"{len(concept_refs)} concept refs"
        )
        return res.finish("ok")
