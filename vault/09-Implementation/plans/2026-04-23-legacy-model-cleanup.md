# Legacy Model Code Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove dead code, redundant parameters, and stale references from backend agents code following the migration to gpt-5 family models. Reduce cognitive noise without breaking any current functionality.

**Architecture:**
- All production models are now gpt-5 family (`gpt-5`, `gpt-5-mini`, `gpt-5-nano`). The compat wrapper in `client.py` automatically strips temperature, multiplies token budgets 3x, and injects `reasoning_effort="low"`. Consequently, `temperature` values passed from 41 call sites are silently discarded. Pricing entries and code paths for gpt-4*, o-series also exist but never execute.
- This cleanup removes that dead surface without changing runtime behavior.

**Tech Stack:** Python 3.11+, FastAPI, OpenAI SDK, pytest.

**Ground rules:**
- Do NOT remove `service_tier`, `verbosity`, or `prompt_cache_key` parameters — all three have active or near-term use (`service_tier` in flex tier retries; `verbosity` planned for A/B; `prompt_cache_key` planned for caching rollout).
- Do NOT remove `is_o_series()` function — kept as small documentation of the o-series family even if unused today.
- Do NOT remove `parse_ai_json()` markdown fallback — cheap safety net.
- Every task ends with Python syntax check + commit.

---

## Task 1: Remove `temperature` from `build_completion_kwargs()` signature and strip all call-site temperature arguments

**Context:** `_apply_gpt5_compat()` strips `temperature` for gpt-5 models (client.py:91-92), so every temperature value passed today is discarded. The parameter is misleading — a reader sees `temperature=0.7` and assumes it affects output when it does not.

**Files to modify:**
- `backend/services/agents/client.py` (signature change)
- `backend/services/agents/advisor.py` (ACTION_CONFIG + call sites, ~22 temperature references)
- `backend/services/agents/blog_advisor.py` (BLOG_ACTION_CONFIG + call sites, ~13 references)
- `backend/services/agents/product_advisor.py` (~9 call sites)
- `backend/services/agents/fact_extractor.py` (1 call site)
- `backend/services/agents/persona_writer.py` (1 call site)
- `backend/services/agents/ranking.py` (5 call sites)
- `backend/services/pipeline.py` (2 call sites)
- `backend/services/pipeline_digest.py` (5 call sites)
- `backend/tests/test_agents_client.py` (update temperature-related assertions)

### Step 1.1: Run exhaustive grep to get the definitive list

Run: `cd backend && rg -n "temperature" services/agents/ services/pipeline.py services/pipeline_digest.py tests/`
Expected: ~50+ matches across the listed files.

Keep this list — it's the authoritative checklist for the next steps.

### Step 1.2: Delete `temperature` key from `ACTION_CONFIG` dicts in `advisor.py`

In `backend/services/agents/advisor.py` around lines 61-107, remove all `"temperature": 0.X,` lines from inside each action-config dict. Example edit:

Before:
```python
"generate": {
    "max_tokens": 4096,
    "temperature": 0.3,
    ...
},
```

After:
```python
"generate": {
    "max_tokens": 4096,
    ...
},
```

Apply to all action configs in the file (there are 7).

### Step 1.3: Delete `temperature=config["temperature"]` from the call site using ACTION_CONFIG

In `backend/services/agents/advisor.py` line 172, remove the `temperature=config["temperature"],` line from the `build_completion_kwargs()` call.

### Step 1.4: Delete all remaining `temperature=` from advisor.py direct call sites

Using the grep list from Step 1.1, remove every `temperature=` argument from `advisor.py` (approximate lines: 231, 317, 495, 580, 867, 928, 1188, 1234, 1283, 1782, 2190, 2365, 2377, 2439, 2479, 2501, 2548, 2585, 3032, 3079).

Each edit removes exactly one line. Example:

