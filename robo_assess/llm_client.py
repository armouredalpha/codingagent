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
from typing import Callable, Optional

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

    def stream_complete(
        self,
        system: str,
        user: str,
        on_chunk: "Callable[[str], None]",
        temperature: float = 0.4,
        max_tokens: int = 4000,
    ) -> tuple[str, TokenUsage]:
        """Stream a completion, calling on_chunk(token) for each text chunk.

        Falls back to a normal complete() call for providers that don't support
        streaming, so callers don't need to branch. Returns the full accumulated
        text and usage like complete() does.
        """
        self._ensure_client()
        if self._compat == "anthropic":
            return self._stream_anthropic(system, user, on_chunk, temperature, max_tokens)
        elif self._compat == "openai":
            return self._stream_openai(system, user, on_chunk, temperature, max_tokens)
        return self.complete(system, user, temperature, max_tokens)

    def _stream_anthropic(
        self, system, user, on_chunk, temperature, max_tokens
    ) -> tuple[str, TokenUsage]:
        import anthropic as _anthropic
        chunks: list[str] = []
        input_tokens = output_tokens = 0
        with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for text in stream.text_stream:
                on_chunk(text)
                chunks.append(text)
            msg = stream.get_final_message()
            input_tokens = msg.usage.input_tokens
            output_tokens = msg.usage.output_tokens
        full = "".join(chunks)
        return full, TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens, model=self.model)

    def _stream_openai(
        self, system, user, on_chunk, temperature, max_tokens
    ) -> tuple[str, TokenUsage]:
        chunks: list[str] = []
        input_tokens = output_tokens = 0
        stream = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        for chunk in stream:
            if chunk.usage:
                input_tokens = getattr(chunk.usage, "prompt_tokens", 0)
                output_tokens = getattr(chunk.usage, "completion_tokens", 0)
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                on_chunk(delta)
                chunks.append(delta)
        full = "".join(chunks)
        return full, TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens, model=self.model)

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

    def complete_with_tools(
        self,
        system: str,
        user: str,
        registry,  # ToolRegistry
        temperature: float = 0.4,
        max_tokens: int = 4000,
        max_tool_rounds: int = 5,
        force_first_tool: bool = True,
    ) -> tuple[str, TokenUsage]:
        """Call the LLM with tool use enabled.

        Executes a multi-turn loop: if the model emits tool_use blocks, each
        tool is dispatched through registry.handle(), the result is fed back,
        and the model continues until it emits a plain-text response or
        max_tool_rounds is reached.

        Set force_first_tool=False to let the model decide on turn 0 whether
        to call a tool at all (useful for simpler questions that may not need
        API lookups before generating code).

        Returns (final_text, cumulative_usage).
        """
        self._ensure_client()
        cumulative = TokenUsage(model=self.model)

        if self._compat == "anthropic":
            return self._tool_loop_anthropic(
                system, user, registry, temperature, max_tokens, max_tool_rounds,
                cumulative, force_first_tool,
            )
        elif self._compat == "openai":
            return self._tool_loop_openai(
                system, user, registry, temperature, max_tokens, max_tool_rounds,
                cumulative, force_first_tool,
            )
        raise RuntimeError(f"complete_with_tools not supported for compat '{self._compat}'")

    def _tool_loop_anthropic(
        self, system, user, registry, temperature, max_tokens, max_tool_rounds,
        cumulative, force_first_tool: bool = True,
    ) -> tuple[str, TokenUsage]:
        import anthropic as _anthropic
        messages = [{"role": "user", "content": user}]
        tools = registry.anthropic_schemas()

        for turn in range(max_tool_rounds):
            # On turn 0 force a tool call only when requested (e.g. skip for easy
            # questions that may not need API lookups before writing code).
            tool_choice = {"type": "any"} if (turn == 0 and force_first_tool) else {"type": "auto"}
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                tools=tools,
                tool_choice=tool_choice,
                messages=messages,
            )
            cumulative.input_tokens += resp.usage.input_tokens
            cumulative.output_tokens += resp.usage.output_tokens

            tool_blocks = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
            text_blocks = [b for b in resp.content if getattr(b, "type", "") == "text"]

            if not tool_blocks:
                text = "".join(b.text for b in text_blocks)
                return text, cumulative

            # submit_question is a structured-output sentinel: capture and return immediately.
            for tb in tool_blocks:
                if tb.name == "submit_question":
                    args = dict(tb.input)
                    log.info("tool_call", tool="submit_question", args=list(args.keys()))
                    sentinel = "__SUBMISSION__:" + json.dumps({
                        "spec_json": args.get("spec_json", "{}"),
                        "starter_code": args.get("starter_code", ""),
                        "reference_code": args.get("reference_code", ""),
                    })
                    return sentinel, cumulative

            # Deduplicate and cap per-tool to prevent runaway explosions (LLM sometimes
            # requests dozens of identical fetch_ros2_docs calls in one turn).
            # Allow up to 2 calls per tool name so different library/query combos can
            # coexist, but a single tool can never monopolise the whole round.
            MAX_CALLS_PER_TOOL = 2
            seen_exact: set[str] = set()
            per_tool_count: dict[str, int] = {}
            filtered: list = []
            for tb in tool_blocks:
                exact_key = f"{tb.name}:{json.dumps(dict(tb.input), sort_keys=True)}"
                if exact_key in seen_exact:
                    continue
                seen_exact.add(exact_key)
                if per_tool_count.get(tb.name, 0) >= MAX_CALLS_PER_TOOL:
                    continue
                per_tool_count[tb.name] = per_tool_count.get(tb.name, 0) + 1
                filtered.append(tb)
            if len(filtered) < len(tool_blocks):
                log.warning("tool_call_filtered",
                            original=len(tool_blocks), filtered=len(filtered))

            # Append assistant turn
            messages.append({"role": "assistant", "content": resp.content})

            # Execute each tool and build tool_result turn
            tool_results = []
            for tb in filtered:
                result = registry.handle(tb.name, dict(tb.input))
                log.info("tool_call", tool=tb.name, args=list(dict(tb.input).keys()))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tb.id,
                    "content": json.dumps(result),
                })
            messages.append({"role": "user", "content": tool_results})

        # Exceeded max rounds — do a final call without tools
        log.warning("tool_loop_max_rounds", rounds=max_tool_rounds)
        text, usage = self._call_anthropic(system, json.dumps(messages[-1]), temperature, max_tokens)
        cumulative.input_tokens += usage.input_tokens
        cumulative.output_tokens += usage.output_tokens
        return text, cumulative

    def _tool_loop_openai(
        self, system, user, registry, temperature, max_tokens, max_tool_rounds,
        cumulative, force_first_tool: bool = True,
    ) -> tuple[str, TokenUsage]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        tools = registry.openai_schemas()

        for turn in range(max_tool_rounds):
            # On turn 0 force a tool call only when requested (e.g. skip for easy
            # questions that may not need API lookups before writing code).
            tool_choice = ("required" if (turn == 0 and force_first_tool) else "auto")
            resp = self._client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                messages=messages,
            )
            cumulative.input_tokens += getattr(resp.usage, "prompt_tokens", 0)
            cumulative.output_tokens += getattr(resp.usage, "completion_tokens", 0)

            msg = resp.choices[0].message
            messages.append(msg)

            tool_calls = getattr(msg, "tool_calls", None) or []
            if not tool_calls:
                return msg.content or "", cumulative

            # submit_question is a structured-output sentinel: capture and return immediately.
            for tc in tool_calls:
                if tc.function.name == "submit_question":
                    try:
                        fn_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        fn_args = {}
                    log.info("tool_call", tool="submit_question", args=list(fn_args.keys()))
                    sentinel = "__SUBMISSION__:" + json.dumps({
                        "spec_json": fn_args.get("spec_json", "{}"),
                        "starter_code": fn_args.get("starter_code", ""),
                        "reference_code": fn_args.get("reference_code", ""),
                    })
                    return sentinel, cumulative

            # Deduplicate and cap per-tool to prevent runaway explosions (LLM sometimes
            # requests dozens of identical fetch_ros2_docs calls in one turn).
            # Allow up to 2 calls per tool name so different library/query combos can
            # coexist, but a single tool can never monopolise the whole round.
            MAX_CALLS_PER_TOOL = 2
            seen_exact_oa: set[str] = set()
            per_tool_count_oa: dict[str, int] = {}
            filtered_tc: list = []
            for tc in tool_calls:
                fn_args_str = getattr(tc.function, "arguments", "") or ""
                exact_key = f"{tc.function.name}:{fn_args_str}"
                if exact_key in seen_exact_oa:
                    continue
                seen_exact_oa.add(exact_key)
                if per_tool_count_oa.get(tc.function.name, 0) >= MAX_CALLS_PER_TOOL:
                    continue
                per_tool_count_oa[tc.function.name] = per_tool_count_oa.get(tc.function.name, 0) + 1
                filtered_tc.append(tc)
            if len(filtered_tc) < len(tool_calls):
                log.warning("tool_call_filtered",
                            original=len(tool_calls), filtered=len(filtered_tc))
            tool_calls = filtered_tc

            for tc in tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}
                result = registry.handle(fn_name, fn_args)
                log.info("tool_call", tool=fn_name, args=list(fn_args.keys()))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        log.warning("tool_loop_max_rounds_openai", rounds=max_tool_rounds)
        fallback_resp = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
        )
        cumulative.input_tokens += getattr(fallback_resp.usage, "prompt_tokens", 0)
        cumulative.output_tokens += getattr(fallback_resp.usage, "completion_tokens", 0)
        return fallback_resp.choices[0].message.content or "", cumulative


