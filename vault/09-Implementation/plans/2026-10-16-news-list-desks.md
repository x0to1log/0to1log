# 뉴스 목록 두 데스크(E안) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/ko/news/`, `/en/news/` 목록을 "비즈니스 데스크 | 날짜 축 | 리서치 데스크" 지면으로 바꾼다. 탭이나 검색을 쓰면 한 단 목록으로 전환된다.

**Architecture:**
- 날짜별 묶기는 순수 함수 `lib/newsDesks.js`가 맡는다.
- 새 컴포넌트 `NewsDeskList`/`NewsDeskCell`은 기존 카드 계약(`.newsprint-card` + data 속성 4개)을 지킨다. 그래서 필터·검색·북마크 스크립트를 그대로 쓴다.
- 새 스크립트 `newsDeskMode.ts`는 표시 모드와 빈 줄만 처리한다.
- 쓰지 않게 되는 헤드라인·카드·레일 컴포넌트와 스크립트는 지운다.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`. 일부 테스트가 `process.cwd()` 기준 경로를 쓴다)

**Spec:** [[2026-10-16-news-list-desks-design]] — 구현 전에 반드시 읽는다.

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `pages/admin/pipeline-runs/*`, `publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 stage하지 않는다.
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 백슬래시가 있는 파일(정규식 테스트, CSS)은 Write/Edit 도구로만 작성한다. Bash heredoc을 쓰면 백슬래시가 사라진다.
- `global.css`는 LF이고, 규칙은 셀렉터로 찾는다.
- dev 서버 때문에 `npm run build`가 EPERM으로 실패하면 재시도하지 말고 보고한다.

**지켜야 할 것**
- 목록은 CDN에 캐시된다. 새로 `Astro.locals.user`를 쓰지 않는다. 기존 persona 해석(`getEffectivePersona(Astro.locals.profile)`)은 그대로 둔다.
- 북마크 버튼은 항상 `data-bookmarked="false"`로 렌더한다(현행과 같다).
- 쿼리는 그대로 둔다(일간 `.limit(100)`, 주간 `.limit(20)`, `POSTS_FIELDS`, 503 처리).
- 테스트 기준선은 PASS 70 / FAIL 23이다. 이번 작업에서 이미 실패 중인 `list-rail-copy`, `list-meta-order`를 삭제하므로 완료 후 기대값은 **FAIL 21, 신규 FAIL 0**이다.

**현재 코드**
- `frontend/src/pages/{ko,en}/news/index.astro`(각 234줄. 두 파일은 문구만 다르다)
  - `NewsprintHeadline` ×3 + `NewsprintListCard` 그리드 + `NewsprintListRail`
  - 스크립트 4개 import: `bookmark`, `handbookSearchHints`, `newsListSearch`, `newsListMultiHeadline`
- `NewsprintCategoryFilter`: `.newsprint-card[data-category]`에 `data-filtered`를 붙이고 `newsprint:filter-change`를 발행한다.
- `scripts/newsListSearch.ts`: `#news-list-results` 안의 `.newsprint-card[data-search-text]`에 `data-search-matched`를 붙인다.
- `kstDay`는 `lib/homeFront.js`에, `issueLabel`/`issueNumber`는 `lib/issue.js`에, `postTypeLabel`은 `lib/postType.js`에 있다.
- 데스크 색 토큰 `--tier-paid`, `--tier-freemium`은 `global.css`에 이미 있다(종이·순백 공용 + 다크 재정의).

---

## Task 1: 날짜별 묶기 순수 함수 (TDD)

**Files:**
- Create: `frontend/src/lib/newsDesks.js`
- Test: `frontend/tests/news-desks-select.test.mjs`

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/news-desks-select.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { buildDeskRows, deskDateParts } = await import(pathToFileURL(path.join(here, '../src/lib/newsDesks.js')).href);

const NOW = new Date('2026-10-15T12:00:00+09:00');
const p = (slug, post_type, published_at) => ({ slug, post_type, published_at });

// 2:2, 오늘 표시, KST 날짜 내림차순, 입력 순서 무관
let rows = buildDeskRows([
  p('r14', 'research', '2026-10-14T00:00:00+00:00'),
  p('b15', 'business', '2026-10-15T00:00:00+00:00'),
  p('r15', 'research', '2026-10-15T00:00:00+00:00'),
  p('b14', 'business', '2026-10-14T00:00:00+00:00'),
], NOW);
assert.deepEqual(rows.map((r) => [r.kind, r.day, r.showDate, r.isToday, r.business?.slug ?? null, r.research?.slug ?? null]), [
  ['day', '2026-10-15', true, true, 'b15', 'r15'],
  ['day', '2026-10-14', true, false, 'b14', 'r14'],
]);

// KST 경계: 2026-10-14T15:30Z = 10월 15일 00:30 KST
rows = buildDeskRows([p('late', 'business', '2026-10-14T15:30:00+00:00')], NOW);
assert.equal(rows[0].day, '2026-10-15');

// 2:1 → 같은 날 두 줄, 둘째 줄은 날짜 숨김, 짝 없는 쪽 null. 같은 유형은 최신이 먼저
rows = buildDeskRows([
  p('b-early', 'business', '2026-09-22T00:00:00+00:00'),
  p('b-late', 'business', '2026-09-22T06:00:00+00:00'),
  p('r', 'research', '2026-09-22T00:00:00+00:00'),
], NOW);
assert.deepEqual(rows.map((r) => [r.showDate, r.business?.slug ?? null, r.research?.slug ?? null]), [
  [true, 'b-late', 'r'],
  [false, 'b-early', null],
]);

// 0:1 → 비즈니스 칸 null
rows = buildDeskRows([p('only-r', 'research', '2026-09-21T00:00:00+00:00')], NOW);
assert.equal(rows[0].business, null);
assert.equal(rows[0].research.slug, 'only-r');

// 주간 정리는 같은 날 day row보다 앞
rows = buildDeskRows([
  p('b20', 'business', '2026-09-20T00:00:00+00:00'),
  p('w20', 'weekly', '2026-09-20T00:00:00+00:00'),
  p('r20', 'research', '2026-09-20T00:00:00+00:00'),
], NOW);
assert.deepEqual(rows.map((r) => [r.kind, r.kind === 'weekly' ? r.post.slug : r.business.slug]), [
  ['weekly', 'w20'],
  ['day', 'b20'],
]);

// 주간 정리만 있는 날은 day row가 없다
rows = buildDeskRows([p('w13', 'weekly', '2026-09-13T00:00:00+00:00')], NOW);
assert.deepEqual(rows.map((r) => r.kind), ['weekly']);

// null published_at 제외, 알 수 없는 유형은 비즈니스 칸
rows = buildDeskRows([p('nodate', 'business', null), p('odd', 'opinion', '2026-09-19T00:00:00+00:00')], NOW);
assert.equal(rows.length, 1);
assert.equal(rows[0].business.slug, 'odd');

assert.deepEqual(buildDeskRows([], NOW), []);

// 날짜 표기
const ko = deskDateParts('2026-10-15', 'ko');
assert.equal(ko.short, '10.15');
assert.equal(ko.issue, '제212호');
assert.equal(ko.weekday, '목');
const en = deskDateParts('2026-09-20', 'en');
assert.equal(en.short, '09.20');
assert.equal(en.issue, 'No. 187');
assert.equal(en.weekday, 'Sun');

console.log('news-desks-select.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/news-desks-select.test.mjs`
Expected: FAIL. `newsDesks.js` 모듈을 찾을 수 없다.

- [ ] **Step 3: 구현** (Write 도구로)

```js
// frontend/src/lib/newsDesks.js
// Pure grouping for the news list "two desks" page: one row per KST day
// (business | date | research), weekly recaps as their own entries. No I/O.
import { kstDay } from './homeFront.js';
import { issueLabel, issueNumber } from './issue.js';

const deskOf = (type) => (type === 'research' ? 'research' : 'business');
const newestFirst = (a, b) => String(b.published_at).localeCompare(String(a.published_at));

/**
 * @param {Array<{post_type?: string|null, published_at: string|null}>} posts daily + weekly, any order
 * @param {Date} [now]
 * @returns {Array<
 *   {kind: 'weekly', day: string, post: object} |
 *   {kind: 'day', day: string, showDate: boolean, isToday: boolean, business: object|null, research: object|null}
 * >} newest KST day first; a day's weekly recaps come before its rows
 */
