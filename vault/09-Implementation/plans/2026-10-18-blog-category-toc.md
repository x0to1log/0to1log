# 블로그 분야 페이지 A(연재 목차) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** done (2026-10-18) — 실행 결과는 문서 끝 참조. (2026-10-18)

**Goal:** `/ko|en/blog/category/{slug}/`를 왼쪽 폴더 트리(`BlogSidebar`) + 제목만 있는 목록(`BlogListItem`, 최신순, 무한 스크롤)에서 목록·글 상세와 같은 가운데 한 단(820px)의 **연재 목차**로 바꾼다. 위에서부터 "경로 줄(← IT 블로그 · 연재/짧은 글) → h1 분야 이름(+설명) → 바이라인(연재 N편 · 기간 | 1화부터 읽기 →) → 목록(목록 페이지와 같은 `BlogSerialItem` 줄 + 요약 두 줄) → 다른 분야(라벨 + 개수)"이다. 연재(main 그룹)는 오래된 순 1화부터, 짧은 글(그 밖)은 최신순. 글 쿼리를 목록·상세와 같은 100편 창으로 맞춰 회차가 세 페이지에서 일치하고, 예전 `tech` 글도 학습 노트 연재에 들어간다. 마지막 사이드바 사용처가 사라지므로 `BlogShell`의 사이드바 prop과 `BlogSidebar`·`blogSidebar.ts`·`BlogCategoryHeader`·`BlogListItem`·관련 CSS·i18n 키를 지운다.

