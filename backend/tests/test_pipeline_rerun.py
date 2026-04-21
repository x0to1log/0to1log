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
from services.pipeline import _load_personas_and_frontload_from_db


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


def test_load_personas_and_frontload_from_db_builds_two_types():
    """Loader reconstructs PersonaOutput (EN+KO) and frontload for both digest_types from existing news_posts rows."""
    supabase = MagicMock()

    # Four expected rows: research-EN, research-KO, business-EN, business-KO
    rows = [
        {
            "slug": "2026-04-19-research-digest",
            "locale": "en",
            "post_type": "research",
            "content_expert": "EN expert body",
            "content_learner": "EN learner body",
            "title": "Research headline",
            "excerpt": "Research excerpt",
            "focus_items": ["a", "b", "c"],
            "guide_items": {"title_learner": "Research learner title", "excerpt_learner": "Research learner excerpt"},
        },
        {
            "slug": "2026-04-19-research-digest-ko",
            "locale": "ko",
            "post_type": "research",
            "content_expert": "KO expert body",
            "content_learner": "KO learner body",
            "title": "Research headline KO",
            "excerpt": "Research excerpt KO",
            "focus_items": ["\u3131", "\u3134", "\u3137"],
            "guide_items": {},
        },
        {
            "slug": "2026-04-19-business-digest",
            "locale": "en",
            "post_type": "business",
            "content_expert": "B-EN expert",
            "content_learner": "B-EN learner",
            "title": "Business headline",
            "excerpt": "Business excerpt",
            "focus_items": ["x", "y", "z"],
            "guide_items": {},
        },
        {
            "slug": "2026-04-19-business-digest-ko",
            "locale": "ko",
            "post_type": "business",
            "content_expert": "B-KO expert",
            "content_learner": "B-KO learner",
            "title": "Business headline KO",
            "excerpt": "Business excerpt KO",
            "focus_items": [],
            "guide_items": {},
        },
    ]
    supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = rows

    personas_by_type, frontload_by_type = _load_personas_and_frontload_from_db(supabase, "2026-04-19")

    # Two digest types reconstructed
    assert set(personas_by_type.keys()) == {"research", "business"}
    assert set(frontload_by_type.keys()) == {"research", "business"}

    # Research personas merged EN + KO
    research_personas = personas_by_type["research"]
    assert research_personas["expert"].en == "EN expert body"
    assert research_personas["expert"].ko == "KO expert body"
    assert research_personas["learner"].en == "EN learner body"
    assert research_personas["learner"].ko == "KO learner body"

    # Business personas
    assert personas_by_type["business"]["expert"].en == "B-EN expert"
    assert personas_by_type["business"]["expert"].ko == "B-KO expert"

    # Frontload from EN row, with focus_items_ko from KO row's focus_items
    research_front = frontload_by_type["research"]
    assert research_front["headline"] == "Research headline"
    assert research_front["headline_ko"] == "Research headline KO"
    assert research_front["excerpt"] == "Research excerpt"
    assert research_front["excerpt_ko"] == "Research excerpt KO"
    assert research_front["focus_items"] == ["a", "b", "c"]
    assert research_front["focus_items_ko"] == ["\u3131", "\u3134", "\u3137"]


def test_load_personas_and_frontload_returns_empty_on_missing_rows():
    """When no news_posts match the batch, the loader returns empty dicts (caller handles)."""
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = []

    personas_by_type, frontload_by_type = _load_personas_and_frontload_from_db(supabase, "2026-04-19")
    assert personas_by_type == {}
    assert frontload_by_type == {}


