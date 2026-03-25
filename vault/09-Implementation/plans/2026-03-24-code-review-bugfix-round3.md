# Code Review Bugfix Round 3 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 bugs — OAuth 오픈 리다이렉트, 추천 API 인증 누락, 온보딩 건너뛰기, 아바타 캐시 미무효화.

**Architecture:** P1 오픈 리다이렉트는 프론트 only. P1 추천 API는 프론트+백엔드 양쪽. P2 두 개는 프론트 only.

**Tech Stack:** Astro v5, FastAPI, Supabase, TypeScript, Python

---

## Task 1: P1 — OAuth 오픈 리다이렉트 방어

**Root cause:** `redirectTo`를 쿼리스트링에서 그대로 받아 검증 없이 `window.location.href`에 대입.

**Files:**
- Modify: `frontend/src/scripts/auth-oauth.ts:5-11`

- [ ] **Step 1: `resolveRedirectTarget`에서 same-origin 경로만 허용**

```typescript
// Before:
function resolveRedirectTarget(button: HTMLButtonElement, root: HTMLElement): string {
  return (
    button.dataset.redirectTo ||
    root.dataset.redirectTo ||
    new URLSearchParams(window.location.search).get('redirectTo') ||
    '/'
  );
}

// After:
function isSafeRedirect(url: string): boolean {
  return url.startsWith('/') && !url.startsWith('//');
}

function resolveRedirectTarget(button: HTMLButtonElement, root: HTMLElement): string {
  const raw =
    button.dataset.redirectTo ||
    root.dataset.redirectTo ||
    new URLSearchParams(window.location.search).get('redirectTo') ||
    '/';
  return isSafeRedirect(raw) ? raw : '/';
}
```

- [ ] **Step 2: callback.astro에서도 이중 검증**

`frontend/src/pages/auth/callback.astro:58` — sessionStorage에서 꺼낸 값도 검증:

```javascript
// Before:
const redirectTo = sessionStorage.getItem('oauth_redirect') || '/';

// After:
const rawRedirect = sessionStorage.getItem('oauth_redirect') || '/';
const redirectTo = (rawRedirect.startsWith('/') && !rawRedirect.startsWith('//')) ? rawRedirect : '/';
```

- [ ] **Step 3: Commit**

---

## Task 2: P1 — 추천 API에 인증 추가

**Root cause:** `/api/recommendations/for-you`가 인증 없이 `user_id` 쿼리 파라미터만 받아 서비스 키로 개인화 데이터 조회.

**해결 방향:** 프론트 SSR에서 이미 `accessToken`을 보유하므로, 이를 Authorization 헤더로 전달. 백엔드에서 토큰 검증 후 `user_id`를 토큰에서 추출.

**Files:**
- Modify: `backend/routers/recommendations.py:40-70`
- Modify: `frontend/src/pages/library/index.astro:172-173`

- [ ] **Step 1: 백엔드 — for-you 엔드포인트에 인증 추가**

`backend/routers/recommendations.py`:

```python
# Before:
@router.get("/for-you", response_model=list[RecommendedPost])
@limiter.limit("20/minute")
async def for_you(
    request: Request,
    locale: str = Query(default="en", pattern=r"^(en|ko)$"),
    user_id: str = Query(..., min_length=1, max_length=256),
):
    """Return personalized recommendations. user_id passed as query param from SSR."""

    client = get_supabase()

# After:
@router.get("/for-you", response_model=list[RecommendedPost])
@limiter.limit("20/minute")
async def for_you(
    request: Request,
    locale: str = Query(default="en", pattern=r"^(en|ko)$"),
    authorization: str = Header(None),
):
    """Return personalized recommendations. Requires Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")

    token = authorization.removeprefix("Bearer ").strip()
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    # Verify token and extract user_id
    auth_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    user_res = auth_client.auth.get_user(token)
    if not user_res or not user_res.user:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = user_res.user.id
```

import 추가: `from fastapi import Header`, `from supabase import create_client`, `from core.config import settings`

