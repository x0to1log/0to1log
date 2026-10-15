# 홈 1면 재설계 (A안) Implementation Plan

**Status:** done (2026-10-15) — 실행 결과는 문서 끝 참조.

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 홈 첫 화면을 진짜 신문 1면으로 바꾼다. 구성은 마스트헤드, 날짜줄, 3단 지면(지난 지면 / 1면 + 키워드 판 / 오늘의 용어), 맨 아래 안내다.

**Architecture:**
- 선택 로직은 `lib/homeFront.js`의 순수 함수로 확장한다. 데이터 쿼리 수는 그대로다.
- `HomeFrontPage.astro`를 1면으로 다시 쓰고, `HomeSplitHero.astro`는 지운 뒤 작은 `HomeIntro.astro`로 대체한다.
- CSS는 `global.css`의 홈 영역(`/* Split Hero */` ~ `@keyframes home-cursor-blink`)을 통째로 교체한다.

**Tech Stack:** Astro v5 SSR, `global.css` CSS 변수, 순수 Node 테스트(`node frontend/tests/<file>`, repo 루트에서 실행)

**Spec:** [[2026-10-15-home-front-page-redesign-design]] — 구현 전에 반드시 읽는다.

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 수정하지 말고 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `pages/admin/pipeline-runs/*`, `publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`)은 절대 stage하지 않는다.
- `git add`는 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 백슬래시가 들어간 파일(정규식 테스트, CSS)은 Write/Edit 도구로만 작성한다. Bash heredoc을 쓰면 백슬래시가 사라진다.
- `global.css`는 LF이고, 수정할 규칙은 셀렉터로 찾는다.
- dev 서버가 떠 있으면 `npm run build`가 EPERM으로 실패할 수 있다. 이때는 재시도를 반복하지 말고 보고한다.

**지켜야 할 것**
- 홈은 CDN에 캐시된다. `Astro.locals.user` 같은 사용자 의존 값을 쓰지 않는다.
- 새 `<script is:inline>`은 만들지 않는다. 필요하면 nonce가 필수다.
- 글꼴은 `--font-*` 변수만 쓴다.
  - `--font-masthead`: Newsreader
  - `--font-heading`: Hahmlet 600/700
  - `--font-ui`: Pretendard
- 테스트 기준선은 PASS 70 / FAIL 23이다. 이름으로 비교하고, 신규 FAIL은 없어야 한다.

**현재 코드 위치**
- `frontend/src/lib/homeFront.js`: `kstDay`, `termIndex`, `selectFrontPage`(현재 반환 `{lead, also, todayCount, term}`)
- `frontend/src/lib/pageData/homeFrontPage.ts`: 쿼리. 뉴스 select에 `tags`가 없다.
- `frontend/src/components/home/HomeFrontPage.astro`, `HomeSplitHero.astro`
- `frontend/src/pages/{ko,en}/index.astro`
- 테스트: `home-front-select.test.mjs`, `home-front-page.test.cjs`, `home-hero-v2.test.cjs`, `home-hero-copy.test.cjs`, `home-front-query-budget.test.cjs`, `list-v2.test.cjs`(HomeFrontPage가 `postTypeLabel` import를 유지해야 한다)

---

## Task 1: 선택 로직과 데이터 (TDD)

**Files:**
- Modify: `frontend/src/lib/homeFront.js`
- Modify: `frontend/src/lib/pageData/homeFrontPage.ts`
- Modify: `frontend/src/components/home/HomeFrontPage.astro`(`also` → `sibling` 최소 변경만. 본격 재작성은 Task 3)
- Test: `frontend/tests/home-front-select.test.mjs`

- [ ] **Step 1: 테스트를 새 반환 형태로 다시 쓴다** (Write 도구로 파일 전체 교체)

