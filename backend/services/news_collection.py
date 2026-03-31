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
    # Common
    "latest AI artificial intelligence news today",
    # Research
    "new AI model release benchmark",
    "AI machine learning research paper arxiv breakthrough",
    "trending AI open source project GitHub HuggingFace",
    # Business
    "AI startup funding investment acquisition partnership",
    "big tech AI announcement OpenAI Google Microsoft Meta",
    "AI regulation policy enterprise adoption",
    "new AI tool product feature release update",
]

BACKFILL_QUERIES = [
    # Common
    "AI artificial intelligence news",
    # Research
    "new AI model release benchmark",
    "AI machine learning research paper arxiv",
    "trending AI open source GitHub HuggingFace",
    # Business
    "AI startup funding investment acquisition partnership",
    "big tech AI announcement OpenAI Google Microsoft",
    "AI enterprise regulation policy",
    "new AI tool product feature release update",
]


def _resolve_google_news_url(url: str) -> str:
    """Resolve a Google News RSS redirect URL to the original article URL.

    Google News RSS returns URLs like news.google.com/rss/articles/CBMi...
    which are opaque redirect links. Uses googlenewsdecoder to extract
    the original URL. Falls back to the redirect URL on failure.
    """
    if "news.google.com/rss/articles/" not in url:
        return url
    try:
        from googlenewsdecoder import new_decoderv1
        result = new_decoderv1(url)
        if result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception:
        pass
    return url


# ---------------------------------------------------------------------------
# Fallback: Exa -> Google News RSS (when Tavily quota exhausted)
# ---------------------------------------------------------------------------

async def _collect_fallback_news(
    queries: list[str], date_kwargs: dict, max_results: int = 10,
) -> list[dict]:
    """Fallback news collection: Exa first, then Google News RSS."""
    results: list[dict] = []

    # --- Exa ---
    if settings.exa_api_key:
        try:
            from exa_py import Exa
            exa = Exa(api_key=settings.exa_api_key)
            loop = asyncio.get_running_loop()
            for query in queries[:4]:  # limit to 4 queries to conserve Exa credits
                try:
                    exa_resp = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda q=query: exa.search_and_contents(
                                q, num_results=5,
                                type="auto", category="news", text=True,
                            ),
                        ),
                        timeout=15,
                    )
                    for r in (exa_resp.results if hasattr(exa_resp, "results") else []):
                        results.append({
                            "url": r.url,
                            "title": r.title or "",
                            "content": (r.text or "")[:2000],
                            "raw_content": r.text or "",
                        })
                except Exception as e:
                    logger.warning("Exa fallback failed for '%s': %s", query, e)
            if results:
                logger.info("Exa fallback collected %d results", len(results))
                return results
        except ImportError:
            logger.warning("exa_py not installed, skipping Exa fallback")
        except Exception as e:
            logger.warning("Exa fallback error: %s", e)

    # --- Google News RSS ---
    try:
        import httpx
        from urllib.parse import quote
        google_results: list[dict] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for query in queries[:4]:
                try:
                    rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
                    resp = await client.get(rss_url)
                    if resp.status_code != 200:
                        continue
                    # Simple XML parsing for RSS items
                    import re
                    items = re.findall(
                        r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?</item>",
                        resp.text, re.DOTALL,
                    )
                    for title, raw_url in items[:5]:
                        # Clean HTML entities
                        title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
                        url = _resolve_google_news_url(raw_url.strip())
                        google_results.append({
                            "url": url,
                            "title": title.strip(),
                            "content": title.strip(),
                            "raw_content": "",
                        })
                except Exception as e:
                    logger.warning("Google News RSS failed for '%s': %s", query, e)
        if google_results:
            logger.info("Google News RSS fallback collected %d results", len(google_results))
        return google_results
    except Exception as e:
        logger.warning("Google News RSS fallback error: %s", e)
        return []


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
    tavily_exhausted = False

    async def _search_with_retry(query: str, dk: dict) -> list[dict]:
        """Search Tavily; if 0 results, retry with wider date range."""
        nonlocal tavily_exhausted
        if tavily_exhausted:
            return []
        for attempt, kwargs in enumerate([dk, {"days": 5}]):
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda q=query, k=kwargs: tavily.search(
                        query=q,
                        search_depth="advanced",
                        max_results=max_results_per_query,
                        topic="news",
                        include_raw_content=True,
                        **k,
                    ),
                )
                results = response.get("results", [])
                if results or attempt > 0:
                    if attempt > 0 and results:
                        logger.info("Tavily retry with wider range found %d results for '%s'", len(results), query)
                    return results
                logger.info("Tavily 0 results for '%s' with %s, retrying wider range", query, kwargs)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "402" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    logger.warning("Tavily quota exhausted: %s — switching to fallback", e)
                    tavily_exhausted = True
                    return []
                logger.warning("Tavily search failed for '%s': %s", query, e)
                return []
        return []

    for query in queries:
        results = await _search_with_retry(query, date_kwargs)
        all_results.extend(results)

    # Fallback: if Tavily exhausted, try Exa then Google News RSS
    if tavily_exhausted or not all_results:
        fallback_results = await _collect_fallback_news(queries, date_kwargs, max_results_per_query)
        all_results.extend(fallback_results)

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

