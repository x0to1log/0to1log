"""Validate that a quality-only rerun preserved content + hit the cost budget.

Usage:
    python scripts/validate_quality_rerun.py baseline 2026-04-19
    # ... trigger rerun via admin UI ...
    python scripts/validate_quality_rerun.py verify 2026-04-19

Writes baseline to scripts/.quality_rerun_baseline_<batch_id>.json (git-ignored).
Exit code 0 = all criteria pass, 1 = any failure.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SB = create_client(
    os.environ["SUPABASE_URL"],
    os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"),
)

COST_BUDGET_USD = 0.10


def slugs_for(batch_id: str) -> list[str]:
    return [
        f"{batch_id}-research-digest",
        f"{batch_id}-research-digest-ko",
        f"{batch_id}-business-digest",
        f"{batch_id}-business-digest-ko",
    ]


def _sha(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def baseline(batch_id: str, out_path: Path) -> int:
    # Preflight: all 4 slugs must exist
    rows = SB.table("news_posts").select(
        "slug,content_expert,content_learner,analyzed_at,quality_score"
    ).in_("slug", slugs_for(batch_id)).execute().data
    by_slug = {r["slug"]: r for r in rows}
    missing = [s for s in slugs_for(batch_id) if s not in by_slug]
    if missing:
        print(f"FAIL preflight: missing slugs {missing}")
        return 1

    # pipeline_logs cutoff — any row created AFTER this timestamp is from the rerun
    run = SB.table("pipeline_runs").select("id").eq(
        "run_key", f"news-{batch_id}"
    ).single().execute().data
    logs = SB.table("pipeline_logs").select("created_at").eq(
        "run_id", run["id"]
    ).order("created_at", desc=True).limit(1).execute().data
    cutoff = logs[0]["created_at"] if logs else "1970-01-01T00:00:00+00:00"

    snapshot = {
        "batch_id": batch_id,
        "run_id": run["id"],
        "cutoff_created_at": cutoff,
        "slugs": {
            slug: {
                "content_expert_hash": _sha(by_slug[slug].get("content_expert")),
                "content_learner_hash": _sha(by_slug[slug].get("content_learner")),
                "analyzed_at": by_slug[slug].get("analyzed_at"),
                "quality_score": by_slug[slug].get("quality_score"),
            }
            for slug in slugs_for(batch_id)
        },
    }
    out_path.write_text(json.dumps(snapshot, indent=2))
    print(f"OK baseline written: {out_path}")
    print(f"   run_id={run['id']}  cutoff={cutoff}")
    return 0


def verify(batch_id: str, in_path: Path) -> int:
    if not in_path.exists():
        print(f"FAIL: baseline file not found: {in_path}")
        return 1
    base = json.loads(in_path.read_text())

    run_id = base["run_id"]
    cutoff = base["cutoff_created_at"]

    fails: list[str] = []

    # Criterion 1: cost — sum pipeline_logs.cost_usd for rows created AFTER cutoff
    new_logs = SB.table("pipeline_logs").select(
        "pipeline_type,cost_usd,created_at"
    ).eq("run_id", run_id).gt("created_at", cutoff).execute().data
    total_cost = sum((log.get("cost_usd") or 0) for log in new_logs)
    print(f"[cost] rerun logs: {len(new_logs)}  total_cost=${total_cost:.4f}")
    for log in new_logs:
        print(f"   ${log.get('cost_usd') or 0:.4f}  {log['pipeline_type']}  {log['created_at'][-14:-4]}")
    if total_cost > COST_BUDGET_USD:
        fails.append(f"cost ${total_cost:.4f} > budget ${COST_BUDGET_USD}")

    # Criterion 2: no digest:* stages ran in the rerun window (proof writer skipped)
    digest_runs = [log for log in new_logs if str(log["pipeline_type"]).startswith("digest:")]
    if digest_runs:
        fails.append(f"digest stages re-ran: {[l['pipeline_type'] for l in digest_runs]}")

    # Criterion 3: each slug's quality_score + analyzed_at refreshed, both locales
    rows = SB.table("news_posts").select(
        "slug,quality_score,quality_flags,content_analysis,analyzed_at,"
        "content_expert,content_learner"
    ).in_("slug", slugs_for(batch_id)).execute().data
    by_slug = {r["slug"]: r for r in rows}

    for slug in slugs_for(batch_id):
        row = by_slug.get(slug)
        if not row:
            fails.append(f"{slug}: row missing")
            continue
        base_slug = base["slugs"][slug]

        # 3a: quality_score is an int
        qs = row.get("quality_score")
        if not isinstance(qs, int):
            fails.append(f"{slug}: quality_score not int ({qs!r})")

        # 3b: content_analysis has the expected shape
        ca = row.get("content_analysis")
        if not (isinstance(ca, dict) and "scores_breakdown" in ca):
            fails.append(f"{slug}: content_analysis missing scores_breakdown")

        # 3c: analyzed_at refreshed (strictly newer than baseline)
        if not row.get("analyzed_at"):
            fails.append(f"{slug}: analyzed_at missing after rerun")
        elif base_slug["analyzed_at"] and row["analyzed_at"] <= base_slug["analyzed_at"]:
            fails.append(f"{slug}: analyzed_at not refreshed "
                         f"(was {base_slug['analyzed_at']}, is {row['analyzed_at']})")

        # 3d: content_expert / content_learner UNCHANGED (writer skipped)
        now_e = _sha(row.get("content_expert"))
        now_l = _sha(row.get("content_learner"))
        if now_e != base_slug["content_expert_hash"]:
            fails.append(f"{slug}: content_expert CHANGED — writer must have re-run")
        if now_l != base_slug["content_learner_hash"]:
            fails.append(f"{slug}: content_learner CHANGED — writer must have re-run")

    if fails:
        print("\nFAIL — criteria violated:")
        for f in fails:
            print(f"   - {f}")
        return 1
    print("\nOK all criteria passed.")
    return 0


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("baseline", "verify"):
        print("usage: python scripts/validate_quality_rerun.py {baseline|verify} <batch_id>")
        return 2
    mode, batch_id = sys.argv[1], sys.argv[2]
    path = Path(__file__).parent / f".quality_rerun_baseline_{batch_id}.json"
    return baseline(batch_id, path) if mode == "baseline" else verify(batch_id, path)


if __name__ == "__main__":
    sys.exit(main())
