"""
Agent 10b — Executable Grading
==============================

The static :class:`AutoGradingAgent` only checks that grading *metadata* exists.
This agent goes further: it **runs** the hidden tests and proves they
discriminate a correct solution from an unsolved scaffold.

For each question it:

1. Materialises the reference solution and the starter scaffold to a temp dir.
2. Generates a self-contained pytest module from the question's declared
   interfaces (topics/services/rates/required rclpy calls). The tests are pure
   static/AST analysis of the source — they do **not** require a live ROS2
   runtime, so they run anywhere pytest is installed.
3. Runs the suite twice:
   * against the **reference solution** — expected to PASS,
   * against the **starter scaffold** — expected to FAIL.
4. A question is *executably verified* only when the reference passes **and**
   the starter fails (``discriminating``). That is the real signal the old
   "≥1 check declared" gate never provided.

Honest degradation (per design decision — soft gate):
* No reference solution (current LLM path) -> ``NO_ARTIFACTS``.
* pytest not importable -> ``SKIPPED_NO_RUNTIME``.
Neither of those blocks approval; only a genuine ``FAIL`` does.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ..schemas import AgentResult, GradingExecution, Question
from .base import BaseAgent

# Map a declared check/interface to the rclpy call a real solution must contain.
_CHECK_TO_API = {
    "topic_exists": "create_publisher",
    "topic_active": "create_publisher",
    "publish_rate": "create_timer",
    "subscriber": "create_subscription",
    "subscription": "create_subscription",
    "service_exists": "create_service",
    "service": "create_service",
    "parameter_set": "declare_parameter",
    "tf_frame_exists": "TransformBroadcaster",
}


def _runtime_available() -> bool:
    try:
        import pytest  # noqa: F401
        return True
    except Exception:
        return False


class ExecutableGradingAgent(BaseAgent):
    name = "executable_grading"

    # ---- artifact extraction ------------------------------------------- #
    def _reference_solution(self, q: Question) -> tuple[str, str] | None:
        """(filename, source) for the reference solution, or None if absent."""
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
        return sorted(apis)

    def _expected_tokens(self, q: Question) -> list[str]:
        """Concrete interface strings (topic/service paths) a solution must reference."""
        toks: set[str] = set()
        for c in q.hidden_checks:
            if c.target.startswith("/"):
                toks.add(c.target)
        for ec in q.evaluation_criteria:
            if ec.target.startswith("/"):
                toks.add(ec.target)
        return sorted(toks)

    # ---- generated test module ----------------------------------------- #
    def _test_module(self, apis: list[str], tokens: list[str], is_python: bool) -> str:
        # Python files get an AST parse + rclpy-call check; YAML/launch/xacro
        # files get a structural sanity check instead (ast.parse would wrongly
        # fail on them). Both share the no-TODO + interface-token discriminators.
        parse_test = (
            "def test_parses():\n    ast.parse(SRC)  # must be valid Python\n"
            if is_python else
            "def test_parses():\n"
            "    assert SRC.strip(), 'config file is empty'\n"
            "    # config files are not Python; a YAML round-trip is best-effort\n"
            "    try:\n"
            "        import yaml; yaml.safe_load(SRC)\n"
            "    except Exception:\n"
            "        pass\n"
        )
        # For Python we analyse the AST so that an API name or interface string
        # sitting in a COMMENT or unrelated identifier cannot satisfy a check —
        # the call must really be invoked and the interface must appear in a real
        # string literal. This closes the "write `# create_publisher` and pass"
        # gaming hole the old substring test had.
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
                "    missing = [t for t in EXPECTED_TOKENS\n"
                "               if not any(t in s for s in _STR_LITERALS)]\n"
                "    assert not missing, (\n"
                "        f'required interfaces not referenced in any string literal: {missing}')\n"
            )
        else:
            impl_test = (
                "def test_implementation_present():\n"
                "    return  # non-Python config: implementation proven via interfaces/no-TODO\n"
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
        return f'''"""Auto-generated executable grading test. Target file: $GRADE_TARGET."""
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

{interfaces_test}'''

    # ---- execution ----------------------------------------------------- #
    def _run_pytest(self, workdir: Path, target_file: Path) -> tuple[bool, str]:
        """Return (all_passed, short_detail).

        The suite runs in a minimal, hardened subprocess: a scrubbed environment
        (no inherited API keys), CPU/address-space/file-size rlimits via a POSIX
        preexec hook, and a wall-clock timeout. This is defence-in-depth for the
        current AST-only tests and a prerequisite before any future variant that
        actually executes candidate code. NOTE: rlimits are not a full sandbox —
        see the author hand-off for container/network isolation.
        """
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             str(workdir / "test_grade.py")],
            cwd=str(workdir),
            env={
                "PATH": _os_environ().get("PATH", "/usr/bin:/bin"),
                "GRADE_TARGET": str(target_file),
                # Generated tests need no third-party plugins; disabling autoload
                # keeps grading hermetic and immune to a broken host plugin set.
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            },
            capture_output=True, text=True, timeout=60,
            preexec_fn=_apply_rlimits if _RLIMITS_SUPPORTED else None,
        )
        passed = proc.returncode == 0
        tail = (proc.stdout or proc.stderr).strip().splitlines()
        return passed, (tail[-1] if tail else "")

    def execute(self, q: Question) -> GradingExecution:
        # Uses AST-based static analysis (ros2_sandbox backend removed)

        if not _runtime_available():
            return GradingExecution(status="SKIPPED_NO_RUNTIME", detail="pytest not importable")

        ref = self._reference_solution(q)
        if ref is None:
            return GradingExecution(
                status="NO_ARTIFACTS", runtime_available=True,
                detail="no reference solution distinct from starter (provider returned none)",
            )

        ref_name, ref_src = ref
        start_name, start_src = self._starter_source(q)
        tokens = self._expected_tokens(q)
        # File-role-aware implementation markers. A launch file is Python but is
        # not a node — it must contain launch actions, not rclpy node calls.
        if ref_name.endswith(".launch.py") or ref_name.endswith("launch.py"):
            apis = ["LaunchDescription", "Node"]
        else:
            apis = self._expected_apis(q)

        is_python = ref_name.endswith(".py")
        with tempfile.TemporaryDirectory(prefix=f"grade_{q.question_id}_") as tmp:
            wd = Path(tmp)
            (wd / "test_grade.py").write_text(
                self._test_module(apis, tokens, is_python), encoding="utf-8")
            ref_path = wd / "reference" / ref_name
            start_path = wd / "starter" / (start_name or ref_name)
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            start_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(ref_src, encoding="utf-8")
            start_path.write_text(start_src, encoding="utf-8")

            ref_pass, ref_detail = self._run_pytest(wd, ref_path)
            start_pass, _ = self._run_pytest(wd, start_path)

        discriminating = ref_pass and not start_pass
        if discriminating:
            status, detail = "PASS", "reference passes, starter fails — tests discriminate"
        elif ref_pass and start_pass:
            status, detail = "FAIL", "starter also passes — tests do not discriminate a solution"
        else:
            status, detail = "FAIL", f"reference solution failed its own tests: {ref_detail}"

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
                # NOTE: we deliberately do NOT flip q.auto_gradable here.
                # `auto_gradable` is the *static* contract ("declares gradable
                # criteria"). A failed execution is routed to the Supervisor,
                # which flags it per-question and drives targeted regeneration —
                # keeping the execution signal authoritative without corrupting
                # the static flag other agents depend on.
            else:
                skipped += 1
        res = self._result(verified=verified, failed=failed, skipped=skipped)
        res.messages.append(
            f"executable grading: {verified} verified, {failed} failed, {skipped} skipped/no-artifacts"
        )
        return res.finish("warn" if failed else "ok")


def _os_environ() -> dict:
    import os
    return dict(os.environ)


try:
    import resource as _resource
    _RLIMITS_SUPPORTED = True
except ImportError:  # non-POSIX
    _RLIMITS_SUPPORTED = False


def _apply_rlimits() -> None:  # pragma: no cover - runs only in the child process
    """Cap CPU seconds, address space and file size in the grading subprocess."""
    _resource.setrlimit(_resource.RLIMIT_CPU, (30, 30))
    _resource.setrlimit(_resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    _resource.setrlimit(_resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
