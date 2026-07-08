"""
Agent 11 — Confidence Scoring
============================

Aggregates the upstream signals into a single 0-100 confidence score.
Weights are loaded from guardrails/guardrail_rules.yaml (confidence.weights)
and updated at runtime via EMA as grading observations accumulate.

Current defaults (guardrail_rules.yaml):
    10% coverage + 10% difficulty + 10% originality +
    60% auto_grading + 10% format_quality + 0% eval_calibration

A question is APPROVED when confidence > ``min_confidence`` (70 by default) and
there are no hard blockers (scope violation, not auto-gradable, duplicate).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..learned_confidence_improved import ImprovedConfidenceScorer

def record_observations(path: str, rows: list[dict]) -> None:
    """Append observation rows to the JSONL calibration log."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def record_instructor_feedback(
    obs_path: str,
    qid: str,
    approved: bool,
    reason: str = "",
    components: dict | None = None,
    raw_confidence: float = 0.0,
) -> None:
    """Write one instructor approval/rejection into the calibration log.

    Instructor labels are weighted 3× over auto-generated labels in the EMA
    weight update, so even a handful of reviews meaningfully shifts the
    confidence weights toward what actually matters pedagogically.
    """
    record_observations(obs_path, [{
        "qid": qid,
        "raw": raw_confidence,
        "label": 1 if approved else 0,
        "source": "instructor",
        "reason": reason,
        "components": components or {},
    }])


