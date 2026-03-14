"""EN → KO whole-post translation — v4.

One gpt-4o call per post. No section splitting, no recovery passes.
"""

import copy
import json
import logging
from typing import Any

from core.config import settings
from models.business import (
    KO_MIN_ANALYSIS_CHARS as BUSINESS_KO_MIN_ANALYSIS,
    KO_MIN_CONTENT_CHARS as BUSINESS_KO_MIN_CONTENT,
    BusinessPost,
)
from models.research import KO_MIN_CONTENT_CHARS as RESEARCH_KO_MIN_CONTENT, ResearchPost
from services.agents.client import (
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
)
from services.agents.prompts import TRANSLATE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_research_translation_payload(en_data: dict[str, Any]) -> dict[str, Any]:
    """Extract translatable fields from a research post."""
    payload: dict[str, Any] = {
        "title": en_data.get("title", ""),
        "excerpt": en_data.get("excerpt", ""),
        "tags": en_data.get("tags", []),
        "focus_items": en_data.get("focus_items", []),
        "guide_items": en_data.get("guide_items"),
    }
    if en_data.get("has_news", True):
        payload["content_original"] = en_data.get("content_original", "")
    else:
        payload["no_news_notice"] = en_data.get("no_news_notice", "")
        payload["recent_fallback"] = en_data.get("recent_fallback", "")
    return payload


def _build_business_translation_payload(en_data: dict[str, Any]) -> dict[str, Any]:
    """Extract translatable fields from a business post."""
    return {
        "title": en_data.get("title", ""),
        "excerpt": en_data.get("excerpt", ""),
        "tags": en_data.get("tags", []),
        "focus_items": en_data.get("focus_items", []),
        "guide_items": en_data.get("guide_items"),
        "related_news": en_data.get("related_news"),
        "fact_pack": en_data.get("fact_pack", {}),
        "content_analysis": en_data.get("content_analysis", ""),
        "content_beginner": en_data.get("content_beginner", ""),
        "content_learner": en_data.get("content_learner", ""),
        "content_expert": en_data.get("content_expert", ""),
    }


def _build_user_prompt(
    payload: dict[str, Any],
    post_type: str,
    length_hints: str = "",
) -> str:
    """Build the user prompt for whole-post translation."""
    hint_block = f"\n\n{length_hints}" if length_hints else ""
    return (
        f"Translate this {post_type} post from English to Korean.\n"
        "Return the same JSON structure with all text values translated.\n"
        "Keep URLs, slugs, field names, booleans, and identifiers unchanged."
        f"{hint_block}\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
    )


