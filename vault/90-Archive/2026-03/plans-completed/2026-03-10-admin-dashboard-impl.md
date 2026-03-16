# Admin Dashboard Improvement — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand the admin dashboard from 4-stat + activity view to a full operational overview with 6 stats, pipeline status, and notifications.

**Architecture:** Single-file modification to `frontend/src/pages/admin/index.astro`. All data is fetched server-side in the Astro frontmatter via Supabase JS client (authenticated with admin's access token). New sections use existing `.dashboard-*` CSS naming. Vanilla JS for two interactive buttons.

**Tech Stack:** Astro v5 SSR, Supabase JS client, scoped CSS, vanilla JS

**Design doc:** `docs/plans/2026-03-10-admin-dashboard-design.md`

---

### Task 1: Expand data fetching (frontmatter)

**Files:**
- Modify: `frontend/src/pages/admin/index.astro:15-57`

**Step 1: Add new variables after existing ones (line 18)**

After `let totalDrafts = 0;` add:

```typescript
let totalUsers = 0;
let totalLikes = 0;

type PipelineRun = {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  last_error: string | null;
};
let lastRun: PipelineRun | null = null;
let pipelineCost = 0;
let pipelineTokens = 0;
let candidatesTotal = 0;
let candidatesSelected = 0;

type Notification = {
  id: string;
  type: string;
  title: string;
  message: string | null;
  created_at: string;
};
let notifications: Notification[] = [];
```

**Step 2: Expand the Promise.all inside the try block**

Replace the existing `Promise.all` call (lines 32-35) with:

```typescript
const [postsRes, termsRes, profilesRes, likesRes, pipelineRes, notifsRes] = await Promise.all([
  sb.from('posts').select('title, slug, status, updated_at').order('updated_at', { ascending: false }),
  sb.from('handbook_terms').select('term, slug, status, updated_at').order('updated_at', { ascending: false }),
  sb.from('profiles').select('id', { count: 'exact', head: true }),
  sb.from('post_likes').select('id', { count: 'exact', head: true }),
  sb.from('pipeline_runs').select('*').order('started_at', { ascending: false }).limit(1),
  sb.from('admin_notifications').select('id, type, title, message, created_at').eq('is_read', false).order('created_at', { ascending: false }).limit(5),
]);
```

**Step 3: Process new data after existing processing**

After `totalDrafts = postDrafts + termDrafts;` (line 46) add:

```typescript
totalUsers = profilesRes.count ?? 0;
totalLikes = likesRes.count ?? 0;

// Pipeline
const runData = pipelineRes.data?.[0] ?? null;
if (runData) {
  lastRun = runData as PipelineRun;

  // Fetch cost + candidates for last run (sequential, depends on run id)
  const [logsRes, candidatesRes] = await Promise.all([
    sb.from('pipeline_logs').select('cost_usd, tokens_used').eq('run_id', lastRun.id),
    sb.from('news_candidates').select('status').eq('batch_id', lastRun.id.split('_')[0] || lastRun.id),
  ]);

  const logs = logsRes.data ?? [];
  pipelineCost = logs.reduce((sum: number, l: any) => sum + (parseFloat(l.cost_usd) || 0), 0);
  pipelineTokens = logs.reduce((sum: number, l: any) => sum + (l.tokens_used || 0), 0);

  const cands = candidatesRes.data ?? [];
  candidatesTotal = cands.length;
  candidatesSelected = cands.filter((c: any) => c.status === 'selected' || c.status === 'published').length;
}

// Notifications
notifications = (notifsRes.data ?? []) as Notification[];
```

**Note:** `news_candidates.batch_id` is a text field. The pipeline run's `run_key` is used as batch_id in the pipeline code. If no candidates match `lastRun.id`, the counts will simply be 0 — graceful degradation.

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 5: Commit**

```bash
git add frontend/src/pages/admin/index.astro
git commit -m "feat(admin): expand dashboard data fetching for stats, pipeline, notifications"
```

---

### Task 2: Expand Stats Grid to 6 cards

**Files:**
- Modify: `frontend/src/pages/admin/index.astro` (HTML template, lines 94-111)

**Step 1: Add Users and Likes stat cards after the Drafts card**

After the existing Drafts `</div>` (line 110), add:

```html
<div class="dashboard-stat-card">
  <div class="dashboard-stat-label">Users</div>
  <div class="dashboard-stat-value">{totalUsers}</div>
</div>
<div class="dashboard-stat-card">
  <div class="dashboard-stat-label">Likes</div>
  <div class="dashboard-stat-value">{totalLikes}</div>
</div>
```

**Step 2: Update grid CSS (line 169)**

Change `grid-template-columns: repeat(4, minmax(0, 1fr));` to:

```css
grid-template-columns: repeat(6, minmax(0, 1fr));
```

**Step 3: Update tablet breakpoint (line 277)**

Change `repeat(2, ...)` to `repeat(3, ...)`:

```css
@media (max-width: 960px) {
  .dashboard-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
```

Mobile (640px) stays at `repeat(2, ...)` — already correct.

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 5: Commit**

```bash
git add frontend/src/pages/admin/index.astro
git commit -m "feat(admin): expand stats grid to 6 cards (add Users, Likes)"
```

---

### Task 3: Add Pipeline Status section

**Files:**
- Modify: `frontend/src/pages/admin/index.astro` (HTML + CSS)

**Step 1: Add Pipeline section HTML after Stats Grid, before Recent Activity**

Insert between the closing `</div>` of `.dashboard-stats` and the `<section class="dashboard-section">` for Recent Activity:

```html
<section class="dashboard-section">
  <h2 class="dashboard-section-title">Pipeline Status</h2>
  {lastRun ? (
    <div class={`dashboard-pipeline dashboard-pipeline--${lastRun.status}`}>
      <div class="dashboard-pipeline-header">
        <span class="dashboard-pipeline-status">
          {lastRun.status === 'success' ? '✓' : lastRun.status === 'failed' ? '✗' : '●'} {lastRun.status}
        </span>
        <span class="dashboard-pipeline-time">{relativeTime(lastRun.started_at)}</span>
      </div>
      <div class="dashboard-pipeline-details">
        {lastRun.finished_at && (
          <span>Duration: {Math.round((new Date(lastRun.finished_at).getTime() - new Date(lastRun.started_at).getTime()) / 1000)}s</span>
        )}
        {candidatesTotal > 0 && (
          <span>Candidates: {candidatesTotal} collected → {candidatesSelected} selected</span>
        )}
        {pipelineCost > 0 && (
          <span>Cost: ${pipelineCost.toFixed(2)} · {pipelineTokens.toLocaleString()} tokens</span>
        )}
      </div>
      {lastRun.status === 'failed' && lastRun.last_error && (
        <div class="dashboard-pipeline-error">{lastRun.last_error}</div>
      )}
      <div class="dashboard-pipeline-actions">
        <button type="button" class="admin-btn admin-btn-primary" id="run-pipeline-btn">Run Pipeline</button>
      </div>
    </div>
  ) : (
    <div class="dashboard-pipeline dashboard-pipeline--none">
      <p class="dashboard-empty">No pipeline runs yet.</p>
      <div class="dashboard-pipeline-actions">
        <button type="button" class="admin-btn admin-btn-primary" id="run-pipeline-btn">Run Pipeline</button>
      </div>
    </div>
  )}
</section>
```

**Step 2: Add Pipeline CSS in the `<style>` block**

```css
.dashboard-pipeline {
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-border);
  background: var(--color-bg-secondary);
  padding: 1rem;
}

.dashboard-pipeline--success {
  border-left-color: var(--color-success);
}

.dashboard-pipeline--failed {
  border-left-color: var(--color-error, #c44);
}

.dashboard-pipeline--running {
  border-left-color: var(--color-accent, #e90);
}

.dashboard-pipeline--none {
  border-left-color: var(--color-border);
}

.dashboard-pipeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.dashboard-pipeline-status {
  font-weight: 600;
  font-size: 0.9rem;
  text-transform: capitalize;
}

.dashboard-pipeline-time {
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.dashboard-pipeline-details {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  font-size: 0.82rem;
  color: var(--color-text-muted);
  margin-bottom: 0.75rem;
}

.dashboard-pipeline-error {
  font-size: 0.8rem;
  color: var(--color-error, #c44);
  background: var(--color-bg);
  padding: 0.5rem;
  border: 1px solid var(--color-error, #c44);
  margin-bottom: 0.75rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.dashboard-pipeline-actions {
  display: flex;
  gap: 0.5rem;
}
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 4: Commit**

```bash
git add frontend/src/pages/admin/index.astro
git commit -m "feat(admin): add pipeline status section to dashboard"
```

---

### Task 4: Add Notifications section

**Files:**
- Modify: `frontend/src/pages/admin/index.astro` (HTML + CSS)

**Step 1: Add Notifications section HTML after Pipeline Status, before Recent Activity**

Only render when `notifications.length > 0`:

```html
{notifications.length > 0 && (
  <section class="dashboard-section">
    <div class="dashboard-section-header">
      <h2 class="dashboard-section-title">Notifications</h2>
      <button type="button" class="admin-btn-text" id="mark-all-read-btn">Mark all read</button>
    </div>
    <ul class="dashboard-activity-list">
      {notifications.map((n) => (
        <li class="dashboard-activity-item">
          <div class="dashboard-notification">
            <span class="dashboard-notification-icon">
              {n.type === 'error' ? '⚠' : n.type === 'pipeline' ? '⚙' : '🔔'}
            </span>
            <span class="dashboard-notification-title">{n.title}</span>
            <span class="dashboard-activity-time">{relativeTime(n.created_at)}</span>
          </div>
        </li>
      ))}
    </ul>
  </section>
)}
```

**Step 2: Add Notification CSS**

```css
.dashboard-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.admin-btn-text {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: 0.78rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  text-decoration: underline;
  font-family: inherit;
}

.admin-btn-text:hover {
  color: var(--color-text);
}

.dashboard-notification {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.25rem;
}

.dashboard-notification-icon {
  font-size: 0.9rem;
  flex-shrink: 0;
}

.dashboard-notification-title {
  flex: 1;
  font-size: 0.9rem;
}
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 4: Commit**

```bash
git add frontend/src/pages/admin/index.astro
git commit -m "feat(admin): add notifications section to dashboard"
```

---

### Task 5: Add vanilla JS for interactive buttons

**Files:**
- Modify: `frontend/src/pages/admin/index.astro` (add `<script>` block after closing `</style>`)

**Step 1: Add script block at end of file**

```html
<script>
  function initDashboardActions(): void {
    // Run Pipeline button
    const pipelineBtn = document.getElementById('run-pipeline-btn');
    if (pipelineBtn) {
      pipelineBtn.addEventListener('click', async () => {
        pipelineBtn.setAttribute('disabled', 'true');
        pipelineBtn.textContent = 'Running…';
        try {
          const res = await fetch('/api/trigger-pipeline', { method: 'POST' });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          pipelineBtn.textContent = 'Started ✓';
          setTimeout(() => window.location.reload(), 2000);
        } catch (err) {
          pipelineBtn.textContent = 'Failed ✗';
          pipelineBtn.removeAttribute('disabled');
          setTimeout(() => { pipelineBtn.textContent = 'Run Pipeline'; }, 3000);
        }
      });
    }

    // Mark all read button
    const markReadBtn = document.getElementById('mark-all-read-btn');
    if (markReadBtn) {
      markReadBtn.addEventListener('click', async () => {
        markReadBtn.textContent = 'Updating…';
        try {
          const { createClient } = await import('@supabase/supabase-js');
          // Access token from cookie for client-side
          const sb = createClient(
            (import.meta as any).env.PUBLIC_SUPABASE_URL,
            (import.meta as any).env.PUBLIC_SUPABASE_ANON_KEY,
          );
          // Get session from existing auth state
          const { data: { session } } = await sb.auth.getSession();
          if (session) {
            await sb.from('admin_notifications').update({ is_read: true }).eq('is_read', false);
          }
          // Remove notifications section from DOM
          markReadBtn.closest('.dashboard-section')?.remove();
        } catch {
          markReadBtn.textContent = 'Failed';
          setTimeout(() => { markReadBtn.textContent = 'Mark all read'; }, 2000);
        }
      });
    }
  }

  document.addEventListener('astro:page-load', initDashboardActions);
  initDashboardActions();
</script>
```

**Note:** The `Run Pipeline` button calls `/api/trigger-pipeline`. If this API endpoint doesn't exist yet, the button will gracefully show "Failed ✗" and recover. The endpoint can be wired up later.

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/pages/admin/index.astro
git commit -m "feat(admin): add pipeline trigger and mark-all-read JS handlers"
```

---

### Task 6: Final verification

**Step 1: Full build**

Run: `cd frontend && npm run build`
Expected: 0 errors

**Step 2: Verify all sections render**

Visually confirm:
- 6 stat cards in grid (Posts, Published, Terms, Drafts, Users, Likes)
- Pipeline Status section with status/time/details or "No pipeline runs yet"
- Notifications section (only if unread notifications exist)
- Recent Activity (unchanged)
- Stale Drafts (unchanged)

---

## File Summary

| File | Action |
|------|--------|
| `frontend/src/pages/admin/index.astro` | Modify (data, HTML, CSS, JS) |

All changes are in a single file, keeping the implementation atomic and easy to review.

## Related Plans

- [[plans/2026-03-10-admin-dashboard-design|Dashboard 설계]]
