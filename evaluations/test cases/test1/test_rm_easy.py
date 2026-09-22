import pytest


def test_robot_state_publisher_active_tc1(eval_results):
    assert eval_results.get("robot_state_publisher_active") is True


def test_robot_description_topic_present_tc2(eval_results):
    assert eval_results.get("robot_description_topic_present") is True


def test_gazebo_active_tc3(eval_results):
    assert eval_results.get("gazebo_active") is True


def test_rviz_active_tc4(eval_results):
    assert eval_results.get("rviz_active") is True


def test_robot_tf_frames_present_tc5(eval_results):
    assert eval_results.get("robot_tf_frames_present") is True


def test_rviz_fixed_frame_valid_tc6(eval_results):
    assert eval_results.get("rviz_fixed_frame_valid") is True


def test_rviz_robot_model_display_enabled_tc7(eval_results):
    assert eval_results.get("rviz_robot_model_display_enabled") is True
