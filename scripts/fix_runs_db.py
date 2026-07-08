"""
Fix logs/runs.db:
  1. Add cost_usd and duration_seconds columns (if missing)
  2. Backfill cost/duration from run_metadata.json files and usage_history.jsonl
  3. Remove incomplete runs (NULL finished_at or n_questions) — these are
     abandoned/crashed runs that never finished and pollute KPI totals

Usage:
  python scripts/fix_runs_db.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DB_PATH = REPO_ROOT / "logs" / "runs.db"
OUTPUTS_DIR = REPO_ROOT / "outputs"


def collect_cost_map() -> dict[str, dict]:
    """Build run_id → {cost_usd, duration_seconds} from all available sources."""
    data: dict[str, dict] = {}

    # Priority 1: run_metadata.json files (most complete)
    for f in OUTPUTS_DIR.rglob("run_metadata.json"):
        try:
            m = json.loads(f.read_text())
            rid = m.get("run_id")
            if not rid:
                continue
            cost = m.get("token_usage", {}).get("estimated_cost_usd") or 0.0
            dur = m.get("duration_seconds") or 0.0
            data.setdefault(rid, {})
            data[rid]["cost_usd"] = cost
            data[rid]["duration_seconds"] = dur
        except Exception as e:
            print(f"  WARN: could not parse {f}: {e}", file=sys.stderr)

    # Priority 2: usage_history.jsonl (fills gaps)
    hist_path = OUTPUTS_DIR / "usage_history.jsonl"
    if hist_path.exists():
        for line in hist_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                rid = r.get("run_id")
                if not rid:
                    continue
                data.setdefault(rid, {})
                if "cost_usd" not in data[rid]:
                    data[rid]["cost_usd"] = r.get("estimated_cost_usd") or 0.0
                if "duration_seconds" not in data[rid]:
                    data[rid]["duration_seconds"] = r.get("duration_seconds") or 0.0
            except Exception as e:
                print(f"  WARN: bad usage_history line: {e}", file=sys.stderr)

    return data


def fix_db(dry_run: bool = False) -> None:
    if not DB_PATH.exists():
        sys.exit(f"ERROR: DB not found at {DB_PATH}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # ── 1. Add missing columns ────────────────────────────────────────────────
    existing_cols = {r[1] for r in cur.execute("PRAGMA table_info(runs)")}
    for col, typedef in [("cost_usd", "REAL"), ("duration_seconds", "REAL")]:
        if col not in existing_cols:
            print(f"  Adding column: {col} {typedef}")
            if not dry_run:
                cur.execute(f"ALTER TABLE runs ADD COLUMN {col} {typedef}")

    # ── 2. Remove incomplete runs ─────────────────────────────────────────────
    cur.execute(
        "SELECT run_id FROM runs WHERE finished_at IS NULL OR n_questions IS NULL"
    )
    incomplete = [r[0] for r in cur.fetchall()]
    print(f"\n  Incomplete runs to remove: {len(incomplete)}")
    for rid in incomplete:
        print(f"    {rid}")
    if not dry_run and incomplete:
        cur.executemany(
            "DELETE FROM runs WHERE run_id = ?", [(r,) for r in incomplete]
        )
        # Also clean up orphaned events
        cur.executemany(
            "DELETE FROM events WHERE run_id = ?", [(r,) for r in incomplete]
        )

    # ── 3. Backfill cost + duration ───────────────────────────────────────────
    cost_map = collect_cost_map()
    print(f"\n  Cost data found for {len(cost_map)} runs")

    # Re-check which columns exist now (columns may have just been added above)
    existing_cols_now = {r[1] for r in cur.execute("PRAGMA table_info(runs)")}
    cost_col = "cost_usd" if "cost_usd" in existing_cols_now else "NULL"
    dur_col = "duration_seconds" if "duration_seconds" in existing_cols_now else "NULL"
    cur.execute(f"SELECT run_id, {cost_col}, {dur_col} FROM runs")
    rows = cur.fetchall()
    updated = 0
    for run_id, existing_cost, existing_dur in rows:
        info = cost_map.get(run_id)
        if not info:
            continue
        new_cost = info.get("cost_usd", 0.0)
        new_dur = info.get("duration_seconds", 0.0)
        if existing_cost != new_cost or existing_dur != new_dur:
            print(f"    {run_id}: cost {existing_cost} → {new_cost:.4f}, dur {existing_dur} → {new_dur:.1f}s")
            if not dry_run:
                cur.execute(
                    "UPDATE runs SET cost_usd = ?, duration_seconds = ? WHERE run_id = ?",
                    (new_cost, new_dur, run_id),
                )
            updated += 1

    if not dry_run:
        con.commit()

    # ── 4. Print final summary ────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM runs")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM runs WHERE finished_at IS NOT NULL")
    complete = cur.fetchone()[0]
    cur.execute("SELECT SUM(n_questions), SUM(n_approved) FROM runs")
    nq, na = cur.fetchone()
    if "cost_usd" in {r[1] for r in cur.execute("PRAGMA table_info(runs)")}:
        cur.execute("SELECT AVG(cost_usd) FROM runs WHERE cost_usd IS NOT NULL AND cost_usd > 0")
        avg_cost = cur.fetchone()[0] or 0.0
    else:
        avg_cost = 0.0

    con.close()

    print(f"\n{'[DRY RUN] ' if dry_run else ''}DB after fix:")
    print(f"  Total runs:       {total}")
    print(f"  Complete runs:    {complete}")
    print(f"  Total questions:  {nq}")
    print(f"  Total approved:   {na}")
    print(f"  Rows updated:     {updated}")
    print(f"  Avg cost/run:     ${avg_cost:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    fix_db(dry_run=args.dry_run)
