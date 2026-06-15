"""
Agent 4 — Question Generator
============================

This is an LLM agent: it calls the configured provider (OpenRouter or Anthropic)
to generate original questions as a three-block
response — a JSON spec, a compiling starter with `# TODO START`/`# TODO END`
markers, and a full reference solution. There is no offline/template fallback;
a transient failure is retried once and otherwise raises so the run fails loudly
rather than shipping silent filler.
"""

from __future__ import annotations

import itertools
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..token_counter import TokenCounter
from ..schemas import (
    AgentResult,
    BloomLevel,
    CoverageMatrix,
    Difficulty,
    EditableFile,
    EvaluationCriterion,
    Question,
    SyllabusAnalysis,
    FileStructure,
    FileToCreate,
    QuestionMetadata,
    Part,
    ExpectedOutput,
    EvaluationCriteria,
    StarterCodeBlock,
)
# DOMAINS removed — now extracted from markdown via MdParserAgent
from .base import BaseAgent

# Bloom level per difficulty
_BLOOM_MAP = {
    Difficulty.EASY: BloomLevel.APPLY,
    Difficulty.MEDIUM: BloomLevel.ANALYZE,
    Difficulty.HARD: BloomLevel.CREATE,
}

# Out-of-scope tech that must never appear unless explicitly granted
_FORBIDDEN_DEFAULT = "Nav2, SLAM, MoveIt, OpenCV, micro-ROS, point clouds"

# Default domains for question generation (cycling through for diversity)
DOMAINS = [
    "warehouse automation", "inspection robotics", "factory assembly",
    "delivery robots", "agriculture", "mining operations",
    "construction", "healthcare", "research labs", "autonomous vehicles",
]

_SYSTEM_PROMPT = (
    "You are a Senior ROS2 Humble Robotics Engineer designing detailed, "
    "industry-realistic coding assessments with scenario-based (twisty, not straightforward) titles. "
    "Return EXACTLY three blocks in this order, each separated by its marker line:\n"
    "BLOCK 1 (JSON): a single valid JSON object with detailed metadata, context, tasks, "
    "file_structure, expected_output, run_commands, and evaluation_criteria. "
    "No markdown fences, no prose.\n"
    "---STARTER_FILE---\n"
    "BLOCK 2 (starter): a complete, COMPILING ROS2 Humble rclpy Python file the "
    "student edits, with the part they must implement bounded by '# TODO START' "
    "and '# TODO END' markers and nothing else inside them.\n"
    "---REFERENCE_FILE---\n"
    "BLOCK 3 (reference): the SAME file with the TODO region fully and correctly "
    "implemented and the TODO markers removed. It MUST actually call the required "
    "rclpy APIs (create_publisher/subscription/service/timer, declare_parameter, etc.) "
    "and reference the exact topic/service names from the JSON criteria. "
    "No rospy, no stubs, no placeholders."
)


def _difficulty_counts(n: int, dist: dict[str, float]) -> dict[str, int]:
    easy = round(n * dist.get("easy", 0.3))
    hard = round(n * dist.get("hard", 0.2))
    medium = max(0, n - easy - hard)
    return {"easy": easy, "medium": medium, "hard": hard}


def _load_prompt_template(prompts_dir: str, use_detailed: bool = True) -> str:
    # Try loading detailed template first if requested
    if use_detailed:
        p = Path(prompts_dir) / "question_generator_detailed.txt"
        if p.is_file():
            return p.read_text(encoding="utf-8")
    # Fall back to original template
    p = Path(prompts_dir) / "question_generator.txt"
    if p.is_file():
        return p.read_text(encoding="utf-8")
    # fallback minimal prompt for detailed format
    return (
        "Generate a ROS2 Humble coding question for skill={skill}, "
        "difficulty={difficulty}, domain={domain}, bloom={bloom_level}. "
        "Return a detailed JSON with: title (scenario-based, twisty), metadata, context, "
        "prerequisites, notes, tasks, file_structure, expected_output, run_commands, "
        "evaluation_criteria, common_mistakes, estimated_solve_minutes. "
        "Follow with ---STARTER_FILE---, starter code with # TODO START/END, "
        "---REFERENCE_FILE---, and complete reference solution."
    )


def _extract_json_object(text: str) -> str:
    """Extract the first complete JSON object from text, ignoring trailing content."""
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_str = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_str:
            escape_next = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return text[start:]


