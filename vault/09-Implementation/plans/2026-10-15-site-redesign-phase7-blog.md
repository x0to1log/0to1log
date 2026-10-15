# 사이트 리디자인 7단계(블로그) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** done (2026-10-15) — 실행 결과는 문서 끝 참조.

**Goal:** 블로그를 Soft Newsprint V2로 다듬는다. 바꾸는 범위는 다섯 가지다.
- 사이드바: 둥근 패널과 그림자를 걷어내고 점선 트리로 만든다.
- 카테고리 폴더 카드 줄: 텍스트 탭 + 개수로 바꾼다.
- 추천 글과 목록: 카드를 걷어내고 칼럼 목록으로 만든다.
- 글 상세 머리: 하드코딩된 📘 아이콘을 빼고, 함렛 제목 + 카테고리 점 라벨로 바꾼다.
- 목차 제목: 정리한다.

**카테고리 색 (사용자 결정 B, 2026-10-15):** DB(`blog_categories.color`)에 있는 카테고리 색은 **작은 점에만** 쓴다. 배지 배경, 글자색, 왼쪽 테두리, 아이콘 색에는 쓰지 않는다. 라벨 글자는 기본 텍스트 색을 쓴다.

**Architecture:**
- 컴포넌트는 카테고리 색을 inline `style`로 박아 넣지 않는다. CSS 변수 `--cat-color`만 넘긴다.
- 점 표시(`::before`)가 `background: var(--cat-color, var(--color-accent))`로 그 변수를 읽는다.
- 데이터 로딩과 스크립트 로직은 바꾸지 않는다.

**Tech Stack:** Astro v5, 순수 Node 테스트(`node frontend/tests/<file>`, repo 루트)

**시안:** `.superpowers/brainstorm/phase7/blog.html` B안 (2026-10-15 승인). 마스트헤드 아래 문구 "만들고, 배우고, 기록하는 칼럼"(en: "A column on building, learning and keeping notes")을 추가한다.

---

## 사전 정보 (실행자 필독)

### 공유 작업 트리 규칙
- 파일을 수정하기 전에 `git status --short -- <file>`로 상태를 확인한다. 미커밋 변경이 있으면 수정하지 말고 BLOCKED로 보고한다.
- `git add`는 계획에 적힌 파일만 경로를 지정해서 한다.
  - `-A`, `.`, stash, reset, checkout은 쓰지 않는다.
  - 샌드박스가 명령을 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 계획에 적힌 그대로 쓴다. `Co-Authored-By`는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 정규식이나 백슬래시가 들어간 파일은 Write/Edit 도구로 작성한다. Bash heredoc을 쓰면 백슬래시가 사라진다.
- `global.css`는 LF 줄바꿈이다. 규칙은 줄 번호가 아니라 셀렉터로 찾는다.
- dev 서버가 떠 있으면 `npm run build`가 EPERM으로 실패할 수 있다. 이때는 재시도를 반복하지 말고 보고한다.

### 수정하지 않는 것
- `src/lib/pageData/*`(blogCategories 포함)
- `src/scripts/*`, middleware, `src/lib/server/*`
- 페이지 frontmatter의 데이터 로딩
- `BlogSidebar.astro`의 `Promise.all` 조회. 순차 await로 되돌리지 않는다.

### 반드시 유지할 것 (Supabase 세션 인계)
- `/en`, `/ko` 페이지의 SSR 출력은 `Astro.locals.user`, `profile`, `isAdmin`에 의존하지 않는다.
- **BlogArticleLayout**
  - 관리자 블록 `data-admin-only hidden={!isAdmin}`
  - `.newsprint-comments`와 그 속성(`data-post-id`, `data-content-type`, `data-preview-mode`, `[data-comment-form]`, `[data-comment-login]`)
  - `ContentFeedback` 컴포넌트
  - 페르소나 스위처 구조(`template#persona-data`, `.persona-switcher-btn[data-persona]`)
- **blog/[slug].astro (ko/en)**
  - `onSessionReady`, `recordReadingHistory`
  - `[data-item-id][data-item-type="blog"]` 요소
  - `handbook-terms-data` 스크립트
