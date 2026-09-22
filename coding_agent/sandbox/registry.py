"""
Sim package registry
=====================

Loads ``config/sim_packages.yaml`` — the catalog of pre-built simulation_ws
robot-model packages a question's ros_ws can launch against. Students never
edit simulation_ws; it's a shared, reusable dependency, distinct from the
per-question ros_ws/src/<pkg> that the generator produces.

Adding a new robot model is a YAML entry, not a code change — everything
downstream (harness generation, question generation) reads through this
loader.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class EditableFileSpec(BaseModel):
    path: str
    role: str = ""


class SimPackage(BaseModel):
    id: str
    robot_model: str
    sim_workspace: str
    student_workspace: str = "ros_ws"
    ros_package: str
    launch_file: str
    domain_tags: list[str] = Field(default_factory=list)
    editable_files: list[EditableFileSpec] = Field(default_factory=list)
    known_nodes: list[str] = Field(default_factory=list)
    known_topics: list[str] = Field(default_factory=list)
    known_services: list[str] = Field(default_factory=list)


def load_sim_packages(path: str | Path = "config/sim_packages.yaml") -> list[SimPackage]:
    """Return all registry entries, or [] if the file is absent/empty.

    Absent file is not an error — callers must treat an empty registry as
    "no sim dependency available" and degrade to a static-only harness,
    same honesty pattern as the rest of the pipeline (NO_ARTIFACTS,
    SKIPPED_NO_RUNTIME, etc).
    """
    p = Path(path)
    if not p.is_file():
        return []
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or []
    return [SimPackage(**entry) for entry in raw]


def find_sim_package(packages: list[SimPackage], sim_package_id: str) -> SimPackage | None:
    return next((p for p in packages if p.id == sim_package_id), None)


def match_sim_package(packages: list[SimPackage], text: str) -> SimPackage | None:
    """Return the registry entry whose domain_tags appear most often as
    substrings of ``text`` (typically a skill name plus surrounding topic
    vocabulary, lowercased by the caller or not — matching is case-insensitive).

    Substring matching (not exact token-set overlap) because skill names are
    full phrases ("Implement AMCL localization for patrol robot") while
    domain_tags are short keywords ("amcl", "localization") — exact-set
    matching would almost never fire.

    Returns None (not a guess) when no domain_tag matches at all — a pure-math
    skill like "quaternion rotation formula" should get no sim dependency,
    not an arbitrary one.
    """
    if not packages or not text:
        return None
    haystack = text.lower()
    best: SimPackage | None = None
    best_score = 0
    for pkg in packages:
        score = sum(1 for tag in pkg.domain_tags if tag.lower() in haystack)
        if score > best_score:
            best, best_score = pkg, score
    return best
