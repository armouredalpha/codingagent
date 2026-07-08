"""
robo_assess.graph.builder
=========================

Builds and compiles the LangGraph StateGraph for the assessment pipeline.

Graph topology
--------------

    build_context
        │
    retrieve_context
        │
    generate ◄──────────────────────────────────────┐
        │                                            │ (NEXT_BATCH)
    validate ──(REGENERATE)──► reflect              │
        │                       │                   │
        │                   regenerate──► validate ─┤
        │                                           │
        │ (batch all pass + more remain)────────────┘
        │
    (FINALIZE — all batches done or budget exhausted)
        │
    supervise
        │
       END

Routing after ``validate``
--------------------------
Three outcomes:

* ``REGENERATE``  → batch has failures and attempts remain → reflect → regenerate → validate
* ``NEXT_BATCH``  → current batch fully approved, more slots remain → generate next batch
* ``FINALIZE``    → all batches done (or budget/attempts exhausted) → supervise → END

The per-batch attempt counter resets when the generate node starts a new batch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from ..schemas import (
    AssessmentRequest,
    CoverageMatrix,
    Question,
    QuestionQuality,
)
from ..agents.planner import PlanAction, RunState
from .nodes import make_nodes
from .state import AssessmentState

if TYPE_CHECKING:
    from ..agents.orchestrator import Orchestrator


def _route_after_validate(state: AssessmentState, orch: "Orchestrator") -> str:
    """Conditional edge router called after the ``validate`` node.

    Priority:
      1. If current batch has failures and attempts remain → REGENERATE (reflect)
      2. If all in current batch passed and more slots remain → NEXT_BATCH (generate)
      3. Otherwise → FINALIZE (supervise)
    """
    questions = [Question(**q) for q in state["questions"]]   # failing questions only (after validate split)
    coverage = CoverageMatrix(**state["coverage"])
    quality = [QuestionQuality(**q) for q in (state["quality"] or [])]
    request = AssessmentRequest(**state["request"])

    accumulated_count = len(state.get("accumulated_questions") or [])
    total_needed = request.num_questions

    run_state = RunState(
        questions=questions,
        coverage=coverage,
        quality=quality,
        attempts=state["attempts"],
        max_attempts=orch.settings.max_regeneration_attempts,
        step=state["step"],
        max_steps=orch.settings.max_planner_steps,
        feedback=state["feedback"],
        tokens_spent=orch.token_counter.total_tokens,
        calls_spent=(
            orch.token_counter.total_calls
            if hasattr(orch.token_counter, "total_calls") else 0
        ),
        budget_tokens=state["budget_tokens"],
        budget_calls=state["budget_calls"],
    )

    decision = orch.planner.decide(run_state)
    orch.log.info(
        "plan_decision",
        action=decision.action.value,
        reason=decision.reason,
        bar_passed=decision.bar_passed,
        bar_total=decision.bar_total,
        accumulated=accumulated_count,
        total_needed=total_needed,
    )

    if decision.action == PlanAction.REGENERATE:
        return "reflect"

    # Current batch is done. Decide between starting another batch and shipping.
    #
    # Only start a new batch when we still need more questions AND the planner's
    # step budget is NOT exhausted. Without the budget guard, a batch whose
    # questions never clear the confidence bar keeps accumulated_count at 0, so
    # ``accumulated_count < total_needed`` stays true forever and the graph loops
    # generate → validate → generate indefinitely (burning tokens). The planner
    # already returns FINALIZE in that case; honour it here.
    new_offset = accumulated_count  # accumulated holds all approved so far
    budget_spent = state["step"] >= orch.settings.max_planner_steps
    if new_offset < total_needed and not budget_spent:
        orch.log.info("next_batch", new_offset=new_offset, total_needed=total_needed)
        return "generate"

    if budget_spent and new_offset < total_needed:
        orch.log.warning(
            "finalize_budget_spent",
            approved=new_offset, needed=total_needed,
            step=state["step"], max_steps=orch.settings.max_planner_steps,
        )
    return "supervise"


def _update_batch_offset(state: AssessmentState) -> dict:
    """Called on the generate edge to advance batch_offset."""
    accumulated_count = len(state.get("accumulated_questions") or [])
    return {"batch_offset": accumulated_count}


def build_assessment_graph(orch: "Orchestrator", checkpoints_db: str = "logs/checkpoints.db"):
    """Build and compile the assessment StateGraph bound to ``orch``.

    Returns a compiled LangGraph graph.  Call ``graph.invoke(state, config)``
    to run it; the ``config`` must contain ``{"configurable": {"thread_id": run_id}}``.

    ``checkpoints_db`` is the path to the SQLite file used by SqliteSaver.
    Storing checkpoints on disk means a crashed run can be resumed by calling
    ``run_from_md(md_path, run_id=<original_id>)`` from a new process.
    """
    import os
    import sqlite3 as _sqlite3
    os.makedirs(os.path.dirname(checkpoints_db) or ".", exist_ok=True)

    nodes = make_nodes(orch)

    builder = StateGraph(AssessmentState)

    # Register all nodes
    for name, fn in nodes.items():
        builder.add_node(name, fn)

    # Fixed edges
    builder.set_entry_point("build_context")
    builder.add_edge("build_context",    "retrieve_context")
    builder.add_edge("retrieve_context", "generate")
    builder.add_edge("generate",         "validate")
    builder.add_edge("reflect",          "regenerate")
    builder.add_edge("regenerate",       "validate")
    builder.add_edge("supervise",        END)

    # Conditional edge: validate → reflect (REGENERATE) | generate (NEXT_BATCH) | supervise (FINALIZE)
    builder.add_conditional_edges(
        "validate",
        lambda state: _route_after_validate(state, orch),
        {"reflect": "reflect", "generate": "generate", "supervise": "supervise"},
    )

    # SqliteSaver.from_conn_string() is a context manager in newer langgraph.
    # Use sqlite3.connect() directly to get a long-lived checkpointer.
    conn = _sqlite3.connect(checkpoints_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return builder.compile(checkpointer=checkpointer)
