import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlunparse

import httpx

from core.config import settings
from models.ranking import NewsCandidate

logger = logging.getLogger(__name__)

TAVILY_QUERIES = [
    "AI LLM new model release",
    "OpenAI Google Anthropic AI announcement",
    "AI startup funding round",
    "AI developer tools launch",
]

AI_KEYWORDS = re.compile(
    r"\b(ai|llm|gpt|openai|anthropic|gemini|claude|mistral|deep\s?learning|machine\s?learning)\b",
    re.IGNORECASE,
)


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication: strip fragments, trailing slashes, lowercase host."""
    parsed = urlparse(url)
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=parsed.path.rstrip("/"),
        fragment="",
    )
    return urlunparse(normalized)


def deduplicate_by_url(candidates: list[NewsCandidate]) -> list[NewsCandidate]:
    """Remove duplicates by normalized URL, keeping first occurrence."""
    seen: set[str] = set()
    unique: list[NewsCandidate] = []
    for c in candidates:
        norm = normalize_url(c.url)
        if norm not in seen:
            seen.add(norm)
            unique.append(c)
    return unique


async def collect_from_tavily(batch_id: str) -> list[NewsCandidate]:
    """Collect news from Tavily API with 4 parallel queries."""
    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured, skipping")
        return []

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    candidates: list[NewsCandidate] = []

    async def search_query(query: str) -> list[dict]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.search(
                query=query,
                search_depth="advanced",
                max_results=3,
                topic="news",
            ),
        )
        return result.get("results", [])

    tasks = [search_query(q) for q in TAVILY_QUERIES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.error("Tavily query failed: %s", result)
            continue
        for item in result:
            candidates.append(
                NewsCandidate(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")[:500],
                    source="tavily",
                )
            )

    return candidates


async def collect_from_hackernews() -> list[NewsCandidate]:
    """Scrape Hacker News top stories and filter by AI keywords."""
    candidates: list[NewsCandidate] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        resp.raise_for_status()
        story_ids = resp.json()[:80]

        async def fetch_story(story_id: int) -> dict | None:
            try:
                r = await client.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                )
                r.raise_for_status()
                return r.json()
            except Exception:
                return None

        stories = await asyncio.gather(*[fetch_story(sid) for sid in story_ids])

    for story in stories:
        if not story or story.get("type") != "story":
            continue
        title = story.get("title", "")
        url = story.get("url", "")
        if not url or not AI_KEYWORDS.search(title):
            continue
        candidates.append(
            NewsCandidate(
                title=title,
                url=url,
                snippet=title,
                source="hackernews",
            )
        )

    return candidates


async def collect_from_github_trending() -> list[NewsCandidate]:
    """Scrape GitHub trending repos created recently with AI topics."""
    try:
        candidates: list[NewsCandidate] = []
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"topic:ai OR topic:llm OR topic:machine-learning created:>{yesterday}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 3,
                },
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            data = resp.json()

        for repo in data.get("items", []):
            candidates.append(
                NewsCandidate(
                    title=repo.get("full_name", ""),
                    url=repo.get("html_url", ""),
                    snippet=repo.get("description", "") or "",
                    source="github",
                )
            )

        return candidates
    except Exception as e:
        logger.info("GitHub trending skipped: %s", e)
        return []


async def collect_all_news(batch_id: str) -> list[NewsCandidate]:
    """Collect from all sources in parallel, deduplicate, return combined list."""
    results = await asyncio.gather(
        collect_from_tavily(batch_id),
        collect_from_hackernews(),
        collect_from_github_trending(),
        return_exceptions=True,
    )

    all_candidates: list[NewsCandidate] = []
    source_names = ["tavily", "hackernews", "github"]

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("%s collection failed: %s", source_names[i], result)
            continue
        all_candidates.extend(result)

    unique = deduplicate_by_url(all_candidates)
    logger.info(
        "Collected %d candidates (%d after dedup) for batch %s",
        len(all_candidates),
        len(unique),
        batch_id,
    )
    return unique
