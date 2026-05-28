"""LLM-based news candidate ranking agent."""
import logging
import re
from typing import Any
from urllib.parse import urlparse

from core.config import settings
from models.news_pipeline import (
    ClassifiedCandidate,
    ClassifiedGroup,
    ClassificationResult,
    CommunityInsight,
    GroupedItem,
    NewsCandidate,
    ThreadInfo,
)
from services.agents.client import (
    build_completion_kwargs,
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
    with_flex_retry,
)
from services.agents.comment_relevance import filter_relevant_comments
from services.agents.prompts_news_pipeline import (
    CLASSIFICATION_SYSTEM_PROMPT,
    COMMUNITY_SUMMARIZER_SYSTEM,
    COMMUNITY_SUMMARIZER_USER_TEMPLATE,
    MERGE_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

_TRUSTED_MEDIA_DOMAINS = (
    "reuters.com",
    "bloomberg.com",
    "techcrunch.com",
    "theverge.com",
    "cnbc.com",
    "wsj.com",
    "businessinsider.com",
    "axios.com",
    "ft.com",
    "the-decoder.com",
    "venturebeat.com",
    "semianalysis.com",
    "technologyreview.com",
    "scmp.com",
)

_BIG_TECH_TERMS = (
    "openai",
    "anthropic",
    "google",
    "deepmind",
    "microsoft",
    "meta",
    "apple",
    "amazon",
    "aws",
    "nvidia",
    "xai",
    "deepseek",
    "qwen",
    "alibaba",
)

_RESEARCH_TERMS = (
    "model",
    "llm",
    "benchmark",
    "parameter",
    "context",
    "weights",
    "open-weight",
    "open source",
    "architecture",
    "paper",
    "arxiv",
    "dataset",
    "inference",
    "training",
    "fine-tuning",
    "agent",
    "sota",
)

_BUSINESS_TERMS = (
    "raises",
    "raise",
    "raised",
    "funding",
    "valuation",
    "acquires",
    "acquisition",
    "merger",
    "merging",
    "ipo",
    "partnership",
    "launches",
    "released",
    "rolls out",
    "regulation",
    "lawsuit",
    "investigation",
    "chip",
    "revenue",
    "enterprise",
)


def _candidate_domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _candidate_text(candidate: NewsCandidate) -> str:
    return f"{candidate.title} {candidate.snippet}".lower()


def _is_probably_index_page(candidate: NewsCandidate) -> bool:
    """Filter category/homepage results that should not become a digest lead."""
    parsed = urlparse(candidate.url)
    path = parsed.path.lower().rstrip("/")
    title = candidate.title.lower()
    if path in {"", "/", "/news", "/blog", "/articles", "/category/artificial-intelligence"}:
        return True
    index_markers = (
        "newsroom | product",
        "latest articles",
        "topics/artificial-intelligence",
        "category/artificial-intelligence",
        "open source ai - fully open weights",
    )
    return any(marker in title for marker in index_markers)


def _stars(candidate: NewsCandidate) -> int:
    match = re.search(r"stars:\s*([\d,]+)", candidate.snippet, flags=re.IGNORECASE)
    return int(match.group(1).replace(",", "")) if match else 0


def _known_ai_org_repo(candidate: NewsCandidate) -> bool:
    title = candidate.title.lower()
    return any(
        title.startswith(prefix)
        for prefix in (
            "openai/",
            "anthropic-ai/",
            "facebookresearch/",
            "meta-llama/",
            "microsoft/",
            "google-deepmind/",
            "google-research/",
            "nvidia/",
            "huggingface/",
            "pytorch/",
            "tensorflow/",
            "langchain-ai/",
            "vllm-project/",
            "ollama/",
            "karpathy/",
            "unsloth/",
            "nousresearch/",
            "qualcomm/",
            "catboost/",
        )
    )


def _classify_research_subcategory(candidate: NewsCandidate) -> str:
    text = _candidate_text(candidate)
    domain = _candidate_domain(candidate.url)
    kind = (candidate.source_kind or "").lower()
    if kind == "paper" or "arxiv.org" in domain:
        return "papers"
    if kind == "official_repo" or "github.com" in domain:
        return "open_source"
    if any(term in text for term in ("model", "llm", "benchmark", "parameter", "weights", "context")):
        return "llm_models"
    return "papers"


def _classify_business_subcategory(candidate: NewsCandidate) -> str:
    text = _candidate_text(candidate)
    if any(term in text for term in ("funding", "raises", "raise", "raised", "valuation", "acquires", "acquisition", "merger", "merging", "ipo", "regulation", "lawsuit", "investigation", "chip")):
        return "industry"
    if any(term in text for term in _BIG_TECH_TERMS):
        return "big_tech"
    return "new_tools"


def _research_score(candidate: NewsCandidate) -> int:
    if _is_probably_index_page(candidate):
        return -100
    text = _candidate_text(candidate)
    domain = _candidate_domain(candidate.url)
    kind = (candidate.source_kind or "").lower()
    tier = (candidate.source_tier or "").lower()
    confidence = (candidate.source_confidence or "").lower()

    score = 0
    if tier == "primary":
        score += 4
    if confidence == "high":
        score += 2
    if kind == "paper" or "arxiv.org" in domain:
        score += 9
    elif kind == "official_repo" or "github.com" in domain:
        score += 5
        if _known_ai_org_repo(candidate) or _stars(candidate) >= 1000:
            score += 4
    elif kind in {"official_site", "official_platform_asset", "research_primary"}:
        score += 5

    score += sum(1 for term in _RESEARCH_TERMS if term in text)
    if re.search(r"\b\d+(?:\.\d+)?\s*(b|m|k|%|tokens?|context|parameters?)\b", text):
        score += 2
    if kind in {"media", "analysis"} and score < 7:
        score -= 3
    return score


def _business_score(candidate: NewsCandidate) -> int:
    if _is_probably_index_page(candidate):
        return -100
    text = _candidate_text(candidate)
    domain = _candidate_domain(candidate.url)
    kind = (candidate.source_kind or "").lower()
    confidence = (candidate.source_confidence or "").lower()
    tier = (candidate.source_tier or "").lower()

    score = 0
    if any(domain.endswith(d) for d in _TRUSTED_MEDIA_DOMAINS):
        score += 5
    if kind in {"media", "official_site"}:
        score += 3
    if confidence == "high":
        score += 2
    if tier == "primary" and kind == "official_site":
        score += 2
    score += sum(1 for term in _BUSINESS_TERMS if term in text)
    if any(term in text for term in _BIG_TECH_TERMS):
        score += 2
    if re.search(r"\$[\d,.]+\s*(billion|million|bn|m|b)?|\b\d+(?:\.\d+)?\s*(billion|million|%)\b", text):
        score += 2
    if kind in {"paper", "official_repo"} and score < 7:
        score -= 3
    return score


def _passes_category_rescue_gate(candidate: NewsCandidate, category: str, score: int) -> bool:
    """Conservative source gate for deterministic category-starvation rescue."""
    if score < 6:
        return False

    domain = _candidate_domain(candidate.url)
    kind = (candidate.source_kind or "").lower()
    tier = (candidate.source_tier or "").lower()
    confidence = (candidate.source_confidence or "").lower()
    trusted_media = any(domain.endswith(d) for d in _TRUSTED_MEDIA_DOMAINS)

    if category == "business":
        if kind in {"paper", "official_repo"}:
            return False
        return (
            trusted_media
            or kind == "official_site"
            or (kind == "media" and confidence in {"high", "medium"})
            or (tier == "primary" and confidence in {"high", "medium"})
        )

    if category == "research":
        if kind in {"paper", "official_repo", "official_site", "research_primary"}:
            return True
        return trusted_media and confidence in {"high", "medium"}

    return False


def build_category_rescue_picks(
    candidates: list[NewsCandidate],
    category: str,
    *,
    limit: int = 3,
) -> tuple[list[ClassifiedCandidate], dict[str, Any]]:
    """Return conservative rule-selected picks for a starved category.

    This is narrower than `build_emergency_classification`: it fills only the
    missing category after the normal LLM classifier had a chance to select
    stories. It exists to prevent one-sided digests when the candidate pool has
    credible category-specific items but prompt-level dedup or classifier bias
    returns zero picks for that category.
    """
    if category not in {"research", "business"}:
        raise ValueError("category must be 'research' or 'business'")

    scorer = _research_score if category == "research" else _business_score
    subcategory_for = (
        _classify_research_subcategory
        if category == "research"
        else _classify_business_subcategory
    )
    scored = sorted(
        ((candidate, scorer(candidate)) for candidate in candidates),
        key=lambda item: (-item[1], item[0].title.lower()),
    )
    eligible = [
        (candidate, score)
        for candidate, score in scored
        if _passes_category_rescue_gate(candidate, category, score)
    ]

    picks = [
        _build_emergency_pick(
            candidate,
            category,
            subcategory_for(candidate),
            score,
        )
        for candidate, score in eligible[:limit]
    ]
    meta = {
        "mode": "category_starvation_rescue",
        "category": category,
        "candidate_count": len(candidates),
        "eligible": len(eligible),
        "selected": len(picks),
        "selected_candidates": [
            {
                "title": pick.title,
                "url": pick.url,
                "subcategory": pick.subcategory,
                "source": pick.source,
            }
            for pick in picks
        ],
    }
    return picks, meta


def _format_classification_candidate(index: int, candidate: NewsCandidate) -> str:
    return (
        f"[{index}] {candidate.title}\n"
        f"    URL: {candidate.url}\n"
        f"    Source: {candidate.source}\n"
        f"    Source tier: {candidate.source_tier or 'unknown'}\n"
        f"    Source kind: {candidate.source_kind or 'unknown'}\n"
        f"    Source confidence: {candidate.source_confidence or 'unknown'}\n"
        f"    Snippet: {candidate.snippet[:300]}"
    )


def _build_emergency_pick(
    candidate: NewsCandidate,
    category: str,
    subcategory: str,
    score: int,
) -> ClassifiedCandidate:
    return ClassifiedCandidate(
        title=candidate.title,
        url=candidate.url,
        snippet=candidate.snippet,
        source=candidate.source,
        category=category,
        subcategory=subcategory,
        reason=(
            "Emergency fallback selected this candidate after the LLM classifier "
            f"returned zero picks; rule score={score}, "
            f"source={candidate.source_kind or 'unknown'}/{candidate.source_tier or 'unknown'}."
        ),
    )


def build_emergency_classification(
    candidates: list[NewsCandidate],
    *,
    per_category_limit: int = 4,
) -> tuple[ClassificationResult, dict[str, Any]]:
    """Deterministically rescue a non-empty daily draft when LLM classify returns 0.

    This is deliberately conservative: it favors primary/official/reputable
    sources and concrete research/business signals. It is not a replacement for
    the LLM classifier; it is an availability safety net before quality gates.
    """
    result = ClassificationResult()
    used_urls: set[str] = set()

    research_scored = sorted(
        ((c, _research_score(c)) for c in candidates),
        key=lambda item: (-item[1], item[0].title.lower()),
    )
    business_scored = sorted(
        ((c, _business_score(c)) for c in candidates),
        key=lambda item: (-item[1], item[0].title.lower()),
    )

    research_subcategories = {
        _classify_research_subcategory(candidate)
        for candidate, score in research_scored
        if score >= 6
    }
    research_caps = {"papers": 2} if (research_subcategories - {"papers"}) else {}
    research_counts: dict[str, int] = {}
    for candidate, score in research_scored:
        if score < 6 or candidate.url in used_urls:
            continue
        subcategory = _classify_research_subcategory(candidate)
        if research_counts.get(subcategory, 0) >= research_caps.get(subcategory, per_category_limit):
            continue
        result.research_picks.append(
            _build_emergency_pick(
                candidate,
                "research",
                subcategory,
                score,
            )
        )
        research_counts[subcategory] = research_counts.get(subcategory, 0) + 1
        used_urls.add(candidate.url)
        if len(result.research_picks) >= per_category_limit:
            break

    for candidate, score in business_scored:
        if score < 6 or candidate.url in used_urls:
            continue
        result.business_picks.append(
            _build_emergency_pick(
                candidate,
                "business",
                _classify_business_subcategory(candidate),
                score,
            )
        )
        used_urls.add(candidate.url)
        if len(result.business_picks) >= per_category_limit:
            break

    meta = {
        "mode": "classification_zero_emergency",
        "candidate_count": len(candidates),
        "research_selected": len(result.research_picks),
        "business_selected": len(result.business_picks),
        "research_candidates": [
            {
                "title": pick.title,
                "url": pick.url,
                "subcategory": pick.subcategory,
                "source": pick.source,
            }
            for pick in result.research_picks
        ],
        "business_candidates": [
            {
                "title": pick.title,
                "url": pick.url,
                "subcategory": pick.subcategory,
                "source": pick.source,
            }
            for pick in result.business_picks
        ],
    }
    result.classification_debug = {
        "emergency_fallback_used": True,
        "emergency_meta": meta,
    }
    return result, meta


def _has_hangul(text: str | None) -> bool:
    """Return True if the string contains at least one Hangul syllable (U+AC00-U+D7AF)."""
    if not text:
        return False
    return any('가' <= c <= '힯' for c in text)


async def _retranslate_quotes_ko_async(quotes_en: list[str]) -> tuple[list[str], dict[str, Any]]:
    """Batch-translate EN community quotes to KO via gpt-5-mini.

    Fallback for summarize_community when an LLM-returned `quotes_ko` entry
    lacks Hangul (English leak into the Korean field). Called with only the
    EN quotes whose paired KO translation failed the Hangul check; returns
    Korean translations in the same order. On any failure returns ([], {}).
    """
    if not quotes_en:
        return [], {}

    import json as _json
    client = get_openai_client()
    model = settings.openai_model_light

    system_prompt = (
        "Translate each English community forum quote into natural Korean. "
        "Preserve the speaker's meaning and tone; do not abridge or editorialize. "
        f"Return JSON only: {{\"quotes_ko\": [\"번역1\", ...]}} — exactly "
        f"{len(quotes_en)} items in the same order as input."
    )
    user_prompt = _json.dumps({"quotes": quotes_en}, ensure_ascii=False)

    try:
        response = await client.chat.completions.create(
            **build_completion_kwargs(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=800,
                service_tier="flex",
            )
        )
    except Exception as e:
        logger.warning("quotes_ko retranslate LLM call failed: %s", e)
        return [], {}

    raw = response.choices[0].message.content or ""
    try:
        data = parse_ai_json(raw, "quotes_ko_retranslate")
    except Exception as e:
        logger.warning("quotes_ko retranslate JSON parse failed: %s", e)
        return [], {}
    if not isinstance(data, dict):
        return [], {}
    translated = data.get("quotes_ko") or []
    if not isinstance(translated, list) or len(translated) != len(quotes_en):
        logger.warning(
            "quotes_ko retranslate returned %d items, expected %d",
            len(translated) if isinstance(translated, list) else 0,
            len(quotes_en),
        )
        return [], {}
    usage = extract_usage_metrics(response, model, requested_service_tier="flex")
    return [str(q) if isinstance(q, str) else "" for q in translated], usage


async def classify_candidates(
    candidates: list[NewsCandidate],
    recent_headlines: list[str] | None = None,
    recent_headlines_by_category: dict[str, list[str]] | None = None,
) -> tuple[ClassificationResult, dict[str, Any], str]:
    """Classify news candidates into research/business subcategories.

    Returns (result, usage, user_prompt). The user_prompt is returned so callers
    can log the EXACT input the LLM saw — including the dedup block — for debugging.

    recent_headlines: legacy flat titles published in the last 3 days.
    recent_headlines_by_category: category-grouped recent titles. Prefer this
    when available so business/research dedup does not over-block each other.
    """
    if not candidates:
        logger.info("No candidates to classify")
        return ClassificationResult(), {}, ""

    candidate_lines = []
    for i, c in enumerate(candidates):
        candidate_lines.append(_format_classification_candidate(i + 1, c))
    user_prompt = "\n\n".join(candidate_lines)

    # Add recent headlines for event dedup. Label MUST match the system prompt rule
    # so the LLM connects the rule to the data block.
    if recent_headlines_by_category and any(recent_headlines_by_category.values()):
        research_block = "\n".join(f"- {h}" for h in recent_headlines_by_category.get("research", []) if h)
        business_block = "\n".join(f"- {h}" for h in recent_headlines_by_category.get("business", []) if h)
        user_prompt += (
            "\n\n---\n\n"
            "ALREADY COVERED HEADLINES BY CATEGORY (last 3 days, both published and draft):\n"
            "Research headlines:\n"
            f"{research_block or '- (none)'}\n\n"
            "Business headlines:\n"
            f"{business_block or '- (none)'}\n\n"
            "For same-category candidates, apply strict same-event dedup. "
            "For cross-category candidates, skip only when the same company and the same "
            "product/announcement are clearly repeated. Do not reject a business story "
            "merely because a research headline mentions the same company, or vice versa."
        )
    elif recent_headlines:
        headlines_block = "\n".join(f"- {h}" for h in recent_headlines)
        user_prompt += (
            "\n\n---\n\n"
            "ALREADY COVERED HEADLINES (last 3 days, both published and draft):\n"
            f"{headlines_block}\n\n"
            "DO NOT select any candidate above that covers the SAME core event "
            "(same company + same product/announcement) as ANY headline in this list. "
            "Variations like 'X hits app charts', 'X gets benchmark Y', 'X integration with Z' "
            "are STILL the same core event and MUST be skipped. The only acceptable repeat "
            "is a structurally different action verb in the source itself "
            "(e.g., source explicitly says 'acquires', 'sues', 'shuts down')."
        )

    client = get_openai_client()
    model = settings.openai_model_light  # gpt-5-mini (kept as reminder: light = mini tier, not nano)
    usage: dict[str, Any] = {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                **build_completion_kwargs(
                    model=model,
                    messages=[
                        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=4096,
                    response_format={"type": "json_object"},
                    service_tier="flex",
                    prompt_cache_key="classify-candidates",
                )
            )
            raw = response.choices[0].message.content or ""
            data = parse_ai_json(raw, "Classification")
            usage = extract_usage_metrics(response, model, requested_service_tier="flex")
            break
        except Exception as e:
            logger.warning("Classification attempt %d failed: %s", attempt + 1, e)
            if attempt == MAX_RETRIES:
                logger.error("Classification failed after %d retries", MAX_RETRIES + 1)
                return ClassificationResult(), usage, user_prompt
            continue

    url_map = {c.url: c for c in candidates}
    result = ClassificationResult()
    invalid_url_picks: list[dict[str, str]] = []

    for category in ("research", "business"):
        picks = data.get(category, [])
        classified = []
        for pick in picks:
            # Support both flat format (url) and grouped format fallback (items)
            url = pick.get("url", "")
            if not url and pick.get("items"):
                # Grouped format fallback — take first item
                url = pick["items"][0].get("url", "") if pick["items"] else ""
            candidate = url_map.get(url)
            if not candidate:
                logger.warning("Classified URL not in candidates: %s", url)
                invalid_url_picks.append({
                    "category": category,
                    "url": url,
                    "reason": "URL not found in candidate pool",
                })
                continue
            classified.append(ClassifiedCandidate(
                title=candidate.title,
                url=candidate.url,
                snippet=candidate.snippet,
                source=candidate.source,
                category=category,
                subcategory=pick.get("subcategory", ""),
                reason=pick.get("reason", ""),
            ))
        setattr(result, f"{category}_picks", classified[:8])

    result.classification_debug = {
        "raw_response": raw[:4000],
        "raw_picks": data,
        "invalid_url_picks": invalid_url_picks,
    }

    # Log cross-category overlap
    if result.research_picks and result.business_picks:
        research_urls = {c.url for c in result.research_picks}
        business_urls = {c.url for c in result.business_picks}
        overlap = research_urls & business_urls
        if overlap:
            logger.info("Cross-category overlap: %d URL(s) in both research and business", len(overlap))

    logger.info(
        "Classification complete: %d research picks, %d business picks",
        len(result.research_picks), len(result.business_picks),
    )
    if not result.business_picks:
        logger.warning("No business articles classified — business digest will be skipped")
    if not result.research_picks:
        logger.warning("No research articles classified — research digest will be skipped")
    return result, usage, user_prompt


async def merge_classified(
    classification: ClassificationResult,
    candidates: list[NewsCandidate],
) -> tuple[ClassificationResult, dict[str, Any]]:
    """Merge classified picks with matching candidates from the full pool.

    For each selected article, finds other candidates covering the same event
    and groups them into ClassifiedGroup.
    """
    all_picks = classification.research_picks + classification.business_picks
    if not all_picks:
        return classification, {}

    # Format selected items
    selected_lines = []
    for i, pick in enumerate(all_picks):
        selected_lines.append(
            f"[S{i+1}] [{pick.category}/{pick.subcategory}] {pick.title}\n"
            f"    URL: {pick.url}\n"
            f"    Reason: {pick.reason}"
        )

    # Format all candidates (title + URL only, for matching)
    candidate_lines = []
    for i, c in enumerate(candidates):
        candidate_lines.append(f"[{i+1}] {c.title}\n    URL: {c.url}")

    user_content = (
        "## Selected Articles (already chosen as important)\n"
        + "\n\n".join(selected_lines)
        + "\n\n## All Candidates\n"
        + "\n\n".join(candidate_lines)
        + "\n\nGroup same-event articles together. Return JSON."
    )

    client = get_openai_client()
    model = settings.openai_model_light
    usage: dict[str, Any] = {}
    data = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                **build_completion_kwargs(
                    model=model,
                    messages=[
                        {"role": "system", "content": MERGE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    max_tokens=4096,
                    response_format={"type": "json_object"},
                    service_tier="flex",
                    prompt_cache_key="merge-classified",
                )
            )
            data = parse_ai_json(response.choices[0].message.content, "Merge")
            usage = extract_usage_metrics(response, model, requested_service_tier="flex")
            break
        except Exception as e:
            logger.warning("Merge attempt %d failed: %s", attempt + 1, e)
            if attempt == MAX_RETRIES:
                logger.error("Merge failed after %d retries — falling back to 1-item groups", MAX_RETRIES + 1)

    if data is None:
        # Fallback: each pick becomes a single-item group
        for category in ("research", "business"):
            picks = getattr(classification, f"{category}_picks")
            groups = [
                ClassifiedGroup(
                    group_title=pick.title,
                    items=[GroupedItem(url=pick.url, title=pick.title)],
                    category=category,
                    subcategory=pick.subcategory,
                    reason=pick.reason,
                )
                for pick in picks
            ]
            setattr(classification, category, groups)
        return classification, usage

    # Parse merge output into ClassifiedGroup
    url_map = {c.url: c for c in candidates}

    for category in ("research", "business"):
        groups_raw = data.get(category, [])
        groups: list[ClassifiedGroup] = []

        for group_data in groups_raw:
            items_raw = group_data.get("items", [])
            grouped_items: list[GroupedItem] = []
            seen_urls: set[str] = set()
            for item_data in items_raw:
                # Support both {"url": "..."} dict and plain "url" string
                if isinstance(item_data, str):
                    url = item_data
                else:
                    url = item_data.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidate = url_map.get(url)
                if candidate:
                    grouped_items.append(GroupedItem(url=url, title=candidate.title))
            if grouped_items:
                groups.append(ClassifiedGroup(
                    group_title=group_data.get("group_title", grouped_items[0].title),
                    items=grouped_items,
                    category=category,
                    subcategory=group_data.get("subcategory", ""),
                    reason=group_data.get("reason", ""),
                ))

        # Fallback: if merge returned nothing, convert picks to 1-item groups
        if not groups:
            picks = getattr(classification, f"{category}_picks")
            groups = [
                ClassifiedGroup(
                    group_title=pick.title,
                    items=[GroupedItem(url=pick.url, title=pick.title)],
                    category=category,
                    subcategory=pick.subcategory,
                    reason=pick.reason,
                )
                for pick in picks
            ]
        setattr(classification, category, groups[:5])

    total_items_r = sum(len(g.items) for g in classification.research)
    total_items_b = sum(len(g.items) for g in classification.business)
    logger.info(
        "Merge complete: %d research groups (%d items), %d business groups (%d items)",
        len(classification.research), total_items_r,
        len(classification.business), total_items_b,
    )
    return classification, usage


async def rank_classified(
    groups: list[ClassifiedGroup],
    category: str,
    community_map: dict[str, str] | None = None,
) -> tuple[list[ClassifiedGroup], dict[str, Any]]:
    """Rank classified groups: assign [LEAD]/[SUPPORTING] role.

    Returns (reordered groups with role in reason field, usage metrics).
    Lead groups come first, then supporting in importance order.
    """
    if len(groups) <= 1:
        if groups:
            groups[0].reason = f"[LEAD] {groups[0].reason}"
        return groups, {}

    from services.agents.prompts_news_pipeline import RANKING_SYSTEM_PROMPT_V2

    community_map = community_map or {}

    item_lines = []
    for i, group in enumerate(groups):
        # Collect community engagement from any URL in the group
        engagement = "no community data"
        for item in group.items:
            community = community_map.get(item.url, "")
            if community:
                first_line = community.split("\n")[0].strip()
                if first_line:
                    engagement = first_line
                    break
        item_lines.append(
            f"[{i+1}] {group.group_title} ({len(group.items)} source(s))\n"
            f"    Subcategory: {group.subcategory}\n"
            f"    Community: {engagement}"
        )

    prompt = RANKING_SYSTEM_PROMPT_V2.format(
        category=category,
        count=len(groups),
        items="\n".join(item_lines),
    )

    client = get_openai_client()
    model = settings.openai_model_light
    data = None
    usage: dict[str, Any] = {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                **build_completion_kwargs(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": "Rank these items."},
                    ],
                    max_tokens=256,
                    response_format={"type": "json_object"},
                    service_tier="flex",
                    prompt_cache_key=f"rank-{category}",
                )
            )
            data = parse_ai_json(response.choices[0].message.content, f"Ranking-{category}")
            usage = extract_usage_metrics(response, model, requested_service_tier="flex")
            break
        except Exception as e:
            logger.warning("Ranking attempt %d for %s failed: %s", attempt + 1, category, e)
            if attempt == MAX_RETRIES:
                logger.error("Ranking failed for %s after %d retries — falling back", category, MAX_RETRIES + 1)
                groups[0].reason = f"[LEAD] {groups[0].reason}"
                for group in groups[1:]:
                    group.reason = f"[SUPPORTING] {group.reason}"
                return groups, {}

    # Match lead by index (LLM returns [1]-based indices or URLs)
    omit_indices = set(_resolve_ranking_refs(data.get("omit", []), groups))
    lead_indices = [
        idx for idx in _resolve_ranking_refs(data.get("lead", []), groups)
        if idx not in omit_indices
    ]
    supporting_indices = [
        idx for idx in _resolve_ranking_refs(data.get("supporting", []), groups)
        if idx not in omit_indices and idx not in lead_indices
    ]

    # If the model did not enumerate supporting stories, keep all non-omitted
    # non-leads in classifier order. If it did enumerate them, append any
    # accidentally unmentioned non-omitted groups so omission is only honored
    # through the explicit `omit` field.
    for idx in range(len(groups)):
        if idx in omit_indices or idx in lead_indices or idx in supporting_indices:
            continue
        supporting_indices.append(idx)

    leads = []
    supports = []
    for idx in lead_indices:
        group = groups[idx]
        group.reason = f"[LEAD] {_strip_rank_tag(group.reason)}".strip()
        leads.append(group)
    for idx in supporting_indices:
        group = groups[idx]
        group.reason = f"[SUPPORTING] {_strip_rank_tag(group.reason)}".strip()
        supports.append(group)

    # If no leads matched, fallback: first group is lead
    if not leads and groups:
        fallback = next((idx for idx in range(len(groups)) if idx not in omit_indices), 0)
        groups[fallback].reason = f"[LEAD] {_strip_rank_tag(groups[fallback].reason)}".strip()
        leads = [groups[fallback]]
        supports = []
        for idx, group in enumerate(groups):
            if idx == fallback or idx in omit_indices:
                continue
            group.reason = f"[SUPPORTING] {_strip_rank_tag(group.reason)}".strip()
            supports.append(group)

    logger.info(
        "Ranking %s: lead=%d, supporting=%d, omitted=%d",
        category, len(leads), len(supports), len(omit_indices),
    )
    return leads + supports, usage


def _strip_rank_tag(reason: str) -> str:
    return re.sub(r"^\s*\[(?:LEAD|SUPPORTING)\]\s*", "", reason or "").strip()


def _ranking_ref_value(ref: Any) -> Any:
    if isinstance(ref, dict):
        return (
            ref.get("url")
            or ref.get("group_title")
            or ref.get("title")
            or ref.get("id")
        )
    return ref


def _resolve_ranking_refs(refs: Any, groups: list[ClassifiedGroup]) -> list[int]:
    """Resolve ranker references to group indexes, preserving ranker order."""
    if not isinstance(refs, list):
        return []

    resolved: list[int] = []
    seen: set[int] = set()
    for raw_ref in refs:
        ref = _ranking_ref_value(raw_ref)
        idx: int | None = None
        if isinstance(ref, int):
            candidate = ref - 1
            if 0 <= candidate < len(groups):
                idx = candidate
        elif isinstance(ref, str):
            ref_norm = ref.strip()
            for group_idx, group in enumerate(groups):
                if (
                    ref_norm in group.urls
                    or ref_norm == group.primary_url
                    or ref_norm == group.group_title
                ):
                    idx = group_idx
                    break
        if idx is None or idx in seen:
            continue
        seen.add(idx)
        resolved.append(idx)
    return resolved


# ---------------------------------------------------------------------------
# Community Summarizer
# ---------------------------------------------------------------------------

# --- Community source header regexes ---
# The `|url=<thread_url>` token is optional for back-compat with checkpoints
# predating the URL-plumbing change. `\S+?` keeps the URL tight (no spaces).
_HN_HEADER_RE = re.compile(
    r"\[Hacker News(?:\|url=(\S+?))?\]\s*.*?\|\s*([\d,]+)\s*points?\s*\|\s*([\d,]+)\s*comments?"
)
_REDDIT_HEADER_RE = re.compile(
    r"\[Reddit\s+r/(\S+?)(?:\|url=(\S+?))?\]\s*.*?\|\s*([\d,]+)\s*upvotes?\s*\|\s*([\d,]+)\s*comments?"
)


def _parse_source_meta(raw_text: str) -> tuple[str, str | None, str | None]:
    """Extract (source_label, hn_url, reddit_url) from raw community text.

    Deterministic \u2014 no LLM. URL captures are optional (None when the blob
    predates the URL-plumbing change in news_collection).
    """
    parts: list[str] = []
    hn_url: str | None = None
    reddit_url: str | None = None

    hn = _HN_HEADER_RE.search(raw_text)
    if hn:
        hn_url = hn.group(1) or None  # group 1 is the URL (optional)
        points = hn.group(2).replace(",", "")
        comments = hn.group(3).replace(",", "")
        parts.append(f"Hacker News {points}\u2191 \u00b7 {comments} comments")

    rd = _REDDIT_HEADER_RE.search(raw_text)
    if rd:
        sub = rd.group(1)
        reddit_url = rd.group(2) or None  # group 2 is the URL (optional)
        upvotes = rd.group(3).replace(",", "")
        parts.append(f"r/{sub} ({upvotes}\u2191)")

    label = " \u00b7 ".join(parts) if parts else ""
    return label, hn_url, reddit_url


# Header regexes for parsing community_map blob into per-platform sections.
# news_collection embeds [Hacker News|url=<url>] / [Reddit r/<sub>|url=<url>]
# tokens at the start of each thread block.
_HN_SECTION_HEADER_RE = re.compile(
    r"\[Hacker News\|url=(?P<url>[^\]]+)\]\s*(?P<title>[^\n|]*?)\s*\|\s*(?P<upvotes>\d[\d,]*)\s*points?\s*\|\s*(?P<comments>\d[\d,]*)\s*comments?",
)
_REDDIT_SECTION_HEADER_RE = re.compile(
    r"\[Reddit\s+r/(?P<sub>[^\|\]]+)\|url=(?P<url>[^\]]+)\]\s*(?P<title>[^\n|]*?)\s*\|\s*(?P<upvotes>\d[\d,]*)\s*upvotes?\s*\|\s*(?P<comments>\d[\d,]*)\s*comments?",
)
_COMMENT_LINE_RE = re.compile(r'^>\s*"(.*)"$', re.MULTILINE)

_THREAD_TITLE_STOPWORDS = {
    "about", "across", "agent", "agents", "and", "are", "article", "best",
    "can", "code", "data", "dataset", "english", "finding", "for", "from",
    "how", "language", "learning", "llm", "llms", "model", "models",
    "myriads", "new", "paper", "research", "small", "speak", "still",
    "task", "that", "the", "this", "tool", "tools", "with", "your",
}
_KNOWN_TOPIC_ENTITIES = {
    "activepieces",
    "anthropic",
    "apple",
    "amazon",
    "deepmind",
    "google",
    "meta",
    "microsoft",
    "nvidia",
    "openai",
    "reddit",
    "tomoro",
}


def _distinctive_topic_entities(text: str) -> set[str]:
    entities: set[str] = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9.+_/-]{1,}", text or ""):
        token = raw.strip(".,;:'\"()[]{}")
        lower = token.lower().strip("._-/")
        if not lower or lower in _THREAD_TITLE_STOPWORDS:
            continue
        has_letter = any(ch.isalpha() for ch in token)
        has_digit = any(ch.isdigit() for ch in token)
        has_internal_upper = any(ch.isupper() for ch in token[1:])
        is_acronym = token.isupper() and 2 <= len(token) <= 8
        is_repoish = "/" in token or "_" in token
        if (
            lower in _KNOWN_TOPIC_ENTITIES
            or (has_letter and has_digit)
            or has_internal_upper
            or is_acronym
            or is_repoish
        ):
            entities.add(lower)
    return entities


def _community_thread_title_matches_article(article_title: str, thread_title: str) -> bool:
    """Obvious-mismatch guard before LLM comment filtering.

    Do not require title overlap. Only fail closed when both titles expose
    distinctive named topics and those topics are disjoint. Generic or ambiguous
    thread titles still go through the comment relevance filter.
    """
    if not thread_title:
        return True

    article_entities = _distinctive_topic_entities(article_title)
    thread_entities = _distinctive_topic_entities(thread_title)
    if article_entities and thread_entities and article_entities.isdisjoint(thread_entities):
        return False

    return True


def _split_blob_by_platform(blob: str) -> list[dict]:
    """Split a community_map blob into per-platform sections.

    Returns list of dicts: [{platform, url, upvotes, comments,
    comments_text: list[str], subreddit?}].
    Each section's `comments_text` is the list of raw comments scraped for that
    platform (extracted via the > "..." line pattern that news_collection emits).
    """
    sections: list[dict] = []
    # Find all section header positions, then slice between them
    headers: list[tuple[int, dict]] = []
    for m in _HN_SECTION_HEADER_RE.finditer(blob):
        headers.append((m.start(), {
            "platform": "hackernews",
            "url": m.group("url"),
            "title": (m.group("title") or "").strip(),
            "upvotes": int(m.group("upvotes").replace(",", "")),
            "comments": int(m.group("comments").replace(",", "")),
        }))
    for m in _REDDIT_SECTION_HEADER_RE.finditer(blob):
        headers.append((m.start(), {
            "platform": "reddit",
            "url": m.group("url"),
            "title": (m.group("title") or "").strip(),
            "subreddit": m.group("sub"),
            "upvotes": int(m.group("upvotes").replace(",", "")),
            "comments": int(m.group("comments").replace(",", "")),
        }))
    headers.sort(key=lambda h: h[0])

    for i, (start, meta) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(blob)
        block = blob[start:end]
        meta["comments_text"] = _COMMENT_LINE_RE.findall(block)
        sections.append(meta)
    return sections


async def summarize_community(
    community_map: dict[str, str],
    groups: list,
) -> tuple[dict[str, CommunityInsight], dict[str, Any]]:
    """Per-platform community summarization.

    For each group's blob, split into platform sections (HN, Reddit, both).
    For each section:
      1. Filter top-voted candidates via gpt-5-nano relevance filter
         (filter_relevant_comments). Apr 25 DeepSeek case: returns [] when
         all top-voted are off-topic -- we skip the summarizer call entirely
         and record the thread with sentiment=None.
      2. If the filter returns comments, call the summarizer LLM with ONLY
         that platform's filtered comments. Build a ThreadInfo from the
         summarizer's output.
    Aggregate ThreadInfo records into CommunityInsight(threads=[...]).
    Quote provenance preserved by construction -- cross-platform never mixes
    in summarizer input.
    """
    result: dict[str, CommunityInsight] = {}
    cumulative_usage: dict[str, Any] = {}

    if not community_map:
        return result, cumulative_usage

    client = get_openai_client()
    model = settings.openai_model_light

    for group in groups:
        primary_url = group.primary_url
        blob = community_map.get(primary_url)
        if not blob:
            continue

        sections = _split_blob_by_platform(blob)
        if not sections:
            continue

        article_title = group.group_title
        article_excerpt = ""  # could be enriched from group.items[0] if available

        threads: list[ThreadInfo] = []
        for section in sections:
            thread_title = section.get("title", "")
            if not _community_thread_title_matches_article(article_title, thread_title):
                logger.info(
                    "Dropping community thread title mismatch: article='%s' thread='%s'",
                    article_title[:80], thread_title[:80],
                )
                threads.append(ThreadInfo(
                    platform=section["platform"],
                    url=section["url"],
                    title=thread_title,
                    subreddit=section.get("subreddit"),
                    upvotes=section["upvotes"],
                    comments=section["comments"],
                    sentiment=None,
                    quotes=[],
                    quotes_ko=[],
                    key_point=None,
                ))
                continue

            # ----- Stage 1: relevance filter -----
            filtered, filter_usage = await filter_relevant_comments(
                section["comments_text"],
                article_title=article_title,
                article_excerpt=article_excerpt,
                max_pick=10,
            )
            cumulative_usage = merge_usage_metrics(cumulative_usage, filter_usage)

            if not filtered:
                # Filter judged everything off-topic (R3 fail-CLOSED) OR
                # no comments at all. Skip summarizer; record empty thread.
                threads.append(ThreadInfo(
                    platform=section["platform"],
                    url=section["url"],
                    title=thread_title,
                    subreddit=section.get("subreddit"),
                    upvotes=section["upvotes"],
                    comments=section["comments"],
                    sentiment=None,
                    quotes=[],
                    quotes_ko=[],
                    key_point=None,
                ))
                continue

            # ----- Stage 2: per-platform summarizer call -----
            comments_blob = "\n".join(f'> "{c}"' for c in filtered)
            user_content = COMMUNITY_SUMMARIZER_USER_TEMPLATE.format(
                groups_text=(
                    f"### Group 0 \u2014 {article_title}\n"
                    f"Original article: {article_title}\n"
                    f"Platform: {section['platform']}\n"
                    f"{comments_blob}"
                ),
            )

            kwargs = build_completion_kwargs(
                model=model,
                messages=[
                    {"role": "system", "content": COMMUNITY_SUMMARIZER_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=2000,
                response_format={"type": "json_object"},
                service_tier="flex",
                prompt_cache_key=f"community-summarize-{section['platform']}",
            )

            try:
                response = await with_flex_retry(
                    lambda: client.chat.completions.create(**kwargs),
                )
                raw_output = response.choices[0].message.content or ""
                data = parse_ai_json(raw_output, f"summarize-{section['platform']}")
                usage = extract_usage_metrics(response, model, requested_service_tier="flex")
                cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
            except Exception as e:
                logger.warning("Summarizer failed for %s: %s", section["platform"], e)
                threads.append(ThreadInfo(
                    platform=section["platform"],
                    url=section["url"],
                    title=thread_title,
                    subreddit=section.get("subreddit"),
                    upvotes=section["upvotes"],
                    comments=section["comments"],
                    sentiment=None,
                    quotes=[],
                    quotes_ko=[],
                    key_point=None,
                ))
                continue

            # Parse summarizer output (single-group shape)
            llm_groups = (data or {}).get("groups", {})
            llm_data = llm_groups.get("group_0", {}) if isinstance(llm_groups, dict) else {}
            if not isinstance(llm_data, dict):
                llm_data = {}

            threads.append(ThreadInfo(
                platform=section["platform"],
                url=section["url"],
                title=thread_title,
                subreddit=section.get("subreddit"),
                upvotes=section["upvotes"],
                comments=section["comments"],
                sentiment=llm_data.get("sentiment"),
                quotes=list(llm_data.get("quotes") or []),
                quotes_ko=list(llm_data.get("quotes_ko") or []),
                key_point=llm_data.get("key_point"),
            ))

        if threads:
            result[primary_url] = CommunityInsight(threads=threads)

    logger.info(
        "Community summarizer: %d/%d groups summarized",
        len(result), len(groups),
    )
    return result, cumulative_usage
