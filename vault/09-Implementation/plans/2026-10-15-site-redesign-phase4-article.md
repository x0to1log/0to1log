# 사이트 리디자인 4단계(뉴스 기사 페이지) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** done (2026-10-15) — 실행 결과는 문서 끝 참조.

**Goal:** 뉴스 기사 페이지를 Soft Newsprint V2로 다듬는다.

**범위:** 기존 2단(본문 + 오른쪽 레일) 구조를 유지하고 다음을 바꾼다.
- 기사 머리: 카테고리 점, 제목, 덱, 태그 위치
- 페르소나를 "입문판·학습판·전문판"으로 표시
- 핵심 팩트를 점선 목록으로 표시
- 섹션 제목
- 기존 본문 용어 하이라이트를 형광펜 스타일로
- 레일 "이 기사의 용어"
- 퀴즈·출처 스타일

**Architecture:** 마크업은 최소로 바꾸고(라벨·순서), 스타일은 `global.css`의 기존 셀렉터를 수정한다. 데이터 로딩, 렌더 파이프라인(rehype), 캐시, 클라이언트 스크립트 로직은 바꾸지 않는다.

**사용자 결정 (2026-10-15):**
1. 레이아웃은 2단을 유지하고 오른쪽 레일만 정리한다. 시안의 3단(왼쪽 목차)은 하지 않는다.
2. 용어 표시는 기존 하이라이트와 팝업을 재스타일한다. 시안의 번호 사이드노트는 하지 않는다.

**Tech Stack:** Astro v5, 순수 Node 테스트(`node frontend/tests/<file>`, repo 루트)

**Spec:** [[2026-10-14-site-redesign-soft-newsprint-design]] §6 뉴스 기사

---

## 사전 정보 (실행자 필독)

### 공유 작업 트리 규칙
- 다른 Claude 세션("Supabase 할당량 최적화")은 기사 파일 작업을 끝내고 넘겨줬다. 그래도 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 수정하지 말고 BLOCKED로 보고한다.
- `src/lib/pageData/*`, `src/middleware.ts`, `src/lib/server/*`, `src/lib/markdown.ts`, `src/lib/rehypeHandbookTerms.ts`, `src/scripts/*`는 수정하지 않는다.
- `git add`는 계획에 적힌 파일만 경로를 지정해서 한다. `-A`/`.`, stash/reset/checkout은 금지다. 샌드박스가 명령을 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 계획에 적힌 그대로 쓴다. `Co-Authored-By`는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 정규식이 들어간 파일은 Write/Edit 도구로 작성한다. Bash heredoc을 쓰면 백슬래시가 사라진다. `global.css`는 줄 번호가 계속 바뀌므로 셀렉터로 찾는다.

### 반드시 유지할 것 (Supabase 세션 인계, 2026-10-14)
- `/en`, `/ko` 페이지의 SSR 출력은 `Astro.locals.user`, `profile`, `isAdmin`에 의존하면 안 된다. 모든 방문자가 같은 HTML을 받는다. `Set-Cookie`, `Vary`는 바꾸지 않는다.
- **NewsprintArticleLayout.astro**
  - 관리자 블록 `<div class="newsprint-admin-actions" ... data-admin-only hidden={!isAdmin}>`
  - `import { onSessionReady } from '../../scripts/session'`
  - `userPicked` 플래그, `setActivePersona(p, { scroll = true } = {})`, `onSessionReady((session) => …session.persona…)` 블록
  - `<template id="persona-data" data-map data-display data-quizzes data-weekly-quizzes data-sources>`
  - `.persona-switcher-btn[data-persona]` + `--active`, `.persona-float-btn[data-persona]`
- **페르소나 값과 라벨**
  - `data-persona` 값은 **beginner / learner / expert 그대로** 둔다.
  - SSR 기본 페르소나는 'learner'다.
  - 라벨은 바꿔도 된다.
- **댓글과 피드백**
  - `.newsprint-comments`와 그 속성 `data-post-id`, `data-content-type`, `data-preview-mode`
  - 안쪽의 `[data-comment-form]`, `[data-comment-login]`
  - `ContentFeedback`(`[data-content-feedback]`)
