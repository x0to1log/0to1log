"""Analyze or remediate one existing handbook draft by slug.

Dry-run is the default: it only reports deterministic remediation issues.
Pass --apply to run one targeted LLM remediation pass and update the draft row.
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
from services.agents.advisor import remediate_handbook_draft_content


SELECT_COLUMNS = (
    "id,term,slug,korean_name,term_full,korean_full,categories,"
    "summary_ko,summary_en,definition_ko,definition_en,"
    "body_basic_ko,body_basic_en,body_advanced_ko,body_advanced_en,"
    "hero_news_context_ko,hero_news_context_en,references_ko,references_en,"
    "term_type,facet_intent,facet_volatility,status,source"
)

UPDATE_COLUMNS = {
    "korean_name",
    "term_full",
    "korean_full",
    "categories",
    "summary_ko",
    "summary_en",
    "definition_ko",
    "definition_en",
    "body_basic_ko",
    "body_basic_en",
    "body_advanced_ko",
    "body_advanced_en",
    "hero_news_context_ko",
    "hero_news_context_en",
    "references_ko",
    "references_en",
    "term_type",
    "facet_intent",
    "facet_volatility",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remediate one handbook draft by slug.")
    parser.add_argument("--slug", required=True, help="handbook_terms.slug to inspect or update.")
    parser.add_argument("--apply", action="store_true", help="Run LLM remediation and update the draft row.")
    return parser.parse_args()


def _public_update_payload(content: dict) -> dict:
    return {key: content[key] for key in UPDATE_COLUMNS if key in content}


async def main_async() -> int:
    args = parse_args()
    supabase = get_supabase()
    if not supabase:
        raise RuntimeError("Supabase is not configured.")

    result = (
        supabase.table("handbook_terms")
        .select(SELECT_COLUMNS)
        .eq("slug", args.slug)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise RuntimeError(f"No handbook term found for slug={args.slug}")

    row = dict(rows[0])
    term = str(row.get("term") or args.slug)
    remediated, usage, issues, meta = await remediate_handbook_draft_content(
        term,
        row,
        apply_llm=args.apply,
    )

    if args.apply:
        payload = _public_update_payload(remediated)
        supabase.table("handbook_terms").update(payload).eq("id", row["id"]).execute()
        supabase.table("pipeline_logs").insert({
            "pipeline_type": "handbook.remediate_existing",
            "status": "success",
            "input_summary": f"slug={args.slug}",
            "output_summary": f"status={remediated.get('_quality_gate', {}).get('status')}",
            "model_used": usage.get("model_used"),
            "tokens_used": usage.get("tokens_used"),
            "cost_usd": usage.get("cost_usd"),
            "debug_meta": {
                "term": term,
                "slug": args.slug,
                "remediation_status": remediated.get("_remediation_status"),
                "remediation_issues": issues,
                "quality_gate": remediated.get("_quality_gate"),
                "remediation_meta": meta,
                "rollup_usage": usage,
            },
        }).execute()

    print(json.dumps({
        "slug": args.slug,
        "applied": args.apply,
        "remediation_status": remediated.get("_remediation_status"),
        "quality_gate": remediated.get("_quality_gate"),
        "issues": issues,
        "usage": usage,
        "meta": meta,
    }, ensure_ascii=False, indent=2, default=str))
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
