"""
robo_assess.token_counter
=========================

Tracks LLM token usage across an entire assessment run.

Usage
-----
    counter = TokenCounter()
    counter.record("question_generator", usage, skill="ROS2 publisher")
    counter.record("question_generator", usage, skill="TF2 transforms")
    report = counter.report()            # full dict
    counter.print_summary()              # terminal table
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .llm_client import TokenUsage


# ---------------------------------------------------------------------------
# Pricing table — USD per 1,000,000 tokens (input, output).
#
# Matched by substring against the model id; first hit wins. Keep entries
# ordered most-specific → least-specific. Local providers cost nothing. When a
# model is unknown we fall back to ``_DEFAULT_PRICE`` so the report still gives
# a non-zero, order-of-magnitude estimate rather than silently reporting $0.
# Update these as provider pricing changes — they are estimates, not a billing
# source of truth.
# ---------------------------------------------------------------------------
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

    def record(self, agent: str, usage: TokenUsage, **metadata: Any) -> None:
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
