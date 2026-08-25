# Supabase Egress Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce Supabase egress by removing public request amplification, restoring cacheable anonymous SSR responses, and shrinking public database payloads without exposing personalized HTML.

**Architecture:** Use a staged approach. Phase 1 keeps authenticated SSR private, gives anonymous editorial routes an explicit Vercel CDN policy, removes response `Set-Cookie`, and centralizes compact public query contracts. Phase 2 static delivery remains behind the seven-day egress gate defined in the design document.

**Tech Stack:** Astro 5, TypeScript, Vercel Functions/CDN, Supabase JS, Node structural regression tests

**Design:** `docs/plans/2026-08-24-supabase-egress-hardening-design.md`

---

## Scope Rules

- Work directly on `main` per repository policy.
- Preserve unrelated dirty Vault and portfolio files.
- Stage only the exact files listed in each task; never use `git add .` or `git add -A`.
- Do not change Supabase schema in Phase 1.
- Do not cache admin, preview, settings, library, auth, or `/api/user/*` responses.
- Do not weaken persona behavior for authenticated users.
- A database transport error is not a valid empty state and must never be cached as `200` public HTML.

## Task 1: Lock the request-fan-out regression

**Files:**
- Create: `frontend/tests/public-prefetch-budget.test.cjs`
- Modify: `frontend/src/components/Navigation.astro`
- Modify: `frontend/src/pages/404.astro`

**Step 1: Write the failing test**

Create a structural test that reads Navigation, 404, and Astro config:

```js
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

const navigation = read('src/components/Navigation.astro');
const notFound = read('src/pages/404.astro');
const astroConfig = read('astro.config.mjs');

assert(!navigation.includes('data-astro-prefetch="viewport"'));
assert(!notFound.includes('data-astro-prefetch="viewport"'));
assert(astroConfig.includes("defaultStrategy: 'hover'"));

console.log('public-prefetch-budget.test.cjs passed');
```

**Step 2: Run the test and verify RED**

Run:

```powershell
cd frontend
node tests/public-prefetch-budget.test.cjs
```

Expected: FAIL because Navigation and 404 still contain viewport prefetch.

**Step 3: Remove request amplification**

- Remove explicit viewport prefetch attributes.
- Rely on the existing global hover strategy.
- Do not add eager programmatic fetches as a replacement.

**Step 4: Run focused regressions**

```powershell
node tests/public-prefetch-budget.test.cjs
node tests/navigation-shell-copy.test.cjs
node tests/view-transitions-traverse-reload.test.cjs
```

Expected: all PASS.

**Step 5: Commit**

```powershell
git add frontend/tests/public-prefetch-budget.test.cjs frontend/src/components/Navigation.astro frontend/src/pages/404.astro
git commit -m "fix: stop viewport prefetch request amplification"
```

## Task 2: Make locale preference cache-compatible

**Files:**
- Create: `frontend/tests/public-locale-cache.test.cjs`
- Modify: `frontend/src/middleware.ts`
- Modify: `frontend/src/components/Navigation.astro`

**Step 1: Write the failing locale contract test**

Assert all of the following:

- middleware does not set `site-locale` from `pathname.startsWith('/en/')` or `/ko/`;
- only a validated `lang` query writes the cookie;
- the `lang` flow redirects to the same URL with `lang` removed;
- Navigation language links append a `lang` preference to list and paired-detail targets.

Use source assertions that name the helper and behavior rather than matching an entire implementation block:

```js
assert(!middleware.includes("pathname.startsWith('/en/')" + ") {\n    context.cookies.set('site-locale'"));
assert(middleware.includes("searchParams.delete('lang')"));
assert(middleware.includes("context.redirect(cleanUrl"));
assert(navigation.includes('withLocalePreference'));
```

**Step 2: Run and verify RED**

```powershell
cd frontend
node tests/public-locale-cache.test.cjs
```

Expected: FAIL because middleware currently writes a cookie on every localized request.

**Step 3: Implement clean locale redirects**

In Navigation, wrap every language target with one helper:

```ts
function withLocalePreference(path: string, targetLocale: 'en' | 'ko'): string {
  const separator = path.includes('?') ? '&' : '?';
  return `${path}${separator}lang=${targetLocale}`;
}
```

In middleware, handle valid `lang` before normal route work:

