import json
import logging
from typing import Any, Callable

from pydantic import ValidationError

from core.config import settings
from models.business import BusinessPost, MIN_ANALYSIS_CHARS, MIN_CONTENT_CHARS, TARGET_CONTENT_CHARS
from models.ranking import RankedCandidate, RelatedPicks
from services.agents.client import extract_usage_metrics, get_openai_client, parse_ai_json

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
PERSONA_ORDER = ("beginner", "learner", "expert")
StageLogger = Callable[
    [str, str, int, dict[str, Any] | None, str | None, str | None, int | None, float | None],
    None,
]


def _emit_stage(
    stage_logger: StageLogger | None,
    stage_name: str,
    status: str,
    *,
    attempt: int = 0,
    debug_meta: dict[str, Any] | None = None,
    output_summary: str | None = None,
    model_used: str | None = None,
    tokens_used: int | None = None,
    cost_usd: float | None = None,
) -> None:
    if not stage_logger:
        return
    try:
        stage_logger(
            stage_name,
            status,
            attempt,
            debug_meta,
            output_summary,
            model_used,
            tokens_used,
            cost_usd,
        )
    except TypeError:
        stage_logger(stage_name, status, attempt, debug_meta, output_summary)


def _candidate_sources(candidate: RankedCandidate, related: RelatedPicks | None) -> list[str]:
    urls = [candidate.url]
    if related:
        for pick in (related.big_tech, related.industry_biz, related.new_tools):
            if pick and pick.url not in urls:
                urls.append(pick.url)
    return urls


def _build_business_fact_pack_prompt(
    candidate: RankedCandidate,
    related: RelatedPicks | None,
    context: str,
) -> str:
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
        "Create a fact pack and source card set for this business news story.\n"
        "Return JSON only.\n"
        "- fact_pack must contain 3 to 5 items.\n"
        "- Each claim must end with one or more inline markers like [[1]] or [[1]][[2]].\n"
        "- source_cards order defines the citation numbering.\n"
        "- Use only evidence present in the provided sources and context.\n"
        "- Keep claims concrete, verifiable, and non-hype.\n\n"
        f"## Main News\nTitle: {candidate.title}\nURL: {candidate.url}\nSummary: {candidate.snippet}\n"
        f"Ranking reason: {candidate.ranking_reason}\n\n"
        f"## Related News\n{related_block}\n\n"
        f"## Tavily Context\n{context}\n\n"
        "Return this shape:\n"
        '{'
        '"fact_pack":[{"id":"claim-1","claim":"... [[1]]","why_it_matters":"...","source_ids":["src-1"],"confidence":"high"}],'
        '"source_cards":[{"id":"src-1","title":"...","publisher":"...","url":"https://...","published_at":"YYYY-MM-DD","evidence_snippet":"...","claim_ids":["claim-1"]}]}'
    )


def _build_business_analysis_prompt(
    candidate: RankedCandidate,
    batch_id: str,
    fact_pack: dict[str, Any],
    source_urls: list[str],
) -> str:
    return (
        "Write the shared business analysis for this story.\n"
        "Return JSON only.\n"
        f"- content_analysis must be at least {MIN_ANALYSIS_CHARS} chars.\n"
        "- content_analysis must use markdown and start with ## Core Analysis.\n"
        "- Use inline source markers like [[1]] that match the provided source_cards order.\n"
        "- Do not generate persona-specific copy here.\n\n"
        f"## Main News\nTitle: {candidate.title}\nURL: {candidate.url}\nSummary: {candidate.snippet}\n"
        f"Ranking reason: {candidate.ranking_reason}\n\n"
        f"## Fact Pack\n{json.dumps(fact_pack, ensure_ascii=False)}\n\n"
        "Return this shape:\n"
        "{"
        f'"title":"...","slug":"{batch_id}-business-daily","content_analysis":"## Core Analysis\\n...",'
        '"excerpt":"...","focus_items":["...","...","..."],'
        '"guide_items":{"one_liner":"...","action_item":"...","critical_gotcha":"...","rotating_item":"...","quiz_poll":{"question":"...","options":["A","B","C"],"answer":"A","explanation":"..."}},"related_news":{"big_tech":null,"industry_biz":null,"new_tools":null},"source_urls":'
        f"{json.dumps(source_urls)}"
        ',"news_temperature":3,"tags":["..."]}'
    )


