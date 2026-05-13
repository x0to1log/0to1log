"""Check if 'missing score' terms are actually slug-mismatch cases.

The HQ-05 'missing scores' may be caused by:
  handbook_quality_scores.term_slug = re.sub(...)(req.term)       <- derived
  handbook_terms.slug                = set manually/by pipeline    <- official

If these differ, a simple slug-join makes it LOOK like scores are missing.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402


def term_to_slug(term: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (term or "").lower().strip()).strip("-")


def main() -> None:
    sb = get_supabase()
    terms = (
        sb.table("handbook_terms")
        .select("term, slug, status")
        .eq("status", "published")
        .execute()
        .data or []
    )
    scores = (
        sb.table("handbook_quality_scores")
        .select("term_slug")
        .execute()
        .data or []
    )
    score_slugs = {s["term_slug"] for s in scores if s.get("term_slug")}

    missing = [t for t in terms if t["slug"] not in score_slugs]

    print(f"Published terms without matching quality_scores (by slug): {len(missing)}\n")
    print(f"{'term':<40} {'official slug':<30} {'derived slug':<30} {'found?':<8} {'note'}")
    print("-" * 130)

    actually_missing = 0
    slug_mismatch = 0
    for t in missing:
        derived = term_to_slug(t["term"])
        if derived in score_slugs:
            found = "Y"
            note = "SLUG MISMATCH (score exists under derived slug)"
            slug_mismatch += 1
        else:
            found = "N"
            note = "truly missing"
            actually_missing += 1
        print(f"{t['term'][:40]:<40} {t['slug'][:30]:<30} {derived[:30]:<30} {found:<8} {note}")

    print(f"\n=== Summary ===")
    print(f"  Slug mismatch (score exists but under different key): {slug_mismatch}")
    print(f"  Truly missing (no score anywhere): {actually_missing}")


if __name__ == "__main__":
    main()
