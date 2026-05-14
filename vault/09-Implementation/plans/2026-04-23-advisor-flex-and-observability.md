# Advisor Flex Tier Parity + Cost Observability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close two gaps discovered during the 2026-04-23 post–Phase-1 audit: (a) 8 handbook-writer call sites have `reasoning_effort="high"` + `prompt_cache_key` but are missing `service_tier="flex"` — losing the 50% tier discount that daily news writer enjoys; (b) three admin-editor code paths (`run_advise`, `run_blog_advise`, `run_deep_verify`) make live OpenAI calls but never insert into `pipeline_logs`, so admin-panel cost analytics and Phase 1.4 cache-hit verification both run blind on those actions.

**Architecture:**
- **Part 1 — Flex parity** threads `service_tier="flex"` into all 8 handbook generate/regen `compat_create_kwargs` calls (basic/advanced × ko/en × first-pass/improved). Zero new concepts; copy-paste pattern already proven on handbook QC and daily news writer.
- **Part 2 — Observability** introduces a shared `_log_advisor_call()` helper in `advisor.py` that mirrors the existing `_log_handbook_stage()` contract (model, tokens, cost, cached_tokens, service_tier, reasoning_tokens). Wires it into `run_advise` (news editor actions), `run_deep_verify` (step1 + step2), and a parallel `_log_blog_advisor_call()` in `blog_advisor.py` for blog editor actions. Also fixes the existing `_log_handbook_stage()` to include `reasoning_tokens` (trivial 1-liner, already surfaced by `extract_usage_metrics`).

**Tech Stack:** Python 3.11, OpenAI SDK, Supabase (pipeline_logs table), pytest.

**Non-goals:**
- Admin-editor cost dashboard UI changes (separate plan — Phase 1.4 SQL is manual)
- Adding `service_tier="flex"` to news advisor `generate` and `seo` actions — plan 2026-04-23-advisor-efficiency.md explicitly kept those on standard tier for interactive latency
- Instrumenting `_run_related_terms` / `_run_translate` (low-cost, low-volume paths) in this plan — if Part 2 stabilizes cleanly, extend in a follow-up

**Key reference files (read before starting):**
- `backend/services/agents/advisor.py:2140-2166` — `_log_handbook_stage()` reference pattern
- `backend/services/agents/client.py:168-216` — `extract_usage_metrics()` returns input/output/cached/reasoning/tier/cost; we already have all we need
- `backend/services/agents/advisor.py:149-195` — `run_advise()` (news editor dispatcher; no logging today)
- `backend/services/agents/advisor.py:219-336` — `run_deep_verify()` (two direct create() calls; no logging)
- `backend/services/agents/blog_advisor.py:129-187` — `run_blog_advise()` dispatcher (no logging)
- `backend/services/pipeline_digest.py:680-697` — canonical writer call pattern: `reasoning_effort="high"` + `service_tier="flex"` + `prompt_cache_key`

---

## Current State (for the executor)

Post-Phase-1 (2026-04-23 evening):

| Call site | file:line | reasoning_effort | service_tier | prompt_cache_key | logs to pipeline_logs? |
|---|---|---|---|---|---|
| Daily news writer (reference) | pipeline_digest.py:689 | high | flex | digest-* | yes (via pipeline_quality._log_stage) |
| Handbook writer basic KO | advisor.py:2204 | high | **MISSING** | hb-generate-basic | yes (via _log_handbook_stage) |
| Handbook writer basic EN | advisor.py:2380 | high | **MISSING** | hb-generate-en-basic | yes |
| Handbook writer advanced KO | advisor.py:2393 | high | **MISSING** | hb-generate-advanced | yes |
| Handbook writer advanced EN | advisor.py:2456 | high | **MISSING** | hb-generate-en-advanced | yes |
| Handbook regen basic KO | advisor.py:2498 | high | **MISSING** | hb-regen-basic | yes |
| Handbook regen basic EN | advisor.py:2522 | high | **MISSING** | hb-regen-en-basic | yes |
| Handbook regen advanced KO | advisor.py:2571 | high | **MISSING** | hb-regen-advanced | yes |
| Handbook regen advanced EN | advisor.py:2610 | high | **MISSING** | hb-regen-en-advanced | yes |
| News advisor 5 check actions | advisor.py:149 (run_advise) | medium | flex (Task 1.1) | advisor-* | **NO LOGGING** |
| deep_verify step1 | advisor.py:227 | medium | flex (Task 1.2) | advisor-deepverify-step1 | **NO LOGGING** |
| deep_verify step2 | advisor.py:312 | medium | flex (Task 1.2) | advisor-deepverify-step2 | **NO LOGGING** |
| Blog advisor 4 check actions | blog_advisor.py:129 | medium | flex (Task 1.3) | blog-advisor-* | **NO LOGGING** |
| `_log_handbook_stage()` meta dict | advisor.py:2145-2154 | — | — | — | captures service_tier + cached_tokens but **MISSING reasoning_tokens** |

