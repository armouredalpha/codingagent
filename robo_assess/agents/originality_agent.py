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

from pathlib import Path

from ..schemas import AgentResult, Question
from ..vectorstore import VectorStore, text_similarity
from .base import BaseAgent

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    try:
        return (_PROMPTS_DIR / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def _question_text(q: Question) -> str:
    return " ".join([q.title, q.scenario, q.objective, " ".join(q.tested_skills)])


class OriginalityAgent(BaseAgent):
    name = "originality_agent"

    def _web_duplicate_check(self, q: Question) -> tuple[float, str] | None:
        """Search the web (OpenRouter ``:online`` model) for near-duplicates of
        this question and return ``(originality_score, note)`` where 1.0 is fully
        original. Returns ``None`` on any failure / when disabled / no key, so the
        caller falls back to the vectorstore signal. Never raises.
        """
        if not getattr(self.settings, "enable_web_originality", False):
            return None
        if self.settings.provider != "openrouter" or not self.settings.api_key:
            return None

        try:
            from ..llm_client import LLMClient

            model = self.settings.model
            if not model.endswith(":online"):
                model = f"{model}:online"
            online = LLMClient(
                provider="openrouter",
                model=model,
                api_key=self.settings.api_key,
            )
            skill = q.tested_skills[0] if q.tested_skills else ""
            template = _load_prompt("originality_web.txt")
            prompt = template.format(
                title=q.title,
                skill=skill,
                scenario=q.scenario,
                objective=q.objective,
            ) if template else (
                "Search the web for existing ROS2 coding exercises/tutorials that "
                "match the following assessment question. Judge how ORIGINAL it is "
                "(1.0 = no close match found online, 0.0 = a near-identical exercise "
                "exists).\n\n"
                f"Title: {q.title}\n"
                f"Skill: {skill}\n"
                f"Scenario: {q.scenario}\n"
                f"Objective: {q.objective}\n\n"
                'Reply with JSON only: {"originality": <0.0-1.0>, "note": "<closest match or none>"}'
            )
            result, _ = online.complete_json(
                system="You assess the originality of ROS2 coding questions using web search.",
                user=prompt,
                temperature=0.0,
                max_tokens=200,
            )
            if isinstance(result, dict) and "originality" in result:
                score = max(0.0, min(1.0, float(result["originality"])))
                return score, str(result.get("note", ""))
        except Exception as exc:  # noqa: BLE001 — web check is best-effort
            self.log.debug("web_originality_unavailable", error=str(exc))
        return None

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

            # Optional live web check — take the STRICTER signal (higher
            # similarity = lower originality). Web originality s maps to
            # similarity (1 - s); blend by max() so a web duplicate can only
            # raise the similarity, never mask the vectorstore signal.
            web = self._web_duplicate_check(q)
            if web is not None:
                web_score, note = web
                web_sim = 1.0 - web_score
                if web_sim > sim:
                    self.log.info("web_originality_stricter",
                                  qid=q.question_id, web_sim=round(web_sim, 3), note=note)
                sim = max(sim, web_sim)

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
