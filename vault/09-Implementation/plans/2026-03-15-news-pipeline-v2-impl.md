I now have a thorough understanding of the entire codebase. Let me compile the comprehensive TDD implementation plan.

---

# AI News Pipeline v2 -- TDD Implementation Plan

## Key Decisions (Resolved)

Before the task-by-task plan, here are the resolved architectural decisions based on codebase exploration:

**1. FactPack JSON Schema:**
The DB already has a `fact_pack JSONB` column on `news_posts` (added in migration `20260312_news_pipeline_observability.sql`). The FactPack will contain: `headline`, `key_facts` (list of claims with source_ids), `numbers` (key metrics/data points), `entities` (companies/people/products mentioned), `sources` (list of source objects), `community_summary` (aggregated reactions). Each fact carries an `id` for cross-referencing with source_cards.

**2. Persona Output JSON Schema:**
Each persona LLM call returns `{"en": "markdown string", "ko": "markdown string"}`. This is a flat JSON structure -- no nested objects for sections. The LLM writes the full markdown with section headers.

**3. EN+KO Storage:**
Separate rows per locale, using `translation_group_id` to pair them. This matches the existing pattern seen in `newsDetailPage.ts` (lines 136-141) and the unique index `uq_posts_daily_ai_type ON news_posts(pipeline_batch_id, post_type, locale)`.

**4. Both post types get 3 personas:**
The v2 design stores both research and business content in `content_beginner`, `content_learner`, `content_expert`. The `content_original` column is no longer used for new pipeline posts. The frontend `newsDetailPage.ts` currently only shows persona tabs for `business` posts (line 232: `isBusinessPost = post?.post_type === 'business'`). This frontend change is NOT part of this backend sprint but the backend should store both types the same way.

**5. Handbook term linking:**
The pipeline fetches all published handbook_terms slugs from Supabase, passes them as a list in the persona system prompts, and the LLM inserts `[term](/handbook/slug/)` links naturally in content.

**6. System prompts:**
Stored as constants in a new `backend/services/agents/prompts_news_pipeline.py` file. This follows the existing pattern: `prompts_advisor.py` for news advisor, `prompts_blog_advisor.py` for blog advisor.

---

## File Inventory

### New Files to Create
| File | Purpose |
|------|---------|
| `backend/models/news_pipeline.py` | Pydantic models for pipeline data |
| `backend/services/news_collection.py` | Tavily news collection + community reactions |
| `backend/services/agents/ranking.py` | LLM ranking agent |
| `backend/services/agents/fact_extractor.py` | LLM fact extraction agent |
| `backend/services/agents/persona_writer.py` | LLM persona writing agent |
| `backend/services/agents/prompts_news_pipeline.py` | All system prompts for pipeline |
| `backend/services/pipeline.py` | Pipeline orchestrator |
| `backend/routers/cron.py` | Cron endpoint |
| `backend/tests/test_news_pipeline_models.py` | Model tests |
| `backend/tests/test_news_collection.py` | Collection tests |
| `backend/tests/test_ranking.py` | Ranking tests |
| `backend/tests/test_fact_extractor.py` | Fact extractor tests |
| `backend/tests/test_persona_writer.py` | Persona writer tests |
| `backend/tests/test_pipeline.py` | Pipeline orchestrator tests |
| `backend/tests/test_cron.py` | Cron endpoint tests |

### Existing Files to Modify
| File | Change |
|------|--------|
| `backend/main.py` | Add `from routers import cron` and `app.include_router(cron.router, prefix="/api")` |

---

## Task NP2-MODEL-01: Pydantic Models

### File: `backend/models/news_pipeline.py`

#### Step 1: Write test -- `backend/tests/test_news_pipeline_models.py`

```python
"""Tests for AI News Pipeline v2 Pydantic models."""
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# FactPack tests
# ---------------------------------------------------------------------------

def test_fact_pack_valid():
    from models.news_pipeline import FactPack

    data = {
        "headline": "OpenAI releases GPT-5",
        "key_facts": [
            {
                "id": "f1",
                "claim": "GPT-5 achieves 95% on MMLU",
                "why_it_matters": "Significant improvement over GPT-4",
                "source_ids": ["s1"],
                "confidence": "high",
            }
        ],
        "numbers": [
            {"value": "95%", "context": "MMLU benchmark score", "source_id": "s1"}
        ],
        "entities": [
            {"name": "OpenAI", "role": "developer", "url": "https://openai.com"}
        ],
        "sources": [
            {
                "id": "s1",
                "title": "OpenAI Blog",
                "publisher": "openai.com",
                "url": "https://openai.com/blog/gpt-5",
                "published_at": "2026-03-15",
            }
        ],
        "community_summary": "Reddit users are excited but skeptical about benchmarks.",
    }
    fp = FactPack.model_validate(data)
    assert fp.headline == "OpenAI releases GPT-5"
    assert len(fp.key_facts) == 1
    assert fp.key_facts[0].id == "f1"
    assert len(fp.sources) == 1


def test_fact_pack_missing_headline_fails():
    from models.news_pipeline import FactPack

    with pytest.raises(ValidationError):
        FactPack.model_validate({
            "key_facts": [],
            "numbers": [],
            "entities": [],
            "sources": [],
            "community_summary": "",
        })


def test_fact_pack_empty_lists_ok():
    from models.news_pipeline import FactPack

    fp = FactPack.model_validate({
        "headline": "Minor update",
        "key_facts": [],
        "numbers": [],
        "entities": [],
        "sources": [],
        "community_summary": "",
    })
    assert fp.headline == "Minor update"
    assert fp.key_facts == []


# ---------------------------------------------------------------------------
# PersonaOutput tests
# ---------------------------------------------------------------------------

def test_persona_output_valid():
    from models.news_pipeline import PersonaOutput

    data = {"en": "## Summary\nEnglish content here", "ko": "## 핵심 요약\n한국어 콘텐츠"}
    po = PersonaOutput.model_validate(data)
    assert len(po.en) > 10
    assert len(po.ko) > 5


def test_persona_output_empty_string_allowed():
    """Empty strings are valid -- the pipeline handles retries separately."""
    from models.news_pipeline import PersonaOutput

    po = PersonaOutput.model_validate({"en": "", "ko": ""})
    assert po.en == ""


# ---------------------------------------------------------------------------
# RankedCandidate tests
# ---------------------------------------------------------------------------

def test_ranked_candidate_valid():
    from models.news_pipeline import RankedCandidate

    rc = RankedCandidate.model_validate({
        "title": "GPT-5 Released",
        "url": "https://example.com/gpt5",
        "snippet": "OpenAI announces GPT-5.",
        "source": "tavily",
        "assigned_type": "research",
        "relevance_score": 0.95,
        "ranking_reason": "Major model release",
    })
    assert rc.assigned_type == "research"
    assert rc.relevance_score == 0.95


# ---------------------------------------------------------------------------
# NewsCandidate tests
# ---------------------------------------------------------------------------

def test_news_candidate_minimal():
    from models.news_pipeline import NewsCandidate

    nc = NewsCandidate.model_validate({
        "title": "Some news",
        "url": "https://example.com",
        "snippet": "A snippet",
        "source": "tavily",
    })
    assert nc.title == "Some news"


# ---------------------------------------------------------------------------
# PipelineResult tests
# ---------------------------------------------------------------------------

def test_pipeline_result_structure():
    from models.news_pipeline import PipelineResult

    pr = PipelineResult(
        batch_id="2026-03-15",
        posts_created=4,
        errors=[],
        usage={"model_used": "gpt-4o", "tokens_used": 5000, "cost_usd": 0.05,
               "input_tokens": 2000, "output_tokens": 3000},
    )
    assert pr.batch_id == "2026-03-15"
    assert pr.posts_created == 4
    assert pr.errors == []


def test_pipeline_result_with_errors():
    from models.news_pipeline import PipelineResult

    pr = PipelineResult(
        batch_id="2026-03-15",
        posts_created=2,
        errors=["research fact extraction failed after 2 retries"],
        usage={},
    )
    assert len(pr.errors) == 1
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_news_pipeline_models.py -v --tb=short`
**Expected:** All FAILED (ImportError -- module does not exist yet).

#### Step 2: Implement -- `backend/models/news_pipeline.py`

