# Article Navigation UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve post detail page navigation with a sticky side rail and bottom article navigation, replacing the awkward top "Back to Log" link.

**Architecture:** Make the existing `.newsprint-rail` sticky on desktop via CSS. Add a bottom nav section inside `NewsprintArticleLayout` with a "back to list" link and optional "next post" card. Query the next (older) post from Supabase in the detail page frontmatter.

**Tech Stack:** Astro v5 (SSR pages), Supabase (posts query), CSS (sticky positioning)

---

### Task 1: Make side rail sticky on desktop

**Files:**
- Modify: `frontend/src/styles/global.css` (lines 220-231, the `@media (min-width: 1024px)` block for `.newsprint-rail`)

**Step 1: Add sticky positioning to `.newsprint-rail` in the desktop media query**

In `global.css`, find the existing desktop media query block for `.newsprint-rail` (around line 220):

```css
@media (min-width: 1024px) {
  /* ... existing .newsprint-grid and .newsprint-main rules ... */

  .newsprint-rail {
    border-top: none;
    padding-top: 0;
    padding-left: 1.5rem;
  }
}
```

Add sticky properties to `.newsprint-rail` inside this media query:

```css
  .newsprint-rail {
    border-top: none;
    padding-top: 0;
    padding-left: 1.5rem;
    position: sticky;
    top: 4.5rem;
    align-self: start;
    max-height: calc(100vh - 5rem);
    overflow-y: auto;
  }
```

- `top: 4.5rem` — clears the sticky header (~3.5rem) + breathing room
- `align-self: start` — required for sticky to work inside CSS Grid
- `max-height` + `overflow-y: auto` — scrollable if rail is taller than viewport

**Step 2: Verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds with 0 errors.

Open dev server, navigate to any article detail page, scroll down — side rail should follow.

**Step 3: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat: make side rail sticky on desktop"
```

---

### Task 2: Add bottom nav CSS styles

**Files:**
- Modify: `frontend/src/styles/global.css` (add after `.newsprint-back:hover` block, around line 512)

**Step 1: Add `.newsprint-article-nav` styles**

After the existing `.newsprint-back:hover` rule (line ~512), add:

```css
.newsprint-article-nav {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--color-border);
}

.newsprint-article-nav-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
}

.newsprint-nav-back {
  color: var(--color-accent);
  text-decoration: none;
  font-family: var(--font-ui);
  font-size: 0.9rem;
  white-space: nowrap;
  transition: color 150ms ease;
}

.newsprint-nav-back:hover {
  text-decoration: underline;
}

.newsprint-nav-next {
  text-align: right;
  text-decoration: none;
  color: inherit;
  max-width: 60%;
  transition: color 150ms ease;
}

.newsprint-nav-next:hover .newsprint-nav-next-title {
  color: var(--color-accent);
}

.newsprint-nav-next-title {
  font-family: var(--font-heading);
  font-size: 1rem;
  line-height: 1.3;
  transition: color 150ms ease;
}

.newsprint-nav-next-meta {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 0.25rem;
}

@media (max-width: 640px) {
  .newsprint-article-nav-row {
    flex-direction: column;
    gap: 1rem;
  }

  .newsprint-nav-next {
    text-align: left;
    max-width: 100%;
  }
}
```

**Step 2: Verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat: add bottom article nav CSS styles"
```

---

### Task 3: Update NewsprintArticleLayout component

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro`

**Step 1: Add `nextPost` to Props interface**

In the Props interface (lines 4-16), add optional `nextPost` and `listLabel`:

```typescript
interface Props {
  locale: 'en' | 'ko';
  slug: string;
  showSlug?: boolean;
  title: string;
  excerpt?: string | null;
  category?: string | null;
  publishedAt?: string | null;
  readingTimeMin?: number | null;
  tags?: string[] | null;
  htmlContent: string;
  backLabel: string;
  nextPost?: { title: string; slug: string; category?: string | null } | null;
}
```

**Step 2: Destructure `nextPost` in the component script**

Update the destructuring (lines 18-28) to include `nextPost`:

```typescript
const {
  locale,
  slug,
  showSlug = false,
  title,
  excerpt,
  category,
  publishedAt,
  readingTimeMin,
  tags,
  htmlContent,
  backLabel,
  nextPost = null,
} = Astro.props;
```

Add after `categoryLabel`:

```typescript
const nextCategoryLabel = nextPost?.category ? getCategoryLabel(locale, nextPost.category) : null;
```

**Step 3: Remove the top back link**

Delete lines 43-45:

```html
<a class="newsprint-back" href={`/${locale}/log/`}>
  &larr; {backLabel}
</a>
```

**Step 4: Add bottom navigation after the prose section**

After the closing `</div>` of `.newsprint-prose` (line ~71) and before `</article>`, add:

```astro
  <nav class="newsprint-article-nav" aria-label={locale === 'ko' ? '글 탐색' : 'Article navigation'}>
    <div class="newsprint-article-nav-row">
      <a class="newsprint-nav-back" href={`/${locale}/log/`}>
        &larr; {backLabel}
      </a>
      {nextPost && (
        <a class="newsprint-nav-next" href={`/${locale}/log/${nextPost.slug}/`}>
          <div class="newsprint-nav-next-title">{nextPost.title} &rarr;</div>
          {nextCategoryLabel && (
            <div class="newsprint-nav-next-meta">{nextCategoryLabel}</div>
          )}
        </a>
      )}
    </div>
  </nav>
