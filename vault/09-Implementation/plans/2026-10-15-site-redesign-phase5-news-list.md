# 사이트 리디자인 5단계(뉴스 목록) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 뉴스 목록 페이지를 Soft Newsprint V2로 다듬는다. 바꾸는 범위는 다음과 같다.
- 카드: 테두리 대신 점선
- 라벨: 색 하나 + 글자로 유형 구분
- 탭: 현재 탭 점
- 태그: `#태그` 글자
- 레일: "최신 기사" + 번호
- 고정 검색창: 배경

**Architecture:**
- 게시물 유형 라벨(비즈니스, 리서치, 주간 정리)을 순수 모듈 `src/lib/postType.js` 하나로 모은다. 지금은 목록 카드, 머리기사, 레일, 홈 1면, 기사 머리 5곳에 흩어져 있다. 머리기사에서 주간 정리가 "Business"로 보이는 버그도 이걸로 고친다.
- 스타일은 `global.css`의 기존 셀렉터를 수정한다. 데이터 로딩과 필터·검색 스크립트는 바꾸지 않는다.

**Tech Stack:** Astro v5, 순수 Node 테스트(`node frontend/tests/<file>`, repo 루트)

**시안:** `.superpowers/brainstorm/phase5/news-list.html` (2026-10-15 사용자 승인)

---

## 사전 정보 (실행자 필독)

### 공유 작업 트리 규칙
- 다른 Claude 세션이 같은 repo에서 작업할 수 있다. 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인하고, 미커밋 변경이 있으면 수정하지 말고 BLOCKED로 보고한다.
- 수정하지 않는 파일: `src/lib/pageData/*`, `src/middleware.ts`, `src/lib/server/*`, `src/scripts/*`, `pages/{en,ko}/news/index.astro`의 데이터 로딩 부분.
- `git add`는 계획에 적힌 파일만 경로를 지정해서 한다. `-A`/`.`, stash/reset/checkout은 금지다. 샌드박스가 명령을 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 계획에 적힌 그대로 쓴다. `Co-Authored-By`는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 정규식이 들어간 파일은 Write/Edit 도구로 작성한다(Bash heredoc을 쓰면 백슬래시가 사라진다). `global.css`는 줄 번호가 계속 바뀌므로 셀렉터로 찾는다.
- dev 서버가 떠 있으면 `npm run build`가 EPERM(파일 잠금)으로 실패할 수 있다. 그 경우 반복 재시도하지 말고 보고한다.

### 유지할 것
- 공개 페이지 SSR 출력은 사용자 정보에 의존하지 않는다.
- 카드의 `data-category`, `data-post-type`, `data-post-id`, `data-search-text` 속성과 `.newsprint-card-stretched-link`를 유지한다. 필터·검색·중복 숨김 스크립트가 쓴다.
- 북마크 버튼 `.newsprint-bookmark-icon[data-item-id][data-item-type]`을 유지한다.
- `.newsprint-card--read` 클래스를 유지한다. 하이드레이션이 붙인다.
- 반드시 통과해야 하는 기존 테스트:
  - `news-search-list-structure`
  - `news-post-type-tab-order`
  - `news-headline-mobile-tags-wrap`(`.newsprint-card-bottom`에 `min-width: 0`, `.newsprint-tags-inline`에 `flex-wrap: wrap`과 `max-width: 100%`)
  - `public-list-personalization`
  - `public-list-query-budget`
  - `product-detail-search-sticky`
  - `home-front-page`
  - `article-v2`
  - `font-roles`
  - `retro-decoration-removed`
  - `theme-palette`

### 공유 셀렉터 (의도된 사이트 전체 변경)
다음 셀렉터는 다른 페이지에서도 함께 바뀐다. 의도된 변경이다.
- `.newsprint-card`: 블로그 추천 카드, 핸드북·기사 레일
- `.newsprint-tag`: 기사 머리 태그
- `.handbook-search-sticky`: 핸드북, 제품 상세

