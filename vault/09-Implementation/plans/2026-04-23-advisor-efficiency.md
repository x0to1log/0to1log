# Admin Advisor Efficiency Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the GPT-5 efficiency patterns already proven on news pipeline writers/QC to the admin advisor + blog advisor action handlers. Add `service_tier="flex"` + `prompt_cache_key` to 9+ action configs (50% tier discount + 50% cached-input discount), then run reasoning_effort and verbosity A/Bs that are gated on the flex+cache rollout stabilizing. Target: admin-editor GPT-5 spend drops ~40-60% on review/check actions while quality score stays flat.

**Scope:** Admin editor advisor paths only. Separate from:
- [[2026-04-23-gpt5-efficiency]] — news pipeline writer + QC flex/cache (in progress)
- [[2026-04-23-legacy-model-cleanup]] — dead code removal (`temperature` params, stale pricing entries) — parallel effort

**Architecture:** Three phases in dependency order.

- **Phase 1 — Flex tier + prompt_cache_key on admin advisor actions (independent, immediate savings).** Thread `service_tier="flex"` and a stable `prompt_cache_key` into 9 actions across `advisor.py` and `blog_advisor.py`. Extend `run_deep_verify` step1/step2 with the same pattern. `with_flex_retry` wrapper already handles flex 429 backoff, so runtime risk is minimal.
- **Phase 2 — `reasoning_effort` medium → low A/B (depends on Phase 1 stabilizing).** Four actions currently hardcode `reasoning_effort="medium"` on gpt-5-mini: `review`, `conceptcheck`, `voicecheck`, `retrocheck`. Public benchmarks show medium=67 / low=64 Intelligence Index; for checklist-style judgments this gap is typically cost-effective. Roll low to these four actions for 1 week, compare quality_score trend + manual spot-check, commit if flat. **Keep `factcheck` at medium** (evidence-tracing task — downgrade risk high).
- **Phase 3 — `verbosity="low"` A/B on handbook generate (deferred, separate track).** Handbook `generate` action is a creative task; publicly measured token savings are ~28% (AG2 low=731 vs medium=1017) but the 2026-04-23 QC `verbosity=low` A/B was rejected due to a -24% evidence hit, so this needs its own independent measurement — different agent, different axis (body length + example count, not evidence density). Run dedicated A/B with 20-term sample before rolling.

**Tech Stack:** Python 3.11, OpenAI Python SDK, Supabase (`pipeline_logs` + `handbook_quality_scores` for observability), pytest.

**Non-goals (explicit):**
- News pipeline writer/QC flex rollout (covered by [[2026-04-23-gpt5-efficiency]])
- `temperature` parameter cleanup (covered by [[2026-04-23-legacy-model-cleanup]])
- `gpt-5-nano` downgrade for voicecheck/retrocheck (JSON stability risk — ranking.py:139 precedent of "o4-mini returns empty responses")
- `json_schema` migration from `json_object` (separate tracking; Pydantic validators need coordinated revision)
- Batch API for admin advisor (admin editor is interactive — 24h async breaks UX)

**Key reference files (read before starting):**
- `backend/services/agents/client.py:76-140` — `_apply_gpt5_compat`, `build_completion_kwargs`, `compat_create_kwargs` (already expose `service_tier`, `verbosity`, `prompt_cache_key` params)
- `backend/services/agents/advisor.py:56-104` — `ACTION_CONFIG` dict (7 admin handbook actions)
- `backend/services/agents/advisor.py:225-350` — `run_deep_verify` step1 + step2 (currently `reasoning_effort="medium"`, flex not set)
- `backend/services/agents/advisor.py:440-480` — `run_handbook_advise` dispatcher (routes action → ACTION_CONFIG → `compat_create_kwargs`)
- `backend/services/agents/blog_advisor.py:49-111` — `BLOG_ACTION_CONFIG` (4 review/check actions)
- `backend/services/agents/blog_advisor.py` — `run_blog_advise` dispatcher (mirrors advisor.py pattern)
- `backend/services/pipeline_digest.py:670-685` — reference pattern: writer with `reasoning_effort="high"` + `service_tier="flex"` + `prompt_cache_key`
- `backend/services/pipeline_quality.py:446-456, 1088-1100` — reference pattern: QC with flex + cache_key already in place

