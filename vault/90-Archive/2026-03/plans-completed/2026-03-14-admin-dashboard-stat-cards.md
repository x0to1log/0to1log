# Admin Dashboard Stat Card Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the admin dashboard stat cards into 3 semantic zones (Content / AI Cost / Site Metrics) and add "Check News" quick action button.

**Architecture:** Single file change — `frontend/src/pages/admin/index.astro`. Add 2 new DB queries (blog_posts count, 30-day pipeline cost), replace the flat 6-card grid with Zone A/B/C HTML, and update CSS accordingly.

**Tech Stack:** Astro v5, Supabase JS client, vanilla CSS (admin-* selectors in component `<style>`)

---

## Context

현재 stat 카드는 Posts / Published / Terms / Drafts / Users / Likes로 콘텐츠 타입과 운영 수치가 뒤섞여 있음.
목표 구조:
- **Zone A** (3 large, 클릭 가능): News → /admin/posts/ · Handbook → /admin/handbook/ · Blog → /admin/blog/
- **Zone B** (1 wide, 클릭 가능): AI Cost (30일) → /admin/pipeline-analytics
- **Zone C** (3 small): Drafts · Users · Likes

---

### Task 1: Frontmatter 쿼리 추가 — blog_posts count & monthly AI cost

**File:**
- Modify: `frontend/src/pages/admin/index.astro` (lines 16–125)

**Step 1: 변수 선언 추가**

기존 변수 선언 블록(line 16 근처)에 아래를 추가:

```typescript
let totalBlogPosts = 0;
let monthlyCost = 0;
let monthlyTokens = 0;
```

**Step 2: Promise.all에 쿼리 2개 추가**

기존 코드:
```typescript
const [postsRes, termsRes, profilesRes, likesRes, pipelineRes, notifsRes] = await Promise.all([
  sb.from('news_posts').select(...),
  sb.from('handbook_terms').select(...),
  sb.from('profiles').select('id', { count: 'exact', head: true }),
  sb.from('news_likes').select('id', { count: 'exact', head: true }),
  sb.from('pipeline_runs').select('*').order('started_at', { ascending: false }).limit(1),
  sb.from('admin_notifications').select(...),
]);
```

변경 후:
```typescript
const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

const [postsRes, termsRes, profilesRes, likesRes, pipelineRes, notifsRes, blogRes, monthlyLogsRes] = await Promise.all([
  sb.from('news_posts').select('title, slug, status, updated_at').order('updated_at', { ascending: false }),
  sb.from('handbook_terms').select('term, slug, status, updated_at, source').order('updated_at', { ascending: false }),
  sb.from('profiles').select('id', { count: 'exact', head: true }),
  sb.from('news_likes').select('id', { count: 'exact', head: true }),
  sb.from('pipeline_runs').select('*').order('started_at', { ascending: false }).limit(1),
  sb.from('admin_notifications').select('id, type, title, message, created_at').eq('is_read', false).order('created_at', { ascending: false }).limit(5),
  sb.from('blog_posts').select('id', { count: 'exact', head: true }),
  sb.from('pipeline_logs').select('cost_usd, tokens_used').gte('created_at', thirtyDaysAgo),
]);
```

**Step 3: 결과 집계 코드 추가**

기존 집계 블록 마지막(totalLikes = ... 직후)에 추가:

```typescript
totalBlogPosts = blogRes.count ?? 0;

const monthlyLogs = monthlyLogsRes.data ?? [];
monthlyCost = monthlyLogs.reduce((sum: number, l: any) => sum + (parseFloat(l.cost_usd) || 0), 0);
monthlyTokens = monthlyLogs.reduce((sum: number, l: any) => sum + (l.tokens_used || 0), 0);
```

**Step 4: 빌드 확인**

```bash
cd c:/Users/amy/Desktop/0to1log/frontend && npm run build
```
Expected: `[build] Complete!` with 0 errors

---

### Task 2: Quick Actions 버튼 수정

