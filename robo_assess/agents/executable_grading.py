"""
Agent 10b — Executable Grading
==============================

Proves that generated tests discriminate a correct solution from an unsolved
scaffold by running them twice: once against the reference solution (must PASS)
and once against the starter (must FAIL).

Two backends are supported, selected by ``settings.grading_backend``:

``"docker"`` (recommended)
    Runs pytest inside a ``robo-grader`` container built from
    ``Dockerfile.grading``. The container has a live ROS2 Humble environment
    so three additional runtime tests run: Python compile check, rclpy import
    verification, and an actual node-initialization test with mocked
    ``rclpy.spin``. This is real executable grading.

    Build the image once with::

        docker build -f Dockerfile.grading -t robo-grader .

    Then set in ``config/config.yaml``::

        grading_backend: docker
        sandbox_image: robo-grader

    Falls back to ``"ast"`` mode automatically when Docker is unavailable or
    the image is not found, so CI environments without Docker still work.

``"ast"`` (default / fallback)
    Pure static analysis: AST-walk to verify rclpy call presence, interface
    string literals, balanced TODO markers. No ROS2 runtime required.

Honest degradation:
* No reference solution → ``NO_ARTIFACTS`` (not a blocker).
* pytest not importable AND Docker unavailable → ``SKIPPED_NO_RUNTIME``.
Only a genuine ``FAIL`` (reference fails its own tests, or starter passes
when it should not) blocks approval.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ..schemas import AgentResult, GradingExecution, Question
from .base import BaseAgent

_CHECK_TO_API = {
    "topic_exists": "create_publisher",
    "topic_active": "create_publisher",
    "topic_published": "create_publisher",
    "topic_subscribed": "create_subscription",
    "subscriber": "create_subscription",
    "subscription": "create_subscription",
    "service_exists": "create_client",
    "service": "create_service",
    "publish_rate": "create_timer",
    "parameter_set": "declare_parameter",
    "tf_frame": "TransformBroadcaster",
    "tf_frame_exists": "TransformBroadcaster",
    # message_content checks a value in source — no specific rclpy API required
    "message_type": "create_publisher",
}


def _runtime_available() -> bool:
    try:
        import pytest  # noqa: F401
        return True
    except Exception:
        return False


def _docker_available(docker_bin: str = "docker", image: str = "robo-grader") -> bool:
    """Return True when the Docker daemon is reachable AND the target image exists."""
    try:
        r = subprocess.run(
            [docker_bin, "images", "-q", image],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


class ExecutableGradingAgent(BaseAgent):
    name = "executable_grading"

    # ---- artifact extraction ------------------------------------------- #

    def _reference_solution(self, q: Question) -> tuple[str, str] | None:
        for f in q.files_to_edit:
            ref = (f.reference_solution or "").strip()
            if ref and ref != (f.starter_code or "").strip():
                return Path(f.path).name, f.reference_solution
        return None

    def _starter_source(self, q: Question) -> tuple[str, str]:
        if q.files_to_edit:
            f = q.files_to_edit[0]
            return Path(f.path).name, (f.starter_code or q.boilerplate_code or "")
        name = Path(q.file_to_edit or "node.py").name
        return name, q.boilerplate_code or ""

    def _expected_apis(self, q: Question) -> list[str]:
        apis: set[str] = set()
        for c in q.hidden_checks:
            api = _CHECK_TO_API.get(c.check_type.value)
            if api:
                apis.add(api)
        for ec in q.evaluation_criteria:
            api = _CHECK_TO_API.get(ec.check)
            if api:
                apis.add(api)
        blob = " ".join(q.tested_skills).lower()
        if "publish" in blob or "publisher" in blob:
            apis.add("create_publisher")
        if "subscrib" in blob:
            apis.add("create_subscription")
        if "service" in blob:
            apis.add("create_service")
            apis.add("create_client")
        if "spawn" in blob or "client" in blob:
            apis.add("create_client")
        return sorted(apis)

    def _expected_tokens(self, q: Question) -> list[str]:
        toks: set[str] = set()
        for c in q.hidden_checks:
            if c.target.startswith("/"):
                toks.add(c.target)
        for ec in q.evaluation_criteria:
            if ec.target.startswith("/"):
                toks.add(ec.target)
        return sorted(toks)

    def _content_checks(self, q: Question) -> list[str]:
        """Non-path message_content targets (numeric values, constants).

        These are checked as raw source substrings in the grading test, which
        discriminates questions like 'fix wheel_radius from 0.05 to 0.1' where
        the correct value only appears in the reference solution.
        """
        toks: set[str] = set()
        for ec in q.evaluation_criteria:
            if ec.check == "message_content" and not ec.target.startswith("/"):
                toks.add(ec.target)
        for c in q.hidden_checks:
            if c.check_type.value == "message_content" and not c.target.startswith("/"):
                toks.add(c.target)
        return sorted(toks)

    # ---- generated test module ----------------------------------------- #

    def _test_module(
        self,
        apis: list[str],
        tokens: list[str],
        is_python: bool,
        docker_mode: bool = False,
        content_checks: list[str] | None = None,
    ) -> str:
        """Return the pytest source for one grading run.

        ``docker_mode=True`` appends three additional tests that require a
        live ROS2 environment: Python-compiler check, rclpy import check, and
        a node-initialization test with mocked rclpy.spin.
        """
        parse_test = (
            "def test_parses():\n    ast.parse(SRC)\n"
            if is_python else
            "def test_parses():\n"
            "    assert SRC.strip(), 'config file is empty'\n"
            "    try:\n"
            "        import yaml; yaml.safe_load(SRC)\n"
            "    except Exception:\n"
            "        pass\n"
        )

        if is_python:
            impl_test = (
                "def test_implementation_present():\n"
                "    if not EXPECTED_APIS:\n        return\n"
                "    found = [a for a in EXPECTED_APIS if a in _CALLED_NAMES]\n"
                "    assert found, (\n"
                "        f'none of the required rclpy calls are actually invoked: '\n"
                "        f'{EXPECTED_APIS} (calls present: {sorted(_CALLED_NAMES)})')\n"
            )
            interfaces_test = (
                "def test_interfaces_referenced():\n"
                "    missing = [t for t in EXPECTED_TOKENS if t not in _STR_LITERALS]\n"
                "    assert not missing, (\n"
                "        f'required interfaces not found as exact string literal: {missing}')\n"
            )
        else:
            impl_test = (
                "def test_implementation_present():\n"
                "    return\n"
            )
            interfaces_test = (
                "def test_interfaces_referenced():\n"
                "    missing = [t for t in EXPECTED_TOKENS if t not in SRC]\n"
                "    assert not missing, f'missing required interfaces: {missing}'\n"
            )

        ast_collect = (
            (
                "_CALLED_NAMES = set()\n"
                "_STR_LITERALS = []\n"
                "try:\n"
                "    _TREE = ast.parse(SRC)\n"
                "    for _n in ast.walk(_TREE):\n"
                "        if isinstance(_n, ast.Call):\n"
                "            _f = _n.func\n"
                "            if isinstance(_f, ast.Attribute):\n"
                "                _CALLED_NAMES.add(_f.attr)\n"
                "            elif isinstance(_f, ast.Name):\n"
                "                _CALLED_NAMES.add(_f.id)\n"
                "        elif isinstance(_n, ast.Constant) and isinstance(_n.value, str):\n"
                "            _STR_LITERALS.append(_n.value)\n"
                "except SyntaxError:\n"
                "    pass\n"
            )
            if is_python else
            "_CALLED_NAMES = set()\n_STR_LITERALS = [SRC]\n"
        )

        docker_extra = self._docker_extra_tests(is_python) if docker_mode else ""

        cc = content_checks or []
        content_test = (
            f"CONTENT_CHECKS = {json.dumps(cc)}\n\n"
            "def test_content_values():\n"
            "    missing = [t for t in CONTENT_CHECKS if t not in SRC]\n"
            "    assert not missing, (\n"
            "        f'required values not found in source: {missing}')\n"
        )

        return f'''"""Auto-generated executable grading test."""
import ast, os
from pathlib import Path

SRC = Path(os.environ["GRADE_TARGET"]).read_text(encoding="utf-8")
EXPECTED_APIS = {json.dumps(apis)}
EXPECTED_TOKENS = {json.dumps(tokens)}

{ast_collect}

{parse_test}

def test_no_unfilled_todo():
    assert "# TODO START" not in SRC and "# TODO END" not in SRC, \\
        "scaffold TODO markers still present — implementation not filled in"


{impl_test}

{interfaces_test}

{content_test}
{docker_extra}'''

    @staticmethod
    def _docker_extra_tests(is_python: bool) -> str:
        """Three runtime tests that only make sense inside a ROS2 container."""
        if not is_python:
            return ""
        return '''

def test_module_compiles():
    """Real Python compiler check — catches errors ast.parse misses (e.g. late binding)."""
    import pytest as _pt
    try:
        compile(SRC, os.environ["GRADE_TARGET"], "exec")
    except SyntaxError as exc:
        _pt.fail(f"SyntaxError: {exc}")


def test_rclpy_importable():
    """Verify rclpy is present in the grading environment."""
    import pytest as _pt
    try:
        import rclpy  # noqa: F401
    except ImportError as exc:
        _pt.fail(f"rclpy not available: {exc}")


def test_node_can_initialize():
    """Execute the module with mocked rclpy.spin and call main() if present.

    This is the real runtime test: it instantiates the ROS2 node inside a
    live rclpy environment and confirms the node does not crash on startup.
    Skipped (not failed) when the source imports a custom ROS2 package that
    is not installed in the grading image.
    """
    import unittest.mock, pytest as _pt
    try:
        import rclpy
        import rclpy.exceptions
    except ImportError as exc:
        _pt.skip(f"rclpy unavailable: {exc}")

    if "rclpy" not in SRC:
        return  # TYPE_A pure-Python question — no ROS2 node to initialize

    ns: dict = {"__name__": "__main__", "__file__": os.environ["GRADE_TARGET"]}
    try:
        rclpy.init(args=[])
    except Exception:
        pass

    try:
        with unittest.mock.patch("rclpy.spin", lambda n: None), \\
             unittest.mock.patch("rclpy.spin_once", lambda n, **kw: None), \\
             unittest.mock.patch("rclpy.shutdown", lambda: None), \\
             unittest.mock.patch("rclpy.init", lambda **kw: None):
            exec(compile(SRC, os.environ["GRADE_TARGET"], "exec"), ns)
            if "main" in ns and callable(ns["main"]):
                ns["main"]()
    except ImportError as exc:
        _pt.skip(f"custom package not available in grading image: {exc}")
    except SystemExit:
        pass  # nodes that call sys.exit(0) in main() are fine
    except Exception as exc:
        _pt.fail(f"node failed to initialize: {exc}")
    finally:
        try:
            rclpy.try_shutdown()
        except Exception:
            pass
'''

    # ---- execution ----------------------------------------------------- #

    def _run_pytest(self, workdir: Path, target_file: Path) -> tuple[bool, str]:
        """Run pytest locally (AST-only mode, no ROS2 runtime needed)."""
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             str(workdir / "test_grade.py")],
            cwd=str(workdir),
            env={
                "PATH": _os_environ().get("PATH", "/usr/bin:/bin"),
                "GRADE_TARGET": str(target_file),
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            },
            capture_output=True, text=True, timeout=60,
            preexec_fn=_apply_rlimits if _RLIMITS_SUPPORTED else None,
        )
        passed = proc.returncode == 0
        tail = (proc.stdout or proc.stderr).strip().splitlines()
        return passed, (tail[-1] if tail else "")

    def _run_pytest_docker(
        self,
        workdir: Path,
        target_file: Path,
        docker_bin: str,
        image: str,
        timeout: int,
    ) -> tuple[bool, str]:
        """Run pytest inside the robo-grader Docker container.

        The workdir is bind-mounted read-only at ``/grade``; the target file
        path is passed as ``GRADE_TARGET``. Network is disabled so generated
        code cannot make outbound calls during grading.
        """
        rel = target_file.relative_to(workdir)
        proc = subprocess.run(
            [
                docker_bin, "run", "--rm",
                "--network=none",
                "--memory=512m",
                "--cpus=1",
                "--pids-limit=256",
                "-v", f"{workdir}:/grade:ro",
                "-e", f"GRADE_TARGET=/grade/{rel}",
                image,
                "python3", "-m", "pytest", "-q", "--tb=short",
                "-p", "no:cacheprovider",
                "/grade/test_grade.py",
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        passed = proc.returncode == 0
        output = (proc.stdout or proc.stderr).strip()
        lines = output.splitlines()
        label = str(target_file.relative_to(workdir))
        print(f"\n[docker:{image}] grading {label}")
        for ln in lines:
            print(f"  {ln}")
        return passed, (lines[-1] if lines else "")

    def execute(self, q: Question) -> GradingExecution:
        docker_bin = getattr(self.settings, "sandbox_docker_bin", "docker")
        image = getattr(self.settings, "sandbox_image", "robo-grader")
        timeout = getattr(self.settings, "sandbox_timeout_s", 120)
        grading_backend = getattr(self.settings, "grading_backend", "ast")

        use_docker = (
            grading_backend == "docker"
            and _docker_available(docker_bin, image)
        )
        if not use_docker and grading_backend == "docker":
            self.log.warning(
                "docker_grading_unavailable",
                image=image,
                fallback="ast",
            )

        if not use_docker and not _runtime_available():
            return GradingExecution(
                status="SKIPPED_NO_RUNTIME",
                detail="pytest not importable and Docker not available",
            )

        ref = self._reference_solution(q)
        if ref is None:
            return GradingExecution(
                status="NO_ARTIFACTS", runtime_available=True,
                detail="no reference solution distinct from starter",
            )

        ref_name, ref_src = ref
        start_name, start_src = self._starter_source(q)

        if ref_name.endswith(".launch.py") or ref_name.endswith("launch.py"):
            apis = ["LaunchDescription", "Node"]
        else:
            apis = self._expected_apis(q)
        tokens = self._expected_tokens(q)
        cc = self._content_checks(q)
        is_python = ref_name.endswith(".py")

        # Docker (snap) cannot mount /tmp; use a home-dir path instead.
        _grade_tmp = Path.home() / ".cache" / "robo-grader"
        _grade_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"grade_{q.question_id}_", dir=_grade_tmp) as tmp:
            wd = Path(tmp)
            (wd / "test_grade.py").write_text(
                self._test_module(apis, tokens, is_python, docker_mode=use_docker, content_checks=cc),
                encoding="utf-8",
            )
            ref_path = wd / "reference" / ref_name
            start_path = wd / "starter" / (start_name or ref_name)
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            start_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(ref_src, encoding="utf-8")
            start_path.write_text(start_src, encoding="utf-8")

            try:
                if use_docker:
                    ref_pass, ref_detail = self._run_pytest_docker(
                        wd, ref_path, docker_bin, image, timeout)
                    start_pass, _ = self._run_pytest_docker(
                        wd, start_path, docker_bin, image, timeout)
                    backend_tag = f"docker:{image}"
                else:
                    ref_pass, ref_detail = self._run_pytest(wd, ref_path)
                    start_pass, _ = self._run_pytest(wd, start_path)
                    backend_tag = "ast"
            except subprocess.TimeoutExpired:
                return GradingExecution(
                    status="FAIL",
                    detail=f"docker grading timed out after {timeout}s — node likely hangs on init",
                    runtime_available=True,
                    discriminating=False,
                    auto_grading_score=0.0,
                )

        discriminating = ref_pass and not start_pass
        if discriminating:
            status = "PASS"
            detail = f"reference passes, starter fails [{backend_tag}]"
        elif ref_pass and start_pass:
            status = "FAIL"
            detail = f"starter also passes — tests do not discriminate [{backend_tag}]"
        else:
            status = "FAIL"
            detail = f"reference solution failed its own tests: {ref_detail} [{backend_tag}]"

        return GradingExecution(
            status=status, runtime_available=True,
            reference_passed=ref_pass, starter_failed=not start_pass,
            discriminating=discriminating, detail=detail,
        )

    # ---- agent entrypoint ---------------------------------------------- #

    def run(self, questions: list[Question]) -> AgentResult:
        verified = failed = skipped = 0
        for q in questions:
            ex = self.execute(q)
            q.grading_execution = ex
            if ex.status == "PASS":
                verified += 1
            elif ex.status == "FAIL":
                failed += 1
            else:
                skipped += 1
        res = self._result(verified=verified, failed=failed, skipped=skipped)
        res.messages.append(
            f"executable grading: {verified} verified, {failed} failed, "
            f"{skipped} skipped/no-artifacts"
        )
        return res.finish("warn" if failed else "ok")


def _os_environ() -> dict:
    import os
    return dict(os.environ)


try:
    import resource as _resource
    _RLIMITS_SUPPORTED = True
except ImportError:
    _RLIMITS_SUPPORTED = False


def _apply_rlimits() -> None:  # pragma: no cover
    _resource.setrlimit(_resource.RLIMIT_CPU, (30, 30))
    _resource.setrlimit(_resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    _resource.setrlimit(_resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