def _build_business_persona_prompt(
    persona: str,
    content_analysis: str,
    fact_pack: dict[str, Any],
    source_cards: list[dict[str, Any]],
) -> str:
    headings = {
        "beginner": "## The Story",
        "learner": "## What Happened",
        "expert": "## Executive Summary",
    }
    instructions = {
        "beginner": "Write for a non-technical reader using analogies and practical consequences.",
        "learner": "Write for a junior builder or PM with enough technical context to act.",
        "expert": "Write for a senior technical decision-maker focused on market and strategy.",
    }
    field_name = f"content_{persona}"

    return (
        f"Write the {persona} persona insight article.\n"
        "Return JSON only.\n"
        f"- The response key must be {field_name}.\n"
        f"- {field_name} must be at least {MIN_CONTENT_CHARS} chars.\n"
        f"- {field_name} must start with {headings[persona]}.\n"
        "- Keep the same facts and citations as the shared analysis, but change framing and explanations for the target reader.\n"
        "- Use inline citation markers like [[1]] consistently.\n"
        f"- {instructions[persona]}\n\n"
        f"## Shared Analysis\n{content_analysis}\n\n"
        f"## Fact Pack\n{json.dumps(fact_pack, ensure_ascii=False)}\n\n"
        f"## Source Cards\n{json.dumps(source_cards, ensure_ascii=False)}\n\n"
        f'Return this shape: {{"{field_name}":"{headings[persona]}\\n..."}}'
    )


def _request_retry_prompt(
    base_prompt: str,
    *,
    field_name: str,
    minimum: int,
    previous_data: dict[str, Any] | None,
) -> str:
    if not previous_data:
        return (
            f"{base_prompt}\n\nIMPORTANT: The previous response was rejected.\n"
            f"- {field_name} must be at least {minimum} chars\n"
            f"- target {TARGET_CONTENT_CHARS - 500}-{TARGET_CONTENT_CHARS + 500} chars when this is a persona field\n"
            "- return the full JSON object again\n"
        )

    value = previous_data.get(field_name, "")
    current_length = len(value) if isinstance(value, str) else 0
    return (
        f"{base_prompt}\n\nIMPORTANT: The previous response was rejected.\n"
        f"- {field_name} was {current_length} chars\n"
        f"- minimum required is {minimum} chars\n"
        f"- target {TARGET_CONTENT_CHARS - 500}-{TARGET_CONTENT_CHARS + 500} chars when this is a persona field\n"
        "- deepen the analysis instead of repeating the same sentence\n"
        "- preserve the same facts and citations\n"
        "PREVIOUS_JSON_DRAFT:\n"
        f"{json.dumps(previous_data, ensure_ascii=False)}"
    )


async def _request_json(
    client: Any,
    prompt: str,
    agent_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = await client.chat.completions.create(
        model=settings.openai_model_main,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are 0to1log's AI Business Analyst. "
                    "Respond in valid JSON only. Use concrete, source-backed language."
                ),
            },
            {"role": "user", "content": prompt},
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


async def _generate_stage_with_retry(
    client: Any,
    *,
    prompt: str,
    field_name: str,
    minimum: int,
    agent_name: str,
    stage_name: str,
    stage_logger: StageLogger | None = None,
) -> dict[str, Any]:
    last_data: dict[str, Any] | None = None

    for attempt in range(1 + MAX_RETRIES):
        stage_prompt = prompt if attempt == 0 else _request_retry_prompt(
            prompt,
            field_name=field_name,
            minimum=minimum,
            previous_data=last_data,
        )
        data, usage = await _request_json(client, stage_prompt, agent_name)
        last_data = data
        value = data.get(field_name, "")
        if isinstance(value, str) and len(value) >= minimum:
            _emit_stage(
                stage_logger,
                stage_name,
                "success",
                attempt=attempt,
                debug_meta={field_name: len(value)},
                output_summary=agent_name,
                model_used=usage.get("model_used"),
                tokens_used=usage.get("tokens_used"),
                cost_usd=usage.get("cost_usd"),
            )
            return data
        current_length = len(value) if isinstance(value, str) else 0
        _emit_stage(
            stage_logger,
            stage_name,
            "retry" if attempt < MAX_RETRIES else "failed",
            attempt=attempt,
            debug_meta={
                "field_name": field_name,
                "current_length": current_length,
                "minimum": minimum,
            },
            output_summary=agent_name,
            model_used=usage.get("model_used"),
            tokens_used=usage.get("tokens_used"),
            cost_usd=usage.get("cost_usd"),
        )
        logger.warning(
            "%s validation failed (attempt %d/%d): %s length=%s minimum=%s",
            agent_name,
            attempt + 1,
            1 + MAX_RETRIES,
            field_name,
            current_length,
            minimum,
        )

    return last_data or {}


