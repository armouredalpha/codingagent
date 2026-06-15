"""Shared pytest fixtures and path setup for the robo_assess test-suite.

This is an LLM agent — there is no offline mode. Tests therefore inject a
deterministic ``FakeLLM`` double instead of calling a real provider, which is
the standard way to test an LLM pipeline reproducibly and without network.
"""
import itertools
import json
import sys
from pathlib import Path

import pytest

# Ensure the repo root is importable when pytest is run from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from robo_assess.config import Settings  # noqa: E402
from robo_assess.llm_client import TokenUsage  # noqa: E402


import re  # noqa: E402

# Per-ROS-primitive spec: the rclpy call a real solution must invoke, the node
# class/name, the interface string, and a distinct scenario seed. Keeping these
# genuinely different is what keeps batch similarity below the originality bar.
_PRIMITIVES = [
    ("publish", "create_publisher", "from geometry_msgs.msg import Twist",
     "VelocityPublisher", "/cmd_vel", "Twist", "topic_active",
     "stream velocity commands to the drive base"),
    ("subscrib", "create_subscription", "from sensor_msgs.msg import LaserScan",
     "ScanMonitor", "/scan", "LaserScan", "topic_active",
     "react to laser scans for obstacle avoidance"),
    ("service", "create_service", "from std_srvs.srv import SetBool",
     "GripperService", "/set_gripper", "SetBool", "service_exists",
     "expose a service that toggles the gripper"),
    ("param", "declare_parameter", "from rcl_interfaces.msg import SetParametersResult",
     "SpeedLimiter", "/max_speed", "double", "parameter_set",
     "read a speed limit from a ROS parameter"),
    ("tf", "TransformBroadcaster", "from tf2_ros import TransformBroadcaster",
     "FramePublisher", "/tf", "TransformStamped", "tf_frame_exists",
     "broadcast a TF frame for the sensor mount"),
    ("launch", "create_publisher", "from std_msgs.msg import String",
     "Heartbeat", "/heartbeat", "String", "topic_active",
     "publish a periodic heartbeat for the supervisor"),
]
_DOMAINS = ["warehouse", "inspection", "factory", "delivery", "agriculture", "mining"]
_ROBOTS = ["TurtleBot3 Burger", "Clearpath Husky", "UR10e", "Warehouse AMR",
           "Franka Panda", "TurtleBot4"]


def _spec_for(skill: str):
    s = skill.lower()
    for prim in _PRIMITIVES:
        if prim[0] in s:
            return prim
    return _PRIMITIVES[0]


