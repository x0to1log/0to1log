import json
import logging

from pydantic import ValidationError

from models.ranking import RankedCandidate, RelatedPicks
from models.business import BusinessPost
from services.agents.client import get_openai_client, parse_ai_json
from services.agents.prompts import BUSINESS_SYSTEM_PROMPT
from core.config import settings

logger = logging.getLogger(__name__)


def _build_business_user_prompt(
    candidate: RankedCandidate,
    related: RelatedPicks | None,
    context: str,
    batch_id: str,
) -> str:
    """Build the user prompt for the business analyst agent."""
    related_section = "## Related News Candidates\n"
    if related:
        if related.big_tech:
            related_section += f"- Big Tech: {related.big_tech.title} ({related.big_tech.url})\n"
        if related.industry_biz:
            related_section += f"- Industry & Biz: {related.industry_biz.title} ({related.industry_biz.url})\n"
        if related.new_tools:
            related_section += f"- New Tools: {related.new_tools.title} ({related.new_tools.url})\n"

    return (
        f"Write a 3-persona post based on the main news and related news below.\n\n"
        f"## Main News\n"
        f"Title: {candidate.title}\n"
        f"URL: {candidate.url}\n"
        f"Summary: {candidate.snippet}\n"
        f"Ranking reason: {candidate.ranking_reason}\n\n"
        f"{related_section}\n"
        f"## Tavily Collected Context\n{context}\n\n"
        f"slug: {batch_id}-business-daily"
    )


async def generate_business_post(
    candidate: RankedCandidate,
    related: RelatedPicks | None,
    context: str,
    batch_id: str,
) -> BusinessPost:
    """Step 3-B: Generate a 3-persona business post using gpt-4o.

    Takes the main business pick and related news picks to produce
    content for beginner/learner/expert personas plus guide_items and related_news.
    """
    client = get_openai_client()
    user_prompt = _build_business_user_prompt(candidate, related, context, batch_id)

    response = await client.chat.completions.create(
        model=settings.openai_model_main,
        messages=[
            {"role": "system", "content": BUSINESS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
        max_tokens=4096,
    )

    raw = response.choices[0].message.content
    data = parse_ai_json(raw, "Business")

    try:
        return BusinessPost.model_validate(data)
    except ValidationError as e:
        logger.error("Business validation failed: %s\nData: %s",
                      e, json.dumps(data, ensure_ascii=False)[:1000])
        raise