**DB verification (2026-04-23 evening):** `SELECT COUNT(*) FROM pipeline_logs WHERE debug_meta ? 'service_tier' AND pipeline_type LIKE 'handbook.%' AND created_at >= NOW() - INTERVAL '14 days'` returns **0** — confirming that none of the handbook writer calls currently surface tier info (because flex isn't being requested, so OpenAI returns `service_tier=None` in the response).

---

## Chunk 1: Part 1 — Handbook Writer Flex Parity

### Task 1.1: Extend `test_advisor_compat.py` with source-level assertions for all 8 handbook writer sites

**Files:**
- Modify: `backend/tests/test_advisor_compat.py` (append new test function)

**Why:** The existing test file covers ACTION_CONFIG + deep_verify via `inspect.getsource`. Adding one parametrized test that enforces `service_tier="flex"` appearing within 5 lines of each known `prompt_cache_key="hb-generate-*"` or `hb-regen-*"` literal gives fast feedback while Task 1.2 edits happen. Source inspection is fine here — we're not verifying runtime behavior (that's what flex tier's own API guarantees), we're verifying the call-site config is uniform.

**Step 1: Write the failing test**

Append to `backend/tests/test_advisor_compat.py`:

```python
@pytest.mark.parametrize("cache_key", [
    "hb-generate-basic",
    "hb-generate-en-basic",
    "hb-generate-advanced",
    "hb-generate-en-advanced",
    "hb-regen-basic",
    "hb-regen-en-basic",
    "hb-regen-advanced",
    "hb-regen-en-advanced",
])
def test_handbook_writer_call_site_uses_flex(cache_key):
    """Every handbook writer/regen compat_create_kwargs call should pair
    reasoning_effort='high' + prompt_cache_key with service_tier='flex',
    matching the daily news writer pattern.

    Verified by source inspection — the call is far enough inside nested
    functions that mock-based verification would be brittle.
    """
    from pathlib import Path

    src = Path("services/agents/advisor.py").read_text(encoding="utf-8")
    # Find the block containing this cache_key literal
    marker = f'prompt_cache_key="{cache_key}"'
    idx = src.find(marker)
    assert idx != -1, f"cache_key {cache_key!r} not found in advisor.py"
    # Look at the surrounding 20 lines for service_tier="flex"
    block_start = max(0, idx - 600)
    block_end = min(len(src), idx + 200)
    block = src[block_start:block_end]
    assert 'service_tier="flex"' in block, (
        f"{cache_key} call site is missing service_tier='flex'. "
        f"Expected within ±several lines of the prompt_cache_key literal."
    )
```

**Step 2: Run test — verify it fails**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py::test_handbook_writer_call_site_uses_flex -v`
Expected: 8/8 FAIL with `AssertionError: hb-generate-basic call site is missing service_tier='flex'`.

**Step 3: Commit the failing test** (optional per TDD; ensures test is reviewed before the fix)

```bash
git add backend/tests/test_advisor_compat.py
git commit -m "test(advisor): add flex-parity assertion for 8 handbook writer call sites"
```

### Task 1.2: Add `service_tier="flex"` to all 8 handbook writer/regen `compat_create_kwargs` calls

**Files:**
- Modify: `backend/services/agents/advisor.py` at the following call sites (verify line numbers with a fresh grep — prior parallel commits may have shifted them by a few lines):
  - `hb-generate-basic` (~2204)
  - `hb-generate-en-basic` (~2380)
  - `hb-generate-advanced` (~2393)
  - `hb-generate-en-advanced` (~2456)
  - `hb-regen-basic` (~2498)
  - `hb-regen-en-basic` (~2522)
  - `hb-regen-advanced` (~2571)
  - `hb-regen-en-advanced` (~2610)

**Step 1: Locate all 8 sites**

Run: `cd backend && grep -n 'prompt_cache_key="hb-\(generate\|regen\)' services/agents/advisor.py`
Expected: 8 matches.

**Step 2: For each site, add `service_tier="flex"` adjacent to the existing `reasoning_effort="high"` + `prompt_cache_key=…`**

Each block currently looks like:
```python
resp1 = await client.chat.completions.create(
    **compat_create_kwargs(
        model,
        messages=[...],
        response_format={"type": "json_object"},
        max_tokens=16000,
        prompt_cache_key="hb-generate-basic",
        reasoning_effort="high",
    )
)
```

Add `service_tier="flex",` on a new line after `reasoning_effort="high",`:

```python
resp1 = await client.chat.completions.create(
    **compat_create_kwargs(
        model,
        messages=[...],
        response_format={"type": "json_object"},
        max_tokens=16000,
        prompt_cache_key="hb-generate-basic",
        reasoning_effort="high",
        service_tier="flex",
    )
)
```

Do not change kwarg order elsewhere. Do not add `service_tier` to non-generate/regen call sites (QC/critique calls already have it; classifier/extractor/gate/translate are lightweight and not priced for flex).

**Step 3: Run the test — verify it passes**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py::test_handbook_writer_call_site_uses_flex -v`
Expected: 8/8 PASS.

**Step 4: Run the full test_advisor_compat suite**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py tests/test_blog_advisor_compat.py -v`
Expected: all existing tests plus the new 8 = 24 pass.

**Step 5: Lint**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check services/agents/advisor.py tests/test_advisor_compat.py`
Expected: `All checks passed!`

**Step 6: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_advisor_compat.py
git commit -m "perf(advisor): flex tier on 8 handbook writer/regen calls

Closes the gap flagged in the 2026-04-23 post-Phase-1 audit: writer and
regen calls had reasoning_effort=high + prompt_cache_key set but were
missing service_tier=flex, losing the 50% tier discount. Mirrors the
daily news writer pattern (pipeline_digest.py:689) which already uses
all three together.

Eight call sites affected (hb-generate-{basic,advanced} × {ko,en} and
hb-regen-{basic,advanced} × {ko,en}). QC/critique calls already had
flex; classifier/extractor/gate/translate intentionally stay on
standard tier (low cost, low volume — no meaningful savings)."
```

---

### Task 1.3: Add `reasoning_tokens` to `_log_handbook_stage()`

**Files:**
- Modify: `backend/services/agents/advisor.py:2145-2156` (inside `_log_handbook_stage`)
- Test: `backend/tests/test_advisor_compat.py` (append source-level test)

**Why:** `extract_usage_metrics()` (client.py:206) already returns `reasoning_tokens`. The existing `_log_handbook_stage` writes `cached_tokens` and `service_tier` when present, but silently drops `reasoning_tokens`. The admin analytics page has a Token Distribution donut but no way to see how much of gpt-5 output is reasoning-vs-visible; fixing this gives us that lever empirically for Phase-2 reasoning_effort A/B.

**Step 1: Write the failing test**

Append to `backend/tests/test_advisor_compat.py`:

```python
def test_log_handbook_stage_includes_reasoning_tokens():
    """_log_handbook_stage should record reasoning_tokens alongside
    cached_tokens and service_tier. extract_usage_metrics already returns it.
    Needed for Phase-2 reasoning_effort A/B measurement.
    """
    from pathlib import Path

    src = Path("services/agents/advisor.py").read_text(encoding="utf-8")
    # Locate the _log_handbook_stage function body
    marker = "def _log_handbook_stage("
    idx = src.find(marker)
    assert idx != -1
    # Next ~600 chars contain the function
    body = src[idx:idx + 800]
    assert "reasoning_tokens" in body, (
        "_log_handbook_stage does not record reasoning_tokens — "
        "extract_usage_metrics returns it but it gets dropped."
    )
```

**Step 2: Run — verify fail**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py::test_log_handbook_stage_includes_reasoning_tokens -v`
Expected: FAIL.

**Step 3: Add the 2 lines to `_log_handbook_stage`**

In `backend/services/agents/advisor.py:2145-2154`, add a conditional mirroring the existing `cached_tokens` guard. Final block:

```python
meta = {
    "term": req.term,
    "source": source,
    "input_tokens": usage.get("input_tokens"),
    "output_tokens": usage.get("output_tokens"),
}
if usage.get("cached_tokens") is not None:
    meta["cached_tokens"] = usage["cached_tokens"]
if usage.get("reasoning_tokens") is not None:
    meta["reasoning_tokens"] = usage["reasoning_tokens"]
if usage.get("service_tier"):
    meta["service_tier"] = usage["service_tier"]
```

Guard on `is not None` (not truthy) because `reasoning_tokens == 0` is a meaningful value — it means the call used `reasoning_effort="minimal"` or the model didn't emit any reasoning tokens for that call.

**Step 4: Run — verify pass**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py -v`
Expected: all pass, including the new one.

**Step 5: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_advisor_compat.py
git commit -m "obs(advisor): record reasoning_tokens in _log_handbook_stage

extract_usage_metrics already returns reasoning_tokens (client.py:206)
but _log_handbook_stage was dropping it. Surfacing it into
pipeline_logs.debug_meta gives Phase-2 reasoning_effort A/B a direct
lever: we can measure how much of the writer's output budget is
'thinking' vs visible content and decide medium vs high empirically."
```

---

## Chunk 2: Part 2 — Admin Editor Cost Observability

**Gate:** Chunk 1 Tasks 1.1–1.3 land cleanly before starting Chunk 2. Observability on a misconfigured call site produces misleading data.

### Task 2.1: Add `_log_advisor_call()` helper in `advisor.py`

**Files:**
- Modify: `backend/services/agents/advisor.py` (add new helper near `run_advise`, ~line 140 before the function definition)
- Test: `backend/tests/test_advisor_compat.py`

**Why:** `run_advise`, `run_deep_verify`, and eventually the other advisor.py entry points all need the same shape of log insert. Extract once, share across three call paths. Signature mirrors `_log_handbook_stage` so future readers see a uniform pattern, but it's a module-level function (not nested inside a coroutine) because the three callers live in different scopes.

**Step 1: Write the failing test**

Append to `backend/tests/test_advisor_compat.py`:

```python
def test_log_advisor_call_helper_exists_and_is_callable():
    """advisor.py should expose _log_advisor_call(stage, usage, extra_meta)
    as a module-level helper for run_advise / run_deep_verify logging.
    """
    from services.agents import advisor

    assert hasattr(advisor, "_log_advisor_call")
    assert callable(advisor._log_advisor_call)


def test_log_advisor_call_writes_all_tier_and_token_fields():
    """When tier/cached/reasoning are present, they appear in debug_meta."""
    from unittest.mock import MagicMock, patch

    from services.agents import advisor

    fake_table = MagicMock()
    fake_supabase = MagicMock()
    fake_supabase.table.return_value = fake_table

    usage = {
        "model_used": "gpt-5-mini",
        "input_tokens": 1500,
        "output_tokens": 200,
        "cached_tokens": 1024,
        "reasoning_tokens": 140,
        "tokens_used": 1700,
        "cost_usd": 0.0008,
        "service_tier": "flex",
    }

    with patch("services.agents.advisor.get_supabase", return_value=fake_supabase):
        advisor._log_advisor_call("advisor.review", usage, extra_meta={"post_id": "abc"})

    fake_table.insert.assert_called_once()
    payload = fake_table.insert.call_args[0][0]
    assert payload["pipeline_type"] == "advisor.review"
    assert payload["tokens_used"] == 1700
    assert payload["cost_usd"] == 0.0008
    meta = payload["debug_meta"]
    assert meta["cached_tokens"] == 1024
    assert meta["reasoning_tokens"] == 140
    assert meta["service_tier"] == "flex"
    assert meta["post_id"] == "abc"
```

**Step 2: Run — verify fail**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py::test_log_advisor_call_helper_exists_and_is_callable -v`
Expected: FAIL (`AttributeError` or `assert hasattr`).

**Step 3: Implement the helper**

Add to `backend/services/agents/advisor.py` immediately before `async def run_advise`:

```python
def _log_advisor_call(
    stage: str,
    usage: dict,
    extra_meta: dict | None = None,
) -> None:
    """Log one admin-editor advisor call to pipeline_logs. Never raises.

    Parallels _log_handbook_stage but lives at module scope so
    run_advise / run_deep_verify / run_blog_advise can share it.

    stage:
        'advisor.<action>' for news editor actions
        'advisor.deepverify.step1' / 'advisor.deepverify.step2'
        Blog uses a separate helper with its own prefix.

    Fields recorded — same shape as _log_handbook_stage so admin
    analytics can treat handbook and advisor logs uniformly.
    """
    supabase = get_supabase()
    if not supabase:
        return
    try:
        meta = {
            "source": "manual",
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        }
        if usage.get("cached_tokens") is not None:
            meta["cached_tokens"] = usage["cached_tokens"]
        if usage.get("reasoning_tokens") is not None:
            meta["reasoning_tokens"] = usage["reasoning_tokens"]
        if usage.get("service_tier"):
            meta["service_tier"] = usage["service_tier"]
        if extra_meta:
            meta.update(extra_meta)
        supabase.table("pipeline_logs").insert({
            "pipeline_type": stage,
            "status": "success",
            "model_used": usage.get("model_used"),
            "tokens_used": usage.get("tokens_used"),
            "cost_usd": usage.get("cost_usd"),
            "debug_meta": meta,
        }).execute()
    except Exception as e:
        logger.warning("Failed to log advisor %s stage: %s", stage, e)
```

**Step 4: Run — verify pass**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py -v`
Expected: all pass.

**Step 5: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_advisor_compat.py
git commit -m "obs(advisor): add _log_advisor_call helper for admin-editor paths

Mirrors _log_handbook_stage but lives at module scope so run_advise,
run_deep_verify, and (next commit) run_blog_advise can share it.
Source='manual' distinguishes admin-editor logs from pipeline cron
logs at the query layer."
```

---

### Task 2.2: Wire `run_advise` (news editor) to call `_log_advisor_call`

**Files:**
- Modify: `backend/services/agents/advisor.py:149-195` (inside `run_advise`)
- Test: `backend/tests/test_advisor_compat.py`

**Why:** News editor runs 7 actions (generate/seo/review/factcheck/conceptcheck/voicecheck/retrocheck). None are currently logged. After this task the admin cost chart shows all of them under pipeline_type `advisor.<action>`.

**Step 1: Write the failing test**

Append to `backend/tests/test_advisor_compat.py`:

```python
@pytest.mark.asyncio
async def test_run_advise_logs_to_pipeline_logs():
    """run_advise should call _log_advisor_call with pipeline_type='advisor.<action>'
    after a successful OpenAI call.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.agents import advisor
    from models.advisor import AiAdviseRequest

    # Mock OpenAI response
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content='{"score": 8, "comments": []}'))]
    mock_resp.usage = MagicMock(completion_tokens=42, prompt_tokens=100, total_tokens=142)
    mock_resp.service_tier = "flex"

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    req = AiAdviseRequest(
        action="review", post_id="test-1", title="t", content="c", category="study",
    )

    with patch("services.agents.advisor.get_openai_client", return_value=mock_client), \
         patch("services.agents.advisor._log_advisor_call") as mock_log:
        await advisor.run_advise(req)

    mock_log.assert_called_once()
    stage_arg = mock_log.call_args[0][0]
    assert stage_arg == "advisor.review"
```

**Step 2: Run — verify fail**

Expected: FAIL (`_log_advisor_call` was not called, or imported but not wired).

**Step 3: Wire the helper**

In `backend/services/agents/advisor.py:149-195`, after the existing `response = await client.chat.completions.create(...)` and parsing block, add:

```python
usage = extract_usage_metrics(response, model)
_log_advisor_call(
    f"advisor.{req.action}",
    usage,
    extra_meta={"post_id": req.post_id} if getattr(req, "post_id", None) else None,
)
```

Position: after `parse_ai_json(...)` and validator block, before `return data, model, tokens`. Do not replace the existing `tokens = response.usage.completion_tokens…` line — keep the return signature stable.

**Step 4: Run — verify pass**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py -v`
Expected: all pass.

**Step 5: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_advisor_compat.py
git commit -m "obs(advisor): log news-editor run_advise calls to pipeline_logs

News-editor actions (generate/seo/review/factcheck/conceptcheck/
voicecheck/retrocheck) now appear in pipeline_logs under
pipeline_type='advisor.<action>'. Admin analytics can now see their
cost + cached/reasoning/tier telemetry, unblocking Phase-1.4 cache-hit
verification on the five flex-enabled check actions."
```

---

### Task 2.3: Wire `run_deep_verify` step1 + step2 to log

**Files:**
- Modify: `backend/services/agents/advisor.py:219-336`
- Test: `backend/tests/test_advisor_compat.py`

**Why:** deep_verify makes 2 OpenAI calls per invocation (claim extract + verify). Logging each separately matches the handbook writer pattern (one log per call) and lets us see step1-vs-step2 cache behavior independently.

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_run_deep_verify_logs_both_steps():
    """run_deep_verify should log step1 and step2 with distinct pipeline_type
    values so cache telemetry is separable (the two steps use different
    system prompts and therefore different cache slots).
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.agents import advisor
    from models.advisor import AiAdviseRequest

    # Two OpenAI responses, one per step
    def _mk_resp(content):
        r = MagicMock()
        r.choices = [MagicMock(message=MagicMock(content=content))]
        r.usage = MagicMock(completion_tokens=10, prompt_tokens=100, total_tokens=110)
        r.service_tier = "flex"
        return r

    step1_resp = _mk_resp('{"claims": []}')  # Empty claims path — step2 skipped

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[step1_resp])

    req = AiAdviseRequest(
        action="deepverify", post_id="test-1", title="t", content="c", category="study",
    )

    with patch("services.agents.advisor.get_openai_client", return_value=mock_client), \
         patch("services.agents.advisor._log_advisor_call") as mock_log:
        await advisor.run_deep_verify(req)

    # Empty-claims path logs step1 only (step2 is short-circuited)
    assert mock_log.call_count == 1
    assert mock_log.call_args_list[0][0][0] == "advisor.deepverify.step1"
