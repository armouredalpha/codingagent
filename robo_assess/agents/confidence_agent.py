"""
Agent 11 — Confidence Scoring
============================

Aggregates the upstream signals into a single 0-100 confidence using the
weighting from the spec:

    20% coverage + 20% difficulty + 15% originality +
    15% scope + 15% auto-grading + 15% format quality

A question is APPROVED when confidence > ``min_confidence`` (85 by default) and
there are no hard blockers (scope violation, not auto-gradable, duplicate).
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    try:
        return (_PROMPTS_DIR / name).read_text(encoding="utf-8")
    except OSError:
        return ""
from ..guardrails import GuardrailConfig
from ..schemas import (
    AgentResult,
    ConfidenceBreakdown,
    CoverageMatrix,
    Difficulty,
    Question,
    StudentProfile,
)
from .base import BaseAgent

_REQUIRED_FIELDS_LEGACY = (
    "title", "scenario", "objective", "expected_behaviour",
    "tested_skills", "files_to_edit", "hidden_checks", "hidden_tests",
    "common_mistakes",
)

_REQUIRED_FIELDS_NEW = (
    "title", "scenario", "objective", "tested_skills",
    "file_to_edit", "evaluation_criteria", "constraints", "common_mistakes",
)


class Calibrator:
    """Stub calibrator that returns identity mapping (raw confidence unchanged).

    Real calibration was removed; this class exists to maintain compatibility
    with the confidence_agent codebase that expects a Calibrator interface.
    """

    def __init__(self):
        self.is_calibrated = False
        self.method = "none"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Calibrator":
        """Load calibrator from file, or return identity mapping if absent."""
        return cls()

    def transform(self, raw_confidence: float) -> float:
        """Apply calibration. Identity map when not fitted."""
        return raw_confidence


def _fallback_calibrate(q: Question) -> Difficulty:
    """Rule-based difficulty estimate used only when DifficultyCalibrationAgent
    did not run (e.g. confidence scored in isolation). Kept deliberately in
    lock-step with DifficultyCalibrationAgent.calibrate so the two never
    disagree on the offline path."""
    n_skills = len(set(q.tested_skills))
    loc = sum(len(f.reference_solution.splitlines()) for f in q.files_to_edit)
    multifile = len(q.files_to_edit) > 1
    if n_skills <= 1 and loc < 35 and not multifile:
        return Difficulty.EASY
    if n_skills <= 3 and loc < 90 and not multifile:
        return Difficulty.MEDIUM
    return Difficulty.HARD


class ConfidenceScoringAgent(BaseAgent):
    name = "confidence_agent"

    _DIFF_ORDER = {Difficulty.EASY: 0, Difficulty.MEDIUM: 1, Difficulty.HARD: 2}

    @property
    def _calibrator(self) -> Calibrator:
        """Load the fitted calibrator once per agent. Absent file ⇒ identity map
        (honest: confidence stays uncalibrated until observations are fitted)."""
        cal = getattr(self, "_cal_cache", None)
        if cal is None:
            cal = Calibrator.load(getattr(self.settings, "calibrator_path",
                                          "calibration/confidence_calibrator.json"))
            self._cal_cache = cal
        return cal

    def _criteria_quality(self, q: Question) -> float:
        """Continuous quality of the machine-checkable criteria (new-style only).

        Replaces the binary auto-gradable flag's all-or-nothing contribution so
        a question with one thin criterion no longer scores identically to one
        with three well-targeted criteria summing to 100 — the main driver of the
        confidence-clustering problem. Well-formed questions return 1.0 (no
        change); legacy questions without evaluation_criteria return 1.0 so the
        legacy format path governs them unchanged."""
        ecs = q.evaluation_criteria
        if not ecs:
            return 1.0
        n = len(ecs)
        pts = sum(ec.points for ec in ecs)
        richness = min(1.0, n / 3.0)
        points_ok = 1.0 if 90 <= pts <= 110 else 0.7
        target_frac = sum(1 for ec in ecs if ec.target) / n
        return round(0.4 + 0.6 * (0.5 * richness + 0.25 * points_ok + 0.25 * target_frac), 3)

    def _difficulty_fit(self, q: Question) -> float:
        """Score how well the *declared* difficulty matches the *calibrated*
        one. Perfect fit -> 1.0, one level off -> 0.6, two levels off -> 0.2.

        If calibration never ran (calibrated_difficulty is None) we fall back to
        the rule-based estimate rather than silently awarding full marks — the
        old behaviour (constant 1.0) made 20% of every confidence score free.
        """
        calibrated = q.calibrated_difficulty or _fallback_calibrate(q)
        distance = abs(self._DIFF_ORDER[q.difficulty] - self._DIFF_ORDER[calibrated])
        # Off-by-one (e.g. easy vs medium) is a soft penalty — the boundary is
        # genuinely fuzzy. Off-by-two (easy labelled hard) is a real defect.
        return {0: 1.0, 1: 0.8}.get(distance, 0.3)

    def _format_quality(self, q: Question) -> float:
        if q.evaluation_criteria:
            # New-style: check new required fields only
            fields = _REQUIRED_FIELDS_NEW
            present = sum(1 for f in fields if getattr(q, f, None))
            return present / len(fields)
        else:
            # Legacy: check old fields + TODO markers
            present = sum(1 for f in _REQUIRED_FIELDS_LEGACY if getattr(q, f, None))
            base = present / len(_REQUIRED_FIELDS_LEGACY)
            todo_ok = all(
                f.starter_code.count("# TODO START") == f.starter_code.count("# TODO END")
                and f.starter_code.count("# TODO START") >= 1
                for f in q.files_to_edit
            )
            return base * (1.0 if todo_ok else 0.7)

    def score(self, q: Question, coverage: CoverageMatrix) -> ConfidenceBreakdown:
        gr = GuardrailConfig.load()
        w = gr.confidence.weights
        min_conf = gr.confidence.min_confidence_score

        matrix_lower = [s.lower() for s in coverage.matrix]
        skills_lower = [s.lower() for s in q.tested_skills]
        # Coverage is now proportional: what fraction of this question's tested
        # skills actually map to a syllabus skill. A question that tests one
        # on-syllabus skill and three off-syllabus ones is NOT fully covered.
        if skills_lower:
            matched = sum(
                1 for qs in skills_lower
                if any(ms in qs or qs in ms for ms in matrix_lower)
            )
            coverage_component = matched / len(skills_lower)
        else:
            coverage_component = 0.0
        difficulty_component = self._difficulty_fit(q)
        originality_component = max(0.0, 1.0 - q.similarity_score)
        scope_component = 0.0 if q.scope_violations else 1.0
        # Continuous, not binary: a gradable question with thin criteria scores
        # below one with rich, well-targeted criteria (breaks score clustering).
        grading_component = (1.0 if q.auto_gradable else 0.0) * self._criteria_quality(q)
        format_component = self._format_quality(q)

        # Use weights from guardrail_rules.yaml
        confidence = (
            w.get("coverage", 20) * coverage_component
            + w.get("difficulty", 20) * difficulty_component
            + w.get("originality", 15) * originality_component
            + w.get("scope", 15) * scope_component
            + w.get("auto_grading", 15) * grading_component
            + w.get("format_quality", 15) * format_component
        )
        raw_confidence = round(confidence, 1)
        # Map the raw heuristic through the fitted calibrator so the number is a
        # measured probability (calibrated against executed-grading outcomes),
        # not just an ordering. Identity map until a calibrator is fitted.
        cal = self._calibrator
        confidence = cal.transform(raw_confidence)

        # Hard blockers: only scope violations and non-gradable questions
        # Similarity is already factored into the originality component score
        hard_blocked = bool(q.scope_violations) or (not q.auto_gradable)
        # Near-duplicate (above threshold AND very high similarity) is still a hard block
        near_duplicate = q.similarity_score >= 0.95
        status = (
            "APPROVED"
            if confidence >= min_conf and not hard_blocked and not near_duplicate
            else "REJECTED"
        )
        return ConfidenceBreakdown(
            coverage=round(w.get("coverage", 20) * coverage_component, 1),
            difficulty=round(w.get("difficulty", 20) * difficulty_component, 1),
            originality=round(w.get("originality", 15) * originality_component, 1),
            scope=round(w.get("scope", 15) * scope_component, 1),
            auto_grading=round(w.get("auto_grading", 15) * grading_component, 1),
            format_quality=round(w.get("format_quality", 15) * format_component, 1),
            confidence=confidence,
            raw_confidence=raw_confidence,
            calibrated=cal.is_calibrated,
            status=status,
        )

    def score_with_students(
        self, q: Question, students: list[StudentProfile]
    ) -> dict:
        """Explanatory confidence signal: for each baseline student profile, ask
        the LLM whether a candidate at that level could solve this question.

        Returns ``{"per_level": {level: 0-1}, "average": 0-1, "notes": {...}}``.
        Best-effort: any LLM failure falls back to a difficulty-vs-experience
        heuristic so the signal is always present without a network dependency.
        This does NOT gate approval — the numeric gate stays with score()/the
        ImprovedConfidenceScorer; this is logged into the confidence report.
        """
        per_level: dict[str, float] = {}
        notes: dict[str, str] = {}
        for s in students:
            val: float | None = None
            try:
                template = _load_prompt("confidence_student.txt")
                prompt = template.format(
                    level=s.level,
                    ros2_experience=s.ros2_experience,
                    skills=", ".join(s.skills),
                    title=q.title,
                    difficulty=q.difficulty.value,
                    objective=q.objective,
                    tested_skills=", ".join(q.tested_skills),
                ) if template else (
                    "A student has this background:\n"
                    f"- level: {s.level}\n"
                    f"- ROS2 experience: {s.ros2_experience}\n"
                    f"- skills: {', '.join(s.skills)}\n\n"
                    "Could this student solve the following ROS2 coding question? "
                    "Estimate probability of success 0.0-1.0.\n\n"
                    f"Title: {q.title}\n"
                    f"Difficulty: {q.difficulty.value}\n"
                    f"Objective: {q.objective}\n"
                    f"Tested skills: {', '.join(q.tested_skills)}\n\n"
                    'Reply JSON only: {"probability": <0.0-1.0>, "note": "<short>"}'
                )
                result, _ = self.llm.complete_json(  # type: ignore[union-attr]
                    system="You estimate whether a student can solve a ROS2 coding question.",
                    user=prompt,
                    temperature=0.0,
                    max_tokens=120,
                )
                if isinstance(result, dict) and "probability" in result:
                    val = max(0.0, min(1.0, float(result["probability"])))
                    notes[s.level] = str(result.get("note", ""))
            except Exception as exc:  # noqa: BLE001
                self.log.debug("student_confidence_unavailable", error=str(exc))

            if val is None:
                # Heuristic fallback: higher experience vs question difficulty.
                exp_rank = {"beginner": 0, "intermediate": 1, "advanced": 2}.get(
                    s.ros2_experience, 0
                )
                diff_rank = self._DIFF_ORDER.get(q.difficulty, 1)
                val = max(0.05, min(1.0, 0.6 + 0.25 * (exp_rank - diff_rank)))
                notes.setdefault(s.level, "heuristic estimate")
            per_level[s.level] = round(val, 3)

        avg = round(sum(per_level.values()) / len(per_level), 3) if per_level else 0.0
        return {"per_level": per_level, "average": avg, "notes": notes}

    def run(self, questions: list[Question], coverage: CoverageMatrix) -> AgentResult:
        gr = GuardrailConfig.load()
        min_conf = gr.confidence.min_confidence_score
        approved = 0
        for q in questions:
            q.confidence = self.score(q, coverage)
            if q.confidence.status == "APPROVED":
                approved += 1
        self._log_calibration_observations(questions)
        res = self._result(approved=approved, total=len(questions))
        cal = self._calibrator
        tag = f"calibrated:{cal.method}" if cal.is_calibrated else "uncalibrated"
        res.messages.append(
            f"{approved}/{len(questions)} approved (confidence > {min_conf}, {tag})")
        return res.finish()

    def _log_calibration_observations(self, questions: list[Question]) -> None:
        """Append (raw_confidence, executed-grading outcome) pairs to the
        observation log. Executable grading runs *before* confidence in the
        validation chain, so its real PASS/FAIL is available here as the label
        the calibrator is later fitted against. NO_ARTIFACTS / SKIPPED carry no
        ground truth and are not logged — we never fabricate labels."""
        if not getattr(self.settings, "log_calibration_observations", True):
            return
        rows = []
        for q in questions:
            ge = q.grading_execution
            if not ge or ge.status not in ("PASS", "FAIL"):
                continue
            if not q.confidence:
                continue
            rows.append({
                "qid": q.question_id,
                "raw": q.confidence.raw_confidence,
                "label": 1 if ge.status == "PASS" else 0,
            })
        if not rows:
            return
        try:
            record_observations(
                getattr(self.settings, "calibration_observations_path",
                        "calibration/observations.jsonl"),
                rows,
            )
        except Exception as exc:  # noqa: BLE001 — logging must never break a run
            self.log.warning("calibration_log_failed", error=str(exc))