def test_load_personas_and_frontload_uses_guide_items_fallback_when_ko_row_lacks_title_excerpt():
    """When ko_row has no title/excerpt, the frontload builder should fall back to en_row's
    guide_items.title_learner / excerpt_learner. This covers the MEMORY.md-flagged
    title_learner field's fallback path."""
    supabase = MagicMock()
    rows = [
        {
            "slug": "2026-04-19-research-digest",
            "locale": "en",
            "post_type": "research",
            "content_expert": "EN expert",
            "content_learner": "EN learner",
            "title": "Research EN",
            "excerpt": "Excerpt EN",
            "focus_items": ["a"],
            "guide_items": {"title_learner": "Guide title KO", "excerpt_learner": "Guide excerpt KO"},
        },
        {
            "slug": "2026-04-19-research-digest-ko",
            "locale": "ko",
            "post_type": "research",
            "content_expert": "KO expert",
            "content_learner": "KO learner",
            "title": None,  # missing — triggers guide_items fallback
            "excerpt": None,
            "focus_items": [],
            "guide_items": {},
        },
    ]
    supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = rows

    _, frontload_by_type = _load_personas_and_frontload_from_db(supabase, "2026-04-19")
    research_front = frontload_by_type["research"]

    assert research_front["headline_ko"] == "Guide title KO", \
        f"expected guide_items.title_learner fallback, got {research_front['headline_ko']!r}"
    assert research_front["excerpt_ko"] == "Guide excerpt KO", \
        f"expected guide_items.excerpt_learner fallback, got {research_front['excerpt_ko']!r}"


def _build_supabase_mock_for_quality_rerun(news_rows: list, checkpoint_returns=None):
    """Shared helper: build a MagicMock supabase for quality-rerun tests.

    Sets up:
      - pipeline_runs claim (.update.eq.neq.execute.data = [{"id": "run-1"}])
      - published guard (.select.eq.eq.execute.data = [])  — bypass guard
      - news_posts personas-loader (.select.eq.in_.execute.data = news_rows)
      - fact_pack read per slug (.select.eq.limit.execute.data = [{"fact_pack": {}}])
      - generic update/delete chains return MagicMock (no data check)
    """
    supabase = MagicMock()
    # pipeline_runs claim-and-lock
    supabase.table.return_value.update.return_value.eq.return_value.neq.return_value.execute.return_value.data = [{"id": "run-1"}]
    # log-delete path
    supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    # news_posts update (quality payload) + final pipeline_runs update
    supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # news_posts load via loader helper (.select.eq.in_.execute)
    supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = news_rows
    # Published guard (.select.eq.eq.execute.data) — must be empty/falsy to bypass
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    # fact_pack read per slug (.select.eq.limit.execute) — empty existing fact_pack
    supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"fact_pack": {}}]
    return supabase


