import json
import logging
from typing import Any

from pydantic import ValidationError

from models.ranking import RankedCandidate
from models.research import MIN_CONTENT_CHARS, TARGET_CONTENT_CHARS, ResearchPost
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
            f"No sufficiently distinct research or model update cleared today's novelty gate ({batch_id}).\n"
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


MAX_RETRIES = 3


def _build_retry_prompt(base_prompt: str, previous_data: dict[str, Any] | None) -> str:
    if not previous_data:
        return (
            base_prompt
            + "\n\nIMPORTANT: Your previous response was rejected because "
            f"content_original was too short. It MUST be at least {MIN_CONTENT_CHARS} characters "
            f"and should target at least {TARGET_CONTENT_CHARS} chars "
            "with 4 sections of at least 1200 characters each. Return valid JSON only."
        )

    content_original = previous_data.get("content_original")
    content_length = len(content_original) if isinstance(content_original, str) else 0
    missing_chars = max(MIN_CONTENT_CHARS - content_length, 0)

    return (
        f"{base_prompt}\n\n"
        "IMPORTANT: Your previous response was rejected.\n"
        f"- content_original was {content_length} chars\n"
        f"- minimum required is {MIN_CONTENT_CHARS} chars\n"
        f"- target at least {TARGET_CONTENT_CHARS} chars so it clears validation comfortably\n"
        f"- add at least {missing_chars} more chars while keeping the same story\n"
        "- keep the 4 required ## sections\n"
        "- keep all facts source-backed\n"
        "- return the full JSON object again, not a partial patch\n\n"
        "PREVIOUS_JSON_DRAFT:\n"
        f"{json.dumps(previous_data, ensure_ascii=False)}"
    )


async def generate_research_post(
    candidate: RankedCandidate | None,
    context: str,
    batch_id: str,
) -> ResearchPost:
    """Step 3-A: Generate a research post using gpt-4o.

    Retries up to MAX_RETRIES times if content is too short.
    """
    client = get_openai_client()
    user_prompt = _build_research_user_prompt(candidate, context, batch_id)
    last_error: ValidationError | None = None
    last_data: dict[str, Any] | None = None

    for attempt in range(1 + MAX_RETRIES):
        prompt = user_prompt if attempt == 0 else _build_retry_prompt(user_prompt, last_data)

        response = await client.chat.completions.create(
            model=settings.openai_model_main,
            messages=[
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=16384,
        )

        raw = response.choices[0].message.content
        data = parse_ai_json(raw, "Research")
        last_data = data

        try:
            return ResearchPost.model_validate(data)
        except ValidationError as e:
            last_error = e
            logger.warning(
                "Research validation failed (attempt %d/%d): %s",
                attempt + 1, 1 + MAX_RETRIES, e,
            )

    logger.error(
        "Research generation failed after %d attempts.\nData: %s",
        1 + MAX_RETRIES, json.dumps(data, ensure_ascii=False)[:1000],
    )
    raise last_error  # type: ignore[misc]
