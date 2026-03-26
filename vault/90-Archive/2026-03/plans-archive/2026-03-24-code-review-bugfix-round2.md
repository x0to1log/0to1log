# Code Review Bugfix Round 2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 bugs — reading history 갱신 불가, toggle delete 에러 미확인, library 리스너 누적, comment avatar XSS.

**Architecture:** 전부 프론트엔드 코드 수정. DB 변경 없음. 4개 모두 독립적.

**Tech Stack:** Astro v5, Supabase JS client, TypeScript

---

## Task 1: P1 — reading history `read_at` 갱신되도록 수정

**Root cause:** `ignoreDuplicates: true`가 `ON CONFLICT DO NOTHING`으로 동작해 재방문 시 `read_at`이 갱신되지 않음. 서재에서 최근 읽은 글이 위로 올라오지 않음.

**Files:**
- Modify: `frontend/src/pages/api/user/reading-history.ts:65-73`

- [ ] **Step 1: `ignoreDuplicates: true` 제거**

```typescript
// Before:
}, { onConflict: 'user_id,item_type,item_id', ignoreDuplicates: true });

// After:
}, { onConflict: 'user_id,item_type,item_id' });
```

주석도 업데이트:
```typescript
// Before:
// Upsert — ON CONFLICT DO NOTHING via upsert with ignoreDuplicates

// After:
// Upsert — ON CONFLICT DO UPDATE to refresh read_at on revisit
```

- [ ] **Step 2: Commit**

```bash
git commit -m "fix: update read_at on revisit so library sorts correctly"
```

---

## Task 2: P1 — toggle delete 결과 에러 체크 추가

**Root cause:** bookmarks.ts, likes.ts, product-likes.ts 3개 파일에서 delete 결과를 무시하고 바로 성공 응답.

**Files:**
- Modify: `frontend/src/pages/api/user/bookmarks.ts:75-80`
- Modify: `frontend/src/pages/api/user/likes.ts:94-95`
- Modify: `frontend/src/pages/api/user/product-likes.ts:65-66`

- [ ] **Step 1: bookmarks.ts delete 에러 체크**

```typescript
// Before:
if (existing) {
  // Remove
  await supabase.from('user_bookmarks').delete().eq('id', existing.id);
  return new Response(JSON.stringify({ bookmarked: false }), {

// After:
if (existing) {
  // Remove
  const { error: deleteError } = await supabase.from('user_bookmarks').delete().eq('id', existing.id);
  if (deleteError) {
    return new Response(JSON.stringify({ error: deleteError.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
  return new Response(JSON.stringify({ bookmarked: false }), {
```

- [ ] **Step 2: likes.ts delete 에러 체크**

```typescript
// Before:
if (existing) {
  await supabase.from(likesTable).delete().eq('id', existing.id);
} else {

// After:
if (existing) {
  const { error: deleteError } = await supabase.from(likesTable).delete().eq('id', existing.id);
  if (deleteError) {
    return new Response(JSON.stringify({ error: deleteError.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
} else {
```

- [ ] **Step 3: product-likes.ts delete 에러 체크**

```typescript
// Before:
if (existing) {
  await supabase.from('ai_product_likes').delete().eq('id', existing.id);
} else {

// After:
if (existing) {
  const { error: deleteError } = await supabase.from('ai_product_likes').delete().eq('id', existing.id);
  if (deleteError) {
    return new Response(JSON.stringify({ error: deleteError.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
} else {
```

- [ ] **Step 4: Commit**

```bash
git commit -m "fix: check delete result in bookmark/like toggle APIs"
```

---

## Task 3: P2 — library 리스너 init guard 추가

**Root cause:** `initLibrary()`가 `astro:page-load`마다 호출되는데 중복 방지 없이 모든 탭·버튼에 리스너 재바인딩.

**Files:**
- Modify: `frontend/src/pages/library/index.astro:574`

- [ ] **Step 1: init guard 추가**

```typescript
// Before:
function initLibrary(): void {
  // Tab switching

// After:
function initLibrary(): void {
  const container = document.querySelector<HTMLElement>('.library-page');
  if (!container || container.dataset.libInit === 'true') return;
  container.dataset.libInit = 'true';

  // Tab switching
```

참고: `.library-page` 클래스가 없으면 실제 컨테이너 클래스를 확인해서 적용.

- [ ] **Step 2: Commit**

```bash
git commit -m "fix: prevent library event handler accumulation on page revisit"
```

---

## Task 4: P2 — comment avatar URL XSS 방어

**Root cause:** `comments.ts:65`에서 `avatar_url`을 escape 없이 `innerHTML`에 삽입. `"` 포함 시 src 속성 탈출 → XSS 가능.

**Files:**
- Modify: `frontend/src/scripts/comments.ts:64-65`

- [ ] **Step 1: avatar_url에 escapeHtml 적용**

```typescript
// Before:
comment.user.avatar_url
  ? `<img src="${comment.user.avatar_url}" alt="" width="28" height="28" style="border-radius:50%;">`

// After:
comment.user.avatar_url
  ? `<img src="${escapeHtml(comment.user.avatar_url)}" alt="" width="28" height="28" style="border-radius:50%;">`
```

참고: `escapeHtml`이 이미 파일 내에서 import되어 있거나 정의되어 있는지 확인 필요.

- [ ] **Step 2: Commit**

```bash
git commit -m "fix: escape avatar URL in comment renderer to prevent XSS"
```

---

## Final: 빌드 확인

- [ ] `cd frontend && npm run build` — 0 errors 확인
- [ ] 전체 push
