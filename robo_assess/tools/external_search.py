"""
robo_assess.tools.external_search
==================================

HTTP clients for external resources:
  - Context7Client  — fetches ROS2 library docs from GitHub
  - WebSearchClient — searches robotics course exercises (Tavily API or static index)

Both degrade gracefully: failures return an error dict, never crash the pipeline.
"""

from __future__ import annotations

import os
from typing import Any

import requests

_TIMEOUT = 10

# Maps common library names to their GitHub repos for doc fetching
_LIB_REPO_MAP: dict[str, str] = {
    "rclpy": "ros2/rclpy",
    "rclcpp": "ros2/rclcpp",
    "geometry_msgs": "ros2/common_interfaces",
    "sensor_msgs": "ros2/common_interfaces",
    "nav_msgs": "ros2/common_interfaces",
    "std_msgs": "ros2/common_interfaces",
    "action_msgs": "ros2/rcl_interfaces",
    "tf2_ros": "ros2/geometry2",
    "tf2": "ros2/geometry2",
    "numpy": "numpy/numpy",
    "ros2": "ros2/ros2",
    "launch": "ros2/launch",
    "ros2cli": "ros2/ros2cli",
}

_BRANCH_ORDER = ["humble", "rolling", "main", "master"]


class Context7Client:
    """Context7-style library documentation fetcher.

    Fetches README / API docs from GitHub for known ROS2 / Python packages.
    Mirrors the intent of the Context7 MCP tool (resolve-library-id +
    query-docs) using direct GitHub raw content requests.
    """

    def resolve_library_id(self, library_name: str) -> str:
        lib = library_name.lower().strip()
        for key, repo in _LIB_REPO_MAP.items():
            if key in lib or lib in key:
                return f"github.com/{repo}"
        return f"github.com/ros2/{lib.replace(' ', '_')}"

    def query_docs(self, library_id: str, query: str, max_tokens: int = 4000) -> dict[str, Any]:
        """Fetch README/docs for the library and return relevant sections."""
        repo = library_id.replace("github.com/", "").strip("/")
        char_limit = max_tokens * 4  # rough chars-per-token estimate

        for branch in _BRANCH_ORDER:
            for doc_path in ["README.md", "README.rst", "docs/index.rst", "CHANGELOG.rst"]:
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/{doc_path}"
                try:
                    resp = requests.get(url, timeout=_TIMEOUT)
                    if resp.status_code == 200:
                        return {
                            "library": library_id,
                            "source": url,
                            "branch": branch,
                            "content": resp.text[:char_limit],
                            "query": query,
                        }
                except requests.RequestException:
                    continue

        return {
            "library": library_id,
            "content": "",
            "note": "Documentation not found on GitHub",
            "query": query,
        }


# ---------------------------------------------------------------------------
# WebSearchClient — course exercise search + URL fetcher
# ---------------------------------------------------------------------------

_TAVILY_URL = "https://api.tavily.com/search"
_EXA_URL = "https://api.exa.ai/search"

# Domains to bias course exercise searches toward
_COURSE_DOMAINS = [
    "docs.ros.org",
    "github.com",
    "rsl.ethz.ch",
    "theconstructsim.com",
    "robotacademy.net.au",
    "wiki.ros.org",
    "automaticaddison.com",
]


