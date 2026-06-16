"""Tests for the single-command v2 generate flow (run_generate_v2 + export_run_v2).

Uses a deterministic LLM double (extends the suite's FakeLLM generation path)
so the run is reproducible and offline. Web originality is disabled.
"""
from __future__ import annotations

import yaml

from robo_assess.agents.orchestrator import Orchestrator
from robo_assess.workflows.assessment_workflow import export_run_v2
from tests.conftest import FakeLLM


_SUMMARY_MD = """## ROS2 Publishers and Subscribers
Create a ROS2 publisher node. Create a ROS2 subscriber node. Use rclpy timers.

## ROS2 Services
Implement a ROS2 service server. Implement a ROS2 service client.
"""

_SKILLS = [
    {"skill": "Create a ROS2 publisher node", "bloom_level": "create", "difficulty": "easy"},
    {"skill": "Create a ROS2 subscriber node", "bloom_level": "create", "difficulty": "easy"},
    {"skill": "Implement a ROS2 service server", "bloom_level": "create", "difficulty": "medium"},
    {"skill": "Implement a ROS2 service client", "bloom_level": "create", "difficulty": "medium"},
    {"skill": "Design a ROS2 launch file", "bloom_level": "create", "difficulty": "hard"},
    {"skill": "Use TF2 transforms", "bloom_level": "create", "difficulty": "hard"},
]


class V2FakeLLM(FakeLLM):
    """Adds summary + skill-extraction + judge behaviour on top of the base
    question-generation double."""

    def complete(self, system, user, temperature=0.4, max_tokens=4000):
        if "curriculum analyst" in (system or "").lower():
            from robo_assess.llm_client import TokenUsage
            return _SUMMARY_MD, TokenUsage(input_tokens=50, output_tokens=80, model=self.model)
        return super().complete(system, user, temperature, max_tokens)

    def complete_json(self, system, user, **kw):
        from robo_assess.llm_client import TokenUsage
        usage = TokenUsage(input_tokens=40, output_tokens=20, model=self.model)
        if "Extract 3-7 skills" in user:
            return _SKILLS, usage
        if "selected_skill" in user:
            # skill picker: choose the first matching skill name in the list
            import re
            names = re.findall(r"- (.+?) \(section", user)
            return {"selected_skill": names[0] if names else _SKILLS[0]["skill"]}, usage
        if "primarily test" in user:
            return {"passes": True, "reason": "matches"}, usage
        if "Could this student solve" in user:
            return {"probability": 0.7, "note": "ok"}, usage
        return {"results": []}, usage


def test_run_generate_v2(tmp_settings, tmp_path, monkeypatch):
    md = tmp_path / "ros2_fundamentals.md"
    md.write_text(_SUMMARY_MD, encoding="utf-8")

    tmp_settings.enable_web_originality = False
    tmp_settings.skills_dir = str(tmp_path / "skills")
    tmp_settings.log_dir = str(tmp_path)
    tmp_settings.students_path = "config/students.yaml"

    orch = Orchestrator(settings=tmp_settings, llm=V2FakeLLM())
    pkg = orch.run_generate_v2(md)

    # Exactly 3 questions, one per difficulty
    assert len(pkg.questions) == 3
    diffs = sorted(q.difficulty.value for q in pkg.questions)
    assert diffs == ["easy", "hard", "medium"]

    # Export and verify the on-disk structure
    out_dir = export_run_v2(
        pkg,
        summary_text=getattr(pkg, "_summary_text", ""),
        skillset=getattr(pkg, "_skillset", None),
        out_root=str(tmp_path / "outputs"),
    )

    assert (out_dir / "summary.md").exists()
    assert (out_dir / "skills.yaml").exists()
    skills_doc = yaml.safe_load((out_dir / "skills.yaml").read_text())
    assert len(skills_doc["skills"]) >= 3

    qdirs = sorted((out_dir / "questions").iterdir())
    assert len(qdirs) == 3
    for qd in qdirs:
        qy = yaml.safe_load((qd / "question.yaml").read_text())
        sy = yaml.safe_load((qd / "solution.yaml").read_text())
        assert qy["question_id"] == sy["question_id"]
        assert qy["evaluation_criteria"]["primary_skill"]["weight"] == 70
        assert "starter_code" in qy
        assert (qd / "boilerplate").is_dir()
        assert (qd / "evaluation" / "grading.json").exists()
        assert any((qd / "evaluation").glob("test_*.py"))

    assert (out_dir / "reports" / "supervisor_verdict.json").exists()
    assert (out_dir / "reports" / "confidence_report.json").exists()
