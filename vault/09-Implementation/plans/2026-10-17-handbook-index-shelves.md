# 용어집 첫 화면 B+A(서가 + A–Z 색인) Implementation Plan

**Status:** done (2026-10-17) — 실행 결과는 문서 끝 참조.

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** ready (2026-10-17)

**Goal:** `/ko/handbook/`, `/en/handbook/` 첫 화면을 "소개 한 줄 → 통계 → 검색 → 오늘의 용어(+먹색 판) → 분야별 서가 → A–Z 색인"으로 바꾼다. 검색어나 `?category=`가 있으면 지금처럼 카드 목록만 보인다.

**Architecture:**
- 오늘의 용어 쿼리는 새 공유 모듈 `lib/pageData/termOfDay.ts`가 맡는다. 홈(`homeFrontPage.ts`)과 용어집이 같은 함수를 부른다.
- 서가·색인·이름·평문 계산은 순수 함수 `lib/handbookShelves.js`가 맡는다(단위 테스트 대상).
- 새 컴포넌트 3개(`components/handbook/HandbookToday|HandbookShelves|HandbookAzIndex.astro`)가 화면을 그린다.
- 페이지 인라인 스크립트는 "기본 모드 ↔ 검색 모드"만 전환한다. 분야 버튼·무한 스크롤은 없앤다.
- 쓰지 않게 되는 레일 컴포넌트와 CSS(인기 용어·분야 쇼케이스·분야 버튼·레일 분야 아이콘)는 지운다.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-10-17-handbook-index-shelves-design]] — 구현 전에 반드시 읽는다.

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `pages/admin/pipeline-runs/*`, `frontend/src/lib/pageData/publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 **읽기만 하고 수정·stage하지 않는다**. 특히 `publicTermIndex.ts`는 이번 작업에서 건드리지 않는다.
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- **백슬래시가 있는 파일(정규식 테스트, `handbookShelves.js`, 페이지의 `'\u2026'`, CSS)은 Write/Edit 도구로만 작성한다.** Bash heredoc을 쓰면 백슬래시가 사라진다.
- 줄바꿈
  - `frontend/src/lib/pageData/handbookPage.ts`는 **CRLF와 LF가 섞여 있다.** Edit 도구로만 고치고 sed/bash로 고치지 않는다.
  - `global.css`, 핸드북 페이지 2개, `homeFrontPage.ts`, 테스트 파일들은 LF다. CSS 규칙은 줄 번호가 아니라 셀렉터/주석으로 찾는다.
  - 기존 파일을 Write로 통째로 바꾸기 전에 반드시 Read로 먼저 읽는다(도구 요구사항).
- dev 서버 때문에 `npm run build`가 EPERM으로 실패하면 재시도하지 말고 보고한다.

**지켜야 할 것**
- 목록은 CDN에 캐시된다(`LIST_CDN_POLICY`). 새로 `Astro.locals.user`/세션을 쓰지 않는다. 북마크 버튼은 항상 `data-bookmarked="false"`로 렌더한다(현행).
- 용어 전체 쿼리(`getHandbookPageData`, `.limit(500)`, 필드)는 그대로 둔다. `public-list-query-budget`이 고정한다.
- 검색 카드 innerHTML 렌더링(현행 문자열 연결, 이스케이프 없음)은 **그대로 옮긴다.** 이스케이프 개선은 범위 밖이다(스펙 "범위 밖").
- 테스트 기준선(2026-10-17, 계획 작성 시 측정): **PASS 74 / FAIL 21**. 이미 실패 중인 21개 중 이번 작업과 관련된 것은 `handbook-category-icons`(Task 3에서 삭제), `handbook-search-recognition`(테마 입력면 색 단언 때문에 실패. 이번 작업 후에도 같은 메시지로 실패해야 정상)이다.
  - 완료 후 기대값: 삭제 1개(FAIL→없음), 신규 3개 PASS → **PASS 77 / FAIL 20, 신규 FAIL 0**. 다른 세션 변경으로 숫자가 흔들릴 수 있으니 판정은 **이름 기준**으로 한다.

**현재 코드**
- `frontend/src/pages/{ko,en}/handbook/index.astro`(각 375줄. 두 파일은 문구·locale만 다르다)
  - `handbookTags` 하드코딩, 인기 용어 쿼리 2개(view_count → published_at 폴백), `section.handbook-trending`, `section#handbook-showcase.product-category-showcase`, `#handbook-controls`(분야 버튼), `HandbookListRail`(레일)
  - 인라인 스크립트 `initHandbookFilters`: 분야 버튼, `?category=`/`?q=`, 카드 지연 생성(`ensureCards`), 기본 모드에서 20개씩 무한 스크롤(sentinel + IntersectionObserver)
- `lib/pageData/handbookPage.ts`: `getHandbookPageData`가 `allTerms`, `termsByCategory`, `totalTerms`, `error`를 반환한다. `termsByCategory`는 handbook index 두 페이지만 쓴다(grep 확인).
- `lib/pageData/homeFrontPage.ts`: 뉴스 쿼리 + count(head)를 병렬로 부른 뒤 `termIndex(now, total)` → `.order('slug').range(i, i).maybeSingle()`로 오늘의 용어를 고른다.
- `lib/homeFront.js`의 `termIndex`, `lib/issue.js`의 `issueLabel`/`issueNumber`는 그대로 쓴다.
- `NewsprintShell`은 이미 `rail?: boolean` prop이 있고, `rail={false}`면 `.newsprint-grid--full`(뉴스 목록 작업에서 추가한 1단 CSS)이 붙는다.
- 홈 키워드 판 CSS `.home-front-plate`(먹색 면 + 점 무늬, 다크는 `--color-bg-tertiary`)를 오늘의 용어 판의 규칙으로 따른다.
- 글꼴: `--font-heading`=Hahmlet(600/700만 로드), `--font-masthead`=Newsreader(500만 로드). 굵기는 이 범위 안에서만 쓴다.
- `components/handbook/` 디렉터리는 아직 없다(새로 만든다).

**스펙 해석(실행자가 임의로 바꾸지 않는다)**
- `#` 그룹의 앵커는 `id="az-num"`이다. `id="az-#"`/`href="#az-#"`는 URL 조각에 `#`가 두 번 들어가 불안정하다. 나머지 글자는 `az-A`…`az-Z`다. `buildAzIndex`가 `anchor` 필드로 준다.
- 표시 이름 규칙은 `termNames(term, locale)` 한 함수로 통일한다. KO는 `korean_name`이 있고 `term`과 다르면 `{ name: korean_name, sub: term }`, 그 밖에는 `{ name: term, sub: '' }`. EN은 항상 `{ name: term, sub: '' }`.
- 인기 용어 쿼리는 서가 정렬에만 쓰므로 select 열을 `slug, view_count`(폴백은 `slug`)로 줄인다. 조건·정렬·`.limit(10)`은 그대로다.
- 통계 줄은 소개 한 줄 아래에서 가운데 정렬한다(`.handbook-intro + .handbook-hero-stats`). 내용("N+ 용어 · M 카테고리")은 현행 그대로다.
- 태블릿(768–1023px)은 서가 2열, 사전 2단이다. 데스크톱 3열/3단, 모바일 1열/1단은 스펙 그대로다.
- 서가 채우기(컨트롤러 결정, 스펙에도 한 줄 추가됨): 첫 정규 분야로 놓은 용어가 목표 수(넓은 서가 6 / 나머지 4)보다 적으면, 그 분야 소속 용어 중 아직 어느 서가에도 안 보인 용어로 채운다(분야 정규 순서대로). 그래도 모자라면 다른 서가에 이미 보인 소속 용어(중복)로 채운다. 각 단계 순서는 trending → `term` 알파벳이다. 그래서 숫자만 있고 목록이 빈 서가는 생기지 않는다.

**계획 사전 검증(작성 시 scratchpad 복제본에서 수행)**
- Task 1–4의 코드·테스트를 그대로 적용해 돌렸다. 각 Step 2는 적힌 메시지로 실패, Step 통과 확인은 PASS, 전체 **PASS 77 / FAIL 20**(기준선에서 `handbook-category-icons`만 빠짐), `astro build` "Complete!".
- dev 서버 렌더(운영 데이터): 114+ 용어 · 9 카테고리, 오늘의 용어가 홈과 같음(판 본문 정상), 넓은 서가 = llm-genai(소속 92), math-statistics도 소속 2개라 서가가 보인다(스펙의 "현재 0개"와 다름. 규칙대로 동작). 서가 채우기 적용 후 목록이 빈 서가 0개다(ko/en 동일). 소속 수 / 표시 수는 products-platforms 15/4, llm-genai(넓음) 92/6, deep-learning 28/4, ml-fundamentals 17/4, data-engineering 13/4, infra-hardware 28/4, safety-ethics 7/4, cs-fundamentals 5/4, math-statistics 2/2이다. 중복 표시는 `f1-score` 1개(ml-fundamentals와 math-statistics)다.

---

## Task 1: 오늘의 용어 공유 모듈 + 홈 리팩터 (TDD)

**Files:**
- Create: `frontend/src/lib/pageData/termOfDay.ts`
- Modify: `frontend/src/lib/pageData/homeFrontPage.ts`
- Test: `frontend/tests/term-of-day.test.cjs`(새 파일), `frontend/tests/home-front-query-budget.test.cjs`(갱신)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/term-of-day.test.cjs
// Term of the day: one shared query (published count + one row by slug) for the home and the handbook index.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const tod = read('lib/pageData/termOfDay.ts');
assert(tod.includes('export async function fetchTermOfDay('), 'shared helper is exported');
assert(/extraColumns = ''/.test(tod), 'extra columns are optional');
assert(/count: 'exact', head: true/.test(tod), 'count is head-only');
assert(/termIndex\(now, total\)/.test(tod), 'index = issue number % published count (lib/homeFront.js)');
assert(/\.order\('slug', \{ ascending: true \}\)/.test(tod), 'stable order by slug');
assert(/\.range\(i, i\)/.test(tod) && /\.maybeSingle\(\)/.test(tod), 'single row');
assert(tod.includes('definition:${definitionField}'), 'only the locale definition column');
assert(/return \{ term: null, total: 0 \}/.test(tod), 'errors degrade to an empty result, never throw');

