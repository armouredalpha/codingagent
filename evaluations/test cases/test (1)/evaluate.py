#!/usr/bin/env python3
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import rclpy
from rclpy.node import Node

WORKSPACE_ROOT = Path(os.getcwd())
_PKG_CANDIDATES = [
    *([Path(os.environ['SIM_PKG_SRC'])] if os.environ.get('SIM_PKG_SRC') else []),
    WORKSPACE_ROOT / 'src' / 'simulation',
    Path.home() / 'simulation',
]


def _find_pkg() -> Path:
    for p in _PKG_CANDIDATES:
        if p.exists():
            return p
    return _PKG_CANDIDATES[0]


def _read(rel: str) -> str:
    pkg = _find_pkg()
    p = pkg / rel
    return p.read_text() if p.exists() else ''


def _collision_box_size_fixed(world_src: str) -> bool:
    try:
        root = ET.fromstring(world_src)
    except ET.ParseError:
        return False

    collision = root.find(
        ".//model[@name='box_obstacle']"
        "/link[@name='box_link']"
        "/collision[@name='box_collision']"
    )
    if collision is None:
        return False

    size = collision.find('geometry/box/size')
    if size is None or size.text is None:
        return False

    try:
        dims = [float(v) for v in size.text.split()]
    except ValueError:
        return False

    return dims == [1.0, 1.0, 1.0]


def _static_checks() -> dict:
    world_src = _read('worlds/custom_world.sdf')
    launch_src = _read('launch/sim_bringup.launch.py')

    return {
        'box_geometry_fixed': _collision_box_size_fixed(world_src),
        'world_file_fixed': "'custom_world.sdf'" in launch_src,
        'robot_state_publisher_in_launch': "package='robot_state_publisher'" in launch_src,
    }


class RuntimeChecker(Node):
    def __init__(self):
        super().__init__('q_sim_hard_evaluator')


def run_evaluation():
    static = _static_checks()

    rclpy.init()
    node = RuntimeChecker()
    rclpy.spin_once(node, timeout_sec=3.0)

    node_names = {n for n, _ in node.get_node_names_and_namespaces()}

    runtime = {
        'robot_state_publisher_node_active': 'robot_state_publisher' in node_names,
        'rviz_node_active': 'rviz2' in node_names,
    }

    node.destroy_node()
    rclpy.shutdown()

    results = {**static, **runtime}
    passed = all(results.values())
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    run_evaluation()