class WebSearchClient:
    """Search robotics course exercises via web API or built-in index.

    Priority:
      1. Tavily API  (TAVILY_API_KEY or settings.tavily_api_key)
      2. Exa API     (EXA_API_KEY    or settings.exa_api_key)
      3. Static course index (always available, no keys needed)
    """

    def __init__(self, tavily_api_key: str = "", exa_api_key: str = "") -> None:
        self.tavily_key = tavily_api_key or os.environ.get("TAVILY_API_KEY", "")
        self.exa_key = exa_api_key or os.environ.get("EXA_API_KEY", "")

    # ------------------------------------------------------------------ #

    def search_course_exercises(
        self,
        query: str,
        course_filter: str = "",
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Return exercises from robotics courses matching the query.

        Returns:
            {
              "results": [{"title", "description", "difficulty", "skills", "url", "source"}, ...],
              "query": str,
              "source": "tavily" | "exa" | "static_index",
            }
        """
        if self.tavily_key:
            result = self._tavily_search(query, course_filter, max_results)
            if result.get("results"):
                return result

        if self.exa_key:
            result = self._exa_search(query, course_filter, max_results)
            if result.get("results"):
                return result

        return self._static_search(query, max_results)

    def fetch_course_content(self, url: str, max_chars: int = 4000) -> dict[str, Any]:
        """Fetch the text content of a URL.

        Automatically converts github.com/…/blob/… links to raw.githubusercontent.com.
        Returns {"url", "content", "length", "truncated"} or {"url", "error", "content": ""}.
        """
        raw_url = self._to_raw_github(url)
        try:
            resp = requests.get(raw_url, timeout=_TIMEOUT, headers={"User-Agent": "robo_assess/1.0"})
            if resp.status_code == 200:
                text = resp.text
                return {
                    "url": raw_url,
                    "content": text[:max_chars],
                    "length": len(text),
                    "truncated": len(text) > max_chars,
                }
            return {"url": raw_url, "error": f"HTTP {resp.status_code}", "content": ""}
        except requests.RequestException as exc:
            return {"url": raw_url, "error": str(exc), "content": ""}

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_raw_github(url: str) -> str:
        if "github.com" in url and "raw.githubusercontent.com" not in url:
            url = url.replace("github.com", "raw.githubusercontent.com")
            url = url.replace("/blob/", "/")
        return url

    def _tavily_search(self, query: str, course_filter: str, max_results: int) -> dict:
        search_q = f"ROS2 programming exercise lab {query}"
        if course_filter:
            search_q = f"{course_filter} {search_q}"
        try:
            resp = requests.post(
                _TAVILY_URL,
                json={
                    "api_key": self.tavily_key,
                    "query": search_q,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_domains": _COURSE_DOMAINS,
                },
                timeout=_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = [
                    {
                        "title": r.get("title", ""),
                        "description": r.get("content", "")[:600],
                        "url": r.get("url", ""),
                        "source": "web:tavily",
                        "difficulty": "",
                        "skills": [],
                    }
                    for r in data.get("results", [])
                ]
                return {"results": results, "query": query, "source": "tavily"}
        except Exception:
            pass
        return {"results": [], "query": query, "source": "tavily_failed"}

    def _exa_search(self, query: str, course_filter: str, max_results: int) -> dict:
        search_q = f"ROS2 robotics programming exercise {query}"
        if course_filter:
            search_q = f"{course_filter} {search_q}"
        try:
            resp = requests.post(
                _EXA_URL,
                headers={"x-api-key": self.exa_key, "Content-Type": "application/json"},
                json={
                    "query": search_q,
                    "numResults": max_results,
                    "includeDomains": _COURSE_DOMAINS,
                    "useAutoprompt": True,
                },
                timeout=_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = [
                    {
                        "title": r.get("title", ""),
                        "description": r.get("text", "")[:600] if "text" in r else r.get("url", ""),
                        "url": r.get("url", ""),
                        "source": "web:exa",
                        "difficulty": "",
                        "skills": [],
                    }
                    for r in data.get("results", [])
                ]
                return {"results": results, "query": query, "source": "exa"}
        except Exception:
            pass
        return {"results": [], "query": query, "source": "exa_failed"}

    def _static_search(self, query: str, max_results: int) -> dict:
        from .course_index import COURSE_EXERCISES, score_exercise
        query_lower = query.lower()
        scored = sorted(
            ((score_exercise(ex, query_lower), ex) for ex in COURSE_EXERCISES),
            key=lambda x: -x[0],
        )
        top = [ex for score, ex in scored if score > 0][:max_results]
        if not top:
            top = [ex for _, ex in scored[:max_results]]
        return {"results": top, "query": query, "source": "static_index"}
