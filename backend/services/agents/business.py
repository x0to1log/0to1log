"""Business post generation — v4 Expert-First 2-Call Cascade.

Call 1: generate_business_expert()  → fact_pack + source_cards + analysis + expert + metadata
Call 2: derive_business_personas()  → learner + beginner (derived from expert)
"""

import json
import logging
from typing import Any

from core.config import settings
from models.business import BusinessPost, MIN_ANALYSIS_CHARS, MIN_CONTENT_CHARS
from models.ranking import RankedCandidate, RelatedPicks
from services.agents.client import (
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
)
from services.agents.prompts import BUSINESS_DERIVE_PROMPT, BUSINESS_EXPERT_PROMPT

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
SOFT_FLOOR_RATIO = 0.50  # Accept content ≥ 50% of target after all retries
WARN_RATIO = 0.70        # 50-70% → very_short_content, 70-100% → short_content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candidate_sources(candidate: RankedCandidate, related: RelatedPicks | None) -> list[str]:
    """Collect all source URLs from the main candidate and related picks."""
    urls = [candidate.url]
    if related:
        for pick in (related.big_tech, related.industry_biz, related.new_tools):
            if pick and pick.url not in urls:
                urls.append(pick.url)
    return urls


def _build_expert_user_prompt(
    candidate: RankedCandidate,
    related: RelatedPicks | None,
    context: str,
    batch_id: str,
    source_urls: list[str],
) -> str:
    """Build the user prompt for Call 1 (Expert generation)."""
    related_lines: list[str] = []
    if related:
        if related.big_tech:
            related_lines.append(f"- Big Tech: {related.big_tech.title} ({related.big_tech.url})")
        if related.industry_biz:
            related_lines.append(f"- Industry & Biz: {related.industry_biz.title} ({related.industry_biz.url})")
        if related.new_tools:
            related_lines.append(f"- New Tools: {related.new_tools.title} ({related.new_tools.url})")

    related_block = "\n".join(related_lines) if related_lines else "- None"

    return (
        f"## Main News\nTitle: {candidate.title}\nURL: {candidate.url}\n"
        f"Summary: {candidate.snippet}\nRanking reason: {candidate.ranking_reason}\n\n"
        f"## Related News\n{related_block}\n\n"
        f"## Tavily Context\n{context}\n\n"
        f"## Metadata\n- batch_id: {batch_id}\n- slug: {batch_id}-business-daily\n"
        f"- source_urls: {json.dumps(source_urls)}\n\n"
        "Generate the Expert version with full analytical depth. Return JSON only."
    )


def _build_derive_user_prompt(expert_content: str) -> str:
    """Build the user prompt for Call 2 (Persona derivation)."""
    return (
        "## Expert Version (reference)\n\n"
        f"{expert_content}\n\n"
        "Derive the Learner and Beginner versions from this Expert post. "
        "Same facts, same depth, same length — different writing style. Return JSON only."
    )


