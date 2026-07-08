"""
Unit tests — QuestionGeneratorAgent parsing functions.

Verifies:
  - three-block response parsing (JSON + starter + reference)
  - __SUBMISSION__: sentinel parsing
  - _parse_llm_question produces a valid Question
"""
from __future__ import annotations

import json

import pytest

from robo_assess.agents.question_generator import (
    _parse_three_block_response,
    _parse_llm_question,
)
from robo_assess.schemas import Difficulty, BloomLevel

from .conftest import (
    make_question_json,
    make_submission_text,
    make_three_block_text,
)


# ---------------------------------------------------------------------------
# _parse_three_block_response
# ---------------------------------------------------------------------------

def test_parse_three_block_response_submission_sentinel():
    text = make_submission_text(idx=1, skill="ROS2 publisher", difficulty="easy")
    raw, starter, reference = _parse_three_block_response(text)

    assert raw["title"] == "Publish a velocity command"
    assert "rclpy" in starter
    assert "# TODO START" in starter
    assert "solution" in reference


def test_parse_three_block_response_marker_format():
    text = make_three_block_text(idx=2, skill="ROS2 subscriber")
    raw, starter, reference = _parse_three_block_response(text)

    assert "ROS2 subscriber" in raw.get("tested_skills", [])
    assert "# TODO START" in starter
    assert "solution" in reference


def test_parse_three_block_response_json_only_fallback():
    spec = make_question_json(skill="TF2 listener")
    text = json.dumps(spec)
    raw, starter, reference = _parse_three_block_response(text)

    assert raw["title"] == "Publish a velocity command"
    assert starter == ""
    assert reference == ""


def test_parse_three_block_response_strips_code_fences():
    spec = make_question_json(skill="ROS2 service")
    json_block = "```json\n" + json.dumps(spec) + "\n```"
    text = json_block + "\n---STARTER_FILE---\n```python\nimport rclpy\n```"
    raw, starter, _ = _parse_three_block_response(text)

    assert raw["title"] == "Publish a velocity command"
    assert "import rclpy" in starter
    assert "```" not in starter


# ---------------------------------------------------------------------------
# _parse_llm_question
# ---------------------------------------------------------------------------

def test_parse_llm_question_returns_valid_question():
    raw = make_question_json(idx=1, skill="ROS2 publisher", difficulty="easy")
    starter = "import rclpy\n# TODO START\npass\n# TODO END\n"
    reference = "import rclpy\nfrom rclpy.node import Node\n"

    q = _parse_llm_question(raw, starter, reference, idx=1,
                             skill="ROS2 publisher", diff=Difficulty.EASY,
                             domain="warehouse automation")

    assert q.question_id == "Q001_ros2_publisher"
    assert q.difficulty == Difficulty.EASY
    assert q.bloom_level == BloomLevel.APPLY
    assert "ROS2 publisher" in q.tested_skills
    assert q.boilerplate_code == starter
    assert q.files_to_edit[0].reference_solution == reference


def test_parse_llm_question_medium_difficulty():
    raw = make_question_json(skill="ROS2 service", difficulty="medium")
    q = _parse_llm_question(raw, "", "", idx=3,
                             skill="ROS2 service", diff=Difficulty.MEDIUM,
                             domain="factory assembly")

    assert q.difficulty == Difficulty.MEDIUM
    assert q.bloom_level == BloomLevel.ANALYZE


def test_parse_llm_question_falls_back_on_missing_title():
    raw = make_question_json(skill="TF2 broadcaster")
    raw["title"] = ""  # empty title → fallback
    q = _parse_llm_question(raw, "", "", idx=2,
                             skill="TF2 broadcaster", diff=Difficulty.EASY,
                             domain="inspection robotics")

    assert q.title  # must not be empty


def test_parse_llm_question_evaluation_criteria_parsed():
    raw = make_question_json(skill="ROS2 publisher")
    q = _parse_llm_question(raw, "", "", idx=1,
                             skill="ROS2 publisher", diff=Difficulty.EASY,
                             domain="warehouse automation")

    assert len(q.evaluation_criteria) == 2
    assert q.evaluation_criteria[0].id == "EC1"
    assert q.evaluation_criteria[0].points == 50


