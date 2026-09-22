import json
import os
import subprocess

import pytest

ROS_SOURCE = "source /opt/ros/humble/setup.bash"

TARGET_PACKAGE = "turtlebot3_description"
_IGNORED_DIRS = {"build", "install", "log", ".git", "__pycache__"}


def _find_package_workspace(base_path: str, package_name: str) -> str:
    import pathlib

    base = pathlib.Path(base_path)
    for package_xml in base.rglob("package.xml"):
        if any(part in _IGNORED_DIRS for part in package_xml.parts):
            continue
        if package_xml.parent.name != package_name:
            continue
        for ancestor in package_xml.parents:
            if ancestor.name == "src":
                return str(ancestor.parent)
    return base_path


@pytest.fixture(scope="session")
def eval_results():
    temp_folder_path = os.getcwd()
    workspace_root = _find_package_workspace(temp_folder_path, TARGET_PACKAGE)
    install_source = f"source {workspace_root}/install/setup.bash"

    _default = {
        "robot_state_publisher_active": False,
        "robot_description_topic_present": False,
    }

    results = dict(_default)
    try:
        eval_proc = subprocess.run(
            ["bash", "-c",
             f"{ROS_SOURCE} && {install_source} && "
             f"python3 {temp_folder_path}/evaluate.py"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        try:
            output = json.loads(eval_proc.stdout)
            results = output.get("results", results)
        except (json.JSONDecodeError, KeyError):
            pass
    except subprocess.TimeoutExpired:
        pass

    yield results
