# 뉴스 목록 읽기 개선 Implementation Plan

**Status:** done (2026-11-22). `recentCutoff` 기준은 기본 제안으로 확정. 실행 결과는 문서 끝 참조.

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 뉴스 목록에서 날짜를 왼쪽 끝으로 옮겨 모든 글을 왼쪽 정렬로 읽게 하고, 한쪽 데스크만 있는 날의 빈 칸을 없애고, 최근 기사만 먼저 보여 페이지를 줄인다.

**Architecture:**
- 목록을 나누는 일(달 구분, 최근/이전)은 순수 함수 `addListBreaks`가 한다. `buildDeskRows`의 출력은 그대로 두고 그 결과를 한 번 더 가공한다.
- 접기는 CSS다. 기사는 전부 DOM에 남으므로 검색·탭 스크립트는 바꾸지 않는다. 목록 모드(`data-mode="list"`)가 되면 접기가 저절로 풀린다.
- 마스트헤드는 `NewsprintShell`의 새 선택 prop `tight`로만 줄인다. 다른 페이지는 넘기지 않는다.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**저장소 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-11-22-news-list-reading-design]] — 구현 전에 반드시 읽는다.

---

## 사전 정보 (실행자 필독)

- 브랜치는 `main`이다. 원래 작업 폴더(`0to1log`)는 다른 브랜치에 미커밋 변경이 있으므로 `main`의 worktree에서 작업한다.
- `git add`는 계획에 적힌 경로만. 커밋 메시지는 적힌 그대로, trailer 없음(`AGENTS.md`). push는 Amy가 말할 때만 한다.
- `global.css`는 14,000줄이 넘는다. Grep으로 위치를 찾아 고친다.
- 시작 전부터 실패하는 테스트 16개는 고치지 않는다(목록: [[2026-11-21-news-article-reading]]의 "사전 정보"). 시작할 때 전체를 돌려 목록을 기록한다.
  ```bash
  for f in frontend/tests/*.test.cjs frontend/tests/*.test.mjs; do node "$f" >/dev/null 2>&1 || echo "FAIL $f"; done
  ```
- Task 2~4의 커밋은 마크업과 CSS가 어긋난 중간 상태다. **Task 5가 끝나기 전에는 배포(push)하지 않는다.**
- 카드 계약을 지킨다: `.newsprint-card`, `data-category`·`data-post-type`·`data-post-id`·`data-search-text`, 북마크 버튼, `newsprint-card-stretched-link`. `NewsDeskCell.astro`는 고치지 않는다.

**파일 지도**

| 파일 | 역할 | 작업 |
|---|---|---|
| `frontend/src/lib/newsDesks.js` | 목록 가공 순수 함수 | `addListBreaks`, `recentCutoff`, `monthLabel` 추가 |
| `frontend/tests/news-desks-select.test.mjs` | 위 함수 단위 테스트 | 단정 추가 |
| `frontend/src/components/newsprint/NewsDeskList.astro` | 목록 마크업 | 다시 씀 |
| `frontend/src/styles/global.css` | 스타일 | 데스크 블록 교체, 마스트헤드 규칙 추가 |
| `frontend/src/scripts/newsDeskMode.ts` | 목록 모드 스크립트 | 더 보기 동작 추가 |
| `frontend/src/components/newsprint/NewsprintShell.astro` | 머리 | `tight` prop |
| `frontend/src/pages/ko/news/index.astro`, `frontend/src/pages/en/news/index.astro` | 목록 페이지 | `tight` 전달, 보조 줄 제거 |
| `frontend/tests/news-list-desks.test.cjs` | 구조 테스트 | 새 구조에 맞게 수정 |

---

## Chunk 1: 목록 가공과 마크업

### Task 1: `addListBreaks`, `monthLabel`

**Files:**
- Modify: `frontend/src/lib/newsDesks.js` (파일 끝에 추가)
- Test: `frontend/tests/news-desks-select.test.mjs`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`news-desks-select.test.mjs`의 import 줄을 바꾼다.

```js
// before
const { buildDeskRows, deskDateParts, deskDayRange } = await import(pathToFileURL(path.join(here, '../src/lib/newsDesks.js')).href);

// after
const { buildDeskRows, deskDateParts, deskDayRange, addListBreaks, recentCutoff, monthLabel, RECENT_DAYS } = await import(pathToFileURL(path.join(here, '../src/lib/newsDesks.js')).href);
```

파일의 마지막 `console.log(...)` 줄 바로 위에 추가한다.