def _strip_code_fences(code: str) -> str:
    code = code.strip()
    code = re.sub(r"^FILE:.*\n", "", code)
    code = re.sub(r"^```(?:python|yaml|xml)?\s*\n?", "", code)
    code = re.sub(r"\n?```\s*$", "", code)
    return code.strip()


def _parse_three_block_response(text: str) -> tuple[dict, str, str]:
    """Split LLM output into (question_json, starter_code, reference_code).

    Accepts the new three-block format (JSON / ---STARTER_FILE--- /
    ---REFERENCE_FILE---) and degrades gracefully to the legacy two-block format
    (JSON / ---SOLUTION_FILE---), in which case the reference is empty and the
    executable-grading gate reports NO_ARTIFACTS rather than silently passing.
    """
    import json as _json
    from ..llm_client import _sanitize_llm_json

    starter_block = reference_block = ""
    # New format first.
    if "---STARTER_FILE---" in text:
        json_block, rest = text.split("---STARTER_FILE---", 1)
        if "---REFERENCE_FILE---" in rest:
            starter_block, reference_block = rest.split("---REFERENCE_FILE---", 1)
        else:
            starter_block = rest
    elif "---SOLUTION_FILE---" in text:  # legacy two-block
        json_block, starter_block = text.split("---SOLUTION_FILE---", 1)
    else:
        json_block = text

    json_block = json_block.strip()
    if json_block.startswith("```"):
        json_block = re.sub(r"^```(?:json)?\s*", "", json_block)
        json_block = re.sub(r"\s*```$", "", json_block)
        json_block = json_block.strip()
    json_block = _extract_json_object(json_block)

    try:
        raw = _json.loads(json_block)
    except _json.JSONDecodeError:
        raw = _json.loads(_sanitize_llm_json(json_block))

    return raw, _strip_code_fences(starter_block), _strip_code_fences(reference_block)


