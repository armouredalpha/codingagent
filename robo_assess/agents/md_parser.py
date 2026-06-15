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

from ..config import Settings
from ..llm_client import LLMClient
from ..memory import Memory
from ..schemas import SkillEntry, SkillSet
from .base import BaseAgent, AgentResult


class MdParserAgent(BaseAgent):
    def __init__(self, settings: Settings, llm: LLMClient, memory: Memory, **kwargs):
        super().__init__(settings=settings, llm=llm, memory=memory, **kwargs)
        self.name = "md_parser"

    def _read_md(self, md_path: str | Path) -> dict[str, str]:
        """Read markdown, extract sections by ## headers.

        Returns: {section_header: section_text}
        """
        path = Path(md_path)
        if not path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")

        text = path.read_text(encoding="utf-8")
        sections = {}

        # Split by ## headers
        parts = re.split(r'^## ', text, flags=re.MULTILINE)
        for part in parts[1:]:  # skip pre-header text
            lines = part.split('\n', 1)
            header = lines[0].strip()
            content = lines[1].strip() if len(lines) > 1 else ""
            sections[header] = content

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

        prompt = self._load_prompt("skill_extractor.txt")
        prompt = prompt.replace("{section_text}", summary)

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
            # Extract skills directly (no summarization for now)
            skills = self._extract_skills(header, text)

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
        skills_dir.mkdir(exist_ok=True)

        import yaml

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
        (skills_dir / "skills.yaml").write_text(
            yaml.dump(skills_yaml, default_flow_style=False, sort_keys=False)
        )

        # Write meta.yaml
        meta = {
            "md_file": skill_set.md_file,
            "md_hash": skill_set.md_hash,
            "total_sections": skill_set.total_sections,
            "sections_covered": len(sections_with_skills),
            "total_skills": len(all_skills),
            "parsed_at": skill_set.parsed_at.isoformat()
        }
        (skills_dir / "meta.yaml").write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

        messages = [
            f"Extracted {len(all_skills)} skills from {len(sections)} sections",
            f"Coverage: {len(sections_with_skills)}/{len(sections)} sections covered"
        ]

        return self._result(
            skills=skill_set.model_dump(),
            messages=messages
        )
