"""LLM-based fact extraction agent."""
import logging
from typing import Any

from core.config import settings
from models.news_pipeline import FactPack
from services.agents.client import compat_create_kwargs, extract_usage_metrics, get_openai_client, parse_ai_json
from services.agents.prompts_news_pipeline import FACT_EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


async def extract_facts(
    news_text: str,
    context_text: str = "",
    community_text: str = "",
) -> tuple[FactPack, dict[str, Any]]:
    """Extract structured facts from news article and context.

    Returns (FactPack, usage_metrics).
    Raises on unrecoverable error after retries.
    """
    user_prompt = f"""## News Article
{news_text}

## Additional Context
{context_text or "(none)"}

## Community Reactions
{community_text or "(none)"}"""

    client = get_openai_client()
    model = settings.openai_model_main
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                **compat_create_kwargs(
                    model,
                    messages=[
                        {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=4096,
                )
            )
            raw = response.choices[0].message.content
            data = parse_ai_json(raw, "FactExtractor")
            fact_pack = FactPack.model_validate(data)
            usage = extract_usage_metrics(response, model)
            logger.info(
                "Fact extraction complete: %d facts, %d sources",
                len(fact_pack.key_facts),
                len(fact_pack.sources),
            )
            return fact_pack, usage
        except Exception as e:
            last_error = e
            logger.warning("Fact extraction attempt %d failed: %s", attempt + 1, e)
            if attempt < MAX_RETRIES:
                continue

    raise last_error  # type: ignore[misc]