```js
// frontend/tests/home-front-select.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { kstDay, selectFrontPage, termIndex, frontKeyword } = await import(pathToFileURL(path.join(here, '../src/lib/homeFront.js')).href);

assert.equal(kstDay('2026-10-14T00:00:00Z'), '2026-10-14');
assert.equal(kstDay('2026-10-13T15:30:00Z'), '2026-10-14'); // KST 00:30
assert.equal(kstDay(null), null);

const NOW = new Date('2026-10-14T12:00:00+09:00');
const news = [
  { slug: 'a', post_type: 'business', published_at: '2026-10-14T00:00:00Z', tags: ['Google', 'Gemini 4 Argon', 'LLM'] },
  { slug: 'b', post_type: 'research', published_at: '2026-10-14T00:00:00Z', tags: [] },
  { slug: 'c', post_type: 'business', published_at: '2026-09-27T00:00:00Z', tags: ['Microsoft'] },
  { slug: 'd', post_type: 'research', published_at: '2026-09-27T00:00:00Z', tags: null },
  { slug: 'e', post_type: 'business', published_at: '2026-09-26T00:00:00Z', tags: [] },
];

// 오늘 기사 2건: 1면 a, 같은 날 다른 유형 b, 지난 지면은 그보다 이른 기사 2건
let r = selectFrontPage({ news, now: NOW });
assert.equal(r.lead.slug, 'a');
assert.equal(r.leadIsToday, true);
assert.equal(r.sibling.slug, 'b');
assert.deepEqual(r.earlier.map((n) => n.slug), ['c', 'd']);
assert.equal(r.todayCount, 2);
assert.deepEqual(r.keyword, { small: 'Google', big: 'Gemini 4 Argon' });

// 오늘 기사가 없으면: 1면은 가장 최근 기사, leadIsToday false
r = selectFrontPage({ news: news.slice(2), now: NOW });
assert.equal(r.lead.slug, 'c');
assert.equal(r.leadIsToday, false);
assert.equal(r.sibling.slug, 'd');
assert.deepEqual(r.earlier.map((n) => n.slug), ['e']);
assert.equal(r.todayCount, 0);

// 같은 날이라도 유형이 같으면 짝 기사가 아님
r = selectFrontPage({ news: [news[0], { ...news[1], post_type: 'business' }], now: NOW });
assert.equal(r.sibling, null);

// 다른 날 기사는 짝 기사가 아님
r = selectFrontPage({ news: [news[0], news[2]], now: NOW });
assert.equal(r.sibling, null);
assert.deepEqual(r.earlier.map((n) => n.slug), ['c']);

// 키워드 판 규칙: 태그 2개 이상 / 1개 / 없음(→ KST 날짜 MM.DD)
assert.deepEqual(frontKeyword(news[0]), { small: 'Google', big: 'Gemini 4 Argon' });
assert.deepEqual(frontKeyword(news[2]), { small: null, big: 'Microsoft' });
assert.deepEqual(frontKeyword(news[1]), { small: null, big: '10.14' });
assert.deepEqual(frontKeyword(news[3]), { small: null, big: '09.27' });
assert.deepEqual(frontKeyword({ ...news[0], tags: ['  ', 'Gemini'] }), { small: null, big: 'Gemini' }); // 빈 태그는 무시
assert.equal(frontKeyword({ slug: 'x', published_at: null, tags: [] }), null);
assert.equal(frontKeyword(null), null);

// 오늘의 용어 인덱스: 호수 % 개수
assert.equal(termIndex(new Date('2026-10-14T12:00:00+09:00'), 3), 1); // 제211호, 211 % 3 = 1
assert.equal(termIndex(new Date('2026-10-14T23:00:00+09:00'), 3), 1); // same KST day
assert.equal(termIndex(new Date('2026-10-15T12:00:00+09:00'), 3), 2); // next day
assert.equal(termIndex(new Date('2026-10-14T12:00:00+09:00'), 0), null);

// term은 그대로 통과
const picked = { slug: 'rag' };
assert.equal(selectFrontPage({ news, term: picked, now: NOW }).term, picked);
assert.equal(selectFrontPage({ news, now: NOW }).term, null);

// 빈 입력
r = selectFrontPage({ news: [], now: new Date() });
assert.deepEqual(r, { lead: null, leadIsToday: false, sibling: null, earlier: [], todayCount: 0, term: null, keyword: null });

console.log('home-front-select.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/home-front-select.test.mjs`
Expected: FAIL. `frontKeyword`가 export되지 않았거나 `r.leadIsToday` 단언에서 실패한다.

- [ ] **Step 3: `homeFront.js`의 `selectFrontPage` 이하를 교체** (Edit 도구로. `kstDay`·`termIndex`는 그대로 둔다)

```js
/**
 * Keyword plate text for the lead story: tags[0] small over tags[1] big;
 * one tag → big only; no tags → the lead's KST date as MM.DD.
 * @returns {{small: string|null, big: string}|null}
 */
export function frontKeyword(lead) {
  if (!lead) return null;
  const tags = (Array.isArray(lead.tags) ? lead.tags : [])
    .map((t) => (typeof t === 'string' ? t.trim() : ''))
    .filter(Boolean);
  if (tags.length >= 2) return { small: tags[0], big: tags[1] };
  if (tags.length === 1) return { small: null, big: tags[0] };
  const day = kstDay(lead.published_at);
  return day ? { small: null, big: `${day.slice(5, 7)}.${day.slice(8, 10)}` } : null;
}

/**
 * @param {{ news: Array<{slug:string, post_type?:string|null, published_at:string|null, tags?:string[]|null}>, term?: object|null, now?: Date }} input
 * news must be ordered by published_at desc. term is the already-chosen term of the day.
 */
export function selectFrontPage({ news, term = null, now = new Date() }) {
  const today = kstDay(now);
  const lead = news[0] ?? null;
  const leadDay = lead ? kstDay(lead.published_at) : null;
  const sibling = leadDay
    ? news.find((n, i) => i > 0 && kstDay(n.published_at) === leadDay && n.post_type !== lead.post_type) ?? null
    : null;
  const earlier = leadDay
    ? news.filter((n) => {
        const day = kstDay(n.published_at);
        return day !== null && day < leadDay;
      }).slice(0, 2)
    : [];
  const todayCount = news.filter((n) => kstDay(n.published_at) === today).length;

  return {
    lead,
    leadIsToday: leadDay !== null && leadDay === today,
    sibling,
    earlier,
    todayCount,
    term,
    keyword: frontKeyword(lead),
  };
}
```

