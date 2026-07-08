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

import asyncio
import itertools
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..token_counter import TokenCounter
from ..tools.registry import ToolRegistry
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
# Includes both AMR/mobile robot domains and robotic arm domains for diversity
DOMAINS = [
    "warehouse automation", "inspection robotics", "factory assembly",
    "delivery robots", "agriculture", "mining operations",
    "construction", "healthcare", "research labs", "autonomous vehicles",
    "robotic arm manipulation", "surgical robotics", "pick and place arm",
]

# Technical specs per domain — tell the LLM WHICH message types and patterns
# to prefer so domain diversity produces genuinely different API usage, not just
# different scenario wrappers around the same publisher boilerplate.
_DOMAIN_SPECS: dict[str, dict] = {
    "warehouse automation": {
        "preferred_msgs": ["geometry_msgs/Twist", "sensor_msgs/LaserScan", "nav_msgs/Odometry"],
        "patterns": "conveyor speed control, zone entry/exit events, pick-and-place arm commands, proximity sensor thresholds",
        "hint": "Use velocity commands and distance sensor feedback. The robot interacts with conveyor belts or shelf-scanning systems.",
    },
    "inspection robotics": {
        "preferred_msgs": ["sensor_msgs/Range", "std_msgs/Float32", "diagnostic_msgs/DiagnosticArray"],
        "patterns": "threshold alerts, periodic structural checks, anomaly detection, sensor aggregation",
        "hint": "Focus on reading Range or Float32 sensor data, comparing against thresholds, and publishing diagnostic alerts when limits are exceeded.",
    },
    "factory assembly": {
        "preferred_msgs": ["control_msgs/JointTrajectory", "sensor_msgs/JointState", "std_msgs/Bool"],
        "patterns": "joint position feedback, assembly completion signals, torque monitoring, force threshold checking",
        "hint": "Use JointState feedback to monitor arm positions and publish Bool completion signals or stop commands when assembly steps complete.",
    },
    "delivery robots": {
        "preferred_msgs": ["geometry_msgs/PoseStamped", "geometry_msgs/Twist", "std_msgs/String"],
        "patterns": "goal tracking, battery-aware speed reduction, waypoint sequencing, delivery status publishing",
        "hint": "The robot receives PoseStamped goals and must manage speed via Twist based on battery or distance to destination.",
    },
    "agriculture": {
        "preferred_msgs": ["sensor_msgs/NavSatFix", "std_msgs/Float32MultiArray", "sensor_msgs/Imu"],
        "patterns": "GPS-based field coverage, soil sensor polling, spray rate control, heading correction from IMU",
        "hint": "Use NavSatFix for field position and Imu for heading. The robot monitors soil sensors (Float32MultiArray) and controls spray actuators.",
    },
    "mining operations": {
        "preferred_msgs": ["sensor_msgs/LaserScan", "std_msgs/Float64", "sensor_msgs/Imu"],
        "patterns": "tunnel mapping, dust/gas threshold monitoring, vibration alerts, emergency stop via topic",
        "hint": "Use LaserScan for tunnel clearance and Float64 for gas-sensor readings. Publish emergency-stop Bool when sensor values breach safety limits.",
    },
    "construction": {
        "preferred_msgs": ["geometry_msgs/PoseWithCovarianceStamped", "std_msgs/Int32", "sensor_msgs/PointCloud2"],
        "patterns": "site boundary enforcement, load-weight monitoring, equipment status reporting, progress counters",
        "hint": "The robot enforces a work-zone boundary using pose and publishes Int32 progress counters as construction tasks complete.",
    },
    "healthcare": {
        "preferred_msgs": ["sensor_msgs/Temperature", "std_msgs/Float32", "std_msgs/Bool"],
        "patterns": "vital-sign monitoring, dosage timer, alert escalation, watchdog heartbeat",
        "hint": "Publish Temperature or Float32 sensor readings at a fixed rate. Emit a Bool alert when readings leave safe ranges. Implement a watchdog that publishes a heartbeat every N seconds.",
    },
    "research labs": {
        "preferred_msgs": ["std_msgs/Float64MultiArray", "sensor_msgs/Imu", "rosgraph_msgs/Clock"],
        "patterns": "experiment logging, synchronized sensor capture, parameter sweep, data-rate throttling",
        "hint": "Log Float64MultiArray experiment data at a configurable rate. Use parameters to control sampling frequency and apply a moving-average filter before publishing.",
    },
    "autonomous vehicles": {
        "preferred_msgs": ["sensor_msgs/Imu", "nav_msgs/Odometry", "geometry_msgs/AccelWithCovarianceStamped"],
        "patterns": "velocity estimation, slip detection, lane-keep corrections, acceleration limiting",
        "hint": "Fuse Imu angular velocity with wheel Odometry to estimate slip. Publish corrective Twist or AccelWithCovarianceStamped when slip exceeds threshold.",
    },
    "robotic arm manipulation": {
        "preferred_msgs": ["control_msgs/FollowJointTrajectory", "sensor_msgs/JointState", "trajectory_msgs/JointTrajectory"],
        "patterns": "joint trajectory planning, end-effector pose control, gripper open/close, torque limit monitoring, workspace collision detection",
        "hint": "Use JointTrajectory to send multi-joint position goals. Monitor JointState feedback for position/velocity/effort. Publish Bool gripper commands or trigger collision stop via service.",
    },
    "surgical robotics": {
        "preferred_msgs": ["geometry_msgs/Pose", "sensor_msgs/JointState", "std_msgs/Float32"],
        "patterns": "precision pose tracking, force-feedback thresholds, tremor filtering, tool-tip position broadcasting, safety zone enforcement",
        "hint": "Publish Pose messages for tool-tip position. Monitor Float32 force sensor and halt motion via service when force exceeds safe threshold. Apply a low-pass filter on JointState velocity to reduce tremor.",
    },
    "pick and place arm": {
        "preferred_msgs": ["control_msgs/GripperCommand", "geometry_msgs/PoseStamped", "moveit_msgs/MoveGroupAction"],
        "patterns": "grasp pose computation, gripper width control, object detection triggers, place zone sequencing, conveyor synchronisation",
        "hint": "Publish GripperCommand to open/close gripper. Read PoseStamped from object detection and relay to arm controller. Sequence pick→move→place actions with service calls.",
    },
}


