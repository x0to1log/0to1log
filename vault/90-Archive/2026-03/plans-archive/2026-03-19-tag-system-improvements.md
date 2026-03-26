# Tag System Improvements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 어드민 4개 콘텐츠(News/Blog/Handbook/Products) 태그 시스템의 일관성·안전성·가시성을 개선한다.

**Architecture:** 3개 독립 레이어 수정. (1) API 레이어 — 태그 정규화 함수(`normalizeTags`) 공유 + Handbook 4개 제한. (2) 리스트 페이지 — SELECT에 태그 컬럼 추가 + 메타 영역에 태그 수 배지 표시. (3) 에디터 JS — 태그 파싱 시 중복 제거.

**Tech Stack:** Astro v5, TypeScript, Supabase (PostgreSQL), global.css (`.admin-tag-count` 스타일)

---

## 파일 구조

**생성:**
- `frontend/src/lib/normalizeTags.ts` — 태그 정규화 유틸 (공유)

**수정:**
- `frontend/src/pages/api/admin/posts/save.ts:42` — normalizeTags 적용
- `frontend/src/pages/api/admin/blog/save.ts:50` — normalizeTags 적용
- `frontend/src/pages/api/admin/handbook/save.ts:63` — normalizeTags + 4개 제한
- `frontend/src/pages/api/admin/products/save.ts:68` — normalizeTags 적용
- `frontend/src/pages/admin/posts/index.astro:36` — SELECT에 tags 추가 + 렌더링
- `frontend/src/pages/admin/blog/index.astro:43` — SELECT에 tags 추가 + 렌더링
- `frontend/src/pages/admin/handbook/index.astro:21` — categories 렌더링 (이미 SELECT됨)
- `frontend/src/pages/admin/products/index.astro:21` — SELECT에 tags 추가 + 렌더링
- `frontend/src/pages/admin/edit/[slug].astro` — 에디터 JS 태그 파싱 정규화
- `frontend/src/pages/admin/blog/edit/[slug].astro` — 에디터 JS 태그 파싱 정규화
- `frontend/src/styles/global.css` — `.admin-tag-count` 스타일 추가

---

## Chunk 1: 태그 정규화 유틸 + API 적용

### Task 1: `normalizeTags` 유틸 생성

**Files:**
- Create: `frontend/src/lib/normalizeTags.ts`

- [ ] **Step 1: 파일 생성**

```typescript
// frontend/src/lib/normalizeTags.ts
/**
 * 태그/카테고리 배열을 정규화한다:
 * - 공백 trim
 * - 소문자 변환
 * - 빈 항목 제거
 * - 중복 제거 (Set)
 * - 최대 개수 제한 (선택)
 */
export function normalizeTags(input: unknown, maxCount?: number): string[] {
  if (!Array.isArray(input)) return [];
  const normalized = [
    ...new Set(
      input
        .map((t) => (typeof t === 'string' ? t.trim().toLowerCase() : ''))
        .filter(Boolean),
    ),
  ];
  return maxCount !== undefined ? normalized.slice(0, maxCount) : normalized;
}
```

- [ ] **Step 2: 빌드 확인 (파일만 추가했으므로 빠르게 통과)**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
```

Expected: `Complete!`

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/lib/normalizeTags.ts
git commit -m "feat: add normalizeTags utility"
```

---

### Task 2: News API — normalizeTags 적용

**Files:**
- Modify: `frontend/src/pages/api/admin/posts/save.ts`

현재 코드 (line 42):
```typescript
tags: Array.isArray(tags) ? tags : [],
```

- [ ] **Step 1: import 추가 + 변경**

파일 상단 import 추가:
```typescript
import { normalizeTags } from '../../../../lib/normalizeTags';
```

line 42 변경:
```typescript
tags: normalizeTags(tags),
```

- [ ] **Step 2: 빌드 확인**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
```

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/pages/api/admin/posts/save.ts
git commit -m "feat: normalize tags in news API"
```

