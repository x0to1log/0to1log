"""Handbook judges and self-critique reviewers must see the whole draft.

Each of these inputs used to be cut to a fixed character count before the
call, so the reviewer scored text it could only partly read.
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agents import advisor

TAIL = "TAIL-MARKER-VISIBLE"


def _client_returning(payload: dict):
    """A chat.completions client that records its kwargs and replies with `payload`."""
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))],
        usage=None,
    )
    create = AsyncMock(return_value=response)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), create


def _messages(create: AsyncMock) -> dict[str, str]:
    return {m["role"]: m["content"] for m in create.call_args.kwargs["messages"]}


def test_section_preview_keeps_long_sections_whole():
    code_section = "x = 1\n" * 600 + TAIL  # ~3,600 chars, the size of a code capsule
    preview = advisor._build_section_preview({"adv_ko_3_code": code_section, "basic_ko_1_plain": "skip"}, "adv_ko_")

    assert TAIL in preview
    assert "basic_ko_1_plain" not in preview


def test_section_preview_still_truncates_when_asked():
    preview = advisor._build_section_preview({"adv_ko_1_mechanism": "a" * 500 + TAIL}, "adv_ko_", max_chars=100)

    assert TAIL not in preview


@pytest.mark.asyncio
async def test_basic_critique_sees_all_of_en_after_a_long_ko():
    client, create = _client_returning({"ko_needs_improvement": False, "en_needs_improvement": False})
    ko = "가" * 7000
    en = "word " * 1200 + TAIL

    await advisor._self_critique_basic(
        "Reasoning Model", "system_workflow_pattern", ko, en, client, "unused",
        reference_context="ref " * 1000 + TAIL,
    )

    sent = _messages(create)
    assert sent["user"].endswith(TAIL)
    assert sent["system"].endswith(TAIL)


@pytest.mark.asyncio
async def test_advanced_critique_sees_whole_draft_and_references():
    client, create = _client_returning({"needs_improvement": False, "score": 80})
    draft = "## adv_en_1_mechanism: " + "detail " * 2000 + TAIL  # ~14,000 chars
    references = "## Deep Reference Materials\n" + "source text " * 2500 + TAIL  # ~30,000 chars

    await advisor._self_critique_advanced(
        "Reasoning Model", "system_workflow_pattern", draft, client, "unused",
        reference_context=references,
    )

    sent = _messages(create)
    assert sent["user"].endswith(TAIL)
    assert TAIL in sent["system"]


@pytest.mark.asyncio
async def test_rescore_judges_see_the_tail_of_long_bodies():
    captured = {}

    async def fake_advanced_quality(term, term_type, advanced_content, client):
        captured["advanced"] = advanced_content
        return 90, {}, {}

    async def fake_basic_quality(term, term_type, basic_content, client):
        captured["basic"] = basic_content
        return 90, {}, {}

    # Longer than the old caps (12,000 advanced / 6,000 basic per locale).
    long_advanced_en = "## Technical Definition & How It Works\n" + "mechanism " * 1500 + f"\n\n## Related\n- (extension) {TAIL}-ADV-EN"
    long_basic_en = "## Plain Explanation\n" + "plain " * 1300 + f"\n\n## Related Reading\n- (next) {TAIL}-BASIC-EN"

    with (
        patch.object(advisor, "_check_handbook_quality", new=AsyncMock(side_effect=fake_advanced_quality)),
        patch.object(advisor, "_check_basic_quality", new=AsyncMock(side_effect=fake_basic_quality)),
    ):
        await advisor.rescore_existing_handbook_quality(
            "Reasoning Model",
            {
                "term_type": "system_workflow_pattern",
                "body_basic_ko": "## 쉽게 이해하기\n내용",
                "body_basic_en": long_basic_en,
                "body_advanced_ko": "## 기술적 정의와 동작 원리\n내용",
                "body_advanced_en": long_advanced_en,
            },
            client=MagicMock(),
            run_semantic=True,
        )

    assert f"{TAIL}-ADV-EN" in captured["advanced"]
    assert f"{TAIL}-BASIC-EN" in captured["basic"]


def test_critique_references_include_each_source_once():
    bundle = {"curated": "", "brave": "BRAVE-RESULTS", "exa": "EXA-FULL-TEXT", "tavily": "TAVILY-RESULTS"}

    context = advisor._critique_reference_context("foundational_concept", None, bundle)

    for source in ("BRAVE-RESULTS", "EXA-FULL-TEXT", "TAVILY-RESULTS"):
        assert context.count(source) == 1
