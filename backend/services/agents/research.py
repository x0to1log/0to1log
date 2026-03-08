import json
import logging

from pydantic import ValidationError

from models.ranking import RankedCandidate
from models.research import ResearchPost
from services.agents.client import get_openai_client, parse_ai_json
from services.agents.prompts import RESEARCH_SYSTEM_PROMPT
from core.config import settings

logger = logging.getLogger(__name__)


def _build_research_user_prompt(
    candidate: RankedCandidate | None,
    context: str,
    batch_id: str,
) -> str:
    """Build the user prompt for the research agent."""
    if candidate is None:
        return (
            f"오늘({batch_id})은 수집된 research 뉴스가 없습니다.\n"
            "has_news=false로 설정하고 no_news_notice와 recent_fallback을 작성하세요.\n"
            f"slug: {batch_id}-research-daily"
        )

    return (
        f"아래 뉴스를 바탕으로 기술 심화 포스트를 작성하세요.\n\n"
        f"제목: {candidate.title}\n"
        f"URL: {candidate.url}\n"
        f"요약: {candidate.snippet}\n"
        f"랭킹 이유: {candidate.ranking_reason}\n\n"
        f"Tavily 수집 컨텍스트:\n{context}\n\n"
        f"slug: {batch_id}-research-daily"
    )


async def generate_research_post(
    candidate: RankedCandidate | None,
    context: str,
    batch_id: str,
) -> ResearchPost:
    """Step 3-A: Generate a research post using gpt-4o."""
    client = get_openai_client()
    user_prompt = _build_research_user_prompt(candidate, context, batch_id)

    response = await client.chat.completions.create(
        model=settings.openai_model_main,
        messages=[
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    raw = response.choices[0].message.content
    data = parse_ai_json(raw, "Research")

    try:
        return ResearchPost.model_validate(data)
    except ValidationError as e:
        logger.error("Research validation failed: %s\nData: %s",
                      e, json.dumps(data, ensure_ascii=False)[:1000])
        raise
