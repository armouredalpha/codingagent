import pytest


def test_talker_node_active_tc1(eval_results):
    assert eval_results.get("talker_node_active") is True


def test_listener_node_active_tc2(eval_results):
    assert eval_results.get("listener_node_active") is True


def test_chatter_topic_present_tc3(eval_results):
    assert eval_results.get("chatter_topic_present") is True


def test_chatter_message_received_tc4(eval_results):
    assert eval_results.get("chatter_message_received") is True
