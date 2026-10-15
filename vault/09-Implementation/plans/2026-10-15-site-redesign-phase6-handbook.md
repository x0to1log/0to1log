# 사이트 리디자인 6단계(핸드북) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 핸드북 목록·상세·카테고리 페이지를 Soft Newsprint V2로 다듬는다.
- 용어 항목: 카드를 없애고 사전 항목처럼 보이게 한다.
- 분야 필터: 점 탭으로 바꾼다.
- 많이 찾는 용어·분야별 목록: 번호 목록과 점선 목록으로 바꾼다.
- 상세 페이지: 머리, 한 줄 정의 박스, 수준 선택 점, 관련 용어 점선 목록을 적용하고 대문자 라벨을 없앤다.

**Architecture:** 스타일 위주로 바꾼다. `global.css`의 기존 셀렉터를 수정하고, 마크업은 inline style 제거와 클래스 추가만 한다. 데이터 로딩, 클라이언트 스크립트 로직, 세션 하이드레이션은 바꾸지 않는다.

**Tech Stack:** Astro v5, 순수 Node 테스트(`node frontend/tests/<file>`, repo 루트)

**시안:** `.superpowers/brainstorm/phase6/handbook.html` (2026-10-15 사용자 승인)

---

## 사전 정보 (실행자 필독)

### 공유 작업 트리 규칙
- 각 파일을 수정하기 전에 `git status --short -- <file>`로 상태를 확인한다. 미커밋 변경이 있으면 수정하지 말고 BLOCKED로 보고한다.
- `git add`는 계획에 적힌 파일만 경로를 지정해서 한다. `-A`/`.`, stash/reset/checkout은 쓰지 않는다. 샌드박스가 명령을 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 계획에 적힌 그대로 쓴다. `Co-Authored-By`는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 정규식이 들어간 파일은 Write/Edit 도구로 작성한다. Bash heredoc을 쓰면 백슬래시가 사라진다. `global.css`는 LF 줄바꿈이고, 줄 번호가 계속 바뀌므로 셀렉터 문자열로 찾는다.
- dev 서버가 떠 있으면 `npm run build`가 EPERM으로 실패할 수 있다. 이때는 반복 재시도하지 말고 보고한다.

### 수정하지 않는 파일
- `src/lib/pageData/*`, `src/lib/rehypeHandbookSectionMarkers.ts`(관련 용어 HTML 생성), `src/scripts/*`, middleware, `src/lib/server/*`
- 페이지 frontmatter의 데이터 로딩 부분

### 반드시 유지할 것 (Supabase 세션 인계)
- `/en`, `/ko` 페이지의 SSR 출력은 사용자 정보에 의존하지 않는다.
- `.handbook-action-bar`에 `data-auth-only hidden` 속성, 그 안에 `.learning-check[data-term-id][data-status]`. 모든 방문자에게 렌더해야 한다. 게스트 조회수 집계(`trackView`)가 `[data-term-id]`로 대상을 찾는다.
- 수준 스위처
  - 스크립트의 `userPicked`, `setActiveLevel(level, { scroll })`, 저장된 수준을 적용하는 `onSessionReady` 블록
  - 마크업의 `<template id="level-data">`, `.handbook-level-btn[data-level]` / `--active`
- 관리자 블록 `data-admin-only hidden`
- 목록 카드의 `.newsprint-bookmark-icon[data-item-id][data-item-type]`, 검색과 필터에 쓰이는 id와 data 속성(`#handbook-search`, `#search-results`, `#handbook-result-count`, `.handbook-filter-btn[data-filter][aria-pressed]`)

### 공유 셀렉터
- `.product-category-showcase*`는 제품 페이지와 공유한다. **`#handbook-showcase` 범위로만** override한다.
- `.handbook-card`, `.handbook-search-*`는 카테고리 페이지와 공유한다. 이건 의도된 변경이다.

### 기존 실패 테스트
다음 테스트는 이미 실패 중이며 이번 범위가 아니다.
- `handbook-category-icons`
- `handbook-detail-table-overflow`
- `handbook-search-recognition`
- `sticky-reading-actions-structure`

이번 작업에서 실패 이유가 바뀌는지만 확인한다.

### 계속 통과해야 하는 테스트
- `handbook-library-copy`
- `public-term-index`
- `detail-rail-actions-placement`
- `term-references`
- `font-roles`
- `retro-decoration-removed`
- `theme-palette`
- `list-v2`
- `article-v2`
- `product-detail-search-sticky`

### 테스트 기준선
5단계 종료 시 PASS 66 / FAIL 23. 비교는 개수가 아니라 이름으로 한다.