async def _call_openai(
    client: Any,
    system_prompt: str,
    user_prompt: str,
    agent_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Make a single OpenAI JSON call and return (parsed_data, usage_metrics)."""
    response = await client.chat.completions.create(
        model=settings.openai_model_main,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=16384,
    )
    raw = response.choices[0].message.content
    return (
        parse_ai_json(raw, agent_name),
        extract_usage_metrics(response, settings.openai_model_main),
    )


# ---------------------------------------------------------------------------
# Call 1: Expert generation
# ---------------------------------------------------------------------------

async def generate_business_expert(
    candidate: RankedCandidate,
    related: RelatedPicks | None,
    context: str,
    batch_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Call 1 — Generate expert version + metadata. Returns (data, usage)."""
    client = get_openai_client()
    source_urls = _candidate_sources(candidate, related)
    user_prompt = _build_expert_user_prompt(candidate, related, context, batch_id, source_urls)

    cumulative_usage: dict[str, Any] = {}
    last_error: Exception | None = None
    last_data: dict[str, Any] | None = None

    for attempt in range(1 + MAX_RETRIES):
        try:
            data, usage = await _call_openai(client, BUSINESS_EXPERT_PROMPT, user_prompt, "BusinessExpert")
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
            last_data = data

            # Validate minimum lengths
            analysis_len = len(data.get("content_analysis") or "")
            expert_len = len(data.get("content_expert") or "")

            if analysis_len < MIN_ANALYSIS_CHARS or expert_len < MIN_CONTENT_CHARS:
                logger.warning(
                    "BusinessExpert attempt %d: analysis=%d/%d, expert=%d/%d",
                    attempt + 1, analysis_len, MIN_ANALYSIS_CHARS, expert_len, MIN_CONTENT_CHARS,
                )
                last_error = ValueError(
                    f"Fields too short: analysis={analysis_len}/{MIN_ANALYSIS_CHARS}, "
                    f"expert={expert_len}/{MIN_CONTENT_CHARS}"
                )
                user_prompt = (
                    f"{user_prompt}\n\n"
                    f"IMPORTANT: Previous response was too short. "
                    f"content_analysis was {analysis_len} chars (min {MIN_ANALYSIS_CHARS}). "
                    f"content_expert was {expert_len} chars (min {MIN_CONTENT_CHARS}). "
                    "Expand the analysis and expert content significantly."
                )
                continue

            logger.info("BusinessExpert success on attempt %d", attempt + 1)
            cumulative_usage["attempts"] = attempt + 1
            return data, cumulative_usage

        except Exception as exc:
            last_error = exc
            logger.warning("BusinessExpert attempt %d failed: %s", attempt + 1, exc)
            if attempt >= MAX_RETRIES:
                break

    # --- Soft-floor fallback: accept if fields ≥ 50% of target ---
    if last_data is not None:
        analysis_len = len(last_data.get("content_analysis") or "")
        expert_len = len(last_data.get("content_expert") or "")
        soft_analysis = int(MIN_ANALYSIS_CHARS * SOFT_FLOOR_RATIO)
        soft_expert = int(MIN_CONTENT_CHARS * SOFT_FLOOR_RATIO)

        if analysis_len >= soft_analysis and expert_len >= soft_expert:
            warnings: list[str] = []
            if analysis_len < int(MIN_ANALYSIS_CHARS * WARN_RATIO) or expert_len < int(MIN_CONTENT_CHARS * WARN_RATIO):
                warnings.append("very_short_content")
            else:
                warnings.append("short_content")
            logger.warning(
                "BusinessExpert: accepting soft-floor result (%s) — "
                "analysis=%d/%d, expert=%d/%d",
                warnings[0], analysis_len, MIN_ANALYSIS_CHARS, expert_len, MIN_CONTENT_CHARS,
            )
            cumulative_usage["attempts"] = 1 + MAX_RETRIES
            cumulative_usage["soft_floor"] = True
            last_data["_quality_warnings"] = warnings
            return last_data, cumulative_usage

    raise ValueError(f"BusinessExpert failed after {1 + MAX_RETRIES} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Call 2: Persona derivation
# ---------------------------------------------------------------------------

async def derive_business_personas(
    expert_content: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Call 2 — Derive learner + beginner from expert. Returns (data, usage)."""
    client = get_openai_client()
    user_prompt = _build_derive_user_prompt(expert_content)

    cumulative_usage: dict[str, Any] = {}
    last_error: Exception | None = None
    last_data: dict[str, Any] | None = None

    for attempt in range(1 + MAX_RETRIES):
        try:
            data, usage = await _call_openai(client, BUSINESS_DERIVE_PROMPT, user_prompt, "BusinessDerive")
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
            last_data = data

            learner_len = len(data.get("content_learner") or "")
            beginner_len = len(data.get("content_beginner") or "")

            if learner_len < MIN_CONTENT_CHARS or beginner_len < MIN_CONTENT_CHARS:
                logger.warning(
                    "BusinessDerive attempt %d: learner=%d/%d, beginner=%d/%d",
                    attempt + 1, learner_len, MIN_CONTENT_CHARS, beginner_len, MIN_CONTENT_CHARS,
                )
                last_error = ValueError(
                    f"Fields too short: learner={learner_len}/{MIN_CONTENT_CHARS}, "
                    f"beginner={beginner_len}/{MIN_CONTENT_CHARS}"
                )
                user_prompt = (
                    f"{user_prompt}\n\n"
                    f"IMPORTANT: Previous response was too short. "
                    f"content_learner was {learner_len} chars (min {MIN_CONTENT_CHARS}). "
                    f"content_beginner was {beginner_len} chars (min {MIN_CONTENT_CHARS}). "
                    "Each version must be a full standalone article of at least 5000 characters."
                )
                continue

            logger.info("BusinessDerive success on attempt %d", attempt + 1)
            cumulative_usage["attempts"] = attempt + 1
            return data, cumulative_usage

        except Exception as exc:
            last_error = exc
            logger.warning("BusinessDerive attempt %d failed: %s", attempt + 1, exc)
            if attempt >= MAX_RETRIES:
                break

    # --- Soft-floor fallback ---
    if last_data is not None:
        learner_len = len(last_data.get("content_learner") or "")
        beginner_len = len(last_data.get("content_beginner") or "")
        soft_content = int(MIN_CONTENT_CHARS * SOFT_FLOOR_RATIO)

        if learner_len >= soft_content and beginner_len >= soft_content:
            warnings: list[str] = []
            warn_content = int(MIN_CONTENT_CHARS * WARN_RATIO)
            if learner_len < warn_content or beginner_len < warn_content:
                warnings.append("very_short_content")
            else:
                warnings.append("short_content")
            logger.warning(
                "BusinessDerive: accepting soft-floor result (%s) — "
                "learner=%d/%d, beginner=%d/%d",
                warnings[0], learner_len, MIN_CONTENT_CHARS, beginner_len, MIN_CONTENT_CHARS,
            )
            cumulative_usage["attempts"] = 1 + MAX_RETRIES
            cumulative_usage["soft_floor"] = True
            last_data["_quality_warnings"] = warnings
            return last_data, cumulative_usage

    raise ValueError(f"BusinessDerive failed after {1 + MAX_RETRIES} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_business_post(
    candidate: RankedCandidate,
    related: RelatedPicks | None,
    context: str,
    batch_id: str,
) -> tuple[BusinessPost, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Generate a complete Business post using the Expert-First 2-Call Cascade.

    Returns (validated BusinessPost, total_usage, expert_usage, derive_usage).
    """
    # Call 1: Expert + metadata
    expert_data, expert_usage = await generate_business_expert(
        candidate, related, context, batch_id,
    )
    expert_warnings = expert_data.pop("_quality_warnings", [])

    # Call 2: Derive learner + beginner from expert
    derive_data, derive_usage = await derive_business_personas(
        expert_data.get("content_expert", ""),
    )
    derive_warnings = derive_data.pop("_quality_warnings", [])

    # Assemble
    combined = {
        **expert_data,
        "content_learner": derive_data.get("content_learner", ""),
        "content_beginner": derive_data.get("content_beginner", ""),
    }

    post = BusinessPost.model_validate(combined)
    total_usage = merge_usage_metrics(expert_usage, derive_usage)

    # Merge quality warnings from both calls into total_usage
    all_warnings = list(dict.fromkeys(expert_warnings + derive_warnings))
    if all_warnings:
        total_usage["_quality_warnings"] = all_warnings

    return post, total_usage, expert_usage, derive_usage
