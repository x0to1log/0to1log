# Article Navigation UX Improvement Design

## Problem

Post detail pages have poor navigation UX:
1. Side rail (More in This Issue, Focus of This Article) disappears when scrolling long articles
2. "Back to Log" link at the top is small, disconnected, and redundant with the global header "Log" link
3. After finishing an article, there's no way to navigate to related content or back to the list without scrolling up

## Solution: Sticky Side Rail + Bottom Article Navigation

### 1. Sticky Side Rail (Desktop)

Apply `position: sticky` to the side rail container so it follows the user while scrolling.

- `top` offset accounts for the sticky header height + padding
- `max-height: calc(100vh - offset)` with `overflow-y: auto` if rail content exceeds viewport
- On mobile, rail flows below content (no sticky effect — intended)

### 2. Bottom Article Navigation

Add a navigation section at the end of the article prose:

```
─── divider ───
[← Back to Log]          [Next article title →]
                          Category · Reading time
```

- **Left**: "Back to Log" / "목록으로 돌아가기" link to `/{locale}/log/`
- **Right**: Next (older) published post in the same locale. If current post is the oldest, show nothing.
- Mobile: vertical stack (list button on top, next post below)

### 3. Remove Top Back Link

Remove `<a class="newsprint-back">` from `NewsprintArticleLayout.astro`. The global header "Log" link provides the same functionality.

## Data Requirements

Each detail page (`en/log/[slug].astro`, `ko/log/[slug].astro`) needs one additional query:

```sql
SELECT title, slug, category
FROM posts
WHERE status = 'published'
  AND locale = :locale
  AND published_at < :current_published_at
ORDER BY published_at DESC
LIMIT 1
```

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/styles/global.css` | Add sticky styles for rail container; add `.newsprint-article-nav` styles |
| `frontend/src/components/newsprint/NewsprintArticleLayout.astro` | Remove top back link; add bottom nav section; add `nextPost` prop |
| `frontend/src/pages/en/log/[slug].astro` | Add next-post query; pass `nextPost` prop |
| `frontend/src/pages/ko/log/[slug].astro` | Same as EN |

## Constraints

- No new dependencies
- Preview pages and admin editor: `nextPost` is optional, so bottom nav shows only the list button
- Newsprint design language maintained (dividers, serif typography, muted colors)

## Related Plans

- [[plans/2026-03-07-article-nav-ux-plan|Article Nav 구현]]
