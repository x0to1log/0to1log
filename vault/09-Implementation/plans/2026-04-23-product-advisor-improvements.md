# Product Advisor Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix real quality bottlenecks in the product advisor pipeline and expose `secondary_categories` to public pages (originally intended but never rendered).

**Architecture:**
- **Backend**: Remove page content truncation in EN profile, add fallback on failure, deterministic format validators, and DB-backed run logging with prompt versioning.
- **Frontend**: Render `secondary_categories` on product detail + card, extend category filter to match secondary.
- **No schema breaks**: all changes are additive. Existing generated content remains valid.

**Tech Stack:** Python (FastAPI, OpenAI SDK), Astro v5, Supabase PostgreSQL, gpt-5 / gpt-5-mini / gpt-5-nano.

---

## Task Priority Order

| # | Task | Why First |
|---|------|-----------|
| 1 | `secondary_categories` public UI rendering | Zero regen needed, instant benefit for all 144 existing products |
| 2 | Remove EN profile `[:2000]` truncation | Biggest quality lever per our analysis |
| 3 | EN generation fallback + hard fail | Prevents silent partial failures |
| 4 | Deterministic format validators (admin warning) | Quality gate without LLM cost |
| 5 | Prompt version + run log DB | Debuggability, enables future A/B |

---

## Task 1: Render `secondary_categories` on public pages

**Files:**
- Modify: `frontend/src/components/products/ProductDetail.astro:150-162` (tags row)
- Modify: `frontend/src/components/products/ProductCard.astro:41` (data attribute)
- Modify: `frontend/src/lib/pageData/productsPage.ts` (ensure ProductCardData includes secondary_categories)
- Modify: `frontend/src/pages/ko/products/index.astro:185-205` (filter logic)
- Modify: `frontend/src/pages/en/products/index.astro` (same filter logic)

### Step 1.1: Add `secondary_categories` to ProductCardData interface

Read `frontend/src/lib/pageData/productsPage.ts` around line 52. Confirm whether `secondary_categories` is on `ProductDetailData` only or also `ProductCardData`.

If only on `ProductDetailData`:
- Add `secondary_categories: string[] | null` to `ProductCardData` interface
- Add to `CARD_COLUMNS` constant (around line 117): append `, secondary_categories`
- In the `resolvedProducts.map()` block, include `secondary_categories: p.secondary_categories as string[] | null`

**Step 1.2: Pass `secondary_categories` through ProductCard**

In `frontend/src/components/products/ProductCard.astro`:
- Accept new prop `secondaryCategories?: string[] | null` in the component props
- On line 41 (`<a href={href} class="product-card" ...>`), add:
  ```astro
  data-secondary-categories={secondaryCategories?.join(',') || ''}
  ```

In `frontend/src/pages/ko/products/index.astro` and `en/products/index.astro`, find where ProductCard is rendered and pass:
```astro
<ProductCard
  ...existing props
  secondaryCategories={product.secondary_categories}
/>
```

**Step 1.3: Update category filter in both list pages**

In `ko/products/index.astro` around line 185-205, replace the `applyFilters()` function's category matching:

```javascript
function applyFilters() {
  const q = currentQuery.trim().toLowerCase();
  let totalVisible = 0;

  cards.forEach((card) => {
    const text = card.dataset.searchText ?? '';
    const primary = card.dataset.category ?? '';
    const secondaryStr = card.dataset.secondaryCategories ?? '';
    const secondary = secondaryStr ? secondaryStr.split(',') : [];

    const matchesCategory =
      currentCategory === 'all' ||
      primary === currentCategory ||
      secondary.includes(currentCategory);
    const matchesSearch = !q || text.includes(q);
    const visible = matchesCategory && matchesSearch;

    if (visible) { card.removeAttribute('hidden'); totalVisible++; }
    else card.setAttribute('hidden', '');
  });
  // ...rest unchanged
}
```

Apply the same change to `en/products/index.astro`.

