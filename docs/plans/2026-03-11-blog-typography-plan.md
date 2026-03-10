# IT Blog Typography Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Apply IBM Plex Sans (EN) + IBM Plex Sans KR (KO) to the entire IT Blog section, keeping News/Handbook/Admin on existing serif fonts.

**Architecture:** Add new `--font-blog-*` CSS custom properties in `global.css @theme`. Load IBM Plex Sans via Google Fonts conditionally in `Head.astro` (only on `/blog/` pages). Override font-family on `.blog-shell` so all children inherit, then explicitly set heading/UI fonts on specific selectors.

**Tech Stack:** Tailwind CSS v4 custom theme, Google Fonts CDN, Astro `Head.astro` component

**Design doc:** `docs/plans/2026-03-11-blog-typography-design.md`

---

### Task 1: Add blog font variables to @theme

**Files:**
- Modify: `frontend/src/styles/global.css:24-33` (the `@theme` block)

**Step 1: Add three new font variables to the @theme block**

In `frontend/src/styles/global.css`, inside the `@theme { }` block (line 24-39), add the blog font variables after the existing `--font-code` line (line 33):

```css
  --font-blog-heading: 'IBM Plex Sans', 'IBM Plex Sans KR', sans-serif;
  --font-blog-body: 'IBM Plex Sans', 'IBM Plex Sans KR', sans-serif;
  --font-blog-ui: 'IBM Plex Sans', 'IBM Plex Sans KR', sans-serif;
```

Existing variables must NOT be modified.

**Step 2: Verify**

Run: `cd frontend && npx astro check 2>&1 | head -20`
Expected: No CSS parse errors.

**Step 3: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat(blog): add IBM Plex Sans font variables to @theme"
```

---

### Task 2: Conditional Google Fonts loading in Head.astro

**Files:**
- Modify: `frontend/src/components/Head.astro:43-48` (font loading section)

**Step 1: Add blog path detection**

In the frontmatter section (before `---` closing), add:

```typescript
const isBlogPage = Astro.url.pathname.includes('/blog/');
```

**Step 2: Add conditional IBM Plex Sans link after existing Google Fonts stylesheet**

After the existing Google Fonts `<link>` (line 48), add:

```html
{isBlogPage && (
  <link
    href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap"
    rel="stylesheet"
  />
)}
```

The existing `preconnect` links to `fonts.googleapis.com` and `fonts.gstatic.com` (lines 43-44) are already present, so no need to duplicate them.

**Step 3: Commit**

```bash
git add frontend/src/components/Head.astro
git commit -m "feat(blog): conditionally load IBM Plex Sans on blog pages"
```

---

### Task 3: Set base font on .blog-shell

**Files:**
- Modify: `frontend/src/styles/global.css:4636` (`.blog-shell` selector)

**Step 1: Add font-family to .blog-shell**

Find the `.blog-shell` rule (line 4636) and add `font-family: var(--font-blog-body);` to it. This makes all children inherit IBM Plex Sans by default.

**Step 2: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat(blog): set IBM Plex Sans as blog-shell base font"
```

---

### Task 4: Update blog heading selectors

**Files:**
- Modify: `frontend/src/styles/global.css` — multiple selectors

**Step 1: Update .blog-masthead-title (line ~5186)**

Change `font-family: var(--font-masthead)` → `font-family: var(--font-blog-heading)`
Change `font-weight: 900` → `font-weight: 600`

**Step 2: Update .blog-article-title (line ~5123)**

Change `font-family: var(--font-display)` → `font-family: var(--font-blog-heading)`
Keep `font-weight: 700`.

**Step 3: Update .blog-featured-card-title (line ~4898)**

Change `font-family: var(--font-display)` → `font-family: var(--font-blog-heading)`
Change `font-weight: 700` → `font-weight: 500`