```python
"""Pydantic models for AI News Pipeline v2."""
from pydantic import BaseModel, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Tavily collection
# ---------------------------------------------------------------------------

class NewsCandidate(BaseModel):
    """Raw news item from Tavily search."""
    title: str
    url: str
    snippet: str = ""
    source: str = "tavily"
    raw_content: str = ""


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

class RankedCandidate(BaseModel):
    """News candidate after LLM ranking."""
    title: str
    url: str
    snippet: str = ""
    source: str = "tavily"
    assigned_type: str  # "research" or "business"
    relevance_score: float = 0.0
    ranking_reason: str = ""


class RankingResult(BaseModel):
    """LLM ranking output."""
    research: Optional[RankedCandidate] = None
    business: Optional[RankedCandidate] = None


# ---------------------------------------------------------------------------
# Fact extraction
# ---------------------------------------------------------------------------

class FactClaim(BaseModel):
    id: str
    claim: str
    why_it_matters: str = ""
    source_ids: list[str] = []
    confidence: str = "medium"  # high, medium, low


class FactNumber(BaseModel):
    value: str
    context: str = ""
    source_id: str = ""


class FactEntity(BaseModel):
    name: str
    role: str = ""
    url: str = ""


class FactSource(BaseModel):
    id: str
    title: str = ""
    publisher: str = ""
    url: str = ""
    published_at: str = ""


class FactPack(BaseModel):
    """Structured facts extracted from a news article + community reactions."""
    headline: str
    key_facts: list[FactClaim] = []
    numbers: list[FactNumber] = []
    entities: list[FactEntity] = []
    sources: list[FactSource] = []
    community_summary: str = ""


# ---------------------------------------------------------------------------
# Persona generation
# ---------------------------------------------------------------------------

class PersonaOutput(BaseModel):
    """EN+KO content from a single persona LLM call."""
    en: str = ""
    ko: str = ""


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

class PipelineResult(BaseModel):
    """Final result of the daily pipeline run."""
    batch_id: str
    posts_created: int = 0
    errors: list[str] = []
    usage: dict = Field(default_factory=dict)
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_news_pipeline_models.py -v --tb=short`
**Expected:** All PASSED.

**Lint:** `cd backend && .venv/Scripts/python -m ruff check models/news_pipeline.py`

**Commit:** `git add backend/models/news_pipeline.py backend/tests/test_news_pipeline_models.py && git commit -m "feat: add Pydantic models for AI News Pipeline v2 [NP2-MODEL-01]"`

---

## Task NP2-COLLECT-01: Tavily News Collection

### File: `backend/services/news_collection.py`

#### Step 1: Write test -- `backend/tests/test_news_collection.py`

```python
"""Tests for Tavily news collection service."""
import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TAVILY_SEARCH_RESPONSE = {
    "results": [
        {
            "title": "GPT-5 Released by OpenAI",
            "url": "https://openai.com/blog/gpt-5",
            "content": "OpenAI has released GPT-5 with significant improvements.",
            "raw_content": "Full article text...",
        },
        {
            "title": "Google Gemini 2.0 Update",
            "url": "https://blog.google/gemini-2",
            "content": "Google announces Gemini 2.0 with new capabilities.",
            "raw_content": "Full article text about Gemini...",
        },
    ]
}


# ---------------------------------------------------------------------------
# collect_news tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_news_returns_candidates():
    """Tavily search results are converted to NewsCandidate list."""
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = TAVILY_SEARCH_RESPONSE

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates = await collect_news()

    assert len(candidates) == 2
    assert candidates[0].title == "GPT-5 Released by OpenAI"
    assert candidates[0].url == "https://openai.com/blog/gpt-5"
    mock_tavily.search.assert_called_once()


@pytest.mark.asyncio
async def test_collect_news_deduplicates_urls():
    """Duplicate URLs should be removed."""
    duped_response = {
        "results": [
            {"title": "Article A", "url": "https://example.com/same", "content": "A", "raw_content": ""},
            {"title": "Article B", "url": "https://example.com/same", "content": "B", "raw_content": ""},
            {"title": "Article C", "url": "https://example.com/other", "content": "C", "raw_content": ""},
        ]
    }
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = duped_response

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates = await collect_news()

    assert len(candidates) == 2


@pytest.mark.asyncio
async def test_collect_news_no_api_key_returns_empty():
    """Missing API key should return empty list, not crash."""
    with patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = ""

        from services.news_collection import collect_news
        candidates = await collect_news()

    assert candidates == []


@pytest.mark.asyncio
async def test_collect_news_api_error_returns_empty():
    """Tavily API error should return empty list, not crash."""
    mock_tavily = MagicMock()
    mock_tavily.search.side_effect = Exception("API rate limit")

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates = await collect_news()

    assert candidates == []
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_news_collection.py -v --tb=short`
**Expected:** All FAILED (ImportError).

#### Step 2: Implement -- `backend/services/news_collection.py`

```python
"""Tavily-based news collection and community reaction gathering."""
import asyncio
import logging
from typing import Optional

from tavily import TavilyClient

from core.config import settings
from models.news_pipeline import NewsCandidate

logger = logging.getLogger(__name__)

# Search queries for diverse AI news coverage
SEARCH_QUERIES = [
    "latest AI artificial intelligence news today",
    "AI startup funding investment announcement",
    "new AI model release benchmark",
]


async def collect_news(
    max_results_per_query: int = 10,
) -> list[NewsCandidate]:
    """Collect AI news candidates from Tavily. Returns deduplicated list."""
    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured, skipping collection")
        return []

    try:
        tavily = TavilyClient(api_key=settings.tavily_api_key)
    except Exception as e:
        logger.error("Failed to create Tavily client: %s", e)
        return []

    loop = asyncio.get_event_loop()
    all_results: list[dict] = []

    for query in SEARCH_QUERIES:
        try:
            response = await loop.run_in_executor(
                None,
                lambda q=query: tavily.search(
                    query=q,
                    search_depth="advanced",
                    max_results=max_results_per_query,
                    topic="news",
                    days=2,
                ),
            )
            all_results.extend(response.get("results", []))
        except Exception as e:
            logger.warning("Tavily search failed for query '%s': %s", query, e)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    candidates: list[NewsCandidate] = []
    for item in all_results:
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        candidates.append(
            NewsCandidate(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("content", ""),
                source="tavily",
                raw_content=item.get("raw_content", ""),
            )
        )

    logger.info("Collected %d unique candidates from %d total results",
                len(candidates), len(all_results))
    return candidates


async def collect_community_reactions(
    news_title: str,
    news_url: str,
) -> str:
    """Collect community reactions for a specific news item from Reddit/HN/X."""
    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured, skipping reactions")
        return ""

    try:
        tavily = TavilyClient(api_key=settings.tavily_api_key)
    except Exception as e:
        logger.error("Failed to create Tavily client: %s", e)
        return ""

    loop = asyncio.get_event_loop()
    queries = [
        f'"{news_title}" site:reddit.com OR site:news.ycombinator.com',
        f'"{news_title}" reactions opinions',
    ]

    reactions: list[str] = []
    for query in queries:
        try:
            response = await loop.run_in_executor(
                None,
                lambda q=query: tavily.search(
                    query=q,
                    search_depth="basic",
                    max_results=5,
                ),
            )
            for result in response.get("results", []):
                content = result.get("content", "")
                if content:
                    source_url = result.get("url", "")
                    reactions.append(f"[{source_url}]: {content}")
        except Exception as e:
            logger.warning("Community reaction search failed: %s", e)

    combined = "\n\n".join(reactions)
    logger.info("Collected %d community reaction snippets for '%s'",
                len(reactions), news_title[:60])
    return combined
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_news_collection.py -v --tb=short`
**Expected:** All PASSED.

**Lint:** `cd backend && .venv/Scripts/python -m ruff check services/news_collection.py`

**Commit:** `git add backend/services/news_collection.py backend/tests/test_news_collection.py && git commit -m "feat: add Tavily news collection service [NP2-COLLECT-01]"`

---

## Task NP2-RANK-01: LLM Ranking

### File: `backend/services/agents/ranking.py`

#### Step 1: Write test -- `backend/tests/test_ranking.py`

