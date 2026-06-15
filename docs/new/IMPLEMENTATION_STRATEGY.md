# Implementation Strategy: 5 Major Improvements

## Priority & Blocking Order

```
STATE PERSISTENCE (BLOCKING)
    ↓
LEARNED CONFIDENCE (depends on state)
    ↓
LLM CALL REDUCTION (performance optimization)
    ↓
SKILL TAXONOMY (independent)
    ↓
PARALLELIZATION (needs batching + state)
```

---

## 1. STATE PERSISTENCE & RESUMABILITY (BLOCKING)

### Why First?
- Without state, can't resume after failures
- Without state, can't implement learned confidence (need to save ref scores)
- Without state, can't debug what went wrong

### What to Persist

```sqlite
CREATE TABLE generation_runs (
    run_id TEXT PRIMARY KEY,
    md_file TEXT,
    mode TEXT,  -- 'auto', 'manual', 'random'
    status TEXT,  -- 'in_progress', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE generation_state (
    run_id TEXT,
    step_name TEXT,  -- 'parse', 'skill_pick_1', 'gen_1', 'validate_1', etc
    state_json TEXT,  -- full state snapshot
    created_at TIMESTAMP,
    PRIMARY KEY (run_id, step_name)
);

CREATE TABLE question_scores (
    run_id TEXT,
    question_id TEXT,
    raw_confidence FLOAT,
    final_confidence FLOAT,
    coverage_score FLOAT,
    difficulty_score FLOAT,
    originality_score FLOAT,
    scope_score FLOAT,
    auto_grading_score FLOAT,
    format_score FLOAT,
    PRIMARY KEY (run_id, question_id)
);

CREATE TABLE reference_scores (
    ref_id TEXT PRIMARY KEY,  -- from evaluations/question.json
    title TEXT,
    difficulty TEXT,
    scenario TEXT,
    skills TEXT,  -- JSON array
    quality_score FLOAT,  -- Expert rating 0-100
    expected_pass_rate FLOAT,  -- 0-1, from evaluations/solution.json results
    num_tests_passed INT,
    num_tests_total INT,
    created_at TIMESTAMP
);
```

### Implementation

```python
class StateManager:
    def __init__(self, db_path="logs/state.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
    
    def save_state(self, run_id, step_name, state):
        """Save state after each major step"""
        self.conn.execute(
            "INSERT INTO generation_state VALUES (?, ?, ?, ?)",
            (run_id, step_name, json.dumps(state), datetime.now())
        )
        self.conn.commit()
    
    def load_state(self, run_id, step_name):
        """Load state from checkpoint"""
        result = self.conn.execute(
            "SELECT state_json FROM generation_state WHERE run_id=? AND step_name=?",
            (run_id, step_name)
        ).fetchone()
        return json.loads(result[0]) if result else None
    
    def get_last_completed_step(self, run_id):
        """Find last checkpoint to resume from"""
        result = self.conn.execute(
            "SELECT step_name FROM generation_state WHERE run_id=? ORDER BY created_at DESC LIMIT 1",
            (run_id,)
        ).fetchone()
        return result[0] if result else None
```

---

## 2. LEARNED CONFIDENCE SCORING

### The Model

