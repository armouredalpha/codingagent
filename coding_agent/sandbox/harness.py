"""
Deterministic 5-file grading harness generator
================================================

Produces the exact ros_ws/ layout described in the platform README:

    ros_ws/
        pytest.ini
        conftest.py
        evaluate.py
        requirements.txt
        test_<qid>.py
        src/<pkg>/...            (written separately — starter/reference files)

All 5 files sit FLAT in ros_ws/ — never in src/, never in a tests/ folder.
`pytest.ini` and `requirements.txt` are byte-identical every time. `conftest.py`
is one template filled from a SimPackage registry entry. `evaluate.py` and
`test_<qid>.py` are generated MECHANICALLY from `q.evaluation_criteria` — the
same criteria the pipeline already validated — so the grading logic and the
question spec can never drift apart.

When a question has no `sim_package_id` (no registry match — e.g. a pure
TYPE_A Python question with nothing to launch), the harness degrades to a
static-only conftest.py that skips colcon build / ros2 launch entirely and
just execs evaluate.py directly — never fabricate a build step that didn't
happen.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..schemas import Question
from .registry import SimPackage

PYTEST_INI = """[pytest]
addopts =
    -p no:launch_testing
    -p no:launch_pytest
    -p no:launch_ros
    -p no:ament_flake8
    -p no:ament_pep257
    -p no:ament_copyright
    -p no:ament_xmllint
"""

REQUIREMENTS_TXT = "pytest>=7.0.0\n"

# Check types that need a LIVE node (spin + introspection) to answer.
# Everything else is treated as a static source check.
_RUNTIME_CHECKS = {
    "node_exists", "topic_active", "topic_published", "topic_subscribed",
    "subscriber", "subscription", "service", "service_exists",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", text.lower()).strip("_") or "check"


def _criterion_key(ec) -> str:
    """Stable snake_case result-dict key derived from the criterion id."""
    return _slug(ec.id) if getattr(ec, "id", "") else _slug(ec.description[:30])


def render_conftest(q: Question, pkg: SimPackage | None) -> str:
    if pkg is None:
        return _render_conftest_static()
    return _render_conftest_ros(pkg)


def _render_conftest_static() -> str:
    return '''"""Auto-generated conftest.py — static-only harness (no sim dependency)."""
import json
import os
import subprocess
import sys

import pytest


@pytest.fixture(scope="session")
def eval_results():
    temp_folder_path = os.getcwd()
    proc = subprocess.run(
        [sys.executable, os.path.join(temp_folder_path, "evaluate.py")],
        capture_output=True, text=True, timeout=30,
    )
    try:
        output = json.loads(proc.stdout)
        yield output.get("results", {})
    except (json.JSONDecodeError, KeyError):
        yield {}
'''


def _render_conftest_ros(pkg: SimPackage) -> str:
    return f'''"""Auto-generated conftest.py — builds, launches, and evaluates the student package."""
import json
import os
import signal
import subprocess
import time

import pytest

ROS_SOURCE = "source /opt/ros/humble/setup.bash"

TARGET_PACKAGE = {pkg.ros_package!r}
LAUNCH_FILE = {pkg.launch_file!r}
SIM_WORKSPACE = {pkg.sim_workspace!r}
_IGNORED_DIRS = {{"build", "install", "log", ".git", "__pycache__"}}


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


def _find_sim_workspace(student_ws_root: str, sim_ws_name: str) -> str:
    """The shared simulation_ws sits alongside ros_ws (see workspace/README.md)."""
    import pathlib
    candidate = pathlib.Path(student_ws_root).parent / sim_ws_name
    return str(candidate) if candidate.exists() else student_ws_root


def _kill_stray_publishers():
    subprocess.run(["pkill", "-9", "-f", LAUNCH_FILE], capture_output=True, check=False)
    subprocess.run(["pkill", "-9", "-f", f"ros2 launch {{TARGET_PACKAGE}}"], capture_output=True, check=False)


@pytest.fixture(scope="session")
def eval_results():
    temp_folder_path = os.getcwd()
    workspace_root = _find_package_workspace(temp_folder_path, TARGET_PACKAGE)
    sim_workspace_root = _find_sim_workspace(workspace_root, SIM_WORKSPACE)
    install_source = f"source {{workspace_root}}/install/setup.bash"
    sim_install_source = f"source {{sim_workspace_root}}/install/setup.bash"

    _default = {{}}

    build = subprocess.run(
        ["bash", "-c",
         f"{{ROS_SOURCE}} && {{sim_install_source}} && cd {{workspace_root}} && "
         f"colcon build --packages-select {{TARGET_PACKAGE}}"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if build.returncode != 0:
        try:
            log_path = os.path.join(temp_folder_path, "colcon_build_error.log")
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write((build.stdout or "") + "\\n" + (build.stderr or ""))
        except OSError:
            pass
        yield _default
        return

    _kill_stray_publishers()
    launch_proc = subprocess.Popen(
        ["bash", "-c",
         f"{{ROS_SOURCE}} && {{sim_install_source}} && {{install_source}} && "
         f"ros2 launch {{TARGET_PACKAGE}} {{LAUNCH_FILE}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    time.sleep(5)

    results = dict(_default)
    try:
        eval_proc = subprocess.run(
            ["bash", "-c",
             f"{{ROS_SOURCE}} && {{sim_install_source}} && {{install_source}} && "
             f"python3 {{temp_folder_path}}/evaluate.py"],
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
'''


def render_evaluate(q: Question, pkg: SimPackage | None) -> str:
    static_criteria = [ec for ec in q.evaluation_criteria if ec.check not in _RUNTIME_CHECKS]
    runtime_criteria = [ec for ec in q.evaluation_criteria if ec.check in _RUNTIME_CHECKS] if pkg else []

    file_path = q.file_to_edit or (q.files_to_edit[0].path if q.files_to_edit else "node.py")
    file_name = Path(file_path).name

    static_lines = []
    for ec in static_criteria:
        key = _criterion_key(ec)
        needle = ec.target or ec.expected
        if needle:
            static_lines.append(f"        {key!r}: {needle!r} in SRC,")
        else:
            # No concrete needle to check against — fail rather than rubber-stamp.
            static_lines.append(f"        {key!r}: False,  # TODO: no target/expected on {ec.id} — author a real check")
    static_block = "\n".join(static_lines) or "        pass"

    if pkg is None:
        return f'''#!/usr/bin/env python3
"""Auto-generated evaluate.py — static-only checks (no sim dependency).

