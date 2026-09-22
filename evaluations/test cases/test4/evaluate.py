#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

WORKSPACE_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.getcwd())
PUBLISHER_CANDIDATES = [
    WORKSPACE_ROOT / 'src' / 'pub_sub' / 'status_publisher.py',
    Path.home() / 'pub_sub' / 'status_publisher.py',
]
LISTENER_CANDIDATES = [
    WORKSPACE_ROOT / 'src' / 'pub_sub' / 'status_listener.py',
    Path.home() / 'pub_sub' / 'status_listener.py',
]


def _find_file(candidates: list) -> Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


def _source_text(path) -> str:
    return path.read_text() if path else ''


class StatusSampler(Node):
    def __init__(self):
        super().__init__('q_lrf_medium_evaluator')
        self.messages: list = []
        self.create_subscription(String, '/robot/status', self._cb, 10)

    def _cb(self, msg: String):
        self.messages.append(msg.data)


def _static_checks(publisher_src: str, listener_src: str) -> dict:
    return {
        'timer_created': 'self.timer = self.create_timer(1.0, self.timer_callback)' in publisher_src,
        'publish_called': 'self.publisher_.publish(msg)' in publisher_src,
        'listener_topic_fixed': "'/robot/status'" in listener_src and "'/robot_status'" not in listener_src,
        'listener_field_fixed': 'msg.data' in listener_src and 'msg.string' not in listener_src,
    }


def run_evaluation():
    publisher_path = _find_file(PUBLISHER_CANDIDATES)
    listener_path = _find_file(LISTENER_CANDIDATES)
    publisher_src = _source_text(publisher_path)
    listener_src = _source_text(listener_path)

    static = _static_checks(publisher_src, listener_src)

    rclpy.init()
    node = StatusSampler()
    deadline = time.time() + 5.0
    while time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    topic_types = dict(node.get_topic_names_and_types())
    runtime = {
        'topic_published': '/robot/status' in topic_types,
        'status_message_received': any(m.startswith('STATUS:') for m in node.messages),
    }

    node.destroy_node()
    rclpy.shutdown()

    results = {**static, **runtime}
    passed = all(results.values())
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    run_evaluation()