```python
"""Tests for LLM news ranking agent."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import NewsCandidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    NewsCandidate(title="GPT-5 Released", url="https://a.com/1", snippet="Major model release", source="tavily"),
    NewsCandidate(title="AI Startup raises $500M", url="https://b.com/2", snippet="Funding round", source="tavily"),
    NewsCandidate(title="New transformer paper", url="https://c.com/3", snippet="Architecture improvement", source="tavily"),
]

RANKING_LLM_RESPONSE = {
    "research": {
        "url": "https://c.com/3",
        "reason": "Novel architecture contribution",
        "score": 0.92,
    },
    "business": {
        "url": "https://b.com/2",
        "reason": "Major funding signals market direction",
        "score": 0.88,
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rank_candidates_selects_research_and_business():
    """Happy path: LLM selects one research and one business candidate."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(RANKING_LLM_RESPONSE)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.ranking import rank_candidates
        result, usage = await rank_candidates(SAMPLE_CANDIDATES)

    assert result.research is not None
    assert result.research.url == "https://c.com/3"
    assert result.research.assigned_type == "research"
    assert result.business is not None
    assert result.business.url == "https://b.com/2"
    assert result.business.assigned_type == "business"
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_rank_candidates_no_research():
    """LLM may return null for research if no suitable candidate."""
    response_data = {
        "research": None,
        "business": {
            "url": "https://b.com/2",
            "reason": "Important business news",
            "score": 0.85,
        },
    }
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(response_data)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.ranking import rank_candidates
        result, usage = await rank_candidates(SAMPLE_CANDIDATES)

    assert result.research is None
    assert result.business is not None


@pytest.mark.asyncio
async def test_rank_candidates_empty_list():
    """Empty candidate list should return empty result without calling LLM."""
    from services.agents.ranking import rank_candidates

    result, usage = await rank_candidates([])
    assert result.research is None
    assert result.business is None
    assert usage == {}


@pytest.mark.asyncio
async def test_rank_candidates_json_parse_error_retries():
    """JSON parse error should trigger retry."""
    good_response = _mock_openai_response(RANKING_LLM_RESPONSE)
    bad_response = MagicMock()
    bad_response.choices = [MagicMock()]
    bad_response.choices[0].message.content = "not valid json{{"
    bad_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [bad_response, good_response]

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.ranking import rank_candidates
        result, usage = await rank_candidates(SAMPLE_CANDIDATES)

    assert result.research is not None
    assert mock_client.chat.completions.create.call_count == 2
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_ranking.py -v --tb=short`
**Expected:** All FAILED.

#### Step 2: Implement -- `backend/services/agents/ranking.py`

```python
"""LLM-based news candidate ranking agent."""
import logging
from typing import Any

from models.news_pipeline import NewsCandidate, RankedCandidate, RankingResult
from services.agents.client import (
    get_openai_client,
    parse_ai_json,
    extract_usage_metrics,
)
from services.agents.prompts_news_pipeline import RANKING_SYSTEM_PROMPT
from core.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


async def rank_candidates(
    candidates: list[NewsCandidate],
) -> tuple[RankingResult, dict[str, Any]]:
    """Rank news candidates and select research + business picks.

    Returns (RankingResult, usage_metrics).
    """
    if not candidates:
        logger.info("No candidates to rank")
        return RankingResult(), {}

    # Build candidate summary for LLM
    candidate_lines = []
    for i, c in enumerate(candidates):
        candidate_lines.append(
            f"[{i+1}] {c.title}\n    URL: {c.url}\n    Snippet: {c.snippet[:300]}"
        )
    user_prompt = "\n\n".join(candidate_lines)

    client = get_openai_client()
    model = settings.openai_model_main
    usage: dict[str, Any] = {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": RANKING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2048,
            )
            usage = extract_usage_metrics(response, model)
            raw = response.choices[0].message.content
            data = parse_ai_json(raw, "Ranking")
            break
        except Exception as e:
            logger.warning("Ranking attempt %d failed: %s", attempt + 1, e)
            if attempt == MAX_RETRIES:
                logger.error("Ranking failed after %d retries", MAX_RETRIES + 1)
                return RankingResult(), usage
            continue

    # Build URL→Candidate lookup
    url_map = {c.url: c for c in candidates}

    result = RankingResult()

    for pick_type in ("research", "business"):
        pick = data.get(pick_type)
        if not pick or not pick.get("url"):
            continue
        url = pick["url"]
        candidate = url_map.get(url)
        if not candidate:
            logger.warning("Ranked URL not in candidates: %s", url)
            continue
        setattr(result, pick_type, RankedCandidate(
            title=candidate.title,
            url=candidate.url,
            snippet=candidate.snippet,
            source=candidate.source,
            assigned_type=pick_type,
            relevance_score=float(pick.get("score", 0)),
            ranking_reason=pick.get("reason", ""),
        ))

    logger.info("Ranking complete: research=%s, business=%s",
                "selected" if result.research else "none",
                "selected" if result.business else "none")
    return result, usage
```

#### Step 3: Create prompts file -- `backend/services/agents/prompts_news_pipeline.py`

```python
"""System prompts for AI News Pipeline v2."""

RANKING_SYSTEM_PROMPT = """You are an AI news editor for 0to1log, a Korean-English bilingual AI news platform.

Your task: Given a list of AI news candidates, select the BEST one for each category.

## Categories
- **research**: Technical/academic focus — new models, architectures, benchmarks, papers, open-source releases
- **business**: Market/strategy focus — funding rounds, acquisitions, partnerships, regulations, competitive moves

## Rules
1. Pick ONE article per category (or null if no good candidate exists)
2. The same article CANNOT be selected for both categories
3. Prefer breaking/exclusive news over incremental updates
4. Prefer news with concrete data (benchmarks, dollar amounts, dates)

## Output JSON format
```json
{
  "research": {"url": "...", "reason": "...", "score": 0.0-1.0} | null,
  "business": {"url": "...", "reason": "...", "score": 0.0-1.0} | null
}
```"""

FACT_EXTRACTION_SYSTEM_PROMPT = """You are a fact extraction engine for 0to1log, an AI news platform.

Given: news article text + context + community reactions.

Extract a structured JSON "FactPack" that will be used by writers to create articles.

## Output JSON format
```json
{
  "headline": "Clear, factual one-line headline (English)",
  "key_facts": [
    {
      "id": "f1",
      "claim": "Specific factual claim",
      "why_it_matters": "Why this matters to AI practitioners",
      "source_ids": ["s1"],
      "confidence": "high|medium|low"
    }
  ],
  "numbers": [
    {"value": "95%", "context": "MMLU benchmark", "source_id": "s1"}
  ],
  "entities": [
    {"name": "OpenAI", "role": "developer", "url": "https://openai.com"}
  ],
  "sources": [
    {
      "id": "s1",
      "title": "Source title",
      "publisher": "domain.com",
      "url": "https://...",
      "published_at": "2026-03-15"
    }
  ],
  "community_summary": "Summary of community reactions from Reddit/HN/X"
}
```

## Rules
1. Every claim must reference at least one source_id
2. Assign confidence: high=official source, medium=reputable reporting, low=rumor/unconfirmed
3. Extract ALL concrete numbers (dollars, percentages, dates, counts)
4. community_summary should be 2-3 sentences summarizing public reaction sentiment
5. headline must be factual, not clickbait
6. Source IDs must be unique strings like "s1", "s2", etc."""


def _build_persona_system_prompt(
    persona: str,
    sections_description: str,
    handbook_slugs: list[str],
) -> str:
    """Build the system prompt for a persona writer.

    Args:
        persona: "expert", "learner", or "beginner"
        sections_description: Markdown describing required sections
        handbook_slugs: List of handbook term slugs for linking
    """
    handbook_section = ""
    if handbook_slugs:
        terms_list = ", ".join(handbook_slugs[:200])  # Cap at 200 terms
        handbook_section = f"""
## Handbook Linking
When you mention any of these AI terms, link them using markdown: [term](/handbook/slug/)
Available terms: {terms_list}
Only link terms that appear naturally in context. Do not force links."""

    return f"""You are a {persona}-level AI news writer for 0to1log.

Write a news article in BOTH English AND Korean simultaneously.
Return a JSON object with "en" and "ko" keys, each containing full markdown content.

## Required Sections (for BOTH en and ko)
{sections_description}

## Writing Rules
1. Every claim must cite sources inline: [Source Name](URL)
2. Use concrete numbers and data — no vague statements
3. Korean content must be naturally written (not translated from English)
4. English and Korean cover the same facts but with natural expression for each language
5. Do NOT include the article title as an H1 — start directly with the first section
{handbook_section}

## Output JSON format
```json
{{
  "en": "## Section 1\\nEnglish content...\\n\\n## Section 2\\n...",
  "ko": "## 섹션 1\\n한국어 콘텐츠...\\n\\n## 섹션 2\\n..."
}}
```"""


EXPERT_SECTIONS = """- **## 핵심 요약 / ## Executive Summary** — 3-line executive summary for busy decision-makers
- **## 기술 심층 분석 / ## Technical Deep Dive** — Architecture, benchmarks, diffs vs. prior work. Concrete numbers required.
- **## 시장 & 경쟁 분석 / ## Market & Competitive Analysis** — Who wins/loses, investment signals, regulatory changes
- **## 전략적 시사점 / ## Strategic Implications** — Build/buy/wait decision, migration path, 6-month outlook"""

LEARNER_SECTIONS = """- **## 무슨 일이 있었나 / ## What Happened** — Who did what, why, with background context
- **## 기술 해부 / ## Technical Breakdown** — How it works. Code snippets and comparison tables welcome.
- **## 실무 적용 / ## Practical Applications** — "How does this affect my work?" for developers/PMs
- **## 참고 자료 / ## References** — Official docs, tutorials, GitHub repos"""

BEGINNER_SECTIONS = """- **## 한 줄 요약 / ## One-Line Summary** — This news in one sentence
- **## 무슨 일이 있었나 / ## What Happened** — Explanation accessible without prior knowledge. Use Handbook links liberally.
- **## 왜 중요한가 / ## Why It Matters** — Impact on daily life, society, jobs
- **## 알아두면 좋은 것 / ## Good to Know** — Basic concepts to understand this topic. Link to Handbook."""


def get_expert_prompt(handbook_slugs: list[str]) -> str:
    return _build_persona_system_prompt("expert", EXPERT_SECTIONS, handbook_slugs)


def get_learner_prompt(handbook_slugs: list[str]) -> str:
    return _build_persona_system_prompt("learner", LEARNER_SECTIONS, handbook_slugs)


def get_beginner_prompt(handbook_slugs: list[str]) -> str:
    return _build_persona_system_prompt("beginner", BEGINNER_SECTIONS, handbook_slugs)
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_ranking.py -v --tb=short`
**Expected:** All PASSED.

