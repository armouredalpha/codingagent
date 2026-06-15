# Configuration

Configuration files for the Robotics Assessment System.

## Files

### `config.yaml`
Main configuration file for the system. Specifies:
- LLM provider and model
- Question generation parameters
- Quality bar settings
- Execution parameters (concurrency, timeouts)
- Paths to data directories

## Usage

```python
from robo_assess.config import Settings

settings = Settings.load()  # Loads from config.yaml
```

### Environment Variables

You can override any setting with environment variables using the `ROBO_` prefix:

```bash
export ROBO_PROVIDER=anthropic
export ROBO_MODEL=claude-sonnet-4-6
export ROBO_MAX_QUESTIONS=20
```

See `robo_assess/config.py` for the complete list of available settings.

## Examples

### Development (Fast, Cheap)
```yaml
provider: openrouter
model: gpt-4o-mini
max_planner_steps: 4
max_regeneration_attempts: 1
```

### Production (Quality)
```yaml
provider: anthropic
model: claude-sonnet-4-6
max_planner_steps: 8
max_regeneration_attempts: 2
quality_bar:
  min_confidence: 85
  require_discriminating: true
  require_judge_approve: true
```

### Research (Thorough)
```yaml
provider: anthropic
model: claude-opus-4-8
max_planner_steps: 8
max_regeneration_attempts: 3
generation_concurrency: 8
enable_llm_judge: true
```
