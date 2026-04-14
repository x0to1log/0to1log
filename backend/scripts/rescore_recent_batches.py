"""Rescore news digests for a date range using the current quality pipeline.

Reads existing news_posts rows, reconstructs PersonaOutput + frontload, and
runs `_check_digest_quality` with the current prompts. Does NOT write to
news_posts or pipeline_logs — purely read-only calibration check.

Usage:
    python -m scripts.rescore_recent_batches --start 2026-04-08 --end 2026-04-14
    python -m scripts.rescore_recent_batches --start 2026-04-12 --end 2026-04-12 --verbose
"""
import argparse
import asyncio
import os
import statistics
import sys
from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase
from models.news_pipeline import PersonaOutput
from services import pipeline as pipeline_module


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _fetch_digest_pair(supabase, batch_date: date, post_type: str) -> tuple[dict | None, dict | None]:
    """Return (en_row, ko_row) for a given date+post_type."""
    base_slug = f"{batch_date.isoformat()}-{post_type}-digest"
    rows = (
        supabase.table("news_posts")
        .select(
            "slug, locale, title, excerpt, focus_items, "
            "content_expert, content_learner, quality_score, fact_pack, guide_items"
        )
        .in_("slug", [base_slug, f"{base_slug}-ko"])
        .execute()
    )
    data = rows.data or []
    en_row = next((r for r in data if r["locale"] == "en"), None)
    ko_row = next((r for r in data if r["locale"] == "ko"), None)
    return en_row, ko_row


def _build_inputs(en_row: dict, ko_row: dict) -> tuple[dict[str, PersonaOutput], dict[str, Any]]:
    personas = {
        "expert": PersonaOutput(
            en=en_row.get("content_expert") or "",
            ko=ko_row.get("content_expert") or "",
        ),
        "learner": PersonaOutput(
            en=en_row.get("content_learner") or "",
            ko=ko_row.get("content_learner") or "",
        ),
    }
    frontload = {
        "headline": en_row.get("title") or "",
        "headline_ko": ko_row.get("title") or "",
        "excerpt": en_row.get("excerpt") or "",
        "excerpt_ko": ko_row.get("excerpt") or "",
        "focus_items": en_row.get("focus_items") or [],
        "focus_items_ko": ko_row.get("focus_items") or [],
    }
    return personas, frontload


async def _rescore_one(
    supabase,
    batch_date: date,
    post_type: str,
    verbose: bool,
) -> dict | None:
    en_row, ko_row = _fetch_digest_pair(supabase, batch_date, post_type)
    if not en_row or not ko_row:
        print(f"  {batch_date} {post_type:9s}: missing rows (en={bool(en_row)}, ko={bool(ko_row)})")
        return None

    personas, frontload = _build_inputs(en_row, ko_row)
    old_score = en_row.get("quality_score")

    # Suppress all pipeline_logs writes — this is a read-only rescore.
    result = await pipeline_module._check_digest_quality(
        personas=personas,
        digest_type=post_type,
        classified=[],  # CP-missing penalty unreachable (no classified urls)
        community_summary_map={},  # same
        supabase=supabase,
        run_id="rescore-script",
        cumulative_usage={},
        frontload=frontload,
    )

    if not isinstance(result, dict):
        print(f"  {batch_date} {post_type:9s}: rescore returned {result!r}")
        return None

    new_score = result.get("score")
    breakdown = result.get("quality_breakdown", {})
    llm = breakdown.get("raw_llm", {})
    issue_penalty = result.get("issue_penalty", 0)
    caps = result.get("quality_caps_applied") or []
    delta = (new_score - old_score) if (old_score is not None) else None

    summary_bits = [
        f"old={old_score}" if old_score is not None else "old=?",
        f"new={new_score}",
    ]
    if delta is not None:
        summary_bits.append(f"delta={delta:+d}")
    summary_bits.append(
        f"exp={llm.get('expert_body', 0)} lea={llm.get('learner_body', 0)} front={llm.get('frontload', 0)}"
    )
    summary_bits.append(f"pen=-{issue_penalty}")
    if caps:
        summary_bits.append(f"caps={len(caps)}")

    print(f"  {batch_date} {post_type:9s}: {' '.join(summary_bits)}")

    if verbose:
        issues = result.get("quality_issues") or []
        for issue in issues[:5]:
            sev = issue.get("severity", "?")
            scope = issue.get("scope", "?")
            cat = issue.get("category", "?")
            msg = (issue.get("message") or "").replace("\n", " ")[:140]
            print(f"      [{sev:5s}] {scope:12s} {cat:12s} {msg}")

    return {
        "date": batch_date,
        "post_type": post_type,
        "old": old_score,
        "new": new_score,
        "delta": delta,
        "breakdown": breakdown,
        "issue_penalty": issue_penalty,
        "caps": caps,
    }


def _print_summary(rows: list[dict]) -> None:
    if not rows:
        print("\nNo rows rescored.")
        return

    print("\n=== SUMMARY ===")
    valid = [r for r in rows if r["old"] is not None and r["new"] is not None]
    olds = [r["old"] for r in valid]
    news = [r["new"] for r in valid]
    deltas = [r["delta"] for r in valid if r["delta"] is not None]

    def _stats(label: str, values: list[int]) -> None:
        if not values:
            print(f"  {label}: no data")
            return
        avg = statistics.mean(values)
        print(
            f"  {label}: min={min(values)} max={max(values)} "
            f"mean={avg:.1f} median={statistics.median(values)} n={len(values)}"
        )

    _stats("old scores", olds)
    _stats("new scores", news)
    if deltas:
        _stats("delta", deltas)

    old_pub = sum(1 for v in olds if v >= 85)
    new_pub = sum(1 for v in news if v >= 85)
    print(f"\n  auto-publish (>=85): old={old_pub}/{len(olds)} new={new_pub}/{len(news)}")

    flips_up = [r for r in valid if r["old"] < 85 <= r["new"]]
    flips_down = [r for r in valid if r["new"] < 85 <= r["old"]]
    if flips_up:
        print(f"\n  would now auto-publish ({len(flips_up)}):")
        for r in flips_up:
            print(f"    {r['date']} {r['post_type']:9s} {r['old']} -> {r['new']}")
    if flips_down:
        print(f"\n  would now draft ({len(flips_down)}):")
        for r in flips_down:
            print(f"    {r['date']} {r['post_type']:9s} {r['old']} -> {r['new']}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=_parse_date, required=True)
    parser.add_argument("--end", type=_parse_date, required=True)
    parser.add_argument("--post-types", nargs="+", default=["research", "business"])
    parser.add_argument("--verbose", action="store_true", help="Show top 5 issues per digest")
    args = parser.parse_args()

    # Monkey-patch _log_stage so the rescore doesn't write pipeline_logs rows.
    pipeline_module._log_stage = AsyncMock()

    supabase = get_supabase()
    print(
        f"Rescoring {args.start}..{args.end} "
        f"({(args.end - args.start).days + 1} days × {len(args.post_types)} post_types)"
    )

    rows: list[dict] = []
    for d in _daterange(args.start, args.end):
        print(f"\n{d}:")
        for pt in args.post_types:
            row = await _rescore_one(supabase, d, pt, args.verbose)
            if row:
                rows.append(row)

    _print_summary(rows)


if __name__ == "__main__":
    asyncio.run(main())
