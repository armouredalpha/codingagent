# Automated Question Generation Guide

## Overview

The `generate_questions.py` script automatically generates assessment questions in the detailed format and saves them in timestamped folders following the schema:

```
outputs/YYYY-MM-DD_HH-MM-SS_questions_N/
├── easy/question.json + solution.json
├── medium/question.json + solution.json
├── hard/question.json + solution.json
├── INDEX.md
└── QUICK_START.md
```

## Usage

### Basic Generation (1 easy, 1 medium, 1 hard)

```bash
python3 generate_questions.py
```

**Output folder created:** `outputs/2026-06-13_23-50-00_questions_3/`

### Generate 6 Questions (2 easy, 2 medium, 2 hard)

```bash
python3 generate_questions.py --easy 2 --medium 2 --hard 2
```

### Generate Specific Combinations

```bash
# 3 easy, 0 medium, 0 hard
python3 generate_questions.py --easy 3

# 1 easy, 3 medium, 2 hard
python3 generate_questions.py --easy 1 --medium 3 --hard 2

# 10 total (equal distribution)
python3 generate_questions.py --easy 4 --medium 3 --hard 3
```

## What Gets Generated

### For Each Question:
- ✅ **question.json** - Complete question specification with:
  - Metadata (topic, concepts, difficulty, time)
  - Scenario-based title
  - Rich context and objectives
  - File structure (package, dependencies, files)
  - Starter code with TODO markers
  - Expected outputs (multiple scenarios)
  - Run commands
  - Evaluation criteria

- ✅ **solution.json** - Reference implementation with:
  - Complete working code (all files)
  - Testing procedures
  - Auto-gradable checks (5-8 per question)
  - Learning outcomes
  - Troubleshooting guide

### Bonus Files:
- ✅ **INDEX.md** - Package overview and guide
- ✅ **QUICK_START.md** - Quick reference

## Output Folder Schema

Each generation creates a **unique timestamped folder**:

```
Naming: YYYY-MM-DD_HH-MM-SS_questions_N

Example: 2026-06-13_23-45-12_questions_3
         └─ 2026-06-13 = Date
         └─ 23-45-12 = Time (HH-MM-SS)
         └─ 3 = Total question count
```

**Benefit:** Each generation is isolated and timestamped, preventing overwrites.

## Folder Structure

```
outputs/
├── 2026-06-13_23-45-12_questions_3/
│   ├── easy/
│   │   ├── question.json (5.8 KB)
│   │   └── solution.json (4.2 KB)
│   ├── medium/
│   │   ├── question.json (7.3 KB)
│   │   └── solution.json (6.3 KB)
│   ├── hard/
│   │   ├── question.json (9.3 KB)
│   │   └── solution.json (8.2 KB)
│   ├── INDEX.md
│   └── QUICK_START.md
│
├── 2026-06-14_10-15-30_questions_6/  ← Next generation
│   ├── easy/...
│   ├── medium/...
│   ├── hard/...
│   ├── INDEX.md
│   └── QUICK_START.md
│
└── ... (more generations)
```

## Examples

### Example 1: Generate 3 Questions (Default)

```bash
$ python3 generate_questions.py

================================================================================
GENERATING 3 QUESTIONS
================================================================================

✓ Created: outputs/2026-06-13_23-52-45_questions_3

Generating questions...
  Generating Easy Question #1...
  Generating Medium Question #2...
  Generating Hard Question #3...

Creating documentation...
  Creating INDEX.md...
  Creating QUICK_START.md...

✓ Validating JSON files...
  ✓ easy       - Q: 5,840 bytes, S: 4,177 bytes
  ✓ medium     - Q: 7,298 bytes, S: 6,324 bytes
  ✓ hard       - Q: 9,263 bytes, S: 8,180 bytes

================================================================================
✅ SUCCESSFULLY GENERATED 3 QUESTIONS
================================================================================

📂 Output folder: outputs/2026-06-13_23-52-45_questions_3

✨ Ready to use! All files validated.
```

### Example 2: Generate 10 Questions (Various Difficulties)

```bash
$ python3 generate_questions.py --easy 4 --medium 3 --hard 3

================================================================================
GENERATING 10 QUESTIONS
================================================================================

✓ Created: outputs/2026-06-13_23-55-00_questions_10

Generating questions...
  Generating Easy Question #1...
  Generating Easy Question #2...
  Generating Easy Question #3...
  Generating Easy Question #4...
  Generating Medium Question #5...
  Generating Medium Question #6...
  Generating Medium Question #7...
  Generating Hard Question #8...
  Generating Hard Question #9...
  Generating Hard Question #10...

Creating documentation...
  Creating INDEX.md...
  Creating QUICK_START.md...

✓ Validating JSON files...
  ✓ easy       - Q: 5,840 bytes, S: 4,177 bytes
  ✓ medium     - Q: 7,298 bytes, S: 6,324 bytes
  ✓ hard       - Q: 9,263 bytes, S: 8,180 bytes

================================================================================
✅ SUCCESSFULLY GENERATED 10 QUESTIONS
================================================================================

📂 Output folder: outputs/2026-06-13_23-55-00_questions_10

✨ Ready to use! All files validated.
```

