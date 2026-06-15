"""Simple metrics collection for observability without external dependencies.

Tracks: agent execution times, token usage, error rates, quality gate pass rates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional


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
                started_at=datetime.utcnow().isoformat(),
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
            run.ended_at = datetime.utcnow().isoformat()
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
