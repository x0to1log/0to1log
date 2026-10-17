# 블로그 목록 A(연재 칼럼) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** done (2026-10-17) — 실행 결과는 문서 끝 참조.

**Goal:** `/ko|en/blog/`를 "마스트헤드 → 필자 줄(+글 검색) → 최신 글(+연재 요약) → 연재(분야별 회차 목록, 2열) → 짧은 글" 한 단(최대 820px) 지면으로 바꾼다. 왼쪽 사이드바·모바일 서랍 토글·분야 탭·추천 4편·"모든 글" 무한 스크롤은 목록 페이지에서 없앤다. 분야 페이지와 글 상세는 그대로다.

**Architecture:**
- 순수 모듈 `lib/blogSerial.js`가 `buildBlogFront(posts, categories)` → `{ lead, series, shortNotes, total, latestAt }`, KST 날짜 `formatBlogDate`, `tech → study` 정규화 `normalizeBlogCategory`(lib/categories.ts 규칙 복사, 테스트로 양쪽 고정)를 맡는다.
- `BlogShell`에 `sidebar` prop(기본 `true`)을 더한다. 목록만 `sidebar={false}` → 사이드바·overlay를 렌더하지 않고 `.blog-shell--single`(최대 820px).
- 새 컴포넌트 2개: `components/blog/BlogFront.astro`(필자 줄·검색·최신 글·연재·짧은 글·검색 스크립트), `components/blog/BlogSerialItem.astro`(회차/짧은 글 한 줄 `li.blog-list-item` + 북마크 버튼).
- 목록 페이지 2개는 쿼리 그대로 + `buildBlogFront` + `<BlogFront>`만 남는다. `BlogFeaturedCard`와 i18n `blog.featured`·`blog.allPosts`는 지운다. 목록 전용 CSS(탭·섹션 헤더·추천 카드)는 Task 3에서 지운다.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-10-17-blog-list-serial-design]] — 구현 전에 반드시 읽는다.

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `frontend/src/pages/admin/pipeline-runs/*`, `frontend/src/lib/pageData/publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 **읽기만 하고 수정·stage하지 않는다**. 특히 `publicTermIndex.ts`는 이번 작업과 무관하며 절대 건드리지 않는다.
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- **백슬래시가 있는 파일은 Write/Edit 도구로만 작성한다.** Bash heredoc을 쓰면 백슬래시가 사라진다. 해당: 테스트 파일 전부(정규식), Task 3의 CSS 삭제 스크립트. 새 Astro 컴포넌트·페이지도 Write 도구로 만든다.
- Astro/JS 파일의 문자열에는 `\uXXXX` 이스케이프를 쓰지 않는다. `·`, `–`, `—`, `→`, 한글은 **문자 그대로** 쓴다(이 계획의 코드 블록도 전부 문자 그대로다). 특히 마스트헤드 `–도록: do log`의 첫 글자는 en dash(U+2013)다.
- 줄바꿈·인코딩
  - `frontend/src/pages/{ko,en}/blog/index.astro`는 작업 트리에서 **CRLF**, `BlogShell.astro`는 **CRLF/LF 혼합**이다. 셋 다 Read 후 **Write로 통째 교체**한다(LF로 저장됨). git 인덱스는 LF이고 `core.autocrlf=true`라 줄바꿈 차이는 diff에 나오지 않는다.
  - `frontend/src/i18n/index.ts`는 작업 트리 **CRLF**다. **Edit 도구로만** 고친다(Write·sed 금지).
  - `blog-category-badge-font.test.cjs`, `blog-title-fonts.test.cjs`는 **CRLF/LF 혼합**이다. Edit 도구로만 고친다.
  - `global.css`와 나머지 테스트는 LF다. CSS 규칙은 줄 번호가 아니라 셀렉터/주석으로 찾는다.
  - 기존 파일을 Write로 통째로 바꾸기 전에 반드시 Read로 먼저 읽는다(도구 요구사항).
- dev 서버(포트 4321)를 켠 채 `npm run build`를 돌리면 EPERM/EMFILE이 날 수 있다. 실패하면 재시도하지 말고 보고한다.

**지켜야 할 것**
- 목록 HTML은 CDN에 캐시된다(user-neutral). 새로 `Astro.locals.user`/세션 의존 렌더를 넣지 않는다. 북마크 버튼은 `data-bookmarked="false"`로 렌더하고 `content-status.ts`가 채운다(`public-list-personalization`이 고정).
- `content-status.ts`는 같은 `item_type:item_id`의 **첫 버튼**에만 상태를 적용하고, 읽음 표시는 버튼에서 가장 가까운 `.blog-list-item`에 붙인다. 그래서
  - 최신 글 블록에는 북마크 버튼을 두지 않는다(같은 글이 연재 회차에도 있다).
  - 회차·짧은 글 줄의 버튼은 반드시 그 `li.blog-list-item` 안에 있다.
- 분야 페이지(`pages/*/blog/category/[slug].astro`)는 `BlogListItem`, `.blog-list-batch`/`[data-blog-sentinel]` 무한 스크롤, `.blog-mobile-toolbar`를 계속 쓴다. 이 CSS·컴포넌트는 지우지 않는다. 글 상세(`pages/*/blog/[slug].astro`)는 `.blog-mono-tag`(BlogArticleLayout)와 사이드바를 쓴다.
- `BlogSidebar`는 자체적으로 분야·묶음 쿼리 2개를 날린다. 목록에서 빠지면서 쿼리가 2개 줄어드는 것은 의도다.
- 검색 스크립트는 번들 `<script>`다(`is:inline` 아님 → nonce 불필요, 미들웨어가 모듈 스크립트에 nonce를 붙인다).
- 테스트 기준선(2026-10-17, 계획 작성 시 측정): **PASS 79 / FAIL 20**.
  - 기준선 FAIL 20개: admin-live-preview, admin-v1-structure, article-deck-font, auth-prompt-library-preview, blog-section-heading-font, blog-sidebar-categories, blog-sidebar-layout, blog-title-fonts, comments-admin-delete-contract, content-feedback-contract, csp-inline-scripts, detail-rail-copy, handbook-detail-table-overflow, handbook-search-recognition, log-list-created-order, navigation-shell-copy, news-fact-pack-structure, product-detail-scenarios-theme, public-slug-visibility, sticky-reading-actions-structure.
  - 이번 작업과 닿는 기존 실패
    - `blog-sidebar-layout`: "Blog sidebar panel must use the shared card radius"(27행)에서 먼저 실패한다. 우리가 바꾸는 84–85행(툴바 단언)까지 가지 못한다. 작업 뒤에도 **같은 메시지**여야 한다.
    - `blog-title-fonts`: "Missing IBM Plex Sans font import: IBM+Plex+Sans"(18행)에서 먼저 실패한다. 셀렉터 목록만 바꾸고 작업 뒤에도 **같은 메시지**여야 한다.
    - `blog-section-heading-font`: 삭제되는 `.blog-section-header` 하나만 검사하던 테스트다. Task 3에서 새 섹션 제목(h2 3종) 검사로 다시 쓴다 → **FAIL → PASS**.
  - 완료 후 기대값: 신규 2개 PASS + `blog-section-heading-font` PASS → **PASS 82 / FAIL 19, 신규 FAIL 0**. 다른 세션 변경으로 숫자가 흔들릴 수 있으니 판정은 **이름 + 첫 오류 메시지 기준**으로 한다.

**현재 코드**
- `pages/{ko,en}/blog/index.astro`(196줄, CRLF). 두 파일은 locale·문구만 다르다.
  - 쿼리: `blog_posts` `id, title, slug, category, published_at, tags, reading_time_min, excerpt`, published, locale, `created_at desc`, limit 100 + `fetchCategories`. 오류 시 503 + `NewsprintNotice`.
  - 마크업: `BlogShell mode="index"`(사이드바) → `.blog-mobile-toolbar`(서랍 토글) → `h1.blog-masthead-title` + `p.blog-masthead-tagline` → `nav.blog-category-tabs` → `h2.blog-section-header`(추천 글) + `BlogFeaturedCard` 4개 → `h2.blog-section-header`(전체 글) + `BlogListItem` 10개씩 배치 + `[data-blog-sentinel]` → 빈 상태 `.blog-empty-state`.
  - 스크립트: `import '../../../scripts/bookmark'` + 무한 스크롤(IntersectionObserver).
- `BlogShell.astro`: 항상 `BlogSidebar` + `.blog-sidebar-overlay[data-sidebar-overlay]` + `.blog-main > .blog-main-inner`(최대 900px) + 선택적 TOC 슬롯. `sidebarPosts`·`totalCount`가 필수 prop이다.
- `BlogFeaturedCard.astro`: 목록 두 페이지만 쓴다. `BlogListItem.astro`(`<article class="blog-list-item">`): 분야 페이지가 쓴다(유지).
- `lib/categories.ts` `normalizeCategorySlug`: `tech → study`. node `.mjs` 테스트에서 `.ts`를 import할 수 없다.
- i18n `blog.featured`·`blog.allPosts`: 목록 두 페이지만 쓴다. `blog.allPostsCount`는 `BlogSidebar`가 쓴다(유지).
- CSS(`global.css`): `/* ── Blog Masthead Tagline + Category Tabs ── */` 아래 `.blog-masthead-tagline` 다음에 `.blog-category-tabs…`(+639px 미디어) → `/* ── Section Headers … */ .blog-section-header` → `/* ── Featured Cards ── */ .blog-featured-grid … .blog-featured-card-tags`가 이어지고, 그 바로 뒤가 `.blog-category-badge {`다(목록 전용 173줄이 한 덩어리). `.blog-list-item`(점선, hover 시 음수 margin)은 분야 페이지와 공유한다.
- 운영 데이터(2026-10-17): KO 발행 11편 — 학습 노트(study) 5, 프로젝트 기록(project) 5, 작업 메모(work-note, sub) 1. 커리어 생각(career)은 0편 → 연재 아님. 분야 설명(`description_*`)은 전부 null. **EN 발행 글은 0편** → EN 목록은 빈 상태("Coming Soon")가 정상이다. 가장 최근 글은 작업 메모(2026-03-11 15:26 UTC = KST 3월 12일)라 최신 글 블록은 짧은 글의 글이다. 학습 노트 1화(03-10 18:42 UTC)는 KST로 3월 11일이다.
- 글꼴: `--font-blog-heading`=Hahmlet(600/700만 로드), `--font-masthead`=Newsreader(500만 로드), `--font-blog-ui`=Pretendard.

**스펙 해석(실행자가 임의로 바꾸지 않는다)**
- 컴포넌트는 `BlogFront`(섹션 전부 + 검색 스크립트)와 `BlogSerialItem`(한 줄) 2개로 나눈다. 회차 줄과 짧은 글 줄이 같은 북마크 계약을 갖도록 한 컴포넌트에 둔다.
- 필자 줄·검색은 글이 1편 이상일 때만 보인다(`front.total > 0`이면 `BlogFront`, 0이면 현행 빈 상태, 쿼리 오류면 현행 오류 안내). 최신 글 섹션은 추가로 `front.lead &&`로 감싼다(글은 있는데 `published_at`이 전부 null이면 `lead`가 null).
- `latestAt`이 null이면 필자 줄은 "Amy · N편"까지만 쓴다.
- EN 편수는 단수를 구분한다: "1 post" / "N posts"(KO는 항상 "N편").
- 최신 글은 분야와 무관하게 `published_at`이 가장 늦은 글이다(지금은 짧은 글). 분야 라벨이 없으면(미분류) 라벨은 "최신"/"Latest"만. 연재가 0개면 오른쪽 요약을 렌더하지 않고 `blog-lead--solo`(1단)로 둔다.
- 날짜 없는 글은 회차·짧은 글 모두 맨 뒤(같은 조건끼리는 입력 순서 유지 = 쿼리의 `created_at desc`). 날짜 칸은 빈 `span`으로 둔다(격자 유지).
- 날짜 표기는 `formatBlogDate`(`toLocaleDateString(…, { timeZone: 'Asia/Seoul', month: 'short', day: 'numeric' })`) 하나로 통일한다: KO "3월 11일", EN "Mar 11". 컴포넌트에서 `toLocaleDateString`을 직접 쓰지 않는다.
- 분야 라벨은 DB `label_{ko|en}`, 없으면 slug(현행 `BlogListItem`과 같은 규칙), 분야가 null이면 라벨 없음. 점 색은 DB `color`, 없으면 `var(--color-border)`. 점 라벨은 기존 `.blog-category-badge`(7단계 B안: 색은 점에만)를 재사용한다.
- 검색: 제목은 `.blog-serial-title`의 `textContent`로 비교한다(data 속성에 제목을 복제하지 않는다). 보이는 연재가 0이면 `.blog-series-grid`도 숨긴다(빈 격자 여백 방지). 페이지 복원으로 입력값이 남아 있으면 초기화 때 바로 필터한다.
- 회차 줄은 `display: grid`라 UA의 `[hidden]` 규칙을 이긴다 → `.blog-front [hidden] { display: none; }`를 블록 끝에 둔다. 공유 `.blog-list-item:hover`의 음수 margin·배경은 `.blog-serial-list` 안에서 끈다(375px 가로 넘침 방지).
- 테스트 갱신 범위
  - `blog-category-badge-font`: FeaturedCard 읽기·단언 2줄만 지운다(나머지 유지).
  - `blog-detail-sidebar-structure`: 목록 `mode="index"` 단언 → `sidebar={false}` 단언, 분야 페이지 `mode="index"` 유지 단언을 더한다.
  - `blog-title-fonts`: 셀렉터 목록에서 `.blog-featured-card-title`을 `.blog-serial-title`로 바꾼다(기존 실패 메시지 유지).
  - `blog-section-heading-font`: Task 3에서 새 h2 3종(`.blog-lead-title`, `.blog-series-title`, `.blog-short-notes-title`)이 `var(--font-blog-heading)` + 700인지 검사하도록 다시 쓴다.
- CSS 정리 범위(Task 3): 탭·섹션 헤더·추천 카드 173줄만. `.blog-list-batch[hidden]`·`.blog-scroll-sentinel`·`.blog-mobile-toggle`·`.blog-mobile-toolbar`·`.blog-list-section`·`.blog-mono-tag`·`.blog-category-badge`는 분야/상세 페이지가 쓰므로 남긴다.

**계획 사전 검증(작성 시 scratchpad 복제본에서 수행)**
- `frontend/`+`supabase/` 복제본(node_modules는 junction)에 Task 1–3을 이 문서의 코드 그대로 적용했다. 복제본 기준선은 실제 repo와 이름·첫 오류 메시지 기준 동일(PASS 79 / FAIL 20).
- 각 "실패 확인" Step은 적힌 메시지로 실패, 통과 확인 Step은 PASS. 전체 **PASS 82 / FAIL 19**, 실패 19개의 첫 오류 메시지가 기준선과 동일. 바뀐 이름은 `blog-list-serial`·`blog-serial`(신규 PASS), `blog-section-heading-font`(FAIL→PASS)뿐.
- `astro build` "Complete!"(Task 2 후, Task 3 후 두 번).
- dev 서버(운영 데이터, 포트 4410) 렌더
  - `/ko/blog/` 200: 사이드바·overlay·서랍 토글 없음, `div.blog-shell.blog-shell--single`. 필자 줄 "Amy · 11편 · 마지막 글 3월 12일". 최신 글 "작업 메모 · 최신 / 요즘은 기능보다 읽는 흐름을 더 자주 보게 된다 / 요약 / 3월 12일"(북마크 없음), 요약 "2 개의 연재 / 학습 노트 5편 / 프로젝트 기록 5편". 연재 학습 노트 1화 "LLM은 어떻게 답을 만들까…"(3월 11일)…5화 "AI Agent는…", 프로젝트 기록 1화 "AI 뉴스 서비스를 학습 루틴으로…"…5화. 짧은 글 1줄(작업 메모). 북마크 버튼 11 = `li.blog-list-item` 11. 스크립트 20개 전부 nonce.
  - `/en/blog/` 200: 빈 상태 "Coming Soon"(EN 글 0편). `/ko/blog/category/study/` 200(사이드바·토글 유지, `div.blog-shell`만), `/en/blog/category/study/` 200, 글 상세 `/ko/blog/importance-of-flow-over-features/` 200(사이드바 유지). 서버 로그 오류 0.
- 브라우저(Playwright): 1200px — 본문 820px, 최신 글 `540px 200px`, 연재 `370px 370px`, 가로 넘침 0. 검색 "rag" → 2줄·연재 1·짧은 글/최신 글 숨김, "흐름" → 짧은 글만·연재 격자 숨김, "zzzz" → `#blog-search-empty`만, 지우기 → 11줄·연재 2·최신 글 복귀, `blogSearchReady="true"`. 375px — 검색 입력 전체 폭(320px), 최신 글·연재 1단, 화면 밖으로 나가는 요소 0.

---

## Task 1: 연재 칼럼 순수 함수 (TDD)

**Files:**
- Create: `frontend/src/lib/blogSerial.js`
- Test: `frontend/tests/blog-serial.test.mjs`(새 파일)

- [ ] **Step 1: 실패하는 테스트 작성** (Write 도구로)

```js
// frontend/tests/blog-serial.test.mjs
// Blog list A (serial column): latest post, series per main field, episode order, short notes, KST dates.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { buildBlogFront, normalizeBlogCategory, formatBlogDate } = await import(
  pathToFileURL(path.join(here, '../src/lib/blogSerial.js')).href
);

// tech -> study, same rule as normalizeCategorySlug() in lib/categories.ts (node cannot import the .ts module)
assert.equal(normalizeBlogCategory('tech'), 'study');
assert.equal(normalizeBlogCategory('project'), 'project');
assert.equal(normalizeBlogCategory(null), null);
assert.equal(normalizeBlogCategory(''), null);
const categoriesTs = fs.readFileSync(path.join(here, '../src/lib/categories.ts'), 'utf8');
assert(
  categoriesTs.includes("return category === 'tech' ? 'study' : category;"),
  'lib/categories.ts normalizeCategorySlug changed: update normalizeBlogCategory in lib/blogSerial.js too',
);

const cat = (slug, group_slug, sort_order, extra = {}) => ({
  slug, group_slug, sort_order, is_visible: true, label_ko: slug, label_en: slug, ...extra,
});
// scrambled on purpose: series order must come from sort_order, not input order
const CATS = [
  cat('project', 'main', 1),
  cat('work-note', 'sub', 0),
  cat('study', 'main', 0),
  cat('career', 'main', 2),
  cat('daily', 'sub', 1),
  cat('secret', 'main', 3, { is_visible: false }),
  cat('hidden-note', 'sub', 2, { is_visible: false }),
  cat('archive', 'legacy', 0),
];
const post = (title, category, published_at) => ({ id: `id-${title}`, title, slug: title, category, published_at });
const POSTS = [
  post('note', 'work-note', '2026-03-11T15:26:58.354+00:00'),
  post('llm', 'tech', '2026-03-10T18:42:39.552+00:00'),
  post('cost', 'study', '2026-03-11T04:32:08.018+00:00'),
  post('undated', 'study', null),
  post('solo', 'project', '2026-03-10T09:42:35.438+00:00'),
  post('routine', 'project', '2026-03-10T09:37:44.626+00:00'),
  post('hidden-main', 'secret', '2026-03-12T00:00:00+00:00'),
  post('old', 'archive', '2026-03-09T00:00:00+00:00'),
  post('unknown', 'ghost', '2026-03-08T00:00:00+00:00'),
  post('walk', 'daily', '2026-03-01T00:00:00+00:00'),
  post('nocat', null, '2026-03-13T00:00:00+00:00'),
  post('hidden-sub', 'hidden-note', '2026-03-07T00:00:00+00:00'),
  post('broken-date', 'study', 'not a date'),
];
const titles = (list) => list.map((p) => p.title);

const front = buildBlogFront(POSTS, CATS);

// lead: newest published_at of all posts (any field); undated/invalid never lead
assert.equal(front.lead.title, 'nocat');
assert.equal(front.latestAt, '2026-03-13T00:00:00+00:00');
assert.equal(front.total, 13);

// series: visible main fields with posts, by sort_order (career has no posts, secret is hidden)
assert.deepEqual(front.series.map((s) => s.category.slug), ['study', 'project']);
// episodes: published_at ascending, undated last (input order kept among them)
assert.deepEqual(titles(front.series[0].posts), ['llm', 'cost', 'undated', 'broken-date']);
assert.deepEqual(titles(front.series[1].posts), ['routine', 'solo']);
assert.equal(front.series[0].posts[0].category, 'study', 'legacy tech post is normalized into the study series');
assert.equal(POSTS[1].category, 'tech', 'input posts are not mutated');

// short notes: visible sub fields (newest first), then everything else (newest first):
// hidden fields of any group, other groups, slugs missing from the DB, posts without a category
assert.deepEqual(titles(front.shortNotes), ['note', 'walk', 'nocat', 'hidden-main', 'old', 'unknown', 'hidden-sub']);
const placed = front.series.reduce((n, s) => n + s.posts.length, 0) + front.shortNotes.length;
assert.equal(placed, front.total, 'every post is listed exactly once outside the lead');

// the lead stays in its own series (intended duplicate)
const leadInSeries = buildBlogFront([post('a', 'study', '2026-03-01T00:00:00Z'), post('b', 'study', '2026-03-02T00:00:00Z')], CATS);
assert.equal(leadInSeries.lead.title, 'b');
assert.deepEqual(titles(leadInSeries.series[0].posts), ['a', 'b']);

// posts exist but none has published_at -> lead/latestAt null while total > 0 (the page guards with `front.lead &&`)
const undatedOnly = buildBlogFront([post('x', 'study', null)], CATS);
assert.equal(undatedOnly.lead, null);
assert.equal(undatedOnly.latestAt, null);
assert.equal(undatedOnly.total, 1);
assert.deepEqual(titles(undatedOnly.series[0].posts), ['x']);

// empty input
const empty = { lead: null, series: [], shortNotes: [], total: 0, latestAt: null };
assert.deepEqual(buildBlogFront([], []), empty);
assert.deepEqual(buildBlogFront(null, null), empty);
assert.deepEqual(titles(buildBlogFront([post('lone', 'study', null)], []).shortNotes), ['lone'], 'no categories: everything is a short note');

// KST dates: 18:42 UTC on Mar 10 is Mar 11 in Seoul
assert.equal(formatBlogDate('2026-03-10T18:42:39.552+00:00', 'ko'), '3월 11일');
assert.equal(formatBlogDate('2026-03-10T18:42:39.552+00:00', 'en'), 'Mar 11');
assert.equal(formatBlogDate('2026-03-10T09:42:35.438+00:00', 'ko'), '3월 10일');
assert.equal(formatBlogDate(null, 'ko'), '');
assert.equal(formatBlogDate('not a date', 'en'), '');

console.log('blog-serial.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/blog-serial.test.mjs`
Expected: FAIL `ERR_MODULE_NOT_FOUND`(`blogSerial.js` 없음).

- [ ] **Step 3: `blogSerial.js` 작성** (Write 도구로. `→`는 문자 그대로)

```js
// frontend/src/lib/blogSerial.js
// Pure helpers for the blog list (A: serial column). No I/O.
// Series = visible fields of the 'main' group (sort_order), episodes in published_at order.
// Short notes = visible 'sub' fields, then every post that fits nowhere else (both newest first).

/**
 * Same rule as normalizeCategorySlug() in lib/categories.ts ('tech' → 'study').
 * Copied because node tests cannot import the .ts module; blog-serial.test.mjs pins both sides.
 */
export function normalizeBlogCategory(category) {
  if (!category) return null;
  return category === 'tech' ? 'study' : category;
}

function timeOf(value) {
  if (!value) return null;
  const t = Date.parse(value);
  return Number.isNaN(t) ? null : t;
}

// Undated posts (published_at null or unparsable) always sort last; ties keep input order.
function byDate(direction) {
  return (a, b) => {
    const ta = timeOf(a.published_at);
    const tb = timeOf(b.published_at);
    if (ta === null || tb === null) return (ta === null ? 1 : 0) - (tb === null ? 1 : 0);
    return direction * (ta - tb);
  };
}

const oldestFirst = byDate(1);
const newestFirst = byDate(-1);

/**
 * @param {Array<{id: string, title: string, slug: string, category?: string|null, published_at?: string|null}>} posts
 * @param {Array<{slug: string, group_slug: string, sort_order?: number, is_visible: boolean}>} categories
 * @returns {{ lead: object|null, series: Array<{category: object, posts: object[]}>, shortNotes: object[], total: number, latestAt: string|null }}
 *   Posts come back as shallow copies with the normalized category.
 *   lead = newest dated post of any field (null when no post has a date); it also stays in its own series.
 *   Every post appears exactly once in series + shortNotes.
 */
export function buildBlogFront(posts, categories) {
  const list = (Array.isArray(posts) ? posts : []).map((post) => ({ ...post, category: normalizeBlogCategory(post.category) }));
  const cats = Array.isArray(categories) ? categories : [];

  const dated = list.filter((post) => timeOf(post.published_at) !== null);
  const lead = dated.length > 0 ? dated.sort(newestFirst)[0] : null;

  const mainCats = cats
    .filter((c) => c.group_slug === 'main' && c.is_visible)
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const series = mainCats
    .map((category) => ({ category, posts: list.filter((post) => post.category === category.slug).sort(oldestFirst) }))
    .filter((s) => s.posts.length > 0);

  const mainSlugs = new Set(mainCats.map((c) => c.slug));
  const subSlugs = new Set(cats.filter((c) => c.group_slug === 'sub' && c.is_visible).map((c) => c.slug));
  const notes = list.filter((post) => subSlugs.has(post.category)).sort(newestFirst);
  const rest = list.filter((post) => !mainSlugs.has(post.category) && !subSlugs.has(post.category)).sort(newestFirst);

  return { lead, series, shortNotes: [...notes, ...rest], total: list.length, latestAt: lead ? lead.published_at : null };
}

/** "3월 11일" / "Mar 11" in KST (the server runs in UTC). '' when undated. */
export function formatBlogDate(value, locale) {
  const t = timeOf(value);
  if (t === null) return '';
  return new Date(t).toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US', {
    timeZone: 'Asia/Seoul',
    month: 'short',
    day: 'numeric',
  });
}
```

- [ ] **Step 4: 통과 확인** — `node frontend/tests/blog-serial.test.mjs` → `blog-serial.test.mjs passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/blogSerial.js frontend/tests/blog-serial.test.mjs
git commit -m "feat: add blog serial column helpers"
```

---

## Task 2: 목록 화면 (Shell sidebar prop·컴포넌트·페이지·CSS·테스트 갱신·FeaturedCard 삭제)

**Files:**
- Create: `frontend/src/components/blog/BlogFront.astro`, `frontend/src/components/blog/BlogSerialItem.astro`
- Modify:
  - `frontend/src/components/blog/BlogShell.astro`(전체 교체)
  - `frontend/src/pages/ko/blog/index.astro`, `frontend/src/pages/en/blog/index.astro`(전체 교체)
  - `frontend/src/i18n/index.ts`(**CRLF → Edit 도구만**, 4줄 삭제)
  - `frontend/src/styles/global.css`(새 블록 추가만. 옛 CSS 삭제는 Task 3)
  - 테스트: `blog-v2.test.cjs`, `blog-bookmark-card-contract.test.cjs`, `blog-detail-sidebar-structure.test.cjs`, `blog-mobile-sidebar-structure.test.cjs`, `blog-category-badge-font.test.cjs`(혼합 EOL → Edit만), `blog-sidebar-layout.test.cjs`
- Test: `frontend/tests/blog-list-serial.test.cjs`(새 파일. Task 3에서 단언을 더한다)
- Delete (`git rm`): `frontend/src/components/blog/BlogFeaturedCard.astro`

- [ ] **Step 0: 상태·사용처 확인**

Run:
```bash
git status --short -- frontend/src/components/blog frontend/src/pages/ko/blog frontend/src/pages/en/blog frontend/src/i18n/index.ts frontend/src/styles/global.css frontend/tests/blog-v2.test.cjs frontend/tests/blog-bookmark-card-contract.test.cjs frontend/tests/blog-detail-sidebar-structure.test.cjs frontend/tests/blog-mobile-sidebar-structure.test.cjs frontend/tests/blog-category-badge-font.test.cjs frontend/tests/blog-sidebar-layout.test.cjs
grep -rn "BlogFeaturedCard\|blog\.featured\|'blog\.allPosts'\|blog-category-tabs" frontend/src --include=*.astro --include=*.ts --include=*.js
```
Expected: status 출력 없음. grep은 목록 두 페이지(`pages/{ko,en}/blog/index.astro`)와 `i18n/index.ts`의 키 4줄만 나온다. 다른 파일이 나오면 멈추고 보고한다.

- [ ] **Step 1: 실패하는 테스트 작성·갱신**

`frontend/tests/blog-list-serial.test.cjs`(Write 도구로):

```js
// frontend/tests/blog-list-serial.test.cjs
// Blog list A (serial column): no sidebar, byline + search, latest post, series, short notes.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// shell: sidebar prop (default true). Only the list passes false; category and detail pages keep the sidebar.
const shell = read('components/blog/BlogShell.astro');
assert(shell.includes('sidebar?: boolean;') && shell.includes('sidebar = true,'), 'shell: sidebar prop defaults to true');
assert(/\{sidebar && \(\s*<>\s*<BlogSidebar[\s\S]*?data-sidebar-overlay><\/div>\s*<\/>\s*\)\}/.test(shell), 'shell: sidebar + overlay only when sidebar');
assert(shell.includes("class:list={['blog-shell', { 'blog-shell--single': !sidebar }]}"), 'shell: single-column modifier');
for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro', 'pages/ko/blog/category/[slug].astro', 'pages/en/blog/category/[slug].astro']) {
  assert(!read(p).includes('sidebar={false}'), `${p} keeps the sidebar`);
}

// pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/blog/index.astro`);
  assert(page.includes(`<BlogShell locale="${locale}" sidebar={false}>`), `${locale}: list renders without the sidebar`);
  for (const gone of ['BlogFeaturedCard', 'BlogListItem', 'data-blog-sentinel', 'blog-category-tabs', 'blog-mobile-toolbar', 'data-sidebar-toggle', 'buildBlogSidebarDataset', 'IntersectionObserver', "'blog.featured'", "'blog.allPosts'"]) {
    assert(!page.includes(gone), `${locale}: ${gone} removed`);
  }
  assert(page.includes(".select('id, title, slug, category, published_at, tags, reading_time_min, excerpt')") && page.includes(".order('created_at', { ascending: false })") && page.includes('.limit(100)'), `${locale}: posts query unchanged`);
  assert(page.includes('const front = buildBlogFront(posts, dbCategories);'), `${locale}: front built by the pure module`);
  assert(page.includes(`<BlogFront locale="${locale}" front={front} categories={dbCategories} />`), `${locale}: renders BlogFront`);
  assert(page.includes(') : front.total > 0 ? (') && page.includes('<div class="blog-empty-state">'), `${locale}: empty state when there are no posts`);
  assert(page.includes("import '../../../scripts/bookmark';"), `${locale}: bookmark + content-status hydration`);
  assert(page.includes('<h1 class="blog-masthead-title">–도록: do log</h1>') && page.includes('class="blog-masthead-tagline"'), `${locale}: masthead kept`);
}
assert(read('pages/ko/blog/index.astro').includes('<h2>준비 중</h2>') && read('pages/en/blog/index.astro').includes('<h2>Coming Soon</h2>'), 'empty state copy kept');
assert(!fs.existsSync(path.join(src, 'components/blog/BlogFeaturedCard.astro')), 'BlogFeaturedCard deleted');
const i18n = read('i18n/index.ts');
assert(!i18n.includes("'blog.featured'") && !i18n.includes("'blog.allPosts'") && i18n.includes("'blog.allPostsCount'"), 'unused i18n keys removed (sidebar count key kept)');

