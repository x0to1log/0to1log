"""News collection from multiple sources: Tavily, HuggingFace, arXiv, GitHub."""
import asyncio
import logging
import re as _re_module
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import httpx
from tavily import TavilyClient

from core.config import settings, today_kst
from core.database import get_supabase
from models.news_pipeline import NewsCandidate

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_domain_filters() -> dict[str, frozenset[str]]:
    """Load domain filter lists from Supabase news_domain_filters table.

    Cached for the lifetime of the process — restart Railway to refresh.
    Returns dict with keys: block_non_en, official_priority, media_tier.
    Falls back to empty sets if DB is unreachable (logs error).
    """
    result: dict[str, frozenset[str]] = {
        "block_non_en": frozenset(),
        "official_priority": frozenset(),
        "media_tier": frozenset(),
        "research_priority": frozenset(),
        "research_blocklist": frozenset(),
    }
    try:
        supabase = get_supabase()
        if supabase is None:
            logger.error("Supabase client unavailable — falling back to empty domain filters")
            return result
        rows = supabase.table("news_domain_filters").select("domain, filter_type").execute()
        if not rows.data:
            logger.error("news_domain_filters table is empty — falling back to empty filters")
            return result
        buckets: dict[str, set[str]] = {k: set() for k in result}
        for row in rows.data:
            ftype = row.get("filter_type")
            domain = row.get("domain")
            if ftype in buckets and domain:
                buckets[ftype].add(domain.lower())
        return {k: frozenset(v) for k, v in buckets.items()}
    except Exception as e:
        logger.error("Failed to load news_domain_filters from DB: %s — falling back to empty", e)
        return result


# Domain filter lists are now loaded from Supabase via _load_domain_filters().
# See migration 00050_news_domain_filters.sql for schema and seed data.
# To modify: update the table directly, then restart Railway to refresh the cache.

SEARCH_QUERIES = [
    # Common
    "latest AI artificial intelligence news today",
    # Research
    "new AI model release benchmark",
    # (arxiv/github/HF research queries dropped 2026-04-16 — free arxiv/github_trending/hf_papers
    #  collectors already cover these domains. Tavily rediscovery was wasted quota.)
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
    # (arxiv/github/HF backfill queries dropped 2026-04-16 — same reason as SEARCH_QUERIES)
    # Business
    "AI startup funding investment acquisition partnership",
    "big tech AI announcement OpenAI Google Microsoft",
    "AI enterprise regulation policy",
    "new AI tool product feature release update",
]

_OFFICIAL_LOOKUP_DOMAIN_HINTS: dict[str, tuple[str, ...]] = {
    "openai": ("openai.com",),
    "anthropic": ("anthropic.com",),
    "microsoft": ("techcommunity.microsoft.com", "microsoft.com", "www.microsoft.com"),
    "nvidia": ("developer.nvidia.com", "blogs.nvidia.com"),
    "google": ("blog.google", "deepmind.google", "ai.google.dev"),
    "deepmind": ("deepmind.google", "blog.google"),
    "meta": ("about.fb.com", "ai.meta.com"),
    "amazon": ("aboutamazon.com", "aws.amazon.com", "openai.com"),
    "aws": ("aws.amazon.com", "aboutamazon.com"),
    "apple": ("developer.apple.com", "machinelearning.apple.com"),
    "cloudflare": ("blog.cloudflare.com",),
    "coreweave": ("coreweave.com",),
}

_OFFICIAL_LOOKUP_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "over", "after",
    "about", "their", "there", "while", "users", "must", "update", "apps", "app",
    "news", "today", "week", "story", "report", "reported", "reportedly", "latest",
    "confirms", "launches", "announces", "introduces", "released", "release",
}