파일 맨 위 주석 `// Pure selection for the home "오늘의 1면" strip. No I/O.`은 `// Pure selection for the home front page (lead, sibling, earlier, keyword plate). No I/O.`로 바꾼다.

- [ ] **Step 4: `homeFrontPage.ts` 수정**
  - `HomeFrontNews`에 `tags: string[] | null;`을 추가한다.
  - `HomeFrontPageData`를 다음으로 바꾼다.
    ```ts
    export interface HomeFrontPageData {
      lead: HomeFrontNews | null;
      leadIsToday: boolean;
      sibling: HomeFrontNews | null;
      earlier: HomeFrontNews[];
      todayCount: number;
      term: HomeFrontTerm | null;
      keyword: { small: string | null; big: string } | null;
    }
    ```
  - `EMPTY`를 `{ lead: null, leadIsToday: false, sibling: null, earlier: [], todayCount: 0, term: null, keyword: null }`로 바꾼다.
  - 뉴스 select 문자열을 `'title, slug, post_type, published_at, excerpt, reading_time_min, tags'`로 바꾼다.
  - 파일 맨 위 주석 `// Lean data for the home "오늘의 1면" strip: 1 news query + 1 term query.`은 `// Lean data for the home front page: 1 news query + term count + 1 term row.`로 바꾼다.

- [ ] **Step 5: `HomeFrontPage.astro` 최소 수정**
  - Props의 `also: HomeFrontNews | null;` → `sibling: HomeFrontNews | null;`
  - 구조분해 `also` → `sibling`
  - 마크업의 `also` 식별자 4곳(`{also && (`, `also.post_type`, `also.slug`, `also.title`)을 모두 `sibling`으로 바꾼다.
  - 하나라도 남으면 렌더 시 ReferenceError가 난다. 테스트로는 잡히지 않으므로 `grep -n "also" frontend/src/components/home/HomeFrontPage.astro`로 확인한다. 클래스명 `home-front-also`는 남아도 된다.
  - Task 3에서 파일 전체를 다시 쓴다.

- [ ] **Step 6: 통과 확인**

Run:
```bash
node frontend/tests/home-front-select.test.mjs
node frontend/tests/home-front-query-budget.test.cjs
node frontend/tests/list-v2.test.cjs
```
Expected: 셋 다 PASS.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/lib/homeFront.js frontend/src/lib/pageData/homeFrontPage.ts frontend/src/components/home/HomeFrontPage.astro frontend/tests/home-front-select.test.mjs
git commit -m "feat: select lead, sibling, earlier stories and keyword plate for home front page"
```

---

## Task 2: 안내 구역(HomeIntro)으로 교체

**Files:**
- Create: `frontend/src/components/home/HomeIntro.astro`
- Delete: `frontend/src/components/home/HomeSplitHero.astro` (`git rm`)
- Modify: `frontend/src/pages/ko/index.astro`, `frontend/src/pages/en/index.astro`
- Test: `frontend/tests/home-hero-copy.test.cjs` (전체 교체)

- [ ] **Step 1: `home-hero-copy.test.cjs`를 교체한다** (Write 도구로)

```js
// frontend/tests/home-hero-copy.test.cjs
// Home intro block (bottom of the front page) + approved intro copy.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const read = (p) => fs.readFileSync(path.join(__dirname, '..', p), 'utf8');

assert(!fs.existsSync(path.join(__dirname, '..', 'src/components/home/HomeSplitHero.astro')), 'HomeSplitHero is replaced by HomeIntro');

const intro = read('src/components/home/HomeIntro.astro');
assert(intro.includes('class="home-intro"'), 'intro root');
assert(intro.includes('0to1log는 이런 곳이에요') && intro.includes('What 0to1log is'), 'ko/en intro title');
assert(intro.includes('{homeIntro}'), 'intro renders the admin-edited home_intro');
assert(intro.includes('href={`/${locale}/news/`}') && intro.includes('href={`/${locale}/handbook/`}'), 'two CTAs: news + glossary');
assert(!/data-type-words|home-type-|<script/.test(intro), 'no typewriter or script');

const koHome = read('src/pages/ko/index.astro');
assert(
  koHome.includes('가장 빠르게 AI 변화를 읽고, 필요한 용어를 바로 찾고, 읽은 뉴스와 용어를 쌓아가며, 서로의 생각을 나누는 공간입니다.'),
  'Korean homepage intro must use the approved homepage copy',
);
const enHome = read('src/pages/en/index.astro');
assert(
  enHome.includes('Stay on top of AI as it changes fast, look up the terms you need right away, build your own library of news and concepts, and share how you make sense of it with others.'),
  'English homepage intro must reflect the updated hero copy',
);
for (const [loc, page] of [['ko', koHome], ['en', enHome]]) {
  assert(/<HomeFrontPage locale=\{locale\} \{\.\.\.front\} \/>\s*<HomeIntro locale=\{locale\} homeIntro=\{homeIntro\} \/>/.test(page), `${loc}: front page first, intro below`);
  assert(!page.includes('HomeSplitHero'), `${loc}: no HomeSplitHero`);
}

