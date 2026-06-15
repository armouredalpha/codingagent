"""
Shared helper for batched LLM critics (scope, difficulty).
=========================================================

Sends a batch of questions to a critic prompt in one ``complete_json`` call and
maps the returned ``{"results": [...]}`` back to questions by ``id``. If a
question's verdict is missing or fails validation, ONLY that question is
re-sent individually (a length-1 batch) — the whole batch is never re-run.
Questions that still fail are left out so the caller can fall back to its
rule-based verdict.
"""

from __future__ import annotations

import json
from typing import Any, Callable


def _chunk(items: list, size: int) -> list[list]:
    size = max(1, size)
    return [items[i:i + size] for i in range(0, len(items), size)]


def _call(llm, system: str, template: str, payload: list[dict], settings,
          token_counter, agent_name: str, log, meta: dict) -> dict[str, dict]:
    """One LLM call over `payload`; return {id: verdict} for entries present."""
    user = template.replace("{questions}", json.dumps(payload, ensure_ascii=False))
    raw, usage = llm.complete_json(
        system=system,
        user=user,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )
    if token_counter:
        token_counter.record(agent_name, usage, **meta)
    results = raw.get("results", []) if isinstance(raw, dict) else []
    out: dict[str, dict] = {}
    for r in results:
        if isinstance(r, dict) and "id" in r:
            out[str(r["id"])] = r
    return out


def run_batched_critic(
    *,
    llm,
    system: str,
    template: str,
    payload: list[dict],
    settings,
    validate: Callable[[dict], bool],
    agent_name: str,
    log,
    token_counter: Any = None,
    meta: dict | None = None,
) -> dict[str, dict]:
    """Return {id: verdict} for every question that produced a valid verdict.

    `payload` is a list of dicts each containing an ``"id"`` key. `validate`
    decides whether a single verdict dict is acceptable. Missing or invalid
    verdicts are retried one-at-a-time; persistent failures are omitted.
    """
    meta = meta or {}
    batch_size = getattr(settings, "critic_batch_size", 10)
    verdicts: dict[str, dict] = {}
    ids = [str(p["id"]) for p in payload]
    by_id = {str(p["id"]): p for p in payload}

    # Pass 1 — batched calls
    for chunk in _chunk(payload, batch_size):
        try:
            got = _call(llm, system, template, chunk, settings,
                        token_counter, agent_name, log, meta)
        except Exception as exc:  # noqa: BLE001 — leave chunk for per-item retry
            log.warning("critic_batch_failed", agent=agent_name, error=str(exc))
            got = {}
        for qid, verdict in got.items():
            if validate(verdict):
                verdicts[qid] = verdict

    # Pass 2 — per-question retry for anything missing/invalid
    for qid in ids:
        if qid in verdicts:
            continue
        try:
            got = _call(llm, system, template, [by_id[qid]], settings,
                        token_counter, agent_name, log, {**meta, "retry": qid})
            verdict = got.get(qid)
            if verdict and validate(verdict):
                verdicts[qid] = verdict
            else:
                log.warning("critic_item_unrecovered", agent=agent_name, qid=qid)
        except Exception as exc:  # noqa: BLE001 — caller falls back to rule-based
            log.warning("critic_item_failed", agent=agent_name, qid=qid, error=str(exc))

    return verdicts
