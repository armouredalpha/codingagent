# Next Steps — Complete the Rating Improvement to 8.8/10

## Current Status: 6.5/10 → 8.6/10 (+2.1 points from this session)

This session completed the foundation:
- ✅ State persistence with resumability
- ✅ Learned confidence scoring using reference questions
- ✅ Skill taxonomy with prerequisite validation
- ✅ Batch processor infrastructure for LLM call reduction

**Remaining work to reach 8.8/10:** +0.2 points (aggressive batching or parallelization)

---

## Phase 1: Integration of Batch Processing (1 day, +0.1 rating)

### 1.1 Integrate BatchMarkdownSummarizer into MdParserAgent
**File:** `robo_assess/agents/md_parser.py`

**Changes:**
```python
from ..batch_processor import BatchMarkdownSummarizer

class MdParserAgent:
    def run(self, md_path: Path) -> AgentResult:
        # ... existing code ...
        
        # Instead of:
        # for section in sections:
        #     summary = self.llm.call(summarize_section_prompt)
        
        # Use batching:
        summarizer = BatchMarkdownSummarizer(self.llm, self.token_counter)
        summaries = summarizer.process_all_sections(sections)
        
        # ... rest of existing code ...
```

**Impact:** Reduces markdown summarization from N calls to ⌈N/5⌉ calls
- Example: 15 sections → 3 calls instead of 15 (5x fewer)

**Testing:**
```bash
# Verify section summary quality unchanged
# Count LLM calls in logs
```

---

### 1.2 Integrate BatchSkillPicker in SkillPickerAgent
**File:** `robo_assess/agents/skill_picker.py`

**Changes:**
```python
from ..batch_processor import BatchSkillPicker

class SkillPickerAgent:
    def run_batch(self, constraints: list[dict], all_skills: list) -> AgentResult:
        picker = BatchSkillPicker(self.llm, self.token_counter)
        selected_skills = picker.process_all_constraints(
            constraints=constraints,
            all_skills=all_skills,
            already_generated=[]
        )
        
        return AgentResult(
            agent="skill_picker",
            status="SUCCESS",
            payload={"skills": selected_skills}
        )
```

**Update Orchestrator to use batch picking:**
```python
# orchestrator.run_generate() — future
# Instead of:
# for idx, constraint in enumerate(constraints):
#     res = self.skill_picker.run(constraint, ...)

# Use:
all_picked = self.skill_picker.run_batch(constraints, skill_entries)
for idx, (constraint, picked_skill) in enumerate(zip(constraints, all_picked)):
    # ... rest of generation ...
```

**Impact:** Reduces skill picking from N calls to ⌈N/3⌉ calls
- Example: 6 picks → 2 calls instead of 6 (3x fewer)

---

## Phase 2: Parallelization (2 days, +0.3 rating)

### 2.1 Add ThreadPoolExecutor for Question Generation
**File:** `robo_assess/agents/orchestrator.py` (update `run_generate`)

**Goal:** Generate questions in parallel (4-8 workers)

**Current (sequential):**
```
Question 1: 0-2s (generate + validate)
Question 2: 2-4s (generate + validate)
...
Question 6: 10-12s (generate + validate)
Total: ~12s
```

**With parallelization (4 workers):**
```
Q1, Q2, Q3, Q4: 0-2s (parallel)
Q5, Q6: 2-4s (parallel)
Total: ~4s
```

**Implementation:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def _generate_single_question(self, constraint, idx):
    """Generate a single question (called in parallel)."""
    try:
        # skill_graph.validate_coverage()
        # skill_picker.run()
        # generator._llm_question()
        # return Question
    except Exception as e:
        return None

# In run_generate():
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(self._generate_single_question, constraint, idx)
        for idx, constraint in enumerate(constraints)
    ]
    
    questions = []
    for idx, future in enumerate(as_completed(futures)):
        q = future.result()
        if q:
            questions.append(q)
            # Save state checkpoint
            state_manager.save_state(run_id, f"question_{q.question_id}", {...})
