"""
coding_agent.tools.handlers
===========================

Concrete implementations for each tool in TOOL_SCHEMAS.

build_handlers() wires them up with the live vectorstore and skill graph so
agents get real answers rather than stubs. Difficulty estimation delegates to
``difficulty_agent.estimate_from_source`` — the single difficulty engine — so
this file has no independent scoring logic of its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..vectorstore import VectorStore
    from ..skill_taxonomy import SkillGraph

from ..agents.difficulty_agent import estimate_from_source
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
    """Difficulty self-check exposed to the generation LLM. Delegates to
    ``difficulty_agent.estimate_from_source`` — the one difficulty engine —
    instead of keeping a second, independent heuristic here."""
    return estimate_from_source(solution_code, declared_difficulty)


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
    tavily_api_key: str = "",
    exa_api_key: str = "",
) -> dict:
    """Return a name→callable dict compatible with ToolRegistry."""
    handlers: dict = {}

    if vectorstore is not None:
        handlers["check_similarity"] = lambda **kw: _check_similarity(vectorstore, **kw)

    if skill_graph is not None:
        handlers["query_skill_graph"] = lambda **kw: _query_skill_graph(skill_graph, **kw)
    else:
        handlers["query_skill_graph"] = lambda **kw: {"error": "skill_graph not available"}

    handlers["estimate_difficulty"] = lambda **kw: _estimate_difficulty(**kw)

    ctx7 = Context7Client()
    handlers["fetch_ros2_docs"] = lambda **kw: _fetch_ros2_docs(ctx7, **kw)

    web = WebSearchClient(tavily_api_key=tavily_api_key, exa_api_key=exa_api_key)
    handlers["search_course_exercises"] = lambda **kw: _search_course_exercises(web, **kw)
    handlers["fetch_course_content"] = lambda **kw: _fetch_course_content(web, **kw)

    return handlers
