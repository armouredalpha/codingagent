import pytest


def test_parent_link_fixed_tc1(eval_results):
    assert eval_results.get("parent_link_fixed") is True


def test_joint_type_added_tc2(eval_results):
    assert eval_results.get("joint_type_added") is True


def test_robot_state_publisher_active_tc3(eval_results):
    assert eval_results.get("robot_state_publisher_active") is True


def test_sensor_mount_segment_loaded_tc4(eval_results):
    assert eval_results.get("sensor_mount_segment_loaded") is True