class FakeLLM:
    """Deterministic stand-in for a *competent* provider.

    Unlike a trivial stub, this double reads the skill and difficulty out of the
    filled prompt and emits questions that are (a) genuinely varied across the
    batch — distinct ROS primitive, robot, domain, topic, message — so they clear
    the originality bar, and (b) difficulty-calibrated — the reference solution's
    line-count and skill-count scale with the requested difficulty so the
    calibrator agrees. The reference invokes the required rclpy call and
    references the interface string, so ExecutableGradingAgent's discrimination
    check (reference passes, starter fails) is exercised for real.

    ``complete_json`` returns an empty ``results`` array so every LLM critic and
    the planner judge cleanly fall back to deterministic scoring — runs stay
    reproducible and offline.
    """

    provider = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self._counter = itertools.count(1)

    @staticmethod
    def _parse(user: str, key: str, default: str) -> str:
        m = re.search(rf"{key}:\s*(.+)", user)
        return m.group(1).strip() if m else default

    def complete(self, system, user, temperature=0.4, max_tokens=4000):
        i = next(self._counter)
        skill = self._parse(user, "skill", "ROS2 publisher")
        difficulty = self._parse(user, "difficulty", "easy").split()[0].lower()
        kw, api, imp, cls, topic, msg, check, blurb = _spec_for(skill)
        domain = _DOMAINS[i % len(_DOMAINS)]
        robot = _ROBOTS[i % len(_ROBOTS)]
        node_name = cls.lower()

        # Difficulty-scaled body: extra skills + line-count so the calibrator
        # (n_skills / LOC / multi-file) re-derives the declared difficulty.
        # Scale only the solution size with difficulty (the calibrator reads LOC +
        # bloom). tested_skills stays = [skill] so coverage is not diluted by
        # off-syllabus sub-skills — difficulty comes from the bloom floor, not from
        # inventing extra skills the syllabus never asked for.
        pad_methods = {"easy": 0, "medium": 2, "hard": 6}[difficulty]
        tested = [skill]

        qjson = {
            "title": f"{cls}: {blurb} for the {domain} {robot} (#{i})",
            "robot": robot,
            "scenario": (
                f"On a {domain} site, a {robot} runs a half-finished {node_name} "
                f"node. To {blurb}, the {kw} path on {topic} must be completed so "
                f"the {domain} fleet behaves correctly in scenario {i}."
            ),
            "objective": f"Implement the {node_name} so it uses {api} on {topic} ({msg}).",
            "file_to_edit": f"{node_name}/{node_name}.py",
            "constraints": [f"Use rclpy and {api}", f"Operate on {topic}",
                            f"Set the question in the {domain} domain"],
            "common_mistakes": ["Forgetting to spin the node", f"Wrong message type for {topic}"],
            "estimated_solve_minutes": {"easy": 20, "medium": 40, "hard": 75}[difficulty],
            "tested_skills": tested,
            "evaluation_criteria": [
                {"id": "EC1", "check": check, "target": topic, "expected": msg,
                 "points": 40, "description": f"uses {api} on {topic}"},
                {"id": "EC2", "check": "node_exists", "target": node_name,
                 "expected": "running", "points": 30, "description": f"{node_name} node present"},
                {"id": "EC3", "check": check, "target": topic, "expected": msg,
                 "points": 30, "description": f"{topic} carries {msg}"},
            ],
        }

        starter = (
            "import rclpy\n"
            "from rclpy.node import Node\n\n"
            f"class {cls}(Node):\n"
            f"    def __init__(self):\n"
            f"        super().__init__('{node_name}')\n"
            "        # TODO START\n"
            "        pass\n"
            "        # TODO END\n"
        )

        pad = "".join(
            f"\n    def _helper_{k}(self):\n"
            f"        # supporting logic for {tested[k % len(tested)]}\n"
            f"        return {k}\n"
            for k in range(pad_methods)
        )
        reference = (
            "import rclpy\n"
            "from rclpy.node import Node\n"
            f"{imp}\n\n"
            f"class {cls}(Node):\n"
            f'    """Reference solution: {blurb}."""\n\n'
            f"    def __init__(self):\n"
            f"        super().__init__('{node_name}')\n"
            f"        self.handle = self.{api}({msg}, '{topic}', 10) "
            f"if '{api}' != 'declare_parameter' else self.{api}('{topic}', 1.0)\n"
            f"        self.get_logger().info('{node_name} ready on {topic}')\n"
            f"{pad}\n"
            "    def tick(self):\n"
            f"        # drive the {topic} interface\n"
            "        pass\n"
        )

        text = (
            json.dumps(qjson)
            + "\n---STARTER_FILE---\n"
            + starter
            + "\n---REFERENCE_FILE---\n"
            + reference
        )
        return text, TokenUsage(input_tokens=120, output_tokens=240, model=self.model)

    def complete_json(self, system, user, **kw):
        return {"results": []}, TokenUsage(input_tokens=60, output_tokens=10, model=self.model)


@pytest.fixture()
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture(autouse=True)
def _inject_fake_llm(monkeypatch):
    """Make every Orchestrator built in the suite use a fresh FakeLLM instead of
    constructing a real provider client."""
    import robo_assess.agents.orchestrator as orch_mod

    monkeypatch.setattr(orch_mod, "make_client", lambda settings: FakeLLM())


@pytest.fixture()
def tmp_settings(tmp_path: Path) -> Settings:
    """Settings pointed entirely at a throwaway temp directory. The provider is
    cosmetic here because the orchestrator's client is replaced with FakeLLM."""
    s = Settings()
    s.provider = "openrouter"
    s.log_db_path = str(tmp_path / "runs.db")
    s.memory_db_path = str(tmp_path / "memory.db")
    s.vectorstore_path = str(tmp_path / "vec.json")
    s.outputs_dir = str(tmp_path / "outputs")
    s.reports_dir = str(tmp_path / "reports")
    s.calibrator_path = str(tmp_path / "calibration" / "calibrator.json")
    s.calibration_observations_path = str(tmp_path / "calibration" / "observations.jsonl")
    return s
