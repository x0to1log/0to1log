import json
import logging
from typing import Any

from pydantic import ValidationError

from models.ranking import RankedCandidate, RelatedPicks
from models.business import MIN_CONTENT_CHARS, TARGET_CONTENT_CHARS, BusinessPost
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


MAX_RETRIES = 3


def _build_retry_prompt(base_prompt: str, previous_data: dict[str, Any] | None) -> str:
    if not previous_data:
        return (
            f"{base_prompt}\n\n"
            "IMPORTANT: Your previous response was rejected because the persona content was too short.\n"
            f"- each persona must be at least {MIN_CONTENT_CHARS} chars\n"
            f"- target {TARGET_CONTENT_CHARS - 500}-{TARGET_CONTENT_CHARS + 500} chars per persona\n"
            "- return the full JSON object again with deeper analysis, examples, and practical detail"
        )

    content_lengths = {
        field: len(previous_data.get(field, ""))
        if isinstance(previous_data.get(field), str)
        else 0
        for field in ("content_beginner", "content_learner", "content_expert")
    }

    return (
        f"{base_prompt}\n\n"
        "IMPORTANT: Your previous response was rejected.\n"
        f"- content_beginner was {content_lengths['content_beginner']} chars\n"
        f"- content_learner was {content_lengths['content_learner']} chars\n"
        f"- content_expert was {content_lengths['content_expert']} chars\n"
        f"- minimum required is {MIN_CONTENT_CHARS} chars for each persona\n"
        f"- target {TARGET_CONTENT_CHARS - 500}-{TARGET_CONTENT_CHARS + 500} chars per persona so the response safely clears validation\n"
        "- preserve the same story, sources, and 3-persona structure\n"
        "- deepen the analysis instead of repeating surface-level wording\n"
        "- return the full JSON object again, not a partial patch\n\n"
        "PREVIOUS_JSON_DRAFT:\n"
        f"{json.dumps(previous_data, ensure_ascii=False)}"
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
    last_data: dict[str, Any] | None = None

    for attempt in range(1 + MAX_RETRIES):
        prompt = user_prompt if attempt == 0 else _build_retry_prompt(user_prompt, last_data)

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
        last_data = data

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
