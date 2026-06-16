"""
robo_assess.schemas
===================

All Pydantic v2 data models shared across the multi-agent robotics
assessment pipeline.

The models are intentionally compact (token-efficient) but fully typed.
Every agent consumes and returns one of these models, which lets the
Orchestrator and Supervisor validate hand-offs structurally rather than
by parsing free text.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class RoleLevel(str, Enum):
    INTERN = "Robotics Intern"
    JUNIOR = "Junior Robotics Engineer"
    ENGINEER = "Robotics Engineer"
    SENIOR = "Senior Robotics Engineer"


class ReadinessLevel(str, Enum):
    BEGINNER = "Beginner"
    EMPLOYABLE = "Employable"
    JOB_READY = "Job Ready"
    INDUSTRY_READY = "Industry Ready"
    ADVANCED = "Advanced Industry Ready"


class CheckType(str, Enum):
    NODE_EXISTS = "node_exists"
    TOPIC_EXISTS = "topic_exists"
    TOPIC_ACTIVE = "topic_active"
    SERVICE_EXISTS = "service_exists"
    TF_EXISTS = "tf_exists"
    TF_FRAME_EXISTS = "tf_frame_exists"
    PARAMETER_EXISTS = "parameter_exists"
    PARAMETER_SET = "parameter_set"
    PUBLISH_RATE = "publish_rate"
    MESSAGE_TYPE = "message_type"
    MESSAGE_FIELD = "message_field"
    BEHAVIOUR = "behaviour"
    SIMULATION = "simulation"


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------
class AssessmentRequest(BaseModel):
    """Top-level input provided by an instructor."""

    topic: str = Field(..., min_length=2)
    syllabus: list[str] = Field(..., min_length=1)
    sources: list[str] = Field(default_factory=list)
    existing_questions: list[str] = Field(default_factory=list)
    num_questions: int = Field(default=6, ge=1, le=60)

    @field_validator("syllabus")
    @classmethod
    def _strip_syllabus(cls, v: list[str]) -> list[str]:
        return [s.strip() for s in v if s and s.strip()]


# ---------------------------------------------------------------------------
# NEW: Markdown parsing & skills extraction
# ---------------------------------------------------------------------------
class SkillEntry(BaseModel):
    """A single extracted skill from the .md teaching material."""
    skill: str
    section: str
    bloom_level: str = "understand"
    difficulty_hint: str = "medium"


class SkillSet(BaseModel):
    """Complete skill extraction result from a .md file."""
    md_file: str
    md_hash: str
    skills: list[SkillEntry] = Field(default_factory=list)
    sections_covered: list[str] = Field(default_factory=list)
    total_sections: int = 0
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# NEW: Single-command generate flow (v2)
# ---------------------------------------------------------------------------
class StudentProfile(BaseModel):
    """A baseline student skill profile used by the confidence scorer to judge
    whether a candidate at this level could solve a generated question."""
    level: str                                  # easy | medium | hard
    skills: list[str] = Field(default_factory=list)
    ros2_experience: str = "beginner"           # beginner | intermediate | advanced


class SkillSpec(BaseModel):
    """The primary skill a question must assess, with target cognitive level and
    difficulty (mirrors the `selected_skill` block of the input format)."""
    skill: str
    bloom_level: str = "apply"
    difficulty: str = "easy"


class QuestionScope(BaseModel):
    """Supporting concepts a question may draw on. Excludes the selected skill."""
    concepts_allowed: list[str] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    """One question-generation request, matching the documented input format:

        topic_name, selected_skill {skill, bloom_level, difficulty},
        question_scope {concepts_allowed}, md_file, md_hash
    """
    topic_name: str
    selected_skill: SkillSpec
    question_scope: QuestionScope = Field(default_factory=QuestionScope)
    md_file: str = ""
    md_hash: str = ""


# ---------------------------------------------------------------------------
# NEW: Evaluation comparisons
# ---------------------------------------------------------------------------
class EvalReference(BaseModel):
    """One reference question from the evaluation set."""
    id: str
    title: str
    difficulty: str
    scenario: str
    skills: list[str] = Field(default_factory=list)
    solution_summary: str = ""


class EvalComparison(BaseModel):
    """Result of comparing a generated question to eval references."""
    eval_match_score: float = Field(default=0.0, ge=0.0, le=100.0)
    closest_refs: list[str] = Field(default_factory=list)
    difficulty_verdict: str = "medium"
    style_notes: str = ""


# ---------------------------------------------------------------------------
# NEW: LLM Critic feedback
# ---------------------------------------------------------------------------
class CriticFeedback(BaseModel):
    """Detailed feedback from the LLM Critic for question regeneration."""
    issues: list[str] = Field(default_factory=list)
    fix_directives: list[str] = Field(default_factory=list)
    severity: str = "minor"  # minor/major/reject


# ---------------------------------------------------------------------------
# Agent 1 — Syllabus Parser
# ---------------------------------------------------------------------------
class SyllabusAnalysis(BaseModel):
    skills: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    apis: list[str] = Field(default_factory=list)
    config_elements: list[str] = Field(default_factory=list)
    ros_components: list[str] = Field(default_factory=list)
    difficulty_range: str = "easy-hard"


# ---------------------------------------------------------------------------
# Agent 2 — Source Research
# ---------------------------------------------------------------------------
class SourceResearch(BaseModel):
    industry_patterns: list[str] = Field(default_factory=list)
    common_errors: list[str] = Field(default_factory=list)
    implementation_styles: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent 3 — Coverage Matrix
# ---------------------------------------------------------------------------
class CoverageMatrix(BaseModel):
    """Maps every syllabus skill -> whether a question tests it yet."""

    matrix: dict[str, bool] = Field(default_factory=dict)

    @property
    def covered(self) -> list[str]:
        return [k for k, v in self.matrix.items() if v]

    @property
    def missing(self) -> list[str]:
        return [k for k, v in self.matrix.items() if not v]

    @property
    def coverage_pct(self) -> float:
        if not self.matrix:
            return 0.0
        return round(100.0 * len(self.covered) / len(self.matrix), 1)


# ---------------------------------------------------------------------------
# Auto-grading metadata
# ---------------------------------------------------------------------------
class EvaluationCriterion(BaseModel):
    """New-style grading criterion with explicit point allocation."""
    id: str
    check: str          # check type string (node_exists, topic_active, etc.)
    target: str         # node name, topic path, field path
    expected: str = ""  # expected value or message type
    points: int = Field(default=25, ge=0, le=100)
    description: str    # non-empty human-readable description


class GradingCheck(BaseModel):
    check_type: CheckType
    target: str  # e.g. "/cmd_vel" or "velocity_publisher"
    expected: str  # e.g. "geometry_msgs/Twist" or "10.0"
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    description: str = ""


class HiddenTest(BaseModel):
    name: str
    kind: str  # positive | negative | edge | failure
    description: str
    assertion: str


# ---------------------------------------------------------------------------
# Files & packages
# ---------------------------------------------------------------------------
class EditableFile(BaseModel):
    path: str
    language: str  # python | yaml | launch | urdf | xacro
    starter_code: str = ""
    reference_solution: str = ""


class PackageStructure(BaseModel):
    name: str
    tree: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# New detailed question format (matching evaluations/question.json)
# ---------------------------------------------------------------------------
class FileToCreate(BaseModel):
    """File to be created as part of the question solution."""
    path: str
    role: str = ""


class FileStructure(BaseModel):
    """Detailed package and file structure specification."""
    ros_package: Optional[str] = None
    dependencies: list[str] = Field(default_factory=list)
    files_to_create: list[FileToCreate] = Field(default_factory=list)


class Part(BaseModel):
    """A multi-part question section."""
    label: str  # "Part I", "Part II", etc.
    tasks: list[str] = Field(default_factory=list)


class ExpectedOutput(BaseModel):
    """Expected output from running the solution."""
    shell: str  # "Shell #1", "Shell #2 (service call)", etc.
    output: str


class EvaluationCriteria(BaseModel):
    """Detailed evaluation requirements for executable testing."""
    compiles_without_error: bool = True
    nodes: Optional[list[str]] = None
    topics_subscribed: Optional[list[str]] = None
    topics_published: Optional[list[str]] = None
    services: Optional[list[str]] = None
    publish_rate: Optional[float] = None


class QuestionMetadata(BaseModel):
    """Metadata for a detailed question format."""
    topic: str
    difficulty_level: str  # "easy", "medium", "hard"
    estimated_time_minutes: int
    language: str = "Python"
    ros_version: str = "ROS2"
    concepts: list[str] = Field(default_factory=list)


class StarterCodeBlock(BaseModel):
    """A starter code file provided to students."""
    filename: str
    content: str


# ---------------------------------------------------------------------------
# Role / hiring models (Agents 12-14)
# ---------------------------------------------------------------------------
class RoleAlignment(BaseModel):
    primary_role: RoleLevel
    secondary_roles: list[RoleLevel] = Field(default_factory=list)
    experience_range: str = "0-2 Years"
    interview_round: str = "Technical Screening"
    estimated_solve_time_minutes: int = 45


class HiringSignal(BaseModel):
    hiring_signal_score: int = Field(ge=0, le=100)
    reason: list[str] = Field(default_factory=list)


class MarketReadiness(BaseModel):
    level: ReadinessLevel
    reason: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------
class ConfidenceBreakdown(BaseModel):
    coverage: float = 0.0
    difficulty: float = 0.0
    originality: float = 0.0
    scope: float = 0.0
    auto_grading: float = 0.0
    format_quality: float = 0.0
    confidence: float = 0.0           # calibrated value used for the APPROVED gate
    raw_confidence: float = 0.0       # pre-calibration weighted heuristic score
    calibrated: bool = False          # True when a fitted calibrator was applied
    status: str = "PENDING"


# ---------------------------------------------------------------------------
# Executable grading (Agent 10 — real test execution)
# ---------------------------------------------------------------------------
class GradingExecution(BaseModel):
    """Result of actually *running* the hidden tests, not just declaring them.

    A question's grading is trustworthy only when the reference solution
    PASSES the generated tests AND the starter scaffold FAILS them — i.e. the
    tests discriminate a correct solution from an unsolved one.
    """

    status: str = "NOT_RUN"        # PASS | FAIL | NO_ARTIFACTS | SKIPPED_NO_RUNTIME
    runtime_available: bool = False
    reference_passed: bool = False
    starter_failed: bool = False
    discriminating: bool = False   # reference_passed AND starter_failed
    detail: str = ""


# ---------------------------------------------------------------------------
# The Question
# ---------------------------------------------------------------------------
class Question(BaseModel):
    question_id: str
    title: str
    difficulty: Difficulty
    bloom_level: BloomLevel
    scenario: str
    tested_skills: list[str]
    objective: str
    constraints: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    industry_domain: str = "warehouse robot"

    # New-style fields (populated by rewritten generator)
    robot: str = ""
    file_to_edit: str = ""                                          # single file path
    boilerplate_code: str = ""                                      # content of boilerplate file
    estimated_solve_minutes: int = 30

    # Detailed format fields (from evaluations/question.json)
    metadata: Optional[QuestionMetadata] = None
    context: str = ""                                               # detailed scenario
    prerequisites: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    parts: list[Part] = Field(default_factory=list)                 # for multi-part questions
    tasks: list[str] = Field(default_factory=list)                  # flat task list
    file_structure: Optional[FileStructure] = None
    starter_code_list: list[StarterCodeBlock] = Field(default_factory=list)
    expected_output: list[ExpectedOutput] = Field(default_factory=list)
    run_commands: list[str] = Field(default_factory=list)
    detailed_evaluation_criteria: Optional[EvaluationCriteria] = None

    # Legacy fields kept for pipeline compatibility
    evaluation_criteria: list[EvaluationCriterion] = Field(default_factory=list)
    files_to_edit: list[EditableFile] = Field(default_factory=list)
    package: PackageStructure = Field(default_factory=lambda: PackageStructure(name="ros2_pkg"))
    expected_behaviour: str = ""
    hidden_checks: list[GradingCheck] = Field(default_factory=list)
    hidden_tests: list[HiddenTest] = Field(default_factory=list)

    # Filled by downstream agents -----------------------------------------
    similarity_score: float = 0.0
    calibrated_difficulty: Optional[Difficulty] = None
    scope_violations: list[str] = Field(default_factory=list)
    realism_score: int = 0
    auto_gradable: bool = True
    role_alignment: Optional[RoleAlignment] = None
    hiring_signal: Optional[HiringSignal] = None
    market_readiness: Optional[MarketReadiness] = None
    confidence: Optional[ConfidenceBreakdown] = None
    grading_execution: Optional[GradingExecution] = None

    # NEW: Eval comparator & LLM critic
    eval_comparison: Optional[EvalComparison] = None
    critic_feedback_history: list[CriticFeedback] = Field(default_factory=list)
    generation_skill: str = ""  # which skill from skills.yaml was used to generate this

    # Cost accounting
    tokens_used: int = 0
    generation_cost_usd: float = 0.0
    generation_attempts: int = 1

    @property
    def approved(self) -> bool:
        return bool(self.confidence and self.confidence.status == "APPROVED")


# ---------------------------------------------------------------------------
# Agent result envelope (used by every agent)
# ---------------------------------------------------------------------------
class AgentResult(BaseModel):
    agent: str
    status: str = "ok"  # ok | warn | fail
    messages: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None

    def finish(self, status: str = "ok") -> "AgentResult":
        self.status = status
        self.finished_at = datetime.now(timezone.utc)
        return self


# ---------------------------------------------------------------------------
# Supervisor / orchestrator
# ---------------------------------------------------------------------------
class SupervisorVerdict(BaseModel):
    supervisor_status: str = "PENDING"  # APPROVED | REJECTED
    validation_score: int = 0
    issues: list[str] = Field(default_factory=list)
    # Per-question rejection routing — drives the closed regeneration loop.
    failing_question_ids: list[str] = Field(default_factory=list)
    question_feedback: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Planner / autonomy
# ---------------------------------------------------------------------------
class PlanAction(str, Enum):
    """The action a PlannerAgent can choose on each control-loop tick."""

    # Parser loop actions
    SUMMARISE = "summarise"       # LLM summarise an .md section
    EXTRACT = "extract"           # LLM extract skills from summary
    VALIDATE_COVERAGE = "validate_coverage"  # check if all sections have skills

    # Generation loop actions
    GENERATE = "generate"         # produce questions from skills
    COMPARE = "compare"           # compare generated question vs eval set
    VALIDATE = "validate"         # run validation chain (originality, scope, etc)
    CHECK_CONFIDENCE = "check_confidence"  # score confidence

    # Feedback loop actions
    CRITIQUE = "critique"         # LLM Critic provides feedback
    REGENERATE = "regenerate"     # replace failing questions w/ feedback

    # Terminal actions
    FINALIZE = "finalize"         # quality bar met (or budget spent) → ship
    ABORT = "abort"               # unrecoverable — stop without a package


class QuestionQuality(BaseModel):
    """Per-question verdict against the quality bar — the gate the planner reads
    to decide whether a question may ship or must be regenerated."""

    question_id: str
    passed: bool = False
    confidence: float = 0.0
    discriminating: bool = False        # executable grading proved the tests work
    judge_approved: bool = True         # independent LLM judge verdict (True if not run)
    failed_checks: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    """One decision the planner made, recorded for the audit trail. This is the
    visible evidence the system is genuinely deciding, not running a fixed DAG."""

    step: int
    action: PlanAction
    reason: str = ""
    targets: list[str] = Field(default_factory=list)   # question_ids acted on
    source: str = "policy"                              # "llm" | "policy"
    bar_passed: int = 0
    bar_total: int = 0


class AssessmentPackage(BaseModel):
    """The full deliverable produced for one AssessmentRequest."""

    run_id: str
    topic: str
    syllabus: list[str]
    syllabus_analysis: SyllabusAnalysis
    source_research: SourceResearch
    coverage_matrix: CoverageMatrix
    questions: list[Question] = Field(default_factory=list)
    portfolio_coverage_score: int = 0
    portfolio_missing_areas: list[str] = Field(default_factory=list)
    supervisor: SupervisorVerdict = Field(default_factory=SupervisorVerdict)
    plan_trace: list[PlanStep] = Field(default_factory=list)
    quality: list[QuestionQuality] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def approved_questions(self) -> list[Question]:
        return [q for q in self.questions if q.approved]
