"""
robo_assess.config
==================

Configuration loader. Priority order:
  1. Environment variables (ROBO_* prefix, or provider-specific keys)
  2. YAML config file (config.yaml by default)
  3. Hard-coded defaults

Supported providers (set via ROBO_PROVIDER or provider: in config.yaml):
  openrouter  — OPENROUTER_API_KEY
  anthropic   — ANTHROPIC_API_KEY
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def _load_dotenv(dotenv_path: str = ".env") -> None:
    p = Path(dotenv_path)
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


class Pricing(BaseModel):
    input_per_million_tokens: float = 0.15
    output_per_million_tokens: float = 0.60


class QualityBar(BaseModel):
    min_confidence: float = 85.0
    require_discriminating: bool = True   # executable grading must PASS (ref✓ starter✗)
    require_judge_approve: bool = True     # independent LLM judge must not REJECT
    max_similarity: float = 0.75          # originality ceiling
    require_in_scope: bool = True         # no out-of-syllabus tech
    min_difficulty_fit: float = 0.6       # calibrated vs declared difficulty agreement


class Settings(BaseModel):
    provider: str = "openrouter"
    model: str = "openai/gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2200

    num_questions: int = 6
    difficulty_distribution: dict[str, float] = Field(
        default_factory=lambda: {"easy": 0.30, "medium": 0.50, "hard": 0.20}
    )
    over_generation_factor: float = 1.0
    max_regeneration_attempts: int = 1

    # ---- Coverage -----------------------------------------------------------
    # The supervisor used to demand 100% syllabus coverage while num_questions
    # was fixed at 6 — structurally unsatisfiable on any real syllabus, so every
    # broad-topic run was REJECTED by construction. Coverage is now a *target*
    # fraction, and generation is coverage-driven (each slot is steered at an
    # uncovered skill) and auto-scales the question count so the target is
    # actually reachable.
    coverage_target: float = 0.85         # fraction of syllabus skills that must be tested
    auto_scale_questions: bool = True     # raise num_questions toward skill count to hit target
    max_questions: int = 14               # hard cap so auto-scaling can't explode cost

    generation_concurrency: int = 4

    # ---- Executable grading backend -----------------------------------------
    grading_backend: str = "ast"
    sandbox_docker_bin: str = "docker"
    sandbox_image: str = "ros:humble"
    sandbox_timeout_s: int = 180
    sandbox_warmup_s: float = 5.0
    sandbox_cpus: str = "2"
    sandbox_memory: str = "1g"
    sandbox_pids_limit: int = 256

    # ---- Autonomy / planner -------------------------------------------------
    max_planner_steps: int = 8
    quality_bar: QualityBar = Field(default_factory=QualityBar)

    similarity_reject_threshold: float = 0.75
    min_confidence: float = 85.0
    min_realism_score: int = 60
    enable_llm_judge: bool = False
    critic_batch_size: int = 10

    chunk_size: int = 1000
    chunk_overlap: int = 100
    top_k: int = 3

    # ---- NEW: MD parsing & skills extraction -----
    skills_dir: str = "skills"
    evaluations_dir: str = "evaluations"
    eval_match_min_score: float = 85.0
    max_critic_retries: int = 2
    parser_section_retries: int = 3

    log_level: str = "INFO"
    log_dir: str = "logs"
    log_db_path: str = "logs/runs.db"
    memory_db_path: str = "memory/memory.db"
    vectorstore_path: str = "vectorstore/index.json"
    prompts_dir: str = "prompts"
    outputs_dir: str = "outputs"
    reports_dir: str = "reports"
    calibrator_path: str = "calibration/calibrator.json"
    calibration_observations_path: str = "calibration/observations.jsonl"

    pricing: Pricing = Field(default_factory=Pricing)
    api_key: str | None = None

    @classmethod
    def load(cls, config_path: str | os.PathLike | None = "config/config.yaml") -> "Settings":
        _load_dotenv()
        data: dict[str, Any] = {}
        if config_path and Path(config_path).is_file():
            with open(config_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}

        env = os.environ
        if "ROBO_PROVIDER" in env:
            data["provider"] = env["ROBO_PROVIDER"]
        if "ROBO_MODEL" in env:
            data["model"] = env["ROBO_MODEL"]
        if "ROBO_NUM_QUESTIONS" in env:
            data["num_questions"] = int(env["ROBO_NUM_QUESTIONS"])
        if "ROBO_LOG_LEVEL" in env:
            data["log_level"] = env["ROBO_LOG_LEVEL"]

        settings = cls(**data)

        # Resolve API key from provider-specific env vars
        from .llm_client import _PROVIDERS, resolve_api_key
        provider = settings.provider

        # Validate provider against registry
        if provider not in _PROVIDERS:
            known = ", ".join(sorted(_PROVIDERS))
            raise ValueError(
                f"Unknown provider '{provider}'. Choose from: {known}"
            )

        settings.api_key = resolve_api_key(provider)

        # This is an LLM agent — a provider that needs a key but has none is a
        # hard configuration error. We do NOT silently degrade to a template
        # engine; that path no longer exists.
        cfg = _PROVIDERS[provider]
        if cfg.get("needs_key", True) and not settings.api_key:
            raise RuntimeError(
                f"No API key found for provider '{provider}'. "
                f"Set one of {cfg['env_keys']} in your environment or .env, "
                f"Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY in your .env."
            )

        return settings
