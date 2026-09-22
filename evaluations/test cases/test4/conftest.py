import json
import os
import signal
import subprocess
import time

import pytest

ROS_SOURCE = "source /opt/ros/humble/setup.bash"

TARGET_PACKAGE = "pub_sub"
TARGET_EXECUTABLE = "status_publisher"
_IGNORED_DIRS = {"build", "install", "log", ".git", "__pycache__"}


def _find_package_workspace(base_path: str, package_name: str) -> str:
    import pathlib
    import re

    base = pathlib.Path(base_path)
    for package_xml in base.rglob("package.xml"):
        if any(part in _IGNORED_DIRS for part in package_xml.parts):
            continue
        try:
            text = package_xml.read_text()
        except OSError:
            continue
        if not re.search(rf"<name>\s*{re.escape(package_name)}\s*</name>", text):
            continue
        for ancestor in package_xml.parents:
            if ancestor.name == "src":
                return str(ancestor.parent)
    return base_path


def _kill_stray_publishers():
    subprocess.run(
        ["pkill", "-9", "-f", f"{TARGET_PACKAGE}/lib/{TARGET_PACKAGE}/{TARGET_EXECUTABLE}"],
        capture_output=True, check=False,
    )
    subprocess.run(
        ["pkill", "-9", "-f", f"ros2 run {TARGET_PACKAGE} {TARGET_EXECUTABLE}"],
        capture_output=True, check=False,
    )


@pytest.fixture(scope="session")
def eval_results():
    temp_folder_path = os.getcwd()
    workspace_root = _find_package_workspace(temp_folder_path, TARGET_PACKAGE)
    install_source = f"source {workspace_root}/install/setup.bash"

    _default = {
        "timer_created": False,
        "publish_called": False,
        "listener_topic_fixed": False,
        "listener_field_fixed": False,
        "topic_published": False,
        "status_message_received": False,
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
    publisher = subprocess.Popen(
        ["bash", "-c",
         f"{ROS_SOURCE} && {install_source} && "
         f"exec ros2 run {TARGET_PACKAGE} {TARGET_EXECUTABLE}"],
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
             f"python3 {temp_folder_path}/evaluate.py {workspace_root}"],
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
            os.killpg(os.getpgid(publisher.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        _kill_stray_publishers()

    yield results