**Architecture:**
- `lib/blogSerial.js`에 순수 함수 `categoryPage(posts, categories, slug)` → `{ kind, posts, range, counts }`. series는 `buildBlogFront(...).series`의 해당 항목을 그대로 쓴다(회차 규칙 한 곳).
- ko/en `pages/{locale}/blog/category/[slug].astro`를 통째로 다시 쓴다: 쿼리 3개(분야 단건·글 100편·분야 목록), 숨김 분야 → 항상 404(관리자 분기 삭제), 글 조회 실패 → 503 + `NewsprintNotice`, 줄은 `BlogSerialItem`(새 선택 prop `excerpt`), 번들 `<script>`의 `scripts/bookmark` import 유지, 무한 스크롤 삭제.
- `BlogShell.astro`: 사이드바·오버레이·`toc` 슬롯·관련 prop 삭제, `blog-shell blog-shell--single` 고정. 호출처 6곳 중 목록·상세 4곳은 `sidebar={false}`만 지운다(분야 2곳은 통째 교체).
- CSS(`global.css`): Task 2에서 `/* ── Category Header ── */` 바로 앞에 분야 페이지 블록을 넣는다(경로 줄, h1, 바이라인, 1화 강조, 요약 `grid-column: 2; grid-row: 2`, 짧은 글 3열 격자, 다른 분야, ≤767px h1 1.9rem). Task 3에서 사이드바·폴더·무한 스크롤·모바일 툴바·`BlogCategoryHeader`·`BlogListItem` 전용 규칙과 변수 2개를 삭제 스크립트로 지운다(≤1023px 블록은 `.blog-shell` 규칙만 남김).
- 테스트: `blog-serial.test.mjs`에 `categoryPage` 단언, 새 구조 테스트 `blog-category-toc.test.cjs`(Task 3에서 삭제 단언 블록 추가). 사이드바 전용 테스트 5개는 삭제(남는 단언은 새 테스트로 옮김), 나머지는 정확한 Edit로 갱신.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-10-18-blog-category-toc-design]] — 구현 전에 반드시 읽는다. 시안: `.superpowers/brainstorm/blog2/category-v1.html`(A안).

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 각 Task의 Step 0 명령으로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `frontend/src/pages/admin/pipeline-runs/*`, `frontend/src/lib/pageData/publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 **읽기만 하고 수정·stage하지 않는다**.
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- **백슬래시가 있는 파일은 Write/Edit 도구로만 작성한다.** Bash heredoc을 쓰면 백슬래시가 사라진다. 해당: 테스트 파일 전부(정규식), CSS 삭제 스크립트. 새/교체 파일은 전부 Write 도구로 만든다.
- 이 계획의 코드 블록은 **목록 밖**에 있고 들여쓰기가 없다. 보이는 그대로 쓴다. Edit의 old/new는 "old:" / "new:" 아래 블록 그대로다.
- Astro/JS 파일의 문자열에는 `\uXXXX` 이스케이프를 쓰지 않는다. `·`, `←`, `→`, `~`, 한글, `📝`는 **문자 그대로** 쓴다.
- 줄바꿈·인코딩(`core.autocrlf=true`, git 인덱스는 모두 LF)
  - **CRLF 작업 트리**: `pages/{ko,en}/blog/category/[slug].astro`, `src/i18n/index.ts`. 분야 페이지 두 개는 **통째로 다시 쓰므로** Read 후 Write로 교체한다(LF로 저장됨, 인덱스가 LF라 diff에 줄바꿈 차이 없음). `i18n/index.ts`는 **Edit 도구로만** 고친다(Edit은 기존 CRLF를 유지한다. 통째 Write 금지).
  - 나머지 대상(`blogSerial.js`, `BlogShell.astro`, `BlogSerialItem.astro`, ko/en `blog/index.astro`·`blog/[slug].astro`, `global.css`, 테스트 파일)은 LF다. 통째 교체 파일은 Read 후 Write, 부분 수정은 Edit 도구로 한다.
  - CSS 삭제는 줄 번호가 아니라 스크립트의 "그 줄과 정확히 같은 줄" 기준으로 찾는다. 스크립트는 줄 수가 하나라도 다르면 **아무것도 쓰지 않고** 오류를 낸다 → 멈추고 보고한다.
  - 기존 파일을 Write로 통째로 바꾸기 전에 반드시 Read로 먼저 읽는다(도구 요구사항).
- dev 서버(포트 4321)를 켠 채 `npm run build`를 돌리면 EPERM/EMFILE이 날 수 있다. 실패하면 재시도하지 말고 보고한다.

**지켜야 할 것**
- 공개 HTML은 user-neutral이다(CDN 캐시, `middleware.ts`·`publicCachePolicy.ts`의 공유 캐시 구역). 분야 페이지에 `Astro.locals.isAdmin`/`user` 분기를 두지 않는다. 저장 버튼은 지금처럼 `data-bookmarked="false"`로 렌더하고 `content-status.ts`(→ `scripts/bookmark`)가 클라이언트에서 채운다.
- 스크립트는 번들 `<script>`만 쓴다(이 계획에 `is:inline` 없음). `is:inline`이 필요해지면 반드시 `nonce={Astro.locals.cspNonce || ''}`를 붙인다.
- 저장 버튼은 줄(`li.blog-list-item`) 안에 **줄당 한 개**(`content-status.ts`가 가까운 `.blog-list-item`에 읽음 표시를 한다. 같은 id 버튼은 첫 번째만 상태를 받는다 → 바이라인·"1화부터 읽기"에 버튼을 두지 않는다).
- `BlogSerialItem`의 ``<a class="blog-serial-title" href={`/${locale}/blog/${post.slug}/`}>{post.title}</a>`` 문자열은 그대로(목록 테스트·검색 스크립트가 읽는다). 목록 페이지는 `excerpt`를 넘기지 않으므로 목록 화면은 바뀌지 않는다.
- 남기는 것: `.blog-list-item`, `.blog-list-item:hover`, `.blog-list-item--read`(목록·`content-status.ts`·테스트), `.blog-category-badge`(+`::before`), `.blog-empty-state`, `.blog-empty-icon`, `--blog-shell-header-offset`(`BlogArticleLayout.astro` 343행 스크립트가 읽는다), ≤1023px의 `.blog-shell { display: block; min-height: auto; }`, `fetchCategoryGroups`(관리자 `admin/blog/categories`·`admin/settings`가 쓴다), `lib/categories.ts`.

**테스트 기준선**(2026-10-18, 계획 작성 시 실제 repo에서 측정): **PASS 83 / FAIL 18**
- 기준선 FAIL 18개와 첫 오류 메시지(경로는 `…`로 줄임)
  - admin-live-preview — `src/pages/admin/blog/edit/[slug].astro must sync preview state into URL history`
  - admin-v1-structure — `Missing admin sidebar settings section: activeSection?: 'posts' | 'handbook' | 'content' | 'settings';`
  - article-deck-font — `ENOENT … pages\en\log\[slug].astro`
  - auth-prompt-library-preview — `ENOENT … scripts\handbookFeedback.ts`
  - blog-sidebar-categories — `Blog categories must define the main posting group in the requested order` → **Task 3에서 파일 삭제**
  - blog-sidebar-layout — `Blog sidebar panel must use the shared card radius` → **Task 3에서 파일 삭제**(Task 2 뒤에도 같은 메시지 — 분야 페이지 툴바 단언은 그보다 뒤에 있다)
  - blog-title-fonts — `Missing IBM Plex Sans font import: IBM+Plex+Sans`(Task 3에서 선택자 목록을 고쳐도 첫 단언이 먼저 죽으므로 같은 메시지)
  - comments-admin-delete-contract — `Missing render delete button from API capability: c.can_delete`
  - content-feedback-contract — `ReferenceError: describe is not defined`
  - csp-inline-scripts — 첫 `Error:` 줄 없음(서버 필요, `fetch failed`)
  - detail-rail-copy — `Missing KO detail rail heading: 비슷한 뉴스 더 보기`
  - handbook-detail-table-overflow — `Handbook detail tables should define a compact horizontal scrollbar size on WebKit browsers`
  - handbook-search-recognition — `Handbook search input must define theme-specific input surface colors`
  - log-list-created-order — `ENOENT … pages\en\log\index.astro`
  - navigation-shell-copy — `English back copy must point to AI News`
  - news-fact-pack-structure — `layout must include sources accordion toggle`
  - public-slug-visibility — `Slug chip must be gated by showSlug`
  - sticky-reading-actions-structure — `Missing helpful action marker: data-reading-action="helpful"`
- 분야 페이지·`BlogShell`·삭제 대상 문자열을 읽는 기존 테스트(`grep -ln "BlogShell\|blog/category\|BlogSidebar\|blogSidebar\|BlogCategoryHeader\|BlogListItem\|blog-sidebar\|blog-folder\|blog-mobile-toolbar\|blog-mobile-toggle\|blog-category-\|blog-list-section\|blog-list-batch\|blog-scroll-sentinel\|blog-list-item\|blog-shell\|allPostsCount\|BlogSerialItem\|blogSerial\|blog-serial" frontend/tests/*`로 찾은 15개 전부)
  - 삭제(Task 2): `blog-detail-sidebar-structure.test.cjs`(`BlogShell`의 `mode`/`currentCategory` 전달, 분야 페이지 index 모드 사이드바를 고정 → Task 2에서 거짓이 됨. 남는 상세 로더 단언 3개는 `blog-category-toc.test.cjs`로 옮김), `blog-mobile-sidebar-structure.test.cjs`(`BlogShell`의 `data-sidebar-overlay` 고정. 남는 "페이지에 드로어 토글 없음" 단언은 새 테스트가 6개 페이지 전부로 넓혀 옮김).
  - 삭제(Task 3): `blog-detail-sidebar-behavior.test.mjs`(전부 `blogSidebar.ts` 모듈의 함수·상수 단언 — 다른 모듈 단언 없음), `blog-sidebar-categories.test.cjs`(사이드바 단언 + 이미 실패 중인 `categories.ts` 그룹 상수·없는 migration 파일 단언 — 사이드바와 무관한 앞부분은 기준선에서 이미 FAIL이라 옮기지 않는다), `blog-sidebar-layout.test.cjs`(사이드바 CSS·툴바. 남는 `--blog-shell-header-offset` 단언은 새 테스트로 옮김, `.blog-rail`·`.blog-toc` 부재는 `blog-post-column.test.cjs`가 이미 본다).
  - 고침: `blog-list-serial`(Task 2: shell 단언·`<BlogShell … sidebar={false}>` / Task 3: i18n 단언·유지 CSS 목록), `blog-post-column`(Task 2: `<BlogShell … sidebar={false}>` / Task 3: 유지 CSS 목록의 `.blog-mobile-toolbar {`), `blog-v2`(Task 3: `BlogListItem`·`BlogSidebar`·사이드바 CSS 단언), `blog-bookmark-card-contract`(Task 3: `BlogListItem` 단언), `blog-category-badge-font`(Task 3: `BlogListItem` → `BlogSerialItem`), `blog-title-fonts`(Task 3: `.blog-list-item-title` 선택자), `blog-serial`(Task 1: `categoryPage` 단언 추가).
  - 그대로 통과해야 함: `public-list-personalization`(목록 페이지·`content-status`의 `blog-list-item--read`), `blog-comment-fonts`(`.blog-shell .newsprint-comment-*` 남음), `cache-invalidation`(문자열 'blog'만), `public-error-cache-policy`(블로그 분야 페이지는 안 읽음).
- 기대값: Task 1 뒤 **PASS 83 / FAIL 18**(변화 없음), Task 2 뒤 **PASS 82 / FAIL 18**(`blog-category-toc` 신규 PASS, PASS였던 `blog-detail-sidebar-structure`·`blog-mobile-sidebar-structure` 삭제), Task 3 뒤 **PASS 81 / FAIL 16**(PASS였던 `blog-detail-sidebar-behavior`, FAIL이던 `blog-sidebar-categories`·`blog-sidebar-layout` 삭제). 남은 실패 16개의 첫 메시지는 기준선과 같아야 한다. 다른 세션 변경으로 숫자가 흔들릴 수 있으니 판정은 **이름 + 첫 오류 메시지 기준**으로 한다.
- 기준선은 Task 1 전에 다시 잡는다(Task 4의 명령으로 결과를 파일에 저장해 둔다).

**현재 코드**
- `pages/{ko,en}/blog/category/[slug].astro`(CRLF, 158줄, locale·문구만 다름): `fetchCategoryBySlug` → 없으면 404, `!is_visible && !Astro.locals.isAdmin`이면 404(이 경로는 공유 캐시 구역이라 `isAdmin`이 항상 비어 있음 → 실제로는 항상 404). 글은 `eq('category', slug)` + `created_at` 내림차순(제한 없음, `tags, reading_time_min, og_image_url` 등 더 많은 열) → 학습 노트 3화가 맨 위, `tech` 글 누락. `fetchCategories`·`fetchCategoryGroups`(사용 안 함) 병렬. `BlogShell`(사이드바 index 모드) 안에 `.blog-mobile-toolbar` 버튼, `BlogCategoryHeader`, 10개씩 `BlogListItem` 배치 + `data-blog-sentinel`, 빈 안내(📝 "아직 작성된 글이 없습니다" / "No posts yet"). 번들 `<script>`에 `import '../../../../scripts/bookmark';` + 무한 스크롤. 조회 오류 처리 없음(빈 안내 200).
- `BlogShell.astro`(LF, 49줄): `sidebar = true` 기본, true면 `BlogSidebar`(자체로 `fetchCategories`·`fetchCategoryGroups` 쿼리) + `.blog-sidebar-overlay`, false면 `blog-shell--single`. `showTOC`면 `toc` 슬롯. 호출처: ko/en `blog/index.astro`·`blog/[slug].astro`는 `sidebar={false}`, 분야 2곳은 기본값.
- `BlogSerialItem.astro`(LF, 54줄): `li.blog-list-item` 안에 회차(`.blog-serial-ep`) 또는 분야 점 라벨 칸(`.blog-serial-cat`), 제목 링크, 날짜, 저장 버튼. 목록 CSS `.blog-serial-list .blog-list-item`이 4열 격자(`auto minmax(0, 1fr) auto auto`).
- `blogSerial.js`: `normalizeBlogCategory`, `buildBlogFront`(main 보이는 분야 = 연재, 오래된 순), `locatePost`, `toSerialProps`, `formatBlogDate`(KST). 내부 `timeOf`·`oldestFirst`·`newestFirst`.
- 목록·상세 글 쿼리: `status = 'published'`, 같은 locale, `order('created_at', desc)`, `limit(100)`.
- CSS(`global.css` 9260행~): `/* Shell: sidebar + main + optional TOC */ .blog-shell`(변수 3개), `/* ── Left Sidebar ── */`부터 사이드바·폴더·footer·more·`/* Infinite scroll batch */`·`/* Mobile sidebar overlay */`·`.blog-mobile-toolbar`·`.blog-mobile-toggle`(한 덩어리), `@media (max-width: 1023px)`(`.blog-shell` + 사이드바 드로어·툴바), `/* ── Main Content ── */`, `.blog-category-badge`, `/* ── List Items (All Posts) ── */ .blog-list-section`, `.blog-list-item`(+hover), `.blog-list-item-left`~`.blog-list-item-category`, `.blog-list-item--read`, `@media (max-width: 639px)`(`.blog-list-item` wrap·meta), `/* ── Empty State ── */`, 목록 A 블록, `/* ── Category Header ── */`(`.blog-category-header`~`.blog-category-count`), `/* ── Article Header ── */`. 삭제 대상 선택자는 이 구간 밖에 없다(grep 확인).
- 운영 데이터(2026-10-18 anon으로 확인): 분야 5개 — study(학습 노트, main 0, 5편), project(프로젝트 기록, main 1, 5편), career(커리어 생각, main 2, 0편), work-note(작업 메모, sub 0, 1편), daily(일상, sub 1, 0편). 설명 전부 null. EN 글 0편. 학습 노트 5편은 KST로 모두 3월 11일(→ 바이라인 기간이 한 날짜 "3월 11일"). 순서: 1화 `llm-초보자를-위한-가장-쉬운-설명`, 2화 `rag-ai-retrieval-augmented-generation`, 3화 `ai-product-performance-cost-evaluation`, 4화 `prompt-rag-finetuning-when-needed`, 5화 `ai-agent`(요약 없음).

**스펙 해석·결정(실행자가 임의로 바꾸지 않는다)**
- `categoryPage`의 `counts`는 평범한 객체(`{ [slug]: n }`), 분야 없는 글은 세지 않는다. 분야가 categories에 없으면(호출 전 페이지가 막지만) `kind: 'notes'`. 짧은 글의 `posts`도 정규화된 얕은 복사본이다(`buildBlogFront`와 같음).
- 기간: `formatBlogDate`(KST, 연도 없음)로 만든 처음·마지막 날짜 문자열이 같으면 한 날짜, 다르면 `처음 ~ 마지막`. 짧은 글 바이라인의 날짜는 `range.last`.
- 바이라인의 분야 점 라벨은 연재에만(`span.blog-category-badge`, `--cat-color: category.color`). 짧은 글은 점 없이 텍스트. EN 짧은 글은 1편이면 단수 "1 short note"(스펙 표의 `{N} short notes`를 수에 맞춤 — `BlogFront`의 `post/posts`와 같은 처리).
- 다른 분야 순서: `fetchCategories` 순서(`group_slug` → `sort_order`)를 그대로 쓴다 → 연재 분야 먼저, 짧은 글 분야 뒤(스펙 "sort_order 순"을 그룹 안 순서로 해석. 전체 `sort_order`만으로 정렬하면 study·work-note·project·daily·career처럼 섞인다). 링크 하나가 "{라벨} {개수}"(`span.blog-cat-others-count`). 보이는 분야가 지금 분야 하나뿐이면 줄 생략.
- 0편 분야: 바이라인·목록 대신 빈 안내 + 다른 분야 줄. 글 조회 실패: 경로 줄·h1은 그대로, 그 아래 `NewsprintNotice`(error, 링크 `/{locale}/blog/` + `error.retry`)만(개수가 무의미하므로 다른 분야 줄 없음).
- 짧은 글 줄: 회차·분야 배지가 없어 첫 칸이 비면 격자 간격만큼 제목이 들여써진다(dry run에서 9.6px 확인). 그래서 `.blog-cat-list:not(.blog-cat-list--series)`에서 `.blog-serial-cat`을 숨기고 격자를 `minmax(0, 1fr) auto auto` 3열로, 요약을 `grid-column: 1`로 둔다(스펙에 없던 보완. 연재 줄은 스펙대로 4열 + 요약 `grid-column: 2; grid-row: 2`).
- `BlogShell`은 `locale` prop만 남긴다(지금은 안 쓰지만 호출처 6곳의 `locale="…"`을 건드리지 않기 위해). 주석·`class:list` 없이 `<div class="blog-shell blog-shell--single">`.
- 분야 페이지 `<BlogShell locale="ko">` 안 순서: `nav.blog-cat-crumb` → `h1.blog-cat-title` → (설명) → 본문. `MainLayout`의 title·description·slug는 현행 그대로.
- ≤1023px 블록의 `.blog-shell` 규칙과 `@media (max-width: 767px)`·`(min-width: 768px)`의 `.blog-main-inner` 여백은 그대로 둔다(스펙 "좌우 여백은 현행"). 639px `.blog-list-item` wrap 블록은 `BlogListItem` 전용(연재 줄은 grid라 `flex-wrap`이 의미 없음)이라 지운다.
- `blog-category-badge-font.test.cjs`는 `BlogListItem` 대신 `BlogSerialItem`의 `<span class="blog-category-badge" style=` 단언으로 바꾼다(배지 폰트 단언의 뜻 유지).

**계획 사전 검증(작성 시 scratchpad 복제본에서 수행)**
- `frontend/`(src, tests, public, scripts, examples, 설정 파일, `.env`; node_modules는 junction) 복제본에서 Task 1–3을 Edit/Write 도구와 이 문서의 CSS 스크립트로 적용했고, 문서 작성 뒤 **이 문서의 코드 블록을 그대로 뽑아** 깨끗한 두 번째 복제본에 다시 적용해 첫 복제본과 파일 단위로 같음을 확인했다.
- 복제본 기준선은 실제 repo와 이름·첫 오류 메시지 기준 동일(PASS 83 / FAIL 18, 메시지 안 경로만 다름).
- 각 "실패 확인" Step은 적힌 메시지로 실패, 통과 확인 Step은 PASS. Task 1 뒤 **PASS 83 / FAIL 18**, Task 2 뒤 **PASS 82 / FAIL 18**, Task 3 뒤 **PASS 81 / FAIL 16**, 실패 메시지는 기준선과 동일.
- `astro build` "Complete!"(Task 2·3 뒤). CSS 스크립트 출력은 Step에 적힌 값과 같았다.
- dev 서버(운영 데이터, 포트 4401, 확인 후 종료) + 브라우저 DOM 검사
  - `/ko/blog/category/study/` 200(1310px): 경로 줄 "← IT 블로그 · 연재", h1 "학습 노트", 바이라인 "연재 5편 · 3월 11일" + "1화부터 읽기 →"(→ 1화 `llm-초보자를-위한-가장-쉬운-설명`), 줄 5개 1화~5화 순서·링크가 목록 페이지 학습 노트 연재와 동일, 줄마다 저장 버튼 1개, 요약 4개(5화는 데이터 없음) `grid-column 2 / grid-row 2`, 줄 격자 `35px 632px 43px 32px`(4열 유지), 1화 번호 accent `rgb(180, 71, 42)` / 2화 muted, 다른 분야 "프로젝트 기록 5 · 커리어 생각 0 · 작업 메모 1 · 일상 0", `.blog-main-inner` 820px, 사이드바·툴바·오버레이 0, nonce 없는 인라인 `<script>` 0.
  - `/ko/blog/category/work-note/`: "← IT 블로그 · 짧은 글", "짧은 글 1편 · 마지막 글 3월 12일", "1화부터 읽기" 없음, 분야 배지 0, 줄 격자 3열(제목·요약 왼쪽 끝이 줄 왼쪽과 같음).
  - `/ko/blog/category/career/`: 빈 안내(📝 "아직 작성된 글이 없습니다") + 다른 분야 "학습 노트 5 · 프로젝트 기록 5 · 작업 메모 1 · 일상 0".
  - `/en/blog/category/study/`·`/en/blog/category/project/`: "← IT Blog · Series", 빈 안내 "No posts yet", "Other fields"(개수 모두 0).
  - `/ko/blog/category/nope/` 404.
  - 375px(모바일 에뮬레이션): 분야 5개 화면 + 목록 + 글 상세 모두 `scrollWidth` 375(넘침 0), 본문 351px, h1 30.4px(1.9rem), 바이라인 한 줄 유지(버튼 오른쪽), 요약은 제목 아래 두 줄 말줄임.
  - 회귀: `/ko/blog/` 820px 한 단, 연재·짧은 글 줄 11개, 요약 0개(목록은 excerpt 안 넘김), `/ko/blog/rag-ai-retrieval-augmented-generation/` 820px, 바이라인 "학습 노트 · 5편 중 2화", 분야 링크 `/ko/blog/category/study/`, 사이드바 0.

---

## Task 1: `categoryPage` 순수 함수 (TDD)

**Files:**
- Modify: `frontend/src/lib/blogSerial.js`(Edit 1곳)
- Test: `frontend/tests/blog-serial.test.mjs`(Edit 2곳)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/lib/blogSerial.js frontend/tests/blog-serial.test.mjs`
Expected: 출력 없음.

