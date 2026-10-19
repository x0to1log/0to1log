"""A/B daily digest generation across model sets without touching production.

Usage (from backend/):
    python -m scripts.ab_daily_models --date 2026-09-27 --check-only
    python -m scripts.ab_daily_models --date 2026-09-27 --arms baseline,A,B

How it stays non-destructive:
  - Production Supabase is only READ: pipeline_runs (run id), pipeline_checkpoints
    (rank / community_summarize / enrich / collect), handbook_terms (slugs).
  - `_generate_digest` (writer + quiz + QC) receives a RecorderClient instead of
    the real client. It touches the DB only through that argument, so every
    news_posts upsert and pipeline_logs insert lands in memory. Any read through
    the recorder raises, so a new hidden DB dependency fails loudly.
  - Handbook extraction is only triggered by run_daily_pipeline, never here.

Both arms replay the SAME checkpoint inputs, so score/cost differences come from
the models, not from re-collected news. classify/merge/rank are not re-run.

Cost is measured by wrapping AsyncCompletions.create and pricing every response
(pipeline_logs alone misses some recovery calls, and daily QC usage is not
merged into the digest's returned usage).

See vault/09-Implementation/plans/2026-10-13-news-pipeline-gpt6-upgrade.md Task 1.4.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections import defaultdict
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from openai.resources.chat.completions import AsyncCompletions

from core.config import settings
from core.database import get_supabase
from models.news_pipeline import ClassifiedGroup, CommunityInsight
from services.agents.client import extract_usage_metrics
from services.pipeline import (
    _build_personas_and_frontload_from_rows,
    _fetch_daily_digest_rows_from_db,
    _fetch_handbook_slugs,
    _generate_digest,
    _load_checkpoint,
)
from services.pipeline_quality import _check_digest_quality

ROLES = ("openai_model_main", "openai_model_light", "openai_model_nano", "openai_model_reasoning")

# Candidate model sets (plan Task 1.4). Roles left out keep the baseline value.
ARMS: dict[str, dict[str, str]] = {
    "baseline": {
        "openai_model_main": "gpt-5",
        "openai_model_light": "gpt-5-mini",
        "openai_model_nano": "gpt-5-nano",
        "openai_model_reasoning": "gpt-5-mini",
    },
    # prod: production since the 2026-10-15 reasoning cutover (gpt-5 writer, sol judge)
    "prod": {
        "openai_model_main": "gpt-5",
        "openai_model_light": "gpt-5-mini",
        "openai_model_nano": "gpt-5-nano",
        "openai_model_reasoning": "gpt-6.1-sol",
    },
    # A: mid model writes, small model does everything else (cheapest)
    "A": {
        "openai_model_main": "gpt-6.1-sol",
        "openai_model_light": "gpt-6-luna",
        "openai_model_nano": "gpt-6-luna",
        "openai_model_reasoning": "gpt-6-luna",
    },
    # A-j5: A's writers with the baseline QC judge. Holding the judge fixed
    # isolates the writer effect (A changed writer and judge at once).
    "A-j5": {
        "openai_model_main": "gpt-6.1-sol",
        "openai_model_light": "gpt-6-luna",
        "openai_model_nano": "gpt-6-luna",
        "openai_model_reasoning": "gpt-5-mini",
    },
    # B: same as A, but the QC judge also uses the mid model
    "B": {
        "openai_model_main": "gpt-6.1-sol",
        "openai_model_light": "gpt-6-luna",
        "openai_model_nano": "gpt-6-luna",
        "openai_model_reasoning": "gpt-6.1-sol",
    },
}

OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output" / "ab-daily-models"


# ---------------------------------------------------------------------------
# In-memory Supabase stand-in
# ---------------------------------------------------------------------------

class _RecorderQuery:
    def __init__(self, recorder: "RecorderClient", table: str, op: str, payload: Any):
        self._recorder = recorder
        self._entry = {"table": table, "op": op, "payload": payload, "filters": []}

    def eq(self, column: str, value: Any) -> "_RecorderQuery":
        self._entry["filters"].append((column, value))
        return self

    def execute(self) -> SimpleNamespace:
        self._recorder.writes.append(self._entry)
        payload = self._entry["payload"]
        return SimpleNamespace(data=payload if isinstance(payload, list) else [payload])


class _RecorderTable:
    def __init__(self, recorder: "RecorderClient", name: str):
        self._recorder = recorder
        self._name = name

    def insert(self, payload: Any, **_: Any) -> _RecorderQuery:
        return _RecorderQuery(self._recorder, self._name, "insert", payload)

    def upsert(self, payload: Any, **_: Any) -> _RecorderQuery:
        return _RecorderQuery(self._recorder, self._name, "upsert", payload)

    def update(self, payload: Any) -> _RecorderQuery:
        return _RecorderQuery(self._recorder, self._name, "update", payload)

    def select(self, *_: Any, **__: Any) -> Any:
        raise RuntimeError(
            f"RecorderClient: unexpected read from '{self._name}'. The digest path "
            "gained a DB read; load it from production before replaying instead."
        )

    def delete(self) -> Any:
        raise RuntimeError(f"RecorderClient: unexpected delete on '{self._name}'")


class RecorderClient:
    """Captures writes in memory. Reads/deletes raise."""

    def __init__(self) -> None:
        self.writes: list[dict[str, Any]] = []

    def table(self, name: str) -> _RecorderTable:
        return _RecorderTable(self, name)

    def rows(self, table: str) -> list[dict[str, Any]]:
        return [w["payload"] for w in self.writes if w["table"] == table]


# ---------------------------------------------------------------------------
# OpenAI call metering
# ---------------------------------------------------------------------------

class CallMeter:
    """Wraps AsyncCompletions.create and prices every response."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._original = AsyncCompletions.create

    def __enter__(self) -> "CallMeter":
        original = self._original
        meter = self

        async def metered_create(self_: Any, *args: Any, **kwargs: Any) -> Any:
            resp = await original(self_, *args, **kwargs)
            usage = getattr(resp, "usage", None)
            if usage is not None:
                metrics = extract_usage_metrics(
                    resp, kwargs.get("model"), requested_service_tier=kwargs.get("service_tier"),
                )
                metrics["requested_model"] = kwargs.get("model")
                metrics["prompt_cache_key"] = kwargs.get("prompt_cache_key")
                metrics["empty_content"] = not (resp.choices and (resp.choices[0].message.content or "").strip())
                meter.calls.append(metrics)
            return resp

        AsyncCompletions.create = metered_create  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: Any) -> None:
        AsyncCompletions.create = self._original  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Checkpoint loading (read-only, mirrors rerun_pipeline_stage write-only path)
