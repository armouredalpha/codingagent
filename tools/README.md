# Tools

Utility scripts and analysis tools for the Robotics Assessment System.

## Scripts

### `analyze_confidence.py`
Analyzes and validates the confidence scoring system using reference question data.

**Usage:**
```bash
python tools/analyze_confidence.py [--reference-file evaluations/question.json] [--output report.json]
```

**What it does:**
- Loads reference questions with known student pass rates
- Compares predicted vs actual pass rates
- Computes calibration metrics (MAE, RMSE, Pearson correlation)
- Generates calibration multipliers for difficulty levels
- Produces detailed analysis report

**Output:**
- Console summary with key metrics
- JSON report with per-question analysis
- Calibration multiplier table

**Example:**
```bash
python tools/analyze_confidence.py
# Outputs: CONFIDENCE_SCORE_REPORT.md + analysis results
```

## Running Analysis

1. **Generate reference questions** (manually or via system)
   ```bash
   robo-assess generate --topic "ROS2 Basics" --num-questions 30
   ```

2. **Collect student attempts** (populated by grader)
   - Each reference question tracks pass/fail for students
   - Data lives in `evaluations/question.json`

3. **Run analysis**
   ```bash
   python tools/analyze_confidence.py
   ```

4. **Review report**
   - Check `CONFIDENCE_SCORE_REPORT.md` for findings
   - Look for systematic bias (easy vs hard questions)
   - Apply calibration multipliers to improve accuracy

## Adding New Tools

1. Place script in this directory
2. Add docstring explaining purpose
3. Include `--help` argument handling
4. Document in this README
5. Update `pyproject.toml` if it should be a CLI command

## Tool Requirements

All tools should:
- Have clear input/output documentation
- Support `--help` flag
- Log progress to stdout
- Return exit code 0 on success, non-zero on error
- Be idempotent (safe to run multiple times)
