import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import ClassifiedGroup, GroupedItem, PersonaOutput


def _mock_openai_response(payload: dict, tokens: int = 500):
    response = MagicMock()
    response.choices[0].message.content = json.dumps(payload)
    response.usage = MagicMock()
    response.usage.prompt_tokens = 1000
    response.usage.completion_tokens = tokens
    response.usage.total_tokens = 1000 + tokens
    return response


class _UpsertQuery:
    def __init__(self, supabase, table_name: str):
        self.supabase = supabase
        self.table_name = table_name
        self.payload = None

    def upsert(self, payload, on_conflict=None):
        self.payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            self.supabase.saved_rows.append((self.table_name, self.payload))
        return MagicMock(data=[])


class _CaptureSupabase:
    def __init__(self):
        self.saved_rows = []

    def table(self, name):
        return _UpsertQuery(self, name)


def _sample_group() -> list[ClassifiedGroup]:
    return [
        ClassifiedGroup(
            group_title="Sample Story",
            items=[GroupedItem(url="https://example.com/story", title="Sample Story")],
            category="research",
            subcategory="llm_models",
            relevance_score=0.9,
            reason="Major",
        )
    ]


def _sample_groups_for_locale_parity() -> list[ClassifiedGroup]:
    return [
        ClassifiedGroup(
            group_title="Microsoft launches three in-house MAI models",
            items=[GroupedItem(url="https://example.com/microsoft", title="Microsoft launches three in-house MAI models")],
            category="business",
            subcategory="big_tech",
            relevance_score=0.9,
            reason="Lead",
        ),
        ClassifiedGroup(
            group_title="Anthropic Managed Agents",
            items=[GroupedItem(url="https://example.com/anthropic", title="Anthropic Managed Agents")],
            category="business",
            subcategory="industry",
            relevance_score=0.8,
            reason="Supporting",
        ),
    ]


def test_find_digest_blockers_flags_placeholder_level3_heading():
    from services.pipeline import _find_digest_blockers

    personas = {
        "expert": PersonaOutput(
            en="## Big Tech\n\n### Proper Heading\n\nBody",
            ko="## Big Tech\n\n### 정상 제목\n\n본문",
        ),
        "learner": PersonaOutput(
            en="## Industry & Biz\n\n### —\n\nBody",
            ko="## Industry & Biz\n\n### 정상 제목\n\n본문",
        ),
    }

    blockers = _find_digest_blockers(personas)

    assert any("placeholder `###` heading" in blocker for blocker in blockers)


def test_find_digest_blockers_flags_hangul_in_en_heading():
    from services.pipeline import _find_digest_blockers

    personas = {
        "expert": PersonaOutput(
            en="## Research Papers\n\n### Tempo: 장시간 비디오 모델\n\nBody",
            ko="## Research Papers\n\n### Tempo: 장시간 비디오 모델\n\n본문",
        ),
        "learner": PersonaOutput(
            en="## Research Papers\n\n### Tempo video model\n\nBody",
            ko="## Research Papers\n\n### Tempo 비디오 모델\n\n본문",
        ),
    }

    blockers = _find_digest_blockers(personas)

    assert any("Hangul in EN `###` heading" in blocker for blocker in blockers)


def test_find_digest_blockers_flags_locale_parity_item_count_mismatch():
    from services.pipeline import _find_digest_blockers

    personas = {
        "expert": PersonaOutput(
            en=(
                "## Big Tech\n\n"
                "### Microsoft launches three in-house MAI models\n\n"
                "Body [1](https://example.com/microsoft)\n"
            ),
            ko=(
                "## Big Tech\n\n"
                "### Microsoft launches three in-house MAI models: MS 자체 모델\n\n"
                "본문 [1](https://example.com/microsoft)\n\n"
                "### Anthropic Managed Agents: 호스팅 에이전트 런타임\n\n"
                "본문 [2](https://example.com/anthropic)\n"
            ),
        ),
    }

    blockers = _find_digest_blockers(personas, classified=_sample_groups_for_locale_parity())

    assert any("locale parity item count mismatch" in blocker for blocker in blockers)


