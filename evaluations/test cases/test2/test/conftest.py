import json
import os
import signal
import subprocess
import time

import pytest

ROS_SOURCE = "source /opt/ros/humble/setup.bash"

TARGET_PACKAGE = "robot_modeling"
PACKAGE_DIR = "robot_modeling"
URDF_REL_PATH = "urdf/sensor_mount.urdf"
_IGNORED_DIRS = {"build", "install", "log", ".git", "__pycache__"}


def _find_package_workspace(base_path: str, package_dir_name: str) -> str:
    import pathlib

    base = pathlib.Path(base_path)
    for package_xml in base.rglob("package.xml"):
        if any(part in _IGNORED_DIRS for part in package_xml.parts):
            continue
        if package_xml.parent.name != package_dir_name:
            continue
        for ancestor in package_xml.parents:
            if ancestor.name == "src":
                return str(ancestor.parent)
    return base_path


def _kill_stray_publishers():
    subprocess.run(
        ["pkill", "-9", "-f", "robot_state_publisher"],
        capture_output=True, check=False,
    )


@pytest.fixture(scope="session")
def eval_results():
    temp_folder_path = os.getcwd()
    search_root = os.path.dirname(temp_folder_path)
    workspace_root = _find_package_workspace(search_root, PACKAGE_DIR)
    install_source = f"source {workspace_root}/install/setup.bash"
    urdf_path = os.path.join(workspace_root, "src", PACKAGE_DIR, URDF_REL_PATH)

    _default = {
        "parent_link_fixed": False,
        "joint_type_added": False,
        "robot_state_publisher_active": False,
        "sensor_mount_segment_loaded": False,
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
    rsp_proc = subprocess.Popen(
        ["bash", "-c",
         f"{ROS_SOURCE} && {install_source} && "
         f"exec ros2 run robot_state_publisher robot_state_publisher --ros-args -p "
         f"robot_description:=\"$(xacro {urdf_path})\""],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    time.sleep(3)

    results = dict(_default)
    try:
        eval_proc = subprocess.run(
            ["bash", "-c",
             f"{ROS_SOURCE} && {install_source} && "
             f"RM_PKG_SRC={workspace_root}/src/{PACKAGE_DIR} "
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
            os.killpg(os.getpgid(rsp_proc.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        _kill_stray_publishers()

    yield results