const adminSettings = read('src/pages/admin/settings.astro');
assert(
  adminSettings.includes("home_intro: { ko: '가장 빠르게 AI 변화를 읽고, 필요한 용어를 바로 찾고, 읽은 뉴스와 용어를 쌓아가며, 서로의 생각을 나누는 공간입니다.'"),
  'Admin default Korean home intro must stay in sync with the homepage hero copy',
);
console.log('home-hero-copy.test.cjs passed');
```

- [ ] **Step 2: 실패 확인** — `node frontend/tests/home-hero-copy.test.cjs` → FAIL ("HomeSplitHero is replaced by HomeIntro")

- [ ] **Step 3: `HomeIntro.astro`를 만든다**

```astro
---
// frontend/src/components/home/HomeIntro.astro
// Quiet "what this is" block under the front page. Copy comes from site content (home_intro).
interface Props {
  locale: 'en' | 'ko';
  homeIntro: string;
}

const { locale, homeIntro } = Astro.props;
const isKo = locale === 'ko';
---

<section class="home-intro" aria-labelledby="home-intro-title">
  <h3 id="home-intro-title" class="home-intro-title">{isKo ? '0to1log는 이런 곳이에요' : 'What 0to1log is'}</h3>
  <p class="home-intro-body">{homeIntro}</p>
  <div class="home-intro-cta">
    <a href={`/${locale}/news/`} class="home-intro-cta-primary">{isKo ? 'AI 뉴스 읽기 →' : 'Read AI News →'}</a>
    <a href={`/${locale}/handbook/`} class="home-intro-cta-secondary">{isKo ? '용어집 보기' : 'Browse Glossary'}</a>
  </div>
</section>
```

- [ ] **Step 4: index 두 개를 수정한다** (ko, en 동일)
  - import `HomeSplitHero` 줄을 다음으로 바꾼다.
    ```astro
    import HomeIntro from '../../components/home/HomeIntro.astro';
    ```
  - `<div class="home-page">` 안을 다음으로 바꾼다.
    ```astro
        <HomeFrontPage locale={locale} {...front} />
        <HomeIntro locale={locale} homeIntro={homeIntro} />
    ```
  - `homeIntro` 상수와 기본 문구는 그대로 둔다(테스트가 확인한다).

- [ ] **Step 5: HomeSplitHero 삭제** — `git rm frontend/src/components/home/HomeSplitHero.astro`

- [ ] **Step 6: 통과 확인**
  - `node frontend/tests/home-hero-copy.test.cjs` → PASS
  - `home-hero-v2.test.cjs`와 `home-front-page.test.cjs`는 이 시점에 실패해도 된다. Task 3에서 교체한다.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/home/HomeIntro.astro frontend/src/pages/ko/index.astro frontend/src/pages/en/index.astro frontend/tests/home-hero-copy.test.cjs
git commit -m "feat: replace home split hero with a quiet intro block under the front page"
```

(`git rm`으로 이미 stage된 HomeSplitHero 삭제도 이 커밋에 포함된다.)

---

## Task 3: 1면 마크업과 CSS

**Files:**
- Modify: `frontend/src/components/home/HomeFrontPage.astro` (전체 교체)
- Modify: `frontend/src/styles/global.css` (홈 영역 교체)
- Test: `frontend/tests/home-front-page.test.cjs`, `frontend/tests/home-hero-v2.test.cjs` (둘 다 전체 교체)

- [ ] **Step 1: `home-front-page.test.cjs` 교체** (Write 도구로)

```js
// frontend/tests/home-front-page.test.cjs
// Home front page: masthead h1, dateline, 3-column page (earlier / lead / term), keyword plate.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const comp = read('components/home/HomeFrontPage.astro');
assert(comp.includes('class="home-front"'), 'front page root');
assert((comp.match(/<h1[\s>]/g) || []).length === 1 && comp.includes('class="home-front-masthead"'), 'masthead is the single h1');
assert(/<h1 class="home-front-masthead">0to1log<span class="site-brand-dot" aria-hidden="true">\.<\/span><\/h1>/.test(comp), 'masthead text + accent period');
assert(!/\{\(lead \|\| term\) && \(/.test(comp), 'masthead and dateline always render');
assert(comp.includes('class="home-front-dateline"'), 'dateline');
assert(/오늘의 1면/.test(comp) && /최근 1면/.test(comp) && /Front page/.test(comp) && /Latest front page/.test(comp), 'lead label: today vs latest, ko/en');
assert(comp.includes('leadIsToday'), 'lead label depends on leadIsToday');
assert(comp.includes('postTypeLabel(locale, '), 'type labels come from lib/postType.js');
assert(/오늘의 용어/.test(comp) && /Term of the day/.test(comp), 'ko/en term label');
assert(/지난 지면/.test(comp) && /Earlier pages/.test(comp), 'ko/en earlier label');
assert(/아직 발행된 기사가 없어요/.test(comp) && /No stories published yet/.test(comp), 'empty state');
assert(comp.includes('class="home-front-plate"') && /오늘의 키워드/.test(comp) && /Today's keyword/.test(comp), 'keyword plate');
assert(comp.includes('href={`/${locale}/news/${lead.slug}/`}'), 'lead links to the news article');
assert(comp.includes('href={`/${locale}/handbook/${term.slug}/`}'), 'term links to the handbook');
assert(/<article class="home-front-lead">[\s\S]*class="home-front-plate"[\s\S]*<\/article>/.test(comp), 'plate sits inside the lead article');
const order = ['class="home-front-lead"', 'class="home-front-term"', 'class="home-front-earlier"'].map((s) => comp.indexOf(s));
assert(order.every((i) => i > 0) && order[0] < order[1] && order[1] < order[2], 'DOM order = reading order: lead, term, earlier');
assert(!/Astro\.locals/.test(comp), 'user-neutral (CDN cached)');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/index.astro`);
  assert(/import \{ getHomeFrontPageData \} from '\.\.\/\.\.\/lib\/pageData\/homeFrontPage'/.test(page), `${locale} page loads front page data`);
  assert(page.includes(`getHomeFrontPageData('${locale}')`), `${locale} page calls the loader`);
  assert(/<HomeFrontPage locale=\{locale\} \{\.\.\.front\} \/>/.test(page), `${locale} page renders the front page`);
  assert(page.includes('if (siteContentError) Astro.response.status = 503;'), `${locale} keeps 503 on site content error`);
}

