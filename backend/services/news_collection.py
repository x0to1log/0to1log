"""News collection from multiple sources: Tavily, HuggingFace, arXiv, GitHub."""
import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tavily import TavilyClient

from core.config import settings, today_kst
from models.news_pipeline import NewsCandidate

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    "latest AI artificial intelligence news today",
    "AI startup funding investment announcement",
    "new AI model release benchmark",
    "AI machine learning research paper arxiv breakthrough",
    "trending AI open source project GitHub HuggingFace",
]

BACKFILL_QUERIES = [
    "AI artificial intelligence news",
    "AI startup funding investment announcement",
    "new AI model release benchmark",
    "AI machine learning research paper arxiv",
    "trending AI open source GitHub HuggingFace",
]


# ---------------------------------------------------------------------------
# Source: Tavily (general news)
# ---------------------------------------------------------------------------

async def _collect_tavily(
    max_results_per_query: int = 10,
    target_date: str | None = None,
) -> tuple[list[NewsCandidate], dict[str, Any]]:
    """Collect AI news candidates from Tavily."""
    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured, skipping collection")
        return [], {"source": "tavily", "status": "skipped"}

    try:
        tavily = TavilyClient(api_key=settings.tavily_api_key)
    except Exception as e:
        logger.error("Failed to create Tavily client: %s", e)
        return [], {"source": "tavily", "status": "error"}

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

    candidates: list[NewsCandidate] = []
    for item in all_results:
        url = item.get("url", "")
        if not url:
            continue
        candidates.append(
            NewsCandidate(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("content", ""),
                source="tavily",
                raw_content=item.get("raw_content") or "",
            )
        )

    meta: dict[str, Any] = {
        "source": "tavily",
        "queries": list(queries),
        "total_results": len(all_results),
        "candidates": len(candidates),
    }
    return candidates, meta


# ---------------------------------------------------------------------------
# Source: HuggingFace Daily Papers
# ---------------------------------------------------------------------------

async def _collect_hf_papers() -> list[NewsCandidate]:
    """Collect today's top papers from HuggingFace Daily Papers."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://huggingface.co/api/daily_papers")
            resp.raise_for_status()
            papers = resp.json()

        candidates: list[NewsCandidate] = []
        for paper in papers[:10]:
            title = paper.get("title", "")
            paper_data = paper.get("paper", {})
            paper_id = paper_data.get("id", "")
            summary = paper_data.get("summary", "") or paper.get("summary", "")

            if not paper_id:
                continue

            candidates.append(NewsCandidate(
                title=title,
                url=f"https://arxiv.org/abs/{paper_id}",
                snippet=summary[:300],
                source="hf_papers",
                raw_content=summary,
            ))

        logger.info("Collected %d papers from HuggingFace Daily Papers", len(candidates))
        return candidates
    except Exception as e:
        logger.warning("HuggingFace Daily Papers collection failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Source: arXiv API (cs.AI, cs.CL, cs.LG)
# ---------------------------------------------------------------------------

async def _collect_arxiv() -> list[NewsCandidate]:
    """Collect recent papers from arXiv in AI categories (cs.AI, cs.CL, cs.LG)."""
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": "10",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.text)

        candidates: list[NewsCandidate] = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
            summary = (entry.findtext("atom:summary", "", ns) or "").strip().replace("\n", " ")
            entry_id = entry.findtext("atom:id", "", ns) or ""

            if not entry_id:
                continue

            abs_url = entry_id.replace("http://", "https://")

            candidates.append(NewsCandidate(
                title=title,
                url=abs_url,
                snippet=summary[:300],
                source="arxiv",
                raw_content=summary,
            ))

        logger.info("Collected %d papers from arXiv", len(candidates))
        return candidates
    except Exception as e:
        logger.warning("arXiv collection failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Source: GitHub Trending (AI/ML)
# ---------------------------------------------------------------------------

async def _collect_github_trending() -> list[NewsCandidate]:
    """Collect trending AI/ML repositories from GitHub Search API."""
    since_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    url = "https://api.github.com/search/repositories"
    params = {
        "q": f"AI OR machine-learning OR LLM OR deep-learning created:>{since_date}",
        "sort": "stars",
        "order": "desc",
        "per_page": "10",
    }
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        candidates: list[NewsCandidate] = []
        for repo in data.get("items", [])[:10]:
            full_name = repo.get("full_name", "")
            description = repo.get("description", "") or ""
            stars = repo.get("stargazers_count", 0)
            language = repo.get("language", "") or ""
            repo_url = repo.get("html_url", "")

            if not repo_url:
                continue

            snippet_parts = [description, f"Stars: {stars:,}"]
            if language:
                snippet_parts.append(f"Language: {language}")
            snippet = " | ".join(snippet_parts)

            candidates.append(NewsCandidate(
                title=f"{full_name}: {description[:100]}" if description else full_name,
                url=repo_url,
                snippet=snippet[:300],
                source="github_trending",
                raw_content=description,
            ))

        logger.info("Collected %d trending repos from GitHub", len(candidates))
        return candidates
    except Exception as e:
        logger.warning("GitHub Trending collection failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Main entry point: collect from all sources
# ---------------------------------------------------------------------------

async def collect_news(
    max_results_per_query: int = 10,
    target_date: str | None = None,
) -> tuple[list[NewsCandidate], dict[str, Any]]:
    """Collect AI news candidates from all sources in parallel.

    Returns (deduplicated candidates list, collection metadata dict).
    """
    # Run all collectors in parallel
    tavily_task = _collect_tavily(max_results_per_query, target_date)
    hf_task = _collect_hf_papers()
    arxiv_task = _collect_arxiv()
    github_task = _collect_github_trending()

    tavily_results, tavily_meta = await tavily_task
    hf_results, arxiv_results, github_results = await asyncio.gather(
        hf_task, arxiv_task, github_task, return_exceptions=True,
    )

    # Safely collect results (treat exceptions as empty lists)
    all_candidates: list[NewsCandidate] = list(tavily_results)
    source_counts: dict[str, int] = {"tavily": len(tavily_results)}

    for name, result in [("hf_papers", hf_results), ("arxiv", arxiv_results), ("github_trending", github_results)]:
        if isinstance(result, Exception):
            logger.warning("Collector %s failed: %s", name, result)
            source_counts[name] = 0
        else:
            all_candidates.extend(result)
            source_counts[name] = len(result)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[NewsCandidate] = []
    for c in all_candidates:
        if c.url not in seen_urls:
            seen_urls.add(c.url)
            unique.append(c)

    logger.info(
        "Collected %d unique candidates (tavily=%d, hf=%d, arxiv=%d, github=%d)",
        len(unique), source_counts["tavily"], source_counts.get("hf_papers", 0),
        source_counts.get("arxiv", 0), source_counts.get("github_trending", 0),
    )

    is_backfill = False
    if target_date:
        try:
            is_backfill = datetime.strptime(target_date, "%Y-%m-%d").date() < datetime.strptime(today_kst(), "%Y-%m-%d").date()
        except ValueError:
            pass

    meta: dict[str, Any] = {
        "is_backfill": is_backfill,
        "source_counts": source_counts,
        "total_candidates": len(unique),
        **tavily_meta,
    }
    return unique, meta


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