- **레일**
  - `.newsprint-bookmark-icon[data-item-id][data-item-type]`
  - `[data-like-btn]`(`data-post-id`, `data-content-type="blog"`), `[data-like-count]`
- **카드와 목록**
  - 추천 카드와 목록 항목의 북마크 버튼과 data 속성(`blog-bookmark-card-contract` 테스트가 검사)
  - `.blog-category-badge` 클래스 문자열(`blog-category-badge-font` 테스트가 검사)
- **사이드바**
  - `data-blog-sidebar`, `#blog-sidebar-search`, `#blog-sidebar-results`
  - `.blog-folder-arrow-btn[aria-expanded]`
  - 토글 스크립트가 쓰는 클래스

### 계속 통과해야 하는 테스트
- blog-bookmark-card-contract
- blog-category-badge-font
- blog-comment-fonts
- blog-detail-sidebar-behavior
- blog-detail-sidebar-structure
- blog-mobile-sidebar-structure
- blog-toc-structure
- library-blog-items-contract
- article-v2
- list-v2
- font-roles
- retro-decoration-removed
- theme-palette

### 이미 실패 중인 테스트 (범위 밖)
- blog-section-heading-font
- blog-sidebar-categories
- blog-sidebar-layout
- blog-title-fonts

### 테스트 기준선
- 6단계 종료 시점: PASS 67 / FAIL 23
- 비교는 테스트 이름으로 한다.

---

## Chunk 1: 목록

### Task 1: 카테고리 색 → 점만, 카드 → 칼럼 목록, 폴더 카드 줄 → 탭, 사이드바 정리

**Files:**
- Modify (컴포넌트): `frontend/src/components/blog/BlogFeaturedCard.astro`, `BlogListItem.astro`, `BlogSidebar.astro`
- Modify (페이지): `frontend/src/pages/ko/blog/index.astro`, `frontend/src/pages/en/blog/index.astro`
- Modify (스타일): `frontend/src/styles/global.css` (블로그 블록)
- Test: `frontend/tests/blog-v2.test.cjs` (새 파일)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/blog-v2.test.cjs
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
  return all[all.length - 1];
}