```js
// --- addListBreaks: 달 구분과 최근/이전 ---
const dayEntry = (day) => ({ kind: 'day', day, showDate: true, isToday: false, business: { slug: `b-${day}` }, research: null });
const pad = (n) => String(n).padStart(2, '0');

// 빈 입력
assert.deepEqual(addListBreaks([]), []);

// 한 달 안, 14일 이하 → 달 구분 없음, 전부 최근
let listed = addListBreaks([dayEntry('2026-11-21'), dayEntry('2026-11-20')]);
assert.deepEqual(listed.map((e) => [e.kind, e.older]), [['day', false], ['day', false]]);

// 달이 바뀌는 첫 항목 앞에 month 항목. 가장 최근 달 앞에는 없다
listed = addListBreaks([dayEntry('2026-11-13'), dayEntry('2026-10-27'), dayEntry('2026-10-26'), dayEntry('2026-09-30')]);
assert.deepEqual(listed.map((e) => (e.kind === 'month' ? `month:${e.month}` : e.day)), [
  '2026-11-13', 'month:2026-10', '2026-10-27', '2026-10-26', 'month:2026-09', '2026-09-30',
]);

// 해가 바뀌는 경우
listed = addListBreaks([dayEntry('2027-01-02'), dayEntry('2026-12-31')]);
assert.deepEqual(listed.map((e) => (e.kind === 'month' ? `month:${e.month}` : e.day)), ['2027-01-02', 'month:2026-12', '2026-12-31']);

// 최근/이전 경계: recentCutoff가 정한 날까지가 최근이다. month 항목은 뒤따르는 항목의 older를 따른다
const twenty = Array.from({ length: 20 }, (_, i) => dayEntry(i < 10 ? `2026-11-${pad(21 - i)}` : `2026-10-${pad(40 - i)}`));
const cutoff = recentCutoff(twenty.map((e) => e.day));
assert.ok(typeof cutoff === 'string' && twenty.some((e) => e.day === cutoff), 'cutoff is one of the listed days');
listed = addListBreaks(twenty);
for (const e of listed.filter((x) => x.kind === 'day')) assert.equal(e.older, e.day < cutoff, `older flag for ${e.day}`);
const firstOctober = listed.findIndex((e) => e.kind === 'month');
assert.equal(listed[firstOctober].older, listed[firstOctober + 1].older, 'month marker follows the entry after it');
assert.ok(listed.some((e) => e.older) && listed.some((e) => !e.older), '20 days: some shown, some folded');

// 같은 날의 주간 정리와 날짜 줄은 같은 쪽에 놓인다
listed = addListBreaks([{ kind: 'weekly', day: '2026-11-15', post: { slug: 'w' } }, dayEntry('2026-11-15')]);
assert.equal(listed[0].older, listed[1].older);

// 입력을 바꾸지 않는다
const frozen = [Object.freeze(dayEntry('2026-11-21'))];
addListBreaks(frozen);
assert.equal('older' in frozen[0], false);

assert.equal(Number.isInteger(RECENT_DAYS) && RECENT_DAYS > 0, true);
assert.equal(recentCutoff([]), null);

// --- monthLabel ---
assert.equal(monthLabel('2026-10', 'ko'), '2026년 10월');
assert.equal(monthLabel('2026-10', 'en'), 'October 2026');
assert.equal(monthLabel('2027-01', 'ko'), '2027년 1월');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-desks-select.test.mjs`
Expected: `TypeError: addListBreaks is not a function`

- [ ] **Step 3: 구현한다**

`frontend/src/lib/newsDesks.js` 파일 끝에 추가한다.

```js

/** How many days the list shows before the "more" button. */
export const RECENT_DAYS = 14;

/**
 * Oldest KST day (YYYY-MM-DD) still shown before "more".
 * @param {string[]} days distinct days that have entries, newest first
 * @returns {string|null}
 */
export function recentCutoff(days) {
  // ── Amy 결정 지점 (Task 1 Step 5) ──────────────────────────────────────
  // 기본 제안: 발행된 날 RECENT_DAYS개까지가 "최근"이다(달력 날짜가 아니다).
  if (days.length === 0) return null;
  return days[Math.min(days.length, RECENT_DAYS) - 1];
}

/**
 * Adds month dividers and an `older` flag to buildDeskRows() output. Pure; input untouched.
 * @param {Array<{kind: 'weekly'|'day', day: string}>} entries newest first
 * @returns {Array<object>} same entries plus {kind: 'month', month: 'YYYY-MM', older}
 */
export function addListBreaks(entries) {
  const cutoff = recentCutoff([...new Set(entries.map((entry) => entry.day))]);
  const out = [];
  let month = entries[0]?.day.slice(0, 7);
  for (const entry of entries) {
    const older = cutoff !== null && entry.day < cutoff;
    const entryMonth = entry.day.slice(0, 7);
    if (entryMonth !== month) {
      out.push({ kind: 'month', month: entryMonth, older });
      month = entryMonth;
    }
    out.push({ ...entry, older });
  }
  return out;
}

/** "2026년 10월" / "October 2026" for a YYYY-MM month. */
export function monthLabel(month, locale) {
  return new Date(`${month}-15T12:00:00+09:00`).toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: 'long',
  });
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `node frontend/tests/news-desks-select.test.mjs`
Expected: 파일의 기존 통과 문구가 나온다.

- [ ] **Step 5: Amy가 "최근"의 기준을 정한다 (사람이 하는 단계)**

`recentCutoff`의 본문은 기본 제안이다. 에이전트가 대신 확정하지 않는다.

- 정할 것: 더 보기 버튼 위에 어디까지 보여줄 것인가.
- 생각할 거리
  - **발행된 날 14개**(기본 제안): 항상 14줄쯤 보인다. 발행이 뜸했으면 한 달 전 기사까지 내려간다. 2026-11-22 데이터로는 11.21부터 10월 하순까지다.
  - **달력 14일**: 가장 최근 발행일에서 14일 전까지. 2026-11-22 데이터로는 11.21~11.13의 8줄만 보인다. 구현 예: 가장 최근 날에서 13일을 뺀 날짜 문자열을 돌려준다(목록에 없는 날이어도 된다. 이 경우 Step 1 테스트의 "cutoff is one of the listed days" 단정은 지운다).
  - **이번 달만**: 달 구분선과 경계가 겹쳐 깔끔하지만 월초에는 한두 줄만 보인다.
- 바꾼 뒤 Step 4를 다시 실행한다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/newsDesks.js frontend/tests/news-desks-select.test.mjs
git commit -m "feat: month dividers and a recent/older split for the news list"
```

