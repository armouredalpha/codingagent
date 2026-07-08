"""
robo_assess.tools.registry
==========================

Anthropic/OpenAI-compatible tool schemas that agents can pass to
LLMClient.complete_with_tools().  Each entry is a dict accepted verbatim by
both the Anthropic SDK (type/name/description/input_schema) and the OpenAI SDK
(type/function.name/function.description/function.parameters).

ToolRegistry wraps the schemas + handler callables and routes tool_use blocks
from the LLM response to the right handler automatically.
"""

from __future__ import annotations

from typing import Any, Callable

# ---------------------------------------------------------------------------
# Canonical tool schema list
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "check_similarity",
        "description": (
            "Check how similar a question text is to previously generated questions "
            "in the vectorstore. Returns a similarity score (0-1) and the closest "
            "matching question title. Use before committing to a question to catch "
            "near-duplicate content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question_text": {
                    "type": "string",
                    "description": "The full question stem / scenario text to check.",
                },
            },
            "required": ["question_text"],
        },
    },
    {
        "name": "validate_guardrails",
        "description": (
            "Run the boilerplate, scope, originality, and difficulty guardrail checks "
            "against a partial question spec. Returns a list of passing and failing "
            "checks so you can fix issues before finalising the question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "solution_loc": {
                    "type": "integer",
                    "description": "Estimated lines of code in the reference solution.",
                },
                "tested_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills this question tests.",
                },
                "uses_technologies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ROS2 packages/libraries the question requires (e.g. nav2_msgs).",
                },
            },
            "required": ["title", "difficulty"],
        },
    },
    {
        "name": "query_skill_graph",
        "description": (
            "Query the skill prerequisite graph. "
            "query_type='prerequisites' returns all skills that must be known before "
            "this one. query_type='dependents' returns skills that build on this one. "
            "query_type='curriculum_path' returns an ordered learning sequence for a "
            "list of skills. query_type='validate_coverage' checks whether all "
            "prerequisites of the target skill are present in the current syllabus."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["prerequisites", "dependents", "curriculum_path", "validate_coverage"],
                },
                "skill_name": {
                    "type": "string",
                    "description": "Primary skill to query (not needed for curriculum_path).",
                },
                "skills_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "For curriculum_path: skills to sequence. "
                                   "For validate_coverage: the current syllabus skill list.",
                },
            },
            "required": ["query_type"],
        },
    },
    {
        "name": "estimate_difficulty",
        "description": (
            "Estimate the difficulty tier (easy/medium/hard) of a Python solution "
            "by analysing its lines-of-code count, cyclomatic complexity, and ROS2 "
            "API surface. Use when you want to verify that your generated solution "
            "matches the requested difficulty before submitting."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "solution_code": {
                    "type": "string",
                    "description": "Reference solution Python source code.",
                },
                "declared_difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                },
            },
            "required": ["solution_code", "declared_difficulty"],
        },
    },
    {
        "name": "check_scope_compliance",
        "description": (
            "Check whether a question uses any gated (forbidden) technologies such as "
            "Nav2, SLAM, MoveIt, or OpenCV. Returns a list of violations and whether "
            "the question passes scope rules."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question_text": {"type": "string"},
                "solution_code": {"type": "string", "description": "Optional — also scan solution."},
                "allowed_scope": {
                    "type": "string",
                    "description": "Comma-separated list of allowed concepts/packages.",
                },
            },
            "required": ["question_text"],
        },
    },
    {
        "name": "fetch_ros2_docs",
        "description": (
            "Fetch live ROS2 / Python library documentation from GitHub. "
            "Use when you need accurate API signatures, parameter names, or message "
            "field names for rclpy, geometry_msgs, sensor_msgs, tf2_ros, etc. "
            "Returns README / API docs so your generated code references real APIs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "library_name": {
                    "type": "string",
                    "description": "Library name, e.g. 'rclpy', 'geometry_msgs', 'tf2_ros', 'numpy'.",
                },
                "query": {
                    "type": "string",
                    "description": "Specific API or concept to look up within the library.",
                },
            },
            "required": ["library_name", "query"],
        },
    },
    {
        "name": "compute_confidence",
        "description": (
            "Compute the multi-dimension confidence score for a question. "
            "Returns the weighted total (threshold 85 for APPROVED) and a breakdown "
            "across coverage, difficulty, originality, scope, auto-grading, and format "
            "dimensions. Use to predict whether a question will pass the confidence gate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question_id": {"type": "string"},
                "auto_grading_score": {"type": "number", "minimum": 0, "maximum": 100},
                "originality_score": {"type": "number", "minimum": 0, "maximum": 100},
                "format_quality_score": {"type": "number", "minimum": 0, "maximum": 100},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "coverage_pct": {
                    "type": "number",
                    "description": "Current syllabus coverage percentage (0-100).",
                },
            },
            "required": ["auto_grading_score", "originality_score", "format_quality_score", "difficulty"],
        },
    },
    {
        "name": "search_course_exercises",
        "description": (
            "Search for similar programming exercises from top robotics courses "
            "(ETH Zurich RSL, ROS2 Official Tutorials, The Construct, ros2/examples). "
            "Use this to find real-world exercise patterns for the topic you are generating, "
            "so your question reflects authentic course difficulty and structure. "
            "Returns titles, descriptions, difficulty labels, skill tags, and source URLs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic or skill to search for, e.g. 'publisher subscriber geometry_msgs Twist'.",
                },
                "course_filter": {
                    "type": "string",
                    "description": "Optional: restrict to a specific course, e.g. 'ETH RSL' or 'ROS2 official'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max number of results to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_course_content",
        "description": (
            "Fetch the text content of a robotics course page or GitHub file. "
            "Supports docs.ros.org, github.com (auto-converts to raw), rsl.ethz.ch, "
            "and any public URL. Use the URLs returned by search_course_exercises to "
            "read the actual exercise text or reference code before generating your question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch. GitHub /blob/ links are auto-converted to raw content.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return (default 4000).",
                    "default": 4000,
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "submit_question",
        "description": (
            "Submit the fully composed question as structured output. Call this as your LAST "
            "action after all tool research is complete. This eliminates ambiguous text "
            "formatting and guarantees the spec, starter code, and reference solution are "
            "captured separately. spec_json must be a valid JSON string of the question spec. "
            "starter_code is the Python file with # TODO START / # TODO END markers. "
            "reference_code is the complete working reference solution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "spec_json": {
                    "type": "string",
                    "description": "Full question specification as a JSON string.",
                },
                "starter_code": {
                    "type": "string",
                    "description": "Python starter file with # TODO START / # TODO END markers.",
                },
                "reference_code": {
                    "type": "string",
                    "description": "Complete working reference solution (no TODO markers).",
                },
            },
            "required": ["spec_json", "starter_code", "reference_code"],
        },
    },
]


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Maps tool names to their schemas and handler callables.

    Usage::

        registry = ToolRegistry(schemas=TOOL_SCHEMAS, handlers=build_handlers(...))
        text, usage = llm.complete_with_tools(system, user, registry)
    """

    def __init__(
        self,
        schemas: list[dict] | None = None,
        handlers: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        self.schemas = schemas or TOOL_SCHEMAS
        self._handlers: dict[str, Callable] = handlers or {}

    def register(self, name: str, handler: Callable) -> None:
        self._handlers[name] = handler

    def handle(self, name: str, inputs: dict) -> Any:
        fn = self._handlers.get(name)
        if fn is None:
            return {"error": f"No handler registered for tool '{name}'"}
        try:
            return fn(**inputs)
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def anthropic_schemas(self) -> list[dict]:
        """Return schemas in Anthropic tool_use format."""
        return [
            {
                "name": s["name"],
                "description": s["description"],
                "input_schema": s["input_schema"],
            }
            for s in self.schemas
        ]

    def openai_schemas(self) -> list[dict]:
        """Return schemas in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": s["name"],
                    "description": s["description"],
                    "parameters": s["input_schema"],
                },
            }
            for s in self.schemas
        ]
