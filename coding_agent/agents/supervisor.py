"""
Supervisor Agent
================

Final audit only — everything upstream (difficulty/originality validators,
PlannerAgent's per-question quality-bar loop) has already scored and decided
which questions to keep or regenerate by the time this runs. The Supervisor
does not re-run any of those checks; it performs ONE pass over the finished
package: syllabus coverage against target, at least one approved question,
structural completeness (evaluation_criteria present), and overall batch
score. No package ships unless the Supervisor approves it.

Also owns eval-bank comparison (``compare_to_eval_bank``, formerly a separate
EvalComparatorAgent): scoring a question's difficulty against the closest
matches in evaluations/question.json+solution.json is itself a supervisory
judgment — "does this look like what a real reviewer would call {difficulty}"
— so it lives here rather than as its own pipeline stage. It still runs
per-question during validation (before confidence scoring, which reads its
result), not as part of the final batch audit.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas import (
    AgentResult, AssessmentPackage, EvalComparison, EvalReference, Question,
    SupervisorVerdict,
)
from ..vectorstore import text_similarity
from ._llm_batch import run_batched_critic
from .base import BaseAgent

def _load_judge_system() -> str:
    """Load supervisor judge prompt from file, fall back to inline."""
    path = Path(__file__).parent.parent.parent / "prompts" / "supervisor_judge.txt"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return (
            "You are an INDEPENDENT senior robotics hiring reviewer. You did not write "
            "these questions. For each one, judge ONLY from the artifact whether it is a "
            "realistic, correctly-scoped, unambiguous, auto-gradable ROS2 Humble coding "
            "ticket whose stated criteria actually match the task. Be skeptical. Return "
            'ONLY JSON: {"results":[{"id": "...", "verdict": "APPROVE"|"REJECT", '
            '"reasons": ["..."]}]} — reasons required when REJECT.'
        )


_JUDGE_SYSTEM = _load_judge_system()


def _valid_judge_verdict(v: dict) -> bool:
    return str(v.get("verdict", "")).upper() in ("APPROVE", "REJECT")


class SupervisorAgent(BaseAgent):
    name = "supervisor"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.eval_refs: list[EvalReference] = []
        self._load_eval_sets()

    # ------------------------------------------------------------------ #
    # Eval-bank comparison (formerly EvalComparatorAgent) — runs per-question
    # during validation, not part of the final-audit pass below.
    # ------------------------------------------------------------------ #

    def _load_eval_sets(self) -> None:
        """Load reference questions and solutions from evaluations/ folder."""
        evals_dir = Path(self.settings.evaluations_dir)

        questions_file = evals_dir / "question.json"
        if not questions_file.exists():
            self.log.warning("eval_sets_missing", file=str(questions_file))
            return

        try:
            questions_data = json.loads(questions_file.read_text())
            if not isinstance(questions_data, list):
                questions_data = [questions_data]
        except (json.JSONDecodeError, IOError):
            self.log.warning("eval_sets_load_error", file=str(questions_file))
            return

        solutions_data = {}
        solutions_file = evals_dir / "solution.json"
        if solutions_file.exists():
            try:
                sol_data = json.loads(solutions_file.read_text())
                if isinstance(sol_data, list):
                    solutions_data = {item.get("id"): item for item in sol_data}
                else:
                    solutions_data = sol_data
            except (json.JSONDecodeError, IOError):
                pass

        for q in questions_data:
            sol = solutions_data.get(q.get("id"), {})
            ref = EvalReference(
                id=q.get("id", "unknown"),
                title=q.get("title", ""),
                difficulty=q.get("difficulty", "medium"),
                scenario=q.get("scenario", ""),
                skills=q.get("skills", []),
                solution_summary=sol.get("solution_summary", ""),
            )
            self.eval_refs.append(ref)

        self.log.info("eval_sets_loaded", count=len(self.eval_refs))

    # Minimum similarity for a reference to be considered relevant.
    # Below this the topics are too different for difficulty comparison to mean anything.
    _MIN_SIM = 0.15

    def _find_closest_refs(self, question: Question, top_k: int = 3) -> list[tuple[str, float]]:
        """Return top-k (ref_id, similarity) pairs above _MIN_SIM threshold."""
        if not self.eval_refs:
            return []

        q_text = f"{question.title} {question.scenario} {' '.join(question.tested_skills)}"
        ref_texts = [f"{r.title} {r.scenario} {' '.join(r.skills)}" for r in self.eval_refs]
        scored = [
            (ref.id, text_similarity(q_text, ref_text))
            for ref, ref_text in zip(self.eval_refs, ref_texts)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        relevant = [(rid, sim) for rid, sim in scored if sim >= self._MIN_SIM]
        return relevant[:top_k]

    def _score_difficulty_match(
        self, question: Question, closest: list[tuple[str, float]]
    ) -> float | None:
        """Score difficulty match against closest refs.

        Skips LLM and returns None when no relevant references exist — the caller
        treats None as 'no_match' and does not penalise confidence.
        When refs exist, uses similarity-weighted difficulty comparison (no LLM call).
        """
        if not closest:
            return None

        _TIER = {"easy": 1, "medium": 2, "hard": 3}
        q_tier = _TIER.get(question.difficulty.value, 2)

        weighted_score = 0.0
        total_weight = 0.0
        for ref_id, sim in closest:
            ref = next((r for r in self.eval_refs if r.id == ref_id), None)
            if not ref:
                continue
            ref_tier = _TIER.get(str(ref.difficulty).lower(), 2)
            tier_diff = abs(q_tier - ref_tier)
            tier_score = [100.0, 60.0, 20.0][min(tier_diff, 2)]
            weighted_score += tier_score * sim
            total_weight += sim

        if total_weight == 0:
            return None
        return round(weighted_score / total_weight, 1)

    def compare_to_eval_bank(self, question: Question) -> AgentResult:
        """Compare question against eval set and score difficulty match.
        Sets ``question.eval_comparison``, read later by confidence scoring
        and by this class's own ``_question_problems`` final audit."""
        if not self.eval_refs:
            comparison = EvalComparison(
                eval_match_score=0.0,
                closest_refs=[],
                difficulty_verdict="no_refs",
                style_notes="No eval references loaded; skipping comparison.",
            )
            question.eval_comparison = comparison
            return self._result(
                comparison=comparison.model_dump(),
                messages=["eval bank comparison skipped: no reference set configured"],
            ).finish("skip")

        closest = self._find_closest_refs(question)
        closest_ids = [ref_id for ref_id, _ in closest]
        eval_match_score = self._score_difficulty_match(question, closest)

        if eval_match_score is None:
            difficulty_verdict = "no_match"
            style_notes = "No similar references in eval set — difficulty score not penalised."
            eval_match_score = 75.0
        elif eval_match_score >= 85:
            difficulty_verdict = question.difficulty.value
            style_notes = f"Match quality: {eval_match_score}/100"
        elif eval_match_score >= 65:
            difficulty_verdict = "uncertain"
            style_notes = f"Match quality: {eval_match_score}/100 — possible tier mismatch"
        else:
            difficulty_verdict = "mismatch"
            style_notes = f"Match quality: {eval_match_score}/100 — difficulty likely wrong"

        comparison = EvalComparison(
            eval_match_score=eval_match_score,
            closest_refs=closest_ids,
            difficulty_verdict=difficulty_verdict,
            style_notes=style_notes,
        )
        question.eval_comparison = comparison

        return self._result(
            comparison=comparison.model_dump(),
            messages=[
                f"Difficulty match: {eval_match_score}/100 ({difficulty_verdict})",
                f"Closest refs: {', '.join(f'{r}({s:.2f})' for r, s in closest)}",
            ],
        )

    # ------------------------------------------------------------------ #
    # Final-audit pass — runs once, on the assembled package.
    # ------------------------------------------------------------------ #

    def _llm_judge(self, pkg: AssessmentPackage) -> dict[str, dict]:
        """Independent per-question LLM verdicts, keyed by question_id. Empty when
        the judge is disabled, unavailable, or fails — the rule-based supervisor
        remains authoritative and the judge can only ADD rejections.

        This is the POST-LOOP supervisor judge, controlled by ``enable_llm_judge``
        in config (default: False). It is separate from the IN-LOOP PlannerAgent
        judge which is controlled by ``quality_bar.require_judge_approve``.
        """
        if not getattr(self.settings, "enable_llm_judge", False) or self.llm is None:
            return {}
        payload = [
            {
                "id": q.question_id,
                "title": q.title,
                "scenario": q.scenario,
                "objective": q.objective,
                "constraints": q.constraints,
                "tested_skills": q.tested_skills,
                "evaluation_criteria": [c.model_dump() for c in q.evaluation_criteria],
                "difficulty": q.difficulty.value,
            }
            for q in pkg.questions
        ]
        template = '{"questions": __Q__}'.replace("__Q__", "{questions}")
        return run_batched_critic(
            llm=self.llm, system=_JUDGE_SYSTEM, template=template, payload=payload,
            settings=self.settings, validate=_valid_judge_verdict,
            agent_name=self.name, log=self.log,
        )

    def _question_problems(self, q: Question) -> list[str]:
        """Final-audit-only per-question defects — concerns not already decided
        by an upstream validator or the PlannerAgent quality-bar loop. Returned
        as human-readable feedback strings that are both logged as issues and
        injected into targeted regeneration."""
        probs: list[str] = []
        if not q.evaluation_criteria:
            probs.append(
                "not auto-gradable; evaluation_criteria list is empty — generate "
                "one criterion per task as a JSON array with id/check/target/points/description "
                "fields, 10 points per task (e.g. 3 tasks -> 3 criteria totaling 30 points)"
            )
        # Eval-comparator difficulty mismatch — soft signal, not a hard block.
        ec = q.eval_comparison
        if ec and ec.difficulty_verdict == "mismatch":
            probs.append(
                f"difficulty label likely wrong (eval match {ec.eval_match_score}/100 against "
                f"reference set); reconsider whether this is '{q.difficulty.value}' or an adjacent tier"
            )
        return probs

    def validate(self, pkg: AssessmentPackage, evaluation_score: float) -> SupervisorVerdict:
        issues: list[str] = []
        failing_ids: list[str] = []
        feedback: dict[str, str] = {}

        if not pkg.questions:
            issues.append("no questions generated")

        # Coverage gate — the configured target is capped by what is physically
        # achievable: n questions can test at most n distinct skills, so we never
        # penalise a small batch for not covering a large syllabus.
        base_target = self.settings.coverage_target
        total_skills = len(pkg.coverage_matrix.matrix)
        n_questions = len(pkg.questions)
        max_achievable = (n_questions / total_skills) if total_skills else 1.0
        target = min(base_target, max_achievable)
        covered = total_skills - len(pkg.coverage_matrix.missing)
        coverage_frac = (covered / total_skills) if total_skills else 0.0
        if covered == 0:
            issues.append("no syllabus skills covered at all")
        elif coverage_frac < target * 0.5:
            # Only hard-block when coverage is critically low (< half of target).
            # Moderate shortfalls (e.g. 60% vs 85% target) are reported in the
            # portfolio_missing_areas field but do not reject the whole batch —
            # confidence scoring already penalises per-question coverage gaps,
            # and a few approved questions are more valuable than zero.
            issues.append(
                f"coverage critically low: {coverage_frac:.0%} "
                f"(target {target:.0%}, {covered}/{total_skills} skills tested)"
            )
        elif coverage_frac < target:
            self.log.info(
                "coverage_below_target",
                coverage_pct=round(coverage_frac * 100),
                target_pct=round(target * 100),
                covered=covered,
                total=total_skills,
            )

        approved = pkg.approved_questions
        if not approved:
            issues.append("no question reached APPROVED confidence")

        judge = self._llm_judge(pkg)

        for q in pkg.questions:
            probs = self._question_problems(q)
            # Independent LLM judge: a REJECT is treated as a defect that routes
            # the question to regeneration, and (if it was approved) raises a
            # batch-level issue — a second, prompt-independent opinion.
            jv = judge.get(q.question_id)
            if jv and str(jv.get("verdict", "")).upper() == "REJECT":
                jr = "; ".join(str(r) for r in jv.get("reasons", [])) or "independent judge rejected"
                probs.append(f"independent judge REJECT: {jr}")
                if q.approved:
                    issues.append(f"{q.question_id}: approved but independent judge rejected — {jr}")
            # An approved question carrying a hard defect is a batch-level issue.
            if q.approved:
                for p in probs:
                    if p.startswith("not auto-gradable"):
                        issues.append(f"{q.question_id}: approved despite — {p}")
            # Any non-approved or defective question is a regeneration target.
            if not q.approved or probs:
                failing_ids.append(q.question_id)
                reason = probs or ["below approval confidence; strengthen scenario, "
                                   "criteria and difficulty fit"]
                feedback[q.question_id] = "; ".join(reason)

        min_score = self.settings.supervisor_min_validation_score
        pass_rate = len(approved) / len(pkg.questions) if pkg.questions else 0.0
        score = round(0.6 * evaluation_score + 40 * pass_rate)
        status = "APPROVED" if not issues and score >= min_score else "REJECTED"
        return SupervisorVerdict(
            supervisor_status=status, validation_score=int(score), issues=issues,
            failing_question_ids=sorted(set(failing_ids)), question_feedback=feedback,
        )

    def run(self, pkg: AssessmentPackage, evaluation_score: float) -> AgentResult:
        verdict = self.validate(pkg, evaluation_score)
        res = self._result(verdict=verdict.model_dump())
        res.messages.append(
            f"{verdict.supervisor_status} (score {verdict.validation_score}, "
            f"{len(verdict.issues)} issues)"
        )
        return res.finish("ok" if verdict.supervisor_status == "APPROVED" else "fail")
