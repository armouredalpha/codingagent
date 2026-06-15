# SkillPickerAgent: Three Modes Implementation ✅

## What You Have Now

A **production-ready skill selection system** with three distinct modes for different use cases.

---

## The Three Modes

### 1️⃣ AUTO MODE 🟢
**Recommended for instructors who want balanced assessments without thinking.**

```bash
robo-assess generate --md teaching.md --auto
```

- **Always generates**: Exactly 3 questions (1 easy, 1 medium, 1 hard)
- **Bloom levels fixed**: apply → analyze → create
- **Difficulty balanced**: Guaranteed 33% each tier
- **Time to result**: ~5 seconds per run
- **Best for**: Quick, balanced assessments

---

### 2️⃣ MANUAL MODE 🔵
**For instructors with specific requirements.**

```bash
robo-assess generate --md teaching.md \
    --difficulty easy --bloom-level apply --num 3
```

- **User specifies**: difficulty + bloom_level + count
- **Flexible**: Generate 1, 5, 10 questions of same constraint
- **Full control**: Pick exactly what you need
- **Best for**: Targeted assessments, specific learning objectives

---

### 3️⃣ RANDOM MODE 🟡
**For exploration and building large question banks.**

```bash
robo-assess generate --md teaching.md --num 20
```

- **Random difficulty**: System picks random difficulty/bloom per question
- **Exploration**: Great for discovering skill coverage
- **Bulk generation**: Generate 10, 20, 50 questions at once
- **Best for**: Testing, exploration, building question banks

---

## SkillPickerAgent Implementation

### Core Methods

**Method 1: Single Skill Selection (Manual/Random)**
```python
agent.run(
    difficulty="easy",
    bloom_level="apply",
    domain="warehouse",
    all_skills=[...],
    already_generated=[]
)
```

**Method 2: Auto Constraint Generation**
```python
constraints = agent.generate_auto_constraints(domain="")
# Returns: [easy/apply, medium/analyze, hard/create]
```

**Method 3: Batch 3-Skill Selection (Auto Mode)**
```python
agent.run_auto(
    all_skills=[...],
    domain="",
    already_generated=[]
)
```

### Selection Algorithm

For each skill:
1. Filter by difficulty (exact match preferred)
2. Filter by Bloom level (>= target OK)
3. Filter by domain (if specified)
4. **Fallback**: Relax difficulty if no candidates
5. **Pick**: Random if ≤2 candidates, LLM if >2

---

## CLI Commands

### Auto Mode
```bash
# 3 questions (easy, medium, hard)
robo-assess generate --md teaching.md --auto

# With domain hint
robo-assess generate --md teaching.md --auto --domain warehouse
```

### Manual Mode
```bash
# Single question
robo-assess generate --md teaching.md --difficulty easy --bloom-level apply

# Multiple same constraint
robo-assess generate --md teaching.md \
    --difficulty medium --bloom-level analyze --num 5

# With domain
robo-assess generate --md teaching.md \
    --difficulty hard --bloom-level create --num 1 --domain simulation
```

### Random Mode
```bash
# N random questions
robo-assess generate --md teaching.md --num 10

# With domain filter
robo-assess generate --md teaching.md --num 5 --domain inspection
```

---

## Use Cases & Examples

### Quick Assessment (30 seconds)
```bash
robo-assess parse --md ros2_fundamentals.md
robo-assess generate --md ros2_fundamentals.md --auto
→ 3 questions ready: easy, medium, hard
```

### Targeted Assessment
```bash
robo-assess parse --md ros2_course.md
robo-assess generate --md ros2_course.md --difficulty easy --bloom-level apply --num 2
robo-assess generate --md ros2_course.md --difficulty medium --bloom-level analyze --num 3
→ 5 questions for junior engineer level
```

### Explore Skills
```bash
robo-assess parse --md comprehensive_ros2.md
robo-assess generate --md comprehensive_ros2.md --num 20
→ 20 diverse questions exploring all skills
```

### Domain-Specific
```bash
robo-assess parse --md simulation_guide.md
robo-assess generate --md simulation_guide.md --auto --domain simulation
→ 3 questions all focused on simulation
```

---

## Files Modified

