"""
Multi-Loop Planner Agent
========================

Manages three distinct feedback loops:

1. PARSER LOOP (skills extraction from markdown):
   SUMMARISE → EXTRACT → VALIDATE_COVERAGE → (retry or DONE_PARSING)

2. GENERATION LOOP (question generation with calibration):
   GENERATE → COMPARE (eval matching) → VALIDATE → CHECK_CONFIDENCE

3. FEEDBACK LOOP (regeneration of failing questions):
   CRITIQUE → REGENERATE → back to COMPARE/VALIDATE

Loop transitions:
- Parser Loop → Generation Loop (after all sections have skills)
- Generation Loop → Feedback Loop (if confidence < bar)
- Feedback Loop → Generation Loop (after regeneration)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..schemas import Question, CoverageMatrix, QuestionQuality


class LoopType(str, Enum):
    """Which loop is active."""
    PARSER = "parser"           # skills extraction
    GENERATION = "generation"   # question generation + calibration
    FEEDBACK = "feedback"       # regeneration with feedback


class ParserAction(str, Enum):
    """Actions in parser loop."""
    SUMMARISE = "summarise"                # LLM summarises markdown section
    EXTRACT = "extract"                    # LLM extracts skills from summary
    VALIDATE_COVERAGE = "validate_coverage" # Check section has ≥1 skill
    DONE_PARSING = "done_parsing"          # All sections done


class GenerationAction(str, Enum):
    """Actions in generation loop."""
    GENERATE = "generate"                  # LLM generates question
    COMPARE = "compare"                    # EvalComparatorAgent matches to reference
    VALIDATE = "validate"                  # Run validators (difficulty, originality, etc)
    CHECK_CONFIDENCE = "check_confidence"  # LearnedConfidenceScorer
    NEXT_CONSTRAINT = "next_constraint"    # Move to next constraint


class FeedbackAction(str, Enum):
    """Actions in feedback loop."""
    CRITIQUE = "critique"                  # LLMCriticAgent harsh feedback
    REGENERATE = "regenerate"              # Re-generate with critique feedback
    BACK_TO_COMPARE = "back_to_compare"   # Validate regenerated question


@dataclass
class ParserLoopState:
    """State of parser loop (skills extraction)."""
    current_section_idx: int = 0
    total_sections: int = 0
    sections_completed: dict[int, list[str]] = field(default_factory=dict)  # {idx: [skills]}
    section_retries: dict[int, int] = field(default_factory=dict)          # {idx: retry_count}
    max_retries: int = 3


@dataclass
class GenerationLoopState:
    """State of generation loop (question generation)."""
    current_constraint_idx: int = 0
    total_constraints: int = 0
    questions: list[Question] = field(default_factory=list)
    generated_skills: list[str] = field(default_factory=list)
    per_question_attempts: dict[str, int] = field(default_factory=dict)


@dataclass
class FeedbackLoopState:
    """State of feedback loop (regeneration)."""
    failing_question_ids: list[str] = field(default_factory=list)
    question_critiques: dict[str, str] = field(default_factory=dict)  # {q_id: critique_text}
    regeneration_attempts: dict[str, int] = field(default_factory=dict)  # {q_id: attempt_count}
    max_regeneration_attempts: int = 2


@dataclass
class LoopDecision:
    """Decision output from planner."""
    loop: LoopType
    action: ParserAction | GenerationAction | FeedbackAction
    reason: str
    targets: list[str] = field(default_factory=list)  # target question/section IDs
    source: str = "planner"

    def model_dump(self) -> dict[str, Any]:
        return {
            "loop": self.loop.value,
            "action": self.action.value,
            "reason": self.reason,
            "targets": self.targets,
            "source": self.source,
        }


class MultiLoopPlanner:
    """Manages all three feedback loops in the generation pipeline."""

    def __init__(self, settings, llm=None, log=None):
        self.settings = settings
        self.llm = llm
        self.log = log

        # Loop states
        self.parser_state = ParserLoopState()
        self.generation_state = GenerationLoopState()
        self.feedback_state = FeedbackLoopState()

        # Current loop
        self.active_loop = LoopType.PARSER
        self.step_count = 0

    # ================================================================
    # PARSER LOOP
    # ================================================================

    def decide_parser_loop(self) -> LoopDecision:
        """Decide next action in parser loop (skills extraction from markdown)."""
        state = self.parser_state

        # All sections processed?
        if state.current_section_idx >= state.total_sections:
            # Transition to generation loop
            self.active_loop = LoopType.GENERATION
            return LoopDecision(
                loop=LoopType.PARSER,
                action=ParserAction.DONE_PARSING,
                reason=f"parsed all {state.total_sections} sections, extracted {sum(len(s) for s in state.sections_completed.values())} skills",
            )

        section_idx = state.current_section_idx
        retry_count = state.section_retries.get(section_idx, 0)

        # Check if section has skills
        if section_idx in state.sections_completed:
            skills = state.sections_completed[section_idx]
            if skills:
                # Section has skills, move to next
                state.current_section_idx += 1
                return LoopDecision(
                    loop=LoopType.PARSER,
                    action=ParserAction.VALIDATE_COVERAGE,
                    reason=f"section {section_idx} has {len(skills)} skills, proceeding to next",
                    targets=[str(section_idx)],
                )
            else:
                # Section had 0 skills, retry summarisation
                if retry_count < state.max_retries:
                    state.section_retries[section_idx] = retry_count + 1
                    return LoopDecision(
                        loop=LoopType.PARSER,
                        action=ParserAction.SUMMARISE,
                        reason=f"section {section_idx} extraction yielded 0 skills, retry {retry_count + 1}/{state.max_retries}",
                        targets=[str(section_idx)],
                    )
                else:
                    # Retry limit, skip to next
                    state.current_section_idx += 1
                    return LoopDecision(
                        loop=LoopType.PARSER,
                        action=ParserAction.VALIDATE_COVERAGE,
                        reason=f"section {section_idx} retry limit reached, skipping",
                        targets=[str(section_idx)],
                    )
        else:
            # Section not yet processed, start with summarisation
            return LoopDecision(
                loop=LoopType.PARSER,
                action=ParserAction.SUMMARISE,
                reason=f"starting extraction from section {section_idx}",
                targets=[str(section_idx)],
            )

    def record_parser_result(self, section_idx: int, skills: list[str]) -> None:
        """Record extraction result from parser loop."""
        self.parser_state.sections_completed[section_idx] = skills

    # ================================================================
    # GENERATION LOOP
    # ================================================================

    def decide_generation_loop(self) -> LoopDecision:
        """Decide next action in generation loop (question generation)."""
        state = self.generation_state

        # All constraints processed?
        if state.current_constraint_idx >= state.total_constraints:
            # All questions generated, transition to feedback loop if needed
            return LoopDecision(
                loop=LoopType.GENERATION,
                action=GenerationAction.NEXT_CONSTRAINT,
                reason=f"generated all {state.total_constraints} questions",
            )

        # Current constraint not yet generated
        if state.current_constraint_idx >= len(state.questions):
            return LoopDecision(
                loop=LoopType.GENERATION,
                action=GenerationAction.GENERATE,
                reason=f"generating question {state.current_constraint_idx + 1}/{state.total_constraints}",
                targets=[f"constraint_{state.current_constraint_idx}"],
            )

        # Question exists, needs validation
        q_id = state.questions[state.current_constraint_idx].question_id
        return LoopDecision(
            loop=LoopType.GENERATION,
            action=GenerationAction.COMPARE,
            reason=f"comparing question {q_id} to reference eval set",
            targets=[q_id],
        )

    def record_generation_result(self, question: Question) -> None:
        """Record generated question."""
        state = self.generation_state
        if len(state.questions) <= state.current_constraint_idx:
            state.questions.append(question)
        state.current_constraint_idx += 1

    # ================================================================
    # FEEDBACK LOOP
    # ================================================================

    def decide_feedback_loop(self) -> LoopDecision:
        """Decide next action in feedback loop (regeneration)."""
        state = self.feedback_state

        # No failing questions?
        if not state.failing_question_ids:
            # Back to generation loop
            self.active_loop = LoopType.GENERATION
            return LoopDecision(
                loop=LoopType.FEEDBACK,
                action=FeedbackAction.BACK_TO_COMPARE,
                reason="no failing questions, back to generation",
            )

        # Pick first failing question
        q_id = state.failing_question_ids[0]
        attempt_count = state.regeneration_attempts.get(q_id, 0)

        # Check regeneration budget
        if attempt_count >= state.max_regeneration_attempts:
            # Budget spent on this question, mark as final and remove from failing list
            state.failing_question_ids.remove(q_id)
            if state.failing_question_ids:
                # More failures to handle
                return self.decide_feedback_loop()
            else:
                # All questions exhausted budget
                self.active_loop = LoopType.GENERATION
                return LoopDecision(
                    loop=LoopType.FEEDBACK,
                    action=FeedbackAction.BACK_TO_COMPARE,
                    reason=f"regeneration budget exhausted for question {q_id}",
                    targets=[q_id],
                )

        # Check if we have critique for this question
        if q_id not in state.question_critiques:
            # Need critique first
            return LoopDecision(
                loop=LoopType.FEEDBACK,
                action=FeedbackAction.CRITIQUE,
                reason=f"generating critique for failing question {q_id}",
                targets=[q_id],
            )
        else:
            # Have critique, regenerate with feedback
            state.regeneration_attempts[q_id] = attempt_count + 1
            return LoopDecision(
                loop=LoopType.FEEDBACK,
                action=FeedbackAction.REGENERATE,
                reason=f"regenerating question {q_id} with critique (attempt {attempt_count + 1}/{state.max_regeneration_attempts})",
                targets=[q_id],
            )

    def record_critique(self, question_id: str, critique: str) -> None:
        """Record LLM critique for a question."""
        self.feedback_state.question_critiques[question_id] = critique

    def record_regeneration_result(self, question_id: str, new_question: Question) -> None:
        """Record regenerated question. Removes from failing list if successful."""
        state = self.feedback_state
        if question_id in state.failing_question_ids:
            # Question regenerated, remove from failing list
            # (quality check will determine if it passes)
            state.failing_question_ids.remove(question_id)

    def set_failing_questions(self, question_ids: list[str]) -> None:
        """Update list of failing questions (from quality checker)."""
        self.feedback_state.failing_question_ids = question_ids.copy()
        self.active_loop = LoopType.FEEDBACK

    # ================================================================
    # MAIN DECISION LOGIC
    # ================================================================

    def decide(self) -> LoopDecision:
        """Decide next action based on current loop."""
        self.step_count += 1

        if self.active_loop == LoopType.PARSER:
            return self.decide_parser_loop()
        elif self.active_loop == LoopType.GENERATION:
            return self.decide_generation_loop()
        elif self.active_loop == LoopType.FEEDBACK:
            return self.decide_feedback_loop()
        else:
            raise ValueError(f"Unknown loop: {self.active_loop}")

    def init_parser_loop(self, total_sections: int) -> None:
        """Initialize parser loop with section count."""
        self.parser_state = ParserLoopState(total_sections=total_sections)
        self.active_loop = LoopType.PARSER

    def init_generation_loop(self, total_constraints: int) -> None:
        """Initialize generation loop with constraint count."""
        self.generation_state = GenerationLoopState(total_constraints=total_constraints)
        self.active_loop = LoopType.GENERATION

    def get_status(self) -> dict[str, Any]:
        """Return current planner status."""
        return {
            "active_loop": self.active_loop.value,
            "step_count": self.step_count,
            "parser": {
                "section": self.parser_state.current_section_idx,
                "total": self.parser_state.total_sections,
                "completed_skills": sum(len(s) for s in self.parser_state.sections_completed.values()),
            },
            "generation": {
                "question": self.generation_state.current_constraint_idx,
                "total": self.generation_state.total_constraints,
                "generated": len(self.generation_state.questions),
            },
            "feedback": {
                "failing_count": len(self.feedback_state.failing_question_ids),
            },
        }