```

Add a second test covering the non-empty claims path (both steps log):

```python
@pytest.mark.asyncio
async def test_run_deep_verify_logs_step2_when_claims_present():
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.agents import advisor
    from models.advisor import AiAdviseRequest

    def _mk_resp(content):
        r = MagicMock()
        r.choices = [MagicMock(message=MagicMock(content=content))]
        r.usage = MagicMock(completion_tokens=10, prompt_tokens=100, total_tokens=110)
        r.service_tier = "flex"
        return r

    step1_resp = _mk_resp('{"claims": [{"claim": "test claim"}]}')
    step2_resp = _mk_resp('{"claims": [{"claim": "test claim", "verdict": "supported"}]}')

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[step1_resp, step2_resp])

    req = AiAdviseRequest(
        action="deepverify", post_id="test-1", title="t",
        content="no urls to check", category="study",
    )

    # Stub out search + URL check to avoid external deps
    with patch("services.agents.advisor.get_openai_client", return_value=mock_client), \
         patch("services.agents.advisor._log_advisor_call") as mock_log, \
         patch("services.agents.advisor._extract_urls_from_content", return_value=[]):
        # Force settings to skip search to keep the test hermetic
        with patch("services.agents.advisor.settings") as mock_settings:
            mock_settings.tavily_api_key = None
            mock_settings.exa_api_key = None
            mock_settings.openai_model_reasoning = "gpt-5-mini"
            await advisor.run_deep_verify(req)

    stages = [c[0][0] for c in mock_log.call_args_list]
    assert stages == ["advisor.deepverify.step1", "advisor.deepverify.step2"]