const css = read('styles/global.css');
assert(/grid-template-areas:\s*"earlier lead term"/.test(css), 'desktop places earlier | lead | term');
assert(/\.home-front-grid > \*\s*\{\s*grid-area:\s*auto;/.test(css), 'mobile drops named areas so items stack in DOM order');
assert(!/\.home-front-[a-z-]+[^{]*\{[^}]*(?:^|[\s;{])order:/m.test(css), 'no CSS order on front page items ("border:" does not count)');
for (const sel of ['.home-front {', '.home-front-masthead {', '.home-front-dateline {', '.home-front-plate {', '.home-intro {']) {
  assert(css.includes(sel), `missing ${sel}`);
}
console.log('home-front-page.test.cjs passed');
```

- [ ] **Step 2: `home-hero-v2.test.cjs` 교체** (Write 도구로)

```js
// frontend/tests/home-hero-v2.test.cjs
// Masthead/dateline moved from the old split hero into HomeFrontPage; typewriter + split hero styles are gone.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const front = fs.readFileSync(path.join(src, 'components/home/HomeFrontPage.astro'), 'utf8');
const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

assert(front.includes('AI 뉴스와 용어를 기록하는 신문'), 'ko motto in the dateline');
assert(/import \{ issueLabel, issueNumber \} from '\.\.\/\.\.\/lib\/issue\.js'/.test(front), 'issue number uses lib/issue.js');
assert(/todayCount\?: number/.test(front), 'front page accepts todayCount');
assert(/todayCount > 0 \?/.test(front), '"오늘 N건" only when there are stories today');

assert(rule('.home-front-masthead').includes('var(--font-masthead)'), 'masthead uses Newsreader');
assert(rule('.home-front-masthead').includes('lining-nums'), 'masthead digits are lining (0to1, not oto1)');
assert(rule('.home-front-masthead').includes('var(--color-text-primary)'), 'masthead is ink');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.home-front-dateline')), 'dateline double rule (top)');
assert(/font-weight:\s*700/.test(rule('.home-front-lead-title')), 'lead title uses a loaded Hahmlet weight');

assert(!/home-split-hero|home-type-|home-cursor-blink/.test(css), 'split hero + typewriter styles removed');
assert(!/data-type-words/.test(front), 'no typewriter markup');
console.log('home-hero-v2.test.cjs passed');
```

- [ ] **Step 3: 실패 확인**

Run:
```bash
node frontend/tests/home-front-page.test.cjs
node frontend/tests/home-hero-v2.test.cjs
```
Expected: 둘 다 FAIL.

- [ ] **Step 4: `HomeFrontPage.astro` 전체 교체** (Write 도구로)

```astro
---
// frontend/src/components/home/HomeFrontPage.astro
// Newspaper front page: masthead, dateline, 3 columns (earlier | lead + keyword plate | term).
// DOM order is the reading order (lead → term → earlier); desktop columns come from grid-template-areas.
import type { HomeFrontNews, HomeFrontTerm } from '../../lib/pageData/homeFrontPage';
import { postTypeLabel } from '../../lib/postType.js';
import { issueLabel, issueNumber } from '../../lib/issue.js';

interface Props {
  locale: 'en' | 'ko';
  lead: HomeFrontNews | null;
  leadIsToday: boolean;
  sibling: HomeFrontNews | null;
  earlier: HomeFrontNews[];
  term: HomeFrontTerm | null;
  todayCount?: number;
  keyword: { small: string | null; big: string } | null;
}

const { locale, lead, leadIsToday, sibling, earlier = [], term, todayCount = 0, keyword } = Astro.props;
const isKo = locale === 'ko';
const lang = isKo ? 'ko-KR' : 'en-US';
const timeZone = 'Asia/Seoul';

const now = new Date();
const issueText = issueLabel(locale, issueNumber(now));
const dateLong = now.toLocaleDateString(lang, { timeZone, year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' });
const dateShort = now.toLocaleDateString(lang, { timeZone, month: 'long', day: 'numeric', weekday: 'short' });
const motto = isKo ? 'AI 뉴스와 용어를 기록하는 신문' : 'A newspaper that keeps a record of AI news and terms';

const typeOf = (n: HomeFrontNews) => postTypeLabel(locale, n.post_type) || (isKo ? 'AI 뉴스' : 'AI News');
const leadDate = lead?.published_at
  ? new Date(lead.published_at).toLocaleDateString(lang, { timeZone, month: isKo ? 'long' : 'short', day: 'numeric' })
  : '';
const leadKicker = !lead
  ? ''
  : leadIsToday
    ? (isKo ? `오늘의 1면 · ${typeOf(lead)}` : `Front page · ${typeOf(lead)}`)
    : (isKo ? `최근 1면 · ${leadDate}` : `Latest front page · ${leadDate}`);
const readTime = lead?.reading_time_min ? (isKo ? `${lead.reading_time_min}분` : `${lead.reading_time_min} min`) : '';
const siblingLead = sibling ? (isKo ? `같은 날 ${typeOf(sibling)}판:` : `Same day, ${typeOf(sibling)}:`) : '';

const termTitle = term ? (isKo ? term.korean_name || term.term : term.term) : '';
const termSub = term && isKo && term.korean_name ? term.term : '';
---

<section class="home-front" aria-label={isKo ? '오늘의 지면' : "Today's paper"}>
  <h1 class="home-front-masthead">0to1log<span class="site-brand-dot" aria-hidden="true">.</span></h1>
  <p class="home-front-dateline">
    <span>{issueText}</span>
    <span class="home-front-date">
      <span class="home-front-date-long">{dateLong} · {motto}</span>
      <span class="home-front-date-short">{dateShort}</span>
    </span>
    {todayCount > 0 ? <b>{isKo ? `오늘 ${todayCount}건` : `${todayCount} today`}</b> : <span></span>}
  </p>

  <div class="home-front-grid">
    {lead ? (
      <article class="home-front-lead">
        <span class="home-front-kicker">{leadKicker}</span>
        <h2 class="home-front-lead-title"><a href={`/${locale}/news/${lead.slug}/`}>{lead.title}</a></h2>
        {lead.excerpt && <p class="home-front-lead-excerpt">{lead.excerpt}</p>}
        {keyword && (
          <div class="home-front-plate" aria-hidden="true">
            <span class="home-front-plate-label">{isKo ? '오늘의 키워드' : "Today's keyword"}</span>
            {keyword.small && <span class="home-front-plate-small">{keyword.small}</span>}
            <span class="home-front-plate-big">{keyword.big}</span>
          </div>
        )}
        {(readTime || sibling) && (
          <p class="home-front-meta">
            {readTime && <span>{readTime}</span>}
            {readTime && sibling && <span aria-hidden="true"> · </span>}
            {sibling && (
              <span>{siblingLead} <a href={`/${locale}/news/${sibling.slug}/`}>{sibling.title}</a></span>
            )}
          </p>
        )}
      </article>
    ) : (
      <article class="home-front-lead">
        <p class="home-front-empty">{isKo ? '아직 발행된 기사가 없어요' : 'No stories published yet'}</p>
      </article>
    )}

    <section class="home-front-term" aria-label={isKo ? '오늘의 용어' : 'Term of the day'}>
      <p class="home-front-label">{isKo ? '오늘의 용어' : 'Term of the day'}</p>
      {term && (
        <>
          <h3 class="home-front-term-name">{termTitle}</h3>
          {termSub && <p class="home-front-term-sub">{termSub}</p>}
          {term.definition && <p class="home-front-term-def">{term.definition}</p>}
          <a class="home-front-term-link" href={`/${locale}/handbook/${term.slug}/`}>{isKo ? '풀이 읽기 →' : 'Read the explainer →'}</a>
        </>
      )}
      <a class="home-front-more" href={`/${locale}/news/`}>{isKo ? '뉴스 전체 보기 →' : 'All news →'}</a>
    </section>

    {earlier.length > 0 && (
      <section class="home-front-earlier" aria-label={isKo ? '지난 지면' : 'Earlier pages'}>
        <p class="home-front-label">{isKo ? '지난 지면' : 'Earlier pages'}</p>
        {earlier.map((story) => (
          <div class="home-front-story">
            <span class="home-front-kicker">{typeOf(story)}</span>
            <h3 class="home-front-story-title"><a href={`/${locale}/news/${story.slug}/`}>{story.title}</a></h3>
            {story.excerpt && <p class="home-front-story-excerpt">{story.excerpt}</p>}
          </div>
        ))}
      </section>
    )}
  </div>
</section>
```

- [ ] **Step 5: `global.css` 홈 영역 교체**
  - 시작: `/* Split Hero */` 줄(`.home-page` 규칙과 그 `@media (min-width: 768px)` 다음)
  - 끝: `@keyframes home-cursor-blink { ... }` 블록의 닫는 `}`(그 다음 줄은 `/* Glossary + Products 2-col spotlight */`)
  - 이 범위 전체를 아래 CSS로 바꾼다. `.home-page` 규칙은 그대로 둔다.
  - 교체 방법: 범위가 커서 Edit가 어려우면 Write 도구로 Node 스크립트(스크래치패드)를 만든다. 스크립트는 두 마커 사이를 아래 CSS 파일 내용으로 바꾼다. CSS도 Write 도구로 별도 파일에 저장한다.

```css
/* Home: newspaper front page — masthead, dateline, 3 columns (earlier | lead | term) */
.home-front {
  max-width: 1120px;
  margin: 0 auto;
  padding: clamp(1.5rem, 4vh, 2.5rem) 0 2.5rem;
}

.home-front-masthead {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: clamp(3rem, 2rem + 4vw, 4.75rem);
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1;
  text-align: center;
  color: var(--color-text-primary);
}

.home-front-dateline {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: baseline;
  gap: 1rem;
  margin-top: 1rem;
  padding: 0.5rem 0;
  border-top: 2px solid var(--color-text-primary);
  border-bottom: 1px solid var(--color-text-primary);
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.home-front-date {
  text-align: center;
}

.home-front-date-short {
  display: none;
}

.home-front-dateline b {
  color: var(--color-accent);
  font-weight: 600;
}

.home-front-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2.1fr) minmax(0, 1fr);
  grid-template-areas: "earlier lead term";
  padding-top: 1.5rem;
}

.home-front-lead {
  grid-area: lead;
  padding: 0 1.5rem;
  border-left: 1px solid var(--color-border);
  border-right: 1px solid var(--color-border);
}

.home-front-earlier {
  grid-area: earlier;
  padding-right: 1.5rem;
}

.home-front-term {
  grid-area: term;
  padding-left: 1.5rem;
}

.home-front-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-text-muted);
  margin-bottom: 0.6rem;
}

.home-front-kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-accent);
}

