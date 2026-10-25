"""Compare handbook writer models on the same terms (HB-CLAUDE-PILOT-01).

Runs full-quality generation (self-critique, regeneration, entity checks, sol
judges) for each term x writer model and writes the results to files only:
the advisor's own DB writes (stage logs, handbook_quality_scores) are cut off
by patching its get_supabase, so a pilot leaves nothing in production. Pick
the writer from summary.md, then generate the chosen drafts with the seed
batch script (--writer-model).

Vault plan 2026-10-23-handbook-seed-claude (결정 3).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import services.pipeline  # noqa: E402,F401  (load order: pipeline before advisor)
from scripts.run_handbook_seed_batch import slugify  # noqa: E402

DEFAULT_OUT_DIR = (
    BACKEND_DIR.parent / "vault" / "09-Implementation" / "plans" / "2026-10-23-handbook-seed-claude" / "pilot"
)
# Categories where the May seed drafts went wrong (category prompt plan, 2026-05-12).
DEFAULT_TERMS = [
    ("Red Teaming", "safety-ethics", "system_workflow_pattern"),
    ("SGLang", "products-platforms", "hardware_runtime_infra"),
    ("Bradley–Terry Model", "math-statistics", "model_algorithm_family"),
]
DEFAULT_MODELS = ["claude-sonnet-5-5", "claude-opus-5-5", "gpt-6.1-sol"]
BODY_FIELDS = [
    "definition_en", "definition_ko", "summary_en", "summary_ko",
    "body_basic_en", "body_basic_ko", "body_advanced_en", "body_advanced_ko",
]


def summarize(term: str, model: str, data: dict[str, Any], usage: dict[str, Any], seconds: float,
              error: str = "") -> dict[str, Any]:
    quality = data.get("quality") or {}
    adv, basic = quality.get("advanced") or {}, quality.get("basic") or {}
    return {
        "term": term,
        "model": model,
        "error": error,
        "seconds": round(seconds),
        "cost_usd": round(float(usage.get("cost_usd") or 0), 4),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cached_tokens": usage.get("cached_tokens"),
        "advanced": adv.get("total"),
        "basic": basic.get("total"),
        "structural_penalty": adv.get("structural_penalty"),
        "structural_warnings": adv.get("structural_warnings") or [],
        "gate": (data.get("generation_gate") or {}).get("status", ""),
        "gate_reasons": (data.get("generation_gate") or {}).get("reasons", []),
        "chars": {field: len(str(data.get(field) or "")) for field in BODY_FIELDS},
        "warnings": data.get("_warnings") or [],
    }


def render_markdown(term: str, model: str, data: dict[str, Any], row: dict[str, Any]) -> str:
    lines = [
        f"# {term} — {model}",
        "",
        f"- advanced {row['advanced']} / basic {row['basic']} / gate {row['gate']} "
        f"/ penalty {row['structural_penalty']} / ${row['cost_usd']} / {row['seconds']}s",
        "",
    ]
    for field in BODY_FIELDS:
        lines += [f"## {field}", "", str(data.get(field) or "_(empty)_"), ""]
    refs = data.get("references_en") or []
    if refs:
        lines += ["## references_en", "", *(f"- {json.dumps(r, ensure_ascii=False)}" for r in refs), ""]
    return "\n".join(lines)


def write_summary(out_dir: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Handbook writer pilot — summary",
        "",
        "> full-quality 생성, 판정은 모두 gpt-6.1-sol. 본문은 같은 폴더의 `<slug>__<model>.md`.",
        "",
        "| term | model | advanced | basic | gate | penalty | cost | time | basic KO 글자 | advanced KO 글자 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if r["error"]:
            lines.append(f"| {r['term']} | {r['model']} | — | — | **error** | — | ${r['cost_usd']} | {r['seconds']}s | {r['error'][:60]} | |")
            continue
        lines.append(
            f"| {r['term']} | {r['model']} | {r['advanced']} | {r['basic']} | {r['gate']} | {r['structural_penalty']} "
            f"| ${r['cost_usd']} | {r['seconds']}s | {r['chars']['body_basic_ko']} | {r['chars']['body_advanced_ko']} |"
        )
    by_model: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)
    lines += ["", "| model | 평균 advanced | 평균 basic | 용어당 비용 | 용어당 시간 |", "|---|---|---|---|---|"]
    for model, items in by_model.items():
        ok = [r for r in items if not r["error"]]
        if not ok:
            continue
        avg = lambda key: round(sum(float(r[key] or 0) for r in ok) / len(ok), 1)  # noqa: E731
        lines.append(f"| {model} | {avg('advanced')} | {avg('basic')} | ${avg('cost_usd')} | {avg('seconds')}s |")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_one(term: str, category: str, term_type: str, model: str, out_dir: Path,
                  timeout: float) -> dict[str, Any]:
    from services.agents.advisor import generate_term_content

    t0 = time.monotonic()
    data: dict[str, Any] = {}
    usage: dict[str, Any] = {}
    error = ""
    try:
        data, usage = await asyncio.wait_for(
            generate_term_content(
                term_name=term,
                source="seed",
                categories=[category],
                term_type_hint=term_type,
                writer_model=model,
            ),
            timeout=timeout,
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    row = summarize(term, model, data, usage, time.monotonic() - t0, error)
    stem = f"{slugify(term)}__{model}"
    (out_dir / f"{stem}.json").write_text(
        json.dumps({"summary": row, "usage": usage, "content": data}, ensure_ascii=False, indent=1), encoding="utf-8",
    )
    if not error:
        (out_dir / f"{stem}.md").write_text(render_markdown(term, model, data, row), encoding="utf-8")
    print(f"  {term} / {model}: adv={row['advanced']} basic={row['basic']} gate={row['gate']} "
          f"${row['cost_usd']} {row['seconds']}s {error[:80]}")
    return row


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", action="append", default=[], help="Writer model. Repeatable.")
    parser.add_argument("--term", action="append", default=[], help='"Term|category|term_type". Repeatable.')
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    terms = [tuple(t.split("|")) for t in args.term] or DEFAULT_TERMS
    models = args.model or DEFAULT_MODELS
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"pilot: {len(terms)} terms x {len(models)} models -> {args.out_dir}")

    sem = asyncio.Semaphore(max(1, args.concurrency))

    async def guarded(term: str, category: str, term_type: str, model: str) -> dict[str, Any]:
        async with sem:
            return await run_one(term, category, term_type, model, args.out_dir, args.timeout)

    # The advisor writes stage logs and quality scores through its own client; cut it off.
    with patch("services.agents.advisor.get_supabase", return_value=None):
        rows = await asyncio.gather(*(guarded(*t, m) for t in terms for m in models))
    write_summary(args.out_dir, list(rows))
    print(f"pilot: total ${sum(r['cost_usd'] for r in rows):.2f}")


if __name__ == "__main__":
    asyncio.run(main())
