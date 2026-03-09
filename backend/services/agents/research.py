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
            f"No research news was collected today ({batch_id}).\n"
            "Set has_news=false and write no_news_notice and recent_fallback.\n"
            f"slug: {batch_id}-research-daily"
        )

    return (
        f"Write an in-depth technical post based on the following news.\n\n"
        f"Title: {candidate.title}\n"
        f"URL: {candidate.url}\n"
        f"Summary: {candidate.snippet}\n"
        f"Ranking reason: {candidate.ranking_reason}\n\n"
        f"Tavily collected context:\n{context}\n\n"
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
        max_tokens=8192,
    )

    raw = response.choices[0].message.content
    data = parse_ai_json(raw, "Research")

    try:
        return ResearchPost.model_validate(data)
    except ValidationError as e:
        logger.error("Research validation failed: %s\nData: %s",
                      e, json.dumps(data, ensure_ascii=False)[:1000])
        raise