---

### Task 3: Blog API — normalizeTags 적용

**Files:**
- Modify: `frontend/src/pages/api/admin/blog/save.ts`

현재 코드 (line 50):
```typescript
tags: Array.isArray(tags) ? tags : [],
```

- [ ] **Step 1: import 추가 + 변경**

파일 상단 import 추가:
```typescript
import { normalizeTags } from '../../../../lib/normalizeTags';
```

line 50 변경:
```typescript
tags: normalizeTags(tags),
```

- [ ] **Step 2: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/api/admin/blog/save.ts
git commit -m "feat: normalize tags in blog API"
```

---

### Task 4: Handbook API — normalizeTags + 4개 제한 적용

**Files:**
- Modify: `frontend/src/pages/api/admin/handbook/save.ts`

현재 코드 (line 63):
```typescript
categories: Array.isArray(categories) ? categories : (categories ? [categories] : []),
```

- [ ] **Step 1: import 추가 + 변경**

파일 상단 import 추가:
```typescript
import { normalizeTags } from '../../../../lib/normalizeTags';
```

line 63 변경 (4개 제한 추가):
```typescript
categories: normalizeTags(Array.isArray(categories) ? categories : (categories ? [categories] : []), 4),
```

Note: `categories`는 사전 정의된 slug 값이므로 소문자 정규화는 정상 동작 (예: `'ai-ml'`, `'backend'` 모두 이미 소문자).

- [ ] **Step 2: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/api/admin/handbook/save.ts
git commit -m "feat: normalize categories + enforce 4-max in handbook API"
```

---

### Task 5: Products API — normalizeTags 적용

**Files:**
- Modify: `frontend/src/pages/api/admin/products/save.ts`

현재 코드 (line 68):
```typescript
if (tags !== undefined) row.tags = Array.isArray(tags) ? tags : [];
```

- [ ] **Step 1: import 추가 + 변경**

파일 상단 import 추가:
```typescript
import { normalizeTags } from '../../../../lib/normalizeTags';
```

line 68 변경:
```typescript
if (tags !== undefined) row.tags = normalizeTags(tags);
```

- [ ] **Step 2: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/api/admin/products/save.ts
git commit -m "feat: normalize tags in products API"
```

---

## Chunk 2: 리스트 페이지 태그 수 표시

### Task 6: global.css — `.admin-tag-count` 스타일 추가

**Files:**
- Modify: `frontend/src/styles/global.css`

`.admin-meta-sep` 스타일 근처에 추가:

- [ ] **Step 1: `.admin-tag-count` 스타일 추가**

`.admin-danger-zone` 블록 바로 뒤(또는 `.admin-meta-sep` 근처)에 추가:
```css
/* Tag count badge — 어드민 리스트 메타 영역 */
.admin-tag-count {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.72rem;
  color: var(--color-text-muted);
  opacity: 0.75;
}
```

- [ ] **Step 2: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/styles/global.css
git commit -m "feat: add admin-tag-count style"
```

---

### Task 7: News 리스트 — tags SELECT 추가 + 태그 수 표시

**Files:**
- Modify: `frontend/src/pages/admin/posts/index.astro`

- [ ] **Step 1: SELECT에 tags 추가** (line 36)

변경 전:
```typescript
.select('id, title, slug, category, locale, status, updated_at, published_at')
```

변경 후:
```typescript
.select('id, title, slug, category, locale, status, tags, updated_at, published_at')
```

- [ ] **Step 2: 리스트 메타에 태그 수 배지 추가** (line 188 근처, `admin-list-meta` div 안)

`Updated ...` span 바로 앞에 추가:
```astro
{post.tags && post.tags.length > 0 && (
  <>
    <span class="admin-meta-sep">·</span>
    <span class="admin-tag-count">🏷 {post.tags.length}</span>
  </>
)}
```