```

**Step 2: Run — verify fail**

Both new tests should FAIL.

**Step 3: Wire the helper into run_deep_verify**

After each `client.chat.completions.create(**stepN_kwargs)` in `run_deep_verify`:

After step1 (around line 237):
```python
usage1 = extract_usage_metrics(resp1, model)
_log_advisor_call("advisor.deepverify.step1", usage1,
                  extra_meta={"post_id": getattr(req, "post_id", None)})
```

After step2 (around line 322):
```python
usage2 = extract_usage_metrics(resp2, model)
_log_advisor_call("advisor.deepverify.step2", usage2,
                  extra_meta={"post_id": getattr(req, "post_id", None)})
```

Do not change the existing `total_tokens +=` accumulation. It reports back to the caller as the return tuple — that's independent from pipeline_logs.

**Step 4: Run — verify pass**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_advisor_compat.py -v`
Expected: all pass including both new tests.

**Step 5: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_advisor_compat.py
git commit -m "obs(advisor): log deep_verify step1 + step2 independently

Each step uses a different system prompt so cache slots are separate;
logging them independently lets admin analytics measure cache hit rate
per step. Empty-claims short-circuit path correctly logs step1 only."
```

---

### Task 2.4: Add `_log_blog_advisor_call` helper + wire `run_blog_advise`

**Files:**
- Modify: `backend/services/agents/blog_advisor.py` (add helper + wire into dispatcher)
- Test: `backend/tests/test_blog_advisor_compat.py`

**Why:** Blog editor uses a separate module + separate cache key namespace (`blog-advisor-*`). Keeping logging symmetric — its own helper with `pipeline_type="blog-advisor.<action>"` — means admin analytics queries can filter handbook/news/blog volumes cleanly.

**Step 1: Write the failing test**

Append to `backend/tests/test_blog_advisor_compat.py`:

```python
def test_log_blog_advisor_call_helper_exists():
    from services.agents import blog_advisor

    assert hasattr(blog_advisor, "_log_blog_advisor_call")
    assert callable(blog_advisor._log_blog_advisor_call)