**Commit:** `git add backend/services/agents/ranking.py backend/services/agents/prompts_news_pipeline.py backend/tests/test_ranking.py && git commit -m "feat: add LLM news ranking agent [NP2-RANK-01]"`

---

## Task NP2-REACT-01: Community Reactions

#### Step 1: Add tests to `backend/tests/test_news_collection.py`

```python
# --- Appended to existing test_news_collection.py ---

TAVILY_REACTION_RESPONSE = {
    "results": [
        {
            "url": "https://reddit.com/r/MachineLearning/abc",
            "content": "This is a game changer. The benchmark improvements are real.",
        },
        {
            "url": "https://news.ycombinator.com/item?id=123",
            "content": "Skeptical about the claims. Need to see independent benchmarks.",
        },
    ]
}


@pytest.mark.asyncio
async def test_collect_community_reactions_returns_text():
    """Community reactions should return combined text."""
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = TAVILY_REACTION_RESPONSE

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("GPT-5 Released", "https://openai.com/gpt5")

    assert "game changer" in text
    assert "reddit.com" in text


@pytest.mark.asyncio
async def test_collect_community_reactions_no_api_key():
    """Missing API key returns empty string."""
    with patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = ""

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("Title", "https://example.com")

    assert text == ""


@pytest.mark.asyncio
async def test_collect_community_reactions_api_error():
    """API error returns empty string, not crash."""
    mock_tavily = MagicMock()
    mock_tavily.search.side_effect = Exception("Timeout")

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("Title", "https://example.com")

    assert text == ""
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_news_collection.py -v --tb=short`
**Expected:** All PASSED (implementation already exists from COLLECT-01).

**Commit:** `git add backend/tests/test_news_collection.py && git commit -m "feat: add community reactions tests [NP2-REACT-01]"`

---

## Task NP2-FACTS-01: Fact Extraction

### File: `backend/services/agents/fact_extractor.py`

#### Step 1: Write test -- `backend/tests/test_fact_extractor.py`

```python
"""Tests for LLM fact extraction agent."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_openai_response(data: dict, tokens: int = 500):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(data)
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 2000
    mock_resp.usage.completion_tokens = tokens
    mock_resp.usage.total_tokens = 2000 + tokens
    return mock_resp


SAMPLE_FACT_PACK = {
    "headline": "OpenAI releases GPT-5 with 95% MMLU score",
    "key_facts": [
        {
            "id": "f1",
            "claim": "GPT-5 scores 95% on MMLU benchmark",
            "why_it_matters": "20% improvement over GPT-4",
            "source_ids": ["s1"],
            "confidence": "high",
        },
        {
            "id": "f2",
            "claim": "Available via API starting today",
            "why_it_matters": "Immediate developer access",
            "source_ids": ["s1"],
            "confidence": "high",
        },
    ],
    "numbers": [
        {"value": "95%", "context": "MMLU score", "source_id": "s1"},
        {"value": "20%", "context": "improvement over GPT-4", "source_id": "s1"},
    ],
    "entities": [
        {"name": "OpenAI", "role": "developer", "url": "https://openai.com"},
    ],
    "sources": [
        {
            "id": "s1",
            "title": "GPT-5 Announcement",
            "publisher": "openai.com",
            "url": "https://openai.com/blog/gpt-5",
            "published_at": "2026-03-15",
        },
    ],
    "community_summary": "Developers excited but waiting for independent benchmarks.",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_facts_returns_valid_fact_pack():
    """Happy path: extract facts from news text."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(SAMPLE_FACT_PACK)

    with patch("services.agents.fact_extractor.get_openai_client", return_value=mock_client), \
         patch("services.agents.fact_extractor.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.fact_extractor import extract_facts
        fact_pack, usage = await extract_facts(
            news_text="OpenAI released GPT-5 today...",
            context_text="Additional Tavily context...",
            community_text="Reddit says it's great.",
        )

    assert fact_pack.headline == "OpenAI releases GPT-5 with 95% MMLU score"
    assert len(fact_pack.key_facts) == 2
    assert fact_pack.key_facts[0].id == "f1"
    assert len(fact_pack.sources) == 1
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_extract_facts_with_empty_community():
    """Community text can be empty."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(SAMPLE_FACT_PACK)

    with patch("services.agents.fact_extractor.get_openai_client", return_value=mock_client), \
         patch("services.agents.fact_extractor.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.fact_extractor import extract_facts
        fact_pack, usage = await extract_facts(
            news_text="Some news text",
            context_text="",
            community_text="",
        )

    assert fact_pack is not None
    # Verify prompt was built (community section should still be present but empty)
    call_args = mock_client.chat.completions.create.call_args
    user_msg = call_args[1]["messages"][1]["content"]
    assert "Community Reactions" in user_msg


@pytest.mark.asyncio
async def test_extract_facts_retries_on_json_error():
    """JSON parse failure triggers retry."""
    bad_resp = MagicMock()
    bad_resp.choices = [MagicMock()]
    bad_resp.choices[0].message.content = "invalid json..."
    bad_resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    good_resp = _mock_openai_response(SAMPLE_FACT_PACK)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [bad_resp, good_resp]

    with patch("services.agents.fact_extractor.get_openai_client", return_value=mock_client), \
         patch("services.agents.fact_extractor.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.fact_extractor import extract_facts
        fact_pack, usage = await extract_facts(
            news_text="News text",
            context_text="Context",
            community_text="Reactions",
        )

    assert fact_pack is not None
    assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_extract_facts_all_retries_fail_raises():
    """If all retries fail, raise the error."""
    bad_resp = MagicMock()
    bad_resp.choices = [MagicMock()]
    bad_resp.choices[0].message.content = "not json"
    bad_resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = bad_resp

    with patch("services.agents.fact_extractor.get_openai_client", return_value=mock_client), \
         patch("services.agents.fact_extractor.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.fact_extractor import extract_facts
        with pytest.raises(Exception):
            await extract_facts(
                news_text="News text",
                context_text="Context",
                community_text="Reactions",
            )
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_fact_extractor.py -v --tb=short`
**Expected:** All FAILED.

#### Step 2: Implement -- `backend/services/agents/fact_extractor.py`