검증 때 함께 확인한다.

### 테스트 기준선
4단계 종료 시점은 PASS 63 / FAIL 23이다(이후 hreflang 테스트 1개 추가). 비교는 개수가 아니라 이름으로 한다.
- `list-rail-copy`는 이미 실패 중이다('Start Here' 단언). 이번에 'Most Read'를 '최신 기사'로 바꾸면 이 테스트가 낡은 문구를 더 많이 단언하게 되지만, 실패 목록 이름은 그대로다. 이 테스트는 고치지 않고 후속으로 남긴다.
- 탭 점은 accent 하나로 통일한다. `NewsprintCategoryFilter`의 `--tab-cat-color` inline 변수는 더 이상 쓰이지 않지만 이번 범위에서는 남겨둔다.

---

## Chunk 1: 유형 라벨 단일화

### Task 1: `src/lib/postType.js` + 5곳 적용 + 카테고리 inline 색 제거

**Files:**
- Create: `frontend/src/lib/postType.js`
- Test: `frontend/tests/post-type-label.test.mjs`
- Modify (컴포넌트):
  - `frontend/src/components/newsprint/NewsprintListCard.astro`
  - `frontend/src/components/newsprint/NewsprintHeadline.astro`
  - `frontend/src/components/newsprint/NewsprintListRail.astro`
  - `frontend/src/components/home/HomeFrontPage.astro`
  - `frontend/src/components/newsprint/NewsprintArticleLayout.astro` (키커 유형 텍스트만)
- Test: `frontend/tests/list-v2.test.cjs` (새 파일, Task 2에서 이어서 추가)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/post-type-label.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { postTypeLabel } = await import(pathToFileURL(path.join(here, '../src/lib/postType.js')).href);

assert.equal(postTypeLabel('ko', 'business'), '비즈니스');
assert.equal(postTypeLabel('ko', 'research'), '리서치');
assert.equal(postTypeLabel('ko', 'weekly'), '주간 정리');
assert.equal(postTypeLabel('en', 'business'), 'Business');
assert.equal(postTypeLabel('en', 'research'), 'Research');
assert.equal(postTypeLabel('en', 'weekly'), 'Weekly');
assert.equal(postTypeLabel('ko', null), '');
assert.equal(postTypeLabel('ko', 'unknown'), '');
console.log('post-type-label.test.mjs passed');
```

```js
// frontend/tests/list-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

