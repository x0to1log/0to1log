"""Smoke test: pull the latest news-* run's checkpoints, run
_inject_cp_citations on its digest bodies, and report linkify coverage.

Usage:
    python scripts/smoke_cp_citations.py YYYY-MM-DD
"""

import os
import re
import sys

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(batch_id: str) -> int:
    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"),
    )

    import services.pipeline  # noqa: F401  (populate re-exports)
    from models.news_pipeline import CommunityInsight  # noqa: E402
    from services.pipeline import _inject_cp_citations  # noqa: F401, E402

    run = sb.table("pipeline_runs").select("id").eq("run_key", f"news-{batch_id}").single().execute().data
    if not run:
        print(f"FAIL: no pipeline_run for news-{batch_id}")
        return 1
    run_id = run["id"]

    ckpt = sb.table("pipeline_checkpoints").select("data").eq(
        "run_id", run_id
    ).eq("stage", "community_summarize").execute().data
    if not ckpt:
        print(f"FAIL: no community_summarize checkpoint for {batch_id}")
        return 1
    cmap = {url: CommunityInsight(**ins) for url, ins in (ckpt[0]["data"].get("summaries") or {}).items()}
    print(f"Loaded {len(cmap)} insights")

    # Count insights with URLs (proves the plumbing worked)
    with_hn = sum(1 for i in cmap.values() if i.hn_url)
    with_rd = sum(1 for i in cmap.values() if i.reddit_url)
    print(f"  with hn_url: {with_hn}, with reddit_url: {with_rd}")
    if with_hn == 0 and with_rd == 0:
        print("WARN: no URLs plumbed - is this a pre-plumbing run?")

    # Apply post-processor to each digest body, count linkification
    slugs = [
        f"{batch_id}-research-digest", f"{batch_id}-research-digest-ko",
        f"{batch_id}-business-digest", f"{batch_id}-business-digest-ko",
    ]
    for slug in slugs:
        row = sb.table("news_posts").select("content_expert,content_learner").eq("slug", slug).execute().data
        if not row:
            print(f"  {slug}: no row")
            continue
        body = (row[0]["content_expert"] or "") + "\n" + (row[0]["content_learner"] or "")
        linked = len(re.findall(r">\s*—\s*\[(Hacker News|Reddit|r/\S+?)\]\(http", body))
        raw = len(re.findall(r"^>\s*—\s*(Hacker News|Reddit|r/\S+?)\s*$", body, re.MULTILINE))
        print(f"  {slug}: linked={linked}, raw={raw}")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/smoke_cp_citations.py YYYY-MM-DD")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
