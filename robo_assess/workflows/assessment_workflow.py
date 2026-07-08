"""
robo_assess.workflows.assessment_workflow
========================================

Turns an :class:`AssessmentPackage` into a directory of deployable artefacts:

    <out>/<run_id>/
        package.json                  full machine-readable package
        coverage_matrix.json
        confidence_report.json
        hiring_readiness_report.json
        evaluation_report.json
        questions/
            <qid>/
                question.json
                README.md             student-facing brief
                starter/<file>        editable starter file with TODO blocks
                solution/<file>       reference solution (instructor only)
                test_<qid>.py         hidden auto-grading test stub
                grading.json          platform evaluation metadata

This is what the platform / instructors actually consume and what the ZIP
delivery requirement packages up.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import yaml

from ..evaluators.dataset_evaluator import evaluate_batch
from ..schemas import AssessmentPackage, Question


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _clean_question_dict(q: Question) -> dict:
    """Return only the student-facing fields for question.json."""
    return {
        "question_id": q.question_id,
        "title": q.title,
        "difficulty": q.difficulty.value,
        "bloom_level": q.bloom_level.value,
        "robot": q.robot,
        "scenario": q.scenario,
        "file_to_edit": q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else ""),
        "objective": q.objective,
        "constraints": q.constraints,
        "tested_skills": q.tested_skills,
        "evaluation_criteria": [ec.model_dump() for ec in q.evaluation_criteria],
        "common_mistakes": q.common_mistakes,
        "estimated_solve_minutes": q.estimated_solve_minutes,
    }


def _evaluate_script(q: Question) -> str:
    """Generate a per-task grading script.

    Output format (points scale with task count — 10 points per task, so
    2 tasks -> max_points 20, not a fixed 100):
        {
          "T1": {"passed": true,  "description": "...", "points": 10},
          "T2": {"passed": false, "description": "...", "points": 10},
          "total_points": 10,
          "max_points": 20,
          "all_passed": false
        }

    Each task maps to one EvaluationCriterion. The check is AST-based
    (static analysis of the student file) so it works without a live ROS2 runtime.
    """
    file_path = q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else "node.py")
    tasks = q.tasks or []
    criteria = q.evaluation_criteria

    # Build per-task check specs: pair each task with its criterion (by index)
    task_checks = []
    for i, task in enumerate(tasks):
        ec = criteria[i] if i < len(criteria) else None
        task_id = f"T{i+1}"
        if ec:
            task_checks.append({
                "id": task_id,
                "description": task,
                "check": ec.check,
                "target": ec.target,
                "expected": ec.expected,
                "points": ec.points,
            })
        else:
            task_checks.append({
                "id": task_id,
                "description": task,
                "check": "compiles",
                "target": "",
                "expected": "",
                "points": 10,  # flat 10 points per task
            })

    task_checks_repr = json.dumps(task_checks, indent=4)

    lines = [
        '"""',
        f"Per-task grading script for: {q.question_id}",
        f"Question: {q.title}",
        "",
        "Usage:",
        f"  python grading.py <path/to/student_file.py>",
        "",
        "Returns JSON with per-task pass/fail and total score.",
        '"""',
        "import ast",
        "import json",
        "import sys",
        "from pathlib import Path",
        "",
        f"QUESTION_ID = {q.question_id!r}",
        f"FILE_TO_EDIT = {file_path!r}",
        "",
        f"TASK_CHECKS = {task_checks_repr}",
        "",
        "",
        "# ── AST helpers ──────────────────────────────────────────────────────",
        "",
        "def _parse(src: str):",
        "    try:",
        "        return ast.parse(src)",
        "    except SyntaxError:",
        "        return None",
        "",
        "",
        "def _called_names(tree) -> set:",
        "    names = set()",
        "    if tree is None:",
        "        return names",
        "    for node in ast.walk(tree):",
        "        if isinstance(node, ast.Call):",
        "            f = node.func",
        "            if isinstance(f, ast.Attribute):",
        "                names.add(f.attr)",
        "            elif isinstance(f, ast.Name):",
        "                names.add(f.id)",
        "    return names",
        "",
        "",
        "def _string_literals(tree) -> list:",
        "    vals = []",
        "    if tree is None:",
        "        return vals",
        "    for node in ast.walk(tree):",
        "        if isinstance(node, ast.Constant) and isinstance(node.value, str):",
        "            vals.append(node.value)",
        "    return vals",
        "",
        "",
        "def _attr_chains(tree) -> set:",
        "    \"\"\"Collect attribute access chains like msg.linear.x as 'linear.x'.\"\"\"",
        "    chains = set()",
        "    if tree is None:",
        "        return chains",
        "    for node in ast.walk(tree):",
        "        if isinstance(node, ast.Attribute):",
        "            parts = []",
        "            cur = node",
        "            while isinstance(cur, ast.Attribute):",
        "                parts.append(cur.attr)",
        "                cur = cur.value",
        "            if parts:",
        "                chains.add('.'.join(reversed(parts)))",
        "    return chains",
        "",
        "",
        "# ── Check implementations ─────────────────────────────────────────────",
        "",
        "def _check(src: str, tree, check: str, target: str, expected: str) -> bool:",
        "    strings = _string_literals(tree)",
        "    calls = _called_names(tree)",
        "    attrs = _attr_chains(tree)",
        "    leaf = target.split('/')[-1].split('.')[-1] if target else ''",
        "",
        "    if check in ('topic_published', 'topic_subscribed', 'topic_active'):",
        "        # Target topic must appear as a string literal in the source",
        "        return target in strings or (leaf and leaf in strings)",
        "",
        "    elif check in ('node_exists', 'node_active'):",
        "        # Any rclpy node call proves the node is active",
        "        ros_calls = {'create_publisher', 'create_subscription', 'create_service',",
        "                     'create_client', 'create_timer', 'declare_parameter'}",
        "        return bool(calls & ros_calls)",
        "",
        "    elif check == 'service_exists':",
        "        return target in strings or (leaf and leaf in strings)",
        "",
        "    elif check == 'function_output':",
        "        # Function/method name must be defined or called",
        "        return leaf in src if leaf else False",
        "",
        "    elif check == 'class_method':",
        "        return leaf in src if leaf else False",
        "",
        "    elif check == 'numerical_accuracy':",
        "        # Target field/variable must appear in source",
        "        return leaf in src if leaf else False",
        "",
        "    elif check == 'message_content':",
        "        return target in strings or (leaf and leaf in src)",
        "",
        "    elif check in ('message_type', 'compiles'):",
        "        return tree is not None  # successfully parsed = compiles",
        "",
        "    elif check == 'publish_rate':",
        "        return 'create_timer' in calls or 'Timer' in calls",
        "",
        "    elif check == 'parameter_set':",
        "        return 'declare_parameter' in calls and (leaf in src if leaf else True)",
        "",
        "    elif check == 'tf_frame':",
        "        return 'TransformBroadcaster' in calls or target in strings",
        "",
        "    elif check in ('behaviour', 'simulation', 'topic_echo', 'ros2_run', 'launch_file'):",
        "        # Cannot be checked statically — pass if file compiles",
        "        return tree is not None",
        "",
        "    # Unknown check — fall back to substring search",
        "    return (leaf in src) if leaf else (tree is not None)",
        "",
        "",
        "# ── Main grading logic ────────────────────────────────────────────────",
        "",
        "def grade(student_file: str) -> dict:",
        "    path = Path(student_file)",
        "    if not path.exists():",
        "        max_pts = sum(tc['points'] for tc in TASK_CHECKS)",
        "        return {'error': f'File not found: {student_file}', 'total_points': 0, 'max_points': max_pts}",
        "    src = path.read_text(encoding='utf-8')",
        "    tree = _parse(src)",
        "",
        "    results = {}",
        "    total = 0",
        "    max_pts = 0",
        "    for tc in TASK_CHECKS:",
        "        passed = _check(src, tree, tc['check'], tc['target'], tc.get('expected', ''))",
        "        pts = tc['points'] if passed else 0",
        "        total += pts",
        "        max_pts += tc['points']",
        "        results[tc['id']] = {",
        "            'passed': passed,",
        "            'description': tc['description'],",
        "            'points': pts,",
        "            'max_points': tc['points'],",
        "        }",
        "",
        "    return {",
        "        'question_id': QUESTION_ID,",
        "        'tasks': results,",
        "        'total_points': total,",
        "        'max_points': max_pts,",
        "        'all_passed': total == max_pts,",
        "    }",
        "",
        "",
        "if __name__ == '__main__':",
        "    if len(sys.argv) < 2:",
        "        print(f'Usage: python grading.py <student_file>', file=sys.stderr)",
        "        sys.exit(1)",
        "    result = grade(sys.argv[1])",
        "    print(json.dumps(result, indent=2))",
        "    # Print human-readable summary",
        "    print()",
        "    for tid, r in result.get('tasks', {}).items():",
        "        status = '✓' if r['passed'] else '✗'",
        "        print(f\"  {status} {tid}: {r['description']} ({r['points']}/{r['max_points']} pts)\")",
        "    print(f\"\\nTotal: {result['total_points']}/{result['max_points']} pts\")",
        "    sys.exit(0 if result['all_passed'] else 1)",
    ]
    return "\n".join(lines) + "\n"