### Task 2: 목록 마크업

**Files:**
- Modify: `frontend/src/components/newsprint/NewsDeskList.astro` (전체 교체)
- Test: `frontend/tests/news-list-desks.test.cjs`

- [ ] **Step 1: 테스트를 새 구조에 맞게 고친다**

`news-list-desks.test.cjs`에서 아래 세 줄 묶음을 찾는다.

```js
for (const s of ['비즈니스 데스크', '리서치 데스크', 'Business desk', 'Research desk', '이날은 리서치 기사가 없어요', 'No research story this day']) {
  assert(list.includes(s), `copy: ${s}`);
}
assert(/<p class="news-desk-empty news-desk-empty--business">/.test(list) && !/news-desk-empty[^>]*(data-search-text|newsprint-card)/.test(list), 'empty placeholders are plain elements');
```

이것을 아래로 바꾼다.

```js
for (const s of ['비즈니스 데스크', '리서치 데스크', 'Business desk', 'Research desk', '주간 정리', 'Weekly', '이전 기사 더 보기', 'Show earlier stories', '오늘', 'Today']) {
  assert(list.includes(s), `copy: ${s}`);
}
assert(!list.includes('news-desk-empty') && !/없어요|No (business|research) story/.test(list), 'no empty-cell placeholders: a lone story takes both columns');
assert(list.includes("solo ? ' news-desk-row--solo' : ''") && /const solo = !entry\.business !== !entry\.research;/.test(list), 'solo row when exactly one desk has a story');
assert(list.includes('addListBreaks(entries)') && list.includes('class="news-desk-month"') && list.includes('monthLabel(entry.month, locale)'), 'month dividers from addListBreaks');
assert((list.match(/data-older=\{olderAttr\(entry\)\}/g) || []).length === 3, 'month, weekly and day entries carry data-older');
assert(list.includes('data-expanded="false"') && list.includes('data-news-more') && list.includes('{olderCount > 0 && ('), 'more button only when something is folded');
assert(list.includes('<em class="news-desk-today">{copy.today}</em>'), 'today marker on its own line');
const heads = ['<span></span>', 'news-desks-head--business', 'news-desks-head--research'].map((s) => list.indexOf(s));
assert(heads.every((i) => i > 0) && heads[0] < heads[1] && heads[1] < heads[2], 'column heads: blank date column first');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-list-desks.test.cjs`
Expected: `AssertionError … copy: 주간 정리`

- [ ] **Step 3: 컴포넌트를 다시 쓴다**

`frontend/src/components/newsprint/NewsDeskList.astro` 전체를 아래로 바꾼다.

