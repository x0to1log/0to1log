# Handbook Quality Measurement — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an objective (non-LLM-judge) measurement script that scans all published handbook terms and produces a baseline report of content quality failure modes — stale benchmarks, outdated model comparisons, missing architecture detail, missing paper references, and publication age — so that subsequent rubric/prompt work (HB-QM sprint) can be justified by data rather than intuition.

**Architecture:**
Standalone Python CLI script at `backend/scripts/measure_handbook_quality.py`, mirroring the `measure_prompt_failures.py` pattern. Each failure mode is a small pure function in `backend/services/handbook_quality_checks.py` with unit tests. The script pulls `handbook_terms` from Supabase, runs each term through all checks, aggregates, and prints a report. Config (stale model list, failure thresholds) lives in a Python dict first; if DB-hosted config is wanted later, migrate like `news_domain_filters` did (deferred per YAGNI).

**Tech Stack:** Python 3.11, Supabase client (already wired via `core.database.get_supabase`), pytest for unit tests, stdlib regex/collections for checks. No new dependencies.

---

## Context & Motivation

See `vault/09-Implementation/plans/ACTIVE_SPRINT.md` HB-QUALITY-01~04 tasks — they are justified by Amy's subjective sense that handbook content is stale. This plan turns that sense into measurable numbers.

The 0to1log news pipeline hardening (2026-04-15~16, see `2026-04-15-news-pipeline-hardening-*` plans) demonstrated that **measurement-first work prevents 30-50% of planned scope being wasted** on already-solved or non-issues. We're applying the same pattern here before touching prompts/rubrics.

**Non-goals:**
- This plan does NOT modify prompts, rubrics, or the handbook generation pipeline.
- This plan does NOT add an LLM-judge layer. The point is objective metrics that don't share evaluators with the generator.
- This plan does NOT back-fill or fix any content — it only measures.

---

## File Structure

| File | Purpose |
|---|---|
| `backend/services/handbook_quality_checks.py` | Pure functions, one per failure mode. No DB access. No IO. Deterministic given (term dict, config). |
| `backend/tests/test_handbook_quality_checks.py` | Unit tests for each check — fixture terms hand-crafted to exercise pass/fail. |
| `backend/scripts/measure_handbook_quality.py` | CLI: pulls `handbook_terms`, runs checks, prints aggregated report. Mirrors `measure_prompt_failures.py` style. |
| `backend/services/handbook_quality_config.py` | Plain-Python config: stale model list, required-architecture term types, thresholds. Easy to move to Supabase later. |
| `vault/09-Implementation/plans/measurements/2026-04-16-handbook-baseline.md` | Baseline report output (manually saved from script run). |

**Why this split:**
- `handbook_quality_checks.py` holds **logic**, unit-tested in isolation, no DB.
- `measure_handbook_quality.py` holds **orchestration + IO**, thin.
- `handbook_quality_config.py` holds **values**, replaceable without touching logic.
- Tests target the pure layer — measurement layer is exercised by running the script once for baseline and verifying output by eye.

---

## Task 1: Define config — stale models, required-architecture types, thresholds

**Files:**
- Create: `backend/services/handbook_quality_config.py`

**Context:** Before any checks, we need to declare what "stale" means and which term types demand which content. This is intentionally a Python file so Amy can edit it without DB round-trips.

- [ ] **Step 1: Create config file**

