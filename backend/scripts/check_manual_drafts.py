"""Verify whether the recent manual drafts without scores have content or not.

This distinguishes HQ-05 (advisor ran but save failed) from "no AI generation
triggered yet" (just an empty shell).

Usage:
    cd backend && python scripts/check_manual_drafts.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402


def main() -> None:
    sb = get_supabase()
    if sb is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    # Recent drafts, with content length checks
    rows = (
        sb.table("handbook_terms")
        .select(
            "slug, term, status, source, term_type, created_at, updated_at, "
            "definition_ko, definition_en, "
            "body_basic_ko, body_basic_en, body_advanced_ko, body_advanced_en"
        )
        .eq("status", "draft")
        .order("created_at", desc=True)
        .limit(15)
        .execute()
        .data or []
    )

    scores = (
        sb.table("handbook_quality_scores")
        .select("term_slug, score, breakdown")
        .execute()
        .data or []
    )
    scored_slugs = {s["term_slug"] for s in scores if s.get("term_slug")}

    print(f"\n=== Recent 15 drafts - content vs score ===\n")
    print(f"{'term':<50} {'source':<10} {'score?':<8} {'def_ko':>8} {'def_en':>8} {'bb_ko':>8} {'ba_ko':>8}")
    print("-" * 110)

    for r in rows:
        slug = r["slug"]
        has_score = "Y" if slug in scored_slugs else "N"
        dko = len(r.get("definition_ko") or "")
        den = len(r.get("definition_en") or "")
        bbko = len(r.get("body_basic_ko") or "")
        bako = len(r.get("body_advanced_ko") or "")
        src = r.get("source") or "?"
        # Flag the HQ-05 case: has content but no score
        flag = ""
        if has_score == "N" and dko > 50:
            flag = "  <-- HQ-05 candidate (content exists, no score)"
        elif has_score == "N":
            flag = "  <-- empty shell (no AI gen run)"
        print(f"{r['term'][:50]:<50} {src:<10} {has_score:<8} {dko:>8} {den:>8} {bbko:>8} {bako:>8}{flag}")


if __name__ == "__main__":
    main()
