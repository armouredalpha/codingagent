#!/usr/bin/env python3
"""
scripts/seed_few_shots.py
=========================

Bootstrap the few_shots table in memory.db by scanning existing question
output directories.  Run this once after first setup or after a batch of
manual exports so the question generator can use proven examples immediately.

Usage
-----
  python scripts/seed_few_shots.py
  python scripts/seed_few_shots.py --outputs-dir outputs --config config/config.yaml
  python scripts/seed_few_shots.py --dry-run

What it reads
-------------
For each outputs/<run>/questions/Q*/ directory it reads:
  - question.yaml  → skill, difficulty, question_id, full question JSON
  - boilerplate/*.py  → starter_code (first .py file found, or "")
  - solution.yaml → reference_code from files[0].content (or "")

It inserts into few_shots with:
  confidence_score = 90.0 (default "approved" grade for manual examples)
  prompt_hash      = NULL  (matches any prompt version — stable examples)

Duplicates (same question_id already in the DB) are silently skipped.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"  [WARN] Cannot parse {path}: {exc}")
        return {}


def _read_starter_code(q_dir: Path) -> str:
    bp_dir = q_dir / "boilerplate"
    if not bp_dir.is_dir():
        return ""
    for py in sorted(bp_dir.glob("*.py")):
        try:
            return py.read_text(encoding="utf-8")
        except OSError:
            pass
    return ""


def _read_reference_code(q_dir: Path) -> str:
    sol_file = q_dir / "solution.yaml"
    if not sol_file.exists():
        return ""
    data = _load_yaml(sol_file)
    files = data.get("files", [])
    if files and isinstance(files[0], dict):
        return files[0].get("content", "")
    return ""


def _existing_qids(db_path: str) -> set[str]:
    """Return set of question_ids already present in few_shots.json field."""
    try:
        with closing(sqlite3.connect(db_path)) as con:
            rows = con.execute("SELECT question_json FROM few_shots").fetchall()
        ids: set[str] = set()
        for (raw,) in rows:
            try:
                d = json.loads(raw)
                qid = d.get("question_id", "")
                if qid:
                    ids.add(qid)
            except Exception:
                pass
        return ids
    except sqlite3.OperationalError:
        return set()


def _insert(db_path: str, entries: list[dict], dry_run: bool) -> None:
    if dry_run:
        return
    ts = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(db_path)) as con:
        for e in entries:
            con.execute(
                """
                INSERT INTO few_shots
                    (skill, difficulty, confidence_score, question_json,
                     starter_code, reference_code, prompt_hash, ts)
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    e["skill"], e["difficulty"], 90.0,
                    e["question_json"], e["starter_code"], e["reference_code"],
                    ts,
                ),
            )
        con.commit()


def seed(outputs_dir: str, db_path: str, dry_run: bool = False) -> int:
    outputs = Path(outputs_dir)
    if not outputs.is_dir():
        print(f"ERROR: outputs directory not found: {outputs}", file=sys.stderr)
        return 1

    # Ensure DB + table exists by initialising Memory
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from robo_assess.memory import Memory
    Memory(db_path)  # creates tables/migrations

    already_in_db = _existing_qids(db_path)
    print(f"DB: {db_path}  ({len(already_in_db)} questions already seeded)")

    q_dirs = sorted(outputs.glob("*/questions/Q*"))
    print(f"Found {len(q_dirs)} question director{'ies' if len(q_dirs) != 1 else 'y'} under {outputs}")

    inserted = skipped_dup = skipped_err = 0
    batch: list[dict] = []

    for q_dir in q_dirs:
        # Handle both directory-per-question (new) and single .json file (legacy) layouts
        if q_dir.suffix == ".json" and q_dir.is_file():
            try:
                data = json.loads(q_dir.read_text(encoding="utf-8"))
            except Exception:
                skipped_err += 1
                continue
            q_dir = q_dir.parent  # parent for boilerplate/solution lookups (won't exist)
        elif q_dir.is_dir():
            q_file = q_dir / "question.yaml"
            if not q_file.exists():
                skipped_err += 1
                continue
            data = _load_yaml(q_file)
        else:
            skipped_err += 1
            continue
        qid = data.get("question_id", "") or q_dir.name
        # New schema: "skill" field; legacy schema: "tested_skills" list
        skill = (
            data.get("skill")
            or (data.get("tested_skills") or [None])[0]
            or ""
        )
        difficulty = str(data.get("difficulty", "medium")).lower()

        if not skill:
            print(f"  [SKIP] {q_dir.name} — no skill field")
            skipped_err += 1
            continue

        if qid in already_in_db:
            skipped_dup += 1
            continue

        # Starter: boilerplate/ dir (new) or boilerplate_code field (legacy)
        starter = _read_starter_code(q_dir) or data.get("boilerplate_code", "") or ""
        reference = _read_reference_code(q_dir)
        q_json = json.dumps(data, default=str)

        batch.append({
            "skill": skill,
            "difficulty": difficulty,
            "question_json": q_json,
            "starter_code": starter,
            "reference_code": reference,
        })
        already_in_db.add(qid)
        inserted += 1

        tag = "[DRY-RUN] " if dry_run else ""
        print(f"  {tag}+ {qid} ({difficulty}) — {skill[:55]}")

    if batch:
        _insert(db_path, batch, dry_run)

    print(f"\n{'DRY-RUN — ' if dry_run else ''}Done: {inserted} inserted, "
          f"{skipped_dup} already present, {skipped_err} skipped (errors)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed few_shots DB from existing outputs/")
    ap.add_argument("--outputs-dir", default="outputs",
                    help="Root outputs directory to scan (default: outputs)")
    ap.add_argument("--config", default="config/config.yaml",
                    help="Config file to locate memory_db_path (default: config/config.yaml)")
    ap.add_argument("--db", default=None,
                    help="Override memory.db path (default: from config)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be inserted without writing to DB")
    args = ap.parse_args()

    db_path = args.db
    if not db_path:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from robo_assess.config import Settings
            settings = Settings.load(args.config)
            db_path = settings.memory_db_path
        except Exception:
            db_path = "memory/memory.db"

    return seed(args.outputs_dir, db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
