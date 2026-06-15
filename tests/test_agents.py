"""Focused unit tests for individual agents and evaluators.

Agents return an :class:`AgentResult` whose ``payload`` carries plain dicts;
the orchestrator reconstructs Pydantic models from them. Validation agents
mutate the ``Question`` objects passed to them in place. These tests mirror
that contract.
"""
from __future__ import annotations

from robo_assess.config import Settings
from robo_assess.memory import Memory
from robo_assess.vectorstore import VectorStore
from robo_assess.schemas import (
    AssessmentRequest, SyllabusAnalysis, CoverageMatrix, Question,
)
from robo_assess.agents.syllabus_parser import SyllabusParserAgent
from robo_assess.agents.coverage_matrix import CoverageMatrixAgent
from robo_assess.agents.question_generator import QuestionGeneratorAgent
from robo_assess.agents.scope_agent import ScopeComplianceAgent
from robo_assess.evaluators.dataset_evaluator import evaluate_batch


def _kw(tmp_path):
    # This is an LLM agent: the generator needs a client. Use the deterministic
    # FakeLLM from conftest. Critic-specific tests override `llm` via _retry_kw.
    from .conftest import FakeLLM

    s = Settings()
    s.provider = "openrouter"
    return dict(
        settings=s,
        llm=FakeLLM(),
        memory=Memory(str(tmp_path / "m.db")),
        vectorstore=VectorStore(str(tmp_path / "v.json")),
    )


def _make_questions(kw, skills, n):
    analysis = SyllabusAnalysis(skills=skills)
    cov = CoverageMatrix(**CoverageMatrixAgent(**kw).run(skills).payload["coverage"])
    payload = QuestionGeneratorAgent(**kw).run(analysis, cov, n).payload
    qs = [Question(**q) for q in payload["questions"]]
    return analysis, cov, qs


def test_syllabus_parser_extracts_skills(tmp_path):
    agent = SyllabusParserAgent(**_kw(tmp_path))
    req = AssessmentRequest(
        topic="ROS2", syllabus=["ROS2 publisher node", "ROS2 services"],
        num_questions=2)
    res = agent.run(req)
    analysis = SyllabusAnalysis(**res.payload["analysis"])
    assert analysis.skills


def test_scope_agent_flags_gated_tech(tmp_path):
    kw = _kw(tmp_path)
    analysis, cov, qs = _make_questions(kw, ["ROS2 publisher node"], 2)
    # Inject gated-tech into a constraint, then re-scope (mutates in place).
    qs[0].constraints.append("Use the Nav2 stack to plan a path")
    ScopeComplianceAgent(**kw).run(qs, analysis)
    assert any(q.scope_violations for q in qs), "scope agent missed gated tech"


def test_coverage_marks_skills(tmp_path):
    kw = _kw(tmp_path)
    cov_agent = CoverageMatrixAgent(**kw)
    cov = CoverageMatrix(
        **cov_agent.run(["ROS2 publisher node", "ROS2 subscriber node"]).payload["coverage"])
    assert cov.coverage_pct == 0.0
    cov_agent.mark(cov, ["ROS2 publisher node"])
    assert 0 < cov.coverage_pct < 100


def test_evaluate_batch_scores(tmp_path):
    kw = _kw(tmp_path)
    analysis, cov, qs = _make_questions(kw, ["ROS2 publisher node", "ROS2 services"], 3)
    report = evaluate_batch(qs, cov, Settings())
    assert "overall_score" in report
    assert 0 <= report["overall_score"] <= 100
    assert report["criteria"]


