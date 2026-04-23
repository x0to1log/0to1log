"""Report prompt-caching hit rate for a pipeline run.

Reads pipeline_logs.debug_meta where _log_stage stashes the
input_tokens / cached_tokens that extract_usage_metrics extracts from
OpenAI's prompt_tokens_details.cached_tokens response field.

Usage:
    python scripts/measure_cached_tokens.py <run_id>
    python scripts/measure_cached_tokens.py --last 1
    python scripts/measure_cached_tokens.py --last 3
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import load_dotenv
from supabase import create_client


def fetch_logs(sb, run_id: str) -> list[dict]:
    return (
        sb.table("pipeline_logs")
        .select("pipeline_type,status,debug_meta,tokens_used,cost_usd,model_used")
        .eq("run_id", run_id)
        .execute()
        .data
        or []
    )


def summarize(logs: list[dict]) -> None:
    per_stage: dict[str, dict[str, int]] = defaultdict(
        lambda: {"input": 0, "cached": 0, "output": 0, "reasoning": 0, "calls": 0, "cost_cents": 0}
    )
    for row in logs:
        debug = row.get("debug_meta") or {}
        stage = row.get("pipeline_type") or "unknown"
        input_tok = int(debug.get("input_tokens") or 0)
        output_tok = int(debug.get("output_tokens") or 0)
        cached_tok = int(debug.get("cached_tokens") or 0)
        reasoning_tok = int(debug.get("reasoning_tokens") or 0)
        cost = row.get("cost_usd")
        cost_cents = int(round(float(cost) * 100)) if cost is not None else 0

        per_stage[stage]["input"] += input_tok
        per_stage[stage]["output"] += output_tok
        per_stage[stage]["cached"] += cached_tok
        per_stage[stage]["reasoning"] += reasoning_tok
        per_stage[stage]["cost_cents"] += cost_cents
        per_stage[stage]["calls"] += 1

    header = (
        f"{'Stage':<42} {'Calls':>5} {'Input':>10} {'Cached':>10} {'Hit%':>5} "
        f"{'Output':>10} {'Reason':>8} {'R%':>5} {'Cost':>7}"
    )
    print(header)
    print("-" * len(header))
    total_input = 0
    total_cached = 0
    total_output = 0
    total_reasoning = 0
    total_cost = 0
    for stage in sorted(per_stage):
        s = per_stage[stage]
        cache_pct = (s["cached"] / s["input"] * 100) if s["input"] else 0.0
        reason_pct = (s["reasoning"] / s["output"] * 100) if s["output"] else 0.0
        cost_dollars = s["cost_cents"] / 100
        print(
            f"{stage:<42} {s['calls']:>5} {s['input']:>10,} {s['cached']:>10,} "
            f"{cache_pct:>4.1f}% {s['output']:>10,} {s['reasoning']:>8,} "
            f"{reason_pct:>4.1f}% ${cost_dollars:>6.2f}"
        )
        total_input += s["input"]
        total_cached += s["cached"]
        total_output += s["output"]
        total_reasoning += s["reasoning"]
        total_cost += s["cost_cents"]

    print("-" * len(header))
    total_cache_pct = (total_cached / total_input * 100) if total_input else 0.0
    total_reason_pct = (total_reasoning / total_output * 100) if total_output else 0.0
    print(
        f"{'TOTAL':<42} {len(logs):>5} {total_input:>10,} {total_cached:>10,} "
        f"{total_cache_pct:>4.1f}% {total_output:>10,} {total_reasoning:>8,} "
        f"{total_reason_pct:>4.1f}% ${total_cost/100:>6.2f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", nargs="?", help="Specific run id (uuid)")
    parser.add_argument("--last", type=int, help="Summarize last N runs")
    args = parser.parse_args()

    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"],
    )

    if args.run_id:
        run_ids_with_keys = [(args.run_id, "?")]
    else:
        n = args.last or 1
        runs = (
            sb.table("pipeline_runs")
            .select("id,run_key,started_at")
            .order("started_at", desc=True)
            .limit(n)
            .execute()
            .data
            or []
        )
        run_ids_with_keys = [(r["id"], r["run_key"]) for r in runs]

    if not run_ids_with_keys:
        print("No runs found.")
        return

    for run_id, run_key in run_ids_with_keys:
        print(f"\n=== {run_key}  run_id={run_id} ===")
        logs = fetch_logs(sb, run_id)
        if not logs:
            print("  (no stage logs)")
            continue
        summarize(logs)


if __name__ == "__main__":
    main()
