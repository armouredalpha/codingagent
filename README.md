# ROS2 - Coding Question Generator

A multi-agent AI system that reads your teaching material (a Markdown file) and
automatically generates ready-to-use ROS2 coding assessment questions — complete
with starter code, reference solutions, and automated graders.

---

## What does it actually do?

You hand it a lesson `.md` file. It reads it, figures out what skills are being
taught, and then:

1. Writes 3–14 original coding questions (easy / medium / hard)
2. Generates the starter code a student receives (with `# TODO` markers)
3. Generates the full reference solution
4. Creates hidden test cases that auto-grade student submissions
5. Runs its own internal quality checks and rejects low-quality questions
6. Keeps trying (up to 3 loops) until a Supervisor AI approves the batch

Output lands in `outputs/<date>_<topic>/` — one folder per question.

---

## Plain-English Glossary of Technical Terms

### Temperature (`temperature: 0.7`)
Think of this as the AI's "creativity dial".

- **0.0** = the AI always gives the same, most predictable answer. Like a robot
  repeating the textbook answer word for word.
- **1.0** = very creative and varied — sometimes surprisingly good, sometimes
  way off.
- **0.7** (our default) = balanced. Creative enough to write different questions
  each time, but focused enough to stay on-topic and technically correct.

You'd turn it *down* (e.g. 0.3) if you wanted very consistent, boring-but-safe
output. You'd turn it *up* (e.g. 0.9) if questions feel repetitive.

---

### Tokens / Max Tokens (`max_tokens: 4000`)
Tokens are the AI's "words" (roughly 1 token ≈ ¾ of an English word).

`max_tokens` is the maximum length the AI is allowed to write in a single
reply. 4000 tokens ≈ about 3,000 words — enough for a full question with
starter code + solution.

Running out of tokens mid-response gets truncated output. Raising this costs
more money per call.

---

### Model (`model: openai/gpt-4o`)
Which AI "brain" does the thinking. Different models have different strengths
and costs:

| Model | What it's good for | Cost |
|---|---|---|
| `openai/gpt-4o` | Best quality — used for writing questions and final verdict | $$$ |
| `openai/gpt-4o-mini` | Fast, cheap — used for critic checks | $ |
| `anthropic/claude-sonnet-4-6` | Alternative high-quality option | $$$ |

The system automatically uses `gpt-4o` for important creative tasks and
`gpt-4o-mini` for the quick checklist-style validators. You set the default
fallback in `config.yaml`.

---

### Provider (`provider: openrouter`)
The "store" you're buying AI from.

- **OpenRouter** — a marketplace that gives you access to GPT-4o, Claude,
  Llama, etc. through one API key. Use `OPENROUTER_API_KEY`.
- **Anthropic** — direct access to Claude models only. Use `ANTHROPIC_API_KEY`.

---

### Confidence Score (`min_confidence: 85.0`)
Each generated question gets scored 0–100. This is the system's own estimate
of "how good is this question?". It's calculated from:

- Does it actually test the right skill? (coverage)
- Is the difficulty level correct? (difficulty calibration)
- Is it original — not a copy of something already in the bank? (originality)
- Is it realistic — not a toy "hello world" example? (realism / scope)
- Can it be auto-graded? (gradability)
- Does the code format look right? (format quality)

A question scoring below 85 gets flagged for regeneration.

---

### Supervisor (the final gatekeeper)
After all questions are generated and validated, the Supervisor AI looks at the
whole batch and decides: **APPROVED** or **REJECTED**.

It checks:
- Is at least 85% of the syllabus covered?
- Did at least one question pass every check?
- Is the overall validation score ≥ 75/100?

If rejected, the CLI asks if you want to run another loop. Up to 3 loops by
default (`--max-loops 3`).

---

### Coverage Target (`coverage_target: 0.85`)
The syllabus has N skills listed. The system aims to cover at least 85% of
them across the generated questions. If your syllabus has 10 skills, at least
8–9 must be tested.

---

### Difficulty Distribution
```yaml
easy: 0.30   # 30% of questions are easy
medium: 0.50 # 50% are medium
hard: 0.20   # 20% are hard
```
Easy = fix one line / complete one missing value.
Medium = write 5–10 lines of logic.
Hard = write a whole ROS2 node from scratch.