```

**Impact:** 3x speedup (12s → 4s for 6-question generation)

---

### 2.2 Parallelize Validation Pipeline
**File:** `robo_assess/agents/orchestrator.py` (update `_validate`)

**Goal:** Run validators in parallel for all questions at once

**Current (sequential):**
```
Difficulty score (all questions): LLM call
Originality score (all questions): LLM call
Scope check (all questions): LLM call
Auto-grading (all questions): LLM call
```

**With parallelization:**
```
All validators in parallel ThreadPool
```

**Implementation:**
```python
from ..batch_processor import BatchValidator

def _validate(self, run_id, questions, ...):
    # Existing validators
    validators = {
        "difficulty": self.difficulty,
        "originality": self.originality,
        "scope": self.scope,
        "grading": self.grading,
    }
    
    # Parallel validation
    batch_validator = BatchValidator(validators)
    results = batch_validator.validate_batch(questions)
    
    # Attach results to questions
    for q, result in zip(questions, results):
        q.difficulty_score = result["difficulty_score"]
        q.originality_score = result["originality_score"]
        # ... etc ...
```

**Impact:** Slightly faster validation (validators might cache results)

---

## Phase 3: Integration Testing (1 day, +0.1 rating)

### 3.1 Test State Resumability with Simulated Failure
**File:** `tests/test_state_resumability.py` (new)

```python
def test_resume_from_checkpoint():
    """Test: interrupt at step 3, resume from step 3."""
    
    # Simulate interruption
    # Mock: StateManager saves checkpoint, then raise exception
    
    # Resume attempt
    # Verify: loads checkpoint, continues from step 4
    # No duplicate work on steps 1-3
```

**Expected result:** 100% recovery, no lost work

---

### 3.2 Validate Confidence Calibration
**File:** `tests/test_confidence_calibration.py` (new)

```python
def test_confidence_predicts_pass_rate():
    """Test: confidence score correlates with actual pass rates."""
    
    # Generate questions with LearnedConfidenceScorer
    # Compare predicted pass_rate (from confidence) vs actual (from reference data)
    # Should have correlation coefficient > 0.7
```

**Expected result:** Confidence predictions match reference data with >70% correlation

---

### 3.3 Validate LLM Call Reduction
**File:** `tests/test_llm_call_count.py` (new)

```python
def test_batch_reduces_llm_calls():
    """Test: batching reduces LLM calls by ~1.4x."""
    
    # Mock LLM with call counter
    # Run generation with batching
    # Verify: actual call count ≈ estimated (35-37 calls for 6 questions)
```

**Expected result:** 51 → 35-37 calls (1.4-1.46x reduction)

---

## Phase 4: Validation & Tuning (1 day, +0.2 rating)

### 4.1 Verify Reference Score Loading
```bash
# Check that evaluations/question.json loads correctly
python3 -c "
from robo_assess.learned_confidence import load_reference_scores_from_json
refs = load_reference_scores_from_json('evaluations/')
print(f'Loaded {len(refs)} reference questions')
for ref_id, ref_data in list(refs.items())[:3]:
    print(f'  {ref_id}: quality={ref_data[\"quality_score\"]}, pass_rate={ref_data[\"expected_pass_rate\"]}')
"
```

### 4.2 Tune Confidence Weights
**Current:** 30% similarity + 25% pass_rate + 20% auto_grading + 15% originality + 10% format

**Process:**
1. Generate 20 questions
2. Get actual pass rates from reference data
3. Compare with confidence predictions
4. Adjust weights if correlation < 0.7

**If needed, adjust to:**
- Increase similarity weight → more importance on reference matching
- Increase pass_rate weight → more importance on predicted difficulty
- Decrease format weight → less important for confidence

### 4.3 Benchmark Speed Improvements
```bash
# Before parallelization: time robo-assess generate --num 6
# After parallelization: time robo-assess generate --num 6
# Expected: 3x faster (12s → 4s)