Question: {q.title}
"""
import json
import sys
from pathlib import Path

FILE_TO_EDIT = {file_name!r}
SRC = Path(FILE_TO_EDIT).read_text(encoding="utf-8") if Path(FILE_TO_EDIT).exists() else ""


def _static_checks() -> dict:
    return {{
{static_block}
    }}


def run_evaluation():
    results = _static_checks()
    passed = all(results.values())
    print(json.dumps({{"status": "completed", "passed": passed, "results": results}}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    run_evaluation()
'''

    runtime_lines = []
    for ec in runtime_criteria:
        key = _criterion_key(ec)
        if ec.check in ("node_exists",):
            runtime_lines.append(f"        {key!r}: {ec.target!r} in node_names,")
        elif ec.check in ("topic_active", "topic_published", "topic_subscribed", "subscriber", "subscription"):
            runtime_lines.append(f"        {key!r}: {ec.target!r} in topic_types,")
        elif ec.check in ("service", "service_exists"):
            runtime_lines.append(f"        {key!r}: {ec.target!r} in service_names,")
    runtime_block = "\n".join(runtime_lines) or "        pass"

    return f'''#!/usr/bin/env python3
"""Auto-generated evaluate.py

Question: {q.title}
Package: {pkg.ros_package}
"""
import json
import os
import sys
from pathlib import Path

import rclpy
from rclpy.node import Node

WORKSPACE_ROOT = Path(os.getcwd())
_PKG_CANDIDATES = [
    WORKSPACE_ROOT / 'src' / {pkg.ros_package!r},
    Path.home() / {pkg.ros_package!r},
]

FILE_TO_EDIT = {file_name!r}


def _find_pkg() -> Path:
    for p in _PKG_CANDIDATES:
        if p.exists():
            return p
    return _PKG_CANDIDATES[0]


def _read(rel: str) -> str:
    pkg = _find_pkg()
    p = pkg / rel
    return p.read_text() if p.exists() else ''


SRC = _read(FILE_TO_EDIT)


def _static_checks() -> dict:
    return {{
{static_block}
    }}


class RuntimeChecker(Node):
    def __init__(self):
        super().__init__('{_slug(q.question_id)}_evaluator')


def run_evaluation():
    static = _static_checks()

    rclpy.init()
    node = RuntimeChecker()
    rclpy.spin_once(node, timeout_sec=3.0)

    node_names = {{n for n, _ in node.get_node_names_and_namespaces()}}
    topic_types = dict(node.get_topic_names_and_types())
    service_names = {{n for n, _ in node.get_service_names_and_types()}}

    runtime = {{
{runtime_block}
    }}

    node.destroy_node()
    rclpy.shutdown()

    results = {{**static, **runtime}}
    passed = all(results.values())
    print(json.dumps({{'status': 'completed', 'passed': passed, 'results': results}}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    run_evaluation()
'''


def render_test_file(q: Question) -> str:
    lines = ["import pytest", "", ""]
    for i, ec in enumerate(q.evaluation_criteria, start=1):
        key = _criterion_key(ec)
        desc = ec.description or f"Verify {ec.check} on {ec.target}"
        lines.append(f"def test_{key}_tc{i}(eval_results):")
        lines.append(f'    """{desc}"""')
        lines.append(f'    assert eval_results.get({key!r}) is True')
        lines.append("")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_sandbox_bundle(q: Question, ros_ws_dir: Path, pkg: SimPackage | None) -> None:
    """Write the 5-file grading bundle flat into ``ros_ws_dir``."""
    ros_ws_dir.mkdir(parents=True, exist_ok=True)
    (ros_ws_dir / "pytest.ini").write_text(PYTEST_INI, encoding="utf-8")
    (ros_ws_dir / "requirements.txt").write_text(REQUIREMENTS_TXT, encoding="utf-8")
    (ros_ws_dir / "conftest.py").write_text(render_conftest(q, pkg), encoding="utf-8")
    (ros_ws_dir / "evaluate.py").write_text(render_evaluate(q, pkg), encoding="utf-8")
    test_name = f"test_{_slug(q.question_id)}.py"
    (ros_ws_dir / test_name).write_text(render_test_file(q), encoding="utf-8")