@pytest.mark.asyncio
async def test_rerun_from_quality_skips_digest_generation_and_writes_payload():
    """rerun_from='quality' must:
      1. call _check_digest_quality (not _generate_digest)
      2. update BOTH locale rows with quality_score, quality_flags, and fact_pack
         (news_posts.updated_at is auto-set by Supabase trigger on any UPDATE)
      3. NEVER write content_analysis — that's a user-facing markdown column
         (Core Analysis section); QC data goes into fact_pack (admin/internal)
      4. return status=success
    """
    from services.pipeline import rerun_pipeline_stage

    news_rows = [
        {"slug": "2026-04-19-research-digest", "locale": "en", "post_type": "research",
         "content_expert": "E", "content_learner": "L", "title": "t", "excerpt": "x",
         "focus_items": [], "guide_items": {}},
        {"slug": "2026-04-19-research-digest-ko", "locale": "ko", "post_type": "research",
         "content_expert": "E-ko", "content_learner": "L-ko", "title": "t-ko", "excerpt": "x-ko",
         "focus_items": [], "guide_items": {}},
    ]
    supabase = _build_supabase_mock_for_quality_rerun(news_rows)

    with patch("services.pipeline.get_supabase", return_value=supabase), \
         patch("services.pipeline._load_checkpoint", return_value=None), \
         patch("services.pipeline._check_digest_quality", new_callable=AsyncMock) as qc_mock, \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock) as gen_mock, \
         patch("services.pipeline._log_stage", new_callable=AsyncMock):
        qc_mock.return_value = {
            "score": 84,
            "quality_score": 84,
            "quality_flags": [],
            "quality_issues": [{"severity": "minor", "scope": "frontload", "message": "ex"}],
            "quality_breakdown": {"total_score": 84, "factuality": {}},
            # NEW: per-QC-call breakdowns (NQ-34)
            "expert_breakdown": {"structural_completeness": {"sections_present": {"evidence": "e1", "score": 10}}},
            "learner_breakdown": {"structural_completeness": {"sections_present": {"evidence": "e2", "score": 9}}},
            "frontload_breakdown": {"factuality": {"number_grounding": {"evidence": "e3", "score": 10}}},
            "quality_version": "v1",
            "quality_caps_applied": [],
            "structural_penalty": 0,
            "structural_warnings": [],
            "url_validation_failed": False,
            "url_validation_failures": [],
        }

        result = await rerun_pipeline_stage(
            source_run_id="run-1",
            from_stage="quality",
            batch_id="2026-04-19",
            category="research",
        )

        assert qc_mock.await_count == 1
        assert gen_mock.await_count == 0
        assert result.status == "success"

        update_calls = [
            c for c in supabase.table.return_value.update.call_args_list
            if c.args and isinstance(c.args[0], dict) and "quality_score" in c.args[0]
        ]
        assert len(update_calls) == 2, f"expected 2 locale updates, got {len(update_calls)}"
        for c in update_calls:
            payload = c.args[0]
            assert payload["quality_score"] == 84
            assert payload["quality_flags"] == []
            # QC data MUST land in fact_pack (not content_analysis — see docstring)
            assert "fact_pack" in payload
            fp = payload["fact_pack"]
            assert fp["quality_score"] == 84
            assert fp["quality_breakdown"] == {"total_score": 84, "factuality": {}}
            assert fp["quality_issues"] == [{"severity": "minor", "scope": "frontload", "message": "ex"}]
            # Per-call breakdowns for admin drill-down (NQ-34)
            assert "expert_breakdown" in fp
            assert "learner_breakdown" in fp
            assert "frontload_breakdown" in fp
            assert fp["expert_breakdown"]["structural_completeness"]["sections_present"]["score"] == 10
            assert fp["learner_breakdown"]["structural_completeness"]["sections_present"]["score"] == 9
            assert fp["frontload_breakdown"]["factuality"]["number_grounding"]["evidence"] == "e3"
            # content_analysis must NOT be touched — that column is user-facing markdown
            assert "content_analysis" not in payload
            # updated_at is trigger-managed by Supabase — we don't send it explicitly
            assert "analyzed_at" not in payload


@pytest.mark.asyncio
async def test_rerun_from_quality_hydrates_classified_and_community_from_checkpoints():
    """When merge + community_summarize checkpoints are present, the quality branch
    must hydrate them into ClassifiedGroup / CommunityInsight objects."""
    from services.pipeline import rerun_pipeline_stage

    news_rows = [
        {"slug": "2026-04-19-research-digest", "locale": "en", "post_type": "research",
         "content_expert": "E", "content_learner": "L", "title": "t", "excerpt": "x",
         "focus_items": [], "guide_items": {}},
        {"slug": "2026-04-19-research-digest-ko", "locale": "ko", "post_type": "research",
         "content_expert": "E-ko", "content_learner": "L-ko", "title": "t-ko", "excerpt": "x-ko",
         "focus_items": [], "guide_items": {}},
    ]
    supabase = _build_supabase_mock_for_quality_rerun(news_rows)

    merge_ckpt = {
        "research": [{
            "group_title": "Anthropic releases Claude 4.7",
            "items": [],
            "category": "research",
            "subcategory": "llm_models",
            "reason": "Major release",
        }],
        "business": [],
    }
    community_ckpt = {
        "summaries": {
            "https://example.com/a": {
                "sentiment": "positive",
                "quotes": [],
                "quotes_ko": [],
            }
        }
    }

    def load_ckpt_side_effect(sb, run_id, stage):
        return {"merge": merge_ckpt, "community_summarize": community_ckpt}.get(stage)

    with patch("services.pipeline.get_supabase", return_value=supabase), \
         patch("services.pipeline._load_checkpoint", side_effect=load_ckpt_side_effect), \
         patch("services.pipeline._check_digest_quality", new_callable=AsyncMock) as qc_mock, \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock) as gen_mock, \
         patch("services.pipeline._log_stage", new_callable=AsyncMock):
        qc_mock.return_value = {
            "score": 80, "quality_score": 80,
            "quality_flags": [], "quality_issues": [],
            "quality_breakdown": {"total_score": 80},
        }

        await rerun_pipeline_stage(
            source_run_id="run-1",
            from_stage="quality",
            batch_id="2026-04-19",
            category="research",
        )

        assert gen_mock.await_count == 0
        assert qc_mock.await_count == 1
        kwargs = qc_mock.await_args.kwargs
        assert len(kwargs["classified"]) == 1
        assert isinstance(kwargs["classified"][0], ClassifiedGroup)
        assert "https://example.com/a" in kwargs["community_summary_map"]
        assert isinstance(kwargs["community_summary_map"]["https://example.com/a"], CommunityInsight)