**Step 4: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat(blog): update heading selectors to IBM Plex Sans"
```

---

### Task 5: Update blog UI selectors (code → blog-ui)

**Files:**
- Modify: `frontend/src/styles/global.css` — multiple selectors

These selectors currently use `var(--font-code)` (JetBrains Mono) for UI purposes. Change them to `var(--font-blog-ui)`.

**Step 1: Update .blog-section-header (line ~4852)**

Change `font-family: var(--font-code)` → `font-family: var(--font-blog-ui)`

**Step 2: Update .blog-mono-tag (line ~4937)**

Change `font-family: var(--font-code)` → `font-family: var(--font-blog-ui)`

**Step 3: Update .blog-list-item-date (line ~5002)**

Change `font-family: var(--font-code)` → `font-family: var(--font-blog-ui)`

**Step 4: Update .blog-list-item-category (line ~5009)**

Change `font-family: var(--font-code)` → `font-family: var(--font-blog-ui)`

**Step 5: Update .blog-toc-header (line ~5066)**

Change `font-family: var(--font-code)` → `font-family: var(--font-blog-ui)`

**Step 6: Update .blog-article-meta (line ~5134)**

Change `font-family: var(--font-code)` → `font-family: var(--font-blog-ui)`

**Step 7: Update .blog-code-copy (line ~5154)**

Change `font-family: var(--font-code)` → `font-family: var(--font-blog-ui)`

**Step 8: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat(blog): update UI selectors from monospace to IBM Plex Sans"
```

---

### Task 6: Scope .newsprint-prose for blog context

**Files:**
- Modify: `frontend/src/styles/global.css` — add blog-scoped overrides

`.newsprint-prose` is shared by News and Blog. We need blog-scoped overrides so only blog articles get IBM Plex Sans.

**Step 1: Add scoped overrides**

After the existing `.newsprint-prose` rules (around line 610), add a new block:

```css
/* Blog-scoped newsprint prose overrides */
.blog-shell .newsprint-prose h1,
.blog-shell .newsprint-prose h2,
.blog-shell .newsprint-prose h3,
.blog-shell .newsprint-prose h4 {
  font-family: var(--font-blog-heading);
}

.blog-shell .newsprint-prose p:first-of-type::first-letter {
  font-family: var(--font-blog-heading);
}
```

Note: `.newsprint-prose` body text inherits from `.blog-shell` automatically. Code blocks (`var(--font-code)`) inside `.newsprint-prose` are NOT overridden — they stay JetBrains Mono.

**Step 2: Update .newsprint-nav-next-title for blog context**

After the existing `.newsprint-nav-next-title` rule (around line 672), add:

```css
.blog-shell .newsprint-nav-next-title {
  font-family: var(--font-blog-heading);
}
```

**Step 3: Update persona-switcher for blog context**

After the existing `.persona-switcher-btn` rule (around line 508), add:

```css
.blog-shell .persona-switcher-btn {
  font-family: var(--font-blog-ui);
}
```

**Step 4: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat(blog): scope newsprint-prose and shared selectors for blog fonts"
```

---

### Task 7: Build verification

**Step 1: Run frontend build**

```bash
cd frontend && npm run build
```

Expected: 0 errors from our changes. (Note: `settings.astro` has a pre-existing encoding bug that may cause a build error — that is unrelated.)

**Step 2: Visual spot-check**

```bash
cd frontend && npm run dev
```

Open in browser:
- `http://localhost:4321/en/blog/` — verify IBM Plex Sans on masthead, card titles, tags, sidebar
- `http://localhost:4321/en/blog/[any-slug]` — verify article title, prose headings, body, meta, TOC
- `http://localhost:4321/en/news/` — verify still using Playfair Display / Lora (no IBM Plex Sans)

**Step 3: Commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(blog): typography adjustments from visual review"
```

---

### Task 8: Update CLAUDE.md font documentation

**Files:**
- Modify: `frontend/CLAUDE.md`

**Step 1: Add blog font info to Tailwind v4 section**

In the font role list, add after the `--font-code` line:

```
- `--font-blog-heading`: IBM Plex Sans + IBM Plex Sans KR
- `--font-blog-body`: IBM Plex Sans + IBM Plex Sans KR
- `--font-blog-ui`: IBM Plex Sans + IBM Plex Sans KR
```

**Step 2: Commit**

```bash
git add frontend/CLAUDE.md
git commit -m "docs: add blog font variables to CLAUDE.md"
```

---

## Dependency Graph

```
Task 1 (variables) ──→ Task 3 (blog-shell base)
                   ──→ Task 4 (heading selectors)
                   ──→ Task 5 (UI selectors)
                   ──→ Task 6 (newsprint-prose scoping)
Task 2 (Head.astro) ── independent
Task 7 (build) ──→ after all above
Task 8 (docs) ──→ after Task 7
```

Tasks 2-6 can run in any order after Task 1, but are written sequentially for clarity.