def _classify_source_meta(url: str, source: str = "", title: str = "") -> dict[str, str]:
    """Classify source provenance metadata using rule-based URL heuristics."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    path = parsed.path.lower().rstrip("/")
    title_lower = title.lower()
    _ = source  # keep signature stable for future collector-specific rules

    if not hostname:
        return {
            "source_kind": "analysis",
            "source_confidence": "low",
            "source_tier": "secondary",
        }

    # Phase 2 — research_blocklist HIGHEST priority (kill source before any other tier check)
    filters = _load_domain_filters()
    if any(d in hostname for d in filters.get("research_blocklist", frozenset())):
        return {
            "source_kind": "spam",
            "source_confidence": "low",
            "source_tier": "spam",
        }

    if "arxiv.org" in hostname:
        return {
            "source_kind": "paper",
            "source_confidence": "high",
            "source_tier": "primary",
        }

    if "microsoft.com" in hostname and any(
        path.startswith(p) for p in (
            "/en-us/research/",
            "/en-us/security/blog/",
            "/en-us/microsoft-365/blog/",
            "/en-us/ai/blog/",
        )
    ):
        return {
            "source_kind": "official_site",
            "source_confidence": "high",
            "source_tier": "primary",
        }

    if any(domain in hostname for domain in _load_domain_filters()["official_priority"]):
        return {
            "source_kind": "official_site",
            "source_confidence": "high",
            "source_tier": "primary",
        }

    if "huggingface.co" in hostname:
        if path.startswith("/blog/"):
            return {
                "source_kind": "official_platform_asset",
                "source_confidence": "medium",
                "source_tier": "primary",
            }
        return {
            "source_kind": "official_platform_asset",
            "source_confidence": "high",
            "source_tier": "primary",
        }

    if "github.com" in hostname:
        if "/pull/" in path or "/releases" in path or "/blob/" in path or path.count("/") <= 2:
            return {
                "source_kind": "official_repo",
                "source_confidence": "medium",
                "source_tier": "primary",
            }
        if "github.com/" in url and any(term in title_lower for term in ("release", "readme", "docs")):
            return {
                "source_kind": "official_repo",
                "source_confidence": "medium",
                "source_tier": "primary",
            }

    if "registry.npmjs.org" in hostname or "npmjs.com" in hostname:
        return {
            "source_kind": "registry",
            "source_confidence": "medium",
            "source_tier": "primary",
        }

    # Phase 2 — research_priority catches remaining research domains
    # (openreview.net, distill.pub, deepmind.google, etc.) not covered by
    # the specific handlers above. arxiv.org and huggingface.co keep their
    # more specific kinds via the earlier branches.
    if any(d in hostname for d in filters.get("research_priority", frozenset())):
        return {
            "source_kind": "research_primary",
            "source_confidence": "high",
            "source_tier": "primary",
        }

    if any(domain in hostname for domain in _load_domain_filters()["media_tier"]):
        return {
            "source_kind": "media",
            "source_confidence": "high",
            "source_tier": "secondary",
        }

    if any(domain in hostname for domain in ("medium.com", "substack.com")):
        return {
            "source_kind": "analysis",
            "source_confidence": "medium",
            "source_tier": "secondary",
        }

    if any(domain in hostname for domain in ("reddit.com", "news.ycombinator.com", "x.com", "twitter.com")):
        return {
            "source_kind": "community",
            "source_confidence": "medium",
            "source_tier": "secondary",
        }

    return {
        "source_kind": "analysis",
        "source_confidence": "low",
        "source_tier": "secondary",
    }


def _build_source_payload(
    *,
    url: str,
    title: str,
    content: str,
    source: str = "",
) -> dict[str, str]:
    """Create a normalized source payload with provenance metadata."""
    meta = _classify_source_meta(url=url, source=source, title=title)
    return {
        "url": url,
        "title": title,
        "content": content,
        **meta,
    }


def _canonicalize_source_url(url: str) -> str:
    """Normalize a source URL for stable dedupe."""
    if not url:
        return ""
    stripped = url.strip()
    parsed = urlparse(stripped)
    path = parsed.path.rstrip("/")
    normalized = parsed._replace(fragment="", path=path)
    return normalized.geturl()


def _enrich_source_passes_quality(payload: dict, source: str) -> tuple[bool, str]:
    """Quality gate for enrich-stage sources. Returns (passes, reason_if_dropped).

    Mirrors collect-stage filters so enrich can't bypass quality checks that
    collect applies (DRY fix for 2026-04-19 content-farm leakage).

    Rules:
    - Drop tier='spam' (matches research_blocklist in _classify_source_meta)
    - Drop analysis+low (unknown content farms with no authority signal)
    - Drop official_repo from exa_enrich (find_similar returns noisy GitHub
      matches — random user repos that happen to mention a company name)

    `source` is passed separately because _build_source_payload does not
    include it in the returned payload dict.
    """
    tier = payload.get("source_tier", "")
    kind = payload.get("source_kind", "")
    confidence = payload.get("source_confidence", "")

    if tier == "spam":
        return False, "spam"
    if kind == "analysis" and confidence == "low":
        return False, "analysis/low (unknown blog)"
    if kind == "official_repo" and source == "exa_enrich":
        return False, "github.com via find_similar (noisy)"
    return True, ""


def _official_lookup_domains(group_title: str, item_title: str) -> list[str]:
    """Infer likely official domains from group/item titles."""
    text = f"{group_title} {item_title}".lower()
    domains: list[str] = []
    for keyword, hinted_domains in _OFFICIAL_LOOKUP_DOMAIN_HINTS.items():
        if keyword not in text:
            continue
        for domain in hinted_domains:
            if domain not in domains:
                domains.append(domain)
    return domains


def _official_lookup_terms(group_title: str, item_title: str) -> list[str]:
    """Build a compact keyword query for official-source lookup."""
    text = f"{group_title} {item_title}".lower()
    raw_terms = _re_module.findall(r"[a-z0-9][a-z0-9\-.]{2,}", text)
    seen: set[str] = set()
    terms: list[str] = []
    for term in raw_terms:
        if term in _OFFICIAL_LOOKUP_STOPWORDS:
            continue
        if term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms[:8]


def _should_lookup_official_source(group) -> bool:
    """Only do official lookup for single-source groups that start from a secondary URL."""
    if len(group.items) != 1:
        return False
    item = group.items[0]
    meta = _classify_source_meta(url=item.url, title=item.title)
    if meta["source_tier"] == "primary":
        return False
    return group.reason.startswith("[LEAD]") or meta["source_tier"] == "secondary"


async def _lookup_official_sources(
    *,
    exa,
    loop,
    group,
    max_sources: int,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Search likely official domains for a source article that matches the lead story."""
    item = group.items[0]
    domains = _official_lookup_domains(group.group_title, item.title)
    if not domains:
        return []

    terms = _official_lookup_terms(group.group_title, item.title)
    if not terms:
        return []

    existing = {_canonicalize_source_url(item.url)}
    official_sources: list[dict] = []

    for domain in domains:
        query = f"{' '.join(terms)} site:{domain}"
        try:
            resp = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda q=query: exa.search_and_contents(
                        q,
                        num_results=max(2, max_sources - 1),
                        type="auto",
                        text=True,
                        start_published_date=start_date,
                        end_published_date=end_date,
                    ),
                ),
                timeout=15,
            )
        except Exception as e:
            logger.debug("Official lookup failed for '%s' on %s: %s", group.group_title[:60], domain, e)
            continue

        for result in (resp.results if hasattr(resp, "results") else []):
            if not result.url:
                continue
            hostname = (urlparse(result.url).hostname or "").lower()
            if hostname != domain and not hostname.endswith(f".{domain}"):
                continue
            canonical_url = _canonicalize_source_url(result.url)
            if canonical_url in existing:
                continue
            result_title = result.title or ""
            if any(d in hostname for d in _load_domain_filters()["block_non_en"]):
                continue
            if any("\u4e00" <= ch <= "\u9fff" for ch in result_title):
                continue
            payload = _build_source_payload(
                url=result.url,
                title=result_title,
                content=result.text or "",
                source="exa_official_lookup",
            )
            passes, reason = _enrich_source_passes_quality(payload, "exa_official_lookup")
            if not passes:
                logger.info(
                    "Official lookup drop [%s]: %s for '%s'",
                    reason, result.url[:80], group.group_title[:40],
                )
                continue
            official_sources.append(payload)
            existing.add(canonical_url)
            if len(official_sources) >= max_sources - 1:
                return official_sources

    return official_sources


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
    fallback_results: list[dict] = []
    if tavily_exhausted or not all_results:
        fallback_results = await _collect_fallback_news(queries, date_kwargs, max_results_per_query)
        all_results.extend(fallback_results)

    fallback_urls = {r.get("url", "") for r in fallback_results}

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
                source="tavily_fallback" if url in fallback_urls else "tavily",
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

