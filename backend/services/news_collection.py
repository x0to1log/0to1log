"""Tavily-based news collection and community reaction gathering."""
import asyncio
import logging

from tavily import TavilyClient

from core.config import settings
from models.news_pipeline import NewsCandidate

logger = logging.getLogger(__name__)

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

    loop = asyncio.get_running_loop()
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

    logger.info(
        "Collected %d unique candidates from %d total results",
        len(candidates),
        len(all_results),
    )
    return candidates


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
