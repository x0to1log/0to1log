"""Regenerate selected product profiles and update ai_products DB row.

Runs `run_product_generate("generate_from_url")` for each listed (slug, url, name),
logs to product_generation_logs automatically, then writes the merged result
back to the ai_products row.

Run from backend dir:
    .venv/Scripts/python scripts/regenerate_products.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time

sys.path.insert(0, ".")

from core.config import settings  # noqa: E402
from core.database import get_supabase  # noqa: E402
from models.product_advisor import ProductGenerateRequest  # noqa: E402
from services.agents.product_advisor import run_product_generate  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("regenerate_products")


TARGETS: list[dict] = [
    {"slug": "elevenlabs", "url": "https://elevenlabs.io/", "name": "ElevenLabs"},
    {"slug": "adobe-firefly", "url": "https://firefly.adobe.com/", "name": "Adobe Firefly"},
    {"slug": "lovable", "url": "https://lovable.dev/", "name": "Lovable"},
]

# Writable fields on ai_products — anything else in the result dict is ignored
WRITABLE_FIELDS = {
    "name", "name_ko", "tagline", "tagline_ko",
    "description", "description_ko",
    "pricing", "pricing_detail", "pricing_detail_ko",
    "platform", "korean_support", "tags",
    "primary_category", "secondary_categories",
    "features", "features_ko",
    "use_cases", "use_cases_ko",
    "getting_started", "getting_started_ko",
    "scenarios", "scenarios_ko",
    "pros_cons", "pros_cons_ko",
    "difficulty", "editor_note", "editor_note_ko",
    "korean_quality_note",
    "search_corpus",
    "logo_url",
}


async def regenerate_one(target: dict) -> dict:
    """Run generation for a single target and write back to DB. Returns summary dict."""
    slug = target["slug"]
    logger.info("=== Regenerating: %s (%s) ===", target["name"], slug)

    req = ProductGenerateRequest(
        action="generate_from_url",
        url=target["url"],
        name=target["name"],
        slug=slug,
    )

    t0 = time.monotonic()
    try:
        result, model_used, tokens_used = await run_product_generate(req)
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        logger.error("generation failed for %s after %dms: %s", slug, elapsed, e)
        return {
            "slug": slug, "success": False, "error": str(e),
            "duration_ms": elapsed,
        }
    elapsed = int((time.monotonic() - t0) * 1000)

    if not isinstance(result, dict) or not result:
        logger.error("empty or invalid result for %s: %r", slug, result)
        return {
            "slug": slug, "success": False, "error": "empty result",
            "duration_ms": elapsed,
        }

    # Map AI response keys to DB column names, then filter to writable fields
    # (EN profile uses description_en; DB column is just 'description'.)
    if "description_en" in result and "description" not in result:
        result["description"] = result["description_en"]
    row_update = {k: v for k, v in result.items() if k in WRITABLE_FIELDS}
    warnings = result.get("_validation_warnings", [])

    sb = get_supabase()
    if not sb:
        logger.error("no supabase client — skipping DB write for %s", slug)
        return {
            "slug": slug, "success": True, "wrote_db": False,
            "duration_ms": elapsed, "tokens_used": tokens_used,
            "warnings": warnings,
        }

    upd = sb.table("ai_products").update(row_update).eq("slug", slug).execute()
    wrote = len(upd.data or [])

    return {
        "slug": slug,
        "success": True,
        "wrote_db": wrote > 0,
        "rows_updated": wrote,
        "duration_ms": elapsed,
        "tokens_used": tokens_used,
        "model_used": model_used,
        "field_count": len(row_update),
        "warnings": warnings,
    }


async def main() -> None:
    logger.info("Starting product regeneration for %d targets", len(TARGETS))
    logger.info("Models: main=%s, light=%s, nano=%s",
                settings.openai_model_main,
                settings.openai_model_light,
                settings.openai_model_nano)

    results: list[dict] = []
    # Sequential to let each one cache warm for the next
    for target in TARGETS:
        summary = await regenerate_one(target)
        results.append(summary)

    logger.info("\n=== SUMMARY ===")
    logger.info("%s", json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
