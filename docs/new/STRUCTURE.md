# Project Structure

This document describes the organized directory structure of the Robotics Assessment System.

## Directory Tree

```
robotics-assessment-system/
├── config/                          ← Configuration files
│   ├── config.yaml                  (Main configuration)
│   └── README.md                    (Configuration guide)
│
├── robo_assess/                     ← Main Python package (source code)
│   ├── __init__.py
│   ├── agents/                      (22 agent implementations)
│   │   ├── orchestrator.py          (Main orchestration)
│   │   ├── planner.py               (Planner/decision logic)
│   │   ├── question_generator.py    (Question generation)
│   │   ├── supervisor.py            (Final validation)
│   │   └── ... (19 more agents)
│   ├── workflows/                   (Workflow definitions)
│   ├── schemas.py                   (Pydantic models)
│   ├── config.py                    (Settings loader)
│   ├── llm_client.py                (LLM provider integration)
│   ├── token_counter.py             (Cost/token tracking)
│   ├── state_manager.py             (State persistence)
│   ├── learned_confidence.py        (Confidence scoring)
│   ├── skill_taxonomy.py            (Skill DAG)
│   ├── batch_processor.py           (LLM batching)
│   ├── vectorstore.py               (Similarity search)
│   ├── memory.py                    (Question caching)
│   ├── logging_utils.py             (Structured logging)
│   ├── guardrails.py                (Safety checks)
│   └── cli.py                       (Command-line interface)
│
├── tests/                           ← Test suite
│   ├── conftest.py                  (Fixtures, FakeLLM)
│   ├── test_pipeline.py             (End-to-end tests)
│   ├── test_agents.py               (Agent tests)
│   ├── test_improved_confidence.py  (Confidence validation)
│   ├── test_infrastructure.py       (State/persistence)
│   ├── test_multi_loop_planner.py   (Planner tests)
│   └── test_orchestrator_*.py       (Orchestrator tests)
│
├── docs/                            ← Documentation
│   ├── INDEX.md                     ← Start here
│   ├── ARCHITECTURE.md              (System design)
│   ├── QUICKSTART.md                (Getting started)
│   ├── API.md                       (API reference)
│   ├── DEPLOYMENT.md                (Production setup)
│   ├── TROUBLESHOOTING.md           (Common issues)
│   ├── CONFIDENCE_SCORE_REPORT.md   (Calibration analysis)
│   ├── INTEGRATION_SUMMARY.md       (Status report)
│   └── new/                         (Additional docs)
│       ├── ARCHITECTURE.md
│       ├── SYSTEM_GUIDE.md
│       ├── IMPLEMENTATION_*.md
│       └── ...
│
├── tools/                           ← Utility scripts
│   ├── analyze_confidence.py        (Confidence analysis)
│   └── README.md                    (Tools guide)
│
├── prompts/                         ← LLM prompts
│   ├── question_generator.txt
│   ├── syllabus_parser.txt
│   └── ... (other prompts)
│
├── skills/                          ← Skill definitions
│   └── skills.yaml                  (Extracted skills)
│
├── configs/                         ← Syllabus/assessment configs
│   └── Robotics & AI Coding...md    (Example configs)
│
├── evaluations/                     ← Reference question data
│   └── question.json                (Ground truth for calibration)
│
├── guardrails/                      ← Guardrail rules
│   ├── __init__.py
│   └── README.md
│
├── logs/                            ← Runtime logs (git-ignored)
│   ├── runs.db                      (Run audit trail)
│   ├── state.db                     (Execution state)
│   ├── .gitkeep                     (Keep directory)
│   └── *.log                        (Log files)
│
├── memory/                          ← Cached data (git-ignored)
│   ├── memory.db                    (Question cache)
│   ├── .gitkeep
│   └── *.log
│
├── vectorstore/                     ← Similarity index (git-ignored)
│   ├── index.json                   (Vector embeddings)
│   ├── .gitkeep
│   └── *.log
│
├── outputs/                         ← Generated questions (git-ignored)
│   ├── questions/                   (Question packages)
│   ├── .gitkeep
│   └── agent*/                      (Run outputs)
│
├── reports/                         ← Analysis reports (git-ignored)
│   ├── .gitkeep
│   └── *.json/
│
├── eval/                            ← Evaluation sets (git-ignored)
│   ├── .gitkeep
│   └── *.json
│
├── Build & Config Files (root)
│   ├── setup.py                     (Package setup)
│   ├── pyproject.toml               (Project metadata)
│   ├── Makefile                     (Build commands)
│   ├── requirements.txt             (Dependencies)
│   ├── requirements-dev.txt         (Dev dependencies)
│   ├── .env.example                 (Environment template)
│   ├── .env                         (Actual env, git-ignored)
│   ├── .gitignore                   (Git ignore rules)
│   ├── Dockerfile                   (Container image)
│   ├── docker-compose.yml           (Container orchestration)
│   ├── .dockerignore                (Docker ignore)
│   ├── LICENSE                      (License file)
│   └── STRUCTURE.md                 ← This file
```

