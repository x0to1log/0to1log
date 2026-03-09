import json
import logging

from services.agents.client import get_openai_client, parse_ai_json
from services.agents.prompts import TRANSLATE_SYSTEM_PROMPT
from core.config import settings

logger = logging.getLogger(__name__)


def _build_translate_user_prompt(en_data: dict, post_type: str) -> str:
    """Build the user prompt for the translation agent."""
    return (
        f"Translate this {post_type} post from English to Korean.\n\n"
        f"```json\n{json.dumps(en_data, ensure_ascii=False, indent=2)}\n```"
    )


async def translate_post(en_data: dict, post_type: str) -> dict:
    """Translate an EN post dict to KO using gpt-4o.

    Args:
        en_data: The English post data as a dict (already validated).
        post_type: "research" or "business".

    Returns:
        A dict with the same structure but text fields translated to Korean.
    """
    client = get_openai_client()
    user_prompt = _build_translate_user_prompt(en_data, post_type)

    response = await client.chat.completions.create(
        model=settings.openai_model_main,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=4096,
    )

    raw = response.choices[0].message.content
    translated = parse_ai_json(raw, f"Translate-{post_type}")
    logger.info(
        "Translated %s post: title=%s",
        post_type,
        translated.get("title", "?")[:80],
    )
    return translated
