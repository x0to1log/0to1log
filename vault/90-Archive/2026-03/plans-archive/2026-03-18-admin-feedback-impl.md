# Admin Feedback Page — Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan.

**Goal:** 어드민 사이드바에 Feedback 메뉴 추가 + 핸드북 피드백 목록 페이지 구현 (Phase 1)

**Architecture:** 기존 어드민 리스트 페이지 패턴(`/admin/handbook/`) 준수. `term_feedback` JOIN `handbook_terms` JOIN `profiles`로 데이터 조회. 소스 탭 + 반응 필터 + 검색.

**설계 문서:** `vault/09-Implementation/plans/2026-03-18-admin-feedback-design.md`

---

## Task 1: AdminSidebar에 Feedback 메뉴 추가

**Files:**
- Modify: `frontend/src/components/admin/AdminSidebar.astro`

- [ ] **Step 1: activeSection 타입에 'feedback' 추가**

```ts
activeSection?: 'dashboard' | 'posts' | 'pipeline' | 'pipeline-analytics' | 'site-analytics' | 'blog' | 'handbook' | 'feedback' | 'products' | 'settings';
```

- [ ] **Step 2: Handbook과 Blog 사이에 Feedback 링크 추가**

Blog `</a>` (line 65) 뒤에 삽입:

```astro
<a href="/admin/feedback/" class:list={['admin-sidebar-link', { 'admin-sidebar-link--active': activeSection === 'feedback' }]}>
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M2 3h12v8H5l-3 3V3z" />
  </svg>
  <span>Feedback</span>
</a>
```

---

## Task 2: 피드백 리스트 페이지 생성

**Files:**
- Create: `frontend/src/pages/admin/feedback/index.astro`

- [ ] **Step 1: 페이지 구조**

```astro
---
export const prerender = false;
import MainLayout from '../../../layouts/MainLayout.astro';
import AdminSidebar from '../../../components/admin/AdminSidebar.astro';
import { createClient } from '@supabase/supabase-js';

const user = Astro.locals.user;
const accessToken = Astro.locals.accessToken;
if (!user || !accessToken) return Astro.redirect('/admin/login');

const supabase = createClient(
  import.meta.env.PUBLIC_SUPABASE_URL,
  import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
  { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
);

// Check admin
const { data: adminCheck } = await supabase
  .from('admin_users')
  .select('user_id')
  .eq('user_id', user.id)
  .maybeSingle();
if (!adminCheck) return Astro.redirect('/admin/login');

// Fetch feedback with term name and user profile
const { data: feedbackList } = await supabase
  .from('term_feedback')
  .select(`
    id, reaction, message, locale, created_at, updated_at,
    handbook_terms ( term, slug ),
    profiles:user_id ( display_name, username )
  `)
  .order('updated_at', { ascending: false })
  .limit(500);

const items = (feedbackList ?? []).map((f: any) => ({
  id: f.id,
  reaction: f.reaction,
  message: f.message,
  locale: f.locale,
  createdAt: f.created_at,
  updatedAt: f.updated_at,
  termName: f.handbook_terms?.term || '(deleted term)',
  termSlug: f.handbook_terms?.slug || '',
  userName: f.profiles?.display_name || f.profiles?.username || 'Anonymous',
}));

const helpfulCount = items.filter((i: any) => i.reaction === 'helpful').length;
const confusingCount = items.filter((i: any) => i.reaction === 'confusing').length;
---
```

- [ ] **Step 2: HTML 템플릿**

```astro
<MainLayout title="Feedback — Admin" locale="en" slug="admin/feedback/">
  <AdminSidebar activeSection="feedback" />
  <div class="admin-dashboard">
    <div class="admin-main-header">
      <h1 class="admin-main-title">Feedback</h1>
    </div>

    <!-- Source tabs (Phase 1: handbook only) -->
    <div class="admin-filter-tabs" style="margin-bottom: 0.75rem;">
      <button class="admin-filter-tab admin-filter-tab--active" data-source="all">전체 ({items.length})</button>
      <button class="admin-filter-tab admin-filter-tab--active" data-source="handbook">핸드북</button>
      <button class="admin-filter-tab" disabled title="Coming soon" style="opacity: 0.4;">뉴스</button>
      <button class="admin-filter-tab" disabled title="Coming soon" style="opacity: 0.4;">블로그</button>
      <button class="admin-filter-tab" disabled title="Coming soon" style="opacity: 0.4;">사이트</button>
    </div>

    <!-- Reaction filters + search -->
    <div class="admin-toolbar">
      <div class="admin-filter-tabs">
        <button class="admin-filter-tab admin-filter-tab--active" data-filter="all">All ({items.length})</button>
        <button class="admin-filter-tab" data-filter="helpful">Helpful ({helpfulCount})</button>
        <button class="admin-filter-tab" data-filter="confusing">Confusing ({confusingCount})</button>
      </div>
      <input type="text" class="admin-input" id="feedback-search" placeholder="Search term or message..." style="max-width: 240px;" />
    </div>

    <!-- Feedback list -->
    <ul class="admin-list" id="feedback-list">
      {items.map((item: any) => (
        <li class="admin-list-item admin-feedback-item" data-reaction={item.reaction} data-term={item.termName.toLowerCase()} data-message={(item.message || '').toLowerCase()}>
          <div class="admin-feedback-item-header">
            <a href={item.termSlug ? `/admin/handbook/edit/${item.termSlug}` : '#'} class="admin-feedback-term-link">
              {item.termName}
            </a>
          </div>
          <div class="admin-feedback-item-meta">
            <span class={`admin-feedback-reaction admin-feedback-reaction--${item.reaction}`}>
              {item.reaction === 'helpful' ? '✓ helpful' : '? confusing'}
            </span>
            <span class="admin-feedback-user">{item.userName}</span>
            <span class="admin-feedback-date">{new Date(item.updatedAt).toLocaleDateString('ko-KR')}</span>
            {item.locale && <span class="admin-lang-badge">{item.locale.toUpperCase()}</span>}
          </div>
          {item.message && (
            <p class="admin-feedback-message">"{item.message}"</p>
          )}
        </li>
      ))}
    </ul>

    {items.length === 0 && (
      <p class="admin-empty-state">피드백이 아직 없습니다.</p>
    )}
  </div>
</MainLayout>
```