- **레일 버튼**
  - 북마크 `.newsprint-bookmark-icon[data-item-id][data-item-type]`
  - 좋아요 `[data-like-btn]`와 그 속성 `data-post-id`, `data-content-type`, 안쪽의 `[data-like-count]`
- **news/[slug].astro**
  - `onSessionReady`로 등록된 `recordReadingHistory(session)`
  - `[data-item-id][data-item-type="news"]` 요소가 최소 1개 있어야 한다.
- 위 항목은 `tests/news-persona-cache-policy.test.cjs`가 일부 검사한다.

### 공유 셀렉터 (의도된 사이트 전체 변경)
다음 셀렉터는 기사 페이지 밖에서도 쓰인다. 이번 변경은 사이트 전체의 일관성을 위해 **의도적으로** 함께 바꾼다.
- `.newsprint-section-title`, `.newsprint-rail .newsprint-section-title`: 핸드북 레일, 목록 레일("지금 많이 읽는 글", "편집 노트")
- `.handbook-term`: 핸드북·블로그 본문
- `.newsprint-card-kicker`: 목록 카드와 헤드라인 카드. 목록 쪽은 inline style로 카테고리 색을 쓰므로 색은 유지된다(5단계에서 정리).

Task 4 검증 때 핸드북 상세와 뉴스 목록도 함께 본다.

### 기존 기능 (재사용, 수정 금지)
- 본문 용어 하이라이트는 `rehypeHandbookTerms.ts`가 만든다. 각 용어의 첫 등장에 `<span class="handbook-term" data-slug data-term>`을 씌우고, `handbook-popup.ts`가 클릭 시 팝업을 띄운다. 이번에는 **CSS만** 바꾼다.
- 레일의 관련 용어는 `NewsprintSideRail.astro`의 "이 글의 키워드" 섹션이다. 데이터는 `newsDetailPage.ts`가 본문의 `data-slug`에서 최대 3개를 뽑는다.

### 테스트 기준선
- 비교는 **이름**으로 한다. 기준선(3단계 종료)은 PASS 61 / FAIL 23이다.
- 계속 통과해야 하는 관련 테스트:
  - `news-persona-cache-policy`
  - `news-persona-title-switcher`
  - `news-article-find-structure`
  - `detail-rail-actions-placement`
  - `reading-actions-layout-regression`
  - `reading-actions-editorial-subtle`
  - `public-detail-query-contract`
  - `font-roles`
  - `retro-decoration-removed`
  - `theme-palette`
- 이미 실패하던 `news-fact-pack-structure`, `detail-rail-copy`, `public-slug-visibility`, `sticky-reading-actions-structure`는 이번 범위가 아니다.

---

## Chunk 1: 머리와 판 선택

### Task 1: 페르소나를 "판"으로 표시, 스위처 재스타일

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro` (`personaLabels`, `.switcher-bar-label` 문구)
- Modify: `frontend/src/styles/global.css` (`.switcher-bar-label`, `.persona-switcher`, `.persona-switcher-btn`, `.persona-switcher-btn:last-child`, `.persona-switcher-btn--active`, `.persona-switcher-btn:hover:not(.persona-switcher-btn--active)`)
- Test: `frontend/tests/article-v2.test.cjs` (새 파일, 이후 Task에서 이어서 추가)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/article-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const layout = read('components/newsprint/NewsprintArticleLayout.astro');
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

// Task 1: 판 라벨 + 스위처
assert(/ko:\s*\{\s*beginner:\s*'입문판',\s*learner:\s*'학습판',\s*expert:\s*'전문판'\s*\}/.test(layout), 'ko edition labels');
assert(/en:\s*\{\s*beginner:\s*'Beginner',\s*learner:\s*'Learner',\s*expert:\s*'Expert'\s*\}/.test(layout), 'en labels unchanged');
assert(layout.includes("{locale === 'ko' ? '판 선택' : 'Edition'}"), 'switcher label reads 판 선택 / Edition');
assert(layout.includes("(['beginner', 'learner', 'expert'] as const)"), 'persona values unchanged');
assert(layout.includes('onSessionReady') && layout.includes('session.persona'), 'session persona hydration kept');
assert(!rule('.switcher-bar-label').includes('uppercase'), 'switcher label not uppercase');
assert(/border:\s*none/.test(rule('.persona-switcher')), 'switcher has no box border');
assert(/width:\s*4px/.test(rule('.persona-switcher-btn--active::after')) && rule('.persona-switcher-btn--active::after').includes('var(--color-accent)'), 'active edition marked by an accent dot');

console.log('article-v2.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/article-v2.test.cjs`
Expected: FAIL. `ko edition labels`

