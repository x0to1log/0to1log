"""Export daily digests into a golden set for human labelling.

The golden set answers one question: does the auto-publish gate block the
digests a person would block? Each unit is one digest (date x research/business,
all personas, EN + KO). The export writes two files per unit:

  items/<id>.json   everything a machine needs: bodies, quizzes, the stored
                    score and caps, and (when that day's checkpoints still
                    exist) the inputs needed to re-run the QC judge.
  review/<id>.md    what a person reads. It has no score, caps or judge issues,
                    so the label is not anchored on the current judge. The
                    label goes in the frontmatter at the top.

Usage (from backend/):
    python -m scripts.export_golden_set --list --since 2026-10-19
    python -m scripts.export_golden_set --sample 40 --since 2026-10-19 --seed 7
    python -m scripts.export_golden_set --dates 2026-11-13,2026-11-14
    python -m scripts.export_golden_set --collect

Production Supabase is only read. Re-running an export never overwrites a
review sheet (it may hold a label) and never drops a QC-input snapshot that an
earlier export saved.

Checkpoints are pruned after 14 days (services/retention.py), and the QC judge
cannot be replayed without them. Export a day while its checkpoints exist if
you want to test judge changes on it later; older days can still be labelled
and compared with the gate decision stored at the time.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output" / "golden-set"

DIGEST_TYPES = ("research", "business")
PERSONAS = ("expert", "learner", "beginner")
LOCALES = ("en", "ko")

VERDICTS = ("publish", "block")

# Why a digest must not auto-publish. This list IS the definition of "block",
# so edit it to match what you would actually hold back, before labelling.
REASONS = {
    "factual_error": "a claim is wrong",
    "source_mismatch": "a claim is not supported by the source it cites",
    "overclaim": "headline, excerpt or body says more than the sources do",
    "locale": "Korean reads badly, or English leaked into it (or the reverse)",
    "structure": "broken, missing or duplicated sections, headings or citations",
    "stale_or_duplicate": "old news, or a story already covered on a recent day",
    "thin": "too little substance to be worth publishing",
    "other": "explain in notes",
}


# ---------------------------------------------------------------------------
# Population and sampling
# ---------------------------------------------------------------------------

def unit_id(date: str, digest_type: str) -> str:
    return f"{date}-{digest_type}"


def group_population(rows: list[dict[str, Any]], gate) -> list[dict[str, Any]]:
    """Collapse EN/KO news_posts rows into one unit per (date, type).

    `gate(score, caps) -> bool` is the auto-publish gate. A unit counts as
    published only when every locale row is published.
    """
    units: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        date, digest_type = row.get("pipeline_batch_id"), row.get("post_type")
        if not date or digest_type not in DIGEST_TYPES:
            continue
        unit = units.setdefault((date, digest_type), {
            "id": unit_id(date, digest_type), "date": date, "type": digest_type,
            "statuses": {}, "score": None, "caps": [],
        })
        unit["statuses"][row.get("locale")] = row.get("status")
        if row.get("locale") == "en":
            unit["score"] = row.get("quality_score")
            unit["caps"] = row.get("caps") or []
    for unit in units.values():
        statuses = set(unit["statuses"].values())
        unit["status"] = "published" if statuses == {"published"} else "draft"
        unit["gate_pass"] = bool(gate(unit["score"], unit["caps"]))
    return sorted(units.values(), key=lambda u: (u["date"], u["type"]))


def choose_sample(units: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    """Pick n units, up to half of them ones the gate held or that stayed draft.

    Held digests are rare, and a set of only published ones cannot show whether
    the gate blocks the right things, so they are taken first.
    """
    rng = random.Random(seed)
    held = [u for u in units if not u["gate_pass"] or u["status"] != "published"]
    passed = [u for u in units if u["gate_pass"] and u["status"] == "published"]
    take_held = min(len(held), n // 2)
    take_passed = min(len(passed), n - take_held)
    chosen = rng.sample(held, take_held) + rng.sample(passed, take_passed)
    return sorted(chosen, key=lambda u: (u["date"], u["type"]))


# ---------------------------------------------------------------------------
# Item building
# ---------------------------------------------------------------------------

def build_item(
    unit: dict[str, Any],
    rows_by_locale: dict[str, dict[str, Any]],
    replay: dict[str, Any] | None,
) -> dict[str, Any]:
    en, ko = rows_by_locale.get("en") or {}, rows_by_locale.get("ko") or {}
    by_locale = {"en": en, "ko": ko}
    fact_pack = en.get("fact_pack") or {}
    return {
        "id": unit["id"],
        "date": unit["date"],
        "type": unit["type"],
        "status": unit["status"],
        "stored": {
            "quality_score": unit["score"],
            "caps": unit["caps"],
            "gate_pass": unit["gate_pass"],
            "quality_version": fact_pack.get("quality_version"),
            "quality_breakdown": fact_pack.get("quality_breakdown"),
            "quality_issues": fact_pack.get("quality_issues") or [],
            "publish_block_reason": fact_pack.get("publish_block_reason"),
        },
        "frontload": {
            locale: {
                "title": row.get("title") or "",
                "excerpt": row.get("excerpt") or "",
                "focus_items": row.get("focus_items") or [],
            }
            for locale, row in by_locale.items()
        },
        "personas": {
            persona: {locale: row.get(f"content_{persona}") or "" for locale, row in by_locale.items()}
            for persona in PERSONAS
        },
        "quizzes": {
            persona: {
                locale: (row.get("guide_items") or {}).get(f"quiz_poll_{persona}")
                for locale, row in by_locale.items()
            }
            for persona in PERSONAS
        },
        "source_cards": en.get("source_cards") or [],
        "replay": replay,
    }


def build_replay(
    digest_type: str,
    rank: dict[str, Any] | None,
    community_summarize: dict[str, Any] | None,
    enrich: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """QC inputs for one digest type, cut from that day's checkpoints.

    Returns None when the rank or enrich checkpoint is gone: the judge cannot
    be replayed without the story groups and their source text.
    """
    if not rank or not enrich:
        return None
    groups = rank.get(digest_type) or []
    if not groups:
        return None
    primary_urls = [g["items"][0]["url"] for g in groups if g.get("items")]
    enriched_map = {
        url: sources for url, sources in (enrich.get("enriched_map") or {}).items()
        if url in primary_urls
    }
    wanted = {item["url"] for g in groups for item in g.get("items", [])}
    wanted |= {s.get("url") for sources in enriched_map.values() for s in sources if isinstance(s, dict)}
    summaries = (community_summarize or {}).get("summaries") or {}
    return {
        "classified": groups,
        "community_summaries": {url: ins for url, ins in summaries.items() if url in primary_urls},
        "enriched_map": enriched_map,
        "raw_content_map": {
            url: text for url, text in (enrich.get("raw_content_map") or {}).items() if url in wanted
        },
    }


def keep_earlier_replay(new_item: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    """A re-export after the checkpoints were pruned must not erase the snapshot."""
    if existing and existing.get("replay") and not new_item.get("replay"):
        return {**new_item, "replay": existing["replay"]}
    return new_item


# ---------------------------------------------------------------------------
# Review sheet (what the labeller reads) and label parsing
# ---------------------------------------------------------------------------

def render_review(item: dict[str, Any]) -> str:
    reasons = " | ".join(REASONS)
    lines = [
        "---",
        f"id: {item['id']}",
        f"verdict:            # {' | '.join(VERDICTS)}",
        f"reasons: []         # any of: {reasons}",
        'notes: ""',
        "---",
        "",
        f"# {item['id']}",
        "",
        "Would you let this digest auto-publish as it is? Judge all personas and both",
        "languages together: one blocking problem anywhere means `block`.",
        "",
    ]
    for locale in LOCALES:
        front = item["frontload"][locale]
        lines += [f"## Front ({locale.upper()})", "", f"**{front['title']}**", "", front["excerpt"], ""]
        lines += [f"- {focus}" for focus in front["focus_items"]]
        lines.append("")
    for persona in PERSONAS:
        for locale in LOCALES:
            body = item["personas"][persona][locale]
            if not body.strip():
                continue
            lines += [f"## {persona} ({locale.upper()})", "", body.strip(), ""]
            quiz = item["quizzes"][persona][locale]
            if quiz:
                lines += [
                    f"**Quiz ({persona}, {locale.upper()})**", "",
                    "```json", json.dumps(quiz, ensure_ascii=False, indent=2), "```", "",
                ]
    lines += ["## Sources", ""]
    lines += [
        f"{card.get('id', '')}. {card.get('title') or card.get('url')} — {card.get('url')}"
        for card in item["source_cards"]
    ]
    return "\n".join(lines) + "\n"


def parse_review_labels(text: str) -> dict[str, Any]:
    """Read id / verdict / reasons / notes from a review sheet's frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("review sheet has no frontmatter")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.split(" #", 1)[0].strip()
    reasons_raw = fields.get("reasons", "").strip("[] ")
    return {
        "id": fields.get("id", ""),
        "verdict": fields.get("verdict", "").strip("\"' "),
        "reasons": [r.strip("\"' ") for r in reasons_raw.split(",") if r.strip("\"' ")],
        "notes": fields.get("notes", "").strip("\"'"),
    }