def _readme(q: Question) -> str:
    """Student-facing brief — scenario, objective, constraints, no solution."""
    file_to_edit = q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else "node.py")
    lines = [
        f"# {q.title}",
        "",
        f"- **Difficulty:** {q.difficulty.value}",
        f"- **Robot:** {q.robot or 'n/a'}",
        f"- **Estimated time:** {q.estimated_solve_minutes} min",
        f"- **File to edit:** `{file_to_edit}`",
        "",
        "## Scenario",
        "",
        q.scenario,
        "",
        "## Your task",
        "",
        q.objective,
    ]
    if q.constraints:
        lines += ["", "## Constraints", ""]
        lines += [f"- {c}" for c in q.constraints]
    lines += [
        "",
        "## Instructions",
        "",
        f"Edit only inside the `# TODO START` / `# TODO END` block in `{file_to_edit}`.",
        "Do not modify code outside that block.",
        "",
        "## Grading",
        "",
        f"Your submission is scored out of {sum(ec.points for ec in q.evaluation_criteria) or 10} "
        "points by the automated checks in `evaluate.py` (see `grading.json` for the criteria). Run:",
        "",
        "```",
        "python evaluate.py",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _grading_dict(q: Question) -> dict:
    """Platform evaluation metadata — machine-readable grading config."""
    return {
        "question_id": q.question_id,
        "file_to_edit": q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else ""),
        "total_points": sum(ec.points for ec in q.evaluation_criteria),
        "pass_threshold": 70,
        "auto_gradable": q.auto_gradable,
        "evaluation_criteria": [ec.model_dump() for ec in q.evaluation_criteria],
    }