@pytest.mark.asyncio
async def test_run_blog_advise_logs_to_pipeline_logs():
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.agents import blog_advisor
    from models.blog_advisor import BlogAdviseRequest

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content='{"score": 8, "comments": []}'))]
    mock_resp.usage = MagicMock(completion_tokens=42, prompt_tokens=100, total_tokens=142)
    mock_resp.service_tier = "flex"

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    req = BlogAdviseRequest(
        action="review", post_id="blog-1", title="t", content="c",
        category="engineering", locale="en",
    )

    with patch("services.agents.blog_advisor.get_openai_client", return_value=mock_client), \
         patch("services.agents.blog_advisor._log_blog_advisor_call") as mock_log:
        await blog_advisor.run_blog_advise(req)

    mock_log.assert_called_once()
    assert mock_log.call_args[0][0] == "blog-advisor.review"
```

**Step 2: Run — verify fail**

Expected: FAIL (`_log_blog_advisor_call` missing).

**Step 3: Add helper + wire**

In `backend/services/agents/blog_advisor.py`, near the top after imports, add:

```python
def _log_blog_advisor_call(
    stage: str,
    usage: dict,
    extra_meta: dict | None = None,
) -> None:
    """Log one blog-editor advisor call to pipeline_logs. Never raises.

    stage: 'blog-advisor.<action>'
    """
    supabase = get_supabase()
    if not supabase:
        return
    try:
        meta = {
            "source": "manual",
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        }
        if usage.get("cached_tokens") is not None:
            meta["cached_tokens"] = usage["cached_tokens"]
        if usage.get("reasoning_tokens") is not None:
            meta["reasoning_tokens"] = usage["reasoning_tokens"]
        if usage.get("service_tier"):
            meta["service_tier"] = usage["service_tier"]
        if extra_meta:
            meta.update(extra_meta)
        supabase.table("pipeline_logs").insert({
            "pipeline_type": stage,
            "status": "success",
            "model_used": usage.get("model_used"),
            "tokens_used": usage.get("tokens_used"),
            "cost_usd": usage.get("cost_usd"),
            "debug_meta": meta,
        }).execute()
    except Exception as e:
        logger.warning("Failed to log blog advisor %s stage: %s", stage, e)
