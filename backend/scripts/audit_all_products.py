"""Re-score every published product against the current PRODUCT_QUALITY_RUBRIC.

Walks ai_products, calls _score_profile() for each, writes results to
scripts/audit_results.json (sorted worst-first). Use the output to pick
which products need regeneration after rubric/prompt changes.

Run from backend dir:
    .venv/Scripts/python scripts/audit_all_products.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from core.config import settings  # noqa: E402
from core.database import get_supabase  # noqa: E402
from services.agents.client import get_openai_client  # noqa: E402
from services.agents.product_advisor import (  # noqa: E402
    _aggregate_quality_score,
    _score_profile,
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
# Suppress per-call noise; keep our own progress logger at INFO
for noisy in ("httpx", "openai._base_client", "services.agents.client", "services.agents.product_advisor"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger("audit")
logger.setLevel(logging.INFO)


def row_to_profile(row: dict) -> dict:
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


def dim_avgs(score: dict) -> dict:
    out = {}
    for dim in ("specificity", "grounding", "voice", "bilingual"):
        d = score.get(dim) or {}
        out[dim] = d.get("score")
    return out


async def main() -> None:
    sb = get_supabase()
    if not sb:
        print("No supabase client")
        return

    res = sb.table("ai_products").select(
        "slug,name,primary_category,is_published,archived,"
        "tagline,tagline_ko,description,features,features_ko,use_cases,"
        "editor_note,pricing,pricing_detail"
    ).eq("is_published", True).eq("archived", False).order("slug").execute()

    rows = res.data or []
    logger.info("Auditing %d published products", len(rows))

    client = get_openai_client()
    results: list[dict] = []
    total_tokens = 0
    t0 = time.monotonic()

    for i, row in enumerate(rows, 1):
        profile = row_to_profile(row)
        try:
            score, tokens = await _score_profile(
                profile, {}, client, settings.openai_model_nano,
            )
        except Exception as e:
            logger.warning("[%d/%d] %s: scoring exception: %s", i, len(rows), row["slug"], e)
            continue
        total_tokens += tokens
        if not score:
            logger.warning("[%d/%d] %s: empty score", i, len(rows), row["slug"])
            continue
        overall = _aggregate_quality_score(score)
        results.append({
            "slug": row["slug"],
            "name": row.get("name"),
            "primary_category": row.get("primary_category"),
            "overall": overall,
            "dims": dim_avgs(score),
            "top_issue": score.get("top_issue"),
        })
        if i % 10 == 0 or i == len(rows):
            elapsed = time.monotonic() - t0
            logger.info(
                "[%d/%d] tokens=%d elapsed=%.0fs (last: %s -> %d)",
                i, len(rows), total_tokens, elapsed, row["slug"], overall,
            )

    # Sort worst-first
    results.sort(key=lambda r: r["overall"])
    out_path = Path("scripts/audit_results.json")
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # Histogram + leaderboard summary to stdout
    print(f"\n=== AUDIT COMPLETE ===")
    print(f"Scored: {len(results)} products in {time.monotonic() - t0:.0f}s, total tokens: {total_tokens}")
    print(f"Saved: {out_path}\n")

    buckets = [(0, 60), (60, 70), (70, 80), (80, 85), (85, 90), (90, 95), (95, 101)]
    for lo, hi in buckets:
        n = sum(1 for r in results if lo <= r["overall"] < hi)
        bar = "#" * n
        print(f"  {lo:3d}-{hi - 1:3d}: {n:3d} {bar}")

    print("\n=== BOTTOM 30 (worst overall scores) ===")
    print(f"{'overall':>7}  {'spec':>5}  {'grnd':>5}  {'voice':>5}  {'biling':>6}  category    slug")
    for r in results[:30]:
        d = r["dims"]
        print(
            f"  {r['overall']:>5}  "
            f"{(d.get('specificity') or 0):>5}  "
            f"{(d.get('grounding') or 0):>5}  "
            f"{(d.get('voice') or 0):>5}  "
            f"{(d.get('bilingual') or 0):>6}  "
            f"{(r['primary_category'] or '-'):10}  "
            f"{r['slug']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
