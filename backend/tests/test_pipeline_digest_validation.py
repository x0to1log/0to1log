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

    with patch("services.pipeline.get_openai_client", return_value=mock_client), \
         patch("services.pipeline.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline._check_digest_quality", new_callable=AsyncMock) as quality_mock, \
         patch("services.pipeline.settings") as mock_settings:
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

    with patch("services.pipeline.get_openai_client", return_value=mock_client), \
         patch("services.pipeline.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline._check_digest_quality", new_callable=AsyncMock, return_value=88), \
         patch("services.pipeline.settings") as mock_settings:
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

    with patch("services.pipeline.get_openai_client", return_value=mock_client), \
         patch("services.pipeline.get_digest_prompt", return_value="prompt"), \
         patch("services.pipeline._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline._check_digest_quality", new_callable=AsyncMock, return_value=88), \
         patch("services.pipeline.settings") as mock_settings:
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