---

## Chunk 1: 목록과 카테고리

### Task 1: 사전 항목, 점 탭, 많이 찾는 용어, 분야별 목록

**Files:**
- Modify: `frontend/src/styles/global.css`
  - 카드: `.handbook-card*`, `.handbook-cat-pill`
  - 필터: `.handbook-filter-btn*`
  - 많이 찾는 용어: `.handbook-trending*`(중복 블록 정리)
  - `.handbook-hero-stats strong`
  - 새 `#handbook-showcase ...` override
- Test: `frontend/tests/handbook-v2.test.cjs` (새 파일)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/handbook-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');
function rules(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
}
function rule(selector) {
  const all = rules(selector);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1]; // last top-level rule wins
}

// Task 1: 목록
const card = rule('.handbook-card');
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(card), 'term entries separated by dotted lines');
assert(/background:\s*none|background:\s*transparent/.test(card) && /box-shadow:\s*none/.test(card), 'term entries are not cards');
assert(/font-weight:\s*600/.test(rule('.handbook-card-title')) && rule('.handbook-card-title').includes('var(--font-heading)'), 'entry title in Hahmlet 600');
assert(/-webkit-line-clamp:\s*2/.test(rule('.handbook-card-def')), 'definition clamps to 2 lines');
const pill = rule('.handbook-cat-pill');
assert(/background:\s*none/.test(pill) && pill.includes('var(--color-accent)'), 'category pill becomes an accent label');
assert(css.includes('.handbook-cat-pill::before {'), 'category label has a dot');
assert(rule('.handbook-filter-btn[aria-pressed="true"]::after').includes('var(--color-accent)'), 'active filter marked by an accent dot');
assert(rules('.handbook-trending').length === 1, 'duplicate .handbook-trending block removed');
assert(/border-bottom:\s*1px dotted/.test(rule('.handbook-trending-list li')), 'trending is a dotted numbered list');
assert(css.includes('#handbook-showcase .product-category-showcase-card {'), 'showcase override is scoped to the handbook');

