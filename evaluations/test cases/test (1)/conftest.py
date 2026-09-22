import json
import os
import signal
import subprocess
import time

import pytest

ROS_SOURCE = "source /opt/ros/humble/setup.bash"

TARGET_PACKAGE = "simulation"
LAUNCH_FILE = "sim_bringup.launch.py"
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


def _kill_stray_publishers():
    subprocess.run(
        ["pkill", "-9", "-f", LAUNCH_FILE],
        capture_output=True, check=False,
    )
    subprocess.run(
        ["pkill", "-9", "-f", f"ros2 launch {TARGET_PACKAGE}"],
        capture_output=True, check=False,
    )
    subprocess.run(["pkill", "-9", "-f", "gzserver"], capture_output=True, check=False)
    subprocess.run(["pkill", "-9", "-f", "gzclient"], capture_output=True, check=False)
    subprocess.run(["pkill", "-9", "-f", "rviz2"], capture_output=True, check=False)


@pytest.fixture(scope="session")
def eval_results():
    temp_folder_path = os.getcwd()
    workspace_root = _find_package_workspace(temp_folder_path, TARGET_PACKAGE)

    sim_ws = os.path.join(os.path.dirname(workspace_root), "simulation_ws")
    sim_ws_setup = os.path.join(sim_ws, "install", "setup.bash")
    ros_source = ROS_SOURCE
    if os.path.isfile(sim_ws_setup):
        ros_source = f"{ROS_SOURCE} && source {sim_ws_setup}"

    install_source = f"source {workspace_root}/install/setup.bash"

    _default = {
        "box_geometry_fixed": False,
        "world_file_fixed": False,
        "robot_state_publisher_in_launch": False,
        "robot_state_publisher_node_active": False,
        "rviz_node_active": False,
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
         f"{ros_source} && {install_source} && "
         f"export TURTLEBOT3_MODEL=burger && "
         f"ros2 launch {TARGET_PACKAGE} {LAUNCH_FILE}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    time.sleep(15)

    results = dict(_default)
    try:
        eval_proc = subprocess.run(
            ["bash", "-c",
             f"{ROS_SOURCE} && {install_source} && "
             f"SIM_PKG_SRC={workspace_root}/src/{TARGET_PACKAGE} "
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
