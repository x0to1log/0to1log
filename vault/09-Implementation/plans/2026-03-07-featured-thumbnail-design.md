# P2C-UI-13: Featured Card Thumbnail Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add og_image_url thumbnail rendering to the featured card with newsprint filter, left-right layout on desktop, stacked on mobile.

**Architecture:** Featured card gets CSS Grid layout (`280px 1fr` desktop, `1fr` mobile). Image uses existing `.img-newsprint` class for grayscale+sepia filter with hover color restore. When `og_image_url` is null, image element is not rendered and card falls back to current full-width text layout.

**Tech Stack:** Astro v5 SSR, CSS custom properties, existing `.img-newsprint` filter class.

---

### Task 1: Add featured card grid layout CSS

**Files:**
- Modify: `frontend/src/styles/global.css` (after `.newsprint-featured[data-filtered="false"]` block, ~line 423)

**Step 1: Add CSS rules**

Insert after line 423 in global.css:

```css
.newsprint-featured--has-img {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1.25rem;
  align-items: start;
}

.newsprint-featured-img {
  width: 100%;
  height: 220px;
  object-fit: cover;
  border: 1px solid var(--color-border);
}

@media (max-width: 767px) {
  .newsprint-featured--has-img {
    grid-template-columns: 1fr;
  }
}
```

**Step 2: Build to verify**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat: add featured card grid layout CSS for thumbnail"
```

---

### Task 2: Add thumbnail to EN log index featured card

**Files:**
- Modify: `frontend/src/pages/en/log/index.astro` (lines 52-63, featured card markup)

**Step 1: Update featured card markup**

Replace the featured card `<a>` block (lines 52-63) with:

```astro
<a href={`/en/log/${featured.slug}/`} class={`newsprint-featured newsprint-card${featured.og_image_url ? ' newsprint-featured--has-img' : ''}`} data-category={featured.category}>
  {featured.og_image_url && (
    <img src={featured.og_image_url} alt={featured.title} class="newsprint-featured-img img-newsprint" loading="lazy" />
  )}
  <div>
    <span class="newsprint-category">{featured.category}</span>
    <h2 class="newsprint-lead-title">{featured.title}</h2>
    {featured.excerpt && <p class="newsprint-excerpt">{featured.excerpt}</p>}
    <div class="newsprint-tags">
      {(featured.tags ?? []).slice(0, 5).map((tag: string) => <span class="newsprint-tag">{tag}</span>)}
    </div>
    <div class="newsprint-meta">
      {featured.published_at && <time>{new Date(featured.published_at).toLocaleDateString('en-US')}</time>}
      {featured.reading_time_min && <span>{featured.reading_time_min} min read</span>}
    </div>
  </div>
</a>
```

Key changes:
- Conditional `newsprint-featured--has-img` class for grid layout
- `<img>` with `.img-newsprint` class (existing filter) + `loading="lazy"`
- Text content wrapped in `<div>` for grid cell
- No image = no `<img>` element, no grid class = current full-width layout

**Step 2: Build to verify**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/pages/en/log/index.astro
git commit -m "feat: add featured thumbnail to EN log index"
```

---

### Task 3: Add thumbnail to KO log index featured card

**Files:**
- Modify: `frontend/src/pages/ko/log/index.astro` (lines 52-63, featured card markup)

**Step 1: Update featured card markup**

Same pattern as Task 2, but with locale `ko`:

```astro
<a href={`/ko/log/${featured.slug}/`} class={`newsprint-featured newsprint-card${featured.og_image_url ? ' newsprint-featured--has-img' : ''}`} data-category={featured.category}>
  {featured.og_image_url && (
    <img src={featured.og_image_url} alt={featured.title} class="newsprint-featured-img img-newsprint" loading="lazy" />
  )}
  <div>
    <span class="newsprint-category">{featured.category}</span>
    <h2 class="newsprint-lead-title">{featured.title}</h2>
    {featured.excerpt && <p class="newsprint-excerpt">{featured.excerpt}</p>}
    <div class="newsprint-tags">
      {(featured.tags ?? []).slice(0, 5).map((tag: string) => <span class="newsprint-tag">{tag}</span>)}
    </div>
    <div class="newsprint-meta">
      {featured.published_at && <time>{new Date(featured.published_at).toLocaleDateString('ko-KR')}</time>}
      {featured.reading_time_min && <span>{featured.reading_time_min}분 읽기</span>}
    </div>
  </div>
</a>
```

