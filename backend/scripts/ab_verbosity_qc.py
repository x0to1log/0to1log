"""A/B test: does verbosity="low" shrink evidence fields in weekly quality JSON?

Runs two identical OpenAI calls against the weekly quality-check prompt on the
same weekly-digest content. Only `verbosity` differs:
  - OFF: verbosity parameter omitted
  - ON:  verbosity="low"

Everything else (model, messages, temperature, max_completion_tokens,
response_format, reasoning_effort, service_tier) is held constant. The two
calls run concurrently via asyncio.gather to minimise drift.

Usage (from backend/):
    ./.venv/Scripts/python.exe -m scripts.ab_verbosity_qc [weekly-slug]

If no slug is given, picks the most recent published weekly
(post_type='weekly', status='published', locale='en'). Read-only: no DB writes,
no pipeline_logs, pure stdout.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Force UTF-8 stdout/stderr on Windows so em-dashes and non-ASCII evidence
# strings don't crash print().
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

# Load .env before importing core.config so settings pick up keys.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from core.config import settings  # noqa: E402
from core.database import get_supabase  # noqa: E402
from services.agents.client import (  # noqa: E402
    build_completion_kwargs,
    extract_usage_metrics,
    get_openai_client,
    parse_ai_json,
)
from services.agents.prompts_news_pipeline import QUALITY_CHECK_WEEKLY_EXPERT  # noqa: E402


# Top-level keys that are NOT rubric groups (they're meta fields). Everything
# else is treated as a group if its value is a dict of sub-score dicts.
_NON_GROUP_KEYS = {
    "total_score",
    "score",
    "issues",
    "excerpt",
    "excerpt_ko",
    "focus_items",
    "focus_items_ko",
    "weekly_quiz",
    "weekly_quiz_ko",
}


def _pick_weekly(supabase, explicit_slug: str | None) -> dict[str, Any]:
    """Return the news_posts row for the weekly we'll probe."""
    q = supabase.table("news_posts").select(
        "slug,locale,post_type,status,content_expert,created_at"
    )
    if explicit_slug:
        # Prefer EN version; fall back to whatever exists.
        rows = q.eq("slug", explicit_slug).execute().data or []
        if not rows:
            # Try the -ko variant or strip -ko.
            alt = explicit_slug[:-3] if explicit_slug.endswith("-ko") else f"{explicit_slug}-ko"
            rows = supabase.table("news_posts").select(
                "slug,locale,post_type,status,content_expert,created_at"
            ).eq("slug", alt).execute().data or []
        if not rows:
            raise SystemExit(f"No news_posts row with slug={explicit_slug!r}")
        return rows[0]

    # Default: newest published weekly, EN locale (has content_expert_en).
    rows = (
        q.eq("post_type", "weekly")
        .eq("status", "published")
        .eq("locale", "en")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    ) or []
    if not rows:
        # Relax: try draft too.
        rows = (
            supabase.table("news_posts")
            .select("slug,locale,post_type,status,content_expert,created_at")
            .eq("post_type", "weekly")
            .eq("locale", "en")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        ) or []
    if not rows:
        raise SystemExit("No weekly news_posts found at all.")
    return rows[0]


def _load_ko_body(supabase, en_slug: str) -> str:
    """Fetch the -ko sibling's content_expert (empty string if missing)."""
    ko_slug = f"{en_slug}-ko" if not en_slug.endswith("-ko") else en_slug
    rows = (
        supabase.table("news_posts")
        .select("content_expert")
        .eq("slug", ko_slug)
        .eq("locale", "ko")
        .limit(1)
        .execute()
        .data
    ) or []
    if not rows:
        return ""
    return rows[0].get("content_expert") or ""