```

Make sure `from services.agents.client import extract_usage_metrics, get_supabase` is at the top. (Check current imports first; `get_openai_client` is there, `get_supabase` may need adding.)

Then in `run_blog_advise` after the `response = await client.chat.completions.create(...)` and parse/validate block, before `return`:

```python
usage = extract_usage_metrics(response, model)
_log_blog_advisor_call(
    f"blog-advisor.{req.action}",
    usage,
    extra_meta={"post_id": req.post_id} if getattr(req, "post_id", None) else None,
)
```

**Step 4: Run — verify pass**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_blog_advisor_compat.py -v
```

Expected: all pass.

**Step 5: Commit**

```bash
git add backend/services/agents/blog_advisor.py backend/tests/test_blog_advisor_compat.py
git commit -m "obs(blog_advisor): log blog-editor check/creative actions

Mirrors advisor.py's _log_advisor_call pattern but with its own
'blog-advisor.<action>' pipeline_type prefix so admin analytics can
split handbook/news/blog traffic cleanly. 9 actions start appearing
in pipeline_logs: outline/draft/rewrite/suggest/generate +
review/conceptcheck/voicecheck/retrocheck."
```

---

## Chunk 3: Post-Deploy Verification

### Task 3.1: Verify logs flow correctly (manual — after 1-2 days of traffic)