async def _call_translate(
    client: Any,
    user_prompt: str,
    agent_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Single OpenAI translation call. Returns (data, usage)."""
    response = await client.chat.completions.create(
        model=settings.openai_model_main,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=16384,
    )
    finish_reason = response.choices[0].finish_reason
    if finish_reason == "length":
        logger.warning(
            "%s: response truncated (finish_reason=length, max_tokens=16384)",
            agent_name,
        )
    raw = response.choices[0].message.content
    return (
        parse_ai_json(raw, agent_name),
        extract_usage_metrics(response, settings.openai_model_main),
    )


def _merge_translation(base: dict[str, Any], translated: dict[str, Any]) -> dict[str, Any]:
    """Merge translated fields into the base EN data, preserving untranslated fields."""
    merged = copy.deepcopy(base)
    for key, value in translated.items():
        if value is not None:
            merged[key] = value
    return merged


# ---------------------------------------------------------------------------
# Research translation
# ---------------------------------------------------------------------------

async def _translate_research(
    en_data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Translate a research post EN → KO. Returns (ko_data, usage)."""
    client = get_openai_client()
    payload = _build_research_translation_payload(en_data)

    # Compute dynamic threshold from actual EN length
    en_content_len = len(en_data.get("content_original") or "")
    ko_target = max(RESEARCH_KO_MIN_CONTENT, int(en_content_len * 0.45))

    length_hints = (
        "IMPORTANT — Length requirements for Korean translation:\n"
        f"- content_original: English is {en_content_len} chars "
        f"→ Korean must be at least {ko_target} chars "
        f"(absolute floor: {RESEARCH_KO_MIN_CONTENT}).\n"
        "Do NOT summarize or compress. Translate every sentence fully."
    )
    user_prompt = _build_user_prompt(payload, "research", length_hints=length_hints)

    cumulative_usage: dict[str, Any] = {}
    last_error: Exception | None = None

    for attempt in range(1 + MAX_RETRIES):
        try:
            translated, usage = await _call_translate(client, user_prompt, "TranslateResearch")
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

            merged = _merge_translation(en_data, translated)

            # Validate with dynamic threshold
            if en_data.get("has_news", True):
                content_len = len(merged.get("content_original") or "")
                if content_len < ko_target:
                    logger.warning(
                        "TranslateResearch attempt %d: content=%d/%d (en=%d)",
                        attempt + 1, content_len, ko_target, en_content_len,
                    )
                    last_error = ValueError(
                        f"content_original too short: {content_len}/{ko_target} (en={en_content_len})"
                    )
                    shortfall = ko_target - content_len
                    user_prompt = (
                        f"{user_prompt}\n\n"
                        f"CRITICAL: content_original was {content_len} chars "
                        f"but minimum is {ko_target} "
                        f"(need {shortfall} more). "
                        "Translate every English sentence fully into Korean — "
                        "do NOT paraphrase, summarize, or merge sentences."
                    )
                    continue

            validated = ResearchPost.model_validate(merged)
            logger.info("TranslateResearch success on attempt %d", attempt + 1)
            cumulative_usage["attempts"] = attempt + 1
            return validated.model_dump(), cumulative_usage

        except Exception as exc:
            last_error = exc
            logger.warning("TranslateResearch attempt %d failed: %s", attempt + 1, exc)
            if attempt >= MAX_RETRIES:
                break

    raise ValueError(f"TranslateResearch failed after {1 + MAX_RETRIES} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Business translation
# ---------------------------------------------------------------------------

async def _translate_business(
    en_data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Translate a business post EN → KO. Returns (ko_data, usage)."""
    client = get_openai_client()
    payload = _build_business_translation_payload(en_data)

    # Compute dynamic thresholds from actual EN lengths
    persona_fields = ("content_beginner", "content_learner", "content_expert")
    en_lengths: dict[str, int] = {}
    ko_targets: dict[str, int] = {}
    hint_lines: list[str] = []
    for field in persona_fields:
        en_len = len(en_data.get(field) or "")
        target = max(BUSINESS_KO_MIN_CONTENT, int(en_len * 0.45))
        en_lengths[field] = en_len
        ko_targets[field] = target
        hint_lines.append(
            f"- {field}: English {en_len} chars → Korean ≥ {target} chars"
        )

    en_analysis_len = len(en_data.get("content_analysis") or "")
    ko_analysis_target = max(BUSINESS_KO_MIN_ANALYSIS, int(en_analysis_len * 0.45))
    en_lengths["content_analysis"] = en_analysis_len
    ko_targets["content_analysis"] = ko_analysis_target
    hint_lines.append(
        f"- content_analysis: English {en_analysis_len} chars → Korean ≥ {ko_analysis_target} chars"
    )

    length_hints = (
        "IMPORTANT — Length requirements for Korean translation:\n"
        + "\n".join(hint_lines) + "\n"
        "Do NOT summarize or compress. Translate every sentence fully."
    )
    user_prompt = _build_user_prompt(payload, "business", length_hints=length_hints)

    cumulative_usage: dict[str, Any] = {}
    last_error: Exception | None = None

    for attempt in range(1 + MAX_RETRIES):
        try:
            translated, usage = await _call_translate(client, user_prompt, "TranslateBusiness")
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

            merged = _merge_translation(en_data, translated)

            # Check minimum lengths with dynamic thresholds
            short_fields: list[str] = []
            for field in persona_fields:
                flen = len(merged.get(field) or "")
                if flen < ko_targets[field]:
                    short_fields.append(f"{field}={flen}/{ko_targets[field]}")

            analysis_len = len(merged.get("content_analysis") or "")
            if analysis_len < ko_analysis_target:
                short_fields.append(f"content_analysis={analysis_len}/{ko_analysis_target}")

            if short_fields:
                logger.warning(
                    "TranslateBusiness attempt %d too short: %s",
                    attempt + 1, ", ".join(short_fields),
                )
                last_error = ValueError(
                    f"Fields too short: {', '.join(short_fields)}"
                )
                user_prompt = (
                    f"{user_prompt}\n\n"
                    f"CRITICAL: These fields were too short: {', '.join(short_fields)}. "
                    "Translate every English sentence fully into Korean — "
                    "do NOT paraphrase, summarize, or merge sentences."
                )
                continue

            validated = BusinessPost.model_validate(merged)
            logger.info("TranslateBusiness success on attempt %d", attempt + 1)
            cumulative_usage["attempts"] = attempt + 1
            return validated.model_dump(), cumulative_usage

        except Exception as exc:
            last_error = exc
            logger.warning("TranslateBusiness attempt %d failed: %s", attempt + 1, exc)
            if attempt >= MAX_RETRIES:
                break

    raise ValueError(f"TranslateBusiness failed after {1 + MAX_RETRIES} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def translate_post(
    en_data: dict[str, Any],
    post_type: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Translate an EN post to KO. Returns (ko_data_dict, usage_metrics).

    Args:
        en_data: Validated EN post data as dict.
        post_type: "research" or "business".
    """
    if post_type == "research":
        ko_data, usage = await _translate_research(en_data)
    elif post_type == "business":
        ko_data, usage = await _translate_business(en_data)
    else:
        raise ValueError(f"Unsupported post_type: {post_type}")

    logger.info("Translated %s post: title=%s", post_type, ko_data.get("title", "?")[:80])
    return ko_data, usage
