"""Tests for classification-stage ranking helpers."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import NewsCandidate


def _mock_openai_response(data: dict, tokens: int = 300):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(data)
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 1000
    mock_resp.usage.completion_tokens = tokens
    mock_resp.usage.total_tokens = 1000 + tokens
    return mock_resp


SAMPLE_CANDIDATES = [
    NewsCandidate(
        title="GPT-5 Released",
        url="https://a.com/1",
        snippet="Major model release",
        source="tavily",
        source_kind="official_site",
        source_confidence="high",
        source_tier="primary",
    ),
    NewsCandidate(
        title="AI Startup raises $500M",
        url="https://b.com/2",
        snippet="Funding round",
        source="tavily",
        source_kind="media",
        source_confidence="high",
        source_tier="secondary",
    ),
    NewsCandidate(
        title="New transformer paper",
        url="https://c.com/3",
        snippet="Architecture improvement",
        source="tavily",
        source_kind="paper",
        source_confidence="high",
        source_tier="primary",
    ),
]


CLASSIFICATION_LLM_RESPONSE = {
    "research": [
        {"url": "https://c.com/3", "subcategory": "papers", "reason": "Novel architecture", "score": 0.92},
        {"url": "https://a.com/1", "subcategory": "llm_models", "reason": "Major release", "score": 0.88},
    ],
    "business": [
        {"url": "https://b.com/2", "subcategory": "industry", "reason": "Major funding", "score": 0.90},
        {"url": "https://a.com/1", "subcategory": "big_tech", "reason": "GPT-5 market impact", "score": 0.85},
    ],
}


def test_legacy_rank_candidates_api_removed():
    from services.agents import ranking

    assert not hasattr(ranking, "rank_candidates")


@pytest.mark.asyncio
async def test_classify_candidates_returns_multiple_picks_and_prompt():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(CLASSIFICATION_LLM_RESPONSE)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_light = "gpt-4o"

        from services.agents.ranking import classify_candidates
        result, usage, user_prompt = await classify_candidates(SAMPLE_CANDIDATES)

    assert len(result.research_picks) == 2
    assert len(result.business_picks) == 2
    assert result.research_picks[0].subcategory == "papers"
    assert result.business_picks[0].subcategory == "industry"
    assert any(c.url == "https://a.com/1" for c in result.research_picks)
    assert any(c.url == "https://a.com/1" for c in result.business_picks)
    assert "[1] GPT-5 Released" in user_prompt
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_classify_candidates_prompt_includes_source_provenance():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(CLASSIFICATION_LLM_RESPONSE)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_light = "gpt-4o"

        from services.agents.ranking import classify_candidates
        _, _, user_prompt = await classify_candidates(SAMPLE_CANDIDATES)

    assert "Source tier: primary" in user_prompt
    assert "Source kind: paper" in user_prompt
    assert "Source confidence: high" in user_prompt


@pytest.mark.asyncio
async def test_classify_candidates_prompt_groups_recent_headlines_by_category():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(CLASSIFICATION_LLM_RESPONSE)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_light = "gpt-4o"

        from services.agents.ranking import classify_candidates
        _, _, user_prompt = await classify_candidates(
            SAMPLE_CANDIDATES,
            recent_headlines_by_category={
                "research": ["Google publishes RoPE attention benchmark"],
                "business": ["Google launches Gemini enterprise pricing"],
            },
        )

    assert "ALREADY COVERED HEADLINES BY CATEGORY" in user_prompt
    assert "Research headlines:" in user_prompt
    assert "- Google publishes RoPE attention benchmark" in user_prompt
    assert "Business headlines:" in user_prompt
    assert "- Google launches Gemini enterprise pricing" in user_prompt
    assert "For same-category candidates, apply strict same-event dedup." in user_prompt


@pytest.mark.asyncio
async def test_classify_candidates_debug_records_raw_and_invalid_url_picks():
    response = {
        "research": [
            {"url": "https://missing.example/paper", "subcategory": "papers", "reason": "Not in pool"},
            {"url": "https://c.com/3", "subcategory": "papers", "reason": "In pool"},
        ],
        "business": [],
    }
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(response)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_light = "gpt-4o"

        from services.agents.ranking import classify_candidates
        result, _, _ = await classify_candidates(SAMPLE_CANDIDATES)

    assert len(result.research_picks) == 1
    assert result.classification_debug["raw_picks"] == response
    assert result.classification_debug["invalid_url_picks"] == [
        {
            "category": "research",
            "url": "https://missing.example/paper",
            "reason": "URL not found in candidate pool",
        }
    ]


def test_emergency_classification_selects_research_and_business_picks():
    from services.agents.ranking import build_emergency_classification

    result, meta = build_emergency_classification(SAMPLE_CANDIDATES)

    assert result.research_picks
    assert result.business_picks
    assert result.research_picks[0].subcategory in {"llm_models", "papers", "open_source"}
    assert result.business_picks[0].subcategory in {"big_tech", "industry", "new_tools"}
    assert meta["mode"] == "classification_zero_emergency"
    assert meta["research_selected"] == len(result.research_picks)
    assert meta["business_selected"] == len(result.business_picks)


def test_emergency_classification_caps_papers_when_other_research_signals_exist():
    from services.agents.ranking import build_emergency_classification

    candidates = [
        NewsCandidate(
            title=f"Paper {i}: LLM benchmark architecture study",
            url=f"https://arxiv.org/abs/2604.{i:05d}",
            snippet="LLM benchmark architecture paper with training data and evaluation.",
            source="arxiv",
            source_kind="paper",
            source_confidence="high",
            source_tier="primary",
        )
        for i in range(4)
    ] + [
        NewsCandidate(
            title="Qwen3.6-27B beats larger predecessor on coding benchmarks",
            url="https://the-decoder.com/qwen36-27b",
            snippet="Alibaba released a dense open-weight model with benchmark gains.",
            source="exa",
            source_kind="media",
            source_confidence="high",
            source_tier="secondary",
        ),
        NewsCandidate(
            title="NousResearch/hermes-agent: The agent that grows with you",
            url="https://github.com/NousResearch/hermes-agent",
            snippet="AI agent framework | Stars: 116,660 | Language: Python",
            source="github_trending",
            source_kind="official_repo",
            source_confidence="medium",
            source_tier="primary",
        ),
    ]

    result, _ = build_emergency_classification(candidates)

    subcategories = [pick.subcategory for pick in result.research_picks]
    assert subcategories.count("papers") <= 2
    assert "llm_models" in subcategories
    assert "open_source" in subcategories


def test_emergency_business_subcategory_treats_raise_and_merging_as_industry():
    from services.agents.ranking import build_emergency_classification

    candidates = [
        NewsCandidate(
            title="Two founders raise a $5.1 million pre-seed for an AI social network",
            url="https://techcrunch.com/example-raise",
            snippet="Funding round for an AI product.",
            source="tavily",
            source_kind="media",
            source_confidence="high",
            source_tier="secondary",
        ),
        NewsCandidate(
            title="Why Cohere is merging with Aleph Alpha",
            url="https://techcrunch.com/example-merging",
            snippet="AI companies combine in a transatlantic deal.",
            source="tavily",
            source_kind="media",
            source_confidence="high",
            source_tier="secondary",
        ),
    ]

    result, _ = build_emergency_classification(candidates)

    assert {pick.subcategory for pick in result.business_picks} == {"industry"}


def test_category_rescue_picks_selects_missing_business_candidates():
    from services.agents.ranking import build_category_rescue_picks

    candidates = [
        NewsCandidate(
            title="New transformer paper",
            url="https://arxiv.org/abs/2605.12345",
            snippet="Architecture improvement with benchmark results.",
            source="arxiv",
            source_kind="paper",
            source_confidence="high",
            source_tier="primary",
        ),
        NewsCandidate(
            title="AI startup raises $500M to build enterprise agents",
            url="https://techcrunch.com/ai-startup-raises-500m",
            snippet="$500M funding round for enterprise agent platform.",
            source="tavily",
            source_kind="media",
            source_confidence="high",
            source_tier="secondary",
        ),
    ]

    picks, meta = build_category_rescue_picks(candidates, "business")

    assert len(picks) == 1
    assert picks[0].url == "https://techcrunch.com/ai-startup-raises-500m"
    assert picks[0].category == "business"
    assert picks[0].subcategory == "industry"
    assert meta["category"] == "business"
    assert meta["selected"] == 1


@pytest.mark.asyncio
async def test_classify_candidates_empty_list_returns_empty_result():
    from services.agents.ranking import classify_candidates

    result, usage, user_prompt = await classify_candidates([])

    assert result.research_picks == []
    assert result.business_picks == []
    assert usage == {}
    assert user_prompt == ""