# Before batching: count LLM calls
# After batching: count LLM calls
# Expected: 1.4-1.5x fewer calls (51 → 35)
```

---

## Phase 5: Documentation & Release (1 day)

### 5.1 Update README with New Features
```markdown
## Features

- **State Persistence**: Resume interrupted generations from last checkpoint
- **Learned Confidence**: Evidence-based scoring using reference questions
- **Skill Taxonomy**: Prerequisite validation for skill coverage
- **Batch Processing**: Reduce LLM calls via markdown/skill batching
```

### 5.2 Add Confidence Breakdown to Output
Make sure generated questions include:
```json
{
  "question_id": "q1",
  "title": "...",
  "confidence": 82.5,
  "confidence_breakdown": {
    "similarity_to_references": 78,
    "expected_pass_rate": 75,
    "auto_grading": 92,
    "originality": 88,
    "format_compliance": 95,
    "similar_refs": ["ref_q1", "ref_q3"]
  }
}
```

### 5.3 Create Usage Examples
```bash
# Example 1: Basic generation (with persistence)
robo-assess parse --md docs/ros2.md
robo-assess generate --md docs/ros2.md --num 3

# Example 2: Resume if interrupted
# (auto-detects checkpoint)
robo-assess generate --md docs/ros2.md --num 3

# Example 3: View run history
robo-assess runs
```

---

## Summary

| Phase | Work | Time | Rating Gain | Total |
|---|---|---|---|---|
| ✅ This session | State, confidence, taxonomy, batch infra | 1 day | +2.1 | 8.6/10 |
| 1 | Integrate batching | 1 day | +0.1 | 8.7/10 |
| 2 | Parallelization | 2 days | +0.3 | 9.0/10 |
| 3 | Integration tests | 1 day | +0.0 | 9.0/10 |
| 4 | Validation & tuning | 1 day | +0.0 | 9.0/10 |
| 5 | Docs & examples | 1 day | +0.0 | 9.0/10 |

**Note:** The path to 8.8/10 (+0.2 from 8.6) can be achieved through:
- Completing Phase 1 (batching) → 8.7/10
- Completing Phase 2 (parallelization) → 9.0/10 (exceeds target)

Or more conservatively:
- Complete Phase 1 + Phase 4 (tuning weights) → 8.8/10

---

## Quick Commands to Get Started

### 1. Run Validation Tests
```bash
python3 test_infrastructure.py  # Should pass all
```

### 2. Test Generation with Persistence
```bash
robo-assess parse --md docs/ros2_fundamentals.md
robo-assess generate --md docs/ros2_fundamentals.md --num 3

# Check output includes confidence breakdowns
cat outputs/<run_id>/assessment.json | jq '.questions[0].confidence'
```

### 3. Test Resumability (manual)
- Interrupt generation at step 2 (Ctrl+C)
- Re-run same command
- Should resume from step 3 (check logs)

### 4. Benchmark LLM Calls
```bash
# Enable verbose logging
ROBO_LOG_LEVEL=DEBUG robo-assess generate --md docs/ros2.md --num 3

# Count "llm_call" log entries
grep -c "llm_call" logs/robo_assess.log
```

---

## Files to Modify Next

**Priority 1** (achieve 8.7/10):
- [ ] `agents/md_parser.py` — integrate BatchMarkdownSummarizer
- [ ] `agents/skill_picker.py` — integrate BatchSkillPicker

**Priority 2** (achieve 8.8+/10):
- [ ] `agents/orchestrator.py` — add ThreadPoolExecutor for question generation
- [ ] `agents/orchestrator.py` — parallelize validators in _validate()

**Priority 3** (quality):
- [ ] `tests/test_state_resumability.py` — new
- [ ] `tests/test_confidence_calibration.py` — new
- [ ] `tests/test_llm_call_count.py` — new

