"""
robo_assess.agents.base
=======================

Common base class for every worker agent. Each agent owns a name, a reference
to ``Settings``, optional ``LLMClient`` / ``Memory`` / ``VectorStore`` handles,
and returns an :class:`~robo_assess.schemas.AgentResult` envelope so the
Orchestrator and Supervisor can validate hand-offs structurally.
"""

from __future__ import annotations

from typing import Any, Optional

from ..config import Settings
from ..llm_client import LLMClient
from ..logging_utils import get_logger
from ..memory import Memory
from ..schemas import AgentResult
from ..vectorstore import VectorStore


class BaseAgent:
    name: str = "base"

    def __init__(
        self,
        settings: Settings,
        llm: Optional[LLMClient] = None,
        memory: Optional[Memory] = None,
        vectorstore: Optional[VectorStore] = None,
    ) -> None:
        self.settings = settings
        self.llm = llm
        self.memory = memory
        self.vectorstore = vectorstore
        self.log = get_logger(f"agent.{self.name}")

    def _result(self, **payload: Any) -> AgentResult:
        return AgentResult(agent=self.name, payload=payload)

    def run(self, *args, **kwargs) -> AgentResult:  # pragma: no cover - abstract
        raise NotImplementedError
