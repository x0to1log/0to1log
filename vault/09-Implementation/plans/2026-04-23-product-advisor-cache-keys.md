# Product Advisor Prompt Caching Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `prompt_cache_key` to 5 product advisor LLM calls so OpenAI's prompt cache hits on repeat invocations — leveraging 24h extended cache retention.

**Architecture:** Add the `prompt_cache_key` kwarg to 5 existing `compat_create_kwargs` calls in `product_advisor.py`. Naming convention: `product-{purpose}` (distinct from `advisor-*` and `blog-advisor-*` namespaces in handbook/blog advisors to prevent cross-eviction, since system prompts differ).

**Tech Stack:** Python 3.11, OpenAI Python SDK (cache key param already plumbed through `compat_create_kwargs` and `build_completion_kwargs`).

**Scope:** `generate_from_url` action path (the 5 internal LLM calls). No `service_tier="flex"` — admin is interactive, waits for result.

---

## Current State

Five LLM calls in `backend/services/agents/product_advisor.py` all use static (or suffix-variable) system prompts ≥400 tokens each. None have `prompt_cache_key` today.

| Call site (function) | Purpose | System prompt | Est. tokens |
|---|---|---|---|
| `_extract_product_facts` | extract facts from sources | `EXTRACT_FACTS_SYSTEM` (static) | ~400 |
| `_classify_product` | classify product into category | `CLASSIFY_PRODUCT_SYSTEM` (static) | ~400 |
| `_generate_en_profile` | main EN profile (gpt-5) | `PROFILE_EN_SYSTEM` + category_guide + rules | ~1300 + ~400 (category) |
| `_generate_ko_profile` | KO profile using EN as ref | `PROFILE_KO_SYSTEM` + category_guide | ~900 + ~400 |
| `_generate_enrichment` | scenarios/pros_cons/etc | `ENRICH_SYSTEM` + category_guide | ~400 + ~400 |

**Why all 5 benefit from a cache key:**
- System prompts are identical across all product runs (category_guide varies but is appended, not interleaved).
- OpenAI caches on prefix match, 1024-token blocks. All 5 prompts' static prefix is long enough to hit the first cache block.
- `prompt_cache_key` routes identical keys to the same physical server → higher hit rate.
- Extended retention (24h vs default 5min) benefits our intermittent admin usage pattern.

**Not doing flex tier** — `generate_from_url` is clicked from admin editor; Amy waits for the result. Flex tier's queue latency (~2-6s extra) would degrade UX.

---

## Chunk 1: Add cache keys to 5 calls

### Task 1.1: Add `prompt_cache_key` to `_extract_product_facts`

**Files:** `backend/services/agents/product_advisor.py`

**Step 1: Locate the call**

Read the file and find the `_extract_product_facts` helper. It contains a `compat_create_kwargs` call. Current shape (no cache key):

```python
resp = await client.chat.completions.create(
    **compat_create_kwargs(
        model,
        messages=[...],
        max_tokens=500,
        response_format={"type": "json_object"},
    ),
)
```

**Step 2: Add cache key**

Add `prompt_cache_key="product-extract-facts"` to the `compat_create_kwargs` call. Since `compat_create_kwargs` forwards unknown kwargs into the API call, no wrapper change needed.

**Step 3: Verify**

Grep the file for `prompt_cache_key` to confirm it's now present:
```bash
cd backend && grep -n "prompt_cache_key" services/agents/product_advisor.py
```
Expected: at least one match pointing to this function.

**Step 4: Syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read()); print('OK')"
```

### Task 1.2: Add `prompt_cache_key` to `_classify_product`

Same pattern. Cache key: `"product-classify"`.

### Task 1.3: Add `prompt_cache_key` to `_generate_en_profile`

Same pattern. Cache key: `"product-en-profile"`.

### Task 1.4: Add `prompt_cache_key` to `_generate_ko_profile`

Same pattern. Cache key: `"product-ko-profile"`.

### Task 1.5: Add `prompt_cache_key` to `_generate_enrichment`

Same pattern. Cache key: `"product-enrichment"`.

### Task 1.6: Do NOT add cache key to search_corpus or individual field generation paths

- The `generate_search_corpus` action (separate from `generate_from_url`) can come later if needed.
- Individual field actions (tagline_en, tagline_ko, description_en, description_ko, pricing_detail) each use different prompt constants; optional in a follow-up pass.

### Task 1.7: Final verification

Run syntax check after all 5 edits:
```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read()); print('OK')"
```
Expected: `OK`

Count the cache keys — should be exactly 5 new ones:
```bash
cd backend && grep -cn "product-.*" services/agents/product_advisor.py | grep -v "^prompts"
```
Expected: at least 5 matches of keys with `product-` prefix.

### Task 1.8: Commit

```bash
git add backend/services/agents/product_advisor.py
git commit -m "$(cat <<'EOF'
feat(product-advisor): add prompt_cache_key to 5 LLM calls

mirrors handbook/blog advisor pattern. cache keys:
  product-extract-facts, product-classify, product-en-profile,
  product-ko-profile, product-enrichment

each system prompt is static (or suffix-variable via category_guide),
so prefix caches. key enables OpenAI's 24h extended retention vs the
default 5-min — useful for our intermittent admin generation pattern.

no flex tier here — generate_from_url is interactive (admin waits
for result); flex queue latency would hurt UX.
EOF
)"
```

---

## Observability (follow-up, not in this plan)

After 3-7 days of admin traffic, verify cache hit rate via `product_generation_logs` table (from the earlier product advisor run log migration):

```sql
SELECT
  (facts->'cached_tokens')::int AS cached,
  tokens_used,
  created_at
FROM product_generation_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
  AND success = true
ORDER BY created_at DESC
LIMIT 20;
```

Note: `cached_tokens` is logged via `extract_usage_metrics()` into `pipeline_logs.debug_meta` for news/handbook flows; **for product advisor this log path may not yet exist**. Future task: wire `cached_tokens` into the `product_generation_logs` insert path.

---

## Out of Scope

- Adding `service_tier="flex"` to any product advisor call (interactive UX).
- Cache keys for `pricing_detail`, `generate_search_corpus`, individual `tagline_en/ko` / `description_en/ko` actions. These may be worth adding in a follow-up but have lower usage frequency.
- Migrating any product advisor path to Batch API.

## Rollback

If cache keys cause issues (unlikely — parameter is transparent), revert the single commit: `git revert <sha>`. No DB state, no config to toggle.
