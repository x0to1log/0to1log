# PERF-HTML-SLIM-01: News Detail HTML Lazy Loading

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce news detail page HTML from 322KB to ~100-150KB by lazy-loading the inactive persona content on tab switch instead of inlining both personas in the initial HTML.

**Architecture:** Currently both Expert and Learner rendered HTML are serialized into a `<template data-map>` attribute (~160KB JSON). Instead, only serve the active persona's HTML in the initial page. When the user switches tabs, fetch the other persona's rendered HTML from a new lightweight API endpoint. The API returns pre-rendered HTML, so no client-side markdown processing is needed.

**Tech Stack:** Astro v5, TypeScript, Supabase

---

## Current State (Problem)

```
Initial HTML (322KB):
├── Active persona HTML (inline in article body)     ~60KB
├── Inactive persona HTML (in <template data-map>)   ~60KB  ← WASTE
├── Analysis HTML (in <template data-map>)            ~20KB  ← small, keep
├── Handbook terms JSON (<script> tag)                ~40KB
├── Source cards, quizzes JSON (in <template>)        ~15KB
└── Page shell, nav, rail, CSS                        ~127KB
```

**Target:** Remove inactive persona from `<template data-map>`, serve only active persona + analysis. Save ~60KB.

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/pages/api/news/persona-content.ts` | **Create** | API endpoint: given `slug`, `locale`, `persona` → returns rendered HTML |
| `frontend/src/lib/pageData/newsDetailPage.ts` | **Modify** | Stop including inactive persona in `personaHtmlMap` |
| `frontend/src/components/newsprint/NewsprintArticleLayout.astro` | **Modify** | `data-map` only has active persona; tab switch triggers fetch |
| `frontend/src/scripts/persona-switcher.ts` | **Modify** (or create if inline) | Add fetch logic on tab switch for missing persona |

---

## Task 1: Create Persona Content API

**Files:**
- Create: `frontend/src/pages/api/news/persona-content.ts`

This endpoint renders a single persona's markdown and returns the HTML. It uses the same `renderMarkdownWithTerms` pipeline as the SSR page, so output is identical.

- [ ] **Step 1: Create the API route**

```typescript
// frontend/src/pages/api/news/persona-content.ts
import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { renderMarkdown, renderMarkdownWithTerms, type TermsMap } from '../../../lib/markdown';
import { getDefinitionField } from '../../../lib/pageData/shared';

export const prerender = false;