- [ ] **Step 1: 실패하는 단언 추가** — `frontend/tests/blog-serial.test.mjs`를 Edit 도구로 2곳 고친다.

1번(import) old:
```js
const { buildBlogFront, normalizeBlogCategory, formatBlogDate, locatePost, toSerialProps } = await import(
```
new:
```js
const { buildBlogFront, normalizeBlogCategory, formatBlogDate, locatePost, toSerialProps, categoryPage } = await import(
```

2번(파일 끝) old:
```js
assert.equal(formatBlogDate(null, 'ko', { year: true }), '');

console.log('blog-serial.test.mjs passed');
```
new:
```js
assert.equal(formatBlogDate(null, 'ko', { year: true }), '');

// --- blog field page A (series table of contents): categoryPage ---
const FIELD_CATS = [
  cat('study', 'main', 0),
  cat('project', 'main', 1),
  cat('career', 'main', 2),
  cat('work-note', 'sub', 0),
  cat('daily', 'sub', 1),
  cat('odd', 'legacy', 0),
  cat('loose', null, 0),
];
// created_at desc on purpose (like the query)
const FIELD = [
  post('w2', 'work-note', '2026-03-12T00:00:00Z'),
  post('st3', 'study', '2026-03-11T05:12:41Z'),
  post('w-undated', 'work-note', null),
  post('st2', 'study', '2026-03-11T04:32:08Z'),
  post('w1', 'work-note', '2026-03-05T00:00:00Z'),
  post('st1', 'tech', '2026-03-10T18:42:39Z'),
  post('p1', 'project', '2026-03-10T09:37:44Z'),
  post('o1', 'odd', '2026-03-09T00:00:00Z'),
  post('l1', 'loose', '2026-03-08T00:00:00Z'),
  post('nocat', null, '2026-03-07T00:00:00Z'),
];
// counted over every loaded post by normalized field (tech → study); posts without a field are not counted
const COUNTS = { 'work-note': 3, study: 3, project: 1, odd: 1, loose: 1 };

// series: the study entry of buildBlogFront (oldest first, legacy tech included), so episode = index + 1 matches the list page
const study = categoryPage(FIELD, FIELD_CATS, 'study');
assert.equal(study.kind, 'series');
assert.deepEqual(titles(study.posts), ['st1', 'st2', 'st3']);
assert.deepEqual(study.posts, buildBlogFront(FIELD, FIELD_CATS).series.find((s) => s.category.slug === 'study').posts, 'same episodes as the list page');
assert.equal(study.posts[0].category, 'study', 'legacy tech post is normalized into the study series');
assert.deepEqual(study.range, { first: '2026-03-10T18:42:39Z', last: '2026-03-11T05:12:41Z' });
assert.deepEqual(study.counts, COUNTS);
assert.equal(FIELD[5].category, 'tech', 'input posts are not mutated');

// main field without posts: still a series, empty list, no range
assert.deepEqual(categoryPage(FIELD, FIELD_CATS, 'career'), { kind: 'series', posts: [], range: null, counts: COUNTS });

// sub field: short notes, newest first, undated last
const workNotes = categoryPage(FIELD, FIELD_CATS, 'work-note');
assert.equal(workNotes.kind, 'notes');
assert.deepEqual(titles(workNotes.posts), ['w2', 'w1', 'w-undated']);
assert.deepEqual(workNotes.range, { first: '2026-03-05T00:00:00Z', last: '2026-03-12T00:00:00Z' }, 'range skips undated posts');
assert.deepEqual(categoryPage(FIELD, FIELD_CATS, 'daily'), { kind: 'notes', posts: [], range: null, counts: COUNTS });

// groups other than main (unknown or null): short notes
const odd = categoryPage(FIELD, FIELD_CATS, 'odd');
assert.deepEqual([odd.kind, titles(odd.posts)], ['notes', ['o1']]);
const loose = categoryPage(FIELD, FIELD_CATS, 'loose');
assert.deepEqual([loose.kind, titles(loose.posts)], ['notes', ['l1']]);

// range: one dated post → first = last; only undated posts → null
assert.deepEqual(categoryPage([post('a', 'work-note', '2026-03-01T00:00:00Z')], FIELD_CATS, 'work-note').range, { first: '2026-03-01T00:00:00Z', last: '2026-03-01T00:00:00Z' });
const undatedSeries = categoryPage([post('u', 'study', null)], FIELD_CATS, 'study');
assert.deepEqual([undatedSeries.kind, titles(undatedSeries.posts), undatedSeries.range], ['series', ['u'], null]);

// empty input
assert.deepEqual(categoryPage(null, null, 'study'), { kind: 'notes', posts: [], range: null, counts: {} });

console.log('blog-serial.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/blog-serial.test.mjs`
Expected: FAIL — `TypeError: categoryPage is not a function`

- [ ] **Step 3: 구현** — `frontend/src/lib/blogSerial.js`를 Edit 도구로 1곳 고친다(`toSerialProps` 뒤, `formatBlogDate` 앞에 함수 추가).

old:
```js
/**
 * "3월 11일" / "Mar 11" in KST (the server runs in UTC). '' when undated.
```
new:
```js
/**
 * One field page (blog field A: series table of contents). Same posts and rules as the list page, so the
 * episode numbers match the list and post pages. The page checks that the field exists and is visible first.
 * @param {Array<{id?: string, title: string, slug: string, category?: string|null, published_at?: string|null, excerpt?: string|null}>} posts
 * @param {Array<{slug: string, group_slug: string|null, sort_order?: number, is_visible: boolean}>} categories
 * @param {string} slug
 * @returns {{ kind: 'series'|'notes', posts: object[], range: {first: string, last: string}|null, counts: Record<string, number> }}
 *   kind: 'series' for the 'main' group, 'notes' otherwise (sub, other groups, null, or a field missing from categories).
 *   series posts = this field's entry of buildBlogFront().series (oldest first; episode = index + 1), [] without posts.
 *   notes posts = posts whose normalized field is slug, newest first, undated last.
 *   range = earliest and latest published_at among the dated posts of this field (null when none).
 *   counts = number of loaded posts per normalized field (posts without a field are not counted).
 */
export function categoryPage(posts, categories, slug) {
  const list = (Array.isArray(posts) ? posts : []).map((post) => ({ ...post, category: normalizeBlogCategory(post.category) }));
  const cats = Array.isArray(categories) ? categories : [];
  const category = cats.find((c) => c.slug === slug) || null;
  const kind = category && category.group_slug === 'main' ? 'series' : 'notes';

  let own;
  if (kind === 'series') {
    const series = buildBlogFront(list, cats).series.find((s) => s.category.slug === slug);
    own = series ? series.posts : [];
  } else {
    own = list.filter((post) => post.category === slug).sort(newestFirst);
  }

  const dated = own.filter((post) => timeOf(post.published_at) !== null).sort(oldestFirst);
  const range = dated.length > 0 ? { first: dated[0].published_at, last: dated[dated.length - 1].published_at } : null;

  const counts = {};
  for (const post of list) {
    if (post.category) counts[post.category] = (counts[post.category] || 0) + 1;
  }

  return { kind, posts: own, range, counts };
}

/**
 * "3월 11일" / "Mar 11" in KST (the server runs in UTC). '' when undated.
```

- [ ] **Step 4: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/blog-serial.test.mjs
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-post-column.test.cjs
```
Expected: 세 줄 모두 `… passed`.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/blogSerial.js frontend/tests/blog-serial.test.mjs
git commit -m "feat: add categoryPage for blog field pages"
```

---

## Task 2: 분야 페이지 연재 목차 + BlogShell 한 단 고정 (구조 테스트·페이지·컴포넌트·CSS)

**Files:**
- Create: `frontend/tests/blog-category-toc.test.cjs`
- Modify: `frontend/src/pages/ko/blog/category/[slug].astro`·`frontend/src/pages/en/blog/category/[slug].astro`(Write 통째), `frontend/src/components/blog/BlogShell.astro`(Write 통째), `frontend/src/components/blog/BlogSerialItem.astro`(Edit 2곳), `frontend/src/pages/{ko,en}/blog/index.astro`·`frontend/src/pages/{ko,en}/blog/[slug].astro`(Edit 각 1곳), `frontend/src/styles/global.css`(Edit 1곳)
- Test: `frontend/tests/blog-list-serial.test.cjs`(Edit 2곳), `frontend/tests/blog-post-column.test.cjs`(Edit 1곳)
- Delete: `frontend/tests/blog-detail-sidebar-structure.test.cjs`, `frontend/tests/blog-mobile-sidebar-structure.test.cjs`

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/pages/ko/blog frontend/src/pages/en/blog frontend/src/components/blog frontend/src/styles/global.css frontend/tests/blog-list-serial.test.cjs frontend/tests/blog-post-column.test.cjs frontend/tests/blog-detail-sidebar-structure.test.cjs frontend/tests/blog-mobile-sidebar-structure.test.cjs`
Expected: 출력 없음.

- [ ] **Step 1: 실패하는 구조 테스트 작성** — Write 도구로 `frontend/tests/blog-category-toc.test.cjs`를 아래 내용 그대로 만든다(Task 3에서 삭제 단언 블록을 더한다).

```js
// frontend/tests/blog-category-toc.test.cjs
// Blog field page A (series table of contents): one column, crumb, title, byline, rows with summaries, other fields.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const COPY = {
  ko: {
    crumbAria: 'aria-label="분야 위치"', back: '← IT 블로그', series: "'연재'", notes: "'짧은 글'",
    seriesByline: '연재 {count}편</span>{period && ` · ${period}`}', notesByline: '짧은 글 {count}편{lastDate && ` · 마지막 글 ${lastDate}`}',
    start: '1화부터 읽기 →', othersAria: 'aria-label="다른 분야"', others: '>다른 분야</span>',
    empty: ['<h2>아직 작성된 글이 없습니다</h2>', '<p>곧 새 글이 올라올 거예요.</p>'],
  },
  en: {
    crumbAria: 'aria-label="Field location"', back: '← IT Blog', series: "'Series'", notes: "'Short notes'",
    seriesByline: '{count}-part series</span>{period && ` · ${period}`}', notesByline: "{count} short note{count === 1 ? '' : 's'}{lastDate && ` · Latest ${lastDate}`}",
    start: 'Start from Ep. 1 →', othersAria: 'aria-label="Other fields"', others: '>Other fields</span>',
    empty: ['<h2>No posts yet</h2>', '<p>New posts coming soon.</p>'],
  },
};