def test_find_digest_blockers_flags_locale_parity_story_set_mismatch():
    from services.pipeline import _find_digest_blockers

    personas = {
        "expert": PersonaOutput(
            en=(
                "## Big Tech\n\n"
                "### Microsoft launches three in-house MAI models\n\n"
                "Body [1](https://example.com/microsoft)\n\n"
                "### Anthropic Managed Agents\n\n"
                "Body [2](https://example.com/anthropic)\n"
            ),
            ko=(
                "## Big Tech\n\n"
                "### Microsoft launches three in-house MAI models: MS 자체 모델\n\n"
                "본문 [1](https://example.com/microsoft)\n\n"
                "### Another Microsoft angle: 가격 인하 경쟁\n\n"
                "본문 [2](https://example.com/microsoft)\n"
            ),
        ),
    }

    blockers = _find_digest_blockers(personas, classified=_sample_groups_for_locale_parity())

    assert any("locale parity story set mismatch" in blocker for blocker in blockers)


def test_structural_penalties_do_not_cap_one_line_summary_length():
    from services.pipeline import _check_structural_penalties

    expert = PersonaOutput(
        en=(
            "## One-Line Summary\n"
            "Nvidia's capital flywheel tightens around compute while regulators move faster on model oversight and AI tooling reaches wider distribution today.\n\n"
            "## Big Tech\n\n"
            "### Microsoft launches three in-house MAI models\n\n"
            "Body paragraph with citation [1](https://example.com/story)\n\n"
            "Second paragraph with citation [1](https://example.com/story)\n\n"
            "Third paragraph with citation [1](https://example.com/story)\n"
        ),
        ko="",
    )

    penalty, warnings = _check_structural_penalties(
        expert,
        learner=None,
        community_summary_map={},
        classified=_sample_group(),
    )

    assert penalty == 0
    assert not any("One-Line Summary too long" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_generate_digest_aborts_before_save_when_structural_blocker_found():
    from services.pipeline import _generate_digest

    supabase = _CaptureSupabase()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(
                {
                    "en": "## Big Tech\n\n### Proper Heading\n\nExpert body [1](https://example.com/story)",
                    "ko": "## Big Tech\n\n### 정상 제목\n\n전문가 본문 [1](https://example.com/story)",
                    "headline": "Expert headline",
                    "headline_ko": "전문가 헤드라인",
                    "excerpt": "Expert excerpt",
                    "excerpt_ko": "전문가 요약",
                }
            ),
            _mock_openai_response(
                {
                    "en": "## Industry & Biz\n\n### —\n\nLearner body [1](https://example.com/story)",
                    "ko": "## Industry & Biz\n\n### 정상 제목\n\n학습자 본문 [1](https://example.com/story)",
                    "headline": "Learner headline",
                    "headline_ko": "학습자 헤드라인",
                    "excerpt": "Learner excerpt",
                    "excerpt_ko": "학습자 요약",
                }
            ),
        ]
    )

    with patch("services.pipeline_digest.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_digest.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality._check_digest_quality", new_callable=AsyncMock) as quality_mock, \
         patch("services.pipeline_digest.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        posts_created, errors, _usage = await _generate_digest(
            classified=_sample_group(),
            digest_type="research",
            batch_id="2026-04-13",
            handbook_slugs=[],
            raw_content_map={"https://example.com/story": "Source body"},
            community_summary_map={},
            supabase=supabase,
            run_id="run-1",
            enriched_map={},
        )

    assert posts_created == 0
    assert any("structural validation failed" in error for error in errors)
    assert supabase.saved_rows == []
    quality_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_digest_saves_source_urls_from_actual_citations():
    from services.pipeline import _generate_digest

    supabase = _CaptureSupabase()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(
                {
                    "en": "## Research Papers\n\n### Expert Heading\n\nExpert body [1](https://example.com/story)",
                    "ko": "## Research Papers\n\n### 전문가 제목\n\n전문가 본문 [1](https://example.com/story)",
                    "headline": "Expert headline",
                    "headline_ko": "전문가 헤드라인",
                    "excerpt": "Expert excerpt",
                    "excerpt_ko": "전문가 요약",
                    "sources": [
                        {"url": "https://example.com/story", "title": "Primary source"},
                        {"url": "https://extra.example.com/analysis", "title": "Extra analysis"},
                    ],
                }
            ),
            _mock_openai_response(
                {
                    "en": "## Research Papers\n\n### Learner Heading\n\nLearner body [1](https://extra.example.com/analysis)",
                    "ko": "## Research Papers\n\n### 학습자 제목\n\n학습자 본문 [1](https://extra.example.com/analysis)",
                    "headline": "Learner headline",
                    "headline_ko": "학습자 헤드라인",
                    "excerpt": "Learner excerpt",
                    "excerpt_ko": "학습자 요약",
                    "sources": [
                        {"url": "https://example.com/story", "title": "Primary source"},
                        {"url": "https://extra.example.com/analysis", "title": "Extra analysis"},
                    ],
                }
            ),
        ]
    )

    with patch("services.pipeline_digest.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_digest.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality._check_digest_quality", new_callable=AsyncMock, return_value=88), \
         patch("services.pipeline_digest.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        posts_created, errors, _usage = await _generate_digest(
            classified=_sample_group(),
            digest_type="research",
            batch_id="2026-04-13",
            handbook_slugs=[],
            raw_content_map={"https://example.com/story": "Source body"},
            community_summary_map={},
            supabase=supabase,
            run_id="run-1",
            enriched_map={
                "https://example.com/story": [
                    {
                        "url": "https://extra.example.com/analysis",
                        "content": "Extra source body",
                    }
                ]
            },
        )

    assert posts_created == 2
    assert errors == []
    assert len(supabase.saved_rows) == 2
    for table_name, payload in supabase.saved_rows:
        assert table_name == "news_posts"
        assert payload["source_urls"] == [
            "https://example.com/story",
            "https://extra.example.com/analysis",
        ]
        assert [card["url"] for card in payload["source_cards"]] == [
            "https://example.com/story",
            "https://extra.example.com/analysis",
        ]


