# Guardrails

This folder contains all guardrail definitions for the assessment system.
Nothing in here touches generation logic — it is pure configuration and reference data.

## Files

### Core (validity — pass/fail)
| File | Purpose |
|---|---|
| `guardrail_rules.yaml` | All numeric thresholds and rule definitions per agent |
| `rejection_patterns.yaml` | String patterns that trigger automatic rejection |
| `construct_benchmark.jsonl` | Construct reference questions used as quality benchmark |

### Quality (excellence — what makes a question *great*)
| File | Purpose |
|---|---|
| `quality_guardrails.yaml` | Craftsmanship bar: solvability, scaffolding, grading fairness, clarity, runnability, realistic framing |
| `pedagogical_guardrails.yaml` | Learning science: Bloom alignment, cognitive load, desirable difficulty, misconception targeting |
| `ros2_correctness_guardrails.yaml` | Domain truth: valid message fields, rclpy idioms, QoS, TF2 conventions, package structure |
| `batch_diversity_guardrails.yaml` | Set-level quality: skill spread, difficulty balance, domain/interface variety, portfolio completeness |

### Severity levels used across quality files
- **REJECT** — hard fail; question is regenerated.
- **WARN** — flagged; recalibrated or surfaced to supervisor.
- **SCORE** — contributes to a 0-100 craftsmanship score (see `quality_guardrails.yaml`).

## How Guardrails Map to Agents

```
guardrail_rules.yaml
  └── boilerplate     → robo_assess/agents/boilerplate_generator.py
  └── scope           → robo_assess/agents/scope_agent.py
  └── originality     → robo_assess/agents/originality_agent.py
  └── difficulty      → robo_assess/agents/difficulty_agent.py
  └── realism         → robo_assess/agents/realism_agent.py
  └── grading         → robo_assess/agents/grading_agent.py
  └── confidence      → robo_assess/agents/confidence_agent.py
  └── supervisor      → robo_assess/agents/supervisor.py

rejection_patterns.yaml
  └── used by         → robo_assess/agents/boilerplate_generator.py (future)

construct_benchmark.jsonl
  └── used by         → robo_assess/evaluators/dataset_evaluator.py
```

## To Add a New Guardrail

1. Add the rule definition to `guardrail_rules.yaml`
2. Add rejection patterns to `rejection_patterns.yaml` if needed
3. Implement enforcement in the relevant agent file
4. Add test cases to `datasets/` matching the new rule

## To Tune Thresholds

Edit `guardrail_rules.yaml` AND `config.yaml` — the agent reads from `config.yaml`
at runtime. `guardrail_rules.yaml` is the human-readable source of truth.
