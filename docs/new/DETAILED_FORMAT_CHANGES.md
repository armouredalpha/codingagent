# Detailed Question Format Refactor

## Overview
The robotics assessment system has been upgraded to generate questions in a comprehensive, detailed format that matches the structure defined in `evaluations/question.json`. This provides richer context, clearer evaluation criteria, and more realistic assessment scenarios.

## Key Changes

### 1. New Schema Models (schemas.py)

Added the following Pydantic models to support the detailed format:

- **QuestionMetadata**: Structured metadata including topic, difficulty level, estimated time, language, ROS version, and concepts
- **FileStructure**: Package and dependency specifications with detailed file creation instructions  
- **FileToCreate**: Individual file specifications with path and role descriptions
- **Part**: Multi-part question sections for more complex exercises
- **ExpectedOutput**: Structured expected output with shell context (e.g., "Shell #1", "Shell #2 (service call)")
- **EvaluationCriteria**: Detailed evaluation specification (nodes, topics subscribed/published, services, publish rate)
- **StarterCodeBlock**: Starter code files provided to students

### 2. Extended Question Schema

The `Question` model now includes:
- `metadata: QuestionMetadata` - Rich metadata about the question
- `context: str` - Detailed problem scenario
- `prerequisites: list[str]` - Prior exercises or knowledge required
- `notes: Optional[str]` - Setup hints and important details
- `parts: list[Part]` - For multi-part questions
- `tasks: list[str]` - Flat task list or detailed breakdown
- `file_structure: FileStructure` - Package and file specifications
- `starter_code_list: list[StarterCodeBlock]` - Starter code files
- `expected_output: list[ExpectedOutput]` - Expected outputs from different shells
- `run_commands: list[str]` - Commands to execute the solution
- `detailed_evaluation_criteria: EvaluationCriteria` - Executable testing requirements

### 3. New Detailed Prompt Template

Created `prompts/question_generator_detailed.txt` with:

**Key Principles:**
- **Scenario-based, "twisty" titles** (not straightforward implementations)
  - ❌ Bad: "Implement a ROS2 publisher"
  - ✅ Good: "Troubleshoot the silent conveyor belt status system"
  
- **Rich context** including realistic engineering scenarios and constraints

- **Structured metadata** with concepts and learning outcomes

- **Detailed file structure** with explicit dependencies and file creation instructions

- **Multiple expected outputs** showing different shells/scenarios

- **Explicit run commands** for solution validation

- **Comprehensive evaluation criteria** defining what makes a solution correct

### 4. Updated Question Generator

Modified `question_generator.py` to:

- Load the detailed prompt template by default
- Parse the new detailed JSON structure
- Populate all new schema fields
- Generate scenario-based, "twisty" titles
- Support both legacy and detailed formats (backward compatible)

## Example Question

### Title (Scenario-Based)
"Bring the silent assembly station back online: Wire up the parts verification service"

### Context
A manufacturing facility has an automated assembly line. Station 3's parts verification service is offline because the service handler was never implemented. The node already subscribes to sensor data; you only implement the service response logic.

### Detailed Breakdown
- **Metadata**: Topic, difficulty, estimated time, concepts
- **Prerequisites**: List of prior exercises
- **Tasks**: 7-8 specific implementation steps
- **File Structure**: Package name, dependencies, files to create
- **Expected Outputs**: Multiple shells showing successful test scenarios
- **Run Commands**: Exact commands to execute and test
- **Evaluation Criteria**: Nodes, topics, services, publish rates to verify
- **Common Mistakes**: 4+ common implementation errors

## Benefits

1. **Clarity**: Students understand the real-world context and why they're solving this problem
2. **Executability**: Detailed file structure and run commands make testing unambiguous
3. **Testability**: Explicit evaluation criteria enable automated verification
4. **Realism**: Scenario-based titles and context reflect actual engineering work
5. **Backward Compatibility**: Legacy fields preserved for existing validation agents

## Testing

Run the demo to see the new format:
```bash
python3 demo_detailed_format.py
```

## Migration Path

Existing questions and agents continue to work because:
- New fields are optional with sensible defaults
- Legacy evaluation_criteria still supported
- Backward-compatible JSON parsing in question generator
- Downstream agents (validators, graders) work with extended schema

## Next Steps

1. ✅ Schema updates complete
2. ✅ Prompt template created
3. ✅ Question generator refactored
4. ⏳ Run full end-to-end test with real LLM
5. ⏳ Update validation agents for new fields
6. ⏳ Update grading agents for detailed criteria
7. ⏳ Export questions to evaluations/question.json format

## File Changes

- `robo_assess/schemas.py` - Added 9 new schema classes
- `robo_assess/agents/question_generator.py` - Updated prompt loading, JSON parsing, field population
- `prompts/question_generator_detailed.txt` - New comprehensive prompt template
- `demo_detailed_format.py` - Demonstration of the new format