---

### Vectorstore (originality memory)
A local file (`vectorstore/index.json`) that remembers every question ever
generated. Before publishing a new question, the system checks how similar it
is to everything in this file. If similarity > 0.75 (75%), the question is
rejected as too close to an existing one.

You can optionally use **Qdrant** (a cloud vector database) for semantic
(meaning-level) similarity instead of word-level matching — configured via
`QDRANT_URL` in `.env`.

---

### Docker / Grading Backend (`grading_backend: docker`)
The system can actually *run* generated code inside a safe, isolated ROS2
container (Docker) and check if it behaves correctly.

- **`docker` mode** — spins up a `ros:humble` container, runs the student's
  node, checks topics/services/TF. Best grading signal.
- **`ast` mode** — just reads the code statically (no Docker needed). Checks
  that the right ROS2 API calls are present.

If Docker isn't installed or the image isn't built, it automatically falls back
to `ast` mode — never crashes.

---

### Calibration / EMA
The confidence scorer learns over time. Every time an instructor manually
approves or rejects a question (`robo-assess review`), that feedback is saved
and the scorer recalibrates. "EMA" (Exponential Moving Average) just means
recent feedback matters more than old feedback.

---

## Setup

### 1. Install

```bash
cd coding_question_generator

# Install Python package + CLI
pip install -r requirements.txt
pip install --no-build-isolation -e .

# Verify install
robo-assess --help
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env — fill in your key:
```

```env
# Choose one provider:
ROBO_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...        # get from openrouter.ai

# OR for direct Anthropic:
# ROBO_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
```

### 3. (Optional) Build the Docker grader

Only needed if you want live ROS2 execution grading. Without this, the system
uses static code analysis instead.

```bash
make grader-build
# or manually:
docker build -f Dockerfile.grading -t robo-grader .
```

---

## Running

### Generate questions from a teaching material

```bash
robo-assess generate --md configs/Simulation_Assessment.docx.md
```

The system will:
- Parse the markdown
- Extract skills
- Generate 6 questions (default; change `num_questions` in `config.yaml`)
- Run all validators
- Print a summary and write output files

### Use a specific config file

```bash
robo-assess generate --md configs/Navigation_Assessment.docx.md --config config/config.yaml
```

### Run up to 3 loops until Supervisor approves (skip prompt between loops)

```bash
robo-assess generate --md configs/SLAM_Assessment.docx.md --max-loops 3 --yes
```

### Single loop (generate once, no retries)

```bash
robo-assess generate --md configs/Computer_Vision_Assessment.docx.md --max-loops 1
```

### Resume a failed run

```bash
robo-assess runs                          # list recent runs, find run_id
robo-assess generate --md configs/... --resume <run_id>
```

### Enable mid-run human review of borderline questions

```bash
robo-assess generate --md configs/... --human-review
```

Borderline = confidence between 82–87%. The system pauses and asks you to
approve/reject before finalising. Default mode (`log`) just logs them and
continues.

### GUI mode (emit JSON events for the Electron frontend)

```bash
robo-assess generate --md configs/... --json-events
```

---

## After Generation

### List all past runs

```bash
robo-assess runs
```

### Review generated questions as an instructor

```bash
robo-assess review outputs/2026-06-28_10-30-00_simulation/
```

This walks you through each question interactively (y/n/skip). Your decisions
are saved to `calibration/observations.jsonl` and improve future confidence
scores.

### Record a student attempt (for difficulty recalibration)

```bash
# Student passed Q001 in 8 minutes
robo-assess record-attempt --qid Q001 --passed --difficulty easy --time-minutes 8

# Student failed Q003
robo-assess record-attempt --qid Q003 --no-passed --difficulty hard --notes "forgot to spin"
```

---

## Output Structure

```
outputs/2026-06-28_10-30-00_ros2_nodes/
├── questions/
│   ├── Q001_publisher_node/
│   │   ├── question.yaml        ← what the student sees
│   │   ├── solution.yaml        ← reference answer
│   │   ├── boilerplate/         ← starter code with # TODO markers
│   │   │   └── publisher_node.py
│   │   └── evaluation/
│   │       └── grading.py       ← hidden auto-grader
│   ├── Q002_subscriber_node/
│   │   └── ...
│   └── Q003_service_client/
│       └── ...
└── reports/
    ├── confidence_report.json   ← per-question quality scores
    ├── supervisor_verdict.json  ← final APPROVED/REJECTED verdict
    └── token_report.json        ← API cost breakdown
```

