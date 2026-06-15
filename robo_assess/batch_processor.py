"""
Batch Processor: Reduce LLM calls by batching similar requests.

Strategies:
1. Markdown summarization: process 5 sections per LLM call instead of per-section
2. Skill picker decisions: batch 3-5 skill-picking requests in one LLM call
3. Question validation: batch multiple questions through validators
"""

from __future__ import annotations

from typing import Any


class BatchMarkdownSummarizer:
    """Batch 5 markdown sections per LLM call instead of individual calls.

    Reduces: N sections → ⌈N/5⌉ calls
    Example: 15 sections → 3 calls (instead of 15)
    """

    def __init__(self, llm, token_counter=None):
        self.llm = llm
        self.token_counter = token_counter
        self.batch_size = 5

    def summarize_batch(self, sections: list[dict[str, str]]) -> dict[int, str]:
        """Summarize multiple sections in a single LLM call.

        Args:
            sections: List of {"section_num": int, "heading": str, "text": str}

        Returns: {section_num: summary}
        """
        # Build prompt for batch summarization
        batch_text = ""
        for s in sections:
            batch_text += f"\n## Section {s['section_num']}: {s['heading']}\n{s['text'][:500]}...\n"

        prompt = f"""Summarize these markdown sections to 30-60% length. Keep technical details.

Sections:
{batch_text}

Respond as JSON:
{{
  "1": "summary of section 1",
  "2": "summary of section 2",
  ...
}}
"""

        response = self.llm.call(prompt, max_tokens=1000)

        # Parse batch response
        import json

        try:
            summaries = json.loads(response)
            return summaries
        except json.JSONDecodeError:
            # Fallback: return empty summaries
            return {s["section_num"]: "" for s in sections}

    def process_all_sections(
        self, sections: list[dict[str, str]]
    ) -> dict[int, str]:
        """Process all sections in batches, reducing LLM calls.

        Args:
            sections: List of all sections to summarize

        Returns: {section_num: summary}
        """
        results = {}

        # Batch sections into groups of 5
        for i in range(0, len(sections), self.batch_size):
            batch = sections[i : i + self.batch_size]
            batch_summaries = self.summarize_batch(batch)
            results.update(batch_summaries)

        return results