**No code changes — this is a checkpoint.**

After Chunks 1+2 merge and admin-editor traffic accumulates (~2 days of handbook term editing + article reviews), run:

```sql
-- Handbook writer flex parity verification
SELECT
  pipeline_type,
  COUNT(*) as calls,
  COUNT(*) FILTER (WHERE debug_meta->>'service_tier' = 'flex') as flex_calls,
  AVG((debug_meta->>'cached_tokens')::int) FILTER (WHERE debug_meta ? 'cached_tokens') as avg_cached,
  AVG((debug_meta->>'reasoning_tokens')::int) FILTER (WHERE debug_meta ? 'reasoning_tokens') as avg_reasoning
FROM pipeline_logs
WHERE pipeline_type LIKE 'handbook.generate.%'
  AND created_at >= NOW() - INTERVAL '2 days'
GROUP BY pipeline_type
ORDER BY pipeline_type;
```

**Expected:** `flex_calls == calls` for every row (100% of writer calls served by flex). `avg_reasoning` > 0 confirming reasoning_tokens capture works. `avg_cached` > 0 after a ~5min warmup window when admin is editing related terms (cache hits kick in after prefix shares across calls).

```sql
-- Admin editor observability gate — verifies Chunk 2 deployed
SELECT
  pipeline_type,
  COUNT(*) as calls,
  SUM(cost_usd) as total_cost
FROM pipeline_logs
WHERE pipeline_type IN (
  'advisor.review', 'advisor.factcheck', 'advisor.conceptcheck',
  'advisor.voicecheck', 'advisor.retrocheck',
  'advisor.deepverify.step1', 'advisor.deepverify.step2',
  'blog-advisor.review', 'blog-advisor.conceptcheck'
)
  AND created_at >= NOW() - INTERVAL '2 days'
GROUP BY pipeline_type;
```

