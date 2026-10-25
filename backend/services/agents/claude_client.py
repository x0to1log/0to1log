"""Send chat.completions-shaped calls for claude-* models to the Anthropic API.

Handbook generation passes one client to the writer calls *and* the critique,
judge and entity calls. `ClaudeRoutingClient` keeps that single client: calls
whose model starts with "claude-" go to Claude, everything else goes to the
wrapped OpenAI client unchanged. The Claude reply is reshaped into the few
fields our call sites read (`choices[0].message.content`, `usage`), so the
writer call sites and `extract_usage_metrics` stay as they are.

Vault plan 2026-10-23-handbook-seed-claude (결정 1, 2).
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

from anthropic import AsyncAnthropic

from core.config import settings

logger = logging.getLogger(__name__)

CLAUDE_MODEL_PREFIX = "claude-"
_CLAUDE_MAX_OUTPUT = 128_000
# Thinking spends max_tokens on Claude too; same 3x headroom the OpenAI
# reasoning models get in client._apply_reasoning_model_kwargs.
_THINKING_HEADROOM = 3
_EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max"})


class ClaudeRefusalError(RuntimeError):
    """Claude declined the request (stop_reason == "refusal")."""


def is_claude_model(model: str | None) -> bool:
    return bool(model) and str(model).startswith(CLAUDE_MODEL_PREFIX)


def to_anthropic_request(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Map chat.completions kwargs to messages.stream kwargs.

    OpenAI-only knobs are dropped: `service_tier`, `prompt_cache_key` (Claude
    caches the system block marked below), `response_format` (handbook prompts
    already ask for one JSON object; see `json_payload`).
    """
    messages = kwargs["messages"]
    system = "\n\n".join(str(m["content"]) for m in messages if m["role"] == "system")
    max_tokens = int(kwargs.get("max_completion_tokens") or kwargs.get("max_tokens") or 4096)
    request: dict[str, Any] = {
        "model": kwargs["model"],
        "max_tokens": min(max_tokens * _THINKING_HEADROOM, _CLAUDE_MAX_OUTPUT),
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"],
    }
    if system:
        # The long, per-call-type system prompt is the stable prefix worth caching.
        request["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    effort = kwargs.get("reasoning_effort")
    if effort in _EFFORTS:
        request["output_config"] = {"effort": effort}
    return request


def json_payload(text: str) -> str:
    """Return the bare JSON object from a Claude reply.

    Claude often wraps the object in a ```json fence. parse_ai_json's fence
    regex is non-greedy, so a handbook body containing its own ```python
    example cut the JSON at that inner fence ("Unterminated string", pilot
    2026-10-25). Strip only the outer fence here, and any prose around the
    object ("Here is the result: {...}").
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        stripped = stripped[first_newline + 1:] if first_newline != -1 else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
        stripped = stripped.strip()
    if stripped.startswith("{"):
        return stripped
    start, end = stripped.find("{"), stripped.rfind("}")
    return stripped[start:end + 1] if 0 <= start < end else stripped


def to_completion_shape(message: Any, model: str, *, wants_json: bool) -> SimpleNamespace:
    """Reshape an Anthropic Message into the fields our call sites read."""
    text = "".join(block.text for block in message.content if block.type == "text")
    if wants_json:
        text = json_payload(text)
    usage = message.usage
    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    prompt_tokens = int(usage.input_tokens or 0) + cache_read + cache_write
    output_tokens = int(usage.output_tokens or 0)
    return SimpleNamespace(
        model=model,
        service_tier=None,  # standard pricing in extract_usage_metrics
        stop_reason=message.stop_reason,
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=text),
            finish_reason="length" if message.stop_reason == "max_tokens" else "stop",
        )],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=output_tokens,
            total_tokens=prompt_tokens + output_tokens,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cache_read),
            completion_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
    )


class _RoutedCompletions:
    def __init__(self, router: "ClaudeRoutingClient") -> None:
        self._router = router

    async def create(self, **kwargs: Any) -> Any:
        model = kwargs.get("model")
        if not is_claude_model(model):
            return await self._router.openai.chat.completions.create(**kwargs)
        request = to_anthropic_request(kwargs)
        # Streaming: handbook sections run to tens of thousands of tokens.
        async with self._router.anthropic.messages.stream(**request) as stream:
            message = await stream.get_final_message()
        if message.stop_reason == "refusal":
            details = getattr(message, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise ClaudeRefusalError(f"{model} refused the request (category={category})")
        if message.stop_reason == "max_tokens":
            logger.warning("%s hit max_tokens=%d; output may be truncated", model, request["max_tokens"])
        wants_json = (kwargs.get("response_format") or {}).get("type") in {"json_object", "json_schema"}
        return to_completion_shape(message, str(model), wants_json=wants_json)


class ClaudeRoutingClient:
    """An AsyncOpenAI stand-in that sends claude-* models to Anthropic."""

    def __init__(self, openai_client: Any, anthropic_client: AsyncAnthropic | None = None) -> None:
        self.openai = openai_client
        self._anthropic = anthropic_client
        self.chat = SimpleNamespace(completions=_RoutedCompletions(self))

    @property
    def anthropic(self) -> AsyncAnthropic:
        if self._anthropic is None:
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            self._anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=4)
        return self._anthropic
