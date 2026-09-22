#!/usr/bin/env python3
import json
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ChatterSampler(Node):
    def __init__(self):
        super().__init__('q_lrf_easy_evaluator')
        self.received = False
        self.create_subscription(String, '/chatter', self._cb, 10)

    def _cb(self, msg):
        self.received = True


def run_evaluation():
    rclpy.init()
    node = ChatterSampler()

    deadline = time.time() + 5.0
    while time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    node_names = {n for n, _ in node.get_node_names_and_namespaces()}
    topic_types = dict(node.get_topic_names_and_types())

    results = {
        'talker_node_active': 'talker' in node_names,
        'listener_node_active': 'listener' in node_names,
        'chatter_topic_present': '/chatter' in topic_types,
        'chatter_message_received': node.received,
    }

    node.destroy_node()
    rclpy.shutdown()

    passed = all(results.values())
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    run_evaluation()
