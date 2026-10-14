# 사이트 리디자인 2단계(공통 헤더·푸터) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 공통 헤더와 푸터를 Soft Newsprint V2로 바꾼다. 제호 마침표, 현재 메뉴 점, 점 줄을 넣고, 페이지 제호의 호수를 자동 계산("제N호")한다.

**Architecture:** 호수 계산은 순수 모듈 `src/lib/issue.js`가 담당한다(DB 조회 없음, KST 기준). 헤더·푸터는 마크업 최소 변경 + `global.css`의 기존 셀렉터 수정으로 처리하고, 점 줄은 헤더 `::after`와 푸터 `::before`가 같은 규칙을 공유한다.

**Tech Stack:** Astro v5, 순수 Node 테스트 스크립트(`node frontend/tests/<file>`, repo 루트에서 실행)

**Spec:** [[2026-10-14-site-redesign-soft-newsprint-design]] §5 (2026-10-14 A안 변경 반영본)

---

## 사전 정보 (실행자 필독)

- **공유 작업 트리:** 다른 Claude 세션("Supabase 할당량 최적화")이 같은 repo에서 작업 중이다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 미커밋 변경이 없는지 확인한다. 있으면 그 파일은 건드리지 말고 BLOCKED로 보고한다.
  - 다음 파일은 **절대 수정하지 않는다**(그 세션의 작업 범위): `src/middleware.ts`, `src/lib/server/*`, `src/lib/pageData/*`, `pages/{en,ko}/**/[slug].astro`, `pages/{en,ko}/**/category/*`, `NewsprintArticleLayout.astro`, `BlogArticleLayout.astro`, `ProductDetail*`, `StickyReadingActions*`.
  - `Navigation.astro`의 세션 하이드레이션 속성은 **반드시 유지**한다: `data-auth-only` / `data-guest-only` / `data-admin-only`와 그 `hidden={...}`, `data-auth-avatar`, `data-label-user`, `data-label-guest`. `MainLayout.astro`의 `import '../scripts/session'`과 body의 `data-ssr-session`도 유지한다.
- `git add`는 계획에 적힌 파일만 경로를 지정해서 한다. `git add -A`/`.`, stash/reset/checkout 금지. 명령이 샌드박스에서 거부되면 우회하지 말고 보고한다.
- 커밋 메시지는 계획에 적힌 그대로. **`Co-Authored-By` 금지.** 브랜치 `main`, push 하지 않는다.
- Bash heredoc과 bash를 통한 python은 이 환경에서 백슬래시를 잃는다. 정규식이 들어간 편집은 Edit 도구로 한다.
- `global.css`의 줄 번호는 계속 바뀐다. 셀렉터 문자열로 찾는다.
- 기준선(2026-10-14, 1단계 종료 시점): 전체 테스트 **PASS 54 / FAIL 23**. FAIL 23개는 1단계 이전부터 실패하던 테스트다. 완료 시 이 23개 외에 새 FAIL이 없어야 한다.

### 확정값
- `ISSUE_EPOCH = '2026-03-18'` (DB `news_posts` 첫 published_at 2026-03-18T09:00Z = KST 18:00). 2026-10-14(KST)는 **제211호**.
- 라벨: ko `제211호`, en `No. 211`.

---

## Chunk 1: 호수 자동 계산

### Task 1: `src/lib/issue.js`

**Files:**
- Create: `frontend/src/lib/issue.js`
- Test: `frontend/tests/issue-number.test.mjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/issue-number.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { ISSUE_EPOCH, issueNumber, issueLabel } = await import(pathToFileURL(path.join(here, '../src/lib/issue.js')).href);

assert.equal(ISSUE_EPOCH, '2026-03-18');

// 창간일 = 1호 (KST 기준)
assert.equal(issueNumber(new Date('2026-03-18T00:00:00+09:00')), 1);
assert.equal(issueNumber(new Date('2026-03-18T23:59:59+09:00')), 1);
assert.equal(issueNumber(new Date('2026-03-19T00:00:00+09:00')), 2);
// UTC로는 전날이어도 KST 날짜를 따른다
assert.equal(issueNumber(new Date('2026-03-18T15:30:00Z')), 2); // KST 3/19 00:30
assert.equal(issueNumber(new Date('2026-10-14T12:00:00+09:00')), 211);
// 창간일 이전 날짜는 1호로 고정
assert.equal(issueNumber(new Date('2026-01-01T12:00:00+09:00')), 1);
// 잘못된 날짜는 null
assert.equal(issueNumber(new Date('invalid')), null);

assert.equal(issueLabel('ko', 211), '제211호');
assert.equal(issueLabel('en', 211), 'No. 211');
assert.equal(issueLabel('ko', null), '');

console.log('issue-number.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/issue-number.test.mjs`
Expected: FAIL. `Cannot find module ... src/lib/issue.js`

