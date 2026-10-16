# 기사 상세 B+C(브리핑 먼저 + 짝 기사) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 뉴스 기사 상세를 한 단 집중 지면으로 바꾼다. 구성은 다음과 같다.
- 경로 줄
- 제목
- 같은 날 짝 기사 링크
- 판 선택
- 30초 브리핑
- 본문(오른쪽 세로 액션 막대)
- 끝 블록: 용어, 두 데스크의 시선, 다음 글

**Architecture:**
- 공유 부품은 옵션 prop으로만 확장한다. `NewsprintShell`에 `compact`, `NewsprintArticleLayout`에 `briefingItems`·`sibling`·slot `after-guide`를 추가한다. 다른 페이지는 변화가 없다.
- 짝 기사는 `newsDetailPage.ts`에 쿼리 1개를 추가해 가져온다. KST 날짜 범위는 순수 함수 `deskDayRange`가 계산한다.
- 액션은 기존 인라인 배치(`showStickyActions` 기본 true)를 재사용한다.
- 뉴스 전용 `NewsprintTOC`는 삭제한다.

**Tech Stack:** Astro v5 SSR, Supabase JS, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-10-16-news-article-briefing-design]] — 구현 전에 반드시 읽는다.

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 파일마다 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `pages/admin/pipeline-runs/*`, `publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 stage하지 않는다.
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. trailer(`Co-Authored-By` 등)는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 백슬래시가 있는 파일(정규식이 든 JS/테스트, CSS)은 Write/Edit 도구로만 작성한다. CRLF 파일도 Edit 도구로 수정한다.
- `npm run build`가 EPERM이면 재시도하지 말고 보고한다.

**지켜야 할 것**
- 기사 HTML은 CDN에 캐시된다. 새 코드에서 `Astro.locals`를 쓰지 않는다. 짝 기사 제목은 리터럴 `'learner'`로 해석한다.
- 스크립트가 쓰는 훅은 바꾸지 않는다: `#persona-data`, `.persona-switcher*`, `#persona-float`, `.newsprint-lead-title`, `.newsprint-deck`, `[data-article-find-root]`, `#article-find`, `.handbook-term`, `[data-like-btn]`, `.newsprint-bookmark-icon[data-item-id][data-item-type]`, `.newsprint-share-wrapper`, `.newsprint-comments`, `[data-reading-end]`, `.newsprint-admin-actions`.
- `ReadingActionsRail`, `NewsprintSideRail`, `.newsprint-rail-stack` CSS는 블로그·용어집·관리자가 쓰므로 지우지 않는다.
- 테스트 기준선은 이름 기준 비교다. 신규 FAIL은 0이어야 한다.

---

## Task 1: KST 날짜 범위 함수 (TDD)

**Files:** Modify `frontend/src/lib/newsDesks.js`, `frontend/tests/news-desks-select.test.mjs`

- [ ] **Step 1: 테스트 추가** (Edit 도구로)
  - import 줄을 `const { buildDeskRows, deskDateParts, deskDayRange } = await import(...)`로 바꾼다.
  - `console.log('news-desks-select.test.mjs passed');` 바로 위에 다음을 추가한다.

```js
// KST 하루 범위 (짝 기사 쿼리용)
assert.deepEqual(deskDayRange('2026-10-15'), { start: '2026-10-14T15:00:00.000Z', end: '2026-10-15T15:00:00.000Z' });
assert.equal(deskDayRange(null), null);
assert.equal(deskDayRange('bad'), null);
assert.equal(deskDayRange('2026-13-40'), null);
```

- [ ] **Step 2: 실패 확인** — `node frontend/tests/news-desks-select.test.mjs` → FAIL(`deskDayRange is not a function`)

- [ ] **Step 3: 구현** (Edit 도구로, `newsDesks.js` 파일 끝에 추가)

```js
/** KST calendar day (YYYY-MM-DD) → UTC ISO range [start, end). null for bad input. */
export function deskDayRange(day) {
  if (typeof day !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const start = new Date(`${day}T00:00:00+09:00`);
  if (Number.isNaN(start.getTime()) || kstDay(start) !== day) return null;
  const end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
  return { start: start.toISOString(), end: end.toISOString() };
}
```

(`kstDay(start) !== day`는 `2026-13-40` 같은 날짜가 Date 보정으로 통과하는 것을 막는다.)

