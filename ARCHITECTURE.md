# Coding-Agent — System Architecture

Multi-agent LangGraph pipeline that turns a syllabus/course `.md` file into graded
ROS2/robotics coding assessment questions. This document covers: agents, tool
calls, API calls, control flow, and the exact grading/points math the system
uses to accept or reject a question.

A full visual diagram is in [`architecture.svg`](./architecture.svg) (open it directly —
GitHub/most editors render SVG inline).

---

## 1. Entry point

```
coding-agent generate --md syllabus/<file>.md [--config config/config.yaml]
                      [--max-loops N] [--yes] [--resume RUN_ID] [--human-review]
```

`cli.py:main()` → `generate_command()` → `Settings.load()` (`.env` → YAML → env
overrides → API key resolution) → builds one `Orchestrator` that constructs
every agent below, then loops `graph.invoke()` up to `--max-loops` times.

---

## 2. Agents (coding_agent/agents/)

| Agent | Role | Model tier (config/config.yaml `agent_models`) |
|---|---|---|
| `SyllabusParserAgent` | Parses syllabus text into skill entries | primary |
| `MdSummaryAgent` | Summarizes the input `.md` (cached by content hash) | `google/gemini-2.5-flash-lite` (cheap) |
| `MdParserAgent` | Extracts `SkillEntry` list → builds `CoverageMatrix` + `SkillGraph` | — (rule-based, no LLM) |
| `SkillTriageAgent` | One combined call: complexity triage + skill/domain/question-type picks | `google/gemini-2.5-flash-lite` (cheap) |
| `ContextRetrievalAgent` | RAG: pulls past exemplars + dedup hashes from vectorstore/memory | — |
| `QuestionGeneratorAgent` | Generates each question (3-block: spec / starter / reference solution) | `google/gemini-2.5-flash-lite` — primary is `openai/gpt-4.1` when not overridden |
| `DifficultyAgent` | Critiques whether declared difficulty matches actual solution complexity | cheap |
| `OriginalityAgent` | Checks vectorstore similarity against prior questions | — (embedding similarity, no LLM) |
| `SupervisorAgent` | Compares to `evaluations/question.json` eval bank; final audit + optional LLM judge | `supervisor_judge` → cheap |
| `ConfidenceAgent` | Computes the 0–100 pass/fail score (see §4) | — (rule-based aggregation) |
| `PlannerAgent` | Deterministic control loop: decide REGENERATE / NEXT_BATCH / FINALIZE; also drives `reflect` | uses LLM only for `reflect` critique |
| `HumanReviewAgent` | Optional: surfaces borderline-confidence questions for a human | — |

---

## 3. Tool calls (coding_agent/tools/)

These are function-calling tools exposed to agents (mainly the generator) via
`ToolRegistry` — Anthropic/OpenAI tool-use schemas built from
`tools/registry.py`, executed by `tools/handlers.py`:

| Tool | Backing call | Purpose |
|---|---|---|
| `check_similarity` | local vectorstore cosine similarity | duplicate-question guard |
| `query_skill_graph` | in-memory `SkillGraph` | prerequisite/coverage lookups |
| `estimate_difficulty` | local heuristic on solution code | pre-check before LLM critique |
| `fetch_ros2_docs` | **Context7 API** | pulls live ROS2/library docs into the prompt |
| `search_course_exercises` | **Tavily/Exa web search API** | finds similar course exercises for grounding |
| `fetch_course_content` | **web fetch** | retrieves a specific URL's content (truncated to `max_chars`) |
| `submit_question` | internal | terminal tool call — the model "submits" its structured answer |

---

## 4. External API calls

| Call | Client | Where |
|---|---|---|
| LLM generation/critique/judge calls | `llm_client.py` → OpenAI-compatible (`openai/*`, `google/*` via OpenRouter) or native Anthropic (`anthropic/*`) | every agent above tagged with a model |
| Vector search / upsert | Qdrant (`QDRANT_API_KEY`) or local JSON fallback (`vectorstore/index.json`) | `semantic_vectorstore.py`, `vectorstore.py` |
| Docs lookup | Context7 | `fetch_ros2_docs` tool |
| Web search | Tavily / Exa | `search_course_exercises`, `fetch_course_content` tools |