def _validate_fact_pack_payload(payload: dict[str, Any]) -> None:
    fact_pack = payload.get("fact_pack") or []
    source_cards = payload.get("source_cards") or []
    if not isinstance(fact_pack, list) or not (1 <= len(fact_pack) <= 5):
        raise ValueError("fact_pack must contain 1 to 5 items")
    if not isinstance(source_cards, list) or not source_cards:
        raise ValueError("source_cards must be non-empty")


async def generate_business_post(
    candidate: RankedCandidate,
    related: RelatedPicks | None,
    context: str,
    batch_id: str,
    stage_logger: StageLogger | None = None,
) -> BusinessPost:
    client = get_openai_client()

    fact_pack_data, fact_pack_usage = await _request_json(
        client,
        _build_business_fact_pack_prompt(candidate, related, context),
        "BusinessFactPack",
    )
    try:
        _validate_fact_pack_payload(fact_pack_data)
    except Exception:
        _emit_stage(
            stage_logger,
            "business.fact_pack.en",
            "failed",
            debug_meta={
                "fact_pack_count": len(fact_pack_data.get("fact_pack") or []),
                "source_card_count": len(fact_pack_data.get("source_cards") or []),
            },
            output_summary="BusinessFactPack",
            model_used=fact_pack_usage.get("model_used"),
            tokens_used=fact_pack_usage.get("tokens_used"),
            cost_usd=fact_pack_usage.get("cost_usd"),
        )
        raise
    _emit_stage(
        stage_logger,
        "business.fact_pack.en",
        "success",
        debug_meta={
            "fact_pack_count": len(fact_pack_data.get("fact_pack") or []),
            "source_card_count": len(fact_pack_data.get("source_cards") or []),
        },
        output_summary="BusinessFactPack",
        model_used=fact_pack_usage.get("model_used"),
        tokens_used=fact_pack_usage.get("tokens_used"),
        cost_usd=fact_pack_usage.get("cost_usd"),
    )

    source_urls = _candidate_sources(candidate, related)
    analysis_data = await _generate_stage_with_retry(
        client,
        prompt=_build_business_analysis_prompt(candidate, batch_id, fact_pack_data, source_urls),
        field_name="content_analysis",
        minimum=MIN_ANALYSIS_CHARS,
        agent_name="BusinessAnalysis",
        stage_name="business.analysis.en",
        stage_logger=stage_logger,
    )

    persona_payloads: dict[str, dict[str, Any]] = {}
    for persona in PERSONA_ORDER:
        persona_payloads[persona] = await _generate_stage_with_retry(
            client,
            prompt=_build_business_persona_prompt(
                persona,
                analysis_data.get("content_analysis", ""),
                fact_pack_data.get("fact_pack", []),
                fact_pack_data.get("source_cards", []),
            ),
            field_name=f"content_{persona}",
            minimum=MIN_CONTENT_CHARS,
            agent_name=f"BusinessPersona{persona.title()}",
            stage_name=f"business.persona.{persona}.en",
            stage_logger=stage_logger,
        )

    combined = {
        **analysis_data,
        "content_beginner": persona_payloads["beginner"].get("content_beginner", ""),
        "content_learner": persona_payloads["learner"].get("content_learner", ""),
        "content_expert": persona_payloads["expert"].get("content_expert", ""),
        "fact_pack": fact_pack_data.get("fact_pack", []),
        "source_cards": fact_pack_data.get("source_cards", []),
    }

    try:
        return BusinessPost.model_validate(combined)
    except ValidationError:
        logger.error(
            "Business generation failed after fact pack/persona assembly.\nData: %s",
            json.dumps(combined, ensure_ascii=False)[:1200],
        )
        raise
