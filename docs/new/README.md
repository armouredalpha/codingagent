# robo_assess — Robotics & AI Assessment Generation System

A production-grade, multi-agent pipeline that **generates, validates, scores and
approves ROS2 (Humble) coding assessments**. Every question is a realistic
engineering ticket with starter scaffolding, a hidden reference solution,
automatable grading checks and hidden tests — never multiple-choice or theory.

The system is an **LLM agent**: every question is generated via OpenRouter or
Anthropic. A provider and API key are **required** — there is no offline/template mode.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Key Features](#2-key-features)
3. [Architecture](#3-architecture)
4. [The Agents](#4-the-agents)
5. [Prerequisites](#5-prerequisites)
6. [Installation](#6-installation)
7. [Quick Start](#7-quick-start)
8. [Configuration](#8-configuration)
9. [Usage (CLI)](#9-usage-cli)
10. [Request Format](#10-request-format)
11. [Output Structure](#11-output-structure)
12. [Confidence Scoring](#12-confidence-scoring)
13. [Quality Gates & Validation](#13-quality-gates--validation)
14. [Datasets](#14-datasets)
15. [Example Assessment Packages](#15-example-assessment-packages)
16. [Testing](#16-testing)
17. [Docker Deployment](#17-docker-deployment)
18. [Project Structure](#18-project-structure)

---

## 1. Overview

`robo_assess` turns an instructor's syllabus into a complete, gradeable ROS2
coding assessment. A team of specialised agents — coordinated by an Orchestrator
and audited by a Supervisor — parses the syllabus, generates engineering-ticket
questions, calibrates their difficulty, checks originality and scope, scores
industry realism, verifies that every question is machine-gradable, and assigns
a confidence score. Only questions that clear an 85/100 confidence bar are
approved; the Supervisor then validates the batch as a whole.

The design priority is **trustworthy, verified output**: every generated
question is run through static and *executable* grading (the reference solution
must pass the generated tests while the unsolved starter fails them) before it
can be approved.

## 2. Key Features

- **Engineering-ticket questions** — every task reads like a real ticket handed
  to a new hire (scenario, acceptance criteria, constraints), not a quiz.
- **TODO-bounded edits** — candidates edit only between `# TODO START` /
  `# TODO END` markers; the surrounding scaffold compiles as-is and is restored
  at grading time to prevent tampering.
- **LLM-generated, then verified** — questions come from the model and must
  pass *executable* grading (AST-level checks that the reference really invokes
  the required rclpy APIs and references the declared interfaces) before approval.
- **Auto-gradable** — each question ships deterministic checks plus hidden tests.
- **Difficulty calibration** — targets a 30% easy / 50% medium / 20% hard mix.
- **Originality enforcement** — blended lexical similarity (token cosine +
  character-shingle Jaccard) ≥ 0.75 against prior questions and a persistent
  memory store triggers rejection.
- **Scope gating** — Nav2, SLAM, MoveIt, OpenCV and micro-ROS appear only when
  the syllabus explicitly includes them.
- **Confidence + hiring reports** — per-question confidence breakdown, role
  alignment, hiring-signal and portfolio-coverage analysis.
- **Auditable** — every run and stage is logged to SQLite.

## 3. Architecture

```
                         ┌──────────────────┐
        AssessmentRequest │   Orchestrator   │  (coordinates all agents)
        ─────────────────▶│                  │
                         └─────────┬────────┘
                                   │
   ┌───────────────────────────────┼───────────────────────────────┐
   ▼                               ▼                               ▼
Syllabus → Source → Coverage → Generation → [Boilerplate, Difficulty,
Parser    Research  Matrix      (LLM, 3-block  Originality, Scope, Realism,
                                JSON+starter+  Auto-Grading + Executable
                                reference)     Grading] → Confidence
                                                                   │
                              Hiring/Role/Market/Portfolio ◀───────┤
                                                                   ▼
                                          Evaluation → AssessmentPackage
                                                                   │
                                                                   ▼
                                                         ┌──────────────────┐
                                                         │    Supervisor    │
                                                         │ (final validation)│
                                                         └──────────────────┘
```

A regeneration loop re-runs generation/validation (up to
`max_regeneration_attempts`) until coverage is complete and enough questions are
approved.

## 4. The Agents

| # | Agent | Responsibility |
|---|---|---|
| — | **Orchestrator** | Wires and sequences all agents; runs the regeneration loop; assembles the package. |
| 1 | Syllabus Parser | Extracts testable skills, concepts, APIs, config elements, ROS components. |
| 2 | Source Research | Gathers reference material (curated offline; optional scraping). |
| 3 | Coverage Matrix | Tracks which syllabus skills are covered by generated questions. |
| 4 | Question Generator | Produces engineering-ticket questions via the LLM (JSON + starter + reference solution). |
| 5 | Boilerplate Generator | Verifies TODO markers are balanced and reference ≠ starter. |
| 6 | Difficulty Calibration | Estimates true difficulty from skills, LOC, files, Bloom. |
| 7 | Originality | Cosine-similarity duplicate detection vs history + memory. |
| 8 | Scope Compliance | Flags gated tech used outside the approved syllabus. |
| 9 | Industry Realism | Scores 0–100 industrial realism of each scenario. |
| 10 | Auto-Grading | Confirms each question is deterministically machine-gradable. |
| 11 | Confidence Scoring | Weighted confidence; approves at ≥ 85. |
| 12 | Role Readiness | Maps each question to role level / interview round. |
| 13 | Hiring Signal | Scores how strong a hiring signal the question provides. |
| 14 | Market Readiness | Rates alignment with current market expectations. |
| 15 | Portfolio Coverage | Measures coverage across portfolio skill areas. |
| 16 | Educational Framework | Batch evaluation across nine quality criteria. |
| — | **Supervisor** | Independent final validation of the whole batch. |

## 5. Prerequisites

- **Python 3.10+**
- Runtime dependencies: `pydantic>=2.5`, `PyYAML>=6.0`, `openai` (OpenRouter),
  `anthropic`, `structlog`.
- A ROS2 Humble environment is **not** required to *generate* assessments. It is
  only needed to *run* the produced ROS2 packages during live grading.

## 6. Installation

```bash
# from the project root
python -m pip install --break-system-packages -r requirements.txt

# (optional) install as a package, exposing the `robo-assess` command
python -m pip install --break-system-packages .

# (optional) dev extras for the test-suite
python -m pip install --break-system-packages -r requirements-dev.txt
```

## 7. Quick Start

```bash
# 1. Generate the evaluation datasets (ships 12 datasets, 320 rows each)
python tools/generate_datasets.py

# 2. Generate an assessment from a sample request (set a provider key first)
python -m robo_assess.cli generate --request configs/ros2_fundamentals.yaml

# 3. Inspect the output
ls outputs/<run_id>/

# 4. (optional) build the three example packages
PYTHONPATH=. python tools/build_examples.py

# 5. (optional) run the test-suite
PYTHONPATH=. python -m pytest
```

A successful run prints a per-question confidence table and a Supervisor verdict,
and writes a full package under `outputs/<run_id>/`.

## 8. Configuration

Settings load in priority order: **environment variables (`ROBO_*`) → `config.yaml`
→ built-in defaults**. Key fields in `config.yaml`:

| Field | Default | Meaning |
|---|---|---|
| `provider` | `openrouter` | `openrouter` \| `anthropic` |
| `model` | provider-specific | model id |
| `num_questions` | `6` | target number of questions |
| `difficulty_distribution` | `0.30 / 0.50 / 0.20` | easy / medium / hard mix |
| `over_generation_factor` | `1.5` | extra candidates generated, best kept |
| `max_regeneration_attempts` | `2` | regeneration loop budget |
| `similarity_reject_threshold` | `0.75` | cosine ≥ this → reject as duplicate |
| `min_confidence` | `85.0` | confidence ≥ this → APPROVED |
| `min_realism_score` | `60` | industry-realism floor |

**Credentials are required** — if the chosen provider needs a key and none is
found, `Settings.load()` raises a clear `RuntimeError` at startup rather than
degrading silently. See `.env.example` for the supported keys.

## 9. Usage (CLI)

```bash
# From a request file
python -m robo_assess.cli generate --request configs/ros2_fundamentals.yaml

# Inline topic + skills
python -m robo_assess.cli generate \
    --topic "ROS2 Core Skills" \
    --skill "ROS2 publisher node" \
    --skill "ROS2 services" \
    --num 4

# Machine-readable summary
python -m robo_assess.cli generate --request configs/ros2_core_skills.yaml --json

# List recent runs (from the SQLite run-log)
python -m robo_assess.cli runs
```

The `generate` command exits `0` when the Supervisor approves the batch and `2`
otherwise — convenient for CI gating.

## 10. Request Format

A request is a small YAML file (see `configs/`):

```yaml
topic: ROS2 Fundamentals
num_questions: 6
syllabus:
  - ROS2 publisher node
  - ROS2 subscriber node
  - ROS2 services
  - TF2 transforms
  - ROS2 parameters
  - ROS2 launch files
sources: []              # optional reference URLs/notes
existing_questions: []   # optional prior stems, for originality
```

`skills` and `topics` are accepted as aliases for `syllabus`.

## 11. Output Structure

Each run writes `outputs/<run_id>/`:

```
outputs/<run_id>/
├── package.json                  # full structured AssessmentPackage
├── coverage_matrix.json          # skill coverage
├── confidence_report.json        # per-question confidence breakdown
├── hiring_readiness_report.json  # role / hiring-signal / portfolio analysis
├── evaluation_report.json        # 9-criteria evaluation + supervisor verdict
└── questions/
    └── <question_id>/
        ├── README.md             # candidate brief
        ├── question.json         # structured record
        ├── grading.json          # checks + weights
        ├── starter/              # candidate-facing code (TODO blocks)
        ├── solution/             # reference solution
        └── test_<id>.py          # hidden tests
```

## 12. Confidence Scoring

Each question's confidence (0–100) is a weighted blend:

| Component | Weight |
|---|---|
| Coverage contribution | 20% |
| Difficulty correctness | 20% |
| Originality | 15% |
| Scope compliance | 15% |
| Auto-grading readiness | 15% |
| Format compliance | 15% |

A question is **APPROVED** when its confidence is **≥ 85** and it has no blocking
issues (scope violation, not auto-gradable, unbalanced boilerplate).

## 13. Quality Gates & Validation

- **Originality gate** — cosine similarity ≥ `0.75` against prior questions and
  the persistent memory store rejects a candidate as a duplicate.
- **Scope gate** — gated technologies (Nav2, SLAM, MoveIt, OpenCV/cv_bridge,
  micro-ROS, ros2_control, Gazebo plugins) are only permitted when named in the
  syllabus; otherwise they are flagged as violations.
- **Auto-grading gate** — a question must carry ≥ 1 deterministic check to pass.
- **Boilerplate gate** — TODO markers must be balanced and the reference solution
  must differ from the starter.
- **Supervisor** — independently validates the batch: 100% syllabus coverage, at
  least one approved question, no scope/grading violations among approved
  questions, and intact TODO markers. It emits an APPROVED/REJECTED verdict with
  a validation score.

## 14. Datasets

`tools/generate_datasets.py` produces **12 evaluation/calibration datasets**,
**320 rows each (3,840 total)**, as JSON-Lines under `datasets/`. Every record is
synthesised from real ROS2 building blocks (genuine topics, message types, QoS
profiles, parameters, failure modes) — no placeholders.

| Dataset | Purpose |
|---|---|
| `difficulty_calibration` | label easy/medium/hard from skills, LOC, files, Bloom |
| `scope_compliance` | detect gated tech outside approved scope |
| `originality` | similarity-based duplicate detection |
| `industry_realism` | 0–100 realism scoring |
| `auto_grading` | deterministic, machine-gradable checks |
| `learning_outcome` | skill → measurable Bloom outcome |
| `hidden_test_coverage` | edge cases hidden tests must exercise |
| `boilerplate_quality` | TODO-marker balance / scaffold validity |
| `format_compliance` | presence of all required question fields |
| `engineering_ticket` | ticket-style vs forbidden MCQ/theory |
| `ros2_best_practices` | QoS/params/logging/lifecycle scoring |
| `solution_complexity` | cyclomatic/LOC complexity tiering |

Run `python tools/generate_datasets.py --rows 500` for larger sets. See
`datasets/README.md` and `datasets/manifest.json`.

## 15. Example Assessment Packages

`tools/build_examples.py` writes three complete, ready-to-ship ROS2 packages
under `examples/` — one per difficulty tier — each a real `ament_python` package
with `package.xml`, `setup.py`, candidate `starter/`, instructor `solution/`,
hidden `test/`, `grading.json` and a `README.md`:

- `examples/easy_publisher_cmd_vel/` — publish `Twist` on `/cmd_vel`.
- `examples/medium_subscriber_estop/` — proximity-triggered e-stop subscriber.
- `examples/hard_reactive_nav/` — reactive LaserScan obstacle avoidance.

See `examples/instructor_guide.md` and `examples/student_guide.md`.

## 16. Testing

```bash
PYTHONPATH=. python -m pytest
```

The suite (90+ tests) drives the end-to-end pipeline with a deterministic
`FakeLLM` double (see `tests/conftest.py`) — no network or API key required to
run the tests — asserting an APPROVED package with 100% coverage, executable
grading invariants (TODO balance, reference ≠ starter, reference passes / starter
fails), dataset integrity, and individual agents/evaluators.

## 17. Docker Deployment

```bash
# Build (datasets are generated at build time so the image ships populated)
docker build -t robo-assess:latest .

# Generate an assessment; outputs are written to ./outputs on the host
docker run --rm -v "$(pwd)/outputs:/app/outputs" robo-assess:latest \
    generate --request configs/ros2_fundamentals.yaml

# Or via compose
docker compose up --build
```

The container needs a provider key, e.g.
`-e ROBO_PROVIDER=openrouter -e OPENROUTER_API_KEY=...` or
`-e ROBO_PROVIDER=anthropic -e ANTHROPIC_API_KEY=...`.

## 18. Project Structure

```
robotics-assessment-system/
├── robo_assess/              # the package
│   ├── agents/               # 16 agents + orchestrator + supervisor
│   ├── evaluators/           # 9-criteria batch evaluator
│   ├── workflows/            # package export
│   ├── templates.py          # DOMAINS list (legacy template bank now unused)
│   ├── schemas.py            # Pydantic models
│   ├── config.py             # settings loader
│   ├── llm_client.py         # provider-agnostic LLM client
│   ├── memory.py             # SQLite question/analysis memory
│   ├── vectorstore.py        # cosine similarity store
│   ├── logging_utils.py      # structlog + SQLite run-log
│   └── cli.py                # command-line entry point
├── tools/
│   ├── generate_datasets.py  # builds the 12 datasets
│   └── build_examples.py     # builds the 3 example packages
├── prompts/                  # LLM-mode prompt templates
├── configs/                  # sample request files
├── datasets/                 # generated evaluation datasets
├── examples/                 # 3 example packages + guides
├── tests/                    # pytest suite
├── docs/                     # additional documentation
├── config.yaml               # system configuration
├── requirements.txt
├── pyproject.toml
├── Dockerfile / docker-compose.yml
├── Makefile
└── README.md
```

---

### License

Released under the Apache-2.0 License. See `LICENSE`.

### A note on verification

The model proposes; the gates dispose. Every question the LLM generates is held
to the same schemas and quality gates, and — crucially — to *executable* grading:
the reference solution must pass the auto-generated tests while the unsolved
starter fails them, or the question is routed back for targeted regeneration.
Tests run against a deterministic `FakeLLM`, so the suite is reproducible without
network access or credentials.
