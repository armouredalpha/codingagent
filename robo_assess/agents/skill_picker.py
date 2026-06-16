"""
Skill Picker Agent
==================

Selects the right skill from skills.yaml based on user-requested difficulty,
Bloom level, and domain. Uses rule-based filtering + optional LLM tiebreaker.

Input: difficulty, bloom_level, domain, all_skills, already_generated
Output: selected skill + reasoning
"""

from __future__ import annotations

import random
from pathlib import Path

from ..config import Settings
from ..llm_client import LLMClient
from ..memory import Memory
from ..schemas import (
    SkillEntry,
    AgentResult,
    GenerateRequest,
    SkillSpec,
    QuestionScope,
)
from .base import BaseAgent


class SkillPickerAgent(BaseAgent):
    """Picks skills based on user constraints.

    Two modes:
    - manual: User specifies constraints, agent picks one skill per constraint
    - auto: Agent auto-generates 3 constraints (easy/medium/hard) ensuring diversity
    """

    def __init__(self, settings: Settings, llm: LLMClient, memory: Memory, **kwargs):
        super().__init__(settings=settings, llm=llm, memory=memory, **kwargs)
        self.name = "skill_picker"

    def _bloom_rank(self, level: str) -> int:
        """Map Bloom level to numeric rank."""
        ranks = {
            "remember": 1,
            "understand": 2,
            "apply": 3,
            "analyze": 4,
            "evaluate": 5,
            "create": 6,
        }
        return ranks.get(level.lower(), 0)

    def _filter_candidates(
        self,
        difficulty: str,
        bloom_level: str,
        domain: str,
        all_skills: list[SkillEntry],
        already_generated: list[str],
    ) -> list[SkillEntry]:
        """Filter skills by constraints."""
        target_bloom_rank = self._bloom_rank(bloom_level)

        candidates = [
            s
            for s in all_skills
            if (
                # Difficulty: exact match preferred
                s.difficulty_hint == difficulty
                # Bloom: must be >= target
                and self._bloom_rank(s.bloom_level) >= target_bloom_rank
                # Not already generated
                and s.skill not in already_generated
            )
        ]

        return candidates

    def _fallback_filter(
        self,
        difficulty: str,
        bloom_level: str,
        all_skills: list[SkillEntry],
        already_generated: list[str],
    ) -> list[SkillEntry]:
        """Relax filters if no candidates found."""
        candidates = [
            s
            for s in all_skills
            if (
                s.difficulty_hint == difficulty
                and s.skill not in already_generated
            )
        ]

        if not candidates:
            # Relax difficulty by one tier
            if difficulty == "easy":
                difficulty = "medium"
            elif difficulty == "medium":
                difficulty = "hard"

            candidates = [
                s
                for s in all_skills
                if (
                    s.difficulty_hint == difficulty
                    and s.skill not in already_generated
                )
            ]

        if not candidates:
            # Last resort: any ungenerated
            candidates = [
                s
                for s in all_skills
                if s.skill not in already_generated
            ]

        return candidates

    def _llm_pick(
        self,
        difficulty: str,
        bloom_level: str,
        domain: str,
        candidates: list[SkillEntry],
        already_generated: list[str],
    ) -> SkillEntry:
        """Use LLM to pick best skill among candidates."""
        # Build skill list text
        skills_text = "\n".join(
            [
                f"- {s.skill} (section: {s.section}, bloom: {s.bloom_level}, difficulty: {s.difficulty_hint})"
                for s in candidates
            ]
        )

        prompt = self._load_prompt("skill_picker.txt")
        prompt = (prompt
            .replace("{difficulty}", difficulty)
            .replace("{bloom_level}", bloom_level)
            .replace("{domain}", domain or "any")
            .replace("{all_skills_list}", skills_text)
            .replace("{already_generated}", ", ".join(already_generated) if already_generated else "none")
        )

        try:
            result, _ = self.llm.complete_json(
                system="You select the best skill from a list.",
                user=prompt,
                temperature=0.3,
                max_tokens=200,
            )

            selected_skill_name = result.get("selected_skill", "")
            selected = next(
                (s for s in candidates if s.skill == selected_skill_name),
                None,
            )

            if selected:
                return selected

        except Exception as e:
            self.log.warning("llm_pick_error", error=str(e))

        # Fallback: return first candidate
        return candidates[0]

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template."""
        path = Path(self.settings.prompts_dir) / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def generate_auto_constraints(self, domain: str = "") -> list[dict]:
        """Generate default constraints for auto mode: 1 easy, 1 medium, 1 hard.

        Args:
            domain: Optional domain filter (warehouse, inspection, simulation, etc)

        Returns: List of 3 constraint dicts
        """
        return [
            {
                "difficulty": "easy",
                "bloom_level": "apply",
                "domain": domain,
                "mode": "auto",
            },
            {
                "difficulty": "medium",
                "bloom_level": "analyze",
                "domain": domain,
                "mode": "auto",
            },
            {
                "difficulty": "hard",
                "bloom_level": "create",
                "domain": domain,
                "mode": "auto",
            },
        ]

    def to_generate_requests(
        self,
        auto_result: AgentResult,
        topic_name: str,
        all_skills: list[SkillEntry],
        md_file: str = "",
        md_hash: str = "",
    ) -> list[GenerateRequest]:
        """Turn a ``run_auto`` result into one GenerateRequest per selected skill.

        ``question_scope.concepts_allowed`` is every extracted skill name MINUS
        the selected skill (the documented input format excludes the selected
        skill from the allowed-concepts list).
        """
        all_names = [s.skill for s in all_skills]
        requests: list[GenerateRequest] = []
        for entry in auto_result.payload.get("skills", []):
            skill_dict = entry["skill"]
            constraint = entry.get("constraint", {})
            selected = skill_dict["skill"]
            concepts_allowed = [n for n in all_names if n != selected]
            requests.append(
                GenerateRequest(
                    topic_name=topic_name,
                    selected_skill=SkillSpec(
                        skill=selected,
                        bloom_level=constraint.get("bloom_level", skill_dict.get("bloom_level", "apply")),
                        difficulty=constraint.get("difficulty", skill_dict.get("difficulty_hint", "easy")),
                    ),
                    question_scope=QuestionScope(concepts_allowed=concepts_allowed),
                    md_file=md_file,
                    md_hash=md_hash,
                )
            )
        return requests

    def run(
        self,
        difficulty: str,
        bloom_level: str,
        domain: str,
        all_skills: list[SkillEntry],
        already_generated: list[str] | None = None,
    ) -> AgentResult:
        """Pick skill matching difficulty/bloom/domain constraints (manual mode).

        Args:
            difficulty: "easy" | "medium" | "hard"
            bloom_level: "understand" | "apply" | "analyze" | "evaluate" | "create"
            domain: "warehouse" | "inspection" | "simulation" | etc, or "" for any
            all_skills: list of SkillEntry from skills.yaml
            already_generated: list of skill names already used

        Returns: AgentResult with selected skill
        """
        already_generated = already_generated or []

        # Filter by constraints
        candidates = self._filter_candidates(
            difficulty, bloom_level, domain, all_skills, already_generated
        )

        if not candidates:
            # Fallback: relax filters
            candidates = self._fallback_filter(
                difficulty, bloom_level, all_skills, already_generated
            )

        if not candidates:
            raise ValueError(
                f"No skills available for difficulty={difficulty}, "
                f"bloom_level={bloom_level}"
            )

        # Pick based on candidate count
        if len(candidates) <= 2:
            # Few options: pick randomly
            selected = random.choice(candidates)
            source = "random (few candidates)"
        else:
            # Many options: use LLM to pick best
            selected = self._llm_pick(
                difficulty, bloom_level, domain, candidates, already_generated
            )
            source = "llm"

        return self._result(
            skill=selected.model_dump(),
            messages=[
                f"Selected: {selected.skill}",
                f"Bloom: {selected.bloom_level}, Difficulty: {selected.difficulty_hint}",
                f"Source: {source}",
            ],
        )

    def run_auto(
        self,
        all_skills: list[SkillEntry],
        domain: str = "",
        already_generated: list[str] | None = None,
    ) -> AgentResult:
        """Auto mode: pick 3 skills (easy, medium, hard) ensuring diversity.

        This is used when instructor just says "generate questions" without
        specifying constraints. System automatically ensures one easy, one medium,
        one hard question.

        Args:
            all_skills: list of SkillEntry from skills.yaml
            domain: Optional domain to constrain to
            already_generated: list of skill names already used in previous runs

        Returns: AgentResult with 3 selected skills
        """
        already_generated = already_generated or []
        constraints = self.generate_auto_constraints(domain)
        selected_skills = []

        for constraint in constraints:
            diff = constraint["difficulty"]
            bloom = constraint["bloom_level"]

            # Filter by constraint
            candidates = self._filter_candidates(
                diff, bloom, domain, all_skills, already_generated
            )

            if not candidates:
                # Fallback: relax
                candidates = self._fallback_filter(
                    diff, bloom, all_skills, already_generated
                )

            if not candidates:
                self.log.warning(
                    "auto_mode_no_candidates",
                    difficulty=diff,
                    bloom_level=bloom,
                )
                continue

            # Pick for this tier
            if len(candidates) <= 2:
                selected = random.choice(candidates)
                source = "random"
            else:
                selected = self._llm_pick(
                    diff, bloom, domain, candidates, already_generated
                )
                source = "llm"

            selected_skills.append(
                {
                    "constraint": constraint,
                    "skill": selected.model_dump(),
                    "source": source,
                }
            )
            already_generated.append(selected.skill)

        if not selected_skills:
            raise ValueError("Auto mode: failed to select any skills")

        return self._result(
            skills=selected_skills,
            messages=[
                f"Auto mode: Selected {len(selected_skills)} skills",
                f"Easy: {selected_skills[0]['skill']['skill']}",
                f"Medium: {selected_skills[1]['skill']['skill']}" if len(selected_skills) > 1 else "",
                f"Hard: {selected_skills[2]['skill']['skill']}" if len(selected_skills) > 2 else "",
            ],
        )