// field pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/blog/category/[slug].astro`);
  const c = COPY[locale];
  for (const gone of ['BlogSidebar', 'blogSidebar', 'BlogCategoryHeader', 'BlogListItem', 'blog-mobile-toolbar', 'data-sidebar-toggle', 'data-blog-sentinel', 'data-blog-batch', 'IntersectionObserver', 'isAdmin', 'fetchCategoryGroups', 'is:inline', ".eq('category'", 'Astro.locals.user']) {
    assert(!page.includes(gone), `${locale}: ${gone} removed`);
  }
  // access: redirect without slug/DB, 404 for a missing or hidden field (no admin branch: shared-cache path)
  assert(page.includes(`return Astro.redirect('/${locale}/blog/');`), `${locale}: redirect without slug or DB`);
  assert(page.includes('if (!category || !category.is_visible) {\n  return new Response(null, { status: 404 });'), `${locale}: missing or hidden field → 404`);
  // data: same posts query as the list and post pages
  const queryAt = page.indexOf(".from('blog_posts')");
  const query = page.slice(queryAt, page.indexOf('.limit(100)', queryAt) + '.limit(100)'.length);
  assert(queryAt > 0 && query.includes(".select('id, title, slug, category, published_at, excerpt')") && query.includes(".eq('status', 'published')") && query.includes(".eq('locale', locale)") && query.includes(".order('created_at', { ascending: false })"), `${locale}: posts query = list page shape (published, locale, created_at desc, 100)`);
  assert(page.includes("import { categoryPage, formatBlogDate } from '../../../../lib/blogSerial.js';") && page.includes('const page = categoryPage(postsRes.data ?? [], dbCategories, slug);'), `${locale}: rows from categoryPage`);
  assert(page.includes("import { fetchCategories, fetchCategoryBySlug } from '../../../../lib/pageData/blogCategories';"), `${locale}: field + field list queries only`);
  // fetch failure: 503 + notice (never a cacheable 200 empty state)
  assert(/if \(fetchError\)\s*\{?\s*Astro\.response\.status = 503/.test(page), `${locale}: 503 on posts query error`);
  assert(page.includes(`<NewsprintNotice variant="error" message={t.${locale}['blog.error']}`), `${locale}: error notice`);
  // layout
  assert(page.includes(`<BlogShell locale="${locale}">`), `${locale}: one-column shell`);
  assert(page.includes(`<nav class="blog-cat-crumb" ${c.crumbAria}>`) && page.includes(`<a href="/${locale}/blog/">${c.back}</a>`), `${locale}: crumb back to the blog`);
  assert(page.includes(c.series) && page.includes(c.notes), `${locale}: kind label in the crumb`);
  assert(page.includes('<h1 class="blog-cat-title">{categoryLabel}</h1>') && page.includes('{categoryDesc && <p class="blog-cat-desc">{categoryDesc}</p>}'), `${locale}: h1 + description only when present`);
  assert(page.includes('{count > 0 ? (') && page.includes('<div class="blog-cat-byline">'), `${locale}: byline only with posts`);
  assert(page.includes(c.seriesByline) && page.includes(c.notesByline), `${locale}: byline copy`);
  assert(page.includes("const period = firstDate && firstDate !== lastDate ? `${firstDate} ~ ${lastDate}` : lastDate;"), `${locale}: one date when the period is a single day`);
  assert(page.includes(`<a class="blog-cat-start" href={\`/${locale}/blog/\${page.posts[0].slug}/\`}>${c.start}</a>`), `${locale}: start from episode 1`);
  assert(page.includes("<ol class:list={['blog-serial-list', 'blog-cat-list', { 'blog-cat-list--series': isSeries }]}>"), `${locale}: rows reuse the list page row grid`);
  assert(page.includes(`<BlogSerialItem locale="${locale}" post={post} episode={isSeries ? i + 1 : undefined} excerpt={post.excerpt} />`), `${locale}: BlogSerialItem with episode (series) and excerpt, no field label`);
  assert(page.includes(`<nav class="blog-cat-others" ${c.othersAria}>`) && page.includes(c.others), `${locale}: other fields`);
  assert(page.includes('const others = dbCategories.filter((c) => c.is_visible && c.slug !== slug);') && page.includes('{page.counts[c.slug] ?? 0}'), `${locale}: visible fields except this one, with counts`);
  assert(page.includes('<div class="blog-empty-state">') && page.includes('<div class="blog-empty-icon">📝</div>') && c.empty.every((s) => page.includes(s)), `${locale}: empty state copy kept`);
  assert(page.includes("<script>\n  import '../../../../scripts/bookmark';\n</script>"), `${locale}: bundled bookmark + content-status script`);
}

// row: optional summary after the title link (title string unchanged for the list page tests/search)
const item = read('components/blog/BlogSerialItem.astro');
assert(item.includes('excerpt?: string | null;') && item.includes('const { locale, post, episode, categoryLabel, categoryColor, excerpt } = Astro.props;'), 'row: excerpt prop');
assert(item.includes('<a class="blog-serial-title" href={`/${locale}/blog/${post.slug}/`}>{post.title}</a>\n  {excerpt && <p class="blog-serial-excerpt">{excerpt}</p>}'), 'row: summary right after the title');
const li = item.slice(item.indexOf('<li class="blog-list-item">'), item.indexOf('</li>'));
assert((li.match(/class="newsprint-bookmark-icon"/g) || []).length === 1, 'row: one bookmark button inside the li');

// shell: always one column, no sidebar props
const shell = read('components/blog/BlogShell.astro');
assert(shell.includes('<div class="blog-shell blog-shell--single">'), 'shell: single column always');
for (const gone of ['BlogSidebar', 'blogSidebar', 'sidebar?:', 'sidebarPosts', 'currentSlug', 'currentCategory', 'totalCount', 'mode', 'showTOC', 'slot name="toc"', 'data-sidebar-overlay', 'class:list']) {
  assert(!shell.includes(gone), `shell: ${gone} removed`);
}
for (const p of ['index.astro', '[slug].astro', 'category/[slug].astro']) {
  for (const locale of ['ko', 'en']) {
    const page = read(`pages/${locale}/blog/${p}`);
    assert(page.includes(`<BlogShell locale="${locale}">`) && !page.includes('sidebar='), `${locale}/blog/${p}: BlogShell without sidebar props`);
    assert(!page.includes('data-sidebar-toggle') && !page.includes('initBlogMobileToggle') && !page.includes('initMobileSidebarToggle'), `${locale}/blog/${p}: no drawer toggle`);
  }
}

// moved from blog-detail-sidebar-structure: the post page list window feeds locatePost (same 100-post window as the list)
const detailLoader = read('lib/pageData/blogDetailPage.ts');
assert(!detailLoader.includes("from './blogSidebar'"), 'Blog detail loader must not build a sidebar dataset');
assert(!detailLoader.includes('.limit(4)') && detailLoader.includes('.limit(100)'), 'Blog detail list window must match the list page (100 posts)');
assert(!detailLoader.includes(".neq('slug', pageSlug)"), 'Blog detail list window must not exclude the current slug');

