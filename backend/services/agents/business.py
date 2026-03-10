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


MAX_RETRIES = 2

RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was rejected because content was "
    "too short. Each persona version MUST be at least 3000 characters. "
    "Write longer, deeper analysis with more detail and examples."
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
    Retries up to MAX_RETRIES times if content is too short.
    """
    client = get_openai_client()
    user_prompt = _build_business_user_prompt(candidate, related, context, batch_id)
    last_error: ValidationError | None = None

    for attempt in range(1 + MAX_RETRIES):
        prompt = user_prompt if attempt == 0 else user_prompt + RETRY_SUFFIX

        response = await client.chat.completions.create(
            model=settings.openai_model_main,
            messages=[
                {"role": "system", "content": BUSINESS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=16384,
        )

        raw = response.choices[0].message.content
        data = parse_ai_json(raw, "Business")

        try:
            return BusinessPost.model_validate(data)
        except ValidationError as e:
            last_error = e
            logger.warning(
                "Business validation failed (attempt %d/%d): %s",
                attempt + 1, 1 + MAX_RETRIES, e,
            )

    logger.error(
        "Business generation failed after %d attempts.\nData: %s",
        1 + MAX_RETRIES, json.dumps(data, ensure_ascii=False)[:1000],
    )
    raise last_error  # type: ignore[misc]
