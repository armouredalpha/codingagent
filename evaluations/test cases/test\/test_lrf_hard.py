import pytest


def test_launch_executable_fixed_tc1(eval_results):
    assert eval_results.get("launch_executable_fixed") is True


def test_launch_param_added_tc2(eval_results):
    assert eval_results.get("launch_param_added") is True


def test_service_import_fixed_tc3(eval_results):
    assert eval_results.get("service_import_fixed") is True


def test_service_type_fixed_tc4(eval_results):
    assert eval_results.get("service_type_fixed") is True


def test_publisher_node_active_tc5(eval_results):
    assert eval_results.get("publisher_node_active") is True


def test_ping_service_node_active_tc6(eval_results):
    assert eval_results.get("ping_service_node_active") is True


def test_ping_service_responds_tc7(eval_results):
    assert eval_results.get("ping_service_responds") is True
