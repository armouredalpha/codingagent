"""
HumanReviewAgent
================

Surfaces borderline questions (confidence in [min, max]) to a human reviewer
instead of auto-approving or auto-rejecting them.

Three modes (set via Settings.human_review_mode):

  "log"   — Write borderline questions to pending_review.json and continue the
             run. Borderline questions are treated as approved for this run.

  "block" — Write pending_review.json, save already-approved questions to a
             checkpoint, then RAISE HumanReviewRequired. The CLI catches this
             and exits with code 2. On the next run, approved questions are
             restored from the checkpoint so only borderline ones are retried.

  "defer" — Mark borderline questions as DEFERRED and continue. They are
             excluded from the final package but written to pending_review.json
             so a human can decide offline. No pipeline interruption.

On the NEXT run (resume), ``run()`` automatically loads prior decisions from the
review file and applies them to questions before surfacing new borderlines:
  - "approve" → ``q.human_decision = "approve"``; confidence gate is bypassed
  - "reject"  → ``q.human_decision = "reject"``; ``q.auto_gradable = False``

Human review is skipped entirely when:
  - human_review_enabled = False (default)
  - No questions fall in the borderline confidence range (and no prior decisions)
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas import AgentResult, Question
from .base import BaseAgent


class HumanReviewRequired(Exception):
    """Raised in 'block' mode when borderline items need human attention."""
    def __init__(self, review_file: str, count: int) -> None:
        super().__init__(
            f"\n{'='*60}\n"
            f"  HUMAN REVIEW REQUIRED — {count} borderline question(s)\n"
            f"  Review file: {review_file}\n"
            f"  Edit 'decision' field: 'approve' | 'reject'\n"
            f"  Then re-run with the same --md flag to resume.\n"
            f"{'='*60}"
        )
        self.review_file = review_file
        self.count = count


class HumanReviewAgent(BaseAgent):
    name = "human_review"

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def run(
        self,
        questions: list[Question],
        run_id: str,
        outputs_dir: str = "outputs",
    ) -> AgentResult:
        """Apply prior human decisions, then identify new borderline questions.

        On a fresh run: writes borderline items to pending_review.json.
        On a resumed run: loads decisions from the prior file and applies them
        before checking for any remaining borderlines.

        Returns an AgentResult. In 'block' mode, raises HumanReviewRequired
        when new borderline items are found.
        """
        if not getattr(self.settings, "human_review_enabled", False):
            res = self._result()
            res.messages.append("human review disabled — skipped")
            return res.finish("ok")

        conf_min = getattr(self.settings, "human_review_confidence_min", 82.0)
        conf_max = getattr(self.settings, "human_review_confidence_max", 87.0)
        mode = getattr(self.settings, "human_review_mode", "log")

        # Apply any decisions from a prior review pass
        prior_decisions = self.load_decisions(run_id, outputs_dir)
        applied = self._apply_decisions(questions, prior_decisions)

        # Find questions still in the borderline zone (no prior decision)
        borderline = []
        for q in questions:
            if q.human_decision:
                continue  # already decided
            conf = q.confidence.confidence if q.confidence else 0.0
            if conf_min <= conf <= conf_max:
                borderline.append({
                    "question_id": q.question_id,
                    "title": q.title,
                    "difficulty": (
                        q.difficulty.value
                        if hasattr(q.difficulty, "value")
                        else str(q.difficulty)
                    ),
                    "confidence": round(conf, 1),
                    "tested_skills": q.tested_skills[:3],
                    "decision": "pending",   # human fills in: "approve" | "reject"
                })

        messages: list[str] = []
        if applied:
            messages.append(
                f"applied {len(applied)} prior human decision(s): "
                + ", ".join(f"{qid}={dec}" for qid, dec in applied.items())
            )

        if not borderline:
            res = self._result(
                borderline_count=0,
                applied_decisions=applied,
            )
            res.messages.extend(messages or ["human review: no borderline items"])
            return res.finish("ok")

        # Write (or overwrite) the review file with the new borderline items
        review_path = Path(outputs_dir) / run_id / "pending_review.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)

        # Merge: keep already-decided items in the file alongside new ones
        existing_decided = [
            {"question_id": qid, "decision": dec}
            for qid, dec in prior_decisions.items()
        ]
        review_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "items": borderline,
                    "previously_decided": existing_decided,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        self.log.info(
            "human_review_borderline",
            count=len(borderline),
            file=str(review_path),
            mode=mode,
        )

        messages.append(
            f"human review: {len(borderline)} borderline item(s) written to {review_path}"
        )

        if mode == "block":
            # Save already-approved questions to a checkpoint before halting so
            # the next run can restore them without re-running the full pipeline.
            self._save_checkpoint(questions, borderline, run_id, outputs_dir)
            raise HumanReviewRequired(str(review_path), len(borderline))

        if mode == "defer":
            # Mark borderline questions as deferred and exclude them from the
            # final package — pipeline continues without interruption.
            borderline_ids = {item["question_id"] for item in borderline}
            for q in questions:
                if q.question_id in borderline_ids:
                    q.human_decision = "deferred"
                    q.auto_gradable = False  # excluded from package by Supervisor
            res = self._result(
                borderline_count=len(borderline),
                deferred_ids=list(borderline_ids),
                review_file=str(review_path),
                applied_decisions=applied,
            )
            res.messages.extend(messages)
            res.messages.append(
                f"defer mode: {len(borderline)} question(s) excluded pending review"
            )
            return res.finish("warn")

        # "log" mode — continue normally; borderline questions remain in-flight
        res = self._result(
            borderline_count=len(borderline),
            review_file=str(review_path),
            applied_decisions=applied,
        )
        res.messages.extend(messages)
        res.messages.append("continuing run (log mode)")
        return res.finish("warn")

    def load_decisions(self, run_id: str, outputs_dir: str = "outputs") -> dict[str, str]:
        """Load human decisions from a prior review file.

        Returns {question_id: decision} where decision is 'approve' or 'reject'.
        Returns empty dict if no review file exists or no decisions are filled in.
        """
        review_path = Path(outputs_dir) / run_id / "pending_review.json"
        if not review_path.exists():
            return {}
        try:
            data = json.loads(review_path.read_text(encoding="utf-8"))
            return {
                item["question_id"]: item["decision"]
                for item in data.get("items", [])
                if item.get("decision") in ("approve", "reject")
            }
        except Exception as exc:  # noqa: BLE001
            self.log.warning("human_review_load_failed", error=str(exc))
            return {}

    def load_checkpoint(self, run_id: str, outputs_dir: str = "outputs") -> list[dict]:
        """Return approved question payloads saved by a prior block-mode halt.

        The orchestrator can call this on resume to restore already-approved
        questions without re-running the full pipeline for them.
        """
        checkpoint_path = Path(outputs_dir) / run_id / "approved_checkpoint.json"
        if not checkpoint_path.exists():
            return []
        try:
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            return data.get("approved_questions", [])
        except Exception as exc:  # noqa: BLE001
            self.log.warning("human_review_checkpoint_load_failed", error=str(exc))
            return []

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _save_checkpoint(
        self,
        questions: list[Question],
        borderline: list[dict],
        run_id: str,
        outputs_dir: str,
    ) -> None:
        """Persist already-approved questions before halting in block mode.

        Only questions that are NOT in the borderline set and have auto_gradable=True
        (i.e. the pipeline already accepted them) are saved. This lets the next run
        skip re-generating them.
        """
        borderline_ids = {item["question_id"] for item in borderline}
        approved = [
            q.model_dump()
            for q in questions
            if q.question_id not in borderline_ids and q.auto_gradable
        ]
        checkpoint_path = Path(outputs_dir) / run_id / "approved_checkpoint.json"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(
            json.dumps({"run_id": run_id, "approved_questions": approved}, indent=2),
            encoding="utf-8",
        )
        self.log.info(
            "human_review_checkpoint_saved",
            approved_count=len(approved),
            path=str(checkpoint_path),
        )

    def _apply_decisions(
        self,
        questions: list[Question],
        decisions: dict[str, str],
    ) -> dict[str, str]:
        """Apply {question_id: decision} back onto Question objects in place.

        Returns the subset of decisions that were actually applied (i.e. matched
        a question in the current run).
        """
        if not decisions:
            return {}

        by_id = {q.question_id: q for q in questions}
        applied: dict[str, str] = {}

        for qid, decision in decisions.items():
            q = by_id.get(qid)
            if q is None:
                self.log.warning("human_review_unknown_id", question_id=qid)
                continue

            q.human_decision = decision

            if decision == "reject":
                # Mark as non-gradable so downstream gates (Supervisor, Planner)
                # treat it as a failure and trigger regeneration.
                q.auto_gradable = False
                self.log.info(
                    "human_review_applied_reject",
                    question_id=qid,
                )
            elif decision == "approve":
                # Approved by human — no further automated gates should block it.
                # Leave confidence/gradable flags intact; downstream agents check
                # human_decision and bypass the confidence threshold when set.
                self.log.info(
                    "human_review_applied_approve",
                    question_id=qid,
                )

            applied[qid] = decision

        return applied
