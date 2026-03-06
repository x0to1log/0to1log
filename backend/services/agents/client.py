import logging
from openai import AsyncOpenAI

from core.config import settings

logger = logging.getLogger(__name__)


def get_openai_client() -> AsyncOpenAI:
    """Return a configured AsyncOpenAI client."""
    return AsyncOpenAI(api_key=settings.openai_api_key)