export function buildDeskRows(posts, now = new Date()) {
  const today = kstDay(now);
  const byDay = new Map();
  for (const post of posts) {
    const day = kstDay(post.published_at);
    if (!day) continue;
    if (!byDay.has(day)) byDay.set(day, { weekly: [], business: [], research: [] });
    const bucket = byDay.get(day);
    if (post.post_type === 'weekly') bucket.weekly.push(post);
    else bucket[deskOf(post.post_type)].push(post);
  }

  const entries = [];
  for (const day of [...byDay.keys()].sort().reverse()) {
    const { weekly, business, research } = byDay.get(day);
    for (const post of weekly.sort(newestFirst)) entries.push({ kind: 'weekly', day, post });
    business.sort(newestFirst);
    research.sort(newestFirst);
    const rows = Math.max(business.length, research.length);
    for (let i = 0; i < rows; i += 1) {
      entries.push({
        kind: 'day',
        day,
        showDate: i === 0,
        isToday: day === today,
        business: business[i] ?? null,
        research: research[i] ?? null,
      });
    }
  }
  return entries;
}

/** Date spine labels for a KST day (YYYY-MM-DD). */
export function deskDateParts(day, locale) {
  const noon = new Date(`${day}T12:00:00+09:00`);
  return {
    short: `${day.slice(5, 7)}.${day.slice(8, 10)}`,
    weekday: noon.toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US', { timeZone: 'Asia/Seoul', weekday: 'short' }),
    issue: issueLabel(locale, issueNumber(noon)),
  };
}
```

- [ ] **Step 4: 통과 확인** — `node frontend/tests/news-desks-select.test.mjs` → PASS

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/newsDesks.js frontend/tests/news-desks-select.test.mjs
git commit -m "feat: group news posts into two-desk rows by KST day"
```

---

## Task 2: 두 데스크 지면 (컴포넌트·스크립트·페이지·CSS)

**Files:**
- Create: `frontend/src/components/newsprint/NewsDeskCell.astro`, `frontend/src/components/newsprint/NewsDeskList.astro`, `frontend/src/scripts/newsDeskMode.ts`
- Modify:
  - `frontend/src/components/newsprint/NewsprintShell.astro`
  - `frontend/src/scripts/newsListSearch.ts`
  - `frontend/src/pages/ko/news/index.astro`, `frontend/src/pages/en/news/index.astro`
  - `frontend/src/styles/global.css`
- Test: `frontend/tests/news-list-desks.test.cjs` (새 파일)

- [ ] **Step 1: 실패하는 구조 테스트 작성** (Write 도구로)

