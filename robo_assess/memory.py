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
                """
            )
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