def _parse_llm_question(raw: dict, boilerplate: str, reference: str, idx: int, skill: str, diff: Difficulty, domain: str) -> Question:
    """Convert raw LLM JSON dict + starter + reference into a validated Question."""

    def _eval_criteria(items: list) -> list[EvaluationCriterion]:
        out = []
        for c in items or []:
            out.append(EvaluationCriterion(
                id=str(c.get("id", f"EC{len(out)+1}")),
                check=str(c.get("check", "behaviour")),
                target=str(c.get("target", "")),
                expected=str(c.get("expected", "")),
                points=int(c.get("points", 25)),
                description=str(c.get("description", "")),
            ))
        return out

    def _parse_file_structure(fs_dict: dict) -> FileStructure:
        if not fs_dict:
            return FileStructure(ros_package="ros2_pkg")
        files = []
        for f in fs_dict.get("files_to_create", []):
            files.append(FileToCreate(
                path=str(f.get("path", "")),
                role=str(f.get("role", "")),
            ))
        return FileStructure(
            ros_package=str(fs_dict.get("ros_package", "ros2_pkg")),
            dependencies=list(fs_dict.get("dependencies", [])),
            files_to_create=files,
        )

    def _parse_metadata(meta_dict: dict) -> QuestionMetadata:
        if not meta_dict:
            return QuestionMetadata(
                topic=skill, difficulty_level=diff.value,
                estimated_time_minutes=30, concepts=[skill]
            )
        return QuestionMetadata(
            topic=str(meta_dict.get("topic", skill)),
            difficulty_level=str(meta_dict.get("difficulty_level", diff.value)),
            estimated_time_minutes=int(meta_dict.get("estimated_time_minutes", 30)),
            language=str(meta_dict.get("language", "Python")),
            ros_version=str(meta_dict.get("ros_version", "ROS2")),
            concepts=list(meta_dict.get("concepts", [skill])),
        )

    def _parse_expected_output(outputs: list) -> list[ExpectedOutput]:
        out = []
        for o in outputs or []:
            out.append(ExpectedOutput(
                shell=str(o.get("shell", "Shell #1")),
                output=str(o.get("output", "")),
            ))
        return out

    def _parse_evaluation_criteria_detailed(ec_dict: dict) -> EvaluationCriteria:
        if not ec_dict:
            return EvaluationCriteria()
        return EvaluationCriteria(
            compiles_without_error=bool(ec_dict.get("compiles_without_error", True)),
            nodes=list(ec_dict.get("nodes")) if ec_dict.get("nodes") else None,
            topics_subscribed=list(ec_dict.get("topics_subscribed")) if ec_dict.get("topics_subscribed") else None,
            topics_published=list(ec_dict.get("topics_published")) if ec_dict.get("topics_published") else None,
            services=list(ec_dict.get("services")) if ec_dict.get("services") else None,
            publish_rate=float(ec_dict.get("publish_rate")) if ec_dict.get("publish_rate") else None,
        )

    file_to_edit = str(raw.get("file_to_edit", "pkg/node.py"))
    slug = skill.replace(" ", "_").lower()[:20]

    # Parse new detailed fields
    metadata = _parse_metadata(raw.get("metadata"))
    file_structure = _parse_file_structure(raw.get("file_structure"))
    expected_outputs = _parse_expected_output(raw.get("expected_output", []))
    # Handle both dict (detailed format) and list (simple format from FakeLLM)
    ec = raw.get("evaluation_criteria", {})
    detailed_eval_criteria = _parse_evaluation_criteria_detailed(ec if isinstance(ec, dict) else {})

    # Parse parts (multi-part questions) or flat tasks
    parts = []
    for p in raw.get("parts", []):
        parts.append(Part(
            label=str(p.get("label", "")),
            tasks=list(p.get("tasks", [])),
        ))
    tasks = list(raw.get("tasks", []))

    return Question(
        question_id=f"Q{idx:03d}_{slug}",
        title=str(raw.get("title", f"Implement {skill}")) or f"Implement {skill}",
        difficulty=diff,
        bloom_level=_BLOOM_MAP.get(diff, BloomLevel.APPLY),
        robot=str(raw.get("robot", "")),
        scenario=str(raw.get("scenario", "")),
        context=str(raw.get("context", "")),
        file_to_edit=file_to_edit,
        objective=str(raw.get("objective", "")),
        constraints=list(raw.get("constraints", [])),
        tested_skills=list(raw.get("tested_skills", [skill])),
        evaluation_criteria=_eval_criteria(
            raw.get("evaluation_criteria", []) if isinstance(raw.get("evaluation_criteria"), list)
            else raw.get("evaluation_criteria", {}).get("criteria", []) if isinstance(raw.get("evaluation_criteria"), dict) and "criteria" in raw.get("evaluation_criteria", {})
            else []
        ),
        boilerplate_code=boilerplate,
        common_mistakes=list(raw.get("common_mistakes", [])),
        estimated_solve_minutes=int(raw.get("estimated_solve_minutes", 30)),
        industry_domain=domain,
        prerequisites=list(raw.get("prerequisites", [])),
        notes=str(raw.get("notes", "")) if raw.get("notes") else None,
        parts=parts,
        tasks=tasks,
        metadata=metadata,
        file_structure=file_structure,
        expected_output=expected_outputs,
        run_commands=list(raw.get("run_commands", [])),
        detailed_evaluation_criteria=detailed_eval_criteria,
        files_to_edit=[EditableFile(
            path=file_to_edit,
            language="python",
            starter_code=boilerplate,
            reference_solution=reference,
        )],
    )


