"""
SkillTriageAgent
================

Merges ComplexityTriageAgent + SkillPickerAgent into a single LLM call.

Previously: 2 separate LLM calls
  1. ComplexityTriageAgent  — decide type_a/b/c distribution
  2. SkillPickerAgent       — pick N ordered skills for slots

Now: 1 LLM call that does both simultaneously.
The LLM sees the full skill list + past exemplars and returns:
  - type distribution (depth_score, type_a/b/c_count)
  - ordered_skills: one entry per slot with skill + archetype + difficulty

Falls back to heuristic triage + rule-based skill picking if LLM fails.
"""

from __future__ import annotations

import itertools
from pathlib import Path

from ..schemas import AgentResult, ContextPack, SkillEntry, SyllabusAnalysis, TriageResult
from .base import BaseAgent

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

_SYSTEM = (
    "You are a robotics curriculum architect. "
    "Analyse the topic and return a JSON triage + skill plan. "
    "No prose. No markdown fences. Valid JSON only."
)


def _load_prompt() -> str:
    p = _PROMPTS_DIR / "skill_triage.txt"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


class SkillTriageAgent(BaseAgent):
    """Single LLM call: complexity triage + skill selection for all slots."""

    name = "skill_triage"

    def run(
        self,
        analysis: SyllabusAnalysis,
        context_pack: ContextPack,
        difficulty: str,
        total_questions: int,
        all_skills: list[SkillEntry],
        already_generated: list[str] | None = None,
        skill_graph=None,
    ) -> AgentResult:
        """Return TriageResult + ordered skill names for each slot.

        Payload keys:
          triage         — TriageResult.model_dump()
          ordered_skills — list of skill names in slot order
        """
        already_generated = list(already_generated or [])
        template = _load_prompt()

        if not template or self.llm is None:
            return self._heuristic_fallback(analysis, difficulty, total_questions, all_skills, already_generated)

        skills_text = "\n".join(
            f"- {s.skill} (section: {s.section}, bloom: {s.bloom_level}, difficulty: {s.difficulty_hint})"
            for s in all_skills
        )
        exemplar_lines = "\n".join(
            f"  - [{e.get('score', 0):.2f}] {e.get('title', e.get('id', ''))}"
            for e in (context_pack.exemplars[:5] or [])
        ) or "  (none — new topic)"
        skills_sample = ", ".join(analysis.skills[:8])
        topic = getattr(analysis, "topic", "") or skills_sample[:60]

        prompt = template.format(
            topic=topic,
            difficulty=difficulty,
            total_questions=total_questions,
            all_skills_list=skills_text,
            already_generated=", ".join(already_generated) if already_generated else "none",
            exemplars=exemplar_lines,
        )

        try:
            raw, usage = self.llm.complete_json(
                system=_SYSTEM,
                user=prompt,
                temperature=0.2,
                max_tokens=2000,
            )

            # Validate counts sum
            raw_sum = (
                int(raw.get("type_a_count", 0))
                + int(raw.get("type_b_count", 0))
                + int(raw.get("type_c_count", 0))
            )
            if raw_sum != total_questions:
                retry_prompt = (
                    prompt
                    + f"\n\nPREVIOUS RESPONSE ERROR: counts sum to {raw_sum}, must equal {total_questions}. "
                    f"Also ordered_skills must have exactly {total_questions} entries. Return corrected JSON."
                )
                raw, usage = self.llm.complete_json(
                    system=_SYSTEM,
                    user=retry_prompt,
                    temperature=0.0,
                    max_tokens=2000,
                )

            triage = TriageResult(
                depth_score=int(raw.get("depth_score", 5)),
                viable_archetypes=raw.get("viable_archetypes", ["TYPE_A", "TYPE_B", "TYPE_C"]),
                type_a_count=int(raw.get("type_a_count", 0)),
                type_b_count=int(raw.get("type_b_count", 0)),
                type_c_count=int(raw.get("type_c_count", 0)),
                notes=str(raw.get("notes", "")),
            )
            triage = self._normalize_counts(triage, total_questions)

            # Extract ordered skill names, validating against available skills
            skill_names = {s.skill for s in all_skills}
            ordered_skills: list[str] = []
            for entry in raw.get("ordered_skills", []):
                name = entry.get("skill", "")
                if name in skill_names and name not in ordered_skills:
                    ordered_skills.append(name)

            # Pad if LLM returned fewer than total_questions skills
            if len(ordered_skills) < total_questions:
                remaining = [s.skill for s in all_skills if s.skill not in ordered_skills and s.skill not in already_generated]
                if not remaining:
                    remaining = [s.skill for s in all_skills if s.skill not in ordered_skills]
                ordered_skills.extend(remaining[:total_questions - len(ordered_skills)])

            self.log.info(
                "skill_triage_done",
                depth=triage.depth_score,
                A=triage.type_a_count, B=triage.type_b_count, C=triage.type_c_count,
                skills=ordered_skills,
                tokens_in=usage.input_tokens,
                tokens_out=usage.output_tokens,
            )

            res = self._result(triage=triage.model_dump(), ordered_skills=ordered_skills)
            res.messages.append(
                f"skill_triage: depth={triage.depth_score} "
                f"A={triage.type_a_count} B={triage.type_b_count} C={triage.type_c_count} "
                f"| skills={ordered_skills}"
            )
            return res.finish("ok")

        except Exception as exc:
            self.log.warning("skill_triage_llm_failed", error=str(exc))
            return self._heuristic_fallback(analysis, difficulty, total_questions, all_skills, already_generated)

    # ------------------------------------------------------------------ #
    # Fallback helpers
    # ------------------------------------------------------------------ #

    def _heuristic_fallback(
        self,
        analysis: SyllabusAnalysis,
        difficulty: str,
        total_questions: int,
        all_skills: list[SkillEntry],
        already_generated: list[str],
    ) -> AgentResult:
        """Rule-based fallback: heuristic triage + ordered skills by difficulty."""
        triage = self._heuristic_triage(analysis, difficulty, total_questions)
        triage = self._normalize_counts(triage, total_questions)

        # Pick skills: prefer matching difficulty, avoid already_generated
        tiers = ["easy", "medium", "hard"]
        tier_map: dict[str, list[SkillEntry]] = {t: [] for t in tiers}
        for s in all_skills:
            if s.skill not in already_generated:
                tier_map.get(s.difficulty_hint or "medium", tier_map["medium"]).append(s)

        diff_seq = (
            ["easy"] * round(total_questions * 0.3)
            + ["medium"] * round(total_questions * 0.5)
            + ["hard"] * round(total_questions * 0.2)
        )
        while len(diff_seq) < total_questions:
            diff_seq.append("medium")
        diff_seq = diff_seq[:total_questions]

        _math_kw = {"matrix", "rotation", "quaternion", "kinematics", "odometry",
                    "transform", "euler", "formula", "derive", "compute", "calculate",
                    "equation", "encoder", "wheel", "dead.reck", "angular", "velocity",
                    "coordinate", "frame", "homogeneous", "vector", "numpy", "math"}

        def _math_score(s: SkillEntry) -> int:
            low = s.skill.lower()
            return sum(1 for kw in _math_kw if kw in low)

        ordered_skills: list[str] = []
        used: set[str] = set()
        for d in diff_seq:
            candidates = [s for s in tier_map.get(d, []) if s.skill not in used]
            if not candidates:
                # relax to any unused
                candidates = [s for s in all_skills if s.skill not in used and s.skill not in already_generated]
            if not candidates:
                candidates = [s for s in all_skills if s.skill not in used]
            if candidates:
                # prefer math-relevant skills over generic ROS2 publisher/subscriber skills
                candidates.sort(key=_math_score, reverse=True)
                chosen = candidates[0]
                ordered_skills.append(chosen.skill)
                used.add(chosen.skill)

        res = self._result(triage=triage.model_dump(), ordered_skills=ordered_skills)
        res.messages.append(
            f"skill_triage: heuristic fallback | "
            f"A={triage.type_a_count} B={triage.type_b_count} C={triage.type_c_count} | "
            f"skills={ordered_skills}"
        )
        return res.finish("ok")

    def _heuristic_triage(self, analysis: SyllabusAnalysis, difficulty: str, total_questions: int) -> TriageResult:
        skills_text = " ".join(analysis.skills).lower()
        math_keywords = {"matrix", "rotation", "quaternion", "kinematics", "odometry",
                         "transform", "euler", "homogeneous", "vector", "formula",
                         "derive", "compute", "calculate", "equation"}
        ros_keywords = {"publish", "subscribe", "service", "topic", "node", "timer",
                        "parameter", "broadcaster", "listener", "tf2", "nav", "odom"}
        math_hits = sum(1 for k in math_keywords if k in skills_text)
        ros_hits = sum(1 for k in ros_keywords if k in skills_text)
        total_hits = math_hits + ros_hits or 1
        math_frac = math_hits / total_hits
        ros_frac = ros_hits / total_hits
        a = round(total_questions * max(0.0, math_frac - 0.2))
        b = round(total_questions * max(0.0, ros_frac - 0.2))
        c = max(0, total_questions - a - b)
        depth = {"easy": 3, "medium": 5, "hard": 8}.get(difficulty, 5)
        return TriageResult(
            depth_score=depth,
            viable_archetypes=["TYPE_A", "TYPE_B", "TYPE_C"],
            type_a_count=a,
            type_b_count=b,
            type_c_count=c,
            notes="heuristic triage",
        )

    def _normalize_counts(self, result: TriageResult, total: int) -> TriageResult:
        current = result.type_a_count + result.type_b_count + result.type_c_count
        if current == total:
            return result
        diff = total - current
        new_c = max(0, result.type_c_count + diff)
        remaining = total - result.type_a_count - result.type_b_count - new_c
        if remaining < 0:
            new_b = max(0, result.type_b_count + remaining)
            remaining = total - result.type_a_count - new_b - new_c
            new_a = max(0, result.type_a_count + remaining)
        else:
            new_a = result.type_a_count
            new_b = result.type_b_count
        return TriageResult(
            depth_score=result.depth_score,
            viable_archetypes=result.viable_archetypes,
            type_a_count=new_a,
            type_b_count=new_b,
            type_c_count=new_c,
            notes=result.notes,
        )