**Step 1.4: Render secondary categories on ProductDetail**

In `frontend/src/components/products/ProductDetail.astro:150-162`, replace the tags row with:

```astro
<!-- ② Tags 행: primary + secondary + tags -->
{(product.primary_category || product.secondary_categories?.length || product.tags?.length) && (
  <div class="product-detail-tags-row">
    {product.primary_category && (
      <a href={`/${locale}/products/?cat=${product.primary_category}`} class="product-detail-chip product-detail-chip--category">
        {product.primary_category}
      </a>
    )}
    {product.secondary_categories?.filter(c => c !== product.primary_category).map(cat => (
      <a href={`/${locale}/products/?cat=${cat}`} class="product-detail-chip product-detail-chip--category-secondary">
        {cat}
      </a>
    ))}
    {product.tags?.map((tag) => (
      <span class="product-detail-chip product-detail-chip--tag">#{tag}</span>
    ))}
  </div>
)}
```

**Step 1.5: Add CSS for `.product-detail-chip--category-secondary`**

In `frontend/src/styles/global.css`, find `.product-detail-chip--category` and add a sibling rule just below. Make it visually lighter than primary (e.g., same shape, dimmer text color, no background):

```css
.product-detail-chip--category-secondary {
  /* Inherit base .product-detail-chip styles */
  color: var(--color-text-muted);
  background: transparent;
  border: 1px solid var(--color-border);
}
.product-detail-chip--category-secondary:hover {
  color: var(--color-text);
  border-color: var(--color-text-muted);
}
```

**Step 1.6: Build check**

Run: `cd frontend && npm run build`
Expected: PASS with 0 errors. Ignore the existing "chunks larger than 500 kB" warning.

**Step 1.7: Commit**

```bash
git add frontend/src/components/products/ProductCard.astro \
  frontend/src/components/products/ProductDetail.astro \
  frontend/src/lib/pageData/productsPage.ts \
  frontend/src/pages/ko/products/index.astro \
  frontend/src/pages/en/products/index.astro \
  frontend/src/styles/global.css
git commit -m "feat(products): render secondary_categories on detail + cards + filter"
```

---

## Task 2: Remove EN profile content truncation

**Files:**
- Modify: `backend/services/agents/product_advisor.py:629`

**Step 2.1: Remove `[:2000]` limit**

Find in `_generate_en_profile()`:

```python
parts.append(f"## Raw Source (additional context)\n{(page_content or '(not available)')[:2000]}")
```

Replace with:

```python
parts.append(f"## Raw Source (additional context)\n{page_content or '(not available)'}")
```

Rationale: `_fetch_page_content()` already caps at 4000 chars. gpt-5 has 128K context window. No need to further truncate.

**Step 2.2: Syntax check**

Run: `cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read())"`
Expected output: (empty, exit code 0)

**Step 2.3: Commit**

```bash
git add backend/services/agents/product_advisor.py
git commit -m "fix(ai): remove 2000-char cap on EN profile page content input

fact extraction gets 8000 chars but EN profile only saw 2000.
gpt-5 context is 128K; no reason to truncate further. Fixes
cases where product pages hide key specs (context window,
feature names) past the 2000-char mark."
```

---

## Task 3: EN generation fallback + hard fail

**Files:**
- Modify: `backend/services/agents/product_advisor.py` (around line 772-780, the EN profile try/except)

**Step 3.1: Replace silent empty-dict fallback**

Locate:

```python
try:
    en_profile, en_tokens = await _generate_en_profile(
        facts, page_content, review_content, en_system,
        client, settings.openai_model_main,
    )
    total_tokens += en_tokens
except Exception as e:
    logger.error("EN profile generation failed: %s", e)
    en_profile = {}
```

Replace with:

```python
try:
    en_profile, en_tokens = await _generate_en_profile(
        facts, page_content, review_content, en_system,
        client, settings.openai_model_main,
    )
    total_tokens += en_tokens
except Exception as e:
    logger.warning("EN profile gpt-5 failed: %s, retrying with gpt-5-mini", e)
    try:
        en_profile, en_tokens = await _generate_en_profile(
            facts, page_content, review_content, en_system,
            client, settings.openai_model_light,
        )
        total_tokens += en_tokens
        logger.info("EN profile recovered with gpt-5-mini fallback")
    except Exception as e2:
        logger.error("EN profile fallback also failed: %s", e2)
        raise  # propagate to router for 502 response
```

**Step 3.2: Syntax check**

Run: `cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read())"`
Expected: exit code 0

**Step 3.3: Commit**

```bash
git add backend/services/agents/product_advisor.py
git commit -m "fix(ai): EN profile fallback to gpt-5-mini on failure; hard fail if both fail

prevents silent partial failure where KO/enrich/corpus would
run with empty en_profile and produce meaningless output."
```

---

## Task 4: Deterministic format validator + admin warning UI

**Files:**
- Modify: `backend/services/agents/product_advisor.py` (add helper function near top)
- Modify: `backend/models/product_advisor.py` (add validation_warnings field to response)
- Modify: `frontend/src/pages/admin/products/edit/[slug].astro` (display warnings)

**Step 4.1: Add `_check_profile_format()` helper in product_advisor.py**

Insert after `_resolve_logo_url()` (around line 580, before `_classify_product`):

```python
# Buzzword blocklist for taglines — ordered by frequency
_TAGLINE_BUZZWORDS = (
    "ai-powered", "revolutionary", "cutting-edge", "game-changing",
    "innovative", "industry-leading", "next-generation", "state-of-the-art",
)


def _check_profile_format(profile: dict) -> list[str]:
    """Deterministic format checks — no LLM. Returns list of warning strings."""
    warnings: list[str] = []

    tagline = (profile.get("tagline") or "").strip()
    if tagline:
        words = tagline.split()
        if len(words) > 12:
            warnings.append(f"tagline exceeds 12 words ({len(words)})")
        lower = tagline.lower()
        hits = [w for w in _TAGLINE_BUZZWORDS if w in lower]
        if hits:
            warnings.append(f"tagline contains buzzword: {', '.join(hits)}")

    tagline_ko = (profile.get("tagline_ko") or "").strip()
    if tagline_ko and len(tagline_ko) > 25:
        warnings.append(f"tagline_ko exceeds 25 chars ({len(tagline_ko)})")

    features = profile.get("features") or []
    if not (3 <= len(features) <= 5):
        warnings.append(f"features count off (got {len(features)}, expected 3-5)")
    for f in features:
        if isinstance(f, str) and "→" not in f:
            warnings.append(f"feature missing → pattern: {f[:60]}")

    features_ko = profile.get("features_ko") or []
    if features and features_ko and len(features) != len(features_ko):
        warnings.append(f"features EN/KO count mismatch ({len(features)} vs {len(features_ko)})")

    if profile.get("pricing_detail") is None and profile.get("pricing") in ("freemium", "paid", "enterprise"):
        warnings.append("pricing is not free but pricing_detail is null")

    primary = profile.get("primary_category")
    secondary = profile.get("secondary_categories") or []
    if primary in secondary:
        warnings.append(f"primary_category '{primary}' duplicated in secondary_categories")

    return warnings
```

**Step 4.2: Call validator at end of run_product_generate**

In `run_product_generate()`, right before the final `return result, settings.openai_model_main, total_tokens` of the `generate_from_url` branch, add:

```python
# Deterministic format validation (no LLM cost)
result["_validation_warnings"] = _check_profile_format(result)
if result["_validation_warnings"]:
    logger.info("Profile validation warnings: %s", result["_validation_warnings"])
```

**Step 4.3: Expose warnings on admin editor**

In `frontend/src/pages/admin/products/edit/[slug].astro`, find the AI apply handler (search for `parsed.features`). After applying all fields, add warning display:

```javascript
// Show validation warnings if any
const warnings = parsed._validation_warnings || [];
const warnBox = document.getElementById('ai-validation-warnings');
if (warnBox) {
  if (warnings.length) {
    warnBox.innerHTML = warnings.map(w => `<li>⚠️ ${esc(w)}</li>`).join('');
    warnBox.hidden = false;
  } else {
    warnBox.hidden = true;
    warnBox.innerHTML = '';
  }
}
```

Add the warning box HTML near the AI Advisor panel (around the `ai-loading` div):

```astro
<ul id="ai-validation-warnings" class="admin-ai-warnings" hidden></ul>
```

**Step 4.4: Add CSS for warning list**

In `global.css`:

```css
.admin-ai-warnings {
  margin: 0.5rem 0;
  padding: 0.5rem 0.75rem;
  list-style: none;
  font-size: 0.8rem;
  color: #b45309;
  background: #fef3c7;
  border-radius: 4px;
}
.admin-ai-warnings li { margin: 0.2rem 0; }
[data-theme="dark"] .admin-ai-warnings {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
}
```

**Step 4.5: Syntax + build check**

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read())"
cd frontend && npm run build
```
Expected: both pass.

**Step 4.6: Commit**

```bash
git add backend/services/agents/product_advisor.py \
  frontend/src/pages/admin/products/edit/[slug].astro \
  frontend/src/styles/global.css
git commit -m "feat(admin): deterministic format validator + warning UI for AI output