```astro
---
// frontend/src/components/newsprint/NewsDeskList.astro
// News list: date | business | research, one row per KST day. A day with one desk's
// story lets it span both columns. Month dividers and the recent/older split come
// from addListBreaks(); older entries are folded by CSS until "more" is pressed.
import NewsDeskCell from './NewsDeskCell.astro';
import { addListBreaks, deskDateParts, monthLabel } from '../../lib/newsDesks.js';

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
      today: '오늘', weekly: '주간 정리', more: '이전 기사 더 보기',
    }
  : {
      business: 'Business desk', businessSub: 'Money and markets',
      research: 'Research desk', researchSub: 'Papers and tech',
      today: 'Today', weekly: 'Weekly', more: 'Show earlier stories',
    };

const listed = addListBreaks(entries);
const storyCount = (entry: any) =>
  entry.kind === 'weekly' ? 1 : entry.kind === 'day' ? (entry.business ? 1 : 0) + (entry.research ? 1 : 0) : 0;
const olderCount = listed.reduce((n: number, entry: any) => (entry.older ? n + storyCount(entry) : n), 0);
const olderAttr = (entry: any) => (entry.older ? 'true' : undefined);
---

<div id="news-list-results" class="news-desks" data-mode="desks" data-expanded="false">
  <div class="news-desks-heads" aria-hidden="true">
    <span></span>
    <p class="news-desks-head news-desks-head--business">{copy.business} <small>· {copy.businessSub}</small></p>
    <p class="news-desks-head news-desks-head--research">{copy.research} <small>· {copy.researchSub}</small></p>
  </div>
  {listed.map((entry: any) => {
    if (entry.kind === 'month') {
      return <p class="news-desk-month" data-older={olderAttr(entry)}>{monthLabel(entry.month, locale)}</p>;
    }
    const date = deskDateParts(entry.day, locale);
    if (entry.kind === 'weekly') {
      return (
        <div class="news-desk-weekly" data-older={olderAttr(entry)}>
          <p class="news-desk-weekly-when"><b>{copy.weekly}</b><span>{date.short} · {date.issue}</span></p>
          <NewsDeskCell locale={locale} post={entry.post} side="weekly" />
        </div>
      );
    }
    const solo = !entry.business !== !entry.research;
    return (
      <div class={`news-desk-row${entry.isToday ? ' news-desk-row--today' : ''}${entry.showDate ? '' : ' news-desk-row--cont'}${solo ? ' news-desk-row--solo' : ''}`} data-older={olderAttr(entry)}>
        <p class="news-desk-date">
          {entry.showDate && (
            <>
              <b>{date.short}</b>
              <span>{date.weekday} · {date.issue}</span>
              {entry.isToday && <em class="news-desk-today">{copy.today}</em>}
            </>
          )}
        </p>
        {entry.business && <NewsDeskCell locale={locale} post={entry.business} side="business" isToday={entry.isToday} />}
        {entry.research && <NewsDeskCell locale={locale} post={entry.research} side="research" isToday={entry.isToday} />}
      </div>
    );
  })}
  {olderCount > 0 && (
    <button type="button" class="news-desks-more" data-news-more>{copy.more}<span>{isKo ? `${olderCount}편` : olderCount}</span></button>
  )}
</div>
```

- [ ] **Step 4: 마크업 단정까지 통과하는지 확인한다**