// Task 1: 유형 라벨 단일화, inline 카테고리 색 제거
for (const p of [
  'components/newsprint/NewsprintListCard.astro',
  'components/newsprint/NewsprintHeadline.astro',
  'components/newsprint/NewsprintListRail.astro',
  'components/home/HomeFrontPage.astro',
  'components/newsprint/NewsprintArticleLayout.astro',
]) {
  const f = read(p);
  assert(/import \{ postTypeLabel \} from '[./]+lib\/postType\.js'/.test(f), `${p} uses postTypeLabel`);
  assert(!/'Research' : 'Business'|'RESEARCH' : 'BUSINESS'/.test(f), `${p} has no hardcoded type ternary`);
}
for (const p of ['components/newsprint/NewsprintListCard.astro', 'components/newsprint/NewsprintHeadline.astro']) {
  const f = read(p);
  assert(!/newsprint-card-kicker" style=/.test(f), `${p} kicker has no inline category color`);
  assert(f.includes('data-post-type=') && f.includes('newsprint-card-stretched-link'), `${p} keeps filter/search hooks`);
}
assert(!read('components/newsprint/NewsprintHeadline.astro').includes('◆'), 'headline drops the ◆ HEADLINE label');
assert(!/const typeLabel = /.test(read('components/home/HomeFrontPage.astro')), 'home front page uses the shared helper');

console.log('list-v2.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/post-type-label.test.mjs` → FAIL(모듈 없음). `node frontend/tests/list-v2.test.cjs` → FAIL(`... uses postTypeLabel`)

- [ ] **Step 3: 모듈 작성**

```js
// frontend/src/lib/postType.js
// Display label for news post_type. Single source for cards, headlines, rails, home and article head.
const LABELS = {
  ko: { business: '비즈니스', research: '리서치', weekly: '주간 정리' },
  en: { business: 'Business', research: 'Research', weekly: 'Weekly' },
};

/** @param {'ko'|'en'} locale */
export function postTypeLabel(locale, type) {
  const table = LABELS[locale] ?? LABELS.en;
  return (type && Object.prototype.hasOwnProperty.call(table, type)) ? table[type] : '';
}
```

- [ ] **Step 4: 5곳 적용**
  - 각 파일 frontmatter에 `import { postTypeLabel } from '<상대경로>/lib/postType.js';`를 추가한다. 상대경로는 newsprint 컴포넌트에서 `../../lib/postType.js`, home 컴포넌트에서도 `../../lib/postType.js`다.
  - **NewsprintListCard**
    - 키커 span의 ` style={`color: ${catColor};`}`를 지운다.
    - 유형 텍스트 삼항식(`postType === 'weekly' ? 'Weekly' : postType === 'research' ? 'Research' : 'Business'`)을 `postTypeLabel(locale, postType)`으로 바꾼다.
    - 쓰이지 않게 된 `catColor`와 `getCategoryColorVar` import를 지운다.
  - **NewsprintHeadline**
    - 키커 inline 색을 지운다.
    - 유형 텍스트를 `postTypeLabel(locale, postType)`으로 바꾼다. 이로써 weekly가 Business로 보이던 버그가 고쳐진다.
    - `kickerLabel` 상수와 `<span>{kickerLabel}</span>`(◆ 헤드라인)을 지운다.
    - 쓰이지 않게 된 `catColor`와 import를 지운다.
  - **NewsprintListRail**
    - `{post.post_type === 'research' ? 'RESEARCH' : 'BUSINESS'}`를 `{postTypeLabel(locale, post.post_type)}`로 바꾼다.
  - **HomeFrontPage**
    - `const typeLabel = ...` 함수를 지우고, 사용처 `typeLabel(x.post_type)`을 `postTypeLabel(locale, x.post_type) || (isKo ? 'AI 뉴스' : 'AI News')`로 바꾼다. 알 수 없는 유형이면 기존처럼 "AI 뉴스"로 표시하기 위해서다.
    - 이로써 홈 1면의 weekly 라벨이 '위클리'에서 사이트 공통 '주간 정리'로 바뀐다(의도).
    - `frontend/tests/home-front-page.test.cjs`의 weekly 단언(`comp.includes("type === 'weekly'") && comp.includes('위클리')`)도 바꾼다. 새 단언은 `comp.includes('postTypeLabel(locale, ')`이고, 메시지는 `'weekly recaps get their label from lib/postType.js'`로 한다. 이 테스트 파일도 Step 6 커밋에 포함한다.
  - **NewsprintArticleLayout**
    - 키커의 `{postType === 'research' ? 'Research' : 'Business'}`를 `{postTypeLabel(locale, postType)}`로 바꾼다.

- [ ] **Step 5: 통과 확인**

Run:
```bash
node frontend/tests/post-type-label.test.mjs && node frontend/tests/list-v2.test.cjs && node frontend/tests/home-front-page.test.cjs && node frontend/tests/article-v2.test.cjs && node frontend/tests/news-search-list-structure.test.cjs
```
Expected: 모두 exit 0

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/postType.js frontend/tests/post-type-label.test.mjs frontend/tests/list-v2.test.cjs frontend/tests/home-front-page.test.cjs frontend/src/components/newsprint/NewsprintListCard.astro frontend/src/components/newsprint/NewsprintHeadline.astro frontend/src/components/newsprint/NewsprintListRail.astro frontend/src/components/home/HomeFrontPage.astro frontend/src/components/newsprint/NewsprintArticleLayout.astro
git commit -m "feat: single post type label source and accent-only list kickers"
```

---

## Chunk 2: 목록 스타일과 레일

### Task 2: 카드, 머리기사, 탭, 태그, 검색창 CSS + 레일 "최신 기사"

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintListRail.astro` (제목, 번호)
- Modify: `frontend/src/styles/global.css`
- Test: `frontend/tests/list-v2.test.cjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (`console.log` 위, Edit 도구로)

```js
// Task 2: 스타일 + 레일
const railSrc = read('components/newsprint/NewsprintListRail.astro');
assert(railSrc.includes("{isKo ? '최신 기사' : 'Latest'}"), 'rail section is honestly named 최신 기사');
assert(railSrc.includes('class="newsprint-rail-rank"'), 'rail items are numbered');
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.newsprint-card')), 'cards separated by dotted lines');
assert(/background(-color)?:\s*transparent|background(-color)?:\s*none/.test(rule('.newsprint-card:hover')), 'card hover has no background wash');
assert(/font-weight:\s*600/.test(rule('.newsprint-card-title')), 'card title uses Hahmlet 600');
assert(!rule('.newsprint-filter-tab').includes('uppercase'), 'tabs not uppercase');
assert(rule('.newsprint-filter-tab[aria-selected="true"]::after').includes('var(--color-accent)'), 'active tab marked by an accent dot');
assert(css.includes(".newsprint-tags-inline .newsprint-tag,\n.newsprint-article-tags .newsprint-tag {") && css.includes(".newsprint-tags-inline .newsprint-tag::before,\n.newsprint-article-tags .newsprint-tag::before {\n  content: '#';"), 'news/article tags render as #text (scoped: portfolio chips keep their pill)');
assert(/font-weight:\s*700/.test(rule('.newsprint-headline-title')), 'headline title 700');
assert(!rule('.newsprint-headline-kicker').includes('uppercase'), 'headline kicker not uppercase');
assert(rule('.handbook-search-sticky').includes('var(--color-bg-primary)'), 'sticky search has a solid background');
// 기존 계약 유지
assert(/min-width:\s*0/.test(rule('.newsprint-card-bottom')), 'card-bottom keeps min-width: 0');
assert(/flex-wrap:\s*wrap/.test(rule('.newsprint-tags-inline')) && /max-width:\s*100%/.test(rule('.newsprint-tags-inline')), 'tags-inline wrap contract');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/list-v2.test.cjs` → FAIL(`rail section is honestly named 최신 기사`)

- [ ] **Step 3: 레일 마크업**
  - 제목 `{isKo ? '지금 많이 읽는 글' : 'Most Read'}`를 `{isKo ? '최신 기사' : 'Latest'}`로 바꾼다.
  - `posts.map((post) => {` 를 `posts.map((post, index) => {`로 바꾸고, `<a class="newsprint-card" ...>` 안쪽 맨 앞에 `<span class="newsprint-rail-rank" aria-hidden="true">{index + 1}</span>`을 추가한다.
  - 기존 `<strong class="newsprint-rail-link">`와 `<span class="newsprint-rail-meta">`는 새 래퍼 `<span class="newsprint-rail-body">...</span>`로 감싼다.
  - 쓰이지 않는 `starterSections` 관련 코드(`StarterSection` 인터페이스, `getStarterHref`, `defaultStarterSections`, `starterSections`)와 `startHereSections` prop은 **그대로 둔다**. 페이지가 prop을 넘기고 있어서, 지우면 페이지 파일도 바꿔야 하기 때문이다. 대신 이 블록 위에 `// TODO(redesign-p5): starter sections are not rendered; remove with the page prop in a follow-up` 주석 한 줄만 추가한다.

- [ ] **Step 4: CSS 수정** (`global.css`, 셀렉터로 찾기)
  - `.newsprint-card`: `border-bottom: 1px solid var(--color-border);` → `1px dotted var(--color-border);`, `padding: 2rem 0;` → `1.1rem 0;`
  - `.newsprint-card:hover`: 본문을 `background-color: transparent;`로 바꾼다.
  - `.newsprint-card-title`: `font-family: var(--font-display);` → `var(--font-heading);`, `font-weight: 700;` → `600;`, `font-size: 1.3rem;` → `1.15rem;`, `line-height: 1.25;` → `1.4;`. `letter-spacing: -0.03em;`을 추가한다.
  - `.newsprint-excerpt`: `font-size: 0.95rem;` → `0.9rem;`, `line-height: 1.6;` → `1.65;`
  - `.newsprint-card-bottom`: `font-size: 0.82rem;` → `0.75rem;`, `color` → `var(--color-text-muted)`. `min-width: 0;`은 유지한다.
  - `.newsprint-tag`와 `.newsprint-tag:hover` 기본 규칙은 **그대로 둔다**. portfolio 페이지가 기술 칩으로 쓰고 있어서 알약 모양을 유지해야 한다.
  - 기본 규칙 뒤에 뉴스 범위 규칙을 추가한다.
    ```css
    .newsprint-tags-inline .newsprint-tag,
    .newsprint-article-tags .newsprint-tag {
      font-size: 0.72rem;
      color: var(--color-text-muted);
      letter-spacing: 0;
      background: none;
      padding: 0;
      border-radius: 0;
    }

    .newsprint-tags-inline .newsprint-tag::before,
    .newsprint-article-tags .newsprint-tag::before {
      content: '#';
      opacity: 0.6;
    }

    .newsprint-tags-inline .newsprint-tag:hover,
    .newsprint-article-tags .newsprint-tag:hover {
      color: var(--color-text-secondary);
      background: none;
    }
    ```
  - `.newsprint-tags-inline`: `gap: 0.3rem;` → `gap: 0.15rem 0.55rem;` (`flex-wrap`과 `max-width`는 유지)
  - `.newsprint-filter-tabs`: `gap: 0;` → `gap: 1.4rem;`
  - `.newsprint-filter-tab`을 아래로 교체한다.
    ```css
    .newsprint-filter-tab {
      position: relative;
      padding: 0.6rem 0.1rem 0.75rem;
      font-size: 0.9rem;
      font-weight: 500;
      letter-spacing: 0;
      color: var(--color-text-muted);
      background: none;
      border: none;
      cursor: pointer;
      transition: color 150ms ease;
      font-family: var(--font-ui);
    }
    ```
  - `.newsprint-filter-tab[aria-selected="true"]`의 본문을 `color: var(--color-text-primary); font-weight: 600;`으로 바꾸고, 바로 뒤에 추가한다.
    ```css
    .newsprint-filter-tab[aria-selected="true"]::after {
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
  - `@media (max-width: 767px)` 안의 `.newsprint-filter-tab { font-size: 0.75rem; padding: 0.5rem 1.5rem; letter-spacing: 0.06em; }`를 `font-size: 0.85rem; padding: 0.5rem 0.1rem 0.7rem; letter-spacing: 0;`으로 바꾼다.
  - `.newsprint-headline`: `border-top: 1px solid var(--color-border);` → `border-top: none;`, `border-bottom: 1px solid var(--color-border);` → `1px solid var(--color-text-primary);`
  - `.newsprint-headline:hover`: 본문을 `background: transparent;`로 바꾼다.
  - `.newsprint-headline-kicker`: `text-transform: uppercase;`를 삭제하고, `letter-spacing: 0.1em;` → `0;`, `color` → `var(--color-text-muted)`
  - `.newsprint-headline-title`: `font-size: clamp(2rem, 4vw, 3rem);` → `clamp(1.5rem, 1rem + 1.6vw, 1.9rem);`, `font-weight: 900;` → `700;`, `line-height: 1.15;` → `1.3;`. `letter-spacing: -0.04em;`을 추가한다.
  - `.newsprint-headline-deck`: `font-size: clamp(1rem, 1.5vw, 1.2rem);` → `0.95rem;`, `line-height: 1.5;` → `1.7;`
  - 레일
    - `.newsprint-rail-link`: `font-weight: 700;` → `600;`, `font-family: var(--font-display);` → `var(--font-heading);`. `font-size: 0.9rem; letter-spacing: -0.02em;`을 추가한다.
    - `.newsprint-rail-date`: `color: var(--color-accent);` → `var(--color-text-muted);`
    - `.newsprint-rail-meta`: `justify-content: space-between;` → `flex-start;`. `gap: 0.4rem; font-size: 0.72rem; color: var(--color-text-muted);`을 추가한다(`font-size: 0.8rem`은 교체).
    - `.newsprint-rail-meta` 규칙 뒤에 추가한다.
      ```css
      .newsprint-stack > a.newsprint-card:has(.newsprint-rail-rank) {
        display: grid;
        grid-template-columns: 1.4rem minmax(0, 1fr);
        gap: 0.25rem;
        border-bottom: 1px dotted var(--color-border);
      }

      .newsprint-stack > a.newsprint-card:has(.newsprint-rail-rank):last-child {
        border-bottom: none;
      }

      .newsprint-rail-rank {
        font-family: var(--font-heading);
        font-weight: 700;
        font-size: 0.95rem;
        line-height: 1.4;
        color: var(--color-accent);
      }
      ```
  - 고정 검색창 `.handbook-search-sticky`: `background: transparent;` → `background: var(--color-bg-primary);`
  - `body:has(.site-header--fixed:not(.site-header--hidden)) .handbook-search-sticky`의 `top: calc(var(--header-h, 4rem) + 0.25rem);` → `top: var(--header-h, 4rem);`. 이 셀렉터 문자열은 그대로 둔다. `product-detail-search-sticky` 테스트가 검사한다.

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/list-v2.test.cjs`. 이어서 사전 정보의 "반드시 통과해야 하는 기존 테스트" 전부를 실행하고, 마지막으로 `cd frontend && npm run build`를 실행한다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintListRail.astro frontend/src/styles/global.css frontend/tests/list-v2.test.cjs
git commit -m "feat: soft newsprint news list cards, tabs, tags, rail and sticky search"
```

---

## Chunk 3: 검증과 문서

### Task 3: 검증 (컨트롤러)
- [ ] 전체 테스트를 기준선과 이름으로 비교한다. 신규 FAIL이 없어야 한다. `npm run build`는 dev 서버를 끈 뒤 실행한다.
- [ ] 브라우저 확인 범위
  - `/ko/news/`, `/en/news/`
  - 종이·다크 × 1280px·375px
- [ ] 브라우저 확인 항목
  - 탭 필터(비즈니스, 리서치, 주간 정리)와 머리기사 전환
  - 검색
  - 머리기사·카드 라벨(주간 정리가 "주간 정리"로 보이는지)
  - 읽은 글 표시
  - 북마크 버튼
  - 레일 번호
  - 스크롤 시 고정 검색창 아래로 본문이 비치지 않는지
- [ ] 공유 셀렉터 영향 확인
  - 블로그 목록
  - 핸드북 상세 레일
  - 기사 레일
  - 제품 상세 검색창

### Task 4: 문서
- [ ] `ACTIVE_SPRINT.md`에 REDESIGN-P5 항목과 증거를 추가한다.
- [ ] 이 계획에 Status와 실행 결과를 추가한다.
- [ ] 2단계·4단계 후속으로 남겨둔 다음 두 항목을 "해결"로 표시한다.
  - 투명한 고정 검색창
  - research/business 색 구분
- [ ] 커밋: `docs: record redesign phase 5 news list`