```python
"""LLM-based fact extraction agent."""
import logging
from typing import Any

from models.news_pipeline import FactPack
from services.agents.client import (
    get_openai_client,
    parse_ai_json,
    extract_usage_metrics,
)
from services.agents.prompts_news_pipeline import FACT_EXTRACTION_SYSTEM_PROMPT
from core.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


async def extract_facts(
    news_text: str,
    context_text: str = "",
    community_text: str = "",
) -> tuple[FactPack, dict[str, Any]]:
    """Extract structured facts from news article and context.

    Returns (FactPack, usage_metrics).
    Raises on unrecoverable error after retries.
    """
    user_prompt = f"""## News Article
{news_text}

## Additional Context
{context_text or "(none)"}

## Community Reactions
{community_text or "(none)"}"""

    client = get_openai_client()
    model = settings.openai_model_main
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4096,
            )
            usage = extract_usage_metrics(response, model)
            raw = response.choices[0].message.content
            data = parse_ai_json(raw, "FactExtractor")
            fact_pack = FactPack.model_validate(data)
            logger.info("Fact extraction complete: %d facts, %d sources",
                        len(fact_pack.key_facts), len(fact_pack.sources))
            return fact_pack, usage
        except Exception as e:
            last_error = e
            logger.warning("Fact extraction attempt %d failed: %s", attempt + 1, e)
            if attempt < MAX_RETRIES:
                continue

    raise last_error  # type: ignore[misc]
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_fact_extractor.py -v --tb=short`
**Expected:** All PASSED.

**Commit:** `git add backend/services/agents/fact_extractor.py backend/tests/test_fact_extractor.py && git commit -m "feat: add LLM fact extraction agent [NP2-FACTS-01]"`

---

## Task NP2-PERSONA-01: Persona Writer

### File: `backend/services/agents/persona_writer.py`

#### Step 1: Write test -- `backend/tests/test_persona_writer.py`

```python
"""Tests for LLM persona writer agent."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import FactPack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_openai_response(data: dict, tokens: int = 2000):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(data)
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 3000
    mock_resp.usage.completion_tokens = tokens
    mock_resp.usage.total_tokens = 3000 + tokens
    return mock_resp


SAMPLE_FACT_PACK = FactPack.model_validate({
    "headline": "OpenAI releases GPT-5",
    "key_facts": [
        {"id": "f1", "claim": "GPT-5 scores 95% on MMLU", "why_it_matters": "Big improvement", "source_ids": ["s1"], "confidence": "high"},
    ],
    "numbers": [{"value": "95%", "context": "MMLU", "source_id": "s1"}],
    "entities": [{"name": "OpenAI", "role": "developer", "url": "https://openai.com"}],
    "sources": [{"id": "s1", "title": "OpenAI Blog", "publisher": "openai.com", "url": "https://openai.com/blog/gpt5", "published_at": "2026-03-15"}],
    "community_summary": "Mixed reactions.",
})

EXPERT_OUTPUT = {
    "en": "## Executive Summary\nGPT-5 achieves 95% on MMLU. " + "x" * 3000,
    "ko": "## 핵심 요약\nGPT-5가 MMLU 95%를 달성. " + "가" * 3000,
}

LEARNER_OUTPUT = {
    "en": "## What Happened\nOpenAI released GPT-5. " + "y" * 3000,
    "ko": "## 무슨 일이 있었나\nOpenAI가 GPT-5를 출시. " + "나" * 3000,
}

BEGINNER_OUTPUT = {
    "en": "## One-Line Summary\nOpenAI made a smarter AI. " + "z" * 3000,
    "ko": "## 한 줄 요약\nOpenAI가 더 똑똑한 AI를 만들었다. " + "다" * 3000,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_persona_expert():
    """Expert persona returns EN+KO content."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(EXPERT_OUTPUT)

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_persona
        output, usage = await write_persona(
            persona="expert",
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=["transformer", "llm"],
        )

    assert "Executive Summary" in output.en
    assert "핵심 요약" in output.ko
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_write_all_personas_parallel():
    """write_all_personas runs 3 personas concurrently."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [
        _mock_openai_response(EXPERT_OUTPUT),
        _mock_openai_response(LEARNER_OUTPUT),
        _mock_openai_response(BEGINNER_OUTPUT),
    ]

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_all_personas
        results, usage = await write_all_personas(
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=[],
        )

    assert "expert" in results
    assert "learner" in results
    assert "beginner" in results
    assert "Executive Summary" in results["expert"].en
    assert "무슨 일이 있었나" in results["learner"].ko
    assert "한 줄 요약" in results["beginner"].ko
    # 3 concurrent calls
    assert mock_client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_write_persona_short_content_business_retries():
    """Business post with EN < 3000 chars triggers one retry."""
    short_output = {
        "en": "## Summary\nShort.",
        "ko": "## 요약\n짧음.",
    }
    long_output = EXPERT_OUTPUT

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [
        _mock_openai_response(short_output, 200),
        _mock_openai_response(long_output, 2000),
    ]

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_persona
        output, usage = await write_persona(
            persona="expert",
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=[],
            post_type="business",
        )

    assert len(output.en) >= 3000
    assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_write_persona_short_content_research_no_retry():
    """Research post with short EN does NOT retry (length doesn't matter)."""
    short_output = {
        "en": "## Summary\nShort research content.",
        "ko": "## 요약\n짧은 리서치 콘텐츠.",
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(short_output, 200)

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_persona
        output, usage = await write_persona(
            persona="expert",
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=[],
            post_type="research",
        )

    assert output.en == short_output["en"]
    assert mock_client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_write_persona_json_error_retries():
    """JSON parse failure triggers infra retry."""
    bad_resp = MagicMock()
    bad_resp.choices = [MagicMock()]
    bad_resp.choices[0].message.content = "not json"
    bad_resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    good_resp = _mock_openai_response(EXPERT_OUTPUT)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [bad_resp, good_resp]

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_persona
        output, usage = await write_persona(
            persona="expert",
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=[],
        )

    assert output is not None
    assert mock_client.chat.completions.create.call_count == 2
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_persona_writer.py -v --tb=short`
**Expected:** All FAILED.

#### Step 2: Implement -- `backend/services/agents/persona_writer.py`

```python
"""LLM-based persona content writer agent."""
import asyncio
import logging
from typing import Any

from models.news_pipeline import FactPack, PersonaOutput
from services.agents.client import (
    get_openai_client,
    parse_ai_json,
    extract_usage_metrics,
    merge_usage_metrics,
)
from services.agents.prompts_news_pipeline import (
    get_expert_prompt,
    get_learner_prompt,
    get_beginner_prompt,
)
from core.config import settings

logger = logging.getLogger(__name__)

MAX_INFRA_RETRIES = 2
BUSINESS_MIN_EN_CHARS = 3000

PERSONA_PROMPT_MAP = {
    "expert": get_expert_prompt,
    "learner": get_learner_prompt,
    "beginner": get_beginner_prompt,
}


def _build_fact_pack_prompt(fact_pack: FactPack) -> str:
    """Convert FactPack to a user prompt string."""
    parts = [f"## Headline\n{fact_pack.headline}"]

    if fact_pack.key_facts:
        facts_text = "\n".join(
            f"- [{f.id}] {f.claim} (confidence: {f.confidence}, sources: {', '.join(f.source_ids)})"
            for f in fact_pack.key_facts
        )
        parts.append(f"## Key Facts\n{facts_text}")

    if fact_pack.numbers:
        nums_text = "\n".join(
            f"- {n.value}: {n.context} (source: {n.source_id})"
            for n in fact_pack.numbers
        )
        parts.append(f"## Key Numbers\n{nums_text}")

    if fact_pack.entities:
        ents_text = "\n".join(
            f"- {e.name} ({e.role})" for e in fact_pack.entities
        )
        parts.append(f"## Entities\n{ents_text}")

    if fact_pack.sources:
        srcs_text = "\n".join(
            f"- [{s.id}] {s.title} — {s.publisher} ({s.url})"
            for s in fact_pack.sources
        )
        parts.append(f"## Sources\n{srcs_text}")

    if fact_pack.community_summary:
        parts.append(f"## Community Reactions\n{fact_pack.community_summary}")

    return "\n\n".join(parts)


async def write_persona(
    persona: str,
    fact_pack: FactPack,
    handbook_slugs: list[str],
    post_type: str = "business",
) -> tuple[PersonaOutput, dict[str, Any]]:
    """Write a single persona's EN+KO content from a FactPack.

    Returns (PersonaOutput, usage_metrics).
    """
    prompt_fn = PERSONA_PROMPT_MAP[persona]
    system_prompt = prompt_fn(handbook_slugs)
    user_prompt = _build_fact_pack_prompt(fact_pack)

    client = get_openai_client()
    model = settings.openai_model_main
    cumulative_usage: dict[str, Any] = {}
    length_retried = False

    for attempt in range(MAX_INFRA_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=16384,
            )
            usage = extract_usage_metrics(response, model)
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

            raw = response.choices[0].message.content
            data = parse_ai_json(raw, f"Persona-{persona}")
            output = PersonaOutput.model_validate(data)

            # Business length check: EN >= 3000 chars
            if (
                post_type == "business"
                and len(output.en) < BUSINESS_MIN_EN_CHARS
                and not length_retried
            ):
                length_retried = True
                logger.warning(
                    "Persona %s EN content too short (%d chars), retrying",
                    persona, len(output.en),
                )
                continue

            logger.info(
                "Persona %s complete: EN=%d chars, KO=%d chars",
                persona, len(output.en), len(output.ko),
            )
            return output, cumulative_usage

        except Exception as e:
            logger.warning("Persona %s attempt %d failed: %s", persona, attempt + 1, e)
            if attempt == MAX_INFRA_RETRIES:
                raise
            continue

    # Should not reach here, but just in case — return last output
    return output, cumulative_usage  # type: ignore[possibly-undefined]


async def write_all_personas(
    fact_pack: FactPack,
    handbook_slugs: list[str],
    post_type: str = "business",
) -> tuple[dict[str, PersonaOutput], dict[str, Any]]:
    """Write all 3 personas concurrently.

    Returns ({"expert": PersonaOutput, "learner": ..., "beginner": ...}, merged_usage).
    """
    tasks = {
        persona: write_persona(persona, fact_pack, handbook_slugs, post_type)
        for persona in ("expert", "learner", "beginner")
    }

    results_raw = await asyncio.gather(
        *tasks.values(),
        return_exceptions=True,
    )

    results: dict[str, PersonaOutput] = {}
    merged_usage: dict[str, Any] = {}
    errors: list[str] = []

    for persona, result in zip(tasks.keys(), results_raw):
        if isinstance(result, Exception):
            errors.append(f"{persona}: {result}")
            logger.error("Persona %s failed: %s", persona, result)
        else:
            output, usage = result
            results[persona] = output
            merged_usage = merge_usage_metrics(merged_usage, usage)

    if errors:
        logger.warning("Persona errors: %s", errors)

    return results, merged_usage
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_persona_writer.py -v --tb=short`
**Expected:** All PASSED.

