"""Locale recovery rebuilds a missing or broken locale by translating the other
one, and only accepts a result that carries exactly the source's [CITE_N] tokens."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

SOURCE_EN = (
    "## Top story\n\n### Lab ships model\n\n"
    "The lab shipped a model. [CITE_1]\n\nIt scored 90 on the benchmark. [CITE_2]"
)


def _client(body: str):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps({"body": body})
    resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    resp.service_tier = "flex"
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=resp)
    return client


async def _recover(body: str):
    from services.pipeline_digest import _recover_locale_by_translation

    client = _client(body)
    result, usage = await _recover_locale_by_translation(
        client, "gpt-6.1-sol",
        target_locale="ko", source_body_raw=SOURCE_EN, cache_key="test-ko-recovery",
    )
    return client, result, usage


@pytest.mark.asyncio
async def test_recovery_accepts_translation_with_identical_cite_tokens():
    ko = "## 주요 소식\n\n### 연구소, 모델 출시\n\n연구소가 모델을 출시했다. [CITE_1]\n\n벤치마크 90점. [CITE_2]"
    client, result, usage = await _recover(ko)

    assert result == ko
    assert usage["input_tokens"] == 100
    messages = client.chat.completions.create.await_args.kwargs["messages"]
    assert SOURCE_EN in messages[1]["content"]
    assert "{{" not in messages[0]["content"]


@pytest.mark.asyncio
async def test_recovery_rejects_translation_that_drops_a_token():
    _c, result, _usage = await _recover("연구소가 모델을 출시했다. [CITE_1]\n\n벤치마크 90점.")
    assert result == ""


@pytest.mark.asyncio
async def test_recovery_rejects_translation_that_renumbers_tokens():
    _c, result, _usage = await _recover("모델 출시. [CITE_1]\n\n벤치마크 90점. [CITE_3]")
    assert result == ""
