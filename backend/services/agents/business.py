import json
import logging
from copy import deepcopy
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
ArtifactRecorder = Callable[[dict[str, Any], str, str | None, str | None], None]


class BusinessGenerationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        failed_stage: str,
        field_name: str | None = None,
        actual_length: int | None = None,
        minimum: int | None = None,
        partial_state: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.failed_stage = failed_stage
        self.field_name = field_name
        self.actual_length = actual_length
        self.minimum = minimum
        self.partial_state = partial_state or {}


def _format_length_failure_message(field_name: str, actual_length: int, minimum: int) -> str:
    if field_name == "content_analysis":
        return f"Business analysis too short: {actual_length} / {minimum} chars."
    persona = field_name.replace("content_", "").replace("_", " ")
    return f"Business {persona} persona too short: {actual_length} / {minimum} chars."


def _is_complete_markdown_field(value: Any, minimum: int) -> bool:
    return isinstance(value, str) and len(value) >= minimum


def _mark_completed_stage(partial_state: dict[str, Any], stage_name: str) -> None:
    completed_stages = partial_state.setdefault("completed_stages", [])
    if stage_name not in completed_stages:
        completed_stages.append(stage_name)


def _record_partial_state(
    artifact_recorder: ArtifactRecorder | None,
    partial_state: dict[str, Any],
    *,
    status: str,
    failed_stage: str | None = None,
    last_validation_error: str | None = None,
) -> None:
    if not artifact_recorder:
        return
    artifact_recorder(
        deepcopy(partial_state),
        status,
        failed_stage,
        last_validation_error,
    )


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
    current_length = 0

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

    raise BusinessGenerationError(
        _format_length_failure_message(field_name, current_length, minimum),
        failed_stage=stage_name,
        field_name=field_name,
        actual_length=current_length,
        minimum=minimum,
    )


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
    partial_state: dict[str, Any] | None = None,
    artifact_recorder: ArtifactRecorder | None = None,
) -> BusinessPost:
    client = get_openai_client()
    partial_state = deepcopy(partial_state or {})
    partial_state.setdefault(
        "candidate",
        {
            "title": candidate.title,
            "url": candidate.url,
            "batch_id": batch_id,
        },
    )
    partial_state.setdefault("fact_pack", [])
    partial_state.setdefault("source_cards", [])
    partial_state.setdefault("analysis_data", {})
    partial_state.setdefault("persona_payloads", {})
    partial_state.setdefault("completed_stages", [])

    if partial_state["fact_pack"] and partial_state["source_cards"]:
        fact_pack_data = {
            "fact_pack": partial_state["fact_pack"],
            "source_cards": partial_state["source_cards"],
        }
        _mark_completed_stage(partial_state, "business.fact_pack.en")
    else:
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
            _record_partial_state(
                artifact_recorder,
                partial_state,
                status="partial",
                failed_stage="business.fact_pack.en",
                last_validation_error="Business fact pack validation failed.",
            )
            raise
        partial_state["fact_pack"] = fact_pack_data.get("fact_pack", [])
        partial_state["source_cards"] = fact_pack_data.get("source_cards", [])
        _mark_completed_stage(partial_state, "business.fact_pack.en")
        _record_partial_state(artifact_recorder, partial_state, status="partial")
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
    analysis_data = partial_state.get("analysis_data", {})
    if not _is_complete_markdown_field(analysis_data.get("content_analysis"), MIN_ANALYSIS_CHARS):
        try:
            analysis_data = await _generate_stage_with_retry(
                client,
                prompt=_build_business_analysis_prompt(candidate, batch_id, fact_pack_data, source_urls),
                field_name="content_analysis",
                minimum=MIN_ANALYSIS_CHARS,
                agent_name="BusinessAnalysis",
                stage_name="business.analysis.en",
                stage_logger=stage_logger,
            )
        except BusinessGenerationError as exc:
            exc.partial_state = deepcopy(partial_state)
            _record_partial_state(
                artifact_recorder,
                partial_state,
                status="partial",
                failed_stage=exc.failed_stage,
                last_validation_error=str(exc),
            )
            raise
        partial_state["analysis_data"] = analysis_data
        _mark_completed_stage(partial_state, "business.analysis.en")
        _record_partial_state(artifact_recorder, partial_state, status="partial")
    else:
        _mark_completed_stage(partial_state, "business.analysis.en")

    persona_payloads: dict[str, dict[str, Any]] = deepcopy(partial_state.get("persona_payloads", {}))
    for persona in PERSONA_ORDER:
        field_name = f"content_{persona}"
        stage_name = f"business.persona.{persona}.en"
        existing_payload = persona_payloads.get(persona, {})
        if _is_complete_markdown_field(existing_payload.get(field_name), MIN_CONTENT_CHARS):
            _mark_completed_stage(partial_state, stage_name)
            continue
        try:
            persona_payloads[persona] = await _generate_stage_with_retry(
                client,
                prompt=_build_business_persona_prompt(
                    persona,
                    analysis_data.get("content_analysis", ""),
                    fact_pack_data.get("fact_pack", []),
                    fact_pack_data.get("source_cards", []),
                ),
                field_name=field_name,
                minimum=MIN_CONTENT_CHARS,
                agent_name=f"BusinessPersona{persona.title()}",
                stage_name=stage_name,
                stage_logger=stage_logger,
            )
        except BusinessGenerationError as exc:
            partial_state["persona_payloads"] = persona_payloads
            exc.partial_state = deepcopy(partial_state)
            _record_partial_state(
                artifact_recorder,
                partial_state,
                status="partial",
                failed_stage=exc.failed_stage,
                last_validation_error=str(exc),
            )
            raise
        partial_state["persona_payloads"] = persona_payloads
        _mark_completed_stage(partial_state, stage_name)
        _record_partial_state(artifact_recorder, partial_state, status="partial")

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
    except ValidationError as exc:
        partial_state["analysis_data"] = analysis_data
        partial_state["persona_payloads"] = persona_payloads
        errors = exc.errors()
        field_name = str(errors[0]["loc"][0]) if errors and errors[0].get("loc") else "content_analysis"
        actual_length = len(combined.get(field_name, "") or "")
        minimum = MIN_ANALYSIS_CHARS if field_name == "content_analysis" else MIN_CONTENT_CHARS
        message = _format_length_failure_message(field_name, actual_length, minimum)
        _record_partial_state(
            artifact_recorder,
            partial_state,
            status="partial",
            failed_stage=field_name,
            last_validation_error=message,
        )
        logger.error(
            "Business generation failed after fact pack/persona assembly.\nData: %s",
            json.dumps(combined, ensure_ascii=False)[:1200],
        )
        raise BusinessGenerationError(
            message,
            failed_stage=field_name,
            field_name=field_name,
            actual_length=actual_length,
            minimum=minimum,
            partial_state=partial_state,
        ) from exc