```ts
const langParam = context.url.searchParams.get('lang');
if (langParam === 'en' || langParam === 'ko') {
  const cleanUrl = new URL(context.url);
  cleanUrl.searchParams.delete('lang');
  context.cookies.set('site-locale', langParam, localeCookieOptions);
  return context.redirect(`${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`, 303);
}
```

Do not infer and write the cookie from a localized pathname.

**Step 4: Test locale behavior**

```powershell
node tests/public-locale-cache.test.cjs
node tests/navigation-shell-copy.test.cjs
npm run check
```

Expected: PASS; no Astro errors.

**Step 5: Commit**

```powershell
git add frontend/tests/public-locale-cache.test.cjs frontend/src/middleware.ts frontend/src/components/Navigation.astro
git commit -m "fix: write locale preference only on explicit switch"
```

## Task 3: Centralize anonymous and private cache policy

**Files:**
- Create: `frontend/src/lib/server/publicCachePolicy.ts`
- Create: `frontend/tests/public-cache-policy.test.mjs`
- Modify: `frontend/src/middleware.ts`
- Modify: `frontend/vercel.json`
- Modify: `frontend/src/pages/ko/news/[slug].astro`
- Modify: `frontend/src/pages/en/news/[slug].astro`
- Modify: `frontend/src/pages/ko/handbook/[slug].astro`
- Modify: `frontend/src/pages/en/handbook/[slug].astro`

**Step 1: Write the failing policy test**

The helper should be pure and export these decisions:

```ts
type PublicCacheKind = 'list' | 'detail';

interface PublicCacheInput {
  kind: PublicCacheKind;
  authenticated: boolean;
  preview: boolean;
  hasError: boolean;
}

interface PublicCacheHeaders {
  cacheControl: string;
  vercelCacheControl: string;
  vary?: string;
}
```

Test cases:

```js
assert.equal(policy({ kind: 'list', authenticated: false, preview: false, hasError: false }).vercelCacheControl,
  'public, s-maxage=300, stale-while-revalidate=3600, stale-if-error=86400');
assert.match(policy({ kind: 'detail', authenticated: false, preview: false, hasError: false }).vercelCacheControl, /s-maxage=3600/);
assert.match(policy({ kind: 'list', authenticated: true, preview: false, hasError: false }).cacheControl, /private, no-store/);
assert.match(policy({ kind: 'list', authenticated: false, preview: false, hasError: true }).cacheControl, /no-store/);
```

If importing TypeScript directly is inconvenient in the existing Node test setup, implement the pure policy in `publicCachePolicy.mjs` and import its types through a small `.d.ts`; do not duplicate policy constants in test and production.

**Step 2: Run and verify RED**

```powershell
cd frontend
node tests/public-cache-policy.test.mjs
```

Expected: FAIL because the helper does not exist.

**Step 3: Implement the policy helper**

- Browser header for public HTML: `public, max-age=0, must-revalidate`.
- Vercel list TTL: 300 seconds; SWR one hour; stale-if-error one day.
- Vercel detail TTL: one hour; SWR one day; stale-if-error seven days.
- Auth, preview, and errors: `private, no-store` or `no-store`.
- Public responses include `Vary: Cookie` during Phase 1.

**Step 4: Apply the policy once**

Middleware should classify only these public editorial paths:

```text
/{en|ko}/
/{en|ko}/news/*
/{en|ko}/handbook/*
/{en|ko}/products/*
/{en|ko}/blog/*
```

Exclude admin, preview, API, library, settings, login, auth callback, and non-GET requests. Apply the headers to the final response returned by `nextWithCsp`.

Remove duplicated page-level public cache branches and the overlapping editorial `Cache-Control` entries from `vercel.json`. Keep immutable asset and security headers.

**Step 5: Run focused tests**

```powershell
node tests/public-cache-policy.test.mjs
node tests/news-persona-cache-policy.test.cjs
node tests/public-locale-cache.test.cjs
npm run check
```

Update `news-persona-cache-policy.test.cjs` to assert the centralized contract rather than the removed inline header strings.

**Step 6: Commit**

```powershell
git add frontend/src/lib/server/publicCachePolicy.ts frontend/tests/public-cache-policy.test.mjs frontend/src/middleware.ts frontend/vercel.json frontend/src/pages/ko/news/[slug].astro frontend/src/pages/en/news/[slug].astro frontend/src/pages/ko/handbook/[slug].astro frontend/src/pages/en/handbook/[slug].astro frontend/tests/news-persona-cache-policy.test.cjs
git commit -m "fix: centralize safe public content caching"
```

## Task 4: Move list bookmark and read state out of SSR

**Files:**
- Create: `frontend/src/pages/api/user/content-status.ts`
- Create: `frontend/src/scripts/content-status.ts`
- Create: `frontend/tests/public-list-personalization.test.cjs`
- Modify: `frontend/src/scripts/bookmark.ts`
- Modify: `frontend/src/pages/ko/news/index.astro`
- Modify: `frontend/src/pages/en/news/index.astro`
- Modify: `frontend/src/pages/ko/handbook/index.astro`
- Modify: `frontend/src/pages/en/handbook/index.astro`
- Modify: `frontend/src/pages/ko/blog/index.astro`
- Modify: `frontend/src/pages/en/blog/index.astro`

**Step 1: Write the failing structural test**

For each public list page, assert that it does not create an authenticated Supabase client or query `reading_history`/`user_bookmarks`. Assert that the page renders item IDs and imports the shared hydration script.

**Step 2: Run and verify RED**

```powershell
cd frontend
node tests/public-list-personalization.test.cjs
```

Expected: FAIL because all three list surfaces query user state during SSR.

**Step 3: Add a bounded batch status API**

`POST /api/user/content-status` request:

```json
{
  "items": [
    { "item_type": "news", "item_id": "uuid" }
  ]
}
```

Rules:

- middleware auth remains authoritative;
- reject more than 200 items with `400`;
- deduplicate IDs before querying;
- run one bookmark query and one reading-history query;
- return `{ bookmarks: { id: true }, reads: { id: true } }`;
- return no content fields.

**Step 4: Add client hydration**

The script must:

- collect rendered `data-item-id`/`data-item-type` pairs;
- call the batch endpoint once per `astro:page-load`;
- update bookmark fill and read-state classes;
- use a dataset initialization flag to avoid duplicate listeners;
- treat `401` as anonymous without showing an error.

Refactor `bookmark.ts` so it does not issue a second bookmark-status request after the shared hydration script has run.

**Step 5: Remove SSR user-state queries**

Render public cards with neutral defaults. Preserve IDs and item types so hydration can update them. Persona title selection can remain request-specific for authenticated responses in Phase 1.

**Step 6: Verify**

```powershell
node tests/public-list-personalization.test.cjs
node tests/auth-prompt-library-preview.test.cjs
node tests/news-persona-cache-policy.test.cjs
npm run check
```

Manual checks: signed-out cards remain neutral; signed-in bookmark/read states appear after hydration; View Transition navigation does not duplicate requests.

**Step 7: Commit**

```powershell
git add frontend/src/pages/api/user/content-status.ts frontend/src/scripts/content-status.ts frontend/src/scripts/bookmark.ts frontend/tests/public-list-personalization.test.cjs frontend/src/pages/ko/news/index.astro frontend/src/pages/en/news/index.astro frontend/src/pages/ko/handbook/index.astro frontend/src/pages/en/handbook/index.astro frontend/src/pages/ko/blog/index.astro frontend/src/pages/en/blog/index.astro
git commit -m "fix: hydrate public list user state client side"
```

## Task 5: Reduce Home query duplication

**Files:**
- Create: `frontend/tests/home-query-budget.test.cjs`
- Modify: `frontend/src/lib/pageData/homePage.ts`

**Step 1: Write the failing test**

Assert:

- only one base `news_posts` query is present in `getHomePageData`;
- Handbook fallback is conditional rather than part of the initial `Promise.all`;
- term columns are locale-specific;
- existing limits for blog, terms, and featured products remain bounded.

**Step 2: Run and verify RED**

```powershell
cd frontend
node tests/home-query-budget.test.cjs
```

**Step 3: Implement one news window**

Fetch the latest 20 published locale posts once. Derive the seven-day set in memory; when fewer than three are recent, use the already-fetched latest rows as fallback.

Fetch favourite terms in the initial parallel group. Only query non-favourite fallback terms if fewer than six favourites were returned. Select `definition_ko` for KO and `definition_en` for EN, not both.

**Step 4: Verify and commit**

```powershell
node tests/home-query-budget.test.cjs
npm run check
git add frontend/tests/home-query-budget.test.cjs frontend/src/lib/pageData/homePage.ts
git commit -m "perf: reduce duplicate home page database reads"
```

## Task 6: Create a compact locale-aware Handbook index

**Files:**
- Create: `frontend/src/lib/pageData/publicTermIndex.ts`
- Create: `frontend/tests/public-term-index.test.cjs`
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts`
- Modify: `frontend/src/lib/pageData/blogDetailPage.ts`
- Modify: `frontend/src/lib/pageData/handbookPage.ts`

**Step 1: Write the failing contract test**

Assert that one shared helper owns the detail-term select and that News/Blog no longer contain `body_basic_ko, body_basic_en`. Assert Handbook list columns do not include both locale definitions in one request.

**Step 2: Run and verify RED**

```powershell
cd frontend
node tests/public-term-index.test.cjs
```

Expected: FAIL on all current duplicated term queries.

**Step 3: Implement the helper**

Expose:

```ts
export async function fetchPublicTermIndex(
  db: SupabaseClient,
  locale: 'en' | 'ko',
  limit = 200,
): Promise<PublicTermIndexEntry[]>;
```

Construct the select from locale-specific `summary`, `definition`, and `body_basic` field names. Normalize aliases to `summary`, `definition`, and `basic_plain` in TypeScript so callers do not need both language columns.

**Step 4: Reuse the helper**

- News detail and Blog detail use the same normalized term data.
- Handbook list selects only the active locale definition.
- Preserve all current inline-link and popup behavior.

**Step 5: Verify**

```powershell
node tests/public-term-index.test.cjs
node tests/handbook-popup-render.test.ts
node tests/handbook-search-recognition.test.cjs
node tests/news-fact-pack-structure.test.cjs
npm run check
```

If the TypeScript test cannot run directly with Node, rely on the structural tests plus `astro check` and build; do not add a test runner solely for this task.

**Step 6: Commit**

```powershell
git add frontend/src/lib/pageData/publicTermIndex.ts frontend/tests/public-term-index.test.cjs frontend/src/lib/pageData/newsDetailPage.ts frontend/src/lib/pageData/blogDetailPage.ts frontend/src/lib/pageData/handbookPage.ts
git commit -m "perf: reuse a compact localized handbook index"
```

## Task 7: Replace public detail wildcard selects

**Files:**
- Create: `frontend/tests/public-detail-query-contract.test.cjs`
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts`
- Modify: `frontend/src/lib/pageData/handbookDetailPage.ts`
- Modify: `frontend/src/lib/pageData/blogDetailPage.ts`
- Modify: `frontend/src/lib/pageData/productsPage.ts`

**Step 1: Write the failing test**

Read the four public loaders and reject `.select('*')`. Require named constants:

```text
NEWS_DETAIL_PUBLIC_COLUMNS
HANDBOOK_DETAIL_PUBLIC_COLUMNS
BLOG_DETAIL_PUBLIC_COLUMNS
PRODUCT_DETAIL_PUBLIC_COLUMNS
```

The test should inspect only public page-data loaders, not admin editors where complete rows may be intentional.

**Step 2: Run and verify RED**

```powershell
cd frontend
node tests/public-detail-query-contract.test.cjs
```

**Step 3: Define explicit contracts**

News must retain fields used by article rendering and persona switching:

```text
id, slug, locale, status, title, title_learner, title_beginner,
excerpt, category, post_type, published_at, updated_at, reading_time_min,
tags, og_image_url, translation_group_id, focus_items, guide_items,
content_original, content_analysis, content_beginner, content_learner,
content_expert, fact_pack, source_cards, source_urls
```

Blog must retain its single localized article body, metadata, translation group, persona metadata if used, and admin-facing fields only in preview mode.

Handbook and Product constants must list every field mapped into their detail view but omit unrelated timestamps, hidden quality metadata, opposite-locale bodies where the page does not need them, and admin-only enrichment fields.

If preview requires a wider contract, define a separate authorized preview column constant. Do not restore wildcard selects.

**Step 4: Run regression tests**

```powershell
node tests/public-detail-query-contract.test.cjs
node tests/news-persona-title-switcher.test.cjs
node tests/news-fact-pack-structure.test.cjs
node tests/blog-detail-sidebar-structure.test.cjs
node tests/product-detail-scenarios-theme.test.cjs
npm run check
```

**Step 5: Commit**

```powershell
git add frontend/tests/public-detail-query-contract.test.cjs frontend/src/lib/pageData/newsDetailPage.ts frontend/src/lib/pageData/handbookDetailPage.ts frontend/src/lib/pageData/blogDetailPage.ts frontend/src/lib/pageData/productsPage.ts
git commit -m "perf: bound public detail query payloads"
```

## Task 8: Audit list payloads without reducing visible coverage

**Files:**
- Create: `frontend/tests/public-list-query-budget.test.cjs`
- Modify: `frontend/src/pages/ko/news/index.astro`
- Modify: `frontend/src/pages/en/news/index.astro`
- Modify: `frontend/src/lib/pageData/handbookPage.ts`
- Modify: `frontend/src/lib/pageData/productsPage.ts`
- Modify: `frontend/src/pages/ko/products/index.astro`
- Modify: `frontend/src/pages/en/products/index.astro`

**Step 1: Write budget assertions**

- News list constants remain explicit and bounded.
- Handbook list never requests body fields or both locale definitions.
- Product category query does not use wildcard select.
- Product list fields have comments/tests proving whether `demo_media` and `search_corpus` are rendered.
- No public list query loses its status/locale/published filters.

**Step 2: Run and verify RED**

```powershell
cd frontend
node tests/public-list-query-budget.test.cjs
```

**Step 3: Slim only proven payload waste**

- Replace category `.select('*')` with the exact category tile fields.
- Keep `demo_media` only if a product lacks a dedicated thumbnail and the UI visibly uses the first demo image.
- Replace `search_corpus` with existing compact name/tag/category/platform fields unless a production payload measurement proves it is small enough to keep.
- Preserve all Handbook terms for client search, but transfer only the active locale's compact card definition.
- Keep the weekly News query separate; do not trade correctness for one fewer query.

**Step 4: Verify search and cards**

```powershell
node tests/public-list-query-budget.test.cjs
node tests/product-filter-bar-mobile-sticky.test.cjs
node tests/product-detail-search-sticky.test.cjs
node tests/handbook-search-recognition.test.cjs
node tests/news-search-list-structure.test.cjs
npm run check
```

**Step 5: Commit**

```powershell
git add frontend/tests/public-list-query-budget.test.cjs frontend/src/pages/ko/news/index.astro frontend/src/pages/en/news/index.astro frontend/src/lib/pageData/handbookPage.ts frontend/src/lib/pageData/productsPage.ts frontend/src/pages/ko/products/index.astro frontend/src/pages/en/products/index.astro
git commit -m "perf: enforce public list query budgets"
```

## Task 9: Prevent caching of Supabase error pages

**Files:**
- Create: `frontend/tests/public-error-cache-policy.test.cjs`
- Modify: `frontend/src/pages/ko/index.astro`
- Modify: `frontend/src/pages/en/index.astro`
- Modify: `frontend/src/pages/ko/news/index.astro`
- Modify: `frontend/src/pages/en/news/index.astro`
- Modify: `frontend/src/pages/ko/handbook/index.astro`
- Modify: `frontend/src/pages/en/handbook/index.astro`
- Modify: `frontend/src/pages/ko/products/index.astro`
- Modify: `frontend/src/pages/en/products/index.astro`
- Modify: `frontend/src/pages/ko/blog/index.astro`
- Modify: `frontend/src/pages/en/blog/index.astro`
- Modify: public detail pages that currently leave loader errors at status 200

**Step 1: Write the failing status contract test**

Require each public data-backed page to distinguish a valid empty result from a loader error and set `Astro.response.status = 503` for the latter.

**Step 2: Run and verify RED**

```powershell
cd frontend
node tests/public-error-cache-policy.test.cjs
```

**Step 3: Set explicit error status**

- Preserve the existing localized error UI.
- Set `503` only for transport/database failures.
- Keep real not-found detail rows at `404`.
- Keep valid empty lists at `200`.
- Ensure the cache helper sees non-success/error state and returns `no-store`.

**Step 4: Verify**

```powershell
node tests/public-error-cache-policy.test.cjs
node tests/public-cache-policy.test.mjs
npm run check
```

**Step 5: Commit**

Stage only the tested public pages and test file:

```powershell
git add frontend/tests/public-error-cache-policy.test.cjs frontend/src/pages/ko frontend/src/pages/en
git commit -m "fix: prevent caching public data errors"
```

Before committing, inspect `git diff --cached --name-only` and unstage unrelated locale files if directory staging captured anything outside this task.

## Task 10: Full local verification

**Files:**
- Modify only if a regression is directly caused by Tasks 1-9.

**Step 1: Run all structural tests**

PowerShell:

```powershell
cd frontend
Get-ChildItem tests -Filter *.test.cjs | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { throw "Failed: $($_.Name)" } }
Get-ChildItem tests -Filter *.test.mjs | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { throw "Failed: $($_.Name)" } }
```

Record baseline failures separately. Do not repair unrelated failures.

**Step 2: Run Astro checks and build**

```powershell
npm run check
npm run build
```

Expected: zero new errors and successful production build.

**Step 3: Inspect scope**

```powershell
git status --short
git diff --stat
git diff --check
```

Expected: unrelated existing Vault/portfolio edits remain unstaged and unchanged.

## Task 11: Production verification after push

**Files:**
- No source changes unless verification exposes a regression.

**Step 1: Verify cache headers without DevTools forced reload**

```powershell
$url = 'https://0to1log.com/ko/news/'
curl.exe -sSI $url
Start-Sleep -Seconds 2
curl.exe -sSI $url
```

Acceptance:

- first request may be `MISS`;
- second request is `HIT` with `Age > 0`;
- normal response has no `Set-Cookie: site-locale`;
- response does not cache a Supabase error page.

Repeat for Home, Handbook, Products, Blog, and one detail URL in each content type.

**Step 2: Verify locale switch**

- Click KO to EN and EN to KO.
- Confirm the redirect response sets `site-locale`.
- Confirm the final URL has no `lang` query.
- Confirm paired News/Blog detail slugs still resolve.

**Step 3: Verify request count**

With a fresh anonymous browser context, load `/ko/` and inspect document requests. News, Handbook, Products, Library, and Blog must not all load before hover/click.

**Step 4: Verify signed-in behavior**

- Login menu and profile remain correct.
- Persona-specific News title/content remains correct.
- Bookmark/read state hydrates correctly.
- Authenticated content response is `private, no-store`.
- Admin preview remains uncached.

## Task 12: Seven-day egress gate

**Files:**
- Update after measurement: `vault/07-Operations/Supabase-Egress-&-Public-Cache-Policy.md`
- Create only if gate opens: `docs/plans/YYYY-MM-DD-public-editorial-static-delivery-design.md`

**Step 1: Record daily usage**

For seven complete days after service restoration, record:

```text
date
organization egress
0to1log project egress
other-project egress
sample route HIT/MISS result
unexpected traffic or deployment notes
```

**Step 2: Evaluate**

Pass when:

- rolling average is `<= 120 MB/day`;
- projected month is `<= 4 GB`;
- repeated anonymous route samples reach at least 90% HIT;
- no personalized HTML is found in shared responses.

**Step 3: Open Phase 2 only when required**

If the threshold is exceeded for three consecutive days, write and approve a separate design for user-neutral public HTML, client auth/persona hydration, real revalidation, and Astro/Vercel static delivery. Do not silently broaden this implementation plan.

## Final Delivery Checklist

- [ ] No public viewport prefetch remains.
- [ ] Normal localized content responses do not set locale cookies.
- [ ] Explicit language switch persists locale through a clean redirect.
- [ ] Anonymous public responses become CDN HITs.
- [ ] Authenticated, preview, admin, and error responses are not shared.
- [ ] Public list user-state SSR queries are removed.
- [ ] News/Blog detail term data uses one locale-aware compact helper.
- [ ] Public detail loaders contain no wildcard selects.
- [ ] Public list payloads preserve search and archive behavior.
- [ ] `npm run check` and `npm run build` pass.
- [ ] Unrelated dirty files remain untouched and unstaged.
- [ ] Seven-day egress measurement is scheduled after service restoration.
