import pytest


def test_box_geometry_fixed_tc1(eval_results):
    assert eval_results.get("box_geometry_fixed") is True


def test_world_file_fixed_tc2(eval_results):
    assert eval_results.get("world_file_fixed") is True


def test_robot_state_publisher_in_launch_tc3(eval_results):
    assert eval_results.get("robot_state_publisher_in_launch") is True


def test_robot_state_publisher_node_active_tc4(eval_results):
    assert eval_results.get("robot_state_publisher_node_active") is True


def test_rviz_node_active_tc5(eval_results):
    assert eval_results.get("rviz_node_active") is True
