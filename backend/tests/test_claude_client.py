"""Claude routing client for handbook seed generation (no network)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agents.claude_client import (
    ClaudeRefusalError,
    ClaudeRoutingClient,
    json_payload,
    to_anthropic_request,
    to_completion_shape,
)
from services.agents.client import compat_create_kwargs, extract_usage_metrics


def _writer_kwargs(model="claude-sonnet-5-5", **extra):
    # Exactly what the handbook writer call sites build.
    return compat_create_kwargs(
        model,
        messages=[{"role": "system", "content": "SYSTEM PROMPT"}, {"role": "user", "content": "term: MoE"}],
        response_format={"type": "json_object"},
        max_tokens=24000,
        prompt_cache_key="hb-generate-basic",
        reasoning_effort="high",
        service_tier="flex",
        **extra,
    )


def _message(text='{"a": 1}', stop="end_turn", input_tokens=1000, output_tokens=500, cache_read=0, cache_write=0):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop,
        usage=SimpleNamespace(
            input_tokens=input_tokens, output_tokens=output_tokens,
            cache_read_input_tokens=cache_read, cache_creation_input_tokens=cache_write,
        ),
    )


class _FakeStream:
    def __init__(self, message):
        self._message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_final_message(self):
        return self._message


def _anthropic(message):
    client = MagicMock()
    client.messages.stream = MagicMock(return_value=_FakeStream(message))
    return client


def test_writer_kwargs_map_to_a_cached_system_block_with_effort_and_headroom():
    request = to_anthropic_request(_writer_kwargs())
    assert request["model"] == "claude-sonnet-5-5"
    assert request["max_tokens"] == 72000  # 24000 x 3 thinking headroom
    assert request["system"] == [{"type": "text", "text": "SYSTEM PROMPT", "cache_control": {"type": "ephemeral"}}]
    assert request["messages"] == [{"role": "user", "content": "term: MoE"}]
    assert request["output_config"] == {"effort": "high"}
    for openai_only in ("service_tier", "prompt_cache_key", "response_format", "reasoning_effort"):
        assert openai_only not in request


def test_max_tokens_is_capped_at_claude_output_limit():
    kwargs = _writer_kwargs()
    kwargs["max_tokens"] = 60000
    assert to_anthropic_request(kwargs)["max_tokens"] == 128000


def test_json_payload_trims_prose_and_the_outer_fence():
    assert json_payload('Here is the entry:\n{"a": {"b": 1}}\nDone.') == '{"a": {"b": 1}}'
    assert json_payload('{"a": 1}') == '{"a": 1}'
    assert json_payload('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_fenced_reply_with_code_examples_inside_parses():
    # Pilot 2026-10-25: every Claude draft failed with "Unterminated string" —
    # parse_ai_json's non-greedy fence regex stopped at the body's own ```python.
    import json

    from services.agents.client import parse_ai_json

    body = {"body_advanced_en": "Example:\n```python\nprint(1)\n```\nDone.", "x": "y"}
    reply = "```json\n" + json.dumps(body) + "\n```"
    assert parse_ai_json(json_payload(reply), "test") == body


def test_reply_is_reshaped_so_existing_usage_accounting_prices_it():
    resp = to_completion_shape(
        _message(input_tokens=200, output_tokens=1000, cache_read=8000, cache_write=0),
        "claude-sonnet-5-5", wants_json=True,
    )
    assert resp.choices[0].message.content == '{"a": 1}'
    usage = extract_usage_metrics(resp, "claude-sonnet-5-5")
    assert usage["input_tokens"] == 8200
    assert usage["cached_tokens"] == 8000
    # 200 fresh x $2 + 8000 cache read x $0.20 + 1000 out x $10, per 1M
    assert usage["cost_usd"] == pytest.approx((200 * 2 + 8000 * 0.2 + 1000 * 10) / 1_000_000)


@pytest.mark.asyncio
async def test_claude_models_go_to_anthropic_and_others_stay_on_openai():
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(return_value="openai-response")
    anthropic_client = _anthropic(_message())
    router = ClaudeRoutingClient(openai_client, anthropic_client)

    claude = await router.chat.completions.create(**_writer_kwargs())
    judge = await router.chat.completions.create(**compat_create_kwargs("gpt-6.1-sol", messages=[], max_tokens=10))

    assert claude.choices[0].message.content == '{"a": 1}'
    anthropic_client.messages.stream.assert_called_once()
    assert judge == "openai-response"
    assert openai_client.chat.completions.create.await_args.kwargs["model"] == "gpt-6.1-sol"


@pytest.mark.asyncio
async def test_refusal_raises_with_its_category_instead_of_returning_empty_content():
    message = _message(text="", stop="refusal")
    message.stop_details = SimpleNamespace(category="cyber", explanation="")
    router = ClaudeRoutingClient(MagicMock(), _anthropic(message))
    with pytest.raises(ClaudeRefusalError, match="category=cyber"):
        await router.chat.completions.create(**_writer_kwargs())


@pytest.mark.asyncio
async def test_refused_term_is_regenerated_with_the_openai_writer():
    from services.agents import advisor

    calls = []

    async def fake_run(req, client, model, **kwargs):
        calls.append(model)
        if model.startswith("claude-"):
            raise ClaudeRefusalError("claude-sonnet-5-5 refused the request (category=cyber)")
        return {"definition_en": "ok"}, {}, []

    with patch.object(advisor, "_run_generate_term", side_effect=fake_run), \
         patch.object(advisor, "get_openai_client", return_value=MagicMock()):
        data, _ = await advisor.generate_term_content("Red Teaming", writer_model="claude-sonnet-5-5")

    assert calls == ["claude-sonnet-5-5", advisor.settings.openai_model_main]
    assert data["_writer_fallback"]["from"] == "claude-sonnet-5-5"
    assert "category=cyber" in data["_writer_fallback"]["reason"]


@pytest.mark.asyncio
async def test_generate_term_content_routes_only_when_writer_model_is_claude():
    from services.agents import advisor

    captured = {}

    async def fake_run(req, client, model, **kwargs):
        captured["client"], captured["model"] = client, model
        return {}, {}, []

    with patch.object(advisor, "_run_generate_term", side_effect=fake_run), \
         patch.object(advisor, "get_openai_client", return_value=MagicMock()):
        await advisor.generate_term_content("MoE", writer_model="claude-sonnet-5-5")
        assert isinstance(captured["client"], ClaudeRoutingClient)
        assert captured["model"] == "claude-sonnet-5-5"

        await advisor.generate_term_content("MoE")
        assert not isinstance(captured["client"], ClaudeRoutingClient)
        assert captured["model"] == advisor.settings.openai_model_main
