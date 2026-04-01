"""LLM-based news candidate ranking agent."""
import logging
import re
from typing import Any

from core.config import settings
from models.news_pipeline import (
    ClassifiedCandidate,
    ClassifiedGroup,
    ClassificationResult,
    CommunityInsight,
    GroupedItem,
    NewsCandidate,
    RankedCandidate,
    RankingResult,
)
from services.agents.client import build_completion_kwargs, extract_usage_metrics, get_openai_client, parse_ai_json
from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT, COMMUNITY_SUMMARIZER_PROMPT, MERGE_SYSTEM_PROMPT, SELECTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


async def rank_candidates(
    candidates: list[NewsCandidate],
) -> tuple[RankingResult, dict[str, Any]]:
    """Rank news candidates using LLM and return best research + business picks."""
    if not candidates:
        logger.info("No candidates to rank")
        return RankingResult(), {}

    candidate_lines = []
    for i, c in enumerate(candidates):
        candidate_lines.append(
            f"[{i + 1}] {c.title}\n    URL: {c.url}\n    Snippet: {c.snippet[:300]}"
        )
    user_prompt = "\n\n".join(candidate_lines)

    client = get_openai_client()
    model = settings.openai_model_light  # gpt-4.1-mini (o4-mini returns empty)
    usage: dict[str, Any] = {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                **build_completion_kwargs(
                    model=model,
                    messages=[
                        {"role": "system", "content": SELECTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=2048,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
            )
            raw = response.choices[0].message.content
            data = parse_ai_json(raw, "Ranking")
            usage = extract_usage_metrics(response, model)
            break
        except Exception as e:
            logger.warning("Ranking attempt %d failed: %s", attempt + 1, e)
            if attempt == MAX_RETRIES:
                logger.error("Ranking failed after %d retries", MAX_RETRIES + 1)
                return RankingResult(), usage
            continue

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
        setattr(
            result,
            pick_type,
            RankedCandidate(
                title=candidate.title,
                url=candidate.url,
                snippet=candidate.snippet,
                source=candidate.source,
                assigned_type=pick_type,
                relevance_score=float(pick.get("score", 0)),
                ranking_reason=pick.get("reason", ""),
            ),
        )

    logger.info(
        "Ranking complete: research=%s, business=%s",
        "selected" if result.research else "none",
        "selected" if result.business else "none",
    )
    return result, usage


async def classify_candidates(
    candidates: list[NewsCandidate],
) -> tuple[ClassificationResult, dict[str, Any]]:
    """Classify news candidates into research/business subcategories.

    Returns 3-5 picks per category instead of 1.
    """
    if not candidates:
        logger.info("No candidates to classify")
        return ClassificationResult(), {}

    candidate_lines = []
    for i, c in enumerate(candidates):
        candidate_lines.append(
            f"[{i + 1}] {c.title}\n    URL: {c.url}\n    Snippet: {c.snippet[:300]}"
        )
    user_prompt = "\n\n".join(candidate_lines)

    client = get_openai_client()
    model = settings.openai_model_light  # gpt-4.1-mini (o4-mini returns empty responses for classification)
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
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
            )
            raw = response.choices[0].message.content
            data = parse_ai_json(raw, "Classification")
            usage = extract_usage_metrics(response, model)
            break
        except Exception as e:
            logger.warning("Classification attempt %d failed: %s", attempt + 1, e)
            if attempt == MAX_RETRIES:
                logger.error("Classification failed after %d retries", MAX_RETRIES + 1)
                return ClassificationResult(), usage
            continue

    url_map = {c.url: c for c in candidates}
    result = ClassificationResult()

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
                continue
            classified.append(ClassifiedCandidate(
                title=candidate.title,
                url=candidate.url,
                snippet=candidate.snippet,
                source=candidate.source,
                category=category,
                subcategory=pick.get("subcategory", ""),
                relevance_score=float(pick.get("score", 0)),
                reason=pick.get("reason", ""),
            ))
        setattr(result, f"{category}_picks", classified[:8])

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
    return result, usage


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
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
            )
            data = parse_ai_json(response.choices[0].message.content, "Merge")
            usage = extract_usage_metrics(response, model)
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
                    relevance_score=pick.relevance_score,
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
                    relevance_score=float(group_data.get("score", 0)),
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
                    relevance_score=pick.relevance_score,
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
                    temperature=0,
                    response_format={"type": "json_object"},
                )
            )
            data = parse_ai_json(response.choices[0].message.content, f"Ranking-{category}")
            usage = extract_usage_metrics(response, model)
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
    lead_indices = set()
    for lead_ref in data.get("lead", []):
        if isinstance(lead_ref, int):
            lead_indices.add(lead_ref - 1)
        elif isinstance(lead_ref, str):
            # Try matching by URL or group_title
            for idx, g in enumerate(groups):
                if lead_ref in g.urls or lead_ref == g.group_title:
                    lead_indices.add(idx)

    leads = []
    supports = []
    for idx, group in enumerate(groups):
        if idx in lead_indices:
            group.reason = f"[LEAD] {group.reason}"
            leads.append(group)
        else:
            group.reason = f"[SUPPORTING] {group.reason}"
            supports.append(group)

    # If no leads matched, fallback: first group is lead
    if not leads and groups:
        groups[0].reason = f"[LEAD] {groups[0].reason}"
        leads = [groups[0]]
        supports = [g for g in groups[1:] if g.reason.startswith("[SUPPORTING]")]

    logger.info(
        "Ranking %s: lead=%d, supporting=%d",
        category, len(leads), len(supports),
    )
    return leads + supports, usage


