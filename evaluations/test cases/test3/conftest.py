import json
import os
import signal
import subprocess
import time

import pytest

ROS_SOURCE = "source /opt/ros/humble/setup.bash"
TARGET_PACKAGE = "pub_sub"


def _kill_stray_publishers():
    subprocess.run(
        ["pkill", "-9", "-f", f"{TARGET_PACKAGE} talker"],
        capture_output=True, check=False,
    )
    subprocess.run(
        ["pkill", "-9", "-f", f"{TARGET_PACKAGE} listener"],
        capture_output=True, check=False,
    )


@pytest.fixture(scope="session")
def eval_results():
    temp_folder_path = os.getcwd()
    workspace_root = os.path.dirname(temp_folder_path) if os.path.basename(temp_folder_path) == "src" else temp_folder_path
    install_source = f"source {workspace_root}/install/setup.bash"

    _default = {
        "talker_node_active": False,
        "listener_node_active": False,
        "chatter_topic_present": False,
        "chatter_message_received": False,
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
    talker = subprocess.Popen(
        ["bash", "-c",
         f"{ROS_SOURCE} && {install_source} && exec ros2 run {TARGET_PACKAGE} talker"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    listener = subprocess.Popen(
        ["bash", "-c",
         f"{ROS_SOURCE} && {install_source} && exec ros2 run {TARGET_PACKAGE} listener"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    time.sleep(3)

    results = dict(_default)
    try:
        eval_proc = subprocess.run(
            ["bash", "-c",
             f"{ROS_SOURCE} && python3 {temp_folder_path}/evaluate.py"],
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
        for proc in (talker, listener):
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        _kill_stray_publishers()

    yield results
