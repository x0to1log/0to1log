# Frontend Design Sprint — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CSS 디자인 시스템 정교화 — 토큰화, 컴포넌트 일관성, 접근성 개선

**Architecture:** global.css의 @theme 블록에 디자인 토큰(radius, spacing) 추가 후, 기존 하드코딩 값을 토큰으로 점진 교체. 드롭다운 키보드 네비게이션은 Navigation.astro에 JS 추가.

**Tech Stack:** Astro v5 + CSS Custom Properties (Tailwind v4 @theme)

**Sprint spec:** `vault/09-Implementation/plans/2026-03-18-frontend-design-sprint.md`

---

## Task 1: 디자인 토큰 정의 (radius + spacing)

**Files:**
- Modify: `frontend/src/styles/global.css:48-67` (@theme 블록)

- [ ] **Step 1: @theme 블록에 radius 토큰 추가**

`--breakpoint-wide` 뒤, `}` 닫기 전에 추가:

```css
  /* Border Radius Scale */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;

  /* Spacing Scale (4px base) */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;
```

- [ ] **Step 2: 빌드 검증**

Run: `cd frontend && npm run build`
Expected: Complete! (토큰 정의만 추가, 기존 코드 미변경)

- [ ] **Step 3: 커밋**

```
feat(tokens): add radius and spacing design tokens to @theme
```

---

## Task 2: Border-radius 토큰 적용

**Files:**
- Modify: `frontend/src/styles/global.css`

**매핑 규칙:**
- `2px`, `3px` → `var(--radius-sm)` (4px) — 배지, 코드블록, 스크롤바, 태그
- `4px` → `var(--radius-sm)` — 포커스 링, 작은 버튼
- `6px` → `var(--radius-md)` (8px) — 카드, 버튼, 입력, 드롭다운
- `8px` → `var(--radius-md)` — 모달, 패널
- `10px`, `12px` → `var(--radius-lg)` (12px) — 큰 패널, 모달
- `999px`, `9999px` → `var(--radius-full)` — pill 버튼
- `50%` → 유지 (원형)
- 비대칭 값 (`24px 24px 18px 18px` 등) → 유지

- [ ] **Step 1: 6px 값들을 var(--radius-md)로 교체**

`border-radius: 6px`를 `border-radius: var(--radius-md)`로 일괄 교체.
단, `@media` 안의 값이나 복합값(`6px 0 0 6px`)은 제외.

- [ ] **Step 2: 3px, 4px 값들을 var(--radius-sm)로 교체**

`border-radius: 3px` → `var(--radius-sm)`, `border-radius: 4px` → `var(--radius-sm)`.
단, `:focus-visible`의 `border-radius: 4px`는 유지 (outline-radius 역할).

- [ ] **Step 3: 8px 값들을 var(--radius-md)로 교체**

`border-radius: 8px` → `var(--radius-md)`.

- [ ] **Step 4: 10px, 12px 값들을 var(--radius-lg)로 교체**

`border-radius: 10px` → `var(--radius-lg)`, `border-radius: 12px` → `var(--radius-lg)`.

- [ ] **Step 5: 999px, 9999px 값들을 var(--radius-full)로 교체**

`border-radius: 999px` → `var(--radius-full)`, `border-radius: 9999px` → `var(--radius-full)`.

- [ ] **Step 6: 2px 값들을 var(--radius-sm)로 교체 (선택적)**

스크롤바 thumb 등 2px는 시각적 영향이 적으므로 교체. 단, `scrollbar-width` 관련은 유지.

- [ ] **Step 7: 빌드 검증 + 4테마 시각 확인**

Run: `cd frontend && npm run build`

- [ ] **Step 8: 커밋**

```
refactor(css): replace hardcoded border-radius with design tokens
```

---

## Task 3: 카드 hover 패턴 통일

**Files:**
- Modify: `frontend/src/styles/global.css`

**통일 패턴:**
```css
[hover] → background: var(--color-accent-subtle)
[hover] .title → color: var(--color-accent)
```

현재 상태:
- `.newsprint-card:hover` — bg: accent-subtle, title: accent (**기준 패턴**)
- `.handbook-card:hover` — bg: bg-secondary (다름)
- `.product-category-showcase-card:hover` — bg: bg-secondary + border: accent (다름)
- `.home-product-card:hover` — bg: bg-secondary + border: accent (다름)

- [ ] **Step 1: handbook-card hover를 기준 패턴으로 변경**

```css
/* 변경 전 */
.handbook-card:hover { background: var(--color-bg-secondary); }

/* 변경 후 */
.handbook-card:hover { background: var(--color-accent-subtle); }
.handbook-card:hover .handbook-card-title { color: var(--color-accent); }
```

- [ ] **Step 2: product-category-showcase-card hover 업데이트**

```css
/* 변경 전 */
.product-category-showcase-card:hover { background: var(--color-bg-secondary); border-color: var(--color-accent); }

/* 변경 후 */
.product-category-showcase-card:hover { background: var(--color-accent-subtle); border-color: var(--color-accent); }
.product-category-showcase-card:hover .product-category-showcase-name { color: var(--color-accent); }
```

- [ ] **Step 3: home-product-card hover 업데이트**

```css
/* 변경 전 */
.home-product-card:hover { background: var(--color-bg-secondary); border-color: var(--color-accent); }

/* 변경 후 */
.home-product-card:hover { background: var(--color-accent-subtle); border-color: var(--color-accent); }
```