---

## Config Reference (`config/config.yaml`)

| Setting | Default | What it controls |
|---|---|---|
| `temperature` | `0.7` | AI creativity (0=safe, 1=wild) |
| `max_tokens` | `4000` | Max response length per AI call |
| `num_questions` | `6` | Target number of questions per run |
| `coverage_target` | `0.85` | Fraction of syllabus skills to cover |
| `max_questions` | `14` | Hard cap (auto-scale won't exceed this) |
| `min_confidence` | `85.0` | Minimum quality score to pass a question |
| `similarity_reject_threshold` | `0.75` | Originality threshold (0.75 = 75% similar → reject) |
| `max_regeneration_attempts` | `2` | Retries per failing question within one loop |
| `generation_batch_size` | `2` | How many questions to generate at once |
| `generation_concurrency` | `4` | Parallel API calls during generation |
| `grading_backend` | `docker` | `docker` (live ROS2) or `ast` (static) |
| `human_review_mode` | `log` | `log` / `defer` / `block` for borderline questions |

---

## Changing the AI Model

**Cheapest (fast, lower quality):**
```yaml
model: openai/gpt-4o-mini
temperature: 0.5
```

**Best quality (slower, more expensive):**
```yaml
model: openai/gpt-4o
temperature: 0.7
```

**Use Claude instead of GPT:**
```yaml
provider: anthropic
model: claude-sonnet-4-6
temperature: 0.7
```
And set `ANTHROPIC_API_KEY` in `.env`.

---

## Cost Estimates

| Scenario | Approx. cost |
|---|---|
| 6 questions, 1 loop | ~$0.50–$0.80 |
| 6 questions, 3 loops (worst case) | ~$1.50–$2.50 |
| Using `gpt-4o-mini` for everything | ~$0.05–$0.15 |

Costs vary by token count of your input `.md` file.

---

## Troubleshooting

**`robo-assess: command not found`**
```bash
pip install --no-build-isolation -e .
# or add ~/.local/bin to PATH:
export PATH="$HOME/.local/bin:$PATH"
```

**`OPENROUTER_API_KEY not set`**
```bash
cp .env.example .env
# edit .env and fill in your key
```

**Docker grading falls back to AST**
This is expected if `make grader-build` hasn't been run. AST mode still works.

**Questions keep getting rejected (Supervisor REJECTED)**
- Lower `min_confidence` to 80 in `config.yaml` for a first test run
- Check that your `.md` file has clear skill descriptions
- Run with `--max-loops 3 --yes` to let it self-correct

---

## System Architecture (Flow)

```
Your .md file
     │
     ▼
[MD Summary Agent]      ← Summarises the teaching material
     │
     ▼
[Skill Extractor]       ← Pulls out ~10–20 teachable skills
     │
     ▼
[Skill Triage Agent]    ← Sorts skills by difficulty, picks which ones to test
     │
     ▼
[Question Generator]    ← Writes the actual questions (GPT-4o, concurrently)
     │
     ▼  ┌─────────────────────────────────────────┐
        │         VALIDATION PIPELINE              │
        │  Boilerplate check (# TODO markers)      │
        │  Difficulty calibration                  │
        │  Originality check (vectorstore)         │
        │  Scope & realism check                   │
        │  Auto-gradability check                  │
        │  Coverage verifier (skill drift)         │
        │  Executable grading (Docker/AST)         │
        │  Confidence scoring (0–100)              │
        └─────────────────────────────────────────┘
     │
     ▼
[Planner Agent]         ← Decides: pass or regenerate each question
     │
     ├── If any fail → [Regenerate] → back to Validation
     │
     ▼ (when quality bar met)
[Supervisor Agent]      ← Final APPROVED / REJECTED verdict
     │
     ▼
[Export]                ← Writes YAML files, solution, grading.py to outputs/
```

---
