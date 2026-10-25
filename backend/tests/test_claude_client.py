"""Claude routing client for handbook seed generation (no network)."""
import json
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


def _writer_kwargs(model="claude-sonnet-5-5", response_format=None, **extra):
    # Exactly what the handbook writer call sites build.
    return compat_create_kwargs(
        model,
        messages=[{"role": "system", "content": "SYSTEM PROMPT"}, {"role": "user", "content": "term: MoE"}],
        response_format=response_format or {"type": "json_object"},
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
async def test_generate_term_content_picks_writer_arg_then_feature_override_then_role(monkeypatch):
    from core.config import settings
    from services.agents import advisor

    captured = {}

    async def fake_run(req, client, model, **kwargs):
        captured["model"] = model
        return {}, {}, []

    with patch.object(advisor, "_run_generate_term", side_effect=fake_run), \
         patch.object(advisor, "get_openai_client", return_value=MagicMock()):
        await advisor.generate_term_content("MoE")
        assert captured["model"] == settings.openai_model_main

        monkeypatch.setattr(settings, "model_overrides", {"handbook.writer": "claude-opus-5-5"})
        await advisor.generate_term_content("MoE")
        assert captured["model"] == "claude-opus-5-5"

        await advisor.generate_term_content("MoE", writer_model="claude-sonnet-5-5")
        assert captured["model"] == "claude-sonnet-5-5"


def test_every_call_site_gets_a_routing_client_that_passes_embeddings_to_openai():
    from services.agents.client import get_openai_client

    client = get_openai_client()
    assert isinstance(client, ClaudeRoutingClient)
    assert client.embeddings is client.openai.embeddings


def test_model_for_uses_override_then_role_default(monkeypatch):
    from core.config import model_for, settings

    monkeypatch.setattr(settings, "model_overrides", {"news.classify": "claude-haiku-5-5"})
    assert model_for("news.classify", "light") == "claude-haiku-5-5"
    assert model_for("news.merge", "light") == settings.openai_model_light
    with pytest.raises(ValueError):
        model_for("news.merge", "medium")


def test_strict_schemas_map_to_claude_structured_outputs_without_rejected_keywords():
    from services.agents.schemas.news_quiz import build_news_quiz_json_schema

    response_format = {"type": "json_schema", "json_schema": build_news_quiz_json_schema("en")}
    request = to_anthropic_request(_writer_kwargs(response_format=response_format))
    fmt = request["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert request["output_config"]["effort"] == "high"
    text = json.dumps(fmt["schema"])
    for rejected in ('"minimum"', '"maximum"', '"minLength"', '"maxItems"', '"minItems": 4'):
        assert rejected not in text
    assert '"additionalProperties": false' in text


def test_schema_cleaner_keeps_supported_keywords():
    from services.agents.claude_client import claude_json_schema

    schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "enum": ["https://a.example/X"]},
            "tags": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1, "maxItems": 3},
            "n": {"type": "integer", "minimum": 1, "maximum": 50},
        },
        "required": ["url", "tags", "n"],
        "additionalProperties": False,
    }
    cleaned = claude_json_schema(schema)
    assert cleaned["properties"]["url"]["enum"] == ["https://a.example/X"]
    assert cleaned["properties"]["tags"] == {"type": "array", "items": {"type": "string"}, "minItems": 1}
    assert cleaned["properties"]["n"] == {"type": "integer"}
    assert cleaned["required"] == ["url", "tags", "n"] and cleaned["additionalProperties"] is False


def test_writer_system_prompt_splits_into_cacheable_base_and_term_guides():
    from services.agents.advisor import _writer_system_messages

    base = "BASE PROMPT"
    system = base + "\n\nCATEGORY GUIDE"
    assert _writer_system_messages(system, base, split=True) == [
        {"role": "system", "content": "BASE PROMPT"},
        {"role": "system", "content": "CATEGORY GUIDE"},
    ]
    # OpenAI writers keep the single message they always had.
    assert _writer_system_messages(system, base, split=False) == [{"role": "system", "content": system}]
    assert _writer_system_messages("OTHER", base, split=True) == [{"role": "system", "content": "OTHER"}]


def test_only_the_first_system_block_carries_the_cache_breakpoint():
    kwargs = compat_create_kwargs(
        "claude-sonnet-5-5",
        messages=[
            {"role": "system", "content": "BASE"},
            {"role": "system", "content": "TERM GUIDES"},
            {"role": "user", "content": "term"},
        ],
        max_tokens=100,
    )
    system = to_anthropic_request(kwargs)["system"]
    assert system == [
        {"type": "text", "text": "BASE", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "TERM GUIDES"},
    ]


def test_claude_writer_guard_sets_budgets_and_code_limit_only_for_advanced():
    from services.agents.prompts_advisor import claude_writer_guard

    basic = claude_writer_guard("basic", "ko")
    advanced = claude_writer_guard("advanced", "en")
    assert "3,000 characters" in basic and "Code:" not in basic
    assert "12,000 characters" in advanced and "55 non-empty lines" in advanced
    assert "no code fence" in basic


def test_stray_latex_backslashes_are_repaired_only_when_parsing_fails():
    # Pilot 2026-10-26: a formula-heavy Claude draft did not parse; LaTeX like
    # \sigma written with one backslash is an invalid JSON escape.
    bs = "\\"
    broken = '{"body": "' + bs + "sigma(x) + " + bs + 'sum_j", "n": 1}'
    assert json.loads(json_payload(broken)) == {"body": bs + "sigma(x) + " + bs + "sum_j", "n": 1}
    valid = '{"a": "line' + bs + 'n", "b": "' + bs + bs + 'alpha"}'
    assert json_payload(valid) == valid