# ---------------------------------------------------------------------------

def load_inputs(sb: Any, date: str) -> dict[str, Any]:
    run_key = f"news-{date}"
    runs = (
        sb.table("pipeline_runs").select("id,status").eq("run_key", run_key).execute().data or []
    )
    if not runs:
        raise SystemExit(f"No pipeline_runs row for {run_key}")
    run_id = runs[0]["id"]

    rank = _load_checkpoint(sb, run_id, "rank") or {}
    cs = _load_checkpoint(sb, run_id, "community_summarize") or {}
    enrich = _load_checkpoint(sb, run_id, "enrich") or {}
    missing = [name for name, data in (("rank", rank), ("enrich", enrich)) if not data]
    if missing:
        raise SystemExit(f"{run_key}: missing checkpoints {missing} — cannot replay")

    raw_content_map = enrich.get("raw_content_map") or {}
    if not raw_content_map:
        collect = _load_checkpoint(sb, run_id, "collect") or {}
        raw_content_map = {
            c["url"]: c["raw_content"] for c in collect.get("candidates", []) if c.get("raw_content")
        }

    return {
        "run_key": run_key,
        "source_run_id": run_id,
        "source_status": runs[0]["status"],
        "classified": {
            "research": [ClassifiedGroup(**g) for g in rank.get("research", [])],
            "business": [ClassifiedGroup(**g) for g in rank.get("business", [])],
        },
        "community_summary_map": {
            url: CommunityInsight(**ins) for url, ins in (cs.get("summaries") or {}).items()
        },
        "enriched_map": enrich.get("enriched_map") or {},
        "raw_content_map": raw_content_map,
        "handbook_slugs": _fetch_handbook_slugs(sb),
    }