- [ ] **Step 4: 통과 확인** — `node frontend/tests/news-desks-select.test.mjs` → PASS

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/newsDesks.js frontend/tests/news-desks-select.test.mjs
git commit -m "feat: add KST day range helper for same-day sibling lookups"
```

---

## Task 2: 짝 기사·브리핑 데이터

**Files:** Modify `frontend/src/lib/pageData/newsDetailPage.ts`; Test `frontend/tests/news-article-data.test.cjs`(새 파일)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/news-article-data.test.cjs
// News detail: same-day sibling (other desk) + briefing fallback flag.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = fs.readFileSync(path.join(__dirname, '..', 'src/lib/pageData/newsDetailPage.ts'), 'utf8');

assert(/export const NEWS_SIBLING_COLUMNS = 'id, slug, title, title_learner, title_beginner, excerpt, post_type, reading_time_min';/.test(src), 'sibling columns constant');
assert(/\.select\(NEWS_SIBLING_COLUMNS\)/.test(src), 'sibling query uses the constant');
assert(/import \{ deskDayRange \} from '\.\.\/newsDesks\.js';/.test(src) && /import \{ kstDay \} from '\.\.\/homeFront\.js';/.test(src), 'KST helpers reused');
assert(/siblingType && siblingRange\s*\?/.test(src), 'query only when a desk type and a valid KST range exist');
assert(/\.eq\('post_type', siblingType\)/.test(src) && /\.gte\('published_at', siblingRange\.start\)/.test(src) && /\.lt\('published_at', siblingRange\.end\)/.test(src), 'other desk, same KST day');
assert(/\.limit\(1\)\s*\.maybeSingle\(\)/.test(src), 'one row, no throw on empty');
assert(/resolveDisplayTitleExcerpt\(siblingRow, 'learner'\)/.test(src), 'sibling title is cache-neutral (learner)');
assert(!/siblingRes\.error[^\n]*503|503[^\n]*siblingRes/.test(src), 'sibling failure never changes the status');
assert(/focusItemsAreFallback/.test(src) && /sibling,/.test(src), 'returns sibling and focusItemsAreFallback');
console.log('news-article-data.test.cjs passed');
```

- [ ] **Step 2: 실패 확인** — `node frontend/tests/news-article-data.test.cjs` → FAIL

- [ ] **Step 3: 구현** (Edit 도구로)
  1. **import**: 파일 상단 import들 아래에 다음을 추가한다.
     ```ts
     import { kstDay } from '../homeFront.js';
     import { deskDayRange } from '../newsDesks.js';
     ```
  2. **상수**: `NEWS_DETAIL_PUBLIC_COLUMNS` 정의 바로 다음에 추가한다.
     ```ts
     export const NEWS_SIBLING_COLUMNS = 'id, slug, title, title_learner, title_beginner, excerpt, post_type, reading_time_min';
     ```
  3. **변수 선언부**(`let sourceCards ...` 다음)에 추가한다.
     ```ts
     let sibling: { slug: string; title: string; excerpt: string | null; post_type: string; reading_time_min: number | null } | null = null;
     let focusItemsAreFallback = true;
     ```
  4. **sibling 조건 계산**: `if (post && publicSupabase) {` 블록 안, `const similarPostsPromise` 앞에 추가한다.
     ```ts
     const siblingType = post.post_type === 'business' ? 'research' : post.post_type === 'research' ? 'business' : null;
     const siblingRange = siblingType && post.published_at ? deskDayRange(kstDay(post.published_at)) : null;
     ```
  5. **병렬 쿼리**
     - 구조분해 배열 끝(`backfillRes,` 다음)에 `siblingRes,`를 추가한다.
     - `Promise.all([...])` 배열 끝(backfill 쿼리 다음)에 다음을 추가한다.
     ```ts
           siblingType && siblingRange
             ? publicSupabase
                 .from('news_posts')
                 .select(NEWS_SIBLING_COLUMNS)
                 .eq('status', 'published')
                 .eq('locale', locale)
                 .eq('post_type', siblingType)
                 .gte('published_at', siblingRange.start)
                 .lt('published_at', siblingRange.end)
                 .order('published_at', { ascending: false })
                 .limit(1)
                 .maybeSingle()
             : Promise.resolve({ data: null, error: null }),
     ```
  6. **결과 처리**: `commentCount = commentCountRes.count ?? 0;` 다음에 추가한다.
     ```ts
         if (siblingRes.error) console.warn('[newsDetailPage] sibling query failed', siblingRes.error.message);
         const siblingRow = siblingRes.error ? null : (siblingRes.data as any);
         if (siblingRow) {
           const shown = resolveDisplayTitleExcerpt(siblingRow, 'learner');
           sibling = {
             slug: siblingRow.slug,
             title: shown.title || siblingRow.title,
             excerpt: shown.excerpt || siblingRow.excerpt || null,
             post_type: siblingRow.post_type,
             reading_time_min: siblingRow.reading_time_min ?? null,
           };
         }
     ```
  7. **fallback 플래그**: focusItems 대입문 바로 다음에 `focusItemsAreFallback = !(post.focus_items && post.focus_items.length > 0);`를 추가한다.
  8. **반환**: return 객체의 `focusItems,` 다음에 `focusItemsAreFallback,`를, `similarPosts,` 다음에 `sibling,`을 추가한다.

