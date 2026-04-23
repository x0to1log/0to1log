# GPT-5 Efficiency Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Cut GPT-5 spend on the news pipeline by ~40-60% through (a) migrating writers to `service_tier="flex"`, (b) enabling prompt caching via `prompt_cache_key` + prompt restructuring, and (c) A/B-testing weekly writer reasoning level. Target: writer+QC combined cost dropping from ~$25/month to ~$10-12/month while preserving quality.

**Architecture:** Three phases in dependency order.
- **Phase 1 — Flex tier for writers (independent, immediate savings).** Move daily + weekly writer calls from standard → flex tier (50% discount, higher latency). Bump timeouts 480s → 900s per OpenAI guidance. Add 429 retry-with-backoff.
- **Phase 2 — Prompt caching enablement + measurement (depends on Phase 1 to avoid mixed signals).** Thread `prompt_cache_key` through `build_completion_kwargs` and `compat_create_kwargs`. Assign stable keys per (model, digest_type, persona). Measure `cached_tokens` before/after via existing observability. If hit rate <30%, restructure `_build_digest_prompt` to put common blocks (HALLUCINATION_GUARD, FRONTLOAD_LOCALE_PARITY, BODY_LOCALE_PARITY) at the start so OpenAI's longest-common-prefix matching activates.
- **Phase 3 — Weekly writer reasoning_effort A/B (deferred; gate by Phase 1-2 stabilizing).** Test `reasoning_effort="medium"` on weekly writer for 2 runs. Compare quality_score + editorial feel. Commit if improvement, roll back otherwise.

**Tech Stack:** Python 3.11, OpenAI Python SDK, Supabase (pipeline_logs for observability), pytest.

**Non-goals (explicit):**
- Batch tier migration (24h turnaround breaks daily cron)
- Priority tier (user-facing speed, irrelevant for async cron)
- Advisor/blog/product-advisor reasoning tuning (separate plan if needed)
- `verbosity` parameter tuning (current state — unset for writers, "low" for QC — is appropriate)

**Key reference files (read before starting):**
- `backend/services/agents/client.py:42-100` — `_apply_gpt5_compat`, `build_completion_kwargs`, `compat_create_kwargs` (user already added `service_tier`, `verbosity` params)
- `backend/services/pipeline_digest.py:670-685` — daily writer call site (service_tier not set, needs flex)
- `backend/services/pipeline.py:2409-2422, 2473-2486` — weekly writer (EN + KO calls)
- `backend/services/pipeline_quality.py:446-456, 1088-1100, 1130-1142` — QC calls (already on flex, reference pattern)
- `backend/services/agents/prompts_news_pipeline.py:226-385` — `_build_digest_prompt` (candidate for restructuring in Phase 2)
- `backend/services/pipeline.py:487-488` — existing `cached_tokens` observability plumbing

---

## Current State (for the executor)

After 2026-04-23 URL compliance migration + user's flex-tier work, the live state is:

| Site | Model | reasoning_effort | service_tier | response_format | timeout |
|------|-------|------------------|--------------|-----------------|---------|
| Daily writer | gpt-5 | `high` (explicit) | standard (unset) | strict json_schema | 480s |
| Weekly writer (EN) | gpt-5 | low (compat default) | standard (unset) | json_object | 240s |
| Weekly writer (KO) | gpt-5 | low (compat default) | standard (unset) | json_object | 180s |
| Daily QC | gpt-5-mini | low | **flex** | json_object | (no wrap) |
| Weekly QC | gpt-5-mini | low | **flex** | json_object | (no wrap) |

Flex tier is already proven on QC. `prompt_cache_key` param exists in OpenAI API but is not threaded through our helpers yet. `cached_tokens` usage is already captured in `extract_usage_metrics` and emitted to `pipeline_logs.debug_meta`.

---

## Chunk 1: Phase 1 — Flex Tier for Writers

### Task 1.1: Add exponential-backoff retry helper for 429 RateLimitError

**Files:**
- Modify: `backend/services/agents/client.py` (add helper near the top)
- Test: `backend/tests/test_agents_client.py` (extend)

**Why:** Flex tier returns HTTP 429 "Resource Unavailable" when capacity is low. Per OpenAI docs the request isn't charged, but our code currently treats 429 as a hard failure. A simple backoff lets capacity free up and the call succeed.