def describe_inputs(inputs: dict[str, Any]) -> None:
    print(f"source run: {inputs['run_key']} ({inputs['source_status']}) id={inputs['source_run_id']}")
    for digest_type, groups in inputs["classified"].items():
        items = sum(len(g.items) for g in groups)
        print(f"  {digest_type:<9} groups={len(groups)} items={items}")
    print(f"  community insights={len(inputs['community_summary_map'])}")
    print(f"  enriched urls={len(inputs['enriched_map'])} raw_content urls={len(inputs['raw_content_map'])}")
    print(f"  handbook slugs={len(inputs['handbook_slugs'])}")


# ---------------------------------------------------------------------------
# Arm execution
# ---------------------------------------------------------------------------

async def run_arm(arm: str, date: str, inputs: dict[str, Any], types: list[str]) -> dict[str, Any]:
    original = {role: getattr(settings, role) for role in ROLES}
    for role, model in ARMS[arm].items():
        setattr(settings, role, model)
    recorder = RecorderClient()
    run_id = str(uuid.uuid4())
    try:
        with CallMeter() as meter:
            results = await asyncio.gather(*[
                _generate_digest(
                    classified=inputs["classified"][digest_type],
                    digest_type=digest_type,
                    batch_id=date,
                    handbook_slugs=inputs["handbook_slugs"],
                    raw_content_map=inputs["raw_content_map"],
                    community_summary_map=inputs["community_summary_map"],
                    supabase=recorder,
                    run_id=run_id,
                    enriched_map=inputs["enriched_map"],
                    auto_publish=False,
                )
                for digest_type in types
                if inputs["classified"][digest_type]
            ], return_exceptions=True)
    finally:
        for role, model in original.items():
            setattr(settings, role, model)

    errors = []
    for r in results:
        if isinstance(r, BaseException):
            errors.append(f"{type(r).__name__}: {r}")
        else:
            errors.extend(r[1])
    return {"arm": arm, "models": ARMS[arm], "recorder": recorder, "calls": meter.calls, "errors": errors}


def summarize_arm(result: dict[str, Any]) -> dict[str, Any]:
    cost_by_model: dict[str, float] = defaultdict(float)
    for call in result["calls"]:
        cost_by_model[call.get("model_used") or call["requested_model"]] += call.get("cost_usd") or 0.0
    posts = {}
    for row in result["recorder"].rows("news_posts"):
        fact_pack = row.get("fact_pack") or {}
        breakdown = fact_pack.get("quality_breakdown") or {}
        posts[row.get("slug")] = {
            "quality_score": row.get("quality_score", fact_pack.get("quality_score")),
            "raw_llm": breakdown.get("raw_llm"),
            "deterministic": breakdown.get("deterministic"),
            "issues": len(fact_pack.get("quality_issues") or []),
            "caps": fact_pack.get("quality_caps_applied") or [],
        }
    return {
        "arm": result["arm"],
        "models": result["models"],
        "calls": len(result["calls"]),
        "empty_responses": sum(1 for c in result["calls"] if c["empty_content"]),
        "cost_usd": round(sum(cost_by_model.values()), 4),
        "cost_by_model": {k: round(v, 4) for k, v in cost_by_model.items()},
        "failed_stages": [
            row.get("pipeline_type") for row in result["recorder"].rows("pipeline_logs")
            if row.get("status") == "failed"
        ],
        "posts": posts,
        "errors": result["errors"],
    }


def print_comparison(summaries: list[dict[str, Any]]) -> None:
    print("\n=== Cost / reliability ===")
    print(f"{'Arm':<10} {'Calls':>6} {'Empty':>6} {'Cost $':>9}  Failed stages")
    for s in summaries:
        print(f"{s['arm']:<10} {s['calls']:>6} {s['empty_responses']:>6} {s['cost_usd']:>9.4f}  {s['failed_stages'] or '-'}")

    print("\n=== Quality score per post ===")
    slugs = sorted({slug for s in summaries for slug in s["posts"]})
    print(f"{'Slug':<38} " + " ".join(f"{s['arm']:>10}" for s in summaries))
    for slug in slugs:
        cells = []
        for s in summaries:
            post = s["posts"].get(slug)
            cells.append(f"{post['quality_score'] if post else '-':>10}")
        print(f"{slug:<38} " + " ".join(cells))

    for s in summaries:
        if s["errors"]:
            print(f"\n[{s['arm']}] errors:")
            for e in s["errors"]:
                print(f"  - {e[:200]}")