const home = read('lib/pageData/homeFrontPage.ts');
assert(/fetchTermOfDay\(supabase, locale, now\)/.test(home), 'home uses the shared term of the day');
assert(/Promise\.all\(\[[\s\S]*?fetchTermOfDay\(supabase, locale, now\)/.test(home), 'term of the day runs in parallel with the news query');
assert(!/from\('handbook_terms'\)/.test(home), 'home owns no term query');

console.log('term-of-day.test.cjs passed');
```

`home-front-query-budget.test.cjs`는 Read 후 Write로 전체를 다음으로 바꾼다. 용어 쿼리 단언은 전부 `termOfDay.ts` 기준으로 옮기고, 홈 파일에는 뉴스 단언과 `fetchTermOfDay(` 호출 단언만 남긴다.

```js
// frontend/tests/home-front-query-budget.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const read = (p) => fs.readFileSync(path.join(__dirname, '..', p), 'utf8');
const home = read('src/lib/pageData/homeFrontPage.ts');
const tod = read('src/lib/pageData/termOfDay.ts');
const count = (src, re) => (src.match(re) || []).length;

// home: one news query + the shared term of the day
assert.equal(count(home, /\.from\('news_posts'\)/g), 1, 'exactly one news_posts query');
assert.equal(count(home, /\.from\('handbook_terms'\)/g), 0, 'home owns no term query (lib/pageData/termOfDay.ts does)');
assert(/\.from\('news_posts'\)[\s\S]*?\.limit\(6\)/.test(home), 'news query is limited to 6 rows');
assert(/selectFrontPage\(/.test(home), 'selection logic lives in lib/homeFront.js');
assert(/fetchTermOfDay\(/.test(home), 'term of the day comes from the shared helper');
assert(!/select\('\*'\)/.test(home), 'no select(*) on the home');

// term of the day: one count query + one single-row query
assert.equal(count(tod, /\.from\('handbook_terms'\)/g), 2, 'handbook_terms: one count query + one single-row query');
assert(/count: 'exact', head: true/.test(tod), 'term count uses head-only exact count');
assert(/\.range\(i, i\)/.test(tod), 'term fetch is a single row via range(i, i)');
assert(/\.order\('slug'/.test(tod), 'term order is stable by slug');
assert(!/is_favourite/.test(tod), 'term of the day comes from all published terms');
assert(!/select\('\*'\)/.test(tod), 'no select(*)');
assert(/definition:\$\{definitionField\}/.test(tod), 'only the locale definition column is selected');
assert(/termIndex\(/.test(tod), 'term index comes from lib/homeFront.js');
console.log('home-front-query-budget.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run:
```bash
node frontend/tests/term-of-day.test.cjs
node frontend/tests/home-front-query-budget.test.cjs
```
Expected: 둘 다 FAIL. `termOfDay.ts`가 없어 ENOENT가 난다.

- [ ] **Step 3: `termOfDay.ts` 작성** (Write 도구로)

```ts
// frontend/src/lib/pageData/termOfDay.ts
// Term of the day, shared by the home front page and the handbook index:
// published count (head only) -> termIndex(now, count) -> one row ordered by slug.
import type { SupabaseClient } from '@supabase/supabase-js';
import { termIndex } from '../homeFront.js';

export interface TermOfDay {
  term: string;
  slug: string;
  korean_name: string | null;
  definition: string | null;
  [column: string]: unknown;
}

export interface TermOfDayResult {
  term: TermOfDay | null;
  /** published term count (0 when a query failed) */
  total: number;
}

/**
 * @param extraColumns extra select columns, e.g. 'hero_news_context_ko'
 * Never throws: failures are logged and return { term: null, total: 0 }.
 */
export async function fetchTermOfDay(
  db: SupabaseClient | null,
  locale: 'en' | 'ko',
  now = new Date(),
  extraColumns = '',
): Promise<TermOfDayResult> {
  if (!db) return { term: null, total: 0 };
  const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';

  const countRes = await db
    .from('handbook_terms')
    .select('slug', { count: 'exact', head: true })
    .eq('status', 'published');
  if (countRes.error) {
    console.warn('[termOfDay] term count query failed', countRes.error.message);
    return { term: null, total: 0 };
  }

  const total = countRes.count ?? 0;
  const i = termIndex(now, total);
  if (i === null) return { term: null, total };

  const columns = `term, slug, korean_name, definition:${definitionField}${extraColumns ? `, ${extraColumns}` : ''}`;
  const termRes = await db
    .from('handbook_terms')
    .select(columns)
    .eq('status', 'published')
    .order('slug', { ascending: true })
    .range(i, i)
    .maybeSingle();
  if (termRes.error) {
    console.warn('[termOfDay] term query failed', termRes.error.message);
    return { term: null, total: 0 };
  }

  return { term: (termRes.data ?? null) as unknown as TermOfDay | null, total };
}
```

- [ ] **Step 4: `homeFrontPage.ts` 교체** (Read 후 Write로 전체 교체. 동작은 같고, 용어 쿼리만 공유 모듈로 옮긴다)

```ts
// frontend/src/lib/pageData/homeFrontPage.ts
// Lean data for the home front page: 1 news query + the shared term of the day (count + 1 row).
import { supabase } from '../supabase';
import { selectFrontPage } from '../homeFront.js';
import { fetchTermOfDay } from './termOfDay';

export interface HomeFrontNews {
  title: string;
  slug: string;
  post_type: string | null;
  published_at: string | null;
  excerpt: string | null;
  reading_time_min: number | null;
  tags: string[] | null;
}

export interface HomeFrontTerm {
  term: string;
  slug: string;
  korean_name: string | null;
  definition: string | null;
}

export interface HomeFrontPageData {
  lead: HomeFrontNews | null;
  leadIsToday: boolean;
  sibling: HomeFrontNews | null;
  earlier: HomeFrontNews[];
  todayCount: number;
  term: HomeFrontTerm | null;
  keyword: { small: string | null; big: string } | null;
}

const EMPTY: HomeFrontPageData = { lead: null, leadIsToday: false, sibling: null, earlier: [], todayCount: 0, term: null, keyword: null };

export async function getHomeFrontPageData(locale: 'en' | 'ko', now = new Date()): Promise<HomeFrontPageData> {
  if (!supabase) return EMPTY;

  const [newsRes, termOfDay] = await Promise.all([
    supabase
      .from('news_posts')
      .select('title, slug, post_type, published_at, excerpt, reading_time_min, tags')
      .eq('status', 'published')
      .eq('locale', locale)
      .order('published_at', { ascending: false })
      .order('post_type', { ascending: true }) // same-day stories share 00:00Z; keep the lead stable across cache refreshes
      .limit(6),
    fetchTermOfDay(supabase, locale, now),
  ]);

  if (newsRes.error) console.warn('[homeFrontPage] news query failed', newsRes.error.message);
  const news = newsRes.error ? [] : ((newsRes.data ?? []) as HomeFrontNews[]);
  const term = termOfDay.term as HomeFrontTerm | null;

  return selectFrontPage({ news, term, now }) as HomeFrontPageData;
}
```

- [ ] **Step 5: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/term-of-day.test.cjs
node frontend/tests/home-front-query-budget.test.cjs
node frontend/tests/home-front-page.test.cjs
node frontend/tests/home-front-select.test.mjs
```
Expected: 모두 PASS. (`HomeFrontPage.astro`는 `HomeFrontTerm` 타입을 계속 import하므로 export를 지우지 않는다.)

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/pageData/termOfDay.ts frontend/src/lib/pageData/homeFrontPage.ts frontend/tests/term-of-day.test.cjs frontend/tests/home-front-query-budget.test.cjs
git commit -m "feat: share the term of the day query between home and handbook"
```

---

## Task 2: 서가·색인 순수 함수 (TDD)

**Files:**
- Create: `frontend/src/lib/handbookShelves.js`
- Test: `frontend/tests/handbook-shelves.test.mjs`

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/handbook-shelves.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { buildShelves, buildAzIndex, plainDefinition, firstNewsLine, termNames } = await import(
  pathToFileURL(path.join(here, '../src/lib/handbookShelves.js')).href
);

const CATS = ['products-platforms', 'llm-genai', 'deep-learning', 'math-statistics'];
const t = (term, categories, extra = {}) => ({
  term,
  slug: term.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
  categories,
  ...extra,
});

const itemsBySlug = (list) => Object.fromEntries(list.map((s) => [s.slug, s.items.map((i) => i.term)]));

// count = membership; placement = first canonical category (listed first); non-canonical-only terms skipped;
// empty fields hidden. Short shelves fill with their other members (here: duplicates, stage 3).
const terms = [
  t('RAG', ['llm-genai']),
  t('Agent', ['llm-genai', 'products-platforms']), // counted in both, placed in llm-genai
  t('Claude', ['products-platforms', 'llm-genai']), // placed in products-platforms
  t('CNN', ['legacy-slug', 'deep-learning']), // first canonical = deep-learning
  t('Orphan', ['legacy-slug']), // no canonical field: index only
];
let shelves = buildShelves(terms, CATS, []);
assert.deepEqual(shelves.map((s) => [s.slug, s.count, s.wide]), [
  ['products-platforms', 2, false],
  ['llm-genai', 3, true],
  ['deep-learning', 1, false],
]);
assert.deepEqual(itemsBySlug(shelves), {
  'products-platforms': ['Claude', 'Agent'],
  'llm-genai': ['Agent', 'RAG', 'Claude'],
  'deep-learning': ['CNN'],
});
assert(!shelves.some((s) => s.items.some((i) => i.term === 'Orphan')), 'orphan stays out of the shelves');

// fill stages: 1) first canonical, 2) unlisted members, 3) members listed elsewhere (duplicates)
const fillTerms = [
  t('P1', ['products-platforms']),
  t('L1', ['llm-genai', 'products-platforms']),
  t('L2', ['llm-genai', 'products-platforms']),
  ...['L3', 'L4', 'L5', 'L6', 'L7'].map((n) => t(n, ['llm-genai'])),
  t('X1', ['llm-genai', 'deep-learning']), // placed in llm-genai but not among its 6 listed
  t('X2', ['llm-genai', 'deep-learning']),
  t('D1', ['deep-learning']),
];
shelves = buildShelves(fillTerms, CATS, ['l2']);
assert.deepEqual(shelves.map((s) => [s.slug, s.count, s.wide]), [
  ['products-platforms', 3, false],
  ['llm-genai', 9, true],
  ['deep-learning', 3, false],
]);
assert.deepEqual(itemsBySlug(shelves), {
  'llm-genai': ['L2', 'L1', 'L3', 'L4', 'L5', 'L6'], // stage 1 only, trending first
  'products-platforms': ['P1', 'L2', 'L1'], // no unlisted members -> stage 3 duplicates, trending first
  'deep-learning': ['D1', 'X1', 'X2'], // stage 2: unlisted members; no more members, stays short of 4
});
assert(shelves.every((s) => s.items.length > 0), 'no shelf renders without terms');
assert(!shelves.find((s) => s.slug === 'llm-genai').items.some((i) => i.term === 'X1'), 'stage 2 picks only unlisted terms');

// stage 2 never hands the same unlisted term to two shelves; the later shelf falls back to stage 3
shelves = buildShelves([
  ...['A1', 'A2', 'A3', 'A4', 'A5', 'A6'].map((n) => t(n, ['llm-genai'])),
  t('Z1', ['llm-genai', 'products-platforms', 'deep-learning']),
  t('B1', ['products-platforms']),
  t('C1', ['deep-learning']),
], CATS, []);
assert.deepEqual(itemsBySlug(shelves), {
  'products-platforms': ['B1', 'Z1'],
  'llm-genai': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6'],
  'deep-learning': ['C1', 'Z1'],
});

// wide tie -> earlier canonical field
shelves = buildShelves([t('A1', ['products-platforms']), t('B1', ['llm-genai'])], CATS, []);
assert.deepEqual(shelves.map((s) => [s.slug, s.wide]), [['products-platforms', true], ['llm-genai', false]]);

// 6 items on the wide shelf, 4 elsewhere; trending order first, then A-Z by term
const many = ['Zeta', 'Alpha', 'Mu', 'Beta', 'Kappa', 'Gamma', 'Delta', 'Eta'].map((n) => t(n, ['llm-genai']));
const few = ['Omega', 'Iota', 'Nu', 'Pi', 'Rho', 'Tau'].map((n) => t(n, ['deep-learning']));
shelves = buildShelves([...many, ...few], CATS, ['mu', 'tau', 'zeta']);
const wide = shelves.find((s) => s.slug === 'llm-genai');
const narrow = shelves.find((s) => s.slug === 'deep-learning');
assert.equal(wide.wide, true);
assert.equal(wide.count, 8);
assert.deepEqual(wide.items.map((i) => i.term), ['Mu', 'Zeta', 'Alpha', 'Beta', 'Delta', 'Eta']);
assert.equal(narrow.wide, false);
assert.deepEqual(narrow.items.map((i) => i.term), ['Tau', 'Iota', 'Nu', 'Omega']);

// plain definition
assert.equal(plainDefinition('  **RAG** is retrieval-augmented **generation**. '), 'RAG is retrieval-augmented generation.');
assert.equal(plainDefinition(null), '');

// A-Z: 27 letters, '#' last (digits/other), groups sorted by term
const az = buildAzIndex([t('rag', []), t('Agent', []), t('API', []), t('3D Gaussian', []), t('Claude', []), t('ablation', [])]);
assert.equal(az.letters.length, 27);
assert.deepEqual(az.letters[26], { letter: '#', anchor: 'num', has: true });
assert.deepEqual(az.letters.filter((l) => l.has).map((l) => l.letter), ['A', 'C', 'R', '#']);
assert.deepEqual(az.groups.map((g) => [g.letter, g.anchor]), [['A', 'A'], ['C', 'C'], ['R', 'R'], ['#', 'num']]);
assert.deepEqual(az.groups[0].items.map((i) => i.term), ['ablation', 'Agent', 'API']);
assert.deepEqual(az.groups[3].items.map((i) => i.term), ['3D Gaussian']);
assert.equal(az.letters[1].has, false); // B

// first news line
assert.equal(firstNewsLine('\n   \n- "RAG를 붙였다" → 검색 결과를 섞었다는 뜻\n- second'), '"RAG를 붙였다" → 검색 결과를 섞었다는 뜻');
assert.equal(firstNewsLine('• bullet line'), 'bullet line');
assert.equal(firstNewsLine('-\n• real line'), 'real line');
assert.equal(firstNewsLine('  plain line  '), 'plain line');
assert.equal(firstNewsLine('   \n\t'), '');
assert.equal(firstNewsLine(null), '');

// display names
assert.deepEqual(termNames({ term: 'RAG', korean_name: '검색 증강 생성' }, 'ko'), { name: '검색 증강 생성', sub: 'RAG' });
assert.deepEqual(termNames({ term: 'RAG', korean_name: '검색 증강 생성' }, 'en'), { name: 'RAG', sub: '' });
assert.deepEqual(termNames({ term: 'GPU', korean_name: 'GPU' }, 'ko'), { name: 'GPU', sub: '' });
assert.deepEqual(termNames({ term: 'GPU', korean_name: null }, 'ko'), { name: 'GPU', sub: '' });

console.log('handbook-shelves.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/handbook-shelves.test.mjs`
Expected: FAIL. `handbookShelves.js` 모듈을 찾을 수 없다(ERR_MODULE_NOT_FOUND).

- [ ] **Step 3: 구현** (Write 도구로 — 정규식 백슬래시 포함)

```js
// frontend/src/lib/handbookShelves.js
// Pure helpers for the handbook index: shelves by field, A–Z index, display names, plain text. No I/O.

const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
const byTerm = (a, b) => String(a.term).localeCompare(String(b.term), 'en');

/** Definition as plain text: `**` removed, outer whitespace trimmed. */
export function plainDefinition(text) {
  return text ? String(text).replace(/\*\*/g, '').trim() : '';
}

/** First non-empty line of hero_news_context, without a leading "- " or "• " marker. */
export function firstNewsLine(text) {
  if (!text) return '';
  for (const raw of String(text).split(/\r?\n/)) {
    const line = raw.trim().replace(/^[-•](?:\s+|$)/, '').trim();
    if (line) return line;
  }
  return '';
}

/** KO: korean_name with the English term beside it (when different). EN: the term only. */
export function termNames(term, locale) {
  const korean = term.korean_name ? String(term.korean_name).trim() : '';
  if (locale === 'ko' && korean && korean !== term.term) return { name: korean, sub: term.term };
  return { name: term.term, sub: '' };
}

/**
 * @param {Array<{slug: string, term: string, categories?: string[]|null}>} terms
 * @param {string[]} categorySlugs canonical order (getHandbookCategories())
 * @param {string[]} [trendingSlugs] most viewed first
 * @returns {Array<{slug: string, count: number, wide: boolean, items: object[]}>}
 *   count = terms whose categories include the slug (same rule as the category page);
 *   items (target 6 wide / 4 other), each stage ordered trending first then A–Z by term:
 *     1. terms whose first canonical category is the slug;
 *     2. if short: other member terms not listed on any shelf yet (shelves filled in canonical order);
 *     3. if still short: member terms already listed on another shelf (duplicates).
 *   fields with count 0 are dropped; the largest count is wide (ties: earlier field).
 */
export function buildShelves(terms, categorySlugs, trendingSlugs = []) {
  const known = new Set(categorySlugs);
  const rank = new Map(trendingSlugs.map((slug, i) => [slug, i]));
  const rankOf = (t) => (rank.has(t.slug) ? rank.get(t.slug) : Number.MAX_SAFE_INTEGER);
  const order = (a, b) => rankOf(a) - rankOf(b) || byTerm(a, b);

  const shelves = categorySlugs
    .map((slug) => {
      const members = terms.filter((t) => (t.categories || []).includes(slug));
      return {
        slug,
        count: members.length,
        members,
        placed: terms.filter((t) => (t.categories || []).find((c) => known.has(c)) === slug),
      };
    })
    .filter((shelf) => shelf.count > 0);

  let wideSlug = null;
  let max = 0;
  for (const shelf of shelves) {
    if (shelf.count > max) {
      max = shelf.count;
      wideSlug = shelf.slug;
    }
  }

  // stage 1: first canonical category
  const built = shelves.map(({ slug, count, members, placed }) => {
    const wide = slug === wideSlug;
    const target = wide ? 6 : 4;
    return { slug, count, wide, target, members, items: [...placed].sort(order).slice(0, target) };
  });

  // stage 2: member terms not listed on any shelf yet
  const listed = new Set(built.flatMap((shelf) => shelf.items.map((t) => t.slug)));
  for (const shelf of built) {
    if (shelf.items.length >= shelf.target) continue;
    const extra = shelf.members
      .filter((t) => !listed.has(t.slug))
      .sort(order)
      .slice(0, shelf.target - shelf.items.length);
    for (const t of extra) listed.add(t.slug);
    shelf.items.push(...extra);
  }

  // stage 3: member terms already listed elsewhere (duplicates)
  for (const shelf of built) {
    if (shelf.items.length >= shelf.target) continue;
    const own = new Set(shelf.items.map((t) => t.slug));
    shelf.items.push(
      ...shelf.members
        .filter((t) => !own.has(t.slug))
        .sort(order)
        .slice(0, shelf.target - shelf.items.length),
    );
  }

  return built.map(({ slug, count, wide, items }) => ({ slug, count, wide, items }));
}

/** Index bucket of a term: its first letter A–Z, otherwise '#'. */
export function azLetter(term) {
  const first = String(term || '').trim().charAt(0).toUpperCase();
  return /^[A-Z]$/.test(first) ? first : '#';
}

/**
 * @returns {{letters: Array<{letter: string, anchor: string, has: boolean}>,
 *            groups: Array<{letter: string, anchor: string, items: object[]}>}}
 *   letters = A–Z + '#' (27); groups = letters that have terms, '#' last, items A–Z by term.
 *   anchor is the letter, or 'num' for '#' (ids stay plain: az-A, az-num).
 */
export function buildAzIndex(terms) {
  const buckets = new Map();
  for (const t of terms) {
    const letter = azLetter(t.term);
    if (!buckets.has(letter)) buckets.set(letter, []);
    buckets.get(letter).push(t);
  }
  const anchorOf = (letter) => (letter === '#' ? 'num' : letter);
  const keys = [...LETTERS, '#'];
  return {
    letters: keys.map((letter) => ({ letter, anchor: anchorOf(letter), has: buckets.has(letter) })),
    groups: keys
      .filter((letter) => buckets.has(letter))
      .map((letter) => ({ letter, anchor: anchorOf(letter), items: buckets.get(letter).sort(byTerm) })),
  };
}
```

- [ ] **Step 4: 통과 확인** — `node frontend/tests/handbook-shelves.test.mjs` → PASS

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/handbookShelves.js frontend/tests/handbook-shelves.test.mjs
git commit -m "feat: add pure shelf and A-Z index builders for the handbook index"
```

---

## Task 3: 용어집 첫 화면 (컴포넌트·페이지·스크립트·CSS·테스트 갱신·레일 삭제)

**Files:**
- Create: `frontend/src/components/handbook/HandbookToday.astro`, `frontend/src/components/handbook/HandbookShelves.astro`, `frontend/src/components/handbook/HandbookAzIndex.astro`
- Modify:
  - `frontend/src/pages/ko/handbook/index.astro`, `frontend/src/pages/en/handbook/index.astro`(전체 교체)
  - `frontend/src/lib/pageData/handbookPage.ts`(`termsByCategory` 제거. **CRLF/LF 혼합 → Edit 도구**)
  - `frontend/src/styles/global.css`(새 블록 추가만. 옛 CSS 삭제는 Task 4)
  - `frontend/tests/term-of-day.test.cjs`, `frontend/tests/handbook-v2.test.cjs`, `frontend/tests/handbook-library-copy.test.cjs`
- Delete (`git rm`): `frontend/src/components/newsprint/HandbookListRail.astro`, `frontend/tests/handbook-category-icons.test.cjs`
- Test: `frontend/tests/handbook-index-shelves.test.cjs`(새 파일)

- [ ] **Step 0: 사용처 확인**

Run:
```bash
git status --short -- frontend/src/pages/ko/handbook/index.astro frontend/src/pages/en/handbook/index.astro frontend/src/lib/pageData/handbookPage.ts frontend/src/styles/global.css
grep -rn "termsByCategory\|HandbookListRail" frontend/src
```
Expected: status 출력 없음. grep은 `handbookPage.ts`, 두 handbook index 페이지, `HandbookListRail.astro` 자신만 나온다. 다른 파일이 나오면 멈추고 보고한다.

- [ ] **Step 1: 실패하는 구조 테스트 작성** (Write 도구로)

```js
// frontend/tests/handbook-index-shelves.test.cjs
// Handbook index B+A: term of the day, shelves by field, A–Z index; search/category mode in the inline script.
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

// components
const today = read('components/handbook/HandbookToday.astro');
for (const s of ['오늘의 용어', 'Term of the day', '풀이 읽기 →', 'Read the explainer →', '뉴스에서는 이렇게 쓰여요', 'How the news uses it']) {
  assert(today.includes(s), `today copy: ${s}`);
}
assert(today.includes('firstNewsLine(newsContext)') && today.includes('{newsLine && ('), 'plate only when a news line exists');
assert(today.includes('issueLabel(locale, issueNumber('), 'label carries the issue number');
assert(today.includes('plainDefinition(term.definition)'), 'definition is plain text');

const shelvesC = read('components/handbook/HandbookShelves.astro');
for (const s of ['분야별 서가', 'Shelves by field', '개 모두 보기 →', 'All ${n} →']) {
  assert(shelvesC.includes(s), `shelves copy: ${s}`);
}
assert(shelvesC.includes('/${locale}/handbook/category/${shelf.slug}/'), 'shelf links to the category page');
assert(shelvesC.includes('handbook-shelf--wide'), 'wide shelf modifier');
assert(shelvesC.includes('getHandbookCategoryLabel(locale, shelf.slug)'), 'shelf name from handbookCategories');

const az = read('components/handbook/HandbookAzIndex.astro');
for (const s of ['A–Z 색인', 'A–Z index']) assert(az.includes(s), `index copy: ${s}`);
assert(az.includes('id={`az-${group.anchor}`}') && az.includes('href={`#az-${l.anchor}`}'), 'letter bar links to group anchors (id="az-…")');
assert(az.includes('<span aria-hidden="true">{l.letter}</span>'), 'letters without terms are muted spans');

// pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/handbook/index.astro`);
  for (const c of ['<HandbookToday ', '<HandbookShelves ', '<HandbookAzIndex ']) {
    assert(page.includes(c), `${locale}: uses ${c.trim()}`);
  }
  assert(/<NewsprintShell[\s\S]*?rail=\{false\}/.test(page), `${locale}: no right rail`);
  assert(!/HandbookListRail|handbook-trending|handbook-showcase|handbook-filter-btn|PREVIEW_COUNT|termsByCategory|handbookTags/.test(page), `${locale}: old trending/showcase/filter/rail removed`);
  assert(page.includes('buildShelves(indexTerms, categories, trendingSlugs)') && page.includes('buildAzIndex(indexTerms)'), `${locale}: shelves and index from lib/handbookShelves.js`);
  assert(page.includes('termOfDay.total || allTerms.length'), `${locale}: term count prefers the exact count`);
  assert(page.includes('<strong>{shelves.length}</strong>'), `${locale}: category count = shelves with terms`);

  // active filter link: hidden, labelled, right before the result count
  const linkAt = page.indexOf('<a id="handbook-active-filter"');
  assert(linkAt > 0 && linkAt < page.indexOf('id="handbook-result-count"'), `${locale}: active-filter link sits right before the result count`);
  assert(/<a id="handbook-active-filter"[^>]*\shidden\s[^>]*data-labels=\{JSON\.stringify\(categoryLabels\)\}/.test(page), `${locale}: link is hidden and carries category labels`);

  // inline script
  assert(page.includes('dataset.handbookIndexReady'), `${locale}: double-binding guard`);
  assert(page.includes("document.addEventListener('astro:page-load', initHandbookIndex);") && /\n  initHandbookIndex\(\);\n/.test(page), `${locale}: page-load + immediate init`);
  assert(page.includes("params.get('category')") && page.includes('Object.prototype.hasOwnProperty.call(labels, slug)'), `${locale}: only canonical ?category= values apply`);
  assert(page.includes("querySelectorAll<HTMLElement>('.handbook-today, .handbook-shelves, .handbook-az')"), `${locale}: browse sections toggle with search mode`);
  assert(page.includes("new Event('content-status:refresh')"), `${locale}: cards hydrate after render`);
  assert(!/IntersectionObserver|sentinel|BATCH_SIZE/.test(page), `${locale}: no infinite scroll`);
}
assert(read('pages/ko/handbook/index.astro').includes("' · 전체 보기로'"), 'ko back-to-all copy');
assert(read('pages/en/handbook/index.astro').includes("' · Back to all'"), 'en back-to-all copy');
assert(!fs.existsSync(path.join(src, 'components/newsprint/HandbookListRail.astro')), 'list rail deleted');
assert(!read('lib/pageData/handbookPage.ts').includes('termsByCategory'), 'unused termsByCategory removed');

// CSS
assert(/grid-template-columns:\s*minmax\(0, 1\.2fr\) minmax\(0, 1fr\)/.test(rule('.handbook-today')), 'today: 1.2fr : 1fr');
assert(rule('.handbook-today-plate').includes('background: var(--color-text-primary)'), 'ink plate in light themes');
assert(rule('[data-theme="dark"] .handbook-today-plate').includes('var(--color-bg-tertiary)'), 'dark plate uses bg-tertiary');
assert(/grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/.test(rule('.handbook-shelves-grid')), 'shelves: 3 columns');
assert(/grid-row:\s*span 2/.test(rule('.handbook-shelf--wide')), 'wide shelf spans 2 rows');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.handbook-shelf')), 'shelf ink rule');
assert(/column-count:\s*3/.test(rule('.handbook-az-dict')) && /column-rule:/.test(rule('.handbook-az-dict')), 'dictionary: 3 ruled columns');
assert(rule('.handbook-az-group').includes('scroll-margin-top: calc(var(--header-h, 4rem) + 4.5rem)'), 'anchors clear the sticky header + search');
assert(/display:\s*none/.test(rule('.handbook-active-filter[hidden]')), 'hidden active-filter link stays hidden');
const mobileAt = css.indexOf('/* Handbook index: mobile */');
assert(mobileAt > 0, 'handbook index mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.handbook-today\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: today one column');
assert(/\.handbook-shelves-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: shelves one column');
assert(/\.handbook-shelf--wide\s*\{[^}]*grid-row:\s*auto/.test(mobile), 'mobile: wide shelf one cell');
assert(/\.handbook-az-bar\s*\{[^}]*overflow-x:\s*auto/.test(mobile), 'mobile: letter bar scrolls sideways');
assert(/\.handbook-az-dict\s*\{[^}]*column-count:\s*1/.test(mobile), 'mobile: dictionary one column');

console.log('handbook-index-shelves.test.cjs passed');
```

`term-of-day.test.cjs`에 handbook 단언을 추가한다(Edit 도구). `console.log('term-of-day.test.cjs passed');` **바로 위**에 넣는다.

```js
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/handbook/index.astro`);
  assert(page.includes(`fetchTermOfDay(supabase, locale, new Date(), 'hero_news_context_${locale}')`), `${locale} handbook: same term of the day as the home, plus the news line column`);
}

```

- [ ] **Step 2: 실패 확인**

Run:
```bash
node frontend/tests/handbook-index-shelves.test.cjs
node frontend/tests/term-of-day.test.cjs
```
Expected: 둘 다 FAIL. 앞은 `HandbookToday.astro` ENOENT, 뒤는 "ko handbook: same term of the day…".

- [ ] **Step 3: `HandbookToday.astro` 작성** (Write 도구로)

```astro
---
// frontend/src/components/handbook/HandbookToday.astro
// Handbook index: term of the day (same pick as the home front page) + an ink plate with the
// first "how the news uses it" line. Without a line the plate is omitted and the text takes the full width.
import type { TermOfDay } from '../../lib/pageData/termOfDay';
import { firstNewsLine, plainDefinition, termNames } from '../../lib/handbookShelves.js';
import { issueLabel, issueNumber } from '../../lib/issue.js';

interface Props {
  locale: 'en' | 'ko';
  term: TermOfDay;
  newsContext?: string | null;
}

const { locale, term, newsContext = null } = Astro.props;
const isKo = locale === 'ko';
const { name, sub } = termNames(term, locale);
const definition = plainDefinition(term.definition);
const newsLine = firstNewsLine(newsContext);
const issue = issueLabel(locale, issueNumber(new Date()));
const copy = isKo
  ? { label: '오늘의 용어', read: '풀이 읽기 →', plate: '뉴스에서는 이렇게 쓰여요' }
  : { label: 'Term of the day', read: 'Read the explainer →', plate: 'How the news uses it' };
---

<section class={`handbook-today${newsLine ? '' : ' handbook-today--solo'}`} aria-label={copy.label}>
  <div class="handbook-today-main">
    <p class="handbook-today-label">{copy.label} · {issue}</p>
    <h2 class="handbook-today-name">{name}</h2>
    {sub && <p class="handbook-today-sub">{sub}</p>}
    {definition && <p class="handbook-today-def">{definition}</p>}
    <a class="handbook-today-link" href={`/${locale}/handbook/${term.slug}/`}>{copy.read}</a>
  </div>
  {newsLine && (
    <div class="handbook-today-plate">
      <p class="handbook-today-plate-label">{copy.plate}</p>
      <p class="handbook-today-plate-text">{newsLine}</p>
    </div>
  )}
</section>
```

- [ ] **Step 4: `HandbookShelves.astro` 작성** (Write 도구로)

```astro
---
// frontend/src/components/handbook/HandbookShelves.astro
// Handbook index: one shelf per field (canonical order, empty fields hidden).
// count = membership (matches the category page); items = terms whose first canonical field is this one.
import { getHandbookCategoryLabel } from '../../lib/handbookCategories';
import { plainDefinition, termNames } from '../../lib/handbookShelves.js';

interface ShelfTerm {
  slug: string;
  term: string;
  korean_name?: string | null;
  definition?: string | null;
}

interface Shelf {
  slug: string;
  count: number;
  wide: boolean;
  items: ShelfTerm[];
}

interface Props {
  locale: 'en' | 'ko';
  shelves: Shelf[];
}

const { locale, shelves } = Astro.props;
const isKo = locale === 'ko';
const heading = isKo ? '분야별 서가' : 'Shelves by field';
const moreLabel = (n: number) => (isKo ? `${n}개 모두 보기 →` : `All ${n} →`);
---

{shelves.length > 0 && (
  <section class="handbook-shelves" aria-labelledby="handbook-shelves-title">
    <h2 class="handbook-index-head" id="handbook-shelves-title">{heading}</h2>
    <div class="handbook-shelves-grid">
      {shelves.map((shelf) => {
        const href = `/${locale}/handbook/category/${shelf.slug}/`;
        return (
          <article class={`handbook-shelf${shelf.wide ? ' handbook-shelf--wide' : ''}`}>
            <div class="handbook-shelf-head">
              <h3 class="handbook-shelf-name"><a href={href}>{getHandbookCategoryLabel(locale, shelf.slug)}</a></h3>
              <span class="handbook-shelf-count">{shelf.count}</span>
            </div>
            {shelf.items.length > 0 && (
              <ul class="handbook-shelf-list">
                {shelf.items.map((item) => {
                  const { name } = termNames(item, locale);
                  const def = shelf.wide ? plainDefinition(item.definition) : '';
                  return (
                    <li>
                      <a href={`/${locale}/handbook/${item.slug}/`}>
                        {name}
                        {def && <span class="handbook-shelf-def">{def}</span>}
                      </a>
                    </li>
                  );
                })}
              </ul>
            )}
            <a class="handbook-shelf-more" href={href}>{moreLabel(shelf.count)}</a>
          </article>
        );
      })}
    </div>
  </section>
)}
```

- [ ] **Step 5: `HandbookAzIndex.astro` 작성** (Write 도구로. "A–Z"의 대시는 en dash `–`(U+2013)다)

```astro
---
// frontend/src/components/handbook/HandbookAzIndex.astro
// Handbook index: A–Z letter bar + dictionary columns, grouped by the English term's first letter
// ('#' = digits/other, anchor az-num). Letters without terms are muted, non-link spans.
import { termNames } from '../../lib/handbookShelves.js';

interface AzTerm {
  slug: string;
  term: string;
  korean_name?: string | null;
}

interface Props {
  locale: 'en' | 'ko';
  index: {
    letters: { letter: string; anchor: string; has: boolean }[];
    groups: { letter: string; anchor: string; items: AzTerm[] }[];
  };
}

const { locale, index } = Astro.props;
const isKo = locale === 'ko';
const heading = isKo ? 'A–Z 색인' : 'A–Z index';
---

{index.groups.length > 0 && (
  <section class="handbook-az" aria-labelledby="handbook-az-title">
    <h2 class="handbook-index-head" id="handbook-az-title">{heading}</h2>
    <nav class="handbook-az-bar" aria-label={heading}>
      {index.letters.map((l) => (
        l.has
          ? <a href={`#az-${l.anchor}`}>{l.letter}</a>
          : <span aria-hidden="true">{l.letter}</span>
      ))}
    </nav>
    <div class="handbook-az-dict">
      {index.groups.map((group) => (
        <div class="handbook-az-group" id={`az-${group.anchor}`}>
          <h3 class="handbook-az-letter">{group.letter}</h3>
          <ul class="handbook-az-list">
            {group.items.map((item) => {
              const { name, sub } = termNames(item, locale);
              return (
                <li>
                  <a href={`/${locale}/handbook/${item.slug}/`}>
                    <span class="handbook-az-name">{name}</span>
                    {sub && <span class="handbook-az-sub">{sub}</span>}
                  </a>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  </section>
)}
```

- [ ] **Step 6: `handbookPage.ts`에서 `termsByCategory` 제거** (Edit 도구로만. CRLF/LF 혼합 파일)
  - `import { getHandbookCategories } from '../handbookCategories';` 줄을 지운다(이 파일에서 더 쓰지 않는다).
  - `HandbookPageData` 인터페이스에서 `  termsByCategory: Record<string, HandbookTermCard[]>;` 줄을 지운다.
  - `return { allTerms: [], termsByCategory: {}, totalTerms: 0, error: null };` → `return { allTerms: [], totalTerms: 0, error: null };`
  - `return { allTerms: [], termsByCategory: {}, totalTerms: 0, error: error.message };` → `return { allTerms: [], totalTerms: 0, error: error.message };`
  - `  // Group by category in the canonical order from handbookCategories` 주석부터 `for (const term of allTerms) { ... }` 블록 끝까지 지운다.
  - `return { allTerms, termsByCategory, totalTerms: allTerms.length, error: null };` → `return { allTerms, totalTerms: allTerms.length, error: null };`
  - 쿼리(`getTermCardColumns`, `.eq('status', 'published')`, `.order('term')`, `.limit(500)`)와 `getHandbookCategoryPageData`는 건드리지 않는다.

Run: `grep -n "termsByCategory\|getHandbookCategories" frontend/src/lib/pageData/handbookPage.ts` → 결과 없음.

- [ ] **Step 7: `pages/ko/handbook/index.astro` 전체 교체** (Read 후 **Write 도구로**. `'\u2026'` 백슬래시가 있다)

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { getHandbookCategoryLabel, getHandbookCategories } from '../../../lib/handbookCategories';
import { localField } from '../../../lib/handbookUtils';
import NewsprintShell from '../../../components/newsprint/NewsprintShell.astro';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';
import HandbookToday from '../../../components/handbook/HandbookToday.astro';
import HandbookShelves from '../../../components/handbook/HandbookShelves.astro';
import HandbookAzIndex from '../../../components/handbook/HandbookAzIndex.astro';
import { getSiteContents, parseJsonArray } from '../../../lib/siteContent';
import { getHandbookPageData } from '../../../lib/pageData/handbookPage';
import { fetchTermOfDay } from '../../../lib/pageData/termOfDay';
import { buildShelves, buildAzIndex } from '../../../lib/handbookShelves.js';
import { supabase } from '../../../lib/supabase';

const locale = 'ko';

const { allTerms, error: fetchError } = await getHandbookPageData(locale);
if (fetchError) Astro.response.status = 503;

// Term of the day: the home's query (count + 1 row). Skipped on error, never a 503.
const termOfDay = await fetchTermOfDay(supabase, locale, new Date(), 'hero_news_context_ko');
const todayTerm = termOfDay.term;
const todayNews = typeof todayTerm?.hero_news_context_ko === 'string' ? todayTerm.hero_news_context_ko : null;

// Most viewed 10 (shelf ordering only; latest published when nothing has views yet)
let popularTerms: { slug: string; view_count?: number | null }[] = [];
if (supabase) {
  const { data } = await supabase
    .from('handbook_terms')
    .select('slug, view_count')
    .eq('status', 'published')
    .order('view_count', { ascending: false })
    .limit(10);
  popularTerms = data ?? [];
}
if (popularTerms.length === 0 || popularTerms.every((pt) => !pt.view_count)) {
  if (supabase) {
    const { data } = await supabase
      .from('handbook_terms')
      .select('slug')
      .eq('status', 'published')
      .order('published_at', { ascending: false })
      .limit(10);
    popularTerms = data ?? [];
  }
}
const trendingSlugs = popularTerms.map((pt) => pt.slug);

const categories = getHandbookCategories();
const indexTerms = allTerms.map((term) => ({
  slug: term.slug,
  term: term.term,
  korean_name: term.korean_name,
  categories: term.categories,
  definition: localField(term, 'definition', locale),
}));
const shelves = buildShelves(indexTerms, categories, trendingSlugs);
const azIndex = buildAzIndex(indexTerms);
const termCount = termOfDay.total || allTerms.length;
const categoryLabels = Object.fromEntries(categories.map((cat) => [cat, getHandbookCategoryLabel(locale, cat)]));

// Site content from DB (fallback to hardcoded values)
const sc = await getSiteContents(
  ['handbook_intro', 'handbook_masthead', 'handbook_edition_label', 'handbook_subkicker'],
  'ko',
);
const hbSubkicker = parseJsonArray<string>(sc.handbook_subkicker, ['용어 사전', '레퍼런스', '학습']);
const intro = sc.handbook_intro || 'AI, 백엔드, 프론트엔드, 보안, 운영 전반의 기술 용어를 한 곳에서 읽기 쉽게 정리합니다.';
---

<MainLayout title={t[locale]['handbook.title']} description="AI·IT 용어를 쉬운 설명과 실제 예시로 정리한 용어집. 기초/심화 레벨로 나뉘어 있고, 매일 AI 뉴스와 연결됩니다." locale={locale} slug="handbook/">
  <NewsprintShell
    locale={locale}
    masthead={sc.handbook_masthead || 'AI 용어집'}
    editionLabel={sc.handbook_edition_label || 'CS · AI · Infra'}
    subkicker={hbSubkicker}
    rail={false}
  >
    <p class="handbook-intro">{intro}</p>
    <p class="handbook-hero-stats">
      <span><strong>{termCount}+</strong> 용어</span>
      <span class="handbook-hero-stats-sep" aria-hidden="true">&middot;</span>
      <span><strong>{shelves.length}</strong> 카테고리</span>
    </p>

    <div class="handbook-search-sticky">
      <input
        type="text"
        id="handbook-search"
        aria-label={t[locale]['handbook.search']}
        placeholder={t[locale]['handbook.search']}
        data-placeholder-hints={JSON.stringify([t[locale]['handbook.search'], 'RAG', 'MCP', '임베딩'])}
        class="handbook-search-input"
      />
    </div>

    <a id="handbook-active-filter" class="handbook-active-filter" href={`/${locale}/handbook/`} hidden data-labels={JSON.stringify(categoryLabels)}></a>
    <div id="handbook-result-count" class="handbook-result-count" aria-live="polite" style="display: none;"></div>

    {todayTerm && <HandbookToday locale={locale} term={todayTerm} newsContext={todayNews} />}
    {allTerms.length > 0 && (
      <>
        <HandbookShelves locale={locale} shelves={shelves} />
        <HandbookAzIndex locale={locale} index={azIndex} />
      </>
    )}

    {fetchError ? (
      <NewsprintNotice
        variant="error"
        message={t[locale]['handbook.error']}
        linkHref={`/${locale}/handbook/`}
        linkLabel={t[locale]['handbook.back']}
      />
    ) : allTerms.length === 0 ? (
      <NewsprintNotice variant="empty" message={t[locale]['handbook.empty']} />
    ) : (
      <>
        <script type="application/json" id="handbook-terms-data" set:html={JSON.stringify(allTerms.map(t => {
          const def = localField(t, 'definition', locale) || '';
          return {
            s: t.slug, t: t.term, k: t.korean_name || '', c: t.categories || [],
            cl: (t.categories || []).map((cat: string) => getHandbookCategoryLabel(locale, cat) || cat),
            d: def.length > 120 ? def.slice(0, 120) + '\u2026' : def,
            id: t.id,
          };
        }))} />
        <div id="search-results" style="display: none;"></div>
      </>
    )}

    <div id="handbook-no-results" style="display: none;">
      <NewsprintNotice variant="empty" message={t[locale]['handbook.searchNoResults']} />
    </div>
  </NewsprintShell>
</MainLayout>

<script>
  import '../../../scripts/bookmark';
</script>

<script>
  import '../../../scripts/handbookSearchHints';
</script>

<script>
  type TermEntry = { s: string; t: string; k: string; c: string[]; cl: string[]; d: string; id: string };

  // Default mode (no query, no canonical ?category=): term of the day + shelves + A–Z index.
  // Search mode: those sections hide and #search-results shows the filtered cards.
  function initHandbookIndex(): void {
    const search = document.getElementById('handbook-search') as HTMLInputElement | null;
    const searchResults = document.getElementById('search-results');
    if (!search || !searchResults || search.dataset.handbookIndexReady === 'true') return;
    search.dataset.handbookIndexReady = 'true';

    const noResults = document.getElementById('handbook-no-results');
    const countEl = document.getElementById('handbook-result-count');
    const activeFilterEl = document.getElementById('handbook-active-filter') as HTMLAnchorElement | null;
    const termsDataEl = document.getElementById('handbook-terms-data');
    const browseSections = Array.from(document.querySelectorAll<HTMLElement>('.handbook-today, .handbook-shelves, .handbook-az'));

    // ?category= applies only to canonical slugs (data-labels keys come from getHandbookCategories())
    const labels: Record<string, string> = JSON.parse(activeFilterEl?.dataset.labels || '{}');
    const isKnownCategory = (slug: string | null): slug is string =>
      !!slug && Object.prototype.hasOwnProperty.call(labels, slug);
    const params = new URLSearchParams(window.location.search);
    const urlCategory = params.get('category');
    const activeCategory = isKnownCategory(urlCategory) ? urlCategory : '';

    let cardsBuilt = false;

    function ensureCards(): void {
      if (cardsBuilt) return;
      cardsBuilt = true;
      if (!termsDataEl || !searchResults) return;
      const termsData: TermEntry[] = JSON.parse(termsDataEl.textContent || '[]');
      termsData.sort((a, b) => a.t.localeCompare(b.t, undefined, { sensitivity: 'base' }));
      const locale = document.documentElement.lang || 'ko';
      const frag = document.createDocumentFragment();
      for (const t of termsData) {
        const a = document.createElement('a');
        a.href = `/${locale}/handbook/${t.s}/`;
        a.className = 'handbook-card';
        a.dataset.categories = JSON.stringify(t.c);
        a.dataset.term = t.t;
        a.dataset.korean = t.k;
        a.dataset.def = t.d;
        let html = '<div class="handbook-card-meta">';
        for (let i = 0; i < t.c.length; i++) {
          html += `<span class="handbook-cat-pill">${t.cl[i]}</span>`;
        }
        html += '</div><div class="handbook-card-title-row"><div class="handbook-card-title">' +
          t.t + '</div><button class="newsprint-bookmark-icon' +
          '" data-item-id="' + t.id + '" data-item-type="term" data-bookmarked="false' +
          '" aria-label="북마크 추가">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
          '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg></button></div>';
        if (t.k) html += '<div class="handbook-card-korean">' + t.k + '</div>';
        if (t.d) html += '<div class="handbook-card-def">' + t.d.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') + '</div>';
        a.innerHTML = html;
        frag.appendChild(a);
      }
      searchResults.appendChild(frag);
      window.dispatchEvent(new Event('content-status:refresh'));
    }

    function setBrowseVisible(visible: boolean): void {
      browseSections.forEach((el) => { el.style.display = visible ? '' : 'none'; });
    }

    function enterDefaultMode(): void {
      searchResults!.style.display = 'none';
      if (noResults) noResults.style.display = 'none';
      if (countEl) { countEl.textContent = ''; countEl.style.display = 'none'; }
      if (activeFilterEl) activeFilterEl.hidden = true;
      setBrowseVisible(true);
    }

    function debounce(fn: () => void, ms: number): () => void {
      let timer: ReturnType<typeof setTimeout>;
      return () => { clearTimeout(timer); timer = setTimeout(fn, ms); };
    }

    function filter(): void {
      const query = search!.value.toLowerCase().trim();

      if (!query && !activeCategory) {
        enterDefaultMode();
        return;
      }

      ensureCards();
      setBrowseVisible(false);
      searchResults!.style.display = 'block';
      if (activeFilterEl) {
        activeFilterEl.hidden = !activeCategory;
        if (activeCategory) activeFilterEl.textContent = labels[activeCategory] + ' · 전체 보기로';
      }

      const cards = searchResults!.querySelectorAll<HTMLElement>('.handbook-card');
      let visible = 0;

      cards.forEach((card) => {
        const cats: string[] = (card as any).__cats ??= JSON.parse(card.dataset.categories || '[]');
        const term = (card.dataset.term || '').toLowerCase();
        const korean = (card.dataset.korean || '').toLowerCase();
        const def = (card.dataset.def || '').toLowerCase();

        const matchesCategory = !activeCategory || cats.includes(activeCategory);
        const matchesSearch = !query || term.includes(query) || korean.includes(query) || def.includes(query);

        const show = matchesCategory && matchesSearch;
        card.style.display = show ? 'block' : 'none';
        if (show) visible++;
      });

      if (noResults) noResults.style.display = visible === 0 ? 'block' : 'none';
      if (countEl) {
        countEl.textContent = `${visible} / ${cards.length}`;
        countEl.style.display = 'block';
      }
    }

    search.addEventListener('input', debounce(filter, 150));

    const urlQuery = params.get('q');
    if (urlQuery) search.value = urlQuery;
    if (activeCategory || urlQuery) filter();
  }

  document.addEventListener('astro:page-load', initHandbookIndex);
  initHandbookIndex();
</script>
```

- [ ] **Step 8: `pages/en/handbook/index.astro` 전체 교체** — Step 7의 KO 파일을 그대로 쓰되 **아래 문자열만** 바꾼다(Read 후 Write 도구로). 그 밖의 줄은 한 글자도 다르지 않아야 한다.

| KO (Step 7) | EN |
|---|---|
| `const locale = 'ko';` | `const locale = 'en';` |
| `fetchTermOfDay(supabase, locale, new Date(), 'hero_news_context_ko')` | `fetchTermOfDay(supabase, locale, new Date(), 'hero_news_context_en')` |
| `typeof todayTerm?.hero_news_context_ko === 'string' ? todayTerm.hero_news_context_ko : null` | `typeof todayTerm?.hero_news_context_en === 'string' ? todayTerm.hero_news_context_en : null` |
| getSiteContents 두 번째 인자 `'ko',` | `'en',` |
| `['용어 사전', '레퍼런스', '학습']` | `['Glossary', 'Reference', 'Learn']` |
| `sc.handbook_intro \|\| 'AI, 백엔드, 프론트엔드, 보안, 운영 전반의 기술 용어를 한 곳에서 읽기 쉽게 정리합니다.'` | `sc.handbook_intro \|\| 'A concise reference of technical terms across AI, backend, frontend, security, and operations.'` |
| MainLayout `description="AI·IT 용어를 쉬운 설명과 실제 예시로 정리한 용어집. 기초/심화 레벨로 나뉘어 있고, 매일 AI 뉴스와 연결됩니다."` | `description="An AI & IT glossary with terms explained in plain language. Basic and advanced levels, real-world examples, and linked to daily AI news."` |
| `sc.handbook_masthead \|\| 'AI 용어집'` | `sc.handbook_masthead \|\| 'AI Glossary'` |
| `<strong>{termCount}+</strong> 용어` | `<strong>{termCount}+</strong> terms` |
| `<strong>{shelves.length}</strong> 카테고리` | `<strong>{shelves.length}</strong> categories` |
| hints `'RAG', 'MCP', '임베딩'` | `'RAG', 'MCP', 'Embedding'` |
| `document.documentElement.lang \|\| 'ko'` | `document.documentElement.lang \|\| 'en'` |
| `'" aria-label="북마크 추가">'` | `'" aria-label="Add bookmark">'` |
| `labels[activeCategory] + ' · 전체 보기로'` | `labels[activeCategory] + ' · Back to all'` |

(표의 `\|\|`는 마크다운 표 이스케이프다. 실제 코드는 `||`다.)

Run: `diff frontend/src/pages/ko/handbook/index.astro frontend/src/pages/en/handbook/index.astro | grep -c '^<'` → **14**(위 표의 행 수). 다르면 표와 대조해 고친다.

- [ ] **Step 9: CSS 추가** (Edit 도구로)
  - 위치: `global.css`의 `/* Handbook "분야별로 보기": dotted list (products keep the card showcase) */` 주석 **바로 위**(`.handbook-hero-stats-sep { ... }` 블록 다음). 이 주석과 그 아래 `#handbook-showcase` 규칙은 Task 4에서 지운다.
  - 내용은 아래 전부다.

```css
/* Handbook index: intro, term of the day, shelves by field, A–Z index */
.handbook-intro {
  max-width: 640px;
  margin: 0 auto 0.25rem;
  text-align: center;
  font-size: 0.92rem;
  line-height: 1.65;
  color: var(--color-text-muted);
}

.handbook-intro + .handbook-hero-stats {
  justify-content: center;
}

.handbook-active-filter {
  display: inline-block;
  margin-bottom: 0.5rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
}

.handbook-active-filter:hover {
  text-decoration: underline;
}

.handbook-active-filter[hidden] {
  display: none;
}

.handbook-index-head {
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  padding-bottom: 0.6rem;
  margin-bottom: 1.1rem;
  border-bottom: 1px solid var(--color-text-primary);
}

/* Term of the day: text | ink plate */
.handbook-today {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 2rem;
  align-items: stretch;
  padding: 1.75rem 0;
  border-bottom: 1px solid var(--color-border);
}

.handbook-today--solo {
  grid-template-columns: minmax(0, 1fr);
}

.handbook-today-label {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-accent);
}

.handbook-today-label::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.handbook-today-name {
  font-family: var(--font-heading);
  font-size: clamp(2rem, 1.5rem + 1.5vw, 2.5rem);
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1.12;
  margin-top: 0.6rem;
  overflow-wrap: anywhere;
}

.handbook-today-sub {
  font-family: var(--font-masthead);
  font-size: 1.05rem;
  color: var(--color-text-muted);
  margin-top: 0.2rem;
}

.handbook-today-def {
  font-size: 0.95rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
  margin: 0.8rem 0 0.7rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.handbook-today-link {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
}

.handbook-today-link:hover {
  text-decoration: underline;
}

/* Same rules as the home keyword plate: ink in light themes, bg-tertiary in dark */
.handbook-today-plate {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-height: 170px;
  padding: 2.4rem 1.25rem 1.1rem;
  overflow: hidden;
  border-radius: 2px;
  background: var(--color-text-primary);
  color: var(--color-bg-primary);
}

.handbook-today-plate::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, currentColor 1.2px, transparent 1.6px);
  background-size: 9px 9px;
  opacity: 0.22;
  -webkit-mask-image: linear-gradient(115deg, transparent 30%, #000 85%);
  mask-image: linear-gradient(115deg, transparent 30%, #000 85%);
}

[data-theme="dark"] .handbook-today-plate {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.handbook-today-plate-label {
  position: absolute;
  top: 0.85rem;
  left: 1.25rem;
  font-size: 0.72rem;
  opacity: 0.75;
}

.handbook-today-plate-text {
  position: relative;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 1.02rem;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Shelves by field: 3 columns, the largest field spans 2 rows */
.handbook-shelves {
  padding: 1.75rem 0 0.5rem;
}

.handbook-shelves-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-auto-flow: row dense;
  gap: 1.75rem 2rem;
}

.handbook-shelf {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding-top: 0.75rem;
  border-top: 2px solid var(--color-text-primary);
}

.handbook-shelf--wide {
  grid-row: span 2;
}

.handbook-shelf-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
}

.handbook-shelf-name {
  font-family: var(--font-heading);
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.3;
}

.handbook-shelf-name a {
  color: var(--color-text-primary);
  text-decoration: none;
}

.handbook-shelf-name a:hover {
  color: var(--color-accent);
}

.handbook-shelf-count {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 1.9rem;
  font-weight: 500;
  line-height: 1;
  color: var(--color-accent);
}

.handbook-shelf-list {
  list-style: none;
  margin: 0.6rem 0 0;
  padding: 0;
}

.handbook-shelf-list li {
  border-bottom: 1px dotted var(--color-border);
}

.handbook-shelf-list a {
  display: block;
  padding: 0.5rem 0;
  font-family: var(--font-heading);
  font-size: 0.92rem;
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-text-primary);
  text-decoration: none;
}

.handbook-shelf-list a:hover {
  color: var(--color-accent);
}

.handbook-shelf-def {
  display: block;
  margin-top: 0.15rem;
  font-family: var(--font-body);
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.handbook-shelf-more {
  margin-top: auto;
  padding-top: 0.7rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
}

.handbook-shelf-more:hover {
  text-decoration: underline;
}

/* A–Z index: letter bar + ruled dictionary columns */
.handbook-az {
  padding: 2rem 0 1rem;
}

.handbook-az-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.1rem;
  margin-bottom: 1.25rem;
}

.handbook-az-bar a,
.handbook-az-bar span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.9rem;
  height: 1.9rem;
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 1rem;
  font-weight: 500;
}

.handbook-az-bar a {
  color: var(--color-text-primary);
  text-decoration: none;
  border-bottom: 1px solid transparent;
}

.handbook-az-bar a:hover {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

.handbook-az-bar span {
  color: var(--color-text-muted);
}

.handbook-az-dict {
  column-count: 3;
  column-gap: 2.25rem;
  column-rule: 1px solid var(--color-border);
}

.handbook-az-group {
  margin-bottom: 1.25rem;
  scroll-margin-top: calc(var(--header-h, 4rem) + 4.5rem);
}

.handbook-az-letter {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: 1.6rem;
  font-weight: 500;
  line-height: 1;
  color: var(--color-accent);
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--color-text-primary);
  break-after: avoid;
}

.handbook-az-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.handbook-az-list li {
  break-inside: avoid;
  border-bottom: 1px dotted var(--color-border);
}

.handbook-az-list a {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.42rem 0;
  color: var(--color-text-primary);
  text-decoration: none;
}

.handbook-az-list a:hover .handbook-az-name {
  color: var(--color-accent);
}

.handbook-az-name {
  min-width: 0;
  font-family: var(--font-heading);
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.handbook-az-sub {
  min-width: 0;
  max-width: 50%;
  font-family: var(--font-masthead);
  font-size: 0.82rem;
  color: var(--color-text-muted);
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 1023px) {
  .handbook-shelves-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .handbook-az-dict {
    column-count: 2;
  }
}

/* Handbook index: mobile */
@media (max-width: 767px) {
  .handbook-today {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.25rem;
    padding: 1.25rem 0;
  }

  .handbook-today-plate {
    min-height: 120px;
  }

  .handbook-shelves-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.5rem;
  }

  .handbook-shelf--wide {
    grid-row: auto;
  }

  .handbook-az-bar {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
  }

  .handbook-az-bar::-webkit-scrollbar {
    display: none;
  }

  .handbook-az-bar a,
  .handbook-az-bar span {
    flex-shrink: 0;
  }

  .handbook-az-dict {
    column-count: 1;
    column-rule: none;
  }
}
```

- [ ] **Step 10: `handbook-v2.test.cjs` 수정** (Edit 도구로. `'\n}\n'` 백슬래시가 있다)
  - **지울 줄**: `assert(rule('.handbook-filter-btn[aria-pressed="true"]::after').includes('var(--color-accent)'), 'active filter marked by an accent dot');`
  - **바꿀 줄 1**: 다음 두 줄
    ```js
    assert(rules('.handbook-trending').length === 1, 'duplicate .handbook-trending block removed');
    assert(/border-bottom:\s*1px dotted/.test(rule('.handbook-trending-list li')), 'trending is a dotted numbered list');
    ```
    →
    ```js
    assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.handbook-shelf')), 'shelf opens with a 2px ink rule');
    assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.handbook-shelf-list li')), 'shelf terms are a dotted list');
    ```
  - **바꿀 줄 2**: `assert(css.includes('#handbook-showcase .product-category-showcase-card {'), 'showcase override is scoped to the handbook');`
    →
    ```js
    assert(/column-count:\s*3/.test(rule('.handbook-az-dict')), 'A–Z dictionary in 3 columns');
    ```
  - **바꿀 줄 3**: `assert(/flex-wrap:\s*nowrap/.test(rule('.handbook-filter-row')), 'filter row stays on one scrolling line');`
    →
    ```js
    const hbMobileAt = css.indexOf('/* Handbook index: mobile */');
    const hbMobile = css.slice(hbMobileAt, css.indexOf('\n}\n', hbMobileAt));
    assert(hbMobileAt > 0 && /\.handbook-az-bar\s*\{[^}]*overflow-x:\s*auto/.test(hbMobile), 'A–Z letter bar scrolls sideways on mobile');
    assert(/\.handbook-az-dict\s*\{[^}]*column-count:\s*1/.test(hbMobile), 'A–Z dictionary is one column on mobile');
    ```
  - 그 밖의 `.handbook-card*`·`.handbook-cat-pill`·상세 단언은 그대로 둔다(카드는 검색 결과와 분야 페이지에서 계속 쓴다).

- [ ] **Step 11: `handbook-library-copy.test.cjs` 수정** (Edit 도구로)
  - `const handbookRail = read('src/components/newsprint/HandbookListRail.astro');`부터 `'Handbook rail heading must say 용어집 소개 in Korean',\n);`까지(단언 2개 포함)를 다음으로 바꾼다.
    ```js
    const koIndex = read('src/pages/ko/handbook/index.astro');
    const enIndex = read('src/pages/en/handbook/index.astro');
    assert(
      enIndex.includes("sc.handbook_intro || 'A concise reference of technical terms across AI, backend, frontend, security, and operations.'"),
      'Handbook intro line must fall back to the English glossary description',
    );
    assert(
      koIndex.includes("sc.handbook_intro || 'AI, 백엔드, 프론트엔드, 보안, 운영 전반의 기술 용어를 한 곳에서 읽기 쉽게 정리합니다.'"),
      'Handbook intro line must fall back to the Korean glossary description',
    );
    ```
  - Library 단언(`tabProgress: 'My Progress'`)은 그대로 둔다.

- [ ] **Step 12: 레일과 stale 테스트 삭제**

```bash
git rm frontend/src/components/newsprint/HandbookListRail.astro frontend/tests/handbook-category-icons.test.cjs
```
(`handbook-category-icons`는 이미 옛 slug 기준으로 실패 중이고 레일 파일을 읽는다. 스펙대로 레일 삭제와 같은 커밋에서 지운다.)

Run: `grep -rn "HandbookListRail\|handbook-category-icons" frontend/src frontend/tests` → 결과 없음.

- [ ] **Step 13: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/handbook-index-shelves.test.cjs
node frontend/tests/term-of-day.test.cjs
node frontend/tests/handbook-shelves.test.mjs
node frontend/tests/handbook-v2.test.cjs
node frontend/tests/handbook-library-copy.test.cjs
node frontend/tests/home-front-query-budget.test.cjs
node frontend/tests/public-list-query-budget.test.cjs
node frontend/tests/public-term-index.test.cjs
node frontend/tests/public-list-personalization.test.cjs
node frontend/tests/issue-number-shell.test.cjs
node frontend/tests/list-v2.test.cjs
node frontend/tests/product-detail-search-sticky.test.cjs
node frontend/tests/handbook-search-recognition.test.cjs
cd frontend && npm run build
```
Expected:
- `handbook-search-recognition`을 뺀 모든 테스트 PASS, 빌드 "Complete!".
- `handbook-search-recognition`은 기준선과 **같은 메시지**("Handbook search input must define theme-specific input surface colors")로 실패해야 한다. 다른 메시지(특히 `data-placeholder-hints`)로 실패하면 페이지 수정이 원인이니 고친다.
- `public-term-index`는 다른 세션이 수정 중인 `publicTermIndex.ts`도 읽는다. 기준선과 결과가 같으면 된다.

- [ ] **Step 14: 커밋**

```bash
git add frontend/src/components/handbook/HandbookToday.astro frontend/src/components/handbook/HandbookShelves.astro frontend/src/components/handbook/HandbookAzIndex.astro frontend/src/pages/ko/handbook/index.astro frontend/src/pages/en/handbook/index.astro frontend/src/lib/pageData/handbookPage.ts frontend/src/styles/global.css frontend/tests/handbook-index-shelves.test.cjs frontend/tests/term-of-day.test.cjs frontend/tests/handbook-v2.test.cjs frontend/tests/handbook-library-copy.test.cjs
git commit -m "feat: handbook index with term of the day, shelves by field and A-Z index"
```

(`git rm`으로 stage된 삭제 2개가 함께 커밋된다.)

---

## Task 4: 쓰지 않게 된 CSS 정리 (TDD)

**Files:**
- Modify: `frontend/src/styles/global.css`, `frontend/tests/handbook-index-shelves.test.cjs`, `frontend/tests/product-filter-bar-mobile-sticky.test.cjs`

- [ ] **Step 1: 다른 사용처 확인**

Run:
```bash
grep -rn "handbook-trending\|product-category-showcase\|handbook-showcase\|newsprint-rail-category\|handbook-filter-\|handbook-difficulty-btn\|handbook-controls" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rn "Handbook trending terms" frontend/tests
```
Expected:
- 첫 grep: 결과 없음(Task 3에서 페이지와 레일이 더 이상 쓰지 않는다). 결과가 있으면 멈추고 보고한다. (`admin-filter-btn`은 다른 클래스라 걸리지 않는다.)
- 둘째 grep: `product-filter-bar-mobile-sticky.test.cjs` 한 줄. 이 테스트가 `/* --- Handbook trending terms --- */` 주석을 모바일 CSS 구간의 끝 표시로 쓴다. Step 4에서 함께 고친다.

- [ ] **Step 2: 실패하는 단언 추가** (Edit 도구로) — `handbook-index-shelves.test.cjs`의 `console.log('handbook-index-shelves.test.cjs passed');` **바로 위**에 넣는다.

```js
// unused CSS removed (Task 4); .handbook-result-count stays because the news list uses it
for (const gone of ['.handbook-trending', '#handbook-showcase', '.product-category-showcase', '.newsprint-rail-category-', '.handbook-filter-', '.handbook-difficulty-btn', '.handbook-controls']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(css.includes('.handbook-result-count {'), 'result count style stays (news list)');

```

Run: `node frontend/tests/handbook-index-shelves.test.cjs`
Expected: FAIL "unused CSS removed: .handbook-trending".

- [ ] **Step 3: CSS 삭제** (Edit 도구로). 정확히 아래 네 구간만 지운다.
  1. **레일 분야 아이콘**: `.newsprint-rail-category-link {`부터 `.newsprint-rail-category-icon svg { ... }` 블록 끝까지. 바로 뒤의 `.newsprint-rail-note,\n.newsprint-rail-copy {`는 **남긴다**(공유 규칙). 앞의 `.newsprint-rail .newsprint-card { ... }`도 남긴다.
  2. **분야 버튼**: `.handbook-controls {`부터 `.handbook-filter-btn[aria-pressed="true"]::after { ... }` 블록 끝까지. 사이에 있는 것(`body:has(...) .handbook-controls`, `.handbook-filter-row*`, `.handbook-filter-btn,\n.handbook-difficulty-btn` 그룹과 hover/focus-visible/active, `.handbook-filter-icon*`)은 모두 지운다. 바로 뒤의 `.handbook-card {`는 **남긴다**.
  3. **인기 용어 + 쇼케이스 카드**: `/* --- Handbook trending terms --- */` 주석부터 `/* --- Category Preview Section --- */` 주석 **바로 앞**까지. `.handbook-trending*`, `@media (max-width: 480px) { .handbook-trending-list ... }`, `/* --- Category showcase cards (shared: products + handbook) --- */` 주석, `.product-category-showcase*` 규칙과 그 `@media (max-width: 639px)`/`@media (min-width: 640px)` 블록이 들어 있다. `/* --- Category Preview Section --- */`와 `.product-category-preview`는 **남긴다**.
  4. **용어집 쇼케이스 오버라이드**: `/* Handbook "분야별로 보기": dotted list (products keep the card showcase) */` 주석부터 `/* --- Handbook category page --- */` 주석 **바로 앞**까지(`#handbook-showcase` 규칙 5개와 `@media (max-width: 639px)` 블록). Task 3에서 넣은 `/* Handbook index: ... */` 블록은 이 주석 **위**에 있으므로 지우지 않는다.
  - 지운 자리에 빈 줄이 3줄 이상 남으면 1줄로 줄인다.

Run: `grep -n "handbook-trending\|product-category-showcase\|handbook-showcase\|newsprint-rail-category\|handbook-filter-\|handbook-difficulty-btn\|handbook-controls" frontend/src/styles/global.css`
Expected: 결과 없음.

- [ ] **Step 4: `product-filter-bar-mobile-sticky.test.cjs` 구간 끝 표시 교체** (Edit 도구로)
  - `globalCss.indexOf('/* --- Handbook trending terms --- */', mobileStart)` → `globalCss.indexOf('/* --- Category Preview Section --- */', mobileStart)`
  - 삭제 뒤 이 주석이 옛 주석 자리 바로 다음에 오므로 잘라내는 구간은 같다.

- [ ] **Step 5: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/handbook-index-shelves.test.cjs
node frontend/tests/handbook-v2.test.cjs
node frontend/tests/product-filter-bar-mobile-sticky.test.cjs
node frontend/tests/products-v2.test.cjs
node frontend/tests/list-v2.test.cjs
node frontend/tests/news-list-desks.test.cjs
node frontend/tests/retro-decoration-removed.test.cjs
node frontend/tests/theme-palette.test.cjs
node frontend/tests/font-roles.test.cjs
cd frontend && npm run build
```
Expected: 모두 PASS, 빌드 "Complete!".

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/handbook-index-shelves.test.cjs frontend/tests/product-filter-bar-mobile-sticky.test.cjs
git commit -m "chore: remove handbook trending, showcase, filter and rail category CSS"
```

---

## Task 5: 검증 (컨트롤러)

- [ ] 전체 테스트를 **이름으로** 기준선(PASS 74 / FAIL 21)과 비교한다.
  ```bash
  for f in frontend/tests/*.cjs frontend/tests/*.mjs; do node "$f" >/dev/null 2>&1 && echo "PASS $(basename $f)" || echo "FAIL $(basename $f)"; done
  ```
  - 실패 목록은 기준선에서 `handbook-category-icons`(삭제)만 빠져야 한다. 신규 FAIL은 0이어야 한다.
  - 새 테스트 3개(`term-of-day`, `handbook-shelves`, `handbook-index-shelves`)는 PASS여야 한다.
- [ ] 브라우저(`.claude/launch.json`의 `frontend-dev`, 포트 4321) 매트릭스: 종이·순백·다크 × ≥1024px·375px × `/ko/handbook/`·`/en/handbook/`
  - 스크린샷(테마·폭·locale마다)
  - 가로 넘침 0: `document.documentElement.scrollWidth <= window.innerWidth`
  - 대비 검사: 서가 숫자, 오늘의 용어 라벨, 색인 바 muted 글자, 판 본문(다크 포함)
  - 1024px 이상: 서가 3열이고 가장 큰 분야가 2행을 차지하는지, 사전이 3단 + 세로 괘선인지
  - 375px: 오늘의 용어 1단(판이 정의 아래), 서가 1열, 색인 바 가로 스크롤(페이지는 넘치지 않음), 사전 1단
- [ ] 직접 클릭
  - 검색 "MCP" 입력 → 세 섹션이 숨고 카드·"N / 전체" 표시 → 지우면 세 섹션이 돌아오고 결과 수·결과 없음 안내가 남지 않는지
  - `?q=RAG`로 직접 진입하면 처음부터 검색 모드인지
  - `?category=llm-genai` → 카드가 그 분야로 걸러지고 "LLM · 생성AI · 전체 보기로"(EN "LLM & Generative AI · Back to all") 링크가 결과 수 바로 위에 보이는지 → 링크를 누르면 기본 모드
  - `?category=bogus` → 기본 모드 그대로(링크 숨김)
  - 색인 글자 클릭 → 그룹 머리가 고정 헤더·검색창 아래로 숨지 않는지. `#` 그룹이 있으면 `#az-num`으로 이동하는지
  - 서가 "N개 모두 보기" → 분야 페이지의 용어 수가 N과 같은지
  - 오늘의 용어가 같은 날 홈(`/ko/`, `/en/`)의 오늘의 용어와 같은지(`.handbook-today-name` vs `.home-front-term-name`)
  - 로그인 상태라면 검색 카드에 북마크/읽음 표시가 붙는지(`content-status:refresh`)
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 6: 문서

- [ ] 스펙 [[2026-10-17-handbook-index-shelves-design]] Status를 `implemented (2026-10-17)`로 바꾼다.
- [ ] 이 계획의 Status를 `done (2026-10-17)`로 바꾸고, 문서 끝에 "실행 결과"(커밋 해시, 테스트 이름 비교 결과, 매트릭스 결과, 계획 대비 변경, 후속)를 적는다.
- [ ] `ACTIVE_SPRINT.md`의 `REDESIGN-NEWS-ARTICLE` 항목 다음에 추가한다.
  `- [x] **REDESIGN-HANDBOOK-INDEX** — 용어집 첫 화면을 B+A로: 소개 한 줄, 오늘의 용어(홈과 같은 쿼리, 먹색 판 "뉴스에서는 이렇게 쓰여요"), 분야별 서가(소속 기준 숫자·첫 정규 분야 배치), A–Z 색인, 분야 버튼·인기 용어·쇼케이스·레일 제거 — [[2026-10-17-handbook-index-shelves-design]], [[2026-10-17-handbook-index-shelves]]`
- [ ] `grep -rln "HandbookListRail\|handbook-trending\|실시간 인기 용어\|handbook-showcase" vault --include=*.md`로 관련 노트를 찾는다. `90-Archive/`와 이번 스펙·계획은 빼고, 현재 구조를 설명하는 노트만 최소한으로 고친다.
- [ ] 알려진 한계를 실행 결과에 적는다: 색인은 앞 500개 용어까지만(통계 N은 count로 정확), 검색 카드 innerHTML 이스케이프는 별도 후보.
- [ ] 커밋(고친 vault 노트 경로만 지정해 add한다. `vault/.obsidian/*`는 넣지 않는다):
  ```bash
  git add vault/09-Implementation/plans/2026-10-17-handbook-index-shelves-design.md vault/09-Implementation/plans/2026-10-17-handbook-index-shelves.md vault/09-Implementation/plans/ACTIVE_SPRINT.md
  git commit -m "docs: record handbook index shelves redesign"
  ```

---

## 실행 결과 (2026-10-17)

- 커밋: `9449bfef` 오늘의 용어 공유 쿼리(홈 리팩터), `b934d453` 서가·색인 순수 함수, `85b46b99` 용어집 첫 화면(오늘의 용어·서가·A–Z), `61183a8d` 미사용 CSS 정리(-370줄).
- 테스트: 실패 목록이 기준선과 이름 기준 동일(삭제한 handbook-category-icons 제외), 신규 FAIL 0. 빌드 성공. 계획 단계에서 scratch 복사본으로 전체 적용·실데이터 렌더 사전 검증.
- 브라우저 검증: 오늘의 용어가 홈과 동일(ko/en 모두 SWE-bench, 판 문장 표시). 검색 "MCP" 2/114 → 오늘·서가·색인 숨김, "zzzzqq" 결과 없음 안내, 지우면 기본 화면 복귀(안내·결과 수 숨김). `?category=llm-genai` 92/114 + 해제 링크, `?category=bogus` 무시, `/en/?q=RAG` 5/114, `/en/?category=safety-ethics` 7 + "Back to all". 서가 9개, 색인 20그룹·114링크, `#az-M` 이동 시 검색창 아래에 보임.
- 매트릭스: 종이·순백·다크 × 1100px·375px × ko/en — 가로 넘침 0, 대비 미달 0.
- 계획 대비: KO 페이지의 `\u2026` 이스케이프와 EN 파생은 노드 스크립트로 처리(결과는 계획 블록과 동일). `product-filter-bar-mobile-sticky` 테스트 마커 갱신(계획에 포함).
- 남은 것: 모바일에서 "분야별 서가" 머리 아래 선과 첫 서가 위 2px 선이 가깝게 붙어 보임(시각 미세 조정 후보).
