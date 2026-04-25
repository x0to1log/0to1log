"""Re-score existing ai_products rows against the current PRODUCT_QUALITY_RUBRIC.

No regeneration — just reads the row, calls _score_profile(), prints the
per-dimension breakdown. Use after rubric edits to validate the scoring change
without burning ~21k tokens per product on full regeneration.

Run from backend dir:
    .venv/Scripts/python scripts/rescore_products.py
"""
from __future__ import annotations

import asyncio
import logging
import sys

sys.path.insert(0, ".")

from core.database import get_supabase  # noqa: E402
from core.config import settings  # noqa: E402
from services.agents.client import get_openai_client  # noqa: E402
from services.agents.product_advisor import _score_profile, _aggregate_quality_score  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("rescore_products")

SLUGS = ["hugging-face", "runway-ml", "semantic-scholar"]


def row_to_profile(row: dict) -> dict:
    """Map ai_products row → profile dict shape that _build_quality_summary expects."""
    return {
        "tagline": row.get("tagline") or "",
        "tagline_ko": row.get("tagline_ko") or "",
        "description_en": row.get("description") or "",
        "features": row.get("features") or [],
        "features_ko": row.get("features_ko") or [],
        "use_cases": row.get("use_cases") or [],
        "editor_note": row.get("editor_note") or "",
        "pricing": row.get("pricing"),
        "pricing_detail": row.get("pricing_detail") or "",
    }


async def main() -> None:
    sb = get_supabase()
    if not sb:
        print("No supabase client")
        return

    res = sb.table("ai_products").select(
        "slug,tagline,tagline_ko,description,features,features_ko,use_cases,"
        "editor_note,pricing,pricing_detail"
    ).in_("slug", SLUGS).execute()

    rows = {r["slug"]: r for r in (res.data or [])}
    client = get_openai_client()

    for slug in SLUGS:
        row = rows.get(slug)
        if not row:
            print(f"== {slug}: not found in DB ==\n")
            continue
        profile = row_to_profile(row)
        # facts={} — we don't store technical_specs separately; judge will see
        # an empty specs list, which only affects facts_coverage scoring (already
        # measured in the prior run, not what we're testing here).
        score, tokens = await _score_profile(
            profile, {}, client, settings.openai_model_nano,
        )
        if not score:
            print(f"== {slug}: scoring failed ==\n")
            continue
        overall = _aggregate_quality_score(score)
        print(f"== {slug}: overall={overall}/100 (tokens={tokens}) ==")
        for dim in ("specificity", "grounding", "voice", "bilingual"):
            d = score.get(dim) or {}
            avg = d.get("score")
            subs = {
                k: v.get("score")
                for k, v in d.items()
                if isinstance(v, dict) and "score" in v
            }
            print(f"  {dim}: avg={avg} {subs}")
            # Print evidence quotes for voice dim — that's what we just rewrote
            if dim == "voice":
                for k, v in d.items():
                    if isinstance(v, dict):
                        ev = (v.get("evidence") or "")[:140]
                        print(f"    {k}: {ev!r}")
        print(f"  top_issue: {score.get('top_issue')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
