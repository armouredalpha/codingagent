#!/usr/bin/env python3
import json
import os
import re
import sys

import rclpy
import yaml
from rclpy.node import Node
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

WORKSPACE_ROOT = os.getcwd()
_PKG_CANDIDATES = [
    *([os.environ['RM_PKG_SRC']] if os.environ.get('RM_PKG_SRC') else []),
    f"{WORKSPACE_ROOT}/src/robot_modeling",
    os.path.expanduser('~/robot_modeling'),
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
    urdf_src = _read('urdf/sensor_mount.urdf')
    urdf_no_comments = re.sub(r'<!--.*?-->', '', urdf_src, flags=re.DOTALL)

    joint_block_match = re.search(
        r'<joint\s+name="sensor_mount_joint"[^>]*>.*?</joint>',
        urdf_no_comments, flags=re.DOTALL)
    joint_block = joint_block_match.group(0) if joint_block_match else ''

    return {
        'parent_link_fixed': bool(re.search(r'<parent\s+link="base_link"\s*/>', joint_block)),
        'joint_type_added': bool(re.search(
            r'<joint\s+name="sensor_mount_joint"\s+type="fixed"', urdf_no_comments)),
    }


class RuntimeChecker(Node):
    def __init__(self):
        super().__init__('q_rm_medium_evaluator')


def _check_tf_frame(node, frame_name: str) -> bool:
    buffer = Buffer()
    TransformListener(buffer, node, spin_thread=False)

    for _ in range(30):
        rclpy.spin_once(node, timeout_sec=0.2)

    try:
        known_frames = set(yaml.safe_load(buffer.all_frames_as_yaml()) or {})
    except yaml.YAMLError:
        known_frames = set()

    return frame_name in known_frames


def run_evaluation():
    static = _static_checks()

    rclpy.init()
    node = RuntimeChecker()
    rclpy.spin_once(node, timeout_sec=3.0)

    node_names = {n for n, _ in node.get_node_names_and_namespaces()}

    runtime = {
        'robot_state_publisher_active': 'robot_state_publisher' in node_names,
        'sensor_mount_segment_loaded': _check_tf_frame(node, 'sensor_mount_link'),
    }

    node.destroy_node()
    rclpy.shutdown()

    results = {**static, **runtime}
    passed = all(results.values())
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    run_evaluation()