def _get_domain_hint(domain: str) -> str:
    """Return a technical hint string for the given domain, or empty string."""
    spec = _DOMAIN_SPECS.get(domain, {})
    if not spec:
        return ""
    msgs = ", ".join(spec.get("preferred_msgs", []))
    return (
        f"Preferred ROS2 message types for this domain: {msgs}. "
        f"Common patterns: {spec.get('patterns', '')}. "
        f"Technical guidance: {spec.get('hint', '')}"
    )

_SYSTEM_PROMPT = (
    "You are a Senior Robotics Engineer designing Python coding assessments for ROS2 Humble. "
    "Follow the prompt instructions EXACTLY.\n\n"
    "TOOL USAGE RULE: For MEDIUM and HARD questions that use ROS2 libraries (rclpy, geometry_msgs, "
    "nav_msgs, tf2_ros, etc.), you MUST call fetch_ros2_docs before writing any code to verify API "
    "signatures. For EASY questions, call fetch_ros2_docs only if you need to confirm a specific "
    "API signature. For pure math questions (numpy only, no rclpy), skip fetch_ros2_docs.\n\n"
    "QUESTION TYPE RULE: Read STEP 1 in the prompt to decide whether to generate a pure Python "
    "class (TYPE A), a ROS2 node (TYPE B), or a math function inside a ROS2 node (TYPE C). "
    "Do NOT default to ROS2 nodes for math-only skills.\n\n"
    "OUTPUT: Return EXACTLY three blocks separated by their marker lines. No markdown fences. No prose."
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


_STARTER_MARKERS = [
    "---STARTER_FILE---",
    "--- STARTER_FILE ---",
    "---STARTER---",
    "--- STARTER ---",
    "--STARTER_FILE--",
    "# STARTER FILE:",
    "# STARTER:",
    "## STARTER FILE",
    "## STARTER",
]

_REFERENCE_MARKERS = [
    "---REFERENCE_FILE---",
    "--- REFERENCE_FILE ---",
    "---REFERENCE---",
    "--- REFERENCE ---",
    "--REFERENCE_FILE--",
    "---SOLUTION_FILE---",
    "--- SOLUTION_FILE ---",
    "# REFERENCE FILE:",
    "# REFERENCE SOLUTION:",
    "# REFERENCE:",
    "## REFERENCE FILE",
    "## REFERENCE SOLUTION",
]


def _find_marker_split(text: str, markers: list[str]) -> tuple[str, str] | None:
    """Return (before, after) for the first matching marker found in text."""
    best_idx: int | None = None
    best_end: int | None = None
    for m in markers:
        idx = text.find(m)
        if idx != -1 and (best_idx is None or idx < best_idx):
            best_idx = idx
            best_end = idx + len(m)
    if best_idx is not None:
        return text[:best_idx], text[best_end:]
    return None


def _parse_three_block_response(text: str) -> tuple[dict, str, str]:
    """Split LLM output into (question_json, starter_code, reference_code).

    Tries all known marker variants so minor LLM formatting deviations (spaces,
    alternative names, legacy format) are handled without dropping the question.
    When no markers are found at all, treats the whole response as JSON only —
    the executable-grading gate then reports NO_ARTIFACTS rather than crashing.
    """
    import json as _json
    from ..llm_client import _sanitize_llm_json

    starter_block = reference_block = ""

    # Detect structured submission from submit_question tool (JSON sentinel)
    if text.startswith("__SUBMISSION__:"):
        try:
            payload = _json.loads(text[len("__SUBMISSION__:"):])
            raw = _json.loads(payload["spec_json"])
            return raw, payload.get("starter_code", ""), payload.get("reference_code", "")
        except Exception:
            pass  # fall through to normal parsing

    split = _find_marker_split(text, _STARTER_MARKERS)
    if split is not None:
        json_block, rest = split
        ref_split = _find_marker_split(rest, _REFERENCE_MARKERS)
        if ref_split is not None:
            starter_block, reference_block = ref_split
        else:
            starter_block = rest
    else:
        ref_split = _find_marker_split(text, _REFERENCE_MARKERS)
        if ref_split is not None:
            json_block, reference_block = ref_split
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

    # New compact format: starter_code / reference_solution embedded in JSON.
    # Use them when the three-block markers produced empty blocks.
    if not starter_block:
        starter_block = raw.pop("starter_code", "") or ""
    if not reference_block:
        reference_block = raw.pop("reference_solution", "") or ""

    return raw, _strip_code_fences(starter_block), _strip_code_fences(reference_block)


def _validate_code_files(boilerplate: str, reference: str) -> None:
    """Validate that generated Python files are syntactically valid and differ."""
    import ast as _ast
    if not reference or not reference.strip():
        raise ValueError("reference solution is empty — response was likely truncated; retry")
    if not boilerplate or not boilerplate.strip():
        raise ValueError("starter file is empty")
    for label, code in [("starter", boilerplate), ("reference", reference)]:
        try:
            _ast.parse(code)
        except SyntaxError as exc:
            raise ValueError(f"{label} file has SyntaxError: {exc}") from exc
    if boilerplate.strip() == reference.strip():
        raise ValueError("starter and reference are identical — bug was not introduced")


def _parse_llm_question(raw: dict, boilerplate: str, reference: str, idx: int, skill: str, diff: Difficulty, domain: str, question_type: str = "") -> Question:
    """Convert raw LLM JSON dict + starter + reference into a validated Question."""
    _validate_code_files(boilerplate, reference)

    def _eval_criteria(items: list, num_tasks: int = 0) -> list[EvaluationCriterion]:
        out = []
        for c in items or []:
            out.append(EvaluationCriterion(
                id=str(c.get("id", f"EC{len(out)+1}")),
                check=str(c.get("check", "behaviour")),
                target=str(c.get("target", "")),
                expected=str(c.get("expected", "")),
                points=int(c.get("points", 10)),
                description=str(c.get("description", "")),
            ))
        # Points scale with task count (10 points per task), not a fixed 100 total.
        # E.g. 1 task -> 10 points, 3 tasks -> 30 points.
        target_total = max(num_tasks, len(out)) * 10 if out else 0
        if out and target_total:
            total = sum(ec.points for ec in out)
            if total != target_total and total > 0:
                # Redistribute proportionally; last criterion absorbs rounding error
                scaled = [round(ec.points / total * target_total) for ec in out]
                diff_fix = target_total - sum(scaled)
                scaled[-1] += diff_fix
                for ec, pts in zip(out, scaled):
                    ec.points = pts
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

    # Support both "file_to_edit" (legacy) and "files_to_edit" (new list format)
    _files_to_edit_list = raw.get("files_to_edit", [])
    file_to_edit = (
        str(raw.get("file_to_edit"))
        if raw.get("file_to_edit")
        else (str(_files_to_edit_list[0]) if _files_to_edit_list else "pkg/node.py")
    )
    slug = re.sub(r"[^a-z0-9_]", "_", skill.replace(" ", "_").lower())[:20]

    # Parse new detailed fields
    metadata = _parse_metadata(raw.get("metadata"))
    file_structure = _parse_file_structure(raw.get("file_structure"))
    expected_outputs = _parse_expected_output(raw.get("expected_output", []))
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
        question_type=str(raw.get("question_type", "") or question_type or ""),
        title=str(raw.get("title", f"Implement {skill}")) or f"Implement {skill}",
        difficulty=diff,
        bloom_level=_BLOOM_MAP.get(diff, BloomLevel.APPLY),
        robot=str(raw.get("robot", "")),
        scenario=str(raw.get("scenario", "")),
        context=str(raw.get("context", "")),
        file_to_edit=file_to_edit,
        objective=str(raw.get("objective") or raw.get("question", "")),
        constraints=list(raw.get("constraints", [])),
        tested_skills=list(raw.get("tested_skills", [skill])),
        evaluation_criteria=_eval_criteria(
            raw.get("evaluation_criteria", []) if isinstance(raw.get("evaluation_criteria"), list)
            else raw.get("evaluation_criteria", {}).get("criteria", []) if isinstance(raw.get("evaluation_criteria"), dict) and "criteria" in raw.get("evaluation_criteria", {})
            else [],
            num_tasks=len(tasks),
        ),
        boilerplate_code=boilerplate,
        common_mistakes=list(raw.get("common_mistakes", [])),
        estimated_solve_minutes=int(raw.get("estimated_solve_minutes", 30)),
        industry_domain=domain,
        prerequisites=list(raw.get("prerequisites", [])),
        notes=("\n".join(raw["notes"]) if isinstance(raw.get("notes"), list) else str(raw["notes"])) if raw.get("notes") else None,
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
        self.tool_registry: ToolRegistry | None = None
        self.triage = None  # set by orchestrator after ComplexityTriageAgent runs
        # Hash the current prompt template so few-shot retrieval can ignore
        # examples generated with an older prompt format.
        import hashlib as _hl
        self._prompt_hash = _hl.md5(self._prompt_tpl.encode()).hexdigest()[:12]

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
        question_type: str = "",
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
            ("{domain_hint}", _get_domain_hint(domain)),
            ("{bloom_level}", bloom),
            ("{allowed_scope}", allowed_scope),
            ("{forbidden_scope}", forbidden),
            ("{existing_titles}", existing_str),
        ]:
            user_prompt = user_prompt.replace(k, v)

        # Inject triage-assigned question type as a directive
        if question_type:
            user_prompt = (
                f"REQUIRED QUESTION TYPE: {question_type}\n"
                f"You MUST generate a {question_type} question for this slot.\n\n"
            ) + user_prompt

        # Inject few-shot examples from past approved runs so the model has
        # concrete reference outputs calibrated to this skill+difficulty.
        if self.memory is not None:
            try:
                shots = self.memory.get_few_shots(
                    skill, difficulty.value, n=2, prompt_hash=self._prompt_hash
                )
                if shots:
                    examples = []
                    for s in shots:
                        import json as _json
                        try:
                            q_data = _json.loads(s["question_json"])
                            examples.append(
                                f"EXAMPLE (skill={s['skill']}, difficulty={s['difficulty']}, "
                                f"confidence={s['confidence_score']:.0f}):\n"
                                f"title: {q_data.get('title', '')}\n"
                                f"question: {q_data.get('question', q_data.get('objective', ''))}\n"
                                f"starter_code (first 300 chars): {s['starter_code'][:300]}"
                            )
                        except Exception:
                            pass
                    if examples:
                        # Memory provided calibrated shots — strip the hardcoded worked
                        # examples from the template to avoid ~1500 tokens of redundancy.
                        _marker = "\nWORKED EXAMPLE"
                        if _marker in user_prompt:
                            user_prompt = user_prompt[:user_prompt.index(_marker)].rstrip()
                        user_prompt = (
                            "REFERENCE EXAMPLES from past approved questions "
                            "(use these to calibrate quality and format — do NOT copy):\n\n"
                            + "\n\n---\n\n".join(examples)
                            + "\n\n---\n\nNOW generate a NEW, ORIGINAL question:\n\n"
                            + user_prompt
                        )
            except Exception:
                pass  # never let few-shot lookup crash generation

        # Closed-loop regeneration: tell the model exactly why the prior attempt
        # was rejected so it does not repeat the same defect.
        if feedback:
            user_prompt += (
                "\n\nThe previous attempt for this slot was REJECTED by the "
                "Supervisor for the following reasons. Produce a NEW question that "
                f"fixes every one of them:\n- {feedback}\n"
            )

        try:
            # TYPE_A questions are pure Python/math — no ROS2 API calls needed.
            # Forcing a tool call wastes a round-trip and contradicts the system prompt.
            use_tools = (
                self.tool_registry is not None
                and hasattr(self.llm, "complete_with_tools")
                and question_type != "TYPE_A"
            )
            if use_tools:
                # Easy questions are simple string/value fixes — they rarely need
                # a live docs lookup before writing code. Letting the model choose
                # on turn 0 (force_first_tool=False) saves one tool-call round-trip.
                text, usage = self.llm.complete_with_tools(  # type: ignore[union-attr]
                    system=_SYSTEM_PROMPT,
                    user=user_prompt,
                    registry=self.tool_registry,
                    temperature=self.settings.temperature,
                    max_tokens=self.settings.max_tokens,
                    force_first_tool=(difficulty != Difficulty.EASY),
                )
            else:
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
            q = _parse_llm_question(raw, boilerplate, reference, idx, skill, difficulty, domain, question_type=question_type)
            # Auto-fix message_content targets: if target not exact in reference,
            # find a line that's in the reference but NOT the starter (the actual fix line).
            # Uses case-insensitive matching to handle UPPER_CASE vs lower_case mismatches.
            if reference and boilerplate and q.evaluation_criteria:
                ref_lines = set(line.strip() for line in reference.splitlines())
                start_lines = set(line.strip() for line in boilerplate.splitlines())
                ref_only_lines = ref_lines - start_lines  # lines that exist only in reference
                for ec in q.evaluation_criteria:
                    if ec.check == "message_content" and ec.target:
                        if ec.target not in reference or ec.target in boilerplate:
                            # Extract the variable name (strip self., case-normalize for matching)
                            var_name = ec.target.split("=")[0].strip().lstrip("self.").strip()
                            var_name_lower = var_name.lower()
                            candidates = [
                                line for line in ref_only_lines
                                if var_name_lower in line.lower() and "=" in line
                                and not line.startswith("#")
                                # Exclude full method calls — target should be a simple assignment
                                and "(" not in line.split("=")[0]
                            ]
                            if candidates:
                                best = min(candidates, key=len)
                                self.log.warning(
                                    "message_content_target_autocorrect",
                                    original=ec.target, corrected=best,
                                )
                                ec.target = best
            # Pre-flight: verify criteria targets are findable in the reference.
            # Catches test_content_values and test_interfaces_referenced failures
            # before Docker runs, so bad questions get retried immediately.
            if reference and q.evaluation_criteria:
                for ec in q.evaluation_criteria:
                    if ec.check == "message_content" and ec.target:
                        if ec.target not in reference:
                            raise ValueError(
                                f"message_content target {ec.target!r} not found in reference — "
                                "grading would fail test_content_values"
                            )
                        if ec.target in boilerplate:
                            raise ValueError(
                                f"message_content target {ec.target!r} present in starter — "
                                "not discriminating (same in both files)"
                            )
                    if ec.check in ("topic_published", "topic_subscribed") and ec.target.startswith("/"):
                        if ec.target not in reference:
                            raise ValueError(
                                f"topic target {ec.target!r} not found as string in reference — "
                                "grading would fail test_interfaces_referenced"
                            )

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
        self, analysis: SyllabusAnalysis, coverage: CoverageMatrix, n: int, offset: int = 0
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

        # Prefer SkillPickerAgent-selected order when available (bloom/difficulty aware)
        picked: list[str] = getattr(self, "picked_skills", [])
        if picked:
            # Extend with remaining ordered skills so cycle never exhausts
            remaining = [s for s in ordered if s not in picked]
            ordered = picked + remaining

        targets = _difficulty_counts(n, self.settings.difficulty_distribution)
        diff_seq: list[Difficulty] = []
        for diff_str, count in targets.items():
            diff_seq.extend([Difficulty(diff_str)] * count)

        skill_cycle = itertools.cycle(ordered)
        domain_cycle = itertools.cycle(DOMAINS)

        # Build type sequence from triage counts (TYPE_A × a, TYPE_B × b, TYPE_C × c)
        type_seq: list[str] = []
        if self.triage is not None:
            type_seq = (
                ["TYPE_A"] * self.triage.type_a_count
                + ["TYPE_B"] * self.triage.type_b_count
                + ["TYPE_C"] * self.triage.type_c_count
            )
        if len(type_seq) < n:
            # Pad or fallback: cycle available types or default to TYPE_B
            base = type_seq or ["TYPE_A", "TYPE_B", "TYPE_C"]
            type_cycle = itertools.cycle(base)
            type_seq = [next(type_cycle) for _ in range(n)]

        return [
            (offset + i + 1, next(skill_cycle), diff_seq[i], next(domain_cycle), type_seq[i])
            for i in range(n)
        ]

    def _llm_batch(
        self,
        analysis: SyllabusAnalysis,
        coverage: CoverageMatrix,
        n: int,
        offset: int = 0,
    ) -> list[Question]:
        # Pass only concepts/APIs as curriculum_scope, not skill descriptions.
        # Skill descriptions read like task directives and bias the LLM toward
        # generating node-heavy questions even for pure math skills.
        allowed_scope = ", ".join(analysis.concepts + analysis.apis) or ", ".join(analysis.skills[:10])
        slots = self._plan_slots(analysis, coverage, n, offset=offset)
        # Sibling skill descriptors give each parallel worker batch context to
        # diversify against — parallel generation can't feed incrementally-built
        # titles, so we seed differentiation from the plan instead and let the
        # OriginalityAgent + targeted regeneration catch any residual near-dupes.
        sibling = [f"{skill} ({diff.value})" for _, skill, diff, _, _type in slots]

        # slot_skill maps slot index → assigned skill for coverage verifier
        slot_skill = {i: skill for i, skill, *_ in slots}

        total_slots = len(slots)
        _progress_lock = threading.Lock()
        _completed = [0]  # mutable counter shared across threads

        def _gen(slot):
            idx, skill, diff, domain, qtype = slot
            others = [s for s in sibling if not s.startswith(f"{skill} (")]
            t0 = time.time()
            q = (
                self._llm_question(
                    skill=skill, difficulty=diff, domain=domain,
                    allowed_scope=allowed_scope, existing_titles=others, idx=idx,
                    question_type=qtype,
                )
                or self._llm_question(
                    skill=skill, difficulty=diff, domain=domain,
                    allowed_scope=allowed_scope, existing_titles=others, idx=idx,
                    question_type=qtype,
                )
                or self._llm_question(
                    skill=skill, difficulty=diff, domain=domain,
                    allowed_scope=allowed_scope, existing_titles=others, idx=idx,
                    question_type=qtype,
                )
            )
            if q is not None:
                q.generation_skill = skill  # type: ignore[attr-defined]
            elapsed = int(time.time() - t0)
            with _progress_lock:
                _completed[0] += 1
                icon = "✓" if q is not None else "✗"
                skill_short = skill[:35] + "…" if len(skill) > 35 else skill
                print(
                    f"  [{icon}] Q{idx:02d} {skill_short} ({diff.value}) — {elapsed}s"
                    f"  [{_completed[0]}/{total_slots}]",
                    flush=True,
                )
            return idx, q

        workers = max(1, int(getattr(self.settings, "generation_concurrency", 4)))
        by_idx: dict[int, Question | None] = {}

        async def _gather_slots() -> list:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=workers) as ex:
                tasks = [loop.run_in_executor(ex, _gen, slot) for slot in slots]
                return await asyncio.gather(*tasks, return_exceptions=True)

        try:
            results = asyncio.run(_gather_slots())
        except RuntimeError:
            # Already inside a running event loop (e.g. Jupyter) — fall back to
            # blocking thread-pool map, which has the same parallelism semantics.
            with ThreadPoolExecutor(max_workers=workers) as ex:
                results = list(ex.map(_gen, slots))

        for item in results:
            if isinstance(item, Exception):
                self.log.warning("generation_slot_exception", error=str(item))
                continue
            idx, q = item
            by_idx[idx] = q

        questions = [by_idx[i] for i, *_ in slots if by_idx.get(i) is not None]
        failed = [i for i, *_ in slots if by_idx.get(i) is None]

        # Expose assigned skills for ScopeQualityAgent's skill-drift check
        self.last_assigned_skills = {
            q.question_id: slot_skill[i]
            for i, *_ in slots
            if (q := by_idx.get(i)) is not None
        }

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
        allowed_scope = ", ".join(analysis.concepts + analysis.apis) or ", ".join(analysis.skills[:10])
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
            # Preserve question_type across regeneration so the model keeps the correct
            # check type (e.g. message_content) instead of falling back to class_method.
            qtype = getattr(q, "question_type", "") or ""
            tasks.append((
                q.question_id, _idx_of(q.question_id), skill, q.difficulty,
                q.industry_domain or next(self._domain_cycle),
                feedback.get(q.question_id, ""),
                qtype,
            ))

        def _regen(task):
            qid, idx, skill, diff, domain, fb, qtype = task
            nq = self._llm_question(
                skill=skill, difficulty=diff, domain=domain,
                allowed_scope=allowed_scope, existing_titles=kept_titles,
                idx=idx, feedback=fb, question_type=qtype,
            )
            return qid, nq

        workers = max(1, int(getattr(self.settings, "generation_concurrency", 4)))
        regen: dict[str, Question | None] = {}
        if tasks:
            async def _gather_regen() -> list:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    coros = [loop.run_in_executor(ex, _regen, t) for t in tasks]
                    return await asyncio.gather(*coros, return_exceptions=True)

            try:
                regen_results = asyncio.run(_gather_regen())
            except RuntimeError:
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    regen_results = list(ex.map(_regen, tasks))

            for item in regen_results:
                if isinstance(item, Exception):
                    self.log.warning("regen_slot_exception", error=str(item))
                    continue
                qid, nq = item
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
        offset: int = 0,
    ) -> AgentResult:
        if self.llm is None:
            raise RuntimeError(
                "QuestionGeneratorAgent requires an LLM client; this is an LLM "
                "agent with no offline/template generation path."
            )
        self.log.info("llm_generation_mode", provider=self.llm.provider, offset=offset, batch=n)
        questions = self._llm_batch(analysis, coverage, n, offset=offset)

        res = self._result(questions=[q.model_dump() for q in questions])
        targets = _difficulty_counts(n, self.settings.difficulty_distribution)
        res.messages.append(
            f"generated {len(questions)} questions (offset={offset}, "
            f"targets easy={targets['easy']} medium={targets['medium']} hard={targets['hard']})"
        )
        return res.finish()
