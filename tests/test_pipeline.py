"""End-to-end pipeline tests — driven by the injected FakeLLM (see conftest)."""
from __future__ import annotations

from robo_assess.agents.orchestrator import Orchestrator
from robo_assess.schemas import AssessmentRequest, Difficulty
from robo_assess.workflows.assessment_workflow import export_package


REQUEST = AssessmentRequest(
    topic="ROS2 Fundamentals",
    syllabus=[
        "ROS2 publisher node",
        "ROS2 subscriber node",
        "ROS2 services",
        "TF2 transforms",
        "ROS2 parameters",
        "ROS2 launch files",
    ],
    num_questions=6,
)


def test_imports():
    import robo_assess
    assert robo_assess.__version__


def test_pipeline_runs_and_approves(tmp_settings):
    orch = Orchestrator(tmp_settings)
    pkg = orch.run(REQUEST)

    # Core guarantees
    assert pkg.questions, "no questions generated"
    assert pkg.supervisor.supervisor_status == "APPROVED"
    assert pkg.coverage_matrix.coverage_pct == 100.0
    assert len(pkg.approved_questions) >= 1


def test_difficulty_mix_present(tmp_settings):
    orch = Orchestrator(tmp_settings)
    pkg = orch.run(REQUEST)
    diffs = {q.difficulty for q in pkg.questions}
    # With 6 questions and a 30/50/20 split we expect at least easy+medium.
    assert Difficulty.EASY in diffs
    assert Difficulty.MEDIUM in diffs


def test_every_question_is_auto_gradable(tmp_settings):
    orch = Orchestrator(tmp_settings)
    pkg = orch.run(REQUEST)
    for q in pkg.questions:
        assert q.auto_gradable, f"{q.question_id} is not auto-gradable"
        # New-style questions carry evaluation_criteria; legacy ones carry
        # hidden_checks. Either is a valid machine-gradable contract.
        assert q.evaluation_criteria or q.hidden_checks, \
            f"{q.question_id} has no grading criteria"


def test_no_scope_violations_in_fundamentals(tmp_settings):
    # Fundamentals syllabus has no gated tech, so nothing should be flagged.
    orch = Orchestrator(tmp_settings)
    pkg = orch.run(REQUEST)
    for q in pkg.questions:
        assert not q.scope_violations, f"{q.question_id}: {q.scope_violations}"


def test_export_writes_full_package(tmp_settings):
    orch = Orchestrator(tmp_settings)
    pkg = orch.run(REQUEST)
    out = export_package(pkg, tmp_settings.outputs_dir)

    assert (out / "package.json").is_file()
    assert (out / "coverage_matrix.json").is_file()
    assert (out / "confidence_report.json").is_file()
    assert (out / "hiring_readiness_report.json").is_file()
    assert (out / "evaluation_report.json").is_file()
    qdirs = list((out / "questions").iterdir())
    assert len(qdirs) == len(pkg.questions)
    for qd in qdirs:
        assert (qd / "README.md").is_file()
        assert (qd / "grading.json").is_file()
        assert (qd / "question.json").is_file()
