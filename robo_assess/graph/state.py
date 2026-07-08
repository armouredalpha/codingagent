"""
robo_assess.graph.state
=======================

Shared state TypedDict for the LangGraph assessment pipeline.

All values are serializable primitives / dicts so LangGraph's checkpointer
can snapshot and resume any node boundary.  Pydantic objects are converted
to dicts at node entry (``Model(**state["key"])``) and back on exit
(``model.model_dump()``).

Non-serializable infrastructure (SkillGraph, StateManager,
ImprovedConfidenceScorer) is held on the ``Orchestrator`` instance under
``_run_ctx`` and is never put in this state dict.
"""

from __future__ import annotations

from typing import Any

try:
    from typing import TypedDict
except ImportError:  # Python < 3.8
    from typing_extensions import TypedDict  # type: ignore[assignment]


class AssessmentState(TypedDict):
    # Identity
    run_id: str
    request: dict                    # AssessmentRequest.model_dump()

    # Context (set by build_context node)
    analysis: dict | None            # SyllabusAnalysis.model_dump()
    coverage: dict | None            # CoverageMatrix.model_dump()
    skill_entries: list[dict]        # [SkillEntry.model_dump()]
    summary_text: str
    skillset: dict | None            # SkillSet.model_dump()

    # RAG + Triage (set by retrieve_context node)
    context_pack: dict | None        # ContextPack.model_dump()
    triage: dict | None              # TriageResult.model_dump()

    # Generation loop
    questions: list[dict]            # [Question.model_dump()] — current batch being worked on
    accumulated_questions: list[dict] # approved questions from completed batches
    batch_offset: int                # how many slots have been fully generated + approved
    quality: list[dict] | None       # [QuestionQuality.model_dump()] | None
    feedback: dict[str, str]         # qid -> regeneration instruction
    attempts: int                    # regeneration rounds completed (per batch)
    step: int                        # planner step counter

    # Budget
    budget_tokens: int | None
    budget_calls: int | None

    # Final output
    pkg: dict | None                 # AssessmentPackage.model_dump()

    # Error channel (set by any node on fatal failure)
    error: str | None                # non-None signals a fatal node failure