// front: byline, lead, series, short notes, search
const front = read('components/blog/BlogFront.astro');
for (const s of ["'마지막 글'", "'Latest'", "'글 검색'", "'Search posts'", "'최신'", "'개의 연재'", "'series'", "'짧은 글'", "'Short notes'", "'일치하는 글이 없어요'", "'No posts match'", '`${n}편`', "`${n} post${n === 1 ? '' : 's'}`", '`${label} ${s.posts.length}편`', '`${label} · ${s.posts.length}`']) {
  assert(front.includes(s), `front copy: ${s}`);
}
assert(front.includes('<div class="blog-byline">') && front.includes('<strong>Amy</strong> · {postsLabel(front.total)}{latest && ` · ${copy.latest} ${latest}`}'), 'byline: Amy · N · latest date');
assert(front.includes('<input type="search" id="blog-search" class="blog-search-input" placeholder={copy.search} aria-label={copy.search} autocomplete="off" />'), 'search input');

assert(front.includes('{front.lead && ('), 'lead guarded: posts without published_at give lead null while total > 0');
const leadAt = front.indexOf("<section class:list={['blog-lead'");
const lead = front.slice(leadAt, front.indexOf('</section>', leadAt));
assert(leadAt > 0 && lead.includes('<h2 class="blog-lead-title">'), 'lead title is an h2');
assert(lead.includes('{front.lead.excerpt && <p class="blog-lead-excerpt">{front.lead.excerpt}</p>}'), 'lead excerpt only when present');
assert(!lead.includes('newsprint-bookmark-icon') && !lead.includes('<BlogSerialItem'), 'no bookmark button in the lead block');
assert(lead.includes("{ 'blog-lead--solo': front.series.length === 0 }") && lead.includes('{front.series.length > 0 && ('), 'series summary only with series');

