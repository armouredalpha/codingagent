"""
robo_assess.memory
==================

A small SQLite-backed memory layer.

It serves two purposes:

* **Analyzer cache** — syllabus parses are deterministic and reusable, so we
  key them by a hash of the topic+syllabus and avoid recomputation (and, in
  LLM mode, repeated token spend).
* **Question memory** — every approved question stem is remembered so the
  Originality Agent can compare future generations against historical output.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def syllabus_key(topic: str, syllabus: list[str]) -> str:
    raw = topic.strip().lower() + "::" + "|".join(sorted(s.lower() for s in syllabus))
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class Memory:
    def __init__(self, db_path: str = "memory/memory.db") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    key  TEXT PRIMARY KEY,
                    json TEXT,
                    ts   TEXT
                );
                CREATE TABLE IF NOT EXISTS questions (
                    qid   TEXT PRIMARY KEY,
                    topic TEXT,
                    stem  TEXT,
                    ts    TEXT
                );
                CREATE TABLE IF NOT EXISTS few_shots (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill            TEXT    NOT NULL,
                    difficulty       TEXT    NOT NULL,
                    confidence_score REAL    NOT NULL,
                    question_json    TEXT    NOT NULL,
                    starter_code     TEXT    NOT NULL DEFAULT '',
                    reference_code   TEXT    NOT NULL DEFAULT '',
                    prompt_hash      TEXT,
                    ts               TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS few_shots_skill_diff
                    ON few_shots (skill, difficulty, confidence_score DESC);
                CREATE TABLE IF NOT EXISTS student_attempts (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    qid          TEXT    NOT NULL,
                    difficulty   TEXT    NOT NULL,
                    passed       INTEGER NOT NULL,
                    time_minutes REAL,
                    notes        TEXT    DEFAULT '',
                    ts           TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS attempts_qid
                    ON student_attempts (qid);
                CREATE INDEX IF NOT EXISTS attempts_difficulty
                    ON student_attempts (difficulty, passed);
                """
            )
            con.commit()
            # Migration: add prompt_hash column to existing few_shots tables.
            cols = {r[1] for r in con.execute("PRAGMA table_info(few_shots)").fetchall()}
            if "prompt_hash" not in cols:
                con.execute("ALTER TABLE few_shots ADD COLUMN prompt_hash TEXT")
                con.commit()

    # ---- analyzer cache -------------------------------------------------
    def get_analysis(self, key: str) -> Optional[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as con:
            row = con.execute(
                "SELECT json FROM analysis_cache WHERE key=?", (key,)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def put_analysis(self, key: str, data: dict[str, Any]) -> None:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                "INSERT OR REPLACE INTO analysis_cache(key, json, ts) VALUES (?,?,?)",
                (key, json.dumps(data), datetime.now(timezone.utc).isoformat()),
            )
            con.commit()

    # ---- question memory ------------------------------------------------
    def remember_question(self, qid: str, topic: str, stem: str) -> None:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                "INSERT OR REPLACE INTO questions(qid, topic, stem, ts) VALUES (?,?,?,?)",
                (qid, topic, stem, datetime.now(timezone.utc).isoformat()),
            )
            con.commit()

    def all_stems(self) -> list[tuple[str, str]]:
        with closing(sqlite3.connect(self.db_path)) as con:
            return con.execute("SELECT qid, stem FROM questions").fetchall()

    # ---- few-shot prompt optimization -----------------------------------

    def save_few_shot(
        self,
        skill: str,
        difficulty: str,
        confidence_score: float,
        question_json: str,
        starter_code: str = "",
        reference_code: str = "",
        prompt_hash: str | None = None,
    ) -> None:
        """Persist an approved question as a few-shot example for future generation."""
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                """
                INSERT INTO few_shots
                    (skill, difficulty, confidence_score, question_json,
                     starter_code, reference_code, prompt_hash, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    skill, difficulty, confidence_score,
                    question_json, starter_code, reference_code,
                    prompt_hash, datetime.now(timezone.utc).isoformat(),
                ),
            )
            con.commit()

    def get_few_shots(
        self,
        skill: str,
        difficulty: str,
        n: int = 2,
        prompt_hash: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return up to n highest-confidence approved examples for skill+difficulty.

        When prompt_hash is supplied, only examples generated with the same prompt
        version (or rows with NULL prompt_hash, i.e. manual seeds) are returned.
        This prevents stale format examples from polluting generation after a
        prompt rewrite.

        Falls back to same-difficulty examples from any skill when fewer than n
        exact matches exist.
        """
        with closing(sqlite3.connect(self.db_path)) as con:
            if prompt_hash:
                rows = con.execute(
                    """
                    SELECT skill, difficulty, confidence_score, question_json,
                           starter_code, reference_code
                    FROM few_shots
                    WHERE skill = ? AND difficulty = ?
                      AND (prompt_hash = ? OR prompt_hash IS NULL)
                    ORDER BY confidence_score DESC
                    LIMIT ?
                    """,
                    (skill, difficulty, prompt_hash, n),
                ).fetchall()
            else:
                rows = con.execute(
                    """
                    SELECT skill, difficulty, confidence_score, question_json,
                           starter_code, reference_code
                    FROM few_shots
                    WHERE skill = ? AND difficulty = ?
                    ORDER BY confidence_score DESC
                    LIMIT ?
                    """,
                    (skill, difficulty, n),
                ).fetchall()

            if len(rows) < n:
                existing_ids = {r[3][:40] for r in rows}
                if prompt_hash:
                    fallback = con.execute(
                        """
                        SELECT skill, difficulty, confidence_score, question_json,
                               starter_code, reference_code
                        FROM few_shots
                        WHERE difficulty = ? AND skill != ?
                          AND (prompt_hash = ? OR prompt_hash IS NULL)
                        ORDER BY confidence_score DESC
                        LIMIT ?
                        """,
                        (difficulty, skill, prompt_hash, n - len(rows)),
                    ).fetchall()
                else:
                    fallback = con.execute(
                        """
                        SELECT skill, difficulty, confidence_score, question_json,
                               starter_code, reference_code
                        FROM few_shots
                        WHERE difficulty = ? AND skill != ?
                        ORDER BY confidence_score DESC
                        LIMIT ?
                        """,
                        (difficulty, skill, n - len(rows)),
                    ).fetchall()
                rows += [r for r in fallback if r[3][:40] not in existing_ids]

        return [
            {
                "skill": r[0], "difficulty": r[1], "confidence_score": r[2],
                "question_json": r[3], "starter_code": r[4], "reference_code": r[5],
            }
            for r in rows
        ]

    # ---- student attempt tracking ----------------------------------------

    def record_attempt(
        self,
        qid: str,
        difficulty: str,
        passed: bool,
        time_minutes: float | None = None,
        notes: str = "",
    ) -> None:
        """Persist one student attempt result for a question."""
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                """
                INSERT INTO student_attempts
                    (qid, difficulty, passed, time_minutes, notes, ts)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    qid, difficulty.lower(), int(passed),
                    time_minutes, notes,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            con.commit()

    def get_difficulty_pass_rates(self) -> dict[str, dict[str, int]]:
        """Return per-difficulty attempt tallies: {difficulty: {passed: N, total: N}}.

        Only difficulties with at least 1 attempt are included.
        """
        with closing(sqlite3.connect(self.db_path)) as con:
            rows = con.execute(
                """
                SELECT difficulty, passed, COUNT(*) as cnt
                FROM student_attempts
                GROUP BY difficulty, passed
                """
            ).fetchall()

        result: dict[str, dict[str, int]] = {}
        for diff, passed_flag, cnt in rows:
            bucket = result.setdefault(diff, {"passed": 0, "total": 0})
            bucket["total"] += cnt
            if passed_flag:
                bucket["passed"] += cnt
        return result
