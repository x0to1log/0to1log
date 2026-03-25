"""Tavily-based news collection and community reaction gathering."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from tavily import TavilyClient

from core.config import settings, today_kst
from models.news_pipeline import NewsCandidate

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    "latest AI artificial intelligence news today",
    "AI startup funding investment announcement",
    "new AI model release benchmark",
]

BACKFILL_QUERIES = [
    "AI artificial intelligence news",
    "AI startup funding investment announcement",
    "new AI model release benchmark",
]


async def collect_news(
    max_results_per_query: int = 10,
    target_date: str | None = None,
) -> tuple[list[NewsCandidate], dict[str, Any]]:
    """Collect AI news candidates from Tavily.

    Returns (deduplicated candidates list, collection metadata dict).
    Args:
        target_date: "YYYY-MM-DD" string for backfill, or None for today.
    """
    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured, skipping collection")
        return [], {}

    try:
        tavily = TavilyClient(api_key=settings.tavily_api_key)
    except Exception as e:
        logger.error("Failed to create Tavily client: %s", e)
        return [], {}

    # Determine date params and query set
    is_backfill = False
    if target_date:
        try:
            td = datetime.strptime(target_date, "%Y-%m-%d").date()
            is_backfill = td < datetime.strptime(today_kst(), "%Y-%m-%d").date()
        except ValueError:
            logger.warning("Invalid target_date format: %s, falling back to today", target_date)

    if is_backfill:
        queries = BACKFILL_QUERIES
        start_d = (td - timedelta(days=1)).isoformat()
        end_d = td.isoformat()
        date_kwargs = {"start_date": start_d, "end_date": end_d}
        logger.info("Backfill mode: searching %s to %s", start_d, end_d)
    else:
        queries = SEARCH_QUERIES
        date_kwargs = {"days": 2}

    loop = asyncio.get_running_loop()
    all_results: list[dict] = []

    for query in queries:
        try:
            response = await loop.run_in_executor(
                None,
                lambda q=query, dk=date_kwargs: tavily.search(
                    query=q,
                    search_depth="advanced",
                    max_results=max_results_per_query,
                    topic="news",
                    include_raw_content=True,
                    **dk,
                ),
            )
            all_results.extend(response.get("results", []))
        except Exception as e:
            logger.warning("Tavily search failed for query '%s': %s", query, e)

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
                raw_content=item.get("raw_content") or "",
            )
        )

    logger.info(
        "Collected %d unique candidates from %d total results",
        len(candidates),
        len(all_results),
    )

    meta: dict[str, Any] = {
        "is_backfill": is_backfill,
        "queries": list(queries),
        "date_kwargs": date_kwargs,
        "total_results": len(all_results),
        "unique_candidates": len(candidates),
    }
    return candidates, meta


async def collect_community_reactions(title: str, url: str) -> str:
    """Collect community reactions (Reddit, HN) for a given article.

    Returns combined text of reactions, or empty string on failure.
    """
    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured, skipping community reactions")
        return ""

    query = f'"{title}" site:reddit.com OR site:news.ycombinator.com'

    try:
        tavily = TavilyClient(api_key=settings.tavily_api_key)
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=query,
                search_depth="basic",
                max_results=5,
            ),
        )
        results = response.get("results", [])
        parts: list[str] = []
        for item in results:
            item_url = item.get("url", "")
            content = item.get("content", "")
            if item_url or content:
                parts.append(f"{item_url}\n{content}")
        combined = "\n\n".join(parts)
        logger.info("Collected community reactions for '%s': %d results", title, len(results))
        return combined
    except Exception as e:
        logger.warning("Failed to collect community reactions for '%s': %s", title, e)
        return ""
