"""
robo_assess.cli
===============

Two-command CLI:
  robo-assess parse --md <teaching_material.md>
  robo-assess generate --md <teaching_material.md> --num <N>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Settings
from .agents.orchestrator import Orchestrator
from .workflows.assessment_workflow import export_package


def parse_command(args) -> int:
    """Parse a markdown file and extract skills to skills/skills.yaml."""
    md_path = Path(args.md)

    if not md_path.exists():
        print(f"ERROR: Markdown file not found: {md_path}", file=sys.stderr)
        return 1

    print(f"Parsing {md_path}...")
    settings = Settings.load(args.config)
    orchestrator = Orchestrator(settings=settings)

    try:
        result = orchestrator.run_parse(md_path)
        print(f"✓ Extracted {len(result.skills)} skills from {result.total_sections} sections")
        print(f"  Coverage: {len(result.sections_covered)}/{result.total_sections} sections have skills")
        print(f"  Written to: {settings.skills_dir}/skills.yaml")
        return 0
    except Exception as e:
        import traceback
        print(f"ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


def generate_command(args) -> int:
    """Generate questions from a markdown file with optional constraints."""
    md_path = Path(args.md)

    if not md_path.exists():
        print(f"ERROR: Markdown file not found: {md_path}", file=sys.stderr)
        return 1

    settings = Settings.load(args.config)

    # Check that skills have been extracted from the same .md
    skills_dir = Path(settings.skills_dir)
    if not (skills_dir / "meta.yaml").exists():
        print(
            f"ERROR: Skills not extracted. Run:\n"
            f"  robo-assess parse --md {md_path}",
            file=sys.stderr
        )
        return 1

    import yaml
    meta = yaml.safe_load((skills_dir / "meta.yaml").read_text())
    if meta.get("md_file") != md_path.name:
        print(
            f"ERROR: Skills were extracted from {meta.get('md_file')}, not {md_path.name}.\n"
            f"Run: robo-assess parse --md {md_path}",
            file=sys.stderr
        )
        return 1

    # Determine generation mode
    orchestrator = Orchestrator(settings=settings)

    if args.auto:
        msg = "AUTO MODE: Generating 3 questions (easy, medium, hard)"
        print(f"{msg} from {md_path}...")
        try:
            pkg = orchestrator.run_generate(
                md_path,
                auto=True,
                domain=args.domain or ""
            )
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    elif args.difficulty and args.bloom_level:
        num = args.num or 1
        constraints = [
            {
                "difficulty": args.difficulty,
                "bloom_level": args.bloom_level,
                "domain": args.domain or ""
            }
            for _ in range(num)
        ]
        msg = f"MANUAL MODE: Generating {num} {args.difficulty}/{args.bloom_level} questions"
        print(f"{msg} from {md_path}...")
        try:
            pkg = orchestrator.run_generate(md_path, constraints=constraints)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    else:
        msg = f"RANDOM MODE: Generating {args.num} random questions"
        print(f"{msg} from {md_path}...")
        try:
            pkg = orchestrator.run_generate(md_path, num_questions=args.num)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    try:

        # Print summary
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

        # Export
        out_dir = export_package(pkg, settings.outputs_dir)
        print(f"  Output: {out_dir}")

        # Exit code: 0 if approved, 2 if rejected
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
  robo-assess parse --md teaching_material.md
  robo-assess generate --md teaching_material.md --num 5
  robo-assess runs
        """
    )

    parser.add_argument("--config", default="config.yaml",
                        help="Config file (default: config.yaml)")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse .md and extract skills")
    parse_parser.add_argument("--md", required=True, help="Markdown file path")
    parse_parser.set_defaults(func=parse_command)

    # Generate command
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate questions from .md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODES:
  Auto mode (simplest):
    robo-assess generate --md file.md --auto
    → Generates 3 questions: 1 easy, 1 medium, 1 hard

  Manual mode (user-specified):
    robo-assess generate --md file.md --difficulty easy --bloom-level apply --num 1
    → Generates N questions matching your constraints

  Random mode:
    robo-assess generate --md file.md --num 5
    → Generates 5 random-difficulty questions
        """
    )
    gen_parser.add_argument("--md", required=True, help="Markdown file path")
    gen_parser.add_argument(
        "--auto",
        action="store_true",
        help="AUTO MODE: Generate 3 questions (easy, medium, hard) automatically"
    )
    gen_parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        help="MANUAL MODE: Target difficulty"
    )
    gen_parser.add_argument(
        "--bloom-level",
        choices=["understand", "apply", "analyze", "evaluate", "create"],
        help="MANUAL MODE: Target Bloom level"
    )
    gen_parser.add_argument(
        "--num",
        type=int,
        default=6,
        help="RANDOM/MANUAL MODE: Number of questions"
    )
    gen_parser.add_argument(
        "--domain",
        help="Optional domain hint (warehouse, inspection, simulation, etc) for all modes"
    )
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