```python
# backend/services/handbook_quality_config.py
"""Config for objective handbook quality checks.

Deliberately a Python module (not DB-hosted) for Phase 1. If check rules
stabilize and need runtime edits, migrate to a Supabase table like
`news_domain_filters` did.

Update this file as the AI landscape evolves. Last reviewed: 2026-04-16.
"""
from __future__ import annotations

# Models considered "previous generation" as of 2026-04-16. Mentioning them
# without a current-generation counterpart suggests stale comparison tables.
STALE_MODELS: frozenset[str] = frozenset({
    "GPT-4",
    "GPT-4o",
    "GPT-4 Turbo",
    "Gemini 1.0",
    "Gemini 1.5",
    "Claude 3 Opus",
    "Claude 3 Sonnet",
    "Claude 3.5 Sonnet",
    "Llama 2",
    "Llama 3",
    "Mistral 7B",
})

# Current-generation models as of 2026-04-16. Presence of any of these
# alongside stale models means the comparison is mixed (less stale).
CURRENT_MODELS: frozenset[str] = frozenset({
    "GPT-5",
    "GPT-5.2",
    "Claude Opus 4.6",
    "Claude Sonnet 4.6",
    "Claude Haiku 4.5",
    "Gemini 3",
    "Llama 4",
})

# Term types that should contain architecture/parameter/benchmark detail
# in body_advanced. Based on the 8-type system from HQ-13 (commit 4f9d809).
ARCHITECTURE_REQUIRED_TYPES: frozenset[str] = frozenset({
    "model_family",
    "technique_algorithm",
    "infrastructure_tool",
})

# Term types that should cite an arxiv/paper link in body_advanced.
PAPER_REFERENCE_REQUIRED_TYPES: frozenset[str] = frozenset({
    "technique_algorithm",
    "research_method",
})

# Flags terms older than this many days as "potentially stale due to age".
# Not a failure on its own, but informs refresh prioritization.
STALE_AGE_DAYS: int = 90

# Regex patterns for dated claims. Matches "as of 2023", "2024 baseline", etc.
# Phrases that explicitly anchor content to a past year trigger a flag.
DATED_CLAIM_PATTERNS: tuple[str, ...] = (
    r"\bas of (?:20[12]\d)\b",
    r"\b(?:20[12]\d)\s*(?:baseline|기준)\b",
    r"\b현재\s*(?:20[12]\d)\b",
    r"\b기준일[^\n]*(?:20[12]\d)\b",
)

# Architecture keywords expected in body_advanced for ARCHITECTURE_REQUIRED_TYPES.
# Presence of ANY keyword passes the check. Multilingual (EN + KO).
ARCHITECTURE_KEYWORDS: frozenset[str] = frozenset({
    # EN
    "parameters", "parameter count", "layers", "attention heads",
    "FLOPs", "context window", "training data", "token",
    "architecture", "transformer", "encoder", "decoder",
    # KO
    "파라미터", "어텐션", "헤드", "레이어", "임베딩",
    "아키텍처", "트랜스포머", "학습 데이터",
})

# Paper-reference regex. Matches arxiv.org, paperswithcode, doi.org, OR a markdown
# link whose text looks like a paper title ("Vaswani et al.", "Attention Is All You Need").
PAPER_REFERENCE_PATTERNS: tuple[str, ...] = (
    r"arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}",
    r"paperswithcode\.com",
    r"doi\.org/10\.",
    r"et al\.",
)
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/handbook_quality_config.py
git commit -m "feat(handbook): add quality-check config — stale models, thresholds, patterns"
```

---

## Task 2: Pure check functions — TDD

**Files:**
- Create: `backend/services/handbook_quality_checks.py`
- Create: `backend/tests/test_handbook_quality_checks.py`

**Context:** Each failure mode is one function returning `(bool, str)` — (did the term fail this check, human-readable reason). Functions accept a `term` dict matching the Supabase `handbook_terms` row shape and return deterministic results without external IO.

The `term` dict has these relevant fields:
- `slug` (str)
- `term` (str, English name)
- `korean_name` (str)
- `term_type` (str, one of the 8 types)
- `body_advanced_en`, `body_advanced_ko`, `body_basic_en`, `body_basic_ko` (str)
- `published_at` (ISO 8601 str)

### 2a: stale_model_comparison

- [ ] **Step 1: Write failing tests first**

```python
# backend/tests/test_handbook_quality_checks.py
from services.handbook_quality_checks import (
    check_stale_model_comparison,
    check_missing_architecture_detail,
    check_missing_paper_reference,
    check_dated_claim,
    check_stale_age,
)


def _term(term_type: str = "model_family", **body) -> dict:
    base = {
        "slug": "test-term",
        "term": "Test Term",
        "term_type": term_type,
        "body_advanced_en": "",
        "body_advanced_ko": "",
        "body_basic_en": "",
        "body_basic_ko": "",
        "published_at": "2026-01-01T00:00:00Z",
    }
    base.update(body)
    return base


def test_stale_model_comparison_fails_when_only_stale_mentioned():
    term = _term(body_advanced_en="We compare against GPT-4o and Gemini 1.5.")
    failed, reason = check_stale_model_comparison(term)
    assert failed is True
    assert "GPT-4o" in reason


def test_stale_model_comparison_passes_when_stale_paired_with_current():
    term = _term(
        body_advanced_en="GPT-4o baseline compared to Claude Opus 4.6 shows ..."
    )
    failed, _ = check_stale_model_comparison(term)
    assert failed is False


def test_stale_model_comparison_passes_when_no_models_mentioned():
    term = _term(body_advanced_en="An attention mechanism uses softmax.")
    failed, _ = check_stale_model_comparison(term)
    assert failed is False
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
cd backend && pytest tests/test_handbook_quality_checks.py -v
```

