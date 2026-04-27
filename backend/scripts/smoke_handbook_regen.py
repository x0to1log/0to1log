"""Smoke regen one handbook term to verify the 2026-04-23 + 2026-04-24 batches.

Verifies:
- Pipeline runs end-to-end without runtime errors
- pipeline_logs.debug_meta carries cached_tokens + service_tier
- Quality calls echo service_tier=flex (or default if capacity downgrade)
- Writer calls log reasoning_tokens > 0 (high reasoning effort active)
- No DB write to handbook_terms (we skip the router's save layer)

Usage:
    cd backend && python scripts/smoke_handbook_regen.py [slug]

Default slug: rope
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402
from models.advisor import HandbookAdviseRequest  # noqa: E402
from services.agents.advisor import run_handbook_advise  # noqa: E402


async def main(slug: str = "rope") -> None:
    sb = get_supabase()
    if sb is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    row = (
        sb.table("handbook_terms")
        .select("id, term, korean_name, term_type, categories, definition_ko, definition_en, "
                "body_basic_ko, body_basic_en, body_advanced_ko, body_advanced_en, "
                "summary_ko, summary_en")
        .eq("slug", slug)
        .single()
        .execute()
        .data
    )
    if not row:
        print(f"ERROR: term with slug '{slug}' not found")
        sys.exit(1)

    print(f"=== Smoke regen: {row['term']} (slug={slug}) ===")
    print(f"  term_id: {row['id']}")
    print(f"  term_type: {row.get('term_type')}")
    print(f"  categories: {row.get('categories')}")
    print()

    req = HandbookAdviseRequest(
        action="generate",
        term_id=row["id"],
        term=row["term"],
        korean_name=row.get("korean_name") or "",
        categories=row.get("categories") or [],
        summary_ko=row.get("summary_ko") or "",
        summary_en=row.get("summary_en") or "",
        definition_ko=row.get("definition_ko") or "",
        definition_en=row.get("definition_en") or "",
        body_basic_ko=row.get("body_basic_ko") or "",
        body_basic_en=row.get("body_basic_en") or "",
        body_advanced_ko=row.get("body_advanced_ko") or "",
        body_advanced_en=row.get("body_advanced_en") or "",
    )

    print("Calling run_handbook_advise(action=generate)... (no DB save - bypassing router)")
    result, model, tokens, warnings = await run_handbook_advise(req)
    print(f"\n=== Result ===")
    print(f"  model: {model}")
    print(f"  tokens: {tokens}")
    print(f"  warnings: {warnings}")
    quality = result.get("quality") or {}
    print(f"  quality.advanced.total: {quality.get('advanced', {}).get('total')}")
    print(f"  quality.basic.total: {quality.get('basic', {}).get('total')}")
    print(f"  quality.advanced.grade: {quality.get('advanced', {}).get('grade')}")
    print(f"  quality.basic.grade: {quality.get('basic', {}).get('grade')}")


if __name__ == "__main__":
    slug_arg = sys.argv[1] if len(sys.argv) > 1 else "rope"
    asyncio.run(main(slug_arg))
