import pytest


def test_property_value_quoted_tc1(eval_results):
    assert eval_results.get("property_value_quoted") is True


def test_plugin_name_added_tc2(eval_results):
    assert eval_results.get("plugin_name_added") is True


def test_launch_filename_fixed_tc3(eval_results):
    assert eval_results.get("launch_filename_fixed") is True


def test_robot_state_publisher_active_tc4(eval_results):
    assert eval_results.get("robot_state_publisher_active") is True


def test_lidar_link_loaded_tc5(eval_results):
    assert eval_results.get("lidar_link_loaded") is True