Before:
```python
compat_create_kwargs(
    model,
    messages=[...],
    max_tokens=2048,
    temperature=0.1,
    response_format={"type": "json_object"},
)
```

After:
```python
compat_create_kwargs(
    model,
    messages=[...],
    max_tokens=2048,
    response_format={"type": "json_object"},
)
```

### Step 1.5: Repeat for `blog_advisor.py`

- Delete `"temperature": 0.X,` from all action configs (lines 55-116, 9 configs).
- Remove `temperature=config["temperature"]` on line 173.
- Remove individual `temperature=` on lines 241, 253, 365.

### Step 1.6: Repeat for remaining files

Remove `temperature=` from:
- `product_advisor.py` (lines 520, 685, 723, 764, 801, 907, 1099, 1129, 1162)
- `fact_extractor.py` (line 48)
- `persona_writer.py` (line 95)
- `ranking.py` (lines 73, 153, 264, 407, 546)
- `pipeline.py` (lines 2422, 2491 — but NOT `service_tier="flex"` on those same calls)
- `pipeline_digest.py` (lines 686, 800, 861, 1005 — and check line 249 for generate_digest_metadata)

### Step 1.7: Remove the `temperature` parameter from `build_completion_kwargs()`

In `backend/services/agents/client.py`, change:

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
```

To:

```python
def build_completion_kwargs(
    model: str,
    messages: list[dict],
    max_tokens: int,
    response_format: dict | None = None,
    reasoning_effort: str | None = None,
    service_tier: str | None = None,
    verbosity: str | None = None,
    prompt_cache_key: str | None = None,
) -> dict:
    """Build kwargs for chat.completions.create for gpt-5 family.

    Note: `temperature` is not accepted because gpt-5/o-series strip it.
    If we ever re-introduce a non-reasoning model family, re-add it here.
    """
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    kwargs["max_completion_tokens"] = max_tokens  # all production models are gpt-5 family
    if response_format:
```

Leave the rest of the function untouched.

### Step 1.8: Fix `_apply_gpt5_compat()` to stop stripping temperature (dead code now)

In `client.py` lines 90-92, remove:

```python
    # gpt-5 and o-series don't support temperature
    if is_o_series(model) or model.startswith("gpt-5"):
        kwargs.pop("temperature", None)
```

Keep the surrounding `max_tokens` multiplier logic unchanged.

### Step 1.9: Update tests

In `backend/tests/test_agents_client.py`:

- `test_gpt5_default_reasoning_effort_is_low` (line 27-32): Remove `"temperature": 0.4` from the kwargs dict. Remove the `assert "temperature" not in out` line. Keep the reasoning_effort + max_completion_tokens assertions.
- `test_non_gpt5_model_untouched` (line 41-45): This test currently verifies that gpt-4.1 keeps its temperature. Since we're no longer supporting gpt-4.1 in this code path, **delete this entire test**. (We are not testing dead scenarios.)
- Search for any other `temperature` references in test files and remove them.

### Step 1.10: Syntax + test run

Run:
```bash
cd backend && python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('services/agents').rglob('*.py')] ; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('services').glob('pipeline*.py')] ; print('SYNTAX OK')"
```
Expected: `SYNTAX OK`

Run:
```bash
cd backend && pytest tests/test_agents_client.py -v --tb=short
```
Expected: All tests pass (except the deleted `test_non_gpt5_model_untouched`).

### Step 1.11: Commit

```bash
git add backend/services/agents/client.py \
  backend/services/agents/advisor.py \
  backend/services/agents/blog_advisor.py \
  backend/services/agents/product_advisor.py \
  backend/services/agents/fact_extractor.py \
  backend/services/agents/persona_writer.py \
  backend/services/agents/ranking.py \
  backend/services/pipeline.py \
  backend/services/pipeline_digest.py \
  backend/tests/test_agents_client.py
git commit -m "chore(agents): remove temperature parameter — gpt-5 strips it anyway