**Commit:** `git add backend/services/agents/persona_writer.py backend/tests/test_persona_writer.py && git commit -m "feat: add LLM persona writer agent [NP2-PERSONA-01]"`

---

## Task NP2-PIPE-01: Pipeline Orchestrator

### File: `backend/services/pipeline.py`

#### Step 1: Write test -- `backend/tests/test_pipeline.py`

```python
"""Tests for the pipeline orchestrator."""
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import date

import pytest

from models.news_pipeline import (
    FactPack,
    NewsCandidate,
    PersonaOutput,
    RankedCandidate,
    RankingResult,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_CANDIDATES = [
    NewsCandidate(title="GPT-5", url="https://a.com/1", snippet="Model release", source="tavily"),
    NewsCandidate(title="AI Fund", url="https://b.com/2", snippet="$500M raised", source="tavily"),
]

SAMPLE_RANKING = RankingResult(
    research=RankedCandidate(
        title="GPT-5", url="https://a.com/1", snippet="Model release",
        source="tavily", assigned_type="research", relevance_score=0.9, ranking_reason="Major release",
    ),
    business=RankedCandidate(
        title="AI Fund", url="https://b.com/2", snippet="$500M raised",
        source="tavily", assigned_type="business", relevance_score=0.85, ranking_reason="Big funding",
    ),
)

SAMPLE_FACT_PACK = FactPack.model_validate({
    "headline": "GPT-5 Released",
    "key_facts": [{"id": "f1", "claim": "Test", "why_it_matters": "Test", "source_ids": ["s1"], "confidence": "high"}],
    "numbers": [], "entities": [],
    "sources": [{"id": "s1", "title": "Test", "publisher": "test.com", "url": "https://test.com", "published_at": "2026-03-15"}],
    "community_summary": "Positive reactions.",
})

SAMPLE_PERSONAS = {
    "expert": PersonaOutput(en="Expert EN content " + "x" * 3000, ko="Expert KO content " + "가" * 3000),
    "learner": PersonaOutput(en="Learner EN content " + "y" * 3000, ko="Learner KO content " + "나" * 3000),
    "beginner": PersonaOutput(en="Beginner EN content " + "z" * 3000, ko="Beginner KO content " + "다" * 3000),
}

EMPTY_USAGE = {"model_used": "gpt-4o", "input_tokens": 0, "output_tokens": 0, "tokens_used": 0, "cost_usd": 0.0}


def _mock_supabase():
    """Create a mock Supabase client with chain methods."""
    mock = MagicMock()
    # For handbook terms query
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
        {"slug": "transformer"}, {"slug": "llm"}, {"slug": "gpt"},
    ])
    # For pipeline_runs insert
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-id"}])
    # For pipeline_runs update
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # For news_posts upsert
    mock.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "post-id"}])
    # For pipeline_logs insert
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_daily_pipeline_happy_path():
    """Full pipeline creates 4 post rows (2 types x 2 locales)."""
    mock_sb = _mock_supabase()

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=SAMPLE_CANDIDATES), \
         patch("services.pipeline.rank_candidates", new_callable=AsyncMock, return_value=(SAMPLE_RANKING, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="Reactions text"), \
         patch("services.pipeline.extract_facts", new_callable=AsyncMock, return_value=(SAMPLE_FACT_PACK, EMPTY_USAGE)), \
         patch("services.pipeline.write_all_personas", new_callable=AsyncMock, return_value=(SAMPLE_PERSONAS, EMPTY_USAGE)):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 4  # research EN/KO + business EN/KO
    assert result.errors == []
    assert result.batch_id  # non-empty


@pytest.mark.asyncio
async def test_pipeline_no_research_creates_2_posts():
    """When ranking returns no research, only business posts are created."""
    ranking_no_research = RankingResult(
        research=None,
        business=SAMPLE_RANKING.business,
    )
    mock_sb = _mock_supabase()

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=SAMPLE_CANDIDATES), \
         patch("services.pipeline.rank_candidates", new_callable=AsyncMock, return_value=(ranking_no_research, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="Reactions"), \
         patch("services.pipeline.extract_facts", new_callable=AsyncMock, return_value=(SAMPLE_FACT_PACK, EMPTY_USAGE)), \
         patch("services.pipeline.write_all_personas", new_callable=AsyncMock, return_value=(SAMPLE_PERSONAS, EMPTY_USAGE)):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 2  # business EN + KO only


@pytest.mark.asyncio
async def test_pipeline_no_candidates_returns_zero_posts():
    """Empty Tavily results = 0 posts, no error."""
    mock_sb = _mock_supabase()

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=[]):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert result.errors == []


@pytest.mark.asyncio
async def test_pipeline_fact_extraction_failure_continues():
    """Fact extraction failure for one post type doesn't stop the other."""
    mock_sb = _mock_supabase()

    call_count = {"extract": 0}

    async def _mock_extract(*args, **kwargs):
        call_count["extract"] += 1
        if call_count["extract"] == 1:
            raise Exception("API timeout")
        return SAMPLE_FACT_PACK, EMPTY_USAGE

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=SAMPLE_CANDIDATES), \
         patch("services.pipeline.rank_candidates", new_callable=AsyncMock, return_value=(SAMPLE_RANKING, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="Reactions"), \
         patch("services.pipeline.extract_facts", side_effect=_mock_extract), \
         patch("services.pipeline.write_all_personas", new_callable=AsyncMock, return_value=(SAMPLE_PERSONAS, EMPTY_USAGE)):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    # One post type failed, the other succeeded
    assert result.posts_created == 2  # only one post type (EN + KO)
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_pipeline_supabase_not_configured():
    """Pipeline without Supabase should fail gracefully."""
    with patch("services.pipeline.get_supabase", return_value=None):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert any("not configured" in e.lower() for e in result.errors)
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_pipeline.py -v --tb=short`
**Expected:** All FAILED.

#### Step 2: Implement -- `backend/services/pipeline.py`