# Trimmed 2026-04-16 — 14-day measurement showed Exa 3.19% selection efficiency
# (847 candidates / 27 selected). Reduced queries 12 → 5 cut API cost ~58%.
# Partial restore 2026-04-17 — after API diet, business digest content dropped
# 22% (research stayed stable because research uses free arxiv/github/hf_papers
# unaffected by the diet). Restored 2 business queries covering editorial
# angles not caught by Tavily SEARCH_QUERIES: regulatory/policy and
# chip/hardware. Now 5 business + 2 research = 7 (was 12 → 3).
EXA_BUSINESS_QUERIES = [
    "AI startup funding acquisition partnership",
    "OpenAI Google Microsoft Meta AI announcement",
    "new AI tool product launch",
    "AI regulation policy enterprise",
    "AI chip hardware Nvidia AMD Intel",
]

EXA_RESEARCH_QUERIES = [
    "new AI model release benchmark SOTA",
    "open source LLM launch weights huggingface",
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


# Brave news collection removed 2026-04-16.
# Measurement (14 days, 372 candidates → 7 selected, 1.88% efficiency) showed
# near-zero ROI vs. Tavily/Exa/free collectors. Brave API key and settings.brave_api_key
# remain in use by collect_community_reactions() for HN/Reddit thread discovery —
# that is Brave's unique value; it is NOT replaced here.


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
                _build_source_payload(
                    url=item.url,
                    title=item.title,
                    content=raw_content_map.get(item.url, ""),
                    source="merge",
                )
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
                _build_source_payload(
                    url=item.url,
                    title=item.title,
                    content=raw_content_map.get(item.url, ""),
                    source="merge",
                )
                for item in group.items
            ]
        return enriched

    try:
        from exa_py import Exa
    except ImportError:
        logger.warning("exa_py not installed — returning merge-only sources")
        for group in needs_enrich:
            enriched[group.primary_url] = [
                _build_source_payload(
                    url=item.url,
                    title=item.title,
                    content=raw_content_map.get(item.url, ""),
                    source="merge",
                )
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
        sources = [
            _build_source_payload(
                url=item.url,
                title=item.title,
                content=original_content,
                source="merge",
            )
        ]

        if _should_lookup_official_source(group):
            official_sources = await _lookup_official_sources(
                exa=exa,
                loop=loop,
                group=group,
                max_sources=max_sources,
                start_date=start_date,
                end_date=end_date,
            )
            sources.extend(official_sources)

        seen_source_urls = {_canonicalize_source_url(source["url"]) for source in sources}

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
                # Filter non-EN/KO sources (same as collect stage)
                r_title = r.title or ""
                r_hostname = _re_module.sub(r"https?://(www\.)?", "", r.url).split("/")[0]
                if any(d in r_hostname for d in _load_domain_filters()["block_non_en"]):
                    continue
                if any("\u4e00" <= ch <= "\u9fff" for ch in r_title):
                    continue
                canonical_url = _canonicalize_source_url(r.url)
                if canonical_url in seen_source_urls:
                    continue
                payload = _build_source_payload(
                    url=r.url,
                    title=r_title,
                    content=r.text or "",
                    source="exa_enrich",
                )
                passes, reason = _enrich_source_passes_quality(payload, "exa_enrich")
                if not passes:
                    logger.info(
                        "Enrich drop [%s]: %s for '%s'",
                        reason, r.url[:80], group.group_title[:40],
                    )
                    continue
                sources.append(payload)
                seen_source_urls.add(canonical_url)
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
    # Brave news collection dropped 2026-04-16 — 14-day measurement showed 1.88%
    # selection efficiency (372 candidates / 7 selected). Brave API key remains
    # required for collect_community_reactions() which uses Brave web search for
    # HN/Reddit thread discovery.

    tavily_result, hf_results, arxiv_results, github_results, exa_results = await asyncio.gather(
        tavily_task, hf_task, arxiv_task, github_task, exa_task, return_exceptions=True,
    )

    # Safely collect results (treat exceptions as empty lists)
    if isinstance(tavily_result, Exception):
        logger.warning("Collector tavily failed: %s", tavily_result)
        tavily_results, tavily_meta = [], {}
    else:
        tavily_results, tavily_meta = tavily_result
    all_candidates: list[NewsCandidate] = list(tavily_results)
    source_counts: dict[str, int] = {"tavily": len(tavily_results)}

    for name, result in [("hf_papers", hf_results), ("arxiv", arxiv_results), ("github_trending", github_results), ("exa", exa_results)]:
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
    # Domain filters are loaded from Supabase via _load_domain_filters() (shared with enrich_sources)
    for c in all_candidates:
        if c.url in already_used:
            excluded_count += 1
            continue
        # Filter category/topic/index pages and non-English domains
        from urllib.parse import urlparse
        parsed = urlparse(c.url)
        path = parsed.path.rstrip("/")
        hostname = parsed.hostname or ""
        if not path or path == "" or any(p in c.url.lower() for p in _NON_ARTICLE_PATTERNS):
            filtered_count += 1
            continue
        if any(d in hostname for d in _load_domain_filters()["block_non_en"]):
            filtered_count += 1
            continue
        # Filter non-EN/KO content by detecting CJK characters in title
        if any("\u4e00" <= ch <= "\u9fff" for ch in c.title):
            filtered_count += 1
            continue
        if c.url not in seen_urls:
            seen_urls.add(c.url)
            source_meta = _classify_source_meta(url=c.url, source=c.source, title=c.title)
            # Phase 2 — drop spam-tier (research_blocklist) candidates at collection time
            if source_meta.get("source_tier") == "spam":
                logger.info("Dropping spam-tier source: %s", c.url)
                filtered_count += 1
                continue
            unique.append(c.model_copy(update=source_meta))

    logger.info(
        "Collected %d unique candidates (tavily=%d, hf=%d, arxiv=%d, github=%d, exa=%d, excluded_published=%d, filtered_non_article=%d)",
        len(unique), source_counts["tavily"], source_counts.get("hf_papers", 0),
        source_counts.get("arxiv", 0), source_counts.get("github_trending", 0),
        source_counts.get("exa", 0), excluded_count, filtered_count,
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


# ---------------------------------------------------------------------------
# Entity-first search helpers for community keyword fallback
# ---------------------------------------------------------------------------

# Common headline words that look like entities (capitalized) but aren't
_HEADLINE_COMMON = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
    "of", "and", "or", "its", "it", "this", "that", "with", "by", "from", "as",
    "has", "have", "had", "how", "what", "why", "new", "latest", "just", "now",
    "here", "there", "where", "when", "who", "which", "but", "not", "no", "all",
    "more", "most", "than", "into", "over", "after", "before", "about", "up",
    "out", "will", "can", "may", "could", "should", "would", "also", "very",
    "top", "best", "first", "next", "last", "only", "still", "yet", "even",
    # Common verbs in headlines
    "launches", "launch", "cuts", "says", "gets", "raises", "shows",
    "makes", "takes", "brings", "builds", "releases", "reveals", "announces",
    "introduces", "joins", "hits", "beats", "meets", "aims", "plans", "seeks",
    "acquires", "partners", "expands", "opens", "closes", "drops", "adds",
    # Common adjectives/prepositions
    "toward", "towards", "across", "behind", "between", "through", "against",
    "capable", "powerful", "efficient", "end", "fine", "long", "full", "open",
    # Common headline nouns (not entities)
    "jobs", "model", "models", "paper", "papers", "tool", "tools", "platform",
    "startup", "startups", "company", "companies", "report", "update", "deal",
    "funding", "research", "study", "memory", "attention", "agents", "agent",
    "statement", "joint", "means", "way", "scale", "editing", "protocol",
    "benchmark", "benchmarking", "coding", "horizon", "trillion", "billion",
    "million", "sources", "context", "window", "training", "inference",
    "performance", "data", "dataset", "code", "system", "framework",
    # ML/AI terms that appear capitalized but aren't entities
    "agentic", "multimodal", "sparse", "scaling", "retrieval", "augmented",
    "fine", "grained", "pre", "post", "self", "supervised", "reinforcement",
    "generative", "diffusion", "transformer", "scientific", "foundation",
    "expression", "facial", "amnesia", "degradation", "degrade",
    "bounty", "tasks", "efficient",
}

_VERSION_PATTERN = _re_module.compile(r"[A-Za-z][\w]*-?\d[\w.-]*")  # GPT-5.4, Llama-4, H200


def _extract_entities(title: str) -> list[str]:
    """Extract named entities (proper nouns, product names, acronyms) from a title."""
    entities: list[str] = []

    # 1. Version-style tokens: GPT-5.4, Llama-4, H200, Claude-3.5
    for m in _VERSION_PATTERN.finditer(title):
        token = m.group().strip(".,;:")
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            entities.append(token)

    # 2. Named entities: capitalized words not in common list
    for word in _re_module.split(r"[\s:,;!?()\[\]]+", title):
        clean = word.strip(".,;:'\"()[]")
        if not clean or len(clean) < 2:
            continue
        if any(clean in e for e in entities):
            continue
        lower = clean.lower()
        if lower in _HEADLINE_COMMON:
            continue
        # ALL-CAPS acronyms (2-5 chars): AI, MSA, TTS, NVIDIA
        if clean.isupper() and 2 <= len(clean) <= 5:
            entities.append(clean)
        # Capitalized proper nouns
        elif clean[0].isupper() and not clean[0].isdigit():
            entities.append(clean)

    # Deduplicate preserving order
    seen: set[str] = set()
    return [e for e in entities if e not in seen and not seen.add(e)]


def _build_search_queries(entities: list[str]) -> list[str]:
    """Build 1-2 short search queries from extracted entities.

    Only uses combinations of 2+ entities to avoid overly broad single-word queries
    that return irrelevant results (e.g. "Atlassian" alone matches old Trello news).
    """
    if len(entities) < 2:
        return []
    queries = []
    # Primary: top 2-3 entities
    queries.append(" ".join(entities[:3]))
    # Secondary: first 2 entities (slightly broader, but still constrained)
    if len(entities) > 2:
        queries.append(" ".join(entities[:2]))
    return queries


def _entity_relevance(title: str, thread_title: str, entities: list[str]) -> float:
    """Enhanced relevance: base + entity boost - foreign entity penalty.

    Boost levels:
    - Version patterns (GPT-5.4, H200, Llama-4): +40 — very specific
    - Long proper nouns (≥6 chars, e.g. Atlassian, Anthropic): +20
    - Short/generic words (AI, US, EU, Act): +0 — too ambiguous

    Penalty: thread contains many entities NOT in our title → likely different topic.
    e.g. "Sam Altman AGI" vs "Sam Altman Sister Abuse Claims" → foreign=[Sister, Abuse, Claims]
    """
    base = _title_relevance(title, thread_title)
    thread_lower = thread_title.lower()
    title_lower = title.lower()

    # Boost: our entities found in thread
    # Only specific identifiers get boost — not short proper nouns (person names, etc.)
    boost = 0.0
    for ent in entities:
        if ent.lower() not in thread_lower:
            continue
        if _VERSION_PATTERN.fullmatch(ent):
            boost = max(boost, 40.0)
        elif len(ent) >= 8:
            boost = max(boost, 20.0)

    # Penalty: thread entities NOT in our title (foreign topics)
    thread_entities = _extract_entities(thread_title)
    foreign = [e for e in thread_entities if len(e) >= 4 and e.lower() not in title_lower]
    penalty = min(len(foreign) * 8, 30)

    return base + boost - penalty


async def collect_community_reactions(title: str, url: str, target_date: str | None = None) -> str:
    """Collect community reactions with ACTUAL COMMENT TEXT from HN + Reddit.

    Strategy: URL-based search first (most accurate), keyword fallback with relevance check.
    target_date: YYYY-MM-DD batch date — keyword search is limited to ±7 days of this date.

    Returns formatted reactions with real quotes, or empty string if none found.
    """
    import httpx

    # Skip URLs unlikely to have community discussions (GitHub profiles, category pages)
    if url and _re_module.match(r"https?://github\.com/[^/]+/?$", url):
        logger.debug("Skipping community search for GitHub profile URL: %s", url[:60])
        return ""

    # Extract entities for keyword fallback search
    entities = _extract_entities(title)
    search_queries = _build_search_queries(entities)
    parts: list[str] = []

    async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "0to1log:news-digest/1.0 (by /u/0to1log)"}) as client:
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

            # Phase 2: Entity-based keyword fallback with relevance check
            if not best_hit:
                import time as _time
                if target_date:
                    from datetime import datetime as _dt
                    _ref = _dt.strptime(target_date, "%Y-%m-%d")
                    _cutoff = int(_ref.timestamp()) - (7 * 86400)
                else:
                    _cutoff = int(_time.time()) - (14 * 86400)
                for sq in search_queries:
                    hn_resp = await client.get(
                        "https://hn.algolia.com/api/v1/search",
                        params={"query": sq, "tags": "story", "hitsPerPage": 5,
                                "numericFilters": f"created_at_i>{_cutoff}"},
                    )
                    if hn_resp.status_code != 200:
                        continue
                    hits = hn_resp.json().get("hits", [])
                    for h in sorted(hits, key=lambda h: h.get("points") or 0, reverse=True):
                        if (h.get("points") or 0) < 5:
                            continue
                        relevance = _entity_relevance(title, h.get("title", ""), entities)
                        if relevance >= 35:
                            best_hit = h
                            logger.debug("HN keyword match: '%s' (relevance=%.0f, pts=%d, query='%s')", h.get("title", "")[:40], relevance, h.get("points", 0), sq)
                            break
                        else:
                            logger.debug("HN keyword skip (relevance=%.0f): '%s'", relevance, h.get("title", "")[:40])
                    if best_hit:
                        break

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
                    import html as _html
                    import re as _re
                    for c in comment_resp.json().get("hits", []):
                        text = c.get("comment_text", "")
                        clean = _re.sub(r"<[^>]+>", " ", text).strip()
                        clean = _html.unescape(clean)
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
            # AI agents & applications
            "ai_agents", "aiwars",
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
            # Business/startup/policy
            "startups", "fintech", "legaltech", "europe",
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

            # Phase 2: Brave Discussions fallback (replaces Reddit keyword search)
            brave_attempted = 0
            brave_matched = False
            if not best_thread and settings.brave_api_key:
                brave_query = " ".join(_extract_entities(title)[:3]) or title[:60]
                try:
                    brave_resp = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": settings.brave_api_key},
                        params={"q": brave_query, "count": 5, "freshness": "pw"},
                    )
                    if brave_resp.status_code == 200:
                        discussions = brave_resp.json().get("discussions", {}).get("results", [])
                        for disc in discussions:
                            disc_url = disc.get("url", "")
                            disc_title = disc.get("title", "")
                            if "reddit.com" not in disc_url:
                                continue
                            _rd_match = _re_module.search(r"reddit\.com/r/(\w+)", disc_url)
                            if not _rd_match:
                                continue
                            subreddit = _rd_match.group(1).lower()
                            if subreddit not in ALLOWED_SUBREDDITS:
                                continue
                            brave_attempted += 1
                            relevance = _entity_relevance(title, disc_title, entities)
                            if relevance >= 35:
                                _perm_match = _re_module.search(r"(/r/\w+/comments/\w+)", disc_url)
                                if not _perm_match:
                                    continue
                                _permalink = _perm_match.group(1)
                                await asyncio.sleep(random.uniform(0.5, 2.0))
                                rd_fetch = await client.get(
                                    f"https://www.reddit.com{_permalink}.json",
                                    params={"limit": 5, "sort": "top", "depth": 1},
                                )
                                if rd_fetch.status_code == 200:
                                    rd_json = rd_fetch.json()
                                    if isinstance(rd_json, list) and rd_json:
                                        post_data = rd_json[0].get("data", {}).get("children", [{}])[0].get("data", {})
                                        if post_data.get("score", 0) >= 5:
                                            post_data["_brave_comments"] = rd_json
                                            best_thread = post_data
                                            brave_matched = True
                                            logger.info("Brave discussions match: r/%s '%s' (relevance=%.0f, score=%d)", subreddit, disc_title[:40], relevance, post_data.get("score", 0))
                                            break
                                else:
                                    logger.warning("Brave→Reddit fetch failed: %d for %s", rd_fetch.status_code, _permalink[:40])
                            else:
                                logger.debug("Brave discussions skip (relevance=%.0f): '%s'", relevance, disc_title[:40])
                    else:
                        logger.warning("Brave API returned %d for '%s'", brave_resp.status_code, title[:40])
                except Exception as e:
                    logger.warning("Brave discussions search failed for '%s': %s", title[:40], e)
            if brave_attempted:
                logger.info("Brave discussions: %d attempted, matched=%s for '%s'", brave_attempted, brave_matched, title[:40])

            if best_thread:
                permalink = best_thread.get("permalink", "")
                rd_title = best_thread.get("title", "")
                subreddit = best_thread.get("subreddit", "")
                score = best_thread.get("score", 0)
                num_comments = best_thread.get("num_comments", 0)
                # Fetch top comments — reuse Brave response if available
                comments_text = []
                try:
                    comment_data = best_thread.pop("_brave_comments", None)
                    if not comment_data:
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                        comment_resp = await client.get(
                            f"https://www.reddit.com{permalink}.json",
                            params={"limit": 5, "sort": "top", "depth": 1},
                        )
                        if comment_resp.status_code == 200:
                            comment_data = comment_resp.json()
                    if comment_data and isinstance(comment_data, list) and len(comment_data) > 1:
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
