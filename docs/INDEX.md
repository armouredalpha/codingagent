# Documentation Index

Complete documentation for the Robotics Assessment System.

## Getting Started

- **[QUICKSTART.md](QUICKSTART.md)** — 5-minute setup and first run
- **[README.md](README.md)** — Overview and key concepts

## Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design, agent contracts, data flow
- **[SYSTEM_GUIDE.md](new/SYSTEM_GUIDE.md)** — Detailed system overview (in `new/`)

## Reports & Analysis

- **[CONFIDENCE_SCORE_REPORT.md](CONFIDENCE_SCORE_REPORT.md)** — Confidence calibration analysis and multipliers
- **[INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)** — Integration milestones and status

## Advanced Topics

- **[API.md](API.md)** — Python API reference (agents, schemas, client)
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Deployment to production, scaling, monitoring
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — Common issues and solutions

## Implementation Details (in `new/`)

- **[IMPLEMENTATION_PROGRESS.md](new/IMPLEMENTATION_PROGRESS.md)** — Current state and blockers
- **[IMPLEMENTATION_STRATEGY.md](new/IMPLEMENTATION_STRATEGY.md)** — Technical approach and tradeoffs
- **[THREE_MODES.md](new/THREE_MODES.md)** — Offline/template/online execution modes
- **[QUICK_REFERENCE.md](new/QUICK_REFERENCE.md)** — Quick lookup for common tasks

## For Developers

See parent directories:
- **`../config/README.md`** — Configuration files and options
- **`../tools/README.md`** — Analysis and utility scripts
- **`../robo_assess/`** — Source code with docstrings

## Testing

See **`../tests/`**:
- `conftest.py` — Pytest fixtures and FakeLLM implementation
- `test_pipeline.py` — End-to-end pipeline tests
- `test_agents.py` — Individual agent tests
- `test_*.py` — Specialized tests (confidence, infrastructure, planner)

## Folder Structure

```
docs/
├── INDEX.md                              ← You are here
├── README.md                             ← Deprecated, see QUICKSTART
├── ARCHITECTURE.md                       ← Core design
├── QUICKSTART.md                         ← Getting started
├── API.md                                ← Python API
├── DEPLOYMENT.md                         ← Production setup
├── TROUBLESHOOTING.md                    ← Common issues
├── CONFIDENCE_SCORE_REPORT.md            ← Calibration analysis
├── INTEGRATION_SUMMARY.md                ← Status report
└── new/                                  ← Newer documentation
    ├── ARCHITECTURE.md
    ├── SYSTEM_GUIDE.md
    ├── IMPLEMENTATION_PROGRESS.md
    ├── IMPLEMENTATION_STRATEGY.md
    ├── THREE_MODES.md
    ├── QUICK_REFERENCE.md
    ├── README.md
    ├── NEXT_STEPS.md
    └── SESSION_SUMMARY.md
```

## Quick Links

| Topic | File | Status |
|-------|------|--------|
| How do I... generate questions? | QUICKSTART.md | ✓ Current |
| How does... the system work? | ARCHITECTURE.md | ✓ Current |
| Where do I... configure the system? | ../config/README.md | ✓ Current |
| How do I... run tests? | ../tests/conftest.py | ✓ Current |
| What are... the evaluation metrics? | CONFIDENCE_SCORE_REPORT.md | ✓ Current |
| How do I... deploy to production? | DEPLOYMENT.md | ⚠ Partial |
| What are... the API endpoints? | API.md | ⚠ Partial |
| How do I... troubleshoot issues? | TROUBLESHOOTING.md | ⚠ Partial |

## Last Updated

- **docs/INDEX.md**: 2026-06-13
- **docs/ARCHITECTURE.md**: 2026-06-12
- **docs/CONFIDENCE_SCORE_REPORT.md**: 2026-06-13
- See individual files for detailed version history