---

## Current State (for the executor)

As of 2026-04-23, after news pipeline writer/QC migration to flex is in progress but before this plan starts:

| Call site | Model | reasoning_effort | service_tier | prompt_cache_key | verbosity |
|---|---|---|---|---|---|
| advisor.py `generate` | gpt-5 | compat default (low) | **unset** | **unset** | unset |
| advisor.py `seo` | gpt-5-nano | compat default (low) | **unset** | **unset** | unset |
| advisor.py `review` | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| advisor.py `factcheck` | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| advisor.py `conceptcheck` | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| advisor.py `voicecheck` | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| advisor.py `retrocheck` | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| advisor.py `run_deep_verify` step1 | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| advisor.py `run_deep_verify` step2 | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| blog_advisor.py `review` | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| blog_advisor.py `conceptcheck` | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| blog_advisor.py `voicecheck` | gpt-5-mini | **medium** | **unset** | **unset** | unset |
| blog_advisor.py `retrocheck` | gpt-5-mini | **medium** | **unset** | **unset** | unset |

**Reference (already optimized for comparison):**

| Call site | Model | reasoning_effort | service_tier | prompt_cache_key |
|---|---|---|---|---|
| pipeline_digest writer | gpt-5 | high | **flex** | `digest-{locale}-{persona}` |
| pipeline_quality daily | gpt-5-mini | low | **flex** | `qc-{type}` |
| pipeline_quality weekly | gpt-5-mini | low | **flex** | `qc-weekly-{role}` |

**System prompt sizes (measured from `prompts_advisor.py`):**

| Prompt | Token estimate |
|---|---|
| `FACTCHECK_SYSTEM_PROMPT` | ~2.5k |
| `CONCEPTCHECK_SYSTEM_PROMPT` | ~2.0k |
| `VOICECHECK_SYSTEM_PROMPT` | ~1.8k |
| `RETROCHECK_SYSTEM_PROMPT` | ~1.5k |
| Review prompt (generated via `get_review_prompt`) | ~2.2k |
| DeepVerify step1 + step2 | ~1.2k + ~1.5k |

All exceed OpenAI's 1024-token prompt-cache threshold → eligible for cache-hit pricing on repeated calls with the same `prompt_cache_key`.

---

## Chunk 1: Phase 1 — Flex Tier + prompt_cache_key on Admin Advisor Actions

### Task 1.1: Extend `ACTION_CONFIG` schema in `advisor.py` to carry `service_tier` and `prompt_cache_key`

**Files:**
- Modify: `backend/services/agents/advisor.py` (lines 56-104 — ACTION_CONFIG dict)
- Modify: `backend/services/agents/advisor.py` (dispatcher in `run_handbook_advise` — thread new keys into `compat_create_kwargs`)
- Test: `backend/tests/test_advisor_compat.py` (new file or extend existing)

**Why:** `compat_create_kwargs` already accepts `service_tier`, `prompt_cache_key`, `verbosity` per its signature (client.py:140). The gap is that `ACTION_CONFIG` doesn't carry these fields, so the dispatcher never forwards them. Add the fields per-action, extract them in the dispatcher, pass through.

**Step 1: Write the failing test**

Append to `backend/tests/test_advisor_compat.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.agents.advisor import ACTION_CONFIG


def test_review_action_has_flex_tier():
    """review action should be configured for flex tier."""
    assert ACTION_CONFIG["review"].get("service_tier") == "flex"


def test_review_action_has_prompt_cache_key():
    """review action should have a stable prompt_cache_key."""
    key = ACTION_CONFIG["review"].get("prompt_cache_key")
    assert key and key.startswith("advisor-")


@pytest.mark.parametrize("action", [
    "review", "factcheck", "conceptcheck", "voicecheck", "retrocheck",
])
def test_admin_check_actions_configured_for_flex_and_cache(action):
    cfg = ACTION_CONFIG[action]
    assert cfg["service_tier"] == "flex"
    assert cfg["prompt_cache_key"] == f"advisor-{action}"


def test_generate_and_seo_stay_on_standard_tier():
    """generate/seo are fast creative calls — keep on standard tier so
    the admin editor doesn't hit flex latency on 'Auto-generate'.
    """
    assert "service_tier" not in ACTION_CONFIG["generate"]
    assert "service_tier" not in ACTION_CONFIG["seo"]
```

