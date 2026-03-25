# Astro Type Error Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 75 astro check errors (18 unique locations) to pass TypeScript strict checking

**Architecture:** Minimal, non-breaking fixes — null guards, type assertions, explicit casts. No refactoring beyond what's needed.

**Tech Stack:** Astro v5, TypeScript, Supabase types

---

### Task 1: Blog category label — string key access (4 files)

**Files:**
- Modify: `frontend/src/components/blog/BlogArticleLayout.astro`
- Modify: `frontend/src/components/blog/BlogBreadcrumb.astro`
- Modify: `frontend/src/components/blog/BlogFeaturedCard.astro`
- Modify: `frontend/src/components/blog/BlogListItem.astro`

**Step 1: Create shared helper**

Add to each file (or a shared util) — replace computed key access:

```typescript
// Before (all 4 files):
catMatch['label_' + locale]

// After:
(locale === 'ko' ? catMatch?.label_ko : catMatch?.label_en) ?? normalizedCat
```

This eliminates computed string key entirely. Explicit conditional is simpler than type gymnastics.

**Step 2: Verify build**
Run: `cd frontend && npm run build`

**Step 3: Commit**
```
fix(types): replace computed key access in blog category labels
```

---

### Task 2: Type-data mismatch — profile.bio + post.tags

**Files:**
- Modify: `frontend/src/pages/settings/index.astro:121`
- Modify: `frontend/src/pages/admin/posts/index.astro:181`

**Step 1: Fix profile.bio**

```typescript
// Before:
const bio = profile?.bio || '';

// After:
const bio = (profile as any)?.bio || '';
```

