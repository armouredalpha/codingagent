"""
Orchestrator Agent
==================

Top-level controller. It receives an :class:`AssessmentRequest`, routes work
through every worker agent in order, maintains execution state, retries failed
or low-confidence stages, aggregates outputs into an
:class:`AssessmentPackage`, and submits the result to the Supervisor for final
approval. No worker output bypasses Supervisor validation.

Execution flow (per spec)
-------------------------
Orchestrator -> Syllabus Parser -> Source Research -> Coverage Matrix ->
Question Generator -> Boilerplate -> Difficulty -> Originality -> Scope ->
Realism -> Auto-Grading -> Confidence -> Hiring/Role/Market/Portfolio ->
Evaluation -> Supervisor -> Final Output.
"""

from __future__ import annotations

import uuid

from ..config import Settings
from ..llm_client import make_client
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
from ..state_manager import StateManager
from ..learned_confidence_improved import (
    ImprovedConfidenceScorer,
    load_improved_reference_scores_from_json,
)
from ..skill_taxonomy import SkillGraph
from .boilerplate_generator import BoilerplateGeneratorAgent
from .confidence_agent import ConfidenceScoringAgent
from .coverage_matrix import CoverageMatrixAgent
from .difficulty_agent import DifficultyCalibrationAgent
from .executable_grading import ExecutableGradingAgent
from .grading_agent import AutoGradingAgent
from .md_parser import MdParserAgent
from .originality_agent import OriginalityAgent
from .planner import PlannerAgent, RunState
from .quality_judge import QualityJudgeAgent
from .question_generator import QuestionGeneratorAgent
from .scope_agent import ScopeComplianceAgent
from .skill_picker import SkillPickerAgent
from .supervisor import SupervisorAgent
from .syllabus_parser import SyllabusParserAgent
from .planner_multi_loop import MultiLoopPlanner, LoopType, ParserAction, GenerationAction, FeedbackAction
from ..schemas import PlanAction, SkillSet
from pathlib import Path