function applySourceCitations(html: string): string {
  if (!html) return html;
  return html.replace(/\[\[(\d+)\]\]/g, (_match, index) =>
    `<sup class="newsprint-citation"><a href="#source-card-${index}">${index}</a></sup>`
  );
}

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get('slug');
  const locale = url.searchParams.get('locale') as 'en' | 'ko' | null;
  const persona = url.searchParams.get('persona');

  if (!slug || !locale || !persona || !['expert', 'learner'].includes(persona)) {
    return new Response(JSON.stringify({ error: 'Missing slug, locale, or persona' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
  );

  const contentColumn = persona === 'expert' ? 'content_expert' : 'content_learner';
  const definitionField = getDefinitionField(locale);

  const [postRes, termsRes] = await Promise.all([
    supabase
      .from('news_posts')
      .select(`${contentColumn}, source_urls, source_cards, guide_items`)
      .eq('slug', slug)
      .eq('locale', locale)
      .eq('status', 'published')
      .single(),
    supabase
      .from('handbook_terms')
      .select(`term, slug, korean_name, ${definitionField}`)
      .eq('status', 'published')
      .limit(200),
  ]);

  if (!postRes.data?.[contentColumn]) {
    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Build terms map
  const termsMap: TermsMap = new Map();
  for (const entry of (termsRes.data || [])) {
    const termEntry = { slug: entry.slug, term: entry.term };
    termsMap.set(entry.term.toLowerCase(), termEntry);
    if (entry.korean_name) termsMap.set(entry.korean_name.toLowerCase(), termEntry);
  }

  const renderMd = termsMap.size > 0
    ? (md: string) => renderMarkdownWithTerms(md, termsMap)
    : (md: string) => renderMarkdown(md);

  const html = applySourceCitations(await renderMd(postRes.data[contentColumn]));

  // Extract persona-specific sources
  const guideItems = postRes.data.guide_items || {};
  const sources = guideItems[`sources_${persona}`] || null;

  return new Response(JSON.stringify({ html, sources }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
    },
  });
};
```

- [ ] **Step 2: Verify endpoint builds**

Run: `cd frontend && npm run build`
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/api/news/persona-content.ts
git commit -m "feat: add persona content API for lazy loading"
```

---

## Task 2: Only Include Active Persona in SSR HTML

**Files:**
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts:259-269`

Change: instead of rendering ALL personas in `personaHtmlMap`, only render the active persona + analysis. Return a `availablePersonas` list so the client knows which tab buttons to show.

- [ ] **Step 1: Modify rendering to only include active persona**

In `newsDetailPage.ts`, replace the block that renders all personas:

```typescript
// BEFORE (line 259-269):
// Render all persona content + analysis in parallel
const renderEntries = Object.entries(contentMap).filter(([, md]) => md);
if (post.content_analysis) renderEntries.push(['__analysis', post.content_analysis]);

const rendered = await Promise.all(
  renderEntries.map(async ([key, md]) => [key, applySourceCitations(await renderMd(md))] as const),
);
for (const [key, html] of rendered) {
  if (key === '__analysis') analysisHtml = html;
  else personaHtmlMap[key] = html;
}

// AFTER:
// Render only active persona + analysis (inactive loads on demand via API)
const renderEntries: [string, string][] = [];
if (contentMap[personaKey]) renderEntries.push([personaKey, contentMap[personaKey]]);
if (post.content_analysis) renderEntries.push(['__analysis', post.content_analysis]);

const rendered = await Promise.all(
  renderEntries.map(async ([key, md]) => [key, applySourceCitations(await renderMd(md))] as const),
);
for (const [key, html] of rendered) {
  if (key === '__analysis') analysisHtml = html;
  else personaHtmlMap[key] = html;
}
```

Also add `availablePersonas` to the return value:

```typescript
// Add to return object:
availablePersonas: Object.keys(contentMap).filter(k => contentMap[k]),
```

- [ ] **Step 2: Update return type**

Add `availablePersonas` to the return statement alongside existing fields.

- [ ] **Step 3: Build check**

Run: `cd frontend && npm run build`
Expected: 0 errors (type errors from template will show — fix in Task 3)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/pageData/newsDetailPage.ts
git commit -m "perf: only render active persona in SSR, skip inactive"
```

---

## Task 3: Update Template to Fetch on Tab Switch

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro`
- Modify: `frontend/src/pages/ko/news/[slug].astro` (pass new props)
- Modify: `frontend/src/pages/en/news/[slug].astro` (pass new props)

The template needs two changes:
1. Use `availablePersonas` (not `personaHtmlMap` keys) for rendering tab buttons
2. When `data-map` doesn't contain the requested persona, fetch from API

- [ ] **Step 1: Add `availablePersonas` prop and use it for tab rendering**

In `NewsprintArticleLayout.astro`, add prop:
```typescript
availablePersonas?: string[];
```

Replace `personaHtmlMap![p]` filter in tab buttons with `availablePersonas`:
```typescript
// BEFORE:
{(['learner', 'expert'] as const).filter(p => personaHtmlMap![p]).map(p => (

// AFTER:
{(['learner', 'expert'] as const).filter(p => availablePersonas?.includes(p)).map(p => (
```

Apply same change to the floating persona buttons.

- [ ] **Step 2: Update persona switcher script to fetch missing content**

Find the persona switcher `<script>` in `NewsprintArticleLayout.astro` (or `persona-switcher.ts`). In the click handler, when `personaMap[persona]` is missing, fetch from API:

```typescript
// In the persona switch handler:
let html = personaMap[persona];
if (!html) {
  const slug = /* get from page URL or data attribute */;
  const locale = /* get from data attribute */;
  const res = await fetch(`/api/news/persona-content?slug=${slug}&locale=${locale}&persona=${persona}`);
  if (res.ok) {
    const data = await res.json();
    html = data.html;
    personaMap[persona] = html; // Cache for subsequent switches
  }
}
if (html) {
  contentEl.innerHTML = html;
}
```

- [ ] **Step 3: Pass `availablePersonas` from page templates**

In both `ko/news/[slug].astro` and `en/news/[slug].astro`, pass the new prop to `NewsprintArticleLayout`:
```typescript
availablePersonas={availablePersonas}
```

- [ ] **Step 4: Build + manual test**

Run: `cd frontend && npm run build`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/newsprint/NewsprintArticleLayout.astro \
  frontend/src/pages/ko/news/\[slug\].astro \
  frontend/src/pages/en/news/\[slug\].astro
git commit -m "perf: lazy-load inactive persona on tab switch via API"
```

---

## Task 4: Verify HTML Size Reduction

- [ ] **Step 1: Deploy and measure**

```bash
npx agent-browser open "https://0to1log.com/ko/news/<latest-slug>/"
npx agent-browser wait --load networkidle
npx agent-browser eval 'document.documentElement.outerHTML.length / 1024'
```

Expected: ~150-200KB (down from 322KB)

- [ ] **Step 2: Test persona tab switch**

Click the inactive persona tab → verify content loads via API and displays correctly.

- [ ] **Step 3: Update sprint**

Mark `PERF-HTML-SLIM-01` as done in `ACTIVE_SPRINT.md`.

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| API fetch fails on tab switch | Show loading indicator, fallback to error message |
| API response differs from SSR render | Same `renderMarkdownWithTerms` pipeline, same output |
| CDN cache on API | `s-maxage=3600` — same policy as page |
| SEO impact (inactive persona not in HTML) | Search engines only see default persona, which is the intended indexed content |
| Preview mode | Preview should render both (admin needs to see both). Add `previewMode` check to skip lazy loading |
