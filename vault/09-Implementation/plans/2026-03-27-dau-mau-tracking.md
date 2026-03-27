# DAU/MAU Tracking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Track daily active users (DAU) and monthly active users (MAU) based on logged-in user activity, and display the metrics on the admin dashboard.

**Architecture:** Add `last_seen_at` column to `profiles` table. Middleware updates it once per day (compare date, not every request). Dashboard queries `profiles` with date filters to compute DAU/MAU. Lightweight — no new tables, no background jobs, no external services.

**Tech Stack:** Supabase (PostgreSQL), Astro middleware, existing admin dashboard

**Key design decision:** Update `last_seen_at` only when the date changes (not every request). This means at most 1 UPDATE per user per day — zero performance concern even at scale.

---

### Task 1: Add `last_seen_at` column to profiles

**Files:**
- Create: `supabase/migrations/00043_profiles_last_seen_at.sql`

**Step 1: Write migration**

```sql
-- 00043_profiles_last_seen_at.sql
-- Add last_seen_at for DAU/MAU tracking.
-- Updated by middleware once per day per user.

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

-- Index for efficient DAU/MAU queries (filter by date range)
CREATE INDEX IF NOT EXISTS idx_profiles_last_seen_at ON profiles(last_seen_at)
  WHERE last_seen_at IS NOT NULL;

-- Backfill: set existing users' last_seen_at to their updated_at
UPDATE profiles SET last_seen_at = updated_at WHERE last_seen_at IS NULL;
```

**Step 2: Execute migration against Supabase**

Run via psql/python (same pattern as avatars bucket migration):
```bash
cd backend && .venv/Scripts/python.exe -c "
import psycopg2
conn = psycopg2.connect('...')  # DATABASE_URL from .env
conn.autocommit = True
cur = conn.cursor()
cur.execute('ALTER TABLE profiles ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ')
cur.execute('''CREATE INDEX IF NOT EXISTS idx_profiles_last_seen_at ON profiles(last_seen_at) WHERE last_seen_at IS NOT NULL''')
cur.execute('UPDATE profiles SET last_seen_at = updated_at WHERE last_seen_at IS NULL')
print('Migration done')
cur.close()
conn.close()
"
```

**Step 3: Commit**

```bash
git add supabase/migrations/00043_profiles_last_seen_at.sql
git commit -m "feat: add last_seen_at column to profiles for DAU/MAU"
```

---

### Task 2: Middleware — update last_seen_at once per day

**Files:**
- Modify: `frontend/src/middleware.ts`

**Design:** After successfully resolving a logged-in user (Zone 1, 2, or 3), check if `last_seen_at` is today. If not, fire an async UPDATE (non-blocking — don't await in the request path).

**Step 1: Add helper function after existing imports**

Add near the top of middleware.ts (after existing helper functions):

```typescript
function touchLastSeen(supabaseUrl: string, supabaseAnonKey: string, accessToken: string, userId: string): void {
  // Fire-and-forget: update last_seen_at if not already today
  // Uses fetch directly to avoid blocking the response
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  fetch(`${supabaseUrl}/rest/v1/profiles?id=eq.${userId}&last_seen_at=lt.${today}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'apikey': supabaseAnonKey,
      'Authorization': `Bearer ${accessToken}`,
      'Prefer': 'return=minimal',
    },
    body: JSON.stringify({ last_seen_at: new Date().toISOString() }),
  }).catch(() => {}); // silent — never block user request
}
```

**Key points about this approach:**
- `last_seen_at=lt.{today}` filter means if already updated today, the PATCH matches 0 rows → no write
- Fire-and-forget (no await) — doesn't slow down page load
- Uses Supabase REST API directly (not JS client) to keep it minimal
- `.catch(() => {})` — silently swallow errors, never affect user experience

**Step 2: Call touchLastSeen at the end of each auth zone**

In Zone 1 (admin), after `context.locals` are set (~line 236):
```typescript
touchLastSeen(supabaseUrl, supabaseAnonKey, result.accessToken, result.user.id);
```

In Zone 2 (user-protected), after `context.locals` are set (~line 261):
```typescript
touchLastSeen(supabaseUrl, supabaseAnonKey, result.accessToken, result.user.id);
```

In Zone 3 (public, logged-in), after `context.locals` are set (~line 295):
```typescript
touchLastSeen(supabaseUrl, supabaseAnonKey, result.accessToken, result.user.id);
```

**Step 3: Build check**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/middleware.ts
git commit -m "feat: middleware updates last_seen_at once per day (fire-and-forget)"
```

---

### Task 3: Admin dashboard — DAU/MAU display

**Files:**
- Modify: `frontend/src/pages/admin/index.astro`

**Step 1: Add DAU/MAU queries to the existing parallel batch**

In the frontmatter, add two new queries to the `Promise.all([...])` block:

```typescript
// DAU: profiles with last_seen_at >= start of today (UTC)
sb.from('profiles').select('id', { count: 'exact', head: true })
  .gte('last_seen_at', new Date(new Date().setUTCHours(0,0,0,0)).toISOString()),

// MAU: profiles with last_seen_at >= 30 days ago
sb.from('profiles').select('id', { count: 'exact', head: true })
  .gte('last_seen_at', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()),
```

Add variables and extract from results:
```typescript
let dau = 0;
let mau = 0;
// ... after Promise.all:
dau = dauRes.count ?? 0;
mau = mauRes.count ?? 0;
```

**Step 2: Update the Users stat card to show DAU/MAU**

Replace the existing simple "Users" stat card with:
```html
<div class="dashboard-stat-card">
  <div class="dashboard-stat-label">Users</div>
  <div class="dashboard-stat-value">{totalUsers}</div>
  <div class="dashboard-stat-sub">
    DAU {dau} · MAU {mau}
  </div>
</div>
```

**Step 3: Add CSS for stat sub-line (if not already exists)**

Check if `.dashboard-stat-sub` exists. If not, add to the dashboard styles:
```css
.dashboard-stat-sub {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-top: 0.25rem;
}
```

**Step 4: Build check**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/admin/index.astro
git commit -m "feat: show DAU/MAU on admin dashboard"
```

---

### Task 4: Final verification + push

**Step 1: Full build**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 2: Push**

```bash
git push origin main
```

**Step 3: Manual verification**

After deploy:
1. Visit any page while logged in → check Supabase profiles table for `last_seen_at` update
2. Visit admin dashboard → verify DAU/MAU numbers appear under Users card
3. DAU should be >= 1 (at least the admin user who just visited)