def label_problems(label: dict[str, Any]) -> list[str]:
    problems = []
    if label["verdict"] not in VERDICTS:
        problems.append(f"verdict must be one of {VERDICTS}, got {label['verdict']!r}")
    unknown = [r for r in label["reasons"] if r not in REASONS]
    if unknown:
        problems.append(f"unknown reasons {unknown}")
    if label["verdict"] == "block" and not label["reasons"]:
        problems.append("a block needs at least one reason")
    return problems


def agreement(labels: list[dict[str, Any]], items: dict[str, dict[str, Any]]) -> Counter:
    """Count (human verdict, stored gate decision) pairs."""
    table: Counter = Counter()
    for label in labels:
        item = items.get(label["id"])
        if item is None:
            continue
        gate = "publish" if item["stored"]["gate_pass"] else "block"
        table[(label["verdict"], gate)] += 1
    return table


# ---------------------------------------------------------------------------
# Supabase reads
# ---------------------------------------------------------------------------

def fetch_population(sb: Any, since: str, until: str | None) -> list[dict[str, Any]]:
    query = (
        sb.table("news_posts")
        # Only the cap list is read from fact_pack: the full JSON is several KB per row.
        .select("slug,locale,post_type,status,quality_score,pipeline_batch_id,caps:fact_pack->quality_caps_applied")
        .eq("category", "ai-news")
        .in_("post_type", list(DIGEST_TYPES))
        .gte("pipeline_batch_id", since)
    )
    if until:
        query = query.lte("pipeline_batch_id", until)
    return query.execute().data or []


