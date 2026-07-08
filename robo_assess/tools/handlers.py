"""
robo_assess.tools.handlers
===========================

Concrete implementations for each tool in TOOL_SCHEMAS.

build_handlers() wires them up with the live vectorstore, guardrail config,
skill graph, and confidence scorer so agents get real answers rather than stubs.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..vectorstore import VectorStore
    from ..skill_taxonomy import SkillGraph
    from ..guardrails import GuardrailConfig

from .external_search import Context7Client, WebSearchClient


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------

def _check_similarity(vectorstore: "VectorStore", question_text: str) -> dict:
    try:
        results = vectorstore.search(question_text, top_k=3)
        if not results:
            return {"similarity_score": 0.0, "closest_title": "", "verdict": "original"}
        top = results[0]
        score = top.get("score", 0.0)
        title = top.get("title", "")
        return {
            "similarity_score": round(score, 3),
            "closest_title": title,
            "verdict": "duplicate" if score >= 0.75 else "similar" if score >= 0.5 else "original",
            "top_matches": [{"title": r.get("title", ""), "score": round(r.get("score", 0), 3)} for r in results],
        }
    except Exception as exc:
        return {"error": str(exc), "similarity_score": 0.0, "verdict": "unknown"}


def _validate_guardrails(config: "GuardrailConfig", **kwargs) -> dict:
    title: str = kwargs.get("title", "")
    difficulty: str = kwargs.get("difficulty", "easy")
    solution_loc: int = kwargs.get("solution_loc", 0)
    tested_skills: list = kwargs.get("tested_skills", [])
    uses_technologies: list = kwargs.get("uses_technologies", [])

    checks_passed = []
    checks_failed = []

    # Difficulty LOC check
    diff_rules = config.difficulty
    loc_limits = {"easy": diff_rules.easy_max_solution_loc, "medium": diff_rules.medium_max_solution_loc}
    if difficulty in loc_limits and solution_loc > 0:
        limit = loc_limits[difficulty]
        if solution_loc <= limit:
            checks_passed.append(f"solution_loc_ok ({solution_loc}<={limit})")
        else:
            checks_failed.append(f"solution_loc_exceeded ({solution_loc}>{limit})")

    # Skill count check
    skill_limits = {"easy": diff_rules.easy_max_skills, "medium": diff_rules.medium_max_skills}
    if difficulty in skill_limits and tested_skills:
        limit = skill_limits[difficulty]
        if len(tested_skills) <= limit:
            checks_passed.append(f"skill_count_ok ({len(tested_skills)}<={limit})")
        else:
            checks_failed.append(f"skill_count_exceeded ({len(tested_skills)}>{limit})")

    # Scope compliance
    gated = config.scope.gated_technologies
    for tech, patterns in gated.items():
        tech_lower = tech.lower()
        text_to_scan = " ".join(uses_technologies).lower()
        if any(p.lower() in text_to_scan for p in patterns) or tech_lower in text_to_scan:
            checks_failed.append(f"gated_technology:{tech}")

    if not checks_failed:
        checks_passed.append("scope_clear")

    return {
        "passed": checks_passed,
        "failed": checks_failed,
        "verdict": "PASS" if not checks_failed else "FAIL",
    }


def _query_skill_graph(skill_graph: "SkillGraph", query_type: str, skill_name: str = "", skills_list: list | None = None) -> dict:
    if query_type == "prerequisites":
        prereqs = skill_graph.get_prerequisites(skill_name, transitive=True)
        return {"skill": skill_name, "prerequisites": sorted(prereqs)}

    if query_type == "dependents":
        deps = skill_graph.get_dependents(skill_name, transitive=True)
        return {"skill": skill_name, "dependents": sorted(deps)}

    if query_type == "curriculum_path":
        path = skill_graph.get_curriculum_path(skills_list or [])
        return {"ordered_path": path}

    if query_type == "validate_coverage":
        if not skill_name or not skills_list:
            return {"error": "skill_name and skills_list required for validate_coverage"}
        valid, missing = skill_graph.validate_coverage(skills_list, skill_name)
        return {
            "skill": skill_name,
            "valid": valid,
            "missing_prerequisites": sorted(missing),
        }

    return {"error": f"Unknown query_type: {query_type}"}


def _estimate_difficulty(solution_code: str, declared_difficulty: str) -> dict:
    """Heuristic difficulty estimate from Python AST analysis."""
    try:
        tree = ast.parse(solution_code)
    except SyntaxError:
        # non-Python or unparseable — fall back to LOC only
        tree = None

    loc = len([l for l in solution_code.splitlines() if l.strip() and not l.strip().startswith("#")])

    ros2_apis = len(re.findall(
        r"(create_publisher|create_subscription|create_service|create_client|"
        r"create_timer|spin_once|spin|get_parameter|declare_parameter|"
        r"create_action_server|create_action_client)",
        solution_code,
    ))

    complexity = 0
    if tree:
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler)):
                complexity += 1

    if loc <= 35 and complexity <= 3 and ros2_apis <= 2:
        estimated = "easy"
    elif loc <= 90 and complexity <= 8 and ros2_apis <= 5:
        estimated = "medium"
    else:
        estimated = "hard"

    return {
        "loc": loc,
        "cyclomatic_complexity": complexity,
        "ros2_api_calls": ros2_apis,
        "estimated_difficulty": estimated,
        "declared_difficulty": declared_difficulty,
        "mismatch": estimated != declared_difficulty,
    }


_GATED_PATTERNS = {
    "Nav2": ["nav2", "navigation2", "nav_msgs/Path", "nav_msgs/OccupancyGrid"],
    "SLAM": ["slam_toolbox", "cartographer", "slam", "map_server"],
    "MoveIt": ["moveit", "move_group", "planning_scene"],
    "OpenCV": ["cv2", "opencv", "cv_bridge", "sensor_msgs/Image"],
}


def _check_scope_compliance(question_text: str, solution_code: str = "", allowed_scope: str = "") -> dict:
    combined = (question_text + " " + solution_code).lower()
    violations = []
    for tech, patterns in _GATED_PATTERNS.items():
        if any(p.lower() in combined for p in patterns):
            violations.append(tech)

    return {
        "violations": violations,
        "compliant": len(violations) == 0,
        "verdict": "PASS" if not violations else "FAIL",
    }


def _compute_confidence(
    auto_grading_score: float,
    originality_score: float,
    format_quality_score: float,
    difficulty: str,
    coverage_pct: float = 80.0,
    question_id: str = "",
) -> dict:
    from ..guardrails import GuardrailConfig
    gr = GuardrailConfig.load()
    threshold = gr.confidence.min_confidence_score
    w = gr.confidence.weights  # keys: coverage, difficulty, originality, scope, auto_grading, format_quality

    diff_score = {"easy": 60.0, "medium": 80.0, "hard": 100.0}.get(difficulty, 70.0)
    scope_score = 100.0  # caller has already run check_scope_compliance if needed

    breakdown = {
        "coverage": coverage_pct,
        "difficulty": diff_score,
        "originality": originality_score,
        "scope": scope_score,
        "auto_grading": auto_grading_score,
        "format": format_quality_score,
    }
    # Map guardrail weight keys (format_quality) to breakdown keys (format)
    key_map = {"format_quality": "format"}
    total = sum(
        breakdown.get(key_map.get(k, k), 0.0) * (v / 100.0)
        for k, v in w.items()
        if key_map.get(k, k) in breakdown
    )
    return {
        "question_id": question_id,
        "total_score": round(total, 2),
        "breakdown": breakdown,
        "threshold": threshold,
        "verdict": "APPROVED" if total >= threshold else "NEEDS_IMPROVEMENT",
        "gap": max(0.0, round(threshold - total, 2)),
    }


# ---------------------------------------------------------------------------
# External search handlers
# ---------------------------------------------------------------------------

def _fetch_ros2_docs(ctx7: Context7Client, library_name: str, query: str) -> dict:
    library_id = ctx7.resolve_library_id(library_name)
    return ctx7.query_docs(library_id, query)


def _search_course_exercises(
    web: WebSearchClient,
    query: str,
    course_filter: str = "",
    max_results: int = 5,
) -> dict:
    return web.search_course_exercises(query, course_filter=course_filter, max_results=max_results)


def _fetch_course_content(web: WebSearchClient, url: str, max_chars: int = 4000) -> dict:
    return web.fetch_course_content(url, max_chars=max_chars)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_handlers(
    vectorstore: Any = None,
    skill_graph: Any = None,
    guardrail_config: Any = None,
    tavily_api_key: str = "",
    exa_api_key: str = "",
) -> dict:
    """Return a name→callable dict compatible with ToolRegistry."""
    handlers: dict = {}

    if vectorstore is not None:
        handlers["check_similarity"] = lambda **kw: _check_similarity(vectorstore, **kw)

    handlers["validate_guardrails"] = (
        (lambda **kw: _validate_guardrails(guardrail_config, **kw))
        if guardrail_config is not None
        else lambda **kw: {"error": "guardrail_config not available"}
    )

    if skill_graph is not None:
        handlers["query_skill_graph"] = lambda **kw: _query_skill_graph(skill_graph, **kw)
    else:
        handlers["query_skill_graph"] = lambda **kw: {"error": "skill_graph not available"}

    handlers["estimate_difficulty"] = lambda **kw: _estimate_difficulty(**kw)
    handlers["check_scope_compliance"] = lambda **kw: _check_scope_compliance(**kw)
    handlers["compute_confidence"] = lambda **kw: _compute_confidence(**kw)

    ctx7 = Context7Client()
    handlers["fetch_ros2_docs"] = lambda **kw: _fetch_ros2_docs(ctx7, **kw)

    web = WebSearchClient(tavily_api_key=tavily_api_key, exa_api_key=exa_api_key)
    handlers["search_course_exercises"] = lambda **kw: _search_course_exercises(web, **kw)
    handlers["fetch_course_content"] = lambda **kw: _fetch_course_content(web, **kw)

    return handlers
