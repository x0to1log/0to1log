import copy
import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from core.config import settings
from models.business import (
    KO_MIN_ANALYSIS_CHARS as BUSINESS_KO_MIN_ANALYSIS_CHARS,
    KO_MIN_CONTENT_CHARS as BUSINESS_KO_MIN_CONTENT_CHARS,
    BusinessPost,
)
from models.research import MIN_CONTENT_CHARS as RESEARCH_MIN_CONTENT_CHARS, ResearchPost
from services.agents.client import (
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
)
from services.agents.prompts import TRANSLATE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

SECTION_MAX_RETRIES = 2
POST_RECOVERY_PASSES = 1
RESEARCH_SECTION_SHRINK_RATIO = 0.68
BUSINESS_SECTION_SHRINK_RATIO = 0.60
RESEARCH_SECTION_MIN_FLOOR = 700
BUSINESS_SECTION_MIN_FLOOR = 600


def split_markdown_sections(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    parts = re.split(r"(?=^##\s)", text, flags=re.MULTILINE)
    sections = [part.strip() for part in parts if part.strip()]
    return sections or [text]


def _merge_translation(base: Any, translated: Any) -> Any:
    if translated is None:
        return copy.deepcopy(base)

    if isinstance(base, dict) and isinstance(translated, dict):
        merged = copy.deepcopy(base)
        for key, value in translated.items():
            if key in merged:
                merged[key] = _merge_translation(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    if isinstance(base, list) and isinstance(translated, list):
        if len(base) == len(translated):
            return [_merge_translation(b, t) for b, t in zip(base, translated)]
        return copy.deepcopy(translated)

    return copy.deepcopy(translated)


def _join_sections(sections: list[str]) -> str:
    return "\n\n".join(section.strip() for section in sections if section.strip())


def _heading_preserved(source: str, translated: str) -> bool:
    if not source.lstrip().startswith("## "):
        return True
    return translated.lstrip().startswith("## ")


def _initial_section_minimums(
    sections: list[str],
    shrink_ratio: float,
    min_floor: int,
) -> list[int]:
    return [max(int(len(section) * shrink_ratio), min_floor) for section in sections]


def _recovery_section_minimums(
    sections: list[str],
    total_min_chars: int,
    shrink_ratio: float,
    min_floor: int,
) -> list[int]:
    total_length = sum(len(section) for section in sections) or 1
    minimums: list[int] = []

    for section in sections:
        base_min = max(int(len(section) * shrink_ratio), min_floor)
        proportional_min = max(int(total_min_chars * len(section) / total_length), min_floor)
        minimums.append(max(base_min, proportional_min))

    shortfall = total_min_chars - sum(minimums)
    if shortfall > 0 and minimums:
        minimums[-1] += shortfall

    return minimums


def _build_translate_metadata_prompt(payload: dict[str, Any], post_type: str) -> str:
    return (
        f"Translate this {post_type} metadata JSON from English to Korean.\n"
        "- Translate only user-facing text values.\n"
        "- Keep URLs, slugs, field names, and empty/null values unchanged.\n"
        "- Preserve nested objects and arrays.\n"
        "- Return the same JSON shape.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
    )


def _build_translate_section_prompt(
    section: str,
    post_type: str,
    field_name: str,
    min_chars: int,
    previous_translation: str | None = None,
    recovery_total_min: int | None = None,
) -> str:
    lines = [
        f"Translate this {post_type} markdown section from English to Korean for {field_name}.",
        "Preserve the heading, links, bullets, tables, code fences, and examples exactly.",
        "Maintain the same information density; do not summarize or compress the content.",
        f"The minimum expected length for this translated section is {min_chars} chars.",
    ]

    if recovery_total_min is not None:
        lines.append(
            f"This is a post-level recovery pass for {field_name}; the minimum required is {recovery_total_min} chars for the full field."
        )

    if previous_translation:
        lines.append(
            f"The previous translation was {len(previous_translation)} chars and was rejected."
        )
        lines.append("Expand the section while preserving the same facts and structure.")
        lines.append("PREVIOUS_TRANSLATION:")
        lines.append(f"```markdown\n{previous_translation}\n```")

    lines.append('Return JSON only in this shape: {"translated_text": "..."}')
    lines.append("SECTION:")
    lines.append(f"```markdown\n{section}\n```")

    return "\n".join(lines)


async def _request_json_translation(
    client: Any,
    prompt: str,
    agent_name: str,
    usage_recorder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await client.chat.completions.create(
        model=settings.openai_model_main,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=16384,
    )
    if usage_recorder is not None:
        merged_usage = merge_usage_metrics(
            usage_recorder,
            extract_usage_metrics(response, settings.openai_model_main),
        )
        usage_recorder.clear()
        usage_recorder.update(merged_usage)

    raw = response.choices[0].message.content
    return parse_ai_json(raw, agent_name)


async def translate_metadata_block(
    client: Any,
    payload: dict[str, Any],
    post_type: str,
    usage_recorder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not payload:
        return {}
    prompt = _build_translate_metadata_prompt(payload, post_type)
    return await _request_json_translation(
        client,
        prompt,
        f"Translate-{post_type}-metadata",
        usage_recorder=usage_recorder,
    )


async def _translate_source_cards(
    client: Any,
    source_cards: list[dict[str, Any]],
    post_type: str,
    usage_recorder: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not source_cards:
        return []

    payload = {
        "source_cards": [
            {
                "id": card.get("id", ""),
                "evidence_snippet": card.get("evidence_snippet", ""),
                "claim_ids": card.get("claim_ids", []),
            }
            for card in source_cards
        ]
    }
    translated = await translate_metadata_block(
        client,
        payload,
        post_type,
        usage_recorder=usage_recorder,
    )
    translated_cards = translated.get("source_cards") or []
    merged: list[dict[str, Any]] = []
    for index, card in enumerate(source_cards):
        local = translated_cards[index] if index < len(translated_cards) else {}
        merged.append(
            {
                **card,
                "evidence_snippet": local.get("evidence_snippet", card.get("evidence_snippet", "")),
                "claim_ids": local.get("claim_ids", card.get("claim_ids", [])),
            }
        )
    return merged


async def translate_section(
    client: Any,
    section: str,
    post_type: str,
    field_name: str,
    min_chars: int,
    recovery_total_min: int | None = None,
    usage_recorder: dict[str, Any] | None = None,
) -> str:
    previous_translation: str | None = None

    for _attempt in range(1 + SECTION_MAX_RETRIES):
        prompt = _build_translate_section_prompt(
            section=section,
            post_type=post_type,
            field_name=field_name,
            min_chars=min_chars,
            previous_translation=previous_translation,
            recovery_total_min=recovery_total_min,
        )
        translated_payload = await _request_json_translation(
            client,
            prompt,
            f"Translate-{post_type}-{field_name}-section",
            usage_recorder=usage_recorder,
        )
        translated_text = translated_payload.get("translated_text", "").strip()

        if translated_text and len(translated_text) >= min_chars and _heading_preserved(section, translated_text):
            return translated_text

        previous_translation = translated_text or previous_translation or ""

    return previous_translation or section


async def _translate_markdown_field(
    client: Any,
    text: str,
    post_type: str,
    field_name: str,
    total_min_chars: int,
    shrink_ratio: float,
    min_floor: int,
    recovery: bool = False,
    usage_recorder: dict[str, Any] | None = None,
) -> str:
    sections = split_markdown_sections(text)
    if not sections:
        return ""

    if recovery:
        minimums = _recovery_section_minimums(
            sections=sections,
            total_min_chars=total_min_chars,
            shrink_ratio=shrink_ratio,
            min_floor=min_floor,
        )
    else:
        minimums = _initial_section_minimums(
            sections=sections,
            shrink_ratio=shrink_ratio,
            min_floor=min_floor,
        )

    translated_sections: list[str] = []
    for section, min_chars in zip(sections, minimums):
        translated_sections.append(
            await translate_section(
                client=client,
                section=section,
                post_type=post_type,
                field_name=field_name,
                min_chars=min_chars,
                recovery_total_min=total_min_chars if recovery else None,
                usage_recorder=usage_recorder,
            )
        )

    return _join_sections(translated_sections)


def _extract_failed_fields(error: ValidationError, allowed_fields: set[str]) -> set[str]:
    failed: set[str] = set()
    for item in error.errors():
        loc = item.get("loc") or ()
        if loc and loc[0] in allowed_fields:
            failed.add(str(loc[0]))
    return failed


async def translate_research_post(
    client: Any,
    en_data: dict[str, Any],
    usage_recorder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    translated = copy.deepcopy(en_data)
    metadata_payload = {
        "title": en_data.get("title", ""),
        "excerpt": en_data.get("excerpt", ""),
        "focus_items": en_data.get("focus_items", []),
        "guide_items": en_data.get("guide_items"),
        "tags": en_data.get("tags", []),
    }
    if not en_data.get("has_news", True):
        metadata_payload["no_news_notice"] = en_data.get("no_news_notice", "")
        metadata_payload["recent_fallback"] = en_data.get("recent_fallback", "")

    translated = _merge_translation(
        translated,
        await translate_metadata_block(
            client,
            metadata_payload,
            "research",
            usage_recorder=usage_recorder,
        ),
    )
    translated["source_cards"] = await _translate_source_cards(
        client,
        en_data.get("source_cards") or [],
        "research",
        usage_recorder=usage_recorder,
    )

    if en_data.get("has_news", True) and en_data.get("content_original"):
        translated["content_original"] = await _translate_markdown_field(
            client=client,
            text=en_data["content_original"],
            post_type="research",
            field_name="content_original",
            total_min_chars=RESEARCH_MIN_CONTENT_CHARS,
            shrink_ratio=RESEARCH_SECTION_SHRINK_RATIO,
            min_floor=RESEARCH_SECTION_MIN_FLOOR,
            usage_recorder=usage_recorder,
        )
    else:
        translated["content_original"] = None

    for recovery_pass in range(1 + POST_RECOVERY_PASSES):
        try:
            return ResearchPost.model_validate(translated).model_dump()
        except ValidationError as error:
            if recovery_pass >= POST_RECOVERY_PASSES:
                raise

            failed_fields = _extract_failed_fields(error, {"content_original"})
            if "content_original" not in failed_fields or not en_data.get("content_original"):
                raise

            translated["content_original"] = await _translate_markdown_field(
                client=client,
                text=en_data["content_original"],
                post_type="research",
                field_name="content_original",
                total_min_chars=RESEARCH_MIN_CONTENT_CHARS,
                shrink_ratio=RESEARCH_SECTION_SHRINK_RATIO,
                min_floor=RESEARCH_SECTION_MIN_FLOOR,
                recovery=True,
                usage_recorder=usage_recorder,
            )

    return translated


async def translate_business_post(
    client: Any,
    en_data: dict[str, Any],
    usage_recorder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    translated = copy.deepcopy(en_data)
    metadata_payload = {
        "title": en_data.get("title", ""),
        "excerpt": en_data.get("excerpt", ""),
        "focus_items": en_data.get("focus_items", []),
        "guide_items": en_data.get("guide_items"),
        "related_news": en_data.get("related_news"),
        "tags": en_data.get("tags", []),
        "fact_pack": en_data.get("fact_pack", []),
    }
    translated = _merge_translation(
        translated,
        await translate_metadata_block(
            client,
            metadata_payload,
            "business",
            usage_recorder=usage_recorder,
        ),
    )
    translated["source_cards"] = await _translate_source_cards(
        client,
        en_data.get("source_cards") or [],
        "business",
        usage_recorder=usage_recorder,
    )
    translated["content_analysis"] = await _translate_markdown_field(
        client=client,
        text=en_data.get("content_analysis", ""),
        post_type="business",
        field_name="content_analysis",
        total_min_chars=BUSINESS_KO_MIN_ANALYSIS_CHARS,
        shrink_ratio=BUSINESS_SECTION_SHRINK_RATIO,
        min_floor=BUSINESS_SECTION_MIN_FLOOR,
        usage_recorder=usage_recorder,
    ) if en_data.get("content_analysis") else ""

    for field_name in ("content_beginner", "content_learner", "content_expert"):
        translated[field_name] = await _translate_markdown_field(
            client=client,
            text=en_data.get(field_name, ""),
            post_type="business",
            field_name=field_name,
            total_min_chars=BUSINESS_KO_MIN_CONTENT_CHARS,
            shrink_ratio=BUSINESS_SECTION_SHRINK_RATIO,
            min_floor=BUSINESS_SECTION_MIN_FLOOR,
            usage_recorder=usage_recorder,
        )

    for recovery_pass in range(1 + POST_RECOVERY_PASSES):
        try:
            return BusinessPost.model_validate(translated).model_dump()
        except ValidationError as error:
            if recovery_pass >= POST_RECOVERY_PASSES:
                raise

            failed_fields = _extract_failed_fields(
                error,
                {"content_analysis", "content_beginner", "content_learner", "content_expert"},
            )
            if not failed_fields:
                raise

            for field_name in failed_fields:
                if field_name == "content_analysis":
                    translated[field_name] = await _translate_markdown_field(
                        client=client,
                        text=en_data.get(field_name, ""),
                        post_type="business",
                        field_name=field_name,
                        total_min_chars=BUSINESS_KO_MIN_ANALYSIS_CHARS,
                        shrink_ratio=BUSINESS_SECTION_SHRINK_RATIO,
                        min_floor=BUSINESS_SECTION_MIN_FLOOR,
                        recovery=True,
                        usage_recorder=usage_recorder,
                    )
                else:
                    translated[field_name] = await _translate_markdown_field(
                        client=client,
                        text=en_data.get(field_name, ""),
                        post_type="business",
                        field_name=field_name,
                        total_min_chars=BUSINESS_KO_MIN_CONTENT_CHARS,
                        shrink_ratio=BUSINESS_SECTION_SHRINK_RATIO,
                        min_floor=BUSINESS_SECTION_MIN_FLOOR,
                        recovery=True,
                        usage_recorder=usage_recorder,
                    )

    return translated


async def translate_post(
    en_data: dict,
    post_type: str,
    usage_recorder: dict[str, Any] | None = None,
) -> dict:
    """Translate an EN post dict to KO using gpt-4o.

    Args:
        en_data: The English post data as a dict (already validated).
        post_type: "research" or "business".

    Returns:
        A dict with the same structure but text fields translated to Korean.
    """
    client = get_openai_client()

    if post_type == "research":
        translated = await translate_research_post(client, en_data, usage_recorder=usage_recorder)
    elif post_type == "business":
        translated = await translate_business_post(client, en_data, usage_recorder=usage_recorder)
    else:
        raise ValueError(f"Unsupported post_type for translation: {post_type}")

    logger.info(
        "Translated %s post: title=%s",
        post_type,
        translated.get("title", "?")[:80],
    )
    return translated