@pytest.mark.asyncio
async def test_generate_digest_includes_source_metadata_labels_in_writer_prompt():
    from services.pipeline import _generate_digest

    supabase = _CaptureSupabase()
    captured_user_prompts: list[str] = []
    responses = [
        _mock_openai_response(
            {
                "en": "## Research Papers\n\n### Expert Heading\n\nExpert body [1](https://example.com/story)",
                "ko": "## Research Papers\n\n### 전문가 제목\n\n전문가 본문 [1](https://example.com/story)",
                "headline": "Expert headline",
                "headline_ko": "전문가 헤드라인",
                "excerpt": "Expert excerpt",
                "excerpt_ko": "전문가 요약",
            }
        ),
        _mock_openai_response(
            {
                "en": "## Research Papers\n\n### Learner Heading\n\nLearner body [1](https://example.com/story)",
                "ko": "## Research Papers\n\n### 학습자 제목\n\n학습자 본문 [1](https://example.com/story)",
                "headline": "Learner headline",
                "headline_ko": "학습자 헤드라인",
                "excerpt": "Learner excerpt",
                "excerpt_ko": "학습자 요약",
            }
        ),
    ]

    async def _capture_create(*args, **kwargs):
        captured_user_prompts.append(kwargs["messages"][1]["content"])
        return responses.pop(0)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_capture_create)

    with patch("services.pipeline_digest.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_digest.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality._check_digest_quality", new_callable=AsyncMock, return_value=88), \
         patch("services.pipeline_digest.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        posts_created, errors, _usage = await _generate_digest(
            classified=_sample_group(),
            digest_type="research",
            batch_id="2026-04-13",
            handbook_slugs=[],
            raw_content_map={"https://example.com/story": "Source body"},
            community_summary_map={},
            supabase=supabase,
            run_id="run-1",
            enriched_map={
                "https://example.com/story": [
                    {
                        "url": "https://example.com/story",
                        "title": "Primary source",
                        "content": "Official launch details. " * 8,
                        "source_kind": "official_site",
                        "source_confidence": "high",
                        "source_tier": "primary",
                    },
                    {
                        "url": "https://example.com/analysis",
                        "title": "Media coverage",
                        "content": "Coverage and context. " * 8,
                        "source_kind": "media",
                        "source_confidence": "high",
                        "source_tier": "secondary",
                    },
                ]
            },
        )

    assert posts_created == 2
    assert errors == []
    assert any(
        "Source 1 [PRIMARY / official_site / high]: https://example.com/story" in prompt
        for prompt in captured_user_prompts
    )
    assert any(
        "Source 2 [SECONDARY / media / high]: https://example.com/analysis" in prompt
        for prompt in captured_user_prompts
    )