# ---------------------------------------------------------------------------
# Community Summarizer
# ---------------------------------------------------------------------------

_HN_HEADER_RE = re.compile(
    r"\[Hacker News\]\s*.*?\|\s*([\d,]+)\s*points?\s*\|\s*([\d,]+)\s*comments?"
)
_REDDIT_HEADER_RE = re.compile(
    r"\[Reddit\s+r/(\S+)\]\s*.*?\|\s*([\d,]+)\s*upvotes?\s*\|\s*([\d,]+)\s*comments?"
)


def _parse_source_label(raw_text: str) -> str:
    """Extract human-readable source label from raw community text (deterministic)."""
    parts: list[str] = []
    hn = _HN_HEADER_RE.search(raw_text)
    if hn:
        points = hn.group(1).replace(",", "")
        comments = hn.group(2).replace(",", "")
        parts.append(f"Hacker News {points}\u2191 \u00b7 {comments} comments")
    rd = _REDDIT_HEADER_RE.search(raw_text)
    if rd:
        sub = rd.group(1)
        upvotes = rd.group(2).replace(",", "")
        parts.append(f"r/{sub} ({upvotes}\u2191)")
    return " \u00b7 ".join(parts) if parts else ""


async def summarize_community(
    community_map: dict[str, str],
    groups: list[ClassifiedGroup],
) -> tuple[dict[str, CommunityInsight], dict[str, Any]]:
    """Summarize raw community reactions into structured insights via LLM.

    Returns (url_to_insight_map, usage_metrics).
    """
    # Build per-group community data for LLM
    # key -> (raw_text, source_label, group_title)
    group_entries: dict[str, tuple[str, str, str]] = {}
    for i, group in enumerate(groups):
        raw_parts = []
        for item in group.items:
            item_raw = community_map.get(item.url, "")
            if item_raw:
                raw_parts.append(item_raw)
        raw = "\n\n".join(raw_parts)
        if not raw:
            continue
        key = f"group_{i}"
        group_entries[key] = (raw, _parse_source_label(raw), group.group_title)

    # If no community data at all, return empty
    if not group_entries:
        logger.info("Community summarizer: no community data to summarize")
        return {}, {}

    # Build prompt text — include original article title for relevance check
    groups_text_parts = []
    for key, (raw, _label, gtitle) in group_entries.items():
        groups_text_parts.append(f"### {key}\nOriginal article: {gtitle}\n{raw}")
    groups_text = "\n\n".join(groups_text_parts)

    prompt = COMMUNITY_SUMMARIZER_PROMPT.format(groups_text=groups_text)

    client = get_openai_client()
    model = settings.openai_model_light
    kwargs = build_completion_kwargs(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.2,
    )

    data = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(**kwargs)
            usage = extract_usage_metrics(response, model)
            raw_output = response.choices[0].message.content or ""
            data = parse_ai_json(raw_output, "CommunitySummarizer")
            break
        except Exception as e:
            logger.warning("Community summarizer attempt %d failed: %s", attempt + 1, e)
            if attempt == MAX_RETRIES:
                logger.error("Community summarizer failed after %d retries", MAX_RETRIES + 1)
                return {}, {}

    # Parse LLM output into CommunityInsight objects
    result: dict[str, CommunityInsight] = {}
    llm_groups = data.get("groups", {})

    for i, group in enumerate(groups):
        key = f"group_{i}"
        primary_url = group.primary_url
        if key not in group_entries:
            # No community data for this group
            continue

        _raw, source_label, _gtitle = group_entries[key]
        llm_data = llm_groups.get(key, {})

        sentiment = llm_data.get("sentiment")
        # null sentiment = LLM judged thread irrelevant to original article
        if sentiment is None:
            logger.debug("Community summarizer: group %s marked irrelevant by LLM", key)
            continue
        if sentiment not in ("positive", "mixed", "negative", "neutral"):
            sentiment = "neutral"

        quotes = llm_data.get("quotes", [])
        if not isinstance(quotes, list):
            quotes = []
        quotes = [q for q in quotes[:2] if isinstance(q, str) and len(q.strip()) > 10]

        key_point = llm_data.get("key_point")
        if key_point and not isinstance(key_point, str):
            key_point = None

        result[primary_url] = CommunityInsight(
            sentiment=sentiment,
            quotes=quotes,
            key_point=key_point,
            source_label=source_label,
        )

    logger.info(
        "Community summarizer: %d/%d groups summarized",
        len(result), len(groups),
    )
    return result, usage
