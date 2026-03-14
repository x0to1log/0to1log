"""LLM-based news candidate ranking agent."""
import logging
from typing import Any

from core.config import settings
from models.news_pipeline import NewsCandidate, RankedCandidate, RankingResult
from services.agents.client import extract_usage_metrics, get_openai_client, parse_ai_json
from services.agents.prompts_news_pipeline import RANKING_SYSTEM_PROMPT

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