console.log('handbook-v2.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/handbook-v2.test.cjs`
Expected: FAIL. `term entries separated by dotted lines`

- [ ] **Step 3: CSS 수정** (`global.css`, 셀렉터로 찾기)

  각 규칙을 먼저 읽고, 아래 **목표 속성**만 바꾸거나 추가한다. 표에 없는 속성은 그대로 둔다.

  **1) 용어 카드 (`.handbook-card*`)**
  - `.handbook-card`
    - `border: none;`, `border-bottom: 1px dotted var(--color-border);`
    - `border-radius: 0;`, `background: none;`, `box-shadow: none;`
    - `padding: 0.95rem 0;`
  - `.handbook-card:hover`: `background: none;`. 제목 색 변화는 `.handbook-card:hover .handbook-card-title`이 맡는다.
  - `.handbook-card-title`
    - `font-family: var(--font-heading);`, `font-weight: 600;`
    - `font-size: 1.1rem;`, `letter-spacing: -0.03em;`, `line-height: 1.4;`
  - `.handbook-card-korean`
    - `font-size: 0.8rem;`, `color: var(--color-text-muted);`
  - `.handbook-card-def`
    - `font-size: 0.88rem;`, `line-height: 1.65;`, `color: var(--color-text-secondary);`
    - 두 줄 자르기: `display: -webkit-box;`, `-webkit-line-clamp: 2;`, `-webkit-box-orient: vertical;`, `overflow: hidden;`
  - `.handbook-cat-pill`
    - `background: none;`, `border: none;`, `padding: 0;`, `border-radius: 0;`
    - `color: var(--color-accent);`, `font-size: 0.72rem;`, `font-weight: 600;`
    - `display: inline-flex;`, `align-items: center;`, `gap: 0.35rem;`
    - `text-transform`이 있으면 삭제하고 `letter-spacing: 0;`
    - 바로 뒤에 아래 규칙을 추가한다.
      ```css
      .handbook-cat-pill::before {
        content: '';
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: currentColor;
      }
      ```
  - `.handbook-diff-pill`이 있으면 같은 방식으로 `background: none; border: none; padding: 0; color: var(--color-text-muted);`로 바꾼다. 점은 붙이지 않는다.

  **2) 분야 필터 (`.handbook-filter-btn*`)**
  - 기본 규칙
    - `position: relative;`
    - `border: none;`, `border-radius: 0;`, `background: none;`
    - `padding: 0.45rem 0.1rem 0.7rem;`
    - `color: var(--color-text-muted);`, `font-weight: 500;`
    - `text-transform`이 있으면 삭제하고 `letter-spacing: 0;`
  - 활성 상태: 현재 활성 셀렉터가 `.handbook-filter-btn.active`든 `[aria-pressed="true"]`든 그 규칙을 `color: var(--color-text-primary); font-weight: 600; background: none; border: none;`로 바꾼다. 마크업이 실제로 어느 쪽을 쓰는지 index.astro 스크립트를 확인한다.
  - 아래 규칙을 추가한다. 활성 셀렉터가 `.active`면 `.handbook-filter-btn.active::after`도 같은 선언으로 함께 둔다.
    ```css
    .handbook-filter-btn[aria-pressed="true"]::after {
      content: '';
      position: absolute;
      left: 50%;
      bottom: 0.2rem;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: var(--color-accent);
      transform: translateX(-50%);
    }
    ```
  - 기본 규칙과 `.active` 규칙은 `.handbook-filter-btn, .handbook-difficulty-btn` 그룹이다.
    - 그룹째 수정해도 된다. difficulty 버튼은 어디서도 쓰이지 않는다.
    - 스크립트는 `.active`와 `aria-pressed="true"`를 둘 다 붙인다. 그래서 `::after`는 `[aria-pressed="true"]` 쪽 하나만 있으면 된다.
  - hover 회색 상자를 없애기 위해 다음 규칙을 추가한다.
    ```css
    .handbook-filter-btn:hover {
      background: none;
      border: none;
      color: var(--color-text-primary);
    }
    ```
  - `.handbook-filter-btn .handbook-filter-icon`은 `display: none;`으로 숨긴다. 아이콘 없이 텍스트 탭으로 만든다.
  - `.handbook-filter-row`
    - 이미 가로 스크롤 설정이 있으면 유지한다.
    - `gap: 1.2rem;`, `border-bottom: 1px solid var(--color-border);`

  **3) 많이 찾는 용어 (`.handbook-trending*`)**
  - `.handbook-trending*` 규칙이 **두 번** 정의되어 있다(첫 블록과 바로 뒤의 중복 블록).
    - 두 블록은 `@media (max-width:480px)`까지 똑같다.
    - 두 번째 블록 전체(~11862–11932행)를 삭제하고, 아래 목표 속성은 남은 첫 블록에 적용한다.
  - `.handbook-trending`: 지금은 테두리가 있는 회색 상자다. `border: none; background: none; padding: 0;`으로 바꾼다.
  - `.handbook-trending-list`: `columns: 2`(2단)와 `li { break-inside: avoid }`는 유지한다.
  - `.handbook-trending-title`: `font-family: var(--font-ui); font-size: 0.78rem; font-weight: 700; color: var(--color-text-muted); text-transform: none; letter-spacing: 0;`
  - `.handbook-trending-list`
    - 격자나 카드 형태라면 `display: block;`
    - `background: none; border: none; padding: 0;`
  - `.handbook-trending-list li`: `border-bottom: 1px dotted var(--color-border);`
  - `.handbook-trending-link`
    - `display: grid; grid-template-columns: 1.4rem minmax(0, 1fr); align-items: baseline;`
    - `padding: 0.55rem 0;`, `border: none;`, `border-radius: 0;`, `background: none;`
    - `font-family: var(--font-heading); font-weight: 600;`
  - `.handbook-trending-link::after`(화살표나 장식)과 `:hover::after`는 `content: none;`
  - `.handbook-trending-rank`
    - `font-family: var(--font-heading); font-weight: 700; color: var(--color-accent);`
    - `background: none; width: auto; height: auto; border-radius: 0;`

  **4) 통계와 분야별 목록**
  - `.handbook-hero-stats strong`: `color: var(--color-accent);`
  - 분야 카드 override를 `.handbook-hero-stats-sep` 규칙 뒤에 추가한다. **핸드북 범위로만** 적용하고, 제품 페이지 카드는 그대로 둔다.
    ```css
    /* Handbook "분야별로 보기": dotted list (products keep the card showcase) */
    #handbook-showcase .product-category-showcase-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0 1.5rem;
    }

    #handbook-showcase .product-category-showcase-card {
      background: none;
      border: none;
      border-bottom: 1px dotted var(--color-border);
      border-radius: 0;
      box-shadow: none;
      padding: 0.6rem 0;
      transform: none;
    }

    #handbook-showcase .product-category-showcase-icon,
    #handbook-showcase .product-category-showcase-tags,
    #handbook-showcase .product-category-showcase-desc {
      display: none;
    }

    #handbook-showcase .product-category-showcase-name {
      font-family: var(--font-ui);
      font-size: 0.9rem;
      font-weight: 600;
    }

    @media (max-width: 639px) {
      #handbook-showcase .product-category-showcase-grid {
        grid-template-columns: 1fr;
      }
    }
    ```

