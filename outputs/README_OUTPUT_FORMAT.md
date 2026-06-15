# Output Format Documentation

This directory contains example output files demonstrating the new detailed question format for the robotics assessment system.

## Files

### `question.json`
Complete detailed question specification in the new format.

**Contents:**
- **question_id**: Unique identifier for the question
- **metadata**: Rich contextual information
  - topic, difficulty_level, estimated_time_minutes
  - language, ros_version
  - concepts (list of tested concepts)
- **title**: Scenario-based, "twisty" title (not straightforward)
  - Example: "Dispatch the stuck delivery robot: Implement the fleet status query service"
  - NOT: "Implement a ROS2 service server"
- **context**: Detailed problem scenario (2-3 sentences)
- **scenario**: Real-world engineering situation
- **prerequisites**: Prior knowledge required
- **objective**: What the student must accomplish
- **constraints**: Specific limitations and requirements
- **tested_skills**: Learning objectives being assessed
- **common_mistakes**: 8+ common implementation errors to help students
- **parts**: Multi-part breakdown of the exercise (Part I, Part II, etc.)
- **tasks**: Flat task list (7-10 discrete steps)
- **file_structure**: 
  - ros_package: Package name
  - dependencies: Required ROS2 and Python packages
  - files_to_create: Explicit file specifications
- **starter_code**: Provided starter code blocks
  - Pre-filled boilerplate with TODO markers
  - Students only edit between # TODO START / # TODO END
- **expected_output**: Multiple expected output scenarios
  - Different shells (node startup, service calls, validation)
  - Exact output text showing success
- **run_commands**: Exact commands to execute and test
- **evaluation_criteria**: What makes a solution correct
  - nodes: Required ROS2 nodes
  - topics_subscribed: Input topics
  - topics_published: Output topics
  - services: Exposed services
  - publish_rate: Publishing frequency if applicable

**Example Question:**
"Dispatch the stuck delivery robot: Implement the fleet status query service"
- Medium difficulty, 30 minutes
- Requires understanding of ROS2 services + custom messages + callbacks
- Real scenario: fleet dispatch system cannot query robot status
- Multi-file implementation (node + service definition + config)

---

### `solution.json`
Complete reference implementation and grading specifications.

**Contents:**

#### Reference Solution
Complete working code for all files:
- **robot_status_node.py** (76 lines)
  - Service server implementation
  - Request/response handling
  - Integration with odometry subscriber
  
- **srv/RobotStatus.srv** (5 lines)
  - Custom service message definition
  - Fields: position_x, position_y, battery_percent, current_task
  
- **package.xml** (24 lines)
  - ROS2 package configuration
  - Message generation setup
  
- **setup.py** (29 lines)
  - Build configuration
  - Entry points

#### Testing Notes
- **how_to_test**: Step-by-step testing procedure
- **expected_behavior**: 6 behaviors to verify
- **common_issues_and_fixes**: Troubleshooting guide

#### Grading Criteria
**7 auto-gradable checks:**
1. Code compiles without errors
2. Service /robot_status is registered
3. Service has correct message type
4. Service responds to requests
5. Response fields have correct types
6. Battery percentage is valid (0-100)
7. Current task string is not empty

Each check includes:
- check_id: Unique identifier
- description: What is being tested
- method: How to test it
- expected: What success looks like

#### Learning Outcomes
6 learning outcomes the student should achieve:
- Custom ROS2 service message creation
- Request/response pattern understanding
- Service server callback implementation
- Multi-concept integration
- Package building and deployment
- Accessing node state from callbacks

#### Difficulty Justification
Explains why this is "medium" difficulty:
- Requires 3+ ROS2 concepts
- Multi-file setup (not just a single node)
- Integration of multiple systems

---

## Format Highlights

### What Makes This Format Better

1. **Scenario-Based Titles**
   - Describe *problems*, not solutions
   - Test deeper understanding
   - Example: "Bring X back online: implement Y service"

2. **Rich Context**
   - Real-world engineering scenarios
   - Constraints and objectives
   - Professional assessment experience

3. **Explicit Structure**
   - Package names, dependencies, files to create
   - No ambiguity about what to build
   - Clear file paths and roles

4. **Multiple Perspectives**
   - Expected outputs from different shells
   - Node startup, service calls, validation
   - Real testing scenarios

5. **Comprehensive Evaluation**
   - Auto-gradable checks with clear criteria
   - Common mistakes listed upfront
   - Testing procedures documented

6. **Learning Focused**
   - Learning outcomes explicit
   - Concepts tagged in metadata
   - Difficulty justified

---

## Comparison to Old Format

### Old Format Issues
- ❌ Generic titles ("Implement ROS2 Service")
- ❌ Minimal context
- ❌ Vague file structure
- ❌ Limited evaluation criteria
- ❌ No learning outcomes

### New Format Solutions
- ✅ Scenario-based, descriptive titles
- ✅ Rich, realistic context
- ✅ Explicit package structure
- ✅ 7+ auto-gradable checks
- ✅ Learning outcomes documented

---

## Using These Files

### For Instructors
1. **Understand the format**: Review how questions are structured
2. **Adapt for your curriculum**: Create similar questions with your learning outcomes
3. **Set up grading**: Use the auto-gradable checks as a template
4. **Track learning**: Use learning outcomes for assessment mapping

### For LLM Generation
1. **Template**: Use this as an example of expected output format
2. **Prompting**: Show this format to LLMs generating new questions
3. **Validation**: Check generated questions against this structure
4. **Refinement**: Iterate on question quality using these criteria

### For Students (Once Published)
1. **Clear expectations**: Title and context explain the problem
2. **Guided learning**: Tasks break down the solution into steps
3. **Self-assessment**: Common mistakes help identify their own errors
4. **Success criteria**: Expected outputs show what "done" looks like

---

## Schema Version

- **Version**: 1.0
- **Created**: 2026-06-13
- **Format**: JSON
- **Compatibility**: ROS2 Humble, rclpy, Python 3.10+
- **Question ID Pattern**: `Q{001+}_{skill}_{variation}`

---

## Next Steps

1. **Generate More Questions**: Use this as a template for LLM-based generation
2. **Validate Questions**: Check that auto-gradable checks actually work
3. **Test with Students**: Get feedback on clarity and difficulty
4. **Refine Grading**: Adjust criteria based on student submissions
5. **Scale to Curriculum**: Apply this format to all assessment questions

---

## File Locations

- Question specification: `/home/niat/claude_Ws/robotics-assessment-system/outputs/question.json`
- Reference solution: `/home/niat/claude_Ws/robotics-assessment-system/outputs/solution.json`
- Demo script: `/home/niat/claude_Ws/robotics-assessment-system/demo_detailed_format.py`
- Format documentation: `/home/niat/claude_Ws/robotics-assessment-system/DETAILED_FORMAT_CHANGES.md`