def fetch_checkpoints(sb: Any, date: str) -> dict[str, dict[str, Any] | None]:
    from services.pipeline import _load_checkpoint

    wanted = ("rank", "community_summarize", "enrich")
    runs = sb.table("pipeline_runs").select("id").eq("run_key", f"news-{date}").execute().data or []
    if not runs:
        return dict.fromkeys(wanted)
    run_id = runs[0]["id"]
    present = {
        row["stage"] for row in
        sb.table("pipeline_checkpoints").select("stage").eq("run_id", run_id).execute().data or []
    }
    return {stage: _load_checkpoint(sb, run_id, stage) if stage in present else None for stage in wanted}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def print_population(units: list[dict[str, Any]]) -> None:
    print(f"{'id':<24} {'status':<10} {'score':>5}  {'gate':<7} caps")
    for u in units:
        gate = "pass" if u["gate_pass"] else "block"
        print(f"{u['id']:<24} {u['status']:<10} {str(u['score']):>5}  {gate:<7} {u['caps'] or '-'}")
    held = sum(1 for u in units if not u["gate_pass"] or u["status"] != "published")
    print(f"\n{len(units)} digests, {held} held by the gate or left as draft")


def export_units(sb: Any, units: list[dict[str, Any]], out: Path) -> None:
    from services.pipeline import _fetch_daily_digest_rows_from_db, _group_daily_digest_rows_by_type

    items_dir, review_dir = out / "items", out / "review"
    items_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    by_date: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        by_date.setdefault(unit["date"], []).append(unit)

    for date, date_units in by_date.items():
        rows_by_type = _group_daily_digest_rows_by_type(_fetch_daily_digest_rows_from_db(sb, date))
        checkpoints = fetch_checkpoints(sb, date)
        for unit in date_units:
            replay = build_replay(
                unit["type"], checkpoints["rank"], checkpoints["community_summarize"], checkpoints["enrich"],
            )
            item = build_item(unit, rows_by_type.get(unit["type"], {}), replay)
            item_path = items_dir / f"{item['id']}.json"
            existing = json.loads(item_path.read_text(encoding="utf-8")) if item_path.exists() else None
            item = keep_earlier_replay(item, existing)
            item_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")

            review_path = review_dir / f"{item['id']}.md"
            if review_path.exists():
                sheet = "kept existing review sheet"
            else:
                review_path.write_text(render_review(item), encoding="utf-8")
                sheet = "wrote review sheet"
            replayable = "QC inputs saved" if item["replay"] else "no QC inputs (checkpoints gone)"
            print(f"{item['id']}: {sheet}; {replayable}")
    print(f"\nLabel the sheets in {review_dir}, then run --collect")