// CSS
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
assert(/max-width:\s*820px/.test(rule('.blog-shell--single .blog-main-inner')), 'one column up to 820px');
assert(rule('.blog-cat-title').includes('var(--font-blog-heading)') && /font-weight:\s*700/.test(rule('.blog-cat-title')) && /font-size:\s*2\.5rem/.test(rule('.blog-cat-title')), 'title: Hahmlet 700, 2.5rem');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-cat-byline')) && /border-bottom:\s*1px solid var\(--color-text-primary\)/.test(rule('.blog-cat-byline')) && /justify-content:\s*space-between/.test(rule('.blog-cat-byline')), 'byline: 2px ink rule above, 1px below, both ends');
assert(rule('.blog-cat-list--series > .blog-list-item:first-child .blog-serial-ep').includes('color: var(--color-accent)'), 'episode 1 in the accent color');
assert(/grid-column:\s*2;/.test(rule('.blog-serial-excerpt')) && /grid-row:\s*2;/.test(rule('.blog-serial-excerpt')) && /-webkit-line-clamp:\s*2/.test(rule('.blog-serial-excerpt')), 'summary: title column, second row, two lines');
assert(/grid-template-columns:\s*minmax\(0, 1fr\) auto auto/.test(rule('.blog-cat-list:not(.blog-cat-list--series) .blog-list-item')) && rule('.blog-cat-list:not(.blog-cat-list--series) .blog-serial-cat').includes('display: none') && /grid-column:\s*1;/.test(rule('.blog-cat-list:not(.blog-cat-list--series) .blog-serial-excerpt')), 'short notes: no empty first cell (title flush left, summary under it)');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-cat-others')) && /flex-wrap:\s*wrap/.test(rule('.blog-cat-others-list')), 'other fields: ink rule, wrapping links');
const mobileAt = css.indexOf('/* Blog field page A: mobile */');
assert(mobileAt > 0, 'field page mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.blog-cat-title\s*\{[^}]*font-size:\s*1\.9rem/.test(mobile), 'mobile: title 1.9rem');
for (const kept of ['.blog-list-item {', '.blog-list-item:hover {', '.blog-list-item--read {', '.blog-category-badge {', '.blog-empty-state {', '.blog-empty-icon {']) {
  assert(css.includes(kept), `CSS kept: ${kept}`);
}

console.log('blog-category-toc.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/blog-category-toc.test.cjs`
Expected: FAIL — `AssertionError [ERR_ASSERTION]: ko: BlogSidebar removed`

- [ ] **Step 3: KO 분야 페이지** — `frontend/src/pages/ko/blog/category/[slug].astro`(CRLF)를 Read한 뒤 Write로 통째 교체한다.

```astro
---
export const prerender = false;

import MainLayout from '../../../../layouts/MainLayout.astro';
import { t } from '../../../../i18n/index';
import { supabase } from '../../../../lib/supabase';
import { fetchCategories, fetchCategoryBySlug } from '../../../../lib/pageData/blogCategories';
import { categoryPage, formatBlogDate } from '../../../../lib/blogSerial.js';
import BlogShell from '../../../../components/blog/BlogShell.astro';
import BlogSerialItem from '../../../../components/blog/BlogSerialItem.astro';
import NewsprintNotice from '../../../../components/newsprint/NewsprintNotice.astro';

const locale = 'ko';
const { slug } = Astro.params;

if (!slug || !supabase) {
  return Astro.redirect('/ko/blog/');
}

// Missing or hidden field: 404 for everyone. This path is in the shared-cache zone (no session), so there is no admin branch.
const category = await fetchCategoryBySlug(supabase, slug);
if (!category || !category.is_visible) {
  return new Response(null, { status: 404 });
}

// Same posts query as the list and post pages (100 newest by created_at), so episode numbers match.
const [postsRes, dbCategories] = await Promise.all([
  supabase
    .from('blog_posts')
    .select('id, title, slug, category, published_at, excerpt')
    .eq('status', 'published')
    .eq('locale', locale)
    .order('created_at', { ascending: false })
    .limit(100),
  fetchCategories(supabase),
]);

let fetchError: string | null = null;
if (postsRes.error) {
  console.error('[blog-category-ko] Supabase error:', postsRes.error.message);
  fetchError = postsRes.error.message;
}
if (fetchError) Astro.response.status = 503;

const page = categoryPage(postsRes.data ?? [], dbCategories, slug);
const isSeries = page.kind === 'series';
const count = page.posts.length;
const firstDate = formatBlogDate(page.range?.first, locale);
const lastDate = formatBlogDate(page.range?.last, locale);
const period = firstDate && firstDate !== lastDate ? `${firstDate} ~ ${lastDate}` : lastDate;
const others = dbCategories.filter((c) => c.is_visible && c.slug !== slug);

const categoryLabel = category.label_ko;
const categoryDesc = category.description_ko;
const pageTitle = `${categoryLabel} | ${t.ko['blog.title']}`;
const pageDescription = category.description_ko || `${categoryLabel} 카테고리의 글 모음`;
---

<MainLayout
  title={pageTitle}
  locale="ko"
  slug={`blog/category/${slug}/`}
  description={pageDescription}
>
  <BlogShell locale="ko">
    <nav class="blog-cat-crumb" aria-label="분야 위치">
      <a href="/ko/blog/">← IT 블로그</a>
      <span aria-hidden="true">·</span>
      <span>{isSeries ? '연재' : '짧은 글'}</span>
    </nav>

    <h1 class="blog-cat-title">{categoryLabel}</h1>
    {categoryDesc && <p class="blog-cat-desc">{categoryDesc}</p>}

    {fetchError ? (
      <NewsprintNotice variant="error" message={t.ko['blog.error']} linkHref="/ko/blog/" linkLabel={t.ko['error.retry']} />
    ) : (
      <>
        {count > 0 ? (
          <>
            <div class="blog-cat-byline">
              {isSeries ? (
                <p class="blog-cat-byline-meta">
                  <span class="blog-category-badge" style={`--cat-color: ${category.color || 'var(--color-border)'}`}>연재 {count}편</span>{period && ` · ${period}`}
                </p>
              ) : (
                <p class="blog-cat-byline-meta">짧은 글 {count}편{lastDate && ` · 마지막 글 ${lastDate}`}</p>
              )}
              {isSeries && (
                <a class="blog-cat-start" href={`/ko/blog/${page.posts[0].slug}/`}>1화부터 읽기 →</a>
              )}
            </div>

            <ol class:list={['blog-serial-list', 'blog-cat-list', { 'blog-cat-list--series': isSeries }]}>
              {page.posts.map((post, i) => (
                <BlogSerialItem locale="ko" post={post} episode={isSeries ? i + 1 : undefined} excerpt={post.excerpt} />
              ))}
            </ol>
          </>
        ) : (
          <div class="blog-empty-state">
            <div class="blog-empty-icon">📝</div>
            <h2>아직 작성된 글이 없습니다</h2>
            <p>곧 새 글이 올라올 거예요.</p>
          </div>
        )}

        {others.length > 0 && (
          <nav class="blog-cat-others" aria-label="다른 분야">
            <span class="blog-cat-others-label">다른 분야</span>
            <ul class="blog-cat-others-list">
              {others.map((c) => (
                <li>
                  <a href={`/ko/blog/category/${c.slug}/`}>{c.label_ko} <span class="blog-cat-others-count">{page.counts[c.slug] ?? 0}</span></a>
                </li>
              ))}
            </ul>
          </nav>
        )}
      </>
    )}
  </BlogShell>
</MainLayout>

<script>
  import '../../../../scripts/bookmark';
</script>
```

- [ ] **Step 4: EN 분야 페이지** — `frontend/src/pages/en/blog/category/[slug].astro`(CRLF)를 Read한 뒤 Write로 통째 교체한다.

```astro
---
export const prerender = false;

import MainLayout from '../../../../layouts/MainLayout.astro';
import { t } from '../../../../i18n/index';
import { supabase } from '../../../../lib/supabase';
import { fetchCategories, fetchCategoryBySlug } from '../../../../lib/pageData/blogCategories';
import { categoryPage, formatBlogDate } from '../../../../lib/blogSerial.js';
import BlogShell from '../../../../components/blog/BlogShell.astro';
import BlogSerialItem from '../../../../components/blog/BlogSerialItem.astro';
import NewsprintNotice from '../../../../components/newsprint/NewsprintNotice.astro';

const locale = 'en';
const { slug } = Astro.params;

if (!slug || !supabase) {
  return Astro.redirect('/en/blog/');
}

// Missing or hidden field: 404 for everyone. This path is in the shared-cache zone (no session), so there is no admin branch.
const category = await fetchCategoryBySlug(supabase, slug);
if (!category || !category.is_visible) {
  return new Response(null, { status: 404 });
}

// Same posts query as the list and post pages (100 newest by created_at), so episode numbers match.
const [postsRes, dbCategories] = await Promise.all([
  supabase
    .from('blog_posts')
    .select('id, title, slug, category, published_at, excerpt')
    .eq('status', 'published')
    .eq('locale', locale)
    .order('created_at', { ascending: false })
    .limit(100),
  fetchCategories(supabase),
]);

let fetchError: string | null = null;
if (postsRes.error) {
  console.error('[blog-category-en] Supabase error:', postsRes.error.message);
  fetchError = postsRes.error.message;
}
if (fetchError) Astro.response.status = 503;

const page = categoryPage(postsRes.data ?? [], dbCategories, slug);
const isSeries = page.kind === 'series';
const count = page.posts.length;
const firstDate = formatBlogDate(page.range?.first, locale);
const lastDate = formatBlogDate(page.range?.last, locale);
const period = firstDate && firstDate !== lastDate ? `${firstDate} ~ ${lastDate}` : lastDate;
const others = dbCategories.filter((c) => c.is_visible && c.slug !== slug);

const categoryLabel = category.label_en;
const categoryDesc = category.description_en;
const pageTitle = `${categoryLabel} | ${t.en['blog.title']}`;
const pageDescription = category.description_en || `Posts in the ${categoryLabel} category`;
---

<MainLayout
  title={pageTitle}
  locale="en"
  slug={`blog/category/${slug}/`}
  description={pageDescription}
>
  <BlogShell locale="en">
    <nav class="blog-cat-crumb" aria-label="Field location">
      <a href="/en/blog/">← IT Blog</a>
      <span aria-hidden="true">·</span>
      <span>{isSeries ? 'Series' : 'Short notes'}</span>
    </nav>

    <h1 class="blog-cat-title">{categoryLabel}</h1>
    {categoryDesc && <p class="blog-cat-desc">{categoryDesc}</p>}

    {fetchError ? (
      <NewsprintNotice variant="error" message={t.en['blog.error']} linkHref="/en/blog/" linkLabel={t.en['error.retry']} />
    ) : (
      <>
        {count > 0 ? (
          <>
            <div class="blog-cat-byline">
              {isSeries ? (
                <p class="blog-cat-byline-meta">
                  <span class="blog-category-badge" style={`--cat-color: ${category.color || 'var(--color-border)'}`}>{count}-part series</span>{period && ` · ${period}`}
                </p>
              ) : (
                <p class="blog-cat-byline-meta">{count} short note{count === 1 ? '' : 's'}{lastDate && ` · Latest ${lastDate}`}</p>
              )}
              {isSeries && (
                <a class="blog-cat-start" href={`/en/blog/${page.posts[0].slug}/`}>Start from Ep. 1 →</a>
              )}
            </div>

            <ol class:list={['blog-serial-list', 'blog-cat-list', { 'blog-cat-list--series': isSeries }]}>
              {page.posts.map((post, i) => (
                <BlogSerialItem locale="en" post={post} episode={isSeries ? i + 1 : undefined} excerpt={post.excerpt} />
              ))}
            </ol>
          </>
        ) : (
          <div class="blog-empty-state">
            <div class="blog-empty-icon">📝</div>
            <h2>No posts yet</h2>
            <p>New posts coming soon.</p>
          </div>
        )}

        {others.length > 0 && (
          <nav class="blog-cat-others" aria-label="Other fields">
            <span class="blog-cat-others-label">Other fields</span>
            <ul class="blog-cat-others-list">
              {others.map((c) => (
                <li>
                  <a href={`/en/blog/category/${c.slug}/`}>{c.label_en} <span class="blog-cat-others-count">{page.counts[c.slug] ?? 0}</span></a>
                </li>
              ))}
            </ul>
          </nav>
        )}
      </>
    )}
  </BlogShell>
</MainLayout>

<script>
  import '../../../../scripts/bookmark';
</script>
```

- [ ] **Step 5: 줄 컴포넌트에 요약** — `frontend/src/components/blog/BlogSerialItem.astro`를 Edit 도구로 2곳 고친다.

1번(prop) old:
```astro
  categoryColor?: string;
}

const { locale, post, episode, categoryLabel, categoryColor } = Astro.props;
```
new:
```astro
  categoryColor?: string;
  /** field page: summary under the title (grid row 2); the list page does not pass it */
  excerpt?: string | null;
}

const { locale, post, episode, categoryLabel, categoryColor, excerpt } = Astro.props;
```

2번(제목 뒤) old:
```astro
  <a class="blog-serial-title" href={`/${locale}/blog/${post.slug}/`}>{post.title}</a>
```
new:
```astro
  <a class="blog-serial-title" href={`/${locale}/blog/${post.slug}/`}>{post.title}</a>
  {excerpt && <p class="blog-serial-excerpt">{excerpt}</p>}
```

- [ ] **Step 6: BlogShell 한 단 고정** — `frontend/src/components/blog/BlogShell.astro`를 Read한 뒤 Write로 통째 교체한다.

```astro
---
// frontend/src/components/blog/BlogShell.astro
// Blog page frame: one centred column for the list, post and field pages (the left sidebar was removed 2026-10-18).
interface Props {
  locale: 'en' | 'ko';
}
---

<div class="blog-shell blog-shell--single">
  <div class="blog-main">
    <div class="blog-main-inner">
      <slot />
    </div>
  </div>
</div>
```

- [ ] **Step 7: 목록·상세 호출처에서 `sidebar={false}` 삭제** — Edit 도구로 4개 파일을 각각 1곳 고친다.

`frontend/src/pages/ko/blog/index.astro`와 `frontend/src/pages/ko/blog/[slug].astro` old:
```astro
  <BlogShell locale="ko" sidebar={false}>
```
new:
```astro
  <BlogShell locale="ko">
```

`frontend/src/pages/en/blog/index.astro`와 `frontend/src/pages/en/blog/[slug].astro` old:
```astro
  <BlogShell locale="en" sidebar={false}>
```
new:
```astro
  <BlogShell locale="en">
```

Run: `grep -rn "sidebar=\|showTOC\|sidebarPosts\|currentCategory=" frontend/src/pages`
Expected: 출력 없음.

- [ ] **Step 8: CSS 추가** — `frontend/src/styles/global.css`를 Edit 도구로 1곳 고친다(목록 A 모바일 블록 뒤, `/* ── Category Header ── */` 바로 앞. 그 주석은 파일에 한 번만 있다).

old:
```css
/* ── Category Header ── */
```
new:
```css
/* ── Blog field page A: series table of contents (crumb, title, byline, rows, other fields) ── */
.blog-cat-crumb {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.4rem;
  margin: 0 0 1rem;
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.blog-cat-crumb a {
  color: var(--color-text-secondary);
  text-decoration: none;
}

.blog-cat-crumb a:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.blog-cat-title {
  margin: 0 0 0.5rem;
  font-family: var(--font-blog-heading);
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.03em;
  color: var(--color-text-primary);
}

.blog-cat-desc {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  line-height: 1.65;
  color: var(--color-text-secondary);
}

.blog-cat-byline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem 1.5rem;
  padding: 0.55rem 0;
  border-top: 2px solid var(--color-text-primary);
  border-bottom: 1px solid var(--color-text-primary);
  margin: 1.25rem 0 0.5rem;
}

.blog-cat-byline-meta {
  margin: 0;
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.blog-cat-byline-meta .blog-category-badge {
  font-size: 0.85rem;
  color: var(--color-text-primary);
}

.blog-cat-start {
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
  white-space: nowrap;
}

.blog-cat-start:hover {
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.blog-cat-list {
  margin-bottom: 3rem;
}

.blog-cat-list--series > .blog-list-item:first-child .blog-serial-ep {
  color: var(--color-accent);
}

/* Summary under the title: row 2 of the title column, so the 4-column row grid stays intact. */
.blog-serial-excerpt {
  grid-column: 2;
  grid-row: 2;
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Short notes: no episode/field cell (an empty first cell would indent the title by the grid gap). */
.blog-cat-list:not(.blog-cat-list--series) .blog-list-item {
  grid-template-columns: minmax(0, 1fr) auto auto;
}

.blog-cat-list:not(.blog-cat-list--series) .blog-serial-cat {
  display: none;
}

.blog-cat-list:not(.blog-cat-list--series) .blog-serial-excerpt {
  grid-column: 1;
}

.blog-cat-others {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem 1.25rem;
  padding-top: 0.6rem;
  border-top: 2px solid var(--color-text-primary);
  margin-bottom: 3rem;
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
}

.blog-cat-others-label {
  font-weight: 700;
  color: var(--color-text-primary);
}

.blog-cat-others-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.blog-cat-others-list a {
  color: var(--color-text-secondary);
  text-decoration: none;
}

.blog-cat-others-list a:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.blog-cat-others-count {
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
}

/* Blog field page A: mobile */
@media (max-width: 767px) {
  .blog-cat-title {
    font-size: 1.9rem;
  }
}

/* ── Category Header ── */
```

- [ ] **Step 9: 기존 테스트 갱신** (Edit 도구로)

`frontend/tests/blog-list-serial.test.cjs` 1번(shell) old:
```js
// shell: sidebar prop (default true). The list and post pages pass false; category pages keep the sidebar.
const shell = read('components/blog/BlogShell.astro');
assert(shell.includes('sidebar?: boolean;') && shell.includes('sidebar = true,'), 'shell: sidebar prop defaults to true');
assert(/\{sidebar && \(\s*<>\s*<BlogSidebar[\s\S]*?data-sidebar-overlay><\/div>\s*<\/>\s*\)\}/.test(shell), 'shell: sidebar + overlay only when sidebar');
assert(shell.includes("class:list={['blog-shell', { 'blog-shell--single': !sidebar }]}"), 'shell: single-column modifier');
for (const p of ['pages/ko/blog/category/[slug].astro', 'pages/en/blog/category/[slug].astro']) {
  assert(!read(p).includes('sidebar={false}'), `${p} keeps the sidebar`);
}
for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro']) {
  assert(read(p).includes('sidebar={false}'), `${p} is one column (blog post A)`);
}
```
new:
```js
// shell: always one column (blog field A, 2026-10-18: the field pages lost the sidebar too, so the prop is gone)
const shell = read('components/blog/BlogShell.astro');
assert(shell.includes('<div class="blog-shell blog-shell--single">') && !shell.includes('BlogSidebar') && !shell.includes('sidebar?:'), 'shell: one column, no sidebar prop');
for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro', 'pages/ko/blog/category/[slug].astro', 'pages/en/blog/category/[slug].astro']) {
  assert(!read(p).includes('sidebar='), `${p}: no sidebar prop`);
}
```

`frontend/tests/blog-list-serial.test.cjs` 2번(목록 페이지) old:
```js
  assert(page.includes(`<BlogShell locale="${locale}" sidebar={false}>`), `${locale}: list renders without the sidebar`);
```
new:
```js
  assert(page.includes(`<BlogShell locale="${locale}">`), `${locale}: list renders in the one-column shell`);
```

`frontend/tests/blog-post-column.test.cjs` old:
```js
  assert(page.includes(`<BlogShell locale="${locale}" sidebar={false}>`), `${locale}: post renders without the sidebar`);
```
new:
```js
  assert(page.includes(`<BlogShell locale="${locale}">`), `${locale}: post renders in the one-column shell`);
```

- [ ] **Step 10: 사이드바 연결을 고정하던 테스트 2개 삭제** (남는 단언은 Step 1의 새 테스트로 옮겼다: 상세 로더 3개, 드로어 토글 없음)

```bash
git rm frontend/tests/blog-detail-sidebar-structure.test.cjs frontend/tests/blog-mobile-sidebar-structure.test.cjs
```

- [ ] **Step 11: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/blog-category-toc.test.cjs
node frontend/tests/blog-serial.test.mjs
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-post-column.test.cjs
node frontend/tests/blog-v2.test.cjs
node frontend/tests/blog-bookmark-card-contract.test.cjs
node frontend/tests/blog-category-badge-font.test.cjs
node frontend/tests/public-list-personalization.test.cjs
node frontend/tests/blog-detail-sidebar-behavior.test.mjs
node frontend/tests/blog-sidebar-layout.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 테스트를 뺀 모두 `… passed` / `… ok`, 빌드 "Complete!".
- `blog-sidebar-layout` FAIL `Blog sidebar panel must use the shared card radius` — 기준선과 **같은 메시지**(Task 3에서 파일 삭제).

- [ ] **Step 12: 커밋**

```bash
git add "frontend/src/pages/ko/blog/category/[slug].astro" "frontend/src/pages/en/blog/category/[slug].astro" frontend/src/components/blog/BlogShell.astro frontend/src/components/blog/BlogSerialItem.astro frontend/src/pages/ko/blog/index.astro "frontend/src/pages/ko/blog/[slug].astro" frontend/src/pages/en/blog/index.astro "frontend/src/pages/en/blog/[slug].astro" frontend/src/styles/global.css frontend/tests/blog-category-toc.test.cjs frontend/tests/blog-list-serial.test.cjs frontend/tests/blog-post-column.test.cjs
git commit -m "feat: blog field page as a series table of contents"
```

(`git rm`으로 stage된 테스트 2개 삭제가 함께 커밋된다.)

---

## Task 3: 사이드바·옛 분야 화면 컴포넌트, CSS, i18n, 테스트 정리 (TDD)

**Files:**
- Delete: `frontend/src/components/blog/BlogSidebar.astro`, `frontend/src/lib/pageData/blogSidebar.ts`, `frontend/src/components/blog/BlogCategoryHeader.astro`, `frontend/src/components/blog/BlogListItem.astro`, `frontend/tests/blog-detail-sidebar-behavior.test.mjs`, `frontend/tests/blog-sidebar-categories.test.cjs`, `frontend/tests/blog-sidebar-layout.test.cjs`
- Modify: `frontend/src/styles/global.css`(Edit 1곳 + 삭제 스크립트), `frontend/src/i18n/index.ts`(CRLF, Edit 2곳)
- Test: `frontend/tests/blog-category-toc.test.cjs`(Edit 1곳), `blog-list-serial.test.cjs`(2곳), `blog-post-column.test.cjs`(1곳), `blog-v2.test.cjs`(3곳), `blog-bookmark-card-contract.test.cjs`(3곳), `blog-category-badge-font.test.cjs`(2곳), `blog-title-fonts.test.cjs`(1곳)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/components/blog frontend/src/lib/pageData/blogSidebar.ts frontend/src/styles/global.css frontend/src/i18n/index.ts frontend/tests`
Expected: 다른 세션 파일(`frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`) 줄만 나온다. 그 밖의 줄이 있으면 BLOCKED.

- [ ] **Step 1: 실패하는 단언 추가** — `frontend/tests/blog-category-toc.test.cjs`의 마지막 줄 앞에 Edit 도구로 블록을 넣는다(블록 끝과 `console.log` 사이 빈 줄 한 줄).

old:
```js
  assert(css.includes(kept), `CSS kept: ${kept}`);
}

console.log('blog-category-toc.test.cjs passed');
```
new:
```js
  assert(css.includes(kept), `CSS kept: ${kept}`);
}

