"""
MD Summary Agent
================

First step of the single-command `generate` flow. Reads the full markdown
teaching material and produces a concise, section-preserving summary that the
MdParserAgent then extracts skills from. Keeping the `## ` headers intact lets
the parser split the summary back into sections.

This is an LLM agent — there is no offline path. A transient failure falls back
to the raw markdown so skill extraction can still proceed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import Settings
from ..llm_client import LLMClient
from ..memory import Memory
from .base import BaseAgent, AgentResult

_SUMMARY_FILENAME = "summary.md"


class MdSummaryAgent(BaseAgent):
    def __init__(self, settings: Settings, llm: LLMClient, memory: Memory | None = None, **kwargs):
        super().__init__(settings=settings, llm=llm, memory=memory, **kwargs)
        self.name = "md_summary"

    def _load_prompt(self) -> str:
        path = Path(self.settings.prompts_dir) / "md_summary.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return "Summarise this robotics curriculum, keeping every ## header and " \
               "every skill/API/component:\n\n{md_text}"

    def run(self, md_path: str | Path) -> AgentResult:
        md_path = Path(md_path)
        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")

        md_text = md_path.read_text(encoding="utf-8")
        md_hash = hashlib.md5(md_text.encode()).hexdigest()

        prompt = self._load_prompt().replace("{md_text}", md_text)

        summary = ""
        try:
            summary, _ = self.llm.complete(  # type: ignore[union-attr]
                system="You are a robotics curriculum analyst.",
                user=prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            summary = summary.strip()
        except Exception as exc:  # noqa: BLE001
            self.log.warning("md_summary_failed_fallback_raw", error=str(exc))

        # Fall back to raw markdown if the summary is empty/too short so skill
        # extraction always has section content to work with.
        if not summary or len(summary) < 50:
            self.log.warning("md_summary_empty_using_raw")
            summary = md_text

        # Persist summary alongside skills.yaml so skill extraction can reuse it.
        skills_dir = Path(self.settings.skills_dir)
        skills_dir.mkdir(parents=True, exist_ok=True)
        summary_path = skills_dir / _SUMMARY_FILENAME
        summary_path.write_text(
            f"<!-- md_hash:{md_hash} -->\n{summary}", encoding="utf-8"
        )
        self.log.info("summary_cached", path=str(summary_path), md_hash=md_hash)

        res = self._result(summary=summary, md_hash=md_hash, md_file=md_path.name)
        res.messages.append(
            f"summarised {len(md_text)} chars → {len(summary)} chars"
        )
        return res.finish()

    @classmethod
    def load_cached(cls, skills_dir: str | Path, md_hash: str) -> str | None:
        """Return cached summary text if it matches md_hash, else None."""
        path = Path(skills_dir) / _SUMMARY_FILENAME
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        first_line, _, body = text.partition("\n")
        if first_line.strip() == f"<!-- md_hash:{md_hash} -->":
            return body
        return None
