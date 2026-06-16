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
from pathlib import Path

from .config import Settings
from .agents.orchestrator import Orchestrator
from .workflows.assessment_workflow import export_run_v2


def generate_command(args) -> int:
    """Summarise → extract skills → pick 3 → generate/validate/score → export YAML."""
    md_path = Path(args.md)

    if not md_path.exists():
        print(f"ERROR: Markdown file not found: {md_path}", file=sys.stderr)
        return 1

    settings = Settings.load(args.config)
    orchestrator = Orchestrator(settings=settings)

    print(f"Generating assessment from {md_path} ...")
    try:
        pkg = orchestrator.run_generate_v2(md_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    try:
        approved = pkg.approved_questions
        print("\n" + "=" * 70)
        print(f"  ASSESSMENT GENERATED — run {pkg.run_id}")
        print("=" * 70)
        print(f"  Questions        : {len(pkg.questions)} generated, "
              f"{len(approved)} approved")
        print(f"  Coverage         : {pkg.coverage_matrix.coverage_pct:.0f}%")
        print(f"  Supervisor       : {pkg.supervisor.supervisor_status} "
              f"(validation {pkg.supervisor.validation_score}/100)")
        if pkg.supervisor.issues:
            print("  Supervisor notes :")
            for issue in pkg.supervisor.issues:
                print(f"      - {issue}")
        print("=" * 70)

        out_dir = export_run_v2(
            pkg,
            summary_text=getattr(pkg, "_summary_text", ""),
            skillset=getattr(pkg, "_skillset", None),
            out_root=settings.outputs_dir,
        )
        print(f"  Output: {out_dir}")

        return 0 if pkg.supervisor.supervisor_status == "APPROVED" else 2

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def runs_command(args) -> int:
    """List recent runs."""
    settings = Settings.load(args.config)
    from .logging_utils import RunLogger
    logger = RunLogger(settings.log_db_path)
    runs = logger.recent_runs(limit=10)

    if not runs:
        print("No recent runs found.")
        return 0

    print("Recent runs:")
    for run in runs:
        print(f"  {run['run_id']:<12} | {run['topic']:<40} | "
              f"{run['supervisor']:<10} | {run['num_questions']:>2} questions")
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

    parser.add_argument("--config", default="config.yaml",
                        help="Config file (default: config.yaml)")

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
    gen_parser.set_defaults(func=generate_command)

    # Runs command
    runs_parser = subparsers.add_parser("runs", help="List recent runs")
    runs_parser.set_defaults(func=runs_command)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
