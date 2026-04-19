"""Tests for the current daily pipeline orchestrator."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import (
    ClassifiedCandidate,
    ClassifiedGroup,
    ClassificationResult,
    CommunityInsight,
    GroupedItem,
    NewsCandidate,
)


SAMPLE_CANDIDATES = [
    NewsCandidate(title="GPT-5", url="https://a.com/1", snippet="Model release", source="tavily"),
    NewsCandidate(title="AI Fund", url="https://b.com/2", snippet="$500M raised", source="tavily"),
]

SAMPLE_COLLECT_META = {
    "is_backfill": False,
    "queries": ["latest AI artificial intelligence news today"],
    "date_kwargs": {"days": 2},
    "total_results": 2,
    "unique_candidates": 2,
}

SAMPLE_CLASSIFY_RESULT = ClassificationResult(
    research_picks=[
        ClassifiedCandidate(
            title="GPT-5",
            url="https://a.com/1",
            snippet="Model release",
            source="tavily",
            category="research",
            subcategory="llm_models",
            reason="Major",
        ),
    ],
    business_picks=[
        ClassifiedCandidate(
            title="AI Fund",
            url="https://b.com/2",
            snippet="$500M raised",
            source="tavily",
            category="business",
            subcategory="industry",
            reason="Big funding",
        ),
    ],
)

SAMPLE_MERGED_RESULT = ClassificationResult(
    research=[
        ClassifiedGroup(
            group_title="GPT-5",
            items=[GroupedItem(url="https://a.com/1", title="GPT-5")],
            category="research",
            subcategory="llm_models",
            reason="Major",
        ),
    ],
    business=[
        ClassifiedGroup(
            group_title="AI Fund",
            items=[GroupedItem(url="https://b.com/2", title="AI Fund")],
            category="business",
            subcategory="industry",
            reason="Big funding",
        ),
    ],
    research_picks=SAMPLE_CLASSIFY_RESULT.research_picks,
    business_picks=SAMPLE_CLASSIFY_RESULT.business_picks,
)

EMPTY_USAGE = {"model_used": "gpt-4o", "input_tokens": 0, "output_tokens": 0, "tokens_used": 0, "cost_usd": 0.0}


class _Query:
    def __init__(self, data):
        self._data = data

    def select(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def upsert(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return MagicMock(data=self._data)


class _Supabase:
    def table(self, name):
        if name == "pipeline_runs":
            return _Query([])
        if name == "news_posts":
            return _Query([])
        if name == "pipeline_logs":
            return _Query([])
        return _Query([])


def _community_summary_map():
    return {
        "https://a.com/1": CommunityInsight(sentiment="positive", quotes=[], quotes_ko=[]),
        "https://b.com/2": CommunityInsight(sentiment="mixed", quotes=[], quotes_ko=[]),
    }


class _InsertCaptureQuery:
    def __init__(self, supabase, name):
        self.supabase = supabase
        self.name = name
        self._insert_payload = None

    def select(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def upsert(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def is_(self, *args, **kwargs):
        return self

    def execute(self):
        if self.name == "handbook_terms" and self._insert_payload is not None:
            self.supabase.inserted_rows.append(self._insert_payload)
            return MagicMock(data=[{"id": "term-row-1"}])
        return MagicMock(data=[])


class _HandbookInsertCaptureSupabase:
    def __init__(self):
        self.inserted_rows = []

    def table(self, name):
        return _InsertCaptureQuery(self, name)


@pytest.mark.asyncio
async def test_run_daily_pipeline_happy_path():
    """Current pipeline creates 4 digest rows when both categories survive."""
    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(SAMPLE_CLASSIFY_RESULT, EMPTY_USAGE, "prompt body")), \
         patch("services.pipeline.merge_classified", new_callable=AsyncMock, return_value=(SAMPLE_MERGED_RESULT, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="community raw"), \
         patch("services.pipeline.summarize_community", new_callable=AsyncMock, return_value=(_community_summary_map(), EMPTY_USAGE)), \
         patch("services.pipeline.rank_classified", new_callable=AsyncMock, side_effect=[(SAMPLE_MERGED_RESULT.research, EMPTY_USAGE), (SAMPLE_MERGED_RESULT.business, EMPTY_USAGE)]), \
         patch("services.pipeline.enrich_sources", new_callable=AsyncMock, return_value={}), \
         patch("services.pipeline._fetch_handbook_slugs", return_value=[]), \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock, return_value=(2, [], EMPTY_USAGE)):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 4
    assert result.errors == []
    assert result.batch_id


@pytest.mark.asyncio
async def test_pipeline_no_research_creates_2_posts():
    """When only business survives after classify, only the business digest is created."""
    classification_no_research = ClassificationResult(
        business_picks=SAMPLE_CLASSIFY_RESULT.business_picks,
    )
    merged_no_research = ClassificationResult(
        business=SAMPLE_MERGED_RESULT.business,
        business_picks=SAMPLE_CLASSIFY_RESULT.business_picks,
    )

    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(classification_no_research, EMPTY_USAGE, "prompt body")), \
         patch("services.pipeline.merge_classified", new_callable=AsyncMock, return_value=(merged_no_research, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="community raw"), \
         patch("services.pipeline.summarize_community", new_callable=AsyncMock, return_value=(_community_summary_map(), EMPTY_USAGE)), \
         patch("services.pipeline.rank_classified", new_callable=AsyncMock, side_effect=[([], EMPTY_USAGE), (merged_no_research.business, EMPTY_USAGE)]), \
         patch("services.pipeline.enrich_sources", new_callable=AsyncMock, return_value={}), \
         patch("services.pipeline._fetch_handbook_slugs", return_value=[]), \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock, return_value=(2, [], EMPTY_USAGE)):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 2


@pytest.mark.asyncio
async def test_pipeline_no_candidates_returns_zero_posts():
    """Empty collect result returns 0 posts without error."""
    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=([], {})):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert result.errors == []


@pytest.mark.asyncio
async def test_pipeline_digest_failure_continues():
    """Digest generation failure for one category should not stop the other."""
    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(SAMPLE_CLASSIFY_RESULT, EMPTY_USAGE, "prompt body")), \
         patch("services.pipeline.merge_classified", new_callable=AsyncMock, return_value=(SAMPLE_MERGED_RESULT, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="community raw"), \
         patch("services.pipeline.summarize_community", new_callable=AsyncMock, return_value=(_community_summary_map(), EMPTY_USAGE)), \
         patch("services.pipeline.rank_classified", new_callable=AsyncMock, side_effect=[(SAMPLE_MERGED_RESULT.research, EMPTY_USAGE), (SAMPLE_MERGED_RESULT.business, EMPTY_USAGE)]), \
         patch("services.pipeline.enrich_sources", new_callable=AsyncMock, return_value={}), \
         patch("services.pipeline._fetch_handbook_slugs", return_value=[]), \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock, side_effect=[Exception("digest failed"), (2, [], EMPTY_USAGE)]):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 2
    assert any("Digest generation failed" in error for error in result.errors)


@pytest.mark.asyncio
async def test_pipeline_supabase_not_configured():
    """Pipeline without Supabase should fail gracefully."""
    with patch("services.pipeline.get_supabase", return_value=None):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert any("not configured" in e.lower() for e in result.errors)


@pytest.mark.asyncio
async def test_extract_and_create_handbook_terms_persists_hero_and_references_fields():
    from services.pipeline import _extract_and_create_handbook_terms

    supabase = _HandbookInsertCaptureSupabase()
    extracted_terms = [
        {
            "term": "Function Calling",
            "korean_name": "함수 호출",
            "category": "llm-genai",
            "secondary_categories": ["products-platforms"],
            "confidence": "high",
        }
    ]
    generated_content = {
        "korean_name": "함수 호출",
        "term_full": "Function Calling",
        "korean_full": "함수 호출",
        "categories": ["llm-genai", "products-platforms"],
        "summary_ko": "학습자용 요약 ko",
        "summary_en": "Learner summary en",
        "definition_ko": "ko definition " * 20,
        "definition_en": "en definition " * 20,
        "body_basic_ko": "ko basic " * 300,
        "body_basic_en": "en basic " * 300,
        "body_advanced_ko": "ko advanced " * 320,
        "body_advanced_en": "en advanced " * 320,
        "hero_news_context_ko": "\"quote1\" → 의미1\n\"quote2\" → 의미2\n\"quote3\" → 의미3",
        "hero_news_context_en": "\"quote1\" -> meaning1\n\"quote2\" -> meaning2\n\"quote3\" -> meaning3",
        "references_ko": [{"title": "KO Ref", "type": "docs", "url": "https://example.com/ko", "tier": "primary", "annotation": "ko"}],
        "references_en": [{"title": "EN Ref", "type": "docs", "url": "https://example.com/en", "tier": "primary", "annotation": "en"}],
        "term_type": "api_feature",
        "facet_intent": ["build"],
        "facet_volatility": "evolving",
    }

    with patch("services.pipeline.extract_terms_from_content", new=AsyncMock(return_value=(extracted_terms, EMPTY_USAGE))), \
         patch("services.pipeline.generate_term_content", new=AsyncMock(return_value=(generated_content.copy(), EMPTY_USAGE))), \
         patch("services.pipeline.gate_candidate_terms", new=AsyncMock(return_value=[{"term": "Function Calling", "korean_name": "함수 호출"}])), \
         patch("services.pipeline._log_stage", new=AsyncMock()):
        created, errors = await _extract_and_create_handbook_terms(
            article_texts=["Function Calling helps models choose tools."],
            supabase=supabase,
            run_id="run-1",
        )

    assert created == 1
    assert errors == []
    assert len(supabase.inserted_rows) == 1
    row = supabase.inserted_rows[0]
    assert row["hero_news_context_ko"] == generated_content["hero_news_context_ko"]
    assert row["hero_news_context_en"] == generated_content["hero_news_context_en"]
    assert row["references_ko"] == generated_content["references_ko"]
    assert row["references_en"] == generated_content["references_en"]
    assert row["summary_ko"] == generated_content["summary_ko"]
    assert row["summary_en"] == generated_content["summary_en"]


@pytest.mark.asyncio
async def test_extract_and_create_handbook_terms_queues_gate_downgraded_candidates():
    from services.pipeline import _extract_and_create_handbook_terms

    supabase = _HandbookInsertCaptureSupabase()
    extracted_terms = [
        {
            "term": "EquiformerV3",
            "korean_name": "EquiformerV3",
            "category": "deep-learning",
            "secondary_categories": ["data-engineering"],
            "confidence": "high",
            "reason": "Mentioned in the article as a technical architecture",
        }
    ]

    gate_mock = AsyncMock(
        return_value=[
            {
                "term": "EquiformerV3",
                "decision": "queue",
                "reason": "versioned niche model name; queue for manual review",
            }
        ]
    )

    with patch("services.pipeline.extract_terms_from_content", new=AsyncMock(return_value=(extracted_terms, EMPTY_USAGE))), \
         patch("services.pipeline.generate_term_content", new=AsyncMock()), \
         patch("services.pipeline.gate_candidate_terms", new=gate_mock), \
         patch("services.pipeline._log_stage", new=AsyncMock()):
        created, errors = await _extract_and_create_handbook_terms(
            article_texts=["EquiformerV3 improves molecular modeling throughput."],
            supabase=supabase,
            run_id="run-1",
        )

    assert created == 0
    assert errors == []
    assert len(supabase.inserted_rows) == 1
    row = supabase.inserted_rows[0]
    assert row["term"] == "EquiformerV3"
    assert row["status"] == "queued"
    assert row["source"] == "pipeline"
    assert "definition_ko" not in row


@pytest.mark.asyncio
async def test_extract_and_create_handbook_terms_passes_category_and_reason_to_gate():
    from services.pipeline import _extract_and_create_handbook_terms

    supabase = _HandbookInsertCaptureSupabase()
    extracted_terms = [
        {
            "term": "Reversible transforms",
            "korean_name": "가역 변환",
            "category": "data-engineering",
            "secondary_categories": ["ml-fundamentals"],
            "confidence": "high",
            "reason": "Article frames it as a transform class for round-trip restoration",
        }
    ]

    gate_mock = AsyncMock(return_value=[
        {
            "term": "Reversible transforms",
            "decision": "reject",
            "reason": "descriptive umbrella phrase, not canonical enough",
        }
    ])

    with patch("services.pipeline.extract_terms_from_content", new=AsyncMock(return_value=(extracted_terms, EMPTY_USAGE))), \
         patch("services.pipeline.generate_term_content", new=AsyncMock()), \
         patch("services.pipeline.gate_candidate_terms", new=gate_mock), \
         patch("services.pipeline._log_stage", new=AsyncMock()):
        created, errors = await _extract_and_create_handbook_terms(
            article_texts=["Reversible transforms can restore original representations after preprocessing."],
            supabase=supabase,
            run_id="run-1",
        )

    assert created == 0
    assert errors == []
    gate_candidates, existing_names = gate_mock.await_args.args
    assert existing_names == []
    assert gate_candidates == [
        {
            "term": "Reversible transforms",
            "korean_name": "가역 변환",
            "category": "data-engineering",
            "secondary_categories": ["ml-fundamentals"],
            "reason": "Article frames it as a transform class for round-trip restoration",
        }
    ]