- [ ] **Step 4: product-card hover — translateY 유지, bg 추가**

product-card는 elevation 패턴이 의도적이므로 유지하되, bg만 통일:

```css
.product-card:hover { background: var(--color-accent-subtle); /* 기존 border-color + transform 유지 */ }
```

- [ ] **Step 5: 빌드 + 커밋**

```
refactor(css): unify card hover patterns to accent-subtle background
```

---

## Task 4: 터치 타겟 44px 보장

**Files:**
- Modify: `frontend/src/styles/global.css`

**위반 요소 (44px 미만):**
- `.site-theme-toggle` — ~18px
- `.site-lang-toggle` — ~22px
- `.user-avatar-btn` — 32px
- `.newsprint-bookmark-icon` — 36px (목록용)
- `.code-copy-btn` — ~20px
- `.admin-ai-create-draft-btn` — ~20px

- [ ] **Step 1: 헤더 유틸리티 버튼 최소 크기 보장**

```css
.site-theme-toggle,
.site-lang-toggle {
  min-width: 2.75rem;   /* 44px */
  min-height: 2.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

- [ ] **Step 2: 아바타 버튼 크기 확대**

`.user-avatar-btn`의 width/height를 `2rem` → `2.5rem` (40px)으로 증가. 완전한 44px는 패딩으로 보충.

- [ ] **Step 3: 북마크 아이콘 목록용 크기 확대**

`.newsprint-bookmark-icon` min-width/min-height 44px 보장.

- [ ] **Step 4: 코드 복사 버튼 크기 확대**

```css
.code-copy-btn {
  min-width: 2.25rem;
  min-height: 2.25rem;
  padding: 0.35rem 0.5rem;
}
```

- [ ] **Step 5: 빌드 + 커밋**

```
fix(a11y): ensure 44px minimum touch targets on interactive elements
```

---

## Task 5: 버튼 사이즈 시스템

**Files:**
- Modify: `frontend/src/styles/global.css`

현재 `.admin-btn`이 사실상 유일한 버튼 시스템. sm/md/lg 확장.

- [ ] **Step 1: 버튼 사이즈 클래스 정의**

기존 `.admin-btn` 아래에 추가:

```css
.admin-btn--sm {
  padding: var(--space-1) var(--space-3);
  font-size: 0.75rem;
}
/* .admin-btn 기본 = md (현재 값 유지: 0.4rem 0.85rem, 0.8rem) */
.admin-btn--lg {
  padding: var(--space-3) var(--space-6);
  font-size: 0.9rem;
}
```

- [ ] **Step 2: 마이크로 버튼 교체**

`.admin-ai-create-draft-btn`의 padding을 `.admin-btn--sm` 수준으로 상향.

- [ ] **Step 3: 빌드 + 커밋**

```
feat(css): add button size variants (sm, md, lg)
```

---

## Task 6: 드롭다운 키보드 네비게이션

**Files:**
- Modify: `frontend/src/components/Navigation.astro` (JS 블록)

- [ ] **Step 1: aria-expanded 상태 추가**

토글 버튼에 `aria-expanded` 속성 동기화:

```javascript
// 토글 시
freshToggle.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
dropdown.setAttribute('data-open', isOpen ? 'false' : 'true');
```

- [ ] **Step 2: Escape 키로 닫기**

```javascript
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const dropdown = document.querySelector('[data-user-dropdown]');
    if (dropdown?.getAttribute('data-open') === 'true') {
      closeUserDropdown();
      toggle.focus(); // 토글 버튼으로 포커스 복귀
    }
  }
});
```

- [ ] **Step 3: 화살표 키 네비게이션**

```javascript
dropdown.addEventListener('keydown', (e) => {
  const items = [...dropdown.querySelectorAll('.user-dropdown-item:not([disabled])')];
  const current = document.activeElement;
  const idx = items.indexOf(current);

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    items[(idx + 1) % items.length]?.focus();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    items[(idx - 1 + items.length) % items.length]?.focus();
  }
});
```

- [ ] **Step 4: 열릴 때 첫 번째 항목에 포커스**

```javascript
// 드롭다운이 열릴 때
if (!isOpen) {
  const firstItem = dropdown.querySelector('.user-dropdown-item');
  requestAnimationFrame(() => firstItem?.focus());
}
```

- [ ] **Step 5: 빌드 + 커밋**

```
feat(a11y): add keyboard navigation to profile dropdown
```

---

## 구현 순서

1. **Task 1** → 토큰 정의 (기반 작업, 다른 Task의 선행 조건)
2. **Task 2** → radius 토큰 적용 (가장 많은 변경, 단순 치환)
3. **Task 3** → hover 통일 (시각적 임팩트 큼)
4. **Task 4** → 터치 타겟 (접근성)
5. **Task 5** → 버튼 시스템 (새 클래스 추가)
6. **Task 6** → 키보드 네비게이션 (JS 작업, CSS와 독립)

## 검증

- 각 Task 후 `cd frontend && npm run build` 통과 필수
- Task 2, 3 완료 후 4개 테마(dark/light/pink/midnight) 시각 확인
- Task 6 완료 후 프로필 드롭다운에서 Tab/Arrow/Escape 키 테스트
