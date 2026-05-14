"""Export existing handbook term slugs for seed curation dedup reference.

Writes `_existing.jsonl` in the handbook-seed-800 workspace. One JSON object
per line with slug/term/term_type/categories/status for each non-archived
handbook term.

Usage:
    cd backend && python scripts/export_handbook_slugs.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402

OUT_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "vault",
        "09-Implementation",
        "plans",
        "2026-04-19-handbook-seed-800",
        "_existing.jsonl",
    )
)

META_LINE = {
    "_meta": True,
    "note": "Existing non-archived handbook terms. Refresh by re-running scripts/export_handbook_slugs.py.",
}


def main() -> None:
    sb = get_supabase()
    if sb is None:
        print("ERROR: Supabase unavailable (check .env)")
        sys.exit(1)

    rows = (
        sb.table("handbook_terms")
        .select("slug, term, term_type, categories, status")
        .neq("status", "archived")
        .execute()
        .data
        or []
    )

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(json.dumps(META_LINE, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} existing terms -> {OUT_PATH}")


if __name__ == "__main__":
    main()
