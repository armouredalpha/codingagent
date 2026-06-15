"""
robo_assess.guardrails
======================

Loads guardrail_rules.yaml and rejection_patterns.yaml from the guardrails/
directory and exposes typed, agent-ready config objects.

Agents import GuardrailConfig and call GuardrailConfig.load() once. The result
is cached so multiple agents in the same process share a single loaded copy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Typed sub-configs (one per agent that reads guardrails)
# ---------------------------------------------------------------------------

@dataclass
class BoilerplateRules:
    require_todo_start: bool = True
    require_todo_end: bool = True
    require_balanced: bool = True
    require_reference_differs: bool = True
    reference_must_not_contain_todo: bool = True
    min_todo_blocks_per_file: int = 1
    action_on_fail: str = "REJECT"


@dataclass
class ScopeRules:
    gated_technologies: dict[str, list[str]] = field(default_factory=dict)
    action_on_violation: str = "REJECT"


@dataclass
class OriginalityRules:
    similarity_reject_threshold: float = 0.75
    compare_against_existing_bank: bool = True
    compare_within_batch: bool = True
    compare_against_memory: bool = True


@dataclass
class DifficultyRules:
    easy_max_skills: int = 1
    easy_max_solution_loc: int = 35
    medium_max_skills: int = 3
    medium_max_solution_loc: int = 90
    bloom_to_difficulty: dict[str, str] = field(default_factory=lambda: {
        "remember": "easy", "understand": "easy", "apply": "medium",
        "analyze": "medium", "evaluate": "hard", "create": "hard",
    })


@dataclass
class RealismRules:
    min_score: int = 60
    required_domains: list[str] = field(default_factory=lambda: [
        "warehouse", "inspection", "factory", "delivery", "rover",
        "conveyor", "patrol",
    ])
    toy_phrases_penalty: list[str] = field(default_factory=lambda: [
        "hello world", "foo", "bar", "example_topic", "test_node", "lorem",
    ])


@dataclass
class GradingRules:
    require_auto_gradable: bool = True
    min_hidden_checks: int = 3
    min_hidden_tests: int = 3
    required_test_kinds: list[str] = field(default_factory=lambda: [
        "positive", "negative", "edge",
    ])


@dataclass
class ConfidenceRules:
    min_confidence_score: float = 85.0
    weights: dict[str, int] = field(default_factory=lambda: {
        "coverage": 20, "difficulty": 20, "originality": 15,
        "scope": 15, "auto_grading": 15, "format_quality": 15,
    })


@dataclass
class SupervisorRules:
    min_validation_score: int = 80
    require_full_coverage: bool = True
    require_at_least_one_approved: bool = True
    # Coverage is judged against this target fraction rather than a hard 100%.
    # require_full_coverage is honoured by treating it as coverage_target = 1.0
    # when explicitly set; otherwise this value governs the gate.
    coverage_target: float = 0.85


@dataclass
class RejectionPatterns:
    theory_question_patterns: list[str] = field(default_factory=list)
    incomplete_solution_patterns: list[str] = field(default_factory=list)
    deprecated_api_patterns: list[str] = field(default_factory=list)
    toy_code_patterns: list[str] = field(default_factory=list)
    non_gradable_check_patterns: list[str] = field(default_factory=list)

    def is_theory_question(self, text: str) -> tuple[bool, str]:
        low = text.lower()
        for p in self.theory_question_patterns:
            if p in low:
                return True, p
        return False, ""

    def has_incomplete_solution(self, code: str) -> tuple[bool, str]:
        for p in self.incomplete_solution_patterns:
            if p in code:
                return True, p
        return False, ""

    def has_deprecated_api(self, code: str) -> tuple[bool, str]:
        for p in self.deprecated_api_patterns:
            if p in code:
                return True, p
        return False, ""

    def has_toy_code(self, code: str) -> tuple[bool, str]:
        low = code.lower()
        for p in self.toy_code_patterns:
            if p in low:
                return True, p
        return False, ""


@dataclass
class GuardrailConfig:
    boilerplate: BoilerplateRules = field(default_factory=BoilerplateRules)
    scope: ScopeRules = field(default_factory=ScopeRules)
    originality: OriginalityRules = field(default_factory=OriginalityRules)
    difficulty: DifficultyRules = field(default_factory=DifficultyRules)
    realism: RealismRules = field(default_factory=RealismRules)
    grading: GradingRules = field(default_factory=GradingRules)
    confidence: ConfidenceRules = field(default_factory=ConfidenceRules)
    supervisor: SupervisorRules = field(default_factory=SupervisorRules)
    rejection: RejectionPatterns = field(default_factory=RejectionPatterns)

    @classmethod
    def load(cls, guardrails_dir: str = "guardrails") -> "GuardrailConfig":
        return _load_cached(guardrails_dir)


# ---------------------------------------------------------------------------
# Cached loader
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_cached(guardrails_dir: str) -> GuardrailConfig:
    return _load(guardrails_dir)


def _load(guardrails_dir: str) -> GuardrailConfig:
    base = Path(guardrails_dir)
    rules_raw: dict[str, Any] = {}
    patterns_raw: dict[str, Any] = {}

    rules_path = base / "guardrail_rules.yaml"
    if rules_path.is_file():
        rules_raw = yaml.safe_load(rules_path.read_text()) or {}

    patterns_path = base / "rejection_patterns.yaml"
    if patterns_path.is_file():
        patterns_raw = yaml.safe_load(patterns_path.read_text()) or {}

    cfg = GuardrailConfig()

    # --- boilerplate ---
    b = rules_raw.get("boilerplate", {})
    cfg.boilerplate = BoilerplateRules(
        require_todo_start=b.get("require_todo_start_marker", True),
        require_todo_end=b.get("require_todo_end_marker", True),
        require_balanced=b.get("require_balanced_markers", True),
        require_reference_differs=b.get("require_reference_differs_from_starter", True),
        reference_must_not_contain_todo=b.get("reference_must_not_contain_todo", True),
        min_todo_blocks_per_file=b.get("min_todo_blocks_per_file", 1),
        action_on_fail=b.get("action_on_fail", "REJECT"),
    )

    # --- scope ---
    s = rules_raw.get("scope", {})
    cfg.scope = ScopeRules(
        gated_technologies=s.get("gated_technologies", {}),
        action_on_violation=s.get("action_on_violation", "REJECT"),
    )

    # --- originality ---
    o = rules_raw.get("originality", {})
    cfg.originality = OriginalityRules(
        similarity_reject_threshold=o.get("similarity_reject_threshold", 0.75),
        compare_against_existing_bank=o.get("compare_against_existing_bank", True),
        compare_within_batch=o.get("compare_within_batch", True),
        compare_against_memory=o.get("compare_against_memory", True),
    )

    # --- difficulty ---
    d = rules_raw.get("difficulty", {})
    cfg.difficulty = DifficultyRules(
        easy_max_skills=d.get("easy_max_skills", 1),
        easy_max_solution_loc=d.get("easy_max_solution_loc", 35),
        medium_max_skills=d.get("medium_max_skills", 3),
        medium_max_solution_loc=d.get("medium_max_solution_loc", 90),
        bloom_to_difficulty=d.get("bloom_to_difficulty", {
            "remember": "easy", "understand": "easy", "apply": "medium",
            "analyze": "medium", "evaluate": "hard", "create": "hard",
        }),
    )

    # --- realism ---
    r = rules_raw.get("realism", {})
    cfg.realism = RealismRules(
        min_score=r.get("min_score", 60),
        required_domains=r.get("required_domains", [
            "warehouse", "inspection", "factory", "delivery", "rover",
            "conveyor", "patrol",
        ]),
        toy_phrases_penalty=r.get("toy_phrases_penalty", [
            "hello world", "foo", "bar", "example_topic", "test_node", "lorem",
        ]),
    )

    # --- grading ---
    g = rules_raw.get("grading", {})
    cfg.grading = GradingRules(
        require_auto_gradable=g.get("require_auto_gradable", True),
        min_hidden_checks=g.get("min_hidden_checks", 3),
        min_hidden_tests=g.get("min_hidden_tests", 3),
        required_test_kinds=g.get("required_test_kinds", ["positive", "negative", "edge"]),
    )

    # --- confidence ---
    c = rules_raw.get("confidence", {})
    cfg.confidence = ConfidenceRules(
        min_confidence_score=c.get("min_confidence_score", 85.0),
        weights=c.get("weights", {
            "coverage": 20, "difficulty": 20, "originality": 15,
            "scope": 15, "auto_grading": 15, "format_quality": 15,
        }),
    )

    # --- supervisor ---
    sv = rules_raw.get("supervisor", {})
    cfg.supervisor = SupervisorRules(
        min_validation_score=sv.get("min_validation_score", 80),
        require_full_coverage=sv.get("require_full_coverage", True),
        require_at_least_one_approved=sv.get("require_at_least_one_approved", True),
        coverage_target=float(sv.get("coverage_target", 0.85)),
    )

    # --- rejection patterns ---
    cfg.rejection = RejectionPatterns(
        theory_question_patterns=patterns_raw.get("theory_question_patterns", []),
        incomplete_solution_patterns=patterns_raw.get("incomplete_solution_patterns", []),
        deprecated_api_patterns=patterns_raw.get("deprecated_api_patterns", []),
        toy_code_patterns=patterns_raw.get("toy_code_patterns", []),
        non_gradable_check_patterns=patterns_raw.get("non_gradable_check_patterns", []),
    )

    return cfg
