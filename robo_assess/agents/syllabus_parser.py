"""
Agent 1 — Syllabus Parser
=========================

Extracts skills, concepts, APIs, config elements and ROS components from the raw
syllabus. Rule-based first (token-efficient, cacheable); when a provider is
online the LLM path enriches the extraction. Any LLM failure falls back to the
rule-based result, so offline behaviour is unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas import AgentResult, AssessmentRequest, SyllabusAnalysis
from ..memory import syllabus_key
from .base import BaseAgent

# Knowledge tables -----------------------------------------------------------
_API_HINTS = {
    "publisher": ["create_publisher", "geometry_msgs/Twist"],
    "subscriber": ["create_subscription", "sensor_msgs"],
    "service": ["create_service", "std_srvs/SetBool"],
    "client": ["create_client"],
    "parameter": ["declare_parameter", "get_parameter"],
    "launch": ["LaunchDescription", "launch_ros.actions.Node"],
    "tf2": ["TransformBroadcaster", "tf2_ros", "TransformStamped"],
    "timer": ["create_timer"],
    "urdf": ["robot_description", "xacro"],
    "gazebo": ["gazebo_ros", "spawn_entity"],
    "navigation": ["nav_msgs", "OccupancyGrid", "Path"],
    "sensor": ["LaserScan", "Range", "Image"],
}
_ROS_COMPONENTS = {
    "publisher": "topic_publisher",
    "subscriber": "topic_subscriber",
    "service": "service_server",
    "client": "service_client",
    "launch": "launch_file",
    "parameter": "parameter_server",
    "tf2": "tf_tree",
    "gazebo": "simulation",
    "urdf": "robot_model",
}
_CONFIG_HINTS = ["parameter", "launch", "yaml", "urdf", "xacro", "config"]

_SYSTEM_PROMPT = (
    "You are the Syllabus Parser Agent for a ROS2 Humble assessment pipeline. "
    "Return ONLY valid JSON, no markdown, no prose."
)


def _load_prompt(prompts_dir: str) -> str | None:
    p = Path(prompts_dir) / "syllabus_parser.txt"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _flatten_components(value) -> list[str]:
    """The prompt returns ros_components as a dict of categories; the schema
    stores a flat list[str]. Accept either shape."""
    if isinstance(value, dict):
        out: list[str] = []
        for items in value.values():
            out.extend(str(i) for i in (items or []))
        return out
    if isinstance(value, list):
        return [str(i) for i in value]
    return []


class SyllabusParserAgent(BaseAgent):
    name = "syllabus_parser"

    def __init__(self, *args, token_counter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_counter = token_counter

    # ------------------------------------------------------------------ #
    def _rule_based(self, request: AssessmentRequest) -> SyllabusAnalysis:
        skills = list(dict.fromkeys(request.syllabus))  # de-dup, keep order
        concepts: list[str] = []
        apis: list[str] = []
        config_elements: list[str] = []
        ros_components: list[str] = []

        for skill in skills:
            low = skill.lower()
            for hint, api_list in _API_HINTS.items():
                if hint in low:
                    apis.extend(api_list)
                    concepts.append(hint)
            for hint, comp in _ROS_COMPONENTS.items():
                if hint in low:
                    ros_components.append(comp)
            for cfg in _CONFIG_HINTS:
                if cfg in low:
                    config_elements.append(cfg)

        return SyllabusAnalysis(
            skills=skills,
            concepts=list(dict.fromkeys(concepts)) or skills,
            apis=list(dict.fromkeys(apis)),
            config_elements=list(dict.fromkeys(config_elements)),
            ros_components=list(dict.fromkeys(ros_components)),
            difficulty_range="easy-hard",
        )

    def _llm_enrich(self, request: AssessmentRequest) -> SyllabusAnalysis | None:
        """Return an LLM-derived analysis, or None on any failure."""
        if self.llm is None:
            return None
        template = _load_prompt(self.settings.prompts_dir)
        if not template:
            return None
        try:
            user = template.replace("{topic}", request.topic).replace(
                "{syllabus}", "\n".join(f"* {s}" for s in request.syllabus)
            )
            raw, usage = self.llm.complete_json(
                system=_SYSTEM_PROMPT,
                user=user,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
            )
            if self.token_counter:
                self.token_counter.record(self.name, usage, topic=request.topic)

            skills = [str(s) for s in raw.get("skills", [])] or list(
                dict.fromkeys(request.syllabus)
            )
            return SyllabusAnalysis(
                skills=skills,
                concepts=[str(c) for c in raw.get("concepts", [])] or skills,
                apis=[str(a) for a in raw.get("apis", [])],
                config_elements=[str(c) for c in raw.get("config_elements", [])],
                ros_components=_flatten_components(raw.get("ros_components")),
                difficulty_range=str(raw.get("difficulty_range") or "easy-hard"),
            )
        except Exception as exc:  # noqa: BLE001 — fall back to rule-based
            self.log.warning("syllabus_llm_failed", error=str(exc))
            return None

    # ------------------------------------------------------------------ #
    def run(self, request: AssessmentRequest) -> AgentResult:
        key = syllabus_key(request.topic, request.syllabus)
        if self.memory:
            cached = self.memory.get_analysis(key)
            if cached:
                self.log.info("syllabus_cache_hit", key=key)
                res = self._result(analysis=cached)
                res.messages.append("cache hit")
                return res.finish()

        analysis = self._llm_enrich(request)
        source = "llm"
        if analysis is None:
            analysis = self._rule_based(request)
            source = "rule-based"

        if self.memory:
            self.memory.put_analysis(key, analysis.model_dump())

        res = self._result(analysis=analysis.model_dump())
        res.messages.append(f"parsed {len(analysis.skills)} skills ({source})")
        return res.finish()
