"""
Orchestrator Agent
==================

Single entry-point for all assessment generation.  Both input modes — a raw
``AssessmentRequest`` with a text syllabus, and an MD teaching-material file —
feed into one unified pipeline:

    build context  →  SkillGraph  →  PlannerAgent loop  →  Supervisor  →  Package

Input modes
-----------
* ``run(request)``         — accepts an ``AssessmentRequest``; if ``request.md_path``
                              is set, skill extraction is done from the MD file,
                              otherwise the syllabus list is used directly.
* ``run_from_md(md_path)`` — convenience wrapper: builds an ``AssessmentRequest``
                              from an MD file and calls ``run()``.

Both modes share the same generation loop (PlannerAgent), SkillGraph wiring,
validation chain, and Supervisor verdict.  There is no second code path.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..config import Settings
from ..llm_client import make_client, make_cheap_client, make_agent_client
from ..logging_utils import RunLogger, configure_logging, get_logger
from ..memory import Memory
from ..token_counter import TokenCounter
from ..schemas import (
    AssessmentPackage,
    AssessmentRequest,
    CoverageMatrix,
    Question,
    SkillEntry,
    SourceResearch,
    SyllabusAnalysis,
)
from ..vectorstore import VectorStore
from ..semantic_vectorstore import build_vectorstore
from ..skill_taxonomy import SkillGraph
from ..learned_confidence_improved import (
    ImprovedConfidenceScorer,
    load_improved_reference_scores_from_json,
)
from .boilerplate_generator import BoilerplateGeneratorAgent
from .confidence_agent import ConfidenceScoringAgent
from .context_retrieval import ContextRetrievalAgent
from .human_review import HumanReviewAgent
from .md_summary import MdSummaryAgent
from .coverage_matrix import CoverageMatrixAgent
from .difficulty_agent import DifficultyCalibrationAgent
from .executable_grading import ExecutableGradingAgent
from .md_parser import MdParserAgent
from .originality_agent import OriginalityAgent
from .planner import PlannerAgent, RunState
from .scope_quality_agent import ScopeQualityAgent
from .question_generator import QuestionGeneratorAgent
from .supervisor import SupervisorAgent
from .syllabus_parser import SyllabusParserAgent
from .eval_comparator import EvalComparatorAgent
from .skill_triage import SkillTriageAgent
from ..schemas import ContextPack, SkillSet, StudentProfile, TriageResult


# ---------------------------------------------------------------------------
# Internal context bundle returned by the two context-builders
# ---------------------------------------------------------------------------

class _PipelineContext:
    __slots__ = (
        "analysis", "coverage", "skill_entries", "request",
        "skill_graph", "students",
        "confidence_scorer", "summary_text", "skillset",
        "context_pack", "triage",
    )

    def __init__(
        self,
        analysis: SyllabusAnalysis,
        coverage: CoverageMatrix,
        skill_entries: list[SkillEntry],
        request: AssessmentRequest,
        skill_graph: SkillGraph,
        students: list[StudentProfile],
        confidence_scorer: ImprovedConfidenceScorer,
        summary_text: str = "",
        skillset: SkillSet | None = None,
        context_pack: ContextPack | None = None,
        triage: TriageResult | None = None,
    ) -> None:
        self.analysis = analysis
        self.coverage = coverage
        self.skill_entries = skill_entries
        self.request = request
        self.skill_graph = skill_graph
        self.students = students
        self.confidence_scorer = confidence_scorer
        self.summary_text = summary_text
        self.skillset = skillset
        self.context_pack = context_pack or ContextPack()
        self.triage = triage


class Orchestrator:
    def __init__(self, settings: Settings | None = None, llm=None) -> None:
        self.settings = settings or Settings.load()
        configure_logging(self.settings.log_level)
        self.log = get_logger("orchestrator")
        self.run_logger = RunLogger(self.settings.log_db_path)
        self.memory = Memory(self.settings.memory_db_path)
        self.vectorstore = build_vectorstore(self.settings)
        self.llm = llm if llm is not None else make_client(self.settings)
        self.cheap_llm = make_cheap_client(self.settings)
        self.token_counter = TokenCounter(self.settings.provider, self.settings.model)

        from ..metrics import MetricsCollector
        self.metrics = MetricsCollector(self.settings.reports_dir)

        # LangGraph — compiled lazily on first run()
        self._graph = None
        # Non-serializable pipeline context per active run, keyed by run_id.
        # Using a dict instead of a single attribute prevents a concurrent (or
        # resumed) run from overwriting the context of a run still in flight.
        self._run_contexts: "dict[str, _PipelineContext]" = {}
        # Optional callback fired immediately after skill extraction completes.
        # Signature: (skill_count: int) -> None
        self.on_skills_extracted: "callable | None" = None

        def _llm(agent_name: str):
            """Return LLMClient for agent, respecting agent_models overrides."""
            return make_agent_client(self.settings, agent_name)

        def _kw(agent_name: str) -> dict:
            return dict(settings=self.settings, llm=_llm(agent_name),
                        memory=self.memory, vectorstore=self.vectorstore)

        kw = dict(settings=self.settings, llm=self.llm,
                  memory=self.memory, vectorstore=self.vectorstore)

        self.syllabus_parser = SyllabusParserAgent(**_kw("syllabus_parser"), token_counter=self.token_counter)
        self.md_parser = MdParserAgent(**_kw("md_parser"))
        self.skill_triage = SkillTriageAgent(**_kw("skill_triage"))
        self.coverage = CoverageMatrixAgent(**kw)
        self.generator = QuestionGeneratorAgent(**_kw("question_generator"), token_counter=self.token_counter)
        self.boilerplate = BoilerplateGeneratorAgent(**kw)
        self.difficulty = DifficultyCalibrationAgent(**_kw("difficulty_agent"), token_counter=self.token_counter)
        self.originality = OriginalityAgent(**kw)
        self.scope_quality = ScopeQualityAgent(**_kw("scope_quality"), token_counter=self.token_counter)
        self.executable_grading = ExecutableGradingAgent(**kw)
        self.confidence = ConfidenceScoringAgent(**kw)
        self.supervisor = SupervisorAgent(**_kw("supervisor_judge"))
        self.planner = PlannerAgent(**kw)
        self.md_summary = MdSummaryAgent(settings=self.settings, llm=_llm("md_summary"), memory=self.memory)
        self.context_retrieval = ContextRetrievalAgent(**kw)
        self.eval_comparator = EvalComparatorAgent(**_kw("eval_comparator"))
        self.human_review = HumanReviewAgent(**kw)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _stage(self, run_id: str, result, elapsed_ms: float = 0.0) -> None:
        self.run_logger.log_event(
            run_id, result.agent, result.status, "; ".join(result.messages)
        )
        self.log.info("stage", agent=result.agent, status=result.status,
                      msg="; ".join(result.messages))
        self.metrics.record_agent_call(run_id, result.agent, elapsed_ms)
        # Write per-question traces carried by the result payload.
        for trace in result.payload.get("question_traces", []):
            try:
                self.run_logger.trace_question(
                    run_id,
                    str(trace.get("qid", "")),
                    result.agent,
                    str(trace.get("decision", "")),
                    str(trace.get("reason", "")),
                )
            except Exception:  # noqa: BLE001
                pass

    def _validate(self, run_id, questions, coverage, analysis, request,
                  confidence_scorer=None, context_pack=None) -> None:
        """Run the full validation chain over the current question set.

        Parallel static validators run first with one auto-retry each, then
        ExecutableGradingAgent and ConfidenceScoringAgent run sequentially
        so their results are available for the confidence gate.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        for q in questions:
            self.coverage.mark(coverage, q.tested_skills)

        # Populated by the generator during the "generate" step — available before
        # validation starts, so scope_quality can run its skill-drift check inline.
        assigned_skills = getattr(self.generator, "last_assigned_skills", {})

        validators = [
            ("boilerplate", lambda: self.boilerplate.run(questions)),
            ("difficulty",  lambda: self.difficulty.run(questions)),
            ("originality", lambda: self.originality.run(
                questions, request.existing_questions,
                known_question_hashes=(context_pack.known_question_hashes if context_pack else None),
            )),
            # scope + quality + skill-drift merged: 1 LLM call (drift check) +
            # offline rules (realism/hiring/market scoring)
            ("scope_quality", lambda: self.scope_quality.run(questions, analysis, assigned_skills)),
        ]

        # Collect patches from parallel validators — applied atomically after all
        # complete so no validator reads a field half-written by another.
        all_patches: dict[str, dict] = {}  # qid → merged {field: value}

        submit_times: dict = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            pending = {}
            for name, fn in validators:
                fut = executor.submit(fn)
                submit_times[id(fut)] = time.time()
                pending[fut] = (name, fn)
            while pending:
                done_future = next(as_completed(pending))
                name, fn = pending.pop(done_future)
                elapsed_ms = int((time.time() - submit_times.pop(id(done_future), time.time())) * 1000)
                try:
                    result = done_future.result(timeout=60)
                    self._stage(run_id, result, elapsed_ms=elapsed_ms)
                    self.log.info("validator_done", name=name, elapsed_ms=elapsed_ms)
                    for qid, fields in result.payload.get("patches", {}).items():
                        all_patches.setdefault(qid, {}).update(fields)
                except Exception as e:
                    if not getattr(done_future, "_retried", False):
                        self.log.warning("validator_retry", name=name, error=str(e))
                        new_future = executor.submit(fn)
                        new_future._retried = True  # type: ignore[attr-defined]
                        submit_times[id(new_future)] = time.time()
                        pending[new_future] = (name, fn)
                    else:
                        self.log.error("validator_exhausted", name=name, error=str(e))
                        raise

        # Apply all validator patches in the main thread — fully serialized,
        # no concurrent writes to Question objects.
        q_by_id = {q.question_id: q for q in questions}
        for qid, fields in all_patches.items():
            q = q_by_id.get(qid)
            if q is None:
                continue
            for field, value in fields.items():
                setattr(q, field, value)

        t0 = time.time()
        self._stage(run_id, self.executable_grading.run(questions),
                    elapsed_ms=int((time.time() - t0) * 1000))

        # Eval comparator runs per-question so eval_comparison is populated
        # before confidence scoring reads it.
        for q in questions:
            t0 = time.time()
            self._stage(run_id, self.eval_comparator.run(q),
                        elapsed_ms=int((time.time() - t0) * 1000))

        t0 = time.time()
        self._stage(run_id,
                    self.confidence.run(questions, coverage, improved_scorer=confidence_scorer),
                    elapsed_ms=int((time.time() - t0) * 1000))

        # Human review interrupt — only runs when explicitly enabled
        if getattr(self.settings, "human_review_enabled", False):
            t0 = time.time()
            outputs_dir = getattr(self.settings, "outputs_dir", "outputs")
            self._stage(run_id,
                        self.human_review.run(questions, run_id, outputs_dir=outputs_dir),
                        elapsed_ms=int((time.time() - t0) * 1000))

    def _validate_skill_graph_coverage(
        self, skill_graph: SkillGraph, questions: list[Question], syllabus_skills: list[str]
    ) -> None:
        """Warn when a question tests a skill whose prerequisites are absent from the syllabus."""
        for q in questions:
            primary = getattr(q, "generation_skill", None)
            if not primary:
                continue
            valid, missing = skill_graph.validate_coverage(syllabus_skills, primary)
            if not valid:
                self.log.warning(
                    "skill_prereq_missing",
                    skill=primary,
                    question_id=q.question_id,
                    missing=sorted(missing),
                )

    def _load_students(self) -> list[StudentProfile]:
        import yaml
        path = Path(getattr(self.settings, "students_path", "config/students.yaml"))
        if not path.exists():
            self.log.warning("students_yaml_missing", path=str(path))
            return []
        try:
            data = yaml.safe_load(path.read_text()) or {}
            return [StudentProfile(**s) for s in data.get("students", [])]
        except Exception as exc:  # noqa: BLE001
            self.log.warning("students_yaml_load_failed", error=str(exc))
            return []

    def _make_confidence_scorer(self) -> ImprovedConfidenceScorer:
        """Return an ImprovedConfidenceScorer, optionally seeded with ground-truth data.

        The scorer's hardcoded difficulty multipliers (easy: +12%, hard: -15%)
        and skill factors are always applied.  When evaluations/confidence.json
        exists the reference_scores are also loaded, which lets the scorer bias
        its predictions toward empirical student pass-rates for known skills.
        Without the file the multipliers still run — the scorer is never skipped.
        """
        evaluations_dir = Path(getattr(self.settings, "evaluations_dir", "evaluations"))
        reference_scores = load_improved_reference_scores_from_json(str(evaluations_dir))
        return ImprovedConfidenceScorer(reference_scores)

    def _build_skill_graph(self, skill_entries: list[SkillEntry]) -> SkillGraph:
        """Build and return a SkillGraph from the extracted skill entries."""
        graph = SkillGraph()
        graph.build_from_skills(skill_entries)
        n_edges = len(graph.edges)
        n_nodes = len(graph.skills)
        self.log.info("skill_graph_built", nodes=n_nodes, edges=n_edges)
        return graph

    def _attach_costs(self, pkg: AssessmentPackage) -> None:
        pq = self.token_counter.per_question()
        for q in pkg.questions:
            stats = pq.get(q.question_id)
            if stats:
                q.tokens_used = stats["tokens"]
                q.generation_cost_usd = stats["cost_usd"]
                q.generation_attempts = stats["attempts"]

    def _finish_run(self, run_id: str, pkg: AssessmentPackage, quality: list) -> None:
        """Log run completion metrics — called by the supervise graph node."""
        import time
        approved_count = len(pkg.approved_questions)
        bar_passed = sum(1 for x in quality if x.passed) if quality else 0
        self.run_logger.finish_run(
            run_id,
            n_questions=len(pkg.questions),
            n_approved=approved_count,
            supervisor=pkg.supervisor.supervisor_status,
            score=pkg.supervisor.validation_score,
        )
        self.metrics.end_run(
            run_id,
            total_tokens=self.token_counter.total_tokens,
            cost_usd=self.token_counter.estimated_cost(),
            questions_generated=len(pkg.questions),
            questions_passed=bar_passed,
        )
        self.log.info(
            "run_done", run_id=run_id,
            status=pkg.supervisor.supervisor_status,
            approved=approved_count,
            bar_passed=bar_passed,
            coverage_pct=pkg.portfolio_coverage_score,
            total_tokens=self.token_counter.total_tokens,
            est_cost_usd=round(self.token_counter.estimated_cost(), 6),
        )
        # Save approved questions as few-shot examples AND to the originality
        # memory/vectorstore. Both happen here (post-supervisor) so only genuinely
        # approved questions ever enter these stores — rejected questions must never
        # pollute future runs' originality checks.
        _FEW_SHOT_MIN_CONFIDENCE = 88.0
        vectorstore_updated = False
        for q in pkg.approved_questions:
            conf = getattr(q, "confidence", None)
            score = conf.confidence if conf and hasattr(conf, "confidence") else 0.0

            # Always remember the stem of approved questions so future originality
            # checks know this question exists and won't generate an exact copy.
            try:
                q_text = " ".join([q.title, q.scenario, q.objective,
                                   " ".join(q.tested_skills)])
                self.memory.remember_question(q.question_id, q.title, q_text)
                self.vectorstore.add(q.question_id, q_text, topic=getattr(q, "topic", ""))
                # Mark as approved in Qdrant payload
                if hasattr(self.vectorstore, "_client"):
                    from qdrant_client.models import SetPayload
                    import hashlib
                    point_id = int(hashlib.md5(q.question_id.encode()).hexdigest(), 16) % (2 ** 63)
                    self.vectorstore._client.set_payload(
                        collection_name=self.vectorstore._collection,
                        payload={"status": "approved"},
                        points=[point_id],
                    )
                vectorstore_updated = True
            except Exception as exc:  # noqa: BLE001
                self.log.warning("originality_memory_save_failed",
                                 qid=q.question_id, error=str(exc))

            # Few-shot: only high-confidence questions seed future generation.
            if score < _FEW_SHOT_MIN_CONFIDENCE:
                continue
            skill = q.tested_skills[0] if q.tested_skills else ""
            if not skill:
                continue
            try:
                import json as _json
                starter = q.files_to_edit[0].starter_code if q.files_to_edit else ""
                reference = q.files_to_edit[0].reference_solution if q.files_to_edit else ""
                prompt_hash = getattr(self.generator, "_prompt_hash", None)
                self.memory.save_few_shot(
                    skill=skill,
                    difficulty=q.difficulty.value,
                    confidence_score=score,
                    question_json=_json.dumps(q.model_dump(), ensure_ascii=False),
                    starter_code=starter,
                    reference_code=reference,
                    prompt_hash=prompt_hash,
                )
                self.log.info("few_shot_saved", qid=q.question_id, skill=skill,
                              difficulty=q.difficulty.value, confidence=score)
            except Exception as exc:  # noqa: BLE001
                self.log.warning("few_shot_save_failed", qid=q.question_id, error=str(exc))

        if vectorstore_updated:
            try:
                self.vectorstore.save()
            except Exception as exc:  # noqa: BLE001
                self.log.warning("vectorstore_save_failed", error=str(exc))

        # Upsert rejected questions to Qdrant with status=rejected so they are
        # searchable for analysis but clearly labelled as not passing QA.
        rejected = [q for q in pkg.questions if q not in pkg.approved_questions]
        for q in rejected:
            try:
                q_text = " ".join(filter(None, [
                    getattr(q, "title", ""),
                    getattr(q, "scenario", ""),
                    getattr(q, "objective", ""),
                    " ".join(getattr(q, "tested_skills", [])),
                ]))
                self.vectorstore.add(q.question_id, q_text, topic=getattr(q, "topic", ""))
                # Patch payload with status if the store supports it (SemanticVectorStore)
                if hasattr(self.vectorstore, "_client"):
                    from qdrant_client.models import SetPayload
                    import hashlib
                    point_id = int(hashlib.md5(q.question_id.encode()).hexdigest(), 16) % (2 ** 63)
                    self.vectorstore._client.set_payload(
                        collection_name=self.vectorstore._collection,
                        payload={"status": "rejected"},
                        points=[point_id],
                    )
            except Exception as exc:  # noqa: BLE001
                self.log.warning("rejected_vectorstore_save_failed",
                                 qid=q.question_id, error=str(exc))

        # Release the per-run context so it doesn't accumulate across many runs
        self._run_contexts.pop(run_id, None)

    def _build_graph(self):
        """Lazily compile the LangGraph assessment graph."""
        from ..graph.builder import build_assessment_graph
        if self._graph is None:
            self._graph = build_assessment_graph(self)
        return self._graph

    # ------------------------------------------------------------------ #
    # Context builders — two input modes, one output type
    # ------------------------------------------------------------------ #

    def _build_context_from_text(
        self, request: AssessmentRequest, run_id: str
    ) -> _PipelineContext:
        """Build pipeline context from a text-based AssessmentRequest."""
        r = self.syllabus_parser.run(request)
        self._stage(run_id, r)
        analysis = SyllabusAnalysis(**r.payload["analysis"])

        r = self.coverage.run(analysis.skills)
        self._stage(run_id, r)
        coverage = CoverageMatrix(**r.payload["coverage"])

        skill_entries: list[SkillEntry] = [
            SkillEntry(skill=s, section="syllabus") for s in analysis.skills
        ]
        skill_graph = self._build_skill_graph(skill_entries)

        return _PipelineContext(
            analysis=analysis,
            coverage=coverage,
            skill_entries=skill_entries,
            request=request,
            skill_graph=skill_graph,
            students=self._load_students(),
            confidence_scorer=self._make_confidence_scorer(),
        )

    def _build_context_from_md(
        self, md_path: Path, request: AssessmentRequest, run_id: str
    ) -> _PipelineContext:
        """Build pipeline context by summarising and parsing an MD file."""
        import hashlib as _hashlib

        raw = md_path.read_text(encoding="utf-8")
        md_hash = _hashlib.md5(raw.encode()).hexdigest()

        # Reuse the cached summary when the file hasn't changed — avoids one
        # LLM call (~$0.01) on every re-run of the same curriculum.
        cached_summary = MdSummaryAgent.load_cached(self.settings.skills_dir, md_hash)
        if cached_summary:
            self.log.info("md_summary_cache_hit", md_hash=md_hash)
            summary_text = cached_summary
        else:
            sres = self.md_summary.run(md_path)
            self._stage(run_id, sres)
            summary_text = sres.payload["summary"]
            md_hash = sres.payload["md_hash"]

        skillset = self.md_parser.extract_from_text(summary_text, md_path, md_hash)
        if not skillset.skills:
            raise ValueError(f"No skills extracted from {md_path.name}")
        skill_entries: list[SkillEntry] = skillset.skills
        self.log.info("skills_extracted", count=len(skill_entries))

        syllabus = [s.skill for s in skill_entries]
        analysis = SyllabusAnalysis(
            skills=syllabus, concepts=[], apis=[], config_elements=[],
            ros_components=[], difficulty_range="easy-hard",
        )
        coverage = CoverageMatrix()
        for s in syllabus:
            coverage.matrix[s] = False

        request = request.model_copy(
            update={"syllabus": syllabus, "num_questions": max(request.num_questions, 3)}
        )

        skill_graph = self._build_skill_graph(skill_entries)

        return _PipelineContext(
            analysis=analysis,
            coverage=coverage,
            skill_entries=skill_entries,
            request=request,
            skill_graph=skill_graph,
            students=self._load_students(),
            confidence_scorer=self._make_confidence_scorer(),
            summary_text=summary_text,
            skillset=skillset,
        )

    def run(self, request: AssessmentRequest) -> AssessmentPackage:
        """Generate an assessment from an AssessmentRequest via LangGraph.

        If ``request.md_path`` is set, skills are extracted from that file and
        the request's syllabus list is replaced with the extracted skills.
        Otherwise the request's syllabus is used directly via SyllabusParserAgent.
        """
        run_id = uuid.uuid4().hex[:12]
        graph = self._build_graph()
        self.run_logger.start_run(run_id, request.topic)
        self.metrics.start_run(run_id, request.topic)
        self.log.info(
            "run_start", run_id=run_id, topic=request.topic,
            provider=self.settings.provider,
            mode="md" if request.md_path else "text",
            engine="langgraph",
        )

        initial_state: dict = {
            "run_id": run_id,
            "request": request.model_dump(),
            "analysis": None,
            "coverage": None,
            "skill_entries": [],
            "summary_text": "",
            "skillset": None,
            "context_pack": None,
            "triage": None,
            "questions": [],
            "accumulated_questions": [],
            "batch_offset": 0,
            "quality": None,
            "feedback": {},
            "attempts": 0,
            "step": 1,
            "budget_tokens": None,
            "budget_calls": None,
            "pkg": None,
            "error": None,
        }

        config = {"configurable": {"thread_id": run_id}}
        try:
            final_state = graph.invoke(initial_state, config=config)
        except Exception as e:
            self.log.error("run_failed", run_id=run_id, error=str(e))
            raise

        pkg = AssessmentPackage(**final_state["pkg"])
        # Attach sidecar data that can't survive model_dump() serialization.
        # Read summary_text and skillset directly from final_state (set by build_context
        # node) rather than _run_contexts, which may be missed if the key is not found.
        summary_text = final_state.get("summary_text") or ""
        if summary_text:
            pkg._summary_text = summary_text  # type: ignore[attr-defined]
        raw_skillset = final_state.get("skillset")
        if raw_skillset:
            try:
                pkg._skillset = SkillSet(**raw_skillset)  # type: ignore[attr-defined]
            except Exception:
                pass
        pkg._token_counter = self.token_counter  # type: ignore[attr-defined]
        return pkg

    def run_from_md(
        self, md_path: str | Path, run_id: str | None = None
    ) -> AssessmentPackage:
        """Generate from an MD teaching-material file.

        Thin wrapper: builds an AssessmentRequest with md_path set and calls
        run().  Pass ``run_id`` to resume a previously failed run.
        """
        md_path = Path(md_path)
        topic_name = md_path.stem
        request = AssessmentRequest(
            topic=topic_name,
            syllabus=[topic_name],   # placeholder — overwritten by MD extraction
            md_path=str(md_path),
            num_questions=3,
        )
        if run_id:
            self.log.info("resume_requested", run_id=run_id)
            return self._run_with_id(request, run_id)
        return self.run(request)

    def _run_with_id(self, request: AssessmentRequest, run_id: str) -> AssessmentPackage:
        """Like run() but uses a caller-supplied run_id (LangGraph thread resume)."""
        graph = self._build_graph()
        self.run_logger.start_run(run_id, request.topic)
        self.metrics.start_run(run_id, request.topic)
        self.log.info("resume_requested", run_id=run_id)

        initial_state: dict = {
            "run_id": run_id,
            "request": request.model_dump(),
            "analysis": None,
            "coverage": None,
            "skill_entries": [],
            "summary_text": "",
            "skillset": None,
            "context_pack": None,
            "triage": None,
            "questions": [],
            "accumulated_questions": [],
            "batch_offset": 0,
            "quality": None,
            "feedback": {},
            "attempts": 0,
            "step": 1,
            "budget_tokens": None,
            "budget_calls": None,
            "pkg": None,
            "error": None,
        }
        config = {"configurable": {"thread_id": run_id}}
        try:
            final_state = graph.invoke(initial_state, config=config)
        except Exception as e:
            self.log.error("run_failed", run_id=run_id, error=str(e))
            raise
        pkg = AssessmentPackage(**final_state["pkg"])
        summary_text = final_state.get("summary_text") or ""
        if summary_text:
            pkg._summary_text = summary_text  # type: ignore[attr-defined]
        raw_skillset = final_state.get("skillset")
        if raw_skillset:
            try:
                pkg._skillset = SkillSet(**raw_skillset)  # type: ignore[attr-defined]
            except Exception:
                pass
        pkg._token_counter = self.token_counter  # type: ignore[attr-defined]
        return pkg

    def run_parse(self, md_path: str | Path) -> SkillSet:
        """Parse a markdown file and extract skills to skills/skills.yaml."""
        md_path = Path(md_path)
        self.log.info("parse_start", md_file=md_path.name)
        r = self.md_parser.run(md_path)
        return SkillSet(**r.payload["skills"])