- [ ] **Step 2: 프론트 — SSR fetch에 Authorization 헤더 추가**

`frontend/src/pages/library/index.astro:172-173`:

```typescript
// Before:
const recsPromise = (fastapiUrl && user?.id)
  ? fetch(`${fastapiUrl}/api/recommendations/for-you?user_id=${user.id}&locale=${locale}`, { signal: AbortSignal.timeout(2000) })

// After:
const recsPromise = (fastapiUrl && user?.id && accessToken)
  ? fetch(`${fastapiUrl}/api/recommendations/for-you?locale=${locale}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      signal: AbortSignal.timeout(2000),
    })
```

- [ ] **Step 3: Commit**

---

## Task 3: P2 — 온보딩 건너뛰기 방지

**Root cause:** `localStorage.getItem('onboarding_seen')`이 한 번 설정되면 서버의 `onboarding_completed` 상태와 무관하게 영구 스킵.

**해결:** `onboarding_seen`을 체크하지 않고 서버의 `onboarding_completed`만 기준으로 판단.

**Files:**
- Modify: `frontend/src/pages/auth/callback.astro:94-106`

- [ ] **Step 1: localStorage 체크 제거, 서버 값만 사용**

```javascript
// Before:
try {
  const profileRes = await fetch('/api/user/profile');
  if (profileRes.ok) {
    const profile = await profileRes.json();
    if (!profile.onboarding_completed && !localStorage.getItem('onboarding_seen')) {
      localStorage.setItem('onboarding_seen', 'true');
      window.location.href = '/settings/?onboarding=true';
      return;
    }
  }
} catch {
  // Profile check failure should not block login
}

// After:
try {
  const profileRes = await fetch('/api/user/profile');
  if (profileRes.ok) {
    const profile = await profileRes.json();
    if (!profile.onboarding_completed) {
      window.location.href = '/settings/?onboarding=true';
      return;
    }
  }
} catch {
  // Profile check failure should not block login
}
```

settings 페이지의 `localStorage.removeItem('onboarding_seen')` (계정 삭제 시)도 더 이상 필요 없지만, 남겨둬도 무해하므로 그대로 둔다.

- [ ] **Step 2: Commit**

---

## Task 4: P2 — 아바타 업로드/삭제 후 캐시 무효화

**Root cause:** `avatar.ts` POST/DELETE 후 `user-extras-cache` 쿠키를 삭제하지 않아 최대 5분간 이전 아바타가 SSR UI에 표시.

**Files:**
- Modify: `frontend/src/pages/api/user/avatar.ts:80` (POST 응답)
- Modify: `frontend/src/pages/api/user/avatar.ts:106` (DELETE 응답)

- [ ] **Step 1: POST/DELETE 응답에서 캐시 쿠키 삭제**

avatar.ts의 POST와 DELETE 핸들러에서 성공 응답 시 `user-extras-cache` 쿠키를 만료시킨다.
API route에서는 `Astro.cookies`를 직접 사용할 수 없으므로 `Set-Cookie` 헤더를 수동으로 추가:

POST 성공 응답 (기존 `return jsonResponse(...)` 교체):
```typescript
// Before:
return jsonResponse({ avatar_url: avatarUrl });

// After:
const res = jsonResponse({ avatar_url: avatarUrl });
res.headers.append('Set-Cookie', 'user-extras-cache=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax');
return res;
```

DELETE 성공 응답:
```typescript
// Before:
return jsonResponse({ avatar_url: oauthAvatar });

// After:
const res = jsonResponse({ avatar_url: oauthAvatar });
res.headers.append('Set-Cookie', 'user-extras-cache=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax');
return res;
```

- [ ] **Step 2: Commit**

---

## Final: 빌드 확인 + 푸시

- [ ] `cd frontend && npm run build` — 0 errors
- [ ] `cd backend && python -m py_compile routers/recommendations.py` — 0 errors
- [ ] 전체 commit + push
