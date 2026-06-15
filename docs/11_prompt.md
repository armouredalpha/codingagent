# Prompt Architecture & Rewrites — June 11, 2026

## Overview

This document captures the complete prompt redesign and wiring for the robotics assessment system. The system now has **four LLM-backed agents** (question_generator, syllabus_parser, scope_critic, difficulty_critic) plus **offline/template fallbacks** for resilience.

---

## 1. Question Generator Prompt (`prompts/question_generator.txt`)

### What changed
**Before:** Batch envelope `{"questions":[...]}`, missing placeholders, no worked example.  
**After:** Single-question two-block output, 7 real placeholders, worked example last.

### Architecture

The prompt is **template-based** with these placeholders filled by `question_generator.py:304-312`:

| Placeholder | Source | Example |
|---|---|---|
| `{skill}` | coverage analysis | `"ROS2 publisher node"` |
| `{difficulty}` | distribution logic | `"easy"` / `"medium"` / `"hard"` |
| `{domain}` | domain cycle | `"warehouse"` / `"medical"` / `"factory"` |
| `{bloom_level}` | _BLOOM_MAP | `"apply"` / `"analyze"` / `"create"` |
| `{allowed_scope}` | syllabus skills | `"Publisher, Subscriber, Services"` |
| `{forbidden_scope}` | gated technologies | `"Nav2, SLAM, MoveIt, OpenCV"` |
| `{existing_titles}` | generated so far | `"- Complete the velocity publisher\n- Implement a service..."` |

### Output contract (must match `_parse_two_block_response` + `_parse_llm_question`)

```
<BLOCK 1: flat JSON object (no markdown fences)>
{
  "title": "",
  "robot": "",
  "scenario": "",
  "objective": "",
  "constraints": [],
  "tested_skills": [],
  "evaluation_criteria": [
    {"id":"EC1", "check":"", "target":"", "expected":"", "points":25, "description":""},
    ...4 criteria total, sum to 100...
  ],
  "common_mistakes": [],
  "estimated_solve_minutes": 0,
  "file_to_edit": ""
}
---SOLUTION_FILE---
<BLOCK 2: Python starter file (plain text, no markdown fence)>
import rclpy
...boilerplate with # TODO START / TODO END...
```

### Evaluation criteria rules
- Exactly **4 criteria**, points sum to **100**.
- `check` ∈ `{node_exists, topic_active, publish_rate, service_exists, parameter_set, tf_frame_exists, behaviour}`.
- `description` is **required and non-empty** (parser rejects empty descriptions).

### Low-end model hardening
- Removed batch framing (single question per call).
- Cut length ~40% (~230 lines instead of 439).
- Worked example placed **last** (recency boost for small models).
- Explicit field names in JSON contract.

---

## 2. Syllabus Parser (`prompts/syllabus_parser.txt` + `robo_assess/agents/syllabus_parser.py`)

### Purpose
Extract testable skills, ROS2 concepts, APIs, config elements, and difficulty range from raw syllabus.

### Placeholders
- `{topic}` — topic name (e.g., "ROS2 Fundamentals")
- `{syllabus}` — bulleted skill list

### Output contract
```json
{
  "skills": ["Implement a ROS2 publisher node...", "..."],
  "testable_skill_count": <integer, length of skills array>,
  "concepts": ["Publisher", "Topic", "..."],
  "apis": ["create_publisher", "publish", "..."],
  "config_elements": ["launch", "yaml", "..."],
  "ros_components": {
    "nodes": [], "topics": [], "services": [], "actions": [],
    "parameters": [], "tf_frames": [], "launch_entities": [], "simulation_entities": []
  },
  "difficulty_range": "easy|medium|hard"
}
```

### Hybrid LLM path (agent only)
- **LLM enabled when:** `provider != offline`
- **Cache:** analysis cache per (topic, syllabus) pair; skips LLM on cache hit
- **Fallback:** rule-based tables if LLM fails
- **Cost:** 1 call per run (very cheap, ~1.5k tokens)

---

## 3. Scope Critic (`prompts/scope_critic.txt` + `robo_assess/agents/scope_agent.py`)