def export_question(q: Question, qdir: Path) -> None:
    # Clean question.json — no code, student-facing only
    _write(qdir / "question.json", json.dumps(_clean_question_dict(q), indent=2))

    # Student-facing brief
    _write(qdir / "README.md", _readme(q))

    # Platform grading metadata
    _write(qdir / "grading.json", json.dumps(_grading_dict(q), indent=2))

    # Boilerplate file in solution/ folder
    boilerplate = q.boilerplate_code
    if not boilerplate and q.files_to_edit:
        boilerplate = q.files_to_edit[0].starter_code  # legacy fallback
    if boilerplate:
        file_name = Path(q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else "node.py")).name
        _write(qdir / "solution" / file_name, boilerplate)

    # Evaluation script with per-criterion scoring
    _write(qdir / "evaluate.py", _evaluate_script(q))


def _compact_summary(pkg: AssessmentPackage) -> dict:
    """Token-efficient summary: question + boilerplate + difficulty + confidence."""
    questions = []
    for q in pkg.questions:
        files = []
        for f in q.files_to_edit:
            files.append({
                "path": f.path,
                "starter": f.starter_code,
            })
        questions.append({
            "id": q.question_id,
            "title": q.title,
            "diff": q.difficulty.value,
            "bloom": q.bloom_level.value,
            "scenario": q.scenario,
            "objective": q.objective,
            "constraints": q.constraints,
            "files": files,
            "conf": round(q.confidence.confidence, 1) if q.confidence else 0,
            "status": q.confidence.status if q.confidence else "PENDING",
            "grading_exec": q.grading_execution.status if q.grading_execution else "NOT_RUN",
            "tokens_used": q.tokens_used,
            "cost_usd": round(q.generation_cost_usd, 6),
            "gen_attempts": q.generation_attempts,
        })
    quality_by_id = {x.question_id: x for x in pkg.quality}
    return {
        "run": pkg.run_id,
        "topic": pkg.topic,
        "supervisor": pkg.supervisor.supervisor_status,
        "supervisor_issues": pkg.supervisor.issues,
        "coverage_pct": pkg.coverage_matrix.coverage_pct,
        # Planner control-loop trace — the evidence the system decided rather than
        # ran a fixed pipeline.
        "plan_trace": [
            {
                "step": s.step, "action": s.action.value, "source": s.source,
                "reason": s.reason, "targets": s.targets,
                "bar": f"{s.bar_passed}/{s.bar_total}",
            }
            for s in pkg.plan_trace
        ],
        "quality_bar": {
            "passed": sum(1 for x in pkg.quality if x.passed),
            "total": len(pkg.quality),
            "failing": {
                x.question_id: x.failed_checks
                for x in pkg.quality if not x.passed
            },
        },
        "questions": questions,
    }