**File:**
- Modify: `frontend/src/pages/admin/index.astro` (Quick Actions 섹션)

**Step 1: HTML 변경**

기존:
```html
<div class="admin-quick-actions">
  <a href="/admin/edit/new" class="admin-btn admin-btn-primary">New Post</a>
  <a href="/admin/handbook/edit/new" class="admin-btn">New Term</a>
</div>
```

변경 후:
```html
<div class="admin-quick-actions">
  <a href="/admin/posts/" class="admin-btn">Check News</a>
  <a href="/admin/handbook/edit/new" class="admin-btn">New Term</a>
  <a href="/admin/edit/new" class="admin-btn admin-btn-primary">New Post</a>
</div>
```

**Step 2: 빌드 확인**

```bash
cd c:/Users/amy/Desktop/0to1log/frontend && npm run build
```
Expected: 0 errors

---

### Task 3: Stat Cards HTML — Zone A/B/C 구조로 교체

**File:**
- Modify: `frontend/src/pages/admin/index.astro` (dashboard-stats 섹션)

**Step 1: 기존 stat cards 블록 전체 교체**

기존 (lines ~162–187):
```html
<div class="dashboard-stats">
  <a href="/admin/posts/" class="dashboard-stat-card">
    <div class="dashboard-stat-label">Posts</div>
    <div class="dashboard-stat-value">{totalPosts}</div>
  </a>
  <a href="/admin/posts/" class="dashboard-stat-card">
    <div class="dashboard-stat-label">Published</div>
    <div class="dashboard-stat-value">{publishedPosts}</div>
  </a>
  <a href="/admin/handbook/" class="dashboard-stat-card">
    <div class="dashboard-stat-label">Terms</div>
    <div class="dashboard-stat-value">{totalTerms}</div>
  </a>
  <div class="dashboard-stat-card dashboard-stat-card--highlight">
    <div class="dashboard-stat-label">Drafts</div>
    <div class="dashboard-stat-value">{totalDrafts}</div>
  </div>
  <div class="dashboard-stat-card">
    <div class="dashboard-stat-label">Users</div>
    <div class="dashboard-stat-value">{totalUsers}</div>
  </div>
  <div class="dashboard-stat-card">
    <div class="dashboard-stat-label">Likes</div>
    <div class="dashboard-stat-value">{totalLikes}</div>
  </div>
</div>
```

교체 후:
```html
<!-- Zone A: 콘텐츠 현황 -->
<div class="dashboard-stats-zone-a">
  <a href="/admin/posts/" class="dashboard-stat-card">
    <div class="dashboard-stat-label">News</div>
    <div class="dashboard-stat-value">{totalPosts}</div>
  </a>
  <a href="/admin/handbook/" class="dashboard-stat-card">
    <div class="dashboard-stat-label">Handbook</div>
    <div class="dashboard-stat-value">{totalTerms}</div>
  </a>
  <a href="/admin/blog/" class="dashboard-stat-card">
    <div class="dashboard-stat-label">Blog</div>
    <div class="dashboard-stat-value">{totalBlogPosts}</div>
  </a>
</div>

<!-- Zone B: AI 운영 비용 -->
<a href="/admin/pipeline-analytics" class="dashboard-ai-cost-card">
  <div class="dashboard-ai-cost-label">AI Cost (this month)</div>
  <div class="dashboard-ai-cost-body">
    <span class="dashboard-ai-cost-main">${monthlyCost.toFixed(2)}</span>
    <span class="dashboard-ai-cost-tokens">{monthlyTokens.toLocaleString()} tokens</span>
  </div>
</a>

<!-- Zone C: 사이트 성과 -->
<div class="dashboard-stats-zone-c">
  <div class="dashboard-stat-card dashboard-stat-card--highlight">
    <div class="dashboard-stat-label">Drafts</div>
    <div class="dashboard-stat-value">{totalDrafts}</div>
  </div>
  <div class="dashboard-stat-card">
    <div class="dashboard-stat-label">Users</div>
    <div class="dashboard-stat-value">{totalUsers}</div>
  </div>
  <div class="dashboard-stat-card">
    <div class="dashboard-stat-label">Likes</div>
    <div class="dashboard-stat-value">{totalLikes}</div>
  </div>
</div>
```

