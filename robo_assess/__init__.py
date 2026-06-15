"""
robo_assess
===========

Production-grade multi-agent system that generates, validates, scores and
approves ROS2 Humble robotics & AI coding assessments.

Public entry points:

    from robo_assess import Orchestrator, AssessmentRequest, Settings
    pkg = Orchestrator().run(AssessmentRequest(topic=..., syllabus=[...]))
"""

from .agents.orchestrator import Orchestrator
from .config import Settings
from .schemas import (
    AssessmentPackage,
    AssessmentRequest,
    Difficulty,
    Question,
)

__version__ = "1.0.0"

__all__ = [
    "Orchestrator",
    "Settings",
    "AssessmentRequest",
    "AssessmentPackage",
    "Question",
    "Difficulty",
    "__version__",
]