def export_package(pkg: AssessmentPackage, out_root: str = "outputs") -> Path:
    root = Path(out_root) / pkg.run_id
    root.mkdir(parents=True, exist_ok=True)

    _write(root / "package.json", pkg.model_dump_json(indent=2))
    _write(root / "coverage_matrix.json",
           json.dumps(pkg.coverage_matrix.model_dump(), indent=2))

    # Confidence report ---------------------------------------------------
    conf = {
        "run_id": pkg.run_id,
        "topic": pkg.topic,
        "questions": [
            {
                "question_id": q.question_id,
                "difficulty": q.difficulty.value,
                "confidence": q.confidence.confidence if q.confidence else 0,
                "status": q.confidence.status if q.confidence else "PENDING",
                "breakdown": q.confidence.model_dump() if q.confidence else {},
                "grading_execution": q.grading_execution.model_dump() if q.grading_execution else {},
            }
            for q in pkg.questions
        ],
        "approved": len(pkg.approved_questions),
        "total": len(pkg.questions),
    }
    _write(root / "confidence_report.json", json.dumps(conf, indent=2))

    # Hiring readiness report --------------------------------------------
    hire = {
        "run_id": pkg.run_id,
        "portfolio_coverage_score": pkg.portfolio_coverage_score,
        "portfolio_missing_areas": pkg.portfolio_missing_areas,
        "questions": [
            {
                "question_id": q.question_id,
                "confidence_score": q.confidence.confidence if q.confidence else 0,
                "role_alignment": q.role_alignment.model_dump() if q.role_alignment else {},
                "hiring_signal_score": q.hiring_signal.hiring_signal_score if q.hiring_signal else 0,
                "market_readiness": q.market_readiness.level.value if q.market_readiness else "",
                "estimated_interview_relevance": (
                    "High" if q.hiring_signal and q.hiring_signal.hiring_signal_score >= 70
                    else "Medium" if q.hiring_signal and q.hiring_signal.hiring_signal_score >= 50
                    else "Low"
                ),
            }
            for q in pkg.questions
        ],
    }
    _write(root / "hiring_readiness_report.json", json.dumps(hire, indent=2))

    # Evaluation report ---------------------------------------------------
    from ..config import Settings

    report = evaluate_batch(pkg.questions, pkg.coverage_matrix, Settings())
    report["supervisor"] = pkg.supervisor.model_dump()
    _write(root / "evaluation_report.json", json.dumps(report, indent=2))

    # Per-question artefacts ---------------------------------------------
    for q in pkg.questions:
        export_question(q, root / "questions" / q.question_id)

    # All questions in one file — easy to read and diff
    all_questions = [_clean_question_dict(q) for q in pkg.questions]
    _write(root / "questions.json", json.dumps({
        "run_id": pkg.run_id,
        "topic": pkg.topic,
        "total": len(all_questions),
        "questions": all_questions,
    }, indent=2))

    # Planner trace + quality-bar report ----------------------------------
    plan = {
        "run_id": pkg.run_id,
        "topic": pkg.topic,
        "steps": [
            {
                "step": s.step, "action": s.action.value, "source": s.source,
                "reason": s.reason, "targets": s.targets,
                "bar_passed": s.bar_passed, "bar_total": s.bar_total,
            }
            for s in pkg.plan_trace
        ],
        "quality": [x.model_dump() for x in pkg.quality],
        "final_supervisor": pkg.supervisor.supervisor_status,
    }
    _write(root / "plan_report.json", json.dumps(plan, indent=2))

    # Compact summary (token-efficient, human-readable) -------------------
    _write(root / "summary.json", json.dumps(_compact_summary(pkg), indent=2))

    # Token usage report --------------------------------------------------
    counter = getattr(pkg, "_token_counter", None)
    if counter is not None:
        _write(root / "token_report.json", json.dumps(counter.report(), indent=2))

    return root