- [ ] **Step 3: 마크업 수정** (`NewsprintArticleLayout.astro`)
  - `personaLabels`의 ko 줄을 `ko: { beginner: '입문판', learner: '학습판', expert: '전문판' },`로 바꾼다. en 줄은 그대로 둔다.
  - `<span class="switcher-bar-label">{locale === 'ko' ? '읽기 모드' : 'Reading Mode'}</span>`을 `<span class="switcher-bar-label">{locale === 'ko' ? '판 선택' : 'Edition'}</span>`으로 바꾼다.

- [ ] **Step 4: CSS 수정** (`global.css`)
  - `.switcher-bar-label`에서 `text-transform: uppercase;`를 삭제하고, `letter-spacing: 0.06em;`을 `0.02em`으로 바꾼다.
  - `.persona-switcher`의 `border: 1px solid var(--color-border);`를 `border: none;`으로, `border-radius: var(--radius-md);`를 `border-radius: 0;`으로, `gap: 0;`을 `gap: 1.1rem;`으로 바꾼다. `overflow: hidden;`은 삭제한다(점이 잘리지 않게).
  - `.persona-switcher-btn`을 아래로 교체한다.
    ```css
    .persona-switcher-btn {
      position: relative;
      font-family: var(--font-ui);
      font-size: 0.85rem;
      font-weight: 500;
      padding: 0.4rem 0.1rem 0.55rem;
      background: transparent;
      border: none;
      cursor: pointer;
      color: var(--color-text-muted);
      transition: color 150ms ease;
    }
    ```
  - `.persona-switcher-btn:last-child { border-right: none; }` 규칙을 삭제한다.
  - `.persona-switcher-btn--active`를 아래로 교체하고, 바로 뒤에 `::after` 규칙을 추가한다.
    ```css
    .persona-switcher-btn--active {
      background: none;
      color: var(--color-text-primary);
      font-weight: 600;
    }

    .persona-switcher-btn--active::after {
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
  - `.persona-switcher-btn:hover:not(.persona-switcher-btn--active)`의 본문을 `color: var(--color-text-primary); background: none;`로 바꾼다.
  - `@media (max-width: 767px)` 안의 `.persona-switcher-btn { padding: 0.25rem 1rem; ... }` override(~2176행)에서 padding을 `0.4rem 0.1rem 0.55rem`으로 바꾼다. 그대로 두면 모바일에서 점 위치와 탭 영역이 데스크톱과 달라진다.

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/article-v2.test.cjs && node frontend/tests/news-persona-cache-policy.test.cjs && node frontend/tests/news-persona-title-switcher.test.cjs`
Expected: 모두 통과(exit 0)

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintArticleLayout.astro frontend/src/styles/global.css frontend/tests/article-v2.test.cjs
git commit -m "feat: present news personas as editions with dot marker"
```

### Task 2: 기사 머리, 섹션 제목, 핵심 팩트

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro`
  - 키커의 inline `style` 제거
  - 태그 블록을 덱 아래로 이동
- Modify: `frontend/src/styles/global.css`
  - 키커: `.newsprint-card-kicker`, `.newsprint-card-kicker-type`, `--research`, `--business`
  - 머리: `.newsprint-lead-title`, `.newsprint-divider`
  - 섹션 제목: `.newsprint-section-title`, `.newsprint-rail .newsprint-section-title`
  - 핵심 팩트: `.newsprint-guide-label`, `.newsprint-fact-pack-grid`, `.newsprint-fact-pack-item`, `.newsprint-fact-pack-item p`, `.newsprint-fact-pack-meta`
