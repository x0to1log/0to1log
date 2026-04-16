"""Measure prompt failure distribution from past 14 days of news_posts.

Phase 2 Task 1 of 2026-04-15-news-pipeline-hardening.

Identifies which quality categories most frequently fall below threshold,
to target Few-shot example additions in prompts_news_pipeline.py.

Usage:
    cd backend && python scripts/measure_prompt_failures.py
"""
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402


def main() -> None:
    supabase = get_supabase()
    if supabase is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

    rows = (
        supabase.table("news_posts")
        .select("id, slug, post_type, locale, quality_score, fact_pack, pipeline_batch_id, created_at")
        .gte("created_at", cutoff)
        .in_("post_type", ["research", "business"])
        .execute()
        .data or []
    )

    print(f"\n=== Sample size: {len(rows)} digests over 14 days ===\n")

    eligible_count = sum(1 for r in rows if (r.get("fact_pack") or {}).get("auto_publish_eligible"))
    total = max(len(rows), 1)
    print(f"auto_publish_eligible=true: {eligible_count} / {len(rows)} ({eligible_count/total*100:.1f}%)")

    score_buckets: Counter = Counter()
    for r in rows:
        s = r.get("quality_score") or 0
        if s >= 90:
            score_buckets["90+"] += 1
        elif s >= 80:
            score_buckets["80-89"] += 1
        elif s >= 70:
            score_buckets["70-79"] += 1
        else:
            score_buckets["<70"] += 1
    print(f"\nQuality score distribution: {dict(score_buckets)}")

    breakdown_sums: dict[str, list[int]] = defaultdict(list)
    issue_categories: Counter = Counter()
    issue_scopes: Counter = Counter()
    issue_severity: Counter = Counter()
    for r in rows:
        fp = r.get("fact_pack") or {}
        breakdown = fp.get("quality_breakdown") or {}
        for group in ("llm", "deterministic", "raw_llm"):
            for cat, score in (breakdown.get(group) or {}).items():
                breakdown_sums[f"{group}.{cat}"].append(score)
        for issue in (fp.get("quality_issues") or []):
            issue_categories[issue.get("category", "unknown")] += 1
            issue_scopes[issue.get("scope", "unknown")] += 1
            issue_severity[issue.get("severity", "unknown")] += 1

    print("\n=== Mean scores per category ===")
    for cat in sorted(breakdown_sums.keys()):
        scores = breakdown_sums[cat]
        if scores:
            print(f"  {cat}: mean={sum(scores)/len(scores):.1f}, min={min(scores)}, max={max(scores)}, n={len(scores)}")

    print("\n=== Most-flagged issue categories (Top 10) ===")
    for cat, cnt in issue_categories.most_common(10):
        print(f"  {cat}: {cnt}")

    print("\n=== Most-flagged scopes (Top 5) ===")
    for scope, cnt in issue_scopes.most_common(5):
        print(f"  {scope}: {cnt}")

    print("\n=== Issue severity distribution ===")
    for sev, cnt in issue_severity.most_common():
        print(f"  {sev}: {cnt}")

    print("\n=== Cross-tab: scope x category (Top 10 combinations) ===")
    combo_counter: Counter = Counter()
    for r in rows:
        fp = r.get("fact_pack") or {}
        for issue in (fp.get("quality_issues") or []):
            scope = issue.get("scope", "unknown")
            cat = issue.get("category", "unknown")
            combo_counter[f"{scope} + {cat}"] += 1
    for combo, cnt in combo_counter.most_common(10):
        print(f"  {combo}: {cnt}")

    print("\n=== Recommendation ===")
    print("Look at the lowest-mean category AND the most-flagged issue category.")
    print("Top 2 results = candidates for Few-shot example additions in prompts_news_pipeline.py.")


if __name__ == "__main__":
    main()
