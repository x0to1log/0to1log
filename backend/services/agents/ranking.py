"""LLM-based news candidate ranking agent."""
import logging
from typing import Any

from core.config import settings
from models.news_pipeline import ClassifiedCandidate, ClassificationResult, NewsCandidate, RankedCandidate, RankingResult
from services.agents.client import extract_usage_metrics, get_openai_client, parse_ai_json
from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT, RANKING_SYSTEM_PROMPT

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
    model = settings.openai_model_main
    usage: dict[str, Any] = {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": RANKING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2048,
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
    model = settings.openai_model_main
    usage: dict[str, Any] = {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=4096,
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

    logger.info(
        "Classification complete: %d research, %d business",
        len(result.research), len(result.business),
    )
    return result, usage