- [ ] **Step 3: 구현**

```js
// frontend/src/lib/issue.js
// Newspaper-style issue number: day 1 = first published news (KST).
// Deterministic, no DB access. Used by NewsprintShell's kicker.

/** First published news date in KST (news_posts, 2026-03-18). */
export const ISSUE_EPOCH = '2026-03-18';

const DAY_MS = 24 * 60 * 60 * 1000;
const kstDate = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
});

function dayIndex(ymd) {
  const [y, m, d] = ymd.split('-').map(Number);
  return Date.UTC(y, m - 1, d) / DAY_MS;
}

/** @returns {number|null} 1-based issue number for the KST calendar day of `date` */
export function issueNumber(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return null;
  const diff = dayIndex(kstDate.format(date)) - dayIndex(ISSUE_EPOCH);
  return Math.max(1, diff + 1);
}

/** @param {'ko'|'en'} locale */
export function issueLabel(locale, n) {
  if (n == null) return '';
  return locale === 'ko' ? `제${n}호` : `No. ${n}`;
}
```

- [ ] **Step 4: 통과 확인**

Run: `node frontend/tests/issue-number.test.mjs`
Expected: `issue-number.test.mjs passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/issue.js frontend/tests/issue-number.test.mjs
git commit -m "feat: compute newspaper issue number from launch date"
```

