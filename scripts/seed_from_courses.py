#!/usr/bin/env python3
"""
scripts/seed_from_courses.py
============================

Seeds the few_shots SQLite table from:
  1. Built-in static course exercise index (always available)
  2. Live GitHub files for selected ROS2 examples (requires network)

Run once to pre-populate few_shots so the question generator has
high-quality reference examples from real courses from day one.

Usage:
    python scripts/seed_from_courses.py
    python scripts/seed_from_courses.py --dry-run
    python scripts/seed_from_courses.py --offline      # skip GitHub fetch
    python scripts/seed_from_courses.py --db path/to/memory.db
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from robo_assess.memory import Memory
from robo_assess.tools.course_index import COURSE_EXERCISES
from robo_assess.tools.external_search import WebSearchClient

# ---------------------------------------------------------------------------
# GitHub example files to fetch and seed as reference code
# ---------------------------------------------------------------------------

# (skill_tag, difficulty, github_raw_url, description_override)
GITHUB_EXAMPLES: list[tuple[str, str, str, str]] = [
    (
        "publisher",
        "easy",
        "https://raw.githubusercontent.com/ros2/examples/humble/rclpy/topics/minimal_publisher/examples_rclpy_minimal_publisher/publisher_member_function.py",
        "ROS2 minimal publisher — timer-driven, publishes std_msgs/String at 0.5 Hz",
    ),
    (
        "subscriber",
        "easy",
        "https://raw.githubusercontent.com/ros2/examples/humble/rclpy/topics/minimal_subscriber/examples_rclpy_minimal_subscriber/subscriber_member_function.py",
        "ROS2 minimal subscriber — callback logs received std_msgs/String messages",
    ),
    (
        "service_server",
        "easy",
        "https://raw.githubusercontent.com/ros2/examples/humble/rclpy/services/minimal_service/examples_rclpy_minimal_service/service_member_function.py",
        "ROS2 minimal service server — AddTwoInts, returns sum of a and b",
    ),
    (
        "service_client",
        "easy",
        "https://raw.githubusercontent.com/ros2/examples/humble/rclpy/services/minimal_client/examples_rclpy_minimal_client/client_member_function.py",
        "ROS2 minimal service client — calls AddTwoInts once on startup",
    ),
    (
        "action_server",
        "hard",
        "https://raw.githubusercontent.com/ros2/examples/humble/rclpy/actions/minimal_action_server/examples_rclpy_minimal_action_server/server_single_goal.py",
        "ROS2 minimal action server — single-goal Fibonacci with streaming feedback",
    ),
    (
        "action_client",
        "hard",
        "https://raw.githubusercontent.com/ros2/examples/humble/rclpy/actions/minimal_action_client/examples_rclpy_minimal_action_client/client_cancel_goal.py",
        "ROS2 minimal action client — sends goal, waits for result, handles cancel",
    ),
    (
        "executor",
        "hard",
        "https://raw.githubusercontent.com/ros2/examples/humble/rclpy/executors/examples_rclpy_executors/callback_group.py",
        "ROS2 MultiThreadedExecutor with MutuallyExclusiveCallbackGroup example",
    ),
    (
        "lifecycle",
        "hard",
        "https://raw.githubusercontent.com/ros2/demos/humble/lifecycle_py/lifecycle_py/lifecycle_talker.py",
        "ROS2 LifecycleNode — on_configure creates publisher, on_activate starts timer",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, chars: int = 2000) -> str:
    return text[:chars] if len(text) > chars else text


def _make_starter(description: str, skill: str) -> str:
    """Generate a minimal starter template from description."""
    return textwrap.dedent(f"""\
        import rclpy
        from rclpy.node import Node


        class MyNode(Node):
            def __init__(self):
                super().__init__('{skill}_node')
                # TODO START
                # Implement: {description[:120]}
                # TODO END

        def main(args=None):
            rclpy.init(args=args)
            node = MyNode()
            rclpy.spin(node)
            node.destroy_node()
            rclpy.shutdown()


        if __name__ == '__main__':
            main()
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Seed few_shots from course exercises")
    parser.add_argument("--db", default="memory/memory.db", help="Path to memory SQLite DB")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be inserted, don't write")
    parser.add_argument("--offline", action="store_true", help="Skip GitHub fetches, only use static index")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not args.dry_run:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    mem = Memory(str(db_path))
    web = WebSearchClient()

    inserted = 0
    skipped = 0

    print(f"{'[DRY-RUN] ' if args.dry_run else ''}Seeding few_shots → {db_path}\n")

    # ── 1. Static course index ────────────────────────────────────────────────
    print(f"── Static course index ({len(COURSE_EXERCISES)} exercises) ──")
    for ex in COURSE_EXERCISES:
        qid = f"course_{ex['id']}"
        skill = (ex.get("skills") or ["rclpy"])[0]
        title = ex["title"]
        description = ex["description"]
        difficulty = ex.get("difficulty", "medium")
        starter = _make_starter(description, skill.replace(" ", "_").lower())

        if args.dry_run:
            print(f"  [would insert] {qid}: {title[:60]} ({difficulty})")
            inserted += 1
            continue

        existing = dict(mem.all_stems())
        if qid in existing:
            print(f"  [skip] {qid} already seeded")
            skipped += 1
            continue

        mem.save_few_shot(
            question_id=qid,
            skill=skill,
            difficulty=difficulty,
            scenario=description,
            starter_code=starter,
            reference_code="",   # no reference for index entries
            confidence_score=85.0,
            prompt_hash=None,    # matches any prompt version
        )
        print(f"  [inserted] {qid}: {title[:60]} ({difficulty})")
        inserted += 1

    # ── 2. Live GitHub examples ───────────────────────────────────────────────
    if not args.offline:
        print(f"\n── GitHub live examples ({len(GITHUB_EXAMPLES)} files) ──")
        for skill, difficulty, url, description in GITHUB_EXAMPLES:
            qid = f"github_{skill}"

            if not args.dry_run:
                existing = dict(mem.all_stems())
                if qid in existing:
                    print(f"  [skip] {qid} already seeded")
                    skipped += 1
                    continue

            result = web.fetch_course_content(url, max_chars=3000)
            if result.get("error"):
                print(f"  [fetch-error] {qid}: {result['error']}")
                skipped += 1
                continue

            reference_code = result.get("content", "")
            starter = _make_starter(description, skill.replace("_", ""))

            if args.dry_run:
                print(f"  [would insert] {qid}: {description[:60]} ({difficulty})")
                print(f"                 fetched {result.get('length', 0)} chars from {url}")
                inserted += 1
                continue

            mem.save_few_shot(
                question_id=qid,
                skill=skill,
                difficulty=difficulty,
                scenario=description,
                starter_code=starter,
                reference_code=reference_code,
                confidence_score=95.0,   # real reference code → high confidence
                prompt_hash=None,
            )
            print(f"  [inserted] {qid}: {description[:60]}")
            print(f"             {result.get('length', 0)} chars from GitHub")
            inserted += 1

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Done: {inserted} inserted, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