Expected: ImportError (module doesn't exist yet).

- [ ] **Step 3: Create module with this check**

```python
# backend/services/handbook_quality_checks.py
"""Objective (no-LLM) quality checks for handbook terms.

Each check returns (failed: bool, reason: str). Pure — no DB, no IO.
Given the same term + config, always returns the same result.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from services.handbook_quality_config import (
    ARCHITECTURE_KEYWORDS,
    ARCHITECTURE_REQUIRED_TYPES,
    CURRENT_MODELS,
    DATED_CLAIM_PATTERNS,
    PAPER_REFERENCE_PATTERNS,
    PAPER_REFERENCE_REQUIRED_TYPES,
    STALE_AGE_DAYS,
    STALE_MODELS,
)


def _all_bodies(term: dict) -> str:
    parts = [
        term.get("body_advanced_en") or "",
        term.get("body_advanced_ko") or "",
        term.get("body_basic_en") or "",
        term.get("body_basic_ko") or "",
    ]
    return "\n".join(parts)


def check_stale_model_comparison(term: dict) -> tuple[bool, str]:
    """Fail if term mentions stale models without any current-gen counterpart."""
    body = _all_bodies(term)
    stale_hits = [m for m in STALE_MODELS if m in body]
    if not stale_hits:
        return False, ""
    current_hits = [m for m in CURRENT_MODELS if m in body]
    if current_hits:
        return False, ""
    return True, f"mentions {stale_hits} without any current-gen model"
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd backend && pytest tests/test_handbook_quality_checks.py -v -k stale_model
```

Expected: 3/3 pass.

- [ ] **Step 5: Commit**

```bash
git add backend/services/handbook_quality_checks.py backend/tests/test_handbook_quality_checks.py
git commit -m "feat(handbook): stale-model-comparison check + tests"
```

### 2b: missing_architecture_detail

- [ ] **Step 1: Add tests**

```python
def test_architecture_check_fails_for_model_family_without_keywords():
    term = _term(
        term_type="model_family",
        body_advanced_en="A new AI model. It works well on tasks.",
    )
    failed, reason = check_missing_architecture_detail(term)
    assert failed is True
    assert "architecture" in reason.lower()


def test_architecture_check_passes_for_model_family_with_keywords():
    term = _term(
        term_type="model_family",
        body_advanced_en="70B parameters across 80 transformer layers.",
    )
    failed, _ = check_missing_architecture_detail(term)
    assert failed is False


def test_architecture_check_skips_non_required_types():
    term = _term(
        term_type="product_brand",
        body_advanced_en="A chatbot app.",
    )
    failed, _ = check_missing_architecture_detail(term)
    assert failed is False
```

- [ ] **Step 2: Run tests — expect fail (function missing)**

```bash
cd backend && pytest tests/test_handbook_quality_checks.py::test_architecture_check_fails_for_model_family_without_keywords -v
```

- [ ] **Step 3: Implement**

```python
def check_missing_architecture_detail(term: dict) -> tuple[bool, str]:
    """Fail if term_type requires architecture detail but none present."""
    if term.get("term_type") not in ARCHITECTURE_REQUIRED_TYPES:
        return False, ""
    body = _all_bodies(term)
    body_lower = body.lower()
    hits = [k for k in ARCHITECTURE_KEYWORDS if k.lower() in body_lower]
    if hits:
        return False, ""
    return True, f"term_type={term.get('term_type')} but no architecture keyword found"
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd backend && pytest tests/test_handbook_quality_checks.py -v -k architecture
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/handbook_quality_checks.py backend/tests/test_handbook_quality_checks.py
git commit -m "feat(handbook): missing-architecture-detail check + tests"
```

### 2c: missing_paper_reference

- [ ] **Step 1: Add tests**

```python
def test_paper_reference_fails_for_research_method_without_link():
    term = _term(
        term_type="research_method",
        body_advanced_en="A method that improves training.",
    )
    failed, _ = check_missing_paper_reference(term)
    assert failed is True


def test_paper_reference_passes_with_arxiv():
    term = _term(
        term_type="research_method",
        body_advanced_en="See https://arxiv.org/abs/2401.12345 for details.",
    )
    failed, _ = check_missing_paper_reference(term)
    assert failed is False


def test_paper_reference_skips_non_research_type():
    term = _term(
        term_type="product_brand",
        body_advanced_en="A product.",
    )
    failed, _ = check_missing_paper_reference(term)
    assert failed is False
```

- [ ] **Step 2: Implement**

```python
def check_missing_paper_reference(term: dict) -> tuple[bool, str]:
    """Fail if term_type needs paper citation but none present."""
    if term.get("term_type") not in PAPER_REFERENCE_REQUIRED_TYPES:
        return False, ""
    body = _all_bodies(term)
    for pattern in PAPER_REFERENCE_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            return False, ""
    return True, f"term_type={term.get('term_type')} but no arxiv/paper reference"
```

- [ ] **Step 3: Run tests — expect PASS**

```bash
cd backend && pytest tests/test_handbook_quality_checks.py -v -k paper
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/handbook_quality_checks.py backend/tests/test_handbook_quality_checks.py
git commit -m "feat(handbook): missing-paper-reference check + tests"
```

### 2d: dated_claim

- [ ] **Step 1: Add tests**

```python
def test_dated_claim_fails_on_as_of_2024():
    term = _term(body_advanced_en="As of 2024, this model leads benchmarks.")
    failed, reason = check_dated_claim(term)
    assert failed is True
    assert "2024" in reason


def test_dated_claim_fails_on_korean_baseline():
    term = _term(body_advanced_ko="2024 기준 성능은 ...")
    failed, _ = check_dated_claim(term)
    assert failed is True


def test_dated_claim_passes_when_no_date_anchor():
    term = _term(body_advanced_en="The model performs well on MMLU.")
    failed, _ = check_dated_claim(term)
    assert failed is False
```

- [ ] **Step 2: Implement**

```python
def check_dated_claim(term: dict) -> tuple[bool, str]:
    """Fail if body contains phrases explicitly anchoring content to a past year."""
    body = _all_bodies(term)
    for pattern in DATED_CLAIM_PATTERNS:
        m = re.search(pattern, body, re.IGNORECASE)
        if m:
            return True, f"dated claim matched: {m.group(0)!r}"
    return False, ""
```

- [ ] **Step 3: Run tests — expect PASS**

```bash
cd backend && pytest tests/test_handbook_quality_checks.py -v -k dated_claim
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/handbook_quality_checks.py backend/tests/test_handbook_quality_checks.py
git commit -m "feat(handbook): dated-claim check + tests"
```

### 2e: stale_age

- [ ] **Step 1: Add tests**

```python
def test_stale_age_fails_when_older_than_threshold():
    term = _term(published_at="2025-01-01T00:00:00Z")
    failed, _ = check_stale_age(term, now=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert failed is True


def test_stale_age_passes_when_recent():
    term = _term(published_at="2026-04-01T00:00:00Z")
    failed, _ = check_stale_age(term, now=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert failed is False


def test_stale_age_passes_when_no_published_at():
    term = _term(published_at=None)
    failed, _ = check_stale_age(term, now=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert failed is False
```

Add the datetime/timezone imports at the top of the test file:

```python
from datetime import datetime, timezone
```

- [ ] **Step 2: Implement**

```python
def check_stale_age(term: dict, now: datetime | None = None) -> tuple[bool, str]:
    """Flag if term was published more than STALE_AGE_DAYS ago.

    `now` injectable for tests. Defaults to datetime.now(timezone.utc).
    """
    published_at = term.get("published_at")
    if not published_at:
        return False, ""
    try:
        pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return False, ""
    now = now or datetime.now(timezone.utc)
    age = now - pub_dt
    if age > timedelta(days=STALE_AGE_DAYS):
        return True, f"published {age.days} days ago (threshold {STALE_AGE_DAYS})"
    return False, ""
```

- [ ] **Step 3: Run full test file — expect all PASS**

```bash
cd backend && pytest tests/test_handbook_quality_checks.py -v
```

Expected: all 14 tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/services/handbook_quality_checks.py backend/tests/test_handbook_quality_checks.py
git commit -m "feat(handbook): stale-age check + tests (check layer complete)"
```

---

## Task 3: Measurement CLI — orchestrates checks, prints aggregated report

**Files:**
- Create: `backend/scripts/measure_handbook_quality.py`

**Context:** Thin orchestration layer. Pulls all `status != 'archived'` handbook terms from Supabase. Runs each check. Aggregates pass/fail counts per check. Prints a report styled like `measure_prompt_failures.py`.

- [ ] **Step 1: Create the script**

```python
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
```

- [ ] **Step 2: Run the script end-to-end**

```bash
cd backend && python scripts/measure_handbook_quality.py
```

Expected: report prints. The actual numbers are what we're measuring — no "correct" output here.

Capture the stdout for the baseline report (Task 4).

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/measure_handbook_quality.py
git commit -m "feat(handbook): measurement CLI — objective quality baseline"
```

---

## Task 4: Save baseline report to vault

**Files:**
- Create: `vault/09-Implementation/plans/measurements/2026-04-16-handbook-baseline.md`

**Context:** Record the point-in-time baseline so future work can be compared. This is the "before" number the HB-QM sprint uses to justify scope decisions.

- [ ] **Step 1: Re-run the script and redirect output**

```bash
cd backend && python scripts/measure_handbook_quality.py > /tmp/handbook-baseline.txt
```

- [ ] **Step 2: Create the baseline vault file**

```markdown
# Handbook Quality Baseline — 2026-04-16

> Source: `backend/scripts/measure_handbook_quality.py` at commit <short-hash>
> Config snapshot: `backend/services/handbook_quality_config.py` at same commit
> Purpose: before-snapshot for HB-QM sprint. Do not edit — re-run script for fresh snapshot.

## Raw output

```
<paste /tmp/handbook-baseline.txt contents here>
```

## Top observations

- [Fill in 2-3 sentences after looking at the numbers, e.g. "X% of terms have stale model comparisons, concentrated in term_type Y. Paper references are missing from Z% of research_method terms — higher than expected."]

## Follow-ups (feed into HB-QM scope)

- [If any check has 0% fail — consider removing it; signal is noise-free but also useless.]
- [If any check has >80% fail — consider splitting it, the check is too coarse.]
- [If a specific term_type dominates failures — target prompt changes there first.]

## Related

- Plan: `2026-04-16-handbook-quality-measurement-plan.md`
- Sprint: `ACTIVE_SPRINT.md` (HB-QM)
```

- [ ] **Step 3: Fill the baseline from the actual script run, commit**

```bash
git add vault/09-Implementation/plans/measurements/2026-04-16-handbook-baseline.md
git commit -m "docs(handbook): baseline quality measurement 2026-04-16"
```

---

## Task 5: Update ACTIVE_SPRINT to reflect Phase 0 completion

**Files:**
- Modify: `vault/09-Implementation/plans/ACTIVE_SPRINT.md`

- [ ] **Step 1: Add a pointer to the baseline in the HB-QM sprint section, note "measurement-first Phase 0 done — HB-QUALITY-01 scope should be re-evaluated against baseline".**

- [ ] **Step 2: Commit**

```bash
git add vault/09-Implementation/plans/ACTIVE_SPRINT.md
git commit -m "docs(sprint): note handbook measurement baseline — HB-QM Phase 0 done"
```

---

## Exit criteria

- [ ] 14 unit tests pass in `backend/tests/test_handbook_quality_checks.py`
- [ ] `python backend/scripts/measure_handbook_quality.py` runs cleanly against production DB
- [ ] Baseline report saved to `vault/09-Implementation/plans/measurements/2026-04-16-handbook-baseline.md`
- [ ] ACTIVE_SPRINT.md points at the baseline
- [ ] All commits use `feat(handbook):` or `docs(handbook|sprint):` conventions per CLAUDE.md

## Deliberately out of scope

- LLM-judge layer (the whole point is NOT this)
- Any prompt or rubric change
- Any content fix / backfill
- Migrating config to Supabase (YAGNI — defer until edit cadence demands it)
- Running the measurement on a schedule / cron (a one-shot baseline is enough; re-run manually when rubrics change)
- Measuring comparison table accuracy against an external "ground truth" (would require curated expected values — a separate plan)

## Risk notes

- **Regex false positives** in `check_dated_claim` — "as of 2025" may be legitimate in a historical section. If false-positive rate on inspection is >20%, tighten the pattern (e.g., require proximity to benchmark words).
- **STALE_MODELS drift** — list is a point-in-time snapshot. Needs review quarterly (or on each new frontier release). Add a reminder in `ACTIVE_SPRINT.md` or a calendar ping.
- **body_advanced empty for Basic-only terms** — `_all_bodies` concatenates all 4 body fields, so a Basic-only term still gets checked against Basic content. This is intentional: a term_type requiring architecture detail but published as Basic-only is still a failure.

## Related

- [[2026-04-15-news-pipeline-hardening-phase2-plan]] — source of measurement-first pattern
- [[ACTIVE_SPRINT]] — HB-QM sprint this feeds
- `backend/scripts/measure_prompt_failures.py` — stylistic template