**Step 2: Build to verify**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/pages/ko/log/index.astro
git commit -m "feat: add featured thumbnail to KO log index"
```

---

### Task 4: Add mock image to preview pages

**Files:**
- Modify: `frontend/src/pages/preview/newsprint-dark.astro`
- Modify: `frontend/src/pages/preview/newsprint-light.astro`
- Modify: `frontend/src/pages/preview/newsprint-pink.astro`

**Step 1: Add og_image_url to first mock post**

In each preview file, add `og_image_url` to the first mock post object:

```javascript
{
  title: 'GPT-5 Release Shakes Up Enterprise AI Adoption',
  slug: 'preview-gpt5-enterprise',
  category: 'ai-news',
  published_at: new Date().toISOString(),
  reading_time_min: 6,
  tags: ['gpt-5', 'enterprise', 'adoption'],
  excerpt: 'Early benchmarks suggest a 40% improvement in complex reasoning tasks, reshaping how enterprises approach AI integration at scale.',
  og_image_url: 'https://picsum.photos/seed/newsprint/600/400',
  content: '...',
},
```

Use `https://picsum.photos/seed/newsprint/600/400` — stable, deterministic placeholder image.

**Step 2: Update featured card markup in each preview**

Replace the `<article class="newsprint-featured" ...>` block (lines 73-85) with:

```astro
<article class={`newsprint-featured${featured.og_image_url ? ' newsprint-featured--has-img' : ''}`} data-category={featured.category}>
  {featured.og_image_url && (
    <img src={featured.og_image_url} alt={featured.title} class="newsprint-featured-img img-newsprint" loading="lazy" />
  )}
  <div>
    <span class="newsprint-category" style={`color: var(--color-cat-ainews);`}>{featured.category}</span>
    <h2 class="newsprint-lead-title">{featured.title}</h2>
    <p class="newsprint-excerpt">{featured.excerpt}</p>
    <div class="newsprint-tags">
      {featured.tags.map((tag) => <span class="newsprint-tag">{tag}</span>)}
    </div>
    <div class="newsprint-meta">
      <time>{new Date(featured.published_at).toLocaleDateString('en-US')}</time>
      <span>{featured.reading_time_min} min read</span>
    </div>
    <div class="newsprint-divider"></div>
  </div>
</article>
```

Repeat for all 3 preview files.

**Step 3: Build to verify**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 4: Commit**

```bash
git add frontend/src/pages/preview/
git commit -m "feat: add mock thumbnail to newsprint preview pages"
```

---

### Task 5: Update ACTIVE_SPRINT.md + final verification

**Files:**
- Modify: `docs/plans/ACTIVE_SPRINT.md`

**Step 1: Update P2C-UI-13 task**

- Change `체크: [ ]` → `체크: [x]`
- Change `상태: todo` → `상태: done`
- Update 목적 to reflect actual scope: "Featured 카드에 og_image_url 기반 썸네일 렌더링 + 기존 .img-newsprint 필터 연결"
- Add 증거 link to commits
- Add 비고: "나머지 카드는 텍스트 전용 유지. 상세 페이지 hero 이미지는 별도 태스크로 분리."

**Step 2: Final build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add docs/plans/ACTIVE_SPRINT.md
git commit -m "docs: mark P2C-UI-13 done"
```

---

## Verification Checklist

1. `npm run build` — 0 errors
2. Preview pages (dark/light/pink): featured card shows image with grayscale+sepia filter
3. Hover on image: color restores with 400ms transition
4. Image-less posts: featured card renders as full-width text (no broken layout)
5. Mobile viewport (<768px): image stacks above text