# --------------------------------------------------------------------------- #
# Generator prompt ⇄ parser contract
# --------------------------------------------------------------------------- #
def test_generator_two_block_parses_into_question():
    """The new question_generator.txt output shape must populate a Question
    with no field falling back to defaults, and 4 criteria summing to 100."""
    from robo_assess.agents.question_generator import (
        _parse_three_block_response, _parse_llm_question,
    )
    from robo_assess.schemas import Difficulty

    sample = (
        '{\n'
        '  "title": "Complete the velocity command publisher",\n'
        '  "robot": "Warehouse AMR",\n'
        '  "scenario": "The drive node is half-finished.",\n'
        '  "objective": "Publish 0.25 m/s on /cmd_vel at 10 Hz.",\n'
        '  "constraints": ["Use geometry_msgs/Twist."],\n'
        '  "tested_skills": ["ROS2 publisher node"],\n'
        '  "evaluation_criteria": [\n'
        '    {"id":"EC1","check":"node_exists","target":"velocity_commander","expected":"running","points":25,"description":"Node alive."},\n'
        '    {"id":"EC2","check":"topic_active","target":"/cmd_vel","expected":"geometry_msgs/Twist","points":25,"description":"Publishes Twist."},\n'
        '    {"id":"EC3","check":"publish_rate","target":"/cmd_vel","expected":"10.0","points":25,"description":"10 Hz."},\n'
        '    {"id":"EC4","check":"behaviour","target":"/cmd_vel","expected":"linear.x=0.25","points":25,"description":"0.25 m/s."}\n'
        '  ],\n'
        '  "common_mistakes": ["Forgetting the timer."],\n'
        '  "estimated_solve_minutes": 20,\n'
        '  "file_to_edit": "scripts/velocity_commander.py"\n'
        '}\n'
        '---SOLUTION_FILE---\n'
        'import rclpy\n\n# ── STUDENT IMPLEMENTATION\n# TODO START\npass\n# TODO END\n'
    )
    raw, boilerplate, reference = _parse_three_block_response(sample)
    q = _parse_llm_question(raw, boilerplate, reference, 1, "ROS2 publisher node",
                            Difficulty.EASY, "warehouse")

    assert q.title == "Complete the velocity command publisher"
    assert q.scenario and q.objective and q.robot == "Warehouse AMR"
    assert q.constraints and q.tested_skills
    assert len(q.evaluation_criteria) == 4
    assert sum(c.points for c in q.evaluation_criteria) == 100
    assert q.file_to_edit == "scripts/velocity_commander.py"
    assert "# TODO START" in q.boilerplate_code


# --------------------------------------------------------------------------- #
# Batched LLM critics — per-question retry, no whole-batch rerun, fallback
# --------------------------------------------------------------------------- #
from collections import Counter
from robo_assess.llm_client import TokenUsage
from robo_assess.schemas import Difficulty
from robo_assess.agents.difficulty_agent import DifficultyCalibrationAgent


class _FakeLLM:
    """Records which ids each call asks for. `omit_first` ids are missing from
    the batch response but returned on their length-1 retry; `always_bad` ids
    never return a valid verdict (forcing rule-based fallback)."""

    offline = False

    def __init__(self, all_ids, verdict_for, omit_first=(), always_bad=()):
        self.all_ids = list(all_ids)
        self.verdict_for = verdict_for
        self.omit_first = set(omit_first)
        self.always_bad = set(always_bad)
        self.calls: list[list[str]] = []
        self._seen: Counter = Counter()

    def complete_json(self, system, user, **kw):
        asked = [qid for qid in self.all_ids if f'"id": "{qid}"' in user]
        self.calls.append(asked)
        results = []
        for qid in asked:
            self._seen[qid] += 1
            if qid in self.always_bad:
                results.append({"id": qid})  # missing required fields → invalid
            elif qid in self.omit_first and self._seen[qid] == 1:
                continue  # omitted from the batch response
            else:
                results.append({"id": qid, **self.verdict_for(qid)})
        return {"results": results}, TokenUsage(input_tokens=10, output_tokens=10)


def _retry_kw(tmp_path, llm):
    kw = _kw(tmp_path)
    kw["llm"] = llm
    return kw


def test_scope_critic_batch_retry_and_fallback(tmp_path):
    # Build 3 questions; give B and C a gated-tech constraint so rule-based flags them.
    base_kw = _kw(tmp_path)
    analysis, cov, qs = _make_questions(base_kw, ["ROS2 publisher node"], 3)
    a, b, c = qs[0].question_id, qs[1].question_id, qs[2].question_id
    qs[1].constraints.append("Use the Nav2 stack to plan a path")
    qs[2].constraints.append("Use the Nav2 stack to plan a path")

    # LLM says every question is in-scope (overriding the rule-based Nav2 flag).
    def verdict(_qid):
        return {"classification": "IN_SCOPE", "question_is_out_of_scope": False,
                "out_of_scope_concepts": [], "coverage_score": 100}

    llm = _FakeLLM([a, b, c], verdict, omit_first=[b], always_bad=[c])
    agent = ScopeComplianceAgent(**_retry_kw(tmp_path, llm))
    agent.run(qs, analysis)

    # Pass 1 asks all three together; retries are length-1 for exactly B and C.
    assert llm.calls[0] == [a, b, c]
    assert all(len(call) == 1 for call in llm.calls[1:])
    assert sorted(call[0] for call in llm.calls[1:]) == sorted([b, c])

    # A (LLM in-scope) and B (recovered on retry) → not flagged.
    # C (never recovered) → rule-based Nav2 flag stands.
    by_id = {q.question_id: q for q in qs}
    assert not by_id[a].scope_violations
    assert not by_id[b].scope_violations
    assert by_id[c].scope_violations  # fell back to rule-based


