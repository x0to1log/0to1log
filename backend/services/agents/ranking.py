"""LLM-based news candidate ranking agent."""
import logging
from typing import Any

from core.config import settings
from models.news_pipeline import ClassifiedCandidate, ClassificationResult, NewsCandidate, RankedCandidate, RankingResult
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
        picks = data.get(category, [])
        classified = []
        for pick in picks:
            url = pick.get("url", "")
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
        setattr(result, category, classified[:5])

    # Allow same URL in both categories — Business and Research write from
    # completely different perspectives (strategic vs technical), so overlap
    # is valuable, not redundant. Log for visibility.
    if result.research and result.business:
        research_urls = {c.url for c in result.research}
        business_urls = {c.url for c in result.business}
        overlap = research_urls & business_urls
        if overlap:
            logger.info("Cross-category overlap: %d URL(s) in both research and business (kept in both)", len(overlap))

    logger.info(
        "Classification complete: %d research, %d business",
        len(result.research), len(result.business),
    )
    if not result.business:
        logger.warning("No business articles classified — business digest will be skipped")
    if not result.research:
        logger.warning("No research articles classified — research digest will be skipped")
    return result, usage


async def rank_classified(
    items: list[ClassifiedCandidate],
    category: str,
    community_map: dict[str, str] | None = None,
) -> tuple[list[ClassifiedCandidate], dict[str, Any]]:
    """Rank classified items: assign [LEAD]/[SUPPORTING] role via o4-mini.

    Returns (reordered items with role in reason field, usage metrics).
    Lead items come first, then supporting in importance order.
    """
    if len(items) <= 1:
        if items:
            items[0].reason = f"[LEAD] {items[0].reason}"
        return items, {}

    from services.agents.prompts_news_pipeline import RANKING_SYSTEM_PROMPT_V2

    community_map = community_map or {}

    item_lines = []
    for i, item in enumerate(items):
        source_domain = "/".join(item.url.split("/")[:3]) if "://" in item.url else "unknown"
        community = community_map.get(item.url, "")
        engagement = "no community data"
        if community:
            first_line = community.split("\n")[0].strip()
            if first_line:
                engagement = first_line
        item_lines.append(
            f"[{i+1}] {item.title}\n"
            f"    URL: {item.url}\n"
            f"    Source: {source_domain}\n"
            f"    Subcategory: {item.subcategory}\n"
            f"    Community: {engagement}"
        )

    prompt = RANKING_SYSTEM_PROMPT_V2.format(
        category=category,
        count=len(items),
        items="\n".join(item_lines),
    )

    client = get_openai_client()
    model = settings.openai_model_reasoning

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
        items[0].reason = f"[LEAD] {items[0].reason}"
        for item in items[1:]:
            item.reason = f"[SUPPORTING] {item.reason}"
        return items, {}

    lead_urls = set(data.get("lead", []))
    supporting_urls = data.get("supporting", [])

    leads = []
    supports = []
    for item in items:
        if item.url in lead_urls:
            item.reason = f"[LEAD] {item.reason}"
            leads.append(item)
        else:
            item.reason = f"[SUPPORTING] {item.reason}"
            supports.append(item)

    url_order = {url: i for i, url in enumerate(supporting_urls)}
    supports.sort(key=lambda x: url_order.get(x.url, 999))

    logger.info(
        "Ranking %s: lead=%d, supporting=%d",
        category, len(leads), len(supports),
    )
    return leads + supports, usage
