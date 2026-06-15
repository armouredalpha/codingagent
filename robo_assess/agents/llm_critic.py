"""
LLM Critic Agent
===============

Harsh, detailed feedback on failed/low-confidence questions.
Used for targeting regeneration feedback.

Input: Question + confidence breakdown + eval score + validation results
Output: CriticFeedback with issues and fix_directives
"""

from __future__ import annotations

from pathlib import Path

from ..config import Settings
from ..llm_client import LLMClient
from ..memory import Memory
from ..schemas import CriticFeedback, Question
from .base import BaseAgent, AgentResult


class LLMCriticAgent(BaseAgent):
    def __init__(self, settings: Settings, llm: LLMClient, memory: Memory, **kwargs):
        super().__init__(settings=settings, llm=llm, memory=memory, **kwargs)
        self.name = "llm_critic"

    def _format_failed_checks(self, question: Question) -> str:
        """Format all failed checks from a question."""
        checks = []

        if question.confidence and question.confidence.confidence < 85:
            checks.append(f"Low confidence: {question.confidence.confidence:.1f}/100")

        if question.eval_comparison and question.eval_comparison.eval_match_score < 85:
            checks.append(
                f"Difficulty mismatch: {question.eval_comparison.eval_match_score:.1f}/100"
            )

        if question.similarity_score >= 0.75:
            checks.append(f"Near-duplicate: similarity {question.similarity_score:.2f}")

        if question.scope_violations:
            checks.extend([f"Scope violation: {v}" for v in question.scope_violations])

        if not question.auto_gradable:
            checks.append("Not auto-gradable")

        if question.grading_execution and question.grading_execution.status == "FAIL":
            checks.append(f"Grading execution failed: {question.grading_execution.detail}")

        return "\n".join(checks) if checks else "Unknown failure"

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template."""
        path = Path(self.settings.prompts_dir) / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def run(self, question: Question) -> AgentResult:
        """Generate harsh critic feedback for question regeneration."""
        failed_checks = self._format_failed_checks(question)

        # Get confidence scores
        conf = question.confidence or {}
        eval_score = (
            question.eval_comparison.eval_match_score
            if question.eval_comparison else 50.0
        )

        prompt = self._load_prompt("llm_critic.txt")
        prompt = prompt.format(
            question_id=question.question_id,
            title=question.title,
            difficulty=question.difficulty.value,
            scenario=question.scenario[:400],
            tested_skills=", ".join(question.tested_skills),
            confidence=getattr(conf, "confidence", 0),
            eval_match_score=eval_score,
            originality=100 - (question.similarity_score * 100),
            scope_violations=len(question.scope_violations),
            auto_gradable=question.auto_gradable,
            failed_checks=failed_checks
        )

        try:
            result, _ = self.llm.complete_json(
                system="You are a demanding senior engineer reviewing assessments.",
                user=prompt,
                temperature=0.5,
                max_tokens=800
            )

            feedback = CriticFeedback(
                issues=result.get("issues", []),
                fix_directives=result.get("fix_directives", []),
                severity=result.get("severity", "major")
            )
        except Exception:
            # Fallback to deterministic feedback
            feedback = CriticFeedback(
                issues=[
                    "Confidence score below 85",
                    "Question failed quality gates"
                ],
                fix_directives=[
                    "Review the scenario for clarity and specificity",
                    "Ensure all tested skills are actually exercised",
                    "Check that question is within syllabus scope"
                ],
                severity="major"
            )

        # Append to feedback history
        question.critic_feedback_history.append(feedback)

        return self._result(
            feedback=feedback.model_dump(),
            messages=[
                f"Issues: {len(feedback.issues)}",
                f"Severity: {feedback.severity}"
            ]
        )