@pytest.mark.asyncio
async def test_generate_digest_saves_source_cards_with_source_metadata():
    from services.pipeline import _generate_digest

    supabase = _CaptureSupabase()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(
                {
                    "en": "## Research Papers\n\n### Expert Heading\n\nExpert body [1](https://example.com/story) [2](https://example.com/analysis)",
                    "ko": "## Research Papers\n\n### 전문가 제목\n\n전문가 본문 [1](https://example.com/story) [2](https://example.com/analysis)",
                    "headline": "Expert headline",
                    "headline_ko": "전문가 헤드라인",
                    "excerpt": "Expert excerpt",
                    "excerpt_ko": "전문가 요약",
                    "sources": [
                        {"url": "https://example.com/story", "title": "Primary source"},
                        {"url": "https://example.com/analysis", "title": "Media coverage"},
                    ],
                }
            ),
            _mock_openai_response(
                {
                    "en": "## Research Papers\n\n### Learner Heading\n\nLearner body [1](https://example.com/story)",
                    "ko": "## Research Papers\n\n### 학습자 제목\n\n학습자 본문 [1](https://example.com/story)",
                    "headline": "Learner headline",
                    "headline_ko": "학습자 헤드라인",
                    "excerpt": "Learner excerpt",
                    "excerpt_ko": "학습자 요약",
                    "sources": [
                        {"url": "https://example.com/story", "title": "Primary source"},
                        {"url": "https://example.com/analysis", "title": "Media coverage"},
                    ],
                }
            ),
        ]
    )

    with patch("services.pipeline_digest.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_digest.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality._check_digest_quality", new_callable=AsyncMock, return_value=88), \
         patch("services.pipeline_digest.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        posts_created, errors, _usage = await _generate_digest(
            classified=_sample_group(),
            digest_type="research",
            batch_id="2026-04-13",
            handbook_slugs=[],
            raw_content_map={"https://example.com/story": "Source body"},
            community_summary_map={},
            supabase=supabase,
            run_id="run-1",
            enriched_map={
                "https://example.com/story": [
                    {
                        "url": "https://example.com/story",
                        "title": "Primary source",
                        "content": "Official launch details. " * 8,
                        "source_kind": "official_site",
                        "source_confidence": "high",
                        "source_tier": "primary",
                    },
                    {
                        "url": "https://example.com/analysis",
                        "title": "Media coverage",
                        "content": "Coverage and context. " * 8,
                        "source_kind": "media",
                        "source_confidence": "high",
                        "source_tier": "secondary",
                    },
                ]
            },
        )

    assert posts_created == 2
    assert errors == []
    for table_name, payload in supabase.saved_rows:
        assert table_name == "news_posts"
        assert payload["source_cards"][0]["source_kind"] == "official_site"
        assert payload["source_cards"][0]["source_confidence"] == "high"
        assert payload["source_cards"][0]["source_tier"] == "primary"
        assert payload["source_cards"][1]["source_kind"] == "media"
        assert payload["source_cards"][1]["source_confidence"] == "high"
        assert payload["source_cards"][1]["source_tier"] == "secondary"


@pytest.mark.asyncio
async def test_generate_digest_orders_primary_sources_first_in_prompt():
    from services.pipeline import _generate_digest

    captured_user_prompts: list[str] = []
    responses = [
        _mock_openai_response(
            {
                "en": "## Research Papers\n\n### Expert Heading\n\nExpert body [1](https://example.com/story)",
                "ko": "## Research Papers\n\n### ?꾨Ц媛 ?쒕ぉ\n\n?꾨Ц媛 蹂몃Ц [1](https://example.com/story)",
                "headline": "Expert headline",
                "headline_ko": "?꾨Ц媛 ?ㅻ뱶?쇱씤",
                "excerpt": "Expert excerpt",
                "excerpt_ko": "?꾨Ц媛 ?붿빟",
                "sources": [{"url": "https://example.com/story", "title": "Primary source"}],
            }
        ),
        _mock_openai_response(
            {
                "en": "## Research Papers\n\n### Learner Heading\n\nLearner body [1](https://example.com/story)",
                "ko": "## Research Papers\n\n### ?숈뒿???쒕ぉ\n\n?숈뒿??蹂몃Ц [1](https://example.com/story)",
                "headline": "Learner headline",
                "headline_ko": "?숈뒿???ㅻ뱶?쇱씤",
                "excerpt": "Learner excerpt",
                "excerpt_ko": "?숈뒿???붿빟",
                "sources": [{"url": "https://example.com/story", "title": "Primary source"}],
            }
        ),
    ]

    async def _capture_create(*args, **kwargs):
        captured_user_prompts.append(kwargs["messages"][1]["content"])
        return responses.pop(0)

    supabase = _CaptureSupabase()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_capture_create)

    with patch("services.pipeline_digest.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_digest.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality._check_digest_quality", new_callable=AsyncMock, return_value=88), \
         patch("services.pipeline_digest.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        posts_created, errors, _usage = await _generate_digest(
            classified=_sample_group(),
            digest_type="research",
            batch_id="2026-04-13",
            handbook_slugs=[],
            raw_content_map={"https://example.com/story": "Source body"},
            community_summary_map={},
            supabase=supabase,
            run_id="run-1",
            enriched_map={
                "https://example.com/story": [
                    {
                        "url": "https://example.com/analysis",
                        "title": "Media coverage",
                        "content": "Coverage and context. " * 8,
                        "source_kind": "media",
                        "source_confidence": "high",
                        "source_tier": "secondary",
                    },
                    {
                        "url": "https://example.com/story",
                        "title": "Primary source",
                        "content": "Official launch details. " * 8,
                        "source_kind": "official_site",
                        "source_confidence": "high",
                        "source_tier": "primary",
                    },
                ]
            },
        )

    assert posts_created == 2
    assert errors == []
    assert any(
        prompt.index("Source 1 [PRIMARY / official_site / high]: https://example.com/story")
        < prompt.index("Source 2 [SECONDARY / media / high]: https://example.com/analysis")
        for prompt in captured_user_prompts
    )