### Purpose
Verify questions stay within the approved syllabus; flag out-of-scope technologies (Nav2, SLAM, MoveIt, OpenCV, etc.).

### Placeholders
- `{syllabus}` — bulleted skills from analysis
- `{questions}` — JSON array of question objects

### Batch input/output
**Input:** Array of objects, each with `id`, `scenario`, `objective`, `tested_skills`, `constraints`.  
**Output:**
```json
{
  "results": [
    {
      "id": "<question_id>",
      "classification": "IN_SCOPE | PARTIALLY_OUT_OF_SCOPE | OUT_OF_SCOPE",
      "coverage_score": 0-100,
      "syllabus_concepts_used": [],
      "out_of_scope_concepts": [],
      "violations": [],
      "question_is_out_of_scope": false,
      "explanation": "..."
    }
  ]
}
```

### Batching & retry logic (agent only)
- **Batch size:** `config.critic_batch_size` (default 10, set to 3 for small models)
- **Per-question retry:** if a verdict is missing or fails validation, re-call LLM with **length-1 batch** (just that question)
- **Never re-run whole batch** on failure
- **Fallback:** rule-based gating (check guardrails YAML) if LLM fails all retries

---

## 4. Difficulty Critic (`prompts/difficulty_critic.txt` + `robo_assess/agents/difficulty_agent.py`)

### Purpose
Independently calibrate true difficulty using Bloom level, concept count, solution LOC, multi-file edits. Compare to declared difficulty and report mismatches.

### Placeholders
- `{questions}` — JSON array of question objects

### Batch input/output
**Input:** Array of objects, each with `id`, `title`, `scenario`, `objective`, `tested_skills`, `constraints`, `declared_difficulty`, `bloom_level`, `solution_loc`, `files`.  
**Output:**
```json
{
  "results": [
    {
      "id": "<question_id>",
      "difficulty": "easy|medium|hard",
      "confidence": 0-100,
      "scores": {
        "bloom_complexity": 0-30,
        "concept_complexity": 0-20,
        "implementation_effort": 0-15,
        "debugging_complexity": 0-15,
        "integration_complexity": 0-15,
        "engineering_reasoning": 0-5
      },
      "role_alignment": "Robotics Intern | Junior Robotics Engineer | Robotics Engineer",
      "estimated_solve_minutes": 0,
      "rationale": "..."
    }
  ]
}
```

### Scoring heuristic
- **Bloom Complexity** (0–30): Remember/Understand = 0–10, Apply/Analyze = 10–20, Evaluate/Create = 20–30
- **Concept Complexity** (0–20): count distinct skills
- **Implementation Effort** (0–15): lines of reference solution, files edited
- **Debugging** (0–15): hidden issues, non-obvious failures
- **Integration** (0–15): cross-node/cross-system dependencies
- **Engineering Reasoning** (0–5): architecture/design decisions
- **Total:** 0–100 → easy (0–35) | medium (36–70) | hard (71–100)

### Rule-based `calibrate()` (always available)
- Kept separate so dataset_evaluator can reuse it without LLM dependency
- Used as **offline fallback** for batched path
- Never deleted; LLM verdicts override only on success

---

## 5. Shared Batching Helper (`robo_assess/agents/_llm_batch.py`)

Both critics use this function:

```python
def run_batched_critic(
    llm, system, template, payload, settings,
    validate, agent_name, log, token_counter=None, meta=None
) -> dict[str, dict]
```

**Algorithm:**
1. Chunk `payload` into batches (size = `settings.critic_batch_size`)
2. For each chunk, call LLM with template (payload → `{questions}` substitution)
3. Parse `{"results":[...]}`, validate each verdict with `validate(v)`
4. **Collect valid verdicts.** For any missing/invalid:
   1. Re-call LLM with **length-1 batch** (just that question)
   2. Validate again; collect if valid
   3. If still invalid, skip (agent falls back to rule-based for this question)
5. Return `{id: verdict}` for every question that succeeded

**Never re-runs the whole batch;** only retries individual failures.

---

