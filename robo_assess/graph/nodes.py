"""
robo_assess.graph.nodes
=======================

LangGraph node functions for the assessment pipeline.

Each node is a pure function ``(state: AssessmentState) -> dict`` that returns
only the keys it mutates.  Pydantic models are deserialized from state dicts on
entry and re-serialized on exit so the state remains JSON-serializable.

Non-serializable infrastructure (SkillGraph, ImprovedConfidenceScorer) is
stored on ``orch._run_contexts[run_id]`` (set by ``build_context``) and
accessed by subsequent nodes via closure over ``orch``.
LangGraph's SqliteSaver checkpointer handles all run-state persistence.

All nodes are produced by ``make_nodes(orch)`` which binds them to a specific
``Orchestrator`` instance.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from ..schemas import (
    AssessmentPackage,
    AssessmentRequest,
    ContextPack,
    CoverageMatrix,
    Question,
    QuestionQuality,
    SourceResearch,
    SyllabusAnalysis,
    TriageResult,
)
from ..guardrails import GuardrailConfig
from ..tools.registry import ToolRegistry
from ..tools.handlers import build_handlers
from .state import AssessmentState

if TYPE_CHECKING:
    from ..agents.orchestrator import Orchestrator


# ---------------------------------------------------------------------------
# Node factory
# ---------------------------------------------------------------------------

def make_nodes(orch: "Orchestrator") -> dict[str, Callable[[AssessmentState], dict]]:
    """Return a dict of node functions bound to the given Orchestrator instance."""

    # ── build_context ────────────────────────────────────────────────────────
    def build_context(state: AssessmentState) -> dict:
        print("[build_context] extracting skills and building context from MD...", flush=True)
        request = AssessmentRequest(**state["request"])
        run_id = state["run_id"]

        if request.md_path:
            ctx = orch._build_context_from_md(Path(request.md_path), request, run_id)
        else:
            ctx = orch._build_context_from_text(request, run_id)

        # Store context keyed by run_id so concurrent runs don't overwrite each other
        orch._run_contexts[run_id] = ctx

        if orch.on_skills_extracted is not None:
            try:
                orch.on_skills_extracted(len(ctx.analysis.skills))
            except Exception:
                pass

        return {
            "analysis": ctx.analysis.model_dump(),
            "coverage": ctx.coverage.model_dump(),
            "skill_entries": [s.model_dump() for s in ctx.skill_entries],
            "summary_text": ctx.summary_text,
            "skillset": ctx.skillset.model_dump() if ctx.skillset else None,
            # propagate budget from request into state
            "budget_tokens": (
                getattr(request, "budget_tokens", None)
                or getattr(orch.settings, "default_budget_tokens", None)
            ),
            "budget_calls": (
                getattr(request, "budget_calls", None)
                or getattr(orch.settings, "default_budget_calls", None)
            ),
        }

    # ── retrieve_context ─────────────────────────────────────────────────────
    def retrieve_context(state: AssessmentState) -> dict:
        print("[retrieve_context] RAG lookup + complexity triage + skill ordering...", flush=True)
        ctx = orch._run_contexts[state["run_id"]]
        run_id = state["run_id"]
        request = AssessmentRequest(**state["request"])
        analysis = SyllabusAnalysis(**state["analysis"])

        # RAG context retrieval
        cr = orch.context_retrieval.run(analysis)
        orch._stage(run_id, cr)
        context_pack = ContextPack(**cr.payload["context_pack"])
        ctx.context_pack = context_pack

        # Merged: complexity triage + skill selection (1 LLM call instead of 2)
        tr = orch.skill_triage.run(
            analysis=analysis,
            context_pack=context_pack,
            difficulty=getattr(request, "difficulty", "mixed"),
            total_questions=request.num_questions,
            all_skills=ctx.skill_entries,
        )
        orch._stage(run_id, tr)
        triage_result = TriageResult(**tr.payload["triage"])
        ctx.triage = triage_result

        # Wire triage into generator for slot planning
        orch.generator.triage = triage_result

        # Wire ordered skills into generator
        ordered_skills = tr.payload.get("ordered_skills", [])
        if ordered_skills:
            orch.generator.picked_skills = ordered_skills
            orch.log.info("skill_triage_skills_selected", skills=ordered_skills)

        # Wire tool registry: similarity check, skill-graph query, guardrails, course search
        handlers = build_handlers(
            vectorstore=orch.vectorstore,
            skill_graph=ctx.skill_graph,
            guardrail_config=GuardrailConfig.load(),
            tavily_api_key=getattr(orch.settings, "tavily_api_key", "") or "",
            exa_api_key=getattr(orch.settings, "exa_api_key", "") or "",
        )
        orch.generator.tool_registry = ToolRegistry(handlers=handlers)
        orch.log.info("tool_registry_wired", tools=list(handlers))

        return {
            "context_pack": context_pack.model_dump(),
            "triage": triage_result.model_dump(),
        }

    # ── generate ─────────────────────────────────────────────────────────────
    def generate(state: AssessmentState) -> dict:
        run_id = state["run_id"]
        analysis = SyllabusAnalysis(**state["analysis"])
        coverage = CoverageMatrix(**state["coverage"])
        request = AssessmentRequest(**state["request"])

        # batch_offset = number of questions already approved (accumulated)
        batch_offset = len(state.get("accumulated_questions") or [])
        batch_size = getattr(orch.settings, "generation_batch_size", 2)
        remaining = request.num_questions - batch_offset
        this_batch = min(batch_size, remaining)

        print(
            f"[generate] batch {batch_offset // batch_size + 1}: "
            f"generating {this_batch} questions (slots {batch_offset + 1}–{batch_offset + this_batch}, "
            f"step {state['step'] + 1})...",
            flush=True,
        )
        r = orch.generator.run(analysis, coverage, this_batch, offset=batch_offset)
        orch._stage(run_id, r)
        questions = [Question(**q) for q in r.payload["questions"]]

        return {
            "questions": [q.model_dump() for q in questions],
            "quality": None,
            "attempts": 0,   # reset per-batch attempt counter
            "step": state["step"] + 1,
        }

    # ── validate ─────────────────────────────────────────────────────────────
    def validate(state: AssessmentState) -> dict:
        print(f"[validate] running 6 validators + grading + confidence on {len(state['questions'])} questions...", flush=True)
        ctx = orch._run_contexts[state["run_id"]]
        run_id = state["run_id"]
        analysis = SyllabusAnalysis(**state["analysis"])
        coverage = CoverageMatrix(**state["coverage"])
        request = AssessmentRequest(**state["request"])
        questions = [Question(**q) for q in state["questions"]]

        # Full validation chain — mutates questions in-place (similarity, confidence, etc.)
        orch._validate(
            run_id, questions, coverage, analysis, request,
            confidence_scorer=ctx.confidence_scorer,
            context_pack=ctx.context_pack,
        )
        orch._validate_skill_graph_coverage(ctx.skill_graph, questions, analysis.skills)

        quality = orch.planner.evaluate_quality(questions, coverage)
        n_pass = sum(1 for x in quality if x.passed)
        orch.log.info("quality_bar", passed=n_pass, total=len(quality))
        # Trace per-question quality bar decisions to DB for observability
        run_id = state["run_id"]
        for qq in quality:
            decision = "quality_pass" if qq.passed else "quality_fail"
            reason = "; ".join(qq.failed_checks) if qq.failed_checks else "passed all checks"
            try:
                orch.run_logger.trace_question(run_id, qq.question_id, "quality_bar", decision, reason)
            except Exception:
                pass

        # Separate passing from failing — passing questions graduate to accumulated_questions
        # so they are never re-validated in subsequent batches or regeneration rounds.
        q_by_id = {q.question_id: q for q in questions}
        passing_ids = {qq.question_id for qq in quality if qq.passed}
        failing_ids = {qq.question_id for qq in quality if not qq.passed}

        accumulated = list(state.get("accumulated_questions") or [])
        for qq in quality:
            if qq.passed:
                q = q_by_id.get(qq.question_id)
                if q:
                    accumulated.append(q.model_dump())

        # Only keep failing questions in `questions` for potential regeneration
        remaining_questions = [q for q in questions if q.question_id in failing_ids]

        orch.log.info(
            "validate_batch_split",
            passed=len(passing_ids),
            failed=len(failing_ids),
            accumulated_total=len(accumulated),
        )

        return {
            "questions": [q.model_dump() for q in remaining_questions],
            "accumulated_questions": accumulated,
            "coverage": coverage.model_dump(),
            "quality": [q.model_dump() for q in quality],
            "step": state["step"] + 1,
        }

    # ── reflect ──────────────────────────────────────────────────────────────
    def reflect(state: AssessmentState) -> dict:
        failing_count = sum(1 for q in (state["quality"] or []) if not q.get("passed", True))
        print(f"[reflect] planner reflecting on {failing_count} failing question(s)...", flush=True)
        questions = [Question(**q) for q in state["questions"]]
        quality = [QuestionQuality(**q) for q in (state["quality"] or [])]
        feedback = orch.planner.reflect(questions, quality)
        # Trace planner regeneration instructions for observability
        run_id = state["run_id"]
        for qid, fix in feedback.items():
            try:
                orch.run_logger.trace_question(run_id, qid, "planner_reflect", "regenerate_instruction", fix[:500])
            except Exception:
                pass
        return {"feedback": feedback}

    # ── regenerate ───────────────────────────────────────────────────────────
    def regenerate(state: AssessmentState) -> dict:
        run_id = state["run_id"]
        analysis = SyllabusAnalysis(**state["analysis"])
        coverage = CoverageMatrix(**state["coverage"])
        questions = [Question(**q) for q in state["questions"]]
        quality = [QuestionQuality(**q) for q in (state["quality"] or [])]
        failing_ids = [q.question_id for q in quality if not q.passed]

        print(f"[regenerate] regenerating {len(failing_ids)} question(s) (attempt {state['attempts'] + 1})...", flush=True)
        orch.log.info(
            "planner_regenerate",
            attempt=state["attempts"] + 1,
            failing=len(failing_ids),
        )

        rr = orch.generator.regenerate(
            questions, failing_ids, state["feedback"], analysis, coverage,
        )
        orch._stage(run_id, rr)
        new_questions = [Question(**q) for q in rr.payload["questions"]]

        # Update coverage with newly generated skills
        for q in new_questions:
            orch.coverage.mark(coverage, q.tested_skills)

        return {
            "questions": [q.model_dump() for q in new_questions],
            "coverage": coverage.model_dump(),
            "quality": None,
            "attempts": state["attempts"] + 1,
            "step": state["step"] + 1,
        }

    # ── supervise ────────────────────────────────────────────────────────────
    def supervise(state: AssessmentState) -> dict:
        # Merge: accumulated (approved from prior batches) + current batch remainder
        all_q_dicts = list(state.get("accumulated_questions") or []) + list(state.get("questions") or [])
        approved_count = sum(1 for q in all_q_dicts if q.get("confidence", {}).get("status") == "APPROVED")
        print(f"[supervise] final gate — {approved_count}/{len(all_q_dicts)} questions approved...", flush=True)
        ctx = orch._run_contexts[state["run_id"]]
        run_id = state["run_id"]
        request = AssessmentRequest(**state["request"])
        analysis = SyllabusAnalysis(**state["analysis"])
        coverage = CoverageMatrix(**state["coverage"])
        questions = [Question(**q) for q in all_q_dicts]
        quality = [QuestionQuality(**q) for q in (state["quality"] or [])]

        bar_pass_rate = sum(1 for x in quality if x.passed) / len(quality) if quality else 0.0
        eval_score = round(bar_pass_rate * 100)

        covered = sum(1 for v in coverage.matrix.values() if v)
        portfolio_coverage_score = (
            round(covered / len(coverage.matrix) * 100) if coverage.matrix else 0
        )

        pkg = AssessmentPackage(
            run_id=run_id,
            topic=request.topic,
            syllabus=request.syllabus,
            syllabus_analysis=analysis,
            source_research=SourceResearch(),
            coverage_matrix=coverage,
            questions=questions,
            portfolio_coverage_score=portfolio_coverage_score,
            portfolio_missing_areas=[s for s, cov in coverage.matrix.items() if not cov],
            plan_trace=[],
            quality=quality,
        )

        t0 = time.time()
        sres = orch.supervisor.run(pkg, eval_score)
        orch._stage(run_id, sres, elapsed_ms=int((time.time() - t0) * 1000))
        pkg.supervisor = pkg.supervisor.model_validate(sres.payload["verdict"])

        orch._attach_costs(pkg)

        orch._finish_run(run_id, pkg, quality)

        return {"pkg": pkg.model_dump()}

    return {
        "build_context":    build_context,
        "retrieve_context": retrieve_context,
        "generate":         generate,
        "validate":         validate,
        "reflect":          reflect,
        "regenerate":       regenerate,
        "supervise":        supervise,
    }