async def _one_call(
    client,
    payload: str,
    *,
    with_verbosity_low: bool,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Execute one QC call. Returns (parsed_json, usage_metrics, raw_text)."""
    kwargs = build_completion_kwargs(
        settings.openai_model_reasoning,
        messages=[
            {"role": "system", "content": QUALITY_CHECK_WEEKLY_EXPERT},
            {"role": "user", "content": payload[:35000]},
        ],
        max_tokens=2000,
        response_format={"type": "json_object"},
        reasoning_effort="low",
        service_tier="flex",
        verbosity="low" if with_verbosity_low else None,
    )
    resp = await client.chat.completions.create(**kwargs)
    raw = resp.choices[0].message.content or ""
    parsed = parse_ai_json(raw, f"ab-qc-{'on' if with_verbosity_low else 'off'}")
    usage = extract_usage_metrics(resp, settings.openai_model_reasoning)
    return parsed, usage, raw


def _subscore_rows(data: dict[str, Any]) -> list[tuple[str, str, int | None, str]]:
    """Flatten rubric v2 JSON into [(group, sub_name, score, evidence), ...].

    Auto-discovers groups: any top-level dict whose values are themselves dicts
    with `score` and/or `evidence` keys. Skips known meta keys like `issues`.
    """
    rows: list[tuple[str, str, int | None, str]] = []
    for group_key, group in data.items():
        if group_key in _NON_GROUP_KEYS or not isinstance(group, dict):
            continue
        for sub_key, sub_val in group.items():
            if not isinstance(sub_val, dict):
                continue
            score = sub_val.get("score")
            evidence = sub_val.get("evidence") or sub_val.get("reason") or ""
            if score is None and not evidence:
                continue
            rows.append((group_key, sub_key, score, str(evidence)))
    return rows


def _print_side_by_side(off: dict[str, Any], on: dict[str, Any]) -> None:
    off_rows = {(g, s): (sc, ev) for g, s, sc, ev in _subscore_rows(off)}
    on_rows = {(g, s): (sc, ev) for g, s, sc, ev in _subscore_rows(on)}
    all_keys = sorted(set(off_rows) | set(on_rows))
    for g, s in all_keys:
        off_sc, off_ev = off_rows.get((g, s), (None, ""))
        on_sc, on_ev = on_rows.get((g, s), (None, ""))
        print(f"== {g}.{s} ==")
        print(f"  OFF (score={off_sc}): \"{off_ev}\"")
        print(f"  ON  (score={on_sc}): \"{on_ev}\"")
        off_len = len(off_ev)
        on_len = len(on_ev)
        delta = on_len - off_len
        pct = (delta / off_len * 100.0) if off_len else 0.0
        print(f"     evidence_chars: OFF={off_len} ON={on_len} delta={delta:+d} ({pct:+.1f}%)")
        print()


def _print_issues(label: str, data: dict[str, Any]) -> None:
    issues = data.get("issues") or []
    print(f"  {label} ({len(issues)} items):")
    for it in issues:
        if not isinstance(it, dict):
            print(f"    - {it}")
            continue
        sev = it.get("severity") or "?"
        scope = it.get("scope") or it.get("category") or "?"
        msg = it.get("message") or it.get("description") or ""
        print(f"    [{sev}] ({scope}) {msg}")


async def _main() -> int:
    ap = argparse.ArgumentParser(description="A/B test verbosity=low for weekly QC.")
    ap.add_argument("slug", nargs="?", default=None, help="Optional weekly slug (EN).")
    args = ap.parse_args()

    supabase = get_supabase()
    if supabase is None:
        print("ERROR: Supabase not configured (missing SUPABASE_URL / SUPABASE_SERVICE_KEY).", file=sys.stderr)
        return 2

    row = _pick_weekly(supabase, args.slug)
    en_slug = row["slug"]
    # If the picked row is KO-only, normalize to its EN sibling for readability.
    if row.get("locale") == "ko" and en_slug.endswith("-ko"):
        en_slug = en_slug[:-3]
        # Re-fetch EN.
        en_rows = (
            supabase.table("news_posts")
            .select("slug,locale,post_type,status,content_expert,created_at")
            .eq("slug", en_slug)
            .eq("locale", "en")
            .limit(1)
            .execute()
            .data
        ) or []
        if en_rows:
            row = en_rows[0]

    content_expert_en = row.get("content_expert") or ""
    content_expert_ko = _load_ko_body(supabase, en_slug)

    print("== INPUT ==")
    print(f"  slug       : {en_slug}")
    print(f"  status     : {row.get('status')}")
    print(f"  created_at : {row.get('created_at')}")
    print(f"  EN chars   : {len(content_expert_en)}")
    print(f"  KO chars   : {len(content_expert_ko)}")
    print(f"  model      : {settings.openai_model_reasoning}")
    print()

    if not content_expert_en:
        print("ERROR: content_expert (EN) is empty; cannot run QC.", file=sys.stderr)
        return 3

    payload = (
        f"## English Expert\n\n{content_expert_en}\n\n"
        f"## Korean Expert\n\n{content_expert_ko}"
    )

    client = get_openai_client()
    (off_data, off_usage, _), (on_data, on_usage, _) = await asyncio.gather(
        _one_call(client, payload, with_verbosity_low=False),
        _one_call(client, payload, with_verbosity_low=True),
    )

    print("== SUB-SCORES (OFF vs ON) ==\n")
    _print_side_by_side(off_data, on_data)

    print("== ISSUES ==")
    _print_issues("OFF", off_data)
    _print_issues("ON ", on_data)
    print()

    off_in = off_usage.get("input_tokens") or 0
    off_out = off_usage.get("output_tokens") or 0
    on_in = on_usage.get("input_tokens") or 0
    on_out = on_usage.get("output_tokens") or 0
    reduction = ((off_out - on_out) / off_out * 100.0) if off_out else 0.0

    print("== TOKENS ==")
    print(f"  OFF: input={off_in} output={off_out}")
    print(f"  ON : input={on_in} output={on_out}")
    print(f"  Output reduction: {reduction:.1f}%")
    print()

    # Also dump the raw length summaries for quick eyeballing.
    off_ev_total = sum(len(ev) for _, _, _, ev in _subscore_rows(off_data))
    on_ev_total = sum(len(ev) for _, _, _, ev in _subscore_rows(on_data))
    ev_delta = ((on_ev_total - off_ev_total) / off_ev_total * 100.0) if off_ev_total else 0.0
    print("== EVIDENCE BYTES ==")
    print(f"  OFF total evidence chars : {off_ev_total}")
    print(f"  ON  total evidence chars : {on_ev_total}")
    print(f"  Evidence delta           : {ev_delta:+.1f}%")
    print()

    # Raw JSON dumps at the bottom for full reproducibility.
    print("== RAW JSON (OFF) ==")
    print(json.dumps(off_data, ensure_ascii=False, indent=2))
    print()
    print("== RAW JSON (ON) ==")
    print(json.dumps(on_data, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
