"""
Structural tests for the LangGraph pipeline.

These tests verify that the graph compiles correctly and has the right shape —
no LLM calls, no Qdrant connection. End-to-end pipeline tests (which require
real OpenRouter + Qdrant credentials) must be run manually.
"""
from __future__ import annotations

import pytest

from robo_assess.graph import AssessmentState, build_assessment_graph
from robo_assess.graph.state import AssessmentState as _StateCheck


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

def test_assessment_state_has_required_keys():
    """AssessmentState TypedDict must define all pipeline-required keys."""
    required = {
        "run_id", "request",
        "analysis", "coverage", "skill_entries", "summary_text", "skillset",
        "context_pack", "triage",
        "questions", "quality", "feedback", "attempts", "step",
        "budget_tokens", "budget_calls",
        "pkg", "error",
    }
    annotations = _StateCheck.__annotations__
    missing = required - set(annotations.keys())
    assert not missing, f"AssessmentState is missing keys: {missing}"


# ---------------------------------------------------------------------------
# Graph structure
# ---------------------------------------------------------------------------

def test_graph_package_imports():
    """robo_assess.graph package exports must be importable."""
    from robo_assess.graph import AssessmentState, build_assessment_graph  # noqa: F401
    assert AssessmentState is not None
    assert build_assessment_graph is not None


def test_graph_compiles(tmp_settings):
    """Graph must compile without errors."""
    from robo_assess.agents.orchestrator import Orchestrator
    from unittest.mock import patch, MagicMock

    # Stub the Qdrant connection only — no LLM mocking
    with patch("robo_assess.agents.orchestrator.VectorStore") as MockVS:
        MockVS.from_settings.return_value = MagicMock()
        orch = Orchestrator(tmp_settings)
        graph = orch._build_graph()

    assert graph is not None


def test_graph_cached_on_second_call(tmp_settings):
    """_build_graph() must return the same compiled instance on every call."""
    from robo_assess.agents.orchestrator import Orchestrator
    from unittest.mock import patch, MagicMock

    with patch("robo_assess.agents.orchestrator.VectorStore") as MockVS:
        MockVS.from_settings.return_value = MagicMock()
        orch = Orchestrator(tmp_settings)
        g1 = orch._build_graph()
        g2 = orch._build_graph()

    assert g1 is g2


def test_graph_nodes_present(tmp_settings):
    """All 7 expected nodes must be wired into the compiled graph."""
    from robo_assess.agents.orchestrator import Orchestrator
    from unittest.mock import patch, MagicMock

    with patch("robo_assess.agents.orchestrator.VectorStore") as MockVS:
        MockVS.from_settings.return_value = MagicMock()
        orch = Orchestrator(tmp_settings)
        graph = orch._build_graph()

    node_names = set(graph.get_graph().nodes.keys())
    expected = {
        "build_context", "retrieve_context", "generate",
        "validate", "reflect", "regenerate", "supervise",
    }
    assert expected.issubset(node_names), f"Missing nodes: {expected - node_names}"


def test_graph_none_before_first_run(tmp_settings):
    """_graph must be None until _build_graph() is called."""
    from robo_assess.agents.orchestrator import Orchestrator
    from unittest.mock import patch, MagicMock

    with patch("robo_assess.agents.orchestrator.VectorStore") as MockVS:
        MockVS.from_settings.return_value = MagicMock()
        orch = Orchestrator(tmp_settings)

    assert orch._graph is None


def test_nodes_module_importable():
    """graph.nodes must import without errors."""
    from robo_assess.graph.nodes import make_nodes  # noqa: F401
    assert callable(make_nodes)


def test_builder_module_importable():
    """graph.builder must import without errors."""
    from robo_assess.graph.builder import build_assessment_graph  # noqa: F401
    assert callable(build_assessment_graph)
