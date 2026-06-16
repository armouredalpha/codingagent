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
    """Generate a runnable evaluation script with per-criterion scoring."""
    ec_repr = json.dumps([ec.model_dump() for ec in q.evaluation_criteria], indent=4)
    file_path = q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else "node.py")
    lines = [
        f'"""',
        f"Evaluation script for {q.question_id}: {q.title}",
        f"",
        f"Run:   python evaluate.py",
        f"Total: 100 points",
        f'"""',
        f"",
        f"import subprocess",
        f"import sys",
        f"import time",
        f"",
        f"QUESTION_ID = {q.question_id!r}",
        f"FILE_TO_EDIT = {file_path!r}",
        f"",
        f"EVALUATION_CRITERIA = {ec_repr}",
        f"",
        f"",
        f"# ── Check implementations ────────────────────────────────────────────",
        f"",
        f"def check_node_exists(target: str) -> bool:",
        f"    result = subprocess.run(['ros2', 'node', 'list'], capture_output=True, text=True, timeout=5)",
        f"    return f'/{{target}}' in result.stdout or target in result.stdout",
        f"",
        f"",
        f"def check_topic_active(target: str, expected: str = '') -> bool:",
        f"    result = subprocess.run(['ros2', 'topic', 'list'], capture_output=True, text=True, timeout=5)",
        f"    return target in result.stdout",
        f"",
        f"",
        f"def check_publish_rate(target: str, expected: str) -> bool:",
        f"    try:",
        f"        hz = float(expected)",
        f"        result = subprocess.run(",
        f"            ['ros2', 'topic', 'hz', target, '--window', '10'],",
        f"            capture_output=True, text=True, timeout=15,",
        f"        )",
        f"        for line in result.stdout.splitlines():",
        f"            if 'average rate' in line:",
        f"                rate = float(line.split(':')[1].strip().split()[0])",
        f"                return abs(rate - hz) <= hz * 0.15  # 15% tolerance",
        f"    except Exception:",
        f"        pass",
        f"    return False",
        f"",
        f"",
        f"def check_service_exists(target: str, expected: str = '') -> bool:",
        f"    result = subprocess.run(['ros2', 'service', 'list'], capture_output=True, text=True, timeout=5)",
        f"    return target in result.stdout",
        f"",
        f"",
        f"def check_parameter_set(target: str, expected: str) -> bool:",
        f"    result = subprocess.run(['ros2', 'param', 'get', '--', target], capture_output=True, text=True, timeout=5)",
        f"    return expected in result.stdout",
        f"",
        f"",
        f"def check_tf_frame_exists(target: str, expected: str = '') -> bool:",
        f"    result = subprocess.run(['ros2', 'run', 'tf2_ros', 'tf2_echo', target, target],",
        f"                            capture_output=True, text=True, timeout=5)",
        f"    return 'Transform' in result.stdout or 'frames' in result.stdout",
        f"",
        f"",
        f"CHECK_FN = {{",
        f"    'node_exists': lambda ec: check_node_exists(ec['target']),",
        f"    'topic_active': lambda ec: check_topic_active(ec['target'], ec.get('expected', '')),",
        f"    'service_exists': lambda ec: check_service_exists(ec['target'], ec.get('expected', '')),",
        f"    'publish_rate': lambda ec: check_publish_rate(ec['target'], ec.get('expected', '0')),",
        f"    'parameter_set': lambda ec: check_parameter_set(ec['target'], ec.get('expected', '')),",
        f"    'tf_frame_exists': lambda ec: check_tf_frame_exists(ec['target'], ec.get('expected', '')),",
        f"    'behaviour': lambda ec: True,   # manual or custom assertion required",
        f"    'message_field': lambda ec: True,",
        f"}}",
        f"",
        f"",
        f"def run_evaluation() -> int:",
        f"    print(f'\\n=== Evaluating {{QUESTION_ID}} ===\\n')",
        f"    total = 0",
        f"    for ec in EVALUATION_CRITERIA:",
        f"        fn = CHECK_FN.get(ec['check'], lambda ec: False)",
        f"        try:",
        f"            passed = fn(ec)",
        f"        except Exception as e:",
        f"            passed = False",
        f"            print(f\"  [ERROR] {{ec['id']}}: {{e}}\")",
        f"        pts = ec['points'] if passed else 0",
        f"        total += pts",
        f"        status = '✓ PASS' if passed else '✗ FAIL'",
        f"        print(f\"  {{status}} {{ec['id']}} (+{{pts}}/{{ec['points']}}) — {{ec['description']}}\")",
        f"    print(f'\\nFinal score: {{total}} / 100')",
        f"    return total",
        f"",
        f"",
        f"if __name__ == '__main__':",
        f"    score = run_evaluation()",
        f"    sys.exit(0 if score >= 70 else 1)",
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
        "Your submission is scored out of 100 points by the automated checks in "
        "`evaluate.py` (see `grading.json` for the criteria). Run:",
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


def _question_yaml_dict(q: Question) -> dict:
    """Student-facing question, mirroring outputs/question.json as YAML.

    Adds the primary_skill / secondary_concepts weighting from the requested
    input/output format. starter_code is null — the solution lives in solution.yaml.
    """
    dec = q.detailed_evaluation_criteria
    concepts = q.metadata.concepts if q.metadata else q.tested_skills
    primary = q.generation_skill or (q.tested_skills[0] if q.tested_skills else "")
    secondary = [c for c in concepts if c != primary]

    metadata = (
        q.metadata.model_dump()
        if q.metadata
        else {
            "topic": q.title,
            "difficulty_level": q.difficulty.value,
            "estimated_time_minutes": q.estimated_solve_minutes,
            "language": "Python",
            "ros_version": "ROS2",
            "concepts": concepts,
        }
    )

    return {
        "question_id": q.question_id,
        "metadata": metadata,
        "title": q.title,
        "context": q.context or q.scenario,
        "scenario": q.scenario,
        "prerequisites": q.prerequisites,
        "notes": q.notes,
        "objective": q.objective,
        "constraints": q.constraints,
        "tested_skills": q.tested_skills,
        "common_mistakes": q.common_mistakes,
        "parts": [p.model_dump() for p in q.parts],
        "tasks": q.tasks,
        "file_structure": q.file_structure.model_dump() if q.file_structure else None,
        "starter_code": None,
        "expected_output": [eo.model_dump() for eo in q.expected_output],
        "run_commands": q.run_commands,
        "evaluation_criteria": {
            "compiles_without_error": dec.compiles_without_error if dec else True,
            "primary_skill": {"skill": primary, "weight": 70},
            "secondary_concepts": {"weight": 30, "concepts": secondary},
            "nodes": dec.nodes if dec else None,
            "topics_subscribed": dec.topics_subscribed if dec else None,
            "topics_published": dec.topics_published if dec else None,
            "services": dec.services if dec else None,
            "publish_rate": dec.publish_rate if dec else None,
        },
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
) -> Path:
    """Write the v2 run into a date-stamped folder with YAML artefacts.

        outputs/<YYYY-MM-DD_HH-MM-SS>_<topic-slug>/
            run_metadata.json, summary.md, skills.yaml
            questions/Q00N_<slug>/{question.yaml, solution.yaml,
                                   boilerplate/, evaluation/{test_*.py, grading.json}}
            reports/{coverage_matrix.json, confidence_report.json, supervisor_verdict.json}
    """
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    root = Path(out_root) / f"{stamp}_{_slug(pkg.topic)}"
    root.mkdir(parents=True, exist_ok=True)

    # Run-level artefacts
    _write(root / "run_metadata.json", json.dumps({
        "run_id": pkg.run_id,
        "topic": pkg.topic,
        "created_at": pkg.created_at.isoformat(),
        "md_hash": getattr(skillset, "md_hash", ""),
        "md_file": getattr(skillset, "md_file", ""),
        "num_questions": len(pkg.questions),
        "supervisor_status": pkg.supervisor.supervisor_status,
    }, indent=2))

    _write(root / "summary.md", summary_text or "")

    if skillset is not None:
        _dump_yaml(root / "skills.yaml", {
            "md_file": skillset.md_file,
            "md_hash": skillset.md_hash,
            "skills": [s.model_dump() for s in skillset.skills],
        })

    # Per-question YAML + boilerplate + evaluation
    for i, q in enumerate(pkg.questions, start=1):
        skill_slug = _slug(q.generation_skill or (q.tested_skills[0] if q.tested_skills else q.title), 24)
        qdir = root / "questions" / f"Q{i:03d}_{skill_slug}"
        _dump_yaml(qdir / "question.yaml", _question_yaml_dict(q))
        _dump_yaml(qdir / "solution.yaml", _solution_yaml_dict(q))

        # boilerplate/ — starter files the student edits
        boilerplate = q.boilerplate_code or (q.files_to_edit[0].starter_code if q.files_to_edit else "")
        if boilerplate:
            fname = Path(q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else "node.py")).name
            _write(qdir / "boilerplate" / fname, boilerplate)

        # evaluation/ — runnable grading script + grading.json
        _write(qdir / "evaluation" / f"test_{q.question_id}.py", _evaluate_script(q))
        _write(qdir / "evaluation" / "grading.json", json.dumps(_grading_dict(q), indent=2))

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

    return root
