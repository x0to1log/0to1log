# 사이트 리디자인 3단계(홈: Hero + 오늘의 1면) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** done (2026-10-14) — 실행 결과는 문서 끝 참조.

**Goal:** 홈 Hero를 V2 스타일(큰 제호 + 마침표, 모토, 호수 줄)로 다듬고, 그 아래에 "오늘의 1면"(머리기사 1건 + 같은 날 기사 1줄 + 오늘의 용어 1개)을 붙인다.

**Architecture:**
- 선택 로직은 순수 모듈 `src/lib/homeFront.js`로 둔다. 오늘(KST) 기사 수 계산, 머리기사와 "같은 날 한 줄" 고르기, 호수 기반 오늘의 용어 선택을 담당한다.
- DB 조회는 새 파일 `src/lib/pageData/homeFrontPage.ts`가 맡는다. 뉴스 1번과 용어 1번만 조회한다.
- 화면은 새 컴포넌트 `HomeFrontPage.astro`와 기존 `HomeSplitHero.astro`가 그린다.
- 홈의 CDN 캐시 정책('list', s-maxage=300)은 그대로 둔다.

**Tech Stack:** Astro v5, Supabase JS(anon), 순수 Node 테스트(`node frontend/tests/<file>`, repo 루트)

**결정 근거:** 3월 20일 결정("홈은 Hero만")의 원칙인 서비스 정체성 → CTA 흐름은 지킨다. 그 아래에 매일 바뀌는 편집된 한 줄만 더한다. 2026-10-14에 사용자가 승인했다.

**시안:** `.superpowers/brainstorm/phase3/home-front.html`

---

## 사전 정보 (실행자 필독)

### 공유 작업 트리
- 다른 Claude 세션("Supabase 할당량 최적화")이 같은 repo에서 작업 중이다. 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 수정하지 말고 BLOCKED로 보고한다.
- **기존** `src/lib/pageData/*` 파일, `src/middleware.ts`, `src/lib/server/*`, `pages/{en,ko}/**/[slug].astro`, `pages/{en,ko}/**/category/*`, `NewsprintArticleLayout.astro`, `BlogArticleLayout.astro`, `ProductDetail*`, `StickyReadingActions*`는 수정하지 않는다.
- `src/lib/pageData/homeFrontPage.ts`는 **새 파일로만 추가**한다. 그 세션과 합의된 사항이다.
- 홈은 CDN에 캐시되어 모든 방문자가 같은 화면을 받는다. 그래서 홈 데이터와 컴포넌트는 `Astro.locals.user`, `profile` 같은 사용자 정보로 **분기하지 않는다**.
- 그 세션은 뉴스·용어가 바뀌면 `home` 캐시 태그도 무효화되게 바꿔뒀다(`lib/server/cacheInvalidation.ts`). 이 계획에서는 손대지 않는다.

### 커밋과 편집 규칙
- `git add`는 계획에 적힌 파일만 경로를 지정해서 한다. `-A`/`.`, stash/reset/checkout은 금지한다. 샌드박스가 명령을 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 계획에 적힌 그대로 쓴다. `Co-Authored-By`는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- 정규식이 들어간 편집은 Edit 도구로 한다. Bash heredoc을 쓰면 백슬래시가 사라진다. `global.css`는 줄 번호가 계속 바뀌므로 셀렉터로 찾는다.

### 테스트 기준선
- 테스트 비교는 개수가 아니라 **이름**으로 한다. 기준선(2단계 종료)은 PASS 57 / FAIL 23이다.
- 반드시 계속 통과해야 하는 기존 테스트:
  - `home-hero-copy`: HomeSplitHero의 `headline` 배열 리터럴과 ko/en 소개 문구
  - `home-query-budget`: homePage.ts. 이 계획에서는 수정하지 않는다.
  - `public-error-cache-policy`: 홈의 siteContent 오류 시 503
  - `public-cache-policy`