## 6. Config Integration

### `config.yaml`
```yaml
provider: openrouter          # or anthropic
model: openai/gpt-4o
temperature: 0.7
max_tokens: 2200
critic_batch_size: 10
```

### `.env`
```
ROBO_PROVIDER=openrouter
ROBO_MODEL=openai/gpt-4o
OPENROUTER_API_KEY=sk-or-...
# Or for Anthropic:
# ROBO_PROVIDER=anthropic
# ROBO_MODEL=claude-sonnet-4-6
# ANTHROPIC_API_KEY=sk-ant-...
```

### Provider registry (`robo_assess/llm_client.py`)
Each provider has:
- `compat`: "openai" | "anthropic"
- `base_url`: resolved from registry
- `needs_key`: True
- `env_keys`: list of env var names to check

---

## 7. Orchestrator Wiring (`robo_assess/agents/orchestrator.py`)

All three agents now receive `token_counter`:

```python
self.syllabus_parser = SyllabusParserAgent(..., token_counter=self.token_counter)
self.difficulty = DifficultyCalibrationAgent(..., token_counter=self.token_counter)
self.scope = ScopeComplianceAgent(..., token_counter=self.token_counter)
```

Each agent records tokens via `token_counter.record(agent_name, usage, **metadata)`, visible in final `token_report.json`.

---

## 8. Export Fix (`robo_assess/workflows/assessment_workflow.py`)

`export_question()` now writes:

1. **`question.json`** — student-facing question (no code, no solutions)
2. **`README.md`** — brief scenario + task + constraints + run instructions
3. **`grading.json`** — evaluation metadata (criteria, points, pass threshold, auto_gradable flag)
4. **`solution/<file>`** — reference implementation (instructor only)
5. **`evaluate.py`** — runnable grading script

---

## 9. Testing

Added 3 new unit tests to `tests/test_agents.py`:

1. **`test_generator_two_block_parses_into_question`** — validates parser contract: flat JSON + separator + starter file → populated Question with 4 criteria summing to 100
2. **`test_scope_critic_batch_retry_and_fallback`** — batches 3 questions, omits 1 from response, marks 1 as always-bad; verifies per-question retry (never whole batch re-run) and rule-based fallback
3. **`test_difficulty_critic_overrides_and_falls_back`** — LLM verdict overrides rule-based; failed retries revert to rule-based per-question

**Result:** 94 passed, 0 failed (was 90 passed, 1 pre-existing export failure).

---

## 10. Deployment Notes

### OpenRouter (paid)
- **Inference speed:** ~30s–2 min per question depending on model
- **Critic batch size:** 10
- **Full run (6 configs, 6 questions each = 36 total):** ~90k tokens

### Anthropic (paid)
- **Inference speed:** ~20s–1 min per question
- **Critic batch size:** 10
- **Full run:** comparable token volume to OpenRouter

### Switch between providers
Update `ROBO_PROVIDER` and the matching API key in `.env`.

---

## 11. Prompt Quality Principles

These rewrites were optimized for:

1. **Structural specificity** — exact JSON schema, no variations
2. **Placeholder injection** — all values come from runtime context, not guessed by the model
3. **Low-end model robustness** — worked example, recency, field names explicit, batch size tuned
4. **Fallback coverage** — every agent has rule-based path as offline fallback
5. **Auditability** — all tokens recorded, all stages logged to SQLite

---

## 12. Running the Full System

```bash
# Generate from all 6 configs
cd /home/niat/claude_Ws/robotics-assessment-system
for cfg in configs/*.yaml; do
  python3 -m robo_assess.cli generate --request "$cfg"
done

# Check results
ls outputs/
cat outputs/<run_id>/token_report.json
cat outputs/<run_id>/summary.json
```

---

## 13. Future Enhancements

- **Streaming output:** stream LLM tokens to see progress (not block on full response)
- **Critic refinement:** add richer feedback (e.g., confidence scores integrated into hiring decisions)
- **Multi-turn refinement:** iterate on low-confidence questions (regenerate + re-score)
- **Distributed execution:** run agents in parallel (currently sequential)