```

**Step 5: Verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds. Preview pages and admin editor won't pass `nextPost`, so only the back link shows.

**Step 6: Commit**

```bash
git add frontend/src/components/newsprint/NewsprintArticleLayout.astro
git commit -m "feat: replace top back link with bottom article nav"
```

---

### Task 4: Add next-post query to EN detail page

**Files:**
- Modify: `frontend/src/pages/en/log/[slug].astro` (lines 55-73, inside the `if (post)` block)

**Step 1: Add `nextPost` variable and query**

After `let articleData: any = undefined;` (line 53), add:

```typescript
let nextPost: { title: string; slug: string; category: string | null } | null = null;
```

Inside the `if (post)` block, after the `recentPosts` assignment (line 66) and before `focusItems` (line 68), add:

```typescript
  if (supabase && post.published_at) {
    const { data: nextData } = await supabase
      .from('posts')
      .select('title, slug, category')
      .eq('status', 'published')
      .eq('locale', 'en')
      .lt('published_at', post.published_at)
      .order('published_at', { ascending: false })
      .limit(1)
      .single();
    nextPost = nextData;
  }
```

**Step 2: Pass `nextPost` prop to NewsprintArticleLayout**

Find the `<NewsprintArticleLayout` JSX (around line 100-110). Add `nextPost` prop:

```astro
      <NewsprintArticleLayout
        locale="en"
        slug={pageSlug}
        showSlug={false}
        title={post.title}
        category={post.category}
        publishedAt={post.published_at}
        readingTimeMin={post.reading_time_min}
        tags={post.tags}
        htmlContent={htmlContent}
        backLabel={t.en['post.back']}
        nextPost={nextPost}
      />
```

**Step 3: Verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 4: Commit**

```bash
git add frontend/src/pages/en/log/[slug].astro
git commit -m "feat: add next-post query to EN detail page"
```

---

### Task 5: Add next-post query to KO detail page

**Files:**
- Modify: `frontend/src/pages/ko/log/[slug].astro` (same structure as EN)

**Step 1: Add `nextPost` variable and query**

Identical to Task 4 but with `locale: 'ko'`:

After `let articleData: any = undefined;` (line 53), add:

```typescript
let nextPost: { title: string; slug: string; category: string | null } | null = null;
```

Inside `if (post)`, after `recentPosts` assignment, add:

```typescript
  if (supabase && post.published_at) {
    const { data: nextData } = await supabase
      .from('posts')
      .select('title, slug, category')
      .eq('status', 'published')
      .eq('locale', 'ko')
      .lt('published_at', post.published_at)
      .order('published_at', { ascending: false })
      .limit(1)
      .single();
    nextPost = nextData;
  }
```

**Step 2: Pass `nextPost` prop**

```astro
      <NewsprintArticleLayout
        locale="ko"
        slug={pageSlug}
        showSlug={false}
        title={post.title}
        category={post.category}
        publishedAt={post.published_at}
        readingTimeMin={post.reading_time_min}
        tags={post.tags}
        htmlContent={htmlContent}
        backLabel={t.ko['post.back']}
        nextPost={nextPost}
      />
```

**Step 3: Verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 4: Commit**

```bash
git add frontend/src/pages/ko/log/[slug].astro
git commit -m "feat: add next-post query to KO detail page"
```

---

### Task 6: Remove unused `.newsprint-back` CSS

**Files:**
- Modify: `frontend/src/styles/global.css` (lines ~502-512)

**Step 1: Delete the `.newsprint-back` styles**

Remove:

```css
.newsprint-back {
  display: inline-block;
  color: var(--color-accent);
  text-decoration: none;
  margin-bottom: 0.85rem;
  transition: color 150ms ease;
}

.newsprint-back:hover {
  text-decoration: underline;
}
```

**Step 2: Verify no other file uses `.newsprint-back`**

Run: `grep -r "newsprint-back" frontend/src/`
Expected: No results (the class was only used in NewsprintArticleLayout which was updated in Task 3).

**Step 3: Build verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 4: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "chore: remove unused .newsprint-back CSS"
```

---

## Verification (End-to-End)

1. `cd frontend && npm run build` — 0 errors
2. Dev server: Open any article detail page at `/en/log/[slug]/`
3. **Sticky rail**: Scroll down a long article — side rail should follow on desktop (1024px+)
4. **Bottom nav**: At the end of the article, "← Back to Log" link on the left, next post card on the right
5. **No next post**: If it's the oldest post, only the back link shows
6. **Mobile (375px)**: Bottom nav stacks vertically; side rail appears below content (not sticky)
7. **Top back link gone**: No more "← Back to Log" above the article title
8. **Preview pages**: Bottom nav shows only "← Back to Log" (no `nextPost` passed)
9. **Global header "Log" link**: Still works as alternative navigation
