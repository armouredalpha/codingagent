"""
robo_assess.cli
===============

Single-command CLI (supervisor-orchestrated v2 flow):
  robo-assess generate --md <teaching_material.md>
  robo-assess runs
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import Settings
from .agents.orchestrator import Orchestrator
from .workflows.assessment_workflow import export_run_v2


def _print_run_summary(pkg, loop_num: int) -> None:
    approved = pkg.approved_questions
    print("\n" + "=" * 70)
    print(f"  LOOP {loop_num} — run {pkg.run_id}")
    print("=" * 70)
    print(f"  Questions  : {len(pkg.questions)} generated, {len(approved)} approved, "
          f"{len(pkg.questions) - len(approved)} rejected")
    print(f"  Coverage   : {pkg.coverage_matrix.coverage_pct:.0f}%")
    print(f"  Supervisor : {pkg.supervisor.supervisor_status} "
          f"(validation {pkg.supervisor.validation_score}/100)")
    if pkg.supervisor.issues:
        for issue in pkg.supervisor.issues:
            print(f"             - {issue}")
    print("=" * 70)


def _prompt_continue(pkg, loop: int, next_loop: int) -> bool:
    """Show rejection details and ask the user whether to run another loop.

    Returns True if the user wants to continue, False to abort.
    """
    sv = pkg.supervisor
    print(f"\n{'─'*70}")
    print(f"  Supervisor REJECTED — reasons:")
    for issue in (sv.issues or ["(no specific issues recorded)"]):
        print(f"    ✗ {issue}")

    feedback = getattr(sv, "question_feedback", {}) or {}
    if feedback:
        print(f"\n  Per-question feedback (first 3):")
        for qid, fb in list(feedback.items())[:3]:
            print(f"    [{qid}] {fb[:120]}")

    print(f"{'─'*70}")
    try:
        ans = input(
            f"\n  Run loop {next_loop}? Costs ~$0.50–$1.50. [y/N]: "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Aborted.")
        return False
    return ans in ("y", "yes")


def generate_command(args) -> int:
    """Generate → validate → if rejected, loop and keep generating.

    Approved questions accumulate in outputs/<run>/questions/.
    Rejected questions from each loop go to outputs/<run>/rejected/.
    Loops until the supervisor approves OR --max-loops is exhausted.
    Pass --yes to skip the between-loop confirmation prompt (CI mode).
    Pass --json-events to emit NDJSON pipeline events (suppresses all print output).
    """
    import json as _json

    md_path = Path(args.md)
    if not md_path.exists():
        print(f"ERROR: Markdown file not found: {md_path}", file=sys.stderr)
        return 1

    settings = Settings.load(args.config)
    if getattr(args, "human_review", False):
        settings = settings.model_copy(update={"human_review_enabled": True})

    json_events = getattr(args, 'json_events', False)

    def emit(obj: dict) -> None:
        if json_events:
            print(_json.dumps(obj), flush=True)

    emit({'event': 'run_start', 'run_id': 'pending', 'topic': md_path.stem.replace('_', ' ').title()})

    orchestrator = Orchestrator(settings=settings)

    _current_loop: list[int] = [1]

    def _on_skills_extracted(skill_count: int) -> None:
        emit({'event': 'stage_done', 'stage': 'skill_extraction', 'skill_count': skill_count})
        emit({'event': 'stage_start', 'stage': 'generate', 'loop': _current_loop[0], 'target': settings.num_questions})

    orchestrator.on_skills_extracted = _on_skills_extracted
    max_loops = getattr(args, "max_loops", 3)
    auto_yes = getattr(args, "yes", False)

    resume_id = getattr(args, "resume", None)
    if resume_id:
        if not json_events:
            print(f"Resuming run {resume_id} from last checkpoint ...")

    _t0 = time.time()
    out_dir = None
    total_approved = 0
    total_rejected = 0
    pkg = None
    out_dir = None

    for loop in range(1, max_loops + 1):
        if not json_events:
            print(f"\n{'─'*70}")
            print(f"  Generation loop {loop}/{max_loops} — {md_path.name}")
            print(f"{'─'*70}")

        try:
            _current_loop[0] = loop
            emit({'event': 'stage_start', 'stage': 'md_summary'})
            emit({'event': 'stage_start', 'stage': 'skill_extraction', 'skill_count': 0})
            # stage_start: generate is emitted by _on_skills_extracted callback after skill count is known
            pkg = orchestrator.run_from_md(md_path, run_id=(resume_id if loop == 1 else None))
            resume_id = None  # only apply resume on first loop
            emit({
                'event': 'stage_done', 'stage': 'supervisor',
                'verdict': pkg.supervisor.supervisor_status,
                'score': pkg.supervisor.validation_score,
                'tokens_in': 0, 'tokens_out': 0, 'cost': 0.0
            })
            # Emit accepted question events
            for i, q in enumerate(pkg.approved_questions):
                qid = getattr(q, 'question_id', f'Q{i+1:03d}')
                title = getattr(q, 'title', getattr(q, 'question_id', f'Question {i+1}'))
                difficulty = getattr(q, 'difficulty', 'medium')
                _cb = getattr(q, 'confidence', None)
                confidence = _cb.confidence if _cb else 85.0
                emit({
                    'event': 'question_accepted',
                    'question_id': qid,
                    'title': str(title)[:80],
                    'difficulty': str(difficulty),
                    'confidence': float(confidence),
                    'total_accepted': i + 1,
                })
            # Emit rejected question events
            rejected = [q for q in pkg.questions if q not in pkg.approved_questions]
            for q in rejected:
                qid = getattr(q, 'question_id', 'unknown')
                title = getattr(q, 'title', getattr(q, 'question_id', 'unknown'))
                emit({
                    'event': 'question_rejected',
                    'question_id': str(qid),
                    'title': str(title)[:80],
                    'failure_class': getattr(q, 'failure_reason', 'low_confidence'),
                    'issues': [],
                })
        except Exception as e:
            emit({'event': 'error', 'stage': 'generate', 'message': str(e), 'retryable': False})
            if not json_events:
                print(f"ERROR in loop {loop}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
            break

        if not json_events:
            _print_run_summary(pkg, loop)

        n_approved = len(pkg.approved_questions)
        n_rejected = len(pkg.questions) - n_approved
        total_approved += n_approved
        total_rejected += n_rejected

        try:
            out_dir = export_run_v2(
                pkg,
                summary_text=getattr(pkg, "_summary_text", ""),
                skillset=getattr(pkg, "_skillset", None),
                out_root=settings.outputs_dir,
                duration_seconds=time.time() - _t0,
                loop_num=loop,
            )
            if not json_events:
                print(f"  Output: {out_dir}")
        except Exception as e:
            if not json_events:
                print(f"ERROR exporting loop {loop}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()

        counter = getattr(pkg, "_token_counter", None)
        if counter is not None and not json_events:
            counter.print_summary()

        cost_usd = getattr(counter, 'total_cost', 0.0) if counter else 0.0
        n_approved = len(pkg.approved_questions)
        n_questions = len(pkg.questions)
        emit({
            'event': 'run_complete',
            'run_id': pkg.run_id,
            'topic': md_path.stem.replace('_', ' ').title(),
            'loop': loop,
            'generated': n_questions,
            'approved': n_approved,
            'rejected': n_questions - n_approved,
            'coverage_pct': float(getattr(pkg.coverage_matrix, 'coverage_pct', 0.0)),
            'supervisor_verdict': pkg.supervisor.supervisor_status,
            'supervisor_score': pkg.supervisor.validation_score,
            'cost_usd': cost_usd,
            'cost_breakdown': {},
            'output_dir': str(out_dir) if out_dir else '',
        })

        if pkg.supervisor.supervisor_status == "APPROVED":
            if not json_events:
                print(f"\n✓ Supervisor APPROVED after loop {loop}. Done.")
            break

        if loop < max_loops:
            if auto_yes or json_events:
                if not json_events:
                    print(f"\n  → {n_rejected} question(s) rejected. Starting loop {loop + 1} ...")
            else:
                if not _prompt_continue(pkg, loop, loop + 1):
                    print("\n  Stopped after loop {loop}. "
                          "Re-run with --yes to skip this prompt.")
                    break
                print(f"\n  Starting loop {loop + 1} ...")

    if not json_events:
        print(f"\n{'='*70}")
        print(f"  FINAL SUMMARY — {loop} loop(s) run")
        print(f"  Total approved : {total_approved}")
        print(f"  Total rejected : {total_rejected}")
        if out_dir:
            print(f"  Last output    : {out_dir}")
        print(f"{'='*70}")

    if pkg is None:
        return 1  # failed before any package was produced
    return 0 if pkg.supervisor.supervisor_status == "APPROVED" else 2


def runs_command(args) -> int:
    """List recent runs from the run logger."""
    settings = Settings.load(args.config)
    from .logging_utils import RunLogger

    logger = RunLogger(settings.log_db_path)
    runs = logger.recent_runs(limit=20)

    if not runs:
        print("No recent runs found.")
        return 0

    print("Recent runs (most recent first):")
    print(f"  {'run_id':<12} | {'topic':<38} | {'supervisor':<10} | questions")
    print(f"  {'-'*12}-+-{'-'*38}-+-{'-'*10}-+----------")
    for run in runs:
        print(f"  {run['run_id']:<12} | {str(run['topic'])[:38]:<38} | "
              f"{str(run.get('supervisor','?')):<10} | {run.get('num_questions', '?'):>2}")
    print(f"\n  Resume a run with: robo-assess generate --md <file> --resume <run_id>")
    return 0


def review_command(args) -> int:
    """Interactive instructor review — approve/reject questions and record feedback.

    Each decision is written to calibration/observations.jsonl with
    source=instructor so the confidence EMA update weights it 3× over
    auto-generated executable_grading labels.
    """
    import yaml

    settings = Settings.load(args.config)
    obs_path = getattr(settings, "calibration_observations_path",
                       "calibration/observations.jsonl")

    from .agents.confidence_agent import record_instructor_feedback

    out_dir = Path(args.output_dir)
    if not out_dir.exists():
        print(f"ERROR: Output directory not found: {out_dir}", file=sys.stderr)
        return 1

    q_root = out_dir / "questions"
    question_dirs = sorted(q_root.glob("Q*")) if q_root.exists() else []
    if not question_dirs:
        print(f"No question directories found under {q_root}", file=sys.stderr)
        return 1

    print(f"\nReviewing {len(question_dirs)} question(s) from: {out_dir.name}")
    print(f"Feedback will be written to: {obs_path}")
    print("=" * 70)

    reviewed = approved_count = 0
    for q_dir in question_dirs:
        q_file = q_dir / "question.yaml"
        if not q_file.exists():
            continue

        try:
            data = yaml.safe_load(q_file.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            print(f"  [SKIP] Cannot read {q_file}: {exc}")
            continue

        qid = data.get("question_id", q_dir.name)
        title = data.get("title", "(untitled)")
        difficulty = str(data.get("difficulty", "?")).upper()
        objective = str(data.get("objective", "")).strip()

        print(f"\n{'─'*70}")
        print(f"  [{difficulty}] {title}")
        print(f"  ID: {qid}")
        if objective:
            print(f"  Objective: {objective[:240]}")
        print(f"  Path: {q_file}")

        while True:
            try:
                ans = input("\n  Approve? [y/n/s(kip)/q(uit)]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  Aborted.")
                return 0
            if ans in ("y", "yes", "n", "no", "s", "skip", "q", "quit"):
                break
            print("  Please enter y, n, s, or q.")

        if ans in ("q", "quit"):
            print("\n  Review stopped early.")
            break
        if ans in ("s", "skip"):
            print("  Skipped.")
            continue

        approved = ans in ("y", "yes")
        reason = ""
        if not approved:
            try:
                reason = input("  Reason (optional, Enter to skip): ").strip()
            except (EOFError, KeyboardInterrupt):
                pass

        record_instructor_feedback(
            obs_path=obs_path,
            qid=qid,
            approved=approved,
            reason=reason,
        )
        verdict = "APPROVED" if approved else "REJECTED"
        print(f"  → {verdict} recorded.")
        reviewed += 1
        if approved:
            approved_count += 1

    print(f"\n{'='*70}")
    print(f"  Reviewed: {reviewed}  |  Approved: {approved_count}  |  "
          f"Rejected: {reviewed - approved_count}")
    print(f"  Observations written to: {obs_path}")
    return 0


def record_attempt_command(args) -> int:
    """Record a student attempt outcome for a specific question.

    Persists the result in memory.db so ImprovedConfidenceScorer can
    recalibrate difficulty_multipliers from real pass/fail data over time.
    """
    if args.passed is None:
        print("ERROR: specify --passed or --no-passed", file=sys.stderr)
        return 1

    settings = Settings.load(args.config)
    from .memory import Memory

    mem = Memory(settings.memory_db_path)
    mem.record_attempt(
        qid=args.qid,
        difficulty=args.difficulty,
        passed=args.passed,
        time_minutes=args.time_minutes,
        notes=args.notes or "",
    )
    verdict = "PASSED" if args.passed else "FAILED"
    print(f"Recorded: [{verdict}] {args.qid} ({args.difficulty})"
          + (f" — {args.time_minutes:.1f} min" if args.time_minutes else ""))

    # Show updated pass rates for this difficulty
    rates = mem.get_difficulty_pass_rates()
    if args.difficulty in rates:
        b = rates[args.difficulty]
        pct = 100 * b["passed"] / b["total"]
        print(f"  {args.difficulty}: {b['passed']}/{b['total']} passed ({pct:.0f}%) overall")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Robotics Assessment Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  robo-assess generate --md teaching_material.md
  robo-assess runs
        """
    )

    parser.add_argument("--config", default="config/config.yaml",
                        help="Config file (default: config/config.yaml)")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command — single supervisor-orchestrated flow
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate an assessment (3 questions: easy/medium/hard) from a .md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The generate command runs end-to-end:
  summarise the markdown → extract skills from the summary →
  pick 3 skills (easy/medium/hard) → generate + validate + score each
  question (with reject/regenerate retries) → write YAML question.yaml +
  solution.yaml per question into a date-stamped run folder with boilerplate
  and grading artefacts.
        """
    )
    gen_parser.add_argument("--md", required=True, help="Markdown file path")
    gen_parser.add_argument(
        "--resume", metavar="RUN_ID",
        help="Resume a previously failed/incomplete run by its run_id "
             "(see: robo-assess runs)",
    )
    gen_parser.add_argument(
        "--max-loops", type=int, default=3, metavar="N",
        help="Max generation loops before stopping (default: 3). "
             "Each loop generates fresh questions; rejected ones are saved to rejected/.",
    )
    gen_parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip the between-loop confirmation prompt (CI / non-interactive mode).",
    )
    gen_parser.add_argument(
        "--human-review", action="store_true",
        help=(
            "Enable mid-run human review for borderline questions (confidence 82–87%%). "
            "Writes pending_review.json; mode is controlled by human_review_mode in config "
            "(log/defer/block). Post-run review: use 'robo-assess review <output_dir>'."
        ),
    )
    gen_parser.add_argument(
        '--json-events', action='store_true',
        help='Emit NDJSON pipeline events to stdout (for GUI sidecar). Suppresses all print() output.',
    )
    gen_parser.set_defaults(func=generate_command)

    # Runs command
    runs_parser = subparsers.add_parser("runs", help="List recent runs")
    runs_parser.set_defaults(func=runs_command)

    # Review command — interactive instructor approval
    review_parser = subparsers.add_parser(
        "review",
        help="Interactively review generated questions and record instructor feedback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Reads questions from a previous run's output directory and records each
instructor approve/reject into calibration/observations.jsonl.  Even 20
labelled examples meaningfully improve confidence weight calibration.

Example:
  robo-assess review outputs/2026-06-28_10-30-00_ros2_nodes/
        """,
    )
    review_parser.add_argument(
        "output_dir",
        help="Path to a run output directory (e.g. outputs/2026-06-28_...)",
    )
    review_parser.set_defaults(func=review_command)

    # Record-attempt command — student outcome tracking
    rec_parser = subparsers.add_parser(
        "record-attempt",
        help="Record a student pass/fail attempt for a question",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Records one student attempt into memory.db.  Accumulate ≥5 attempts per
difficulty to unlock live recalibration of confidence multipliers.

Examples:
  robo-assess record-attempt --qid Q001 --passed --difficulty easy --time-minutes 8
  robo-assess record-attempt --qid Q003 --no-passed --difficulty hard --notes "forgot to spin"
        """,
    )
    rec_parser.add_argument("--qid", required=True, help="Question ID (e.g. Q001)")
    rec_parser.add_argument(
        "--passed", dest="passed", action="store_true", default=None,
        help="Student passed the question",
    )
    rec_parser.add_argument(
        "--no-passed", dest="passed", action="store_false",
        help="Student failed the question",
    )
    rec_parser.add_argument(
        "--difficulty", required=True, choices=["easy", "medium", "hard"],
        help="Question difficulty",
    )
    rec_parser.add_argument(
        "--time-minutes", type=float, default=None, metavar="MINS",
        help="How long the student spent (optional)",
    )
    rec_parser.add_argument("--notes", default="", help="Optional free-text notes")
    rec_parser.set_defaults(func=record_attempt_command)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