### 데이터 사실 (2026-10-14 확인)
- `news_posts.published_at`은 그날 `00:00:00Z`로 저장된다. 하루에 business 1건과 research 1건 정도다. 9/27부터 10/14 사이에는 공백이 있다.
- `handbook_terms`에 `is_favourite = true`인 용어가 있다. 정의 컬럼은 `definition_ko`, `definition_en`이고 이름 컬럼은 `term`, `korean_name`이다.

---

## Chunk 1: 데이터

### Task 1: 순수 선택 로직 `src/lib/homeFront.js`

**Files:**
- Create: `frontend/src/lib/homeFront.js`
- Test: `frontend/tests/home-front-select.test.mjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/home-front-select.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { kstDay, selectFrontPage } = await import(pathToFileURL(path.join(here, '../src/lib/homeFront.js')).href);

assert.equal(kstDay('2026-10-14T00:00:00Z'), '2026-10-14');
assert.equal(kstDay('2026-10-13T15:30:00Z'), '2026-10-14'); // KST 00:30
assert.equal(kstDay(null), null);

const news = [
  { slug: 'a', title: 'A', published_at: '2026-10-14T00:00:00Z' },
  { slug: 'b', title: 'B', published_at: '2026-10-14T00:00:00Z' },
  { slug: 'c', title: 'C', published_at: '2026-09-27T00:00:00Z' },
];
const terms = [{ slug: 'rag' }, { slug: 'bm25' }, { slug: 'agent' }];

// 오늘(KST) 기사 2건, 머리기사 a, 같은 날 한 줄 b
let r = selectFrontPage({ news, terms, now: new Date('2026-10-14T12:00:00+09:00') });
assert.equal(r.todayCount, 2);
assert.equal(r.lead.slug, 'a');
assert.equal(r.also.slug, 'b');

// 오늘 기사가 없으면 todayCount 0, 머리기사는 가장 최근 기사
r = selectFrontPage({ news: news.slice(2), terms, now: new Date('2026-10-14T12:00:00+09:00') });
assert.equal(r.todayCount, 0);
assert.equal(r.lead.slug, 'c');
assert.equal(r.also, null);

// 같은 날이 아니면 also 없음
r = selectFrontPage({ news: [news[0], news[2]], terms, now: new Date('2026-10-14T12:00:00+09:00') });
assert.equal(r.also, null);

// 오늘의 용어: slug 정렬 후 호수 % 개수 → 결정적이며 날마다 바뀜
const t1 = selectFrontPage({ news, terms, now: new Date('2026-10-14T12:00:00+09:00') }).term.slug;
const t1b = selectFrontPage({ news, terms: [...terms].reverse(), now: new Date('2026-10-14T23:00:00+09:00') }).term.slug;
const t2 = selectFrontPage({ news, terms, now: new Date('2026-10-15T12:00:00+09:00') }).term.slug;
assert.equal(t1, t1b, 'same KST day + same set → same term regardless of input order');
assert.notEqual(t1, t2, 'next day → different term');
// 2026-10-14 = 제211호, 정렬 [agent, bm25, rag], 211 % 3 = 1 → bm25
assert.equal(t1, 'bm25');

// 빈 입력
r = selectFrontPage({ news: [], terms: [], now: new Date() });
assert.deepEqual(r, { lead: null, also: null, todayCount: 0, term: null });

console.log('home-front-select.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/home-front-select.test.mjs`
Expected: FAIL. `Cannot find module ... src/lib/homeFront.js`

- [ ] **Step 3: 구현**