class QuestionGeneratorAgent(BaseAgent):
    name = "question_generator"

    def __init__(self, *args, token_counter: TokenCounter | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._domain_cycle = itertools.cycle(DOMAINS)
        self._prompt_tpl = _load_prompt_template(self.settings.prompts_dir, use_detailed=True)
        self.token_counter = token_counter

    # ------------------------------------------------------------------ #
    # LLM path (the only generation path — this is an LLM agent)
    # ------------------------------------------------------------------ #
    def _llm_question(
        self,
        skill: str,
        difficulty: Difficulty,
        domain: str,
        allowed_scope: str,
        existing_titles: list[str],
        idx: int,
        feedback: str | dict = "",
        bloom_level: str = "",
        forbidden_scope: str = "",
    ) -> Question | None:
        if isinstance(difficulty, str):
            difficulty = Difficulty(difficulty)
        bloom = _BLOOM_MAP.get(difficulty, BloomLevel.APPLY).value
        existing_str = "\n".join(f"- {t}" for t in existing_titles) or "(none yet)"

        # Determine forbidden tech based on allowed scope
        forbidden = forbidden_scope or ", ".join(
            tech for tech in ["Nav2", "SLAM", "MoveIt", "OpenCV", "micro-ROS"]
            if tech.lower() not in allowed_scope.lower()
        ) or "none"

        # Use simple replacement to avoid KeyError on JSON { } in the template
        user_prompt = self._prompt_tpl
        for k, v in [
            ("{skill}", skill),
            ("{difficulty}", difficulty.value),
            ("{domain}", domain),
            ("{bloom_level}", bloom),
            ("{allowed_scope}", allowed_scope),
            ("{forbidden_scope}", forbidden),
            ("{existing_titles}", existing_str),
        ]:
            user_prompt = user_prompt.replace(k, v)

        # Closed-loop regeneration: tell the model exactly why the prior attempt
        # was rejected so it does not repeat the same defect.
        if feedback:
            user_prompt += (
                "\n\nThe previous attempt for this slot was REJECTED by the "
                "Supervisor for the following reasons. Produce a NEW question that "
                f"fixes every one of them:\n- {feedback}\n"
            )

        try:
            text, usage = self.llm.complete(  # type: ignore[union-attr]
                system=_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
            )
            raw, boilerplate, reference = _parse_three_block_response(text)
            self.log.info(
                "llm_question_generated",
                skill=skill,
                diff=difficulty.value,
                tokens_in=usage.input_tokens,
                tokens_out=usage.output_tokens,
                has_reference=bool(reference),
            )
            q = _parse_llm_question(raw, boilerplate, reference, idx, skill, difficulty, domain)
            # Attribute tokens to THIS question_id so cost-per-question (initial
            # generation + every regeneration of this slot) is reported.
            if self.token_counter:
                self.token_counter.record(
                    "question_generator", usage,
                    question_id=q.question_id,
                    skill=skill, difficulty=difficulty.value, domain=domain,
                )
            return q
        except Exception as exc:
            self.log.warning("llm_question_failed", skill=skill, error=str(exc))
            return None

    def _plan_slots(
        self, analysis: SyllabusAnalysis, coverage: CoverageMatrix, n: int
    ) -> list[tuple[int, str, Difficulty, str]]:
        """Coverage-driven slot plan: ``(idx, skill, difficulty, domain)``.

        Each slot is aimed at a syllabus skill that is **not yet covered**, so a
        limited batch maximises coverage instead of cycling skills blindly. When
        ``auto_scale_questions`` is on and the syllabus has more skills than the
        requested count, ``n`` is raised toward the skill count (capped at
        ``max_questions``) so the coverage target is actually reachable rather
        than mathematically impossible.

        Domains are pre-assigned here (in the calling thread) because
        ``itertools.cycle`` is not safe to advance from the worker pool.
        """
        skills = analysis.skills or ["ROS2 publisher"]
        if self.settings.auto_scale_questions and len(skills) > n:
            n = min(len(skills), self.settings.max_questions)
            self.log.info("coverage_autoscale", skills=len(skills), num_questions=n)

        covered = {k for k, v in coverage.matrix.items() if v}
        uncovered = [s for s in skills if s not in covered]
        ordered = uncovered + [s for s in skills if s in covered] or skills

        targets = _difficulty_counts(n, self.settings.difficulty_distribution)
        diff_seq: list[Difficulty] = []
        for diff_str, count in targets.items():
            diff_seq.extend([Difficulty(diff_str)] * count)

        skill_cycle = itertools.cycle(ordered)
        domain_cycle = itertools.cycle(DOMAINS)
        return [
            (i + 1, next(skill_cycle), diff_seq[i], next(domain_cycle))
            for i in range(n)
        ]

    def _llm_batch(
        self,
        analysis: SyllabusAnalysis,
        coverage: CoverageMatrix,
        n: int,
    ) -> list[Question]:
        allowed_scope = ", ".join(analysis.skills + analysis.concepts + analysis.apis)
        slots = self._plan_slots(analysis, coverage, n)
        # Sibling skill descriptors give each parallel worker batch context to
        # diversify against — parallel generation can't feed incrementally-built
        # titles, so we seed differentiation from the plan instead and let the
        # OriginalityAgent + targeted regeneration catch any residual near-dupes.
        sibling = [f"{skill} ({diff.value})" for _, skill, diff, _ in slots]

        def _gen(slot):
            idx, skill, diff, domain = slot
            others = [s for s in sibling if not s.startswith(f"{skill} (")]
            # One retry per slot: a transient bad/unparseable response shouldn't
            # waste the slot. No template fallback — a slot that truly can't be
            # generated returns None and is surfaced, not faked.
            q = self._llm_question(
                skill=skill, difficulty=diff, domain=domain,
                allowed_scope=allowed_scope, existing_titles=others, idx=idx,
            ) or self._llm_question(
                skill=skill, difficulty=diff, domain=domain,
                allowed_scope=allowed_scope, existing_titles=others, idx=idx,
            )
            return idx, q

        workers = max(1, int(getattr(self.settings, "generation_concurrency", 4)))
        by_idx: dict[int, Question | None] = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for idx, q in ex.map(_gen, slots):
                by_idx[idx] = q

        questions = [by_idx[idx] for idx, *_ in slots if by_idx.get(idx) is not None]
        failed = [idx for idx, *_ in slots if by_idx.get(idx) is None]

        # Reliability policy: a single bad slot must not abort the run (the old
        # behaviour), but a wholesale failure is a real provider/config fault and
        # should surface loudly rather than ship a near-empty batch.
        if not questions or len(failed) > len(slots) // 2:
            raise RuntimeError(
                f"question generation failed for {len(failed)}/{len(slots)} slots "
                f"after retry; provider={getattr(self.llm, 'provider', '?')} "
                f"model={getattr(self.llm, 'model', '?')}"
            )
        if failed:
            self.log.warning("generation_partial", failed=len(failed), ok=len(questions))
        return questions

    # ------------------------------------------------------------------ #
    # Closed-loop targeted regeneration
    # ------------------------------------------------------------------ #
    def regenerate(
        self,
        questions: list[Question],
        failing_ids: list[str],
        feedback: dict[str, str],
        analysis: SyllabusAnalysis,
        coverage: CoverageMatrix,
    ) -> AgentResult:
        """Replace ONLY the failing questions, keeping every passing one intact.

        Each replacement is generated with the Supervisor's per-question feedback
        injected, so the loop converges instead of re-rolling the whole batch.
        """
        allowed_scope = ", ".join(analysis.skills + analysis.concepts + analysis.apis)
        failing = set(failing_ids)
        kept_titles = [q.title for q in questions if q.question_id not in failing]

        def _idx_of(qid: str) -> int:
            m = re.match(r"Q(\d+)_", qid)
            return int(m.group(1)) if m else 1

        # Build the regeneration tasks in this thread (domain_cycle advance is not
        # thread-safe), then fan them out — each failing slot is independent.
        tasks = []
        for q in questions:
            if q.question_id not in failing:
                continue
            skill = q.tested_skills[0] if q.tested_skills else (analysis.skills or ["ROS2 publisher"])[0]
            tasks.append((
                q.question_id, _idx_of(q.question_id), skill, q.difficulty,
                q.industry_domain or next(self._domain_cycle),
                feedback.get(q.question_id, ""),
            ))

        def _regen(task):
            qid, idx, skill, diff, domain, fb = task
            nq = self._llm_question(
                skill=skill, difficulty=diff, domain=domain,
                allowed_scope=allowed_scope, existing_titles=kept_titles,
                idx=idx, feedback=fb,
            )
            return qid, nq

        workers = max(1, int(getattr(self.settings, "generation_concurrency", 4)))
        regen: dict[str, Question | None] = {}
        if tasks:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                for qid, nq in ex.map(_regen, tasks):
                    regen[qid] = nq

        replaced = 0
        new_questions: list[Question] = []
        for q in questions:
            if q.question_id not in failing:
                new_questions.append(q)
                continue
            nq = regen.get(q.question_id)
            if nq is None:
                # No template fallback: keep the old (flagged) question rather than
                # fabricate a replacement. The Supervisor will flag it again next
                # round; a persistent failure surfaces instead of being masked.
                self.log.warning("regenerate_failed_keeping_prior", qid=q.question_id)
                new_questions.append(q)
                continue
            new_questions.append(nq)
            replaced += 1

        res = self._result(questions=[q.model_dump() for q in new_questions], replaced=replaced)
        res.messages.append(f"regenerated {replaced} failing question(s) with supervisor feedback")
        return res.finish()

    # ------------------------------------------------------------------ #
    def run(
        self,
        analysis: SyllabusAnalysis,
        coverage: CoverageMatrix,
        n: int,
    ) -> AgentResult:
        if self.llm is None:
            raise RuntimeError(
                "QuestionGeneratorAgent requires an LLM client; this is an LLM "
                "agent with no offline/template generation path."
            )
        self.log.info("llm_generation_mode", provider=self.llm.provider)
        questions = self._llm_batch(analysis, coverage, n)

        res = self._result(questions=[q.model_dump() for q in questions])
        targets = _difficulty_counts(n, self.settings.difficulty_distribution)
        res.messages.append(
            f"generated {len(questions)} questions "
            f"(targets easy={targets['easy']} medium={targets['medium']} hard={targets['hard']})"
        )
        return res.finish()
