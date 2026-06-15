# Architecture: State Persistence, Learned Confidence, & Skill Taxonomy

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Commands                            │
│  robo-assess parse --md file.md                              │
│  robo-assess generate --md file.md --num N                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Orchestrator.      │
        │ run_generate()     │
        └────────┬───────────┘
                 │
        ┌────────▼───────────────────────────────────────────────┐
        │                                                         │
        │  1. Initialize StateManager                            │
        │     ├─ Create SQLite DB at logs/state.db               │
        │     ├─ start_run(run_id, md_file, mode, num_questions) │
        │     └─ Register run in generation_runs table           │
        │                                                         │
        │  2. Load Reference Scores                              │
        │     ├─ Load evaluations/question.json                  │
        │     ├─ Extract quality_score, expected_pass_rate       │
        │     └─ Upsert into reference_scores table              │
        │                                                         │
        │  3. Initialize LearnedConfidenceScorer                 │
        │     └─ Pass reference_scores dict                      │
        │                                                         │
        │  4. Build SkillGraph                                   │
        │     ├─ Create DAG from SkillEntry list                │
        │     ├─ Auto-infer prerequisites                        │
        │     └─ Validate no cycles                              │
        │                                                         │
        │  5. Generate Questions (per constraint)                │
        │     ├─ skill_graph.validate_coverage()                 │
        │     ├─ skill_picker.run()                              │
        │     ├─ generator._llm_question()                       │
        │     └─ state_manager.save_state(run_id, "constraint_N")|
        │                                                         │
        │  6. Validate All Questions                             │
        │     ├─ Run validators (difficulty, originality, etc.)  │
        │     └─ Score with LearnedConfidenceScorer              │
        │                                                         │
        │  7. Save Question Scores                               │
        │     ├─ save_question_scores(run_id, q_id, confidence)  │
        │     ├─ Store similar_refs for reference matching       │
        │     └─ Store features for future analysis              │
        │                                                         │
        │  8. Finalize & Persist                                 │
        │     ├─ Supervisor.run(pkg)                             │
        │     └─ state_manager.complete_run(run_id)              │
        │                                                         │
        └────────────────────────────────────────────────────────┘
```

---

## Component Details

### StateManager: Persistence Layer
**Purpose:** Save/restore generation state; enable resumability; track confidence breakdowns.

**Database Schema:**
```sql
generation_runs
├─ run_id (PK)
├─ md_file
├─ mode (parse|generate)
├─ status (in_progress|completed|failed)
├─ started_at
├─ completed_at
├─ error_message
└─ num_questions

generation_state
├─ run_id (FK)
├─ step_name (PK with run_id)
├─ state_json (serialized state)
└─ created_at

question_scores
├─ run_id (FK)
├─ question_id (PK with run_id)
├─ raw_confidence
├─ final_confidence
├─ coverage_score, difficulty_score, originality_score, etc.
├─ similar_ref_ids (JSON list)
└─ features_json

reference_scores
├─ ref_id (PK)
├─ title, difficulty, scenario
├─ skills (JSON list)
├─ quality_score (0-100)
├─ expected_pass_rate (0-1)
├─ num_tests_passed, num_tests_total
└─ created_at
```

**Resumability Flow:**
```
Generation attempt 1:
├─ start_run(run_id, "ros2.md", "generate", 6)
├─ Process constraint 0 → save_state(run_id, "constraint_0", {...})
├─ Process constraint 1 → save_state(run_id, "constraint_1", {...})
├─ Process constraint 2 → save_state(run_id, "constraint_2", {...})
└─ CRASH

Generation attempt 2 (re-run same command):
├─ Orchestrator.run_generate(...)
├─ StateManager detects existing checkpoint at "constraint_2"
├─ Load saved state from "constraint_2"
├─ Resume from constraint 3 instead of restarting
└─ complete_run(run_id)
```

---

### LearnedConfidenceScorer: Reference-Based Calibration
**Purpose:** Predict student pass rates using reference questions as ground truth.

**Features Extracted:**
```python
features = {
    "num_skills": 2,
    "num_criteria": 3,
    "lines_of_code": 45,
    "bloom_level_rank": 3,  # 1-6 (remember to create)
    "has_constraints": True,
    "scenario_complexity": 25,  # word count
    "num_common_mistakes": 2
}
```

**Scoring Formula:**
```
confidence = 0.30 * similarity_to_refs
           + 0.25 * predicted_pass_rate
           + 0.20 * auto_grading_score
           + 0.15 * originality_score
           + 0.10 * format_compliance
```

Where:
- **similarity_to_refs**: Cosine + Jaccard blend of (title, scenario, skills) vs top-3 references
- **predicted_pass_rate**: Average reference pass_rate, adjusted by feature differences
  - Each additional skill: ×0.95 penalty
  - Higher Bloom level (>3): ×0.95 penalty

**Example:**
```python
question = Question(
    title="Create a ROS2 Publisher in C++",
    scenario="Write a minimal publisher that sends Twist messages",
    tested_skills=["ROS2", "C++"]
)