assert(front.includes('<article class="blog-series">') && front.includes('<h2 class="blog-series-title"><a href={`/${locale}/blog/category/${category.slug}/`}>{label}</a></h2>'), 'series heading links to the field page');
assert(front.includes('{desc && <p class="blog-series-desc">{desc}</p>}'), 'series description only when present');
assert(front.includes('<BlogSerialItem locale={locale} post={post} episode={i + 1} />'), 'episodes numbered from 1');
assert(front.includes('{front.shortNotes.length > 0 && (') && front.includes('<h2 class="blog-short-notes-title">{copy.short}</h2>'), 'short notes h2, hidden when empty');
assert((front.match(/<ol class="blog-serial-list">/g) || []).length === 2, 'series and short notes are ordered lists');
assert(front.includes('<p id="blog-search-empty" class="blog-search-empty" role="status" aria-live="polite" hidden>{copy.empty}</p>'), 'no-results status');

// search script: bundled (no nonce needed), guarded, debounced, restores everything when cleared
assert(!front.includes('is:inline'), 'search script is bundled');
for (const s of [
  "input.dataset.blogSearchReady === 'true'",
  "input.dataset.blogSearchReady = 'true';",
  "document.addEventListener('astro:page-load', initBlogSearch);",
  'timer = window.setTimeout(apply, 150);',
  "front.querySelectorAll<HTMLElement>('.blog-series, .blog-short-notes')",
  "item.querySelector('.blog-serial-title')?.textContent",
  'item.hidden = !match;',
  'group.hidden = visible === 0;',
  'lead.hidden = query.length > 0;',
  'empty.hidden = !query || shown > 0;',
]) {
  assert(front.includes(s), `search script: ${s}`);
}

