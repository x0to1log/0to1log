"""Plan handbook draft generation from curated JSONL seed files.

This script is intentionally dry-run first. It shows which seed terms are not
present in `handbook_terms` yet, so Amy can review the next batch before any
OpenAI cost is incurred.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Iterable
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.database import get_supabase


DEFAULT_SEED_DIR = (
    Path(__file__).resolve().parents[2]
    / "vault"
    / "09-Implementation"
    / "plans"
    / "2026-04-19-handbook-seed-800"
)


@dataclass(frozen=True)
class SeedTerm:
    term: str
    aliases: tuple[str, ...]
    term_type: str
    note: str
    category: str
    slug: str
    source_file: str
    line_number: int


@dataclass
class ExistingTermIndex:
    terms: set[str] = field(default_factory=set)
    slugs: set[str] = field(default_factory=set)


@dataclass
class SeedBatchResult:
    run_id: str
    run_key: str
    created: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _category_from_filename(path: Path) -> str:
    name = path.name
    name = re.sub(r"^\d+-", "", name)
    return name.removesuffix(".jsonl")


def _iter_seed_files(seed_dir: Path, include_files: Iterable[str] | None = None) -> list[Path]:
    requested = {name for name in (include_files or []) if name}
    files = sorted(seed_dir.glob("[0-9]*.jsonl"))
    if not requested:
        return files
    return [path for path in files if path.name in requested]


def load_seed_terms(seed_dir: str | Path, include_files: Iterable[str] | None = None) -> list[SeedTerm]:
    base = Path(seed_dir)
    terms: list[SeedTerm] = []
    for path in _iter_seed_files(base, include_files):
        category = _category_from_filename(path)
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("_meta"):
                category = str(data.get("category") or category)
                continue
            term = str(data.get("term") or "").strip()
            if not term:
                continue
            aliases = tuple(str(alias).strip() for alias in (data.get("aliases") or []) if str(alias).strip())
            terms.append(
                SeedTerm(
                    term=term,
                    aliases=aliases,
                    term_type=str(data.get("type") or "").strip(),
                    note=str(data.get("note") or "").strip(),
                    category=category,
                    slug=slugify(term),
                    source_file=path.name,
                    line_number=line_number,
                )
            )
    return terms


def load_existing_index(supabase) -> ExistingTermIndex:
    index = ExistingTermIndex()
    if not supabase:
        return index

    page_size = 1000
    for page in range(20):
        result = (
            supabase.table("handbook_terms")
            .select("term, slug")
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        rows = result.data or []
        for row in rows:
            term = str(row.get("term") or "").strip().lower()
            slug = str(row.get("slug") or "").strip().lower()
            if term:
                index.terms.add(term)
            if slug:
                index.slugs.add(slug)
        if len(rows) < page_size:
            break
    return index


def _seed_keys(seed: SeedTerm) -> tuple[set[str], set[str]]:
    term_keys = {seed.term.lower(), *(alias.lower() for alias in seed.aliases)}
    slug_keys = {seed.slug, *(slugify(alias) for alias in seed.aliases)}
    return term_keys, {slug for slug in slug_keys if slug}


def _exists(seed: SeedTerm, existing: ExistingTermIndex) -> bool:
    term_keys, slug_keys = _seed_keys(seed)
    return bool(term_keys & existing.terms or slug_keys & existing.slugs)


def select_seed_candidates(
    seeds: list[SeedTerm],
    existing: ExistingTermIndex,
    *,
    limit: int = 3,
    offset: int = 0,
) -> list[SeedTerm]:
    candidates: list[SeedTerm] = []
    seen = ExistingTermIndex(set(existing.terms), set(existing.slugs))
    filtered_index = 0

    for seed in seeds:
        if _exists(seed, seen):
            continue
        term_keys, slug_keys = _seed_keys(seed)
        seen.terms.update(term_keys)
        seen.slugs.update(slug_keys)
        if filtered_index < offset:
            filtered_index += 1
            continue
        candidates.append(seed)
        filtered_index += 1
        if len(candidates) >= limit:
            break
    return candidates


def count_remaining_candidates(seeds: list[SeedTerm], existing: ExistingTermIndex) -> int:
    return len(select_seed_candidates(seeds, existing, limit=len(seeds)))


def format_candidates(candidates: list[SeedTerm]) -> str:
    if not candidates:
        return "No seed candidates available."
    lines = []
    for idx, seed in enumerate(candidates, start=1):
        aliases = ", ".join(seed.aliases) if seed.aliases else "-"
        lines.append(
            f"{idx}. {seed.term} "
            f"[{seed.category} / {seed.term_type}] "
            f"aliases={aliases} "
            f"source={seed.source_file}:{seed.line_number}"
        )
        if seed.note:
            lines.append(f"   note={seed.note}")
    return "\n".join(lines)


def _derive_korean_name(content: dict) -> str:
    korean_name = str(content.get("korean_name") or "").strip()
    if korean_name:
        return korean_name

    korean_full = str(content.get("korean_full") or "").strip()
    if not korean_full:
        return ""
    return re.sub(r"\s*\([^)]*\)\s*$", "", korean_full).strip()


def build_handbook_insert_row(seed: SeedTerm, content: dict) -> dict:
    categories = content.get("categories") or [seed.category]
    if isinstance(categories, str):
        categories = [categories]

    return {
        "term": seed.term,
        "slug": seed.slug,
        "korean_name": _derive_korean_name(content),
        "term_full": content.get("term_full", ""),
        "korean_full": content.get("korean_full", ""),
        "categories": categories,
        "summary_ko": content.get("summary_ko", ""),
        "summary_en": content.get("summary_en", ""),
        "definition_ko": content.get("definition_ko", ""),
        "definition_en": content.get("definition_en", ""),
        "body_basic_ko": content.get("body_basic_ko", ""),
        "body_basic_en": content.get("body_basic_en", ""),
        "body_advanced_ko": content.get("body_advanced_ko", ""),
        "body_advanced_en": content.get("body_advanced_en", ""),
        "hero_news_context_ko": content.get("hero_news_context_ko", ""),
        "hero_news_context_en": content.get("hero_news_context_en", ""),
        "references_ko": content.get("references_ko", []),
        "references_en": content.get("references_en", []),
        "term_type": seed.term_type or content.get("term_type", ""),
        "facet_intent": content.get("facet_intent", []),
        "facet_volatility": content.get("facet_volatility", "stable"),
        "status": "draft",
        "source": "seed",
    }


def _usage_debug_meta(seed: SeedTerm, usage: dict, extra: dict | None = None) -> dict:
    meta = {
        "term": seed.term,
        "slug": seed.slug,
        "source": "seed",
        "seed_file": seed.source_file,
        "seed_line": seed.line_number,
        "seed_type": seed.term_type,
        "seed_note": seed.note,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }
    if usage.get("cached_tokens") is not None:
        meta["cached_tokens"] = usage["cached_tokens"]
    if usage.get("reasoning_tokens") is not None:
        meta["reasoning_tokens"] = usage["reasoning_tokens"]
    if usage.get("service_tier"):
        meta["service_tier"] = usage["service_tier"]
    if extra:
        meta.update(extra)
    return meta


def _insert_pipeline_log(
    supabase,
    *,
    run_id: str,
    seed: SeedTerm,
    status: str,
    usage: dict | None = None,
    error_message: str | None = None,
    extra_meta: dict | None = None,
) -> None:
    usage = usage or {}
    payload = {
        "run_id": run_id,
        "pipeline_type": "handbook.seed_generate",
        "status": status,
        "input_summary": f"term={seed.term}",
        "output_summary": f"slug={seed.slug}" if status == "success" else None,
        "model_used": usage.get("model_used"),
        "tokens_used": usage.get("tokens_used"),
        "cost_usd": usage.get("cost_usd"),
        "error_message": error_message,
        "debug_meta": _usage_debug_meta(seed, usage, extra_meta),
    }
    try:
        supabase.table("pipeline_logs").insert(payload).execute()
    except Exception as exc:
        print(f"warning: pipeline_logs insert failed for {seed.term}: {exc}", file=sys.stderr)


async def execute_seed_batch(
    candidates: list[SeedTerm],
    supabase,
    *,
    generator: Callable[..., Awaitable[tuple[dict, dict]]] | None = None,
    run_key: str | None = None,
    max_concurrent: int = 1,
    term_timeout_seconds: float | None = 900,
    draft_only: bool = True,
    remediate: bool = False,
) -> SeedBatchResult:
    if not supabase:
        raise RuntimeError("Supabase is not configured; cannot execute seed batch.")

    if generator is None:
        from services.agents.advisor import generate_term_content

        generator = generate_term_content

    run_id = str(uuid4())
    run_key = run_key or f"handbook-seed-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    result = SeedBatchResult(run_id=run_id, run_key=run_key)

    supabase.table("pipeline_runs").insert({
        "id": run_id,
        "run_key": run_key,
        "status": "running",
    }).execute()

    sem = asyncio.Semaphore(max(1, max_concurrent))

    async def _create_one(seed: SeedTerm) -> None:
        async with sem:
            try:
                async def _generate_one() -> tuple[dict, dict]:
                    return await generator(
                        term_name=seed.term,
                        korean_name="",
                        source="seed",
                        article_context="",
                        categories=[seed.category],
                        term_type_hint=seed.term_type,
                        log_run_id=run_id,
                        skip_quality_check=draft_only,
                        skip_self_critique=draft_only,
                        skip_post_generation_checks=draft_only,
                        remediate_after_generation=remediate,
                    )

                if term_timeout_seconds and term_timeout_seconds > 0:
                    content, usage = await asyncio.wait_for(
                        _generate_one(),
                        timeout=term_timeout_seconds,
                    )
                else:
                    content, usage = await _generate_one()
                content = dict(content or {})
                warnings = content.pop("_warnings", [])
                remediation_issues = content.pop("_remediation_issues", [])
                quality_gate = content.pop("_quality_gate", None)
                remediation_status = content.pop("_remediation_status", "not_requested")
                remediation_meta = content.pop("_remediation_meta", None)
                row = build_handbook_insert_row(seed, content)
                insert_result = supabase.table("handbook_terms").insert(row).execute()
                if not getattr(insert_result, "data", None):
                    raise RuntimeError("handbook_terms insert returned empty data")
                result.created += 1
                _insert_pipeline_log(
                    supabase,
                    run_id=run_id,
                    seed=seed,
                    status="success",
                    usage={},
                    extra_meta={
                        "billing_scope": "rollup",
                        "quality_mode": "draft-only" if draft_only else "full-quality",
                        "remediation_enabled": remediate,
                        "rollup_usage": usage or {},
                        **({"warnings": warnings} if warnings else {}),
                        **({"remediation_issues": remediation_issues} if remediation_issues else {}),
                        **({"quality_gate": quality_gate} if quality_gate else {}),
                        "remediation_status": remediation_status,
                        **({"remediation_meta": remediation_meta} if remediation_meta else {}),
                    },
                )
            except asyncio.TimeoutError:
                result.failed += 1
                timeout_label = f"{term_timeout_seconds:g}s" if term_timeout_seconds else "configured timeout"
                message = f"{seed.term}: timed out after {timeout_label}"
                result.errors.append(message)
                _insert_pipeline_log(
                    supabase,
                    run_id=run_id,
                    seed=seed,
                    status="failed",
                    error_message=message,
                    extra_meta={
                        "quality_mode": "draft-only" if draft_only else "full-quality",
                        "remediation_enabled": remediate,
                        "term_timeout_seconds": term_timeout_seconds,
                    },
                )
            except Exception as exc:
                result.failed += 1
                message = f"{seed.term}: {exc}"
                result.errors.append(message)
                _insert_pipeline_log(
                    supabase,
                    run_id=run_id,
                    seed=seed,
                    status="failed",
                    error_message=message,
                )

    await asyncio.gather(*[_create_one(seed) for seed in candidates])

    final_status = "failed" if result.created == 0 and result.failed else "success"
    supabase.table("pipeline_runs").update({
        "status": final_status,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "last_error": result.errors[0] if result.errors else None,
    }).eq("id", run_id).execute()
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run the next handbook seed batch from JSONL files.",
    )
    parser.add_argument("--seed-dir", default=str(DEFAULT_SEED_DIR), help="Seed JSONL directory.")
    parser.add_argument("--file", action="append", default=[], help="Specific seed file name. Repeatable.")
    parser.add_argument("--limit", type=int, default=3, help="Number of candidates to show.")
    parser.add_argument("--offset", type=int, default=0, help="Skip N available candidates after DB filtering.")
    parser.add_argument("--execute", action="store_true", help="Generate and insert draft rows. Default is dry-run.")
    parser.add_argument("--max-concurrent", type=int, default=1, help="Max concurrent term generations in execute mode.")
    parser.add_argument(
        "--remediate",
        action="store_true",
        default=False,
        help="Run one targeted remediation pass before inserting each generated draft.",
    )
    parser.add_argument(
        "--term-timeout-seconds",
        type=float,
        default=900,
        help="Hard timeout per term in execute mode. Use 0 to disable.",
    )
    quality_group = parser.add_mutually_exclusive_group()
    quality_group.add_argument(
        "--draft-only",
        dest="draft_only",
        action="store_true",
        default=True,
        help="Generate draft content only; skip self-critique, improvement, and semantic quality checks. Default.",
    )
    quality_group.add_argument(
        "--full-quality",
        dest="draft_only",
        action="store_false",
        help="Run self-critique, improvement, post-generation verification, and semantic quality checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    seeds = load_seed_terms(args.seed_dir, args.file)
    existing = load_existing_index(get_supabase())
    candidates = select_seed_candidates(
        seeds,
        existing,
        limit=max(0, args.limit),
        offset=max(0, args.offset),
    )
    remaining = count_remaining_candidates(seeds, existing)

    mode = "execute" if args.execute else "dry-run"
    print(f"Handbook seed batch {mode}")
    print(f"seed_dir={args.seed_dir}")
    print(f"seed_terms={len(seeds)}")
    print(f"remaining_candidates={remaining}")
    print(f"limit={args.limit} offset={args.offset}")
    print(f"max_concurrent={args.max_concurrent}")
    print(f"term_timeout_seconds={args.term_timeout_seconds}")
    print(f"quality_mode={'draft-only' if args.draft_only else 'full-quality'}")
    print(f"remediation={'on' if args.remediate else 'off'}")
    print()
    print(format_candidates(candidates))

    if args.execute:
        if not candidates:
            print("\nNo candidates to execute.")
            return 0
        result = asyncio.run(
            execute_seed_batch(
                candidates,
                get_supabase(),
                max_concurrent=args.max_concurrent,
                term_timeout_seconds=args.term_timeout_seconds,
                draft_only=args.draft_only,
                remediate=args.remediate,
            )
        )
        print()
        print(f"run_key={result.run_key}")
        print(f"run_id={result.run_id}")
        print(f"created={result.created} failed={result.failed}")
        if result.errors:
            print("errors:")
            for error in result.errors:
                print(f"- {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
