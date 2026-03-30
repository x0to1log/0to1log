"""LLM-based news candidate ranking agent."""
import logging
from typing import Any

from core.config import settings
from models.news_pipeline import ClassifiedGroup, ClassificationResult, GroupedItem, NewsCandidate, RankedCandidate, RankingResult
from services.agents.client import build_completion_kwargs, extract_usage_metrics, get_openai_client, parse_ai_json
from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT, SELECTION_SYSTEM_PROMPT

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
        groups_raw = data.get(category, [])
        classified_groups: list[ClassifiedGroup] = []

        for group_data in groups_raw:
            # Support both grouped format (items array) and legacy flat format (single url)
            items_raw = group_data.get("items", [])
            if not items_raw and group_data.get("url"):
                # Legacy flat format fallback
                items_raw = [{"url": group_data["url"], "title": group_data.get("title", "")}]

            grouped_items: list[GroupedItem] = []
            for item_data in items_raw:
                url = item_data.get("url", "")
                candidate = url_map.get(url)
                if not candidate:
                    logger.warning("Classified URL not in candidates: %s", url)
                    continue
                grouped_items.append(GroupedItem(url=url, title=candidate.title))

            if grouped_items:
                classified_groups.append(ClassifiedGroup(
                    group_title=group_data.get("group_title", grouped_items[0].title),
                    items=grouped_items,
                    category=category,
                    subcategory=group_data.get("subcategory", ""),
                    relevance_score=float(group_data.get("score", 0)),
                    reason=group_data.get("reason", ""),
                ))
        setattr(result, category, classified_groups[:5])

    # Log cross-category overlap
    if result.research and result.business:
        research_urls = {u for g in result.research for u in g.urls}
        business_urls = {u for g in result.business for u in g.urls}
        overlap = research_urls & business_urls
        if overlap:
            logger.info("Cross-category overlap: %d URL(s) in both research and business", len(overlap))

    total_items_r = sum(len(g.items) for g in result.research)
    total_items_b = sum(len(g.items) for g in result.business)
    logger.info(
        "Classification complete: %d research groups (%d items), %d business groups (%d items)",
        len(result.research), total_items_r, len(result.business), total_items_b,
    )
    if not result.business:
        logger.warning("No business articles classified — business digest will be skipped")
    if not result.research:
        logger.warning("No research articles classified — research digest will be skipped")
    return result, usage


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
    except Exception as e:
        logger.warning("Ranking failed for %s: %s — falling back to classification order", category, e)
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
