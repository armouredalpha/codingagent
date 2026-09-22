#!/usr/bin/env python3
import json
import os
import re
import sys

import rclpy
from rclpy.node import Node

WORKSPACE_ROOT = os.getcwd()
_PKG_CANDIDATES = [
    *([os.environ['RM_PKG_SRC']] if os.environ.get('RM_PKG_SRC') else []),
    f"{WORKSPACE_ROOT}/src/robot_modelling",
    os.path.expanduser('~/robot_modelling'),
]


def _find_pkg() -> str:
    for p in _PKG_CANDIDATES:
        if os.path.exists(p):
            return p
    return _PKG_CANDIDATES[0]


def _read(rel: str) -> str:
    pkg = _find_pkg()
    p = f"{pkg}/{rel}"
    return open(p).read() if os.path.exists(p) else ''


def _static_checks() -> dict:
    xacro_src = _read('urdf/burger_lidar.xacro')
    xacro_no_comments = re.sub(r'<!--.*?-->', '', xacro_src, flags=re.DOTALL)
    launch_src = _read('launch/model_bringup.launch.py')

    return {
        'property_value_quoted': bool(re.search(
            r'<xacro:property\s+name="lidar_height"\s+value="0\.5"\s*/>',
            xacro_no_comments)),
        'plugin_name_added': 'name="lidar_plugin"' in xacro_no_comments,
        'launch_filename_fixed': "'burger_lidar.xacro'" in launch_src,
    }


class RuntimeChecker(Node):
    def __init__(self):
        super().__init__('q_rm_hard_evaluator')


def run_evaluation():
    static = _static_checks()

    rclpy.init()
    node = RuntimeChecker()
    rclpy.spin_once(node, timeout_sec=3.0)

    node_names = {n for n, _ in node.get_node_names_and_namespaces()}
    topic_types = dict(node.get_topic_names_and_types())

    runtime = {
        'robot_state_publisher_active': 'robot_state_publisher' in node_names,
        'lidar_link_loaded': '/robot_description' in topic_types,
    }

    node.destroy_node()
    rclpy.shutdown()

    results = {**static, **runtime}
    passed = all(results.values())
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    run_evaluation()