- Test: `frontend/tests/article-v2.test.cjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (`console.log` 위, Edit 도구로)

```js
// Task 2: 머리 / 섹션 제목 / 핵심 팩트
assert(!/newsprint-article-kicker"\s+style=/.test(layout), 'kicker uses the accent from CSS, no inline category color');
const deckIdx = layout.indexOf('<p class="newsprint-deck">');
const tagsIdx = layout.indexOf('<div class="newsprint-article-tags">');
assert(deckIdx > 0 && tagsIdx > deckIdx, 'tags render below the deck');
assert(!rule('.newsprint-card-kicker').includes('uppercase'), 'kicker not uppercase');
assert(/clip-path:\s*none/.test(rule('.newsprint-card-kicker-type')), 'type badge drops the arrow shape');
assert(!/\n\.newsprint-card-kicker-type::before/.test(css) && css.includes('.newsprint-card-kicker .newsprint-card-kicker-type::before'), 'middle dot only inside a kicker (rails use kicker-type standalone)');
assert(/font-weight:\s*700/.test(rule('.newsprint-lead-title')), 'lead title uses a loaded Hahmlet weight');
assert(/height:\s*1px/.test(rule('.newsprint-divider')), 'divider is a hairline');
assert(!rule('.newsprint-section-title').includes('uppercase'), 'section titles not uppercase');
assert(!rule('.newsprint-guide-label').includes('uppercase'), 'guide labels not uppercase');
assert(/border-bottom:\s*1px dotted/.test(rule('.newsprint-fact-pack-item')), 'fact pack items separated by dotted lines');
assert(/box-shadow:\s*none/.test(rule('.newsprint-fact-pack-item')), 'fact pack items are not cards');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/article-v2.test.cjs`
Expected: FAIL. `kicker uses the accent from CSS, no inline category color`

- [ ] **Step 3: 마크업 수정**
  - 키커 span `<span class="newsprint-card-kicker newsprint-article-kicker" style={`color: ${catColor};`}>`에서 ` style={...}` 속성을 지운다. `catColor` 변수는 다른 곳에서 쓰지 않으면 선언도 지운다(`grep -n catColor`로 확인). 그 결과 `getCategoryColorVar` import가 쓰이지 않게 되면 import도 지운다.
  - `{tags && tags.length > 0 && (...)}` 태그 블록 전체를 잘라서 `{excerpt && <p class="newsprint-deck">{excerpt}</p>}` 바로 아래, `<div class="newsprint-divider"></div>` 위로 옮긴다.

- [ ] **Step 4: CSS 수정**
  - `.newsprint-card-kicker`: `text-transform: uppercase;`를 삭제하고 `letter-spacing: 0.08em;`을 `0;`으로 바꾼다. 아래 선언을 추가한다.
    ```css
      color: var(--color-accent);
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
    ```
    기존 `display: block;`은 삭제한다. 바로 뒤에 규칙을 하나 추가한다.
    ```css
    .newsprint-card-kicker::before {
      content: '';
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
      flex-shrink: 0;
    }
    ```
  - `.newsprint-card-kicker-type`을 아래로 교체한다.
    ```css
    .newsprint-card-kicker-type {
      display: inline-flex;
      align-items: center;
      font-size: 0.72rem;
      font-weight: 500;
      letter-spacing: 0;
      padding: 0;
      margin-left: 0.15rem;
      clip-path: none;
      color: var(--color-text-muted);
    }

    .newsprint-card-kicker .newsprint-card-kicker-type::before {
      content: '·';
      margin-right: 0.3rem;
    }
    ```
    가운뎃점은 키커 안에 있을 때만 붙인다(셀렉터 범위를 좁힘). 레일("다음 읽어볼 글"), `NewsprintListRail`, `HandbookSideRail`은 kicker-type을 단독으로 쓰므로, 범위를 좁히지 않으면 줄 앞에 점이 하나 더 생긴다.
  - `.newsprint-rail-meta .newsprint-card-kicker-type` 규칙(~2364행)의 `font-size`를 `0.68rem`으로, `padding`을 `0`으로 바꾼다.
  - `.newsprint-card-kicker-type--research`와 `--business` 두 규칙의 본문을 모두 `background: none; color: var(--color-text-muted);`로 바꾼다.
  - `.newsprint-lead-title`: `font-weight: 800;` → `700;`, `line-height: 1.16;` → `1.28;`. `letter-spacing: -0.035em;`을 추가한다.
  - `.newsprint-divider`: `height: 3px;` → `1px;`
  - `.newsprint-section-title`을 아래로 교체한다.
    ```css
    .newsprint-section-title {
      font-family: var(--font-heading);
      font-weight: 600;
      font-size: 1.15rem;
      letter-spacing: -0.02em;
      margin-bottom: 0.8rem;
    }
    ```
  - `.newsprint-rail .newsprint-section-title`을 아래로 교체한다.
    ```css
    .newsprint-rail .newsprint-section-title {
      display: block;
      font-family: var(--font-ui);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0;
      color: var(--color-text-muted);
      padding-bottom: 0.4rem;
      border-bottom: 1px solid var(--color-border);
      margin-bottom: 0.75rem;
    }
    ```
  - `.newsprint-guide-label`: `text-transform: uppercase;`를 삭제하고, `letter-spacing: 0.08em;` → `0;`, `font-weight: 600;` → `700;`, `color: var(--color-muted);` → `color: var(--color-accent);`로 바꾼다.
  - 핵심 팩트 규칙을 아래로 교체한다.
    ```css
    .newsprint-fact-pack-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 0;
    }

    .newsprint-fact-pack-item {
      padding: 0.85rem 0;
      border: none;
      border-bottom: 1px dotted var(--color-border);
      background: none;
      box-shadow: none;
    }

    .newsprint-fact-pack-item:last-child {
      border-bottom: none;
    }

    .newsprint-fact-pack-item p {
      margin: 0;
      font-family: var(--font-heading);
      font-size: 1.05rem;
      font-weight: 600;
      line-height: 1.5;
      letter-spacing: -0.02em;
    }

    .newsprint-fact-pack-item p.newsprint-fact-pack-meta {
      margin-top: 0.35rem;
      font-family: var(--font-body);
      font-size: 0.9rem;
      font-weight: 400;
      letter-spacing: 0;
      color: var(--color-text-secondary);
    }
    ```
    기존 `.newsprint-fact-pack-meta { margin-top: 0.6rem !important; ... }` 규칙은 삭제한다. 위의 `p.newsprint-fact-pack-meta`가 대신한다.

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/article-v2.test.cjs && node frontend/tests/retro-decoration-removed.test.cjs && node frontend/tests/font-roles.test.cjs`
Expected: 모두 통과

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintArticleLayout.astro frontend/src/styles/global.css frontend/tests/article-v2.test.cjs
git commit -m "feat: soft newsprint article head, section titles and fact pack"
```

---

## Chunk 2: 용어, 레일, 퀴즈·출처

### Task 3: 용어 하이라이트, 레일 용어 섹션, 퀴즈·출처

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintSideRail.astro` (키워드 섹션 제목)
- Modify: `frontend/src/styles/global.css` (`.handbook-term`, `.handbook-term:hover`, 퀴즈 블록, `.source-card`)
- Test: `frontend/tests/article-v2.test.cjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (`console.log` 위)

```js
// Task 3: 용어 / 레일 / 퀴즈·출처
const rail = read('components/newsprint/NewsprintSideRail.astro');
assert(rail.includes("{isKo ? '이 기사의 용어' : 'Terms in This Article'}"), 'rail term section title');
const term = rule('.handbook-term');
assert(/text-decoration:\s*none/.test(term), 'term highlight drops the dotted underline');
assert(/linear-gradient\(transparent 60%/.test(term), 'term highlight is a highlighter stroke');
assert(css.includes('.newsprint-guide-quiz,\n.newsprint-guide-weekly-quiz {') || /\.newsprint-guide-quiz,\s*\.newsprint-guide-weekly-quiz\s*\{/.test(css), 'quiz blocks get a soft surface');
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.source-card')), 'sources separated by dotted lines');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/article-v2.test.cjs`
Expected: FAIL. `rail term section title`

- [ ] **Step 3: 레일 제목 수정**
  `NewsprintSideRail.astro`의 `{isKo ? '이 글의 키워드' : 'Keywords in This Article'}`를 `{isKo ? '이 기사의 용어' : 'Terms in This Article'}`로 바꾼다.

- [ ] **Step 4: CSS 수정**
  - `.handbook-term`과 `.handbook-term:hover`를 아래로 교체한다.
    ```css
    .handbook-term {
      text-decoration: none;
      cursor: pointer;
      padding: 0 0.05em;
      border-radius: 1px;
      background: linear-gradient(transparent 60%, color-mix(in srgb, var(--color-accent) 22%, transparent) 60%);
      transition: background 0.15s ease, color 0.15s ease;
    }

    .handbook-term:hover {
      background: color-mix(in srgb, var(--color-accent) 18%, transparent);
      color: var(--color-text-primary);
    }
    ```
  - `.newsprint-guide-block:last-child { ... }` 규칙 바로 뒤에 추가한다.
    ```css
    .newsprint-guide-quiz,
    .newsprint-guide-weekly-quiz {
      background: var(--color-bg-secondary);
      border-radius: 4px;
      border-bottom: none;
      padding: 1rem 1.15rem;
      margin-top: 0.75rem;
    }
    ```
  - `.source-card`의 `border-bottom: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);`를 `border-bottom: 1px dotted var(--color-border);`로 바꾼다.

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/article-v2.test.cjs`, 이어서 사전 정보의 "계속 통과해야 하는 관련 테스트" 전부를 실행한다. 그다음 `cd frontend && npm run build`로 에러 0을 확인한다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintSideRail.astro frontend/src/styles/global.css frontend/tests/article-v2.test.cjs
git commit -m "feat: highlighter term marks, rail terms, softer quiz and sources"
```

---

## Chunk 3: 검증과 문서

### Task 4: 검증 (컨트롤러)
- [ ] 전체 테스트를 기준선과 이름으로 비교한다. 신규 FAIL이 없어야 한다.
- [ ] `npm run build` 에러 0을 확인한다.
- [ ] 브라우저에서 확인할 조합
  - 페이지: 뉴스 기사 1개(페르소나 3개 있는 것) ko/en
  - 테마·화면: 종이·다크 × 1280px·375px
- [ ] 확인 항목
  - 판 전환이 동작하는가(본문·제목 교체, 점 이동, 플로팅 버튼)
  - 용어 하이라이트를 클릭하면 팝업이 뜨는가
  - 레일에 "이 기사의 용어"가 보이는가
  - 핵심 팩트, 퀴즈 응답, 출처, 댓글 영역, 좋아요·북마크 버튼이 보이는가
  - 게스트 상태에서 관리자 블록이 숨겨지는가

### Task 5: 문서
- [ ] 스펙 §6 뉴스 기사 항목을 실제 결정으로 갱신한다. 2단 유지, 기존 하이라이트 재스타일, 번호 사이드노트 미적용.
- [ ] `ACTIVE_SPRINT.md`에 REDESIGN-P4 항목과 증거를 추가한다.
- [ ] 이 계획에 Status와 실행 결과를 추가한다.
- [ ] 커밋: `docs: record redesign phase 4 article page`


---

## 실행 결과 (2026-10-15)

- 커밋: `4957ce17` 판 선택, `24a22e3e` 머리·섹션 제목·핵심 팩트, `8fb0ece7` 용어·레일·퀴즈·출처, `a6df5abb` 정리·테스트 보강. 품질 리뷰 승인.
- 검증: 전체 테스트 63 PASS / 23 FAIL(신규 실패 0), `npm run build` 성공(중간 EPERM은 dev 서버의 파일 잠금), 브라우저 확인(판 전환, 용어 팝업, 레일, 게스트 관리자 블록 숨김, 댓글·좋아요·북마크 훅).
- 계획 대비: 퀴즈 위 보더 제거 규칙은 해당 마크업 구조가 없어 생략. 블로그 판 스위처가 같은 스타일을 공유함(의도로 수용).

### 후속 작업
- [ ] 목록 카드의 research/business 라벨이 같은 회색이 됨 → 5단계에서 구분 방식 결정
- [ ] 레일 "이 기사의 용어" 최대 3개 제한(newsDetailPage.ts) — 필요 시 조정