```python
"""AI News Pipeline v2 orchestrator."""
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

from core.config import settings
from core.database import get_supabase
from models.news_pipeline import (
    FactPack,
    PersonaOutput,
    PipelineResult,
    RankedCandidate,
)
from services.agents.client import merge_usage_metrics
from services.agents.fact_extractor import extract_facts
from services.agents.persona_writer import write_all_personas
from services.agents.ranking import rank_candidates
from services.news_collection import collect_community_reactions, collect_news

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:80]


def _fetch_handbook_slugs(supabase) -> list[str]:
    """Fetch all published handbook term slugs."""
    try:
        result = (
            supabase.table("handbook_terms")
            .select("slug")
            .eq("status", "published")
            .execute()
        )
        return [row["slug"] for row in (result.data or [])]
    except Exception as e:
        logger.warning("Failed to fetch handbook slugs: %s", e)
        return []


async def _generate_post(
    candidate: RankedCandidate,
    post_type: str,
    batch_id: str,
    handbook_slugs: list[str],
    supabase,
) -> tuple[int, list[str], dict[str, Any]]:
    """Generate a single post (fact extraction + 3 personas + save EN/KO).

    Returns (posts_created, errors, usage).
    """
    errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}
    posts_created = 0

    # Step 1: Collect community reactions
    try:
        reactions = await collect_community_reactions(candidate.title, candidate.url)
    except Exception as e:
        logger.warning("Community reactions failed for %s: %s", candidate.title, e)
        reactions = ""

    # Step 2: Extract facts
    try:
        news_text = f"Title: {candidate.title}\nURL: {candidate.url}\n\n{candidate.snippet}"
        fact_pack, fact_usage = await extract_facts(
            news_text=news_text,
            context_text=candidate.snippet,
            community_text=reactions,
        )
        cumulative_usage = merge_usage_metrics(cumulative_usage, fact_usage)
    except Exception as e:
        error_msg = f"{post_type} fact extraction failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        return 0, errors, cumulative_usage

    # Step 3: Write all 3 personas
    try:
        personas, persona_usage = await write_all_personas(
            fact_pack=fact_pack,
            handbook_slugs=handbook_slugs,
            post_type=post_type,
        )
        cumulative_usage = merge_usage_metrics(cumulative_usage, persona_usage)
    except Exception as e:
        error_msg = f"{post_type} persona writing failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        return 0, errors, cumulative_usage

    # Step 4: Save EN + KO rows
    translation_group_id = str(uuid.uuid4())
    base_slug = _slugify(fact_pack.headline or candidate.title)

    # Build source_cards from fact_pack.sources for the DB
    source_cards = [s.model_dump() for s in fact_pack.sources]
    source_urls = [s.url for s in fact_pack.sources if s.url]
    fact_pack_json = fact_pack.model_dump()

    for locale in ("en", "ko"):
        slug_suffix = "" if locale == "en" else "-ko"
        slug = f"{base_slug}{slug_suffix}"

        row = {
            "title": fact_pack.headline or candidate.title,
            "slug": f"{batch_id}-{slug}",
            "locale": locale,
            "category": "ai-news",
            "post_type": post_type,
            "status": "draft",
            "content_expert": personas.get("expert", PersonaOutput()).en if locale == "en"
                else personas.get("expert", PersonaOutput()).ko,
            "content_learner": personas.get("learner", PersonaOutput()).en if locale == "en"
                else personas.get("learner", PersonaOutput()).ko,
            "content_beginner": personas.get("beginner", PersonaOutput()).en if locale == "en"
                else personas.get("beginner", PersonaOutput()).ko,
            "fact_pack": fact_pack_json,
            "source_cards": source_cards,
            "source_urls": source_urls,
            "pipeline_batch_id": batch_id,
            "pipeline_model": settings.openai_model_main,
            "translation_group_id": translation_group_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            supabase.table("news_posts").upsert(row).execute()
            posts_created += 1
            logger.info("Saved %s %s draft: %s", post_type, locale, row["slug"])
        except Exception as e:
            error_msg = f"Failed to save {post_type} {locale}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    return posts_created, errors, cumulative_usage


async def run_daily_pipeline(
    batch_id: str | None = None,
) -> PipelineResult:
    """Run the full daily AI news pipeline.

    Flow: collect → rank → (react + extract + personas) × 2 → save drafts.
    """
    if batch_id is None:
        batch_id = date.today().isoformat()

    supabase = get_supabase()
    if not supabase:
        return PipelineResult(
            batch_id=batch_id,
            errors=["Supabase not configured"],
        )

    total_posts = 0
    all_errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}

    # Record pipeline run
    run_id = str(uuid.uuid4())
    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "run_key": f"news-v2-{batch_id}",
            "status": "running",
        }).execute()
    except Exception as e:
        logger.warning("Failed to record pipeline run: %s", e)

    try:
        # Step 1: Collect news
        candidates = await collect_news()
        if not candidates:
            logger.info("No news candidates found, pipeline complete")
            return PipelineResult(batch_id=batch_id)

        # Step 2: Rank candidates
        ranking, rank_usage = await rank_candidates(candidates)
        cumulative_usage = merge_usage_metrics(cumulative_usage, rank_usage)

        # Step 3: Fetch handbook slugs for linking
        handbook_slugs = _fetch_handbook_slugs(supabase)

        # Step 4: Generate posts for each selected type
        picks = []
        if ranking.research:
            picks.append(("research", ranking.research))
        if ranking.business:
            picks.append(("business", ranking.business))

        for post_type, candidate in picks:
            posts, errors, usage = await _generate_post(
                candidate=candidate,
                post_type=post_type,
                batch_id=batch_id,
                handbook_slugs=handbook_slugs,
                supabase=supabase,
            )
            total_posts += posts
            all_errors.extend(errors)
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

        # Update pipeline run status
        status = "success" if not all_errors else "failed"
        try:
            supabase.table("pipeline_runs").update({
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": all_errors[0] if all_errors else None,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Failed to update pipeline run: %s", e)

        # Log pipeline execution
        try:
            supabase.table("pipeline_logs").insert({
                "run_id": run_id,
                "pipeline_type": "news-v2",
                "status": status,
                "input_summary": f"{len(candidates)} candidates, {len(picks)} selected",
                "output_summary": f"{total_posts} posts created",
                "model_used": cumulative_usage.get("model_used"),
                "tokens_used": cumulative_usage.get("tokens_used"),
                "cost_usd": cumulative_usage.get("cost_usd"),
                "error_message": "; ".join(all_errors) if all_errors else None,
            }).execute()
        except Exception as e:
            logger.warning("Failed to log pipeline execution: %s", e)

    except Exception as e:
        logger.error("Pipeline unexpected error: %s", e)
        all_errors.append(str(e))
        try:
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": str(e),
            }).eq("id", run_id).execute()
        except Exception:
            pass

    result = PipelineResult(
        batch_id=batch_id,
        posts_created=total_posts,
        errors=all_errors,
        usage=cumulative_usage,
    )
    logger.info("Pipeline complete: %d posts, %d errors", total_posts, len(all_errors))
    return result
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_pipeline.py -v --tb=short`
**Expected:** All PASSED.

**Commit:** `git add backend/services/pipeline.py backend/tests/test_pipeline.py && git commit -m "feat: add pipeline orchestrator [NP2-PIPE-01]"`

---

## Task NP2-CRON-01: Cron Endpoint

### File: `backend/routers/cron.py`

#### Step 1: Write test -- `backend/tests/test_cron.py`

```python
"""Tests for cron endpoint."""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_cron_news_pipeline_returns_202():
    """POST /api/cron/news-pipeline with valid secret returns 202."""
    with patch("routers.cron.run_daily_pipeline", new_callable=AsyncMock) as mock_pipeline:
        from main import app
        client = TestClient(app)

        with patch("core.config.settings") as mock_settings:
            mock_settings.cron_secret = "test-secret-123"

            response = client.post(
                "/api/cron/news-pipeline",
                headers={"x-cron-secret": "test-secret-123"},
            )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "batch_id" in data


def test_cron_news_pipeline_missing_secret_returns_401():
    """POST without x-cron-secret header returns 401."""
    from main import app
    client = TestClient(app)

    with patch("core.config.settings") as mock_settings:
        mock_settings.cron_secret = "test-secret-123"

        response = client.post("/api/cron/news-pipeline")

    assert response.status_code == 401


def test_cron_news_pipeline_wrong_secret_returns_401():
    """POST with wrong secret returns 401."""
    from main import app
    client = TestClient(app)

    with patch("core.config.settings") as mock_settings:
        mock_settings.cron_secret = "test-secret-123"

        response = client.post(
            "/api/cron/news-pipeline",
            headers={"x-cron-secret": "wrong-secret"},
        )

    assert response.status_code == 401


def test_cron_health_returns_200():
    """GET /api/cron/health returns 200 with pipeline info."""
    from main import app
    client = TestClient(app)

    response = client.get("/api/cron/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "pipeline" in data
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_cron.py -v --tb=short`
**Expected:** All FAILED.