@pytest.mark.asyncio
async def test_generate_digest_recovers_en_when_hangul_leaks_into_en_heading():
    from services.pipeline import _generate_digest

    supabase = _CaptureSupabase()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(
                {
                    "en": "## Research Papers\n\n### ClawBench: 실사용 웹 과제에서의 에이전트 성능 점검\n\nExpert body [1](https://example.com/story)",
                    "ko": "## Research Papers\n\n### ClawBench: 실사용 웹 과제에서의 에이전트 성능 점검\n\n전문가 본문 [1](https://example.com/story)",
                    "headline": "Expert headline",
                    "headline_ko": "전문가 헤드라인",
                    "excerpt": "Expert excerpt",
                    "excerpt_ko": "전문가 요약",
                }
            ),
            _mock_openai_response(
                {
                    "en": "## Research Papers\n\n### Learner Heading\n\nLearner body [1](https://example.com/story)",
                    "ko": "## Research Papers\n\n### 학습자 제목\n\n학습자 본문 [1](https://example.com/story)",
                    "headline": "Learner headline",
                    "headline_ko": "학습자 헤드라인",
                    "excerpt": "Learner excerpt",
                    "excerpt_ko": "학습자 요약",
                }
            ),
            _mock_openai_response(
                {
                    "en": "## Research Papers\n\n### ClawBench: Agent performance on everyday web tasks\n\nRecovered expert body [1](https://example.com/story)"
                }
            ),
        ]
    )

    with patch("services.pipeline_digest.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_digest.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality._check_digest_quality", new_callable=AsyncMock, return_value=88), \
         patch("services.pipeline_digest.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        posts_created, errors, _usage = await _generate_digest(
            classified=_sample_group(),
            digest_type="research",
            batch_id="2026-04-13",
            handbook_slugs=[],
            raw_content_map={"https://example.com/story": "Source body"},
            community_summary_map={},
            supabase=supabase,
            run_id="run-1",
            enriched_map={},
        )

    assert posts_created == 2
    assert errors == []
    en_row = next(payload for _table, payload in supabase.saved_rows if payload["locale"] == "en")
    assert "Agent performance on everyday web tasks" in en_row["content_expert"]


