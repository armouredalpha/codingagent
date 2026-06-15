# Robotics Assessment System — Complete System Guide

## 1. Commands to Run the System

```bash
cd /home/niat/claude_Ws/robotics-assessment-system

# Run from a config file (recommended)
python3 -m robo_assess.cli generate --request configs/ros2_fundamentals.yaml

# Run with inline skills (no config file needed)
python3 -m robo_assess.cli generate \
  --topic "ROS2 SLAM" \
  --skill "slam_toolbox mapping" \
  --skill "map saving" \
  --num 6

# Specify number of questions explicitly
python3 -m robo_assess.cli generate --request configs/ros2_fundamentals.yaml --num 10

# Also print a compact JSON summary to terminal
python3 -m robo_assess.cli generate --request configs/ros2_fundamentals.yaml --json

# List all previous runs
python3 -m robo_assess.cli runs

# Run all three existing topic configs back-to-back
python3 -m robo_assess.cli generate --request configs/ros2_fundamentals.yaml
python3 -m robo_assess.cli generate --request configs/ros2_core_skills.yaml
python3 -m robo_assess.cli generate --request configs/ros2_perception_intro.yaml
```

---

## 2. Where to Define the Syllabus / Scope

Create config files in `configs/` — one per topic:

```
configs/
  ros2_fundamentals.yaml        ← publisher, subscriber, services, TF2, params, launch
  ros2_core_skills.yaml         ← publisher, subscriber, services, parameters
  ros2_perception_intro.yaml    ← publisher, subscriber, LaserScan, obstacle avoidance, launch
```

Config file structure:
```yaml
topic: ROS2 SLAM
num_questions: 10
syllabus:
  - slam_toolbox mapping
  - map saving and loading
  - localization with AMCL
  - occupancy grid maps
  - laser scan processing
sources: []
existing_questions: []
```

The `syllabus:` list IS the scope. The `ScopeComplianceAgent` blocks any question
referencing tech not in this list (Nav2, MoveIt, OpenCV, etc. are gated by default).

---

## 4. Vectorstore — Originality Tracking

The vectorstore at `vectorstore/index.json` remembers every generated question across
all runs. The originality agent uses it to reject duplicates (cosine similarity > 0.75).

### Reset the vectorstore (clear duplicate history)
```bash
echo '[]' > vectorstore/index.json
```

### Reset the question memory DB
```bash
python3 -c "
import sqlite3
con = sqlite3.connect('memory/memory.db')
con.execute('DELETE FROM questions')
con.commit(); con.close()
print('done')
"
```

**When to reset:** Only reset before a completely new assessment generation session.
Do NOT reset mid-session — the vectorstore is what prevents duplicate questions across batches.

---

## 5. How to Tighten Guardrails

### Quick thresholds — edit `config.yaml`
```yaml
min_confidence: 90                  # default 85 — raise to require higher quality
min_realism_score: 75               # default 60 — raise to require more realistic scenarios
similarity_reject_threshold: 0.60   # default 0.75 — lower to reject more near-duplicates
max_regeneration_attempts: 3        # default 2 — more retries before giving up
```

### Per-rule file locations
| What to change | File |
|---|---|
| Block out-of-scope tech | `robo_assess/agents/scope_agent.py` → `_GATED` dict |
| Boilerplate TODO validation | `robo_assess/agents/boilerplate_generator.py` |
| Difficulty calibration logic | `robo_assess/agents/difficulty_agent.py` |
| Realism scoring keywords | `robo_assess/agents/realism_agent.py` |
| Confidence scoring weights | `robo_assess/agents/confidence_agent.py` |
| Supervisor pass score | `robo_assess/agents/supervisor.py` → `score >= 85` |
| Prompt rules & JSON schema | `prompts/question_generator.txt` |