- [ ] **Step 4: 통과 확인**

Run: `node frontend/tests/handbook-v2.test.cjs`, 이어서 사전 정보의 "계속 통과해야 하는 테스트"를 모두 돌린다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/handbook-v2.test.cjs
git commit -m "feat: dictionary-style handbook list, dot filters, numbered trending"
```

---

## Chunk 2: 상세

### Task 2: 머리, 한 줄 정의, 수준 선택, 관련 용어, 라벨

**Files:**
- Modify: `frontend/src/pages/ko/handbook/[slug].astro`, `frontend/src/pages/en/handbook/[slug].astro`
  - `.handbook-detail-meta` 안 span의 inline style 제거
  - 수준 라벨이 대문자 영문이면 확인만 하고, 문구는 바꾸지 않는다
- Modify: `frontend/src/components/newsprint/HandbookHeroCard.astro` (정의 박스 스타일)
- Modify: `frontend/src/styles/global.css`
  - 상세 머리: `.handbook-detail-title`(두 규칙 모두), `.handbook-detail-korean`, `.handbook-detail-meta`
  - 수준 스위처: `.handbook-level-switcher`, `.handbook-level-btn*`, 모바일 override
  - 라벨: `.handbook-toc__title`, `.handbook-section-label`
  - 관련 용어: `.hb-related-terms*` 태그
  - `.learning-check`
- Test: `frontend/tests/handbook-v2.test.cjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (`console.log` 위, Edit 도구로)

```js
// Task 2: 상세
for (const p of ['pages/ko/handbook/[slug].astro', 'pages/en/handbook/[slug].astro']) {
  const page = read(p);
  assert(!/handbook-detail-meta[\s\S]{0,400}<span style=/.test(page), `${p} meta spans have no inline styles`);
  assert(page.includes('data-auth-only') && page.includes('learning-check') && page.includes('data-term-id'), `${p} keeps the learning action bar`);
  assert(page.includes('id="level-data"') && page.includes('data-level'), `${p} keeps the level switcher hooks`);
  assert(page.includes('onSessionReady'), `${p} keeps session hydration`);
  assert(page.includes('data-admin-only'), `${p} keeps the admin block`);
}
for (const body of rules('.handbook-detail-title')) {
  assert(!/font-weight:\s*(800|900)/.test(body), 'detail title uses a loaded Hahmlet weight');
}
assert(rule('.handbook-detail-meta').includes('var(--color-accent)'), 'detail category label is accent');
assert(/border:\s*none/.test(rule('.handbook-level-switcher')), 'level switcher has no box border');
assert(rule('.handbook-level-btn--active::after').includes('var(--color-accent)'), 'active level marked by an accent dot');
assert(!rule('.handbook-toc__title').includes('uppercase'), 'toc title not uppercase');
assert(!rule('.handbook-section-label').includes('uppercase'), 'section label not uppercase');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/handbook-v2.test.cjs`
Expected: FAIL. `... meta spans have no inline styles` 또는 상세 관련 첫 단언

- [ ] **Step 3: 마크업 수정**
  - ko/en `[slug].astro`의 `.handbook-detail-meta` 안 카테고리 span에서 `style="font-size:0.8rem;color:var(--color-text-muted)"` 같은 inline style을 지운다. 스타일은 CSS가 맡는다.
  - 헤더 컨테이너의 `style="margin-bottom:1.5rem"`과 h1의 inline margin은 그대로 둔다(레이아웃 간격).
  - `HandbookHeroCard.astro`의 scoped style에서 상자 모양은 `.handbook-hero-card`가 맡고 있다(테두리, `--color-bg-tertiary`, radius 6px). 이 규칙을 다음과 같이 바꾼다.
    - `background: var(--color-bg-secondary);`
    - `border: none; border-radius: 4px; box-shadow: none;`
    - `padding: 1rem 1.15rem;`
    - margin은 그대로 둔다.
  - `.handbook-hero-card__definition`은 텍스트 스타일만 있으므로 그대로 둔다.
  - 컴포넌트 구조와 텍스트도 그대로 둔다.

