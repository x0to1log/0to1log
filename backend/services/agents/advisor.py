"""AI Advisor agent handlers — 4 independent actions."""

import logging

from pydantic import ValidationError

from core.config import settings
from models.advisor import (
    AiAdviseRequest,
    GenerateResult,
    SeoResult,
    ReviewResult,
    FactcheckResult,
)
from services.agents.client import get_openai_client, parse_ai_json
from services.agents.prompts_advisor import (
    GENERATE_SYSTEM_PROMPT,
    SEO_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
    FACTCHECK_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

# Model + config per action
ACTION_CONFIG = {
    "generate": {
        "model_attr": "openai_model_main",
        "prompt": GENERATE_SYSTEM_PROMPT,
        "max_tokens": 4096,
        "temperature": 0.3,
        "validator": GenerateResult,
    },
    "seo": {
        "model_attr": "openai_model_light",
        "prompt": SEO_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "temperature": 0.5,
        "validator": SeoResult,
    },
    "review": {
        "model_attr": "openai_model_light",
        "prompt": REVIEW_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "temperature": 0.2,
        "validator": ReviewResult,
    },
    "factcheck": {
        "model_attr": "openai_model_main",
        "prompt": FACTCHECK_SYSTEM_PROMPT,
        "max_tokens": 4096,
        "temperature": 0.2,
        "validator": FactcheckResult,
    },
}


def _build_user_prompt(req: AiAdviseRequest) -> str:
    """Build user prompt from editor state."""
    parts = [
        f"Title: {req.title}",
        f"Category: {req.category}",
        f"Post type: {req.post_type}" if req.post_type else None,
        f"Tags: {', '.join(req.tags)}" if req.tags else None,
        f"Slug: {req.slug}" if req.slug else None,
        f"Excerpt: {req.excerpt}" if req.excerpt else None,
        "",
        "Content:",
        req.content,
    ]
    return "\n".join(p for p in parts if p is not None)


def _build_seo_user_prompt(req: AiAdviseRequest) -> str:
    """Build SEO user prompt — truncate content for cost efficiency."""
    content_preview = req.content[:2000]
    if len(req.content) > 2000:
        content_preview += "\n[... truncated for analysis]"
    parts = [
        f"Title: {req.title}",
        f"Excerpt: {req.excerpt}" if req.excerpt else None,
        f"Tags: {', '.join(req.tags)}" if req.tags else None,
        "",
        "Content (first 2000 chars):",
        content_preview,
    ]
    return "\n".join(p for p in parts if p is not None)


async def run_advise(req: AiAdviseRequest) -> tuple[dict, str, int]:
    """Run an advisor action. Returns (result_dict, model_name, tokens_used)."""
    config = ACTION_CONFIG[req.action]
    model = getattr(settings, config["model_attr"])
    client = get_openai_client()

    user_prompt = (
        _build_seo_user_prompt(req) if req.action == "seo"
        else _build_user_prompt(req)
    )

    logger.info("Advisor [%s] starting with model=%s", req.action, model)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": config["prompt"]},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )

    raw = response.choices[0].message.content
    data = parse_ai_json(raw, f"Advisor-{req.action}")
    tokens = response.usage.completion_tokens if response.usage else 0

    # Validate against action-specific schema
    validator = config["validator"]
    try:
        validator.model_validate(data)
    except ValidationError as e:
        logger.warning("Advisor [%s] validation soft-fail: %s", req.action, e)
        # Return raw data anyway — partial results are still useful

    logger.info("Advisor [%s] completed, tokens=%d", req.action, tokens)
    return data, model, tokens