temperature was passed at 40+ call sites but stripped by _apply_gpt5_compat
for every gpt-5 model (which is all of production). Removing the parameter
from build_completion_kwargs signature and all call sites eliminates 41
lines of dead noise. Also removed the strip logic itself since nothing
passes temperature now.

If a non-reasoning model family is ever re-introduced, re-add the
parameter at that time."
```

---

## Task 2: Remove gpt-4 and o-series entries from the pricing table

**Context:** `OPENAI_MODEL_PRICING_PER_1M` in `client.py:46-58` includes 8 non-production models. Since `_resolve_pricing_key()` would only use them if a call passed one of those model names — and no call does — they are dead entries that confuse new readers.

**Files to modify:**
- `backend/services/agents/client.py`

### Step 2.1: Delete non-gpt-5 pricing entries

In `client.py`, replace the `OPENAI_MODEL_PRICING_PER_1M` dict (lines 46-58) with a gpt-5-only version:

```python
OPENAI_MODEL_PRICING_PER_1M = {
    "gpt-5": {"input": Decimal("2.00"), "output": Decimal("8.00")},
    "gpt-5-mini": {"input": Decimal("0.25"), "output": Decimal("2.00")},
    "gpt-5-nano": {"input": Decimal("0.05"), "output": Decimal("0.40")},
}
```

### Step 2.2: Check `_resolve_pricing_key()` still works

Read `client.py:141-153`. The function uses longest-prefix matching. With 3 entries it still works correctly for any model string starting with `gpt-5`, `gpt-5-mini`, or `gpt-5-nano`. No change needed.

### Step 2.3: Test pricing estimates still compute

Run:
```bash
cd backend && pytest tests/test_usage_metrics.py -v --tb=short
```
Expected: All tests pass. If any test passes a gpt-4 / o-series model name and expects a cost, update it to use a gpt-5 model.

### Step 2.4: Commit

```bash
git add backend/services/agents/client.py backend/tests/test_usage_metrics.py
git commit -m "chore(agents): remove pricing entries for gpt-4/o-series (non-production)

production config only uses gpt-5 family. keeping pricing entries for
models we never call is stale. if a fallback model family is added
later, add its pricing at the same time."
```

---

## Task 3: Remove unreachable `else` branch in `build_completion_kwargs()`

**Context:** After Task 1 Step 1.7, the function already consolidates to `max_completion_tokens`. This task is a defensive double-check in case Step 1.7 was incomplete, and to explicitly remove `_uses_max_completion_tokens()` conditional logic from `_apply_gpt5_compat` where it becomes tautological.

**Files to modify:**
- `backend/services/agents/client.py`

### Step 3.1: Verify `build_completion_kwargs()` has no else branch

Open `client.py` and confirm the function (after Task 1) contains only:
```python
kwargs["max_completion_tokens"] = max_tokens
```

(No `if _uses_max_completion_tokens(model)`.)

If the `if/else` is still present, delete the else branch.

### Step 3.2: Simplify `_apply_gpt5_compat()` token logic

The function at line 84-88 has two branches that do similar work. Since `build_completion_kwargs()` now directly sets `max_completion_tokens`, and `compat_create_kwargs()` receives `max_tokens`, the two branches are still both reachable (one per path). **Leave them as-is**, but add a docstring clarification at the top of the function:

```python
def _apply_gpt5_compat(kwargs: dict, model: str) -> dict:
    """Apply gpt-5 compatibility: 3x token headroom for reasoning + low default effort.

    Two token paths to handle:
    1. compat_create_kwargs caller passed max_tokens → pop + rename + 3x.
    2. build_completion_kwargs caller already set max_completion_tokens → 3x in place.
    """
```

Remove the older line comment on line 83 (`# max_tokens → max_completion_tokens (with 3x headroom for reasoning)`) since the docstring now explains it.

### Step 3.3: Syntax check

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/client.py', encoding='utf-8').read()); print('OK')"
```

### Step 3.4: Commit

```bash
git add backend/services/agents/client.py
git commit -m "refactor(agents): clarify token multiplication paths in _apply_gpt5_compat

