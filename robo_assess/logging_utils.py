"""
robo_assess.logging_utils
=========================

Structured logging built on ``structlog`` plus a tiny SQLite run-log so every
pipeline execution is auditable (run id, topic, stage timings, confidence,
supervisor verdict). Falls back to the std-lib ``logging`` formatting if
``structlog`` is unavailable, so the module never hard-fails on import.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # structlog is optional at runtime
    import structlog

    _HAS_STRUCTLOG = True
except Exception:  # pragma: no cover
    _HAS_STRUCTLOG = False


_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric, format="%(message)s")
    if _HAS_STRUCTLOG:
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(numeric),
        )
    _CONFIGURED = True


def get_logger(name: str):
    if _HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# SQLite run logger
# ---------------------------------------------------------------------------
class RunLogger:
    """Append-only audit log for pipeline runs and per-stage events."""

    def __init__(self, db_path: str = "logs/runs.db") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id      TEXT PRIMARY KEY,
                    topic       TEXT,
                    started_at  TEXT,
                    finished_at TEXT,
                    n_questions INTEGER,
                    n_approved  INTEGER,
                    supervisor  TEXT,
                    score       INTEGER
                );
                CREATE TABLE IF NOT EXISTS events (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id  TEXT,
                    agent   TEXT,
                    status  TEXT,
                    ts      TEXT,
                    detail  TEXT
                );
                CREATE TABLE IF NOT EXISTS question_traces (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id     TEXT,
                    question_id TEXT,
                    agent      TEXT,
                    decision   TEXT,
                    reason     TEXT,
                    ts         TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_qt_run   ON question_traces(run_id);
                CREATE INDEX IF NOT EXISTS idx_qt_qid   ON question_traces(question_id);
                """
            )
            con.commit()

    def start_run(self, run_id: str, topic: str) -> None:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                "INSERT OR REPLACE INTO runs(run_id, topic, started_at) VALUES (?,?,?)",
                (run_id, topic, datetime.now(timezone.utc).isoformat()),
            )
            con.commit()

    def log_event(self, run_id: str, agent: str, status: str, detail: str = "") -> None:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                "INSERT INTO events(run_id, agent, status, ts, detail) VALUES (?,?,?,?,?)",
                (run_id, agent, status, datetime.now(timezone.utc).isoformat(), detail),
            )
            con.commit()

    def trace_question(
        self,
        run_id: str,
        question_id: str,
        agent: str,
        decision: str,
        reason: str = "",
    ) -> None:
        """Record a per-question agent decision (approve/reject/flag/mismatch/etc.)."""
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                "INSERT INTO question_traces(run_id, question_id, agent, decision, reason, ts) "
                "VALUES (?,?,?,?,?,?)",
                (run_id, question_id, agent, decision,
                 reason[:2000],  # cap to prevent runaway text
                 datetime.now(timezone.utc).isoformat()),
            )
            con.commit()

    def question_trace(self, run_id: str) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT * FROM question_traces WHERE run_id=? ORDER BY ts",
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def finish_run(
        self,
        run_id: str,
        n_questions: int,
        n_approved: int,
        supervisor: str,
        score: int,
    ) -> None:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                """UPDATE runs SET finished_at=?, n_questions=?, n_approved=?,
                       supervisor=?, score=? WHERE run_id=?""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    n_questions,
                    n_approved,
                    supervisor,
                    score,
                    run_id,
                ),
            )
            con.commit()

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path)) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