def collect_labels(out: Path) -> None:
    review_dir, items_dir = out / "review", out / "items"
    labels, unlabelled, invalid = [], [], []
    for path in sorted(review_dir.glob("*.md")):
        label = parse_review_labels(path.read_text(encoding="utf-8"))
        if not label["verdict"]:
            unlabelled.append(path.name)
            continue
        problems = label_problems(label)
        if problems:
            invalid.append(f"{path.name}: {'; '.join(problems)}")
            continue
        labels.append(label)
    labels_path = out / "labels.jsonl"
    labels_path.write_text(
        "".join(json.dumps(label, ensure_ascii=False) + "\n" for label in labels), encoding="utf-8",
    )
    print(f"{len(labels)} labelled, {len(unlabelled)} not yet labelled, {len(invalid)} invalid")
    for line in invalid:
        print(f"  INVALID {line}")

    items = {
        p.stem: json.loads(p.read_text(encoding="utf-8")) for p in items_dir.glob("*.json")
    }
    table = agreement(labels, items)
    if table:
        print("\nHuman verdict vs the gate decision stored at the time:")
        print(f"  both publish                    {table[('publish', 'publish')]}")
        print(f"  both block                      {table[('block', 'block')]}")
        print(f"  gate published, human blocks    {table[('block', 'publish')]}   <- the costly miss")
        print(f"  gate blocked, human publishes   {table[('publish', 'block')]}")
        print("  (stored decisions come from whichever judge and threshold ran that day)")
    reason_counts = Counter(r for label in labels for r in label["reasons"])
    if reason_counts:
        print("\nBlock reasons:", dict(reason_counts.most_common()))
    print(f"\nWrote {labels_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default="2026-10-19", help="first batch date (default: current QC judge era)")
    parser.add_argument("--until", help="last batch date")
    parser.add_argument("--list", action="store_true", help="show the digests in range and stop")
    parser.add_argument("--sample", type=int, help="export this many digests, half of them gate-held if possible")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dates", help="export exactly these batch dates, comma-separated")
    parser.add_argument("--collect", action="store_true", help="read labels back from the review sheets")
    parser.add_argument("--out", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()

    if args.collect:
        collect_labels(args.out)
        return

    import services.pipeline  # noqa: F401 - load re-exports before pipeline_quality
    from core.database import get_supabase
    from services.pipeline_quality import passes_auto_publish_gate

    sb = get_supabase()
    if sb is None:
        raise SystemExit("Supabase unavailable")

    dates = [d.strip() for d in (args.dates or "").split(",") if d.strip()]
    since = min(dates) if dates else args.since
    until = max(dates) if dates else args.until
    units = group_population(fetch_population(sb, since, until), passes_auto_publish_gate)
    if dates:
        units = [u for u in units if u["date"] in dates]

    if args.list:
        print_population(units)
        return
    if args.sample:
        units = choose_sample(units, args.sample, args.seed)
    elif not dates:
        parser.error("choose --list, --sample N, --dates or --collect")
    export_units(sb, units, args.out)


if __name__ == "__main__":
    sys.exit(main())
