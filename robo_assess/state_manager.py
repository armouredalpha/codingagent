"""
State Manager: Save/load generation state for resumability and learned confidence.

Tables:
- generation_runs: track overall run status
- generation_state: checkpoints after each step
- question_scores: confidence breakdowns
- reference_scores: reference question calibration data
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class StateManager:
    """Persistent state store for generation runs."""

    def __init__(self, db_path: str = "logs/state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Create tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS generation_runs (
                run_id TEXT PRIMARY KEY,
                md_file TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT DEFAULT 'in_progress',
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT,
                num_questions INT
            );

            CREATE TABLE IF NOT EXISTS generation_state (
                run_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, step_name),
                FOREIGN KEY (run_id) REFERENCES generation_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS question_scores (
                run_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                raw_confidence FLOAT,
                final_confidence FLOAT,
                coverage_score FLOAT,
                difficulty_score FLOAT,
                originality_score FLOAT,
                scope_score FLOAT,
                auto_grading_score FLOAT,
                format_score FLOAT,
                similar_ref_ids TEXT,
                features_json TEXT,
                PRIMARY KEY (run_id, question_id),
                FOREIGN KEY (run_id) REFERENCES generation_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS reference_scores (
                ref_id TEXT PRIMARY KEY,
                title TEXT,
                difficulty TEXT,
                scenario TEXT,
                skills TEXT,
                quality_score FLOAT,
                expected_pass_rate FLOAT,
                num_tests_passed INT,
                num_tests_total INT,
                created_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_generation_state_run_id ON generation_state(run_id);
            CREATE INDEX IF NOT EXISTS idx_question_scores_run_id ON question_scores(run_id);
        """)
        self.conn.commit()

    def start_run(
        self, run_id: str, md_file: str, mode: str, num_questions: int
    ) -> None:
        """Record the start of a generation run."""
        self.conn.execute(
            """INSERT INTO generation_runs (run_id, md_file, mode, started_at, num_questions)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, md_file, mode, datetime.now().isoformat(), num_questions),
        )
        self.conn.commit()

    def save_state(self, run_id: str, step_name: str, state: dict[str, Any]) -> None:
        """Save state checkpoint after a step."""
        self.conn.execute(
            """INSERT OR REPLACE INTO generation_state (run_id, step_name, state_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (run_id, step_name, json.dumps(state), datetime.now().isoformat()),
        )
        self.conn.commit()

    def load_state(self, run_id: str, step_name: str) -> Optional[dict[str, Any]]:
        """Load state from a checkpoint."""
        result = self.conn.execute(
            """SELECT state_json FROM generation_state
               WHERE run_id = ? AND step_name = ?""",
            (run_id, step_name),
        ).fetchone()
        return json.loads(result[0]) if result else None

    def get_last_completed_step(self, run_id: str) -> Optional[str]:
        """Find the last successfully completed step for resumption."""
        result = self.conn.execute(
            """SELECT step_name FROM generation_state
               WHERE run_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (run_id,),
        ).fetchone()
        return result[0] if result else None

    def save_question_scores(
        self,
        run_id: str,
        question_id: str,
        confidence: float,
        breakdown: dict[str, float],
        similar_refs: list[str],
        features: dict[str, Any],
    ) -> None:
        """Save confidence breakdown for a question."""
        self.conn.execute(
            """INSERT OR REPLACE INTO question_scores
               (run_id, question_id, raw_confidence, final_confidence,
                coverage_score, difficulty_score, originality_score, scope_score,
                auto_grading_score, format_score, similar_ref_ids, features_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                question_id,
                breakdown.get("raw_confidence", 0),
                confidence,
                breakdown.get("coverage", 0),
                breakdown.get("difficulty", 0),
                breakdown.get("originality", 0),
                breakdown.get("scope", 0),
                breakdown.get("auto_grading", 0),
                breakdown.get("format", 0),
                json.dumps(similar_refs),
                json.dumps(features),
            ),
        )
        self.conn.commit()

    def load_reference_scores(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Load all reference question scores for confidence calibration."""
        results = self.conn.execute(
            """SELECT ref_id, title, difficulty, scenario, skills, quality_score,
                      expected_pass_rate, num_tests_passed, num_tests_total
               FROM reference_scores"""
        ).fetchall()

        references = {}
        for (
            ref_id,
            title,
            difficulty,
            scenario,
            skills,
            quality_score,
            expected_pass_rate,
            num_tests_passed,
            num_tests_total,
        ) in results:
            references[ref_id] = {
                "id": ref_id,
                "title": title,
                "difficulty": difficulty,
                "scenario": scenario,
                "skills": json.loads(skills) if isinstance(skills, str) else skills,
                "quality_score": quality_score,
                "expected_pass_rate": expected_pass_rate,
                "num_tests_passed": num_tests_passed,
                "num_tests_total": num_tests_total,
            }

        return references

    def upsert_reference_scores(
        self, ref_id: str, ref_data: dict[str, Any]
    ) -> None:
        """Insert or update a reference question score."""
        self.conn.execute(
            """INSERT OR REPLACE INTO reference_scores
               (ref_id, title, difficulty, scenario, skills, quality_score,
                expected_pass_rate, num_tests_passed, num_tests_total, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ref_id,
                ref_data.get("title"),
                ref_data.get("difficulty"),
                ref_data.get("scenario"),
                json.dumps(ref_data.get("skills", [])),
                ref_data.get("quality_score", 0),
                ref_data.get("expected_pass_rate", 0),
                ref_data.get("num_tests_passed", 0),
                ref_data.get("num_tests_total", 0),
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        """Mark a run as completed or failed."""
        self.conn.execute(
            """UPDATE generation_runs SET status = ?, completed_at = ?
               WHERE run_id = ?""",
            (status, datetime.now().isoformat(), run_id),
        )
        self.conn.commit()

    def fail_run(self, run_id: str, error_message: str) -> None:
        """Mark a run as failed with error message."""
        self.conn.execute(
            """UPDATE generation_runs SET status = ?, completed_at = ?, error_message = ?
               WHERE run_id = ?""",
            ("failed", datetime.now().isoformat(), error_message, run_id),
        )
        self.conn.commit()

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent generation runs."""
        results = self.conn.execute(
            """SELECT run_id, md_file, mode, status, started_at, completed_at, num_questions
               FROM generation_runs
               ORDER BY started_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

        return [
            {
                "run_id": r[0],
                "md_file": r[1],
                "mode": r[2],
                "status": r[3],
                "started_at": r[4],
                "completed_at": r[5],
                "num_questions": r[6],
            }
            for r in results
        ]

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
