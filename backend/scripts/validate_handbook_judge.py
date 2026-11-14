"""Check the handbook quality judge against Amy's own publish / archive decisions.

Published and archived terms are human labels the judge never saw. If the
judge's score cannot tell the two groups apart, a score threshold is not a
usable gate. This script rescores those terms read-only (no DB writes) and
reports how well each score separates the groups.

Dry-run is the default: it reads the terms and prints counts and a cost
estimate without calling a model.

    python scripts/validate_handbook_judge.py
    python scripts/validate_handbook_judge.py --execute --out judge.jsonl
    python scripts/validate_handbook_judge.py --report judge.jsonl
    # Same-judge noise: score some terms a second time, then compare.
    python scripts/validate_handbook_judge.py --execute --repeat-from judge.jsonl --limit 20 --out judge-repeat.jsonl
    python scripts/validate_handbook_judge.py --report judge.jsonl --repeat judge-repeat.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SELECT_COLUMNS = (
    "id,term,slug,korean_name,term_full,korean_full,categories,"
    "summary_ko,summary_en,definition_ko,definition_en,"
    "body_basic_ko,body_basic_en,body_advanced_ko,body_advanced_en,"
    "hero_news_context_ko,hero_news_context_en,references_ko,references_en,"
    "term_type,facet_intent,facet_volatility,status,source,"
    "created_at,updated_at,published_at"
)
BODY_FIELDS = ("body_basic_ko", "body_basic_en", "body_advanced_ko", "body_advanced_en")
LABEL_STATUSES = ("published", "archived")
# Opus rescore 2026-11-13: $5.50 for 30 terms, with judge inputs still truncated.
MEASURED_COST_PER_TERM_USD = 0.18
TERM_TIMEOUT_SEC = 600
GATE_PASS = 70


# --- data -------------------------------------------------------------------

def fetch_labeled_terms(sb) -> list[dict]:
    rows: list[dict] = []
    for status in LABEL_STATUSES:
        start = 0
        while True:
            page = (
                sb.table("handbook_terms").select(SELECT_COLUMNS)
                .eq("status", status).order("slug").range(start, start + 49).execute().data or []
            )
            rows.extend(page)
            if len(page) < 50:
                break
            start += 50
    return rows


def has_all_bodies(row: dict) -> bool:
    return all(str(row.get(field) or "").strip() for field in BODY_FIELDS)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- scoring ----------------------------------------------------------------

def _sub_scores(breakdown: dict | None) -> dict[str, int]:
    """Flatten {"sub_scores": {dimension: {sub: {"score": n}}}} to {"dimension.sub": n}."""
    flat: dict[str, int] = {}
    for dim, subs in ((breakdown or {}).get("sub_scores") or {}).items():
        if not isinstance(subs, dict):
            continue
        for name, value in subs.items():
            if isinstance(value, dict) and "score" in value:
                flat[f"{dim}.{name}"] = value["score"]
    return flat


async def score_one(row: dict) -> dict:
    from services.agents.advisor import rescore_existing_handbook_quality

    record = {
        "slug": row["slug"],
        "term": row["term"],
        "status": row["status"],
        "source": row.get("source"),
        "term_type": row.get("term_type"),
        "updated_at": row.get("updated_at"),
        "chars": {field: len(str(row.get(field) or "")) for field in BODY_FIELDS},
    }
    try:
        scored, usage, _warnings = await asyncio.wait_for(
            rescore_existing_handbook_quality(str(row["term"]), row, run_semantic=True),
            timeout=TERM_TIMEOUT_SEC,
        )
    except Exception as exc:  # recorded and retried on the next run, never scored
        return {**record, "error": f"{type(exc).__name__}: {exc}"}

    quality = scored.get("quality") or {}
    adv, basic = quality.get("advanced") or {}, quality.get("basic") or {}
    return {
        **record,
        "structural_penalty": adv.get("structural_penalty"),
        "adv": adv.get("total"),
        "adv_sem": adv.get("semantic_score"),
        "basic": basic.get("total"),
        "basic_sem": basic.get("semantic_score"),
        "judges_missing": scored.get("_judges_missing") or [],
        "adv_subs": _sub_scores(adv.get("semantic_breakdown")),
        "basic_subs": _sub_scores(basic.get("semantic_breakdown")),
        "cost_usd": usage.get("cost_usd"),
        "model_used": usage.get("model_used"),
    }


async def execute(rows: list[dict], out: Path, concurrency: int) -> None:
    done = {r["slug"] for r in read_jsonl(out) if "error" not in r}
    todo = [row for row in rows if row["slug"] not in done]
    print(f"{len(done)} already scored in {out.name}, {len(todo)} to score")
    sem = asyncio.Semaphore(concurrency)
    spent = 0.0

    async def worker(row: dict) -> None:
        nonlocal spent
        async with sem:
            record = await score_one(row)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        spent += float(record.get("cost_usd") or 0)
        outcome = record.get("error") or f"adv={record['adv_sem']} basic={record['basic_sem']}"
        print(f"  [{record['status']}] {record['slug']}: {outcome} (run total ${spent:.2f})")

    await asyncio.gather(*(worker(row) for row in todo))


# --- statistics -------------------------------------------------------------

def auc(positive: list[float], negative: list[float]) -> float | None:
    """P(a random positive scores above a random negative); ties count half. 0.5 = no signal."""
    if not positive or not negative:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in positive for n in negative)
    return wins / (len(positive) * len(negative))


def auc_interval(positive: list[float], negative: list[float], rounds: int = 2000) -> tuple[float, float] | None:
    """95% bootstrap interval for the AUC (fixed seed, so reports are reproducible)."""
    if len(positive) < 2 or len(negative) < 2:
        return None
    rng = random.Random(0)
    samples = sorted(
        auc(rng.choices(positive, k=len(positive)), rng.choices(negative, k=len(negative)))
        for _ in range(rounds)
    )
    return samples[int(rounds * 0.025)], samples[int(rounds * 0.975) - 1]


def _mean_sd(values: list[float]) -> str:
    if not values:
        return "—"
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{statistics.mean(values):.1f} ({sd:.1f})"


def _separation_row(label: str, published: list[float], archived: list[float]) -> str:
    value = auc(published, archived)
    interval = auc_interval(published, archived)
    auc_text = "—" if value is None else f"{value:.2f}"
    ci_text = "—" if interval is None else f"{interval[0]:.2f}–{interval[1]:.2f}"
    return f"| {label} | {_mean_sd(published)} | {_mean_sd(archived)} | {auc_text} | {ci_text} |"


def build_report(records: list[dict], repeat: list[dict]) -> str:
    scored = [r for r in records if "error" not in r]
    errors = [r for r in records if "error" in r]
    groups = {status: [r for r in scored if r["status"] == status] for status in LABEL_STATUSES}

    def values(status: str, getter) -> list[float]:
        return [v for v in (getter(r) for r in groups[status]) if v is not None]

    lines = [
        "# Handbook judge vs publish/archive decisions",
        "",
        f"- Scored: published {len(groups['published'])}, archived {len(groups['archived'])}"
        f" (errors {len(errors)}, judge missing {sum(1 for r in scored if r['judges_missing'])})",
        f"- Recorded cost: ${sum(float(r.get('cost_usd') or 0) for r in records):.2f}",
        "- AUC = chance that a published term outscores an archived one. 0.5 is no signal, 1.0 is perfect.",
        "",
        "## Does the score separate the groups?",
        "",
        "| Score | published mean (sd) | archived mean (sd) | AUC | 95% interval |",
        "|---|---|---|---|---|",
    ]
    headline = (
        ("advanced, judge only", lambda r: r["adv_sem"]),
        ("advanced, after penalty", lambda r: r["adv"] if r["adv_sem"] is not None else None),
        ("basic, judge only", lambda r: r["basic_sem"]),
        ("basic, after penalty", lambda r: r["basic"] if r["basic_sem"] is not None else None),
        # Negated so that "higher is better" holds for the AUC, as it does for the scores.
        ("structural penalty (code, negated)", lambda r: None if r["structural_penalty"] is None else -r["structural_penalty"]),
    )
    for label, getter in headline:
        lines.append(_separation_row(label, values("published", getter), values("archived", getter)))

    # Published terms come from several sources and archived ones mostly from the
    # news pipeline, so the all-terms table also measures "which source". Within
    # one source both groups were written the same way.
    for source in sorted({str(r.get("source")) for r in groups["archived"]}):
        same = {s: [r for r in groups[s] if str(r.get("source")) == source] for s in LABEL_STATUSES}
        if len(same["published"]) < 5 or len(same["archived"]) < 5:
            continue
        lines += [
            "", f"### source = {source} only (published {len(same['published'])}, archived {len(same['archived'])})", "",
            "| Score | published mean (sd) | archived mean (sd) | AUC | 95% interval |", "|---|---|---|---|---|",
        ]
        for label, getter in headline:
            lines.append(_separation_row(
                label,
                [v for v in (getter(r) for r in same["published"]) if v is not None],
                [v for v in (getter(r) for r in same["archived"]) if v is not None],
            ))

    lines += ["", f"## Gate at {GATE_PASS}", "", "| | published | archived |", "|---|---|---|"]
    for label, key in (("advanced ≥ 70", "adv"), ("basic ≥ 70", "basic")):
        cells = []
        for status in LABEL_STATUSES:
            judged = [r for r in groups[status] if r[f"{key}_sem"] is not None]
            passed = sum(1 for r in judged if r[key] >= GATE_PASS)
            cells.append(f"{passed}/{len(judged)}" if judged else "—")
        lines.append(f"| {label} | {cells[0]} | {cells[1]} |")

    lines += ["", "## Sub-scores (0–10)", "", "| Sub-score | published mean (sd) | archived mean (sd) | AUC | 95% interval |", "|---|---|---|---|---|"]
    for level in ("adv_subs", "basic_subs"):
        names = sorted({name for r in scored for name in r[level]})
        for name in names:
            lines.append(_separation_row(
                f"{level.split('_')[0]} · {name}",
                values("published", lambda r: r[level].get(name)),
                values("archived", lambda r: r[level].get(name)),
            ))

    lines += ["", "## Who is in each group", "", "| | published | archived |", "|---|---|---|"]
    sources = sorted({str(r.get("source")) for r in scored})
    for source in sources:
        counts = [sum(1 for r in groups[s] if str(r.get("source")) == source) for s in LABEL_STATUSES]
        lines.append(f"| source = {source} | {counts[0]} | {counts[1]} |")
    for field in BODY_FIELDS:
        lines.append(
            f"| {field} chars, mean (sd) | {_mean_sd(values('published', lambda r: r['chars'][field]))}"
            f" | {_mean_sd(values('archived', lambda r: r['chars'][field]))} |"
        )

    if repeat:
        first = {r["slug"]: r for r in scored}
        lines += ["", "## Same judge, same text, scored twice", "", "| Score | terms | mean abs difference | max | gate result flipped |", "|---|---|---|---|---|"]
        for label, key in (("advanced", "adv"), ("basic", "basic")):
            pairs = [
                (first[r["slug"]], r) for r in repeat
                if "error" not in r and r["slug"] in first
                and r[f"{key}_sem"] is not None and first[r["slug"]][f"{key}_sem"] is not None
            ]
            if not pairs:
                continue
            diffs = [abs(a[f"{key}_sem"] - b[f"{key}_sem"]) for a, b in pairs]
            flips = sum(1 for a, b in pairs if (a[key] >= GATE_PASS) != (b[key] >= GATE_PASS))
            lines.append(f"| {label} | {len(pairs)} | {statistics.mean(diffs):.1f} | {max(diffs)} | {flips}/{len(pairs)} |")

    if errors:
        lines += ["", "## Errors", ""] + [f"- {r['slug']}: {r['error']}" for r in errors]
    return "\n".join(lines) + "\n"


# --- entry point ------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--execute", action="store_true", help="Call the judge (costs money). Appends to --out; rerun to resume.")
    parser.add_argument("--out", type=Path, default=Path("handbook-judge-validation.jsonl"))
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="Score at most this many terms per status.")
    parser.add_argument("--source", help="Only terms with this handbook_terms.source (e.g. pipeline).")
    parser.add_argument("--repeat-from", type=Path, help="Score terms already in this JSONL again (for same-judge noise).")
    parser.add_argument("--report", type=Path, help="Print a markdown report from this JSONL. No DB or model calls.")
    parser.add_argument("--repeat", type=Path, help="With --report: a second-pass JSONL to compare against.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.report:
        print(build_report(read_jsonl(args.report), read_jsonl(args.repeat) if args.repeat else []))
        return 0

    from core.database import get_supabase

    sb = get_supabase()
    if sb is None:
        raise RuntimeError("Supabase is not configured.")
    rows = fetch_labeled_terms(sb)
    usable = [row for row in rows if has_all_bodies(row)]

    print("status     total  all 4 bodies  sources")
    for status in LABEL_STATUSES:
        total = [r for r in rows if r["status"] == status]
        ok = [r for r in total if has_all_bodies(r)]
        sources: dict[str, int] = {}
        for r in ok:
            sources[str(r.get("source"))] = sources.get(str(r.get("source")), 0) + 1
        print(f"{status:<10} {len(total):>5}  {len(ok):>12}  {sources}")

    if args.repeat_from:
        earlier = {r["slug"] for r in read_jsonl(args.repeat_from) if "error" not in r}
        usable = [row for row in usable if row["slug"] in earlier]
    if args.source:
        usable = [row for row in usable if str(row.get("source")) == args.source]
    if args.limit:
        usable = [row for status in LABEL_STATUSES for row in [r for r in usable if r["status"] == status][: args.limit]]

    print(f"\n{len(usable)} terms to score, 2 judge calls each.")
    print(f"Estimate: ~${len(usable) * MEASURED_COST_PER_TERM_USD:.0f} at the measured ${MEASURED_COST_PER_TERM_USD}/term "
          "(2026-11-13, truncated inputs); whole-body inputs will cost somewhat more.")
    if not args.execute:
        print("Dry run. Pass --execute to call the judge.")
        return 0
    asyncio.run(execute(usable, args.out, args.concurrency))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