def test_difficulty_critic_overrides_and_falls_back(tmp_path):
    base_kw = _kw(tmp_path)
    analysis, cov, qs = _make_questions(base_kw, ["ROS2 publisher node"], 2)
    for q in qs:
        q.difficulty = Difficulty.EASY
    a, b = qs[0].question_id, qs[1].question_id

    def verdict(_qid):
        return {"difficulty": "hard", "rationale": "llm says hard"}

    llm = _FakeLLM([a, b], verdict, always_bad=[b])
    agent = DifficultyCalibrationAgent(**_retry_kw(tmp_path, llm))
    res = agent.run(qs)

    # Batch asked both; B retried alone; batch never re-run as a whole.
    assert llm.calls[0] == [a, b]
    assert llm.calls[1:] == [[b]]
    # A flagged as mismatch via LLM (easy declared vs hard verdict).
    qids = [m["qid"] for m in res.payload["mismatches"]]
    assert a in qids


# --------------------------------------------------------------------------- #
# Independent LLM judge in the Supervisor (opt-in second opinion)
# --------------------------------------------------------------------------- #
def test_supervisor_independent_judge_rejects(tmp_path):
    from robo_assess.agents.supervisor import SupervisorAgent
    from robo_assess.schemas import (
        AssessmentPackage, SyllabusAnalysis, SourceResearch, CoverageMatrix,
        Question, BloomLevel, ConfidenceBreakdown,
    )

    def _q(qid):
        q = Question(
            question_id=qid, title=f"t{qid}", difficulty=Difficulty.EASY,
            bloom_level=BloomLevel.APPLY, scenario="warehouse robot",
            objective="publish", tested_skills=["ROS2 publisher node"],
        )
        q.confidence = ConfidenceBreakdown(status="APPROVED", confidence=90.0)
        return q

    qa, qb = _q("Q001_a"), _q("Q002_b")
    pkg = AssessmentPackage(
        run_id="r", topic="t", syllabus=["ROS2 publisher node"],
        syllabus_analysis=SyllabusAnalysis(skills=["ROS2 publisher node"]),
        source_research=SourceResearch(),
        coverage_matrix=CoverageMatrix(matrix={"ROS2 publisher node": True}),
        questions=[qa, qb],
    )

    # Judge approves A, rejects B.
    def verdict(qid):
        if qid == "Q002_b":
            return {"verdict": "REJECT", "reasons": ["criteria do not match the task"]}
        return {"verdict": "APPROVE", "reasons": []}

    kw = _kw(tmp_path)
    kw["llm"] = _FakeLLM(["Q001_a", "Q002_b"], verdict)
    kw["settings"].enable_llm_judge = True
    sup = SupervisorAgent(**kw)

    v = sup.validate(pkg, evaluation_score=90.0)
    # B is routed to regeneration and raises a batch issue; A is untouched.
    assert "Q002_b" in v.failing_question_ids
    assert "Q001_a" not in v.failing_question_ids
    assert any("independent judge" in i for i in v.issues)
    assert v.supervisor_status == "REJECTED"


def test_supervisor_judge_disabled_by_default(tmp_path):
    """With the flag off, the judge never runs even if an LLM is present."""
    from robo_assess.agents.supervisor import SupervisorAgent
    from robo_assess.schemas import (
        AssessmentPackage, SyllabusAnalysis, SourceResearch, CoverageMatrix,
        Question, BloomLevel, ConfidenceBreakdown,
    )
    q = Question(
        question_id="Q1", title="t", difficulty=Difficulty.EASY,
        bloom_level=BloomLevel.APPLY, scenario="warehouse robot",
        objective="publish", tested_skills=["ROS2 publisher node"],
    )
    q.confidence = ConfidenceBreakdown(status="APPROVED", confidence=90.0)
    pkg = AssessmentPackage(
        run_id="r", topic="t", syllabus=["ROS2 publisher node"],
        syllabus_analysis=SyllabusAnalysis(skills=["ROS2 publisher node"]),
        source_research=SourceResearch(),
        coverage_matrix=CoverageMatrix(matrix={"ROS2 publisher node": True}),
        questions=[q],
    )
    llm = _FakeLLM(["Q1"], lambda qid: {"verdict": "REJECT", "reasons": ["x"]})
    kw = _kw(tmp_path)
    kw["llm"] = llm
    # enable_llm_judge defaults False
    SupervisorAgent(**kw).validate(pkg, evaluation_score=90.0)
    assert llm.calls == []  # judge never invoked
