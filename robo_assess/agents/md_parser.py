"""
MD Parser Agent
===============

Three-tier parsing of markdown teaching materials:
- T1: Read raw markdown (full text, cached by hash)
- T2: LLM summarises each ## section to 30-60% length
- T3: LLM extracts testable skills from each summary (5-10% of T1)
- Coverage validation: all sections must yield ≥1 skill

Output: skills/skills.yaml + skills/meta.yaml
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone

import yaml

from ..config import Settings
from ..llm_client import LLMClient
from ..memory import Memory
from ..schemas import SkillEntry, SkillSet
from .base import BaseAgent, AgentResult


class MdParserAgent(BaseAgent):
    def __init__(self, settings: Settings, llm: LLMClient, memory: Memory, **kwargs):
        super().__init__(settings=settings, llm=llm, memory=memory, **kwargs)
        self.name = "md_parser"

    @staticmethod
    def _split_by_headers(text: str) -> dict[str, str]:
        """Split markdown text into {header: content} by ## headings."""
        sections: dict[str, str] = {}
        for part in re.split(r'^## ', text, flags=re.MULTILINE)[1:]:
            lines = part.split('\n', 1)
            header = lines[0].strip()
            content = lines[1].strip() if len(lines) > 1 else ""
            sections[header] = content
        return sections

    def _read_md(self, md_path: str | Path) -> dict[str, str]:
        """Read markdown file and extract sections by ## headers."""
        path = Path(md_path)
        if not path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")

        sections = self._split_by_headers(path.read_text(encoding="utf-8"))
        if not sections:
            raise ValueError(f"No ## sections found in {md_path}")
        return sections

    def _summarise_section(self, header: str, text: str) -> str:
        """LLM summarise a section to 30-60% length."""
        if not text or len(text) < 50:
            return text

        prompt = self._load_prompt("md_section_summariser.txt")
        prompt = prompt.replace("{section_text}", text)

        text_result, _ = self.llm.complete(
            system="You are a technical content specialist.",
            user=prompt,
            temperature=0.3,
            max_tokens=800
        )
        return text_result.strip()

    def _extract_skills(self, header: str, summary: str) -> list[SkillEntry]:
        """LLM extract skills from a section summary."""
        if not summary or len(summary) < 30:
            return []

        template = self._load_prompt("skill_extractor.txt")
        if not template:
            self.log.warning("skill_extractor_prompt_missing", header=header)
            return []
        prompt = template.replace("{section_text}", summary)

        try:
            result, _ = self.llm.complete_json(
                system="You are a skill extraction specialist.",
                user=prompt,
                temperature=0.3,
                max_tokens=600
            )

            skills = []
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and "skill" in item:
                        skills.append(SkillEntry(
                            skill=item["skill"],
                            section=header,
                            bloom_level=item.get("bloom_level", "understand"),
                            difficulty_hint=item.get("difficulty", "medium")
                        ))
            return skills
        except Exception as e:
            self.log.debug(f"skill_extraction_failed", header=header, error=str(e))
            return []

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template from prompts_dir."""
        path = Path(self.settings.prompts_dir) / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _split_sections_text(self, text: str) -> dict[str, str]:
        """Split an in-memory summary string into ## sections.

        Degrades to a single synthetic section when no ## headers are present
        so skill extraction still runs.
        """
        sections = self._split_by_headers(text)
        if not sections:
            sections["Curriculum"] = text.strip()
        return sections

    def extract_from_text(
        self,
        summary_text: str,
        md_path: str | Path,
        md_hash: str,
    ) -> SkillSet:
        """Extract skills from an already-produced summary string (v2 flow).

        Reuses the per-section skill extraction used by ``run`` but sources the
        sections from the summary instead of the raw markdown file. Does NOT write
        to the global skills/ dir — the v2 flow writes skills.yaml into the run
        folder via the workflow layer.
        """
        md_path = Path(md_path)
        sections = self._split_sections_text(summary_text)

        all_skills: list[SkillEntry] = []
        sections_with_skills: list[str] = []
        for header, text in sections.items():
            skills = self._extract_skills(header, text)
            if skills:
                all_skills.extend(skills)
                sections_with_skills.append(header)

        return SkillSet(
            md_file=str(md_path.name),
            md_hash=md_hash,
            skills=all_skills,
            sections_covered=sections_with_skills,
            total_sections=len(sections),
            parsed_at=datetime.now(timezone.utc),
        )

    def run(self, md_path: str | Path) -> AgentResult:
        """Parse markdown: read → summarise → extract → validate coverage."""
        md_path = Path(md_path)

        # Read sections
        sections = self._read_md(md_path)
        md_text = md_path.read_text(encoding="utf-8")
        md_hash = hashlib.md5(md_text.encode()).hexdigest()

        all_skills = []
        sections_with_skills = []

        for header, text in sections.items():
            summarised = self._summarise_section(header, text)
            skills = self._extract_skills(header, summarised)

            if skills:
                all_skills.extend(skills)
                sections_with_skills.append(header)

        skill_set = SkillSet(
            md_file=str(md_path.name),
            md_hash=md_hash,
            skills=all_skills,
            sections_covered=sections_with_skills,
            total_sections=len(sections),
            parsed_at=datetime.now(timezone.utc)
        )

        # Write to skills/ folder
        skills_dir = Path(self.settings.skills_dir)
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Write skills.yaml
        skills_yaml = {
            "md_file": skill_set.md_file,
            "md_hash": skill_set.md_hash,
            "skills": [
                {
                    "skill": s.skill,
                    "section": s.section,
                    "bloom_level": s.bloom_level,
                    "difficulty_hint": s.difficulty_hint
                }
                for s in skill_set.skills
            ]
        }
        try:
            (skills_dir / "skills.yaml").write_text(
                yaml.dump(skills_yaml, default_flow_style=False, sort_keys=False)
            )
        except OSError as e:
            raise RuntimeError(f"Failed to write skills.yaml to {skills_dir}: {e}") from e

        meta = {
            "md_file": skill_set.md_file,
            "md_hash": skill_set.md_hash,
            "total_sections": skill_set.total_sections,
            "sections_covered": len(sections_with_skills),
            "total_skills": len(all_skills),
            "parsed_at": skill_set.parsed_at.isoformat()
        }
        try:
            (skills_dir / "meta.yaml").write_text(
                yaml.dump(meta, default_flow_style=False, sort_keys=False)
            )
        except OSError as e:
            raise RuntimeError(f"Failed to write meta.yaml to {skills_dir}: {e}") from e

        messages = [
            f"Extracted {len(all_skills)} skills from {len(sections)} sections",
            f"Coverage: {len(sections_with_skills)}/{len(sections)} sections covered"
        ]

        return self._result(
            skills=skill_set.model_dump(),
            messages=messages
        )