```js
// frontend/src/lib/homeFront.js
// Pure selection for the home "오늘의 1면" strip. No I/O.
import { issueNumber } from './issue.js';

const kstFormat = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
});

/** @returns {string|null} YYYY-MM-DD of the KST calendar day */
export function kstDay(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : kstFormat.format(date);
}

/**
 * @param {{ news: Array<{slug:string, published_at:string|null}>, terms: Array<{slug:string}>, now?: Date }} input
 * news must be ordered by published_at desc.
 */
export function selectFrontPage({ news, terms, now = new Date() }) {
  const today = kstDay(now);
  const lead = news[0] ?? null;
  const leadDay = lead ? kstDay(lead.published_at) : null;
  const second = news[1] ?? null;
  const also = second && leadDay && kstDay(second.published_at) === leadDay ? second : null;
  const todayCount = news.filter((n) => kstDay(n.published_at) === today).length;

  let term = null;
  if (terms.length > 0) {
    const sorted = [...terms].sort((a, b) => a.slug.localeCompare(b.slug));
    term = sorted[(issueNumber(now) ?? 0) % sorted.length];
  }
  return { lead, also, todayCount, term };
}
```

- [ ] **Step 4: 통과 확인**

Run: `node frontend/tests/home-front-select.test.mjs`
Expected: `home-front-select.test.mjs passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/homeFront.js frontend/tests/home-front-select.test.mjs
git commit -m "feat: select home front page lead story and term of the day"
```

### Task 2: 데이터 함수 `src/lib/pageData/homeFrontPage.ts`

**Files:**
- Create: `frontend/src/lib/pageData/homeFrontPage.ts`
- Test: `frontend/tests/home-front-query-budget.test.cjs`

- [ ] **Step 1: 실패하는 테스트 작성** (기존 `home-query-budget`과 같은 정적 검사 방식)

```js
// frontend/tests/home-front-query-budget.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const file = path.join(__dirname, '..', 'src/lib/pageData/homeFrontPage.ts');
const src = fs.readFileSync(file, 'utf8');
const count = (re) => (src.match(re) || []).length;

assert.equal(count(/\.from\('news_posts'\)/g), 1, 'exactly one news_posts query');
assert.equal(count(/\.from\('handbook_terms'\)/g), 1, 'exactly one handbook_terms query');
assert(/\.from\('news_posts'\)[\s\S]*?\.limit\(6\)/.test(src), 'news query is limited to 6 rows');
assert(/\.from\('handbook_terms'\)[\s\S]*?\.limit\(60\)/.test(src), 'term query is limited to 60 rows');
assert(!/select\('\*'\)/.test(src), 'no select(*)');
assert(/\.eq\('is_favourite', true\)/.test(src), 'term of the day comes from favourites');
assert(/definition:\$\{definitionField\}/.test(src), 'only the locale definition column is selected');
assert(/selectFrontPage\(/.test(src), 'selection logic lives in lib/homeFront.js');
console.log('home-front-query-budget.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/home-front-query-budget.test.cjs`
Expected: FAIL. `ENOENT ... homeFrontPage.ts`

- [ ] **Step 3: 구현**

```ts
// frontend/src/lib/pageData/homeFrontPage.ts
// Lean data for the home "오늘의 1면" strip: 1 news query + 1 term query.
import { supabase } from '../supabase';
import { selectFrontPage } from '../homeFront.js';

export interface HomeFrontNews {
  title: string;
  slug: string;
  post_type: string | null;
  published_at: string | null;
  excerpt: string | null;
  reading_time_min: number | null;
}

export interface HomeFrontTerm {
  term: string;
  slug: string;
  korean_name: string | null;
  definition: string | null;
}

export interface HomeFrontPageData {
  lead: HomeFrontNews | null;
  also: HomeFrontNews | null;
  todayCount: number;
  term: HomeFrontTerm | null;
}

const EMPTY: HomeFrontPageData = { lead: null, also: null, todayCount: 0, term: null };

export async function getHomeFrontPageData(locale: 'en' | 'ko', now = new Date()): Promise<HomeFrontPageData> {
  if (!supabase) return EMPTY;
  const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';

  const [newsRes, termsRes] = await Promise.all([
    supabase
      .from('news_posts')
      .select('title, slug, post_type, published_at, excerpt, reading_time_min')
      .eq('status', 'published')
      .eq('locale', locale)
      .order('published_at', { ascending: false })
      .order('post_type', { ascending: true }) // same-day stories share 00:00Z; keep the lead stable across cache refreshes
      .limit(6),
    supabase
      .from('handbook_terms')
      .select(`term, slug, korean_name, definition:${definitionField}`)
      .eq('status', 'published')
      .eq('is_favourite', true)
      .order('slug', { ascending: true })
      .limit(60),
  ]);

  const news = newsRes.error ? [] : ((newsRes.data ?? []) as HomeFrontNews[]);
  const terms = termsRes.error ? [] : ((termsRes.data ?? []) as HomeFrontTerm[]);
  return selectFrontPage({ news, terms, now }) as HomeFrontPageData;
}
```