### Guardrail definitions (human-readable specs)
```
guardrails/
  guardrail_rules.yaml              ← all thresholds and rules per agent
  quality_guardrails.yaml           ← craftsmanship: solvability, scaffolding, grading fairness
  pedagogical_guardrails.yaml       ← Bloom alignment, cognitive load, misconception targeting
  ros2_correctness_guardrails.yaml  ← message fields, rclpy idioms, QoS, TF2 conventions
  batch_diversity_guardrails.yaml   ← skill spread, difficulty balance, domain variety
  rejection_patterns.yaml           ← string patterns that auto-reject
  construct_benchmark.jsonl         ← Construct reference questions for benchmarking
```

---

## 6. Eval Sets — Adding Construct Benchmark Data

All eval sets live in `datasets/`. Each is a `.jsonl` file (one JSON object per line).

| File | What it tests | What to add |
|---|---|---|
| `boilerplate_quality.jsonl` | TODO markers present/balanced | Real Construct questions |
| `scope_compliance.jsonl` | In-scope vs out-of-scope tech | Known good/bad question pairs |
| `difficulty_calibration.jsonl` | Easy/medium/hard labelling | Manually labelled questions |
| `industry_realism.jsonl` | Real vs toy phrasing | Good Construct questions as positives |
| `auto_grading.jsonl` | Checks are automatable | Questions with proven grading scripts |
| `engineering_ticket.jsonl` | Reads like a real ticket | Sample `.md` assessment questions |

Add a Construct benchmark row to `engineering_ticket.jsonl`:
```jsonl
{"id": "construct_001", "title": "Publish /cmd_vel at 10Hz", "scenario": "...", "is_engineering_ticket": true, "has_scenario": true, "has_objective": true, "has_constraints": true, "todo_blocks": true, "reference_solution_present": true}
```
Then increment `rows` in `datasets/manifest.json`.

---

## 7. Output Structure

Every run saves to `outputs/<run_id>/`:

```
outputs/<run_id>/
  summary.json                  ← compact: question + boilerplate + difficulty + confidence
  package.json                  ← full machine-readable package
  coverage_matrix.json          ← which syllabus skills were covered
  confidence_report.json        ← per-question confidence breakdown
  hiring_readiness_report.json  ← role alignment and market readiness
  evaluation_report.json        ← benchmark scores against datasets
  questions/
    <qid>/
      question.json             ← full question data
      README.md                 ← student-facing brief
      starter/<file>            ← editable file with # TODO START / # TODO END
      solution/<file>           ← reference solution (instructor only)
      test_<qid>.py             ← hidden auto-grading test stub
      grading.json              ← grading check metadata
```

The `summary.json` is the most useful single file — it contains all questions with
boilerplate starters, difficulty, confidence score, and approval status.

---

## 8. Verified Working Runs

| Run ID | Topic | Questions | Approved | Supervisor | Score |
|---|---|---|---|---|---|
| `3ff5c35b1bcd` | ROS2 Fundamentals | 3 | 2 | APPROVED | 81 |
| `1a8637739959` | ROS2 Fundamentals | 6 | 6 | APPROVED | 96 |

Run `python3 -m robo_assess.cli runs` to see the full history.

---

## 9. Quick Reference — All Key Files

```
configs/                              ← DEFINE SYLLABUS HERE (one .yaml per topic)
prompts/question_generator.txt        ← LLM prompt rules and JSON schema
config.yaml                           ← thresholds: min_confidence, max_tokens, etc.
.env                                  ← OPENROUTER_API_KEY or ANTHROPIC_API_KEY, ROBO_PROVIDER, ROBO_MODEL

robo_assess/agents/
  question_generator.py               ← LLM generation + template fallback logic
  scope_agent.py                      ← gated tech list
  boilerplate_generator.py            ← TODO marker validation
  confidence_agent.py                 ← 0-100 confidence scoring
  supervisor.py                       ← final approval authority

guardrails/                           ← declarative guardrail specs (config only)
datasets/                             ← eval benchmark data (.jsonl files)
vectorstore/index.json                ← originality tracking across all runs
memory/memory.db                      ← question stem cache + syllabus cache
outputs/                              ← all generated assessment packages
```
