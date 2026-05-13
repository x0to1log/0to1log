"""Look at the most recent pipeline runs — new drafts and their scores.

Helps verify: does the new pipeline record scores reliably? What's the
quality profile of pipeline-generated content vs manually-created content?

Usage:
    cd backend && python scripts/diagnose_new_pipeline_runs.py
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402


def main() -> None:
    sb = get_supabase()
    if sb is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    # Pull the most recent 10 draft + 10 published terms (any status)
    terms = (
        sb.table("handbook_terms")
        .select("id, slug, term, status, source, term_type, published_at, created_at, updated_at")
        .neq("status", "archived")
        .order("created_at", desc=True)
        .limit(30)
        .execute()
        .data or []
    )

    # Pull most recent score rows
    scores = (
        sb.table("handbook_quality_scores")
        .select("term_slug, term_id, score, breakdown, created_at, source")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data or []
    )

    # Group scores by slug
    scores_by_slug: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for s in scores:
        slug = s.get("term_slug")
        if not slug:
            continue
        level = (s.get("breakdown") or {}).get("level", "unknown")
        scores_by_slug[slug][level].append(s)

    print("\n=== Most recent 30 terms (any status) ===")
    print(f"{'status':<10} {'source':<15} {'created':<12} {'adv':>4} {'basic':>6} {'method':<18} {'term'}")
    print("-" * 110)
    for t in terms:
        slug = t["slug"]
        adv_list = scores_by_slug[slug].get("advanced", [])
        basic_list = scores_by_slug[slug].get("basic", [])
        adv_score = adv_list[0].get("score") if adv_list else None
        basic_score = basic_list[0].get("score") if basic_list else None
        method = ""
        if adv_list:
            method = (adv_list[0].get("breakdown") or {}).get("method", "?")
        adv_str = str(adv_score) if adv_score is not None else "-"
        basic_str = str(basic_score) if basic_score is not None else "-"
        created = (t.get("created_at") or "")[:10]
        status = t.get("status", "?")
        source = t.get("source") or "?"
        print(f"{status:<10} {source:<15} {created:<12} {adv_str:>4} {basic_str:>6} {method:<18} {t['term'][:45]}")

    # Focus on latest pipeline-source drafts
    print("\n=== Pipeline-sourced terms (source=pipeline or batch-regen) ===")
    pipeline_terms = [t for t in terms if t.get("source") and "pipeline" in (t.get("source") or "").lower() or "batch" in (t.get("source") or "").lower()]
    if not pipeline_terms:
        # Also check by source != 'manual'
        pipeline_terms = [t for t in terms if (t.get("source") or "").lower() not in ("manual", "")]
    if not pipeline_terms:
        print("  (no pipeline-tagged terms in recent 30. Check source field values.)")
    else:
        for t in pipeline_terms[:20]:
            slug = t["slug"]
            adv = scores_by_slug[slug].get("advanced", [])
            basic = scores_by_slug[slug].get("basic", [])
            print(f"\n  [{t['status']}] {t['term']} (source={t.get('source')}, type={t.get('term_type')})")
            print(f"    created: {t.get('created_at')}")
            for s in adv:
                bd = s.get("breakdown") or {}
                print(f"    adv:   score={s['score']}  method={bd.get('method','?')}  penalty={bd.get('structural_penalty','?')}  warnings={bd.get('structural_warnings','?')}")
            for s in basic:
                bd = s.get("breakdown") or {}
                print(f"    basic: score={s['score']}  method={bd.get('method','?')}")
            if not adv and not basic:
                print("    [X] NO SCORES RECORDED")

    # Distinct source values
    print("\n=== Distinct `source` values in recent terms ===")
    sources: dict[str, int] = defaultdict(int)
    for t in terms:
        sources[t.get("source") or "(null)"] += 1
    for src, n in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {n}")


if __name__ == "__main__":
    main()
