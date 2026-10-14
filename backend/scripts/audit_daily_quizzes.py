"""Audit answer correctness of quizzes on recently published daily digests.

Usage (from backend/):
    python -m scripts.audit_daily_quizzes --days 7
    python -m scripts.audit_daily_quizzes --days 7 --model gpt-6.1-sol

Read-only against Supabase (news_posts select). Writes a JSON report under
output/quiz-audit/. Why this exists: the daily QC rubric scores quiz answer
integrity only in the Beginner prompts, so wrong answers on Expert/Learner
quizzes are never scored (found 2026-10-14 during the GPT-6 A/B).

Each quiz is judged against the same persona + locale body it was written from.
Flagged items need a human look: the judge can be wrong too.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import openai

from core.database import get_supabase
from services.agents.client import get_openai_client
from services.agents.quiz_verifier import verify_quiz

PERSONAS = ("expert", "learner", "beginner")
QUIZ_KEY_PREFIX = "quiz_poll_"
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output" / "quiz-audit"

def structural_quiz_issue(quiz: dict[str, Any]) -> str | None:
    """Deterministic checks that need no model. Returns a description or None."""
    options = quiz.get("options") or []
    answer = quiz.get("answer")
    if answer not in options:
        return f"answer {answer!r} not in options"
    index = quiz.get("answer_index")
    if isinstance(index, int) and (index >= len(options) or options[index] != answer):
        return f"answer_index {index} points to {options[index] if index < len(options) else None!r}, not answer"
    return None


def iter_quizzes(rows: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Yield one item per quiz, paired with the persona body of the same row."""
    for row in rows:
        guide_items = row.get("guide_items") or {}
        for persona in PERSONAS:
            quiz = guide_items.get(f"{QUIZ_KEY_PREFIX}{persona}")
            if not isinstance(quiz, dict):
                continue
            yield {
                "slug": row["slug"],
                "locale": row["locale"],
                "post_type": row.get("post_type"),
                "persona": persona,
                "body": row.get(f"content_{persona}") or "",
                "quiz": quiz,
            }


def fetch_rows(sb: Any, days: int) -> list[dict[str, Any]]:
    return (
        sb.table("news_posts")
        .select("slug,locale,post_type,published_at,content_expert,content_learner,content_beginner,guide_items")
        .in_("post_type", ["research", "business"])
        .eq("status", "published")
        .order("published_at", desc=True)
        .limit(days * 4)  # research + business, EN + KO per day
        .execute()
        .data
        or []
    )


async def judge_quiz(client: Any, model: str, item: dict[str, Any], sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            verdict, usage = await verify_quiz(client, model, item["body"], item["quiz"])
        except openai.RateLimitError:
            verdict, usage = await verify_quiz(client, model, item["body"], item["quiz"], service_tier="default")
    return {**{k: v for k, v in item.items() if k != "body"}, "judge": verdict, "cost_usd": usage.get("cost_usd") or 0.0}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=7, help="most recent published days to audit")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    sb = get_supabase()
    if sb is None:
        raise SystemExit("Supabase unavailable")
    rows = fetch_rows(sb, args.days)
    items = list(iter_quizzes(rows))
    dates = sorted({r["slug"][:10] for r in rows})
    print(f"{len(rows)} published rows ({dates[0] if dates else '-'} .. {dates[-1] if dates else '-'}), {len(items)} quizzes")

    structural = [(i, issue) for i in items if (issue := structural_quiz_issue(i["quiz"]))]
    for item, issue in structural:
        print(f"STRUCTURAL {item['slug']} {item['persona']}: {issue}")

    client = get_openai_client()
    sem = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(*[judge_quiz(client, args.model, i, sem) for i in items], return_exceptions=True)
    failures = [r for r in results if isinstance(r, BaseException)]
    judged = [r for r in results if not isinstance(r, BaseException)]

    print(f"\n{'Persona':<9} {'Total':>5} {'ok':>4} {'wrong':>6} {'ambig':>6} {'ungrnd':>7}")
    for persona in PERSONAS:
        mine = [r for r in judged if r["persona"] == persona]
        counts = {v: sum(1 for r in mine if r["judge"].get("verdict") == v)
                  for v in ("ok", "wrong_answer", "ambiguous", "ungrounded")}
        print(f"{persona:<9} {len(mine):>5} {counts['ok']:>4} {counts['wrong_answer']:>6} "
              f"{counts['ambiguous']:>6} {counts['ungrounded']:>7}")

    flagged = [r for r in judged if r["judge"].get("verdict") != "ok"]
    for r in flagged:
        q = r["quiz"]
        print(f"\n[{r['judge']['verdict']}] {r['slug']} {r['persona']}/{r['locale']}")
        print(f"  Q: {q.get('question')}")
        print(f"  marked: {q.get('answer')}")
        print(f"  better: {r['judge'].get('better_option')}")
        print(f"  why: {r['judge'].get('evidence')}")

    total_cost = sum(r["cost_usd"] for r in judged)
    print(f"\njudged={len(judged)} failed_calls={len(failures)} flagged={len(flagged)} cost=${total_cost:.4f}")
    for f in failures[:5]:
        print(f"  call failed: {type(f).__name__}: {str(f)[:160]}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_ROOT / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{args.model}.json"
    out.write_text(json.dumps({
        "model": args.model, "days": args.days, "structural": [
            {"slug": i["slug"], "persona": i["persona"], "locale": i["locale"], "issue": issue}
            for i, issue in structural
        ], "results": judged,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report: {out}")


if __name__ == "__main__":
    asyncio.run(main())