Run: `cd backend && pytest tests/test_advisor_compat.py::test_review_action_has_flex_tier -v`
Expected: FAIL with `AssertionError: None != 'flex'`.

**Step 2: Extend ACTION_CONFIG**

In `backend/services/agents/advisor.py` around lines 69-103, for each of `review`, `factcheck`, `conceptcheck`, `voicecheck`, `retrocheck`, add:

```python
"service_tier": "flex",
"prompt_cache_key": "advisor-<action_name>",
```

Do NOT add to `generate` or `seo` — those are creative / quick-lookup calls where admin UX prioritizes low latency.

**Step 3: Thread new keys through dispatcher**

In `run_handbook_advise` (around line 440-480), the existing pattern:

```python
config = ACTION_CONFIG[req.action]
extra_kwargs = {}
if config.get("reasoning_effort"):
    extra_kwargs["reasoning_effort"] = config["reasoning_effort"]
# ... build_completion_kwargs / compat_create_kwargs call ...
```

Extend to also forward `service_tier` and `prompt_cache_key`:

```python
for key in ("reasoning_effort", "service_tier", "prompt_cache_key", "verbosity"):
    if config.get(key):
        extra_kwargs[key] = config[key]
```

**Step 4: Run test → should pass**

Run: `cd backend && pytest tests/test_advisor_compat.py -v`
Expected: all pass.

**Step 5: Commit**

```
feat(advisor): enable flex tier + prompt caching on 5 admin check actions

review/factcheck/conceptcheck/voicecheck/retrocheck now route through
service_tier="flex" with prompt_cache_key="advisor-{action}". Flex gives
50% tier discount; cache_key enables OpenAI's prompt-cache hit pricing
(50% off cached input tokens) on repeated calls with the same system prompt.

generate and seo stay on standard tier — those are latency-sensitive
'Auto-generate' paths in the admin editor.
```

---

### Task 1.2: Add flex + cache to `run_deep_verify` step1 and step2

**Files:**
- Modify: `backend/services/agents/advisor.py:225-350`
- Test: `backend/tests/test_advisor_compat.py` (extend)

**Why:** `run_deep_verify` uses direct `compat_create_kwargs` calls rather than going through ACTION_CONFIG, so Task 1.1 doesn't cover it. It's a two-call chain on gpt-5-mini with ~1.2k + ~1.5k system prompts — cache-eligible and identical-prompt on repeated invocations.

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_deep_verify_step1_passes_flex_and_cache_key():
    """run_deep_verify step1 should set service_tier=flex and a stable cache key."""
    # Inspect the call through a mock client
    # Assert kwargs contain service_tier="flex" and prompt_cache_key="advisor-deepverify-step1"
    ...
```

**Step 2-3: Update both step1 and step2 `compat_create_kwargs` calls**

For step1 (claim extraction):
```python
kwargs = compat_create_kwargs(
    model,
    messages=[...],
    max_tokens=...,
    response_format={"type": "json_object"},
    reasoning_effort="medium",
    service_tier="flex",
    prompt_cache_key="advisor-deepverify-step1",
)
```

Same for step2 (verification) with `prompt_cache_key="advisor-deepverify-step2"`.

**Step 4: Commit**

```
feat(advisor): flex tier + cache key for deep_verify step1/step2

