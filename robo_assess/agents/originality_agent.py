"""
Agent 7 — Originality
=====================

Compares each question against (a) the existing question bank supplied with the
request, (b) previously generated questions stored in memory, and (c) the other
questions in the current batch, using the cosine vector store. Questions scoring
above ``similarity_reject_threshold`` (0.75 by default) are flagged for
regeneration. The computed similarity is written back onto each Question.
"""

from __future__ import annotations

from ..schemas import AgentResult, Question
from ..vectorstore import VectorStore, text_similarity
from .base import BaseAgent


def _question_text(q: Question) -> str:
    return " ".join([q.title, q.scenario, q.objective, " ".join(q.tested_skills)])


class OriginalityAgent(BaseAgent):
    name = "originality_agent"

    def run(
        self,
        questions: list[Question],
        existing: list[str] | None = None,
    ) -> AgentResult:
        store = self.vectorstore or VectorStore(self.settings.vectorstore_path)

        # Seed with existing bank + historical memory
        for i, ex in enumerate(existing or []):
            store.add(f"existing_{i}", ex)
        if self.memory:
            for qid, stem in self.memory.all_stems():
                store.add(qid, stem)

        rejected = []
        batch_texts: list[tuple[str, str]] = []
        for q in questions:
            text = _question_text(q)
            # Exclude this question's own slot id so a re-validated or regenerated
            # question is never flagged as a duplicate of the prior version it
            # replaces (which shares the same question_id in the store/memory).
            ext_sim, match = store.max_similarity(text, exclude_id=q.question_id)
            # also compare within the current batch
            batch_sim = 0.0
            for prev_id, prev_text in batch_texts:
                if prev_id == q.question_id:
                    continue
                batch_sim = max(batch_sim, text_similarity(text, prev_text))
            sim = max(ext_sim, batch_sim)
            q.similarity_score = sim
            batch_texts.append((q.question_id, text))
            store.add(q.question_id, text)
            if self.memory:
                self.memory.remember_question(q.question_id, q.title, text)
            if sim > self.settings.similarity_reject_threshold:
                rejected.append({"qid": q.question_id, "similarity": sim, "match": match})

        store.save()
        res = self._result(rejected=rejected)
        res.messages.append(
            f"originality scored {len(questions)} questions; {len(rejected)} duplicates"
        )
        return res.finish("warn" if rejected else "ok")