.home-front-kicker::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.home-front-lead-title {
  font-family: var(--font-heading);
  font-size: clamp(1.7rem, 1.1rem + 1.6vw, 2.4rem);
  font-weight: 700;
  line-height: 1.18;
  letter-spacing: -0.045em;
  margin: 0.6rem 0 0.9rem;
}

.home-front-lead-title a,
.home-front-story-title a,
.home-front-meta a {
  color: var(--color-text-primary);
  text-decoration: none;
}

.home-front-lead-title a:hover,
.home-front-story-title a:hover,
.home-front-meta a:hover {
  color: var(--color-accent);
}

.home-front-lead-excerpt {
  font-size: 1rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

/* Keyword plate: the page's only solid block (ink in light themes) */
.home-front-plate {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-height: 150px;
  margin-top: 1.1rem;
  padding: 0.9rem 1.1rem 1rem;
  overflow: hidden;
  border-radius: 2px;
  background: var(--color-text-primary);
  color: var(--color-bg-primary);
}

.home-front-plate::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, currentColor 1.2px, transparent 1.6px);
  background-size: 9px 9px;
  opacity: 0.22;
  -webkit-mask-image: linear-gradient(115deg, transparent 30%, #000 85%);
  mask-image: linear-gradient(115deg, transparent 30%, #000 85%);
}

[data-theme="dark"] .home-front-plate {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.home-front-plate-label {
  position: absolute;
  top: 0.8rem;
  left: 1.1rem;
  font-size: 0.72rem;
  opacity: 0.75;
}

.home-front-plate-small,
.home-front-plate-big {
  position: relative;
}

.home-front-plate-small {
  font-size: 0.85rem;
  opacity: 0.8;
}

.home-front-plate-big {
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-size: clamp(2rem, 1.2rem + 2vw, 2.9rem);
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1.05;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}

.home-front-meta {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin-top: 0.75rem;
}

.home-front-meta a {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.home-front-empty {
  font-size: 0.95rem;
  color: var(--color-text-muted);
  padding: 2rem 0;
}

.home-front-story + .home-front-story {
  margin-top: 1.1rem;
  padding-top: 1rem;
  border-top: 1px dotted var(--color-border);
}

.home-front-story-title {
  font-family: var(--font-heading);
  font-size: 1.1rem;
  font-weight: 600;
  line-height: 1.38;
  letter-spacing: -0.03em;
  margin: 0.45rem 0 0.35rem;
}

.home-front-story-excerpt {
  font-size: 0.85rem;
  line-height: 1.65;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-front-term-name {
  font-family: var(--font-heading);
  font-size: 1.9rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1.15;
}

.home-front-term-sub {
  font-family: var(--font-masthead);
  font-size: 1rem;
  color: var(--color-text-muted);
  margin-top: 0.15rem;
}

.home-front-term-def {
  font-size: 0.85rem;
  line-height: 1.65;
  color: var(--color-text-secondary);
  margin: 0.75rem 0 0.6rem;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-front-term-link,
.home-front-more {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
}

.home-front-more {
  display: block;
  margin-top: 1.25rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--color-text-primary);
}

@media (max-width: 767px) {
  .home-front-dateline {
    gap: 0.5rem;
    font-size: 0.72rem;
  }

  .home-front-date-long {
    display: none;
  }

  .home-front-date-short {
    display: inline;
  }

  .home-front-grid {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: none;
    padding-top: 1.25rem;
  }

  .home-front-grid > * {
    grid-area: auto;
  }

  .home-front-lead,
  .home-front-earlier,
  .home-front-term {
    padding: 0;
    border: none;
  }

  .home-front-term,
  .home-front-earlier {
    margin-top: 1.5rem;
    padding-top: 1.25rem;
    border-top: 1px dotted var(--color-border);
  }

  .home-front-plate {
    min-height: 110px;
  }
}

/* Home: intro under the front page */
.home-intro {
  max-width: 640px;
  margin: 0 auto;
  padding: 2.25rem 0 1rem;
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.home-intro-title {
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.home-intro-body {
  margin: 0.6rem 0 1.1rem;
  font-size: 0.95rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.home-intro-cta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
}

.home-intro-cta-primary,
.home-intro-cta-secondary {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  padding: 0.55rem 1.1rem;
  border-radius: 4px;
  text-decoration: none;
  transition: background-color 0.18s, border-color 0.18s, color 0.18s;
}

.home-intro-cta-primary {
  background: var(--color-text-primary);
  color: var(--color-bg-primary);
  font-weight: 700;
}

.home-intro-cta-primary:hover {
  background: var(--color-accent);
}

.home-intro-cta-secondary {
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.home-intro-cta-secondary:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.home-intro-cta-primary:focus-visible,
.home-intro-cta-secondary:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  .home-intro-cta-primary,
  .home-intro-cta-secondary {
    transition: none;
  }
}
```

- [ ] **Step 6: 남은 참조 확인**

Run: `grep -rn "home-split-hero\|home-type-\|home-cursor-blink\|HomeSplitHero\|home-front-also\|home-front-title\|home-front-head" frontend/src`
Expected: 결과 없음. `frontend/tests`는 검색하지 않는다. 새 테스트가 "없어야 한다"는 단언에 이 문자열을 담고 있기 때문이다.

- [ ] **Step 7: 통과 확인**

Run:
```bash
node frontend/tests/home-front-page.test.cjs
node frontend/tests/home-hero-v2.test.cjs
node frontend/tests/home-hero-copy.test.cjs
node frontend/tests/home-front-select.test.mjs
node frontend/tests/home-front-query-budget.test.cjs
node frontend/tests/list-v2.test.cjs
node frontend/tests/font-roles.test.cjs
node frontend/tests/theme-palette.test.cjs
node frontend/tests/retro-decoration-removed.test.cjs
cd frontend && npm run build
```
Expected: 모두 PASS, 빌드 "Complete!". 테스트 파일 확장자가 다르면 `ls frontend/tests | grep <이름>`으로 찾는다.

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/home/HomeFrontPage.astro frontend/src/styles/global.css frontend/tests/home-front-page.test.cjs frontend/tests/home-hero-v2.test.cjs
git commit -m "feat: newspaper front page home with masthead, dateline, three columns and keyword plate"
```

---

## Task 4: 검증 (컨트롤러)

- [ ] 전체 테스트를 기준선(PASS 70 / FAIL 23)과 이름으로 비교한다. 신규 FAIL은 없어야 한다.
- [ ] 브라우저 매트릭스를 확인한다: 종이·순백·다크 × 데스크톱(≥1024px)·모바일(375px), `/ko/`와 `/en/`
  - 스크린샷
  - 페이지 가로 넘침: `document.documentElement.scrollWidth === clientWidth`
  - 글자 대비 검사(일반 4.5:1, 큰 글자 3:1)
  - 키워드 판: 다크에서 너무 튀지 않는지, 긴 태그가 2줄에서 말줄임되는지
  - 모바일 순서: 1면 → 키워드 판 → 짝 기사 → 오늘의 용어 → 지난 지면 → 안내
- [ ] 발견한 문제는 고친 뒤 `fix:` 커밋으로 남긴다.

## Task 5: 문서

- [ ] 스펙 Status를 `implemented (2026-10-15)`로 바꾼다.
- [ ] 이 계획에 Status와 실행 결과를 적는다.
- [ ] `ACTIVE_SPRINT.md`에 REDESIGN-HOME 항목과 증거(커밋, 테스트 수, 브라우저 매트릭스)를 추가한다.
- [ ] `vault/12-Journal-&-Decisions/2026-10-14-homepage-front-strip.md`에 후속 결정을 한 단락 덧붙인다. 1면 띠가 전면 1면(A안)으로 바뀌었다는 내용이다.
- [ ] 커밋: `docs: record home front page redesign`

---

## 실행 결과 (2026-10-15)

- 커밋: `0634c4d4` 선택 로직·데이터, `efaf2385` HomeIntro 교체(HomeSplitHero 삭제), `c4b3658e` 1면 마크업·CSS(홈 CSS 342줄 → 381줄 교체).
- 테스트: 전체 70 PASS / 23 FAIL(실패 목록 기준선과 동일, 신규 0). 빌드 성공.
- 브라우저: 종이·순백·다크 × 1085px·360/375px × /ko/·/en/ — 페이지 가로 넘침 0, 홈 영역 대비 미달 0. 모바일 순서 1면 → 키워드 판 → 짝 기사 → 오늘의 용어 → 지난 지면 → 안내 확인.
- 계획 대비: 없음. 다크 테마 키워드 판은 먹색 대신 `--color-bg-tertiary` 면(계획 CSS에 명시).
