"""Recompute handbook quality metadata without regenerating handbook content.

Dry-run is the default. Use --apply to insert fresh handbook_quality_scores
rows and a pipeline log. Use --semantic to also run the LLM quality judge;
otherwise the score is structural-only and free.

Examples:
    python scripts/rescore_handbook_quality.py --slug prompt-caching
    python scripts/rescore_handbook_quality.py --slug prompt-caching --apply --semantic
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.database import get_supabase
from services.agents.advisor import (
    _record_handbook_quality_scores,
    rescore_existing_handbook_quality,
)


SELECT_COLUMNS = (
    "id,term,slug,korean_name,term_full,korean_full,categories,"
    "summary_ko,summary_en,definition_ko,definition_en,"
    "body_basic_ko,body_basic_en,body_advanced_ko,body_advanced_en,"
    "hero_news_context_ko,hero_news_context_en,references_ko,references_en,"
    "term_type,facet_intent,facet_volatility,status,source"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rescore existing handbook draft quality by slug.")
    parser.add_argument(
        "--slug",
        action="append",
        required=True,
        help="handbook_terms.slug to inspect or rescore. Repeat for multiple terms.",
    )
    parser.add_argument("--apply", action="store_true", help="Insert fresh score rows and pipeline log.")
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Run the LLM quality judge. Without this, only structural checks run.",
    )
    return parser.parse_args()


def _latest_score_snapshot(sb, slug: str) -> list[dict]:
    rows = (
        sb.table("handbook_quality_scores")
        .select("score,breakdown,created_at,source")
        .eq("term_slug", slug)
        .order("created_at", desc=True)
        .limit(4)
        .execute()
        .data or []
    )
    return [
        {
            "score": row.get("score"),
            "level": (row.get("breakdown") or {}).get("level"),
            "method": (row.get("breakdown") or {}).get("method"),
            "created_at": row.get("created_at"),
            "source": row.get("source"),
        }
        for row in rows
    ]


async def _rescore_one(sb, slug: str, *, apply: bool, semantic: bool) -> dict:
    result = (
        sb.table("handbook_terms")
        .select(SELECT_COLUMNS)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise RuntimeError(f"No handbook term found for slug={slug}")

    row = dict(rows[0])
    term = str(row.get("term") or slug)
    before_scores = _latest_score_snapshot(sb, slug)
    scored, usage, warnings = await rescore_existing_handbook_quality(
        term,
        row,
        run_semantic=semantic,
    )

    inserted = 0
    if apply:
        inserted = _record_handbook_quality_scores(
            sb,
            scored,
            source=str(row.get("source") or "manual"),
        )
        sb.table("pipeline_logs").insert({
            "pipeline_type": "handbook.quality_rescore",
            "status": "success",
            "input_summary": f"slug={slug}",
            "output_summary": f"status={scored.get('_quality_gate', {}).get('status')}",
            "model_used": usage.get("model_used"),
            "tokens_used": usage.get("tokens_used"),
            "cost_usd": usage.get("cost_usd"),
            "debug_meta": {
                "term": term,
                "slug": slug,
                "semantic": semantic,
                "score_rows_inserted": inserted,
                "quality": scored.get("quality"),
                "quality_gate": scored.get("_quality_gate"),
                "remediation_status": scored.get("_remediation_status"),
                "remediation_issues": scored.get("_remediation_issues"),
                "warnings": warnings,
                "rollup_usage": usage,
            },
        }).execute()

    return {
        "slug": slug,
        "term": term,
        "applied": apply,
        "semantic": semantic,
        "score_rows_inserted": inserted,
        "before_scores": before_scores,
        "quality": scored.get("quality"),
        "quality_gate": scored.get("_quality_gate"),
        "issues": scored.get("_remediation_issues"),
        "warnings": warnings,
        "usage": usage,
    }


async def main_async() -> int:
    args = parse_args()
    sb = get_supabase()
    if sb is None:
        raise RuntimeError("Supabase is not configured.")

    results = []
    for slug in args.slug:
        results.append(await _rescore_one(sb, slug, apply=args.apply, semantic=args.semantic))

    print(json.dumps({"results": results}, ensure_ascii=False, indent=2, default=str))
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