- [ ] **Step 3: 클라이언트 JS (필터 + 검색)**

```html
<script>
  function initFeedbackAdmin() {
    const list = document.getElementById('feedback-list');
    if (!list || list.dataset.init === '1') return;
    list.dataset.init = '1';

    let activeFilter = 'all';
    const searchInput = document.getElementById('feedback-search') as HTMLInputElement;

    // Reaction filter tabs
    document.querySelectorAll('[data-filter]').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('[data-filter]').forEach(t => t.classList.remove('admin-filter-tab--active'));
        tab.classList.add('admin-filter-tab--active');
        activeFilter = (tab as HTMLElement).dataset.filter || 'all';
        applyFilters();
      });
    });

    // Search
    let searchTimeout: ReturnType<typeof setTimeout>;
    searchInput?.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(applyFilters, 200);
    });

    function applyFilters() {
      const query = (searchInput?.value || '').toLowerCase();
      list!.querySelectorAll('.admin-feedback-item').forEach(item => {
        const el = item as HTMLElement;
        const matchReaction = activeFilter === 'all' || el.dataset.reaction === activeFilter;
        const matchSearch = !query || (el.dataset.term || '').includes(query) || (el.dataset.message || '').includes(query);
        el.style.display = matchReaction && matchSearch ? '' : 'none';
      });
    }
  }

  document.addEventListener('DOMContentLoaded', initFeedbackAdmin);
</script>
```

---

## Task 3: CSS 스타일

**Files:**
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: 피드백 아이템 CSS 추가**

기존 `admin-list` 패턴을 재활용하되, 피드백 전용 스타일 추가:

```css
/* --- Admin Feedback List --- */
.admin-feedback-item {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--color-border);
}

.admin-feedback-item-header {
  margin-bottom: 0.25rem;
}

.admin-feedback-term-link {
  font-family: var(--font-heading);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text-primary);
  text-decoration: none;
}

.admin-feedback-term-link:hover {
  color: var(--color-accent);
}

.admin-feedback-item-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.admin-feedback-reaction {
  font-weight: 600;
}

.admin-feedback-reaction--helpful {
  color: var(--color-success);
}

.admin-feedback-reaction--confusing {
  color: var(--color-warning);
}

.admin-feedback-message {
  margin: 0.35rem 0 0;
  font-size: 0.82rem;
  font-style: italic;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.admin-empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}
```

---

## Task 4: RLS 정책 — admin이 모든 피드백 + 프로필 조회

**Files:**
- Create: `supabase/migrations/00030_admin_read_feedback.sql`

현재 `term_feedback` RLS는 `auth.uid() = user_id`만 허용. admin이 전체 피드백을 읽으려면 정책 추가 필요:

```sql
-- Admin can read all term_feedback
CREATE POLICY "admin_read_all_feedback" ON term_feedback FOR SELECT
  USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );

-- Admin can read all profiles (for display_name/username)
CREATE POLICY "admin_read_all_profiles" ON profiles FOR SELECT
  USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );
```

> 참고: profiles에 이미 admin read 정책이 있을 수 있음 — 기존 정책 확인 후 중복 방지.

---

## 구현 순서

1. Task 4 → DB 마이그레이션 (RLS 정책)
2. Task 1 → 사이드바 메뉴 추가
3. Task 3 → CSS 스타일
4. Task 2 → 페이지 생성
5. `cd frontend && npm run build` 검증

## 검증

1. `/admin/feedback/` 접속 → 피드백 목록 표시
2. 반응 필터 (All/Helpful/Confusing) 동작
3. 검색으로 용어명/메시지 필터링
4. 용어명 클릭 → 에디터로 이동
5. 비활성 탭 (뉴스/블로그/사이트) 클릭 불가
6. 사이드바에 Feedback 메뉴 활성 상태 표시