def dump(out_dir: Path, result: dict[str, Any], summary: dict[str, Any]) -> None:
    arm_dir = out_dir / result["arm"]
    arm_dir.mkdir(parents=True, exist_ok=True)
    (arm_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (arm_dir / "calls.json").write_text(json.dumps(result["calls"], ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (arm_dir / "writes.json").write_text(
        json.dumps(result["recorder"].writes, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
    )
    for row in result["recorder"].rows("news_posts"):
        (arm_dir / f"{row.get('slug')}.md").write_text(str(row.get("content_expert") or row), encoding="utf-8")


# ---------------------------------------------------------------------------
# Rescore mode: same saved articles, different QC judges, repeated
# ---------------------------------------------------------------------------

QUIZ_KEY_PREFIX = "quiz_poll_"


def quizzes_from_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Regroup guide_items quizzes into {digest_type: {persona: {locale: quiz}}}.

    Mirrors the persona_quizzes arg _generate_digest hands to _check_digest_quality,
    so a rescore judges exactly what the original QC saw.
    """
    by_type: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        quizzes = by_type.setdefault(row["post_type"], {})
        for key, quiz in (row.get("guide_items") or {}).items():
            if key.startswith(QUIZ_KEY_PREFIX):
                quizzes.setdefault(key[len(QUIZ_KEY_PREFIX):], {})[row["locale"]] = quiz
    return by_type


def load_recorded_rows(arm_dir: Path) -> list[dict[str, Any]]:
    writes = json.loads((arm_dir / "writes.json").read_text(encoding="utf-8"))
    latest: dict[str, dict[str, Any]] = {}
    for entry in writes:
        payload = entry["payload"]
        if entry["table"] == "news_posts" and isinstance(payload, dict) and payload.get("post_type"):
            latest[payload["slug"]] = payload
    return list(latest.values())


async def rescore_once(judge: str, digest_type: str, qc_inputs: dict[str, Any]) -> dict[str, Any]:
    result = await _check_digest_quality(
        personas=qc_inputs["personas"][digest_type],
        digest_type=digest_type,
        classified=qc_inputs["classified"][digest_type],
        community_summary_map=qc_inputs["community_summary_map"],
        supabase=RecorderClient(),
        run_id=str(uuid.uuid4()),
        cumulative_usage={},
        frontload=qc_inputs["frontload"].get(digest_type, {}),
        enriched_map=qc_inputs["enriched_map"],
        raw_content_map=qc_inputs["raw_content_map"],
        persona_quizzes=qc_inputs["quizzes"].get(digest_type, {}),
    )
    if not isinstance(result, dict):
        return {"judge": judge, "type": digest_type, "score": None, "error": f"non-dict QC result: {result!r}"}
    breakdown = result.get("quality_breakdown") or {}
    return {
        "judge": judge,
        "type": digest_type,
        "score": int(result.get("score") or result.get("quality_score") or 0),
        "caps": result.get("quality_caps_applied") or [],
        "raw_llm": breakdown.get("raw_llm"),
        "major_issues": [
            i.get("message", "")[:160] for i in result.get("quality_issues") or [] if i.get("severity") == "major"
        ],
        "issue_count": len(result.get("quality_issues") or []),
    }


def expand_date_range(spec: str) -> list[str]:
    """"2026-09-15:2026-09-17" -> each date inclusive; a single date passes through."""
    first, _, last = spec.partition(":")
    day = date_cls.fromisoformat(first)
    end = date_cls.fromisoformat(last or first)
    dates = []
    while day <= end:
        dates.append(day.isoformat())
        day += timedelta(days=1)
    return dates


def _cap_value(cap: str) -> int | None:
    tail = cap.rsplit("_", 1)[-1]
    return int(tail) if tail.isdigit() else None


def summarize_threshold(runs: list[dict[str, Any]], *, threshold: int, baseline_judge: str) -> dict[str, Any]:
    """Pass rates per judge, and posts the baseline judge passes but another blocks.

    cap_blocked counts runs held below threshold by a cap set under it (the
    84 caps exist to block auto-publish on major issues).
    """
    scored = [r for r in runs if r.get("score") is not None]
    by_judge: dict[str, dict[str, Any]] = {}
    for judge in dict.fromkeys(r["judge"] for r in scored):
        mine = [r for r in scored if r["judge"] == judge]
        by_judge[judge] = {
            "n": len(mine),
            "mean": round(sum(r["score"] for r in mine) / len(mine), 1),
            "pass": sum(1 for r in mine if r["score"] >= threshold),
            "cap_blocked": sum(
                1 for r in mine
                if r["score"] < threshold and any((_cap_value(c) or 100) < threshold for c in r["caps"])
            ),
        }
    baseline = {(r["date"], r["type"]): r["score"] for r in scored if r["judge"] == baseline_judge}
    newly_blocked: dict[str, list[dict[str, Any]]] = {}
    for judge in by_judge:
        if judge == baseline_judge:
            continue
        newly_blocked[judge] = [
            {"date": r["date"], "type": r["type"], "baseline": baseline[(r["date"], r["type"])],
             "score": r["score"], "caps": r["caps"], "major_issues": r["major_issues"]}
            for r in scored
            if r["judge"] == judge and r["score"] < threshold
            and baseline.get((r["date"], r["type"]), 0) >= threshold
        ]
    return {"threshold": threshold, "baseline_judge": baseline_judge,
            "by_judge": by_judge, "newly_blocked": newly_blocked}


async def rescore_rows(
    date: str, rows: list[dict[str, Any]], judges: list[str], repeats: int, types: list[str],
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Re-run QC on saved digest rows once per judge x repeat. Never writes to Supabase."""
    personas, frontload = _build_personas_and_frontload_from_rows(rows)
    sb = get_supabase()
    if sb is None:
        raise SystemExit("Supabase unavailable")
    inputs = load_inputs(sb, date)
    qc_inputs = {**inputs, "personas": personas, "frontload": frontload, "quizzes": quizzes_from_rows(rows)}
    types = [t for t in types if t in personas]

    original_judge = settings.openai_model_reasoning
    runs: list[dict[str, Any]] = []
    costs: dict[str, float] = {}
    try:
        # Judges run sequentially (settings is process-global); repeats in parallel.
        for judge in judges:
            settings.openai_model_reasoning = judge
            with CallMeter() as meter:
                runs += await asyncio.gather(*[
                    rescore_once(judge, t, qc_inputs) for t in types for _ in range(repeats)
                ])
            costs[judge] = round(sum(c.get("cost_usd") or 0.0 for c in meter.calls), 4)
    finally:
        settings.openai_model_reasoning = original_judge
    for run in runs:
        run["date"] = date
    return runs, costs


async def run_rescore(arm_dir: Path, judges: list[str], repeats: int, types: list[str]) -> None:
    rows = load_recorded_rows(arm_dir)
    if not rows:
        raise SystemExit(f"No recorded news_posts rows in {arm_dir / 'writes.json'}")
    date = rows[0]["pipeline_batch_id"]
    print(f"rescoring {arm_dir} ({date}) types={types} judges={judges} repeats={repeats}")
    runs, costs = await rescore_rows(date, rows, judges, repeats, types)

    print(f"\n{'Judge':<14} {'Type':<9} {'Scores':<18} {'Spread':>6} {'Capped':>7} {'Cost $':>8}")
    for judge in judges:
        for t in types:
            mine = [r for r in runs if r["judge"] == judge and r["type"] == t and r["score"] is not None]
            scores = [r["score"] for r in mine]
            spread = max(scores) - min(scores) if scores else 0
            capped = sum(1 for r in mine if r["caps"])
            print(f"{judge:<14} {t:<9} {str(scores):<18} {spread:>6} {capped:>4}/{len(mine):<2} {costs[judge]:>8.4f}")

    out = arm_dir / f"rescore-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps({"judges": judges, "repeats": repeats, "costs": costs, "runs": runs},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetails (raw_llm, caps, major issues per run): {out}")


async def run_rescore_production(dates: list[str], judges: list[str], types: list[str]) -> None:
    """Re-judge published production digests per date; read-only (Task 1.7)."""
    sb = get_supabase()
    if sb is None:
        raise SystemExit("Supabase unavailable")
    all_runs: list[dict[str, Any]] = []
    stored: dict[tuple[str, str], Any] = {}
    total_cost: dict[str, float] = {}
    for date in dates:
        rows = _fetch_daily_digest_rows_from_db(sb, date)
        if not rows:
            print(f"{date}: no digest rows, skipped")
            continue
        for row in rows:
            if row.get("locale") == "en":
                stored[(date, row["post_type"])] = (row.get("fact_pack") or {}).get("quality_score")
        try:
            runs, costs = await rescore_rows(date, rows, judges, 1, types)
        except SystemExit as exc:
            print(f"{date}: skipped ({exc})")
            continue
        all_runs += runs
        for judge, cost in costs.items():
            total_cost[judge] = round(total_cost.get(judge, 0.0) + cost, 4)
        line = "  ".join(
            f"{r['type'][:3]}/{r['judge']}={r['score']}" for r in sorted(runs, key=lambda r: (r["type"], r["judge"]))
        )
        print(f"{date}: {line}")

    threshold = settings.auto_publish_threshold
    summary = summarize_threshold(all_runs, threshold=threshold, baseline_judge=judges[0])
    print(f"\n=== threshold {threshold} (baseline judge: {judges[0]}) ===")
    print(f"{'Judge':<14} {'n':>3} {'mean':>6} {'pass':>6} {'cap-blocked':>12} {'cost $':>8}")
    for judge, row in summary["by_judge"].items():
        print(f"{judge:<14} {row['n']:>3} {row['mean']:>6} {row['pass']:>3}/{row['n']:<2} "
              f"{row['cap_blocked']:>12} {total_cost.get(judge, 0.0):>8.4f}")
    for judge, posts in summary["newly_blocked"].items():
        print(f"\nPassed by {judges[0]} but blocked by {judge}: {len(posts)}")
        for post in posts:
            print(f"  {post['date']} {post['type']}: {post['baseline']} -> {post['score']} caps={post['caps']}")
            for issue in post["major_issues"]:
                print(f"      MAJOR: {issue}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_ROOT / f"threshold-{dates[0]}_{dates[-1]}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps({
        "judges": judges, "stored_scores": {f"{d}/{t}": v for (d, t), v in stored.items()},
        "costs": total_cost, "summary": summary, "runs": all_runs,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetails: {out}")


def weekly_slugs(week_id: str) -> tuple[str, str]:
    """"2026-W38" -> EN and KO weekly digest slugs."""
    base = f"{week_id.lower()}-weekly-digest"
    return base, f"{base}-ko"


async def run_rescore_weeks(week_ids: list[str], judges: list[str]) -> None:
    """Re-judge published weekly digests with each QC model; read-only (Task 1.5a)."""
    from services.pipeline_persistence import _fetch_week_digests
    from services.pipeline_quality import _check_weekly_quality, passes_auto_publish_gate

    sb = get_supabase()
    if sb is None:
        raise SystemExit("Supabase unavailable")
    runs: list[dict[str, Any]] = []
    total_cost: dict[str, float] = {}
    original_judge = settings.openai_model_reasoning
    try:
        for week_id in week_ids:
            en_slug, ko_slug = weekly_slugs(week_id)
            rows = {
                r["locale"]: r for r in sb.table("news_posts")
                .select("slug,locale,status,quality_score,content_expert,content_learner")
                .in_("slug", [en_slug, ko_slug]).execute().data or []
            }
            if "en" not in rows or "ko" not in rows:
                print(f"{week_id}: weekly rows missing, skipped")
                continue
            digests = await _fetch_week_digests(sb, week_id, "en") + await _fetch_week_digests(sb, week_id, "ko")
            source_urls = list(dict.fromkeys(
                card["url"] for d in digests for card in (d.get("source_cards") or []) if card.get("url")
            ))
            for judge in judges:
                settings.openai_model_reasoning = judge
                with CallMeter() as meter:
                    result = await _check_weekly_quality(
                        content_expert_en=rows["en"].get("content_expert") or "",
                        content_learner_en=rows["en"].get("content_learner") or "",
                        content_expert_ko=rows["ko"].get("content_expert") or "",
                        content_learner_ko=rows["ko"].get("content_learner") or "",
                        source_urls=source_urls,
                        supabase=RecorderClient(),
                        run_id=str(uuid.uuid4()),
                        cumulative_usage={},
                    )
                cost = sum(c.get("cost_usd") or 0.0 for c in meter.calls)
                total_cost[judge] = round(total_cost.get(judge, 0.0) + cost, 4)
                breakdown = result.get("quality_breakdown") or {}
                runs.append({
                    "date": week_id, "type": "weekly", "judge": judge,
                    "stored": rows["en"].get("quality_score"), "status": rows["en"].get("status"),
                    "score": result.get("quality_score"),
                    "caps": result.get("quality_caps_applied") or [],
                    "llm": breakdown.get("llm"),
                    "major_issues": [
                        i.get("message", "")[:200] for i in result.get("quality_issues") or []
                        if i.get("severity") == "major"
                    ],
                    "url_validation_failed": "url_validation_failed" in (result.get("quality_flags") or []),
                })
    finally:
        settings.openai_model_reasoning = original_judge

    print(f"\n{'Week':<10} {'Judge':<13} {'stored':>6} {'score':>6}  gate@85 gate@70  caps")
    original_threshold = settings.auto_publish_threshold
    try:
        for r in runs:
            gates = []
            for threshold in (85, 70):
                settings.auto_publish_threshold = threshold
                ok = passes_auto_publish_gate(r["score"], r["caps"]) and not r["url_validation_failed"]
                gates.append("pass" if ok else "draft")
            print(f"{r['date']:<10} {r['judge']:<13} {str(r['stored']):>6} {str(r['score']):>6}  "
                  f"{gates[0]:<7} {gates[1]:<7} {r['caps'] or '-'}")
            for issue in r["major_issues"]:
                print(f"      MAJOR: {issue}")
    finally:
        settings.auto_publish_threshold = original_threshold
    print(f"\ncost: {total_cost}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_ROOT / f"weekly-rescore-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps({"judges": judges, "costs": total_cost, "runs": runs},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Details: {out}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", help="batch date with saved checkpoints, e.g. 2026-09-27")
    parser.add_argument("--arms", default="baseline,A,B", help=f"comma-separated, from {list(ARMS)}")
    parser.add_argument("--types", default="research,business")
    parser.add_argument("--check-only", action="store_true", help="load checkpoints only; no OpenAI calls")
    parser.add_argument("--rescore", type=Path, help="arm output dir to re-judge (skips generation)")
    parser.add_argument("--judges", default="gpt-6-luna,gpt-6.1-sol,gpt-5-mini")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--rescore-dates",
        help="re-judge published production digests, e.g. 2026-09-15:2026-10-14 (first judge = baseline)",
    )
    parser.add_argument("--rescore-weeks", help="re-judge published weekly digests, e.g. 2026-W37,2026-W38")
    args = parser.parse_args()

    if args.rescore_weeks:
        judges = [j.strip() for j in args.judges.split(",") if j.strip()]
        await run_rescore_weeks([w.strip() for w in args.rescore_weeks.split(",") if w.strip()], judges)
        return
    if args.rescore_dates:
        judges = [j.strip() for j in args.judges.split(",") if j.strip()]
        types = [t.strip() for t in args.types.split(",") if t.strip()]
        await run_rescore_production(expand_date_range(args.rescore_dates), judges, types)
        return

    if args.rescore:
        judges = [j.strip() for j in args.judges.split(",") if j.strip()]
        types = [t.strip() for t in args.types.split(",") if t.strip()]
        await run_rescore(args.rescore, judges, args.repeats, types)
        return
    if not args.date:
        parser.error("--date is required unless --rescore is given")

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"Unknown arms {unknown}; choose from {list(ARMS)}")
    types = [t.strip() for t in args.types.split(",") if t.strip()]

    sb = get_supabase()
    if sb is None:
        raise SystemExit("Supabase unavailable")
    inputs = load_inputs(sb, args.date)
    describe_inputs(inputs)
    if args.check_only:
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_ROOT / f"{args.date}-{stamp}"
    summaries = []
    # Arms run sequentially: settings.openai_model_* is process-global.
    for arm in arms:
        print(f"\n--- running arm {arm}: {ARMS[arm]}")
        result = await run_arm(arm, args.date, inputs, types)
        summary = summarize_arm(result)
        dump(out_dir, result, summary)
        summaries.append(summary)

    print_comparison(summaries)
    print(f"\nArtifacts: {out_dir}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
