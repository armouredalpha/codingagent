"""
coding_agent.telemetry
======================

Single module for the three observability concerns that used to live in
separate files (``logging_utils.py``, ``metrics.py``, ``token_counter.py``):

- Structured logging + a SQLite run/event/question-trace audit log
  (``configure_logging``, ``get_logger``, ``RunLogger``)
- In-memory per-agent timing/error metrics, dumped to ``reports/metrics_*.json``
  (``MetricsCollector``, ``AgentMetrics``, ``RunMetrics``)
- LLM token usage + cost accounting, priced per-record by the model that
  produced it (``TokenCounter``, ``AgentTokenRecord``, ``price_for``)

They stay three distinct classes — each with its own storage (structlog/stdlib
logging, an in-memory dict, a list of records) and their own callers — merged
here for one import path instead of three, not rewritten into a shared API
that none of their call sites actually need.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    # Deferred: llm_client imports get_logger from this module, so importing
    # TokenUsage at module level here would create an import cycle. Safe as a
    # type-only import because of `from __future__ import annotations`.
    from .llm_client import TokenUsage

try:  # structlog is optional at runtime
    import structlog

    _HAS_STRUCTLOG = True
except Exception:  # pragma: no cover
    _HAS_STRUCTLOG = False


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------

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
# SQLite run logger — audit trail (run id, topic, stage timings, verdicts)
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


# ---------------------------------------------------------------------------
# In-memory per-agent metrics — timing/error rates, dumped to reports/*.json
# ---------------------------------------------------------------------------

@dataclass
class AgentMetrics:
    """Per-agent execution metrics."""
    agent_name: str
    total_calls: int = 0
    total_elapsed_ms: float = 0.0
    errors: int = 0
    max_elapsed_ms: float = 0.0
    min_elapsed_ms: float = float('inf')

    @property
    def avg_elapsed_ms(self) -> float:
        return self.total_elapsed_ms / max(1, self.total_calls)

    @property
    def error_rate(self) -> float:
        return (self.errors / self.total_calls * 100) if self.total_calls > 0 else 0


@dataclass
class RunMetrics:
    """Metrics for an entire generation run."""
    run_id: str
    topic: str
    started_at: str
    ended_at: Optional[str] = None
    agents: dict[str, AgentMetrics] = field(default_factory=dict)
    total_questions_generated: int = 0
    total_questions_passed_bar: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    total_elapsed_ms: float = 0.0

    @property
    def pass_rate(self) -> float:
        return (self.total_questions_passed_bar / self.total_questions_generated * 100) \
            if self.total_questions_generated > 0 else 0


class MetricsCollector:
    """Thread-safe metrics collection."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self.runs: dict[str, RunMetrics] = {}

    def start_run(self, run_id: str, topic: str) -> None:
        """Mark the start of a generation run."""
        with self._lock:
            self.runs[run_id] = RunMetrics(
                run_id=run_id,
                topic=topic,
                started_at=datetime.now(timezone.utc).isoformat(),
            )

    def record_agent_call(
        self,
        run_id: str,
        agent_name: str,
        elapsed_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Record a single agent execution."""
        with self._lock:
            if run_id not in self.runs:
                return
            run = self.runs[run_id]
            if agent_name not in run.agents:
                run.agents[agent_name] = AgentMetrics(agent_name=agent_name)
            m = run.agents[agent_name]
            m.total_calls += 1
            m.total_elapsed_ms += elapsed_ms
            m.max_elapsed_ms = max(m.max_elapsed_ms, elapsed_ms)
            m.min_elapsed_ms = min(m.min_elapsed_ms, elapsed_ms)
            if error:
                m.errors += 1

    def end_run(
        self,
        run_id: str,
        total_tokens: int,
        cost_usd: float,
        questions_generated: int,
        questions_passed: int,
    ) -> None:
        """Mark the end of a run and save metrics."""
        with self._lock:
            if run_id not in self.runs:
                return
            run = self.runs[run_id]
            run.ended_at = datetime.now(timezone.utc).isoformat()
            run.total_tokens_used = total_tokens
            run.total_cost_usd = cost_usd
            run.total_questions_generated = questions_generated
            run.total_questions_passed_bar = questions_passed

            # Save to file
            out_path = self.output_dir / f"metrics_{run_id}.json"
            metrics_dict = {
                "run": {
                    "run_id": run.run_id,
                    "topic": run.topic,
                    "started_at": run.started_at,
                    "ended_at": run.ended_at,
                    "total_elapsed_ms": run.total_elapsed_ms,
                },
                "questions": {
                    "generated": run.total_questions_generated,
                    "passed_bar": run.total_questions_passed_bar,
                    "pass_rate_pct": round(run.pass_rate, 1),
                },
                "tokens": {
                    "total": run.total_tokens_used,
                    "cost_usd": round(run.total_cost_usd, 6),
                },
                "agents": {
                    name: {
                        "calls": m.total_calls,
                        "errors": m.errors,
                        "error_rate_pct": round(m.error_rate, 1),
                        "avg_elapsed_ms": round(m.avg_elapsed_ms, 1),
                        "min_elapsed_ms": round(m.min_elapsed_ms, 1),
                        "max_elapsed_ms": round(m.max_elapsed_ms, 1),
                    }
                    for name, m in run.agents.items()
                },
            }
            out_path.write_text(json.dumps(metrics_dict, indent=2))

    def get_run_summary(self, run_id: str) -> Optional[dict]:
        """Get a summary of run metrics."""
        with self._lock:
            if run_id not in self.runs:
                return None
            run = self.runs[run_id]
            return {
                "run_id": run.run_id,
                "topic": run.topic,
                "questions": {
                    "generated": run.total_questions_generated,
                    "passed_bar": run.total_questions_passed_bar,
                    "pass_rate_pct": round(run.pass_rate, 1),
                },
                "cost_usd": round(run.total_cost_usd, 6),
                "slow_agents": [
                    (name, round(m.avg_elapsed_ms, 1))
                    for name, m in sorted(run.agents.items(), key=lambda x: -x[1].avg_elapsed_ms)[:3]
                ],
                "failed_agents": [
                    (name, m.errors)
                    for name, m in run.agents.items()
                    if m.errors > 0
                ],
            }


# ---------------------------------------------------------------------------
# Token usage + cost accounting
# ---------------------------------------------------------------------------

# Pricing table — USD per 1,000,000 tokens (input, output).
#
# Matched by substring against the model id; first hit wins. Keep entries
# ordered most-specific → least-specific. Local providers cost nothing. When a
# model is unknown we fall back to ``_DEFAULT_PRICE`` so the report still gives
# a non-zero, order-of-magnitude estimate rather than silently reporting $0.
# Update these as provider pricing changes — they are estimates, not a billing
# source of truth.
_PRICE_TABLE: list[tuple[str, tuple[float, float]]] = [
    ("claude-opus-4", (15.0, 75.0)),
    ("claude-sonnet-4", (3.0, 15.0)),
    ("claude-haiku-4", (1.0, 5.0)),
    ("claude-3-5-haiku", (0.80, 4.0)),
    ("claude", (3.0, 15.0)),
    # GPT-4.1 family — MUST come before the "gpt-4" catch-all below, otherwise
    # "gpt-4.1" matches "gpt-4" and gets billed at the legacy $30/$60 rate.
    ("gpt-4.1-nano", (0.10, 0.40)),
    ("gpt-4.1-mini", (0.40, 1.60)),
    ("gpt-4.1", (2.00, 8.00)),
    ("gpt-4o-mini", (0.15, 0.60)),
    ("gpt-4o", (2.50, 10.0)),
    ("gpt-4", (30.0, 60.0)),       # legacy GPT-4 (original) — genuinely $30/$60
    ("o1-mini", (1.10, 4.40)),
    ("o1", (15.0, 60.0)),
    # Google Gemini
    ("gemini-2.5-flash-lite", (0.10, 0.40)),
    ("gemini-2.5-flash", (0.30, 2.50)),
    ("gemini-2.5-pro", (1.25, 10.0)),
    ("gemini-2.0-flash-lite", (0.075, 0.30)),
    ("gemini-2.0-flash", (0.10, 0.40)),
    ("gemini", (0.30, 2.50)),
]
_DEFAULT_PRICE = (0.15, 0.60)


def price_for(provider: str, model: str) -> tuple[float, float]:
    """Return (input_per_M, output_per_M) USD for a provider/model pair."""
    m = (model or "").lower()
    for needle, price in _PRICE_TABLE:
        if needle in m:
            return price
    return _DEFAULT_PRICE


@dataclass
class AgentTokenRecord:
    agent: str
    call_index: int
    input_tokens: int
    output_tokens: int
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class TokenCounter:
    """Accumulates token usage records for one full pipeline run.

    Pass ``provider``/``model`` so cost is priced from the live :func:`price_for`
    table; otherwise it falls back to the default rate. Tag a ``record`` with
    ``question_id=...`` to attribute its tokens/cost to a specific question — the
    report then carries a per-question cost breakdown (the number you watch to
    know what one question costs on a given model).
    """

    def __init__(self, provider: str = "", model: str = "") -> None:
        self._records: list[AgentTokenRecord] = []
        self._call_counts: dict[str, int] = {}
        self.provider = provider
        self.model = model
        self._in_per_m, self._out_per_m = price_for(provider, model)
        # Generation now runs concurrently (ThreadPoolExecutor in the question
        # generator), so record() is called from worker threads — guard the
        # shared mutable state.
        self._lock = threading.Lock()

    def record(self, agent: str, usage: "TokenUsage", **metadata: Any) -> None:
        """Record one LLM call's token usage. Thread-safe."""
        with self._lock:
            idx = self._call_counts.get(agent, 0) + 1
            self._call_counts[agent] = idx
            self._records.append(AgentTokenRecord(
                agent=agent,
                call_index=idx,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                model=usage.model,
                metadata=metadata,
            ))

    # ------------------------------------------------------------------ #
    def _cost(self, in_tokens: int, out_tokens: int) -> float:
        """Cost at the run's primary model rate (used as a fallback)."""
        return (in_tokens / 1_000_000 * self._in_per_m
                + out_tokens / 1_000_000 * self._out_per_m)

    def _record_cost(self, r: AgentTokenRecord) -> float:
        """Cost of a single record priced by *its own* model.

        Critics run on cheaper models (gpt-4.1-mini, gemini-flash-lite) than the
        generator, so pricing every record at the run's primary model rate would
        over-report critic cost. Each record carries the model that produced it,
        so we price it individually and fall back to the run's primary rate only
        when the record has no usable model string.
        """
        if r.model and r.model != "none":
            in_m, out_m = price_for(self.provider, r.model)
        else:
            in_m, out_m = self._in_per_m, self._out_per_m
        return (r.input_tokens / 1_000_000 * in_m
                + r.output_tokens / 1_000_000 * out_m)

    # ------------------------------------------------------------------ #
    # Aggregates
    # ------------------------------------------------------------------ #
    @property
    def total_input(self) -> int:
        return sum(r.input_tokens for r in self._records)

    @property
    def total_output(self) -> int:
        return sum(r.output_tokens for r in self._records)

    @property
    def total_tokens(self) -> int:
        return self.total_input + self.total_output

    @property
    def total_calls(self) -> int:
        return len(self._records)

    def by_agent(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for r in self._records:
            bucket = out.setdefault(
                r.agent, {"calls": 0, "input": 0, "output": 0, "total": 0, "cost_usd": 0.0}
            )
            bucket["calls"] += 1
            bucket["input"] += r.input_tokens
            bucket["output"] += r.output_tokens
            bucket["total"] += r.total_tokens
            # Price each record by its own model so cheap critics aren't billed
            # at the generator's rate.
            bucket["cost_usd"] += self._record_cost(r)
        for stats in out.values():
            stats["cost_usd"] = round(stats["cost_usd"], 6)
        return out

    def heaviest_agent(self) -> str:
        """Return the agent name that consumed the most total tokens."""
        by_ag = self.by_agent()
        if not by_ag:
            return "none"
        return max(by_ag, key=lambda k: by_ag[k]["total"])

    def estimated_cost(self, input_per_m: float | None = None, output_per_m: float | None = None) -> float:
        """Total run cost in USD.

        With no arguments, each call is priced by its own model (so a run that
        mixes gpt-4.1 generation with gemini-flash-lite critics is costed
        correctly). Pass explicit rates to force a single flat rate across all
        tokens (used when the caller wants config-driven pricing).
        """
        if input_per_m is None and output_per_m is None:
            return sum(self._record_cost(r) for r in self._records)
        ipm = self._in_per_m if input_per_m is None else input_per_m
        opm = self._out_per_m if output_per_m is None else output_per_m
        return self.total_input / 1_000_000 * ipm + self.total_output / 1_000_000 * opm

    def avg_tokens_per_question(self) -> float:
        gen_records = [r for r in self._records if r.agent == "question_generator"]
        if not gen_records:
            return 0.0
        return sum(r.total_tokens for r in gen_records) / len(gen_records)

    def per_question(self) -> dict[str, dict[str, Any]]:
        """Tokens + USD attributed to each question_id (generation + regen).

        Only records tagged with ``question_id`` are counted, so this is the true
        marginal cost of producing a question, separate from batch-level critic
        calls. ``attempts`` counts how many generation calls that slot consumed —
        a high number means the quality bar kept rejecting it.
        """
        out: dict[str, dict[str, Any]] = {}
        for r in self._records:
            qid = r.metadata.get("question_id")
            if not qid:
                continue
            b = out.setdefault(str(qid), {
                "tokens": 0, "input": 0, "output": 0, "cost_usd": 0.0, "attempts": 0,
            })
            b["input"] += r.input_tokens
            b["output"] += r.output_tokens
            b["tokens"] += r.total_tokens
            b["cost_usd"] = round(b["cost_usd"] + self._record_cost(r), 6)
            b["attempts"] += 1
        return out

    def avg_cost_per_question(self) -> float:
        pq = self.per_question()
        if not pq:
            # No per-question tags — approximate from generator calls.
            return round(self._cost(self.total_input, self.total_output) / max(1, self._call_counts.get("question_generator", 1)), 6)
        return round(sum(v["cost_usd"] for v in pq.values()) / len(pq), 6)

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def summary(self) -> dict[str, Any]:
        """Compact summary dict for embedding in run_metadata.json."""
        model = self.model or (self._records[0].model if self._records else "none")
        return {
            "model": model,
            "provider": self.provider,
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input,
            "total_output_tokens": self.total_output,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost(), 6),
            "avg_cost_per_question_usd": self.avg_cost_per_question(),
            "heaviest_agent": self.heaviest_agent(),
            "price_input_per_million_usd": self._in_per_m,
            "price_output_per_million_usd": self._out_per_m,
        }

    def report(self) -> dict[str, Any]:
        model = self.model or (self._records[0].model if self._records else "none")
        return {
            "model": model,
            "provider": self.provider,
            "price_input_per_million_usd": self._in_per_m,
            "price_output_per_million_usd": self._out_per_m,
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input,
            "total_output_tokens": self.total_output,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_question": round(self.avg_tokens_per_question(), 1),
            "estimated_cost_usd": round(self.estimated_cost(), 6),
            "avg_cost_per_question_usd": self.avg_cost_per_question(),
            "heaviest_agent": self.heaviest_agent(),
            "per_question": self.per_question(),
            "by_agent": self.by_agent(),
            "calls": [
                {
                    "agent": r.agent,
                    "call": r.call_index,
                    "input": r.input_tokens,
                    "output": r.output_tokens,
                    "total": r.total_tokens,
                    **r.metadata,
                }
                for r in self._records
            ],
        }

    def print_summary(self) -> None:
        if not self._records:
            print("  [token_counter] No LLM calls recorded.")
            return

        model = self._records[0].model
        by_ag = self.by_agent()

        print()
        print("=" * 60)
        print("  TOKEN USAGE REPORT")
        print("=" * 60)
        print(f"  Model          : {model}")
        print(f"  Total calls    : {self.total_calls}")
        print(f"  Total input    : {self.total_input:,} tokens")
        print(f"  Total output   : {self.total_output:,} tokens")
        print(f"  Total          : {self.total_tokens:,} tokens")
        print(f"  Avg/question   : {self.avg_tokens_per_question():.0f} tokens")
        print(f"  Price (in/out) : ${self._in_per_m}/${self._out_per_m} per 1M tokens")
        print(f"  Est. run cost  : ${self.estimated_cost():.5f} USD")
        print(f"  Avg cost/Q     : ${self.avg_cost_per_question():.6f} USD")
        print("-" * 72)
        print(f"  {'Agent':<28} {'Calls':>5} {'Input':>8} {'Output':>8} {'Total':>8} {'Cost USD':>10}")
        print(f"  {'-'*28} {'-'*5} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")
        for agent, stats in sorted(by_ag.items(), key=lambda x: -x[1]["total"]):
            print(f"  {agent:<28} {stats['calls']:>5} {stats['input']:>8,} {stats['output']:>8,} {stats['total']:>8,} {stats['cost_usd']:>10.6f}")
        print(f"  {'heaviest: ' + self.heaviest_agent():<72}")
        pq = self.per_question()
        if pq:
            print("-" * 60)
            print(f"  {'Question':<28} {'Attempts':>8} {'Tokens':>10} {'Cost USD':>12}")
            print(f"  {'-'*28} {'-'*8} {'-'*10} {'-'*12}")
            for qid, st in sorted(pq.items()):
                print(f"  {qid:<28} {st['attempts']:>8} {st['tokens']:>10,} {st['cost_usd']:>12.6f}")
        print("=" * 60)
        print()