Same pattern as Task 1.1 but for the two-step deep verification chain
which bypasses ACTION_CONFIG.
```

---

### Task 1.3: Mirror Task 1.1 on `blog_advisor.py`

**Files:**
- Modify: `backend/services/agents/blog_advisor.py:49-111` (BLOG_ACTION_CONFIG)
- Modify: `backend/services/agents/blog_advisor.py` (dispatcher — `run_blog_advise`)
- Test: `backend/tests/test_blog_advisor_compat.py`

**Why:** Blog advisor is a full copy of the advisor.py pattern for blog posts. Same 4 actions (review/conceptcheck/voicecheck/retrocheck) currently hardcode `reasoning_effort="medium"` without flex or cache.

**Steps:** Mirror Task 1.1 exactly, with cache keys `"blog-advisor-{action}"` to avoid collision with handbook advisor's cache slots (OpenAI matches on `(api_key, prompt_cache_key, prefix)` tuple — different system prompts would evict each other from the same cache slot).

**Commit:**
```
feat(blog_advisor): enable flex tier + prompt caching on 4 check actions

Mirrors advisor.py Task 1.1 pattern. Cache keys "blog-advisor-{action}"
are distinct from handbook advisor's "advisor-{action}" to prevent
cross-eviction since system prompts differ.
```

---

### Task 1.4: Observability — verify `cached_tokens` appearing in pipeline_logs for these 13 actions

**Files (read-only):**
- Query: `pipeline_logs` filtered by `pipeline_type` of the admin actions

**Why:** Phase 1 is only valuable if prompt cache is actually hitting. After deploying Task 1.1-1.3 and letting 1-2 days of traffic accumulate, query to confirm `cached_tokens > 0` appears for repeat-prompt actions.

**Step 1: Verification SQL (run against Supabase after deployment)**

```sql
SELECT
  pipeline_type,
  COUNT(*) as calls,
  AVG((debug_meta->>'cached_tokens')::int) as avg_cached,
  AVG((debug_meta->>'input_tokens')::int) as avg_input,
  AVG((debug_meta->>'cached_tokens')::float / NULLIF((debug_meta->>'input_tokens')::int, 0)) as cache_hit_ratio
FROM pipeline_logs
WHERE pipeline_type LIKE 'handbook.%'
  AND created_at >= NOW() - INTERVAL '2 days'
  AND (debug_meta->>'cached_tokens') IS NOT NULL
GROUP BY pipeline_type;
```

**Success criterion:** `cache_hit_ratio >= 0.4` on review/conceptcheck/voicecheck/retrocheck after warmup (cache TTL ~5 minutes per OpenAI docs, so concentrated admin editing sessions should hit easily; sparse single-term editing won't hit).

**Step 2: Decision point**

- If ratio ≥ 0.4 on check actions: Phase 1 successful, proceed to Phase 2.
- If ratio < 0.2: investigate prompt variance (dynamic timestamps? user-specific prefixes? Reorder user prompt so variable parts come at the end, not interleaved).
- If ratio 0.2 ~ 0.4: partial success, investigate top-variance prompt section.

**No commit for this task** — it's a verification checkpoint.

---

## Chunk 2: Phase 2 — `reasoning_effort` medium → low A/B

**Gate:** Do not start Phase 2 until Phase 1 has been live for ≥ 3 days and cache_hit_ratio ≥ 0.4 verified on the 4 check actions. Mixed signals otherwise.

### Task 2.1: Add `reasoning_effort` config override env flag

**Files:**
- Modify: `backend/services/agents/advisor.py` (ACTION_CONFIG — 4 entries)
- Modify: `backend/core/config.py` (new setting `advisor_check_reasoning_effort`, default `"medium"`)

**Why:** Rather than branching `if env == "ab": reasoning_effort="low" else "medium"` in code, gate via a single setting. Flip via env var, no code deploy needed for A/B iterations.

**Step 1: Add setting**

In `backend/core/config.py`:
```python
advisor_check_reasoning_effort: Literal["low", "medium", "high"] = "medium"
```

**Step 2: Wire into ACTION_CONFIG**

For review/conceptcheck/voicecheck/retrocheck:
```python
"reasoning_effort": settings.advisor_check_reasoning_effort,
```

Leave `factcheck` hardcoded as `"medium"` — explicitly exempted.

**Step 3: Commit**

```
feat(advisor): env-gated reasoning_effort for check actions A/B