```js
// frontend/tests/news-list-desks.test.cjs
// News list "two desks": business | date spine | research; list mode on filter/search.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');

const cell = read('components/newsprint/NewsDeskCell.astro');
for (const attr of ['data-category=', 'data-post-type=', 'data-post-id=', 'data-search-text=']) {
  assert(cell.includes(attr), `cell keeps the list-card contract: ${attr}`);
}
assert(/class=\{`newsprint-card news-desk-cell/.test(cell), 'cell is a .newsprint-card (filter/search hide it)');
assert(cell.includes('newsprint-bookmark-icon') && cell.includes('data-bookmarked="false"'), 'bookmark button, user-neutral');
assert(cell.includes('newsprint-card-stretched-link'), 'whole cell is clickable');
assert(cell.includes('postTypeLabel(locale, '), 'desk label comes from lib/postType.js');
assert(!/newsprint-tags-inline|newsprint-tag\b|getCategoryLabel/.test(cell), 'no hashtag row or category label in the list');

const list = read('components/newsprint/NewsDeskList.astro');
assert(list.includes('id="news-list-results"') && list.includes('data-mode="desks"'), 'results root starts in desk mode');
for (const s of ['비즈니스 데스크', '리서치 데스크', 'Business desk', 'Research desk', '이날은 리서치 기사가 없어요', 'No research story this day']) {
  assert(list.includes(s), `copy: ${s}`);
}
assert(/<p class="news-desk-empty news-desk-empty--business">/.test(list) && !/news-desk-empty[^>]*(data-search-text|newsprint-card)/.test(list), 'empty placeholders are plain elements');
const order = ['class="news-desk-date"', '<NewsDeskCell locale={locale} post={entry.business}', '<NewsDeskCell locale={locale} post={entry.research}'].map((s) => list.indexOf(s));
assert(order.every((i) => i > 0) && order[0] < order[1] && order[1] < order[2], 'DOM order: date, business, research');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/news/index.astro`);
  assert(page.includes('<NewsDeskList locale=') && page.includes('buildDeskRows('), `${locale}: renders desks from buildDeskRows`);
  assert(/<NewsprintShell[\s\S]*?rail=\{false\}/.test(page), `${locale}: no right rail`);
  assert(page.includes("import '../../../scripts/newsDeskMode';"), `${locale}: desk mode script`);
  assert(!/NewsprintHeadline|NewsprintListCard|NewsprintListRail|newsListMultiHeadline/.test(page), `${locale}: old headline/card/rail removed`);
  assert(page.includes('sc.editorial_note'), `${locale}: editorial note kept`);
}

const shell = read('components/newsprint/NewsprintShell.astro');
assert(/rail\?: boolean/.test(shell) && /\{rail && \(/.test(shell), 'shell can drop the rail');

const mode = read('scripts/newsDeskMode.ts');
assert(mode.includes('deskModeReady') && mode.includes("'news:list-updated'") && mode.includes("'newsprint:filter-change'"), 'mode script: guard + both signals');
assert(mode.includes('data-row-empty'), 'mode script hides empty rows');
assert(read('scripts/newsListSearch.ts').includes("new CustomEvent('news:list-updated')"), 'search announces updates');

assert(/grid-template-areas:\s*"business date research"/.test(css), 'desk grid: business | date | research');
assert(/\.news-desks\[data-mode="list"\] \.news-desk-row\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(css), 'list mode is one column');
assert(/\.news-desk-row\[data-row-empty="true"\],\s*\n\.news-desk-weekly\[data-row-empty="true"\]\s*\{\s*display:\s*none;/.test(css), 'empty rows hidden');
assert(/\[data-theme="dark"\] \.news-desk-weekly\s*\{/.test(css), 'dark weekly band rule');
assert(/\.news-desk-cell--business\s*\{\s*--desk:\s*var\(--tier-paid\);/.test(css) && /\.news-desk-cell--research\s*\{\s*--desk:\s*var\(--tier-freemium\);/.test(css), 'desk colours reuse tier tokens');
assert(!/\.news-desk[a-z-]*[^{]*\{[^}]*(?:^|[\s;{])order:/m.test(css), 'no CSS order on desk items');

// desk colours are small text: >= 4.5:1 on bg-primary in all three themes
function block(sel) { const i = css.indexOf(sel); assert(i >= 0, `missing ${sel}`); return css.slice(i, css.indexOf('}', i)); }
function tok(b, name) { const m = b.match(new RegExp(`${name}:\\s*(#[0-9A-Fa-f]{6})`)); return m && m[1]; }
function lum(h) { return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)).reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0); }
function ratio(a, b) { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
const tierLight = block(':root {\n  --tier-free');
const tierDark = block('[data-theme="dark"] {\n  --tier-free');
const bgs = { light: block('[data-theme="light"] {').match(/--color-bg-primary:\s*(#[0-9A-Fa-f]{6})/)[1], white: block('[data-theme="white"] {').match(/--color-bg-primary:\s*(#[0-9A-Fa-f]{6})/)[1], dark: block('[data-theme="dark"] {').match(/--color-bg-primary:\s*(#[0-9A-Fa-f]{6})/)[1] };
for (const t of ['--tier-paid', '--tier-freemium']) {
  assert(ratio(tok(tierLight, t), bgs.light) >= 4.5, `${t} on paper`);
  assert(ratio(tok(tierLight, t), bgs.white) >= 4.5, `${t} on white`);
  assert(ratio(tok(tierDark, t), bgs.dark) >= 4.5, `${t} on dark`);
}
console.log('news-list-desks.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/news-list-desks.test.cjs`
Expected: FAIL. `NewsDeskCell.astro`가 없어 ENOENT가 난다.

- [ ] **Step 3: `NewsDeskCell.astro` 작성**

```astro
---
// frontend/src/components/newsprint/NewsDeskCell.astro
// One story in the two-desk news list. Keeps the list-card contract
// (.newsprint-card + data-category/post-type/post-id/search-text) so the
// existing filter, search and bookmark scripts work unchanged.
import { normalizeCategorySlug } from '../../lib/categories';
import { postTypeLabel } from '../../lib/postType.js';

interface DeskPost {
  id: string;
  slug: string;
  title: string;
  display_title?: string | null;
  excerpt?: string | null;
  display_excerpt?: string | null;
  category?: string | null;
  post_type?: string | null;
  reading_time_min?: number | null;
  tags?: string[] | null;
}

interface Props {
  locale: 'en' | 'ko';
  post: DeskPost;
  side: 'business' | 'research' | 'weekly';
  isToday?: boolean;
}

const { locale, post, side, isToday = false } = Astro.props;
const isKo = locale === 'ko';
const title = post.display_title || post.title;
const excerpt = post.display_excerpt || post.excerpt;
const type = post.post_type || 'business';
const searchText = [title, excerpt, post.tags?.join(' ')].filter(Boolean).join(' ');
const readingLabel = post.reading_time_min ? (isKo ? `${post.reading_time_min}분` : `${post.reading_time_min} min`) : '';
---

<article
  class={`newsprint-card news-desk-cell news-desk-cell--${side}${isToday ? ' news-desk-cell--today' : ''}`}
  data-category={normalizeCategorySlug(post.category) || 'uncategorized'}
  data-post-type={type}
  data-post-id={post.id}
  data-search-text={searchText}
>
  <span class="news-desk-label">{postTypeLabel(locale, type)}</span>
  <div class="news-desk-head">
    <h2 class="news-desk-title"><a href={`/${locale}/news/${post.slug}/`} class="newsprint-card-stretched-link">{title}</a></h2>
    <button
      class="newsprint-bookmark-icon"
      data-item-id={post.id}
      data-item-type="news"
      data-bookmarked="false"
      aria-label="Add bookmark"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
      </svg>
    </button>
  </div>
  {excerpt && <p class="news-desk-excerpt">{excerpt}</p>}
  {readingLabel && <p class="news-desk-meta">{readingLabel}</p>}
</article>
```

- [ ] **Step 4: `NewsDeskList.astro` 작성**

```astro
---
// frontend/src/components/newsprint/NewsDeskList.astro
// Two-desk news list: business | date spine | research, one row per KST day.
// DOM order is date → business → research (reading order); desktop columns come from grid-template-areas.
import NewsDeskCell from './NewsDeskCell.astro';
import { deskDateParts } from '../../lib/newsDesks.js';

interface Props {
  locale: 'en' | 'ko';
  entries: any[];
}

const { locale, entries } = Astro.props;
const isKo = locale === 'ko';
const copy = isKo
  ? {
      business: '비즈니스 데스크', businessSub: '돈과 시장',
      research: '리서치 데스크', researchSub: '논문과 기술',
      noBusiness: '이날은 비즈니스 기사가 없어요', noResearch: '이날은 리서치 기사가 없어요',
      today: '오늘',
    }
  : {
      business: 'Business desk', businessSub: 'Money and markets',
      research: 'Research desk', researchSub: 'Papers and tech',
      noBusiness: 'No business story this day', noResearch: 'No research story this day',
      today: 'Today',
    };
---

<div id="news-list-results" class="news-desks" data-mode="desks">
  <div class="news-desks-heads" aria-hidden="true">
    <p class="news-desks-head news-desks-head--business">{copy.business} <small>· {copy.businessSub}</small></p>
    <span></span>
    <p class="news-desks-head news-desks-head--research">{copy.research} <small>· {copy.researchSub}</small></p>
  </div>
  {entries.map((entry) => {
    const date = deskDateParts(entry.day, locale);
    if (entry.kind === 'weekly') {
      return (
        <div class="news-desk-weekly">
          <p class="news-desk-weekly-when">{date.short} · {date.issue}</p>
          <NewsDeskCell locale={locale} post={entry.post} side="weekly" />
        </div>
      );
    }
    return (
      <div class={`news-desk-row${entry.isToday ? ' news-desk-row--today' : ''}${entry.showDate ? '' : ' news-desk-row--cont'}`}>
        <p class="news-desk-date">
          {entry.showDate && (
            <>
              <b>{date.short}</b>
              <span>{date.weekday} · {date.issue}{entry.isToday ? ` · ${copy.today}` : ''}</span>
            </>
          )}
        </p>
        {entry.business
          ? <NewsDeskCell locale={locale} post={entry.business} side="business" isToday={entry.isToday} />
          : <p class="news-desk-empty news-desk-empty--business">{copy.noBusiness}</p>}
        {entry.research
          ? <NewsDeskCell locale={locale} post={entry.research} side="research" isToday={entry.isToday} />
          : <p class="news-desk-empty news-desk-empty--research">{copy.noResearch}</p>}
      </div>
    );
  })}
</div>
```

- [ ] **Step 5: `newsDeskMode.ts` 작성**

```ts
// frontend/src/scripts/newsDeskMode.ts
// News list: two-desk layout when the "all" tab is active and the search box is empty,
// single-column list otherwise. Rows whose cards are all hidden get data-row-empty.
// Runs after NewsprintCategoryFilter (data-filtered) and newsListSearch (data-search-matched).

function activeFilter(): string {
  const tab = document.querySelector<HTMLElement>(
    '.newsprint-filter-tabs[data-filter-key="post_type"] .newsprint-filter-tab[aria-selected="true"]',
  );
  return tab?.dataset.filter || new URLSearchParams(window.location.search).get('post_type') || 'all';
}

function update(): void {
  const root = document.querySelector<HTMLElement>('.news-desks');
  if (!root) return;
  const search = document.getElementById('news-search') as HTMLInputElement | null;
  const query = (search?.value ?? '').trim();
  root.dataset.mode = activeFilter() === 'all' && !query ? 'desks' : 'list';

  root.querySelectorAll<HTMLElement>('.news-desk-row, .news-desk-weekly').forEach((row) => {
    const hasVisible = Array.from(row.querySelectorAll<HTMLElement>('.newsprint-card')).some(
      (card) => card.dataset.filtered !== 'false' && card.dataset.searchMatched !== 'false',
    );
    if (hasVisible) row.removeAttribute('data-row-empty');
    else row.setAttribute('data-row-empty', 'true');
  });
}

function init(): void {
  const root = document.querySelector<HTMLElement>('.news-desks');
  if (!root || root.dataset.deskModeReady === 'true') return;
  root.dataset.deskModeReady = 'true';
  window.addEventListener('newsprint:filter-change', () => requestAnimationFrame(update));
  window.addEventListener('news:list-updated', update);
  update();
}

document.addEventListener('astro:page-load', init);
init();
```

- [ ] **Step 6: `newsListSearch.ts`에 이벤트 한 줄을 추가한다** — 이 파일은 CRLF다. Edit 도구로만 수정하고 sed/bash는 쓰지 않는다.
  - `applySearch` 함수 맨 끝, 즉 `if (updateUrl) { syncQuery(query); }` 블록 다음 줄에 넣는다.
    ```ts
        window.dispatchEvent(new CustomEvent('news:list-updated'));
    ```

- [ ] **Step 7: `NewsprintShell.astro`에 `rail` prop을 추가한다**
  - Props에 `rail?: boolean;`을 추가하고, 구조분해에 `rail = true`를 넣는다.
  - 하단 grid를 다음으로 바꾼다.
    ```astro
      <div class={`newsprint-grid${rail ? '' : ' newsprint-grid--full'}`}>
        <div class="newsprint-main">
          <slot />
        </div>
        {rail && (
          <aside class="newsprint-rail">
            <slot name="rail" />
          </aside>
        )}
      </div>
    ```

- [ ] **Step 8: 페이지 두 개를 수정한다** (ko 먼저, en은 문구만 다르게 동일 적용)
  - **import**
    - `NewsprintHeadline`, `NewsprintListCard`, `NewsprintListRail` import를 지운다.
    - 다음 두 줄을 추가한다.
      ```astro
      import NewsDeskList from '../../../components/newsprint/NewsDeskList.astro';
      import { buildDeskRows } from '../../../lib/newsDesks.js';
      ```
  - **frontmatter**
    - persona 해석 루프 다음의 정렬(`TYPE_ORDER`, `dateKey`, `posts.sort`)부터 `railPosts`까지 지운다. 지울 것: headline 3종, `latestDate`, `allHeadlineType`, `allHeadline`, `rest`, `railPosts`.
    - 그 자리에 `const deskEntries = buildDeskRows(posts);`을 넣는다.
    - `startHereSections` 줄을 지운다.
    - `postTypeItems`, `subkicker`, 검색 상수는 그대로 둔다.
  - **`<NewsprintShell ...>`** 속성에 `rail={false}`를 추가한다.
  - **편집 노트**: Shell 안 맨 앞(검색 sticky 위)에 추가한다.
    ```astro
        {sc.editorial_note && <p class="news-desks-note">{sc.editorial_note}</p>}
    ```
  - **결과 블록**
    - `posts.length > 0 ? ( <div id="news-list-results" data-multi-headline ...> ... </div> )` 분기 전체를 다음으로 바꾼다.
      ```astro
          ) : posts.length > 0 ? (
            <NewsDeskList locale="ko" entries={deskEntries} />
          ) : (
      ```
    - en은 `locale="en"`으로 쓴다.
  - **레일**: `<Fragment slot="rail"> ... </Fragment>` 블록을 삭제한다.
  - **스크립트**: `import '../../../scripts/newsListMultiHeadline';`을 `import '../../../scripts/newsDeskMode';`로 바꾼다. `newsListSearch` import보다 뒤에 둔다.

- [ ] **Step 9: CSS 추가**
  - 위치: `global.css`의 `/* Headline (front-page style) */` 주석 **바로 위**
  - 블록 첫 줄은 `/* News list: two desks (business | date | research) */`
  - 내용은 아래 전부다.
  - 먼저 1024px `.newsprint-main` 규칙(`@media (min-width: 1024px) { .newsprint-grid {...} .newsprint-main {...} }`)을 읽는다. 레일 쪽 padding/border가 있으면 아래 블록의 `--full` 규칙에 같은 속성을 0/none으로 넣어 중화한다.

```css
/* News list: two desks (business | date | research) */
@media (min-width: 1024px) {
  .newsprint-grid--full {
    grid-template-columns: minmax(0, 1fr);
  }

  .newsprint-grid--full > .newsprint-main {
    padding-right: 0;
    border-right: none;
  }
}

.news-desks-note {
  text-align: center;
  font-size: 0.9rem;
  color: var(--color-text-muted);
  margin: -0.5rem 0 1rem;
}

.news-desks-heads {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 92px minmax(0, 1fr);
  padding: 1rem 0 0.6rem;
  border-bottom: 1px solid var(--color-text-primary);
  font-size: 0.82rem;
  font-weight: 700;
}

.news-desks-head small {
  font-weight: 400;
  color: var(--color-text-muted);
}

.news-desks-head--business {
  text-align: right;
  color: var(--tier-paid);
}

.news-desks-head--research {
  color: var(--tier-freemium);
}

.news-desk-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 92px minmax(0, 1fr);
  grid-template-areas: "business date research";
  border-bottom: 1px dotted var(--color-border);
}

.news-desk-row > .news-desk-date {
  grid-area: date;
}

.news-desk-row > .news-desk-cell--business,
.news-desk-row > .news-desk-empty--business {
  grid-area: business;
  text-align: right;
  padding: 1rem 1.4rem 1.1rem 0;
}

.news-desk-row > .news-desk-cell--research,
.news-desk-row > .news-desk-empty--research {
  grid-area: research;
  padding: 1rem 0 1.1rem 1.4rem;
}

.news-desk-cell--business {
  --desk: var(--tier-paid);
}

.news-desk-cell--research {
  --desk: var(--tier-freemium);
}

.news-desk-cell.newsprint-card {
  border-bottom: none;
}

.news-desk-date {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 1rem;
}

.news-desk-date::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  border-left: 1px solid var(--color-border);
}

.news-desk-date b,
.news-desk-date span {
  position: relative;
  background: var(--color-bg-primary);
}

.news-desk-date b {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 1.5rem;
  font-weight: 500;
  line-height: 1;
  padding: 0.1rem 0.35rem;
}

.news-desk-date span {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  padding: 0.15rem 0.25rem;
  text-align: center;
}

.news-desk-row--today .news-desk-date b {
  color: var(--color-accent);
}

.news-desk-label {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--desk, var(--color-accent));
}

.news-desk-label::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.news-desk-head {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.news-desk-cell--business .news-desk-head {
  flex-direction: row-reverse;
}

.news-desk-title {
  flex: 1;
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.36;
  letter-spacing: -0.035em;
  transition: color 150ms ease;
}

.news-desk-cell--today .news-desk-title {
  font-size: 1.4rem;
}

.news-desk-cell:hover .news-desk-title {
  color: var(--color-accent);
}

.news-desk-excerpt {
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin-top: 0.3rem;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-desk-meta {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.3rem;
}

.news-desk-empty {
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

/* Weekly recap: full-width band (ink in light themes) */
.news-desk-weekly {
  margin: 0.5rem 0;
  padding: 1.1rem 1.4rem;
  text-align: center;
  background: var(--color-text-primary);
  color: var(--color-bg-primary);
}

[data-theme="dark"] .news-desk-weekly {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.news-desk-weekly-when {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 0.9rem;
  opacity: 0.75;
}

.news-desk-weekly .newsprint-card {
  padding: 0.3rem 0 0;
}

.news-desk-weekly .news-desk-label,
.news-desk-weekly .news-desk-excerpt,
.news-desk-weekly .news-desk-meta,
.news-desk-weekly .newsprint-bookmark-icon {
  color: inherit;
}

.news-desk-weekly .newsprint-bookmark-icon--active {
  color: var(--color-accent);
}

.news-desk-weekly .news-desk-title {
  font-size: 1.2rem;
}

.news-desk-weekly .news-desk-head {
  justify-content: center;
}

.news-desk-weekly .news-desk-title {
  flex: 0 1 auto;
}

.news-desk-row[data-row-empty="true"],
.news-desk-weekly[data-row-empty="true"] {
  display: none;
}

/* Desktop desk mode: the column says which desk — keep the label for screen readers only */
@media (min-width: 768px) {
  .news-desks[data-mode="desks"] .news-desk-cell:not(.news-desk-cell--weekly) .news-desk-label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
}

/* List mode (a desk tab or a search query is active): one column */
.news-desks[data-mode="list"] .news-desks-heads {
  display: none;
}

.news-desks[data-mode="list"] .news-desk-row {
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas: none;
}

.news-desks[data-mode="list"] .news-desk-row > * {
  grid-area: auto;
  text-align: left;
  padding: 0.6rem 0 0.8rem;
}

.news-desks[data-mode="list"] .news-desk-cell--business .news-desk-head {
  flex-direction: row;
}

.news-desks[data-mode="list"] .news-desk-date {
  flex-direction: row;
  align-items: baseline;
  gap: 0.5rem;
  padding: 1rem 0 0;
}

.news-desks[data-mode="list"] .news-desk-date::before {
  display: none;
}

.news-desks[data-mode="list"] .news-desk-row--cont .news-desk-date,
.news-desks[data-mode="list"] .news-desk-empty {
  display: none;
}

@media (max-width: 767px) {
  .news-desks-heads {
    display: none;
  }

  .news-desk-row {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: none;
  }

  /* 0,2,0 + later in file: beats the named-area rules so items stack in DOM order */
  .news-desks .news-desk-row > * {
    grid-area: auto;
  }

  .news-desks[data-mode="list"] .news-desk-row > .news-desk-cell {
    padding-left: 0.75rem;
  }

  .news-desk-row > .news-desk-cell--business,
  .news-desk-row > .news-desk-cell--research {
    text-align: left;
    padding: 0.5rem 0 0.6rem 0.75rem;
    margin-bottom: 0.6rem;
    border-left: 2px solid var(--desk);
  }

  .news-desk-cell--business .news-desk-head {
    flex-direction: row;
  }

  .news-desk-date {
    flex-direction: row;
    align-items: baseline;
    gap: 0.5rem;
    padding: 1rem 0 0.5rem;
  }

  .news-desk-date::before {
    display: none;
  }

  .news-desk-row--cont .news-desk-date,
  .news-desk-empty {
    display: none;
  }

  .news-desk-weekly {
    padding: 1rem;
    text-align: left;
  }

  .news-desk-weekly .news-desk-head {
    justify-content: flex-start;
  }
}
```

- [ ] **Step 10: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/news-list-desks.test.cjs
node frontend/tests/news-desks-select.test.mjs
node frontend/tests/public-list-query-budget.test.cjs
node frontend/tests/public-list-personalization.test.cjs
node frontend/tests/issue-number-shell.test.cjs
node frontend/tests/news-post-type-tab-order.test.cjs
cd frontend && npm run build
```
Expected: 모두 PASS, 빌드 "Complete!".
- `list-v2`, `news-search-list-structure`는 Task 3 전까지 계속 PASS다. 삭제 전이라 옛 컴포넌트 파일이 남아 있기 때문이다.
- `public-list-personalization`이 실패하면 무엇을 요구하는지 읽고 보고한다. 페이지가 쓰던 개인화 관련 import/주석을 지웠을 수 있다.

- [ ] **Step 11: 커밋**

```bash
git add frontend/src/components/newsprint/NewsDeskCell.astro frontend/src/components/newsprint/NewsDeskList.astro frontend/src/scripts/newsDeskMode.ts frontend/src/scripts/newsListSearch.ts frontend/src/components/newsprint/NewsprintShell.astro frontend/src/pages/ko/news/index.astro frontend/src/pages/en/news/index.astro frontend/src/styles/global.css frontend/tests/news-list-desks.test.cjs
git commit -m "feat: two-desk news list with date spine, weekly bands and list mode for filters"
```

---

## Task 3: 옛 헤드라인·카드·레일 정리와 테스트 갱신

**Files:**
- Delete (`git rm`):
  - `frontend/src/components/newsprint/NewsprintHeadline.astro`
  - `frontend/src/components/newsprint/NewsprintListCard.astro`
  - `frontend/src/components/newsprint/NewsprintListRail.astro`
  - `frontend/src/scripts/newsListMultiHeadline.ts`
  - `frontend/tests/list-rail-copy.test.cjs`, `frontend/tests/list-meta-order.test.cjs`
- Modify: `frontend/src/styles/global.css`, `frontend/tests/list-v2.test.cjs`, `frontend/tests/news-search-list-structure.test.cjs`, `frontend/tests/news-headline-mobile-tags-wrap.test.cjs`, `frontend/tests/font-roles.test.cjs`

- [ ] **Step 1: 다른 사용처 확인**

Run: `grep -rn "NewsprintHeadline\|NewsprintListCard\|NewsprintListRail\|newsListMultiHeadline" frontend/src`
Expected: 결과 없음. Task 2에서 페이지가 더 이상 쓰지 않는다. 결과가 있으면 멈추고 보고한다.

- [ ] **Step 2: 파일 삭제**

```bash
git rm frontend/src/components/newsprint/NewsprintHeadline.astro frontend/src/components/newsprint/NewsprintListCard.astro frontend/src/components/newsprint/NewsprintListRail.astro frontend/src/scripts/newsListMultiHeadline.ts frontend/tests/list-rail-copy.test.cjs frontend/tests/list-meta-order.test.cjs
```

- [ ] **Step 3: CSS 삭제**

정확히 아래 규칙 블록만 통째로 지운다. 각 셀렉터로 블록을 찾아 `{`부터 짝이 맞는 `}`까지 지운다.
- `/* Headline (front-page style) */` 주석과 `.newsprint-headline {`
- `.newsprint-headline:hover {`
- `.newsprint-headline[data-filtered="false"] {`
- `.newsprint-headline[data-search-matched="false"] {`
- `/* Multi-headline filter — ... */` 주석과 `.newsprint-headline[data-headline-hidden="true"] {`
- `/* Hide rest-grid card when ... */` 주석과 `.newsprint-card[data-headline-duplicate="true"] {`
- `.newsprint-headline-kicker {`
- `.newsprint-headline-kicker .newsprint-card-kicker {`
- `.newsprint-headline-title {`
- `.newsprint-headline:hover .newsprint-headline-title {`
- `.newsprint-headline-deck {`
- `.newsprint-headline-bottom {`
- `.newsprint-stack > a.newsprint-card:has(.newsprint-rail-rank) {`
- `.newsprint-stack > a.newsprint-card:has(.newsprint-rail-rank):last-child {`
- `.newsprint-rail-rank {`

**주의**
- 사이에 있는 `.newsprint-article-topline*`, `.newsprint-article-kicker`, `.newsprint-article-tags`, `.newsprint-rail-date`, `.newsprint-rail-meta ...`, `.newsprint-rail-subtitle`, `.newsprint-rail-badge`는 **지우지 않는다**.
- `.newsprint-card-bottom`, `.newsprint-tags-inline*`도 지우지 않는다(스펙에 따라 이번 범위에서 유지).

Run: `grep -n "newsprint-headline\|newsprint-rail-rank\|headline-duplicate" frontend/src/styles/global.css`
Expected: 결과 없음.

- [ ] **Step 4: `list-v2.test.cjs` 수정** (Edit 도구로)
  - **Task 1 첫 루프 배열**
    - `'components/newsprint/NewsprintListCard.astro'`, `'components/newsprint/NewsprintHeadline.astro'`, `'components/newsprint/NewsprintListRail.astro'` 세 줄을 지운다.
    - 그 자리에 `'components/newsprint/NewsDeskCell.astro',`를 넣는다.
  - **두 번째 루프**: `for (const p of ['components/newsprint/NewsprintListCard.astro', 'components/newsprint/NewsprintHeadline.astro']) { ... }`를 다음으로 바꾼다.
    ```js
    {
      const f = read('components/newsprint/NewsDeskCell.astro');
      assert(!/news-desk-label" style=/.test(f), 'desk label has no inline colour');
      assert(f.includes('data-post-type=') && f.includes('newsprint-card-stretched-link'), 'desk cell keeps filter/search hooks');
    }
    ```
  - **지울 줄**
    - `assert(!read('components/newsprint/NewsprintHeadline.astro').includes('◆'), ...)`
    - `const railSrc = ...`와 그 다음 `railSrc` 단언 두 줄
  - **바꿀 단언**
    - `assert(/font-weight:\s*700/.test(rule('.newsprint-headline-title')), 'headline title 700');` → `assert(/font-weight:\s*700/.test(rule('.news-desk-title')), 'desk title 700');`
    - `assert(!rule('.newsprint-headline-kicker').includes('uppercase'), 'headline kicker not uppercase');` → `assert(!rule('.news-desk-label').includes('uppercase'), 'desk label not uppercase');`

- [ ] **Step 5: `news-search-list-structure.test.cjs` 수정** (Edit 도구로)
  - `const headline = read('frontend/src/components/newsprint/NewsprintHeadline.astro');` 블록과 `const listCard = read('frontend/src/components/newsprint/NewsprintListCard.astro');` 블록(각 assert 포함)을 다음으로 바꾼다.
    ```js
    const deskCell = read('frontend/src/components/newsprint/NewsDeskCell.astro');
    assert.ok(
      deskCell.includes('data-search-text='),
      'NewsDeskCell.astro must expose search text for list filtering',
    );

    const searchScript = read('frontend/src/scripts/newsListSearch.ts');
    assert.ok(
      searchScript.includes("new CustomEvent('news:list-updated')"),
      'newsListSearch must announce updates so the desk layout can follow',
    );
    ```

- [ ] **Step 6: `news-headline-mobile-tags-wrap.test.cjs` 수정**
  - `const headline = read('src/components/newsprint/NewsprintHeadline.astro');`와 바로 다음 `assert(...)` 블록을 지운다.
  - CSS 단언(`.newsprint-card-bottom`, `.newsprint-tags-inline`)은 남긴다.

- [ ] **Step 7: `font-roles.test.cjs` 수정** — 셀렉터 배열 `['.newsprint-deck', '.newsprint-headline-deck', '.handbook-definition']`에서 `'.newsprint-headline-deck'`을 `'.news-desk-excerpt'`로 바꾼다.

- [ ] **Step 8: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/list-v2.test.cjs
node frontend/tests/news-search-list-structure.test.cjs
node frontend/tests/news-headline-mobile-tags-wrap.test.cjs
node frontend/tests/font-roles.test.cjs
node frontend/tests/news-list-desks.test.cjs
node frontend/tests/retro-decoration-removed.test.cjs
node frontend/tests/theme-palette.test.cjs
cd frontend && npm run build
```
Expected: 모두 PASS, 빌드 "Complete!".

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/list-v2.test.cjs frontend/tests/news-search-list-structure.test.cjs frontend/tests/news-headline-mobile-tags-wrap.test.cjs frontend/tests/font-roles.test.cjs
git commit -m "chore: remove news headline, list card and list rail replaced by the desk list"
```

(`git rm`으로 stage된 삭제 6개가 함께 커밋된다.)

---

## Task 4: 검증 (컨트롤러)

- [ ] 전체 테스트를 **이름으로** 기준선과 비교한다. 개수는 실행 방식(.ts 포함 여부)에 따라 다를 수 있다. 판정 기준:
  - 삭제된 `list-rail-copy`, `list-meta-order` 외에 실패 목록이 같아야 한다.
  - 신규 FAIL은 0이어야 한다.
- [ ] 브라우저 매트릭스: 종이·순백·다크 × 데스크톱(≥1024px)·375px × `/ko/news/`·`/en/news/`
  - 스크린샷
  - 가로 넘침 0
  - 대비 검사
  - 직접 클릭: 탭 비즈니스 → 리서치 → 주간 정리 → 전체. 검색 "Gemini" 입력 후 지우기. 결과 수, 빈 줄 숨김, 모드 전환을 확인한다.
  - `?post_type=research`, `?q=Gemini`로 직접 들어왔을 때 처음부터 목록 모드인지
  - 북마크 아이콘이 칸마다 보이는지
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 5: 문서

- [ ] 스펙 Status를 `implemented (2026-10-16)`로 바꾼다.
- [ ] 이 계획에 Status와 실행 결과를 적는다.
- [ ] `ACTIVE_SPRINT.md`에 REDESIGN-NEWS-LIST 항목과 증거를 추가한다.
- [ ] 커밋: `docs: record two-desk news list redesign`
