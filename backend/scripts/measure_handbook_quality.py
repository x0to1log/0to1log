"""Measure objective quality failure rate across published handbook terms.

Phase 1 of 2026-04-16-handbook-quality-measurement plan.

Runs non-LLM checks (stale model comparison, missing architecture detail,
missing paper reference, dated claim, stale age) against all active
handbook terms and prints a baseline report.

Usage:
    cd backend && python scripts/measure_handbook_quality.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase  # noqa: E402
from services.handbook_quality_checks import (  # noqa: E402
    check_dated_claim,
    check_missing_architecture_detail,
    check_missing_paper_reference,
    check_stale_age,
    check_stale_model_comparison,
)

CHECKS = [
    ("stale_model_comparison", check_stale_model_comparison),
    ("missing_architecture_detail", check_missing_architecture_detail),
    ("missing_paper_reference", check_missing_paper_reference),
    ("dated_claim", check_dated_claim),
    ("stale_age", check_stale_age),
]


def main() -> None:
    supabase = get_supabase()
    if supabase is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    rows = (
        supabase.table("handbook_terms")
        .select(
            "slug, term, korean_name, term_type, "
            "body_advanced_en, body_advanced_ko, "
            "body_basic_en, body_basic_ko, "
            "published_at, status"
        )
        .neq("status", "archived")
        .execute()
        .data or []
    )

    total = len(rows)
    print(f"\n=== Sample size: {total} active handbook terms ===\n")

    if total == 0:
        print("No terms to measure.")
        return

    # Per-check fail count
    fail_counts: Counter = Counter()
    # Per-type × per-check fail count (for segment analysis)
    fail_by_type: dict[str, Counter] = defaultdict(Counter)
    # Terms with at least one failure
    any_fail_terms: list[str] = []
    # Top offenders (most failed checks)
    term_fail_tally: list[tuple[int, str, list[str]]] = []

    for term in rows:
        term_type = term.get("term_type") or "unknown"
        failed_checks: list[str] = []
        for name, fn in CHECKS:
            failed, _reason = fn(term)
            if failed:
                fail_counts[name] += 1
                fail_by_type[term_type][name] += 1
                failed_checks.append(name)
        if failed_checks:
            any_fail_terms.append(term.get("slug", "?"))
            term_fail_tally.append((len(failed_checks), term.get("slug", "?"), failed_checks))

    # --- Report ---
    print("=== Per-check fail rate ===")
    for name, _ in CHECKS:
        n = fail_counts[name]
        pct = n / total * 100
        print(f"  {name}: {n} / {total} ({pct:.1f}%)")

    print("\n=== Any-check-failed (terms needing attention) ===")
    any_n = len(any_fail_terms)
    print(f"  {any_n} / {total} ({any_n/total*100:.1f}%)")

    print("\n=== Per-term-type × per-check fail count ===")
    for term_type in sorted(fail_by_type.keys()):
        type_counts = fail_by_type[term_type]
        if not type_counts:
            continue
        print(f"  {term_type}:")
        for name, _ in CHECKS:
            if type_counts[name]:
                print(f"    {name}: {type_counts[name]}")

    print("\n=== Top 10 worst offenders (most failed checks) ===")
    term_fail_tally.sort(reverse=True)
    for count, slug, failed_checks in term_fail_tally[:10]:
        print(f"  [{count}] {slug}: {', '.join(failed_checks)}")

    print()


if __name__ == "__main__":
    main()
