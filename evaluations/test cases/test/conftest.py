import json
import os
import signal
import subprocess
import time

import pytest

ROS_SOURCE = "source /opt/ros/humble/setup.bash"

TARGET_PACKAGE = "robot_modeling"
LAUNCH_FILE = "model_bringup.launch.py"
_IGNORED_DIRS = {"build", "install", "log", ".git", "__pycache__"}


def _find_package_workspace(base_path: str, package_name: str) -> str:
    import pathlib

    base = pathlib.Path(base_path)
    for package_xml in base.rglob("package.xml"):
        if any(part in _IGNORED_DIRS for part in package_xml.parts):
            continue
        try:
            declared_name = package_xml.read_text()
        except OSError:
            continue
        if f"<name>{package_name}</name>" not in declared_name:
            continue
        for ancestor in package_xml.parents:
            if ancestor.name == "src":
                return str(ancestor.parent)
    return base_path


def _kill_stray_publishers():
    subprocess.run(
        ["pkill", "-9", "-f", LAUNCH_FILE],
        capture_output=True, check=False,
    )
    subprocess.run(
        ["pkill", "-9", "-f", f"ros2 launch {TARGET_PACKAGE}"],
        capture_output=True, check=False,
    )


@pytest.fixture(scope="session")
def eval_results():
    temp_folder_path = os.getcwd()
    search_root = os.path.dirname(temp_folder_path)
    workspace_root = _find_package_workspace(search_root, TARGET_PACKAGE)
    install_source = f"source {workspace_root}/install/setup.bash"

    _default = {
        "property_value_quoted": False,
        "plugin_name_added": False,
        "launch_filename_fixed": False,
        "robot_state_publisher_active": False,
        "lidar_link_loaded": False,
    }

    build = subprocess.run(
        ["bash", "-c",
         f"{ROS_SOURCE} && cd {workspace_root} && "
         f"colcon build --packages-select {TARGET_PACKAGE}"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if build.returncode != 0:
        try:
            log_path = os.path.join(temp_folder_path, "colcon_build_error.log")
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write((build.stdout or "") + "\n" + (build.stderr or ""))
        except OSError:
            pass
        yield _default
        return

    _kill_stray_publishers()
    launch_proc = subprocess.Popen(
        ["bash", "-c",
         f"{ROS_SOURCE} && {install_source} && "
         f"ros2 launch {TARGET_PACKAGE} {LAUNCH_FILE}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    time.sleep(5)

    results = dict(_default)
    try:
        eval_proc = subprocess.run(
            ["bash", "-c",
             f"{ROS_SOURCE} && {install_source} && "
             f"RM_PKG_SRC={workspace_root}/src/robot_modelling "
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
    finally:
        try:
            os.killpg(os.getpgid(launch_proc.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        _kill_stray_publishers()

    yield results