# ===========================================================================
# v2 export — date-stamped run folder with YAML question/solution files
# ===========================================================================

def _slug(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return s[:maxlen] or "item"


def _dump_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _extract_notes_from_code(starter: str, reference: str, criteria) -> list[str]:
    """Derive notes by diffing the starter (buggy) and reference (correct) code via AST.

    Finds string literals and attribute chains that appear in the reference but not
    in the starter — these are the exact names the student must use.
    Also adds notes from evaluation_criteria targets for any value not already covered.
    """
    import ast as _ast

    def _strings(src: str) -> set:
        try:
            tree = _ast.parse(src)
        except SyntaxError:
            return set()
        return {
            node.value
            for node in _ast.walk(tree)
            if isinstance(node, _ast.Constant) and isinstance(node.value, str) and node.value.strip()
        }

    def _attr_chains(src: str) -> set:
        try:
            tree = _ast.parse(src)
        except SyntaxError:
            return set()
        chains = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Attribute):
                parts = []
                cur = node
                while isinstance(cur, _ast.Attribute):
                    parts.append(cur.attr)
                    cur = cur.value
                if len(parts) >= 2:
                    chains.add(".".join(reversed(parts)))
        return chains

    notes: list[str] = []
    seen: set[str] = set()

    if starter and reference:
        starter_strings = _strings(starter)
        ref_strings = _strings(reference)
        new_strings = ref_strings - starter_strings
        removed_strings = starter_strings - ref_strings

        for val in sorted(new_strings):
            if val.startswith("/") or len(val) > 2:
                if removed_strings:
                    wrong = next(iter(removed_strings))
                    note = f"Use '{val}' (not '{wrong}')"
                    removed_strings.discard(wrong)
                else:
                    note = f"Use exact value: '{val}'"
                if note not in seen:
                    notes.append(note)
                    seen.add(note)

        starter_attrs = _attr_chains(starter)
        ref_attrs = _attr_chains(reference)
        for chain in sorted(ref_attrs - starter_attrs):
            note = f"Use field access: {chain}"
            if note not in seen:
                notes.append(note)
                seen.add(note)

    # Fill in from criteria targets only when the target value isn't already in any note
    existing_text = " ".join(notes)
    for ec in (criteria or []):
        t = (ec.target or "").strip()
        if not t or t in existing_text:
            continue
        if t.startswith("/"):
            note = f"Topic/service name must be exactly: {t}"
        else:
            note = f"Use exact name: {t}"
        if note not in seen:
            notes.append(note)
            seen.add(note)

    return notes


