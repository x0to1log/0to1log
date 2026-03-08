import json
import logging
import re

from openai import AsyncOpenAI

from core.config import settings

logger = logging.getLogger(__name__)


def get_openai_client() -> AsyncOpenAI:
    """Return a configured AsyncOpenAI client."""
    return AsyncOpenAI(api_key=settings.openai_api_key)


def parse_ai_json(raw: str, agent_name: str) -> dict:
    """Parse AI response as JSON with fallback for code-block wrapping."""
    logger.info("%s raw response (first 500 chars): %.500s", agent_name, raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        logger.error("%s: failed to parse JSON: %.1000s", agent_name, raw)
        raise