### Task 2: NewsprintShell 키커에 자동 호수 적용, `volume_issue` 제거

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintShell.astro` (Props, 키커 첫 span)
- Modify: `frontend/src/pages/en/news/index.astro`, `frontend/src/pages/ko/news/index.astro`, `frontend/src/pages/en/handbook/index.astro`, `frontend/src/pages/ko/handbook/index.astro` (`volume_issue` 키와 `volumeLabel` prop 제거)
- Modify: `frontend/src/pages/admin/settings.astro` (`volume_issue` 설정 항목 제거: 36행 keys, 42행 필드 정의, 735행 기본값, 753행 그룹 목록)
- Test: `frontend/tests/issue-number-shell.test.cjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/issue-number-shell.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const shell = read('components/newsprint/NewsprintShell.astro');
assert(/import\s*\{[^}]*issueNumber[^}]*\}\s*from\s*['"][./]+lib\/issue\.js['"]/.test(shell), 'NewsprintShell must import issueNumber from lib/issue.js');
assert(shell.includes('issueLabel(locale, issueNumber(displayDate))'), 'kicker must show the issue for the displayed date');
assert(!shell.includes('제01권') && !shell.includes('Vol.01'), 'hardcoded volume label must be removed');
assert(!/volumeLabel/.test(shell), 'volumeLabel prop is obsolete');

for (const p of ['pages/en/news/index.astro', 'pages/ko/news/index.astro', 'pages/en/handbook/index.astro', 'pages/ko/handbook/index.astro', 'pages/admin/settings.astro']) {
  assert(!read(p).includes('volume_issue'), `${p} must not use volume_issue`);
  assert(!read(p).includes('volumeLabel'), `${p} must not pass volumeLabel`);
}
console.log('issue-number-shell.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/issue-number-shell.test.cjs`
Expected: FAIL. `NewsprintShell must import issueNumber from lib/issue.js`

- [ ] **Step 3: NewsprintShell 수정**
  - frontmatter 맨 위(Props 위)에 `import { issueLabel, issueNumber } from '../../lib/issue.js';`를 추가한다.
  - Props에서 `volumeLabel?: string;`를 삭제하고, 구조분해에서 `volumeLabel`을 뺀다.
  - 키커 첫 span을 아래로 바꾼다.
    ```astro
    <span>{issueLabel(locale, issueNumber(displayDate))}</span>
    ```

- [ ] **Step 4: 페이지 4개 수정**
  - `getSiteContents([...])` 키 배열에서 `'volume_issue'`를 삭제한다. 뉴스 페이지 2개에서는 배열의 마지막 항목이므로 앞의 쉼표까지(`, 'volume_issue'`) 지운다.
  - `<NewsprintShell ...>`의 `volumeLabel={sc.volume_issue || undefined}` 줄을 삭제한다.

- [ ] **Step 5: admin/settings.astro 수정**
  `volume_issue`가 나오는 4곳을 삭제한다: `keys` 배열 항목(36행), `{ key: 'volume_issue', ... }` 필드 정의 한 줄(42행), 기본값 객체의 `volume_issue: { ko: '', en: '' },`(735행), 그룹 목록 배열 항목(753행). 각 배열·객체의 쉼표가 깨지지 않게 한다. DB의 `site_content` 행은 건드리지 않는다.

- [ ] **Step 6: 통과 확인**

Run: `node frontend/tests/issue-number-shell.test.cjs && node frontend/tests/newsprint-local-date.test.cjs`
Expected: 둘 다 `passed`

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintShell.astro frontend/src/pages/en/news/index.astro frontend/src/pages/ko/news/index.astro frontend/src/pages/en/handbook/index.astro frontend/src/pages/ko/handbook/index.astro frontend/src/pages/admin/settings.astro frontend/tests/issue-number-shell.test.cjs
git commit -m "feat: show computed issue number in newsprint kicker"
```

---

## Chunk 2: 헤더와 푸터

### Task 3: 공통 헤더 (제호 마침표, 현재 메뉴 점, 점 줄)

**Files:**
- Modify: `frontend/src/components/Navigation.astro` (178행 `<header>`의 inline style, 182–184행 브랜드 링크)
- Modify: `frontend/src/styles/global.css` (`.site-header`, `.site-brand-link`, `.site-page-label`, `.site-nav-pill::after` 계열)
- Test: `frontend/tests/site-header-footer.test.cjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/site-header-footer.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');
const nav = read('components/Navigation.astro');

function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

// 헤더: inline 배경/실선 제거, 제호 마침표
const headerTag = nav.match(/<header class="site-header"[^>]*>/);
assert(headerTag, 'site-header element missing');
assert(!/style=/.test(headerTag[0]), 'site-header must not use inline background/border styles');
assert(/class="site-brand-link"[^>]*>\s*0to1log<span class="site-brand-dot" aria-hidden="true">\.<\/span>/.test(nav), 'brand must render 0to1log + accent period');
assert(rule('.site-header').includes('var(--color-bg-primary)'), 'header uses the page background');
assert(rule('.site-brand-link').includes('var(--color-text-primary)'), 'brand text is ink, not accent');
assert(rule('.site-brand-dot').includes('var(--color-accent)'), 'brand period is accent');

// 점 줄: 헤더 아래 + 푸터 위가 같은 규칙을 공유
assert(/\.site-header::after,\s*\.site-footer::before\s*\{[^}]*radial-gradient/.test(css), 'header/footer share one dot-rule declaration');

// 현재 메뉴 = 점
const active = rule('.site-nav-pill--active::after');
assert(active.includes('var(--color-accent)'), 'active nav dot is accent');
const base = rule('.site-nav-pill::after');
assert(/border-radius:\s*50%/.test(base) && /width:\s*4px/.test(base), 'nav marker is a 4px dot');

// 페이지 라벨: 대문자·넓은 자간 제거
assert(!rule('.site-page-label').includes('uppercase'), 'page label must not be uppercase');

// 세션 하이드레이션 속성 유지
for (const attr of ['data-auth-only', 'data-guest-only', 'data-admin-only', 'data-auth-avatar', 'data-label-user', 'data-label-guest']) {
  assert(nav.includes(attr), `Navigation must keep ${attr}`);
}

console.log('site-header-footer.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/site-header-footer.test.cjs`
Expected: FAIL. `site-header must not use inline background/border styles`

- [ ] **Step 3: Navigation 마크업 수정**
  - 178행 `<header ...>`에서 `style={...}` 속성 전체를 삭제한다. `class`와 `data-always-visible`은 유지한다.
  - 브랜드 링크 내용을 아래로 바꾼다(앞뒤 공백 없이 한 줄).
    ```astro
    <a href={`/${locale}/`} class="site-brand-link">0to1log<span class="site-brand-dot" aria-hidden="true">.</span></a>
    ```

- [ ] **Step 4: 헤더 CSS 수정** (`global.css`)
  - `.site-header { z-index: 100; }`를 아래로 교체하고, 바로 뒤에 점 줄 공유 규칙 2개를 추가한다.
    ```css
    .site-header {
      position: relative;
      z-index: 100;
      background-color: var(--color-bg-primary);
    }

    /* Soft Newsprint dot rule: header bottom edge + footer top edge */
    .site-header::after,
    .site-footer::before {
      content: '';
      position: absolute;
      left: 0;
      right: 0;
      height: 4px;
      background: radial-gradient(circle, var(--color-text-primary) 1px, transparent 1.4px) 0 50% / 6px 4px repeat-x;
      opacity: 0.45;
      pointer-events: none;
    }

    .site-header::after {
      bottom: 0;
    }
    ```
    `.site-header--fixed`의 `position: fixed`는 이 규칙보다 뒤에 있으므로 그대로 이긴다. 순서가 바뀌지 않게 한다.
  - `.site-brand-link`에서 `color: var(--color-accent);`를 `color: var(--color-text-primary);`로, `font-size: 1.25rem;`을 `1.35rem`으로 바꾼다. 그 아래에 추가한다.
    ```css
    .site-brand-dot {
      color: var(--color-accent);
    }
    ```
  - `.site-page-label`에서 `text-transform: uppercase;`를 삭제하고 `letter-spacing: 0.12em;`을 `0.02em`으로 바꾼다.
  - `.site-nav-pill::after`, `.site-nav-pill:hover::after`, `.site-nav-pill--active::after` 세 규칙을 아래로 교체한다.
    ```css
    .site-nav-pill::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 50%;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: transparent;
      transform: translateX(-50%);
      transition: background 150ms ease;
    }

    .site-nav-pill:hover::after {
      background: var(--color-border);
    }

    .site-nav-pill--active::after {
      background: var(--color-accent);
    }
    ```

- [ ] **Step 5: 확인**

Run: `node frontend/tests/site-header-footer.test.cjs`
Expected: 헤더 관련 assert는 통과하고, 점 줄 공유 규칙 assert도 통과한다(`.site-footer::before` 셀렉터는 Step 4에서 추가됨). 푸터 마크업은 Task 4에서 다룬다. 테스트 전체가 통과해야 한다. 실패하면 메시지를 보고 Step 3–4를 고친다.
그리고 기존 테스트를 실행한다: `node frontend/tests/navigation-admin-icon.test.cjs`, `public-locale-cache.test.cjs`, `public-prefetch-budget.test.cjs`, `theme-wiring.test.cjs`, `product-detail-search-sticky.test.cjs` (모두 기준선 PASS. 계속 PASS여야 한다).

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/Navigation.astro frontend/src/styles/global.css frontend/tests/site-header-footer.test.cjs
git commit -m "feat: soft newsprint header with brand period, nav dot and dot rule"
```

### Task 4: 푸터

**Files:**
- Modify: `frontend/src/components/Footer.astro` (전체 마크업)
- Modify: `frontend/src/styles/global.css` (`.newsprint-footer-nav` 수정, `.site-footer*` 추가)
- Test: `frontend/tests/site-header-footer.test.cjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (`console.log` 위)

```js
const footer = read('components/Footer.astro');
assert(/<footer class="site-footer">/.test(footer), 'footer uses .site-footer (no inline styles)');
assert(!/<footer[^>]*style=/.test(footer), 'footer must not use inline styles');
assert(/class="site-footer-brand"[^>]*>0to1log<span class="site-brand-dot" aria-hidden="true">\.<\/span>/.test(footer), 'footer brand renders 0to1log + accent period');
assert(footer.includes('AI 뉴스와 용어를 기록하는 신문'), 'footer shows the ko motto');
assert(rule('.site-footer').includes('var(--color-bg-primary)'), 'footer uses page background');
assert(!rule('.newsprint-footer-nav').includes('uppercase'), 'footer links must not be uppercase');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/site-header-footer.test.cjs`
Expected: FAIL. `footer uses .site-footer (no inline styles)`

- [ ] **Step 3: Footer.astro 마크업 교체**
  frontmatter는 그대로 두고, `<footer ...>`부터 끝까지를 아래로 교체한다.
  ```astro
  <footer class="site-footer">
    <div class="site-footer-inner">
      <a href={`/${locale}/`} class="site-footer-brand">0to1log<span class="site-brand-dot" aria-hidden="true">.</span></a>
      <p class="site-footer-motto">{locale === 'ko' ? 'AI 뉴스와 용어를 기록하는 신문' : 'A newspaper that keeps a record of AI news and terms'}</p>
      <div class="newsprint-footer-nav">
        {links.map((link, i) => (
          <>
            <a href={locale === 'ko' && link.koHref ? link.koHref : link.href}>{locale === 'ko' ? link.ko : link.en}</a>
            {i < links.length - 1 && <span class="newsprint-footer-dot">&middot;</span>}
          </>
        ))}
      </div>
      <p class="site-footer-copy">&copy; {year} 0to1log. All rights reserved.</p>
    </div>
  </footer>
  ```

- [ ] **Step 4: 푸터 CSS**
  - `.newsprint-footer-nav`에서 `text-transform: uppercase;`를 삭제하고, `letter-spacing: 0.08em;` → `0.02em`, `font-weight: 700;` → `600`, `font-size: 0.875rem;` → `0.85rem`, `margin-bottom: 1rem;` → `0.85rem`으로 바꾼다.
  - `/* Footer category nav */` 주석 바로 위에 추가한다.
    ```css
    .site-footer {
      position: relative;
      background-color: var(--color-bg-primary);
      padding: 2.5rem 1rem 2rem;
      text-align: center;
    }

    .site-footer::before {
      top: 0;
    }

    .site-footer-inner {
      max-width: 1280px;
      margin: 0 auto;
    }

    .site-footer-brand {
      font-family: var(--font-masthead);
      font-variant-numeric: lining-nums;
      font-size: 1.35rem;
      font-weight: 500;
      color: var(--color-text-primary);
      text-decoration: none;
    }

    .site-footer-motto {
      margin: 0.35rem 0 1rem;
      font-size: 0.8rem;
      color: var(--color-text-muted);
    }

    .site-footer-copy {
      font-size: 0.8rem;
      color: var(--color-text-muted);
    }
    ```

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/site-header-footer.test.cjs`
Expected: `site-header-footer.test.cjs passed`

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/Footer.astro frontend/src/styles/global.css frontend/tests/site-header-footer.test.cjs
git commit -m "feat: soft newsprint footer with dot rule and motto"
```

---

## Chunk 3: 검증과 문서

### Task 5: 회귀, 빌드, 시각 검증 (컨트롤러가 직접 수행)

- [ ] 전체 테스트: PASS 54 + 신규 3(`issue-number`, `issue-number-shell`, `site-header-footer`) = 57 이상, FAIL은 기준선 23개의 부분집합.
- [ ] `cd frontend && npm run build` 에러 0.
- [ ] 브라우저(종이·화이트·다크 × 1280px·375px): `/ko/`, `/ko/news/`, 뉴스 기사, `/ko/handbook/`.
  - 헤더 마침표·점·점 줄 표시
  - 스크롤 시 헤더 숨김/고정 동작과 배경(고정 상태에서 내용이 비치지 않는지)
  - 키커에 `제211호`(기사는 발행일 기준 호수)
  - 푸터
  - 게스트 상태 사용자 메뉴(로그인 항목만 보이는지), 사용자 드롭다운이 헤더 아래 콘텐츠 위에 제대로 뜨는지(헤더가 `position: relative` + `z-index: 100`이 됨)
  - 헤더가 스크롤로 숨겨졌을 때 화면 맨 위에 점 줄이 남지 않는지
- [ ] 테스트 비교는 개수가 아니라 **이름**으로 한다(다른 세션이 테스트 파일을 추가할 수 있음).

**알려진 한계(수용):** 호수는 서버 렌더 시점의 KST 날짜로 계산되고, 옆의 날짜는 브라우저 시간대로 다시 표시된다. CDN 캐시(s-maxage) 때문에 KST 자정 직후나 해외 독자에게는 잠시 호수와 날짜가 하루 어긋날 수 있다. 의미가 크지 않아 이번 단계에서는 처리하지 않는다.

### Task 6: vault 문서 갱신

- [ ] `vault/08-Design/Design-System.md`에 헤더·푸터 규칙(점 줄, 마침표, 메뉴 점)과 `lib/issue.js`(ISSUE_EPOCH)를 짧게 반영한다.
- [ ] `vault/09-Implementation/plans/ACTIVE_SPRINT.md`의 리디자인 항목에 2단계 완료와 증거(커밋 범위, 테스트·빌드·브라우저 결과)를 추가한다.
- [ ] 이 계획 문서 맨 위에 `**Status:** done (날짜)`와 짧은 "실행 결과"를 추가한다.
- [ ] 커밋: `docs: record redesign phase 2 header and footer`
