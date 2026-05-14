# GPT-5 Cost Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Apply targeted GPT-5 cost/observability optimizations to the news pipeline without changing output quality.

**Architecture:** Four independent, ordered tasks. We start with measurement (cached_tokens telemetry) so the cost impact of every later change is observable, then ship the one-line model downgrade with the largest safe saving, then probe an unverified discount tier, then ship the verbosity tweak only if SDK confirms support.

**Tech Stack:** OpenAI Python SDK (`openai>=1.x`), FastAPI, Supabase (`pipeline_logs.debug_meta` JSONB), pytest.

---

## Background

Audit findings (verified 2026-04-23):

- **Daily quality scoring** ([backend/services/pipeline_quality.py:440](backend/services/pipeline_quality.py#L440)) uses `settings.openai_model_reasoning` (`gpt-5-mini`).
- **Weekly quality scoring** ([backend/services/pipeline_quality.py:1066](backend/services/pipeline_quality.py#L1066)) uses `settings.openai_model_main` (`gpt-5`).
- Both call rubric-v2 quality prompts that share the same shape (`QUALITY_CHECK_*_EXPERT/LEARNER`). Same judge task, different model — no documented reason.
- `extract_usage_metrics` in [backend/services/agents/client.py:130-147](backend/services/agents/client.py#L130-L147) does **not** read `usage.prompt_tokens_details.cached_tokens`, so we have no visibility into prompt-cache hit rate even though OpenAI returns it for free.
- `_log_stage` ([backend/services/pipeline.py:461-520](backend/services/pipeline.py#L461-L520)) merges `input_tokens` / `output_tokens` into `debug_meta` but has no slot for cached.

Pricing reference (per [client.py:18-20](backend/services/agents/client.py#L18-L20)):
- gpt-5: $2.00 / $8.00 per 1M (in/out)
- gpt-5-mini: $0.25 / $2.00 per 1M (in/out) — **8× cheaper input, 4× cheaper output**
- gpt-5-nano: $0.05 / $0.40 per 1M

---

## Task Order Rationale

1. **Task D — cached_tokens telemetry first.** Zero behavior change, but every downstream optimization needs it to be measurable. Free signal that's currently being thrown away.
2. **Task A — weekly quality model downgrade.** One line. ~75% drop in weekly-quality token cost. Same prompts as daily already tolerate gpt-5-mini.
3. **Task C — service_tier="flex" probe.** Up to 50% off cron-path inference, but unverified for GPT-5. Probe-only first; ship only if probe passes.
4. **Task B — verbosity="low" for quality scoring.** GPT-5 supports a `verbosity` parameter; quality JSON outputs can be tighter. Verify SDK acceptance, then ship.

---

## Task D: Add cached_tokens telemetry

OpenAI returns `usage.prompt_tokens_details.cached_tokens` on every chat completion when prompt caching kicks in (≥1024 input tokens, identical prefix, within ~5 min). We're billed at 50% rate for cached input but currently can't see whether we're hitting cache.

### Task D.1: Extend `extract_usage_metrics` to include cached_tokens

**Files:**
- Modify: [backend/services/agents/client.py:130-147](backend/services/agents/client.py#L130-L147)
- Test: `backend/tests/test_usage_metrics.py` (new)

**Step 1: Write the failing test**

Create `backend/tests/test_usage_metrics.py`:

```python
from types import SimpleNamespace

from services.agents.client import extract_usage_metrics


def _resp(prompt: int, completion: int, cached: int | None) -> SimpleNamespace:
    details = None
    if cached is not None:
        details = SimpleNamespace(cached_tokens=cached)
    usage = SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        prompt_tokens_details=details,
    )
    return SimpleNamespace(usage=usage)


def test_extract_usage_metrics_reads_cached_tokens():
    metrics = extract_usage_metrics(_resp(1000, 500, cached=800), "gpt-5-mini")
    assert metrics["cached_tokens"] == 800


def test_extract_usage_metrics_cached_tokens_zero_when_no_details():
    metrics = extract_usage_metrics(_resp(1000, 500, cached=None), "gpt-5-mini")
    assert metrics["cached_tokens"] == 0


def test_extract_usage_metrics_cached_tokens_zero_when_field_missing():
    # SDK returns details object but no cached_tokens attribute
    usage = SimpleNamespace(
        prompt_tokens=100, completion_tokens=50, total_tokens=150,
        prompt_tokens_details=SimpleNamespace(),
    )
    resp = SimpleNamespace(usage=usage)
    metrics = extract_usage_metrics(resp, "gpt-5")
    assert metrics["cached_tokens"] == 0
```

**Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_usage_metrics.py -v
```

Expected: FAIL with `KeyError: 'cached_tokens'` on all three tests.

**Step 3: Implement minimal change**

Edit [backend/services/agents/client.py:130-147](backend/services/agents/client.py#L130-L147):

```python
def extract_usage_metrics(response: Any, model_name: str | None) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens_raw = getattr(usage, "total_tokens", None)
    total_tokens = (
        int(total_tokens_raw)
        if total_tokens_raw is not None
        else prompt_tokens + completion_tokens
    )

    details = getattr(usage, "prompt_tokens_details", None)
    cached_tokens = int(getattr(details, "cached_tokens", 0) or 0)

    return {
        "model_used": model_name,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "cached_tokens": cached_tokens,
        "tokens_used": total_tokens,
        "cost_usd": estimate_openai_cost_usd(model_name, prompt_tokens, completion_tokens),
    }
```

**Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_usage_metrics.py -v
```

Expected: PASS (3 passed).

**Step 5: Verify `merge_usage_metrics` still works**

`merge_usage_metrics` at [client.py:150-178](backend/services/agents/client.py#L150-L178) doesn't sum `cached_tokens` yet — that's fine for D.1, we'll handle in D.2 if needed. But add a regression test:

Append to `backend/tests/test_usage_metrics.py`:

```python
from services.agents.client import merge_usage_metrics


def test_merge_usage_metrics_preserves_existing_keys_with_cached_field():
    left = {"input_tokens": 100, "output_tokens": 50, "tokens_used": 150,
            "cached_tokens": 64, "cost_usd": 0.001, "model_used": "gpt-5-mini"}
    right = {"input_tokens": 200, "output_tokens": 100, "tokens_used": 300,
             "cached_tokens": 128, "cost_usd": 0.002, "model_used": "gpt-5-mini"}
    merged = merge_usage_metrics(left, right)
    assert merged["input_tokens"] == 300
    assert merged["output_tokens"] == 150
    # cached_tokens not yet summed — that's expected, just no crash
```

Run: `pytest tests/test_usage_metrics.py -v` → all 4 pass.

**Step 6: Sum cached_tokens in `merge_usage_metrics`**

Add the cached_tokens sum to the return dict at [client.py:172-178](backend/services/agents/client.py#L172-L178):

```python
    return {
        "model_used": merged_model,
        "input_tokens": int(left.get("input_tokens", 0) or 0) + int(right.get("input_tokens", 0) or 0),
        "output_tokens": int(left.get("output_tokens", 0) or 0) + int(right.get("output_tokens", 0) or 0),
        "cached_tokens": int(left.get("cached_tokens", 0) or 0) + int(right.get("cached_tokens", 0) or 0),
        "tokens_used": int(left.get("tokens_used", 0) or 0) + int(right.get("tokens_used", 0) or 0),
        "cost_usd": merged_cost,
    }
```

Update the test to assert the sum:

```python
    assert merged["cached_tokens"] == 192
```

Run: `pytest tests/test_usage_metrics.py -v` → 4 pass.

**Step 7: Commit**

```bash
git add backend/services/agents/client.py backend/tests/test_usage_metrics.py
git commit -m "feat(observability): track cached_tokens from OpenAI usage"
```

---

### Task D.2: Surface cached_tokens in pipeline_logs.debug_meta

**Files:**
- Modify: [backend/services/pipeline.py:481-486](backend/services/pipeline.py#L481-L486)
- Test: `backend/tests/test_log_stage_meta.py` (new)

**Step 1: Write the failing test**

Create `backend/tests/test_log_stage_meta.py`:

```python
import asyncio
from unittest.mock import MagicMock

from services.pipeline import _log_stage


def test_log_stage_includes_cached_tokens_in_debug_meta():
    supabase = MagicMock()
    insert = supabase.table.return_value.insert
    insert.return_value.execute.return_value = MagicMock()

    asyncio.run(_log_stage(
        supabase, "run-1", "test:stage", "ok", 0.0,
        usage={
            "model_used": "gpt-5-mini",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cached_tokens": 800,
            "tokens_used": 1500,
            "cost_usd": 0.001,
        },
    ))

    insert.assert_called_once()
    row = insert.call_args[0][0]
    assert row["debug_meta"]["cached_tokens"] == 800
    assert row["debug_meta"]["input_tokens"] == 1000


def test_log_stage_omits_cached_tokens_when_zero():
    supabase = MagicMock()
    insert = supabase.table.return_value.insert
    insert.return_value.execute.return_value = MagicMock()

    asyncio.run(_log_stage(
        supabase, "run-1", "test:stage", "ok", 0.0,
        usage={"input_tokens": 1000, "output_tokens": 500, "cached_tokens": 0},
    ))

    row = insert.call_args[0][0]
    assert "cached_tokens" not in row.get("debug_meta", {})
```

**Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_log_stage_meta.py -v
```

Expected: FAIL on first test (`KeyError: 'cached_tokens'`).

**Step 3: Implement**

Edit [backend/services/pipeline.py:481-486](backend/services/pipeline.py#L481-L486), add cached_tokens after the existing input/output_tokens block:

```python
    # Merge input/output tokens into debug_meta for easy UI access
    meta = dict(debug_meta or {})
    if usage.get("input_tokens"):
        meta["input_tokens"] = usage["input_tokens"]
    if usage.get("output_tokens"):
        meta["output_tokens"] = usage["output_tokens"]
    if usage.get("cached_tokens"):
        meta["cached_tokens"] = usage["cached_tokens"]
```

**Step 4: Run tests**

```bash
cd backend && pytest tests/test_log_stage_meta.py tests/test_usage_metrics.py -v
```

Expected: all pass.

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_log_stage_meta.py
git commit -m "feat(observability): surface cached_tokens in pipeline_logs.debug_meta"
```

**Step 6: Manual verification after first deploy**

After Railway redeploys, run one cron pipeline (`POST /api/cron/news` with the secret). In Supabase, query:

```sql
select pipeline_type, debug_meta->>'cached_tokens' as cached, debug_meta->>'input_tokens' as input
from pipeline_logs
where created_at > now() - interval '1 hour'
  and debug_meta ? 'cached_tokens'
order by created_at desc
limit 20;
```

Expected: rows where `cached > 0` for repeated stages (digest pass 2 of same locale, quality scoring after writer, etc). If `cached` is always 0 even for obviously-similar prompts: caching is not kicking in — investigate prompt prefix stability separately (out of scope for this plan).

---

## Task A: Downgrade weekly quality scoring to gpt-5-mini

**Why this is safe:** Daily quality scoring already uses `gpt-5-mini` on the same rubric-v2 prompt shape. The judge task — score a single article body against 10 evidence-anchored sub-scores — is well within mini's capability. The only difference is content length, which is bounded by the same `content[:35000]` truncation pattern.

**Files:**
- Modify: [backend/services/pipeline_quality.py:1066](backend/services/pipeline_quality.py#L1066)

**Step 1: Read current state**

Confirm line 1066 still reads:

```python
model = settings.openai_model_main
```

If it has drifted, adjust the edit accordingly.

**Step 2: Make the change**

Edit [backend/services/pipeline_quality.py:1066](backend/services/pipeline_quality.py#L1066):

```python
    model = settings.openai_model_reasoning  # gpt-5-mini — match daily quality
```

The trailing comment marks intent so future audits don't re-flip it.

**Step 3: Run existing weekly quality tests**

```bash
cd backend && pytest tests/test_weekly_quality_scoring.py -v --tb=short
```

Expected: all 16 pass (they mock the LLM, so model-name change shouldn't affect them — this just confirms no regression).

**Step 4: Lint**

```bash
cd backend && ruff check services/pipeline_quality.py
```

Expected: clean.

**Step 5: Commit**

```bash
git add backend/services/pipeline_quality.py
git commit -m "perf(weekly): score with gpt-5-mini to match daily quality model"
```

**Step 6: Post-deploy validation**

After deploy, regenerate one weekly digest (admin → `POST /api/admin/weekly` or wait for cron). Compare score for the same week against the most recent gpt-5 score:

- Expect score within ±5 points (LLM judge variance is already this wide).
- Expect issue list shape unchanged (rubric is the same).
- If score drops >10 points or issues become noticeably less specific: rollback the one line and re-investigate.

Watchpoint: the weekly content payload (`content_expert_en + content_expert_ko`) can approach the input-token limit. mini has the same 200k context as gpt-5-class, so this is fine, but flag if `tokens_used` jumps unexpectedly.

---

## Task C: Probe `service_tier="flex"` support for GPT-5

**Why probe first:** OpenAI documented `service_tier` for some models but support for `gpt-5` family on `chat.completions` is not guaranteed. A bad assumption here breaks all cron writes silently if the API rejects the parameter at request time.

**Files:**
- Create: `backend/scripts/probe_flex_tier.py`

**Step 1: Write the probe**

Create `backend/scripts/probe_flex_tier.py`:

```python
"""One-shot probe: does service_tier='flex' work with our GPT-5 models?

Usage: python -m scripts.probe_flex_tier
Reads OPENAI_API_KEY from env. Does NOT touch DB.
"""
import asyncio
import os
import sys

from openai import AsyncOpenAI


MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]


async def probe(model: str) -> tuple[str, str, int | None]:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60.0)
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_completion_tokens=20,
            service_tier="flex",
            reasoning_effort="low",
        )
        return (model, "ok", resp.usage.total_tokens)
    except Exception as e:
        return (model, f"ERROR: {type(e).__name__}: {e}", None)


async def main():
    results = await asyncio.gather(*(probe(m) for m in MODELS))
    print(f"\n{'Model':<15} {'Result':<60} {'Tokens'}")
    print("-" * 90)
    for model, status, tokens in results:
        print(f"{model:<15} {status[:60]:<60} {tokens or '-'}")
    failures = [r for r in results if not r[1].startswith("ok")]
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Run the probe locally**

```bash
cd backend && source .venv/Scripts/activate && python -m scripts.probe_flex_tier
```

Expected: one of two outcomes.

- **All 3 ok** → flex tier supported. Proceed to Step 3.
- **Any error like `BadRequestError: service_tier 'flex' not supported`** → STOP. Do not implement the integration. Add a one-line note to this plan (`Task C: rejected by API as of 2026-04-23`) and skip to Task B. Commit the probe script anyway as documentation.

**Step 3 (only if probe passed): Apply flex tier to cron-path quality calls**

Touch points (cron-path only; user-facing admin calls keep default tier for low latency):

- `_check_quality` daily call: [pipeline_quality.py:446](backend/services/pipeline_quality.py#L446)
- `_check_weekly_quality` weekly call: [pipeline_quality.py:1080](backend/services/pipeline_quality.py#L1080) and the matching learner call below it

The cleanest place to inject is `build_completion_kwargs`. Add an optional `service_tier: str | None = None` parameter to [client.py:76-95](backend/services/agents/client.py#L76-L95) and pass `service_tier="flex"` from the quality call sites only.

Write a unit test first that confirms the kwarg is forwarded:

```python
def test_build_completion_kwargs_forwards_service_tier():
    kwargs = build_completion_kwargs(
        "gpt-5-mini", messages=[{"role": "user", "content": "x"}],
        max_tokens=100, service_tier="flex",
    )
    assert kwargs["service_tier"] == "flex"


def test_build_completion_kwargs_omits_service_tier_when_none():
    kwargs = build_completion_kwargs(
        "gpt-5-mini", messages=[{"role": "user", "content": "x"}], max_tokens=100,
    )
    assert "service_tier" not in kwargs
```

Implement, run, commit:

```bash
git add backend/services/agents/client.py backend/services/pipeline_quality.py \
        backend/scripts/probe_flex_tier.py backend/tests/test_usage_metrics.py
git commit -m "perf(cron): use service_tier=flex for quality scoring"
```

**Step 4: Post-deploy validation**

After one cron run, query `pipeline_logs` for `quality:*` rows and confirm:
- `status = 'ok'` (no requests rejected)
- `cost_usd` for quality stages is ~50% of pre-change baseline (compare same-day-of-week)

If any `quality:*` row shows status=`error` with API-side rejection: revert the call sites only (keep the kwarg plumbing for future use).

---

## Task B: Set `verbosity="low"` for quality scoring

**Why optional:** GPT-5 supports a `verbosity` parameter (low/medium/high) that trims chattiness without changing reasoning depth. Quality scoring returns JSON — there's no upside to verbosity. Saving estimated 5-10% on output tokens for these calls.

**Risk:** SDK or model may not accept the parameter on `chat.completions.create`. Verify before shipping.

**Files:**
- Modify: [backend/services/agents/client.py:42-64](backend/services/agents/client.py#L42-L64) (`_apply_gpt5_compat`)
- Modify: [backend/services/agents/client.py:76-95](backend/services/agents/client.py#L76-L95) (`build_completion_kwargs`)
- Modify: [backend/services/pipeline_quality.py:447, 1081, learner call](backend/services/pipeline_quality.py)

**Step 1: Verify SDK acceptance with a probe**

Add a 5-line probe at the bottom of `backend/scripts/probe_flex_tier.py` (or a new `probe_verbosity.py`):

```python
async def probe_verbosity(model: str = "gpt-5-mini"):
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60.0)
    try:
        resp = await client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "Reply: ok"}],
            max_completion_tokens=20, verbosity="low", reasoning_effort="low",
        )
        print(f"verbosity=low ok, tokens={resp.usage.total_tokens}")
    except Exception as e:
        print(f"verbosity=low FAIL: {type(e).__name__}: {e}")
```

Run it. If it errors with "unknown parameter": skip Task B, this is not currently supported on chat.completions for our models.

**Step 2: TDD the kwarg plumbing**

Mirror Task C step 3's testing pattern: assert `verbosity` flows through `build_completion_kwargs` and is omitted when None.

**Step 3: Apply at quality call sites only**

Daily quality at [pipeline_quality.py:446-456](backend/services/pipeline_quality.py#L446-L456) and weekly at [pipeline_quality.py:1080-1091](backend/services/pipeline_quality.py#L1080-L1091): add `verbosity="low"` to the `build_completion_kwargs` call.

**Step 4: Commit and validate**

```bash
git commit -m "perf(quality): use verbosity=low for JSON-only scoring calls"
```

Post-deploy: compare `output_tokens` for quality stages before/after on the same content size. Expect 5-10% reduction. No quality score drift expected (LLM still produces full rubric JSON).

---

## After all four tasks

1. Update [vault/09-Implementation/plans/ACTIVE_SPRINT.md](vault/09-Implementation/plans/ACTIVE_SPRINT.md) — move this plan's bullet to done with evidence: PR/commit hashes, before/after cost row from `pipeline_logs`.
2. Move this plan to `vault/90-Archive/2026-04/plans-completed/`.
3. Update [project_news_pipeline_state.md](C:\Users\amy\.claude\projects\c--Users-amy-Desktop-0to1log\memory\project_news_pipeline_state.md) memory if pipeline cost profile changed materially.

## Rollback notes

- **Task D**: pure additive, no rollback needed.
- **Task A**: revert single line at [pipeline_quality.py:1066](backend/services/pipeline_quality.py#L1066).
- **Task C**: revert call-site `service_tier="flex"` arg; keep plumbing.
- **Task B**: revert call-site `verbosity="low"` arg; keep plumbing.

Each task is independently revertible — the order is for safety, not coupling.