- [ ] **Step 4: 통과 확인**

```bash
node frontend/tests/news-article-data.test.cjs
node frontend/tests/public-detail-query-contract.test.cjs
node frontend/tests/news-persona-cache-policy.test.cjs
```
Expected: PASS(`public-detail-query-contract`가 원래 실패 중이면 그대로인지만 확인한다).

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/pageData/newsDetailPage.ts frontend/tests/news-article-data.test.cjs
git commit -m "feat: load the same-day other-desk story and briefing flag for news detail"
```

---

## Task 3: 경로 줄·브리핑·짝 기사·끝 블록 (마크업·페이지·CSS)

**Files:**
- Modify:
  - `frontend/src/components/newsprint/NewsprintShell.astro`
  - `frontend/src/components/newsprint/NewsprintArticleLayout.astro`
  - `frontend/src/pages/ko/news/[slug].astro`, `frontend/src/pages/en/news/[slug].astro`
  - `frontend/src/styles/global.css`
  - `frontend/tests/detail-rail-actions-placement.test.cjs`, `frontend/tests/article-v2.test.cjs`
- Create:
  - `frontend/src/components/newsprint/NewsArticleTerms.astro`
  - `frontend/src/components/newsprint/NewsTwinDesks.astro`
  - `frontend/src/components/newsprint/NewsReadNext.astro`
  - `frontend/tests/news-article-briefing.test.cjs`

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/news-article-briefing.test.cjs
// News detail B+C: crumb shell, no rail, briefing, same-day twin link, end blocks.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/news/[slug].astro`);
  assert(/<NewsprintShell[\s\S]*?compact[\s\S]*?rail=\{false\}/.test(page), `${locale}: compact shell without rail`);
  assert(!page.includes('showStickyActions={false}'), `${locale}: inline reading actions on`);
  assert(!/NewsprintTOC|NewsprintSideRail|ReadingActionsRail|slot="rail"/.test(page), `${locale}: rail removed`);
  assert(page.includes('briefingItems={focusItemsAreFallback ? [] : focusItems}') && page.includes('sibling={sibling}'), `${locale}: briefing + sibling wired`);
  assert(page.includes('slot="after-guide"') && page.includes('<NewsArticleTerms') && page.includes('<NewsTwinDesks'), `${locale}: end blocks in the layout slot`);
  assert(page.includes('<NewsReadNext'), `${locale}: read next`);
  assert(!/masthead=|editionMap|subkicker=/.test(page), `${locale}: no masthead props`);
  assert(page.includes(locale === 'ko' ? "backLabel=\"AI 뉴스\"" : "backLabel=\"AI News\""), `${locale}: crumb label`);
}

const shell = read('components/newsprint/NewsprintShell.astro');
assert(/compact\?: boolean/.test(shell) && /masthead\?: string/.test(shell), 'shell: compact prop, optional masthead');
assert(shell.includes('class="newsprint-crumb"') && shell.includes('newsprint-main--article'), 'shell: crumb + article column');

