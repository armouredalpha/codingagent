"""
robo_assess.llm_client
=====================

LLM wrapper supporting two providers:

  openrouter  — OpenAI-compatible endpoint at openrouter.ai
  anthropic   — Anthropic Claude API (native SDK)

Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY in .env (or environment).

Provider     Model examples
-----------  -----------------------------------------------
openrouter   openai/gpt-4o, anthropic/claude-sonnet-4-6
anthropic    claude-haiku-4-5-20251001, claude-sonnet-4-6
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Optional

from .logging_utils import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, dict] = {
    "openrouter": {
        "compat": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "env_keys": ["OPENROUTER_API_KEY", "ROBO_OPENROUTER_KEY"],
        "needs_key": True,
    },
    "anthropic": {
        "compat": "anthropic",
        "base_url": None,
        "env_keys": ["ANTHROPIC_API_KEY"],
        "needs_key": True,
    },
}


def _resolve_base_url(provider: str) -> str:
    """Return the effective base_url for a provider."""
    return _PROVIDERS[provider]["base_url"] or ""


def resolve_api_key(provider: str) -> str | None:
    """Return the first matching env-var value for a provider, or None."""
    cfg = _PROVIDERS.get(provider, {})
    for key in cfg.get("env_keys", []):
        val = os.environ.get(key)
        if val:
            return val
    return os.environ.get("ROBO_API_KEY")  # universal fallback


# ---------------------------------------------------------------------------
# JSON helpers (shared across all providers)
# ---------------------------------------------------------------------------

def _fix_triple_quotes(text: str) -> str:
    def _escape_content(m: re.Match) -> str:
        content = m.group(1)
        content = content.replace("\\", "\\\\")
        content = content.replace('"', '\\"')
        content = content.replace("\n", "\\n")
        content = content.replace("\r", "\\r")
        content = content.replace("\t", "\\t")
        return '"' + content + '"'
    return re.sub(r'"""(.*?)"""', _escape_content, text, flags=re.DOTALL)


def _sanitize_llm_json(text: str) -> str:
    if '"""' in text:
        text = _fix_triple_quotes(text)
    result = []
    in_str = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\" and in_str:
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_str = not in_str
            result.append(ch)
            continue
        if in_str and ch == "\n":
            result.append("\\n")
            continue
        if in_str and ch == "\r":
            result.append("\\r")
            continue
        if in_str and ch == "\t":
            result.append("\\t")
            continue
        result.append(ch)
    return "".join(result)


# ---------------------------------------------------------------------------
# Core classes
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "none"

    def cost(self, in_per_m: float, out_per_m: float) -> float:
        return (
            self.input_tokens / 1_000_000 * in_per_m
            + self.output_tokens / 1_000_000 * out_per_m
        )


class LLMClient:
    def __init__(
        self,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        backoff: float = 2.0,
    ) -> None:
        if provider not in _PROVIDERS:
            known = ", ".join(sorted(_PROVIDERS))
            raise ValueError(f"Unknown provider '{provider}'. Choose from: {known}")
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff = backoff
        self._client = None
        # complete() is called concurrently by the question generator's thread
        # pool; guard the lazy client construction so two threads don't race to
        # build it. The underlying OpenAI/Anthropic SDK clients are safe to
        # share across threads once built.
        self._client_lock = threading.Lock()

    @property
    def _compat(self) -> str:
        return _PROVIDERS[self.provider]["compat"]

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        with self._client_lock:
            if self._client is not None:  # double-checked under the lock
                return
            if self._compat == "openai":
                from openai import OpenAI
                base_url = _resolve_base_url(self.provider)
                # OpenAI SDK requires a non-empty api_key even for keyless providers
                api_key = self.api_key or "none"
                self._client = OpenAI(base_url=base_url, api_key=api_key)
            elif self._compat == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)

    def _call_openai(
        self, system: str, user: str, temperature: float, max_tokens: int
    ) -> tuple[str, TokenUsage]:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content or ""
        usage = TokenUsage(
            input_tokens=getattr(resp.usage, "prompt_tokens", 0),
            output_tokens=getattr(resp.usage, "completion_tokens", 0),
            model=self.model,
        )
        return text, usage

    def _call_anthropic(
        self, system: str, user: str, temperature: float, max_tokens: int
    ) -> tuple[str, TokenUsage]:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        )
        usage = TokenUsage(
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            model=self.model,
        )
        return text, usage

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.4,
        max_tokens: int = 4000,
    ) -> tuple[str, TokenUsage]:
        """Return (text, usage). Calls the configured provider's API."""
        self._ensure_client()
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                if self._compat == "openai":
                    return self._call_openai(system, user, temperature, max_tokens)
                elif self._compat == "anthropic":
                    return self._call_anthropic(system, user, temperature, max_tokens)
            except Exception as exc:
                last_err = exc
                wait = self.backoff * (2 ** attempt)
                log.warning("llm_retry", attempt=attempt, wait=wait, error=str(exc))
                time.sleep(wait)
        raise RuntimeError(
            f"LLM call failed after {self.max_retries} retries: {last_err}"
        )

    def complete_json(self, system: str, user: str, **kw) -> tuple[dict, TokenUsage]:
        text, usage = self.complete(system, user, **kw)
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()
        try:
            return json.loads(text), usage
        except json.JSONDecodeError:
            pass
        return json.loads(_sanitize_llm_json(text)), usage


def make_client(settings) -> LLMClient:
    return LLMClient(
        provider=settings.provider,
        model=settings.model,
        api_key=settings.api_key,
    )