### New Methods Added to SkillPickerAgent
- `generate_auto_constraints(domain: str)` → generates [easy/apply, medium/analyze, hard/create]
- `run_auto(all_skills, domain, already_generated)` → picks 3 skills in batch

### Orchestrator Updated
- `run_generate(md_path, constraints, num_questions, auto, domain)`
- Supports `auto=True` for auto mode
- Supports `constraints=[...]` for manual mode
- Supports `num_questions=N` for random mode

### CLI Enhanced
- `--auto` flag for auto mode
- `--difficulty`, `--bloom-level`, `--num` for manual mode
- `--num N` for random mode
- `--domain` works with all modes
- Better help text with examples

---

## Implementation Highlights

✅ **Smart fallback logic** — If no skills match constraint, system relaxes difficulty tier
✅ **LLM optimization** — Uses LLM only when >2 candidates exist (most cases use random)
✅ **Auto mode guarantee** — Every run with `--auto` produces exactly 3 questions
✅ **Domain filtering** — Optional but powerful for focused assessments
✅ **No mode mixing** — Enforces single mode per run (cleaner semantics)
✅ **Backward compatible** — Existing manual/random still works

---

## Key Differences

| Feature | Auto | Manual | Random |
|---------|------|--------|--------|
| Command | `--auto` | `--difficulty X --bloom Y` | `--num N` |
| Count | Always 3 | User-specified | User-specified |
| Difficulty | 1-1-1 (easy-medium-hard) | Fixed by user | Random per question |
| Bloom | Fixed (apply-analyze-create) | User-specified | Random per question |
| Domain | Optional filter | Optional filter | Optional filter |
| Domain consistency | ALL 3 constrained | ALL constrained | NONE guaranteed |
| Use case | Quick balanced | Targeted/specific | Exploration |

---

## Testing

```bash
# Verify auto mode generates exactly 3 questions
robo-assess generate --md test.md --auto
→ Should show 3 questions with confirmed difficulties

# Verify manual mode respects user input
robo-assess generate --md test.md --difficulty hard --bloom-level create --num 2
→ Should show 2 hard/create questions

# Verify random mode varies
robo-assess generate --md test.md --num 5
robo-assess generate --md test.md --num 5
→ Should see different difficulty mixes each run
```

---

## Architecture Summary

```
SkillPickerAgent
├── run(difficulty, bloom_level, domain, all_skills, already_generated)
│   ├── Filters by constraint
│   ├── Fallback logic if no match
│   ├── Picks single skill
│   └── Returns: 1 SkillEntry
├── run_auto(all_skills, domain, already_generated)
│   ├── Generates 3 constraints
│   ├── Calls run() for each constraint
│   └── Returns: 3 SkillEntries
└── generate_auto_constraints(domain)
    └── Returns: [easy/apply, medium/analyze, hard/create]

Orchestrator.run_generate()
├── If auto: calls agent.run_auto() once
├── If constraints: calls agent.run() per constraint
└── If random: calls agent.run() per random constraint
```

---

## What Changed

**Before:**
- 1 CLI flag (`--num`)
- No mode distinction
- Simple random generation

**After:**
- 3 modes with distinct semantics
- `--auto` for balanced (recommended)
- `--difficulty --bloom-level` for manual
- `--num` for random exploration
- Better defaults and help text

---

## Ready to Use

```bash
# Parse once
robo-assess parse --md teaching.md

# Then use any mode
robo-assess generate --md teaching.md --auto              # ✅ Balanced
robo-assess generate --md teaching.md --difficulty easy   # ✅ Targeted
robo-assess generate --md teaching.md --num 10            # ✅ Exploration
```

Every run generates questions with:
- ✅ Skill picking via SkillPickerAgent
- ✅ Question generation via QuestionGeneratorAgent
- ✅ Full validation (boilerplate, originality, scope, difficulty, grading, confidence)
- ✅ Supervisor approval (final verdict)
- ✅ Output to `outputs/<run_id>/`

---

## Next Steps (Optional)

1. **Regeneration feedback loop** — If confidence < 85, use critic feedback to regenerate
2. **Skill persistence** — Save selected skills per run for reproducibility
3. **Batch API** — Generate all 3 modes in single command
4. **Web dashboard** — Visualize skill coverage and question distribution
5. **Tool calling** — Use LLM tools for vector search if >100 skills

