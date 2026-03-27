# PERF-AUTH-CDN-01: CDN Cache for Logged-in Users

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend CDN caching to logged-in users by separating personalization (bookmark/like status) from the page HTML, loading it client-side after page render.

**Architecture:** Currently logged-in users skip CDN cache because `isBookmarked` and `isLiked` are baked into SSR HTML. The fix: always serve the page with `isBookmarked=false, isLiked=false` defaults, cache it for all users, then hydrate the real state client-side via a lightweight status API. The existing `bookmark.ts` and `likes.ts` scripts already handle toggling — they just need initial state hydration added.

**Tech Stack:** Astro v5, TypeScript, Supabase

---

## Current State

```
Logged-in user request:
→ SSR: fetch post + 8 parallel queries (including bookmark/like check) + markdown render
→ TTFB: ~1600ms
→ HTML includes isBookmarked=true/false, isLiked=true/false from server

Non-logged-in user request:
→ CDN cache hit
→ TTFB: ~9ms
```

**After this change:** Both get CDN cache → TTFB ~9ms for everyone.

---

## Task 1: Remove user-specific queries from SSR data loader

**Files:**
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts`

The `Promise.all` block fetches `bookmarkRes` and `likeRes` using the authenticated Supabase client. Remove these two queries — they'll be handled client-side.

- [ ] **Step 1: Remove bookmark and like queries from Promise.all**

In `newsDetailPage.ts`, the parallel query array has 8 entries. Remove the bookmark check (index 4) and like check (index 5), replacing them with `Promise.resolve({ data: null })`. Also remove the `authSupabase` creation since it's no longer needed for this page.

Keep `isBookmarked = false` and `isLiked = false` as hardcoded defaults (already initialized this way).

- [ ] **Step 2: Commit**

```bash
git commit -m "perf: remove bookmark/like queries from news SSR"
```

---

## Task 2: Enable CDN cache for all users (remove user check)

**Files:**
- Modify: `frontend/src/pages/ko/news/[slug].astro`
- Modify: `frontend/src/pages/en/news/[slug].astro`

- [ ] **Step 1: Remove `!Astro.locals.user` condition from cache header**

```typescript
// BEFORE:
if (post && !previewMode && !Astro.locals.user) {
  Astro.response.headers.set('Cache-Control', 'public, s-maxage=3600, stale-while-revalidate=86400');
}

