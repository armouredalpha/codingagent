# SkillPickerAgent: Three Modes

The SkillPickerAgent now supports **3 distinct modes** for different use cases:

## 1️⃣ AUTO MODE (Recommended for Simple Use)

**Best for:** Instructors who just want "generate me some questions" without thinking about constraints.

**Command:**
```bash
robo-assess generate --md teaching.md --auto
```

**What it does:**
- System automatically generates exactly **3 questions**: 1 easy, 1 medium, 1 hard
- Ensures balanced difficulty distribution every single run
- SkillPickerAgent picks 3 skills matching each tier
- Perfect for balanced assessments

**Example Output:**
```
AUTO MODE: Generating 3 questions (easy, medium, hard) from teaching.md...
✓ Constraint 1 (easy/apply):
  SkillPickerAgent selected: "Load a Gazebo world SDF file"
  QuestionGeneratorAgent generated question
  Confidence: 87/100 → APPROVED

✓ Constraint 2 (medium/analyze):
  SkillPickerAgent selected: "Implement custom Gazebo sensor plugin"
  QuestionGeneratorAgent generated question
  Confidence: 89/100 → APPROVED

✓ Constraint 3 (hard/create):
  SkillPickerAgent selected: "Design physics simulation parameters"
  QuestionGeneratorAgent generated question
  Confidence: 91/100 → APPROVED

Output: outputs/run_a1b2c3d4/
```

### Auto Mode with Domain Hint
```bash
robo-assess generate --md teaching.md --auto --domain warehouse
```
Generates 3 questions all focused on warehouse domain.

---

## 2️⃣ MANUAL MODE (Full Control)

**Best for:** Instructors who want specific difficulty/bloom levels.

**Command:**
```bash
# Generate 1 easy/apply question
robo-assess generate --md teaching.md \
    --difficulty easy --bloom-level apply --num 1

# Generate 3 medium/analyze questions
robo-assess generate --md teaching.md \
    --difficulty medium --bloom-level analyze --num 3

# Generate 1 hard/create question for inspection domain
robo-assess generate --md teaching.md \
    --difficulty hard --bloom-level create --num 1 --domain inspection
```

**What it does:**
- User specifies **exactly** what they want
- SkillPickerAgent picks skills matching the constraint
- --num determines how many questions with same constraint

**Example Output:**
```
MANUAL MODE: Generating 3 medium/analyze questions from teaching.md...
✓ Question 1: medium/analyze
  SkillPickerAgent selected: "Write callback with error handling"
  Confidence: 86/100 → APPROVED

✓ Question 2: medium/analyze
  SkillPickerAgent selected: "Implement service with timeout logic"
  Confidence: 88/100 → APPROVED

✓ Question 3: medium/analyze
  SkillPickerAgent selected: "Debug node lifecycle issues"
  Confidence: 84/100 → REJECTED (regenerate needed)

Output: outputs/run_e5f6g7h8/ (2 approved, 1 rejected)
```

---

## 3️⃣ RANDOM MODE (Exploration)

**Best for:** Testing, generating large batches, exploring skill coverage.

**Command:**
```bash
# Generate 10 random-difficulty questions
robo-assess generate --md teaching.md --num 10

# Generate 5 random questions from warehouse domain
robo-assess generate --md teaching.md --num 5 --domain warehouse
```

**What it does:**
- System generates N random (difficulty, bloom_level) constraints
- SkillPickerAgent picks skills for each constraint
- Good for exploring what questions can be generated

**Example Output:**
```
RANDOM MODE: Generating 10 random questions from teaching.md...
✓ Question 1: easy/apply
  SkillPickerAgent selected: "Create basic publisher"
  Confidence: 85/100 → APPROVED

✓ Question 2: hard/evaluate
  SkillPickerAgent selected: "Compare two middleware approaches"
  Confidence: 92/100 → APPROVED

✓ Question 3: medium/analyze
  SkillPickerAgent selected: "Debug timing synchronization"
  Confidence: 81/100 → REJECTED

✓ Question 4: easy/understand
  SkillPickerAgent selected: "Identify ROS2 parameter usage"
  Confidence: 89/100 → APPROVED

... (7 more) ...

Output: outputs/run_i9j0k1l2/ (7 approved, 3 rejected)
```