## Accessing Generated Questions

### View Generated Folder

```bash
# List all generated packages
ls -la outputs/ | grep "^d"

# List contents of latest generation
ls -la outputs/2026-06-13_23-52-45_questions_3/
```

### Read a Question

```bash
# View easy question
cat outputs/2026-06-13_23-52-45_questions_3/easy/question.json | python -m json.tool | less

# View with prettier formatting
python3 << 'EOF'
import json
with open('outputs/2026-06-13_23-52-45_questions_3/easy/question.json') as f:
    q = json.load(f)
print(f"Title: {q['title']}")
print(f"Difficulty: {q['metadata']['difficulty_level']}")
print(f"Time: {q['metadata']['estimated_time_minutes']} min")
print(f"Concepts: {', '.join(q['metadata']['concepts'])}")
EOF
```

### Copy to Your System

```bash
# Copy a specific question folder
cp -r outputs/2026-06-13_23-52-45_questions_3/easy ~/my-assessments/

# Copy all latest questions
cp -r outputs/2026-06-13_23-52-45_questions_3/* ~/my-assessments/

# Copy to LMS
cp outputs/2026-06-13_23-52-45_questions_3/*/question.json ~/canvas-import/
```

## Question Contents

Each `question.json` includes:

```json
{
  "question_id": "Q001_...",
  "metadata": { ... },
  "title": "Scenario-based title",
  "context": "Real-world problem...",
  "objective": "What to accomplish",
  "constraints": ["Requirement 1", ...],
  "tested_skills": ["Skill 1", ...],
  "common_mistakes": ["Mistake 1", ...],
  "tasks": ["Task 1", ...],
  "file_structure": { "ros_package": "...", ... },
  "starter_code": [ { "filename": "...", "content": "..." } ],
  "expected_output": [ { "shell": "...", "output": "..." } ],
  "run_commands": ["ros2 run ...", ...],
  "evaluation_criteria": { ... }
}
```

Each `solution.json` includes:

```json
{
  "question_id": "Q001_...",
  "reference_solution": { ... complete working code ... },
  "testing_notes": { ... },
  "grading_criteria": { "auto_gradable_checks": [...] },
  "learning_outcomes": [...],
  "difficulty_justification": {...}
}
```

## Customization

### Modify Question Content

Edit `generate_questions.py` templates:

- **EASY_QUESTION_TEMPLATE** (lines ~50-150)
- **MEDIUM_QUESTION_TEMPLATE** (lines ~150-250)
- **HARD_QUESTION_TEMPLATE** (lines ~250-350)

Update:
- Title template
- Context/scenario
- Concepts
- Constraints
- Common mistakes

### Generate Different Topics

Replace template text in the generation functions:
- `generate_easy_question()`
- `generate_medium_question()`
- `generate_hard_question()`

### Add More Difficulties

Duplicate a function and modify:
1. Copy `generate_easy_question()`
2. Rename to `generate_advanced_question()`
3. Update content
4. Add to main generation loop

## Batch Generation

### Generate Multiple Packages

```bash
#!/bin/bash
# Generate 3 packages of 3 questions each
for i in {1..3}; do
    echo "Generating package $i..."
    python3 generate_questions.py --easy 1 --medium 1 --hard 1
    sleep 1  # Ensure unique timestamps
done

echo "✓ Generated 3 packages (9 total questions)"
ls -la outputs/ | grep "questions_3"
```

## Validation

All generated questions are automatically validated:
- ✅ JSON syntax
- ✅ Required fields present
- ✅ Proper structure
- ✅ File accessibility

## Troubleshooting

### Script not executable?

```bash
chmod +x generate_questions.py
python3 generate_questions.py
```

### Permission denied?

```bash
# Run with python directly
python3 /full/path/to/generate_questions.py

# Or run from correct directory
cd /home/niat/claude_Ws/robotics-assessment-system/
python3 generate_questions.py
```

### Output folder not created?

```bash
# Check outputs directory exists
mkdir -p outputs/

# Check permissions
ls -la outputs/

# Run script again
python3 generate_questions.py
```

## Integration

### With LMS

```bash
# Export all latest questions as JSON
cat outputs/$(ls -t outputs | head -1)/*/*/question.json > import.jsonl
```

### With Assessment System

```python
import json
from pathlib import Path

# Load all questions from latest generation
base = Path("outputs").glob("*_questions_*")
latest = sorted(base)[-1]

for difficulty in ["easy", "medium", "hard"]:
    q_file = latest / difficulty / "question.json"
    s_file = latest / difficulty / "solution.json"
    
    with open(q_file) as f:
        question = json.load(f)
    with open(s_file) as f:
        solution = json.load(f)
    
    # Process questions...
```

## Support

- **Questions about format?** See `DETAILED_FORMAT_CHANGES.md`
- **Quick reference?** See `QUICK_START.md` in generated folder
- **Full guide?** See `INDEX.md` in generated folder

---

**Ready to generate questions!** Run the script and get started. 🚀