@pytest.mark.asyncio
async def test_rerun_from_quality_with_no_category_filter_rescores_both_types():
    """When category=None, the quality branch must rescore BOTH research and business.
    Covers the branch where the category filter is off — previously only the
    category='research' path was tested."""
    from services.pipeline import rerun_pipeline_stage

    news_rows = [
        # research
        {"slug": "2026-04-19-research-digest", "locale": "en", "post_type": "research",
         "content_expert": "E", "content_learner": "L", "title": "t", "excerpt": "x",
         "focus_items": [], "guide_items": {}},
        {"slug": "2026-04-19-research-digest-ko", "locale": "ko", "post_type": "research",
         "content_expert": "E-ko", "content_learner": "L-ko", "title": "t-ko", "excerpt": "x-ko",
         "focus_items": [], "guide_items": {}},
        # business
        {"slug": "2026-04-19-business-digest", "locale": "en", "post_type": "business",
         "content_expert": "EB", "content_learner": "LB", "title": "tb", "excerpt": "xb",
         "focus_items": [], "guide_items": {}},
        {"slug": "2026-04-19-business-digest-ko", "locale": "ko", "post_type": "business",
         "content_expert": "EB-ko", "content_learner": "LB-ko", "title": "tb-ko", "excerpt": "xb-ko",
         "focus_items": [], "guide_items": {}},
    ]
    supabase = _build_supabase_mock_for_quality_rerun(news_rows)

    with patch("services.pipeline.get_supabase", return_value=supabase), \
         patch("services.pipeline._load_checkpoint", return_value=None), \
         patch("services.pipeline._check_digest_quality", new_callable=AsyncMock) as qc_mock, \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock) as gen_mock, \
         patch("services.pipeline._log_stage", new_callable=AsyncMock):
        qc_mock.return_value = {
            "score": 82, "quality_score": 82,
            "quality_flags": [], "quality_issues": [],
            "quality_breakdown": {"total_score": 82},
        }

        result = await rerun_pipeline_stage(
            source_run_id="run-1",
            from_stage="quality",
            batch_id="2026-04-19",
            category=None,  # no filter -> both types
        )

        # Both digest_types rescored
        assert qc_mock.await_count == 2, f"expected 2 QC calls (research+business), got {qc_mock.await_count}"
        # Writer still never called
        assert gen_mock.await_count == 0
        assert result.status == "success"

        # 4 update() calls (2 digest_types x 2 locales)
        update_calls = [
            c for c in supabase.table.return_value.update.call_args_list
            if c.args and isinstance(c.args[0], dict) and "quality_score" in c.args[0]
        ]
        assert len(update_calls) == 4, f"expected 4 locale updates, got {len(update_calls)}"