---

## Comparison Table

| Feature | Auto Mode | Manual Mode | Random Mode |
|---------|-----------|-------------|-------------|
| **Use Case** | Quick balanced assessments | Specific requirements | Testing/exploration |
| **Questions Generated** | Always 3 (easy, medium, hard) | Exactly what you specify | N random |
| **Difficulty Distribution** | Guaranteed balanced | 100% user-controlled | Random mix |
| **Bloom Level** | Fixed (apply, analyze, create) | User-specified | Random |
| **Domain Flexibility** | Optional hint | Optional hint | Optional hint |
| **Command Simplicity** | Simplest (`--auto`) | More options | Simple (`--num N`) |
| **Use Frequency** | Recommended | For specific needs | For exploration |

---

## SkillPickerAgent Logic (All Modes)

In all three modes, SkillPickerAgent works the same way for each skill selection:

```
Input: difficulty, bloom_level, domain, all_skills, already_generated

1. Filter by difficulty (exact match preferred)
2. Filter by Bloom level (>= target OK)
3. Filter by domain (if specified)
4. If no candidates: relax constraints (difficulty-1)
5. If still no candidates: take any ungenerated
6. If ≤2 candidates: random pick
7. If >2 candidates: LLM picks best match
8. Return: selected skill + reasoning
```

---

## Real-World Workflows

### Workflow 1: Quick Assessment Creation (Auto Mode)
```bash
# Create a quick, balanced assessment
$ robo-assess parse --md docs/ROS2_fundamentals.md
$ robo-assess generate --md docs/ROS2_fundamentals.md --auto

→ 3 questions ready in minutes
  - 1 easy for confidence building
  - 1 medium for core competency
  - 1 hard for differentiation
```

### Workflow 2: Targeted Assessment (Manual Mode)
```bash
# Create an assessment targeting junior engineers
$ robo-assess parse --md docs/simulation.md
$ robo-assess generate --md docs/simulation.md \
    --difficulty easy --bloom-level apply --num 2 \
    --domain warehouse
$ robo-assess generate --md docs/simulation.md \
    --difficulty medium --bloom-level analyze --num 3 \
    --domain warehouse

→ 5 custom questions targeting:
  - Foundation building (2 easy)
  - Core competency (3 medium)
  - Warehouse domain focus
```

### Workflow 3: Comprehensive Skill Coverage (Random Mode)
```bash
# Generate many questions to explore all skills
$ robo-assess parse --md docs/comprehensive_ros2.md
$ robo-assess generate --md docs/comprehensive_ros2.md --num 20

→ 20 diverse questions
  - Random mix of difficulties
  - Explores all extracted skills
  - Useful for building question banks
```

---

## Behind the Scenes: SkillPickerAgent

The agent provides two methods:

### For Manual/Random Modes (single skill pick):
```python
agent.run(
    difficulty="easy",
    bloom_level="apply",
    domain="warehouse",
    all_skills=[...],
    already_generated=["skill1", "skill2"]
)
→ Returns: 1 selected skill
```

### For Auto Mode (batch pick 3 skills):
```python
agent.run_auto(
    all_skills=[...],
    domain="",  # optional
    already_generated=[]
)
→ Returns: 3 selected skills (easy, medium, hard)
```

---

## Tips for Best Results

✅ **Use Auto Mode** for simple, balanced assessments
✅ **Use Manual Mode** when you have specific learning objectives
✅ **Use Random Mode** to explore skill coverage before finalizing
✅ **Add --domain** hint to constrain questions to specific areas
✅ **Run multiple times** to get different questions (skill_picker varies selection)

❌ Don't mix modes in single run (pick one per invocation)
❌ Don't overthink constraints - skills are pre-extracted, system will handle it
❌ Don't worry about duplicates - originality check covers it

