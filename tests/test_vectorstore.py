"""
Integration tests — TF-IDF VectorStore.

Covers: add, max_similarity, exclude_id, topic filter, eviction,
disk save/load.  No network calls.
"""
from __future__ import annotations

import json
import math

import pytest

from robo_assess.vectorstore import VectorStore, text_similarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _store(tmp_path, max_entries: int = 500) -> VectorStore:
    return VectorStore(path=str(tmp_path / "vec.json"), max_entries=max_entries)


# ---------------------------------------------------------------------------
# Basic operations
# ---------------------------------------------------------------------------

def test_empty_store_returns_zero_similarity(tmp_path):
    s = _store(tmp_path)
    sim, match = s.max_similarity("any text about ROS2 publisher")
    assert sim == 0.0
    assert match is None


def test_add_and_find_single_entry(tmp_path):
    s = _store(tmp_path)
    s.add("Q001", "publisher node publishes geometry_msgs Twist at 10 Hz")
    sim, match = s.max_similarity("publisher node geometry_msgs Twist velocity")
    assert sim > 0.5
    assert match == "Q001"


def test_add_multiple_returns_best_match(tmp_path):
    s = _store(tmp_path)
    s.add("Q001", "publisher node Twist velocity cmd_vel")
    s.add("Q002", "subscriber IMU sensor data callback")
    s.add("Q003", "service server request response handler")

    sim, match = s.max_similarity("subscriber IMU callback sensor data processing")
    assert match == "Q002"
    assert sim > 0.3


def test_dissimilar_text_returns_low_score(tmp_path):
    s = _store(tmp_path)
    s.add("Q001", "publisher node Twist velocity cmd_vel")
    sim, _ = s.max_similarity("unrelated content about machine learning neural networks")
    assert sim < 0.3


# ---------------------------------------------------------------------------
# exclude_id (the bug that was silently broken)
# ---------------------------------------------------------------------------

def test_exclude_id_skips_own_entry(tmp_path):
    """A question must not be flagged as a duplicate of itself (regression test
    for the exclude_ids → exclude_id bug fixed in this session)."""
    s = _store(tmp_path)
    text = "publisher node geometry_msgs Twist velocity cmd_vel 10 Hz warehouse"
    s.add("Q001", text)
    sim, match = s.max_similarity(text, exclude_id="Q001")
    # With only one entry and it excluded, result should be zero / no match
    assert match is None or match != "Q001"


def test_exclude_id_still_returns_other_matches(tmp_path):
    s = _store(tmp_path)
    text = "publisher Twist velocity cmd_vel"
    s.add("Q001", text)
    s.add("Q002", text + " warehouse robot")
    sim, match = s.max_similarity(text, exclude_id="Q001")
    assert match == "Q002"


# ---------------------------------------------------------------------------
# Topic filter
# ---------------------------------------------------------------------------

def test_topic_filter_restricts_results(tmp_path):
    s = _store(tmp_path)
    s.add("Q001", "publisher node Twist velocity", topic="ros2_basics")
    s.add("Q002", "publisher node Twist velocity", topic="advanced")

    sim, match = s.max_similarity("publisher Twist velocity", topic="advanced")
    assert match == "Q002"

    sim2, match2 = s.max_similarity("publisher Twist velocity", topic="ros2_basics")
    assert match2 == "Q001"


# ---------------------------------------------------------------------------
# Eviction (max_entries)
# ---------------------------------------------------------------------------

def test_eviction_drops_oldest_entries(tmp_path):
    s = _store(tmp_path, max_entries=3)
    s.add("Q001", "publisher Twist velocity cmd_vel")
    s.add("Q002", "subscriber IMU callback")
    s.add("Q003", "service server request response")
    # Add 4th entry → Q001 should be evicted
    s.add("Q004", "launch file gazebo simulation")

    assert len(s) == 3
    sim, match = s.max_similarity("publisher Twist velocity cmd_vel")
    # Q001 was evicted; similar text might still get a hit from Q003/Q004
    # but the old exact match is gone
    assert match != "Q001"


def test_eviction_does_not_drop_recent_entries(tmp_path):
    s = _store(tmp_path, max_entries=3)
    s.add("Q001", "old entry one")
    s.add("Q002", "old entry two")
    s.add("Q003", "recent entry three")
    s.add("Q004", "newest entry four")

    # Q001 evicted; Q003, Q004 must still be present
    sim3, match3 = s.max_similarity("recent entry three")
    assert match3 == "Q003"

    sim4, match4 = s.max_similarity("newest entry four")
    assert match4 == "Q004"


# ---------------------------------------------------------------------------
# Disk save / load
# ---------------------------------------------------------------------------

def test_save_and_load(tmp_path):
    path = str(tmp_path / "test_vec.json")
    s1 = VectorStore(path=path)
    s1.add("Q001", "publisher Twist velocity cmd_vel")
    s1.save()

    s2 = VectorStore(path=path)
    sim, match = s2.max_similarity("publisher Twist velocity")
    assert match == "Q001"
    assert sim > 0.3


# ---------------------------------------------------------------------------
# text_similarity helper
# ---------------------------------------------------------------------------

def test_text_similarity_identical():
    a = "publisher ROS2 Twist velocity cmd_vel warehouse"
    assert text_similarity(a, a) == pytest.approx(1.0, abs=0.01)


def test_text_similarity_disjoint():
    a = "publisher Twist velocity"
    b = "neural network machine learning classification"
    assert text_similarity(a, b) < 0.1
