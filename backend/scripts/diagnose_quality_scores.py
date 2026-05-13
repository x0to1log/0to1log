"""Diagnose handbook quality_scores recording health.

Answers:
  1. How many published terms have quality_scores rows?
  2. What's the score distribution (advanced vs basic)?
  3. Any recent published terms missing scores?
  4. Are there any orphan score rows (no matching term)?

Usage:
    cd backend && python scripts/diagnose_quality_scores.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402


def bucket(score: int) -> str:
    if score >= 85: return "85+"
    if score >= 70: return "70-84"
    if score >= 55: return "55-69"
    return "<55"


def main() -> None:
    sb = get_supabase()
    if sb is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    terms = (
        sb.table("handbook_terms")
        .select("id, slug, term, status, published_at, created_at, updated_at")
        .neq("status", "archived")
        .execute()
        .data or []
    )

    scores = (
        sb.table("handbook_quality_scores")
        .select("term_slug, term_id, score, breakdown, created_at, source")
        .execute()
        .data or []
    )

    print(f"\n=== Totals ===")
    print(f"handbook_terms (non-archived): {len(terms)}")
    print(f"  - published: {sum(1 for t in terms if t['status']=='published')}")
    print(f"  - draft:     {sum(1 for t in terms if t['status']=='draft')}")
    print(f"  - queued:    {sum(1 for t in terms if t['status']=='queued')}")
    print(f"handbook_quality_scores: {len(scores)}")

    # Unique slugs with scores
    score_slugs = {s["term_slug"] for s in scores if s.get("term_slug")}
    published_slugs = {t["slug"] for t in terms if t["status"] == "published"}

    missing = published_slugs - score_slugs
    extra = score_slugs - {t["slug"] for t in terms}

    print(f"\n=== Coverage ===")
    print(f"Published terms with score: {len(published_slugs & score_slugs)} / {len(published_slugs)}")
    print(f"Published terms MISSING score: {len(missing)}")
    print(f"Orphan score rows (no matching term): {len(extra)}")

    # Score distribution per level
    print(f"\n=== Score distribution ===")
    dist: dict[str, Counter] = defaultdict(Counter)
    for s in scores:
        level = (s.get("breakdown") or {}).get("level", "unknown")
        score_val = s.get("score")
        if score_val is None:
            continue
        dist[level][bucket(int(score_val))] += 1

    for level in sorted(dist.keys()):
        total = sum(dist[level].values())
        print(f"\n  [{level}] n={total}")
        for b in ["85+", "70-84", "55-69", "<55"]:
            n = dist[level][b]
            pct = (n / total * 100) if total else 0
            bar = "#" * int(pct / 2)
            print(f"    {b:>6}: {n:>4} ({pct:5.1f}%) {bar}")

    # Method distribution (hybrid vs structural-only)
    print(f"\n=== Scoring method ===")
    method_counter: Counter = Counter()
    for s in scores:
        method = (s.get("breakdown") or {}).get("method", "unknown")
        method_counter[method] += 1
    for method, n in method_counter.most_common():
        pct = n / len(scores) * 100 if scores else 0
        print(f"  {method:<20}: {n:>4} ({pct:5.1f}%)")

    # Recent published with/without score
    print(f"\n=== Most recent 20 published terms ===")
    recent_pub = sorted(
        [t for t in terms if t["status"] == "published" and t.get("published_at")],
        key=lambda t: t["published_at"],
        reverse=True,
    )[:20]

    for t in recent_pub:
        has_score = t["slug"] in score_slugs
        marker = "[O]" if has_score else "[X]"
        pub = (t.get("published_at") or "")[:10]
        print(f"  {marker} {pub}  {t['term'][:50]}")

    # Missing list (for HQ-05 bug scope)
    if missing:
        print(f"\n=== Published terms MISSING quality_score ({len(missing)}) ===")
        for t in sorted([t for t in terms if t["slug"] in missing], key=lambda t: t.get("published_at") or "", reverse=True)[:30]:
            pub = (t.get("published_at") or "??")[:10]
            print(f"  {pub}  {t['term'][:60]}")

    # Gap analysis: terms published after score creation vs before
    print(f"\n=== Score age distribution (for published terms with scores) ===")
    score_by_slug: dict[str, list] = defaultdict(list)
    for s in scores:
        if s.get("term_slug"):
            score_by_slug[s["term_slug"]].append(s)

    stale_scores = 0
    fresh_scores = 0
    for t in terms:
        if t["status"] != "published" or t["slug"] not in score_by_slug:
            continue
        term_updated = t.get("updated_at") or t.get("published_at")
        if not term_updated:
            continue
        latest_score = max(s["created_at"] for s in score_by_slug[t["slug"]] if s.get("created_at"))
        if latest_score < term_updated:
            stale_scores += 1
        else:
            fresh_scores += 1
    print(f"  Score newer than term update:  {fresh_scores}")
    print(f"  Score older than term update:  {stale_scores}  (content edited after scoring)")


if __name__ == "__main__":
    main()
