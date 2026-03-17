"""LLM-based persona content writer agent."""
import asyncio
import logging
from typing import Any

from core.config import settings
from models.news_pipeline import FactPack, PersonaOutput
from services.agents.client import (
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
)
from services.agents.prompts_news_pipeline import (
    get_expert_prompt,
    get_learner_prompt,
)

logger = logging.getLogger(__name__)

MAX_INFRA_RETRIES = 2
BUSINESS_MIN_EN_CHARS = 3000

PERSONA_PROMPT_MAP = {
    "expert": get_expert_prompt,
    "learner": get_learner_prompt,
}


def _build_fact_pack_prompt(fact_pack: FactPack) -> str:
    """Convert FactPack to a user prompt string."""
    parts = [f"## Headline\n{fact_pack.headline}"]

    if fact_pack.key_facts:
        facts_text = "\n".join(
            f"- [{f.id}] {f.claim} (confidence: {f.confidence}, sources: {', '.join(f.source_ids)})"
            for f in fact_pack.key_facts
        )
        parts.append(f"## Key Facts\n{facts_text}")

    if fact_pack.numbers:
        nums_text = "\n".join(
            f"- {n.value}: {n.context} (source: {n.source_id})"
            for n in fact_pack.numbers
        )
        parts.append(f"## Key Numbers\n{nums_text}")

    if fact_pack.entities:
        ents_text = "\n".join(f"- {e.name} ({e.role})" for e in fact_pack.entities)
        parts.append(f"## Entities\n{ents_text}")

    if fact_pack.sources:
        srcs_text = "\n".join(
            f"- [{s.id}] {s.title} — {s.publisher} ({s.url})"
            for s in fact_pack.sources
        )
        parts.append(f"## Sources\n{srcs_text}")

    if fact_pack.community_summary:
        parts.append(f"## Community Reactions\n{fact_pack.community_summary}")

    return "\n\n".join(parts)


async def write_persona(
    persona: str,
    fact_pack: FactPack,
    handbook_slugs: list[str],
    post_type: str = "business",
) -> tuple[PersonaOutput, dict[str, Any]]:
    """Write a single persona's EN+KO content from a FactPack.

    Returns (PersonaOutput, usage_metrics).
    """
    prompt_fn = PERSONA_PROMPT_MAP[persona]
    system_prompt = prompt_fn(handbook_slugs)
    user_prompt = _build_fact_pack_prompt(fact_pack)

    client = get_openai_client()
    model = settings.openai_model_main
    cumulative_usage: dict[str, Any] = {}
    length_retried = False

    for attempt in range(MAX_INFRA_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=16384,
            )
            usage = extract_usage_metrics(response, model)
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

            raw = response.choices[0].message.content
            data = parse_ai_json(raw, f"Persona-{persona}")
            output = PersonaOutput.model_validate(data)

            # Business length check: EN >= 3000 chars
            if (
                post_type == "business"
                and len(output.en) < BUSINESS_MIN_EN_CHARS
                and not length_retried
            ):
                length_retried = True
                logger.warning(
                    "Persona %s EN content too short (%d chars), retrying",
                    persona,
                    len(output.en),
                )
                continue

            logger.info(
                "Persona %s complete: EN=%d chars, KO=%d chars",
                persona,
                len(output.en),
                len(output.ko),
            )
            return output, cumulative_usage

        except Exception as e:
            logger.warning("Persona %s attempt %d failed: %s", persona, attempt + 1, e)
            if attempt == MAX_INFRA_RETRIES:
                raise
            continue

    # Should not reach here, but just in case — return last output
    return output, cumulative_usage  # type: ignore[possibly-undefined]


async def write_all_personas(
    fact_pack: FactPack,
    handbook_slugs: list[str],
    post_type: str = "business",
) -> tuple[dict[str, PersonaOutput], dict[str, Any]]:
    """Write all 3 personas concurrently.

    Returns ({"expert": PersonaOutput, "learner": ..., "beginner": ...}, merged_usage).
    """
    tasks = {
        persona: write_persona(persona, fact_pack, handbook_slugs, post_type)
        for persona in ("expert", "learner", "beginner")
    }

    results_raw = await asyncio.gather(
        *tasks.values(),
        return_exceptions=True,
    )

    results: dict[str, PersonaOutput] = {}
    merged_usage: dict[str, Any] = {}
    errors: list[str] = []

    for persona, result in zip(tasks.keys(), results_raw):
        if isinstance(result, Exception):
            errors.append(f"{persona}: {result}")
            logger.error("Persona %s failed: %s", persona, result)
        else:
            output, usage = result
            results[persona] = output
            merged_usage = merge_usage_metrics(merged_usage, usage)

    if errors:
        logger.warning("Persona errors: %s", errors)

    return results, merged_usage
