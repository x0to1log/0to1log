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


EMPTY_USAGE = {"model_used": "gpt-4o", "input_tokens": 0, "output_tokens": 0, "tokens_used": 0, "cost_usd": 0.0}

SAMPLE_CANDIDATES = [
    NewsCandidate(title="GPT-5", url="https://a.com/1", snippet="Model release", source="tavily"),
    NewsCandidate(title="AI Fund", url="https://b.com/2", snippet="$500M raised", source="tavily"),
]

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


class _Query:
    def __init__(self, data):
        self._data = data
        self.updated_payloads = []

    def select(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        if args:
            self.updated_payloads.append(args[0])
        return self

    def delete(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def execute(self):
        return MagicMock(data=self._data)


class _Supabase:
    def __init__(self):
        self.pipeline_runs_query = _Query([{"id": "run-id"}])

    def table(self, name):
        if name == "pipeline_runs":
            return self.pipeline_runs_query
        if name == "news_posts":
            return _Query([])
        return _Query([])


@pytest.mark.asyncio
async def test_rerun_pipeline_stage_classify_accepts_three_value_classify_result():
    def _load_checkpoint(_supabase, _run_id, stage):
        if stage == "collect":
            return {"candidates": [c.model_dump() for c in SAMPLE_CANDIDATES]}
        return None

    community_summary_map = {
        "https://a.com/1": CommunityInsight(sentiment="positive", quotes=[], quotes_ko=[]),
        "https://b.com/2": CommunityInsight(sentiment="positive", quotes=[], quotes_ko=[]),
    }

    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline._load_checkpoint", side_effect=_load_checkpoint), \
         patch("services.pipeline._fetch_handbook_slugs", return_value=[]), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(SAMPLE_CLASSIFY_RESULT, EMPTY_USAGE, "prompt body")), \
         patch("services.pipeline.merge_classified", new_callable=AsyncMock, return_value=(SAMPLE_MERGED_RESULT, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="community raw"), \
         patch("services.pipeline.summarize_community", new_callable=AsyncMock, return_value=(community_summary_map, EMPTY_USAGE)), \
         patch("services.pipeline.rank_classified", new_callable=AsyncMock, side_effect=[(SAMPLE_MERGED_RESULT.research, EMPTY_USAGE), (SAMPLE_MERGED_RESULT.business, EMPTY_USAGE)]), \
         patch("services.pipeline.enrich_sources", new_callable=AsyncMock, return_value={}), \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock, return_value=(2, [], EMPTY_USAGE)), \
         patch("services.pipeline._save_checkpoint"), \
         patch("services.pipeline._log_stage", new_callable=AsyncMock):
        from services.pipeline import rerun_pipeline_stage

        result = await rerun_pipeline_stage(
            source_run_id="run-id",
            from_stage="classify",
            batch_id="2026-04-13",
        )

    assert result.status == "success"
    assert result.posts_created == 4


@pytest.mark.asyncio
async def test_rerun_pipeline_stage_marks_partial_digest_failure_as_failed():
    supabase = _Supabase()

    def _load_checkpoint(_supabase, _run_id, stage):
        if stage == "collect":
            return {"candidates": [c.model_dump() for c in SAMPLE_CANDIDATES]}
        return None

    community_summary_map = {
        "https://a.com/1": CommunityInsight(sentiment="positive", quotes=[], quotes_ko=[]),
        "https://b.com/2": CommunityInsight(sentiment="positive", quotes=[], quotes_ko=[]),
    }

    with patch("services.pipeline.get_supabase", return_value=supabase), \
         patch("services.pipeline._load_checkpoint", side_effect=_load_checkpoint), \
         patch("services.pipeline._fetch_handbook_slugs", return_value=[]), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(SAMPLE_CLASSIFY_RESULT, EMPTY_USAGE, "prompt body")), \
         patch("services.pipeline.merge_classified", new_callable=AsyncMock, return_value=(SAMPLE_MERGED_RESULT, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="community raw"), \
         patch("services.pipeline.summarize_community", new_callable=AsyncMock, return_value=(community_summary_map, EMPTY_USAGE)), \
         patch("services.pipeline.rank_classified", new_callable=AsyncMock, side_effect=[(SAMPLE_MERGED_RESULT.research, EMPTY_USAGE), (SAMPLE_MERGED_RESULT.business, EMPTY_USAGE)]), \
         patch("services.pipeline.enrich_sources", new_callable=AsyncMock, return_value={}), \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock, side_effect=[(0, ["research blocked"], EMPTY_USAGE), (2, [], EMPTY_USAGE)]), \
         patch("services.pipeline._save_checkpoint"), \
         patch("services.pipeline._log_stage", new_callable=AsyncMock) as log_stage:
        from services.pipeline import rerun_pipeline_stage

        result = await rerun_pipeline_stage(
            source_run_id="run-id",
            from_stage="classify",
            batch_id="2026-04-13",
        )

    assert result.status == "failed"
    assert result.posts_created == 2
    assert result.errors == ["research blocked"]
    assert any(
        call.args[2] == "summary" and call.args[3] == "failed"
        for call in log_stage.await_args_list
    )
    assert any(payload.get("status") == "failed" for payload in supabase.pipeline_runs_query.updated_payloads)
