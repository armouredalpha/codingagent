#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

WORKSPACE_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.getcwd())
_SRC_CANDIDATES = [
    WORKSPACE_ROOT / 'src',
    Path.home() / 'pub_sub',
]


def _find_src() -> Path:
    for p in _SRC_CANDIDATES:
        if p.exists():
            return p
    return _SRC_CANDIDATES[0]


def _read(rel: str) -> str:
    src = _find_src()
    p = src / rel
    return p.read_text() if p.exists() else ''


def _static_checks() -> dict:
    launch = _read('launch/robot_bringup.launch.py')
    service = _read('pub_sub/ping_service.py')

    return {
        'launch_executable_fixed': "executable='status_publisher'" in launch,
        'launch_param_added': "'robot_name': 'turtlebot3'" in launch,
        'service_import_fixed': 'from std_srvs.srv import Trigger' in service,
        'service_type_fixed': 'create_service(Trigger' in service,
    }


class RuntimeChecker(Node):
    def __init__(self):
        super().__init__('q_lrf_hard_evaluator')

    def call_ping(self):
        client = self.create_client(Trigger, '/robot/ping')
        if not client.wait_for_service(timeout_sec=5.0):
            return False
        future = client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if future.done():
            result = future.result()
            return bool(result and result.success)
        return False


def run_evaluation():
    static = _static_checks()

    rclpy.init()
    node = RuntimeChecker()
    rclpy.spin_once(node, timeout_sec=3.0)

    node_names = {n for n, _ in node.get_node_names_and_namespaces()}

    runtime = {
        'publisher_node_active': 'status_publisher' in node_names,
        'ping_service_node_active': 'ping_service' in node_names,
        'ping_service_responds': node.call_ping(),
    }

    node.destroy_node()
    rclpy.shutdown()

    results = {**static, **runtime}
    passed = all(results.values())
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    run_evaluation()
