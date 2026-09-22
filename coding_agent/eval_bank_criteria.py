"""
Eval-bank check-vocabulary calibration
=======================================

``evaluations/test cases/`` holds real, human-authored grading bundles
(conftest.py / evaluate.py / test_*.py) from production assessments —
distinct from ``evaluations/question.json`` + ``solution.json`` (which
``SupervisorAgent`` already uses for title/scenario/difficulty calibration).

Those bundles are the ground truth for what a GOOD ``evaluation_criteria``
entry looks like: which ``check`` types real graders actually use, and what
realistic ``target``/``expected`` values look like for each. This module
turns that corpus into a small, curated few-shot block injected into the
question-generator prompt, so the LLM calibrates against real precedent
instead of only the one worked example baked into the prompt template.

The examples below are hand-extracted from every bundle under
``evaluations/test cases/`` (rm_easy/medium/hard, lrf_easy/medium/hard,
sim_hard) — one per distinct check type actually observed there, translated
into this pipeline's ``EvaluationCriterion`` shape. This is a static,
reviewed snapshot rather than a runtime parser over arbitrary source, so a
new bundle dropped into that folder does not silently change generation
until this list is re-curated.
"""

from __future__ import annotations

_EXAMPLES: list[dict] = [
    {
        "check": "message_content",
        "target": "wheel_radius = 0.1",
        "description": "the corrected constant is assigned in the fixed line",
        "source": "rm_medium-style static value fix",
    },
    {
        "check": "string_absent",
        "target": "/robot_status",
        "description": "the old, wrong topic name no longer appears anywhere in the listener",
        "source": "lrf_medium listener_topic_fixed — catches partial fixes",
    },
    {
        "check": "topic_published",
        "target": "/robot/status",
        "description": "the publisher node advertises the corrected topic",
        "source": "lrf_medium topic_published",
    },
    {
        "check": "topic_message_type",
        "target": "/chatter",
        "expected": "std_msgs/msg/String",
        "description": "the chatter topic is advertised with the correct message type",
        "source": "lrf_easy / heartbeat message_type_ok",
    },
    {
        "check": "message_field_contains",
        "target": "/robot/status",
        "expected": "STATUS:",
        "description": "published messages actually carry the corrected status prefix",
        "source": "lrf_medium status_message_received — runtime content, not just source text",
    },
    {
        "check": "node_exists",
        "target": "listener",
        "description": "the listener node is running",
        "source": "lrf_easy listener_node_active",
    },
    {
        "check": "service_exists",
        "target": "/robot/ping",
        "description": "the ping service server is advertised",
        "source": "lrf_hard ping_service_node_active",
    },
    {
        "check": "service_responds",
        "target": "/robot/ping",
        "expected": "std_srvs.srv.Trigger",
        "description": "calling the ping service returns a successful Trigger response",
        "source": "lrf_hard ping_service_responds — actual round-trip call, not just existence",
    },
    {
        "check": "tf_frame_exists",
        "target": "sensor_mount_link",
        "description": "the new URDF joint actually broadcasts this frame in the live tf tree",
        "source": "rm_medium sensor_mount_segment_loaded",
    },
]


def render_examples_block(max_n: int = 6) -> str:
    """Return a prompt-ready block of curated real check-type exemplars.

    ``max_n`` caps how many are shown (token budget) — always includes a
    spread of check types rather than the first N, since duplicated check
    types teach the model nothing new.
    """
    examples = _EXAMPLES[:max_n]
    if not examples:
        return ""
    lines = [
        "REAL EVAL-BANK CHECK VOCABULARY (from evaluations/test cases/ — calibration "
        "for what a realistic, discriminating evaluation_criteria entry looks like; "
        "do not copy targets verbatim, match the STYLE and specificity):"
    ]
    for ex in examples:
        parts = [f'check={ex["check"]!r}', f'target={ex["target"]!r}']
        if ex.get("expected"):
            parts.append(f'expected={ex["expected"]!r}')
        lines.append(f"  - {', '.join(parts)} — {ex['description']} ({ex['source']})")
    return "\n".join(lines)