**Step 1: Write the failing test**

Append to `backend/tests/test_agents_client.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock

import openai
import pytest

from services.agents.client import with_flex_retry


@pytest.mark.asyncio
async def test_with_flex_retry_succeeds_after_one_429():
    """First call 429s, second succeeds → returns the success response."""
    mock_ok = MagicMock(choices=[MagicMock()])
    fn = AsyncMock(side_effect=[
        openai.RateLimitError(
            message="resource unavailable",
            response=MagicMock(status_code=429),
            body={"error": {"type": "requests"}},
        ),
        mock_ok,
    ])
    out = await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert out is mock_ok
    assert fn.call_count == 2


@pytest.mark.asyncio
async def test_with_flex_retry_gives_up_after_max_attempts():
    err = openai.RateLimitError(
        message="resource unavailable",
        response=MagicMock(status_code=429),
        body={"error": {"type": "requests"}},
    )
    fn = AsyncMock(side_effect=[err, err, err])
    with pytest.raises(openai.RateLimitError):
        await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 3


@pytest.mark.asyncio
async def test_with_flex_retry_passes_through_non_429_errors():
    err = openai.BadRequestError(
        message="schema invalid",
        response=MagicMock(status_code=400),
        body={"error": {"type": "invalid_request"}},
    )
    fn = AsyncMock(side_effect=[err])
    with pytest.raises(openai.BadRequestError):
        await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 1  # no retry
```

**Step 2: Run — expect failures**

Run: `.venv/Scripts/python -m pytest tests/test_agents_client.py::test_with_flex_retry_succeeds_after_one_429 -v`

Expected: FAIL with `ImportError: cannot import name 'with_flex_retry'`.

**Step 3: Implement `with_flex_retry`**

Add to `backend/services/agents/client.py` (after the imports block):

```python
import asyncio as _asyncio  # local alias to avoid top-of-file import churn
from typing import Awaitable, Callable, TypeVar

_T = TypeVar("_T")


async def with_flex_retry(
    fn: Callable[[], Awaitable[_T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 2.0,
) -> _T:
    """Retry an OpenAI call on 429 (flex-tier resource-unavailable).

    Exponential backoff: base_delay, 2*base_delay, 4*base_delay. Only retries
    openai.RateLimitError; every other exception passes through unchanged.
    Not charged on 429 per OpenAI flex docs, so retrying is free.
    """
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await fn()
        except openai.RateLimitError as e:
            last_err = e
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "flex 429 (attempt %d/%d) — backing off %.1fs: %s",
                attempt + 1, max_attempts, delay, e,
            )
            await _asyncio.sleep(delay)
    # Unreachable — raise above exits the loop
    assert last_err is not None
    raise last_err
```

Add to top of file if not present:
```python
import openai
```

**Step 4: Run tests — all pass**

Run: `.venv/Scripts/python -m pytest tests/test_agents_client.py -v`

Expected: all pass (5 existing + 3 new = 8).

**Step 5: Commit**

```bash
git add backend/services/agents/client.py backend/tests/test_agents_client.py
git commit -m "feat(agents): add with_flex_retry helper for 429 capacity errors"
```

---

### Task 1.2: Migrate daily writer to flex tier

**Files:**
- Modify: `backend/services/pipeline_digest.py:670-685` (main writer call)
- Modify: `backend/services/pipeline_digest.py:781-792, 837-848` (recovery KO + EN paths)

**Step 1: Wrap the main writer call in `with_flex_retry` + set service_tier**

Change:
```python
response = await asyncio.wait_for(
    client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": writer_schema,
            },
            max_tokens=24000,
            reasoning_effort="high",
        )
    ),
    timeout=480,  # 8 minutes: high reasoning effort is 2-3x slower
)
```

To:
```python
async def _call() -> Any:
    return await asyncio.wait_for(
        client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": writer_schema,
                },
                max_tokens=24000,
                reasoning_effort="high",
                service_tier="flex",
            )
        ),
        # Flex: OpenAI docs recommend 15min timeout. Also accommodates
        # high-reasoning writer (typically 3-5 min) with headroom for queue.
        timeout=900,
    )

response = await with_flex_retry(_call)
```