**Expected:** Non-empty rows for any action the admin has used in the last 2 days. Rows with `cost_usd` > 0, `tokens_used` > 0.

### Task 3.2: Document outcome

**Files:**
- Create: `vault/12-Journal-&-Decisions/2026-MM-DD-advisor-flex-observability-outcome.md`

Record: Which actions now show data, cache_hit_ratio on the 5 flex-enabled check actions (inputs to Phase-2 reasoning_effort A/B decision from plan `2026-04-23-advisor-efficiency.md`), observed cost reduction on handbook writer vs. pre-flex baseline.

---

## Success Criteria

Plan is complete when:
- [ ] Chunk 1 Task 1.2 merged: all 8 handbook writer/regen sites include `service_tier="flex"`
- [ ] Chunk 1 Task 1.3 merged: `_log_handbook_stage` captures `reasoning_tokens`
- [ ] Chunk 2 Tasks 2.1–2.4 merged: `_log_advisor_call` + `_log_blog_advisor_call` wired into `run_advise`, `run_deep_verify`, `run_blog_advise`
- [ ] Chunk 3 Task 3.1 verification query shows flex_calls == calls on handbook writer rows and non-zero rows for new `advisor.*` / `blog-advisor.*` pipeline types

## Rollback Criteria

- **Flex regression (Chunk 1):** If handbook writer tail-latency p95 exceeds 12 minutes (current standard-tier p95 is ~4 min; flex typically adds 2-5 min for high-reasoning), revert just `service_tier="flex"` from the 4 advanced calls (longest outputs) but keep basic calls on flex. Preserves the majority of the discount at modest latency cost.
- **Logging regression (Chunk 2):** If `pipeline_logs` insert errors ever surface to the user (they shouldn't — `_log_*` functions catch exceptions), degrade by no-oping the helper via a settings flag. Do not roll back `service_tier="flex"` or `prompt_cache_key` changes — those are independent of logging.

---

## Execution Handoff

Plan complete and saved to `vault/09-Implementation/plans/2026-04-23-advisor-flex-and-observability.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration. **Warning:** concurrent sessions have been modifying advisor.py heavily today — subagent output may collide with unrelated parallel commits (as happened earlier with Task 1.1). If choosing this option, pick a calmer window.

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints. Recommended if other sessions are likely to keep committing to advisor.py.

**3. Direct execution (this session, no subagents)** — I implement each task sequentially. Appropriate for small tasks like these (most are <20 lines). Reviews are lighter-touch but concurrent-collision risk is minimized (fewer context handoffs).

Which approach?