async def _collect_hf_papers(target_date: str | None = None) -> list[NewsCandidate]:
    """Collect top papers from HuggingFace Daily Papers."""
    try:
        params = {}
        if target_date:
            params["date"] = target_date
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://huggingface.co/api/daily_papers", params=params)
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

async def _collect_arxiv(target_date: str | None = None) -> list[NewsCandidate]:
    """Collect recent papers from arXiv in AI categories (cs.AI, cs.CL, cs.LG)."""
    url = "https://export.arxiv.org/api/query"
    base_query = "cat:cs.AI OR cat:cs.CL OR cat:cs.LG"
    if target_date:
        # arXiv date filter: submittedDate:[YYYYMMDD0000 TO YYYYMMDD2359]
        d = target_date.replace("-", "")
        base_query = f"({base_query}) AND submittedDate:[{d}0000 TO {d}2359]"
    params = {
        "search_query": base_query,
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

async def _fetch_readme_excerpt(client: httpx.AsyncClient, full_name: str) -> str:
    """Fetch the first 1000 chars of a repo's README."""
    try:
        resp = await client.get(
            f"https://api.github.com/repos/{full_name}/readme",
            headers={"Accept": "application/vnd.github.raw+json"},
        )
        if resp.status_code == 200:
            return resp.text[:1000]
    except Exception:
        pass
    return ""


async def _collect_github_trending(target_date: str | None = None) -> list[NewsCandidate]:
    """Collect trending AI/ML repositories from GitHub Search API."""
    if target_date:
        ref = datetime.strptime(target_date, "%Y-%m-%d")
    else:
        ref = datetime.now(timezone.utc)
    created_since = (ref - timedelta(days=7)).strftime("%Y-%m-%d")
    url = "https://api.github.com/search/repositories"
    params = {
        "q": f"machine-learning OR deep-learning OR LLM OR language-model OR AI-agent created:>{created_since} stars:>20",
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

        repos = data.get("items", [])[:10]

        # Fetch README excerpts in parallel
        async with httpx.AsyncClient(timeout=10.0) as readme_client:
            readme_tasks = [
                _fetch_readme_excerpt(readme_client, repo.get("full_name", ""))
                for repo in repos
            ]
            readmes = await asyncio.gather(*readme_tasks, return_exceptions=True)

        candidates: list[NewsCandidate] = []
        for repo, readme in zip(repos, readmes):
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

            readme_text = readme if isinstance(readme, str) else ""
            raw = f"{description}\n\n{readme_text}".strip() if readme_text else description

            candidates.append(NewsCandidate(
                title=f"{full_name}: {description[:100]}" if description else full_name,
                url=repo_url,
                snippet=snippet[:300],
                source="github_trending",
                raw_content=raw,
            ))

        logger.info("Collected %d trending repos from GitHub", len(candidates))
        return candidates
    except Exception as e:
        logger.warning("GitHub Trending collection failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Source: Exa (business-focused news)
# ---------------------------------------------------------------------------

EXA_BUSINESS_QUERIES = [
    "AI startup funding acquisition partnership",
    "OpenAI Google Microsoft Meta AI announcement",
    "new AI tool product launch",
    "AI regulation policy enterprise",
    "AI enterprise deployment case study ROI",
    "AI chip hardware Nvidia AMD Intel",
    "AI pricing model SaaS subscription",
    "AI workforce hiring layoffs talent",
]

EXA_RESEARCH_QUERIES = [
    "new AI model release benchmark SOTA",
    "open source LLM launch weights huggingface",
    "AI framework library update release",
    "machine learning breakthrough architecture",
]

async def _collect_exa(target_date: str | None = None) -> list[NewsCandidate]:
    """Collect AI business news via Exa API. Runs independently of Tavily."""
    if not settings.exa_api_key:
        return []

    try:
        from exa_py import Exa
    except ImportError:
        logger.warning("exa_py not installed, skipping Exa collection")
        return []

    try:
        exa = Exa(api_key=settings.exa_api_key)
        loop = asyncio.get_running_loop()
        candidates: list[NewsCandidate] = []

        for query in EXA_BUSINESS_QUERIES + EXA_RESEARCH_QUERIES:
            try:
                exa_resp = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda q=query: exa.search_and_contents(
                            q, num_results=5,
                            type="auto", category="news", text=True,
                        ),
                    ),
                    timeout=15,
                )
                for r in (exa_resp.results if hasattr(exa_resp, "results") else []):
                    if not r.url:
                        continue
                    candidates.append(NewsCandidate(
                        title=r.title or "",
                        url=r.url,
                        snippet=(r.text or "")[:300],
                        source="exa",
                        raw_content=r.text or "",
                    ))
            except Exception as e:
                logger.debug("Exa query failed for '%s': %s", query, e)

        logger.info("Collected %d candidates from Exa", len(candidates))
        return candidates
    except Exception as e:
        logger.warning("Exa collection failed: %s", e)
        return []


BRAVE_QUERIES = [
    "AI news today latest announcements",
    "AI startup funding round",
    "new AI product tool launch",
    "AI regulation policy update",
]


async def _collect_brave(target_date: str | None = None) -> list[NewsCandidate]:
    """Collect AI news via Brave Search API. Independent collector."""
    if not settings.brave_api_key:
        return []

    try:
        candidates: list[NewsCandidate] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in BRAVE_QUERIES:
                try:
                    resp = await client.get(
                        "https://api.search.brave.com/res/v1/news/search",
                        headers={"X-Subscription-Token": settings.brave_api_key},
                        params={
                            "q": query,
                            "count": 10,
                            "freshness": "pd",  # past day
                        },
                    )
                    if resp.status_code != 200:
                        logger.debug("Brave query '%s' returned %d", query, resp.status_code)
                        continue
                    data = resp.json()
                    for result in data.get("results", []):
                        url = result.get("url", "")
                        if not url:
                            continue
                        candidates.append(NewsCandidate(
                            title=result.get("title", ""),
                            url=url,
                            snippet=result.get("description", "")[:300],
                            source="brave",
                            raw_content=result.get("description", ""),
                        ))
                except Exception as e:
                    logger.debug("Brave query failed for '%s': %s", query, e)

        logger.info("Collected %d candidates from Brave", len(candidates))
        return candidates
    except Exception as e:
        logger.warning("Brave collection failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Multi-source enrichment: find additional sources for classified items
# ---------------------------------------------------------------------------

async def enrich_sources(
    groups: list,
    raw_content_map: dict[str, str],
    target_date: str | None = None,
    max_sources: int = 4,
) -> dict[str, list[dict]]:
    """Find additional sources for groups that need them.

    Groups with 2+ items already have multi-source coverage from merge — skip.
    Groups with 1 item use Exa find_similar to locate additional sources.

    Args:
        groups: ClassifiedGroup list (post-ranking).
        raw_content_map: {url: raw_content} from 1st collection.
        target_date: Target date string (YYYY-MM-DD) or None for today.
        max_sources: Max total sources per group (including originals).

    Returns:
        {primary_url: [{"url": ..., "title": ..., "content": ...}, ...]}
    """
    enriched: dict[str, list[dict]] = {}
    needs_enrich: list = []

    for group in groups:
        primary = group.primary_url
        if not primary:
            continue

        if len(group.items) >= 2:
            # Already multi-source from merge — use existing sources
            enriched[primary] = [
                {"url": item.url, "title": item.title,
                 "content": raw_content_map.get(item.url, "")}
                for item in group.items
            ]
        else:
            needs_enrich.append(group)

    if not needs_enrich:
        logger.info("All %d groups have 2+ sources — skipping Exa enrichment", len(groups))
        return enriched

    if not settings.exa_api_key:
        logger.info("No Exa API key — returning merge-only sources")
        for group in needs_enrich:
            enriched[group.primary_url] = [
                {"url": item.url, "title": item.title,
                 "content": raw_content_map.get(item.url, "")}
                for item in group.items
            ]
        return enriched

    try:
        from exa_py import Exa
    except ImportError:
        logger.warning("exa_py not installed — returning merge-only sources")
        for group in needs_enrich:
            enriched[group.primary_url] = [
                {"url": item.url, "title": item.title,
                 "content": raw_content_map.get(item.url, "")}
                for item in group.items
            ]
        return enriched

    # Date filter: 48 hours around target date
    if target_date:
        try:
            base = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            base = datetime.now(timezone.utc)
    else:
        base = datetime.now(timezone.utc)
    start_date = (base - timedelta(days=2)).strftime("%Y-%m-%d")
    end_date = (base + timedelta(days=1)).strftime("%Y-%m-%d")

    exa = Exa(api_key=settings.exa_api_key)
    loop = asyncio.get_running_loop()

    async def _enrich_one(group) -> tuple[str, list[dict]]:
        item = group.items[0]
        original_content = raw_content_map.get(item.url, "")
        sources = [{"url": item.url, "title": item.title, "content": original_content}]

        try:
            resp = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: exa.find_similar_and_contents(
                        url=item.url,
                        num_results=max_sources - 1,
                        text=True,
                        start_published_date=start_date,
                        end_published_date=end_date,
                    ),
                ),
                timeout=15,
            )
            for r in (resp.results if hasattr(resp, "results") else []):
                if not r.url or r.url == item.url:
                    continue
                sources.append({
                    "url": r.url,
                    "title": r.title or "",
                    "content": r.text or "",
                })
        except Exception as e:
            logger.debug("Enrich failed for '%s': %s", group.group_title[:60], e)

        return group.primary_url, sources

    tasks = [_enrich_one(g) for g in needs_enrich]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.debug("Enrich task exception: %s", result)
            continue
        url, sources = result
        enriched[url] = sources

    total_extra = sum(max(0, len(s) - 1) for s in enriched.values())
    merged_count = len(groups) - len(needs_enrich)
    logger.info(
        "Enriched %d groups: %d from merge (skipped Exa), %d via Exa (%d extra sources)",
        len(groups), merged_count, len(needs_enrich), total_extra,
    )
    return enriched