**Step 2: 빌드 확인**

```bash
cd c:/Users/amy/Desktop/0to1log/frontend && npm run build
```
Expected: 0 errors

---

### Task 4: CSS — Zone A/B/C 스타일 추가 및 기존 .dashboard-stats 수정

**File:**
- Modify: `frontend/src/pages/admin/index.astro` (`<style>` 블록)

**Step 1: 기존 `.dashboard-stats` 블록 교체 및 Zone 스타일 추가**

기존 `.dashboard-stats` CSS 규칙 (및 미디어 쿼리 내 재정의 포함) 전체 제거 후 아래로 교체:

```css
/* Zone A — 콘텐츠 현황 */
.dashboard-stats-zone-a {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.dashboard-stats-zone-a .dashboard-stat-card {
  padding: 1.25rem 1rem;
}

.dashboard-stats-zone-a .dashboard-stat-value {
  font-size: 2rem;
}

/* Zone B — AI 운영 비용 */
.dashboard-ai-cost-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  padding: 0.875rem 1rem;
  text-decoration: none;
  color: inherit;
  margin-bottom: 0.75rem;
  transition: border-color 0.15s;
}

.dashboard-ai-cost-card:hover {
  border-color: var(--color-text-muted);
}

.dashboard-ai-cost-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.dashboard-ai-cost-body {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.dashboard-ai-cost-main {
  font-size: 1.25rem;
  font-weight: 700;
}

.dashboard-ai-cost-tokens {
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

/* Zone C — 사이트 성과 */
.dashboard-stats-zone-c {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

/* 반응형 */
@media (max-width: 640px) {
  .dashboard-stats-zone-a,
  .dashboard-stats-zone-c {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dashboard-ai-cost-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
  }
}
```

**Step 2: 기존 미디어쿼리 내 `.dashboard-stats` 관련 규칙 제거**

`@media (max-width: 960px)` 및 `@media (max-width: 640px)` 블록에서 `.dashboard-stats` 관련 grid-template-columns 재정의 삭제.

**Step 3: 빌드 확인**

```bash
cd c:/Users/amy/Desktop/0to1log/frontend && npm run build
```
Expected: 0 errors

---

### Task 5: 최종 정리 및 커밋

**Step 1: publishedPosts 변수 제거**

`let publishedPosts = 0;` 선언 및 `publishedPosts = posts.filter(...)` 할당 줄 삭제.
(stat 카드에서 더 이상 사용 안 함)

**Step 2: 전체 빌드 최종 확인**

```bash
cd c:/Users/amy/Desktop/0to1log/frontend && npm run build
```
Expected: 0 errors, 0 warnings (prerender warning 제외)

**Step 3: 커밋**

```bash
git add frontend/src/pages/admin/index.astro vault/09-Implementation/plans/2026-03-14-admin-dashboard-redesign.md vault/09-Implementation/plans/2026-03-14-admin-dashboard-stat-cards.md
git commit -m "feat(admin): redesign dashboard stat cards into Zone A/B/C layout"
```

---

## 완료 기준

- [ ] Zone A: News / Handbook / Blog — 각각 총 수 표시, 해당 관리 페이지 링크
- [ ] Zone B: AI Cost (30일 합계 비용 + 토큰 수) — /admin/pipeline-analytics 링크
- [ ] Zone C: Drafts (highlight) / Users / Likes
- [ ] Quick Actions: Check News / New Term / New Post 3개
- [ ] `publishedPosts` 변수 완전 제거
- [ ] `npm run build` 0 errors

## Related Plans

- [[plans/2026-03-14-admin-dashboard-redesign|Dashboard 리디자인]]