```python
# Step 1: Score Reference Questions (ONE TIME)
reference_scores = {
    "Q001": {
        "title": "Implement velocity publisher",
        "difficulty": "easy",
        "scenario": "...",
        "skills": ["create publisher"],
        "quality_score": 95,  # Expert rating
        "expected_pass_rate": 0.92,  # 92% of students pass this
        "features": {
            "num_skills": 1,
            "num_criteria": 4,
            "lines_of_code": 15,
            "bloom_level_rank": 3,  # apply
        }
    }
}

# Step 2: Compute Features for Generated Question
def compute_features(question):
    return {
        "num_skills": len(question.tested_skills),
        "num_criteria": len(question.evaluation_criteria),
        "lines_of_code": count_code_lines(question.reference_solution),
        "bloom_level_rank": BLOOM_RANK[question.bloom_level],
        "has_constraints": len(question.constraints) > 0,
        "scenario_complexity": len(question.scenario.split()),
    }

# Step 3: Find Similar Reference Questions
def find_similar_references(generated_q, ref_questions, top_k=3):
    """Use cosine similarity on scenario text"""
    gen_embedding = embed(generated_q.scenario)
    similarities = []
    for ref_id, ref_q in ref_questions.items():
        ref_embedding = embed(ref_q.scenario)
        sim = cosine_similarity(gen_embedding, ref_embedding)
        similarities.append((ref_id, sim, ref_q))
    return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]

# Step 4: Learn Expected Pass Rate
def predict_pass_rate(features, similar_refs):
    """
    If similar reference questions have:
      - avg quality_score: 92
      - avg expected_pass_rate: 0.88
    And generated question has similar features → expect 0.88 pass rate
    """
    avg_ref_quality = mean([r.quality_score for r in similar_refs])
    avg_ref_pass_rate = mean([r.expected_pass_rate for r in similar_refs])
    
    # If generated question is harder (more skills), adjust down
    feature_adjustment = 1.0
    if len(features["skills"]) > 1:
        feature_adjustment = 0.95 ** (len(features["skills"]) - 1)
    
    return avg_ref_pass_rate * feature_adjustment

# Step 5: Compute Learned Confidence
def compute_learned_confidence(question, similar_refs, validators):
    similarity_to_refs = mean([sim for _, sim, _ in similar_refs])
    expected_pass_rate = predict_pass_rate(question.features, similar_refs)
    
    confidence = (
        0.30 * (similarity_to_refs * 100) +           # How similar to reference?
        0.25 * (expected_pass_rate * 100) +           # What do similar Q's achieve?
        0.20 * validators["auto_grading"] +           # Can we actually grade?
        0.15 * validators["originality"] +            # Unique enough?
        0.10 * validators["format_compliance"]        # Well-formed?
    )
    
    return confidence
```

### Pseudo-Code Flow

```python
# In Orchestrator.run_generate():

# Load reference scores ONCE
reference_scores = load_reference_scores("evaluations/question.json")

# For each question:
for constraint in constraints:
    question = generate_question(constraint)
    
    # Validate
    validators = run_validators(question)
    
    # Score using learned confidence
    features = compute_features(question)
    similar_refs = find_similar_references(question, reference_scores)
    confidence = compute_learned_confidence(question, similar_refs, validators)
    
    # Save scores for future learning
    state_manager.save_question_score(run_id, question.id, {
        "confidence": confidence,
        "similar_refs": [r.id for r in similar_refs],
        "features": features,
        "validators": validators,
    })
    
    question.confidence = confidence
```

---

## 3. LLM CALL REDUCTION

### Changes Needed

**MdParserAgent:** Batch summarization
```python
# Before: summarize 1 section per LLM call
# After: summarize 5 sections per LLM call

sections = split_by_headers(md_text)
for i in range(0, len(sections), 5):
    batch = sections[i:i+5]
    summaries = llm.complete_json(
        user=f"Summarize these 5 sections in parallel:\n{format_batch(batch)}"
    )  # Returns dict with keys "section_0", "section_1", etc
```

**SkillPickerAgent:** Batch skill picks
```python
# Before: pick 1 skill per LLM call (for >2 candidates)
# After: batch pick 5 skills in one call

candidates_per_question = [...]  # 5 lists of candidates
batch_picks = llm.complete_json(
    user=f"Pick best skill for each of these 5 questions:\n{format_batch(...)}"
)
```

---

## 4. SKILL TAXONOMY & PREREQUISITES

### Data Structure

```python
class SkillGraph:
    def __init__(self):
        self.skills = {}  # name -> SkillNode
        self.edges = []   # (from_skill, to_skill) = prerequisite
    
    def add_skill(self, name, difficulty, bloom_level, section):
        self.skills[name] = SkillNode(name, difficulty, bloom_level, section)
    
    def add_prerequisite(self, skill_a, skill_b):
        """skill_a requires skill_b"""
        self.edges.append((skill_a, skill_b))
        # Validate no cycles
        assert not self.has_cycle(), "Skill prerequisites must be acyclic"
    
    def get_prerequisites(self, skill_name):
        """All skills that must be learned before this one"""
        visited = set()
        def dfs(skill, result):
            if skill in visited:
                return
            visited.add(skill)
            for dep in self._get_direct_deps(skill):
                result.add(dep)
                dfs(dep, result)
        
        result = set()
        dfs(skill_name, result)
        return result
    
    def validate_coverage(self, syllabus_skills, required_prerequisites):
        """Check if all prerequisites are in syllabus"""
        missing = required_prerequisites - set(syllabus_skills)
        return missing
```

