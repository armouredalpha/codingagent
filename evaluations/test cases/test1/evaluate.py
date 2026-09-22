#!/usr/bin/env python3
import json
import os
import sys

import rclpy
import yaml
from rclpy.node import Node
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

# Frames robot_state_publisher should be broadcasting for burger_lidar.xacro.
EXPECTED_FRAMES = {
    'base_footprint',
    'base_link',
    'base_scan',
    'caster_back_link',
    'imu_link',
    'wheel_left_link',
    'wheel_right_link',
}

RVIZ_CONFIG_PATH = os.path.expanduser('~/.rviz2/default.rviz')


class RspChecker(Node):
    def __init__(self):
        super().__init__('q_rm_easy_evaluator')


def _check_tf_frames(node):
    buffer = Buffer()
    TransformListener(buffer, node, spin_thread=False)

    for _ in range(30):
        rclpy.spin_once(node, timeout_sec=0.2)

    try:
        known_frames = set(yaml.safe_load(buffer.all_frames_as_yaml()) or {})
    except yaml.YAMLError:
        known_frames = set()

    return known_frames, EXPECTED_FRAMES.issubset(known_frames)


def _check_rviz_config(known_frames):
    result = {
        'config_found': False,
        'fixed_frame_valid': False,
        'robot_model_display_enabled': False,
    }

    if not os.path.isfile(RVIZ_CONFIG_PATH):
        return result
    result['config_found'] = True

    try:
        with open(RVIZ_CONFIG_PATH) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError:
        return result

    viz_manager = (config or {}).get('Visualization Manager', {})

    fixed_frame = viz_manager.get('Global Options', {}).get('Fixed Frame')
    result['fixed_frame_valid'] = bool(fixed_frame) and fixed_frame in known_frames

    for display in viz_manager.get('Displays', []) or []:
        if display.get('Class') == 'rviz_default_plugins/RobotModel' and display.get('Enabled'):
            result['robot_model_display_enabled'] = True
            break

    return result


def run_evaluation():
    rclpy.init()
    node = RspChecker()

    results = {
        'robot_state_publisher_active': False,
        'robot_description_topic_present': False,
        'gazebo_active': False,
        'rviz_active': False,
        'robot_tf_frames_present': False,
        'rviz_fixed_frame_valid': False,
        'rviz_robot_model_display_enabled': False,
    }

    rclpy.spin_once(node, timeout_sec=3.0)

    node_names = {n for n, _ in node.get_node_names_and_namespaces()}
    topic_types = dict(node.get_topic_names_and_types())

    results['robot_state_publisher_active'] = 'robot_state_publisher' in node_names
    results['robot_description_topic_present'] = '/robot_description' in topic_types
    results['gazebo_active'] = 'gazebo' in node_names
    results['rviz_active'] = any(n == 'rviz' or n.startswith('rviz') for n in node_names)

    known_frames, frames_ok = _check_tf_frames(node)
    results['robot_tf_frames_present'] = frames_ok

    # Gate the file-based rviz checks on rviz actually being open right now,
    # otherwise a leftover config from an unrelated earlier session would
    # pass even though nothing is currently running.
    rviz_config = _check_rviz_config(known_frames)
    results['rviz_fixed_frame_valid'] = results['rviz_active'] and rviz_config['fixed_frame_valid']
    results['rviz_robot_model_display_enabled'] = (
        results['rviz_active'] and rviz_config['robot_model_display_enabled']
    )

    node.destroy_node()
    rclpy.shutdown()

    passed = all(results.values())
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    run_evaluation()