const layout = read('components/newsprint/NewsprintArticleLayout.astro');
assert(/briefingItems\?: string\[\];/.test(layout) && /sibling\?: \{/.test(layout), 'layout: new optional props');
const idx = ['newsprint-twin-link', 'class="switcher-bar"', 'class="news-briefing"', 'class="newsprint-article-find"'].map((s) => layout.indexOf(s));
assert(idx.every((i) => i > 0) && idx[0] < idx[1] && idx[1] < idx[2] && idx[2] < idx[3], 'order: twin link → edition switcher → briefing → find');
const slotAt = layout.indexOf('<slot name="after-guide" />');
assert(slotAt > layout.indexOf('class="newsprint-guide-items"') && slotAt < layout.indexOf('class="newsprint-sources"'), 'after-guide slot sits between guide items and sources');
for (const s of ['30초 브리핑', '30-second briefing', '리서치 데스크는 이렇게 봤어요', "The research desk's take", '비즈니스 데스크는 이렇게 봤어요', "The business desk's take"]) {
  assert(layout.includes(s), `layout copy: ${s}`);
}

const terms = read('components/newsprint/NewsArticleTerms.astro');
assert(terms.includes("{isKo ? '이 기사의 용어' : 'Terms in This Article'}"), 'terms block title');
const twin = read('components/newsprint/NewsTwinDesks.astro');
for (const s of ['이 소식, 두 데스크의 시선', 'Two desks on this story', '지금 읽은 글', 'You just read']) assert(twin.includes(s), `twin copy: ${s}`);
assert(twin.includes('postTypeLabel(locale, '), 'twin labels from lib/postType.js');
const next = read('components/newsprint/NewsReadNext.astro');
assert(next.includes("{isKo ? '다음 읽어볼 글' : 'Read Next'}") && next.includes('postTypeLabel(locale, '), 'read next title + shared labels');

assert(/\.newsprint-main--article\s*\{[^}]*max-width:\s*800px/.test(css), '800px article column');
assert(/\.news-briefing-list\s*\{[^}]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/.test(css), 'briefing: three columns');
assert(/@media \(max-width: 767px\)\s*\{[^}]*\.news-briefing-list\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\)/.test(css), 'briefing: one column on phones');
assert(/\.newsprint-twin-link--business\s*\{\s*--desk:\s*var\(--tier-paid\);/.test(css) && /\.newsprint-twin-link--research\s*\{\s*--desk:\s*var\(--tier-freemium\);/.test(css), 'twin link desk colours');
console.log('news-article-briefing.test.cjs passed');
```

- [ ] **Step 2: 실패 확인** — `node frontend/tests/news-article-briefing.test.cjs` → FAIL

- [ ] **Step 3: `NewsprintShell.astro` 수정**
  - **Props**
    - `masthead: string;` → `masthead?: string;`
    - 추가: `compact?: boolean;`, `backHref?: string;`, `backLabel?: string;`
    - 구조분해에 `masthead = ''`, `compact = false`, `backHref`, `backLabel`을 넣는다.
  - **`<header class="newsprint-header">...</header>`**를 다음으로 감싼다. header 내용은 바꾸지 않는다.
    ```astro
      {compact ? (
        <nav class="newsprint-crumb" aria-label={isKo ? '위치' : 'Breadcrumb'}>
          <a href={backHref ?? `/${locale}/news/`}>← {backLabel ?? (isKo ? 'AI 뉴스' : 'AI News')}</a>
          <span>{issueLabel(locale, issueNumber(displayDate))}</span>
          <span data-local-date data-date-iso={browserDateIso} data-date-locale={browserLocale}>{dateLabel}</span>
        </nav>
      ) : (
        <header class="newsprint-header">
          ...기존 내용 그대로...
        </header>
      )}
    ```
  - `<div class="newsprint-main">` → `<div class={`newsprint-main${compact ? ' newsprint-main--article' : ''}`}>`
  - inline `<script is:inline nonce={nonce}>`는 그대로 둔다. crumb의 `data-local-date`도 이 스크립트가 갱신한다.

- [ ] **Step 4: `NewsprintArticleLayout.astro` 수정**
  - **Props**(`postType?: string | null;` 다음)에 추가한다.
    ```ts
      briefingItems?: string[];
      sibling?: { slug: string; title: string; excerpt?: string | null; post_type: string; reading_time_min?: number | null } | null;
    ```
  - 구조분해에 `briefingItems = [],`, `sibling = null,`을 추가한다.
  - frontmatter 끝(마지막 const 다음)에 추가한다.
    ```ts
    const siblingDesk = sibling?.post_type === 'research' ? 'research' : 'business';
    const siblingLead = !sibling ? '' : siblingDesk === 'research'
      ? (isKo ? '리서치 데스크는 이렇게 봤어요 →' : "The research desk's take →")
      : (isKo ? '비즈니스 데스크는 이렇게 봤어요 →' : "The business desk's take →");
    ```
  - **이동 + 삽입**
    - `<div class="newsprint-divider"></div>` 바로 다음, `.newsprint-article-find` 앞에 아래 순서로 넣는다.
      1. 짝 링크
      2. 기존 `{showPersonaSwitcher && ( <> switcher-bar ... persona-data template </> )}` 블록. Fact Pack/Core Analysis 뒤 원래 자리에서 잘라 옮긴다. `persona-float` 블록은 원래 자리에 둔다.
      3. 브리핑
    - 넣을 마크업:
    ```astro
      {sibling && (
        <a class={`newsprint-twin-link newsprint-twin-link--${siblingDesk}`} href={`/${locale}/news/${sibling.slug}/`}>
          <span class="newsprint-twin-link-label">{siblingLead}</span>
          <span class="newsprint-twin-link-title">{sibling.title}</span>
        </a>
      )}

      {/* 기존 switcher-bar + persona-data 블록 (이동) */}

      {briefingItems.length > 0 && (
        <section class="news-briefing" aria-label={isKo ? '30초 브리핑' : '30-second briefing'}>
          <p class="news-briefing-label">{isKo ? '30초 브리핑' : '30-second briefing'}</p>
          <ol class="news-briefing-list">
            {briefingItems.slice(0, 3).map((item, i) => (
              <li><span class="news-briefing-num" aria-hidden="true">{i + 1}</span><span>{item}</span></li>
            ))}
          </ol>
        </section>
      )}
    ```
  - **slot**: `{hasSources && (` 바로 앞 줄에 `<slot name="after-guide" />`를 넣는다.

- [ ] **Step 5: 새 컴포넌트 3개 작성** (Write 도구로)

```astro
---
// frontend/src/components/newsprint/NewsArticleTerms.astro
// End-of-article glossary list (was the right-rail "이 기사의 용어").
interface RelatedTerm { slug: string; term: string; koreanName: string; definition: string; }
interface Props { locale: 'en' | 'ko'; terms: RelatedTerm[]; }
const { locale, terms } = Astro.props;
const isKo = locale === 'ko';
---

{terms.length > 0 && (
  <section class="news-article-terms">
    <h2 class="news-end-title">{isKo ? '이 기사의 용어' : 'Terms in This Article'}</h2>
    <ul>
      {terms.slice(0, 3).map((t) => (
        <li>
          <a href={`/${locale}/handbook/${t.slug}/`}>
            <strong class="news-article-term-name">{isKo && t.koreanName ? t.koreanName : t.term}</strong>
            {isKo && t.koreanName && <span class="news-article-term-en">{t.term}</span>}
          </a>
          {t.definition && <p>{t.definition}</p>}
        </li>
      ))}
    </ul>
  </section>
)}
```

```astro
---
// frontend/src/components/newsprint/NewsTwinDesks.astro
// "Two desks on this story": the story just read next to the same-day story from the other desk.
import { postTypeLabel } from '../../lib/postType.js';

interface Sibling { slug: string; title: string; excerpt?: string | null; post_type: string; }
interface Props { locale: 'en' | 'ko'; currentTitle: string; currentType?: string | null; sibling: Sibling | null; }
const { locale, currentTitle, currentType, sibling } = Astro.props;
const isKo = locale === 'ko';
const desk = (type?: string | null) => (type === 'research' ? 'research' : 'business');
---

{sibling && (
  <section class="news-twin-desks">
    <h2 class="news-end-title">{isKo ? '이 소식, 두 데스크의 시선' : 'Two desks on this story'}</h2>
    <div class="news-twin-desks-grid">
      <div class={`news-twin-desk news-twin-desk--${desk(currentType)}`}>
        <span class="news-twin-desk-label">{postTypeLabel(locale, currentType)} · {isKo ? '지금 읽은 글' : 'You just read'}</span>
        <p class="news-twin-desk-title">{currentTitle}</p>
      </div>
      <a class={`news-twin-desk news-twin-desk--${desk(sibling.post_type)}`} href={`/${locale}/news/${sibling.slug}/`}>
        <span class="news-twin-desk-label">{postTypeLabel(locale, sibling.post_type)}</span>
        <p class="news-twin-desk-title">{sibling.title}</p>
        {sibling.excerpt && <p class="news-twin-desk-excerpt">{sibling.excerpt}</p>}
      </a>
    </div>
  </section>
)}
```

```astro
---
// frontend/src/components/newsprint/NewsReadNext.astro
// "Read next" list under the article (was the right-rail block).
import { postTypeLabel } from '../../lib/postType.js';

interface SimilarPost { post_id: string; slug: string; title: string; post_type?: string | null; }
interface Props { locale: 'en' | 'ko'; posts: SimilarPost[]; }
const { locale, posts } = Astro.props;
const isKo = locale === 'ko';
---

{posts.length > 0 && (
  <section class="news-read-next">
    <h2 class="news-end-title">{isKo ? '다음 읽어볼 글' : 'Read Next'}</h2>
    <ul>
      {posts.slice(0, 3).map((p) => (
        <li>
          <a href={`/${locale}/news/${p.slug}/`}>
            {p.post_type && <span class="news-read-next-type">{postTypeLabel(locale, p.post_type)}</span>}
            <span class="news-read-next-title">{p.title}</span>
          </a>
        </li>
      ))}
    </ul>
  </section>
)}
```

- [ ] **Step 6: 페이지 두 개 수정** (ko 먼저, en은 문구만 다르게)
  - **import**
    - `NewsprintTOC`, `NewsprintSideRail`, `ReadingActionsRail` import를 지운다.
    - 다음을 추가한다.
      ```astro
      import NewsArticleTerms from '../../../components/newsprint/NewsArticleTerms.astro';
      import NewsTwinDesks from '../../../components/newsprint/NewsTwinDesks.astro';
      import NewsReadNext from '../../../components/newsprint/NewsReadNext.astro';
      ```
    - 사용하지 않게 되는 `normalizeCategorySlug`·`getCategoryLabel` import는 실제 사용 여부를 확인하고 지운다.
  - **구조분해**: `getNewsDetailPageData` 결과에 `focusItemsAreFallback,`와 `sibling,`을 추가한다.
  - **변수 삭제**: `masthead`, `editionMap`, `editionLabel`
  - **`<NewsprintShell ...>`** 속성을 다음으로 바꾼다.
    ```astro
      <NewsprintShell
        locale="ko"
        compact
        rail={false}
        backHref="/ko/news/"
        backLabel="AI 뉴스"
        publishedAt={post?.published_at}
      >
    ```
    EN은 `locale="en"`, `backHref="/en/news/"`, `backLabel="AI News"`다.
  - **`<NewsprintArticleLayout ... />`**
    - `showStickyActions={false}` 줄을 지운다.
    - 다음 두 줄을 추가한다.
      ```astro
            briefingItems={focusItemsAreFallback ? [] : focusItems}
            sibling={sibling}
      ```
    - self-closing을 열고 닫는 형태로 바꿔 slot 내용을 넣는다.
      ```astro
          >
            <Fragment slot="after-guide">
              <NewsArticleTerms locale="ko" terms={relatedTerms} />
              <NewsTwinDesks locale="ko" currentTitle={displayTitle || post.title} currentType={post.post_type} sibling={sibling} />
            </Fragment>
          </NewsprintArticleLayout>
      ```
  - **다음 글**: weekly 카드 블록 다음 줄에 `{post && <NewsReadNext locale="ko" posts={similarPosts} />}`를 추가한다.
  - **레일**: `<Fragment slot="rail"> ... </Fragment>` 블록 전체를 삭제한다(레일 검색 폼 포함).
  - 모바일 sticky 검색 폼(`handbook-search-sticky--detail`)과 하단 스크립트는 그대로 둔다.

- [ ] **Step 7: CSS 추가**
  - 위치: `global.css`의 `/* News list: two desks (business | date | research) */` 블록 **바로 위**
  - 블록 첫 줄은 `/* News article: crumb, briefing, twin desks, end blocks */`

```css
/* News article: crumb, briefing, twin desks, end blocks */
.newsprint-crumb {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.25rem 0.75rem;
  max-width: 800px;
  margin: 0 auto 1.25rem;
  padding: 1rem 0 0.75rem;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.newsprint-crumb a {
  color: var(--color-text-secondary);
  font-weight: 600;
  text-decoration: none;
}

.newsprint-crumb a:hover {
  color: var(--color-accent);
}

.newsprint-main--article {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.newsprint-twin-link {
  display: block;
  margin: 1rem 0 0.25rem;
  padding: 0.5rem 0 0.5rem 0.85rem;
  border-left: 2px solid var(--desk);
  text-decoration: none;
  color: inherit;
}

.newsprint-twin-link--business {
  --desk: var(--tier-paid);
}

.newsprint-twin-link--research {
  --desk: var(--tier-freemium);
}

.newsprint-twin-link-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--desk);
}

.newsprint-twin-link-title {
  display: block;
  margin-top: 0.2rem;
  font-family: var(--font-heading);
  font-size: 0.98rem;
  font-weight: 600;
  line-height: 1.45;
  letter-spacing: -0.025em;
  transition: color 150ms ease;
}

.newsprint-twin-link:hover .newsprint-twin-link-title {
  color: var(--color-accent);
}

.news-briefing {
  margin: 1.1rem 0 1.5rem;
  padding: 1.1rem 1.25rem 1.2rem;
  background: var(--color-bg-secondary);
  border-radius: 2px;
}

.news-briefing-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-text-muted);
  margin-bottom: 0.75rem;
}

.news-briefing-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 1.25rem;
}

.news-briefing-list li {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--color-text-secondary);
}