@pytest.mark.asyncio
async def test_generate_digest_surfaces_url_validation_to_fact_pack_and_forces_draft():
    """Phase 2 regression guard: url_validation_failed on quality_meta must
    (1) land in the persisted fact_pack, and (2) force auto_publish_eligible=False
    even when the caller passed auto_publish=True. Catches the 2026-04-16 bug where
    the fact_pack whitelist dropped Phase 2 fields.
    """
    from services.pipeline import _generate_digest

    supabase = _CaptureSupabase()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response({
                "en": "## Research Papers\n\n### Expert\n\nBody [1](https://example.com/story)",
                "ko": "## Research Papers\n\n### 전문가\n\n본문 [1](https://example.com/story)",
                "headline": "H", "headline_ko": "헤",
                "excerpt": "E", "excerpt_ko": "요",
                "sources": [{"url": "https://example.com/story", "title": "S"}],
            }),
            _mock_openai_response({
                "en": "## Research Papers\n\n### Learner\n\nBody [1](https://example.com/story)",
                "ko": "## Research Papers\n\n### 학습자\n\n본문 [1](https://example.com/story)",
                "headline": "H", "headline_ko": "헤",
                "excerpt": "E", "excerpt_ko": "요",
                "sources": [{"url": "https://example.com/story", "title": "S"}],
            }),
        ]
    )

    # Simulate _check_digest_quality reporting a URL validation failure.
    quality_meta_with_failure = {
        "score": 95,
        "quality_score": 95,
        "quality_version": "v2",
        "quality_breakdown": {},
        "quality_issues": [],
        "quality_caps_applied": [],
        "structural_penalty": 0,
        "structural_warnings": [],
        "url_validation_failed": True,
        "url_validation_failures": [
            {"persona": "expert", "locale": "en",
             "unknown_urls": ["https://hallucinated.example.com/fake"],
             "citation_count": 1},
        ],
        "auto_publish_eligible": False,
    }

    with patch("services.pipeline_digest.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_digest.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality._check_digest_quality",
               new_callable=AsyncMock, return_value=quality_meta_with_failure), \
         patch("services.pipeline_digest.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        posts_created, errors, _usage = await _generate_digest(
            classified=_sample_group(),
            digest_type="research",
            batch_id="2026-04-15",
            handbook_slugs=[],
            raw_content_map={"https://example.com/story": "Source body"},
            community_summary_map={},
            supabase=supabase,
            run_id="run-1",
            enriched_map={},
            auto_publish=True,  # caller requested auto-publish — must be overridden
        )

    assert posts_created == 2
    assert errors == []
    assert len(supabase.saved_rows) == 2
    for _table, payload in supabase.saved_rows:
        fp = payload["fact_pack"]
        # (1) URL validation outcome surfaced to DB
        assert fp["url_validation_failed"] is True, \
            f"url_validation_failed missing from fact_pack: keys={list(fp.keys())}"
        assert fp["url_validation_failures"], "url_validation_failures should not be empty"
        # (2) auto_publish=True was overridden to False due to validation failure
        assert fp["auto_publish_eligible"] is False, \
            "auto_publish_eligible must be False when url_validation_failed=True"


@pytest.mark.asyncio
async def test_generate_digest_surfaces_url_validation_pass_state_to_fact_pack():
    """Happy path: url_validation_failed=False must also land in fact_pack (not null).
    Ensures the field is always surfaced, not just when failures occur.
    """
    from services.pipeline import _generate_digest

    supabase = _CaptureSupabase()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response({
                "en": "## Research Papers\n\n### Expert\n\nBody [1](https://example.com/story)",
                "ko": "## Research Papers\n\n### 전문가\n\n본문 [1](https://example.com/story)",
                "headline": "H", "headline_ko": "헤",
                "excerpt": "E", "excerpt_ko": "요",
                "sources": [{"url": "https://example.com/story", "title": "S"}],
            }),
            _mock_openai_response({
                "en": "## Research Papers\n\n### Learner\n\nBody [1](https://example.com/story)",
                "ko": "## Research Papers\n\n### 학습자\n\n본문 [1](https://example.com/story)",
                "headline": "H", "headline_ko": "헤",
                "excerpt": "E", "excerpt_ko": "요",
                "sources": [{"url": "https://example.com/story", "title": "S"}],
            }),
        ]
    )

    quality_meta_clean = {
        "score": 90, "quality_score": 90, "quality_version": "v2",
        "quality_breakdown": {}, "quality_issues": [], "quality_caps_applied": [],
        "structural_penalty": 0, "structural_warnings": [],
        "url_validation_failed": False,
        "url_validation_failures": [],
    }

    with patch("services.pipeline_digest.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_digest.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality._check_digest_quality",
               new_callable=AsyncMock, return_value=quality_meta_clean), \
         patch("services.pipeline_digest.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        posts_created, errors, _usage = await _generate_digest(
            classified=_sample_group(),
            digest_type="research",
            batch_id="2026-04-15",
            handbook_slugs=[],
            raw_content_map={"https://example.com/story": "Source body"},
            community_summary_map={},
            supabase=supabase,
            run_id="run-1",
            enriched_map={},
        )

    assert posts_created == 2
    for _table, payload in supabase.saved_rows:
        fp = payload["fact_pack"]
        assert fp.get("url_validation_failed") is False, \
            f"expected url_validation_failed=False, got {fp.get('url_validation_failed')}"
        assert fp.get("url_validation_failures") == []