# ---------------------------------------------------------------------------
# Main entry point: collect from all sources
# ---------------------------------------------------------------------------

async def collect_news(
    max_results_per_query: int = 10,
    target_date: str | None = None,
    published_urls: set[str] | None = None,
) -> tuple[list[NewsCandidate], dict[str, Any]]:
    """Collect AI news candidates from all sources in parallel.

    Args:
        published_urls: URLs already used in recent digests — excluded from results.
    Returns (deduplicated candidates list, collection metadata dict).
    """
    # Run all collectors in parallel
    tavily_task = _collect_tavily(max_results_per_query, target_date)
    hf_task = _collect_hf_papers(target_date)
    arxiv_task = _collect_arxiv(target_date)
    github_task = _collect_github_trending(target_date)
    exa_task = _collect_exa(target_date)
    brave_task = _collect_brave(target_date)

    tavily_results, tavily_meta = await tavily_task
    hf_results, arxiv_results, github_results, exa_results, brave_results = await asyncio.gather(
        hf_task, arxiv_task, github_task, exa_task, brave_task, return_exceptions=True,
    )

    # Safely collect results (treat exceptions as empty lists)
    all_candidates: list[NewsCandidate] = list(tavily_results)
    source_counts: dict[str, int] = {"tavily": len(tavily_results)}

    for name, result in [("hf_papers", hf_results), ("arxiv", arxiv_results), ("github_trending", github_results), ("exa", exa_results), ("brave", brave_results)]:
        if isinstance(result, Exception):
            logger.warning("Collector %s failed: %s", name, result)
            source_counts[name] = 0
        else:
            all_candidates.extend(result)
            source_counts[name] = len(result)

    # Deduplicate by URL + exclude already-published URLs + filter non-article pages
    already_used = published_urls or set()
    seen_urls: set[str] = set()
    unique: list[NewsCandidate] = []
    excluded_count = 0
    filtered_count = 0
    _NON_ARTICLE_PATTERNS = ("/category/", "/categories/", "/topics/", "/topic/", "/tag/", "/tags/", "/archive/")
    for c in all_candidates:
        if c.url in already_used:
            excluded_count += 1
            continue
        # Filter category/topic/index pages (not individual articles)
        from urllib.parse import urlparse
        path = urlparse(c.url).path.rstrip("/")
        if not path or path == "" or any(p in c.url.lower() for p in _NON_ARTICLE_PATTERNS):
            filtered_count += 1
            continue
        if c.url not in seen_urls:
            seen_urls.add(c.url)
            unique.append(c)

    logger.info(
        "Collected %d unique candidates (tavily=%d, hf=%d, arxiv=%d, github=%d, exa=%d, brave=%d, excluded_published=%d, filtered_non_article=%d)",
        len(unique), source_counts["tavily"], source_counts.get("hf_papers", 0),
        source_counts.get("arxiv", 0), source_counts.get("github_trending", 0),
        source_counts.get("exa", 0), source_counts.get("brave", 0), excluded_count, filtered_count,
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


def _is_spam_comment(text: str) -> bool:
    """Detect bot-generated spam comments (meaningless tech jargon patterns)."""
    # Spam pattern: sentences with random tech terms strung together without meaning
    spam_phrases = [
        "automates dom elements",
        "queries backend services",
        "implements continuous integration",
        "encrypts load balancers",
        "initializes dom elements",
        "overrides recursive functions",
        "enhances complex variables",
        "iterates responsive layouts",
        "structures load balancers",
        "prototyping phase",
    ]
    lower = text.lower()
    matches = sum(1 for p in spam_phrases if p in lower)
    return matches >= 2


def _title_relevance(article_title: str, thread_title: str) -> float:
    """Check relevance between article title and thread title (0-100)."""
    from difflib import SequenceMatcher
    # Token-set comparison: normalize, split, compare overlap
    a_tokens = set(article_title.lower().split())
    t_tokens = set(thread_title.lower().split())
    if not a_tokens or not t_tokens:
        return 0.0
    overlap = len(a_tokens & t_tokens)
    # Weighted: overlap / min(len) gives higher score when shorter title fully matches
    token_score = (overlap / min(len(a_tokens), len(t_tokens))) * 100
    # Also use sequence matcher for substring similarity
    seq_score = SequenceMatcher(None, article_title.lower(), thread_title.lower()).ratio() * 100
    return max(token_score, seq_score)


async def collect_community_reactions(title: str, url: str) -> str:
    """Collect community reactions with ACTUAL COMMENT TEXT from HN + Reddit.

    Strategy: URL-based search first (most accurate), keyword fallback with relevance check.

    Returns formatted reactions with real quotes, or empty string if none found.
    """
    import httpx

    # Extract key search terms for keyword fallback
    _STOP_WORDS = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
                   "of", "and", "or", "its", "it", "this", "that", "with", "by", "from", "as",
                   "has", "have", "had", "how", "what", "why", "new", "latest", "just", "now"}
    keywords = [w for w in title.split() if w.lower().strip(",:;.!?'\"()") not in _STOP_WORDS]
    search_terms = " ".join(keywords[:6])
    parts: list[str] = []

    async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "0to1log:news-digest/1.0 (by /u/0to1log)"}) as client:
        # --- Hacker News: URL search first, keyword fallback ---
        try:
            # Phase 1: URL-based search (most accurate)
            best_hit = None
            if url:
                hn_url_resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"query": url, "tags": "story", "restrictSearchableAttributes": "url", "hitsPerPage": 3},
                )
                if hn_url_resp.status_code == 200:
                    url_hits = [h for h in hn_url_resp.json().get("hits", []) if (h.get("points") or 0) >= 5]
                    if url_hits:
                        best_hit = max(url_hits, key=lambda h: h.get("points") or 0)
                        logger.debug("HN URL match: '%s' (%d pts)", best_hit.get("title", "")[:40], best_hit.get("points", 0))

            # Phase 2: Keyword fallback with relevance check
            if not best_hit:
                hn_resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"query": search_terms, "tags": "story", "hitsPerPage": 5},
                )
                if hn_resp.status_code == 200:
                    hits = hn_resp.json().get("hits", [])
                    for h in sorted(hits, key=lambda h: h.get("points") or 0, reverse=True):
                        if (h.get("points") or 0) < 5:
                            continue
                        relevance = _title_relevance(title, h.get("title", ""))
                        if relevance >= 35:
                            best_hit = h
                            logger.debug("HN keyword match: '%s' (relevance=%.0f, pts=%d)", h.get("title", "")[:40], relevance, h.get("points", 0))
                            break
                        else:
                            logger.debug("HN keyword skip (low relevance=%.0f): '%s'", relevance, h.get("title", "")[:40])

            # Fetch comments for matched HN thread (works for both URL and keyword matches)
            if best_hit:
                story_id = best_hit.get("objectID", "")
                hn_title = best_hit.get("title", "")
                points = best_hit.get("points", 0)
                num_comments = best_hit.get("num_comments", 0)
                comment_resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"tags": f"comment,story_{story_id}", "hitsPerPage": 5},
                )
                comments_text = []
                if comment_resp.status_code == 200:
                    import re as _re
                    for c in comment_resp.json().get("hits", []):
                        text = c.get("comment_text", "")
                        clean = _re.sub(r"<[^>]+>", " ", text).strip()
                        clean = _re.sub(r"\s+", " ", clean)
                        if len(clean) > 50 and len(clean) < 500 and not _is_spam_comment(clean):
                            comments_text.append(clean)
                        if len(comments_text) >= 3:
                            break
                thread_block = f"[Hacker News] {hn_title} | {points} points | {num_comments} comments\n"
                if comments_text:
                    thread_block += "Top comments:\n"
                    thread_block += "\n".join(f'> "{ct}"' for ct in comments_text)
                parts.append(thread_block)
        except Exception as e:
            logger.debug("HN search failed for '%s': %s", title[:40], e)

        # --- Reddit: URL search first, keyword fallback with relevance ---
        import random
        await asyncio.sleep(random.uniform(1.0, 5.0))
        ALLOWED_SUBREDDITS = {
            # AI/ML research
            "machinelearning", "artificial", "artificialintelligence",
            "deeplearning", "datascience", "mlops", "learnmachinelearning",
            "languagemodels", "agi", "singularity",
            "reinforcementlearning", "computervision", "nlp", "mlpapers",
            # Frameworks & tools
            "pytorch", "tensorflow", "jax",
            # Model/platform specific
            "locallama", "openai", "chatgpt", "claudeai", "anthropic",
            "mistralai", "ollama", "stablediffusion", "huggingface",
            # Big Tech
            "google", "microsoft", "apple", "meta", "nvidia", "amd", "aws",
            # General tech
            "technology", "programming", "compsci", "computerscience",
            "science", "futurology", "robotics", "selfhosted", "opensource",
            # Business/startup
            "startups",
        }
        try:
            best_thread = None

            # Phase 1: URL-based Reddit search (most accurate)
            if url:
                rd_url_resp = await client.get(
                    "https://www.reddit.com/search.json",
                    params={"q": f"url:{url}", "sort": "relevance", "limit": 5, "t": "month"},
                )
                if rd_url_resp.status_code == 200:
                    for child in rd_url_resp.json().get("data", {}).get("children", []):
                        rd = child.get("data", {})
                        if rd.get("subreddit", "").lower() in ALLOWED_SUBREDDITS and (rd.get("score", 0) >= 5):
                            best_thread = rd
                            logger.debug("Reddit URL match: r/%s '%s' (%d upvotes)", rd.get("subreddit", ""), rd.get("title", "")[:40], rd.get("score", 0))
                            break

            # Phase 2: Keyword fallback with relevance check
            if not best_thread:
                await asyncio.sleep(random.uniform(0.5, 2.0))  # Extra delay between requests
                reddit_resp = await client.get(
                    "https://www.reddit.com/search.json",
                    params={"q": search_terms, "sort": "relevance", "limit": 10, "t": "week"},
                )
                if reddit_resp.status_code == 200:
                    children = reddit_resp.json().get("data", {}).get("children", [])
                    for child in children:
                        rd = child.get("data", {})
                        subreddit = rd.get("subreddit", "").lower()
                        if subreddit not in ALLOWED_SUBREDDITS:
                            continue
                        score = rd.get("score", 0)
                        if score < 5:
                            continue
                        relevance = _title_relevance(title, rd.get("title", ""))
                        if relevance >= 35:
                            best_thread = rd
                            logger.debug("Reddit keyword match: r/%s '%s' (relevance=%.0f, score=%d)", subreddit, rd.get("title", "")[:40], relevance, score)
                            break
                        else:
                            logger.debug("Reddit keyword skip (relevance=%.0f): r/%s '%s'", relevance, subreddit, rd.get("title", "")[:40])
                if best_thread:
                    permalink = best_thread.get("permalink", "")
                    rd_title = best_thread.get("title", "")
                    subreddit = best_thread.get("subreddit", "")
                    score = best_thread.get("score", 0)
                    num_comments = best_thread.get("num_comments", 0)
                    # Fetch top comments
                    comments_text = []
                    try:
                        comment_resp = await client.get(
                            f"https://www.reddit.com{permalink}.json",
                            params={"limit": 5, "sort": "top", "depth": 1},
                        )
                        if comment_resp.status_code == 200:
                            comment_data = comment_resp.json()
                            if len(comment_data) > 1:
                                for c in comment_data[1].get("data", {}).get("children", []):
                                    body = c.get("data", {}).get("body", "")
                                    c_score = c.get("data", {}).get("score", 0)
                                    if body and len(body) > 30 and len(body) < 500 and c_score > 2 and not _is_spam_comment(body):
                                        comments_text.append(body.strip())
                                    if len(comments_text) >= 3:
                                        break
                    except Exception:
                        pass
                    thread_block = f"[Reddit r/{subreddit}] {rd_title} | {score} upvotes | {num_comments} comments\n"
                    if comments_text:
                        thread_block += "Top comments:\n"
                        thread_block += "\n".join(f'> "{ct}"' for ct in comments_text)
                    parts.append(thread_block)
        except Exception as e:
            logger.debug("Reddit search failed for '%s': %s", title[:40], e)

    combined = "\n\n".join(parts)
    if parts:
        logger.info("Collected %d community threads with comments for '%s'", len(parts), title[:40])
    return combined