// row: li.blog-list-item with the bookmark button inside (content-status marks the closest .blog-list-item read)
const item = read('components/blog/BlogSerialItem.astro');
const li = item.slice(item.indexOf('<li class="blog-list-item">'), item.indexOf('</li>'));
assert(li.length > 0 && li.includes('class="newsprint-bookmark-icon"') && li.includes('data-item-id={post.id}') && li.includes('data-item-type="blog"') && li.includes('data-bookmarked="false"'), 'bookmark contract inside li.blog-list-item');
assert(!item.includes('blog-list-item-icon'), 'no icon slot');
assert(item.includes('`${episode}화`') && item.includes('`Ep. ${episode}`'), 'episode labels');
assert(item.includes('<a class="blog-serial-title" href={`/${locale}/blog/${post.slug}/`}>{post.title}</a>'), 'title link');
assert(item.includes('style={`--cat-color: ${categoryColor || \'var(--color-border)\'}`}'), 'short note dot label uses the DB color');

// KST everywhere: components only format through formatBlogDate
assert(read('lib/blogSerial.js').includes("timeZone: 'Asia/Seoul'"), 'dates in KST');
for (const [name, f] of [['BlogFront', front], ['BlogSerialItem', item]]) {
  assert(!f.includes('toLocaleDateString') && f.includes('formatBlogDate('), `${name}: dates via formatBlogDate`);
}