validators = {
    "auto_grading": 92,
    "originality": 88,
    "format_compliance": 95
}

confidence, breakdown = scorer.score(question, validators)
# confidence: 82.5 (rounded)
# breakdown:
# {
#   "raw_confidence": 82.5,
#   "similarity_to_references": 78.0,  # 78% match to top-3 refs
#   "expected_pass_rate": 75.0,  # 75% of students expected to pass
#   "auto_grading": 92,
#   "originality": 88,
#   "format_compliance": 95,
#   "similar_refs": ["ref_q1", "ref_q3", "ref_q7"],
#   "features": {...}
# }
```

---

### SkillGraph: Prerequisite Validation
**Purpose:** Verify syllabus covers all prerequisites for tested skills; enable curriculum design.

**DAG Structure:**
```
    create publisher ─┐
          │           ├─ implement callback
    create subscriber ┤
          │           ├─ design launch file
    implement callback┘
```

**Validation Example:**
```python
graph = SkillGraph()
graph.build_from_skills(skill_entries)

# Scenario 1: Valid coverage
question_skill = "implement callback"
syllabus = ["create publisher", "create subscriber", "implement callback"]
is_valid, missing = graph.validate_coverage(syllabus, question_skill)
# is_valid: True, missing: {}

# Scenario 2: Missing prerequisite
syllabus = ["create publisher", "implement callback"]  # missing subscriber
is_valid, missing = graph.validate_coverage(syllabus, question_skill)
# is_valid: False, missing: {"create subscriber"}

# Log: warning("missing_prerequisites", skill="implement callback", missing=[...])
```

**Auto-inference Rules:**
```python
# Rule 1: "implement X" requires "create X"
graph.add_skill("implement callback", ...)
graph.add_skill("create subscriber", ...)
# Auto-inferred: implement callback requires create subscriber

# Rule 2: "design launch file" requires both publishers + subscribers
# Auto-inferred: design launch file requires create publisher + create subscriber

# Rule 3: "handle errors in X" requires "implement X"
# Auto-inferred: handle errors in callback requires implement callback
```

---

### BatchProcessor: LLM Call Reduction
**Purpose:** Reduce LLM calls by batching similar requests (markdown summarization, skill picking).

**Strategy 1: Markdown Summarization**
```
Without batching:
└─ Summarize section 1   → 1 call
└─ Summarize section 2   → 1 call
├─ ...
└─ Summarize section 15  → 1 call
   Total: 15 calls

With batching (batch_size=5):
└─ Batch 1: Summarize sections 1-5   → 1 call
└─ Batch 2: Summarize sections 6-10  → 1 call
└─ Batch 3: Summarize sections 11-15 → 1 call
   Total: 3 calls
   Reduction: 15 → 3 (5x per-batch, 5x fewer calls)
```

**Strategy 2: Skill Picking**
```
Without batching:
└─ Pick skill for constraint 1   → 1 call
├─ ...
└─ Pick skill for constraint 6   → 1 call
   Total: 6 calls

With batching (batch_size=3):
└─ Batch 1: Pick skills for constraints 1-3 → 1 call
└─ Batch 2: Pick skills for constraints 4-6 → 1 call
   Total: 2 calls
   Reduction: 6 → 2 (3x per-batch, 3x fewer calls)
```

**Total LLM Call Reduction:**
```
Baseline (51 calls for 6-question generation):
├─ Markdown: 15 calls
├─ Skill picking: 6 calls
├─ Question generation: 6 calls
├─ Validators: 24 calls (4 per question)
└─ Total: 51 calls

With batching (37 calls):
├─ Markdown: 3 calls (15 → 3)
├─ Skill picking: 2 calls (6 → 2)
├─ Question generation: 6 calls
├─ Validators: 24 calls (unchanged)
└─ Total: 35 calls
   Reduction: 1.46x

With aggressive validator batching (12 calls, future):
├─ Markdown: 3 calls
├─ Skill picking: 2 calls
├─ Question generation: 6 calls
├─ Validators: 1 call (all 6 questions in one call)
└─ Total: 12 calls
   Reduction: 4.2x (deferred to next phase)
```

---

## Data Flow Example

**Scenario:** Generate 6 questions from `docs/ros2_fundamentals.md`

### Step 1: Load Skills & References
```
Orchestrator.run_generate(md_path="docs/ros2_fundamentals.md", num_questions=6)
  ├─ Load skills/skills.yaml → 20 skills
  ├─ Load evaluations/question.json → 30 reference questions
  └─ Build SkillGraph with auto-inferred prerequisites
