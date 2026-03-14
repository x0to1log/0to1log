import json
import logging
from typing import Any

from pydantic import ValidationError

from models.ranking import NewsCandidate, NewsRankingResult
from services.agents.client import (
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
)
from services.agents.prompts import RANKING_SYSTEM_PROMPT
from core.config import settings

logger = logging.getLogger(__name__)


def _build_ranking_user_prompt(candidates: list[NewsCandidate]) -> str:
    """Format candidates into a numbered list for the ranking agent."""
    lines = ["아래 뉴스 후보들을 분류하고 랭킹하세요:\n"]
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. [{c.source}] {c.title}\n   URL: {c.url}\n   {c.snippet}\n")
    return "\n".join(lines)


async def rank_candidates(
    candidates: list[NewsCandidate],
    usage_recorder: dict[str, Any] | None = None,
) -> NewsRankingResult:
    """Step 2: Classify and rank news candidates using gpt-4o-mini."""
    client = get_openai_client()
    user_prompt = _build_ranking_user_prompt(candidates)

    response = await client.chat.completions.create(
        model=settings.openai_model_light,
        messages=[
            {"role": "system", "content": RANKING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    usage = extract_usage_metrics(response, settings.openai_model_light)
    if usage_recorder is not None:
        merged_usage = merge_usage_metrics(usage_recorder, usage)
        merged_usage["attempts"] = 1
        usage_recorder.clear()
        usage_recorder.update(merged_usage)

    raw = response.choices[0].message.content
    data = parse_ai_json(raw, "Ranking")

    try:
        return NewsRankingResult.model_validate(data)
    except ValidationError as e:
        logger.error("Ranking validation failed: %s\nData: %s",
                      e, json.dumps(data, ensure_ascii=False)[:1000])
        raise
