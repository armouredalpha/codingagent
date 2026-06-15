# Robotics Assessment System — Complete Restructure ✅

## What You Have Now

A **clean, constraint-driven assessment generation system** for robotics education.

### Core Workflow

```
Teaching Material (.md)
    ↓
    Parse: Extract testable skills
    ↓
skills/skills.yaml
    ↓
    Generate: Pick skill → Create question → Validate
    ↓
Assessment Package (questions + reports)
```

### Two Simple Commands

```bash
# 1. Parse teaching material to extract skills
robo-assess parse --md teaching.md

# 2. Generate questions with constraints
robo-assess generate --md teaching.md \
    --difficulty easy \
    --bloom-level apply \
    --domain warehouse
```

---

## What Changed

### Removed (90+ files)
- Legacy template bank (1000+ lines)
- Dataset generators (gibberish data)
- Evaluation harnesses (never used)
- Calibration code
- Hiring/role agents (out of scope)
- Source research agent
- Example packages

### Added
- **SkillPickerAgent** — Picks the right skill based on difficulty/bloom level
- **MdParserAgent** — 3-tier parsing: read → summarize → extract skills
- **Simplified prompts** — 3 total (down from 8+)
- **Constraint-based generation** — User specifies difficulty/bloom, system picks skill

### Simplified
- **Orchestrator** — Two entry points: `run_parse()`, `run_generate()`
- **CLI** — 3 commands: `parse`, `generate`, `runs`
- **Guardrails** — Simple YAML config (not code)
- **No tool calling** — Text/JSON completion only

---

## Architecture: 3 Agents + Validators

```
┌──────────────────────────────────────┐
│  PARSE (.md → skills.yaml)           │
├──────────────────────────────────────┤
│ MdParserAgent                        │
│  T1: Read raw markdown               │
│  T2: Summarize sections (LLM)        │
│  T3: Extract skills (LLM)            │
│  Coverage check: all sections → ≥1   │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  GENERATE (constraints → question)   │
├──────────────────────────────────────┤
│ 1. SkillPickerAgent                  │
│    Input: difficulty, bloom_level    │
│    Output: selected skill             │
│                                       │
│ 2. QuestionGeneratorAgent            │
│    Input: skill + metadata            │
│    Output: question (JSON+code)       │
│                                       │
│ 3. Validators                        │
│    - Boilerplate (TODO markers)      │
│    - Originality (similarity < 0.75) │
│    - Scope (within syllabus)         │
│    - Difficulty (auto-calibration)   │
│    - Auto-grading (≥3 criteria)      │
│    - Confidence (≥85 to approve)     │
│                                       │
│ 4. Supervisor                        │
│    Final verdict: APPROVED/REJECTED   │
└──────────────────────────────────────┘
```

---

## Key Design Decisions

✅ **Single .md file input** — No YAML configs. Teaching material is the source of truth.

✅ **Constraint-based generation** — User specifies what they want (easy/apply/warehouse), system picks the right skill.

✅ **Simple skill picker** — Rule-based filtering + optional LLM tiebreaker for <3 candidates.

✅ **No regeneration loop** — Low-confidence questions logged but not re-looped (can add later).

✅ **No tool calling** — Text completion fast enough. Tools deferred until needed.

✅ **Guardrails as YAML** — Config only, no code evaluators.

✅ **Cleaned prompts** — 3 essential ones with clear placeholders for all variables.

---

## Files Structure

```
robotics-assessment-system/
├── prompts/
│   ├── skill_extractor.txt
│   ├── question_generator.txt
│   └── skill_picker.txt
├── guardrails/
│   └── guardrails.yaml              ← Simple config
├── skills/                          ← Auto-generated
│   ├── skills.yaml
│   └── meta.yaml
├── evaluations/                     ← User-provided
│   ├── question.json               (30 reference Q's)
│   ├── solution.json               (30 reference solutions)
│   └── README.md
├── robo_assess/
│   ├── agents/
│   │   ├── skill_picker.py         ← NEW
│   │   ├── md_parser.py            ← NEW
│   │   ├── question_generator.py
│   │   ├── orchestrator.py         ← UPDATED
│   │   ├── confidence_agent.py
│   │   └── ... (validation agents)
│   ├── cli.py                      ← UPDATED
│   ├── config.py                   ← UPDATED
│   ├── schemas.py                  ← UPDATED
│   └── ...
└── outputs/
    └── <run_id>/
        ├── package.json
        ├── confidence_report.json
        └── questions/
```

---

## Example Commands

```bash
# 1. Parse a simulation teaching material
$ robo-assess parse --md docs/simulation.md
✓ Extracted 15 skills from 8 sections
  Coverage: 8/8 sections
  Written to: skills/skills.yaml

# 2. Generate 1 easy/apply question
$ robo-assess generate --md docs/simulation.md \
    --difficulty easy --bloom-level apply --num 1
✓ SkillPickerAgent selected: "Load a Gazebo world file"
✓ QuestionGeneratorAgent generated question
✓ All validators passed
✓ Confidence: 87/100 → APPROVED
Output: outputs/run_a1b2c3d4/

# 3. Generate 1 hard/create question
$ robo-assess generate --md docs/simulation.md \
    --difficulty hard --bloom-level create --domain simulation --num 1
✓ SkillPickerAgent selected: "Design custom Gazebo plugin"
✓ QuestionGeneratorAgent generated question
✓ All validators passed
✓ Confidence: 91/100 → APPROVED
Output: outputs/run_e5f6g7h8/

# 4. List recent runs
$ robo-assess runs
run_a1b2c3d4 | simulation | APPROVED | 1 questions
run_e5f6g7h8 | simulation | APPROVED | 1 questions
```

---

## Prompts (Super Clean)

### skill_extractor.txt
```
Extract 3-7 testable skills from a section.
Each skill is: verb phrase + bloom_level + difficulty
Return: JSON array
```

### question_generator.txt
```
Generate ONE engineering ticket question.
Input: {skill}, {difficulty}, {bloom_level}, {domain}, 
       {allowed_scope}, {forbidden_scope}, {existing_titles}
Output: Three blocks (JSON spec + starter code + reference)
```

### skill_picker.txt
```
Select ONE skill from a list based on constraints.
Input: {difficulty}, {bloom_level}, {domain}, {all_skills_list}
Output: JSON with selected_skill + reasoning
```

---

## No Tool Calling (Why Not?)

All agents use **text completion** (`llm.complete()` / `llm.complete_json()`):

- ✅ Fast
- ✅ Reliable
- ✅ No latency overhead of tool invocation loops
- ✅ Sufficient for current use case

**Future tool candidates** (if needed):
- Skill vector search by tag
- File read from outputs directory
- Vector DB lookups
- But not required now — text completion sufficient

---

## Next Steps (Optional)

1. **Regeneration loop** — Add feedback from low-confidence questions
2. **Tests** — Update test suite with FakeLLM
3. **Example .md** — Create sample teaching material
4. **Guardrails loading** — Load guardrails.yaml in validators
5. **Tool calling** — Add if future need arises

---

## TL;DR

**Old:** YAML configs → templates → datasets → evals → calibration (over-engineered)

**New:** .md file → parse skills → constraint-based generation → simple validators (clean & focused)

**Result:** A system that's easy to understand, maintain, and extend.