from ..guardrails import GuardrailConfig
from ..schemas import (
    AgentResult,
    ConfidenceBreakdown,
    CoverageMatrix,
    Difficulty,
    Question,
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

    def _eval_calibration(self, q: Question) -> float:
        """0-1 component from eval_comparator's difficulty match score.

        Returns 0.75 (neutral) when no reference set is available so questions
        are not penalised simply because the eval set is unconfigured.
        """
        ec = q.eval_comparison
        if ec is None or ec.difficulty_verdict in ("no_refs", "no_match"):
            return 0.75
        if ec.eval_match_score >= 85:
            return 1.0
        if ec.eval_match_score >= 65:
            return 0.7
        return 0.3  # "mismatch" — difficulty label likely wrong

    def score(
        self,
        q: Question,
        coverage: CoverageMatrix,
        improved_scorer: "ImprovedConfidenceScorer | None" = None,
    ) -> ConfidenceBreakdown:
        gr = GuardrailConfig.load()
        w = gr.confidence.weights
        min_conf = gr.confidence.min_confidence_score

        # Coverage: proportion of tested skills that match a syllabus skill.
        # Uses the same token-set matching as CoverageMatrixAgent.mark() to
        # avoid false positives from substring containment ("tf" in "staff").
        from .coverage_matrix import _skills_match
        syllabus_skills = list(coverage.matrix.keys())
        if q.tested_skills:
            matched = sum(
                1 for tested in q.tested_skills
                if any(_skills_match(tested, key) for key in syllabus_skills)
            )
            coverage_component = matched / len(q.tested_skills)
        else:
            coverage_component = 0.0
        difficulty_component = self._difficulty_fit(q)
        originality_component = max(0.0, 1.0 - q.similarity_score)
        # Use sandbox execution result when available; fall back to static analysis.
        # PASS  → reference passes its own tests AND starter fails → 1.0
        # FAIL  → sandbox proved tests are broken → 0.0 (hard fail)
        # SKIPPED/NO_ARTIFACTS/NOT_RUN → trust static auto_gradable flag at half weight
        ge = q.grading_execution
        if ge is not None and ge.status == "PASS":
            grading_component = 1.0
        elif ge is not None and ge.status == "FAIL":
            grading_component = 0.0
        else:
            grading_component = (0.5 if q.auto_gradable else 0.0) * self._criteria_quality(q)
        format_component = self._format_quality(q)
        eval_component = self._eval_calibration(q)

        # Use weights from guardrail_rules.yaml
        confidence = (
            w.get("coverage", 10) * coverage_component
            + w.get("difficulty", 10) * difficulty_component
            + w.get("originality", 10) * originality_component
            + w.get("auto_grading", 60) * grading_component
            + w.get("format_quality", 10) * format_component
            + w.get("eval_calibration", 0) * eval_component
        )
        raw_confidence = round(confidence, 1)

        if improved_scorer is not None:
            # Use ground-truth-calibrated scorer: pass 0-100 scaled validator
            # signals so the empirical pass-rate model can blend them.
            validators = {
                "auto_grading": grading_component * 100,
                "originality": originality_component * 100,
                "format_compliance": format_component * 100,
            }
            confidence, _ = improved_scorer.score(
                q, validators, difficulty_hint=q.difficulty.value.lower()
            )
            is_calibrated = True
            cal_method = "improved_ground_truth"
        else:
            cal = self._calibrator
            confidence = cal.transform(raw_confidence)
            is_calibrated = cal.is_calibrated
            cal_method = cal.method

        # Hard blockers: scope violations and questions that cannot be auto-graded.
        # If sandbox ran and PASSED, trust it over the static auto_gradable flag.
        sandbox_passed = ge is not None and ge.status == "PASS"
        sandbox_failed = ge is not None and ge.status == "FAIL"
        not_gradable = sandbox_failed or (not sandbox_passed and not q.auto_gradable)
        hard_blocked = bool(q.scope_violations) or not_gradable
        # Near-duplicate (above threshold AND very high similarity) is still a hard block
        near_duplicate = q.similarity_score >= 0.95

        # Human-approved questions bypass the confidence threshold but never
        # bypass hard blockers (scope violations / non-gradable are still fatal).
        if getattr(q, "human_decision", "") == "approve" and not hard_blocked and not near_duplicate:
            status = "APPROVED"
        else:
            status = (
                "APPROVED"
                if confidence >= min_conf and not hard_blocked and not near_duplicate
                else "REJECTED"
            )
        return ConfidenceBreakdown(
            coverage=round(w.get("coverage", 10) * coverage_component, 1),
            difficulty=round(w.get("difficulty", 10) * difficulty_component, 1),
            originality=round(w.get("originality", 10) * originality_component, 1),
            auto_grading=round(w.get("auto_grading", 60) * grading_component, 1),
            format_quality=round(w.get("format_quality", 10) * format_component, 1),
            eval_calibration=round(w.get("eval_calibration", 0) * eval_component, 1),
            confidence=confidence,
            raw_confidence=raw_confidence,
            calibrated=is_calibrated,
            status=status,
        )


    def run(
        self,
        questions: list[Question],
        coverage: CoverageMatrix,
        improved_scorer: "ImprovedConfidenceScorer | None" = None,
    ) -> AgentResult:
        gr = GuardrailConfig.load()
        min_conf = gr.confidence.min_confidence_score
        approved = 0
        for q in questions:
            q.confidence = self.score(q, coverage, improved_scorer=improved_scorer)
            if q.confidence.status == "APPROVED":
                approved += 1
        self._log_calibration_observations(questions)
        res = self._result(approved=approved, total=len(questions))
        if improved_scorer is not None:
            tag = "calibrated:improved_ground_truth"
        else:
            cal = self._calibrator
            tag = f"calibrated:{cal.method}" if cal.is_calibrated else "uncalibrated"
        res.messages.append(
            f"{approved}/{len(questions)} approved (confidence > {min_conf}, {tag})")
        return res.finish()

    def _log_calibration_observations(self, questions: list[Question]) -> None:
        """Append (raw_confidence, executed-grading outcome) pairs to the
        observation log, then recompute weights via EMA if enough data exists.

        Executable grading runs *before* confidence in the validation chain,
        so its real PASS/FAIL is available here as the label. NO_ARTIFACTS /
        SKIPPED carry no ground truth and are not logged."""
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
                "source": "executable_grading",
                "components": {
                    "coverage": q.confidence.coverage,
                    "difficulty": q.confidence.difficulty,
                    "originality": q.confidence.originality,
                    "auto_grading": q.confidence.auto_grading,
                    "format_quality": q.confidence.format_quality,
                },
            })
        if not rows:
            return
        obs_path = getattr(
            self.settings, "calibration_observations_path",
            "calibration/observations.jsonl",
        )
        try:
            record_observations(obs_path, rows)
        except Exception as exc:  # noqa: BLE001
            self.log.warning("calibration_log_failed", error=str(exc))
            return

        # After logging, try to recompute weights from all observations via EMA.
        # Minimum 20 labelled observations before touching weights.
        try:
            self._ema_update_weights(obs_path)
        except Exception as exc:  # noqa: BLE001
            self.log.debug("calibration_ema_skipped", error=str(exc))

    _EMA_ALPHA = 0.1          # smoothing factor: 0.1 → slow, stable adaptation
    _MIN_OBS_FOR_EMA = 20     # don't update weights with fewer observations
    _MIN_WEIGHT = 5           # floor so no signal becomes irrelevant

    def _ema_update_weights(self, obs_path: str) -> None:
        """Read the full observation log and update confidence weights via EMA.

        For each component, computes the mean component score separately for
        PASS (label=1) and FAIL (label=0) questions. Components with a larger
        PASS–FAIL gap are more predictive and get proportionally more weight.
        The new weights are blended into the guardrail YAML via EMA so a single
        bad batch can't swing weights dramatically.
        """
        p = Path(obs_path)
        if not p.exists():
            return

        observations = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        if len(observations) < self._MIN_OBS_FOR_EMA:
            return

        component_keys = ["coverage", "difficulty", "originality",
                          "auto_grading", "format_quality"]

        # Instructor labels are pedagogically authoritative — weight them 3×
        # over auto-generated executable_grading labels so a handful of reviews
        # outweighs a large volume of synthetic AST-based signals.
        _INSTRUCTOR_WEIGHT = 3
        weighted: list[dict] = []
        for o in observations:
            if not o.get("components"):
                continue
            weight = _INSTRUCTOR_WEIGHT if o.get("source") == "instructor" else 1
            weighted.extend([o] * weight)

        # Separate PASS / FAIL pools from the weighted set
        pass_obs = [o for o in weighted if o.get("label") == 1]
        fail_obs = [o for o in weighted if o.get("label") == 0]
        if not pass_obs or not fail_obs:
            return

        def mean_component(pool: list[dict], key: str) -> float:
            vals = [o["components"].get(key, 0.0) for o in pool]
            return sum(vals) / len(vals) if vals else 0.0

        # Discriminative power = |pass_mean - fail_mean| for each component
        discriminative = {
            k: abs(mean_component(pass_obs, k) - mean_component(fail_obs, k))
            for k in component_keys
        }
        total_disc = sum(discriminative.values()) or 1.0

        # Convert to weights that sum to 100, respecting the floor
        raw_new = {k: max(self._MIN_WEIGHT, round(v / total_disc * 100)) for k, v in discriminative.items()}
        # Re-normalise to exactly 100 after floor clamping
        total_raw = sum(raw_new.values())
        scale = 100 / total_raw
        new_weights = {k: max(self._MIN_WEIGHT, round(v * scale)) for k, v in raw_new.items()}
        # Fix any rounding residual on the largest component
        diff = 100 - sum(new_weights.values())
        if diff:
            largest = max(new_weights, key=new_weights.get)
            new_weights[largest] += diff

        # EMA blend with current guardrail weights
        gr = GuardrailConfig.load()
        current = gr.confidence.weights
        alpha = self._EMA_ALPHA
        blended = {
            k: round((1 - alpha) * current.get(k, 100 // len(component_keys)) + alpha * new_weights[k])
            for k in component_keys
        }
        # Persist blended weights back to guardrail_rules.yaml and clear the
        # lru_cache so the next GuardrailConfig.load() reads the new values.
        try:
            import yaml as _yaml
            from .. import guardrails as _gr_module
            rules_path = Path(getattr(self.settings, "guardrails_dir", "guardrails")) / "guardrail_rules.yaml"
            if rules_path.exists():
                data = _yaml.safe_load(rules_path.read_text()) or {}
                data.setdefault("confidence", {})["weights"] = blended
                rules_path.write_text(_yaml.dump(data, default_flow_style=False, sort_keys=False))
                _gr_module._load_cached.cache_clear()
                self.log.info(
                    "confidence_weights_updated",
                    n_obs=len(observations),
                    new_weights=blended,
                )
        except Exception as exc:  # noqa: BLE001
            self.log.warning("confidence_weights_save_failed", error=str(exc))