// CSS
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
assert(/max-width:\s*820px/.test(rule('.blog-shell--single .blog-main-inner')), 'single column up to 820px');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-byline')) && /border-bottom:\s*1px solid var\(--color-text-primary\)/.test(rule('.blog-byline')), 'byline: 2px ink rule above, 1px below');
assert(/grid-template-columns:\s*minmax\(0, 1fr\) 200px/.test(rule('.blog-lead')), 'lead: 1fr : 200px');
assert(/border-left:\s*1px solid var\(--color-border\)/.test(rule('.blog-lead-aside')), 'series summary has a left rule');
assert(/grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/.test(rule('.blog-series-grid')), 'series: 2 columns');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-series-head')), 'series head: 2px ink rule');
for (const sel of ['.blog-lead-title', '.blog-series-title', '.blog-short-notes-title']) {
  assert(rule(sel).includes('var(--font-blog-heading)') && /font-weight:\s*700/.test(rule(sel)), `${sel}: Hahmlet 700`);
}
assert(rule('.blog-serial-ep').includes('var(--font-masthead)'), 'episode number in Newsreader');
assert(/font-weight:\s*600/.test(rule('.blog-serial-title')), 'episode title 600');
assert(rule('.blog-front [hidden]').includes('display: none'), 'search hides grid rows (display: grid beats the UA [hidden] rule)');
const mobileAt = css.indexOf('/* Blog list A: mobile */');
assert(mobileAt > 0, 'blog list mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.blog-byline\s*\{[^}]*flex-wrap:\s*wrap/.test(mobile), 'mobile: byline wraps');
assert(/\.blog-search-input\s*\{[^}]*width:\s*100%/.test(mobile), 'mobile: search on its own full-width line');
assert(/\.blog-lead\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: lead one column');
assert(/\.blog-series-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: series one column');

console.log('blog-list-serial.test.cjs passed');
```

`blog-v2.test.cjs`(Edit 도구로, 2곳):
1. ```js
   for (const p of ['components/blog/BlogFeaturedCard.astro', 'components/blog/BlogListItem.astro']) {
   ```
   →
   ```js
   for (const p of ['components/blog/BlogSerialItem.astro', 'components/blog/BlogListItem.astro']) {
   ```
2. ```js
   const feat = rule('.blog-featured-card');
   assert(/border:\s*none/.test(feat) && /border-bottom:\s*1px dotted var\(--color-border\)/.test(feat), 'featured posts are dotted column entries');
   assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.blog-list-item')), 'list items separated by dotted lines');

   // 폴더 카드 줄 → 탭
   for (const p of ['pages/ko/blog/index.astro', 'pages/en/blog/index.astro']) {
     const f = read(p);
     assert(f.includes('class="blog-category-tabs"'), `${p} renders category tabs`);
   ```
   →
   ```js
   assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.blog-list-item')), 'list items separated by dotted lines');

   // 폴더 카드 줄 → 탭 → 연재 칼럼(2026-10-17): 탭·추천 카드 없이 BlogFront
   for (const p of ['pages/ko/blog/index.astro', 'pages/en/blog/index.astro']) {
     const f = read(p);
     assert(!f.includes('blog-category-tabs') && f.includes('<BlogFront '), `${p} renders the serial column instead of tabs`);
   ```
   (루프의 나머지 3줄, en 태그라인, 모바일 드로어 배경 단언은 그대로 둔다.)

`blog-bookmark-card-contract.test.cjs`(Edit 도구로, 2곳):
1. ```js
   const featuredCard = read('frontend/src/components/blog/BlogFeaturedCard.astro');
   const listItem = read('frontend/src/components/blog/BlogListItem.astro');
   const enIndex = read('frontend/src/pages/en/blog/index.astro');
   const koIndex = read('frontend/src/pages/ko/blog/index.astro');
   const bookmarkScript = read('frontend/src/scripts/bookmark.ts');

   assertIncludes(featuredCard, 'isBookmarked?: boolean;', 'blog featured bookmark prop');
   assertIncludes(featuredCard, 'itemId?: string;', 'blog featured bookmark item id prop');
   assertIncludes(featuredCard, "itemType?: 'blog';", 'blog featured bookmark item type prop');
   assertIncludes(featuredCard, 'newsprint-bookmark-icon', 'blog featured bookmark button markup');
   assertIncludes(featuredCard, 'data-item-id={itemId}', 'blog featured bookmark item id binding');
   assertIncludes(featuredCard, 'data-item-type={itemType}', 'blog featured bookmark item type binding');
   ```
   →
   ```js
   const serialItem = read('frontend/src/components/blog/BlogSerialItem.astro');
   const listItem = read('frontend/src/components/blog/BlogListItem.astro');
   const enIndex = read('frontend/src/pages/en/blog/index.astro');
   const koIndex = read('frontend/src/pages/ko/blog/index.astro');
   const bookmarkScript = read('frontend/src/scripts/bookmark.ts');

   // list page rows (series episodes + short notes): the button lives inside li.blog-list-item (read-state target)
   assertIncludes(serialItem, '<li class="blog-list-item">', 'blog serial row read-state target');
   assertIncludes(serialItem, 'class="newsprint-bookmark-icon"', 'blog serial bookmark button markup');
   assertIncludes(serialItem, 'data-item-id={post.id}', 'blog serial bookmark item id binding');
   assertIncludes(serialItem, 'data-item-type="blog"', 'blog serial bookmark item type binding');
   assertIncludes(serialItem, 'data-bookmarked="false"', 'blog serial bookmark neutral SSR state');
   ```
2. ```js
   assertExcludes(enIndex, 'bookmarkedPostIds', 'EN blog SSR bookmark state');
   assertIncludes(enIndex, 'itemId={post.id}', 'EN blog list bookmark item id wiring');
   assertIncludes(enIndex, 'itemType="blog"', 'EN blog list bookmark item type wiring');
   assertIncludes(enIndex, '<BlogFeaturedCard', 'EN featured blog card usage');

   assertExcludes(koIndex, 'bookmarkedPostIds', 'KO blog SSR bookmark state');
   assertIncludes(koIndex, 'itemId={post.id}', 'KO blog list bookmark item id wiring');
   assertIncludes(koIndex, 'itemType="blog"', 'KO blog list bookmark item type wiring');
   assertIncludes(koIndex, '<BlogFeaturedCard', 'KO featured blog card usage');
   ```
   →
   ```js
   assertExcludes(enIndex, 'bookmarkedPostIds', 'EN blog SSR bookmark state');
   assertIncludes(enIndex, '<BlogFront ', 'EN blog serial front usage');

   assertExcludes(koIndex, 'bookmarkedPostIds', 'KO blog SSR bookmark state');
   assertIncludes(koIndex, '<BlogFront ', 'KO blog serial front usage');
   ```
   (`listItem` 단언 6줄과 `bookmarkScript` 단언은 그대로 둔다.)

`blog-detail-sidebar-structure.test.cjs`(Edit 도구로):
```js
const koIndex = read('src/pages/ko/blog/index.astro');
assert(koIndex.includes('mode="index"'), 'Korean blog list page must render sidebar in index mode');

const enIndex = read('src/pages/en/blog/index.astro');
assert(enIndex.includes('mode="index"'), 'English blog list page must render sidebar in index mode');
```
→
```js
// The list page (A: serial column) renders without the sidebar; category pages keep it in index mode.
const koIndex = read('src/pages/ko/blog/index.astro');
assert(koIndex.includes('sidebar={false}') && !koIndex.includes('mode="index"'), 'Korean blog list page must render without the sidebar');

const enIndex = read('src/pages/en/blog/index.astro');
assert(enIndex.includes('sidebar={false}') && !enIndex.includes('mode="index"'), 'English blog list page must render without the sidebar');

for (const locale of ['ko', 'en']) {
  const categoryPage = read(`src/pages/${locale}/blog/category/[slug].astro`);
  assert(categoryPage.includes('mode="index"') && categoryPage.includes('currentCategory={slug}'), `${locale} blog category page must keep the index-mode sidebar`);
}
```

`blog-mobile-sidebar-structure.test.cjs`(Edit 도구로):
```js
assertNoPageLevelToggle('frontend/src/pages/ko/blog/index.astro');
assertNoPageLevelToggle('frontend/src/pages/en/blog/index.astro');
assertNoPageLevelToggle('frontend/src/pages/ko/blog/[slug].astro');
assertNoPageLevelToggle('frontend/src/pages/en/blog/[slug].astro');
```
→
```js
assertNoPageLevelToggle('frontend/src/pages/ko/blog/category/[slug].astro');
assertNoPageLevelToggle('frontend/src/pages/en/blog/category/[slug].astro');
assertNoPageLevelToggle('frontend/src/pages/ko/blog/[slug].astro');
assertNoPageLevelToggle('frontend/src/pages/en/blog/[slug].astro');

// The list page (A: serial column) has no sidebar, so no drawer toggle either.
for (const locale of ['ko', 'en']) {
  const index = read(`frontend/src/pages/${locale}/blog/index.astro`);
  assert.ok(
    index.includes('sidebar={false}') && !index.includes('data-sidebar-toggle'),
    `${locale} blog list: no sidebar and no drawer toggle`,
  );
}
```
(BlogShell의 `data-sidebar-overlay` 단언은 그대로 둔다 — 조건부로 남는다.)

`blog-category-badge-font.test.cjs`(**Edit 도구로만**, 혼합 EOL): 아래 두 줄을 지운다(줄 전체, 줄바꿈 포함). 나머지는 그대로다.
```js
const featured = fs.readFileSync(path.join(process.cwd(), 'frontend/src/components/blog/BlogFeaturedCard.astro'), 'utf8');
```
```js
assert(featured.includes('class="blog-category-badge"'), 'Featured card should use blog-category-badge');
```

`blog-sidebar-layout.test.cjs`(Edit 도구로):
```js
assertNoInlineToolbar('frontend/src/pages/ko/blog/index.astro');
assertNoInlineToolbar('frontend/src/pages/en/blog/index.astro');
```
→
```js
// The list page has no sidebar (and no drawer toggle); category pages keep the toolbar.
assertNoInlineToolbar('frontend/src/pages/ko/blog/category/[slug].astro');
assertNoInlineToolbar('frontend/src/pages/en/blog/category/[slug].astro');
```

- [ ] **Step 2: 실패 확인**

Run:
```bash
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-v2.test.cjs
node frontend/tests/blog-bookmark-card-contract.test.cjs
node frontend/tests/blog-detail-sidebar-structure.test.cjs
node frontend/tests/blog-mobile-sidebar-structure.test.cjs
node frontend/tests/blog-category-badge-font.test.cjs
node frontend/tests/blog-sidebar-layout.test.cjs
```
Expected:
- `blog-list-serial`: FAIL "shell: sidebar prop defaults to true"
- `blog-v2`, `blog-bookmark-card-contract`: FAIL `ENOENT … BlogSerialItem.astro`
- `blog-detail-sidebar-structure`: FAIL "Korean blog list page must render without the sidebar"
- `blog-mobile-sidebar-structure`: FAIL "ko blog list: no sidebar and no drawer toggle"
- `blog-category-badge-font`: PASS(지운 단언만 바뀜) — "blog category badge font mapping ok"
- `blog-sidebar-layout`: 기준선과 같은 "Blog sidebar panel must use the shared card radius"

- [ ] **Step 3: `BlogShell.astro` 전체 교체** (Read 후 Write 도구로)

```astro
---
import BlogSidebar from './BlogSidebar.astro';
import type { BlogSidebarMode, SidebarPost } from '../../lib/pageData/blogSidebar';

interface Props {
  locale: 'en' | 'ko';
  sidebarPosts?: SidebarPost[];
  currentSlug?: string;
  currentCategory?: string;
  totalCount?: number;
  mode?: BlogSidebarMode;
  showTOC?: boolean;
  /** false: no sidebar, overlay or drawer — one centred column (blog list). Category and detail pages keep the default. */
  sidebar?: boolean;
}

const {
  locale,
  sidebarPosts = [],
  currentSlug,
  currentCategory,
  totalCount = 0,
  mode = 'index',
  showTOC,
  sidebar = true,
} = Astro.props as Props;
---

<div class:list={['blog-shell', { 'blog-shell--single': !sidebar }]}>
  {sidebar && (
    <>
      <BlogSidebar
        locale={locale}
        posts={sidebarPosts}
        currentSlug={currentSlug}
        currentCategory={currentCategory}
        totalCount={totalCount}
        mode={mode}
      />
      <div class="blog-sidebar-overlay" data-sidebar-overlay></div>
    </>
  )}
  <div class="blog-main">
    <div class="blog-main-inner">
      <slot />
    </div>
  </div>
  {showTOC && <slot name="toc" />}
</div>
```

- [ ] **Step 4: `BlogSerialItem.astro` 작성** (Write 도구로)

```astro
---
// frontend/src/components/blog/BlogSerialItem.astro
// Blog list A: one row of a series (episode number) or of the short notes (field dot label).
// The bookmark button must stay inside this li: content-status.ts marks the closest .blog-list-item as read.
// Bookmark state is neutral on the server (CDN-cacheable HTML); content-status.ts hydrates it.
import { formatBlogDate } from '../../lib/blogSerial.js';

interface SerialPost {
  id: string;
  title: string;
  slug: string;
  published_at?: string | null;
}

interface Props {
  locale: 'en' | 'ko';
  post: SerialPost;
  /** series row: 1-based episode number */
  episode?: number;
  /** short-note row: field label and DB color */
  categoryLabel?: string;
  categoryColor?: string;
}

const { locale, post, episode, categoryLabel, categoryColor } = Astro.props;
const episodeLabel = episode ? (locale === 'ko' ? `${episode}화` : `Ep. ${episode}`) : '';
const date = formatBlogDate(post.published_at, locale);
---

<li class="blog-list-item">
  {episodeLabel ? (
    <span class="blog-serial-ep">{episodeLabel}</span>
  ) : (
    <span class="blog-serial-cat">
      {categoryLabel && (
        <span class="blog-category-badge" style={`--cat-color: ${categoryColor || 'var(--color-border)'}`}>{categoryLabel}</span>
      )}
    </span>
  )}
  <a class="blog-serial-title" href={`/${locale}/blog/${post.slug}/`}>{post.title}</a>
  <span class="blog-serial-date">{date}</span>
  <button
    type="button"
    class="newsprint-bookmark-icon"
    data-item-id={post.id}
    data-item-type="blog"
    data-bookmarked="false"
    aria-label="Add bookmark"
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  </button>
</li>
```

- [ ] **Step 5: `BlogFront.astro` 작성** (Write 도구로. `·`는 문자 그대로)

```astro
---
// frontend/src/components/blog/BlogFront.astro
// Blog list A (serial column): byline + search, latest post, one series per main field, short notes.
// Data comes from buildBlogFront() (lib/blogSerial.js); every date goes through formatBlogDate (KST).
// The latest-post block has no bookmark button: the same post is also an episode row, and
// content-status.ts applies state to the first button per id only.
import type { BlogCategory } from '../../lib/pageData/blogCategories';
import { formatBlogDate } from '../../lib/blogSerial.js';
import BlogSerialItem from './BlogSerialItem.astro';

interface FrontPost {
  id: string;
  title: string;
  slug: string;
  category: string | null;
  published_at: string | null;
  excerpt?: string | null;
}

interface Props {
  locale: 'en' | 'ko';
  front: {
    lead: FrontPost | null;
    series: { category: BlogCategory; posts: FrontPost[] }[];
    shortNotes: FrontPost[];
    total: number;
    latestAt: string | null;
  };
  categories: BlogCategory[];
}

const { locale, front, categories } = Astro.props;
const isKo = locale === 'ko';
const copy = isKo
  ? { latest: '마지막 글', search: '글 검색', latestTag: '최신', seriesCount: '개의 연재', seriesAria: '연재', short: '짧은 글', empty: '일치하는 글이 없어요' }
  : { latest: 'Latest', search: 'Search posts', latestTag: 'Latest', seriesCount: 'series', seriesAria: 'Series', short: 'Short notes', empty: 'No posts match' };
const postsLabel = (n: number) => (isKo ? `${n}편` : `${n} post${n === 1 ? '' : 's'}`);

const bySlug = new Map(categories.map((c) => [c.slug, c]));
const labelOf = (slug: string | null) => {
  if (!slug) return '';
  const category = bySlug.get(slug);
  return category ? (isKo ? category.label_ko : category.label_en) : slug;
};
const colorOf = (slug: string | null) => (slug && bySlug.get(slug)?.color) || 'var(--color-border)';

const latest = formatBlogDate(front.latestAt, locale);
const leadLabel = front.lead ? labelOf(front.lead.category) : '';
---

<div class="blog-front" data-blog-front>
  <div class="blog-byline">
    <p class="blog-byline-meta"><strong>Amy</strong> · {postsLabel(front.total)}{latest && ` · ${copy.latest} ${latest}`}</p>
    <input type="search" id="blog-search" class="blog-search-input" placeholder={copy.search} aria-label={copy.search} autocomplete="off" />
  </div>

  {front.lead && (
    <section class:list={['blog-lead', { 'blog-lead--solo': front.series.length === 0 }]}>
      <div class="blog-lead-main">
        <p class="blog-lead-kicker">
          <span class="blog-category-badge" style={`--cat-color: ${colorOf(front.lead.category)}`}>{leadLabel ? `${leadLabel} · ${copy.latestTag}` : copy.latestTag}</span>
        </p>
        <h2 class="blog-lead-title"><a href={`/${locale}/blog/${front.lead.slug}/`}>{front.lead.title}</a></h2>
        {front.lead.excerpt && <p class="blog-lead-excerpt">{front.lead.excerpt}</p>}
        <p class="blog-lead-date">{formatBlogDate(front.lead.published_at, locale)}</p>
      </div>
      {front.series.length > 0 && (
        <aside class="blog-lead-aside" aria-label={copy.seriesAria}>
          <p class="blog-lead-count">{front.series.length}</p>
          <p class="blog-lead-count-label">{copy.seriesCount}</p>
          <ul class="blog-lead-series">
            {front.series.map((s) => {
              const label = labelOf(s.category.slug);
              return <li>{isKo ? `${label} ${s.posts.length}편` : `${label} · ${s.posts.length}`}</li>;
            })}
          </ul>
        </aside>
      )}
    </section>
  )}

  {front.series.length > 0 && (
    <section class="blog-series-grid" aria-label={copy.seriesAria}>
      {front.series.map(({ category, posts }) => {
        const label = labelOf(category.slug);
        const desc = isKo ? category.description_ko : category.description_en;
        return (
          <article class="blog-series">
            <header class="blog-series-head">
              <h2 class="blog-series-title"><a href={`/${locale}/blog/category/${category.slug}/`}>{label}</a></h2>
              <span class="blog-series-count">{postsLabel(posts.length)}</span>
            </header>
            {desc && <p class="blog-series-desc">{desc}</p>}
            <ol class="blog-serial-list">
              {posts.map((post, i) => (
                <BlogSerialItem locale={locale} post={post} episode={i + 1} />
              ))}
            </ol>
          </article>
        );
      })}
    </section>
  )}

  {front.shortNotes.length > 0 && (
    <section class="blog-short-notes">
      <h2 class="blog-short-notes-title">{copy.short}</h2>
      <ol class="blog-serial-list">
        {front.shortNotes.map((post) => (
          <BlogSerialItem locale={locale} post={post} categoryLabel={labelOf(post.category)} categoryColor={colorOf(post.category)} />
        ))}
      </ol>
    </section>
  )}

  <p id="blog-search-empty" class="blog-search-empty" role="status" aria-live="polite" hidden>{copy.empty}</p>
</div>

<script>
  // Blog list search: title substring match (case-insensitive), 150ms debounce.
  // Hides non-matching rows, series/short notes with no visible row, and the latest-post block
  // (its post is already in the results). Clearing the query restores everything.
  function initBlogSearch(): void {
    const input = document.getElementById('blog-search') as HTMLInputElement | null;
    if (!input || input.dataset.blogSearchReady === 'true') return;
    input.dataset.blogSearchReady = 'true';

    const front = input.closest<HTMLElement>('[data-blog-front]');
    if (!front) return;
    const lead = front.querySelector<HTMLElement>('.blog-lead');
    const grid = front.querySelector<HTMLElement>('.blog-series-grid');
    const empty = document.getElementById('blog-search-empty');
    const groups = Array.from(front.querySelectorAll<HTMLElement>('.blog-series, .blog-short-notes'));
    let timer: number | undefined;

    function apply(): void {
      const query = input!.value.trim().toLowerCase();
      let shown = 0;
      for (const group of groups) {
        let visible = 0;
        group.querySelectorAll<HTMLElement>('.blog-list-item').forEach((item) => {
          const title = (item.querySelector('.blog-serial-title')?.textContent || '').toLowerCase();
          const match = !query || title.includes(query);
          item.hidden = !match;
          if (match) visible += 1;
        });
        group.hidden = visible === 0;
        shown += visible;
      }
      if (grid) grid.hidden = !grid.querySelector('.blog-series:not([hidden])');
      if (lead) lead.hidden = query.length > 0;
      if (empty) empty.hidden = !query || shown > 0;
    }

    input.addEventListener('input', () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(apply, 150);
    });
    // A restored value (back/forward cache, autofill) filters right away.
    if (input.value) apply();
  }

  document.addEventListener('astro:page-load', initBlogSearch);
  initBlogSearch();
</script>
```

- [ ] **Step 6: `pages/ko/blog/index.astro` 전체 교체** (Read 후 Write 도구로)

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { supabase } from '../../../lib/supabase';
import { fetchCategories } from '../../../lib/pageData/blogCategories';
import { buildBlogFront } from '../../../lib/blogSerial.js';
import BlogShell from '../../../components/blog/BlogShell.astro';
import BlogFront from '../../../components/blog/BlogFront.astro';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';

let posts: any[] = [];
let fetchError: string | null = null;

// Parallel: posts + categories (no dependencies between them)
const [postsRes, dbCategories] = await Promise.all([
  supabase
    ? supabase.from('blog_posts')
        .select('id, title, slug, category, published_at, tags, reading_time_min, excerpt')
        .eq('status', 'published')
        .eq('locale', 'ko')
        .order('created_at', { ascending: false })
        .limit(100)
    : Promise.resolve({ data: null, error: null }),
  supabase ? fetchCategories(supabase) : Promise.resolve([]),
]);

if (postsRes.error) {
  console.error('[blog-list-ko] Supabase error:', postsRes.error.message);
  fetchError = postsRes.error.message;
} else {
  posts = postsRes.data ?? [];
}
if (fetchError) Astro.response.status = 503;

// Serial column: latest post, one series per visible main field (episodes by published_at), short notes.
const front = buildBlogFront(posts, dbCategories);
---

<MainLayout title={t.ko['blog.title']} description="AI 엔지니어링, 커리어, 프로젝트 케이스 스터디에 대한 심층 글. 개발자와 기획자를 위해 작성되었습니다." locale="ko" slug="blog/">
  <BlogShell locale="ko" sidebar={false}>
    <!-- Masthead -->
    <h1 class="blog-masthead-title">–도록: do log</h1>

    <p class="blog-masthead-tagline">만들고, 배우고, 기록하는 칼럼</p>

    {fetchError ? (
      <NewsprintNotice variant="error" message={t.ko['blog.error']} linkHref="/ko/blog/" linkLabel={t.ko['error.retry']} />
    ) : front.total > 0 ? (
      <BlogFront locale="ko" front={front} categories={dbCategories} />
    ) : (
      <div class="blog-empty-state">
        <div class="blog-empty-icon">📝</div>
        <h2>준비 중</h2>
        <p>글을 준비하고 있어요. 곧 만나요!</p>
      </div>
    )}
  </BlogShell>
</MainLayout>

<script>
  import '../../../scripts/bookmark';
</script>
```

- [ ] **Step 7: `pages/en/blog/index.astro` 전체 교체** (Read 후 Write 도구로). KO와 다른 곳은 `.eq('locale', 'en')`, `[blog-list-en]`, `MainLayout`의 title/description/locale, `BlogShell locale="en"`, 태그라인, `NewsprintNotice`(`t.en`, `/en/blog/`), `BlogFront locale="en"`, 빈 상태 문구뿐이다. 마스트헤드 `–도록: do log`는 KO와 같다.

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { supabase } from '../../../lib/supabase';
import { fetchCategories } from '../../../lib/pageData/blogCategories';
import { buildBlogFront } from '../../../lib/blogSerial.js';
import BlogShell from '../../../components/blog/BlogShell.astro';
import BlogFront from '../../../components/blog/BlogFront.astro';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';

let posts: any[] = [];
let fetchError: string | null = null;

// Parallel: posts + categories (no dependencies between them)
const [postsRes, dbCategories] = await Promise.all([
  supabase
    ? supabase.from('blog_posts')
        .select('id, title, slug, category, published_at, tags, reading_time_min, excerpt')
        .eq('status', 'published')
        .eq('locale', 'en')
        .order('created_at', { ascending: false })
        .limit(100)
    : Promise.resolve({ data: null, error: null }),
  supabase ? fetchCategories(supabase) : Promise.resolve([]),
]);

if (postsRes.error) {
  console.error('[blog-list-en] Supabase error:', postsRes.error.message);
  fetchError = postsRes.error.message;
} else {
  posts = postsRes.data ?? [];
}
if (fetchError) Astro.response.status = 503;

// Serial column: latest post, one series per visible main field (episodes by published_at), short notes.
const front = buildBlogFront(posts, dbCategories);
---

<MainLayout title={t.en['blog.title']} description="In-depth articles on AI engineering, career development, and project case studies. Written for developers and product thinkers." locale="en" slug="blog/">
  <BlogShell locale="en" sidebar={false}>
    <!-- Masthead -->
    <h1 class="blog-masthead-title">–도록: do log</h1>

    <p class="blog-masthead-tagline">A column on building, learning and keeping notes</p>

    {fetchError ? (
      <NewsprintNotice variant="error" message={t.en['blog.error']} linkHref="/en/blog/" linkLabel={t.en['error.retry']} />
    ) : front.total > 0 ? (
      <BlogFront locale="en" front={front} categories={dbCategories} />
    ) : (
      <div class="blog-empty-state">
        <div class="blog-empty-icon">📝</div>
        <h2>Coming Soon</h2>
        <p>Posts are being prepared. Check back soon!</p>
      </div>
    )}
  </BlogShell>
</MainLayout>

<script>
  import '../../../scripts/bookmark';
</script>
```

- [ ] **Step 8: i18n 키 삭제** (**Edit 도구로만**, CRLF 유지. 2곳)
  1. ```ts
         'blog.title': 'IT Blog',
         'blog.featured': 'Featured',
         'blog.allPosts': 'All Posts',
     ```
     →
     ```ts
         'blog.title': 'IT Blog',
     ```
  2. ```ts
         'blog.title': 'IT 블로그',
         'blog.featured': '추천 글',
         'blog.allPosts': '전체 글',
     ```
     →
     ```ts
         'blog.title': 'IT 블로그',
     ```
  (`'blog.allPostsCount'`는 사이드바가 쓰므로 남긴다.)

Run: `tr -cd '\r' < frontend/src/i18n/index.ts | wc -c; wc -l < frontend/src/i18n/index.ts` → 두 숫자가 같다(172, 전부 CRLF 유지).

- [ ] **Step 9: CSS 추가** (Edit 도구로) — `global.css`의 `/* ── Category Header ── */` 주석 **바로 위**에 다음 블록을 넣는다(블록 끝의 빈 줄 한 줄 포함). `/* ── Empty State ── */` 블록 뒤, 분야 헤더 블록 앞이다.

```css
/* ── Blog list A: serial column (byline, latest post, series, short notes) ── */
.blog-shell--single .blog-main-inner {
  max-width: 820px;
}

.blog-byline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem 1.5rem;
  padding: 0.55rem 0;
  border-top: 2px solid var(--color-text-primary);
  border-bottom: 1px solid var(--color-text-primary);
  margin-bottom: 2rem;
}

.blog-byline-meta {
  margin: 0;
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.blog-byline-meta strong {
  font-weight: 700;
  color: var(--color-text-primary);
}

.blog-search-input {
  width: 14rem;
  max-width: 100%;
  padding: 0.4rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: 0;
  background: var(--color-input-surface);
  color: var(--color-text-primary);
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
}

.blog-search-input:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -1px;
}

.blog-lead {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 200px;
  gap: 2rem;
  padding-bottom: 2rem;
  margin-bottom: 2.5rem;
  border-bottom: 1px solid var(--color-border);
}

.blog-lead--solo {
  grid-template-columns: minmax(0, 1fr);
}

.blog-lead-kicker {
  margin: 0 0 0.6rem;
}

.blog-lead-title {
  margin: 0 0 0.75rem;
  font-family: var(--font-blog-heading);
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.03em;
}

.blog-lead-title a,
.blog-series-title a {
  color: var(--color-text-primary);
  text-decoration: none;
}

.blog-lead-title a:hover,
.blog-series-title a:hover,
.blog-serial-title:hover {
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.blog-lead-excerpt {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  line-height: 1.65;
  color: var(--color-text-secondary);
}

.blog-lead-date {
  margin: 0;
  font-family: var(--font-blog-ui);
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.blog-lead-aside {
  padding-left: 1.5rem;
  border-left: 1px solid var(--color-border);
}

.blog-lead-count {
  margin: 0;
  font-family: var(--font-masthead);
  font-size: 3rem;
  font-weight: 500;
  line-height: 1;
  font-variant-numeric: lining-nums;
  color: var(--color-text-primary);
}

.blog-lead-count-label {
  margin: 0.3rem 0 0.75rem;
  font-family: var(--font-blog-ui);
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.blog-lead-series {
  margin: 0;
  padding: 0;
  list-style: none;
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.blog-series-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2.5rem 2rem;
  margin-bottom: 3rem;
}

.blog-series-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  padding-top: 0.6rem;
  border-top: 2px solid var(--color-text-primary);
  margin-bottom: 0.4rem;
}

.blog-series-title {
  margin: 0;
  font-family: var(--font-blog-heading);
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.02em;
}

.blog-series-count {
  flex-shrink: 0;
  font-family: var(--font-blog-ui);
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.blog-series-desc {
  margin: 0 0 0.4rem;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.blog-serial-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.blog-serial-list .blog-list-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0;
}

.blog-serial-list .blog-list-item:hover {
  background: none;
  margin-inline: 0;
  padding-inline: 0;
}

.blog-serial-ep {
  min-width: 2.6em;
  font-family: var(--font-masthead);
  font-size: 0.85rem;
  font-weight: 500;
  font-variant-numeric: lining-nums;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.blog-serial-title {
  min-width: 0;
  font-family: var(--font-blog-heading);
  font-size: 0.98rem;
  font-weight: 600;
  line-height: 1.45;
  letter-spacing: -0.02em;
  color: var(--color-text-primary);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.blog-serial-date {
  font-family: var(--font-blog-ui);
  font-size: 0.78rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.blog-serial-list .newsprint-bookmark-icon {
  width: 2rem;
  height: 2rem;
}

.blog-short-notes {
  margin-bottom: 3rem;
}

.blog-short-notes-title {
  margin: 0 0 0.4rem;
  padding-top: 0.6rem;
  border-top: 2px solid var(--color-text-primary);
  font-family: var(--font-blog-heading);
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.02em;
}

.blog-search-empty {
  margin: 1rem 0 3rem;
  padding: 2rem 0;
  text-align: center;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

/* Rows are display: grid, which beats the UA [hidden] rule: the search needs this. */
.blog-front [hidden] {
  display: none;
}

/* Blog list A: mobile */
@media (max-width: 767px) {
  .blog-byline {
    flex-wrap: wrap;
  }

  .blog-search-input {
    width: 100%;
    font-size: 1rem;
  }

  .blog-lead {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.25rem;
  }

  .blog-lead-aside {
    padding: 1rem 0 0;
    border-left: none;
    border-top: 1px solid var(--color-border);
  }

  .blog-lead-title {
    font-size: 1.6rem;
  }

  .blog-series-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
```

- [ ] **Step 10: `BlogFeaturedCard` 삭제**

```bash
git rm frontend/src/components/blog/BlogFeaturedCard.astro
grep -rn "BlogFeaturedCard" frontend/src frontend/tests --include=*.astro --include=*.ts --include=*.js --include=*.cjs --include=*.mjs
```
Expected: grep은 `blog-list-serial.test.cjs`의 부정 단언 2줄만 나온다.

- [ ] **Step 11: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-serial.test.mjs
node frontend/tests/blog-v2.test.cjs
node frontend/tests/blog-bookmark-card-contract.test.cjs
node frontend/tests/blog-detail-sidebar-structure.test.cjs
node frontend/tests/blog-mobile-sidebar-structure.test.cjs
node frontend/tests/blog-category-badge-font.test.cjs
node frontend/tests/public-list-personalization.test.cjs
node frontend/tests/library-blog-items-contract.test.cjs
node frontend/tests/blog-detail-sidebar-behavior.test.cjs
node frontend/tests/blog-toc-structure.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/public-cache-policy.test.mjs
node frontend/tests/font-roles.test.cjs
node frontend/tests/retro-decoration-removed.test.cjs
node frontend/tests/blog-sidebar-layout.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 테스트를 뺀 모두 PASS, 빌드 "Complete!".
- `blog-sidebar-layout`은 기준선과 **같은 메시지** "Blog sidebar panel must use the shared card radius".

- [ ] **Step 12: 커밋**

```bash
git add frontend/src/components/blog/BlogFront.astro frontend/src/components/blog/BlogSerialItem.astro frontend/src/components/blog/BlogShell.astro frontend/src/pages/ko/blog/index.astro frontend/src/pages/en/blog/index.astro frontend/src/i18n/index.ts frontend/src/styles/global.css frontend/tests/blog-list-serial.test.cjs frontend/tests/blog-v2.test.cjs frontend/tests/blog-bookmark-card-contract.test.cjs frontend/tests/blog-detail-sidebar-structure.test.cjs frontend/tests/blog-mobile-sidebar-structure.test.cjs frontend/tests/blog-category-badge-font.test.cjs frontend/tests/blog-sidebar-layout.test.cjs
git commit -m "feat: blog list as a serial column with byline, latest post, series and short notes"
```

(`git rm`으로 stage된 `BlogFeaturedCard.astro` 삭제가 함께 커밋된다.)

---

## Task 3: 쓰지 않게 된 CSS 정리 (TDD)

**Files:**
- Modify: `frontend/src/styles/global.css`, `frontend/tests/blog-list-serial.test.cjs`, `frontend/tests/blog-section-heading-font.test.cjs`(전체 교체), `frontend/tests/blog-title-fonts.test.cjs`(혼합 EOL → Edit만)

- [ ] **Step 1: 다른 사용처 확인**

Run:
```bash
grep -rn "blog-featured\|blog-category-tab\|blog-section-header" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rln "blog-list-batch\|data-blog-sentinel\|blog-mobile-toolbar\|blog-mono-tag" frontend/src --include=*.astro
```
Expected:
- 첫 grep: 결과 없음(Task 2에서 목록 페이지·FeaturedCard가 더 이상 쓰지 않는다). 결과가 있으면 멈추고 보고한다.
- 둘째 grep: 분야 페이지 2개, 글 상세 2개, `BlogArticleLayout.astro` — 이 CSS들은 **남긴다**.

- [ ] **Step 2: 실패하는 단언 추가·테스트 갱신**

`blog-list-serial.test.cjs`(Edit 도구로): `console.log('blog-list-serial.test.cjs passed');` **바로 위**에 넣는다. 블록과 `console.log` 줄 사이에는 빈 줄 한 줄을 둔다.

```js
// unused CSS removed (Task 3): featured cards, list-page tabs and section headers were list-only
for (const gone of ['.blog-featured-', '.blog-category-tab', '.blog-section-header', 'Blog Masthead Tagline + Category Tabs']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
// still used by the category pages / article layout
for (const kept of ['.blog-list-batch[hidden] {', '.blog-scroll-sentinel {', '.blog-mobile-toolbar {', '.blog-list-section {', '.blog-mono-tag {', '.blog-category-badge {', '.blog-masthead-tagline {']) {
  assert(css.includes(kept), `CSS kept: ${kept}`);
}
```

`blog-section-heading-font.test.cjs` 전체 교체(Read 후 Write 도구로):

```js
const fs = require('fs');
const path = require('path');

const root = process.cwd();

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function assertIncludes(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

// Blog list A (2026-10-17): the old .blog-section-header ("추천 글"/"전체 글") is gone.
// Section headings are now the latest post, series and short-notes h2s: Hahmlet 700.
const css = read('frontend/src/styles/global.css');
for (const selector of ['.blog-lead-title', '.blog-series-title', '.blog-short-notes-title']) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = css.match(new RegExp(`(?:^|\\n)${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`));
  if (!match) {
    throw new Error(`Missing ${selector} rule block`);
  }
  assertIncludes(match[1], 'font-family: var(--font-blog-heading);', `${selector} heading font`);
  assertIncludes(match[1], 'font-weight: 700;', `${selector} weight`);
}
if (css.includes('.blog-section-header')) {
  throw new Error('Unexpected legacy .blog-section-header rule');
}

console.log('blog-section-heading-font.test.cjs passed');
```

`blog-title-fonts.test.cjs`(**Edit 도구로만**):
```js
const selectors = ['.blog-featured-card-title', '.blog-list-item-title', '.blog-article-title'];
```
→
```js
const selectors = ['.blog-list-item-title', '.blog-serial-title', '.blog-article-title'];
```

Run:
```bash
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-section-heading-font.test.cjs
node frontend/tests/blog-title-fonts.test.cjs
```
Expected: 앞의 둘은 FAIL "unused CSS removed: .blog-featured-", "Unexpected legacy .blog-section-header rule". `blog-title-fonts`는 기준선과 같은 "Missing IBM Plex Sans font import: IBM+Plex+Sans".

- [ ] **Step 3: CSS 삭제** — 173줄을 Edit 한 번으로 옮기기는 위험하므로 아래 스크립트를 쓴다.
  1. 다음 내용을 **Write 도구로** scratchpad에 `drop-blog-list-css.cjs`로 저장한다(repo 안에 만들지 않는다).

```js
// Run from the repo root: node <this file>
// Removes the list-only blog CSS (category tabs, section header, featured cards): the 173 lines from
// `.blog-category-tabs {` up to (not including) `.blog-category-badge {`, and renames the tagline comment.
const fs = require('fs');

const file = 'frontend/src/styles/global.css';
const lines = fs.readFileSync(file, 'utf8').split('\n');
const start = lines.indexOf('.blog-category-tabs {');
const end = lines.indexOf('.blog-category-badge {');
if (start < 0 || end < 0 || end - start !== 173) {
  throw new Error(`unexpected range: .blog-category-tabs at ${start + 1}, .blog-category-badge at ${end + 1} (expected 173 lines apart)`);
}
lines.splice(start, end - start);
const comment = lines.indexOf('/* ── Blog Masthead Tagline + Category Tabs ── */');
if (comment < 0) throw new Error('tagline comment not found');
lines[comment] = '/* ── Blog Masthead Tagline ── */';
fs.writeFileSync(file, lines.join('\n'));
console.log(`removed lines ${start + 1}-${end} (${end - start} lines)`);
```

  2. repo 루트에서 `node <scratchpad>/drop-blog-list-css.cjs` → `removed lines 9795-9967 (173 lines)`(줄 번호는 다른 세션 변경으로 달라질 수 있다. 줄 수 173이 아니면 스크립트가 아무것도 쓰지 않고 오류를 낸다 → 멈추고 보고).
  - 지워지는 것: `.blog-category-tabs`·`.blog-category-tab*`·639px 탭 미디어, `/* ── Section Headers … */` + `.blog-section-header`, `/* ── Featured Cards ── */` + `.blog-featured-grid`·`.blog-featured-card*`(640/639px 미디어, `.blog-featured-card .newsprint-bookmark-icon` 포함). 결과: `.blog-masthead-tagline { … }` → 빈 줄 → `.blog-category-badge {`.
  - 주석 `/* ── Blog Masthead Tagline + Category Tabs ── */` → `/* ── Blog Masthead Tagline ── */`.

Run: `grep -n "blog-featured\|blog-category-tab\|blog-section-header" frontend/src/styles/global.css` → 결과 없음.

- [ ] **Step 4: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-section-heading-font.test.cjs
node frontend/tests/blog-serial.test.mjs
node frontend/tests/blog-v2.test.cjs
node frontend/tests/blog-category-badge-font.test.cjs
node frontend/tests/blog-bookmark-card-contract.test.cjs
node frontend/tests/font-roles.test.cjs
node frontend/tests/retro-decoration-removed.test.cjs
node frontend/tests/theme-palette.test.cjs
node frontend/tests/blog-title-fonts.test.cjs
node frontend/tests/blog-sidebar-layout.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 두 테스트를 뺀 모두 PASS(`blog-section-heading-font`는 기준선 FAIL → PASS), 빌드 "Complete!".
- `blog-title-fonts` "Missing IBM Plex Sans font import: IBM+Plex+Sans", `blog-sidebar-layout` "Blog sidebar panel must use the shared card radius" — 기준선과 **같은 메시지**.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/blog-list-serial.test.cjs frontend/tests/blog-section-heading-font.test.cjs frontend/tests/blog-title-fonts.test.cjs
git commit -m "chore: remove blog featured card, tab and section header CSS"
```

---

## Task 4: 검증 (컨트롤러)

- [ ] 전체 테스트를 **이름으로** 기준선(PASS 79 / FAIL 20)과 비교한다.
  ```bash
  for f in frontend/tests/*.cjs frontend/tests/*.mjs; do node "$f" >/dev/null 2>&1 && echo "PASS $(basename $f)" || echo "FAIL $(basename $f)"; done
  ```
  - 실패 목록은 기준선 20개에서 `blog-section-heading-font`를 뺀 19개와 같아야 한다(신규 FAIL 0). 실패 테스트의 첫 오류 메시지도 기준선과 같은지 본다.
  - 새 테스트 2개(`blog-serial`, `blog-list-serial`)는 PASS → **PASS 82 / FAIL 19**.
- [ ] 브라우저(`.claude/launch.json`의 `frontend-dev`, 포트 4321) 매트릭스: 종이·순백·다크 × ≥1024px·375px × ko/en
  - 대상: `/ko/blog/`(연재 2·짧은 글 1), `/en/blog/`(EN 글 0편 → 빈 상태 "Coming Soon"이 정상)
  - 스크린샷(테마·폭·locale마다), 가로 넘침 0(`document.documentElement.scrollWidth <= window.innerWidth`)
  - 대비 검사: 필자 줄, 검색 placeholder, 최신 라벨·요약·날짜, 연재 편수, 회차 번호(muted), 날짜(muted), 짧은 글 점 라벨(다크 포함)
  - ≥1024px: 최신 글 2단(1fr : 200px, 오른쪽 세로선), 연재 2열. 375px: 필자 줄 줄바꿈 + 검색 전체 폭, 최신 글 1단(요약이 아래, 위 선), 연재 1열
- [ ] 직접 확인
  - 검색: 입력(150ms 뒤 필터) → 일치 회차만, 빈 연재·짧은 글 숨김, 최신 글 숨김 / 일치 없음 → "일치하는 글이 없어요"("No posts match") / 지우기(× 포함) → 원래대로
  - 연재 제목 → 분야 페이지(`/ko/blog/category/study/`), 회차 제목 → 글 상세, 회차 순서가 발행 순(1화가 가장 오래된 글), 날짜가 KST(학습 노트 1화 3월 11일, 작업 메모 3월 12일)
  - 북마크: 회차·짧은 글 줄마다 버튼 1개, 최신 글 블록에는 없음. 로그인 시 상태·읽음 흐림(`blog-list-item--read`)이 줄 단위로 적용, 비로그인 클릭 시 로그인 안내
  - ViewTransitions로 다른 페이지 갔다가 돌아와도 검색이 한 번만 바인딩(`#blog-search[data-blog-search-ready="true"]`, 한 글자 입력에 필터 1회)
- [ ] 회귀: `/ko|en/blog/category/study/`(사이드바·서랍 토글·무한 스크롤 그대로), 글 상세(사이드바·TOC·액션 그대로)
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 5: 문서

- [ ] 스펙 [[2026-10-17-blog-list-serial-design]] Status를 `implemented (2026-10-17)`로 바꾼다.
- [ ] 이 계획의 Status를 `done (2026-10-17)`로 바꾸고, 문서 끝에 "실행 결과"(커밋 해시, 테스트 이름 비교 결과, 매트릭스 결과, 계획 대비 변경, 후속)를 적는다.
- [ ] `ACTIVE_SPRINT.md`의 `REDESIGN-HANDBOOK-TERM` 항목 다음에 추가한다.
  `- [x] **REDESIGN-BLOG-LIST** — 블로그 목록을 연재 칼럼(A)으로: 필자 줄 + 글 검색, 최신 글 + 연재 요약, 분야별 연재(발행 순 회차, 2열), 짧은 글(+미분류), KST 날짜, 사이드바·분야 탭·추천 4편·무한 스크롤 제거(분야·상세는 유지) — [[2026-10-17-blog-list-serial-design]], [[2026-10-17-blog-list-serial]]`
- [ ] `grep -rln "BlogFeaturedCard\|blog-featured\|blog-category-tabs\|추천 4편\|blog.featured" vault --include=*.md`로 관련 노트를 찾는다. `90-Archive/`와 이번 스펙·계획은 빼고, 블로그 목록의 현재 구조를 설명하는 노트만 최소한으로 고친다(예: `2026-10-15-site-redesign-phase7-blog.md`가 아직 `plans/`에 있으면 "목록은 2026-10-17 연재 칼럼으로 대체" 한 줄).
- [ ] 알려진 한계를 실행 결과에 적는다: 연재 이름·순서는 분야 이름·발행 순 고정(관리자 편집 없음), 연재당 표시 수 상한 없음, 글 100편 상한, 날짜에 연도 없음(같은 해 가정), EN 발행 글 0편이라 EN 목록은 빈 상태.
- [ ] 커밋(고친 vault 노트 경로만 지정해 add한다. `vault/.obsidian/*`는 넣지 않는다):
  ```bash
  git add vault/09-Implementation/plans/2026-10-17-blog-list-serial-design.md vault/09-Implementation/plans/2026-10-17-blog-list-serial.md vault/09-Implementation/plans/ACTIVE_SPRINT.md
  git commit -m "docs: record blog list serial column redesign"
  ```
  (Task 5에서 고친 다른 vault 노트가 있으면 그 경로도 `git add`에 더한다.)

---

## 실행 결과 (2026-10-17)

- 커밋: `e6b0c0a9` 연재 칼럼 계산(blogSerial.js), `36937103` 목록을 연재 칼럼으로(바이라인·최신 글·연재·짧은 글, 목록에서 사이드바 제거), `e3cc40ee` 대표 카드·탭·섹션 머리 CSS 삭제.
- 테스트: PASS 82, 기준선 대비 변화는 `blog-section-heading-font` FAIL→PASS 하나뿐, 신규 FAIL 0.
- 브라우저 클릭 검증(/ko/blog/): 검색 "rag" 2건·"흐름" 1건·없는 말 → 빈 안내·지우면 11건 복원, 연재 제목 → /ko/blog/category/study/·project/, 행마다 저장 버튼 1개(11개), 최신 글 블록에는 저장 버튼 없음, 1화 = 가장 이른 글.
- 매트릭스: 종이·순백·다크 × 1100px·375px × ko/en — 가로 넘침 0, 대비 미달 0. EN은 글 0편이라 빈 안내.
- 회귀: 카테고리 페이지(사이드바 유지, 5건)와 글 상세(/ko/blog/ai-agent/, 사이드바 유지) 정상.
