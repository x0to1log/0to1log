"""Directly invoke the advisor for a test term and verify quality_score is saved.

This bypasses the admin endpoint to isolate whether the score save path works.
Will make real OpenAI API calls.

Usage:
    cd backend && python scripts/test_advisor_score_save.py CoT
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402
from models.advisor import HandbookAdviseRequest  # noqa: E402
from services.agents.advisor import run_handbook_advise  # noqa: E402


async def main(term: str) -> None:
    sb = get_supabase()
    if sb is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    # 1. Look up existing term by case-insensitive term or slug
    term_slug = term.lower().replace(" ", "-")
    rows = (
        sb.table("handbook_terms")
        .select("id, slug, term, status, source, definition_ko, body_advanced_ko, term_type")
        .or_(f"slug.eq.{term_slug},term.eq.{term}")
        .limit(5)
        .execute()
        .data or []
    )
    if not rows:
        print(f"ERROR: Term '{term}' not found in handbook_terms. Pass an existing term.")
        sys.exit(1)
    if len(rows) > 1:
        print(f"Multiple matches for '{term}':")
        for r in rows:
            print(f"  id={r['id']}  slug={r['slug']}  term={r['term']}")
        sys.exit(1)

    row = rows[0]
    print(f"\n=== Target term ===")
    print(f"  id:     {row['id']}")
    print(f"  slug:   {row['slug']}")
    print(f"  term:   {row['term']}")
    print(f"  status: {row['status']}")
    print(f"  source: {row['source']}")
    print(f"  type:   {row.get('term_type')}")
    print(f"  def_ko len: {len(row.get('definition_ko') or '')}")
    print(f"  body_adv_ko len: {len(row.get('body_advanced_ko') or '')}")

    # 2. Snapshot current score rows for this term
    before_scores = (
        sb.table("handbook_quality_scores")
        .select("id, score, breakdown, created_at")
        .eq("term_slug", row["slug"])
        .execute()
        .data or []
    )
    print(f"\n=== Before: score rows for '{row['slug']}' ===")
    print(f"  count: {len(before_scores)}")
    for s in before_scores[-3:]:
        bd = s.get("breakdown") or {}
        print(f"    {s['created_at']}  score={s['score']}  level={bd.get('level','?')}  method={bd.get('method','?')}")

    # 3. Record cutoff timestamp
    t0 = datetime.now(timezone.utc)
    print(f"\n=== Invoking run_handbook_advise (action=generate) at {t0.isoformat()} ===")

    req = HandbookAdviseRequest(
        action="generate",
        term_id=row["id"],
        term=row["term"],
    )

    try:
        result, model_used, tokens, warnings = await run_handbook_advise(req)
    except Exception as e:
        print(f"  [X] EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

    t1 = datetime.now(timezone.utc)
    duration = (t1 - t0).total_seconds()
    print(f"\n=== Advisor completed in {duration:.1f}s ===")
    print(f"  model: {model_used}")
    print(f"  tokens: {tokens}")
    print(f"  warnings: {len(warnings)}")
    for w in warnings[:3]:
        print(f"    - {w[:100]}")

    # Quality info from result
    quality = result.get("quality") or {}
    print(f"\n=== Quality in result payload ===")
    for level in ("advanced", "basic"):
        q = quality.get(level) or {}
        print(f"  [{level}] total={q.get('total')}  method={q.get('method')}  semantic={q.get('semantic_score')}  penalty={q.get('structural_penalty')}")

    # 4. Query DB AFTER to see if new rows inserted since t0
    after_scores = (
        sb.table("handbook_quality_scores")
        .select("id, score, breakdown, created_at, source")
        .eq("term_slug", row["slug"])
        .gte("created_at", t0.isoformat())
        .execute()
        .data or []
    )
    print(f"\n=== After: score rows inserted since t0 ===")
    print(f"  count: {len(after_scores)}")
    for s in after_scores:
        bd = s.get("breakdown") or {}
        print(f"    {s['created_at']}  score={s['score']}  level={bd.get('level','?')}  method={bd.get('method','?')}  source={s.get('source')}")

    # 5. Verdict
    print(f"\n=== VERDICT ===")
    if len(after_scores) >= 2:
        print(f"  [OK] HQ-05 appears fixed — {len(after_scores)} new score rows saved")
    elif len(after_scores) == 1:
        print(f"  [PARTIAL] Only 1 row saved (expected 2: advanced + basic)")
    else:
        print(f"  [FAIL] No new score rows inserted. HQ-05 bug still active.")
        print(f"         Advisor computed quality={quality.get('advanced', {}).get('total')}/{quality.get('basic', {}).get('total')}")
        print(f"         but INSERT did not persist — check logger.warning lines in server output")


if __name__ == "__main__":
    term = sys.argv[1] if len(sys.argv) > 1 else "CoT"
    asyncio.run(main(term))