#### Step 2: Implement -- `backend/routers/cron.py`

```python
"""Cron-triggered pipeline endpoints."""
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends

from core.security import verify_cron_secret
from services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])


@router.post("/news-pipeline", status_code=202)
async def trigger_news_pipeline(
    background_tasks: BackgroundTasks,
    _secret=Depends(verify_cron_secret),
):
    """Trigger the daily AI news pipeline. Returns 202 immediately."""
    batch_id = date.today().isoformat()

    async def _run():
        try:
            result = await run_daily_pipeline(batch_id=batch_id)
            logger.info(
                "Pipeline batch %s finished: %d posts, %d errors",
                result.batch_id, result.posts_created, len(result.errors),
            )
        except Exception as e:
            logger.error("Pipeline batch %s crashed: %s", batch_id, e)

    background_tasks.add_task(_run)

    return {
        "status": "accepted",
        "batch_id": batch_id,
        "message": "Pipeline started in background",
    }


@router.get("/health")
async def cron_health():
    """Health check for cron service."""
    return {
        "status": "ok",
        "pipeline": "news-v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

#### Step 3: Register router in `backend/main.py`

Add to imports and router registration:

```python
from routers import cron
# ...
app.include_router(cron.router, prefix="/api")
```

**Run:** `cd backend && .venv/Scripts/python -m pytest tests/test_cron.py -v --tb=short`
**Expected:** All PASSED.

**Full test suite:** `cd backend && .venv/Scripts/python -m pytest tests/ -v --tb=short`
**Expected:** All PASSED.

**Lint:** `cd backend && .venv/Scripts/python -m ruff check .`

**Commit:** `git add backend/routers/cron.py backend/tests/test_cron.py backend/main.py && git commit -m "feat: add cron endpoint for news pipeline [NP2-CRON-01]"`

---

## Task NP2-E2E-01: Local E2E Verification (Manual)

This is a manual verification task, not code. Steps:

1. Ensure `.env` has valid `OPENAI_API_KEY`, `TAVILY_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `CRON_SECRET`
2. Start backend: `cd backend && .venv/Scripts/python -m uvicorn main:app --host 0.0.0.0 --port 8000`
3. Trigger pipeline: `curl -X POST http://localhost:8000/api/cron/news-pipeline -H "x-cron-secret: YOUR_SECRET"`
4. Verify response: `{"status": "accepted", "batch_id": "2026-03-15", ...}`
5. Wait 2-3 minutes, then check logs
6. Verify in Supabase Dashboard:
   - `news_posts` table has 4 new rows (research EN/KO + business EN/KO) with `status='draft'`
   - Each row has `content_expert`, `content_learner`, `content_beginner` populated
   - `fact_pack` JSONB column has structured data
   - `source_cards` JSONB column has source references
   - `translation_group_id` pairs EN/KO rows correctly
7. Verify `pipeline_runs` table has a successful run record
8. Verify `pipeline_logs` table has execution log with tokens/cost

---

## Task NP2-DEPLOY-01: Railway Deploy (Manual)

1. Push to `main`: `git push origin main`
2. Railway auto-deploys
3. Verify Railway health: `curl https://YOUR-RAILWAY-URL/health`
4. Verify cron health: `curl https://YOUR-RAILWAY-URL/api/cron/health`
5. Set up cron job in Railway (or external cron service) to hit `/api/cron/news-pipeline` daily
6. Wait for first run
7. Check Supabase for draft posts
8. Check Railway logs for errors

---

## Summary of All pytest Commands

```bash
# Task 1: Models
cd backend && .venv/Scripts/python -m pytest tests/test_news_pipeline_models.py -v --tb=short

# Task 2: Collection
cd backend && .venv/Scripts/python -m pytest tests/test_news_collection.py -v --tb=short

# Task 3: Ranking
cd backend && .venv/Scripts/python -m pytest tests/test_ranking.py -v --tb=short

# Task 4: Reactions (tests in test_news_collection.py)
cd backend && .venv/Scripts/python -m pytest tests/test_news_collection.py -v --tb=short

# Task 5: Fact extraction
cd backend && .venv/Scripts/python -m pytest tests/test_fact_extractor.py -v --tb=short

# Task 6: Persona writer
cd backend && .venv/Scripts/python -m pytest tests/test_persona_writer.py -v --tb=short

# Task 7: Pipeline orchestrator
cd backend && .venv/Scripts/python -m pytest tests/test_pipeline.py -v --tb=short

# Task 8: Cron endpoint
cd backend && .venv/Scripts/python -m pytest tests/test_cron.py -v --tb=short

# Full suite (before final commit)
cd backend && .venv/Scripts/python -m pytest tests/ -v --tb=short
cd backend && .venv/Scripts/python -m ruff check .
```

## Summary of All git commit Commands

```bash
# Task 1
git add backend/models/news_pipeline.py backend/tests/test_news_pipeline_models.py && git commit -m "feat: add Pydantic models for AI News Pipeline v2 [NP2-MODEL-01]"

# Task 2
git add backend/services/news_collection.py backend/tests/test_news_collection.py && git commit -m "feat: add Tavily news collection service [NP2-COLLECT-01]"

# Task 3
git add backend/services/agents/ranking.py backend/services/agents/prompts_news_pipeline.py backend/tests/test_ranking.py && git commit -m "feat: add LLM news ranking agent [NP2-RANK-01]"

# Task 4
git add backend/tests/test_news_collection.py && git commit -m "feat: add community reactions tests [NP2-REACT-01]"

# Task 5
git add backend/services/agents/fact_extractor.py backend/tests/test_fact_extractor.py && git commit -m "feat: add LLM fact extraction agent [NP2-FACTS-01]"

# Task 6
git add backend/services/agents/persona_writer.py backend/tests/test_persona_writer.py && git commit -m "feat: add LLM persona writer agent [NP2-PERSONA-01]"

# Task 7
git add backend/services/pipeline.py backend/tests/test_pipeline.py && git commit -m "feat: add pipeline orchestrator [NP2-PIPE-01]"

# Task 8
git add backend/routers/cron.py backend/tests/test_cron.py backend/main.py && git commit -m "feat: add cron endpoint for news pipeline [NP2-CRON-01]"
```

---

## Key Architectural Notes

**Why no `content_original` for v2:** Both research and business posts now use 3 personas. The `content_original` column (used by v1 research posts) is no longer written to by the pipeline. The frontend will need a separate update to enable persona tabs for research posts too, but that is outside this backend sprint.

**Why `upsert` in save:** The unique index `uq_news_posts_daily_ai_type` on `(pipeline_batch_id, post_type, locale)` means re-running the pipeline for the same day updates existing rows rather than creating duplicates. Using `upsert` handles both fresh and re-run cases.

**Why no `has_news` column:** The v1 `has_news` boolean for research posts is not needed in v2. If there is no research news, the ranking simply returns `research: null` and no research post is created.

**Error isolation:** Each post type (research, business) runs in its own try/except block. A failure in research fact extraction does not prevent business post generation. This matches the design requirement "Pipeline NEVER crashes on content quality."

**Token cost tracking:** Every LLM call's usage is extracted via `extract_usage_metrics()` and accumulated via `merge_usage_metrics()`. The final totals are stored in `pipeline_logs.tokens_used` and `pipeline_logs.cost_usd`.

### Critical Files for Implementation
- `c:\Users\amy\Desktop\0to1log\backend\models\news_pipeline.py` - Core data models (FactPack, PersonaOutput, PipelineResult) that all other modules depend on
- `c:\Users\amy\Desktop\0to1log\backend\services\agents\prompts_news_pipeline.py` - System prompts for ranking, fact extraction, and 3 personas; controls LLM output quality
- `c:\Users\amy\Desktop\0to1log\backend\services\pipeline.py` - Orchestrator that ties collect/rank/extract/write/save together with error handling
- `c:\Users\amy\Desktop\0to1log\backend\services\agents\client.py` - Existing utility (parse_ai_json, extract_usage_metrics, merge_usage_metrics) reused by all new agents
- `c:\Users\amy\Desktop\0to1log\backend\main.py` - Must register new cron router to expose the pipeline endpoint

## Related Plans

- [[plans/ACTIVE_SPRINT|ACTIVE SPRINT]]