advisor_check_reasoning_effort setting (default "medium") controls
review/conceptcheck/voicecheck/retrocheck. factcheck stays pinned at
medium — evidence-tracing task, downgrade risk too high.
```

### Task 2.2: Run 1-week A/B with `reasoning_effort=low`

**Procedure (manual, not code):**

1. Set `ADVISOR_CHECK_REASONING_EFFORT=low` on Railway for 1 calendar week
2. Record baseline: `avg_cost` and `avg_quality_score` for these 4 actions in the week before
3. After A/B week: compare
4. If `avg_quality_score` delta ≤ -2 points (absolute) and cost reduced ≥ 25%: commit to low (change default in config.py)
5. Else: revert to medium

**No code commit until decision** — the env flag stays as the abort handle.

### Task 2.3: Document A/B outcome

**Files:**
- Create: `vault/12-Journal-&-Decisions/2026-MM-DD-advisor-reasoning-ab.md`

Record the baseline vs. A/B metrics and final decision. If rolling low, update config.py default and note in the file.

---

## Chunk 3: Phase 3 — handbook `generate` verbosity A/B (deferred)

**Gate:** Do not start until Phase 2 decision is documented. Different action type (creative writing vs. checklist judgment), needs independent measurement.

### Task 3.1: Add `verbosity` to `generate` action config

**Files:**
- Modify: `backend/services/agents/advisor.py` (generate entry in ACTION_CONFIG)
- Modify: `backend/core/config.py` (new `handbook_generate_verbosity` setting, default unset/None)

Wire same env-gated pattern as Task 2.1. Default `None` keeps current behavior.

### Task 3.2: Manual A/B on 20-term sample

**Procedure:**

1. Select 20 diverse handbook terms (mix of types/categories from existing published set)
2. Generate each twice via admin editor — once with `HANDBOOK_GENERATE_VERBOSITY=medium` (control), once with `=low` (treatment)
3. Measurement axes (different from QC A/B — that failed on evidence, creative has different failure modes):
   - `avg_tokens_used` — expected 20-30% reduction
   - `avg_body_length_chars` (basic + advanced combined)
   - Number of examples / code snippets per term (manual count)
   - Subjective quality: "does it feel thin?" 1-5 rating by Amy
4. Decision:
   - Token reduction ≥ 20% + subjective rating drop ≤ 0.5 points → commit low as default for generate
   - Else → revert, document as known-bad

### Task 3.3: Document outcome

Same pattern as Task 2.3.

---

## Out-of-scope but related (future plans, do not implement in this plan)

1. **Admin cost dashboard** — Add Phase 1/2/3 rollout indicator to `pipeline-analytics` admin page so the Quality Score Trend + cost chart annotate which period used which settings. (Currently no overlay UI.)
2. **Batch API for handbook backfill regeneration** — HB-SEED-800 / HB-MIGRATE-138 are non-realtime and could use Batch API (50% discount, 24h turnaround). Out of scope here because they're batch pipelines, not the admin editor. Separate plan.
3. **`json_schema` migration** — Strict structured output across advisor.py. Reduces retry rate but requires Pydantic validator audit. Separate plan.
4. **gpt-5-nano cost floor exploration** — voicecheck/retrocheck conceivably on gpt-5-nano. Not explored here due to JSON stability precedent from ranking.py:139 ("o4-mini returns empty responses").

---

## Success Criteria

Plan is complete when:
- [x] Phase 1 Tasks 1.1-1.3 implemented and deployed
- [ ] Phase 1 Task 1.4 verification confirms cache_hit_ratio ≥ 0.4
- [ ] Phase 2 Task 2.2 A/B run with documented decision
- [ ] Phase 3 Task 3.2 A/B run with documented decision (may conclude "keep medium" if subjective rating drops)
- [ ] Admin-editor GPT-5 spend trending downward vs. pre-Phase 1 baseline, visible in pipeline-analytics cost chart (7-day rolling)

**Rollback criteria:** If any A/B shows quality score dropping ≥ 3 points absolute, revert immediately via env flag (no redeploy). If Phase 1 flex causes user-visible admin latency complaints (> 30s p95 on check actions), revert those 5 actions to standard tier (keep cache_key — it's cheap and cache-only).
