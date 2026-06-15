# SkillPickerAgent: Quick Reference

## Three Modes at a Glance

```bash
# 🟢 AUTO MODE: Generate 3 balanced questions (easy, medium, hard)
robo-assess generate --md teaching.md --auto

# 🔵 MANUAL MODE: User-specified constraints
robo-assess generate --md teaching.md --difficulty easy --bloom-level apply --num 1

# 🟡 RANDOM MODE: N random difficulty questions
robo-assess generate --md teaching.md --num 10
```

---

## Command Reference

### Parse (Required first step)
```bash
robo-assess parse --md teaching.md
# Output: skills/skills.yaml + meta.yaml
```

### Auto Mode (Simplest)
```bash
robo-assess generate --md teaching.md --auto
# Generates: 1 easy + 1 medium + 1 hard (total: 3 questions)

robo-assess generate --md teaching.md --auto --domain warehouse
# Same but filtered to warehouse domain
```

### Manual Mode (Full Control)
```bash
# Single constraint
robo-assess generate --md teaching.md --difficulty easy --bloom-level apply

# Repeat same constraint N times
robo-assess generate --md teaching.md \
    --difficulty medium --bloom-level analyze --num 5

# With domain filter
robo-assess generate --md teaching.md \
    --difficulty hard --bloom-level create --num 1 --domain simulation
```

### Random Mode (Exploration)
```bash
# N random questions
robo-assess generate --md teaching.md --num 10

# With domain hint
robo-assess generate --md teaching.md --num 5 --domain inspection
```

---

## Bloom Levels (For Manual Mode)

- `understand` — Knowledge recall, basic comprehension
- `apply` — Use knowledge in new situations
- `analyze` — Break down and examine
- `evaluate` — Judge and justify
- `create` — Build something new

**Auto Mode mapping:**
- Easy → `apply`
- Medium → `analyze`
- Hard → `create`

---

## SkillPickerAgent API

### Method 1: Pick single skill (Manual/Random)
```python
from robo_assess.agents.skill_picker import SkillPickerAgent

agent.run(
    difficulty="easy",
    bloom_level="apply",
    domain="warehouse",
    all_skills=[...],  # from skills.yaml
    already_generated=[]
)
# Returns: AgentResult with selected_skill
```

### Method 2: Auto-generate 3 constraints
```python
constraints = agent.generate_auto_constraints(domain="")
# Returns: [
#   {"difficulty": "easy", "bloom_level": "apply", ...},
#   {"difficulty": "medium", "bloom_level": "analyze", ...},
#   {"difficulty": "hard", "bloom_level": "create", ...}
# ]
```

### Method 3: Pick 3 skills (Auto Mode)
```python
agent.run_auto(
    all_skills=[...],
    domain="",
    already_generated=[]
)
# Returns: AgentResult with 3 selected skills
```

---

## How SkillPickerAgent Picks

For each skill selection:
1. **Filter by difficulty** (exact match first)
2. **Filter by Bloom level** (>= target OK)
3. **Filter by domain** (if specified, optional)
4. **Fallback logic:**
   - No matches? Relax difficulty (easy → medium → hard)
   - Still no matches? Take any ungenerated skill
5. **Pick algorithm:**
   - ≤2 candidates: Random pick
   - >2 candidates: LLM picks best match

---

## Examples by Use Case

### Use Case 1: Create Quick Assessment
```bash
robo-assess parse --md ros2_fundamentals.md
robo-assess generate --md ros2_fundamentals.md --auto
# Done in 30 seconds: 3 balanced questions ready
```

### Use Case 2: Targeted Junior Engineer Assessment
```bash
robo-assess parse --md ros2_course.md
robo-assess generate --md ros2_course.md \
    --difficulty easy --bloom-level apply --num 2
robo-assess generate --md ros2_course.md \
    --difficulty medium --bloom-level analyze --num 3
# Result: 5 questions targeting junior level
```

### Use Case 3: Explore All Extracted Skills
```bash
robo-assess parse --md comprehensive_ros2.md
robo-assess generate --md comprehensive_ros2.md --num 20
# Result: 20 random questions exploring all skills
```

### Use Case 4: Domain-Specific Assessment
```bash
robo-assess parse --md simulation_guide.md
robo-assess generate --md simulation_guide.md --auto --domain simulation
# Result: 3 questions all focused on simulation
```

---

## Output Structure

```
outputs/<run_id>/
├── package.json                    # Full assessment metadata
├── confidence_report.json          # Per-question confidence scores
├── questions/
│   ├── Q001_<title>/
│   │   ├── question.json          # Question spec
│   │   ├── starter/               # Candidate code (TODO blocks)
│   │   ├── solution/              # Reference solution
│   │   └── grading.json           # Evaluation criteria
│   ├── Q002_<title>/
│   │   └── ...
│   └── Q003_<title>/
│       └── ...
└── evaluation_report.json         # Overall batch evaluation
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Skills not extracted" | Run `robo-assess parse --md file.md` first |
| "No skills available" | Check --domain filter, try wider constraints |
| Low confidence scores | Increase Bloom level, specific domain helps |
| Duplicate questions | Run multiple times, system varies selections |
| Want 5 questions total | Use `--auto` (3) + manual (2) or `--num 5` in random mode |

---

## Key Differences from Manual to Auto

| Aspect | Manual | Auto |
|--------|--------|------|
| Command | `--difficulty X --bloom-level Y` | `--auto` |
| Questions | User-controlled count | Always 3 |
| Difficulty | What user specifies | Balanced (1-1-1) |
| Bloom | User picks | Fixed (apply-analyze-create) |
| Domain | Optional filter | Optional filter |
| Best for | Targeted assessments | Quick balanced assessments |

---

## Tips & Tricks

✅ **Faster iterations:** Use auto mode first, then manual mode for refinement
✅ **Better variety:** Run multiple times (system varies skill picks)
✅ **Domain focus:** Add `--domain warehouse` to filter questions
✅ **Explore skills:** Use random mode with high --num to see what's available
✅ **Combine runs:** `--auto` three times = 9 questions = full bank

❌ **Avoid:** Mixing modes in one run (pick one per command)
❌ **Avoid:** Over-constraining (if too specific, relax domain or difficulty)