// AFTER:
if (post && !previewMode) {
  Astro.response.headers.set('Cache-Control', 'public, s-maxage=3600, stale-while-revalidate=86400');
}
```

- [ ] **Step 2: Apply same change to handbook detail pages**

Same change in:
- `frontend/src/pages/ko/handbook/[slug].astro`
- `frontend/src/pages/en/handbook/[slug].astro`

- [ ] **Step 3: Commit**

---

## Task 3: Hydrate bookmark/like state client-side

**Files:**
- Modify: `frontend/src/scripts/bookmark.ts`
- Modify: `frontend/src/scripts/likes.ts`

Add initialization logic: on page load, if user is authenticated, fetch the real bookmark/like status and update the UI.

- [ ] **Step 1: Add hydration to bookmark.ts**

After `initBookmarks()` binds click handlers, add a hydration step:

```typescript
async function hydrateBookmarks(): Promise<void> {
  const buttons = document.querySelectorAll<HTMLButtonElement>('.newsprint-bookmark-icon');
  if (buttons.length === 0) return;

  // Collect all item IDs that need status checks
  const checks: { btn: HTMLButtonElement; itemType: string; itemId: string }[] = [];
  buttons.forEach((btn) => {
    const itemId = btn.dataset.itemId;
    const itemType = btn.dataset.itemType;
    if (itemId && itemType) checks.push({ btn, itemType, itemId });
  });
  if (checks.length === 0) return;

  // Single API call to check bookmark status
  try {
    const res = await fetch('/api/user/bookmarks/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: checks.map(c => ({ item_type: c.itemType, item_id: c.itemId })) }),
    });
    if (!res.ok) return; // Not logged in or error — keep defaults
    const data = await res.json();
    // data.statuses: Record<item_id, boolean>
    for (const { btn, itemId } of checks) {
      const isBookmarked = data.statuses?.[itemId] ?? false;
      btn.dataset.bookmarked = isBookmarked ? 'true' : 'false';
      btn.classList.toggle('newsprint-bookmark-icon--active', isBookmarked);
      const svg = btn.querySelector('svg');
      if (svg) svg.setAttribute('fill', isBookmarked ? 'currentColor' : 'none');
    }
  } catch { /* silent */ }
}
```

Call `hydrateBookmarks()` after `initBookmarks()` in `astro:page-load`.

- [ ] **Step 2: Add hydration to likes.ts**

Similar pattern — after `initLikes()`, hydrate the like button state:

```typescript
async function hydrateLikes(): Promise<void> {
  const btn = document.querySelector<HTMLButtonElement>('[data-like-btn]');
  if (!btn) return;
  const postId = btn.dataset.postId;
  const contentType = btn.dataset.contentType || 'news';
  if (!postId) return;

  try {
    const res = await fetch(`/api/user/likes/status?post_id=${postId}&type=${contentType}`);
    if (!res.ok) return;
    const data = await res.json();
    btn.dataset.liked = data.liked ? 'true' : 'false';
    btn.classList.toggle('newsprint-engage-btn--active', data.liked);
    const svg = btn.querySelector('svg');
    if (svg) svg.setAttribute('fill', data.liked ? 'currentColor' : 'none');
    const countEl = btn.querySelector('[data-like-count]');
    if (countEl && data.count != null) countEl.textContent = String(data.count);
  } catch { /* silent */ }
}
```

- [ ] **Step 3: Commit**

---

## Task 4: Create status API endpoints

**Files:**
- Create: `frontend/src/pages/api/user/bookmarks/status.ts`
- Create: `frontend/src/pages/api/user/likes/status.ts`

- [ ] **Step 1: Create bookmark status endpoint**

POST `/api/user/bookmarks/status` — accepts `{ items: [{ item_type, item_id }] }`, returns `{ statuses: { [item_id]: boolean } }`.

```typescript
// frontend/src/pages/api/user/bookmarks/status.ts
import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ statuses: {} }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const { items } = await request.json();
  if (!Array.isArray(items) || items.length === 0) {
    return new Response(JSON.stringify({ statuses: {} }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${locals.accessToken}` } } },
  );

  const itemIds = items.map((i: any) => i.item_id);
  const { data } = await supabase
    .from('user_bookmarks')
    .select('item_id')
    .eq('user_id', locals.user.id)
    .in('item_id', itemIds);

  const statuses: Record<string, boolean> = {};
  for (const item of items) {
    statuses[item.item_id] = (data || []).some(d => d.item_id === item.item_id);
  }

  return new Response(JSON.stringify({ statuses }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
```

- [ ] **Step 2: Create like status endpoint**

GET `/api/user/likes/status?post_id=xxx&type=news` — returns `{ liked: boolean, count: number }`.

```typescript
// frontend/src/pages/api/user/likes/status.ts
import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { supabase as anonSupabase } from '../../../../lib/supabase';

export const prerender = false;

export const GET: APIRoute = async ({ url, locals }) => {
  const postId = url.searchParams.get('post_id');
  const type = url.searchParams.get('type') || 'news';
  if (!postId) {
    return new Response(JSON.stringify({ error: 'Missing post_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const likesTable = type === 'blog' ? 'blog_likes' : 'news_likes';

  // Get count (public)
  const { count } = await anonSupabase
    .from(likesTable)
    .select('id', { count: 'exact', head: true })
    .eq('post_id', postId);

  // Get user's like status
  let liked = false;
  if (locals.user && locals.accessToken) {
    const supabase = createClient(
      import.meta.env.PUBLIC_SUPABASE_URL,
      import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
      { global: { headers: { Authorization: `Bearer ${locals.accessToken}` } } },
    );
    const { data } = await supabase
      .from(likesTable)
      .select('id')
      .eq('user_id', locals.user.id)
      .eq('post_id', postId)
      .maybeSingle();
    liked = !!data;
  }

  return new Response(JSON.stringify({ liked, count: count ?? 0 }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
```

- [ ] **Step 3: Build + commit**

---

## Task 5: Verify & measure

- [ ] **Step 1: Build check**
- [ ] **Step 2: Deploy and measure TTFB for logged-in user**
- [ ] **Step 3: Verify bookmark/like hydration works correctly**
- [ ] **Step 4: Verify admin preview mode still bypasses cache**

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Flash of un-liked/un-bookmarked state (FOUC) | Hydration is fast (~100ms). Icons start neutral, then fill. Subtle and acceptable. |
| Admin buttons in cached HTML | Admin buttons render based on `isAdmin` which is still SSR. Preview mode bypasses cache. |
| User persona preference | SSR reads `locals.profile.persona` for active persona. With CDN cache, all users get the same default. **Decision needed: use default persona in SSR, switch client-side.** |
| Handbook learning progress | Handbook pages have `learningStatus` / `learningProgressId` from SSR. Same pattern applies — hydrate client-side. (Separate task if needed.) |

### ⚠️ Blocker: Admin & Persona

Two items need attention before implementation:

1. **Admin buttons**: `isAdmin` check renders edit/unpublish buttons server-side. If the page is CDN-cached, non-admin users would see admin buttons meant for admins. **Fix:** Admin buttons must be conditionally shown client-side, or admin users must bypass CDN cache.

2. **Persona preference**: CDN-cached page has a fixed `activePersona` (default: learner). Logged-in users with `persona=expert` preference would see learner content first, then the page would need to swap. This is a worse UX than the bookmark FOUC.

**Recommended approach:** Keep `!Astro.locals.user` for admin bypass, but only skip CDN cache for admin users, not all logged-in users:

```typescript
// Skip CDN cache only for admins (who need edit buttons) and preview mode
if (post && !previewMode && !Astro.locals.isAdmin) {
  Astro.response.headers.set('Cache-Control', 'public, s-maxage=3600, stale-while-revalidate=86400');
}
```

This gives CDN cache to **all non-admin logged-in users** while preserving admin functionality.