def _question_yaml_dict(q: Question, md_source: str = "") -> dict:
    """Student-facing question.yaml — slim, task-driven format."""
    # Topic: prefer the md source filename, fall back to metadata topic or title
    topic = (
        md_source
        or (q.metadata.topic if q.metadata else "")
        or q.generation_skill
        or q.tested_skills[0] if q.tested_skills else q.title
    )

    # Files the student must edit
    files = []
    for f in q.files_to_edit:
        if f.path:
            files.append(f.path)
    if not files and q.file_to_edit:
        files.append(q.file_to_edit)
    if not files:
        files.append("node.py")

    # Notes: start from LLM-provided notes, then enrich with code diff
    llm_notes: list[str] = []
    if q.notes:
        llm_notes = [ln.lstrip("•-* ").strip() for ln in q.notes.splitlines() if ln.strip()]

    starter = q.boilerplate_code or (q.files_to_edit[0].starter_code if q.files_to_edit else "")
    reference = q.files_to_edit[0].reference_solution if q.files_to_edit else ""
    code_notes = _extract_notes_from_code(starter, reference, q.evaluation_criteria)

    # Merge: LLM notes first (they're more readable), then code-derived notes not already covered
    seen = set(llm_notes)
    all_notes = list(llm_notes)
    for n in code_notes:
        if n not in seen:
            all_notes.append(n)
            seen.add(n)

    # Build direct question (no story — just what to do)
    question_text = q.objective or q.scenario

    return {
        "question_id": q.question_id,
        "topic": topic,
        "difficulty": q.difficulty.value,
        "estimated_time_minutes": q.estimated_solve_minutes or (
            q.metadata.estimated_time_minutes if q.metadata else 15
        ),
        "question": question_text,
        "context": (q.context or q.scenario or "").strip(),
        "files_to_edit": files,
        "notes": all_notes,
        "tasks": q.tasks or ([q.objective] if q.objective else ["Complete the implementation"]),
        "skill": q.generation_skill or (q.tested_skills[0] if q.tested_skills else ""),
    }


def _solution_yaml_dict(q: Question) -> dict:
    """Reference solution, mirroring outputs/solution.json as YAML."""
    files = []
    for f in q.files_to_edit:
        content = f.reference_solution or f.starter_code
        if content:
            files.append({"path": f.path, "content": content})
    if not files and q.boilerplate_code:
        files.append({"path": q.file_to_edit or "node.py", "content": q.boilerplate_code})

    fs = q.file_structure
    pkg_name = fs.ros_package if fs and fs.ros_package else "ros2_pkg"
    deps = fs.dependencies if fs else ["rclpy"]
    setup_commands = [
        f"ros2 pkg create {pkg_name} --build-type ament_python --dependencies "
        + " ".join(deps)
    ]
    build_commands = [
        f"colcon build --packages-select {pkg_name}",
        "source install/setup.bash",
    ]
    verification = []
    for eo in q.expected_output:
        verification.append({
            "description": f"Verify: {eo.shell}",
            "expected": eo.output,
        })
    return {
        "question_id": q.question_id,
        "setup_commands": setup_commands,
        "files": files,
        "build_commands": build_commands,
        "run_commands": q.run_commands,
        "expected_output": [eo.model_dump() for eo in q.expected_output],
        "verification": verification,
        "key_concepts_demonstrated": q.tested_skills,
    }