- [ ] **Step 4: 통과 확인**

Run: `node frontend/tests/home-front-query-budget.test.cjs`
Expected: `passed`. 이어서 `node frontend/tests/home-query-budget.test.cjs`도 실행해서 계속 PASS인지 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/pageData/homeFrontPage.ts frontend/tests/home-front-query-budget.test.cjs
git commit -m "feat: add lean home front page data loader"
```

---

## Chunk 2: 화면

### Task 3: `HomeFrontPage.astro` + 홈 페이지 연결

**Files:**
- Create: `frontend/src/components/home/HomeFrontPage.astro`
- Modify: `frontend/src/pages/ko/index.astro`, `frontend/src/pages/en/index.astro`
- Modify: `frontend/src/styles/global.css` (`/* Typewriter word animation */` 주석 바로 위에 `.home-front*` 추가)
- Test: `frontend/tests/home-front-page.test.cjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/home-front-page.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const comp = read('components/home/HomeFrontPage.astro');
assert(comp.includes('class="home-front"'), 'front strip root');
assert(/오늘의 1면/.test(comp) && /Today's front page/.test(comp), 'ko/en section title');
assert(/오늘의 용어/.test(comp) && /Term of the day/.test(comp), 'ko/en term label');
assert(comp.includes('href={`/${locale}/news/${lead.slug}/`}'), 'lead links to the news article');
assert(comp.includes('href={`/${locale}/handbook/${term.slug}/`}'), 'term links to the handbook');
assert(/\{\(lead \|\| term\) && \(/.test(comp), 'strip renders only when there is a lead or a term');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/index.astro`);
  assert(/import \{ getHomeFrontPageData \} from '\.\.\/\.\.\/lib\/pageData\/homeFrontPage'/.test(page), `${locale} page loads front page data`);
  assert(page.includes(`getHomeFrontPageData('${locale}')`), `${locale} page calls the loader`);
  assert(/<HomeFrontPage locale=\{locale\} \{\.\.\.front\} \/>/.test(page), `${locale} page renders the strip`);
  assert(/todayCount=\{front\.todayCount\}/.test(page), `${locale} hero receives todayCount`);
  assert(page.includes('if (siteContentError) Astro.response.status = 503;'), `${locale} keeps 503 on site content error`);
}

const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');
for (const sel of ['.home-front {', '.home-front-grid {', '.home-front-term {']) {
  assert(css.includes(sel), `missing ${sel}`);
}
console.log('home-front-page.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/home-front-page.test.cjs`
Expected: FAIL. `ENOENT ... HomeFrontPage.astro`

- [ ] **Step 3: 컴포넌트 작성**

```astro
---
// frontend/src/components/home/HomeFrontPage.astro
import type { HomeFrontNews, HomeFrontTerm } from '../../lib/pageData/homeFrontPage';

interface Props {
  locale: 'en' | 'ko';
  lead: HomeFrontNews | null;
  also: HomeFrontNews | null;
  term: HomeFrontTerm | null;
  todayCount?: number;
}

const { locale, lead, also, term } = Astro.props;
const isKo = locale === 'ko';
const typeLabel = (type: string | null) => {
  if (type === 'business') return isKo ? '비즈니스' : 'Business';
  if (type === 'research') return isKo ? '리서치' : 'Research';
  return isKo ? 'AI 뉴스' : 'AI News';
};
const termTitle = term ? (isKo ? term.korean_name || term.term : term.term) : '';
const termSub = term && isKo && term.korean_name ? term.term : '';
---

{(lead || term) && (
  <section class="home-front" aria-labelledby="home-front-title">
    <div class="home-front-head">
      <h2 id="home-front-title" class="home-front-title">{isKo ? '오늘의 1면' : "Today's front page"}</h2>
      <a class="home-front-more" href={`/${locale}/news/`}>{isKo ? '뉴스 전체 보기 →' : 'All news →'}</a>
    </div>
    <div class="home-front-grid">
      {lead && (
        <article class="home-front-lead">
          <span class="home-front-kicker">{typeLabel(lead.post_type)}</span>
          <h3 class="home-front-lead-title"><a href={`/${locale}/news/${lead.slug}/`}>{lead.title}</a></h3>
          {lead.excerpt && <p class="home-front-lead-excerpt">{lead.excerpt}</p>}
          {lead.reading_time_min ? (
            <p class="home-front-meta">{isKo ? `${lead.reading_time_min}분 읽기` : `${lead.reading_time_min} min read`}</p>
          ) : null}
          {also && (
            <p class="home-front-also">
              <span>{typeLabel(also.post_type)}</span>
              <a href={`/${locale}/news/${also.slug}/`}>{also.title}</a>
            </p>
          )}
        </article>
      )}
      {term && (
        <aside class="home-front-term">
          <p class="home-front-term-label">{isKo ? '오늘의 용어' : 'Term of the day'}</p>
          <h3 class="home-front-term-name">{termTitle}</h3>
          {termSub && <p class="home-front-term-sub">{termSub}</p>}
          {term.definition && <p class="home-front-term-def">{term.definition}</p>}
          <a class="home-front-term-link" href={`/${locale}/handbook/${term.slug}/`}>{isKo ? '핸드북에서 보기 →' : 'Open in Handbook →'}</a>
        </aside>
      )}
    </div>
  </section>
)}
```

- [ ] **Step 4: 페이지 연결** (ko 기준. en도 같은 방식으로 `'en'`)
  - frontmatter import에 다음 두 줄을 추가한다.
    ```astro
    import HomeFrontPage from '../../components/home/HomeFrontPage.astro';
    import { getHomeFrontPageData } from '../../lib/pageData/homeFrontPage';
    ```
  - siteContent 조회 줄을 `Promise.all`로 바꾸지 말고, **바로 다음 줄에** 추가한다. 기존 503 줄은 그대로 둔다.
    ```astro
    const front = await getHomeFrontPageData('ko');
    ```
  - body를 아래로 바꾼다.
    ```astro
    <div class="home-page">
      <HomeSplitHero locale={locale} homeIntro={homeIntro} todayCount={front.todayCount} />
      <HomeFrontPage locale={locale} {...front} />
    </div>
    ```

- [ ] **Step 5: CSS 추가** (`/* Typewriter word animation */` 주석 바로 위)

```css
/* Home: 오늘의 1면 */
.home-front {
  position: relative;
  max-width: 960px;
  margin: 0 auto;
  padding: 1.75rem 0 2.5rem;
}

.home-front::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: radial-gradient(circle, var(--color-text-primary) 1px, transparent 1.4px) 0 50% / 6px 4px repeat-x;
  opacity: 0.45;
}

.home-front-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 1rem;
}

.home-front-title {
  font-family: var(--font-heading);
  font-size: 1.1rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.home-front-more,
.home-front-term-link {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
}

.home-front-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
  gap: 1.75rem;
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
  font-size: clamp(1.2rem, 1rem + 1vw, 1.45rem);
  font-weight: 600;
  line-height: 1.35;
  letter-spacing: -0.035em;
  margin: 0.5rem 0;
}

.home-front-lead-title a,
.home-front-also a {
  color: var(--color-text-primary);
  text-decoration: none;
}

.home-front-lead-title a:hover,
.home-front-also a:hover {
  color: var(--color-accent);
}

.home-front-lead-excerpt {
  font-size: 0.9rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.home-front-meta {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.6rem;
}

.home-front-also {
  margin-top: 0.9rem;
  padding-top: 0.75rem;
  border-top: 1px dotted var(--color-border);
  font-size: 0.875rem;
}

.home-front-also span {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-right: 0.4rem;
}

.home-front-term {
  align-self: start;
  background: var(--color-bg-secondary);
  border-radius: 4px;
  padding: 1rem 1.15rem;
}

.home-front-term-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--color-accent);
}

.home-front-term-name {
  font-family: var(--font-heading);
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0.35rem 0 0.1rem;
}

.home-front-term-sub {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: 0.5rem;
}

.home-front-term-def {
  font-size: 0.85rem;
  line-height: 1.65;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 0.6rem;
}

@media (max-width: 767px) {
  .home-front {
    padding: 1.25rem 0 2rem;
  }

  .home-front-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .home-front-lead-excerpt {
    display: none;
  }
}
```

- [ ] **Step 6: 통과 확인**

Run: `node frontend/tests/home-front-page.test.cjs && node frontend/tests/public-error-cache-policy.test.cjs && node frontend/tests/home-hero-copy.test.cjs`
Expected: 셋 다 통과. 마지막 둘은 성공 시 출력이 없을 수 있으니 exit 0으로 확인한다.
`astro check`가 깨지지 않도록 이 Task에서 `HomeSplitHero.astro`의 Props에 `todayCount?: number;` **한 줄만** 미리 추가한다(사용은 Task 4). 그리고 이 파일도 Step 7 커밋에 포함한다.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/home/HomeFrontPage.astro frontend/src/components/home/HomeSplitHero.astro frontend/src/pages/ko/index.astro frontend/src/pages/en/index.astro frontend/src/styles/global.css frontend/tests/home-front-page.test.cjs
git commit -m "feat: add today's front page strip to home"
```

### Task 4: Hero V2 스타일

**Files:**
- Modify: `frontend/src/components/home/HomeSplitHero.astro`
- Modify: `frontend/src/styles/global.css` (`.home-split-hero*`, `.home-type-*`)
- Test: `frontend/tests/home-hero-v2.test.cjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/home-hero-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const hero = fs.readFileSync(path.join(src, 'components/home/HomeSplitHero.astro'), 'utf8');
const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

assert(/class="home-split-hero-wordmark"[^>]*>0to1log<span class="site-brand-dot" aria-hidden="true">\.<\/span>/.test(hero), 'wordmark gets the accent period');
assert(hero.includes('AI 뉴스와 용어를 기록하는 신문'), 'ko motto');
assert(/import \{ issueLabel, issueNumber \} from '\.\.\/\.\.\/lib\/issue\.js'/.test(hero), 'issue line uses lib/issue.js');
assert(/todayCount\?: number/.test(hero), 'hero accepts todayCount');
assert(/todayCount > 0 &&/.test(hero), '"오늘 N건" only when there are stories today');
assert(hero.includes('class="home-split-hero-issue"'), 'issue line element');

assert(rule('.home-split-hero-wordmark').includes('var(--color-text-primary)'), 'wordmark is ink');
assert(!/min-height:\s*calc\(100svh/.test(rule('.home-split-hero')), 'hero no longer fills the viewport (front strip follows)');
assert(/font-weight:\s*700/.test(rule('.home-split-hero-headline')), 'headline uses a loaded Hahmlet weight');
assert(rule('.home-type-target').includes('var(--color-accent)'), 'typed word is accent');
assert(/@media \(max-width: 639px\)\s*\{[^}]*\.home-split-hero-sub\s*\{\s*display:\s*none;/.test(css), 'sub copy hidden on small screens');
console.log('home-hero-v2.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/home-hero-v2.test.cjs`
Expected: FAIL. `wordmark gets the accent period`

- [ ] **Step 3: HomeSplitHero 수정**
  - Props의 `todayCount?: number;`는 Task 3에서 이미 추가됐다. 구조분해를 `const { locale, homeIntro, todayCount = 0 } = Astro.props;`로 바꾼다.
  - frontmatter 맨 위에 `import { issueLabel, issueNumber } from '../../lib/issue.js';`를 추가한다.
  - frontmatter 끝(`ctaSecondary` 다음)에 추가한다.
    ```ts
    const now = new Date();
    const issueText = issueLabel(locale, issueNumber(now));
    const dateText = now.toLocaleDateString(isKo ? 'ko-KR' : 'en-US', {
      timeZone: 'Asia/Seoul', month: 'long', day: 'numeric', weekday: 'long',
    });
    const motto = isKo ? 'AI 뉴스와 용어를 기록하는 신문' : 'A newspaper that keeps a record of AI news and terms';
    ```
  - `headline` 배열과 `kicker`는 그대로 둔다. `home-hero-copy` 테스트가 검사하는 부분이다.
  - 마크업에서 wordmark 줄부터 kicker 줄까지를 아래로 교체한다.
    ```astro
    <div class="home-split-hero-wordmark" aria-hidden="true">0to1log<span class="site-brand-dot" aria-hidden="true">.</span></div>
    <p class="home-split-hero-motto">{motto}</p>
    <p class="home-split-hero-issue">
      <span>{issueText}</span>
      <span>{dateText}</span>
      {todayCount > 0 && <b>{isKo ? `오늘 ${todayCount}건` : `${todayCount} today`}</b>}
    </p>
    <p class="home-split-hero-kicker">{kicker}</p>
    ```

- [ ] **Step 4: Hero CSS 수정**
  - `.home-split-hero`: `min-height: calc(100svh - 3rem);`를 삭제하고, `padding`을 `clamp(2.5rem, 9vh, 5.5rem) 1.25rem 2.5rem`으로 바꾼다.
  - `@media (max-width: 639px) { .home-split-hero { padding-top: 2.5rem; } }`는 `padding-top: 1.75rem;`으로 바꾼다.
  - `.home-split-hero-wordmark`:
    - `letter-spacing: 0.08em;` → `-0.03em;`
    - `color: var(--color-accent);` → `var(--color-text-primary);`
    - `margin-bottom: 2.5rem;` → `0.6rem;`
    - `font-size: 2.5rem;` → `3rem;`
    - 768px 이상 media의 `3.75rem` → `4.5rem`
  - `.home-split-hero-kicker` 바로 위에 추가한다.
    ```css
    .home-split-hero-motto {
      font-size: 0.8rem;
      color: var(--color-text-muted);
      margin-bottom: 0.9rem;
    }

    .home-split-hero-issue {
      display: inline-flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 0.25rem 0.75rem;
      font-size: 0.75rem;
      color: var(--color-text-secondary);
      padding: 0.35rem 0;
      border-top: 1px solid var(--color-border);
      border-bottom: 1px solid var(--color-border);
      margin-bottom: 1.5rem;
    }

    .home-split-hero-issue b {
      color: var(--color-accent);
      font-weight: 600;
    }
    ```
  - `.home-split-hero-headline`:
    - `font-size: clamp(2.5rem, 6vw, 3.75rem);` → `clamp(1.55rem, 1rem + 2.6vw, 2.4rem);`
    - `font-weight: 800;` → `700;`
    - `letter-spacing: -0.02em;` → `-0.04em;`
    - `line-height: 1.2;` → `1.3;`
    - `margin-bottom: 0.5rem;` → `0.75rem;`
  - `.home-type-target`의 color를 `var(--color-accent)`로 바꾼다. `.home-type-cursor`의 `background-color`도 `var(--color-accent)`로 바꾼다.
  - `.home-split-hero-cta` 규칙 위에 추가한다.
    ```css
    @media (max-width: 639px) {
      .home-split-hero-sub {
        display: none;
      }
    }
    ```

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/home-hero-v2.test.cjs && node frontend/tests/home-hero-copy.test.cjs && node frontend/tests/home-front-page.test.cjs && node frontend/tests/font-roles.test.cjs`
그다음 `cd frontend && npm run build`를 실행한다. 에러가 0이어야 한다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/home/HomeSplitHero.astro frontend/src/styles/global.css frontend/tests/home-hero-v2.test.cjs
git commit -m "feat: soft newsprint home hero with masthead, motto and issue line"
```

---

## Chunk 3: 검증과 문서

### Task 5: 검증 (컨트롤러)

- [ ] 전체 테스트: 기준선 PASS 목록 + 신규 4개(`home-front-select`, `home-front-query-budget`, `home-front-page`, `home-hero-v2`). FAIL은 기준선 23개의 부분집합이어야 한다.
- [ ] `npm run build`에서 에러 0.
- [ ] 브라우저에서 `/ko/`, `/en/`를 종이·다크 테마 × 1280px·375px로 확인한다.
  - 제호 마침표, 모토, 호수 줄
  - 오늘 기사가 있으면 "오늘 N건"이 보이는지
  - 모바일 제목이 3줄 정도인지, 소개 문장이 숨겨지는지
  - 1면의 머리기사·같은 날 한 줄·용어 링크가 동작하는지
  - en에서 용어 표시가 맞는지
- [ ] 응답 헤더 확인: `curl -sI http://localhost:4321/ko/`가 200이고, 캐시 헤더가 기존과 같은지(Vercel 헤더는 로컬에서 다를 수 있음. 미들웨어 결과만 확인).

### Task 6: 문서

- [ ] `vault/12-Journal-&-Decisions/2026-10-14-homepage-front-strip.md`에 결정 기록을 새로 쓴다. 내용은 3월 20일 결정의 연장선이다. Hero는 유지하고 "오늘의 1면"만 추가했고, 사용자 승인을 받았다. 이유와 데이터 비용(조회 2번, CDN 5분 캐시)도 적는다. 알려진 한계도 함께 적는다. 홈 캐시(s-maxage 300 + SWR 3600) 때문에 날짜, 호수, 오늘의 용어는 KST 자정 이후 최대 약 1시간 늦게 바뀔 수 있다. 오늘의 용어 후보는 즐겨찾기 용어를 slug 순으로 60개까지만 쓴다.
- [ ] 스펙 문서 §6의 "홈" 항목을 이 구조로 갱신한다.
- [ ] `vault/08-Design/Design-System.md`의 Header & Footer 절에서 홈 제호 설명을 갱신한다.
- [ ] `ACTIVE_SPRINT.md`에 REDESIGN-P3 항목과 증거를 추가한다.
- [ ] 이 계획 문서에 Status와 실행 결과를 추가한다.
- [ ] 커밋: `docs: record redesign phase 3 home front page`


---

## 실행 결과 (2026-10-14)

- 커밋: `23423a90` homeFront.js, `4fc2a107` 로더, `fc282cc9` 1면 컴포넌트, `8e9d9516` Hero V2, `82fc1d1c` 오늘의 용어 수정, `1fad2005` 위클리 라벨. 품질 리뷰 승인.
- 검증: 전체 테스트 61 PASS / 23 FAIL(신규 실패 0), `npm run build` 에러 0, 브라우저 /ko/ 종이·다크 × 1280·375px, /en/ 문구.
- **계획 대비 변경:** DB에 `is_favourite=true` 용어가 0개여서 즐겨찾기 60개 목록 대신 `발행 용어 개수(head) → termIndex(호수 % 개수) → range(i,i) 1행` 방식으로 바꿨다. `selectFrontPage`는 이제 선택된 `term`을 그대로 넘긴다. 머리기사 정렬에 `post_type` 보조 정렬을 추가했다.
- **교훈:** 계획 단계에서 조건(즐겨찾기)에 맞는 실데이터가 있는지 확인하지 않았다. 단위 테스트는 통과했지만 화면이 비었다. 데이터 조건이 들어가는 기능은 계획 때 실제 행 수를 확인한다.