### Building the Graph

```python
# From skills.yaml, add manual prerequisite definitions
skill_graph = SkillGraph()

for skill in skills:
    skill_graph.add_skill(skill.name, skill.difficulty_hint, skill.bloom_level, skill.section)

# Manual relationships (could be auto-inferred from skill names)
skill_graph.add_prerequisite("implement callback with error handling", "create subscriber node")
skill_graph.add_prerequisite("design launch file", "create publisher node")
skill_graph.add_prerequisite("design launch file", "create subscriber node")
```

### Validation

```python
# In generation loop:
question = generate(skill)
required_prerequisites = skill_graph.get_prerequisites(question.generation_skill)
missing_prerequisites = skill_graph.validate_coverage(request.syllabus, required_prerequisites)

if missing_prerequisites:
    question.has_prerequisite_violation = True
    question.missing_skills = missing_prerequisites
    question.confidence -= 10  # Penalize
```

---

## 5. PARALLELIZATION

### Parallel Markdown Processing

```python
from concurrent.futures import ThreadPoolExecutor

def parse_parallel(md_sections):
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Summarize in parallel
        summaries = {}
        futures = {}
        for section_name, text in md_sections.items():
            futures[section_name] = executor.submit(
                llm.complete,
                user=render_prompt("md_section_summariser.txt", section_text=text)
            )
        
        for section_name, future in futures.items():
            summaries[section_name] = future.result()
        
        # Extract skills in parallel
        skills_result = {}
        for section_name, summary in summaries.items():
            futures[section_name] = executor.submit(
                llm.complete_json,
                user=render_prompt("skill_extractor.txt", section_summary=summary)
            )
        
        for section_name, future in futures.items():
            skills_result[section_name] = future.result()
    
    return skills_result
```

### Parallel Question Generation

```python
# For auto mode (3 constraints) or manual mode with multiple constraints

def generate_parallel(constraints, all_skills):
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for idx, constraint in enumerate(constraints):
            # Skill picking
            skill_future = executor.submit(
                skill_picker.run,
                difficulty=constraint["difficulty"],
                bloom_level=constraint["bloom_level"],
                domain=constraint.get("domain", ""),
                all_skills=all_skills,
                already_generated=[]
            )
            
            # Question generation (depends on skill)
            skill_result = skill_future.result()
            skill = SkillEntry(**skill_result.payload["skill"])
            
            gen_future = executor.submit(
                generator._llm_question,
                skill=skill.skill,
                ...
            )
            
            futures[idx] = gen_future
        
        questions = []
        for idx, future in futures.items():
            questions.append(future.result())
    
    return questions
```

---

## Implementation Timeline

| Task | Effort | Dependencies | Start |
|---|---|---|---|
| State Persistence | 2 days | None | Day 1 |
| Learned Confidence | 3 days | State | Day 3 |
| LLM Call Reduction | 1 day | None | Day 1 (parallel) |
| Skill Taxonomy | 3 days | None | Day 1 (parallel) |
| Parallelization | 2 days | State + LLM reduction | Day 6 |
| **Total** | **~7 days** | | |

---

## Effort vs Impact

```
STATE PERSISTENCE: 2 days effort → enables everything (critical path)
LEARNED CONFIDENCE: 3 days → +1.5 rating points (worth it)
LLM REDUCTION: 1 day → 4.2x faster parse, 4x faster generation (worth it)
SKILL TAXONOMY: 3 days → +0.8 points (medium priority)
PARALLELIZATION: 2 days → 3x total speedup (worth it)
```

Total expected rating increase: **+1.5 + 0.8 = +2.3 points** → 6.5 + 2.3 = **8.8/10**