(bio comes from DB but isn't in the Supabase generated type — `as any` is correct until types are regenerated)

**Step 2: Fix post.tags**

```typescript
// Before:
{post.tags && post.tags.length > 0 && ...

// After:
{Array.isArray(post.tags) && post.tags.length > 0 && ...
```

`Array.isArray` narrows type safely.

**Step 3: Verify build + Commit**
```
fix(types): fix profile.bio and post.tags type access
```

---

### Task 3: Computed definition field access (2 files)

**Files:**
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts:215`
- Modify: `frontend/src/lib/pageData/blogDetailPage.ts:74`

**Step 1: Fix entry[definitionField]**

```typescript
// Before:
definition: entry[definitionField] || '',

// After:
definition: (entry as Record<string, any>)[definitionField] || '',
```

**Step 2: Verify build + Commit**
```
fix(types): cast handbook entry for computed definition field access
```

---

### Task 4: Nullable direct access — sourceCards, termsData, dataset

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro:165`
- Modify: `frontend/src/pages/en/handbook/index.astro:237`
- Modify: `frontend/src/pages/ko/products/index.astro:162`

**Step 1: Fix sourceCards.length**

```typescript
// Before (around line 165):
sourceCount: isKo ? `${sourceCards.length}개 출처` : `${sourceCards.length} sources`,

// After:
sourceCount: isKo ? `${(sourceCards || []).length}개 출처` : `${(sourceCards || []).length} sources`,
```

**Step 2: Fix termsData.sort**

```typescript
// Before:
termsData.sort(...)

// After:
(termsData || []).sort(...)
```

Or add type after JSON.parse.

**Step 3: Fix dataset access**

```typescript
// Before:
t.dataset.category

// After:
(t as HTMLElement).dataset.category
```

**Step 4: Verify build + Commit**
```
fix(types): guard nullable sourceCards, termsData, and dataset access
```

---

### Task 5: DOM null checks — Navigation, articleFind, comments, newsListSearch

**Files:**
- Modify: `frontend/src/components/Navigation.astro:445`
- Modify: `frontend/src/scripts/articleFind.ts:115`
- Modify: `frontend/src/scripts/comments.ts:151`
- Modify: `frontend/src/scripts/newsListSearch.ts:45`

**Step 1: Fix Navigation.astro closure null**

```typescript
// Before (inside scroll handler closure):
header.classList.add(...)
spacer.style.display = ...

// After: store references before closure
const _header = header!;
const _spacer = spacer!;
// Then use _header, _spacer inside handler
```

**Step 2: Fix articleFind.ts**

```typescript
// Before:
countEl.textContent = '';

// After:
if (countEl) countEl.textContent = '';
```

**Step 3: Fix comments.ts**

```typescript
// Before:
charcount.textContent = '';

// After:
if (charcount) charcount.textContent = '';
```

**Step 4: Fix newsListSearch.ts closure**

```typescript
// Before (inside applySearch):
const query = search.value.trim()...

// After: early return or store ref
if (!search) return;
const query = search.value.trim()...
```

**Step 5: Verify build + Commit**
```
fix(types): add DOM null guards in Navigation, articleFind, comments, newsListSearch
```

---

### Task 6: Wide element type — admin editor btnManager

**Files:**
- Modify: `frontend/src/pages/admin/edit/[slug].astro:633`

**Step 1: Fix btnPreview type**

```typescript
// Before:
btnManager.begin(btnPreview, 'Saving...');

// After:
if (btnPreview) btnManager.begin(btnPreview as HTMLButtonElement, 'Saving...');
```

**Step 2: Verify build + Commit**
```
fix(types): narrow btnPreview type for btnManager
```

---

### Task 7: Library type mismatches — markdown.ts, rehypeHandbookTerms.ts

**Files:**
- Modify: `frontend/src/lib/markdown.ts:76,128,138`
- Modify: `frontend/src/lib/rehypeHandbookTerms.ts:150`

**Step 1: Fix shikiOptions type**

```typescript
// Before:
const shikiOptions = { theme: cssVarTheme, langs: SHIKI_LANGS, transformers: [...] };

// After:
const shikiOptions = { theme: cssVarTheme, langs: SHIKI_LANGS, transformers: [...] } as any;
```

(Library type mismatch — `as any` is appropriate for plugin options)

**Step 2: Fix sanitize attribute names (bonus bug)**

```typescript
// Before:
span: [...(sanitizeSchema.attributes?.span || []), 'dataSlug', 'dataTerm'],

// After:
span: [...(sanitizeSchema.attributes?.span || []), 'data-slug', 'data-term'],
```

This is an actual bug — the sanitizer was silently stripping `data-slug` and `data-term` from handbook term spans.

**Step 3: Fix visit.SKIP**

```typescript
// Before:
return [visit.SKIP, index! + parts.length];

// After:
return [visit.SKIP as any, index! + parts.length];
```

**Step 4: Fix termsProcessorCache type**

```typescript
// Before:
const termsProcessorCache = new WeakMap<TermsMap, ReturnType<typeof unified>>();

// After:
const termsProcessorCache = new WeakMap<TermsMap, any>();
```

**Step 5: Verify build + Commit**
```
fix(types): resolve library type mismatches in markdown + rehype plugins
```

---

### Task 8: Final verification

**Step 1:** Run `cd frontend && npx astro check 2>&1 | tail -20`
**Step 2:** Run `cd frontend && npm run build`
**Step 3:** Commit any remaining fixes
```
chore: pass astro check with zero type errors
```

---

## Summary

| Task | Files | Error Count (est.) | Priority |
|------|-------|--------------------|----------|
| 1 | 4 blog components | ~8 | Medium |
| 2 | settings + admin posts | ~4 | High |
| 3 | newsDetail + blogDetail | ~4 | High |
| 4 | ArticleLayout + handbook + products | ~6 | High |
| 5 | Navigation + 3 scripts | ~15 | High |
| 6 | admin editor | ~2 | Medium |
| 7 | markdown + rehype | ~10 | Medium (bonus real bug) |
| 8 | Final verification | — | — |
| **Total** | **~18 files** | **~49 core** | — |