.news-briefing-num {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 1.75rem;
  font-weight: 500;
  line-height: 1;
  color: var(--color-accent);
}

.news-end-title {
  font-family: var(--font-heading);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 2rem 0 0.4rem;
  padding-top: 0.6rem;
  border-top: 2px solid var(--color-text-primary);
}

.news-article-terms ul,
.news-read-next ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.news-article-terms li,
.news-read-next li {
  padding: 0.7rem 0;
  border-bottom: 1px dotted var(--color-border);
}

.news-article-terms a,
.news-read-next a {
  color: inherit;
  text-decoration: none;
}

.news-article-term-name {
  font-family: var(--font-heading);
  font-size: 1rem;
  font-weight: 700;
  transition: color 150ms ease;
}

.news-article-term-en {
  margin-left: 0.4rem;
  font-family: var(--font-masthead);
  font-size: 0.92rem;
  color: var(--color-text-muted);
}

.news-article-terms a:hover .news-article-term-name,
.news-read-next a:hover .news-read-next-title {
  color: var(--color-accent);
}

.news-article-terms p {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-twin-desks-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.news-twin-desk {
  display: block;
  padding: 0.9rem 1.2rem 1rem 0;
  color: inherit;
  text-decoration: none;
}

.news-twin-desk + .news-twin-desk {
  padding: 0.9rem 0 1rem 1.2rem;
  border-left: 1px solid var(--color-border);
}

.news-twin-desk--business {
  --desk: var(--tier-paid);
}

.news-twin-desk--research {
  --desk: var(--tier-freemium);
}

.news-twin-desk-label {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--desk);
}

