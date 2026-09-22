import pytest


def test_timer_created_tc1(eval_results):
    assert eval_results.get("timer_created") is True


def test_publish_called_tc2(eval_results):
    assert eval_results.get("publish_called") is True


def test_listener_topic_fixed_tc3(eval_results):
    assert eval_results.get("listener_topic_fixed") is True


def test_listener_field_fixed_tc4(eval_results):
    assert eval_results.get("listener_field_fixed") is True


def test_topic_published_tc5(eval_results):
    assert eval_results.get("topic_published") is True


def test_status_message_received_tc6(eval_results):
    assert eval_results.get("status_message_received") is True
