# Code Review Bugfix Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 bugs found in code review — bio data loss on settings save, pipeline cancel false success, mark-all-read non-persistent.

**Architecture:** All 3 fixes are isolated, independent changes in the frontend. No DB migration, no backend change, no new files needed.

**Tech Stack:** Astro v5, Supabase JS client, TypeScript

---

## Task 1: P1 — Middleware profile select에 `bio` 추가

**Root cause:** `fetchUserExtras()`의 profiles select에 `bio` 컬럼이 빠져 있어 settings 페이지에서 항상 빈 값으로 로드됨. 저장 시 `bio: null`이 서버로 전송되어 기존 bio가 삭제됨.

**Files:**
- Modify: `frontend/src/middleware.ts:94`

- [ ] **Step 1: middleware select에 bio 추가**

`frontend/src/middleware.ts:94` — `.select()` 문자열에 `bio` 추가:

```typescript
// Before:
.select('display_name, username, username_changed_at, avatar_url, persona, preferred_locale, handbook_level, is_public, onboarding_completed')

// After:
.select('display_name, username, username_changed_at, avatar_url, bio, persona, preferred_locale, handbook_level, is_public, onboarding_completed')
```

- [ ] **Step 2: fallback 객체에도 bio 추가**

`frontend/src/middleware.ts:103-113` — `profileResult.data` fallback에 `bio: null` 추가:

```typescript
const profile = profileResult.data || {
  display_name: user.user_metadata?.full_name || null,
  username: null,
  username_changed_at: null,
  avatar_url: user.user_metadata?.avatar_url || null,
  bio: null,          // <-- 추가
  persona: null,
  preferred_locale: 'ko',
  handbook_level: 'basic',
  is_public: false,
  onboarding_completed: false,
};
```

- [ ] **Step 3: settings 페이지에서 `as any` 캐스트 제거**

`frontend/src/pages/settings/index.astro:121`:

```typescript
// Before:
const bio = (profile as any)?.bio || '';

// After:
const bio = profile?.bio || '';
```

- [ ] **Step 4: 빌드 확인**

```bash
cd frontend && npm run build
```

Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/middleware.ts frontend/src/pages/settings/index.astro
git commit -m "fix: include bio in middleware profile select to prevent data erasure"
```

---

## Task 2: P1 — Pipeline cancel에 응답 상태 체크 추가

**Root cause:** `fetch()` 후 `res.ok`를 확인하지 않아 4xx/5xx 응답에서도 "Pipeline cancelled" 성공 메시지를 표시. 운영자가 파이프라인이 멈춘 줄 알지만 실제로는 계속 실행 중.

**Files:**
- Modify: `frontend/src/pages/admin/index.astro:1032-1038`
- Modify: `frontend/src/pages/admin/pipeline-runs/index.astro:1163-1169`

- [ ] **Step 1: admin/index.astro cancel 핸들러 수정**

`frontend/src/pages/admin/index.astro:1031-1039` — `res.ok` 체크 추가:

```javascript
try {
  const res = await fetch('/api/admin/pipeline-cancel', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId }),
  });
  if (!res.ok) throw new Error('Cancel failed');
  setPipelineFeedback('Pipeline cancelled.', 'success');
  setTimeout(() => window.location.reload(), 1500);
} catch {
  cancelBtn.textContent = 'Failed';
  setTimeout(() => { cancelBtn.textContent = 'Cancel'; }, 2000);
}
```

- [ ] **Step 2: pipeline-runs/index.astro cancel 핸들러 수정**

`frontend/src/pages/admin/pipeline-runs/index.astro:1163-1169` — 동일 패턴 적용:

```javascript
fetch('/api/admin/pipeline-cancel', {
  method: 'POST',
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ run_id: runId }),
}).then(function(res) {
  if (!res.ok) throw new Error('Cancel failed');
  setPipelineFeedback('Pipeline cancelled.', 'success');
  setTimeout(function() { window.location.reload(); }, 1500);
}).catch(function() {
  cancelBtn.textContent = 'Failed';
  setTimeout(function() { cancelBtn.textContent = 'Cancel'; }, 2000);
});
```

- [ ] **Step 3: 빌드 확인**

```bash
cd frontend && npm run build
```

Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/admin/index.astro frontend/src/pages/admin/pipeline-runs/index.astro
git commit -m "fix: check response status on pipeline cancel to prevent false success"
```

---

## Task 3: P2 — Mark all read를 서버 API route로 이동

**Root cause:** 클라이언트에서 `createClient()` + `sb.auth.getSession()`으로 Supabase 직접 호출하지만, 이 앱은 HTTP-only 쿠키 인증이라 브라우저 SDK에서 session이 항상 null. DB update가 실행되지 않지만 DOM은 제거되어 UI가 거짓말함.

**해결 방향:** 서버 API route (`/api/admin/notifications-read`)를 만들어 서버 측에서 accessToken 기반으로 update 실행. 클라이언트는 이 API를 호출.

**Files:**
- Create: `frontend/src/pages/api/admin/notifications-read.ts`
- Modify: `frontend/src/pages/admin/index.astro:1050-1068`

- [ ] **Step 1: 서버 API route 생성**

`frontend/src/pages/api/admin/notifications-read.ts`:

```typescript
export const prerender = false;

import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const POST: APIRoute = async ({ locals }) => {
  const accessToken = locals.accessToken;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
  }

  const sb = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  const { error } = await sb
    .from('admin_notifications')
    .update({ is_read: true })
    .eq('is_read', false);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }

  return new Response(JSON.stringify({ ok: true }), { status: 200 });
};
```

- [ ] **Step 2: 클라이언트 핸들러를 API 호출로 교체**

`frontend/src/pages/admin/index.astro:1050-1068` — Supabase 직접 호출 대신 API route 사용:

```javascript
const markReadBtn = document.getElementById('mark-all-read-btn');
if (markReadBtn && !markReadBtn.dataset.init) {
  markReadBtn.dataset.init = '1';
  markReadBtn.addEventListener('click', async () => {
    markReadBtn.textContent = 'Updating…';
    try {
      const res = await fetch('/api/admin/notifications-read', {
        method: 'POST',
        credentials: 'same-origin',
      });
      if (!res.ok) throw new Error('Failed');
      markReadBtn.closest('.dashboard-section')?.remove();
    } catch {
      markReadBtn.textContent = 'Failed';
      setTimeout(() => { markReadBtn.textContent = 'Mark all read'; }, 2000);
    }
  });
}
```

핵심 변경: DOM 제거를 `res.ok` 이후에만 실행 → 성공 시에만 UI 반영.

- [ ] **Step 3: 빌드 확인**

```bash
cd frontend && npm run build
```

Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/api/admin/notifications-read.ts frontend/src/pages/admin/index.astro
git commit -m "fix: move mark-all-read to server API route for proper auth"
```