no behavior change; docstring explains why there are two branches for
max_tokens vs max_completion_tokens. follows the temperature cleanup
in the previous commit."
```

---

## Task 4: Update stale gpt-4.1 comments

**Context:** Three comments still reference gpt-4.1 even though the code calls gpt-5-mini.

**Files to modify:**
- `backend/services/agents/advisor.py` (lines 1210, 3019)
- `backend/services/agents/ranking.py` (line 140)

### Step 4.1: Update advisor.py line 1210

Find:
```python
"""Self-critique basic KO+EN content in one call (gpt-4.1-mini).
```

Replace the `(gpt-4.1-mini)` part with `(gpt-5-mini)` — keep the rest of the docstring unchanged. Use Grep to confirm the exact surrounding context if needed.

### Step 4.2: Update advisor.py line 3019

Find:
```python
# Truncate to first 24000 chars for extraction (gpt-4.1-mini supports 128K)
```

Replace with:
```python
# Truncate to first 24000 chars for extraction (gpt-5-mini supports 128K)
```

### Step 4.3: Update ranking.py line 140

Find:
```python
model = settings.openai_model_light  # gpt-4.1-mini (o4-mini returns empty responses for classification)
```

Replace with:
```python
model = settings.openai_model_light  # gpt-5-mini (kept as inline reminder that light = mini, not nano)
```

The original comment's rationale (o4-mini returning empty responses) is obsolete since we no longer support o-series here.

### Step 4.4: Syntax check

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/advisor.py', encoding='utf-8').read()); ast.parse(open('services/agents/ranking.py', encoding='utf-8').read()); print('OK')"
```

### Step 4.5: Commit

```bash
git add backend/services/agents/advisor.py backend/services/agents/ranking.py
git commit -m "docs(agents): update stale gpt-4.1 references to gpt-5"
```

---

## Final Verification

### Step F.1: Full backend syntax check

```bash
cd backend && python -c "
import ast, pathlib
for p in list(pathlib.Path('services').rglob('*.py')) + list(pathlib.Path('tests').rglob('*.py')):
    try:
        ast.parse(p.read_text(encoding='utf-8'))
    except SyntaxError as e:
        print(f'FAIL {p}: {e}')
        raise
print('ALL SYNTAX OK')
"
```

### Step F.2: Full test suite

```bash
cd backend && pytest tests/ -v --tb=short
```

Expected: All tests pass. Any failures indicate we removed something a test relied on — investigate and fix before pushing.

### Step F.3: Frontend build (smoke — nothing should have changed)

```bash
cd frontend && npm run build
```

Expected: Pass. (No frontend files touched, but catches accidental issues.)

### Step F.4: Push

```bash
git push origin main
```

---

## Out of Scope (Explicitly Not Doing)

- `is_o_series()` function: kept. Three-line function, serves as compatibility marker.
- `parse_ai_json()` markdown fallback: kept. Safety net, negligible cost.
- `reasoning_effort` auto-injection: kept. Current design works.
- `service_tier`, `verbosity`, `prompt_cache_key` parameters: kept. Active use (`service_tier`) or planned use.
- Double-multiplication refactor (unifying token math to one place): kept as-is. Works correctly; refactor is churn.

## Known Trade-offs

- After Task 1, if a caller (e.g., a future script) tries to pass `temperature=` to `build_completion_kwargs()` they will get a `TypeError`. This is intended — fail loudly rather than silently discard.
- After Task 2, if a legacy script uses one of the deleted pricing keys, `_resolve_pricing_key()` returns `None` and cost estimation becomes `None` (already the documented fallback). No crash.

## Rollback Plan

Each task is a separate commit. If anything breaks:
- Task 1 rollback: `git revert <sha>` restores the temperature parameter and all call sites.
- Subsequent tasks are independently revertible.