```

### Step 2: Per-Constraint Generation
```
For constraint in [6 constraints]:
  1. skill_graph.validate_coverage(syllabus, skill)
     └─ Check: is skill's prerequisites in syllabus?
  
  2. skill_picker.run() → select skill
     └─ e.g., "create publisher"
  
  3. generator._llm_question() → generate question
     └─ Question object with title, scenario, evaluated_skills, etc.
  
  4. state_manager.save_state("constraint_N", {...})
     └─ Checkpoint after question 1, 2, 3, ...
```

### Step 3: Validation & Confidence Scoring
```
For each generated question:
  1. Run validators:
     ├─ difficulty_agent.run() → difficulty_score
     ├─ originality_agent.run() → originality_score
     ├─ scope_agent.run() → scope_score
     └─ grading_agent.run() → auto_grading_score
  
  2. Score with learned confidence:
     └─ confidence_scorer.score(question, validators)
        ├─ Compute features
        ├─ Find similar_refs (top-3)
        ├─ Predict pass_rate from references
        └─ Return: confidence (0-100), breakdown dict
  
  3. Persist:
     └─ state_manager.save_question_scores(
          run_id, q_id, confidence, breakdown, refs, features
        )
```

### Step 4: Finalize
```
1. supervisor.run(pkg) → final verdict
2. state_manager.complete_run(run_id, "completed")
3. Return: AssessmentPackage with all questions + metadata
```

---

## Integration Points

### 1. CLI → Orchestrator
```python
# cli.py: generate_command()
orchestrator = Orchestrator(settings=settings)
pkg = orchestrator.run_generate(md_path, num_questions=args.num)
```

### 2. Orchestrator → StateManager
```python
# orchestrator.run_generate()
state_manager = StateManager(str(Path(settings.log_dir) / "state.db"))
state_manager.start_run(run_id, str(md_path), "generate", len(constraints))
# ... per constraint ...
state_manager.save_state(run_id, f"constraint_{idx}", {...})
# ... after validation ...
state_manager.save_question_scores(run_id, q.question_id, confidence, breakdown, refs, features)
state_manager.complete_run(run_id)
```

### 3. Orchestrator → LearnedConfidenceScorer
```python
# orchestrator.run_generate()
reference_scores = load_reference_scores_from_json(str(evaluations_dir))
confidence_scorer = LearnedConfidenceScorer(reference_scores)
# ... after validation ...
confidence, breakdown = confidence_scorer.score(question, validators)
```

### 4. Orchestrator → SkillGraph
```python
# orchestrator.run_generate()
skill_graph = SkillGraph()
skill_graph.build_from_skills(skill_entries)
# ... per constraint ...
is_valid, missing = skill_graph.validate_coverage(request.syllabus, skill)
if not is_valid:
    log.warning("missing_prerequisites", skill=skill, missing=list(missing))
```

---

## Future Integration: Batch Processing

### Phase 2a: BatchMarkdownSummarizer in MdParserAgent
```python
# agents/md_parser.py (future)
summarizer = BatchMarkdownSummarizer(self.llm, self.token_counter)
summaries = summarizer.process_all_sections(sections)
# 15 sections → 3 calls instead of 15
```

### Phase 2b: BatchSkillPicker in SkillPickerAgent
```python
# agents/skill_picker.py (future)
picker = BatchSkillPicker(self.llm, self.token_counter)
selected_skills = picker.process_all_constraints(
    constraints, all_skills, already_generated
)
# 6 picks → 2 calls instead of 6
```

---

## Configuration

```yaml
# config.yaml

# Persistence
log_dir: logs                           # SQLite database location
log_db_path: logs/runs.db               # Run history

# Reference data
evaluations_dir: evaluations            # For question.json, solution.json
eval_match_min_score: 85.0              # Difficulty calibration threshold

# Skills
skills_dir: skills                      # Parsed skills output

# Skill taxonomy
max_critic_retries: 2                   # Regeneration limit per question
parser_section_retries: 3               # Markdown section parsing retries
```

---

## Testing

### Validation Tests (`test_infrastructure.py`)
```
✅ StateManager: start_run, save_state, load_state, complete_run
✅ SkillGraph: add_skill, add_prerequisite, validate_coverage, topological_sort
✅ LearnedConfidenceScorer: load_reference_scores, score
✅ BatchProcessor: markdown reduction (15→3), skill picker (6→2)
```

**Run:**
```bash
python3 test_infrastructure.py
```

---

## Performance Expectations

| Metric | Value |
|---|---|
| State persistence overhead | <10ms per checkpoint |
| SkillGraph lookup | O(n) where n = num skills |
| LearnedConfidenceScorer | O(m) where m = num reference questions |
| Batch LLM call reduction | 1.46x (51 → 35 calls) |
| Resumability recovery time | <1s (SQLite lookup) |