Add the import at the top of the file:
```python
from services.agents.client import (
    compat_create_kwargs,
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
    with_flex_retry,  # ← new
)
```

**Step 2: Apply the same pattern to KO recovery call (line ~781)**

Wrap the `ko_resp = await asyncio.wait_for(...)` in `with_flex_retry`, add `service_tier="flex"`, bump timeout 120 → 300.

**Step 3: Apply same pattern to EN recovery call (line ~837)**

Wrap `en_resp`, add flex tier, bump timeout 120 → 300.

**Step 4: Run pipeline_digest tests**

Run: `.venv/Scripts/python -m pytest tests/test_pipeline_digest_validation.py -v --tb=short`

Expected: 13 pass (flex tier doesn't change mocked behavior — tests mock the client call).

**Step 5: Commit**

```bash
git add backend/services/pipeline_digest.py
git commit -m "feat(news): migrate daily writer + recovery calls to flex tier

Applies service_tier=flex to the 3 gpt-5 calls in _generate_digest
(main writer + KO recovery + EN recovery). Bumps timeouts to 900s
(main) and 300s (recovery) per OpenAI flex guidance. Wraps each call
in with_flex_retry so 429 'resource unavailable' triggers exp backoff
instead of aborting the whole run."
```

---

### Task 1.3: Migrate weekly writer to flex tier

**Files:**
- Modify: `backend/services/pipeline.py:2409-2422` (weekly EN call)
- Modify: `backend/services/pipeline.py:2473-2486` (weekly KO call)

**Step 1: Wrap EN call**

Change:
```python
en_response = await asyncio.wait_for(
    client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": daily_text},
            ],
            response_format={"type": "json_object"},
            max_tokens=16000,
        )
    ),
    timeout=240,
)
```

To:
```python
async def _call_en() -> Any:
    return await asyncio.wait_for(
        client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": daily_text},
                ],
                response_format={"type": "json_object"},
                max_tokens=16000,
                service_tier="flex",
            )
        ),
        timeout=900,
    )
en_response = await with_flex_retry(_call_en)
```

Add `with_flex_retry` to the imports at top of file (find existing `from services.agents.client import ...` and extend).

**Step 2: Wrap KO call (same pattern)**

Change the `ko_response = await asyncio.wait_for(...)` block identically — add `service_tier="flex"`, bump timeout 180 → 900, wrap in `with_flex_retry`.

**Step 3: Run pipeline tests**

Run: `.venv/Scripts/python -m pytest tests/test_pipeline.py tests/test_weekly_quality_scoring.py -v --tb=short`

Expected: no regressions.

**Step 4: Commit**

```bash
git add backend/services/pipeline.py
git commit -m "feat(weekly): migrate weekly writer to flex tier

Both EN and KO weekly writer calls use service_tier=flex with
timeout=900s + with_flex_retry for 429 backoff. Weekly runs once per
week on cron — latency is unconstrained; cost cut ~50%."
```

---

## Chunk 2: Phase 2 — Prompt Caching

### Task 2.1: Thread `prompt_cache_key` through helper functions

**Files:**
- Modify: `backend/services/agents/client.py` (`build_completion_kwargs`, `compat_create_kwargs`)
- Test: `backend/tests/test_agents_client.py` (extend)

**Why:** `prompt_cache_key` is an optional OpenAI API parameter that hints which cache bucket to use. Supplying a stable key (e.g., `"digest-research-expert"`) increases the probability of hitting the same physical server that processed the last call with the same prefix, and — per recent OpenAI updates — enables extended (24h) retention on cached prefixes. Without a key, caching is purely opportunistic at the 5-10 min TTL.

**Step 1: Write failing test**

Append to `backend/tests/test_agents_client.py`:

```python
def test_build_completion_kwargs_passes_prompt_cache_key():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
        prompt_cache_key="digest-research-expert",
    )
    assert out["prompt_cache_key"] == "digest-research-expert"


def test_build_completion_kwargs_omits_prompt_cache_key_when_none():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
    )
    assert "prompt_cache_key" not in out


def test_compat_create_kwargs_passes_prompt_cache_key_through():
    out = compat_create_kwargs(
        "gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
        prompt_cache_key="digest-business-learner",
    )
    assert out["prompt_cache_key"] == "digest-business-learner"
```

**Step 2: Run test — expect failure**

Run: `.venv/Scripts/python -m pytest tests/test_agents_client.py::test_build_completion_kwargs_passes_prompt_cache_key -v`

Expected: FAIL with unexpected keyword arg.

**Step 3: Add `prompt_cache_key` param**

Modify `backend/services/agents/client.py:76-100`:

```python
def build_completion_kwargs(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.3,
    response_format: dict | None = None,
    reasoning_effort: str | None = None,
    service_tier: str | None = None,
    verbosity: str | None = None,
    prompt_cache_key: str | None = None,
) -> dict:
    """Build kwargs for chat.completions.create, handling model differences."""
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if _uses_max_completion_tokens(model):
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
    kwargs["temperature"] = temperature
    if response_format:
        kwargs["response_format"] = response_format
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    if service_tier is not None:
        kwargs["service_tier"] = service_tier
    if verbosity is not None:
        kwargs["verbosity"] = verbosity
    if prompt_cache_key is not None:
        kwargs["prompt_cache_key"] = prompt_cache_key
    return _apply_gpt5_compat(kwargs, model)
```

`compat_create_kwargs` is already `**kwargs`-based, so it passes `prompt_cache_key` through automatically — no change needed there.

**Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_agents_client.py -v`

Expected: all pass (11 total now).

**Step 5: Commit**

```bash
git add backend/services/agents/client.py backend/tests/test_agents_client.py
git commit -m "feat(agents): thread prompt_cache_key through helper kwargs

Adds prompt_cache_key param to build_completion_kwargs.
compat_create_kwargs already passes through via **kwargs. No behavior
change without a caller providing a key — sets up the plumbing for
the next commit to apply keys to writer+QC call sites."
```

---

### Task 2.2: Apply `prompt_cache_key` to writer call sites

**Files:**
- Modify: `backend/services/pipeline_digest.py` (daily writer: main + recovery)
- Modify: `backend/services/pipeline.py` (weekly writer: EN + KO)
- Modify: `backend/services/pipeline_quality.py:446-456` (daily QC — same rationale)

**Why:** Daily writer runs 4 distinct calls per day (research×2 + business×2). Each gets its own stable key. QC runs 2 per day, also keyed. Weekly writer: 2 per week. Stable keys give OpenAI the "route this to the same server you used last time" signal → higher cache hit probability, especially with extended retention.

**Step 1: Daily writer — add key to main call**

In `pipeline_digest.py` writer call, add `prompt_cache_key` kwarg:

```python
**compat_create_kwargs(
    model,
    messages=[...],
    response_format={"type": "json_schema", "json_schema": writer_schema},
    max_tokens=24000,
    reasoning_effort="high",
    service_tier="flex",
    prompt_cache_key=f"digest-{digest_type}-{persona_name}",  # ← new
)
```

This gives 4 distinct stable keys: `digest-research-expert`, `digest-research-learner`, `digest-business-expert`, `digest-business-learner`.

**Step 2: Daily writer — add same key to KO + EN recovery calls**

For the KO recovery block (around line 781), add:
```python
prompt_cache_key=f"digest-{digest_type}-{persona_name}-ko-recovery",
```

For EN recovery:
```python
prompt_cache_key=f"digest-{digest_type}-{persona_name}-en-recovery",
```

Recovery paths use different system prompts (with `"Generate ONLY the Korean (ko) content..."` override) — separate keys avoid cross-contaminating cache with the main call's prefix.

**Step 3: Weekly writer — add keys to EN + KO**

In `pipeline.py:2409`, add `prompt_cache_key=f"weekly-{persona}-en"`.
In `pipeline.py:2473`, add `prompt_cache_key=f"weekly-{persona}-ko"`.

**Step 4: Daily QC — add keys**

In `pipeline_quality.py:446` (the `_score` inner function), add:
```python
prompt_cache_key=f"qc-{label}",  # label is e.g. "Quality-research-expert"
```

Same treatment for weekly QC at line 1088 and 1130.

**Step 5: Run full relevant test suite**

Run: `.venv/Scripts/python -m pytest tests/test_agents_client.py tests/test_pipeline.py tests/test_pipeline_rerun.py tests/test_pipeline_digest_validation.py tests/test_pipeline_quality_scoring.py tests/test_weekly_quality_scoring.py -v --tb=short`

Expected: no regressions.

**Step 6: Commit**

```bash
git add backend/services/pipeline_digest.py backend/services/pipeline.py backend/services/pipeline_quality.py
git commit -m "feat(pipeline): add prompt_cache_key to writer+QC call sites

Assigns stable per-call-type keys (e.g. digest-research-expert,
weekly-expert-en, qc-Quality-business-learner) so OpenAI routes
repeat calls to the same physical server + unlocks extended cache
retention. Cache hits are still opportunistic until we measure."
```

---

### Task 2.3: Measurement script — cached_tokens hit rate

**Files:**
- Create: `backend/scripts/measure_cached_tokens.py`

**Why:** Before deciding whether prompt restructuring is worth the risk, measure the baseline. Extended retention with stable keys may suffice on its own.

**Step 1: Write the diagnostic script**

Create `backend/scripts/measure_cached_tokens.py`:

```python
"""Report cached_tokens hit rate for a pipeline run.

Usage:
    python scripts/measure_cached_tokens.py <run_id>
    # or:
    python scripts/measure_cached_tokens.py --last 3  # last 3 runs
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client


def fetch_stage_logs(sb, run_id: str) -> list[dict]:
    return (
        sb.table("pipeline_logs")
        .select("stage,status,debug_meta,usage")
        .eq("run_id", run_id)
        .execute()
        .data
    )


def summarize(logs: list[dict]) -> None:
    per_stage = defaultdict(lambda: {"prompt": 0, "cached": 0, "count": 0})
    for row in logs:
        usage = row.get("usage") or {}
        debug = row.get("debug_meta") or {}
        prompt_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        cached = (
            debug.get("cached_tokens")
            or usage.get("cached_tokens")
            or 0
        )
        stage = row.get("stage") or "unknown"
        per_stage[stage]["prompt"] += int(prompt_tokens)
        per_stage[stage]["cached"] += int(cached)
        per_stage[stage]["count"] += 1

    print(f"{'Stage':<40} {'Calls':>6} {'Prompt tokens':>15} {'Cached':>10} {'Hit%':>6}")
    print("-" * 80)
    for stage in sorted(per_stage):
        s = per_stage[stage]
        pct = (s["cached"] / s["prompt"] * 100) if s["prompt"] else 0.0
        print(f"{stage:<40} {s['count']:>6} {s['prompt']:>15,} {s['cached']:>10,} {pct:>5.1f}%")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", nargs="?", help="Specific run id (uuid)")
    parser.add_argument("--last", type=int, help="Summarize last N runs")
    args = parser.parse_args()

    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"],
    )

    if args.run_id:
        run_ids = [args.run_id]
    else:
        n = args.last or 1
        runs = (
            sb.table("pipeline_runs")
            .select("id,run_key")
            .order("started_at", desc=True)
            .limit(n)
            .execute()
            .data
        )
        run_ids = [r["id"] for r in runs]

    for run_id in run_ids:
        print(f"\n=== run_id = {run_id} ===")
        logs = fetch_stage_logs(sb, run_id)
        if not logs:
            print("  no stage logs")
            continue
        summarize(logs)


if __name__ == "__main__":
    main()
```

**Step 2: Run on Apr 23 rerun data (baseline)**

Run:
```bash
.venv/Scripts/python scripts/measure_cached_tokens.py e1a54ea8-364a-4290-8433-e56d20016f5f
```

Expected: see per-stage cached_tokens vs prompt_tokens with hit %.

Record the output under a new heading `## Phase 2 Cache Baseline` in this plan file.

**Step 3: Commit script + baseline note**

```bash
git add backend/scripts/measure_cached_tokens.py vault/09-Implementation/plans/2026-04-23-gpt5-efficiency.md
git commit -m "chore(scripts): add cached_tokens hit-rate diagnostic"
```

---

### Task 2.4: Post-migration cache measurement (after a real cron run)

**Step 1: Wait for next cron run OR trigger a fresh Apr 24 digest**

The flex + prompt_cache_key changes are deployed (Phase 1+Task 2.1-2.2). Next daily cron (or a manual run) is the first run with the new keys.

**Step 2: Run the diagnostic**

```bash
.venv/Scripts/python scripts/measure_cached_tokens.py --last 1
```

**Step 3: Decision gate**

- **If writer stages show cached_tokens > ~30% of prompt_tokens** → caching is working well. Skip Task 2.5 (prompt restructure). Move to Phase 3.
- **If writer stages show cached_tokens < ~30%** → proceed to Task 2.5 (restructure prompts so common blocks form a long stable prefix).

Record the outcome + decision under `## Phase 2 Cache After Migration` in this plan file.

**Step 4: Commit the decision note**

```bash
git add vault/09-Implementation/plans/2026-04-23-gpt5-efficiency.md
git commit -m "docs(plan): record post-migration cache hit rate + next step"
```

---

### Task 2.5: Prompt restructure (CONDITIONAL — only if Task 2.4 shows low hit rate)

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py:226-385` (`_build_digest_prompt`)
- Test: `backend/tests/test_news_digest_prompts.py` (possibly extend with ordering assertion)

**Why:** OpenAI cache works by longest-common-prefix. Current prompt structure:
```
Line 1: You are a {persona}-level AI news digest writer for 0to1log.
Line 4: Your job: write a **{digest_type} daily digest**...
```
The persona and digest_type diverge immediately at token ~10, so the 4 daily writer prompts share essentially zero prefix. Moving stable content (HALLUCINATION_GUARD, FRONTLOAD_LOCALE_PARITY, BODY_LOCALE_PARITY, title strategy, citation format rules, learner rules) to the top and pushing variable bits (persona identity, digest_type) lower can create a shared prefix of 2-3K tokens — enough to trigger significant caching.

**Step 1: Inspect how much content is currently persona/digest-type-dependent**

Run: `grep -n "{persona\|{digest_type\|{sections_description\|{skeleton\|{title_strategy\|{persona_guide" backend/services/agents/prompts_news_pipeline.py | head -30`

Inventory: every `{X}` interpolation is a potential cache-break point. Tally which are constant across the 4 prompts vs variable.

**Step 2: Design the restructure**

New prompt skeleton (pseudocode):
```
[COMMON HEADER — identical across all 4 prompts]
You are an AI news digest writer for 0to1log.

## Writing Rules (universal)
{universal writing rules — citations, paragraph counts, no predictions, etc.}

## Hallucination Guard
{HALLUCINATION_GUARD content — unchanged}

## Frontload / Body Locale Parity
{FRONTLOAD_LOCALE_PARITY + BODY_LOCALE_PARITY content — unchanged}

## Output JSON format
{JSON shape — unchanged}

[VARIABLE TAIL — differs per prompt]
## This run
- Persona: {persona}
- Category: {digest_type}

## Persona Guide
{persona_guide}

## Required Sections
{sections_description}

## Structure Example
{skeleton}

## Title Strategy
{title_strategy}

## Persona-specific rules
{learner_ko_rule, learner_opening_rule, etc. — only for learner persona}
```

Order invariant: the `[COMMON HEADER]` must be a byte-identical string across all 4 prompts. Any accidental variation (trailing whitespace, different newline counts) defeats the cache.

**Step 3: Write a test that asserts shared prefix**

Add to `backend/tests/test_news_digest_prompts.py`:

```python
def test_daily_digest_prompts_share_long_common_prefix():
    """All 4 daily writer prompts should share >=2000 chars of identical prefix.

    Caching relies on longest-common-prefix matching; the shared prefix must
    stay byte-identical across persona + digest_type combinations for
    prompt_cache_key routing to help.
    """
    prompts = [
        get_digest_prompt(cat, persona, [])
        for cat in ("research", "business")
        for persona in ("expert", "learner")
    ]
    # Find longest common prefix across all 4
    min_len = min(len(p) for p in prompts)
    common = 0
    for i in range(min_len):
        ch = prompts[0][i]
        if all(p[i] == ch for p in prompts):
            common = i + 1
        else:
            break
    assert common >= 2000, (
        f"Common prefix is only {common} chars — prompt restructure failed. "
        f"Expected >=2000 for effective caching."
    )
```

Run: expect FAIL on current code (common prefix is ~15 chars — "You are a ").

**Step 4: Restructure the f-string in `_build_digest_prompt`**

Move the common blocks (HALLUCINATION_GUARD, FRONTLOAD_LOCALE_PARITY, BODY_LOCALE_PARITY, citation rules, JSON format, structural warnings) ABOVE the variable interpolations. Keep behavior identical — only reordering, no content changes.

**Step 5: Run the full prompt test suite**

Run: `.venv/Scripts/python -m pytest tests/test_news_digest_prompts.py -v`

Expected: all 32+ pass (including the new common-prefix test).

**Step 6: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py backend/tests/test_news_digest_prompts.py
git commit -m "perf(news): restructure digest prompt for longer cached prefix

Moves HALLUCINATION_GUARD / FRONTLOAD_LOCALE_PARITY / BODY_LOCALE_PARITY
and other stable content above the persona/digest_type interpolations.
All 4 daily writer prompts now share ~2500-char identical prefix,
letting OpenAI's automatic cache + our prompt_cache_key routing
produce real hit rates across calls and days."
```

**Step 7: Re-run measurement after deploy**

Wait for next cron run; re-run `scripts/measure_cached_tokens.py --last 1`. Expected hit rate >=30% on writer stages. Record in plan file.

---

## Chunk 3: Phase 3 — Weekly Writer Reasoning Tuning (Deferred)

### Task 3.1: Add an experiment flag for weekly writer reasoning_effort

**Files:**
- Modify: `backend/services/pipeline.py:2400+` (weekly writer loop)
- Modify: `backend/core/config.py` (add experiment flag)

**Step 1: Add env-backed flag**

In `backend/core/config.py`, add:
```python
weekly_writer_reasoning_effort: str = "low"  # override to "medium" to A/B test
```

**Step 2: Wire through the 2 weekly writer calls**

Change both `_call_en` and `_call_ko` compat kwargs:
```python
reasoning_effort=settings.weekly_writer_reasoning_effort,
```

**Step 3: Commit**

```bash
git add backend/core/config.py backend/services/pipeline.py
git commit -m "chore(weekly): env flag for weekly writer reasoning_effort

Defaults to 'low' (unchanged behavior). Override via env to experiment."
```

**Step 4: Run A/B**

For 2 consecutive weekly runs, toggle the env var between runs. Record in plan:
- Run 1: WEEKLY_WRITER_REASONING_EFFORT=low → observe quality_score, subjective read
- Run 2: WEEKLY_WRITER_REASONING_EFFORT=medium → same

Compare. If medium is clearly better (quality_score +3 or more, subjective improvement), make it the default. Else keep low.

---

## Chunk 4: Followups (out of scope — deferred)

- **Batch tier for non-time-sensitive jobs**: candidate for handbook seed generation (no deadline), but breaks daily news cron. Not applicable here.
- **Tool-call citation API**: alternate architecture for URL enforcement. Already rejected in the URL compliance plan (2026-04-23-news-writer-url-compliance.md).
- **Advisor / blog advisor reasoning tuning**: each action has its own complexity profile. Separate audit plan if cost observability shows high spend there.
- **Verbosity for writer**: current default (medium) fits our heavily-structured sections. Changing to high would bloat output; low would under-deliver. Leave alone.

---

## Decision Log

- **2026-04-23**: Plan created. Scope limited to writer + QC + weekly (highest-volume, highest-unit-cost paths). Advisor/blog/product-advisor deferred to a separate audit once cost observability is deployed long enough to show per-feature spend.
- **2026-04-23**: Chose flex over batch for writers — batch 24h turnaround breaks daily cron SLA, flex keeps minutes-scale latency with the same 50% discount.
- **2026-04-23**: Chose to thread `prompt_cache_key` through helpers first and measure BEFORE attempting prompt restructure. OpenAI caching is opportunistic at minute-scale TTL — may suffice for repeated same-day calls without restructuring. Task 2.5 gated by Task 2.4 measurement.

## Phase 2 Cache Baseline

*(To be filled in when Task 2.3 runs. Record per-stage prompt_tokens, cached_tokens, hit % for Apr 23 rerun — the last run before flex + keys deployed.)*

## Phase 2 Cache After Migration

*(To be filled in when Task 2.4 runs. Record same metrics for the first run after flex + keys deploy. Compare to baseline. Decide whether Task 2.5 is needed.)*