// Task 1: 카테고리 색은 점에만
for (const p of ['components/blog/BlogFeaturedCard.astro', 'components/blog/BlogListItem.astro']) {
  const f = read(p);
  assert(!/style=\{`background:/.test(f) && !/style=\{`color:/.test(f), `${p} has no inline badge/tag colors`);
  assert(f.includes('--cat-color:'), `${p} passes the category color as --cat-color only`);
}
const badge = rule('.blog-category-badge');
assert(/background:\s*none/.test(badge) && !/var\(--cat-color/.test(badge), 'badge text/background do not use the category color');
assert(css.includes('.blog-category-badge::before {') && rule('.blog-category-badge::before').includes('var(--cat-color, var(--color-accent))'), 'category color lives only on the dot');
assert(!/style=\{`color:/.test(read('components/blog/BlogSidebar.astro')), 'sidebar folder icon has no inline color');

// 카드 → 칼럼 목록
const feat = rule('.blog-featured-card');
assert(/border:\s*none/.test(feat) && /border-bottom:\s*1px dotted var\(--color-border\)/.test(feat), 'featured posts are dotted column entries');
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.blog-list-item')), 'list items separated by dotted lines');

// 폴더 카드 줄 → 탭
for (const p of ['pages/ko/blog/index.astro', 'pages/en/blog/index.astro']) {
  const f = read(p);
  assert(f.includes('class="blog-category-tabs"'), `${p} renders category tabs`);
  assert(!f.includes('blog-category-showcase-card'), `${p} drops the folder cards`);
  assert(f.includes('blog-masthead-tagline'), `${p} has the masthead tagline`);
  assert(!f.includes('CATEGORY_ICONS'), `${p} drops the unused showcase icon map`);
}
assert(read('pages/en/blog/index.astro').includes('A column on building, learning and keeping notes'), 'en tagline');
assert(/@media \(max-width: 1023px\)\s*\{[\s\S]*?\.blog-sidebar\s*\{[^}]*background:\s*var\(--color-bg-primary\)/.test(css), 'mobile sidebar drawer keeps an opaque background');

// 사이드바 패널 정리
const sidebar = rule('.blog-sidebar');
assert(/box-shadow:\s*none/.test(sidebar) && /border-radius:\s*0/.test(sidebar), 'sidebar is not a floating rounded panel');
assert(!rule('.blog-folder-btn--group').includes('uppercase'), 'sidebar group labels not uppercase');

console.log('blog-v2.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/blog-v2.test.cjs`
Expected: FAIL. `... has no inline badge/tag colors`

- [ ] **Step 3: 컴포넌트 수정**
  - **BlogFeaturedCard.astro**
    - 카테고리 배지 span의 inline style(`background: color-mix(...)`, `color: ...`)을 `style={`--cat-color: ${catColor}`}`로 바꾼다. 변수명은 기존 색 변수명을 그대로 쓴다.
    - `.blog-mono-tag`의 inline 색 style을 삭제한다.
    - 배지를 감싼 inline flex div는 남겨도 된다.
  - **BlogListItem.astro**
    - `.blog-list-item-category.blog-category-badge`의 inline 색을 `style={`--cat-color: ${...}`}`로 바꾼다.
    - `.blog-list-item-icon` svg에 inline 색이 있으면 삭제한다.
  - **BlogSidebar.astro**
    - `svg.blog-folder-icon`의 inline `color:` style을 삭제한다.
    - `--folder-color` inline 변수는 유지한다. 점에서 쓴다.
    - `Promise.all`과 스크립트는 건드리지 않는다.
  - **index.astro (ko/en)**
    - 마스트헤드 h1 바로 아래에 다음 한 줄을 추가한다. en은 `A column on building, learning and keeping notes`로 쓴다.
      ```astro
      <p class="blog-masthead-tagline">만들고, 배우고, 기록하는 칼럼</p>
      ```
    - `section.blog-category-showcase` 전체를 아래 탭으로 교체한다.
      - 페이지에 `isKo`, `locale` 변수는 **없다**. 경로는 하드코딩한다.
      - 데이터는 `visibleCategories`, 개수는 `postCountByCategory[cat.slug] || 0`이다.
      - ko 페이지:
        ```astro
        <nav class="blog-category-tabs" aria-label="카테고리">
          <a class="blog-category-tab blog-category-tab--active" href="/ko/blog/" aria-current="page">전체</a>
          {visibleCategories.map((cat) => (
            <a class="blog-category-tab" href={`/ko/blog/category/${cat.slug}/`}>
              {cat.label_ko}<span class="blog-category-tab-count">{postCountByCategory[cat.slug] || 0}</span>
            </a>
          ))}
        </nav>
        ```
      - en 페이지는 같은 구조로 쓰되 다음만 다르다: `aria-label="Categories"`, `/en/blog/`, `All`, `cat.label_en`. `label_en`이 비어 있을 수 있으면 기존 en 쇼케이스 코드의 fallback 식을 그대로 쓴다.
    - 쇼케이스에서만 쓰이던 `CATEGORY_ICONS` 상수(ko 42행, en 41행 부근)와 `iconSvg` 관련 줄을 삭제한다.

- [ ] **Step 4: CSS 수정** (블로그 블록. 셀렉터로 찾아 아래 목표 속성으로 바꾸거나 추가한다)

  **사이드바**
  - `.blog-sidebar`(기본 규칙)
    - `border-radius: 0; box-shadow: none; background: none; border: none; border-right: 1px solid var(--color-border);`로 바꾼다.
    - 패딩과 너비는 유지한다.
  - **모바일 슬라이드아웃은 반드시 따로 보정한다.** `@media (max-width: 1023px)` 안의 `.blog-sidebar` 규칙(~9496)은 `position: fixed` 슬라이드아웃이다. 지금은 기본 규칙의 배경에 기대고 있어서, 기본 배경을 없애면 드로어가 투명해져 본문이 비친다. 그 미디어 규칙에 `background: var(--color-bg-primary); border: 1px solid var(--color-border); border-radius: 0.5rem;`을 추가하고, 기존 `box-shadow`는 유지한다.
  - `.blog-sidebar-search-input`: `border-radius: 6px;`
  - `.blog-folder-btn--group`: `text-transform`을 삭제하고 `letter-spacing: 0;`
  - 행 구분선: 카테고리 행 `.blog-folder-header`와 글 행 `.blog-sidebar-link`에 모두 `border-bottom: 1px dotted var(--color-border);`를 적용한다.
    - 둥근 hover 배경이 있으면 `background: none`으로 바꾼다.
    - 활성 상태(`.blog-sidebar-link--active`)는 `font-weight: 600; color: var(--color-text-primary); background: none;`으로 둔다.
  - `.blog-folder-icon`: `display: none;`
  - 대신 점을 추가한다.
    ```css
    .blog-folder-category-link::before {
      content: '';
      flex-shrink: 0;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--folder-color, var(--color-accent));
    }
    ```
    `.blog-folder-category-link`가 flex가 아니면 `display: inline-flex; align-items: center; gap: 0.45rem;`을 추가한다.

  **마스트헤드와 탭**
  - 마스트헤드 아래에 추가한다.
    ```css
    .blog-masthead-tagline {
      text-align: center;
      font-size: 0.8rem;
      color: var(--color-text-muted);
      margin: 0.35rem 0 1rem;
    }

    .blog-category-tabs {
      display: flex;
      flex-wrap: nowrap;
      overflow-x: auto;
      justify-content: center;
      gap: 1.2rem;
      padding: 0.6rem 0 0.75rem;
      border-top: 1px solid var(--color-border);
      border-bottom: 1px solid var(--color-border);
      margin-bottom: 1.25rem;
      scrollbar-width: none;
    }

    .blog-category-tab {
      position: relative;
      flex-shrink: 0;
      white-space: nowrap;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text-muted);
      text-decoration: none;
      padding-bottom: 0.25rem;
    }

    .blog-category-tab:hover {
      color: var(--color-text-primary);
    }

    .blog-category-tab--active {
      color: var(--color-text-primary);
      font-weight: 600;
    }

    .blog-category-tab--active::after {
      content: '';
      position: absolute;
      left: 50%;
      bottom: -0.35rem;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: var(--color-accent);
      transform: translateX(-50%);
    }

    .blog-category-tab-count {
      font-size: 0.72rem;
      margin-left: 0.2rem;
      color: var(--color-text-muted);
    }

    @media (max-width: 639px) {
      .blog-category-tabs {
        justify-content: flex-start;
      }
    }
    ```
  - `.blog-category-showcase*` 규칙(~9547–9600)은 두 index 페이지에서만 쓰이므로 모두 삭제한다. 미디어 쿼리 안에 있는 사본도 함께 삭제한다.

  **카테고리 배지**
  - `.blog-category-badge`: `background: none; border-radius: 0; padding: 0; color: var(--color-text-secondary); display: inline-flex; align-items: center; gap: 0.35rem; font-weight: 600;`
    - `font-family: var(--font-blog-ui)`은 유지한다(테스트가 검사한다).
  - 바로 뒤에 추가한다.
    ```css
    .blog-category-badge::before {
      content: '';
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--cat-color, var(--color-accent));
      flex-shrink: 0;
    }
    ```
  - `.blog-mono-tag`: `background: none; padding: 0; border-radius: 0; color: var(--color-text-muted); font-size: 0.72rem;`
    - `::before { content: '#'; opacity: 0.6; }`도 추가한다.

  **추천 카드**
  - `.blog-featured-card`: `border: none; border-bottom: 1px dotted var(--color-border); border-radius: 0; background: none; box-shadow: none; padding: 0.9rem 0;`
    - hover에 배경이나 테두리 변화가 있으면 `background: none`으로 바꾼다. 제목 색 변화는 유지한다.
  - `.blog-featured-grid`: 2열이면 `gap: 0 1.5rem;`. 카드 사이 세로 간격은 점선이 대신한다.
  - `.blog-featured-card-title`: `font-family: var(--font-blog-heading); font-weight: 600; font-size: 1.05rem; letter-spacing: -0.03em; line-height: 1.4;`

  **목록과 섹션 제목**
  - `.blog-list-item`: `border: none; border-bottom: 1px dotted var(--color-border); border-radius: 0; background: none; box-shadow: none;`
  - `.blog-list-item-title`: `font-family: var(--font-blog-heading); font-weight: 600; letter-spacing: -0.02em;`
  - `.blog-section-header`: 레일 섹션 제목과 같은 형태로 맞춘다.
    - `font-family: var(--font-ui); font-size: 0.78rem; font-weight: 700; color: var(--color-text-muted); letter-spacing: 0; text-transform: none;`
    - `blog-section-heading-font` 테스트는 이미 실패 중이다. 이 변경으로 그 상태가 바뀌어도 신경 쓰지 않는다.

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/blog-v2.test.cjs`, 이어서 사전 정보의 "계속 통과해야 하는 테스트"를 모두 돌린다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/blog/BlogFeaturedCard.astro frontend/src/components/blog/BlogListItem.astro frontend/src/components/blog/BlogSidebar.astro frontend/src/pages/ko/blog/index.astro frontend/src/pages/en/blog/index.astro frontend/src/styles/global.css frontend/tests/blog-v2.test.cjs
git commit -m "feat: soft newsprint blog list with category color dots and column entries"
```

---

## Chunk 2: 상세와 카테고리 페이지

### Task 2: 글 머리, 브레드크럼, 목차, 카테고리 헤더

**Files:**
- Modify: `frontend/src/components/blog/BlogArticleLayout.astro` (📘 아이콘 제거, 카테고리 점 라벨)
- Modify: `frontend/src/components/blog/BlogBreadcrumb.astro` (📘 제거. 경로는 `grep -rl "blog-breadcrumb" frontend/src/components`로 확인)
- Modify: `frontend/src/components/blog/BlogCategoryHeader.astro` (아이콘과 inline 색 정리)
- Modify: `frontend/src/styles/global.css`
- Test: `frontend/tests/blog-v2.test.cjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (`console.log` 위)

```js
// Task 2: 상세
const layout = read('components/blog/BlogArticleLayout.astro');
assert(!layout.includes('📘') && !layout.includes('blog-article-icon'), 'hardcoded 📘 article icon removed');
assert(layout.includes('data-admin-only') && layout.includes('newsprint-comments') && layout.includes('data-comment-form') && layout.includes('ContentFeedback') && layout.includes('id="persona-data"'), 'blog article keeps admin/comments/feedback/persona hooks');
assert(/class="blog-article-category"[^>]*--cat-color/.test(layout), 'article meta shows the category as a color dot label');
assert(!/style=\{`background:/.test(layout), 'article tags have no inline colors');
assert(/font-weight:\s*700/.test(rule('.blog-article-title')), 'article title 700');
assert(!rule('.blog-toc-header').includes('uppercase'), 'toc header not uppercase');
for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro']) {
  const f = read(p);
  assert(f.includes('onSessionReady') && f.includes('recordReadingHistory') && f.includes('handbook-terms-data'), `${p} keeps session/reading-history/terms hooks`);
}
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/blog-v2.test.cjs`
Expected: FAIL. `hardcoded 📘 article icon removed`

- [ ] **Step 3: 마크업 수정**
  - **BlogArticleLayout**
    - `.blog-article-icon` 요소(📘)를 삭제한다.
    - `.blog-article-meta` 안의 카테고리 라벨을 아래 형태로 바꾼다. 실제 변수명을 쓴다. 카테고리 색 변수가 없으면 frontmatter에서 이미 받는 카테고리 데이터에서 색을 꺼내고, 그것도 없으면 `var(--color-accent)`를 쓴다.
      ```astro
      <span class="blog-article-category" style={`--cat-color: ${catColor}`}>{categoryLabel}</span>
      ```
      - `catColor`와 `categoryLabel`은 레이아웃 frontmatter에 이미 있다(~83행). `catColor`의 fallback은 `var(--color-border)`이니, 점이 보이도록 `var(--color-accent)`로 바꾼다.
    - `.blog-mono-tag`의 inline 색은 삭제한다.
    - 관리자 블록, 댓글, 피드백, 페르소나 스위처는 건드리지 않는다.
  - **BlogBreadcrumb**
    - `.blog-breadcrumb-current`의 하드코딩 "📘 "를 삭제한다.
  - **BlogCategoryHeader**
    - 헤더 inline `--category-color`는 유지한다.
    - 아이콘 svg는 `display: none`으로 숨기지 말고, 크기 1rem의 무채색(`color: var(--color-text-muted)`)으로 둔다. 색이 있는 왼쪽 테두리나 배경이 CSS에 있으면 제거한다(Step 4).

- [ ] **Step 4: CSS 수정**
  - `.blog-article-title`: `font-family: var(--font-blog-heading); font-weight: 700; letter-spacing: -0.04em; line-height: 1.3;`
  - `.blog-article-meta`: `font-size: 0.8rem; color: var(--color-text-muted);`
  - `.blog-article-category`를 추가한다. 배지와 같은 점 라벨이다.
    ```css
    .blog-article-category {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-weight: 600;
      color: var(--color-text-secondary);
    }

    .blog-article-category::before {
      content: '';
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--cat-color, var(--color-accent));
    }
    ```
  - `.blog-toc-header`: `text-transform`을 삭제하고 아래로 바꾼다. 모노 글꼴도 버린다.
    - `letter-spacing: 0; font-family: var(--font-ui); font-size: 0.78rem; font-weight: 700; color: var(--color-text-muted);`
  - `.blog-category-header*`
    - 색이 있는 테두리나 배경(`--category-color`를 쓰는 border와 background)은 `border-color: var(--color-border)`와 `background: none`으로 바꾼다.
    - `.blog-category-title`: `font-family: var(--font-blog-heading); font-weight: 700; letter-spacing: -0.04em;`
    - 헤더 아이콘: `color: var(--color-text-muted); width: 1rem; height: 1rem;`
  - 쓰이지 않게 된 `.blog-article-icon` 규칙은 삭제한다.

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/blog-v2.test.cjs`, 이어서 "계속 통과해야 하는 테스트" 전부, 그리고 `cd frontend && npm run build`.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/blog/BlogArticleLayout.astro frontend/src/components/blog/BlogBreadcrumb.astro frontend/src/components/blog/BlogCategoryHeader.astro frontend/src/styles/global.css frontend/tests/blog-v2.test.cjs
git commit -m "feat: soft newsprint blog article head, breadcrumb, toc and category header"
```
Breadcrumb와 CategoryHeader의 경로가 다르면 실제 경로로 바꿔 add한다.

---

## Chunk 3: 검증과 문서

### Task 3: 검증 (컨트롤러)
- [ ] 전체 테스트를 기준선과 이름으로 비교한다. 신규 FAIL이 없어야 하고 빌드가 성공해야 한다.
- [ ] 브라우저 확인 범위: `/ko/blog/`, 블로그 글 1개, 카테고리 페이지 1개, `/en/blog/`. 각각 종이·다크 테마 × 1280px·375px로 본다.
- [ ] 목록 페이지에서 확인할 것
  - 사이드바 트리와 점 색
  - 사이드바 검색
  - 폴더 펼침과 접힘
  - 카테고리 탭 이동
  - 추천 글과 목록
  - 북마크
  - 모바일 사이드바 토글
- [ ] 글 상세와 공통 기능에서 확인할 것
  - 상세 머리, 브레드크럼, 목차
  - 판 선택(있으면)
  - 댓글과 좋아요
  - 게스트일 때 관리자 블록이 숨겨지는지

### Task 4: 문서
- [ ] `ACTIVE_SPRINT.md`에 REDESIGN-P7 항목과 증거를 추가한다.
- [ ] 이 계획에 Status와 실행 결과를 적는다.
- [ ] 스펙 §6에 블로그 카테고리 색 결정(B안)을 적는다.
- [ ] 커밋: `docs: record redesign phase 7 blog`


---

## 실행 결과 (2026-10-15)

- 커밋: `6e3bad16` 목록, `9d213539` 상세, `84ec9daf` 태그 중복·메타 글꼴·사이드바 hover/활성·불필요 변수·모바일 탭 페이드. 품질 리뷰 반영.
- 검증: 전체 테스트 68 PASS / 23 FAIL(신규 실패 0), 빌드 성공, 브라우저 확인.
- 계획 대비: `BlogCategoryHeader`는 CSS만으로 충분해 마크업은 미사용 `--category-color`만 제거. 글 태그 마크업은 `#{tag}`→`{tag}`(CSS가 `#`를 붙임).
