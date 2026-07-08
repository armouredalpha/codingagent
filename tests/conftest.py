"""Shared pytest fixtures and helpers for the robo_assess test-suite."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from robo_assess.config import Settings


# ---------------------------------------------------------------------------
# Question factory
# ---------------------------------------------------------------------------

def make_question_json(
    idx: int = 1,
    skill: str = "ROS2 publisher",
    difficulty: str = "easy",
    title: str = "Publish a velocity command",
) -> dict:
    """Minimal dict that _parse_llm_question can consume."""
    return {
        "title": title,
        "scenario": f"A warehouse robot must publish a Twist message to /cmd_vel.",
        "objective": f"Implement a ROS2 node that publishes geometry_msgs/Twist at 10 Hz.",
        "tested_skills": [skill],
        "constraints": ["Use rclpy", "Publish at exactly 10 Hz"],
        "common_mistakes": ["forgetting to spin"],
        "evaluation_criteria": [
            {"id": "EC1", "check": "topic_active", "target": "/cmd_vel",
             "expected": "geometry_msgs/Twist", "points": 50, "description": "topic publishes"},
            {"id": "EC2", "check": "publish_rate", "target": "/cmd_vel",
             "expected": "10.0", "points": 50, "description": "rate is 10 Hz"},
        ],
        "file_structure": {"ros_package": "vel_pub", "dependencies": ["rclpy", "geometry_msgs"]},
        "tasks": ["Create the publisher node", "Publish Twist at 10 Hz"],
        "metadata": {
            "topic": skill,
            "difficulty_level": difficulty,
            "estimated_time_minutes": 20,
            "concepts": [skill],
        },
    }


def make_submission_text(idx: int = 1, skill: str = "ROS2 publisher", difficulty: str = "easy") -> str:
    """Return a __SUBMISSION__:... string that _parse_three_block_response accepts."""
    spec = make_question_json(idx=idx, skill=skill, difficulty=difficulty)
    payload = {
        "spec_json": json.dumps(spec),
        "starter_code": "import rclpy\n# TODO START\n# TODO END\n",
        "reference_code": "import rclpy\nfrom rclpy.node import Node\n# solution\n",
    }
    return "__SUBMISSION__:" + json.dumps(payload)


def make_three_block_text(idx: int = 1, skill: str = "ROS2 subscriber") -> str:
    """Return a three-block (JSON + STARTER + REFERENCE) response string."""
    spec = make_question_json(idx=idx, skill=skill, difficulty="medium")
    json_block = json.dumps(spec)
    starter = "import rclpy\n# TODO START\npass\n# TODO END\n"
    reference = "import rclpy\nfrom rclpy.node import Node\n# full solution\n"
    return f"{json_block}\n---STARTER_FILE---\n{starter}\n---REFERENCE_FILE---\n{reference}"


# ---------------------------------------------------------------------------
# Settings fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_settings(tmp_path: Path) -> Settings:
    """Settings pointed at throwaway temp directories — no API key needed."""
    s = Settings()
    s.provider = "openrouter"
    s.api_key = "fake-key-for-tests"
    s.log_db_path = str(tmp_path / "runs.db")
    s.memory_db_path = str(tmp_path / "memory.db")
    s.vectorstore_path = str(tmp_path / "vec.json")
    s.outputs_dir = str(tmp_path / "outputs")
    s.reports_dir = str(tmp_path / "reports")
    s.prompts_dir = str(tmp_path / "prompts")
    s.skills_dir = str(tmp_path / "skills")
    s.calibrator_path = str(tmp_path / "calibration" / "calibrator.json")
    s.calibration_observations_path = str(tmp_path / "calibration" / "observations.jsonl")
    s.qdrant_url = None  # always use TF-IDF store in tests
    return s