.news-twin-desk-label::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.news-twin-desk-title {
  margin: 0.35rem 0 0.25rem;
  font-family: var(--font-heading);
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: -0.03em;
  transition: color 150ms ease;
}

a.news-twin-desk:hover .news-twin-desk-title {
  color: var(--color-accent);
}

.news-twin-desk-excerpt {
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-read-next-type {
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-accent);
}

.news-read-next-title {
  font-family: var(--font-heading);
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.45;
  letter-spacing: -0.025em;
  transition: color 150ms ease;
}

@media (max-width: 767px) {
  .news-briefing-list {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.6rem;
  }

  .news-briefing-list li {
    flex-direction: row;
    align-items: baseline;
    gap: 0.6rem;
  }

  .news-briefing-num {
    min-width: 1.1rem;
    font-size: 1.3rem;
  }

  .news-twin-desks-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .news-twin-desk {
    padding-right: 0;
  }

  .news-twin-desk + .news-twin-desk {
    padding: 0.9rem 0 1rem;
    border-left: none;
    border-top: 1px dotted var(--color-border);
  }
}
```

- [ ] **Step 8: 기존 테스트 갱신** (Edit 도구로)
  - **`detail-rail-actions-placement.test.cjs`**: 파일을 읽고 뉴스 페이지 단언 4개를 반대로 바꾼다. 블로그·용어집 단언과 CSS 단언은 그대로 둔다.
    - `assertIncludes(newsEn, 'showStickyActions={false}', ...)`와 KO 짝 → `assert(!newsEn.includes('showStickyActions={false}'), 'news EN uses inline reading actions')`(KO 동일)
    - `assertIncludes(newsEn, '<ReadingActionsRail', ...)`와 KO 짝 → `assert(!newsEn.includes('<ReadingActionsRail'), 'news EN has no right rail')`(KO 동일)
    - 파일에 `assert`가 없으면 기존 helper 스타일에 맞춰 `if (...) throw new Error(...)`로 쓴다.
  - **`article-v2.test.cjs`**: `rail term section title` 단언 다음 줄에 추가한다.
    ```js
    assert(read('components/newsprint/NewsArticleTerms.astro').includes("{isKo ? '이 기사의 용어' : 'Terms in This Article'}"), 'end-of-article term title');
    ```

- [ ] **Step 9: 통과 확인** (repo 루트)

```bash
node frontend/tests/news-article-briefing.test.cjs
node frontend/tests/news-article-data.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/article-v2.test.cjs
node frontend/tests/news-persona-title-switcher.test.cjs
node frontend/tests/news-persona-cache-policy.test.cjs
node frontend/tests/news-article-find-structure.test.cjs
node frontend/tests/issue-number-shell.test.cjs
node frontend/tests/hreflang-alt-slug.test.cjs
node frontend/tests/news-list-desks.test.cjs
cd frontend && npm run build
```
- Expected: 모두 PASS, 빌드 "Complete!".
- 단, 원래 실패 중이던 테스트(예: `csp-inline-scripts`, `admin-live-preview`)는 그대로 실패해도 된다. 확장자는 `ls frontend/tests | grep <이름>`으로 확인한다.

- [ ] **Step 10: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintShell.astro frontend/src/components/newsprint/NewsprintArticleLayout.astro frontend/src/components/newsprint/NewsArticleTerms.astro frontend/src/components/newsprint/NewsTwinDesks.astro frontend/src/components/newsprint/NewsReadNext.astro "frontend/src/pages/ko/news/[slug].astro" "frontend/src/pages/en/news/[slug].astro" frontend/src/styles/global.css frontend/tests/news-article-briefing.test.cjs frontend/tests/detail-rail-actions-placement.test.cjs frontend/tests/article-v2.test.cjs
git commit -m "feat: single-column news article with briefing, same-day desk link and end blocks"
```