완성된 `admin-list-meta` 구조 (변경 후):
```astro
<div class="admin-list-meta">
  <span class={`admin-status-badge admin-status-badge--${post.status}`}>{post.status}</span>
  {post.locale && <span class="admin-lang-badge admin-lang-badge--ready">{post.locale.toUpperCase()}</span>}
  {post.category && (
    <>
      <span class="admin-meta-sep">·</span>
      <span>{post.category}</span>
    </>
  )}
  {post.tags && post.tags.length > 0 && (
    <>
      <span class="admin-meta-sep">·</span>
      <span class="admin-tag-count">🏷 {post.tags.length}</span>
    </>
  )}
  <span class="admin-meta-sep">·</span>
  <span class="admin-meta-date">Updated ...</span>
  ...
</div>
```

- [ ] **Step 3: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/admin/posts/index.astro
git commit -m "feat: show tag count in news admin list"
```

---

### Task 8: Blog 리스트 — tags SELECT 추가 + 태그 수 표시

**Files:**
- Modify: `frontend/src/pages/admin/blog/index.astro`

- [ ] **Step 1: SELECT에 tags 추가** (line 43)

변경 전:
```typescript
.select('id, title, slug, category, locale, status, source, updated_at, published_at')
```

변경 후:
```typescript
.select('id, title, slug, category, locale, status, source, tags, updated_at, published_at')
```

- [ ] **Step 2: 메타에 태그 수 배지 추가** (line 199 근처)

`Updated ...` span 앞에 추가 (News와 동일 패턴):
```astro
{post.tags && post.tags.length > 0 && (
  <>
    <span class="admin-meta-sep">·</span>
    <span class="admin-tag-count">🏷 {post.tags.length}</span>
  </>
)}
```

- [ ] **Step 3: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/admin/blog/index.astro
git commit -m "feat: show tag count in blog admin list"
```

---

### Task 9: Handbook 리스트 — categories 배지 표시

**Files:**
- Modify: `frontend/src/pages/admin/handbook/index.astro`

Handbook은 이미 `categories`를 SELECT하고 있음. 리스트에서 표시만 추가.

- [ ] **Step 1: 현재 handbook 리스트 아이템 HTML 파악**

`frontend/src/pages/admin/handbook/index.astro` 파일에서 `.admin-list-meta` 영역을 읽어 어디에 삽입할지 확인 (line 155~200 범위 예상).

- [ ] **Step 2: categories 표시 추가**

`admin-list-meta` 내 기존 메타 항목들 뒤, `Updated ...` 앞에 추가:
```astro
{term.categories && term.categories.length > 0 && (
  <>
    <span class="admin-meta-sep">·</span>
    <span class="admin-tag-count">🏷 {term.categories.length}</span>
  </>
)}
```

- [ ] **Step 3: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/admin/handbook/index.astro
git commit -m "feat: show category count in handbook admin list"
```

---

### Task 10: Products 리스트 — tags SELECT 추가 + 태그 수 표시

**Files:**
- Modify: `frontend/src/pages/admin/products/index.astro`

- [ ] **Step 1: 현재 Products 리스트 SELECT 확인**

파일 line 21 근처를 읽어 현재 SELECT 컬럼 파악.

- [ ] **Step 2: SELECT에 tags 추가**

현재:
```typescript
.select('id, slug, name, name_ko, logo_url, primary_category, is_published, featured, pricing, korean_support, sort_order, updated_at')
```

변경:
```typescript
.select('id, slug, name, name_ko, logo_url, primary_category, is_published, featured, pricing, korean_support, sort_order, tags, updated_at')
```

- [ ] **Step 3: 메타에 태그 수 배지 추가**

Products 리스트 아이템의 메타 영역에 추가:
```astro
{product.tags && product.tags.length > 0 && (
  <>
    <span class="admin-meta-sep">·</span>
    <span class="admin-tag-count">🏷 {product.tags.length}</span>
  </>
)}
```

- [ ] **Step 4: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/admin/products/index.astro
git commit -m "feat: show tag count in products admin list"
```