def make_client(settings) -> LLMClient:
    return LLMClient(
        provider=settings.provider,
        model=settings.model,
        api_key=settings.api_key,
    )


def make_cheap_client(settings) -> LLMClient:
    """Return a cheap-tier LLM client for critic/triage agents.

    Uses cheap_model + cheap_provider from settings when configured.
    Falls back to the main model so the system always works without extra config.
    """
    cheap_provider = getattr(settings, "cheap_provider", None) or settings.provider
    cheap_model = getattr(settings, "cheap_model", None) or settings.model

    # Resolve API key: cheap_api_key > provider-specific env var > main api_key
    cheap_api_key = getattr(settings, "cheap_api_key", None)
    if not cheap_api_key:
        cheap_api_key = resolve_api_key(cheap_provider) or settings.api_key

    return LLMClient(
        provider=cheap_provider,
        model=cheap_model,
        api_key=cheap_api_key,
    )


def make_agent_client(settings, agent_name: str) -> LLMClient:
    """Return an LLMClient for a specific agent, using agent_models override if set.

    Falls back to make_cheap_client for critic agents, make_client for others.
    Config example (config.yaml):
        agent_models:
            question_generator: openai/gpt-4o
            md_summary: openai/gpt-4o-mini
            skill_triage: openai/gpt-4o-mini
    """
    _CRITIC_AGENTS = {
        "difficulty_agent", "scope_quality",
        "skill_triage", "eval_comparator",
    }

    agent_models: dict = getattr(settings, "agent_models", {})
    model_override = agent_models.get(agent_name)
    if model_override:
        # For critic agents with an override, honour cheap_provider so the
        # override model is routed to the correct endpoint (e.g. gpt-4o-mini
        # on OpenRouter when main provider is Anthropic).
        if agent_name in _CRITIC_AGENTS:
            provider = getattr(settings, "cheap_provider", None) or settings.provider
            api_key = (
                getattr(settings, "cheap_api_key", None)
                or resolve_api_key(provider)
                or settings.api_key
            )
        else:
            provider = settings.provider
            api_key = settings.api_key
        return LLMClient(provider=provider, model=model_override, api_key=api_key)

    # No override: critics use cheap tier, everything else uses main model
    if agent_name in _CRITIC_AGENTS:
        return make_cheap_client(settings)
    return make_client(settings)