checks tagline length/buzzwords, tagline_ko 25-char limit,
features count + arrow pattern, EN/KO count match, pricing
consistency, category duplication. LLM-free; shown as
yellow warnings in admin editor before save."
```

---

## Task 5: Prompt version + run log DB

**Files:**
- Create: `supabase/migrations/YYYYMMDDHHMMSS_product_generation_logs.sql`
- Modify: `backend/services/agents/product_advisor.py`

**Step 5.1: Create DB migration**

Create new migration file at `supabase/migrations/<next-number>_product_generation_logs.sql` (find highest existing number and +1). Content:

```sql
-- Product generation audit log
create table if not exists product_generation_logs (
  id uuid primary key default gen_random_uuid(),
  product_slug text,
  action text not null,
  prompt_version text not null,
  model_used text,
  tokens_used integer,
  duration_ms integer,
  success boolean not null default true,
  error_message text,
  facts jsonb,
  validation_warnings jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_product_gen_logs_slug on product_generation_logs(product_slug, created_at desc);
create index if not exists idx_product_gen_logs_version on product_generation_logs(prompt_version, created_at desc);

-- RLS: admin-only read/write (service role bypasses anyway)
alter table product_generation_logs enable row level security;
```

Apply via Supabase MCP:
- Use `mcp__claude_ai_Supabase__apply_migration` with name `product_generation_logs` and the SQL above.

**Step 5.2: Add PROMPT_VERSION constant in product_advisor.py**

At the top of `backend/services/agents/product_advisor.py` (after imports, before the first constant), add:

```python
# Bump this when any generation prompt changes materially.
PROMPT_VERSION = "2026-04-23-v1"
```

**Step 5.3: Add log insert helper**

Insert after `_resolve_logo_url()`:

```python
async def _log_generation(
    product_slug: str | None,
    action: str,
    prompt_version: str,
    model_used: str,
    tokens_used: int,
    duration_ms: int,
    success: bool,
    error_message: str | None,
    facts: dict | None,
    validation_warnings: list[str] | None,
) -> None:
    """Insert a row into product_generation_logs. Never raises."""
    try:
        from core.database import get_supabase
        sb = get_supabase()
        sb.table("product_generation_logs").insert({
            "product_slug": product_slug,
            "action": action,
            "prompt_version": prompt_version,
            "model_used": model_used,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
            "success": success,
            "error_message": error_message,
            "facts": facts,
            "validation_warnings": validation_warnings,
        }).execute()
    except Exception as e:
        logger.warning("Failed to log product generation: %s", e)
```

**Step 5.4: Instrument run_product_generate**

At the start of `run_product_generate()`, add timing:

```python
import time
start_time = time.monotonic()
```

At the final return of the `generate_from_url` branch (after `_check_profile_format` call added in Task 4), wrap result collection:

```python
duration_ms = int((time.monotonic() - start_time) * 1000)
await _log_generation(
    product_slug=getattr(body, "slug", None),
    action=body.action,
    prompt_version=PROMPT_VERSION,
    model_used=settings.openai_model_main,
    tokens_used=total_tokens,
    duration_ms=duration_ms,
    success=True,
    error_message=None,
    facts=facts if isinstance(facts, dict) else None,
    validation_warnings=result.get("_validation_warnings"),
)
return result, settings.openai_model_main, total_tokens
```

Also wrap the hard-fail path from Task 3 (where we `raise`) to log the failure:

```python
except Exception as e2:
    logger.error("EN profile fallback also failed: %s", e2)
    await _log_generation(
        product_slug=getattr(body, "slug", None),
        action=body.action,
        prompt_version=PROMPT_VERSION,
        model_used="multiple",
        tokens_used=total_tokens,
        duration_ms=int((time.monotonic() - start_time) * 1000),
        success=False,
        error_message=str(e2),
        facts=facts if isinstance(facts, dict) else None,
        validation_warnings=None,
    )
    raise
```

**Step 5.5: Verify ProductGenerateRequest accepts slug**

Check `backend/models/product_advisor.py`. If `ProductGenerateRequest` doesn't have `slug`, add it as optional:

```python
slug: str | None = None
```

And on the frontend admin editor, when calling the AI, pass `slug` in the fetch body (only when editing an existing product — for new products it can be null).

**Step 5.6: Syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read())"
cd backend && python -c "import ast; ast.parse(open('models/product_advisor.py', encoding='utf-8').read())"
```

**Step 5.7: Commit (migration + code)**

```bash
git add supabase/migrations/*_product_generation_logs.sql \
  backend/services/agents/product_advisor.py \
  backend/models/product_advisor.py \
  frontend/src/pages/admin/products/edit/[slug].astro
git commit -m "feat(ai): log product generation runs with prompt version

adds product_generation_logs table + PROMPT_VERSION constant
+ duration tracking + success/failure logging. enables
A/B comparison and debugging 'which prompt produced this
output'."
```

---

## Final Verification

**Step F.1: Full backend syntax check**

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read()); ast.parse(open('models/product_advisor.py', encoding='utf-8').read()); print('OK')"
```

**Step F.2: Frontend build**

```bash
cd frontend && npm run build
```

**Step F.3: Manual smoke test (Amy)**

In admin editor:
1. Open an existing product (e.g., Claude)
2. Click "Generate from URL"
3. Verify:
   - Warnings panel shows (or stays hidden if no issues)
   - All fields populated including secondary_categories
   - Check `product_generation_logs` table in Supabase for the new row with correct prompt_version
4. Visit `/ko/products/claude/` — confirm secondary_categories chips appear below primary
5. On `/ko/products/`, click a secondary category — confirm Claude appears in filtered results

**Step F.4: Push**

```bash
git push origin main
```

---

## Out of Scope (Future Work)

- Task 6 (deferred): KO/enrichment model upgrade A/B test (gpt-5-mini → gpt-5). Run after Task 5 ships so we have comparison baseline in logs.
- Benchmark test set (10 diverse products) — useful but large effort, defer until we have 1 week of log data to pick what matters.
- `released_at` field — either remove or surface; decide separately.

## Known Trade-offs

- Task 2 increases EN profile input by ~500 tokens. Cost: ~$0.0006/product. Negligible.
- Task 5 adds 1 DB write per generation. Non-blocking (wrapped in try/except).
- Category filter change in Task 1 may surface products in categories where they were previously hidden — this is intended behavior.