## Directory Purposes

### Core Directories

| Directory | Purpose | Git-Tracked? |
|-----------|---------|--------------|
| `robo_assess/` | Python package source code | ✓ Yes |
| `tests/` | Test suite (pytest) | ✓ Yes |
| `docs/` | Documentation (markdown) | ✓ Yes |
| `config/` | Configuration templates | ✓ Yes |
| `tools/` | Utility scripts | ✓ Yes |
| `prompts/` | LLM prompt templates | ✓ Yes |

### Runtime Directories

| Directory | Purpose | Contents | Git-Tracked? |
|-----------|---------|----------|--------------|
| `logs/` | Execution logs | SQLite DBs, log files | ✗ No |
| `memory/` | Question cache | SQLite DB | ✗ No |
| `vectorstore/` | Similarity index | JSON vectors | ✗ No |
| `outputs/` | Generated questions | JSON packages | ✗ No |
| `reports/` | Analysis reports | JSON reports | ✗ No |
| `eval/` | Evaluation sets | Reference data | ✗ No |

### Data Directories

| Directory | Purpose | Contents | Git-Tracked? |
|-----------|---------|----------|--------------|
| `skills/` | Skill definitions | YAML files | ✓ Yes |
| `evaluations/` | Reference questions | JSON ground truth | ✓ Yes |
| `configs/` | Assessment configs | Markdown specs | ✓ Yes |
| `guardrails/` | Safety rules | Python modules | ✓ Yes |

## Important Files

### Configuration

- **`config/config.yaml`** — Main system configuration
- **`.env.example`** — Template for environment variables
- **`.env`** — Actual secrets (git-ignored, copy from example)

### Entry Points

- **`robo_assess/cli.py`** — Command-line interface
- **`robo_assess/agents/orchestrator.py`** — Main orchestration logic
- **`setup.py`** — Package installation
- **`Makefile`** — Common commands

### Documentation

- **`docs/INDEX.md`** — Documentation index (start here)
- **`docs/ARCHITECTURE.md`** — System design and architecture
- **`docs/QUICKSTART.md`** — Getting started guide
- **`STRUCTURE.md`** — This file

### Development

- **`tests/conftest.py`** — Pytest fixtures and FakeLLM
- **`requirements-dev.txt`** — Development dependencies
- **`Makefile`** — Testing and development commands

## File Organization Rules

### Git-Tracked (committed to repository)
- Source code: `robo_assess/`, `tests/`
- Documentation: `docs/`, `*.md` files
- Configuration templates: `config/`, `prompts/`, `skills/`
- Data definitions: `evaluations/`, `configs/`, `guardrails/`
- Build files: `setup.py`, `pyproject.toml`, `Makefile`
- Examples: `.env.example`, `docker-compose.yml`

### Git-Ignored (not committed)
- Runtime data: `logs/`, `memory/`, `vectorstore/`
- Generated output: `outputs/`, `reports/`, `eval/`
- Environment: `.env`, `.env.local`
- Caches: `.pytest_cache/`, `__pycache__/`, `.mypy_cache/`
- IDE: `.vscode/`, `.idea/`

## Commands

See **`Makefile`** for common tasks:

```bash
make test              # Run test suite
make test-verbose      # Run with verbose output
make coverage          # Generate coverage report
make lint              # Run linters
make format            # Format code
make docs              # Build documentation
make clean             # Clean build artifacts
make install           # Install in development mode
```

## Getting Started

1. **Read documentation**
   ```bash
   cat docs/INDEX.md          # Documentation index
   cat docs/QUICKSTART.md     # Quick start guide
   ```

2. **Configure system**
   ```bash
   cp .env.example .env
   vi config/config.yaml      # Edit configuration
   ```

3. **Install dependencies**
   ```bash
   make install
   ```

4. **Run tests**
   ```bash
   make test
   ```

5. **Generate questions**
   ```bash
   robo-assess generate --topic "ROS2 Basics" --num-questions 6
   ```

## Related Documentation

- **`config/README.md`** — Configuration guide
- **`tools/README.md`** — Tool usage guide
- **`docs/ARCHITECTURE.md`** — System architecture
- **`robo_assess/agents/`** — Agent documentation (in docstrings)

## Structure History

- **2026-06-13**: Reorganized root-level files to clean structure
  - Moved test files to `tests/`
  - Moved markdown docs to `docs/`
  - Moved analysis tools to `tools/`
  - Created `config/` directory
  - Added `.gitkeep` files for runtime directories

---

**Last updated:** 2026-06-13
