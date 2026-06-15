# Quick Start: Run the Agent

## Setup
```bash
export OPENROUTER_API_KEY="your-key-here"
# OR
export ANTHROPIC_API_KEY="your-key-here"
```

## 1. Parse Skills (Required First)
```bash
python3 -m robo_assess.cli parse --md "configs/Robotics & AI Coding Assessment- LINUX & ROS2 Fundamentals.md"
```
Extracts skills from markdown into `skills/skills.yaml`.

## 2. Generate Questions - AUTO MODE
```bash
python3 -m robo_assess.cli generate --md "configs/Robotics & AI Coding Assessment- LINUX & ROS2 Fundamentals.md" --auto
```
Generates 3 questions automatically (1 easy, 1 medium, 1 hard).

## 3. Generate Questions - MANUAL MODE
```bash
python3 -m robo_assess.cli generate --md "configs/Robotics & AI Coding Assessment- LINUX & ROS2 Fundamentals.md" --difficulty easy --bloom-level apply --num 2
```
Generates N questions with specific difficulty/bloom level. Pick from: `easy|medium|hard` and `understand|apply|analyze|evaluate|create`.

## 4. View Results
```bash
ls -la outputs/
cat outputs/*/summary.json
```
