"""Measure prompt token usage per pipeline stage from pipeline_logs.

Phase 3 Task 1 of 2026-04-15-news-pipeline-hardening.

Computes rolling averages over the last N days to enable before/after
comparison of prompt token reduction work.

Usage:
    cd backend && python scripts/measure_token_usage.py
    cd backend && python scripts/measure_token_usage.py --days 3
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    supabase = get_supabase()
    if supabase is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    rows = (
        supabase.table("pipeline_logs")
        .select("pipeline_type, tokens_used, debug_meta, created_at")
        .gte("created_at", cutoff)
        .execute()
        .data or []
    )

    news_stages = {
        "classify", "merge", "community_summarize", "ranking", "enrich",
        "digest:research:expert", "digest:research:learner",
        "digest:business:expert", "digest:business:learner",
        "quality:research", "quality:business",
    }

    by_stage_total: dict[str, list[int]] = defaultdict(list)
    by_stage_input: dict[str, list[int]] = defaultdict(list)
    by_stage_output: dict[str, list[int]] = defaultdict(list)
    per_day_totals: dict[str, int] = defaultdict(int)

    for r in rows:
        stage = r.get("pipeline_type")
        if stage not in news_stages:
            continue
        total = r.get("tokens_used") or 0
        meta = r.get("debug_meta") or {}
        input_tok = meta.get("input_tokens") or 0
        output_tok = meta.get("output_tokens") or 0
        if total:
            by_stage_total[stage].append(total)
        if input_tok:
            by_stage_input[stage].append(input_tok)
        if output_tok:
            by_stage_output[stage].append(output_tok)
        d = (r.get("created_at") or "")[:10]
        if d and total:
            per_day_totals[d] += total

    print(f"\n=== Token usage over last {args.days} days ===\n")
    print(f"Stages observed: {len(by_stage_total)} / {len(news_stages)}")
    print(f"Daily totals: {dict(sorted(per_day_totals.items()))}\n")

    print(f"{'Stage':<32} {'N':>4} {'Avg total':>11} {'Avg input':>11} {'Avg output':>11}")
    print("-" * 74)
    for stage in sorted(by_stage_total.keys()):
        totals = by_stage_total[stage]
        inputs = by_stage_input.get(stage, [])
        outputs = by_stage_output.get(stage, [])
        avg_total = sum(totals) / len(totals) if totals else 0
        avg_in = sum(inputs) / len(inputs) if inputs else 0
        avg_out = sum(outputs) / len(outputs) if outputs else 0
        print(f"{stage:<32} {len(totals):>4} {avg_total:>11.0f} {avg_in:>11.0f} {avg_out:>11.0f}")

    grand_total_per_day = sum(per_day_totals.values()) / max(len(per_day_totals), 1)
    print(f"\nAverage total tokens per daily run: {grand_total_per_day:.0f}")


if __name__ == "__main__":
    main()