Run: `node frontend/tests/news-list-desks.test.cjs`
Expected: 마크업 단정은 통과하고 CSS 단정에서 멈춘다(다음 Task에서 고친다). 지금 나오는 메시지는 `desk grid: business | date | research`가 **아니어야** 한다. 그 단정은 CSS를 아직 안 바꿨으므로 통과한다. 통과 문구 `news-list-desks.test.cjs passed`가 나오면 정상이다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/newsprint/NewsDeskList.astro frontend/tests/news-list-desks.test.cjs
git commit -m "feat: news list rows with a left date column, solo stories and month dividers"
```

---

## Chunk 2: 스타일, 동작, 머리

### Task 3: 데스크 CSS 교체

**Files:**
- Modify: `frontend/src/styles/global.css` (`.news-desks-heads {`부터 `.newsprint-article-topline {` 바로 앞까지)
- Test: `frontend/tests/news-list-desks.test.cjs`

- [ ] **Step 1: 테스트의 CSS 단정을 고친다**

`news-list-desks.test.cjs`에서 두 줄을 바꾼다.

```js
// before
assert(/grid-template-areas:\s*"business date research"/.test(css), 'desk grid: business | date | research');
// after
assert(/grid-template-areas:\s*"date business research"/.test(css), 'desk grid: date | business | research');
```

```js
// before
assert(/\[data-theme="dark"\] \.news-desk-weekly\s*\{/.test(css), 'dark weekly band rule');
// after
assert(!/\[data-theme="dark"\] \.news-desk-weekly\s*\{/.test(css) && !/\.news-desk-weekly\s*\{[^}]*background:/.test(css), 'weekly recap is ruled, not a filled band');
```

그 바로 아래에 추가한다.

```js
assert(/\.news-desk-row--solo > \.news-desk-cell\s*\{[^}]*grid-column:\s*2 \/ 4/.test(css), 'solo story spans both desk columns');
assert(!/\.news-desk-empty/.test(css) && !/text-align:\s*right/.test(css.slice(css.indexOf('.news-desks-heads {'), css.indexOf('.newsprint-article-topline {'))), 'no empty-cell styles, nothing right-aligned in the desk block');
assert(/\.news-desk-excerpt\s*\{[^}]*-webkit-line-clamp:\s*2[^}]*word-break:\s*keep-all/.test(css), 'excerpt: two lines, no mid-word breaks');
assert(css.includes('.news-desks[data-mode="desks"]:not([data-expanded="true"]) [data-older="true"] {'), 'older entries fold only in desk mode');
assert(css.includes('.news-desks[data-mode="desks"] .news-desk-row:not(.news-desk-row--solo) .news-desk-label {'), 'desk label hidden only where the column already says it');
assert(/\.news-desks\[data-mode="list"\] \.news-desks-more,\s*\n\.news-desks\[data-expanded="true"\] \.news-desks-more\s*\{\s*display:\s*none;/.test(css), 'more button gone in list mode and once expanded');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-list-desks.test.cjs`
Expected: `AssertionError … desk grid: date | business | research`

- [ ] **Step 3: CSS 블록을 교체한다**

`frontend/src/styles/global.css`에서 줄 맨 앞에서 시작하는 `.news-desks-heads {` 규칙(같은 선택자가 뒤에 다른 선택자의 일부로 더 나온다. 첫 번째 것이다)부터 줄 맨 앞의 `.newsprint-article-topline {` **바로 앞**까지를 통째로 아래로 바꾼다. 그 위의 `.news-desks-note` 규칙과 그 아래의 `.newsprint-article-topline` 규칙은 건드리지 않는다.

```css
.news-desks-heads {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) minmax(0, 1fr);
  gap: 0 1.75rem;
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
  color: var(--tier-paid);
}

.news-desks-head--research {
  color: var(--tier-freemium);
}

/* One KST day: date | business | research, everything left-aligned */
.news-desk-row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) minmax(0, 1fr);
  grid-template-areas: "date business research";
  gap: 0 1.75rem;
  padding: 1.1rem 0 1rem;
  border-bottom: 1px dotted var(--color-border);
}

.news-desk-row > .news-desk-date {
  grid-area: date;
}

.news-desk-row > .news-desk-cell--business {
  grid-area: business;
  padding: 0;
}

.news-desk-row > .news-desk-cell--research {
  grid-area: research;
  padding: 0;
}

/* Only one desk published that day: its story takes both columns */
.news-desk-row--solo > .news-desk-cell {
  grid-area: auto;
  grid-column: 2 / 4;
  max-width: 47.5rem;
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
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
}

.news-desk-date b {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 1.6rem;
  font-weight: 500;
  line-height: 1;
}

.news-desk-date span {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.news-desk-today {
  font-size: 0.7rem;
  font-style: normal;
  font-weight: 700;
  color: var(--color-accent);
}

.news-desk-row--today .news-desk-date b {
  color: var(--color-accent);
}

.news-desk-label {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  margin-bottom: 0.3rem;
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
  gap: 0.75rem;
}

.news-desk-title {
  flex: 1;
  font-family: var(--font-heading);
  font-size: 1.19rem;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: -0.035em;
  word-break: keep-all;
  transition: color 150ms ease;
}

.news-desk-cell--today .news-desk-title {
  font-size: 1.4rem;
}

.news-desk-cell:hover .news-desk-title {
  color: var(--color-accent);
}

.news-desk-excerpt {
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--color-text-secondary);
  margin-top: 0.4rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.news-desk-meta {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.35rem;
}

/* Month divider between months */
.news-desk-month {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 1.75rem 0 0.25rem;
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 0.95rem;
  color: var(--color-text-muted);
}

.news-desk-month::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

/* Weekly recap: ruled row, label in the date column */
.news-desk-weekly {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 0 1.75rem;
  margin: 0.6rem 0;
  padding: 0.9rem 0;
  border-top: 2px solid var(--color-text-primary);
  border-bottom: 1px solid var(--color-text-primary);
}

.news-desk-weekly-when {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.75rem;
}

.news-desk-weekly-when b {
  font-weight: 700;
}

.news-desk-weekly-when span {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.news-desk-weekly .newsprint-card {
  max-width: 47.5rem;
  padding: 0;
}

/* The date column already says "weekly": keep the cell label for screen readers only */
.news-desk-weekly .news-desk-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.news-desk-weekly .news-desk-excerpt {
  -webkit-line-clamp: 1;
}

.news-desk-row[data-row-empty="true"],
.news-desk-weekly[data-row-empty="true"] {
  display: none;
}

/* Recent stories first: older entries stay in the DOM (search still finds them) and unfold on "more" */
.news-desks[data-mode="desks"]:not([data-expanded="true"]) [data-older="true"] {
  display: none;
}

.news-desks-more {
  display: block;
  width: 100%;
  min-height: 2.75rem;
  margin-top: 1.5rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--color-border);
  background: none;
  font-family: var(--font-ui);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: border-color 150ms ease;
}

.news-desks-more span {
  margin-left: 0.4rem;
  font-weight: 400;
  color: var(--color-text-muted);
}

.news-desks-more:hover {
  border-color: var(--color-text-primary);
}

.news-desks[data-mode="list"] .news-desks-more,
.news-desks[data-expanded="true"] .news-desks-more {
  display: none;
}

/* Desktop desk mode: a two-story row's column says which desk — keep the label for screen readers only */
@media (min-width: 768px) {
  .news-desks[data-mode="desks"] .news-desk-row:not(.news-desk-row--solo) .news-desk-label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
}

/* List mode (a desk tab or a search query is active): one column, everything unfolded */
.news-desks[data-mode="list"] .news-desks-heads,
.news-desks[data-mode="list"] .news-desk-month {
  display: none;
}

.news-desks[data-mode="list"] .news-desk-row {
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas: none;
  gap: 0.6rem 0;
}

.news-desks[data-mode="list"] .news-desk-row > * {
  grid-area: auto;
  grid-column: auto;
  max-width: none;
}

.news-desks[data-mode="list"] .news-desk-date {
  flex-direction: row;
  align-items: baseline;
  gap: 0.5rem;
}

.news-desks[data-mode="list"] .news-desk-row--cont .news-desk-date {
  display: none;
}

.news-desks[data-mode="list"] .news-desk-weekly {
  grid-template-columns: minmax(0, 1fr);
  gap: 0.4rem 0;
}

.news-desks[data-mode="list"] .news-desk-weekly-when {
  flex-direction: row;
  align-items: baseline;
  gap: 0.5rem;
}

@media (max-width: 767px) {
  .news-desks-heads {
    display: none;
  }

  .news-desk-row {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: none;
    gap: 0;
    padding: 0.9rem 0 0.4rem;
  }

  /* 0,2,0 + later in file: beats the named-area and solo rules so items stack in DOM order */
  .news-desks .news-desk-row > * {
    grid-area: auto;
    grid-column: auto;
    max-width: none;
  }

  .news-desks .news-desk-row > .news-desk-cell {
    margin-bottom: 0.6rem;
    padding: 0.5rem 0 0.6rem 0.75rem;
    border-left: 2px solid var(--desk);
  }

  .news-desk-date {
    flex-direction: row;
    align-items: baseline;
    gap: 0.5rem;
    padding-bottom: 0.5rem;
  }

  .news-desk-row--cont .news-desk-date {
    display: none;
  }

  .news-desk-weekly {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.4rem 0;
  }

  .news-desk-weekly-when {
    flex-direction: row;
    align-items: baseline;
    gap: 0.5rem;
  }
}

```

- [ ] **Step 4: 통과와 회귀를 확인한다**

Run:
```bash
node frontend/tests/news-list-desks.test.cjs
node frontend/tests/list-v2.test.cjs
node frontend/tests/font-roles.test.cjs
node frontend/tests/news-search-list-structure.test.cjs
node frontend/tests/retro-decoration-removed.test.cjs
```
Expected: 다섯 파일 모두 `… passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/news-list-desks.test.cjs
git commit -m "feat: left-aligned news list with two-line excerpts and a ruled weekly row"
```

### Task 4: 더 보기 동작

**Files:**
- Modify: `frontend/src/scripts/newsDeskMode.ts`
- Test: `frontend/tests/news-list-desks.test.cjs`

- [ ] **Step 1: 테스트에 단정을 더한다**

`news-list-desks.test.cjs`에서 `assert(mode.includes('data-row-empty'), 'mode script hides empty rows');` 줄 바로 아래에 추가한다.

```js
assert(mode.includes("'[data-news-more]'") && mode.includes("root.dataset.expanded = 'true'"), 'mode script: more button expands the list');
assert(mode.includes("sessionStorage.setItem(EXPANDED_KEY, '1')") && mode.includes("sessionStorage.getItem(EXPANDED_KEY) === '1'"), 'mode script: expanded state survives a visit to an article');
assert(/try \{[^}]*sessionStorage\.setItem/.test(mode) && /try \{[^}]*sessionStorage\.getItem/.test(mode), 'storage access is guarded');
assert(mode.includes("'[data-older=\"true\"] a'"), 'focus moves to the first revealed story');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-list-desks.test.cjs`
Expected: `AssertionError … mode script: more button expands the list`

- [ ] **Step 3: 스크립트를 고친다**

`frontend/src/scripts/newsDeskMode.ts`의 맨 위 주석 네 줄 아래, `function activeFilter()` 위에 추가한다.

```ts
// Also runs the "more" button: older entries are folded by CSS until data-expanded is true.
const EXPANDED_KEY = 'news-list-expanded';

function wasExpanded(): boolean {
  try { return sessionStorage.getItem(EXPANDED_KEY) === '1'; } catch { return false; }
}

function expand(root: HTMLElement, moveFocus: boolean): void {
  root.dataset.expanded = 'true';
  try { sessionStorage.setItem(EXPANDED_KEY, '1'); } catch { /* storage blocked: nothing to remember */ }
  // The button disappears once expanded, so hand focus to the first story it revealed.
  if (moveFocus) root.querySelector<HTMLElement>('[data-older="true"] a')?.focus();
}

```

`init()` 안에서 `root.dataset.deskModeReady = 'true';` 줄 바로 아래에 추가한다.

```ts
  if (wasExpanded()) expand(root, false);
  root.querySelector<HTMLElement>('[data-news-more]')?.addEventListener('click', () => expand(root, true));
```

- [ ] **Step 4: 통과를 확인한다**

Run: `node frontend/tests/news-list-desks.test.cjs`
Expected: `news-list-desks.test.cjs passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/scripts/newsDeskMode.ts frontend/tests/news-list-desks.test.cjs
git commit -m "feat: unfold earlier stories on the news list and remember it for the session"
```

### Task 5: 줄인 마스트헤드

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintShell.astro`
- Modify: `frontend/src/pages/ko/news/index.astro`, `frontend/src/pages/en/news/index.astro`
- Modify: `frontend/src/styles/global.css` (첫 번째 `.newsprint-grid {` 규칙 바로 앞)
- Test: `frontend/tests/news-list-desks.test.cjs`

- [ ] **Step 1: 테스트에 단정을 더한다**

`news-list-desks.test.cjs`에서 `assert(/rail\?: boolean/.test(shell) && /\{rail && \(/.test(shell), 'shell can drop the rail');` 줄 바로 아래에 추가한다.

```js
assert(/tight\?: boolean;/.test(shell) && shell.includes("class={`newsprint-header${tight ? ' newsprint-header--tight' : ''}`}"), 'shell: tight masthead is opt-in');
assert(/\.newsprint-header--tight \.newsprint-masthead\s*\{[^}]*font-size:\s*clamp\(1\.7rem, 4\.4vw, 2\.4rem\)/.test(css), 'tight masthead is about half size');
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/news/index.astro`);
  assert(/<NewsprintShell[\s\S]*?\n\s+tight\s*\n/.test(page), `${locale}: news list uses the tight masthead`);
  assert(!/subkicker|parseJsonArray/.test(page), `${locale}: no subkicker row on the news list`);
}
for (const p of ['pages/ko/handbook/index.astro', 'pages/en/handbook/index.astro']) {
  assert(!/\n\s+tight\s*\n/.test(read(p)), `${p}: handbook list keeps the full masthead`);
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node frontend/tests/news-list-desks.test.cjs`
Expected: `AssertionError … shell: tight masthead is opt-in`

- [ ] **Step 3: Shell을 고친다**

`NewsprintShell.astro`의 `interface Props`에서 `compact?: boolean;` 줄 아래에 추가한다.

```ts
  /** full header only: half-size masthead (news list) */
  tight?: boolean;
```

구조 분해 줄에서 `compact = false,` 뒤에 `tight = false,`를 넣는다.

```ts
const { locale, masthead = '', editionLabel, subkicker, publishedAt, rail = true, compact = false, tight = false, backHref, backLabel, crumbItems, crumbDesk, crumbReading } = Astro.props;
```

`<header class="newsprint-header">`를 바꾼다.

```astro
    <header class={`newsprint-header${tight ? ' newsprint-header--tight' : ''}`}>
```

- [ ] **Step 4: 목록 페이지 두 곳을 고친다**

`frontend/src/pages/ko/news/index.astro`와 `frontend/src/pages/en/news/index.astro` 둘 다 같은 네 군데를 고친다.

```ts
// before
import { getSiteContents, parseJsonArray } from '../../../lib/siteContent';
// after
import { getSiteContents } from '../../../lib/siteContent';
```

```ts
// before
    ['editorial_note', 'news_masthead', 'news_edition_label', 'news_subkicker'],
// after
    ['editorial_note', 'news_masthead', 'news_edition_label'],
```

`const subkicker = parseJsonArray<string>(…);` 줄을 지운다(KO와 EN의 기본값 문자열이 다르다. 줄 전체를 지운다).

```astro
// before
    subkicker={subkicker}
    rail={false}
// after
    tight
    rail={false}
```

- [ ] **Step 5: CSS를 추가한다**

`frontend/src/styles/global.css`에서 첫 번째 `.newsprint-grid {` 줄(479px 마스트헤드 미디어 블록 바로 다음에 있다) **바로 앞**에 넣는다.

```css
/* Tight masthead (news list): half-size name so the first story starts sooner */
.newsprint-header--tight {
  margin-bottom: 1rem;
}

.newsprint-header--tight .newsprint-masthead {
  margin-top: 0.5rem;
  margin-bottom: 0.6rem;
  font-size: clamp(1.7rem, 4.4vw, 2.4rem);
}

```

- [ ] **Step 6: 통과와 회귀를 확인한다**

Run:
```bash
node frontend/tests/news-list-desks.test.cjs
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/issue-number-shell.test.cjs
node frontend/tests/news-article-briefing.test.cjs
node frontend/tests/news-article-reading.test.cjs
node frontend/tests/font-roles.test.cjs
```
Expected: 여섯 파일 모두 `… passed`

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/newsprint/NewsprintShell.astro frontend/src/pages/ko/news/index.astro frontend/src/pages/en/news/index.astro frontend/src/styles/global.css frontend/tests/news-list-desks.test.cjs
git commit -m "feat: half-size masthead on the news list"
```

### Task 6: 빌드와 실제 화면 확인

**Files:** 없음(확인만). 고칠 것이 나오면 해당 Task의 파일을 고치고 그 Task의 테스트를 다시 돌린다.

- [ ] **Step 1: 전체 테스트** — "사전 정보"의 명령을 돌려 실패 목록이 시작할 때 기록한 것과 같은지 본다.
- [ ] **Step 2: 빌드** — `cd frontend && npm run build`, 오류 0.
- [ ] **Step 3: 개발 서버로 화면을 본다** — `/ko/news/`와 `/en/news/`, 1280×900과 390×844, 종이·다크 테마.
  - [ ] 날짜가 왼쪽, 모든 글이 왼쪽 정렬이다. 북마크가 제목 오른쪽에 있다.
  - [ ] 한쪽만 있는 날은 기사가 넓게 나오고 색 점 라벨이 보인다. 양쪽 다 있는 날은 두 칸이고 라벨이 안 보인다.
  - [ ] 요약문이 두 줄이고 단어 중간에서 끊기지 않는다.
  - [ ] 주간 정리가 선으로만 구분된다. 달이 바뀌는 곳에 구분선이 있다.
  - [ ] 더 보기 버튼에 접힌 기사 수가 나온다. 누르면 펼쳐지고 버튼이 사라진다. 기사에 들어갔다 뒤로 오면 펼친 상태다.
  - [ ] 검색어를 넣으면 접혀 있던 기사도 결과에 나온다. 탭(비즈니스·리서치·주간 정리)도 마찬가지다. 검색어를 지우면 다시 데스크 모드다.
  - [ ] 마스트헤드가 작아졌고 보조 줄이 없다. 용어집 목록의 마스트헤드는 그대로다.
  - [ ] 모바일: 날짜 → 기사 한 단, 왼쪽 색 선, 가로 넘침 없음.
  - [ ] 다크 테마에서 주간 정리 선과 더 보기 버튼이 보인다.
  - [ ] 첫 기사 위치(바꾸기 전 데스크톱 507px, 모바일 467px)와 페이지 길이(11,917px, 24,637px)를 재서 적는다.
- [ ] **Step 4: 문서 상태를 갱신하고 커밋**

스펙의 Status를 `implemented (<날짜>) — [[2026-11-22-news-list-reading]]`로, 이 계획 제목 아래에 `**Status:** done (<날짜>)`와 실행 결과를 적는다.

```bash
git add vault/09-Implementation/plans/2026-11-22-news-list-reading-design.md vault/09-Implementation/plans/2026-11-22-news-list-reading.md
git commit -m "docs: record the news list reading pass"
```

---

## 실행 결과 (2026-11-22)

- 작업 폴더: `C:UsersamyDesktop to1log-news-list` (`main`의 worktree).
- 테스트: 전체 실행 시 실패 목록이 시작 전 16개와 같다. `news-list-desks`, `news-desks-select` 통과.
- 빌드: `npm run build` 오류 0.
- 화면(개발 서버, `/ko/news/`, 2026-11-22 데이터)

| 항목 | 전 | 후 |
|---|---|---|
| 첫 기사 위치(데스크톱 1280) | 507px | 414px |
| 첫 기사 위치(모바일 390) | 467px | 404px |
| 페이지 길이(데스크톱) | 11,917px | 3,197px (펼치면 13,087px) |
| 페이지 길이(모바일) | 24,637px | 5,419px |
| 처음 보이는 기사 | 120편 | 21편(날짜 줄 13개 + 주간 2개), 나머지 99편은 더 보기 |
| 빈 칸 문구 | 날짜 줄 56개 중 12개 | 0 |

- 확인한 동작: 한쪽만 있는 날의 넓은 칸과 라벨, 검색("Gemini" 18/120, 접혀 있던 8월 기사까지), 탭(주간 정리 20/120), 더 보기 후 포커스 이동, 기사에 들어갔다 뒤로 왔을 때 펼친 상태 유지, 다크 테마, 모바일 한 단, EN 문구("October 2026", "Show earlier stories · 99"), 용어집 목록 마스트헤드는 그대로.
- 계획과 달라진 것(검토 결과 반영, 커밋 `fix: restore the unfolded news list before paint…`)
  - 펼친 상태 복원을 `astro:page-load`가 아니라 인라인 스크립트와 `astro:before-swap`에서 한다.
  - 더 보기 문구의 가운뎃점을 실제 글자로 넣었다. 주간 정리의 보이는 라벨은 `aria-hidden`.
  - 모바일 목록 모드의 간격 중복, 주간 정리 칸의 최대 폭, 주간 정리 날짜 줄바꿈("제243/호")을 고쳤다.
  - 북마크 버튼(44px)이 한 줄 제목의 줄 높이를 늘리던 것을 음수 여백으로 없앴다. 누르는 영역은 그대로다.
  - Task 1 Step 5(사람이 정하는 단계)는 기본 제안으로 커밋하고 진행했다.
- 확인하지 못한 것: 순백 테마, 키보드만으로 더 보기를 눌렀을 때의 실제 읽기 프로그램 출력.
- 눈에 띈 것(이번 범위 밖)
  - 기사에서 뒤로 오면 스크롤이 맨 위로 간다. 운영 사이트(바꾸기 전)에서도 같다. `NewsprintCategoryFilter`가 초기화 때 `history.replaceState(null, …)`로 Astro의 기록 상태를 지우는 것이 원인으로 보인다.
  - `recentCutoff`는 주간 정리만 있는 날도 하루로 센다. 주간 정리 쿼리(20건)가 일간(100건)보다 훨씬 과거까지 가서, 펼친 목록의 끝부분은 달 구분선과 주간 정리만 이어진다.