---

## Chunk 3: 에디터 JS 태그 파싱 정규화

### Task 11: News 에디터 — JS 파싱에 중복 제거 추가

**Files:**
- Modify: `frontend/src/pages/admin/edit/[slug].astro`

현재 News 에디터 JS에서 태그를 파싱하는 코드를 찾아 수정.

- [ ] **Step 1: 현재 태그 파싱 코드 위치 확인**

```bash
grep -n "split.*','.*trim\|tagsRaw\|edit-tags" frontend/src/pages/admin/edit/[slug].astro | head -10
```

- [ ] **Step 2: 파싱 코드 수정**

현재 (예상 패턴):
```javascript
const tagsRaw = tagsInput?.value || '';
const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);
```

변경 후:
```javascript
const tagsRaw = tagsInput?.value || '';
const tags = [...new Set(tagsRaw.split(',').map(t => t.trim().toLowerCase()).filter(Boolean))];
```

- [ ] **Step 3: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/admin/edit/[slug].astro
git commit -m "fix: deduplicate + lowercase tags in news editor JS"
```

---

### Task 12: Blog 에디터 — JS 파싱에 중복 제거 추가

**Files:**
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro`

- [ ] **Step 1: 현재 태그 파싱 코드 위치 확인**

```bash
grep -n "split.*','.*trim\|tagsRaw\|edit-tags" frontend/src/pages/admin/blog/edit/[slug].astro | head -10
```

- [ ] **Step 2: 파싱 코드 수정 (News와 동일 패턴)**

```javascript
const tags = [...new Set(tagsRaw.split(',').map(t => t.trim().toLowerCase()).filter(Boolean))];
```

- [ ] **Step 3: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Complete" | tail -5
git add frontend/src/pages/admin/blog/edit/[slug].astro
git commit -m "fix: deduplicate + lowercase tags in blog editor JS"
```

---

### Task 13: 최종 빌드 + 전체 검증

- [ ] **Step 1: 최종 클린 빌드**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|warning|Complete|built" | tail -10
```

Expected: `Complete!` with 0 errors

- [ ] **Step 2: 수동 검증 체크리스트**

  - [ ] News 리스트: 태그 있는 아이템에 `🏷 N` 표시 확인
  - [ ] Blog 리스트: 동일 확인
  - [ ] Handbook 리스트: 카테고리 있는 아이템에 `🏷 N` 표시 확인
  - [ ] Products 리스트: 동일 확인
  - [ ] News 에디터: 태그 입력 후 Save → `"ai", "AI", " AI "` 모두 → 저장 후 `["ai"]` 1개만 됨
  - [ ] Handbook 에디터: 4개 선택 후 5번째 체크박스 선택 불가 (기존 UI 동작 확인) + API로 5개 보내도 4개만 저장됨

- [ ] **Step 3: ACTIVE_SPRINT 업데이트**

  `ACTIVE_SPRINT.md`에 `TAG-IMPROVE-01` 태스크 추가 + done 표시.

- [ ] **Step 4: 최종 Push**

```bash
git push origin main
```

---

## 의존성 순서

```
Task 1 (normalizeTags 유틸)
  → Task 2 (News API)
  → Task 3 (Blog API)
  → Task 4 (Handbook API)
  → Task 5 (Products API)

Task 6 (CSS 스타일)
  → Task 7 (News 리스트)
  → Task 8 (Blog 리스트)
  → Task 9 (Handbook 리스트)
  → Task 10 (Products 리스트)

Task 11 (News 에디터 JS)  ← 독립
Task 12 (Blog 에디터 JS)  ← 독립

Task 13 (최종 검증)
```

Task 1~5 (API)와 Task 6~12 (리스트+에디터)는 서로 독립 → 병렬 실행 가능.