---

## Task 4: `NewsprintTOC` 삭제

**Files:** Delete `frontend/src/components/newsprint/NewsprintTOC.astro`; Modify `frontend/src/styles/global.css`

- [ ] **Step 1: 사용처 확인**

Run: `grep -rn "NewsprintTOC\|newsprint-toc\|data-newsprint-toc" frontend/src frontend/tests --include=*.astro --include=*.ts --include=*.js --include=*.cjs --include=*.mjs`
Expected: 다음 두 곳 외에는 결과가 없어야 한다. 그 밖의 결과가 있으면 멈추고 보고한다.
- `NewsprintTOC.astro` 자신
- `frontend/tests/news-article-briefing.test.cjs`의 부정 단언(`!/NewsprintTOC|...`)

- [ ] **Step 2: 삭제**
  - `git rm frontend/src/components/newsprint/NewsprintTOC.astro`
  - `global.css`에서 셀렉터에 `newsprint-toc`가 들어간 규칙 블록을 모두 지운다. 미디어쿼리 안의 것도 포함한다. 미디어쿼리가 비게 되면 그 미디어쿼리도 지운다.
  - Run: `grep -n "newsprint-toc" frontend/src/styles/global.css` → 결과 없음

- [ ] **Step 3: 확인** — `node frontend/tests/news-article-briefing.test.cjs` → PASS, `cd frontend && npm run build` → Complete!

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/styles/global.css
git commit -m "chore: remove news-only table of contents replaced by the single-column article"
```

---

## Task 5: 검증 (컨트롤러)

- [ ] 전체 테스트를 기준선과 이름으로 비교한다. 신규 FAIL은 0이어야 한다.
- [ ] 브라우저 매트릭스: 종이·순백·다크 × ≥1024px·375px × ko/en
  - 대상 기사: 비즈니스 기사, 리서치 기사(짝 있음), 주간 정리 기사(짝 없음)
  - 스크린샷
  - 가로 넘침 0
  - 대비 검사(`.newsprint-main--article` 영역)
  - 직접 클릭: 판 전환(제목·요약·본문·퀴즈가 바뀌는지), 용어 하이라이트 클릭 → 팝업, `?q=` 본문 찾기, 북마크 버튼 존재, 공유 메뉴 열림, 댓글 영역, 짝 링크·두 데스크 카드 이동
  - 데스크톱 세로 액션 막대가 본문 오른쪽에 붙어 따라오는지, 모바일 하단 바와 판 float가 겹치지 않는지
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 6: 문서

- [ ] 스펙 Status를 `implemented (2026-10-16)`로, 이 계획에 Status와 실행 결과를 적는다.
- [ ] `ACTIVE_SPRINT.md`에 REDESIGN-NEWS-ARTICLE 항목과 증거를 추가한다.
- [ ] 커밋: `docs: record news article briefing redesign`