- [ ] **Step 4: CSS 수정**

  **1) 상세 머리**
  - `.handbook-detail-title`은 두 곳에 나온다.
    - 첫 번째(~1047행)는 `.newsprint-lead-title,\n.handbook-detail-title { scroll-margin-top }` 그룹 규칙이다. **건드리지 않는다.** 바꾸면 뉴스 기사 제목도 함께 바뀐다.
    - 두 번째인 단독 규칙(~7124행)만 `font-family: var(--font-heading); font-weight: 700; letter-spacing: -0.04em; line-height: 1.25;`로 바꾼다. 현재는 800이다.
  - `.handbook-detail-korean`: `font-family: var(--font-ui); font-weight: 400; font-size: 0.5em; color: var(--color-text-muted); margin-left: 0.5rem; letter-spacing: 0;`
  - `.handbook-detail-meta`: `color: var(--color-accent); font-size: 0.78rem; font-weight: 600; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;`
  - `.handbook-detail-meta span:first-child::before`를 추가한다. 내용은 `content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: currentColor; margin-right: 0.4rem; vertical-align: middle;`

  **2) 수준 스위처**
  - 기사 페이지 판 선택과 같은 방식이다(`.persona-switcher*` 4단계 규칙 참고).
  - `.handbook-level-switcher`: `border: none; border-radius: 0; gap: 1.1rem; overflow: visible;`
  - `.handbook-level-btn`
    - `position: relative; border: none; background: transparent;`
    - `padding: 0.4rem 0.1rem 0.55rem;`
    - `color: var(--color-text-muted); font-weight: 500;`
  - `.handbook-level-btn:last-child`: 테두리 관련 선언을 지운다. 비면 규칙째 삭제한다.
  - `.handbook-level-btn--active`: `background: none; color: var(--color-text-primary); font-weight: 600;`. 그리고 다음 규칙을 추가한다.
    ```css
    .handbook-level-btn--active::after {
      content: '';
      position: absolute;
      left: 50%;
      bottom: 0;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: var(--color-accent);
      transform: translateX(-50%);
    }
    ```
  - `.handbook-level-btn:hover:not(.handbook-level-btn--active)`: `color: var(--color-text-primary); background: none;`
  - `@media (max-width: 767px)` 안의 `.handbook-level-btn { padding: 0.25rem 1rem; }`: 이 override를 삭제한다. 기본 규칙과 같게 만든다.

  **3) 라벨**
  - `.handbook-toc__title`: `text-transform` 삭제, `letter-spacing: 0;`
  - `.handbook-section-label`: `text-transform` 삭제, `letter-spacing: 0;`, `color: var(--color-accent);`

  **4) 관련 용어 (`.hb-related-terms`)**
  - `.newsprint-prose .hb-related-terms__tag`(radius 999px, color-mix 틴트)를 바꾼다.
    - `background: none; border: none; border-radius: 0; padding: 0;`
    - `color: var(--color-text-muted); font-size: 0.75rem;`
  - `.newsprint-prose .hb-related-terms > li`: `border-bottom`을 `1px dotted var(--color-border)`로 바꾼다. 지금은 solid다.
  - 관련 용어 HTML은 rehype가 만든다. 마크업은 건드리지 않고 CSS만 바꾼다.

  **5) 학습 완료 버튼**
  - `.learning-check`: `border-radius: 4px; box-shadow: none;`. `inset` 그림자가 있으면 지운다.

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/handbook-v2.test.cjs`, 이어서 사전 정보의 "계속 통과해야 하는 테스트" 전부, `cd frontend && npm run build`.

- [ ] **Step 6: 커밋**

```bash
git add "frontend/src/pages/ko/handbook/[slug].astro" "frontend/src/pages/en/handbook/[slug].astro" frontend/src/components/newsprint/HandbookHeroCard.astro frontend/src/styles/global.css frontend/tests/handbook-v2.test.cjs
git commit -m "feat: soft newsprint handbook detail head, level dots and related terms"
```

---

## Chunk 3: 검증과 문서

### Task 3: 검증 (컨트롤러)
- [ ] 전체 테스트를 기준선과 이름으로 비교한다. 신규 FAIL이 없어야 한다. 빌드가 성공해야 한다.
- [ ] 브라우저(종이·다크 × 1280·375px)로 아래를 확인한다.
  - `/ko/handbook/`
    - 사전 항목
    - 분야 필터: 동작, 점 이동
    - 검색
    - 많이 찾는 용어
    - 분야별 목록
    - 북마크
  - 용어 상세
    - 수준 전환
    - 관련 용어
    - 팝업
    - 게스트 상태에서 학습 버튼과 관리자 블록이 숨겨지는지
  - 카테고리 페이지
  - `/ko/products/`: 분야 카드가 그대로인지

### Task 4: 문서
- [ ] `ACTIVE_SPRINT.md`에 REDESIGN-P6과 증거를 추가한다.
- [ ] 이 계획에 Status와 실행 결과를 적는다.
- [ ] 커밋: `docs: record redesign phase 6 handbook`