class BatchSkillPicker:
    """Batch skill-picking decisions: pick 3 skills in one LLM call.

    Reduces: 6 questions × 1 call per skill → 2 calls (one batch of 3, one batch of 3)
    """

    def __init__(self, llm, token_counter=None):
        self.llm = llm
        self.token_counter = token_counter
        self.batch_size = 3

    def pick_batch(
        self,
        constraints: list[dict[str, str]],
        all_skills: list[dict[str, str]],
        already_generated: list[str],
    ) -> list[dict[str, str]]:
        """Pick N skills in a single LLM call for N constraints.

        Args:
            constraints: List of {"difficulty": "easy|medium|hard", "bloom_level": "...", "domain": "..."}
            all_skills: List of available skills with metadata
            already_generated: Skills already used (avoid repeats)

        Returns: List of selected skills (one per constraint, in order)
        """
        available_skills = [s for s in all_skills if s["skill"] not in already_generated]

        # Build prompt for batch skill selection
        skills_text = "\n".join(
            [f"- {s['skill']} (difficulty: {s.get('difficulty', 'medium')}, section: {s.get('section')})" for s in
             available_skills]
        )

        constraints_text = "\n".join(
            [
                f"{i + 1}. Difficulty: {c['difficulty']}, Bloom: {c['bloom_level']}, Domain: {c.get('domain', 'any')}"
                for i, c in enumerate(constraints)
            ]
        )

        prompt = f"""Pick the best skill for each question constraint. Match by difficulty, Bloom level, and domain.

Available skills:
{skills_text}

Constraints (pick one skill per constraint):
{constraints_text}

Respond as JSON list:
[
  {{"skill": "skill name", "reason": "why this matches"}},
  {{"skill": "skill name", "reason": "why this matches"}},
  ...
]
"""

        response = self.llm.call(prompt, max_tokens=500)

        # Parse batch response
        import json

        try:
            picks = json.loads(response)
            # Validate picks are in available_skills
            validated = []
            for pick in picks:
                skill_name = pick.get("skill")
                if any(s["skill"] == skill_name for s in available_skills):
                    validated.append(pick)
                else:
                    # Fallback to first available skill
                    validated.append(available_skills[0] if available_skills else {})
            return validated
        except json.JSONDecodeError:
            # Fallback: pick first N available skills
            return available_skills[: len(constraints)]

    def process_all_constraints(
        self,
        constraints: list[dict[str, str]],
        all_skills: list[dict[str, str]],
        already_generated: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Process all constraints in batches, reducing LLM calls.

        Args:
            constraints: All constraints to process
            all_skills: All available skills
            already_generated: Skills already used

        Returns: List of selected skills (one per constraint, in order)
        """
        already_generated = already_generated or []
        results = []

        # Batch constraints into groups of 3
        for i in range(0, len(constraints), self.batch_size):
            batch_constraints = constraints[i : i + self.batch_size]
            batch_picks = self.pick_batch(batch_constraints, all_skills, already_generated)
            results.extend(batch_picks)
            # Update already_generated with newly picked skills
            for pick in batch_picks:
                skill_name = pick.get("skill")
                if skill_name:
                    already_generated.append(skill_name)

        return results


class BatchValidator:
    """Batch validation: run 3-4 questions through validators in parallel.

    Reduces individual question validation overhead.
    """

    def __init__(self, validators: dict[str, Any]):
        """
        Args:
            validators: {"difficulty": DifficultyAgent, "originality": OriginalityAgent, ...}
        """
        self.validators = validators

    def validate_batch(self, questions: list[Any]) -> list[dict[str, Any]]:
        """Validate multiple questions in parallel.

        Args:
            questions: List of Question objects

        Returns: List of validation results
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = [None] * len(questions)

        def validate_question(idx: int, q: Any) -> tuple[int, dict[str, Any]]:
            """Validate a single question against all validators."""
            result = {"question_id": q.question_id}
            for validator_name, validator in self.validators.items():
                try:
                    # Each validator returns a score 0-100
                    score = validator.score(q)
                    result[f"{validator_name}_score"] = score
                except Exception as e:
                    result[f"{validator_name}_error"] = str(e)
                    result[f"{validator_name}_score"] = 0
            return idx, result

        # Run validation in parallel (up to 4 threads)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(validate_question, idx, q)
                for idx, q in enumerate(questions)
            ]
            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result

        return results


def estimate_llm_call_reduction(
    num_questions: int,
    num_sections: int,
    batch_size_markdown: int = 5,
    batch_size_skills: int = 3,
) -> dict[str, int]:
    """Estimate LLM call reduction from batching.

    Example:
    - 6 questions, 15 sections
    - Without batching: 15 (markdown) + 6 (skill picker) + ... = ~30 calls
    - With batching: 3 (markdown) + 2 (skill picker) + ... = ~8 calls
    - Reduction: 4.2x

    Returns: {"without_batching": N, "with_batching": M, "reduction_factor": N/M}
    """
    # Markdown summarization calls
    markdown_calls_without = num_sections
    markdown_calls_with = (num_sections + batch_size_markdown - 1) // batch_size_markdown

    # Skill picker calls
    picker_calls_without = num_questions
    picker_calls_with = (num_questions + batch_size_skills - 1) // batch_size_skills

    # Estimate: ~5 calls per question for validation (difficulty, originality, scope, etc.)
    validation_calls = num_questions * 5

    total_without = markdown_calls_without + picker_calls_without + validation_calls
    total_with = markdown_calls_with + picker_calls_with + validation_calls

    reduction_factor = total_without / max(total_with, 1)

    return {
        "without_batching": total_without,
        "with_batching": total_with,
        "reduction_factor": round(reduction_factor, 2),
        "markdown_reduction": f"{markdown_calls_without} → {markdown_calls_with}",
        "picker_reduction": f"{picker_calls_without} → {picker_calls_with}",
    }