// removed with the sidebar (Task 3): components, the sidebar helper, their CSS and i18n key
for (const file of ['components/blog/BlogSidebar.astro', 'lib/pageData/blogSidebar.ts', 'components/blog/BlogCategoryHeader.astro', 'components/blog/BlogListItem.astro']) {
  assert(!fs.existsSync(path.join(src, file)), `${file} deleted`);
}
for (const gone of ['.blog-sidebar', '.blog-folder', '.blog-mobile-toolbar', '.blog-mobile-toggle', '.blog-category-header', '.blog-category-banner', '.blog-category-title', '.blog-category-icon', '.blog-category-description', '.blog-category-count', '.blog-list-section', '.blog-list-batch', '.blog-scroll-sentinel', '--blog-shell-rail-gap', '--blog-shell-panel-radius']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(!/\.blog-list-item-[a-z]/.test(css), 'unused CSS removed: BlogListItem parts (.blog-list-item-title, -meta, …; .blog-list-item--read stays)');
assert(css.includes('--blog-shell-header-offset: 5rem;'), 'header offset kept (BlogArticleLayout reads it)');
assert(/@media \(max-width: 1023px\) \{\n  \.blog-shell \{\n    display: block;\n    min-height: auto;\n  \}\n\}/.test(css), '1023px block keeps only the shared shell rule');
assert(!read('i18n/index.ts').includes("'blog.allPostsCount'"), 'sidebar-only i18n key removed');
for (const gone of ['blog-detail-sidebar-behavior.test.mjs', 'blog-detail-sidebar-structure.test.cjs', 'blog-mobile-sidebar-structure.test.cjs', 'blog-sidebar-categories.test.cjs', 'blog-sidebar-layout.test.cjs']) {
  assert(!fs.existsSync(path.join(__dirname, gone)), `deleted: tests/${gone}`);
}

console.log('blog-category-toc.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/blog-category-toc.test.cjs`
Expected: FAIL — `AssertionError [ERR_ASSERTION]: components/blog/BlogSidebar.astro deleted`

- [ ] **Step 3: 사용처가 없음을 확인**

Run:
```bash
grep -rln "BlogSidebar\|blogSidebar\|BlogCategoryHeader\|BlogListItem\|allPostsCount" frontend/src
grep -rln "blog-sidebar\|blog-folder\|blog-mobile-to\|blog-category-header\|blog-category-banner\|blog-category-title\|blog-category-icon\|blog-category-description\|blog-category-count\|blog-list-section\|blog-list-batch\|blog-scroll-sentinel\|data-sidebar-\|data-blog-batch\|data-blog-sentinel\|blog-shell-rail-gap\|blog-shell-panel-radius" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rln "[^-]blog-list-item-[a-z]" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rln "BlogSidebar\|blogSidebar\|BlogCategoryHeader\|BlogListItem\|allPostsCount\|blog-sidebar\|blog-folder\|blog-mobile-to\|blog-list-section\|blog-list-batch\|blog-scroll-sentinel\|\.blog-list-item-[a-z]\|blog-shell-rail-gap\|blog-shell-panel-radius" frontend/tests
```
Expected:
- 첫 줄: `frontend/src/components/blog/BlogSidebar.astro`, `frontend/src/i18n/index.ts`, `frontend/src/lib/pageData/blogSidebar.ts` 세 줄뿐(삭제 대상 자신과 Step 6에서 지울 i18n 키. 분야 페이지·`BlogShell`에는 없음).
- 둘째 줄: `frontend/src/components/blog/BlogCategoryHeader.astro`, `frontend/src/components/blog/BlogSidebar.astro` 두 줄뿐.
- 셋째 줄: `frontend/src/components/blog/BlogListItem.astro` 한 줄뿐(`home-blog-list-item-*`은 앞의 `[^-]`로 빠진다).
- 넷째 줄: `blog-bookmark-card-contract.test.cjs`, `blog-category-badge-font.test.cjs`, `blog-category-toc.test.cjs`(부재 단언), `blog-detail-sidebar-behavior.test.mjs`, `blog-list-serial.test.cjs`, `blog-post-column.test.cjs`, `blog-sidebar-categories.test.cjs`, `blog-sidebar-layout.test.cjs`, `blog-title-fonts.test.cjs`, `blog-v2.test.cjs` 10개뿐(모두 Step 7·8에서 고치거나 지운다).
- 하나라도 다르면 멈추고 보고한다.

- [ ] **Step 4: 컴포넌트·헬퍼 삭제**

```bash
git rm frontend/src/components/blog/BlogSidebar.astro frontend/src/lib/pageData/blogSidebar.ts frontend/src/components/blog/BlogCategoryHeader.astro frontend/src/components/blog/BlogListItem.astro
```

- [ ] **Step 5: 안 쓰는 CSS 삭제**

1. `frontend/src/styles/global.css`를 Edit 도구로 1곳 고친다(셸 주석 + 사이드바 전용 변수 2개).

old:
```css
/* Shell: sidebar + main + optional TOC */
.blog-shell {
  --blog-shell-header-offset: 5rem;
  --blog-shell-rail-gap: 1rem;
  --blog-shell-panel-radius: 1.5rem;
```
new:
```css
/* Shell: one centred column (list, post and field pages) */
.blog-shell {
  --blog-shell-header-offset: 5rem;
```

2. Write 도구로 scratchpad에 `drop-blog-sidebar-css.cjs`를 아래 내용 그대로 만든다(repo 밖, 커밋하지 않음).

```js
// Removes the blog CSS that only the sidebar, the old field page (BlogCategoryHeader, infinite scroll, mobile toolbar)
// and BlogListItem used. Each cut removes lines [start - before, end): start = the only line equal to `from`,
// end = first line equal to `to` after it. The line count must match `expected`, otherwise nothing is written.
// Run from the repo root.
const fs = require('fs');

const file = 'frontend/src/styles/global.css';
const lines = fs.readFileSync(file, 'utf8').split('\n');

function cut(name, from, to, expected, { before = 0 } = {}) {
  const at = lines.indexOf(from);
  if (at < 0) throw new Error(`${name}: start not found: ${from}`);
  if (lines.indexOf(from, at + 1) >= 0) throw new Error(`${name}: start is not unique: ${from}`);
  const end = lines.indexOf(to, at + 1);
  if (end < 0) throw new Error(`${name}: end not found: ${to}`);
  const start = at - before;
  if (end - start !== expected) {
    throw new Error(`${name}: expected ${expected} lines, found ${end - start} (lines ${start + 1}-${end})`);
  }
  lines.splice(start, end - start);
  console.log(`${name}: removed ${expected} lines from line ${start + 1}`);
}

// 1. sidebar, folders, sidebar footer/more, infinite scroll batch + sentinel, overlay, mobile toolbar + toggle
cut('sidebar', '/* ── Left Sidebar ── */', '@media (max-width: 1023px) {', 363);
// 2. sidebar drawer + toolbar inside the 1023px query (the shared .blog-shell rule and the closing brace stay)
cut('mobile sidebar', '  .blog-sidebar {', '}', 26, { before: 1 });
// 3. old field page list wrapper
cut('list section', '.blog-list-section {', '.blog-list-item {', 5);
// 4. BlogListItem-only rules (.blog-list-item, :hover and --read stay)
cut('list item parts', '.blog-list-item-left {', '.blog-list-item--read {', 60);
// 5. BlogListItem 639px wrap (serial rows are grids)
cut('list item 639px', '  .blog-list-item-meta {', '/* ── Empty State ── */', 12, { before: 5 });
// 6. BlogCategoryHeader
cut('category header', '/* ── Category Header ── */', '/* ── Article Header ── */', 57);

fs.writeFileSync(file, lines.join('\n'));
console.log('done');
```

3. repo 루트에서 `node <scratchpad>/drop-blog-sidebar-css.cjs` → 아래 출력(시작 줄 번호는 달라질 수 있다. **줄 수**가 다르면 아무것도 쓰지 않고 오류 → 멈추고 보고):
```
sidebar: removed 363 lines from line 9279
mobile sidebar: removed 26 lines from line 9284
list section: removed 5 lines from line 9358
list item parts: removed 60 lines from line 9381
list item 639px: removed 12 lines from line 9385
category header: removed 57 lines from line 9854
done
```

- 지워지는 것: `/* ── Left Sidebar ── */`부터 `.blog-sidebar*`(search·nav·link·footer), `.blog-folder*`, `/* Sidebar folder "more" button */`, `/* Infinite scroll batch */ .blog-list-batch[hidden]`·`.blog-scroll-sentinel`, `/* Mobile sidebar overlay */ .blog-sidebar-overlay(--open)`, `.blog-mobile-toolbar`, `.blog-mobile-toggle(:hover)`; ≤1023px 블록 안 `.blog-sidebar`·`.blog-sidebar--open`·`.blog-mobile-toolbar`; `.blog-list-section`; `.blog-list-item-left`~`.blog-list-item-category`(`.blog-list-item:hover .blog-list-item-title` 포함); 639px `.blog-list-item` wrap·meta 블록; `/* ── Category Header ── */`부터 `.blog-category-count`까지.
- 남는 것: `.blog-shell`(+`--blog-shell-header-offset`), ≤1023px `.blog-shell { display: block; min-height: auto; }`, `/* ── Main Content ── */` 이하, `.blog-category-badge`, `/* ── List Items (All Posts) ── */ .blog-list-item`·`:hover`·`--read`, `/* ── Empty State ── */`, 목록 A 블록, Task 2 분야 페이지 블록, `/* ── Article Header ── */` 이하.

Run:
```bash
grep -n "blog-sidebar\|blog-folder\|blog-mobile-to\|blog-category-header\|blog-category-banner\|blog-category-title\|blog-category-icon\|blog-category-description\|blog-category-count\|blog-list-section\|blog-list-batch\|blog-scroll-sentinel\|blog-shell-rail-gap\|blog-shell-panel-radius\|\.blog-list-item-[a-z]" frontend/src/styles/global.css
grep -n "^\.blog-list-item {\|^\.blog-list-item:hover {\|^\.blog-list-item--read {\|^\.blog-category-badge {\|^\.blog-empty-state {\|--blog-shell-header-offset: 5rem;" frontend/src/styles/global.css
```
Expected: 첫 줄 결과 없음. 둘째 줄 6줄.

- [ ] **Step 6: i18n 키 삭제** — `frontend/src/i18n/index.ts`(CRLF)를 Edit 도구로 2곳 고친다(통째 Write 금지).

1번(en) old:
```ts
    'blog.search': 'Search...',
    'blog.allPostsCount': 'All Posts',
```
new:
```ts
    'blog.search': 'Search...',
```

2번(ko) old:
```ts
    'blog.search': '검색...',
    'blog.allPostsCount': '전체 글',
```
new:
```ts
    'blog.search': '검색...',
```

Run: `grep -c "allPostsCount" frontend/src/i18n/index.ts; git diff --stat -- frontend/src/i18n/index.ts`
Expected: `0`, 그리고 `1 file changed, 2 deletions(-)`(줄바꿈 전체가 바뀌었다고 나오면 Write로 저장된 것 → 멈추고 보고).

- [ ] **Step 7: 기존 테스트 갱신** (Edit 도구로)

`frontend/tests/blog-list-serial.test.cjs` 1번(i18n) old:
```js
assert(!i18n.includes("'blog.featured'") && !i18n.includes("'blog.allPosts'") && i18n.includes("'blog.allPostsCount'"), 'unused i18n keys removed (sidebar count key kept)');
```
new:
```js
assert(!i18n.includes("'blog.featured'") && !i18n.includes("'blog.allPosts'") && !i18n.includes("'blog.allPostsCount'"), 'unused i18n keys removed');
```

`frontend/tests/blog-list-serial.test.cjs` 2번(유지 CSS) old:
```js
// still used by the category pages / article layout
for (const kept of ['.blog-list-batch[hidden] {', '.blog-scroll-sentinel {', '.blog-mobile-toolbar {', '.blog-list-section {', '.blog-mono-tag {', '.blog-category-badge {', '.blog-masthead-tagline {']) {
```
new:
```js
// still used by the article layout and field pages (the old field page CSS is checked in blog-category-toc.test.cjs)
for (const kept of ['.blog-mono-tag {', '.blog-category-badge {', '.blog-masthead-tagline {']) {
```

`frontend/tests/blog-post-column.test.cjs` old:
```js
// still used elsewhere: category pages (toolbar), news/handbook layouts and handbook-popup.ts (persona float)
for (const kept of ['.blog-mobile-toolbar {', '.persona-float {',
```
new:
```js
// still used elsewhere: news/handbook layouts and handbook-popup.ts (persona float)
for (const kept of ['.persona-float {',
```

`frontend/tests/blog-v2.test.cjs` 1번 old:
```js
for (const p of ['components/blog/BlogSerialItem.astro', 'components/blog/BlogListItem.astro']) {
```
new:
```js
for (const p of ['components/blog/BlogSerialItem.astro']) {
```

`frontend/tests/blog-v2.test.cjs` 2번 old:
```js
assert(css.includes('.blog-category-badge::before {') && rule('.blog-category-badge::before').includes('var(--cat-color, var(--color-accent))'), 'category color lives only on the dot');
assert(!/style=\{`color:/.test(read('components/blog/BlogSidebar.astro')), 'sidebar folder icon has no inline color');
```
new:
```js
assert(css.includes('.blog-category-badge::before {') && rule('.blog-category-badge::before').includes('var(--cat-color, var(--color-accent))'), 'category color lives only on the dot');
```

`frontend/tests/blog-v2.test.cjs` 3번 old:
```js
assert(read('pages/en/blog/index.astro').includes('A column on building, learning and keeping notes'), 'en tagline');
assert(/@media \(max-width: 1023px\)\s*\{[\s\S]*?\.blog-sidebar\s*\{[^}]*background:\s*var\(--color-bg-primary\)/.test(css), 'mobile sidebar drawer keeps an opaque background');

// 사이드바 패널 정리
const sidebar = rule('.blog-sidebar');
assert(/box-shadow:\s*none/.test(sidebar) && /border-radius:\s*0/.test(sidebar), 'sidebar is not a floating rounded panel');
assert(!rule('.blog-folder-btn--group').includes('uppercase'), 'sidebar group labels not uppercase');
```
new:
```js
assert(read('pages/en/blog/index.astro').includes('A column on building, learning and keeping notes'), 'en tagline');
```

`frontend/tests/blog-bookmark-card-contract.test.cjs` 1번 old:
```js
const serialItem = read('frontend/src/components/blog/BlogSerialItem.astro');
const listItem = read('frontend/src/components/blog/BlogListItem.astro');
```
new:
```js
const serialItem = read('frontend/src/components/blog/BlogSerialItem.astro');
```

`frontend/tests/blog-bookmark-card-contract.test.cjs` 2번 old:
```js
// list page rows (series episodes + short notes): the button lives inside li.blog-list-item (read-state target)
```
new:
```js
// list and field page rows (series episodes + short notes): the button lives inside li.blog-list-item (read-state target)
```

`frontend/tests/blog-bookmark-card-contract.test.cjs` 3번 old:
```js
assertIncludes(serialItem, 'data-bookmarked="false"', 'blog serial bookmark neutral SSR state');

assertIncludes(listItem, 'isBookmarked?: boolean;', 'blog list bookmark prop');
assertIncludes(listItem, 'itemId?: string;', 'blog list bookmark item id prop');
assertIncludes(listItem, "itemType?: 'blog';", 'blog list bookmark item type prop');
assertIncludes(listItem, 'newsprint-bookmark-icon', 'blog list bookmark button markup');
assertIncludes(listItem, 'data-item-id={itemId}', 'blog list bookmark item id binding');
assertIncludes(listItem, 'data-item-type={itemType}', 'blog list bookmark item type binding');
```
new:
```js
assertIncludes(serialItem, 'data-bookmarked="false"', 'blog serial bookmark neutral SSR state');
```

`frontend/tests/blog-category-badge-font.test.cjs` 1번 old:
```js
const listItem = fs.readFileSync(path.join(process.cwd(), 'frontend/src/components/blog/BlogListItem.astro'), 'utf8');
```
new:
```js
const serialItem = fs.readFileSync(path.join(process.cwd(), 'frontend/src/components/blog/BlogSerialItem.astro'), 'utf8');
```

`frontend/tests/blog-category-badge-font.test.cjs` 2번 old:
```js
assert(listItem.includes('class="blog-list-item-category blog-category-badge"'), 'List item category should include blog-category-badge');
```
new:
```js
assert(serialItem.includes('<span class="blog-category-badge" style='), 'Short-note row field label should use blog-category-badge');
```

`frontend/tests/blog-title-fonts.test.cjs` old:
```js
const selectors = ['.blog-list-item-title', '.blog-serial-title', '.blog-article-title'];
```
new:
```js
const selectors = ['.blog-serial-title', '.blog-article-title'];
```

- [ ] **Step 8: 사이드바 테스트 3개 삭제** (`blog-detail-sidebar-behavior`는 `blogSidebar.ts` 함수·상수만 본다 — 옮길 단언 없음. `blog-sidebar-layout`의 남는 `--blog-shell-header-offset` 단언은 Step 1 블록으로 옮겼다. `blog-sidebar-categories`의 앞부분(`categories.ts` 그룹 상수·migration 파일)은 기준선에서 이미 FAIL이라 옮기지 않는다)

```bash
git rm frontend/tests/blog-detail-sidebar-behavior.test.mjs frontend/tests/blog-sidebar-categories.test.cjs frontend/tests/blog-sidebar-layout.test.cjs
```

- [ ] **Step 9: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/blog-category-toc.test.cjs
node frontend/tests/blog-serial.test.mjs
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-post-column.test.cjs
node frontend/tests/blog-v2.test.cjs
node frontend/tests/blog-bookmark-card-contract.test.cjs
node frontend/tests/blog-category-badge-font.test.cjs
node frontend/tests/blog-comment-fonts.test.cjs
node frontend/tests/public-list-personalization.test.cjs
node frontend/tests/blog-title-fonts.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 테스트를 뺀 모두 `… passed` / `… ok` / `… present`, 빌드 "Complete!".
- `blog-title-fonts` FAIL `Missing IBM Plex Sans font import: IBM+Plex+Sans` — 기준선과 **같은 메시지**.

- [ ] **Step 10: 커밋**

```bash
git add frontend/src/styles/global.css frontend/src/i18n/index.ts frontend/tests/blog-category-toc.test.cjs frontend/tests/blog-list-serial.test.cjs frontend/tests/blog-post-column.test.cjs frontend/tests/blog-v2.test.cjs frontend/tests/blog-bookmark-card-contract.test.cjs frontend/tests/blog-category-badge-font.test.cjs frontend/tests/blog-title-fonts.test.cjs
git commit -m "chore: remove blog sidebar, old field page components and unused CSS"
```

(`git rm`으로 stage된 컴포넌트·헬퍼 4개와 테스트 3개 삭제가 함께 커밋된다.)

---

## Task 4: 검증 (컨트롤러)

- [ ] 전체 테스트를 **이름 + 첫 오류 메시지로** 기준선(PASS 83 / FAIL 18)과 비교한다.
  ```bash
  for f in frontend/tests/*.cjs frontend/tests/*.mjs; do out=$(node "$f" 2>&1) && echo "PASS $(basename $f)" || echo "FAIL $(basename $f) :: $(echo "$out" | grep -m1 -E '^[A-Za-z]*Error( \[[A-Z_]+\])?: ')"; done
  ```
  - 실패 목록은 기준선 18개에서 `blog-sidebar-categories`·`blog-sidebar-layout`만 빠진 16개여야 한다(신규 FAIL 0). 첫 오류 메시지도 기준선과 같은지 본다.
  - 이름 변화는 `blog-category-toc` 신규 PASS, `blog-detail-sidebar-structure`·`blog-mobile-sidebar-structure`·`blog-detail-sidebar-behavior`(PASS) 및 `blog-sidebar-categories`·`blog-sidebar-layout`(FAIL) 삭제뿐 → **PASS 81 / FAIL 16**.
- [ ] `cd frontend && npm run build` "Complete!".
- [ ] 브라우저(`.claude/launch.json`의 `frontend-dev`, 포트 4321) 매트릭스: 종이·순백·다크 × 1100px·375px × ko/en, 대상 `study`(연재 5편), `work-note`(짧은 글 1편), `career`(0편), en `study`(0편 빈 안내)
  - 스크린샷(테마·폭·locale마다), 가로 넘침 0(`document.documentElement.scrollWidth <= window.innerWidth`)
  - 대비 검사: 경로 줄(secondary), h1, 바이라인(secondary·점 라벨 primary), "1화부터 읽기"(accent), 1화 번호(accent)·다른 회차(muted), 제목, 요약(secondary), 날짜(muted), 다른 분야 라벨(primary)·링크(secondary)·개수(muted), 빈 안내
  - ≥768px: h1 2.5rem, 바이라인 양 끝, 줄 4열(연재)·3열(짧은 글), 요약이 제목 아래(날짜·저장 버튼 열을 밀지 않음). ≤767px: h1 1.9rem, 바이라인 줄바꿈 허용, 다른 분야 줄바꿈, 넘침 0.
- [ ] 직접 클릭
  - "1화부터 읽기" → 1화 글(상세 바이라인 "학습 노트 · 5편 중 1화"), 각 줄 제목 → 해당 글, 회차가 목록 페이지·글 상세와 같은지 대조.
  - 저장 버튼(줄당 1개): 비로그인 → 로그인 안내, 로그인 상태면 토글(가능하면). 읽은 글 줄 흐리게(`blog-list-item--read`).
  - 다른 분야 링크 → 해당 분야, 경로 줄 "← IT 블로그" → 목록.
  - 없는 분야(`/ko/blog/category/nope/`) 404.
- [ ] 회귀: 목록 페이지(820px 한 단, 연재·짧은 글·검색, 요약 없음), 글 상세(820px, 바이라인·이전/다음·연재 목록), 둘 다 사이드바 없음·폭 동일.
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 5: 문서

- [ ] 스펙 [[2026-10-18-blog-category-toc-design]] Status를 `implemented (YYYY-MM-DD)`로 바꾼다.
- [ ] 이 계획의 Status를 `done (YYYY-MM-DD) — 실행 결과는 문서 끝 참조.`로 바꾸고, 문서 끝에 "## 실행 결과 (YYYY-MM-DD)"(커밋 해시, 테스트 이름 비교 결과, 빌드, 매트릭스·클릭 결과, 계획 대비 변경, 후속)를 적는다.
- [ ] `ACTIVE_SPRINT.md`의 `REDESIGN-PRODUCT-DETAIL` 항목 아래 `- **증거:** 커밋 3d697589, 12e2f1b0, 12475893, …` 줄 **바로 다음 줄**에 추가한다(그 아래 `27e00b48` 증거 줄은 건드리지 않는다).
  ```
  - [x] **REDESIGN-BLOG-CATEGORY** — 블로그 분야 페이지를 연재 목차(A)로: 가운데 한 단, 경로 줄(← IT 블로그 · 연재/짧은 글), 분야 h1, 바이라인(연재 N편 · 기간 | 1화부터 읽기), 목록과 같은 줄 + 요약, 다른 분야(개수), 0편 빈 안내, 조회 실패 503, 숨김 분야 항상 404, 글 쿼리를 목록·상세와 같은 100편 창으로(회차 일치·tech 포함), BlogShell 사이드바 prop 제거, BlogSidebar·blogSidebar.ts·BlogCategoryHeader·BlogListItem·사이드바 CSS·allPostsCount 삭제 — [[2026-10-18-blog-category-toc-design]], [[2026-10-18-blog-category-toc]]
    - **증거:** 커밋 <Task 1>, <Task 2>, <Task 3>, 신규 FAIL 0, 빌드 성공, <매트릭스·클릭 요약>
  ```
- [ ] `grep -rln "BlogSidebar\|blogSidebar\|BlogCategoryHeader\|BlogListItem\|blog-sidebar\|sidebar={false}" vault --include=*.md`로 관련 노트를 찾는다. `90-Archive/`와 이번 스펙·계획, 지난 날짜의 완료된 계획 본문은 빼고, 블로그의 **현재 구조**를 설명하는 노트만 최소한으로 고친다(예: "분야 페이지는 2026-10-18 연재 목차(A)로 대체, 블로그에 사이드바 없음" 한 줄).
- [ ] 알려진 한계·후속을 실행 결과에 적는다: 분야 설명 데이터 없음(전부 null — `p.blog-cat-desc`는 조건부), 글 100편 초과 시 목록과 같은 한계(개수도 100편 기준), `fetchCategoryBySlug` 조회 오류가 404로 캐시되는 현행 한계, 분야 배너·아이콘 데이터 미사용, EN 글 0편이라 EN 줄 화면은 빈 안내로만 확인.
- [ ] 커밋(고친 vault 노트 경로만 지정해 add한다. `vault/.obsidian/*`는 넣지 않는다):
  ```bash
  git add vault/09-Implementation/plans/2026-10-18-blog-category-toc-design.md vault/09-Implementation/plans/2026-10-18-blog-category-toc.md vault/09-Implementation/plans/ACTIVE_SPRINT.md
  git commit -m "docs: record blog category table-of-contents redesign"
  ```
  (Task 5에서 고친 다른 vault 노트가 있으면 그 경로도 `git add`에 더한다.)

---

## 실행 결과 (2026-10-18)

- 커밋: `04985ba2` categoryPage 순수 함수, `38030e5c` 분야 페이지를 연재 목차로(경로 줄·바이라인·1화부터 읽기·회차 목록·요약·다른 분야·빈 안내·503, BlogShell 한 단 고정), `73fe590b` 블로그 사이드바·옛 분야 컴포넌트·미사용 CSS·`blog.allPostsCount` 삭제.
- 테스트: PASS 81 / FAIL 16(기준선 83 / 18). 변화는 `blog-category-toc` 추가, 통과하던 사이드바 테스트 3개(`blog-detail-sidebar-structure`·`blog-mobile-sidebar-structure`·`blog-detail-sidebar-behavior`)와 실패하던 2개(`blog-sidebar-categories`·`blog-sidebar-layout`) 삭제. 남은 16개 실패는 이름·첫 오류 동일, 신규 FAIL 0. 빌드 성공(Task 2·3 후). 계획 단계에서 scratch 복사본 2벌 + 운영 데이터 렌더로 사전 검증.
- 브라우저 클릭 검증(/ko/blog/category/study/): 사이드바 없음, 경로 줄 "← IT 블로그 · 연재", 바이라인 "연재 5편 · 3월 11일 | 1화부터 읽기 →", 1~5화가 목록 페이지와 같은 순서·링크, 요약이 제목 아래(4열 격자 유지), 저장 버튼 줄당 1개(5개), 다른 분야 "프로젝트 기록 5 · 커리어 생각 0 · 작업 메모 1 · 일상 0". "1화부터 읽기" 클릭 → 1화 글, 상세 바이라인 "학습 노트 · 5편 중 1화"로 회차 일치. 없는 분야 404, 스크립트 nonce 누락 0.
- 매트릭스: 종이·순백·다크 × 1100px·375px, 대상 study(연재 5)·work-note(짧은 글 1, "마지막 글 3월 12일")·career(0편 빈 안내)·en study(0편 빈 안내) — 가로 넘침 0, 대비 미달 0. 회귀: 목록·글 상세 폭 동일, 사이드바 없음. 글 상세 순백 테마의 `reading-actions__count` 2.60은 스캐너가 `oklab()` 배경을 못 읽은 오탐(실제 #5A544B on L 0.94 배경).
- 계획 단계 결정: 짧은 글 줄은 3열 격자(빈 첫 칸 들여쓰기 제거), 다른 분야는 DB 순서(그룹 → sort_order), EN 단수 "1 short note", 오류 화면은 경로 줄·제목·안내만, BlogShell은 `locale` prop 유지.