def export_run_v2(
    pkg: AssessmentPackage,
    summary_text: str = "",
    skillset=None,
    out_root: str = "outputs",
    duration_seconds: float | None = None,
    loop_num: int = 1,
) -> Path:
    """Write the v2 run into a date-stamped folder with YAML artefacts.

        outputs/<YYYY-MM-DD_HH-MM-SS>_<topic-slug>/
            run_metadata.json, summary.md, skills.yaml
            questions/Q00N_<slug>/{question.yaml, solution.yaml,
                                   boilerplate/, evaluation/{test_*.py, grading.json}}
            rejected/R00N_<slug>/   ← same structure, questions that didn't pass
            reports/{coverage_matrix.json, confidence_report.json, supervisor_verdict.json}
    """
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    loop_tag = f"_loop{loop_num}" if loop_num > 1 else ""
    root = Path(out_root) / f"{stamp}{loop_tag}_{_slug(pkg.topic)}"
    root.mkdir(parents=True, exist_ok=True)

    # Run-level artefacts
    counter = getattr(pkg, "_token_counter", None)
    token_summary = counter.summary() if counter is not None else {}
    n_approved = len(pkg.approved_questions)
    meta: dict = {
        "run_id": pkg.run_id,
        "topic": pkg.topic,
        "loop_num": loop_num,
        "created_at": pkg.created_at.isoformat(),
        "md_hash": getattr(skillset, "md_hash", ""),
        "md_file": getattr(skillset, "md_file", ""),
        "num_questions": len(pkg.questions),
        "num_approved": n_approved,
        "num_rejected": len(pkg.questions) - n_approved,
        "supervisor_status": pkg.supervisor.supervisor_status,
    }
    if duration_seconds is not None:
        meta["duration_seconds"] = round(duration_seconds, 1)
    if token_summary:
        meta["token_usage"] = token_summary
    _write(root / "run_metadata.json", json.dumps(meta, indent=2))

    _write(root / "summary.md", summary_text or "")

    if skillset is not None:
        _dump_yaml(root / "skills.yaml", {
            "md_file": skillset.md_file,
            "md_hash": skillset.md_hash,
            "skills": [s.model_dump() for s in skillset.skills],
        })

    # Per-question YAML + boilerplate + evaluation
    # Approved questions go to questions/, rejected ones go to rejected/
    approved_ids = {q.question_id for q in pkg.approved_questions}
    approved_counter = 0
    rejected_counter = 0
    for q in pkg.questions:
        skill_slug = _slug(q.generation_skill or (q.tested_skills[0] if q.tested_skills else q.title), 24)
        is_approved = q.question_id in approved_ids
        if is_approved:
            approved_counter += 1
            qdir = root / "questions" / f"Q{approved_counter:03d}_{skill_slug}"
        else:
            rejected_counter += 1
            qdir = root / "rejected" / f"R{rejected_counter:03d}_{skill_slug}"
        md_name = getattr(skillset, "md_file", "") if skillset else ""
        _dump_yaml(qdir / "question.yaml", _question_yaml_dict(q, md_source=md_name))
        _dump_yaml(qdir / "solution.yaml", _solution_yaml_dict(q))

        # boilerplate/ — starter files the student edits (with bug markers)
        boilerplate = q.boilerplate_code or (q.files_to_edit[0].starter_code if q.files_to_edit else "")
        if boilerplate:
            fname = Path(q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else "node.py")).name
            _write(qdir / "boilerplate" / fname, boilerplate)

        # evaluation/ — per-task grading script
        _write(qdir / "evaluation" / "grading.py", _evaluate_script(q))

    # Reports
    _write(root / "reports" / "coverage_matrix.json",
           json.dumps(pkg.coverage_matrix.model_dump(), indent=2))

    student_conf = getattr(pkg, "_student_confidence", {})
    _write(root / "reports" / "confidence_report.json", json.dumps({
        "run_id": pkg.run_id,
        "topic": pkg.topic,
        "questions": [
            {
                "question_id": q.question_id,
                "difficulty": q.difficulty.value,
                "confidence": q.confidence.confidence if q.confidence else 0,
                "status": q.confidence.status if q.confidence else "PENDING",
                "breakdown": q.confidence.model_dump() if q.confidence else {},
                "student_confidence": student_conf.get(q.question_id, {}),
            }
            for q in pkg.questions
        ],
        "approved": len(pkg.approved_questions),
        "total": len(pkg.questions),
    }, indent=2))

    _write(root / "reports" / "supervisor_verdict.json",
           json.dumps(pkg.supervisor.model_dump(), indent=2))

    # Full token report (per-call breakdown + by_agent costs)
    if counter is not None:
        _write(root / "reports" / "token_report.json",
               json.dumps(counter.report(), indent=2))

    # Append one line to cross-run usage history at outputs root
    _append_usage_history(Path(out_root), meta, token_summary)

    return root


def _append_usage_history(out_root: Path, meta: dict, token_summary: dict) -> None:
    """Append a one-line JSON record to outputs/usage_history.jsonl."""
    import json as _json
    record = {
        "run_id": meta.get("run_id"),
        "topic": meta.get("topic"),
        "created_at": meta.get("created_at"),
        "num_questions": meta.get("num_questions"),
        "num_approved": meta.get("num_approved"),
        "supervisor_status": meta.get("supervisor_status"),
        "duration_seconds": meta.get("duration_seconds"),
    }
    record.update(token_summary)
    hist_path = out_root / "usage_history.jsonl"
    out_root.mkdir(parents=True, exist_ok=True)
    with hist_path.open("a", encoding="utf-8") as f:
        f.write(_json.dumps(record) + "\n")
