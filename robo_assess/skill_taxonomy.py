"""
Skill Taxonomy: Graph of skills with prerequisite relationships.

Enables:
- Prerequisite validation (ensure required skills are in syllabus)
- Curriculum design (sequence skills by dependencies)
- Completeness checking (catch skill gaps)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .schemas import SkillEntry


@dataclass
class SkillNode:
    """Node in the skill dependency graph."""

    name: str
    difficulty: str  # easy, medium, hard
    bloom_level: str  # understand, apply, analyze, evaluate, create
    section: str  # which markdown section
    prerequisites: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)  # skills that depend on this


class SkillGraph:
    """Directed acyclic graph (DAG) of skill prerequisites."""

    def __init__(self):
        self.skills: dict[str, SkillNode] = {}
        self.edges: list[tuple[str, str]] = []  # (required_by, requires)

    def add_skill(self, name: str, difficulty: str, bloom_level: str, section: str):
        """Add a skill node to the graph."""
        if name not in self.skills:
            self.skills[name] = SkillNode(
                name=name, difficulty=difficulty, bloom_level=bloom_level, section=section
            )

    def add_prerequisite(self, skill_name: str, prerequisite_name: str):
        """Add edge: skill_name requires prerequisite_name.

        Example: "design launch file" requires "create publisher node"
        """
        if skill_name not in self.skills or prerequisite_name not in self.skills:
            raise ValueError(
                f"Both skills must exist: {skill_name}, {prerequisite_name}"
            )

        self.skills[skill_name].prerequisites.add(prerequisite_name)
        self.skills[prerequisite_name].dependents.add(skill_name)
        self.edges.append((skill_name, prerequisite_name))

        # Validate no cycles
        if self._has_cycle():
            raise ValueError(
                f"Adding prerequisite would create cycle: {skill_name} requires {prerequisite_name}"
            )

    def get_prerequisites(
        self, skill_name: str, transitive: bool = True
    ) -> set[str]:
        """Get all prerequisites for a skill (direct or transitive).

        Args:
            skill_name: The skill to query
            transitive: If True, include all transitive prerequisites; if False, only direct

        Returns: Set of prerequisite skill names
        """
        if skill_name not in self.skills:
            return set()

        if not transitive:
            return self.skills[skill_name].prerequisites.copy()

        # DFS to find all transitive prerequisites
        visited = set()
        result = set()

        def dfs(skill: str):
            if skill in visited:
                return
            visited.add(skill)
            for prereq in self.skills[skill].prerequisites:
                result.add(prereq)
                dfs(prereq)

        dfs(skill_name)
        return result

    def get_dependents(self, skill_name: str, transitive: bool = True) -> set[str]:
        """Get all skills that depend on this one (direct or transitive).

        Args:
            skill_name: The skill to query
            transitive: If True, include all transitive dependents; if False, only direct

        Returns: Set of skill names that depend on this one
        """
        if skill_name not in self.skills:
            return set()

        if not transitive:
            return self.skills[skill_name].dependents.copy()

        # DFS to find all transitive dependents
        visited = set()
        result = set()

        def dfs(skill: str):
            if skill in visited:
                return
            visited.add(skill)
            for dependent in self.skills[skill].dependents:
                result.add(dependent)
                dfs(dependent)

        dfs(skill_name)
        return result

    def validate_coverage(
        self, syllabus_skills: list[str], question_skill: str
    ) -> tuple[bool, set[str]]:
        """Check if all prerequisites are in the syllabus for a given question skill.

        Args:
            syllabus_skills: List of skills in the curriculum
            question_skill: Skill being tested in the question

        Returns: (is_valid, missing_prerequisites)
        """
        required = self.get_prerequisites(question_skill, transitive=True)
        required.add(question_skill)  # Question skill must also be in syllabus

        missing = required - set(syllabus_skills)
        is_valid = len(missing) == 0

        return is_valid, missing

    def _has_cycle(self) -> bool:
        """Detect cycle using DFS. Returns True if cycle exists."""
        visited = {}  # 0: unvisited, 1: in_progress, 2: visited

        def has_cycle_dfs(skill: str) -> bool:
            if skill not in visited:
                visited[skill] = 0

            if visited[skill] == 1:  # Found back edge
                return True

            if visited[skill] == 2:  # Already completed
                return False

            visited[skill] = 1

            for prereq in self.skills[skill].prerequisites:
                if has_cycle_dfs(prereq):
                    return True

            visited[skill] = 2
            return False

        for skill in self.skills:
            if visited.get(skill, 0) == 0:
                if has_cycle_dfs(skill):
                    return True

        return False

    def topological_sort(self) -> list[str]:
        """Return skills in topological order (prerequisites before dependents).

        Useful for curriculum sequencing.
        """
        visited = set()
        stack = []

        def dfs(skill: str):
            if skill in visited:
                return
            visited.add(skill)

            for prereq in self.skills[skill].prerequisites:
                dfs(prereq)

            stack.append(skill)

        for skill in self.skills:
            dfs(skill)

        return stack

    def build_from_skills(self, skill_entries: list[SkillEntry]):
        """Populate graph from SkillEntry list."""
        for entry in skill_entries:
            self.add_skill(
                entry.skill, entry.difficulty_hint, entry.bloom_level, entry.section
            )

        # Infer prerequisites from skill names (heuristic)
        # Example: "implement callback" requires "create subscriber"
        self._infer_prerequisites()

    def _infer_prerequisites(self):
        """Infer prerequisite edges from ROS2 concept-keyword dependencies.

        Each rule is a (dependent_keywords, requires_keywords) pair: if a skill
        name contains ALL words in dependent_keywords, it requires any skill whose
        name contains ALL words in requires_keywords.  Rules are grounded in the
        actual ROS2 API dependency chain rather than English verb patterns
        ("implement" → "create") which break when skill names don't follow that
        exact phrasing.

        Ordering matters — simpler concepts must appear before advanced ones so
        the prerequisite graph reflects the curriculum sequence a student would
        actually follow.
        """
        # (dependent_signal, prerequisite_signal)
        # signal = tuple of lowercase substrings ALL of which must appear in the skill name
        _CONCEPT_RULES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
            # Subscriber presupposes understanding topics via publisher
            (("subscriber",),          ("publisher",)),
            (("subscription",),        ("publisher",)),
            # Service client presupposes knowing there is a server to call
            (("service", "client"),    ("service", "server")),
            (("call", "service"),      ("service", "server")),
            # Service server presupposes pub/sub for context
            (("service", "server"),    ("publisher",)),
            # Action client presupposes action server; action server presupposes services
            (("action", "client"),     ("action", "server")),
            (("action", "server"),     ("service", "server")),
            # TF2 listener needs broadcaster to exist first
            (("tf2", "listener"),      ("tf2", "broadcaster")),
            (("lookup", "transform"),  ("tf2", "broadcaster")),
            (("tf2", "buffer"),        ("tf2", "broadcaster")),
            # Parameter callbacks/events require knowing how to declare parameters
            (("parameter", "callback"), ("parameter", "declare")),
            (("parameter", "event"),    ("parameter", "declare")),
            (("on_set_parameters",),    ("parameter", "declare")),
            # QoS tuning requires knowing the transport it is applied to
            (("qos", "subscriber"),    ("subscriber",)),
            (("qos", "publisher"),     ("publisher",)),
            (("reliability", "policy"), ("publisher",)),
            # Lifecycle nodes build on plain nodes
            (("lifecycle",),           ("publisher",)),
            (("managed", "node"),      ("publisher",)),
            # Composable / component nodes assume pub/sub
            (("component",),           ("publisher",)),
            (("composition",),         ("publisher",)),
            # Launch files orchestrate nodes that already exist
            (("launch", "file"),       ("publisher",)),
            (("launch", "file"),       ("subscriber",)),
            (("launch", "node"),       ("publisher",)),
            # Error handling / retry logic sits on top of the base pattern
            (("error", "publisher"),   ("publisher",)),
            (("error", "subscriber"),  ("subscriber",)),
            (("error", "service"),     ("service", "server")),
            (("retry",),               ("publisher",)),
            # Timer-based publishing requires a publisher to exist
            (("timer", "publish"),     ("publisher",)),
            (("periodic", "publish"),  ("publisher",)),
            # Odometry / sensor fusion chains
            (("odometry", "publish"),  ("publisher",)),
            (("sensor", "fusion"),     ("subscriber",)),
            (("imu", "publish"),       ("publisher",)),
        ]

        skill_names = list(self.skills.keys())
        skill_lowers = {s: s.lower() for s in skill_names}

        def _matches(skill_lower: str, signal: tuple[str, ...]) -> bool:
            return all(kw in skill_lower for kw in signal)

        for dep_signal, req_signal in _CONCEPT_RULES:
            # Find all skills that are dependents (match dep_signal)
            dependents = [s for s in skill_names if _matches(skill_lowers[s], dep_signal)]
            # Find all skills that are prerequisites (match req_signal)
            prereqs = [s for s in skill_names if _matches(skill_lowers[s], req_signal)]

            for dep in dependents:
                for pre in prereqs:
                    if dep == pre:
                        continue
                    try:
                        self.add_prerequisite(dep, pre)
                    except ValueError:
                        pass  # cycle would form — skip

    def get_curriculum_path(self, skills_to_learn: list[str]) -> list[str]:
        """Get optimal order to learn a set of skills (respecting prerequisites).

        Returns: Ordered list of skills with prerequisites before dependents
        """
        # Create subgraph with only requested skills
        all_prerequisite_skills = set(skills_to_learn)
        for skill in skills_to_learn:
            all_prerequisite_skills.update(self.get_prerequisites(skill))

        # Topological sort within subgraph
        visited = set()
        stack = []

        def dfs(skill: str):
            if skill in visited or skill not in all_prerequisite_skills:
                return
            visited.add(skill)

            for prereq in self.skills[skill].prerequisites:
                if prereq in all_prerequisite_skills:
                    dfs(prereq)

            stack.append(skill)

        for skill in skills_to_learn:
            dfs(skill)

        return stack

    def to_dict(self) -> dict:
        """Export graph as dictionary for persistence."""
        return {
            "skills": {
                name: {
                    "difficulty": node.difficulty,
                    "bloom_level": node.bloom_level,
                    "section": node.section,
                    "prerequisites": list(node.prerequisites),
                }
                for name, node in self.skills.items()
            },
            "edges": [{"from": f, "to": t} for f, t in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> SkillGraph:
        """Restore graph from dictionary."""
        graph = cls()

        # Add all skills first
        for skill_name, skill_data in data.get("skills", {}).items():
            graph.add_skill(
                skill_name,
                skill_data["difficulty"],
                skill_data["bloom_level"],
                skill_data["section"],
            )

        # Add edges
        for edge in data.get("edges", []):
            try:
                graph.add_prerequisite(edge["from"], edge["to"])
            except ValueError:
                pass  # Skip invalid edges

        return graph
