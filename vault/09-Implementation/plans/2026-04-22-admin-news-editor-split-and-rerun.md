---
date: 2026-04-22
topic: Admin news editor — isolate from legacy posts + inline quality rerun
status: active
owner: Amy
related:
  - frontend/src/pages/admin/edit/[slug].astro
  - frontend/src/pages/admin/posts/index.astro
  - frontend/src/components/admin/QualityPanel.astro
  - backend/services/pipeline.py (rerun_pipeline_stage)
---

# Admin Editor Split (blog / news) + Inline Quality Rerun

> **For agentic workers:** Execute with superpowers:subagent-driven-development (if available) or superpowers:executing-plans. Steps use `- [ ]` checkboxes for tracking.

**Goal:** (1) Clean up the admin editor routing so the news editor has a news-specific URL and the legacy "Posts" index is removed; (2) add a "Save & re-run quality" button inside the news editor so Amy can iterate on digest content without leaving the page.

**Architecture:**
- **Part 1 (refactor, standalone commit):** Move `/admin/edit/[slug].astro` to `/admin/news/edit/[slug].astro`. Delete the legacy `/admin/posts/*` tree (duplicates `/admin/news/`). Re-point internal links. "New Post" labels pointing at the news editor either become blog-targeted or are removed (news is pipeline-generated, not manually created).
- **Part 2 (feature, second commit):** Inside the news editor, add a button that saves the Milkdown content, triggers `/api/admin/pipeline-rerun` with `from_stage=quality`, polls `updated_at` via a tiny status endpoint, and reloads on completion. No backend change needed — `_load_personas_and_frontload_from_db` at [pipeline.py:1626-1633](backend/services/pipeline.py#L1626-L1633) already reads content from the DB rows the save path just wrote.

**Tech stack:** Astro v5 (SSR editor page + API proxies), Tailwind v4 (theme-aware via CSS vars), FastAPI (existing `/api/cron/pipeline-rerun` + admin proxy at `/api/admin/pipeline-rerun.ts`).

**Not in scope:**
- `auto_publish_eligible` refresh on quality rerun — user chose to leave this alone. Morning promote cron handles publishing.
- Backend changes — rerun flow already supports reading content from DB.
- Blog editor (already at `/admin/blog/edit/` — untouched).

---

## File Structure

**Moved/renamed:**
- `frontend/src/pages/admin/edit/[slug].astro` → `frontend/src/pages/admin/news/edit/[slug].astro`

**Deleted:**
- `frontend/src/pages/admin/posts/index.astro` (duplicate of `/admin/news/index.astro`)

**Modified (link updates):**
- `frontend/src/pages/admin/index.astro` — dashboard
- `frontend/src/pages/admin/news/index.astro` — news list
- `frontend/src/pages/admin/analytics.astro` — recent news linkbacks
- `frontend/src/pages/admin/feedback/index.astro` — "news" case of slug resolver
- `frontend/src/components/admin/AdminToolbar.astro` — edit link resolver
- `frontend/src/components/admin/AdminSidebar.astro` — recent items + activeSection matchers

**Modified (Part 2):**
- `frontend/src/pages/admin/news/edit/[slug].astro` — add server-side batch/run lookup, data attributes, rerun button, inline script
- `frontend/src/components/admin/QualityPanel.astro` — no change (stays reusable)

**Created (Part 2):**
- `frontend/src/pages/api/admin/posts/quality-status.ts` — lightweight polling endpoint that returns `{updated_at, quality_score}` for one slug

---

## Chunk 1: Part 1 — Routing cleanup (single commit)

### Task 1.1: Move news editor file

**Files:**
- Move: `frontend/src/pages/admin/edit/[slug].astro` → `frontend/src/pages/admin/news/edit/[slug].astro`

**Steps:**

- [ ] **1.1.1** Move the file with `git mv` (preserves history):
  ```bash
  git mv frontend/src/pages/admin/edit/[slug].astro frontend/src/pages/admin/news/edit/[slug].astro
  ```

- [ ] **1.1.2** Update the internal `editorPath` constant inside the file (currently `/admin/edit/`):
  - Find: `editorPath: '/admin/edit/',`
  - Replace: `editorPath: '/admin/news/edit/',`

- [ ] **1.1.3** Update the post-create redirect inside the same file:
  - Find: `window.location.href = \`/admin/edit/${saved.slug}\`;`
  - Replace: `window.location.href = \`/admin/news/edit/${saved.slug}\`;`

- [ ] **1.1.4** "Back" links (`<a href="/admin/news/">`) already point to the right place — no change to href.

- [ ] **1.1.5** Update the sidebar section marker — legacy `"posts"` label:
  - Find (2 occurrences — one per render branch): `<AdminSidebar activeSection="posts" />`
  - Replace: `<AdminSidebar activeSection="news" />`
  - Rationale: Task 1.4.3 drops the `|| activeSection === 'posts'` fallback from the sidebar matcher, so the page MUST declare itself as `'news'` (the remaining canonical value) to keep the Paper tab highlighted. Without this, the sidebar highlight breaks after 1.4.3 lands.

- [ ] **1.1.6** Verify the file's `<MainLayout title>` still reads sensibly. Currently: `{isNew ? 'New Post' : (post ? \`Edit: ${post.title}\` : 'Editor')}`. Since news isn't manually created (see 1.3), `isNew` will effectively be dead-code here, but leave it — guard added later.

### Task 1.2: Update external links to the news editor

**Files:**
- `frontend/src/pages/admin/index.astro`
- `frontend/src/pages/admin/news/index.astro`
- `frontend/src/pages/admin/analytics.astro`
- `frontend/src/pages/admin/feedback/index.astro`
- `frontend/src/components/admin/AdminToolbar.astro`
- `frontend/src/components/admin/AdminSidebar.astro`

**Steps:**

- [ ] **1.2.1** In each file above, replace every `/admin/edit/` occurrence with `/admin/news/edit/`.
  - Use grep first to list hits:
    ```bash
    grep -rn "/admin/edit/" frontend/src
    ```
  - Per-file counts (from audit — confirm with grep):
    - `admin/index.astro` — 3 refs (lines ~558, 590, dashboard card)
    - `admin/news/index.astro` — 3 refs (lines ~132, 226, 244-245)
    - `admin/analytics.astro` — 2 refs (lines ~392, 632)
    - `admin/feedback/index.astro` — 1 ref (line ~98 — the `'news'` case)
    - `components/admin/AdminToolbar.astro` — 1 ref (line ~8 — the `type === 'post'` branch)
    - `components/admin/AdminSidebar.astro` — 1 ref (line ~125 — recent items, `type === 'post'` branch)

- [ ] **1.2.2** Grep audit after all edits:
  ```bash
  grep -rn "/admin/edit/" frontend/src
  ```
  Expected: 0 results (except possibly within string literals in comments — if present, leave).

### Task 1.3: Fix "New Post" buttons that incorrectly target news editor

Three locations have `<a href="/admin/edit/new">New Post</a>`. News is pipeline-generated — manual creation doesn't make sense. Fix per-location:

**Files:**
- `frontend/src/pages/admin/index.astro` (dashboard, line ~298)
- `frontend/src/pages/admin/news/index.astro` (line ~132)

**Steps:**

- [ ] **1.3.1** Dashboard `admin/index.astro` line ~298 — keep label, repoint href:
  - Find: `<a href="/admin/edit/new" class="admin-btn">New Post</a>`
  - Replace: `<a href="/admin/blog/edit/new" class="admin-btn">New Post</a>`
  - Rationale: Dashboard's "New Post" CTA now creates a blog post (the only manually-authored type). Label stays "New Post" per user preference.

- [ ] **1.3.2** News list `admin/news/index.astro` line ~132 — remove the button entirely:
  - Find the `<a href="/admin/edit/new" class="admin-btn admin-btn-primary">New Post</a>` element
  - Delete it (including its container `<div>` or flex-wrapper if the button was the only child — verify visually).
  - Rationale: News isn't manually created. An empty news index means "no news run yet today" — not "click here to make one".

- [ ] **1.3.3** Guard `isNew` in the moved news editor file (`admin/news/edit/[slug].astro`):
  - After the `const isNew = pageSlug === 'new';` line, add an early-exit:
    ```astro
    if (isNew) {
      return Astro.redirect('/admin/news/');
    }
    ```
  - Rationale: `/admin/news/edit/new` should never be reachable via UI after 1.3.1/1.3.2, but a stale bookmark or typed URL should bounce cleanly rather than render a broken form.

### Task 1.4: Delete legacy `/admin/posts/` index

**Files:**
- Delete: `frontend/src/pages/admin/posts/index.astro`

**Steps:**

- [ ] **1.4.1** Confirm nothing non-trivial references it beyond sidebar active-state matching:
  ```bash
  grep -rn "admin/posts" frontend/src --include="*.astro" --include="*.ts" | grep -v "api/admin/posts"
  ```
  The `/api/admin/posts/*` endpoints are the shared CRUD API for `news_posts` table — those STAY. Only the UI page is legacy.
  Expected non-api hits: `components/admin/AdminSidebar.astro` has `activeSection === 'posts'` — this is a UI marker string, see 1.4.3.

- [ ] **1.4.2** Delete the file:
  ```bash
  git rm frontend/src/pages/admin/posts/index.astro
  ```

- [ ] **1.4.3** In `AdminSidebar.astro`, drop the `|| activeSection === 'posts'` clause from the News link's active-state matcher (line ~72). The section string is a relic of the old name.

- [ ] **1.4.4** Grep once more for any remaining `admin/posts/` URL paths:
  ```bash
  grep -rn "admin/posts/\"" frontend/src
  grep -rn "admin/posts/$" frontend/src
  ```
  Expected: 0.

### Task 1.5: Relabel user-facing "News" → "Paper"

Route URLs (`/admin/news/*`) and API paths (`/api/admin/posts/*`) stay — they're technical paths matching the `news_posts` table. Only user-visible text changes.

**Files:**
- `frontend/src/components/admin/AdminSidebar.astro`
- `frontend/src/pages/admin/news/index.astro`
- `frontend/src/pages/admin/news/edit/[slug].astro` (moved in Task 1.1)
- Possibly `frontend/src/pages/admin/index.astro` (dashboard section heading, if any uses "News")

**Steps:**

- [ ] **1.5.1** `AdminSidebar.astro` line ~76 — sidebar menu label:
  - Find: `<span>News</span>`
  - Replace: `<span>Paper</span>`

- [ ] **1.5.2** `admin/news/index.astro` — page heading / title:
  - Grep the file for `News` as user-visible text (H1, title attribute, breadcrumbs). Replace each with `Paper` where context is "the news section" rather than generic word.
  - Skip variable names, comments, data labels like `"draft"/"published"` counts, internal code strings. Only change render-to-DOM text.

- [ ] **1.5.3** `admin/news/edit/[slug].astro` — back link text:
  - Find: `<a href="/admin/news/" class="admin-editor-back">&larr; Back</a>` (2 occurrences per Task 1.1 inventory)
  - Replace: `<a href="/admin/news/" class="admin-editor-back">&larr; Paper</a>`
  - Also the `<MainLayout title>` wrapper if it reads "News" — adjust to "Paper" where applicable.

- [ ] **1.5.4** Grep sweep for any remaining user-visible `>News<` tokens:
  ```bash
  grep -rn ">News<\|'News'\|\"News\"" frontend/src/pages/admin frontend/src/components/admin
  ```
  Each hit: decide case-by-case whether it's user-visible text (→ change) or internal key (→ leave).

### Task 1.6: Verify

- [ ] **1.6.1** Build:
  ```bash
  cd frontend && npm run build
  ```
  Expected: exit 0. Any broken imports or missing routes surface here.

- [ ] **1.6.2** Dev server smoke:
  ```bash
  cd frontend && npm run dev
  ```
  Visit in browser:
  - `http://localhost:4321/admin/news/` — loads, sidebar label says **Paper**, "Edit" buttons on existing digests point to `/admin/news/edit/<slug>`, no "New Post" button
  - `http://localhost:4321/admin/news/edit/2026-04-22-research-digest` — editor loads, QualityPanel renders, back link reads "← Paper"
  - `http://localhost:4321/admin/` — dashboard loads, "New Post" button links to `/admin/blog/edit/new` (creates a blog post)
  - `http://localhost:4321/admin/edit/2026-04-22-research-digest` — expected **404** (old route removed)
  - `http://localhost:4321/admin/posts/` — expected **404** (legacy page removed)

- [ ] **1.6.3** Commit Part 1:
  ```bash
  git add frontend/src/pages/admin/news/edit/[slug].astro \
          frontend/src/pages/admin/index.astro \
          frontend/src/pages/admin/news/index.astro \
          frontend/src/pages/admin/analytics.astro \
          frontend/src/pages/admin/feedback/index.astro \
          frontend/src/components/admin/AdminToolbar.astro \
          frontend/src/components/admin/AdminSidebar.astro
  git rm frontend/src/pages/admin/edit/[slug].astro frontend/src/pages/admin/posts/index.astro
  git commit -m "refactor(admin): split news editor from legacy posts, relabel as Paper

  Move /admin/edit/[slug] → /admin/news/edit/[slug] so the news editor has a
  news-specific URL (blog already lives at /admin/blog/edit/, handbook at
  /admin/handbook/edit/). Delete the orphaned /admin/posts/ index (duplicated
  /admin/news/ via the same news_posts table). Re-point the dashboard 'New
  Post' CTA to /admin/blog/edit/new (the only manually-authored type); the
  news list drops its misleading 'New Post' button (news is pipeline-generated).
  Guard /admin/news/edit/new with a redirect for stale bookmarks.

  Rename user-visible 'News' labels to 'Paper' in the sidebar, list page,
  and editor back-link. Route URLs and API paths stay /admin/news/* to match
  the news_posts table."
  ```

---

## Chunk 2: Part 2 — Inline quality rerun (single commit)

### Task 2.1: Server-side lookup — batch_id, digest_type, run_id

**Files:**
- Modify: `frontend/src/pages/admin/news/edit/[slug].astro` (the file moved in Task 1.1)

**Steps:**

- [ ] **2.1.1** After the existing `post` fetch block (around line ~57), add a block that decides whether this slug is a daily digest and, if so, looks up the run_id:

  ```astro
  // Detect daily-digest slug pattern: YYYY-MM-DD-(research|business)-digest(-ko)?
  // Weekly recap + other post types don't match → rerun button hidden.
  const digestMatch = pageSlug.match(/^(\d{4}-\d{2}-\d{2})-(research|business)-digest(?:-ko)?$/);
  const digestBatchId = digestMatch ? digestMatch[1] : null;
  const digestType = digestMatch ? digestMatch[2] : null;

  let digestRunId: string | null = null;
  if (digestBatchId) {
    try {
      const sbAdmin = createClient(
        import.meta.env.PUBLIC_SUPABASE_URL,
        import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
        { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
      );
      const { data: runRow } = await sbAdmin
        .from('pipeline_runs')
        .select('id')
        .eq('run_key', `news-${digestBatchId}`)
        .single();
      digestRunId = runRow?.id ?? null;
    } catch {
      digestRunId = null;
    }
  }

  const canRerunQuality = !!(digestBatchId && digestType && digestRunId);
  ```

  Rationale: Only dailies get the button. If the pipeline_runs row is missing (unusual), hide the button gracefully rather than error.

### Task 2.2: Status polling API endpoint

**Files:**
- Create: `frontend/src/pages/api/admin/posts/quality-status.ts`

**Steps:**

- [ ] **2.2.1** Write the file:

  ```typescript
  import type { APIRoute } from 'astro';
  import { createClient } from '@supabase/supabase-js';

  export const prerender = false;

  // Lightweight polling endpoint for the news editor's "re-run quality" flow.
  // Client polls every 5s until updated_at crosses the trigger threshold.
  export const GET: APIRoute = async ({ url, locals }) => {
    const accessToken = locals.accessToken;
    if (!accessToken || !locals.isAdmin) {
      return new Response(JSON.stringify({ error: 'Forbidden' }), {
        status: 403, headers: { 'Content-Type': 'application/json' },
      });
    }

    const slug = url.searchParams.get('slug');
    if (!slug) {
      return new Response(JSON.stringify({ error: 'Missing slug' }), {
        status: 400, headers: { 'Content-Type': 'application/json' },
      });
    }

    const sb = createClient(
      import.meta.env.PUBLIC_SUPABASE_URL,
      import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
      { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
    );
    const { data, error } = await sb
      .from('news_posts')
      .select('slug,updated_at,quality_score')
      .eq('slug', slug)
      .single();

    if (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 404, headers: { 'Content-Type': 'application/json' },
      });
    }
    return new Response(JSON.stringify(data), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  };
  ```

### Task 2.3: Rerun button markup + data attributes

**Files:**
- Modify: `frontend/src/pages/admin/news/edit/[slug].astro`

**Steps:**

- [ ] **2.3.1** Find the existing QualityPanel block at line ~220:
  ```astro
  {!isNew && post && (
    <div class="mb-6">
      <QualityPanel factPack={post.fact_pack} />
    </div>
  )}
  ```

  Replace with:

  ```astro
  {!isNew && post && (
    <div class="mb-6">
      <QualityPanel factPack={post.fact_pack} />
      {canRerunQuality && (
        <div class="admin-quality-rerun-row">
          <button
            id="btn-rerun-quality"
            type="button"
            class="admin-btn"
            data-slug={pageSlug}
            data-run-id={digestRunId}
            data-batch-id={digestBatchId}
            data-digest-type={digestType}
          >
            ⟳ Save & re-run quality
          </button>
          <span id="rerun-quality-status" class="admin-quality-rerun-status"></span>
        </div>
      )}
    </div>
  )}
  ```

  Notes:
  - Data attributes carry all params the script needs. No access-token exposure (per CLAUDE.md rule).
  - `data-run-id` / `data-batch-id` are not secrets — they're already visible in the URL when the admin navigates to a pipeline run.

- [ ] **2.3.2** Add the small CSS rule to `frontend/src/styles/global.css` (near the other `.admin-quality-*` classes added in the Apr 22 theme commit):

  ```css
  .admin-quality-rerun-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: 0.75rem;
  }

  .admin-quality-rerun-status {
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }
  .admin-quality-rerun-status--running {
    color: var(--color-warning);
  }
  .admin-quality-rerun-status--done {
    color: var(--color-success);
  }
  .admin-quality-rerun-status--error {
    color: var(--color-error);
  }
  ```

### Task 2.4: Client script — save, trigger, poll, reload

**Files:**
- Modify: `frontend/src/pages/admin/news/edit/[slug].astro` (inside the existing `<script>` block or a new one — keep within the same file for context)

**Steps:**

- [ ] **2.4.1** Locate the existing inline script (around line ~372 where `btnSave` etc. are grabbed). At the bottom of that script, after the existing `btnSave?.addEventListener(...)` handler, append:

  ```typescript
  const btnRerun = document.getElementById('btn-rerun-quality') as HTMLButtonElement | null;
  const rerunStatus = document.getElementById('rerun-quality-status');

  function setRerunStatus(text: string, kind: 'idle' | 'running' | 'done' | 'error') {
    if (!rerunStatus) return;
    rerunStatus.textContent = text;
    rerunStatus.className = 'admin-quality-rerun-status' +
      (kind !== 'idle' ? ` admin-quality-rerun-status--${kind}` : '');
  }

  btnRerun?.addEventListener('click', async () => {
    const slug = btnRerun.dataset.slug || '';
    const runId = btnRerun.dataset.runId || '';
    const batchId = btnRerun.dataset.batchId || '';

    if (!slug || !runId || !batchId) {
      setRerunStatus('Missing run metadata — try refresh', 'error');
      return;
    }

    btnManager.begin(btnRerun, 'Saving…');
    setRerunStatus('Saving content…', 'running');

    // Step 1: save current editor content so the rerun reads the latest version
    const saved = await handleSave({ showFeedback: false, redirectOnCreate: false });
    if (!saved) {
      btnManager.end(btnRerun);
      setRerunStatus('Save failed — see toast', 'error');
      return;
    }

    // Step 2: record the pre-rerun timestamp so we know when polling should stop
    let preUpdatedAt: string | null = null;
    try {
      const pre = await fetch(`/api/admin/posts/quality-status?slug=${encodeURIComponent(slug)}`);
      if (pre.ok) {
        preUpdatedAt = (await pre.json()).updated_at || null;
      }
    } catch { /* best effort */ }

    btnManager.progress(btnRerun, 'Running quality…');
    setRerunStatus('Quality rerun started (30–90s)…', 'running');

    // Step 3: trigger the rerun
    try {
      const res = await fetch('/api/admin/pipeline-rerun', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: runId,
          from_stage: 'quality',
          batch_id: batchId,
          // category intentionally null → rerun both research + business.
          // Leaving null matches the admin pipeline-runs dropdown default.
        }),
      });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err.slice(0, 120));
      }
    } catch (err) {
      btnManager.end(btnRerun);
      setRerunStatus(`Rerun trigger failed: ${err instanceof Error ? err.message : 'unknown'}`, 'error');
      return;
    }

    // Step 4: poll updated_at every 5s, max 24 attempts (2 minutes)
    for (let attempt = 1; attempt <= 24; attempt += 1) {
      await new Promise((r) => setTimeout(r, 5000));
      try {
        const res = await fetch(`/api/admin/posts/quality-status?slug=${encodeURIComponent(slug)}`);
        if (!res.ok) continue;
        const data = await res.json();
        if (data.updated_at && data.updated_at !== preUpdatedAt) {
          setRerunStatus(`Done — new score ${data.quality_score}. Reloading…`, 'done');
          setTimeout(() => window.location.reload(), 800);
          return;
        }
      } catch { /* keep polling */ }
    }

    btnManager.end(btnRerun);
    setRerunStatus('Timed out — check pipeline runs page', 'error');
  });
  ```

  Note: assumes `btnManager` is the existing helper that handles button loading state ([edit/[slug].astro:394](frontend/src/pages/admin/edit/[slug].astro#L394) in the pre-move copy). Verify its methods are `begin`, `progress`, `end` — adjust if different.

- [ ] **2.4.2** Confirm the script block has `nonce={Astro.locals.cspNonce || ''}` (CLAUDE.md requirement). If the script is appended to an existing nonce'd block, inherits the nonce; no change needed.

### Task 2.5: Verify end-to-end

- [ ] **2.5.1** Build:
  ```bash
  cd frontend && npm run build
  ```
  Expected: exit 0.

- [ ] **2.5.2** Dev server manual test:
  - Visit `/admin/news/edit/2026-04-22-research-digest`
  - Confirm button "⟳ Save & re-run quality" appears below QualityPanel
  - Click button with no edit → expect save + rerun + score refresh via reload within ~60-90s
  - Edit a trivial thing (add a space to KO body), click button → same flow
  - Visit `/admin/news/edit/2026-04-20-weekly-recap` (or equivalent non-digest slug) → button should NOT appear (pattern doesn't match)

- [ ] **2.5.3** Theme sanity (since Apr 22 QualityPanel commit just went in): switch theme via admin header toggle — panel + new button + status text all reflect theme colors (no hardcoded white/gray).

- [ ] **2.5.4** Commit Part 2:
  ```bash
  git add frontend/src/pages/admin/news/edit/[slug].astro \
          frontend/src/pages/api/admin/posts/quality-status.ts \
          frontend/src/styles/global.css
  git commit -m "feat(admin): inline 'Save & re-run quality' button in news editor

  Add a button inside the news editor that saves the current Milkdown content,
  triggers rerun_from=quality via /api/admin/pipeline-rerun, polls updated_at
  via a new /api/admin/posts/quality-status endpoint, and reloads on completion.
  Button only renders for daily-digest slugs (pattern
  YYYY-MM-DD-(research|business)-digest[-ko]), keeping weekly recap and other
  post types out of scope.

  No backend change — rerun_from=quality already reads content from news_posts
  at pipeline.py:1626-1633, so the save-then-trigger ordering picks up fresh
  edits naturally."
  ```

---

## Rollback strategy

- **Part 1:** single commit → `git revert <sha>` restores the old routing. Tests should catch any integration break before commit.
- **Part 2:** single commit, independent from Part 1 → revertable on its own. The only cross-commit dependency is the file location (`/admin/news/edit/[slug].astro`) — if Part 2 is reverted but Part 1 stays, the editor remains functional, just without the rerun button.

## Risks / watch-outs

1. **`btnManager` API surface:** Plan assumes `begin/progress/end`. Pre-move file might expose only `begin/end`. Read the helper first; adjust the script to whatever's there.
2. **Polling after background task failure:** If the rerun background task dies (as happened Apr 21/22), `updated_at` never moves → polling times out at 2 min → user sees "Timed out — check pipeline runs page". That's honest behavior.
3. **CSP nonce:** Inline script must inherit the existing block's nonce. If added as a new `<script is:inline>`, must include `nonce={Astro.locals.cspNonce || ''}`.
4. **Grep-miss on link updates:** Task 1.2.2 grep audit is the safety net. If something slipped through, dev server 404s catch it.
5. **`/admin/news/edit/new` route:** Guarded via redirect in Task 1.3.3 — stale bookmarks bounce to `/admin/news/`.

## Open questions (non-blocking)

- Weekly recap editor: currently uses `/admin/edit/[slug]` too? Worth checking — weekly slugs look like `weekly-YYYY-MM-DD-recap`. If they're also served by this editor, the regex guard simply hides the rerun button (weekly doesn't match the digest pattern), so weekly editing keeps working, just without the button. Weekly has its own rerun chain anyway.