**Pricing table** (config/config.yaml, $ / 1M tokens, in/out):

| Model | In | Out |
|---|---|---|
| openai/gpt-4.1 (primary: generator + supervisor) | $2.00 | $8.00 |
| openai/gpt-4.1-mini (difficulty, eval, md_summary) | $0.40 | $1.60 |
| google/gemini-2.5-flash-lite (triage, scope_quality) | $0.10 | $0.40 |
| openai/gpt-4o | $2.50 | $10.00 |
| anthropic/claude-sonnet-4-6 | $3.00 | $15.00 |

---

## 5. Grading — how points are allocated

### 5.1 Confidence score (per-question pass bar)

`ConfidenceAgent` computes a single **0–100 confidence score** as a weighted
sum of 5 components, each weighted **20 points** (config/config.yaml
`confidence_weights`):

| Component | Weight | What it measures |
|---|---|---|
| `coverage` | 20 | Does the question cover its assigned syllabus skill(s)? |
| `difficulty` | 20 | Does actual solution complexity match declared difficulty? |
| `originality` | 20 | Is it sufficiently different from prior questions (vectorstore similarity)? |
| `format_quality` | 20 | Structural correctness: spec/starter/reference all present & well-formed |
| `eval_calibration` | 20 | Agreement with the eval-bank comparison (`evaluations/question.json`) |

**Pass bar:** `min_confidence_score = 80.0` — a question needs ≥80/100 to be
considered "confident enough" to keep.

> Note: `auto_grading` exists as a schema field but is hardcoded to `0.0` —
> executable/sandboxed grading was designed but is not currently wired in (see
> `sandbox/harness.py`, unused).

### 5.2 Quality bar (planner gate, applied every validate round)

On top of the confidence score, `PlannerAgent.evaluate_quality()` requires
ALL of:

| Gate | Threshold |
|---|---|
| `min_confidence` | ≥ 80.0 |
| `require_judge_approve` | off by default (in-loop LLM judge not required) |
| `max_similarity` | ≤ 0.60 (vectorstore cosine similarity to any past question) |
| `require_in_scope` | must map to a real syllabus skill |
| `min_difficulty_fit` | ≥ 0.6 |

A question failing any gate is routed to **reflect → regenerate** instead of
being accepted.

### 5.3 Supervisor final audit (package-level gate)

After all questions pass/exhaust retries, `SupervisorAgent` runs one
last audit over the whole package:

- `supervisor_min_validation_score = 75` — package-level validation score threshold.
- `coverage_target = 0.85` — at least 85% of extracted syllabus skills must be covered across the accepted questions.
- At least one approved question required, or the whole package is REJECTED.
- Optional post-loop LLM judge (`enable_llm_judge`, off by default) for a second opinion.

Verdict: `APPROVED` or `REJECTED`, which determines CLI exit code (0 vs 2) and
whether the CLI offers another generation loop.

### 5.4 Control-loop bounds (why it doesn't loop forever)

- `max_regeneration_attempts = 2` — a single failing question gets at most 2 regen tries before being dropped/left failing.
- `max_planner_steps = 8` — hard ceiling on total graph loop ticks per run (safety valve).
- `generation_concurrency = 4` — questions are generated in parallel batches of 4 via `ThreadPoolExecutor`.
- `similarity_reject_threshold = 0.60` — hard reject (not just quality-gate fail) above this similarity.

---

## 6. Full control flow

```
generate ──► validate ──► planner.decide()
   ▲            │              │
   │            │      ┌───────┼────────────┐
   │            │  REGENERATE  NEXT_BATCH  FINALIZE
   │            │      │            │           │
   │            │      ▼            │           ▼
   │            │   reflect         │       supervise
   │            │      │            │       (final audit,
   │            │      ▼            │        memory + vectorstore
   │            └── regenerate      │        writes, package
   │                   │            │        assembly)
   └───────────────────┴────────────┘           │
                                                 ▼
                                   export_run_v2 → outputs/<run>/questions/Q*/
                                                 │
                                   REJECTED + loops left? ──► prompt → loop again
```

See `architecture.svg` for the fully annotated diagram including every tool
call, API call, and the grading thresholds overlaid on the flow.