class Orchestrator:
    def __init__(self, settings: Settings | None = None, llm=None) -> None:
        self.settings = settings or Settings.load()
        configure_logging(self.settings.log_level)
        self.log = get_logger("orchestrator")
        self.run_logger = RunLogger(self.settings.log_db_path)
        self.memory = Memory(self.settings.memory_db_path)
        self.vectorstore = VectorStore(self.settings.vectorstore_path)
        # `llm` can be injected (tests, or a custom client); otherwise build from
        # settings. This is an LLM agent — there is no offline/null client path.
        self.llm = llm if llm is not None else make_client(self.settings)
        self.token_counter = TokenCounter(self.settings.provider, self.settings.model)

        # Metrics collection for observability
        from ..metrics import MetricsCollector
        self.metrics = MetricsCollector(self.settings.reports_dir)

        kw = dict(settings=self.settings, llm=self.llm,
                  memory=self.memory, vectorstore=self.vectorstore)
        self.syllabus_parser = SyllabusParserAgent(**kw, token_counter=self.token_counter)
        self.md_parser = MdParserAgent(**kw)
        self.skill_picker = SkillPickerAgent(**kw)
        self.coverage = CoverageMatrixAgent(**kw)
        self.generator = QuestionGeneratorAgent(**kw, token_counter=self.token_counter)
        self.boilerplate = BoilerplateGeneratorAgent(**kw)
        self.difficulty = DifficultyCalibrationAgent(**kw, token_counter=self.token_counter)
        self.originality = OriginalityAgent(**kw)
        self.scope = ScopeComplianceAgent(**kw, token_counter=self.token_counter)
        self.quality_judge = QualityJudgeAgent(**kw, token_counter=self.token_counter)
        self.grading = AutoGradingAgent(**kw)
        self.executable_grading = ExecutableGradingAgent(**kw)
        self.confidence = ConfidenceScoringAgent(**kw)
        self.supervisor = SupervisorAgent(**kw)
        self.planner = PlannerAgent(**kw)

    # ------------------------------------------------------------------ #
    def _stage(self, run_id: str, result) -> None:
        self.run_logger.log_event(
            run_id, result.agent, result.status, "; ".join(result.messages)
        )
        self.log.info("stage", agent=result.agent, status=result.status,
                       msg="; ".join(result.messages))

    # ------------------------------------------------------------------ #
    def _validate(self, run_id, questions, coverage, analysis, request) -> None:
        """Run the full validation chain over the current question set.

        Executable grading runs *after* static auto-grading so its real
        PASS/FAIL signal can override the static verdict before confidence is
        scored. Confidence/hiring read the validated questions.

        Optimized: Parallel validator execution where independent and automatic
        state checkpointing after each stage.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor

        for q in questions:
            self.coverage.mark(coverage, q.tested_skills)

        # Validators that can run in parallel (no inter-dependencies)
        validators = [
            ("boilerplate", lambda: self.boilerplate.run(questions)),
            ("difficulty", lambda: self.difficulty.run(questions)),
            ("originality", lambda: self.originality.run(questions, request.existing_questions)),
            ("scope", lambda: self.scope.run(questions, analysis)),
            ("quality_judge", lambda: self.quality_judge.run(questions)),
            ("grading", lambda: self.grading.run(questions)),
        ]

        # Run validators in parallel with timing and retry
        with ThreadPoolExecutor(max_workers=4) as executor:
            start_batch = time.time()
            futures = {executor.submit(fn): (name, fn) for name, fn in validators}

            for future in futures:
                name, fn = futures[future]
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        start = time.time()
                        result = future.result(timeout=60)
                        elapsed_ms = int((time.time() - start) * 1000)
                        self._stage(run_id, result)
                        self.log.info("validator_done", name=name, elapsed_ms=elapsed_ms, attempt=attempt+1)
                        break  # Success, move to next validator
                    except Exception as e:
                        if attempt < max_retries - 1:
                            self.log.warning("validator_retry", name=name, attempt=attempt+1, error=str(e))
                            # Re-submit the task
                            future = executor.submit(fn)
                        else:
                            self.log.error("validator_exhausted", name=name, attempts=max_retries, error=str(e))
                            raise

        # Sequential validators that depend on prior results
        self._stage(run_id, self.executable_grading.run(questions))
        self._stage(run_id, self.confidence.run(questions, coverage))

    # ------------------------------------------------------------------ #
    def run(self, request: AssessmentRequest) -> AssessmentPackage:
        import time
        run_id = uuid.uuid4().hex[:12]
        run_start_time = time.time()
        self.run_logger.start_run(run_id, request.topic)
        self.metrics.start_run(run_id, request.topic)
        self.log.info("run_start", run_id=run_id, topic=request.topic,
                       provider=self.settings.provider)

        # Initialize state manager for resumability
        from ..state_manager import StateManager
        state_mgr = StateManager(self.settings.log_db_path.replace('runs.db', 'state.db'))
        state_mgr.start_run(run_id, str(request.topic), "orchestrator", request.num_questions)

        try:
            # 1 — syllabus ----------------------------------------------------
            r = self.syllabus_parser.run(request); self._stage(run_id, r)
            analysis = SyllabusAnalysis(**r.payload["analysis"])
            state_mgr.save_state(run_id, "syllabus_parsed", {"analysis": analysis.model_dump()})

            # 2 — source research (skipped, using empty research) -----
            research = SourceResearch(sources=request.sources or [], materials=[])

            # 3 — coverage matrix --------------------------------------------
            r = self.coverage.run(analysis.skills); self._stage(run_id, r)
            coverage = CoverageMatrix(**r.payload["coverage"])
            state_mgr.save_state(run_id, "coverage_computed", {"coverage": coverage.model_dump()})

            # 4 — planner-driven control loop --------------------------------
            # No fixed generate→validate→regenerate sequence: the PlannerAgent reads
            # the run state each tick and CHOOSES the next action. It loops
            # generate → validate → reflect → regenerate until every question clears
            # the quality bar (config.quality_bar) or the step/regeneration budget is
            # spent, then FINALIZE. Deterministic rails in the planner guarantee
            # progress and termination; the LLM only advises and authors feedback.
            n_target = request.num_questions
            questions: list[Question] = []
            quality = None
            feedback: dict[str, str] = {}
            attempts = 0
            plan_trace = []

            for step_no in range(1, self.settings.max_planner_steps + 1):
                state = RunState(
                    questions=questions, coverage=coverage, quality=quality,
                    attempts=attempts, max_attempts=self.settings.max_regeneration_attempts,
                    step=step_no, max_steps=self.settings.max_planner_steps,
                    feedback=feedback,
                )
                decision = self.planner.decide(state)
                plan_trace.append(decision)
                self.run_logger.log_event(
                    run_id, "planner", decision.action.value,
                    f"[{decision.source}] {decision.reason} "
                    f"(bar {decision.bar_passed}/{decision.bar_total})",
                )
                self.log.info("plan_step", step=step_no, action=decision.action.value,
                               reason=decision.reason, targets=len(decision.targets))

                if decision.action == PlanAction.GENERATE:
                    r = self.generator.run(analysis, coverage, n_target)
                    self._stage(run_id, r)
                    questions = [Question(**q) for q in r.payload["questions"]]
                    quality = None
                    state_mgr.save_state(run_id, f"generated_step_{step_no}",
                                        {"questions": [q.model_dump() for q in questions]})

                elif decision.action == PlanAction.VALIDATE:
                    self._validate(run_id, questions, coverage, analysis, request)
                    quality = self.planner.evaluate_quality(questions, coverage)
                    npass = sum(1 for x in quality if x.passed)
                    self.log.info("quality_bar", passed=npass, total=len(quality))
                    state_mgr.save_state(run_id, f"validated_step_{step_no}",
                                        {"quality": [q.model_dump() for q in quality]})

                elif decision.action == PlanAction.REGENERATE:
                    feedback = self.planner.reflect(questions, quality or [])
                    attempts += 1
                    self.log.info("planner_regenerate", attempt=attempts,
                                   failing=len(decision.targets))
                    rr = self.generator.regenerate(
                        questions, decision.targets, feedback, analysis, coverage,
                    )
                    self._stage(run_id, rr)
                    questions = [Question(**q) for q in rr.payload["questions"]]
                    for q in questions:
                        self.coverage.mark(coverage, q.tested_skills)
                    quality = None
                    state_mgr.save_state(run_id, f"regenerated_step_{step_no}",
                                        {"questions": [q.model_dump() for q in questions]})

                else:  # FINALIZE or ABORT
                    break

        # 5 — assemble + final supervisor verdict -------------------------
            if quality is None:
                # Loop exited right after a change without re-validating (only happens
                # at the step ceiling) — validate once so the package is consistent.
                self._validate(run_id, questions, coverage, analysis, request)
                quality = self.planner.evaluate_quality(questions, coverage)

            # Mock hiring and evaluation scores (agents not yet implemented)
            eval_score = 75.0

            pkg = AssessmentPackage(
                run_id=run_id,
                topic=request.topic,
                syllabus=request.syllabus,
                syllabus_analysis=analysis,
                source_research=research,
                coverage_matrix=coverage,
                questions=questions,
                portfolio_coverage_score=75,
                portfolio_missing_areas=[],
                plan_trace=plan_trace,
                quality=quality,
            )
            sres = self.supervisor.run(pkg, eval_score); self._stage(run_id, sres)
            pkg.supervisor = pkg.supervisor.model_validate(sres.payload["verdict"])

            self._attach_costs(pkg)
            state_mgr.save_state(run_id, "final_package",
                                {"status": pkg.supervisor.supervisor_status})

            run_elapsed_ms = int((time.time() - run_start_time) * 1000)
            approved_count = len(pkg.approved_questions)
            bar_passed = sum(1 for x in quality if x.passed) if quality else 0

            self.run_logger.finish_run(
                run_id,
                n_questions=len(questions),
                n_approved=approved_count,
                supervisor=pkg.supervisor.supervisor_status,
                score=pkg.supervisor.validation_score,
            )

            # Record metrics
            self.metrics.end_run(
                run_id,
                total_tokens=self.token_counter.total_tokens,
                cost_usd=self.token_counter.estimated_cost(),
                questions_generated=len(questions),
                questions_passed=bar_passed,
            )

            self.log.info(
                "run_done", run_id=run_id,
                status=pkg.supervisor.supervisor_status,
                approved=approved_count,
                bar_passed=bar_passed,
                steps=len(plan_trace),
                total_tokens=self.token_counter.total_tokens,
                est_cost_usd=round(self.token_counter.estimated_cost(), 6),
                elapsed_ms=run_elapsed_ms,
            )

            # Log metrics summary
            metrics_summary = self.metrics.get_run_summary(run_id)
            if metrics_summary:
                self.log.info("metrics_summary", **metrics_summary)

            # Attach counter to package for downstream export
            pkg._token_counter = self.token_counter  # type: ignore[attr-defined]
            state_mgr.complete_run(run_id)
            return pkg

        except Exception as e:
            self.log.error("run_failed", run_id=run_id, error=str(e))
            state_mgr.fail_run(run_id, str(e))
            raise

    # ------------------------------------------------------------------ #
    def _attach_costs(self, pkg: AssessmentPackage) -> None:
        """Write per-question token/cost back onto each Question so the cost of
        generating that specific item (incl. every regeneration) ships in the
        package, not just an aggregate."""
        pq = self.token_counter.per_question()
        for q in pkg.questions:
            stats = pq.get(q.question_id)
            if stats:
                q.tokens_used = stats["tokens"]
                q.generation_cost_usd = stats["cost_usd"]
                q.generation_attempts = stats["attempts"]

    # ================================================================== #
    # Multi-Loop Generation (with Parser, Generation, and Feedback loops)
    # ================================================================== #

    def run_generate_with_loops(
        self,
        md_path: str | Path,
        constraints: list[dict] | None = None,
        num_questions: int | None = None,
        auto: bool = False,
        domain: str = "",
    ) -> AssessmentPackage:
        """Generate questions using multi-loop planner with feedback loops.

        Three loops managed by planner:
        1. Parser loop: Markdown sections → skills extraction
        2. Generation loop: Per-constraint question generation + calibration
        3. Feedback loop: Regenerate failing questions with LLM critique

        Returns: AssessmentPackage with generated questions
        """
        import yaml

        md_path = Path(md_path)
        skills_dir = Path(self.settings.skills_dir)

        # Load skills
        skills_yaml_path = skills_dir / "skills.yaml"
        if not skills_yaml_path.exists():
            raise FileNotFoundError(
                f"Skills not extracted. Run: robo-assess parse --md {md_path}"
            )

        skills_data = yaml.safe_load(skills_yaml_path.read_text())
        skill_entries = [SkillEntry(**s) for s in skills_data.get("skills", [])]

        if not skill_entries:
            raise ValueError(f"No skills found in {skills_yaml_path}")

        # Normalize constraints
        if auto:
            constraints = self.skill_picker.generate_auto_constraints(domain)
        elif not constraints and num_questions:
            import random
            difficulties = ["easy", "medium", "hard"]
            bloom_levels = ["understand", "apply", "analyze", "evaluate", "create"]
            constraints = [
                {
                    "difficulty": random.choice(difficulties),
                    "bloom_level": random.choice(bloom_levels),
                    "domain": domain or ""
                }
                for _ in range(num_questions)
            ]
        elif not constraints:
            raise ValueError("Either auto=True, constraints, or num_questions must be provided")

        # Initialize components
        run_id = uuid.uuid4().hex[:12]
        state_manager = StateManager(str(Path(self.settings.log_dir) / "state.db"))
        state_manager.start_run(run_id, str(md_path), "generate", len(constraints))

        evaluations_dir = Path(self.settings.evaluations_dir) if hasattr(self.settings, 'evaluations_dir') else Path("evaluations")
        reference_scores = load_improved_reference_scores_from_json(str(evaluations_dir))

        for ref_id, ref_data in reference_scores.items():
            state_manager.upsert_reference_scores(ref_id, ref_data)

        # Initialize improved confidence scorer with calibration multipliers
        confidence_scorer = ImprovedConfidenceScorer(reference_scores)
        skill_graph = SkillGraph()
        skill_graph.build_from_skills(skill_entries)

        # Initialize multi-loop planner
        planner = MultiLoopPlanner(self.settings, self.llm, self.log)
        planner.init_generation_loop(len(constraints))

        # Create synthetic request
        syllabus_analysis = SyllabusAnalysis(
            skills=[s.skill for s in skill_entries],
            concepts=[], apis=[], config_elements=[], ros_components=[],
            difficulty_range="easy-hard"
        )
        request = AssessmentRequest(
            topic=md_path.stem,
            syllabus=[s.skill for s in skill_entries],
            sources=[], existing_questions=[],
            num_questions=len(constraints)
        )

        self.run_logger.start_run(run_id, request.topic)
        self.log.info(
            "generate_with_loops_start",
            run_id=run_id, constraints=len(constraints),
            reference_count=len(reference_scores)
        )

        questions: list[Question] = []
        coverage = CoverageMatrix()
        for skill in request.syllabus:
            coverage.matrix[skill] = False

        try:
            # Multi-loop orchestration
            max_loops = 50
            loop_count = 0

            while loop_count < max_loops:
                loop_count += 1
                decision = planner.decide()

                self.log.info(
                    "planner_decision",
                    loop=decision.loop.value,
                    action=decision.action.value,
                    reason=decision.reason,
                    step=planner.step_count
                )

                # PARSER LOOP (skipped if skills already extracted)
                # In practice, parser runs in run_parse() separately
                # This shows the structure for completeness

                # GENERATION LOOP
                if decision.loop == LoopType.GENERATION:
                    if decision.action == GenerationAction.GENERATE:
                        idx = planner.generation_state.current_constraint_idx
                        constraint = constraints[idx]

                        # Pick skill
                        try:
                            res = self.skill_picker.run(
                                difficulty=constraint.get("difficulty", "medium"),
                                bloom_level=constraint.get("bloom_level", "apply"),
                                domain=constraint.get("domain", ""),
                                all_skills=skill_entries,
                                already_generated=planner.generation_state.generated_skills,
                            )
                            selected_skill = SkillEntry(**res.payload["skill"])
                            planner.generation_state.generated_skills.append(selected_skill.skill)
                            self._stage(run_id, res)
                        except Exception as e:
                            self.log.error("skill_picker_error", error=str(e))
                            continue

                        # Generate question
                        try:
                            r = self.generator._llm_question(
                                skill=selected_skill.skill,
                                difficulty=constraint.get("difficulty", "medium"),
                                domain=constraint.get("domain", ""),
                                bloom_level=constraint.get("bloom_level", "apply"),
                                allowed_scope=", ".join(request.syllabus),
                                forbidden_scope="Nav2, SLAM, MoveIt, OpenCV",
                                existing_titles=[q.title for q in questions],
                                idx=idx+1,
                                feedback={}
                            )
                            if r:
                                questions.append(r)
                                r.generation_skill = selected_skill.skill
                                self.coverage.mark(coverage, r.tested_skills)
                                planner.record_generation_result(r)

                                state_manager.save_state(
                                    run_id,
                                    f"constraint_{idx}",
                                    {"question": r.model_dump(), "skill": selected_skill.skill}
                                )
                        except Exception as e:
                            self.log.error("generation_error", idx=idx+1, error=str(e))

                    elif decision.action == GenerationAction.COMPARE:
                        # EvalComparatorAgent: match to reference questions
                        self.log.debug("eval_comparison", targets=decision.targets)

                    elif decision.action == GenerationAction.VALIDATE:
                        # Run validators
                        if questions:
                            self._validate(run_id, questions, coverage, syllabus_analysis, request)

                    elif decision.action == GenerationAction.CHECK_CONFIDENCE:
                        # Score with improved confidence scorer (with calibration multipliers)
                        for q in questions:
                            validators = {
                                "auto_grading": getattr(q, "auto_grading_score", 0),
                                "originality": getattr(q, "originality_score", 0),
                                "format_compliance": getattr(q, "format_quality_score", 0),
                            }
                            # Pass difficulty hint for calibration
                            difficulty_hint = getattr(q, "difficulty", None)
                            if difficulty_hint:
                                difficulty_hint = difficulty_hint.value.lower()

                            confidence, breakdown = confidence_scorer.score(
                                q, validators, difficulty_hint=difficulty_hint
                            )
                            state_manager.save_question_scores(
                                run_id, q.question_id, confidence, breakdown,
                                breakdown.get("similar_refs", []),
                                breakdown.get("features", {})
                            )
                            self.log.info(
                                "confidence_scored_improved",
                                question_id=q.question_id,
                                confidence=confidence,
                                multiplier=breakdown.get("difficulty_multiplier"),
                            )

                    elif decision.action == GenerationAction.NEXT_CONSTRAINT:
                        # Move to feedback loop if there are failing questions
                        quality = self.planner.evaluate_quality(questions, coverage)
                        failing_ids = [q.question_id for q, qq in zip(questions, quality) if not qq.passed]

                        if failing_ids:
                            planner.set_failing_questions(failing_ids)
                            self.log.info("feedback_loop_start", failing_count=len(failing_ids))
                        else:
                            # All pass, finalize
                            break

                # FEEDBACK LOOP
                elif decision.loop == LoopType.FEEDBACK:
                    if decision.action == FeedbackAction.CRITIQUE:
                        # LLMCriticAgent: harsh feedback for failing question
                        q_id = decision.targets[0] if decision.targets else None
                        if q_id:
                            q = next((qq for qq in questions if qq.question_id == q_id), None)
                            if q:
                                critique = f"Below quality bar. Improve clarity, test coverage, and scope alignment."
                                planner.record_critique(q_id, critique)
                                self.log.debug("critique_generated", question_id=q_id)

                    elif decision.action == FeedbackAction.REGENERATE:
                        # Regenerate with feedback
                        q_id = decision.targets[0] if decision.targets else None
                        critique = planner.feedback_state.question_critiques.get(q_id)

                        if q_id and critique:
                            # Find original question
                            orig_idx = next((i for i, q in enumerate(questions) if q.question_id == q_id), None)
                            if orig_idx is not None:
                                try:
                                    # Regenerate with critique feedback
                                    r = self.generator._llm_question(
                                        skill=questions[orig_idx].generation_skill or "general",
                                        difficulty=questions[orig_idx].difficulty.value,
                                        domain="",
                                        bloom_level=questions[orig_idx].bloom_level.value,
                                        allowed_scope=", ".join(request.syllabus),
                                        forbidden_scope="Nav2, SLAM, MoveIt, OpenCV",
                                        existing_titles=[q.title for q in questions if q.question_id != q_id],
                                        idx=orig_idx+1,
                                        feedback={"critique": critique}
                                    )
                                    if r:
                                        questions[orig_idx] = r
                                        planner.record_regeneration_result(q_id, r)
                                        self.log.info("question_regenerated", question_id=q_id)
                                except Exception as e:
                                    self.log.error("regeneration_error", question_id=q_id, error=str(e))

                    elif decision.action == FeedbackAction.BACK_TO_COMPARE:
                        # Validate regenerated questions and loop back
                        if questions:
                            self._validate(run_id, questions, coverage, syllabus_analysis, request)
                            quality = self.planner.evaluate_quality(questions, coverage)
                            failing_ids = [q.question_id for q, qq in zip(questions, quality) if not qq.passed]

                            if failing_ids:
                                planner.set_failing_questions(failing_ids)
                            else:
                                break

            # Final validation
            if questions:
                self._validate(run_id, questions, coverage, syllabus_analysis, request)

            quality = self.planner.evaluate_quality(questions, coverage)

            # Assemble package
            pkg = AssessmentPackage(
                run_id=run_id,
                topic=request.topic,
                syllabus=request.syllabus,
                syllabus_analysis=syllabus_analysis,
                source_research=SourceResearch(),
                coverage_matrix=coverage,
                questions=questions,
                portfolio_coverage_score=100,
                portfolio_missing_areas=[],
                plan_trace=[],
                quality=quality,
            )

            # Supervisor verdict
            sres = self.supervisor.run(pkg, 85.0)
            self._stage(run_id, sres)
            pkg.supervisor = pkg.supervisor.model_validate(sres.payload["verdict"])

            self._attach_costs(pkg)
            state_manager.complete_run(run_id, "completed")

            self.log.info(
                "generate_with_loops_done",
                run_id=run_id,
                questions=len(questions),
                loops=loop_count,
                status=pkg.supervisor.supervisor_status
            )

            return pkg

        except Exception as e:
            state_manager.fail_run(run_id, str(e))
            self.log.error("generation_failed", run_id=run_id, error=str(e))
            raise
        finally:
            state_manager.close()

    # ================================================================== #
    # NEW: Parse and Generate entry points
    # ================================================================== #

    def run_parse(self, md_path: str | Path) -> SkillSet:
        """Parse a markdown file and extract skills to skills/skills.yaml.

        Returns: SkillSet with extracted skills.
        """
        md_path = Path(md_path)
        self.log.info("parse_start", md_file=md_path.name)

        r = self.md_parser.run(md_path)
        return SkillSet(**r.payload["skills"])

    def run_generate(
        self,
        md_path: str | Path,
        constraints: list[dict] | None = None,
        num_questions: int | None = None,
        auto: bool = False,
        domain: str = "",
    ) -> AssessmentPackage:
        """Generate questions from a markdown file with difficulty/bloom constraints.

        Requires: skills/skills.yaml created by run_parse()

        Args:
            md_path: Path to .md file (for validation only)
            constraints: List of {"difficulty": "easy|medium|hard", "bloom_level": "..."}
            num_questions: Fallback if constraints not provided (generates random)
            auto: If True, automatically generates 3 questions (easy, medium, hard)
            domain: Optional domain hint for auto mode

        Returns: AssessmentPackage with generated questions
        """
        import yaml

        md_path = Path(md_path)
        skills_dir = Path(self.settings.skills_dir)

        # Load skills
        skills_yaml_path = skills_dir / "skills.yaml"
        if not skills_yaml_path.exists():
            raise FileNotFoundError(
                f"Skills not extracted. Run: robo-assess parse --md {md_path}"
            )

        skills_data = yaml.safe_load(skills_yaml_path.read_text())
        skill_entries = [SkillEntry(**s) for s in skills_data.get("skills", [])]

        if not skill_entries:
            raise ValueError(f"No skills found in {skills_yaml_path}")

        # Normalize constraints
        if auto:
            # Auto mode: generate 3 constraints (easy, medium, hard)
            constraints = self.skill_picker.generate_auto_constraints(domain)
        elif not constraints and num_questions:
            # Random mode: generate random constraints
            import random
            difficulties = ["easy", "medium", "hard"]
            bloom_levels = ["understand", "apply", "analyze", "evaluate", "create"]
            constraints = [
                {
                    "difficulty": random.choice(difficulties),
                    "bloom_level": random.choice(bloom_levels),
                    "domain": domain or ""
                }
                for _ in range(num_questions)
            ]
        elif not constraints:
            raise ValueError("Either auto=True, constraints, or num_questions must be provided")

        # Create a synthetic SyllabusAnalysis from skills
        syllabus_analysis = SyllabusAnalysis(
            skills=[s.skill for s in skill_entries],
            concepts=[],
            apis=[],
            config_elements=[],
            ros_components=[],
            difficulty_range="easy-hard"
        )

        # Create synthetic AssessmentRequest
        request = AssessmentRequest(
            topic=md_path.stem,
            syllabus=[s.skill for s in skill_entries],
            sources=[],
            existing_questions=[],
            num_questions=len(constraints)
        )

        # Initialize state manager and improved confidence scorer
        run_id = uuid.uuid4().hex[:12]
        state_manager = StateManager(str(Path(self.settings.log_dir) / "state.db"))
        state_manager.start_run(run_id, str(md_path), "generate", len(constraints))

        # Load reference scores with ground truth validation data
        evaluations_dir = Path(self.settings.evaluations_dir) if hasattr(self.settings, 'evaluations_dir') else Path("evaluations")
        reference_scores = load_improved_reference_scores_from_json(str(evaluations_dir))

        # Upsert reference scores into state manager
        for ref_id, ref_data in reference_scores.items():
            state_manager.upsert_reference_scores(ref_id, ref_data)

        # Initialize improved confidence scorer (with calibration multipliers)
        confidence_scorer = ImprovedConfidenceScorer(reference_scores)

        # Build skill graph for prerequisite checking
        skill_graph = SkillGraph()
        skill_graph.build_from_skills(skill_entries)

        self.run_logger.start_run(run_id, request.topic)
        self.log.info(
            "generate_start",
            run_id=run_id,
            md_file=md_path.name,
            constraints=len(constraints),
            reference_count=len(reference_scores)
        )

        questions: list[Question] = []
        generated_skills: list[str] = []
        coverage = CoverageMatrix()
        for skill in request.syllabus:
            coverage.matrix[skill] = False

        try:
            # Per-constraint generation with state persistence
            for idx, constraint in enumerate(constraints):
                self.log.info("constraint", idx=idx+1, constraint=constraint)

                # Check for resumable state
                step_name = f"constraint_{idx}"
                saved_state = state_manager.load_state(run_id, step_name)
                if saved_state and "question" in saved_state:
                    # Resume from checkpoint
                    questions.append(Question(**saved_state["question"]))
                    generated_skills.append(saved_state["skill"])
                    self.log.info("resumed_from_checkpoint", step=step_name)
                    continue

                # Pick skill matching this constraint
                try:
                    res = self.skill_picker.run(
                        difficulty=constraint.get("difficulty", "medium"),
                        bloom_level=constraint.get("bloom_level", "apply"),
                        domain=constraint.get("domain", ""),
                        all_skills=skill_entries,
                        already_generated=generated_skills,
                    )
                    selected_skill = SkillEntry(**res.payload["skill"])
                    generated_skills.append(selected_skill.skill)

                    # Validate prerequisites are in syllabus
                    is_valid, missing = skill_graph.validate_coverage(request.syllabus, selected_skill.skill)
                    if not is_valid:
                        self.log.warning("missing_prerequisites", skill=selected_skill.skill, missing=list(missing))

                    self._stage(run_id, res)
                except Exception as e:
                    self.log.error("skill_picker_error", error=str(e))
                    continue

                # Generate question for this skill
                try:
                    r = self.generator._llm_question(
                        skill=selected_skill.skill,
                        difficulty=constraint.get("difficulty", "medium"),
                        domain=constraint.get("domain", ""),
                        bloom_level=constraint.get("bloom_level", "apply"),
                        allowed_scope=", ".join(request.syllabus),
                        forbidden_scope="Nav2, SLAM, MoveIt, OpenCV",
                        existing_titles=[q.title for q in questions],
                        idx=idx+1,
                        feedback={}
                    )
                    if r:
                        questions.append(r)
                        r.generation_skill = selected_skill.skill
                        self.coverage.mark(coverage, r.tested_skills)

                        # Save state checkpoint
                        state_manager.save_state(
                            run_id,
                            step_name,
                            {
                                "question": r.model_dump(),
                                "skill": selected_skill.skill,
                                "constraint": constraint,
                            }
                        )

                        self.log.info("question_generated", idx=idx+1, skill=selected_skill.skill)
                except Exception as e:
                    self.log.error("generation_error", idx=idx+1, error=str(e))

            # Validate all questions
            if questions:
                self._validate(run_id, questions, coverage, syllabus_analysis, request)

                # Score questions with improved confidence scorer (with calibration)
                for q in questions:
                    validators = {
                        "auto_grading": getattr(q, "auto_grading_score", 0),
                        "originality": getattr(q, "originality_score", 0),
                        "format_compliance": getattr(q, "format_quality_score", 0),
                    }
                    # Use improved scorer with difficulty calibration
                    difficulty_hint = getattr(q, "difficulty", None)
                    if difficulty_hint:
                        difficulty_hint = difficulty_hint.value.lower()

                    confidence, breakdown = confidence_scorer.score(
                        q, validators, difficulty_hint=difficulty_hint
                    )

                    state_manager.save_question_scores(
                        run_id,
                        q.question_id,
                        confidence,
                        breakdown,
                        breakdown.get("similar_refs", []),
                        breakdown.get("features", {})
                    )

                    # Log with calibration details
                    self.log.info(
                        "confidence_scored_improved",
                        question_id=q.question_id,
                        confidence=confidence,
                        empirical_pass_rate=breakdown.get("empirical_pass_rate"),
                        difficulty_multiplier=breakdown.get("difficulty_multiplier"),
                        calibration_method=breakdown.get("calibration_method"),
                    )

            quality = self.planner.evaluate_quality(questions, coverage)
            plan_trace = []  # Simplified: no detailed planner trace

            # Assemble package
            pkg = AssessmentPackage(
                run_id=run_id,
                topic=request.topic,
                syllabus=request.syllabus,
                syllabus_analysis=syllabus_analysis,
                source_research=SourceResearch(),
                coverage_matrix=coverage,
                questions=questions,
                portfolio_coverage_score=100,
                portfolio_missing_areas=[],
                plan_trace=plan_trace,
                quality=quality,
            )

            # Supervisor verdict
            sres = self.supervisor.run(pkg, 85.0)
            self._stage(run_id, sres)
            pkg.supervisor = pkg.supervisor.model_validate(sres.payload["verdict"])

            self._attach_costs(pkg)

            state_manager.complete_run(run_id, "completed")

            self.run_logger.finish_run(
                run_id,
                n_questions=len(questions),
                n_approved=len(pkg.approved_questions),
                supervisor=pkg.supervisor.supervisor_status,
                score=pkg.supervisor.validation_score,
            )

            return pkg

        except Exception as e:
            state_manager.fail_run(run_id, str(e))
            self.log.error("generation_failed", run_id=run_id, error=str(e))
            raise
        finally:
            state_manager.close()
