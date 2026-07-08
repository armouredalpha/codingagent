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
from ..vectorstore import text_similarity
from ..semantic_vectorstore import build_vectorstore
from ..agents.context_retrieval import _structural_hash
from .base import BaseAgent

def _question_text(q: Question) -> str:
    return " ".join([q.title, q.scenario, q.objective, " ".join(q.tested_skills)])


class OriginalityAgent(BaseAgent):
    name = "originality_agent"

    def run(
        self,
        questions: list[Question],
        existing: list[str] | None = None,
        known_question_hashes: list[str] | None = None,
    ) -> AgentResult:
        """Score originality using two layers.

        Layer A (structural) — O(1) hash lookup, runs first:
            Normalise text (lowercase, strip punctuation, canonicalise numbers)
            → MD5 hash → check against known_question_hashes set.
            Catches reworded-identical questions that cosine might score below
            the rejection threshold because a few words differ.

        Layer B (semantic) — existing cosine + shingle vectorstore:
            Only reached when Layer A does not flag the question.
            Catches same-concept paraphrases that structural normalisation misses.
        """
        store = self.vectorstore or build_vectorstore(self.settings)

        # Build the known-hash set from RAG context + existing bank only.
        # Memory stems (previously-generated questions) are NOT loaded here;
        # they are only added to the vectorstore after a run fully completes
        # with APPROVED questions (in orchestrator._finish_run). Loading all
        # past stems here caused every re-run of the same syllabus to see
        # its own questions as near-duplicates (similarity=1.0), which made
        # the entire batch fail confidence with no path out via regeneration.
        hash_set: set[str] = set(known_question_hashes or [])

        for i, ex in enumerate(existing or []):
            store.add(f"existing_{i}", ex)
            hash_set.add(_structural_hash(ex))

        # Remove hashes belonging to the current batch so that a question
        # validated in round 1 is not flagged as its own duplicate in round 2.
        current_ids = {q.question_id for q in questions}
        current_hashes = {_structural_hash(_question_text(q)) for q in questions}
        hash_set -= current_hashes

        rejected = []
        patches: dict[str, dict] = {}
        layer_a_hits = 0
        batch_texts: list[tuple[str, str]] = []
        batch_hashes: set[str] = set()

        for q in questions:
            text = _question_text(q)
            q_hash = _structural_hash(text)

            # ── Layer A: structural hash ─────────────────────────────────────
            if q_hash in hash_set or q_hash in batch_hashes:
                sim = 1.0  # treat structural duplicate as similarity=1
                layer_a_hits += 1
                self.log.info(
                    "layer_a_duplicate",
                    qid=q.question_id,
                    title=q.title[:60],
                )
            else:
                # ── Layer B: cosine + shingle vectorstore ────────────────────
                # exclude_id (singular) skips the question's own prior version
                ext_sim, match = store.max_similarity(text, exclude_id=q.question_id)
                batch_sim = 0.0
                for prev_id, prev_text in batch_texts:
                    if prev_id == q.question_id:
                        continue
                    batch_sim = max(batch_sim, text_similarity(text, prev_text))
                sim = max(ext_sim, batch_sim)



            patches[q.question_id] = {"similarity_score": sim}
            batch_texts.append((q.question_id, text))
            batch_hashes.add(q_hash)
            hash_set.add(q_hash)     # prevent intra-batch structural duplicates
            store.add(q.question_id, text)
            # Do NOT call memory.remember_question() here — questions are saved
            # to memory only after the run completes with APPROVED status
            # (see orchestrator._finish_run). Saving rejected questions here
            # caused the near-duplicate spiral: same-syllabus re-runs see their
            # own questions as duplicates and cannot escape via regeneration.
            if sim > self.settings.similarity_reject_threshold:
                rejected.append({"qid": q.question_id, "similarity": sim})

        # Do NOT save the vectorstore here — it is persisted in _finish_run
        # only for approved questions so rejected runs don't pollute future
        # originality checks.
        res = self._result(rejected=rejected, patches=patches)
        res.messages.append(
            f"originality scored {len(questions)} questions; "
            f"{layer_a_hits} layer-A (structural) + "
            f"{len(rejected) - layer_a_hits} layer-B (semantic) duplicates"
        )
        return res.finish("warn" if rejected else "ok")
