# 블로그 글 상세 A(칼럼 한 편) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** done (2026-10-17) — 실행 결과는 문서 끝 참조.

**Goal:** `/ko|en/blog/{slug}/`를 세 칸(폴더 트리 · 본문 · 액션+목차 레일)에서 목록과 같은 한 단(최대 820px)으로 바꾼다. 위에서부터 "경로 줄(← IT 블로그 · 분야 · n화) → 제목 → 요약 → 바이라인(Amy · 연도 포함 날짜 · 읽기 시간 / 분야 · N편 중 n화) → 이 글의 차례(접히는 `details`) → 본문 + 공용 인라인 액션 → 태그 · 관리자 · 피드백 → 이전·다음(같은 연재의 앞·뒤 회차) → 연재 목록 → 댓글(h2)"이다. "다음 글"이 거꾸로 가던 버그(더 이른 글로 이동)도 함께 사라진다.

**Architecture:**
- 순수 모듈 `lib/blogSerial.js`에 `locatePost(posts, categories, slug)`(연재·회차·앞뒤 글)와 `toSerialProps(located, categories, locale, category)`(레이아웃 `serial` prop)를 더하고, `formatBlogDate`에 `{ year: true }` 옵션을 단다. 연재 계산은 목록과 같은 `buildBlogFront`를 그대로 쓴다.
- `blogDetailPage.ts`: 글 목록 쿼리를 목록 페이지와 같은 모양(`created_at desc`, 100편, `title, slug, category, published_at`)으로 바꾸고 "다음 글" 쿼리와 사이드바 데이터셋을 없앤다(`.from('blog_posts')` 4 → 3).
- ko/en `[slug].astro`: `BlogShell sidebar={false}`, 레일·`toc` 슬롯·모바일 툴바를 없애고 `serial`을 계산해 넘긴다.
- `BlogArticleLayout.astro`: 경로 줄 · 요약 · 바이라인 · 차례(`details` + 번들 스크립트) · 인라인 `StickyReadingActions` · 이전·다음 · 연재 목록 · 댓글 h2. 옛 메타 줄 · `newsprint-article-nav` · 떠 있는 "목록으로" 버튼을 없앤다.
- Task 3에서 블로그 상세 전용이던 `BlogTOC`·`BlogBreadcrumb`·`ReadingActionsRail`, `StickyReadingActions`의 `placement="rail"` 분기, 그 CSS, i18n `blog.onThisPage`를 지운다.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-10-17-blog-post-column-design]] — 구현 전에 반드시 읽는다. 시안: `.superpowers/brainstorm/blogpost/post-v1.html`(A안).

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `frontend/src/pages/admin/pipeline-runs/*`, `frontend/src/lib/pageData/publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 **읽기만 하고 수정·stage하지 않는다**. `blogDetailPage.ts`는 `publicTermIndex.ts`를 import만 한다 — 그 파일은 절대 건드리지 않는다.
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- **백슬래시가 있는 파일은 Write/Edit 도구로만 작성한다.** Bash heredoc을 쓰면 백슬래시가 사라진다. 해당: 테스트 파일 전부(정규식), `BlogArticleLayout.astro`(차례 스크립트의 정규식), Task 3의 CSS 삭제 스크립트. 새/교체 파일은 전부 Write 도구로 만든다.
- 번호 목록 안의 `old`/`new` 코드 블록은 목록 들여쓰기 때문에 줄마다 앞에 공백 3칸이 더 붙어 있다. Edit할 때 그 3칸을 빼고 쓴다(그 안의 원래 들여쓰기는 그대로). 목록 밖 코드 블록은 그대로 쓴다.
- Astro/JS 파일의 문자열에는 `\uXXXX` 이스케이프를 쓰지 않는다. `·`, `←`, `→`, `—`, 한글은 **문자 그대로** 쓴다(이 계획의 코드 블록도 전부 문자 그대로다).
- 줄바꿈·인코딩
  - `pages/{ko,en}/blog/[slug].astro`, `components/blog/BlogArticleLayout.astro`, `lib/pageData/blogDetailPage.ts`는 작업 트리 **CRLF**다. Read 후 **Write로 통째 교체**한다(LF로 저장됨). git 인덱스는 LF이고 `core.autocrlf=true`라 줄바꿈 차이는 diff에 나오지 않는다.
  - `frontend/src/i18n/index.ts`는 작업 트리 **CRLF**다. **Edit 도구로만** 고친다(Write·sed 금지).
  - `blogSerial.js`, `StickyReadingActions.astro`, `global.css`, 테스트 파일은 LF다. CSS 규칙은 줄 번호가 아니라 셀렉터/주석으로 찾는다.
  - 기존 파일을 Write로 통째로 바꾸기 전에 반드시 Read로 먼저 읽는다(도구 요구사항).
- dev 서버(포트 4321)를 켠 채 `npm run build`를 돌리면 EPERM/EMFILE이 날 수 있다. 실패하면 재시도하지 말고 보고한다.

**지켜야 할 것**
- 공개 HTML은 user-neutral이다(CDN 캐시). `Astro.locals` 사용자 상태로 새로 마크업을 가르지 않는다. 기존 `isAdmin`/`isAuthenticated` 전달은 그대로 둔다. 저장·좋아요 상태는 `data-bookmarked="false"`/`data-liked="false"`로 렌더되고 클라이언트가 채운다.
- `[data-item-id][data-item-type="blog"]` 버튼은 페이지에 **하나**다(`StickyReadingActions`의 저장 버튼). `recordReadingHistory`와 `content-status.ts`가 이 버튼을 찾는다. 이전·다음 카드와 연재 목록에는 버튼을 두지 않는다.
- 새 스크립트는 번들 `<script>`다(`is:inline` 아님 → nonce 불필요, 미들웨어가 모듈 스크립트에 nonce를 붙인다). `is:inline`을 써야 하면 반드시 `nonce={Astro.locals.cspNonce || ''}`를 붙인다(이 계획에는 없다).
- 분야 페이지(`pages/*/blog/category/[slug].astro`)는 사이드바·`.blog-mobile-toolbar`·`BlogSidebar` 데이터셋(`buildBlogSidebarDataset`)을 계속 쓴다. `lib/pageData/blogSidebar.ts`, `BlogShell`의 `mode`/`currentCategory` prop, `.blog-mobile-toolbar` CSS는 지우지 않는다.
- `.persona-float*` CSS는 뉴스·용어 레이아웃과 `handbook-popup.ts`가 쓰므로 남긴다(블로그 레이아웃의 `persona-float--back` 마크업만 지운다).
- 뉴스·용어 상세의 액션 막대는 바뀌지 않는다. 블로그도 공용 `.reading-actions-layout--article` CSS를 그대로 쓴다(1024px 이상 본문 오른쪽 72px 세로 막대, 미만 하단 바). 블로그 전용 재정의를 넣지 않는다.

**테스트 기준선**(2026-10-17, 계획 작성 시 실제 repo에서 측정): **PASS 82 / FAIL 19**
- 기준선 FAIL 19개와 첫 오류 메시지
  - admin-live-preview — `src/pages/admin/blog/edit/[slug].astro must sync preview state into URL history`
  - admin-v1-structure — `Missing admin sidebar settings section: …`
  - article-deck-font — `ENOENT … pages\en\log\[slug].astro`
  - auth-prompt-library-preview — `ENOENT … scripts\handbookFeedback.ts`
  - blog-sidebar-categories — `Blog categories must define the main posting group in the requested order`
  - blog-sidebar-layout — `Blog sidebar panel must use the shared card radius`
  - blog-title-fonts — `Missing IBM Plex Sans font import: IBM+Plex+Sans`
  - comments-admin-delete-contract — `Missing render delete button from API capability: c.can_delete`
  - content-feedback-contract — `ReferenceError: describe is not defined`
  - csp-inline-scripts — `fetch failed`(서버 필요)
  - detail-rail-copy — `Missing KO detail rail heading: 비슷한 뉴스 더 보기`
  - handbook-detail-table-overflow, handbook-search-recognition, log-list-created-order, navigation-shell-copy, news-fact-pack-structure, product-detail-scenarios-theme, public-slug-visibility — 이번 작업과 무관
  - sticky-reading-actions-structure — `Missing helpful action marker: data-reading-action="helpful"`
- 이번 작업과 닿는 기존 실패(작업 뒤에도 **같은 메시지**여야 한다)
  - `blog-sidebar-layout`: 27행에서 먼저 실패한다. 우리가 바꾸는 19–22행(Task 3), 59–62행(Task 3), 84–88행(Task 2)은 27행보다 앞이거나 뒤다. **19–22행은 27행보다 앞**이라 `.blog-rail` CSS를 지우는 Task 3에서 반드시 함께 바꾼다(안 바꾸면 첫 메시지가 달라진다).
  - `sticky-reading-actions-structure`: 40행(helpful)에서 실패한다. Task 3에서 31–33행(`placementClass`)을 바꾸는데, 새 단언은 통과해야 한다(실패하면 첫 메시지가 달라진다).
  - `admin-live-preview`, `auth-prompt-library-preview`, `content-feedback-contract`는 블로그 레이아웃을 읽지만 그 전에 실패한다. 그래도 레이아웃에서 `previewMode?: boolean;`, `data-preview-mode`, `Admin preview`, `Preview mode · comments are read-only.`, `data-auth-action="comment"`, `#comments`, `ContentFeedback`를 유지한다.
- 완료 후 기대값: `blog-post-column` 신규 PASS, `blog-toc-structure` 삭제(Task 3) → **PASS 82 / FAIL 19, 실패 목록·첫 메시지 기준선과 동일, 신규 FAIL 0**. 다른 세션 변경으로 숫자가 흔들릴 수 있으니 판정은 **이름 + 첫 오류 메시지 기준**으로 한다.
- 기준선은 Task 1 전에 다시 잡는다(Task 4의 명령으로 결과를 파일에 저장해 둔다).

**현재 코드**
- `pages/{ko,en}/blog/[slug].astro`(CRLF, 190/209줄): `getBlogDetailPageData` → `BlogShell mode="detail" showTOC` + 사이드바 → `.blog-mobile-toolbar`(서랍 토글) → `BlogArticleLayout showStickyActions={false} categories={dbCategories} backLabel nextPost` → `slot="toc"`에 `ReadingActionsRail`(`StickyReadingActions placement="rail"` + `BlogTOC`). en 페이지에만 쓰이지 않는 `masthead`/`editionMap`/`editionLabel`과 `normalizeCategorySlug` import가 있다. 페이지 스크립트(저장·좋아요·댓글·용어 팝업·피드백 import, `recordReadingHistory`, `initAdminActions`)는 그대로 둔다.
- `lib/pageData/blogDetailPage.ts`(CRLF): `blog_posts` 쿼리 4개 — 본문, 사이드바(`published_at desc`, 50편), 다음 글(`.lt('published_at', …)` → **더 이른 글**이라 순서가 거꾸로다), 번역 짝. 반환에 `nextPost`, `sidebarPosts`(`buildBlogSidebarDataset`), `recentPosts`.
- `BlogArticleLayout.astro`(CRLF, 324줄): `BlogBreadcrumb`(제목까지) → 미리보기 배너 → `h1.blog-article-title` + `.blog-article-meta`(달력 아이콘·날짜·읽기 시간·분야 점) → 페르소나 스위처 → `.persona-float--back` → `.reading-actions-layout`(블로그는 `showStickyActions={false}`라 액션 없음) → 본문 → 태그 → 관리자 → `ContentFeedback` → `data-reading-end` → 댓글(`h3`) → `nav.newsprint-article-nav`. 스크립트: `share.ts`, 페르소나 스위처, 코드 복사(유지).
- `StickyReadingActions.astro`(LF): `placement?: 'inline' | 'rail'`과 `placementClass`. `placement="rail"`은 `ReadingActionsRail`만 쓴다. 뉴스 레이아웃·용어 페이지는 기본값(inline)이다.
- `BlogTOC.astro`: `h2, h3`을 모아 id를 붙이고(기존 id → 영문 slug → `section-{n}`, 중복 `-{k}`) 헤더 오프셋(`--blog-shell-header-offset`)으로 스크롤, IntersectionObserver로 강조. `blog.onThisPage`는 이 파일만 쓴다.
- `BlogShell.astro`: `sidebar={false}`면 사이드바·overlay 없이 `.blog-shell--single`(최대 820px). `.blog-shell`이 `--blog-shell-header-offset: 5rem`을 정의한다.
- CSS(`global.css`): `.newsprint-article-nav … .newsprint-nav-next-meta` + 640px 쿼리(블로그 레이아웃만 사용) → `/* ── Breadcrumb ── */` … `/* ── TOC (Right Rail) ── */` `.blog-rail`·`.blog-toc*`(1280/1279px 쿼리) → `/* ── Article Header ── */` → `.blog-article-meta`·`.blog-article-category` → `/* ── Code Copy Button ── */` → `/* ── Tags Footer ── */` → `/* ── Masthead (reuse newsprint pattern but in blog context) ── */`. 액션: `.reading-actions-rail*`, `.reading-actions--rail-placement`(기본 + 1024px 쿼리 안 여러 블록, `.blog-rail …`, `.newsprint-rail .reading-actions--rail-placement`).
- 운영 데이터(2026-10-17): KO 11편 — 학습 노트(study) 5화, 프로젝트 기록(project) 5화, 작업 메모(work-note, sub) 1편. EN 발행 글 0편. 학습 노트 2화 `rag-ai-retrieval-augmented-generation`은 `reading_time_min`이 비어 있고 본문 `h2`가 6개다. 짧은 글 `importance-of-flow-over-features`가 가장 최근 글이다(다음 없음, 이전 = 학습 노트 5화).

**스펙 해석·결정(실행자가 임의로 바꾸지 않는다)**
- `toSerialProps`는 네 번째 인자로 글의 원래 `category`를 받는다(`toSerialProps(located, categories, locale, category)`). 연재 글은 연재 분야를 쓰고, 연재가 아닌 글(짧은 글, 목록에 없는 미리보기 초안)은 이 값을 정규화해 경로 줄·바이라인의 분야를 정한다. 스펙의 3인자 시그니처로는 짧은 글의 분야를 알 수 없어서다. 분야 라벨은 `label_{locale}`, 비어 있으면 slug. DB에 없는 분야는 `categoryLabel = null`, 숨김 분야는 `categoryHref = null`.
- `locatePost`는 입력을 정규화한 복사본으로 계산한다(입력 불변). 연재가 아닌 글의 앞·뒤는 날짜 있는 전체 글(연재 회차 포함)의 오래된 순 목록에서 찾는다.
- 경로 줄 첫 칸은 i18n `blog.title`("IT 블로그"/"IT Blog") 앞에 `← `를 붙인다. 구분자는 `·`(`aria-hidden`).
- 미리보기 배너는 경로 줄 바로 아래(제목 위)에 둔다(현행과 같은 자리).
- 바이라인 날짜·읽기 시간이 없으면 각 칸을 생략한다(RAG 글은 "Amy · 2026년 3월 11일"만).
- 차례: 서버는 빈 `details.blog-post-toc[hidden]`(요약 줄 "이 글의 차례 (<span data-toc-count>0</span>)")만 렌더하고, 스크립트가 `ol`을 채우고 개수를 쓴 뒤 `hidden`을 푼다. `.blog-post-toc[hidden] { display: none; }`을 둔다. 스크립트는 `astro:page-load`에만 묶는다(페이지 스크립트의 다른 init과 같은 방식, ViewTransitions가 첫 로드에도 이벤트를 낸다). 목록을 비우고 다시 만들어 중복이 없다.
- 이전·다음: 카드 두 칸 격자에서 "다음" 카드에 `grid-column: 2`를 줘서 "이전"이 없어도 오른쪽에 머문다(빈 자리 표시용 요소 없음). ≤767px에서는 1단·`grid-column: auto`.
- 연재 목록 머리 오른쪽: 분야 링크가 있으면 "연재 N편 · 전체 보기 →" 링크, 없으면(숨김 분야 — 실제로는 연재가 보이는 분야로만 만들어져 생기지 않는다) "연재 N편" 텍스트. EN 편수는 단수를 구분한다("1 post · View all →").
- 모바일 좌우 여백은 현행 그대로다(`.main-public` 12px + `.blog-main-inner` 8px = 20px, 목록과 같음). 16px로 줄이려고 공용 규칙을 바꾸지 않는다.
- `BlogShell`의 `showTOC` prop과 `toc` 슬롯은 이번에 쓰는 곳이 없어지지만 손대지 않는다(스펙 범위 밖, 실행 결과의 후속에 적는다).
- 기존 테스트 처리
  - Task 2: `detail-rail-actions-placement`(36–37, 41–42행), `blog-list-serial`(10, 15–17행), `blog-sidebar-layout`(84–88행), `blog-detail-sidebar-structure`(22–25, 33–39행), `blog-v2`(53, 56, 63행)를 새 기준으로 바꾼다.
  - Task 3: `detail-rail-actions-placement`(27, 48–51행), `sticky-reading-actions-structure`(31–33행), `reading-actions-layout-regression`(36–46행), `reading-actions-editorial-subtle`(전체 교체: 레일 버튼 대신 인라인 액션 버튼의 차분한 스타일 고정), `blog-sidebar-layout`(19–22, 59–62행)을 바꾸고, `blog-toc-structure.test.cjs`는 대상(`BlogTOC.astro`)과 함께 **삭제**한다(새 차례 스크립트는 `blog-post-column`이 고정한다).

**계획 사전 검증(작성 시 scratchpad 복제본에서 수행)**
- `frontend/`(src, tests, public, scripts, 설정 파일, `.env`; node_modules는 junction)+`supabase/` 복제본에 Task 1–3을 이 문서의 코드 그대로 적용했다(테스트 수정은 Edit와 같은 "정확히 한 번 일치" 치환 스크립트로). 복제본 기준선은 실제 repo와 이름·첫 오류 메시지 기준 동일(PASS 82 / FAIL 19).
- 각 "실패 확인" Step은 적힌 메시지로 실패, 통과 확인 Step은 PASS. Task 2 뒤 **PASS 83 / FAIL 19**, Task 3 뒤 **PASS 82 / FAIL 19**(바뀐 이름은 `blog-post-column` 신규 PASS, `blog-toc-structure` 삭제뿐), 실패 19개의 첫 오류 메시지가 기준선과 동일.
- `astro build` "Complete!"(Task 2 후, Task 3 후 두 번). CSS 삭제 스크립트 출력은 Step에 적힌 값과 같았다.
- dev 서버(운영 데이터, 포트 4405) 렌더
  - `/ko/blog/rag-ai-retrieval-augmented-generation/` 200: `div.blog-shell.blog-shell--single`, 사이드바·레일·서랍 토글 마크업 없음. 경로 줄 "← IT 블로그 · 학습 노트 · 2화", 요약 있음, 바이라인 "Amy · 2026년 3월 11일" + "학습 노트 · 5편 중 2화". 이전·다음 "← 1화 LLM은 어떻게 답을 만들까…" / "3화 → AI는 똑똑하기만 하면 될까…". 연재 목록 "학습 노트 / 연재 5편 · 전체 보기 →" 1–5화, 2화는 "· 지금 읽는 글". 저장 버튼 1개, 댓글 h2, 끝 블록 순서 본문 → 태그 → 관리자 → reading-end → pager → series → comments, `<script>` 26개 전부 nonce.
  - `/ko/blog/importance-of-flow-over-features/` 200: 경로 줄 "← IT 블로그 · 작업 메모", 바이라인 "Amy · 2026년 3월 12일"(연재 칸 없음), 이전·다음은 "← 이전 글 AI Agent는 그냥 챗봇과 무엇이 다를까"만(다음 없음), 연재 목록 없음.
  - `/ko/blog/category/study/` 200(사이드바·서랍 토글 유지), `/ko/blog/` 200, 없는 글 404. 서버 로그 오류 0.
- 브라우저(Playwright, RAG 글): 1100px — 차례 `open`, 6개 링크, `ol` 2단, 액션 격자 `685px 72px`(막대가 본문 오른쪽), 본문 영역 820px, 가로 넘침 없음, 저장 버튼 1개. 375px — 차례 접힘(`open=false`, 보임), 액션 `position: fixed`(하단 바), 이전·다음 1단(320px), 제목 28.8px(1.8rem), 화면 밖 요소 0.

---

## Task 1: 연재 위치 순수 함수 (TDD)

**Files:**
- Modify: `frontend/src/lib/blogSerial.js`(전체 교체)
- Test: `frontend/tests/blog-serial.test.mjs`(Edit 도구로 2곳)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/lib/blogSerial.js frontend/tests/blog-serial.test.mjs`
Expected: 출력 없음.

- [ ] **Step 1: 실패하는 테스트 작성** (Edit 도구로)

1. import 줄:
   ```js
   const { buildBlogFront, normalizeBlogCategory, formatBlogDate } = await import(
   ```
   →
   ```js
   const { buildBlogFront, normalizeBlogCategory, formatBlogDate, locatePost, toSerialProps } = await import(
   ```
2. 마지막 줄 `console.log('blog-serial.test.mjs passed');` **바로 위**에 아래 블록을 넣는다(블록 끝과 `console.log` 사이 빈 줄 한 줄).

```js
// --- blog post page (A: one column): where a post sits, serial props, dates with the year ---
const SERIAL_CATS = [
  cat('study', 'main', 0, { label_ko: '학습 노트', label_en: 'Study Notes', color: '#6E9682' }),
  cat('project', 'main', 1),
  cat('work-note', 'sub', 0, { label_ko: '작업 메모', label_en: 'Work Notes' }),
  cat('secret-note', 'sub', 1, { is_visible: false }),
];
// created_at desc order on purpose (like the query); timeline oldest first: s1, p1, s2, note-a, s3
const SERIAL = [
  post('s3', 'study', '2026-03-12T00:00:00Z'),
  post('note-a', 'work-note', '2026-03-11T12:00:00Z'),
  post('s2', 'study', '2026-03-11T00:00:00Z'),
  post('p1', 'project', '2026-03-10T12:00:00Z'),
  post('s1', 'tech', '2026-03-10T00:00:00Z'),
  post('undated-note', 'work-note', null),
  post('hidden', 'secret-note', '2026-03-09T00:00:00Z'),
  post('lost', 'ghost', '2026-03-08T00:00:00Z'),
];
const NONE = { series: null, index: -1, prev: null, next: null };

// in a series: index + neighbouring episodes of the same series
const s2 = locatePost(SERIAL, SERIAL_CATS, 's2');
assert.equal(s2.series.category.slug, 'study');
assert.deepEqual(titles(s2.series.posts), ['s1', 's2', 's3']);
assert.equal(s2.index, 1);
assert.equal(s2.prev.title, 's1');
assert.equal(s2.next.title, 's3');
const s1 = locatePost(SERIAL, SERIAL_CATS, 's1');
assert.equal(s1.index, 0, 'legacy tech post is episode 1 of the study series');
assert.equal(s1.prev, null, 'first episode has no previous');
assert.equal(s1.next.title, 's2');
assert.equal(s1.series.posts[0].category, 'study');
assert.equal(locatePost(SERIAL, SERIAL_CATS, 's3').next, null, 'last episode has no next');
const p1 = locatePost(SERIAL, SERIAL_CATS, 'p1');
assert.deepEqual([p1.series.category.slug, p1.index, p1.prev, p1.next], ['project', 0, null, null], 'one-episode series');

// not in a series: neighbours among every dated post, episodes included, oldest first
const noteA = locatePost(SERIAL, SERIAL_CATS, 'note-a');
assert.equal(noteA.series, null);
assert.equal(noteA.index, -1);
assert.equal(noteA.prev.title, 's2');
assert.equal(noteA.next.title, 's3');
const hidden = locatePost(SERIAL, SERIAL_CATS, 'hidden');
assert.deepEqual([hidden.series, hidden.prev && hidden.prev.title, hidden.next && hidden.next.title], [null, 'lost', 's1'], 'hidden field: short note, timeline neighbours');
assert.deepEqual(locatePost(SERIAL, SERIAL_CATS, 'undated-note'), NONE, 'undated short note: no neighbours');
assert.deepEqual(locatePost(SERIAL, SERIAL_CATS, 'draft-preview'), NONE, 'slug missing from the list');
assert.deepEqual(locatePost(null, null, 's1'), NONE);
assert.equal(SERIAL[4].category, 'tech', 'input posts are not mutated');

// serial props (one builder for the ko/en pages)
assert.deepEqual(toSerialProps(s2, SERIAL_CATS, 'ko'), {
  categoryLabel: '학습 노트',
  categoryHref: '/ko/blog/category/study/',
  categoryColor: '#6E9682',
  episode: 2,
  total: 3,
  episodes: [{ title: 's1', slug: 's1' }, { title: 's2', slug: 's2' }, { title: 's3', slug: 's3' }],
  prev: { title: 's1', slug: 's1' },
  next: { title: 's3', slug: 's3' },
});
const s2en = toSerialProps(s2, SERIAL_CATS, 'en', 'study');
assert.deepEqual([s2en.categoryLabel, s2en.categoryHref], ['Study Notes', '/en/blog/category/study/']);
assert.deepEqual(toSerialProps(noteA, SERIAL_CATS, 'ko', 'work-note'), {
  categoryLabel: '작업 메모',
  categoryHref: '/ko/blog/category/work-note/',
  categoryColor: null,
  episode: null,
  total: null,
  episodes: [],
  prev: { title: 's2', slug: 's2' },
  next: { title: 's3', slug: 's3' },
});
const hiddenProps = toSerialProps(hidden, SERIAL_CATS, 'ko', 'secret-note');
assert.deepEqual([hiddenProps.categoryLabel, hiddenProps.categoryHref], ['secret-note', null], 'hidden field: label without a link');
const lostProps = toSerialProps(locatePost(SERIAL, SERIAL_CATS, 'lost'), SERIAL_CATS, 'ko', 'ghost');
assert.deepEqual([lostProps.categoryLabel, lostProps.categoryHref, lostProps.categoryColor], [null, null, null], 'field missing from the DB: no label');
const draftProps = toSerialProps(NONE, SERIAL_CATS, 'ko', 'tech');
assert.deepEqual(draftProps, {
  categoryLabel: '학습 노트',
  categoryHref: '/ko/blog/category/study/',
  categoryColor: '#6E9682',
  episode: null,
  total: null,
  episodes: [],
  prev: null,
  next: null,
}, 'draft preview: field from the post itself (tech → study), no series, no neighbours');

// byline dates: KST with the year; without the option the list format is unchanged (asserted above)
assert.equal(formatBlogDate('2026-03-10T18:42:39.552+00:00', 'ko', { year: true }), '2026년 3월 11일');
assert.equal(formatBlogDate('2026-03-10T18:42:39.552+00:00', 'en', { year: true }), 'Mar 11, 2026');
assert.equal(formatBlogDate('2025-12-31T16:00:00Z', 'en', { year: true }), 'Jan 1, 2026', 'the year rolls over in KST');
assert.equal(formatBlogDate(null, 'ko', { year: true }), '');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/blog-serial.test.mjs`
Expected: FAIL `TypeError: locatePost is not a function`.

- [ ] **Step 3: `blogSerial.js` 전체 교체** (Read 후 Write 도구로. `→`는 문자 그대로). 기존 함수는 그대로이고, 머리 주석 1줄·`buildBlogFront` JSDoc의 `id?`·`locatePost`·`toSerialProps`·`formatBlogDate`의 `options`만 바뀐다.

```js
// frontend/src/lib/blogSerial.js
// Pure helpers for the blog list (A: serial column) and the blog post page (A: one column). No I/O.
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
 * @param {Array<{id?: string, title: string, slug: string, category?: string|null, published_at?: string|null}>} posts
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

/**
 * Where one post sits, for the blog post page. Uses buildBlogFront, so the episode number matches the list page
 * when both get the same posts (same query window and order).
 * @param {Array<{title: string, slug: string, category?: string|null, published_at?: string|null}>} posts
 * @param {Array<{slug: string, group_slug: string, sort_order?: number, is_visible: boolean}>} categories
 * @param {string} slug
 * @returns {{ series: {category: object, posts: object[]}|null, index: number, prev: object|null, next: object|null }}
 *   In a series: index (0-based) and the neighbouring episodes of that series.
 *   Otherwise series null, index -1, and the neighbours among every dated post (episodes included), oldest first;
 *   both null when the post itself is undated. A slug missing from posts (e.g. a draft preview) gives all nulls.
 */
export function locatePost(posts, categories, slug) {
  const none = { series: null, index: -1, prev: null, next: null };
  const list = (Array.isArray(posts) ? posts : []).map((post) => ({ ...post, category: normalizeBlogCategory(post.category) }));
  if (!slug || !list.some((post) => post.slug === slug)) return none;

  for (const series of buildBlogFront(list, categories).series) {
    const index = series.posts.findIndex((post) => post.slug === slug);
    if (index >= 0) {
      return { series, index, prev: series.posts[index - 1] ?? null, next: series.posts[index + 1] ?? null };
    }
  }

  const timeline = list.filter((post) => timeOf(post.published_at) !== null).sort(oldestFirst);
  const at = timeline.findIndex((post) => post.slug === slug);
  if (at < 0) return none;
  return { series: null, index: -1, prev: timeline[at - 1] ?? null, next: timeline[at + 1] ?? null };
}

/**
 * The `serial` prop of BlogArticleLayout, built once for the ko and en post pages.
 * @param {{ series: {category: object, posts: object[]}|null, index: number, prev: object|null, next: object|null }} located  locatePost() result
 * @param {Array<{slug: string, label_ko?: string, label_en?: string, color?: string|null, is_visible: boolean}>} categories
 * @param {'ko'|'en'} locale
 * @param {string|null} [category]  the post's own category: names the field when the post is not in a series
 *   (short notes, or a draft preview missing from the list)
 * @returns {{ categoryLabel: string|null, categoryHref: string|null, categoryColor: string|null, episode: number|null,
 *   total: number|null, episodes: {title: string, slug: string}[], prev: {title: string, slug: string}|null,
 *   next: {title: string, slug: string}|null }}
 *   categoryLabel null when the field is not in the DB; categoryHref null when the field is hidden.
 */
export function toSerialProps(located, categories, locale, category) {
  const cats = Array.isArray(categories) ? categories : [];
  const series = located && located.series ? located.series : null;
  const fieldSlug = series ? series.category.slug : normalizeBlogCategory(category);
  const field = fieldSlug ? cats.find((c) => c.slug === fieldSlug) || null : null;
  const link = (post) => (post ? { title: post.title, slug: post.slug } : null);

  return {
    categoryLabel: field ? (locale === 'ko' ? field.label_ko : field.label_en) || field.slug : null,
    categoryHref: field && field.is_visible ? `/${locale}/blog/category/${field.slug}/` : null,
    categoryColor: (field && field.color) || null,
    episode: series ? located.index + 1 : null,
    total: series ? series.posts.length : null,
    episodes: series ? series.posts.map(link) : [],
    prev: link(located ? located.prev : null),
    next: link(located ? located.next : null),
  };
}

/**
 * "3월 11일" / "Mar 11" in KST (the server runs in UTC). '' when undated.
 * { year: true } → "2026년 3월 11일" / "Mar 11, 2026" (blog post byline).
 */
export function formatBlogDate(value, locale, options = {}) {
  const t = timeOf(value);
  if (t === null) return '';
  return new Date(t).toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US', {
    timeZone: 'Asia/Seoul',
    ...(options.year ? { year: 'numeric' } : {}),
    month: 'short',
    day: 'numeric',
  });
}
```

- [ ] **Step 4: 통과 확인**

Run:
```bash
node frontend/tests/blog-serial.test.mjs
node frontend/tests/blog-list-serial.test.cjs
```
Expected: `blog-serial.test.mjs passed`, `blog-list-serial.test.cjs passed`(목록은 옵션 없는 호출이라 그대로).

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/blogSerial.js frontend/tests/blog-serial.test.mjs
git commit -m "feat: add blog post series position helpers"
```

---

## Task 2: 글 상세 화면 (데이터·페이지·레이아웃·CSS·테스트)

**Files:**
- Modify:
  - `frontend/src/lib/pageData/blogDetailPage.ts`(CRLF → Read 후 Write로 전체 교체)
  - `frontend/src/pages/ko/blog/[slug].astro`, `frontend/src/pages/en/blog/[slug].astro`(CRLF → 전체 교체)
  - `frontend/src/components/blog/BlogArticleLayout.astro`(CRLF → 전체 교체)
  - `frontend/src/styles/global.css`(새 블록 추가만. 옛 CSS 삭제는 Task 3)
  - 테스트(Edit 도구로): `detail-rail-actions-placement.test.cjs`, `blog-list-serial.test.cjs`, `blog-sidebar-layout.test.cjs`, `blog-detail-sidebar-structure.test.cjs`, `blog-v2.test.cjs`
- Test: `frontend/tests/blog-post-column.test.cjs`(새 파일. Task 3에서 단언을 더한다)

- [ ] **Step 0: 상태·사용처 확인**

Run:
```bash
git status --short -- frontend/src/lib/pageData/blogDetailPage.ts "frontend/src/pages/ko/blog/[slug].astro" "frontend/src/pages/en/blog/[slug].astro" frontend/src/components/blog/BlogArticleLayout.astro frontend/src/styles/global.css frontend/tests/detail-rail-actions-placement.test.cjs frontend/tests/blog-list-serial.test.cjs frontend/tests/blog-sidebar-layout.test.cjs frontend/tests/blog-detail-sidebar-structure.test.cjs frontend/tests/blog-v2.test.cjs
grep -rn "BlogArticleLayout\|getBlogDetailPageData\|nextPost\|sidebarPosts" frontend/src --include=*.astro --include=*.ts --include=*.js
```
Expected: status 출력 없음. grep은 `pages/{ko,en}/blog/[slug].astro`, `BlogArticleLayout.astro`, `blogDetailPage.ts`, 그리고 분야 페이지·`BlogShell`·`BlogSidebar`의 `sidebarPosts`(분야 페이지용, 유지)만 나온다. 블로그 상세 밖에서 `BlogArticleLayout`이나 `getBlogDetailPageData`를 쓰는 파일이 나오면 멈추고 보고한다.

- [ ] **Step 1: 실패하는 테스트 작성·갱신**

`frontend/tests/blog-post-column.test.cjs`(Write 도구로):

```js
// frontend/tests/blog-post-column.test.cjs
// Blog post A (one column): no sidebar/rail, crumb, byline, contents, inline actions, pager, series list.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// pages: one column, series position computed once via lib/blogSerial.js
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/blog/[slug].astro`);
  assert(page.includes(`<BlogShell locale="${locale}" sidebar={false}>`), `${locale}: post renders without the sidebar`);
  for (const gone of ['ReadingActionsRail', 'BlogTOC', 'slot="toc"', 'showTOC', 'blog-mobile-toolbar', 'data-sidebar-toggle', 'sidebarPosts', 'nextPost', 'backLabel', 'showStickyActions={false}', 'categories={dbCategories}', 'editionLabel', 'masthead']) {
    assert(!page.includes(gone), `${locale}: ${gone} removed`);
  }
  assert(page.includes("import { locatePost, toSerialProps } from '../../../lib/blogSerial.js';"), `${locale}: serial helpers imported`);
  assert(page.includes(`const serial = toSerialProps(locatePost(recentPosts, dbCategories, pageSlug), dbCategories, '${locale}', post?.category);`), `${locale}: serial computed from the list window`);
  assert(page.includes('serial={serial}'), `${locale}: serial passed to the layout`);
  assert(page.includes("import '../../../scripts/handbook-popup';") && page.includes('id="handbook-terms-data"'), `${locale}: term popup kept`);
}

// data: list query = list page shape, no "next post" query
const loader = read('lib/pageData/blogDetailPage.ts');
assert(!loader.includes(".lt('published_at'"), 'no older-post "next" query');
assert.strictEqual((loader.match(/\.from\('blog_posts'\)/g) || []).length, 3, 'blog_posts queries: post, list window, translation pair');
const listAt = loader.indexOf(".select('title, slug, category, published_at')");
const listQuery = loader.slice(listAt, loader.indexOf('.limit(100)', listAt) + '.limit(100)'.length);
assert(listAt > 0 && listQuery.includes(".eq('status', 'published')") && listQuery.includes(".eq('locale', locale)") && listQuery.includes(".order('created_at', { ascending: false })"), 'list window: published, same locale, created_at desc, 100 (as the list page)');
assert(!loader.includes('blogSidebar') && !loader.includes('nextPost') && !loader.includes('sidebarPosts'), 'no sidebar dataset or next post in the loader');
assert(loader.includes('recentPosts: listRows,'), 'list rows returned for locatePost');

// layout
const layout = read('components/blog/BlogArticleLayout.astro');
for (const gone of ['BlogBreadcrumb', 'blog-article-meta', 'blog-article-category', 'newsprint-article-nav', 'persona-float', 'backLabel', 'nextPost', 'categories', 'normalizeCategorySlug', 'toLocaleDateString', 'placement=']) {
  assert(!layout.includes(gone), `layout: ${gone} removed`);
}
assert(layout.includes('serial: {') && layout.includes('episodes: SerialLink[];') && layout.includes('prev: SerialLink | null;') && layout.includes('next: SerialLink | null;'), 'layout: serial prop');
assert(layout.includes("formatBlogDate(publishedAt, locale, { year: true })"), 'byline date: KST with the year');

const crumbAt = layout.indexOf('<nav class="blog-post-crumb" aria-label={copy.crumb}>');
const crumb = layout.slice(crumbAt, layout.indexOf('</nav>', crumbAt));
assert(crumbAt > 0 && crumb.includes("<a href={`/${locale}/blog/`}>← {t[locale]['blog.title']}</a>"), 'crumb: back to the blog');
assert(crumb.includes('{serial.categoryHref ? <a href={serial.categoryHref}>{serial.categoryLabel}</a> : <span>{serial.categoryLabel}</span>}'), 'crumb: field link, or a label for hidden fields');
assert(crumb.includes('<span>{ep(episode)}</span>'), 'crumb: episode');
for (const s of ["'글 위치'", "'Post location'", '`${n}화`', '`Ep. ${n}`', "'이 글의 차례'", "'In this post'", "'이전·다음 글'", "'Previous and next posts'", "'← 이전 글'", "'← Previous'", "'다음 글 →'", "'Next →'", '`연재 ${total}편 · 전체 보기 →`', "`${total} post${total === 1 ? '' : 's'} · View all →`", "' · 지금 읽는 글'", "' · Reading now'", '`약 ${readingTimeMin}분`', '`${readingTimeMin} min read`', '`${serial.categoryLabel} · ${total}편 중 ${episode}화`', '`${serial.categoryLabel} · Ep. ${episode} of ${total}`']) {
  assert(layout.includes(s), `layout copy: ${s}`);
}
assert(layout.includes('<h1 class="blog-article-title">{title}</h1>') && layout.includes('{excerpt && <p class="blog-post-dek">{excerpt}</p>}'), 'title + dek');
assert(layout.includes('<div class="blog-post-byline">') && layout.includes('<strong>Amy</strong>{dateLabel && ` · ${dateLabel}`}{readingLabel && ` · ${readingLabel}`}'), 'byline: Amy · date · reading time');
assert(layout.includes('{bylineSeries && <span class="blog-category-badge blog-post-byline-series" style={`--cat-color: ${catColor}`}>{bylineSeries}</span>}'), 'byline: series dot label');
assert(layout.includes('<details class="blog-post-toc" hidden>') && layout.includes('<ol class="blog-post-toc-list"></ol>') && layout.includes('<span data-toc-count>0</span>'), 'contents: empty hidden details, filled by the script');

// body + actions: StickyReadingActions is the first child of the article grid, inline (no placement)
const gridAt = layout.indexOf("<div class={`reading-actions-layout ${showStickyActions ? 'reading-actions-layout--article' : ''}`.trim()}>");
assert(gridAt > 0, 'article action grid');
const afterGrid = layout.slice(gridAt).split('\n').slice(1).map((l) => l.trim()).filter(Boolean);
assert.deepStrictEqual(afterGrid.slice(0, 2), ['{showStickyActions && (', '<StickyReadingActions'], 'StickyReadingActions is the first child of the grid');
assert(layout.includes('showStickyActions = true,'), 'inline actions on by default');
assert.strictEqual((layout.match(/<StickyReadingActions/g) || []).length, 1, 'one action bar (one blog bookmark button per page)');

// end blocks, in order, inside the body
const bodyAt = layout.indexOf('<div class="reading-actions-layout__body">');
const order = ['<div class="newsprint-prose', '<div class="blog-tags-footer">', 'class="newsprint-admin-actions"', '<ContentFeedback', '<div data-reading-end></div>', '<nav class="blog-post-pager" aria-label={copy.pager}>', '<aside class="blog-post-series" aria-labelledby="blog-post-series-title">', '<section\n        id="comments"'];
let last = bodyAt;
for (const marker of order) {
  const at = layout.indexOf(marker, last);
  assert(at > last, `end blocks in order: ${marker}`);
  last = at;
}
assert(layout.includes('{(serial.prev || serial.next) && ('), 'pager only with a neighbour');
assert(layout.includes('{serial.prev && (') && layout.includes('<a class="blog-post-pager-link blog-post-pager-link--next"'), 'pager: each card optional, next marked');
assert(layout.includes('{isSeries && (') && layout.includes('<p id="blog-post-series-title" class="blog-post-series-title">{serial.categoryLabel}</p>'), 'series list only for episodes; head is not a heading tag');
assert(layout.includes('<span class="blog-post-series-name" aria-current="page">{item.title}<span class="blog-post-series-now">{copy.readingNow}</span></span>'), 'current episode: text, aria-current');
assert(layout.includes('<a class="blog-post-series-name" href={`${resolvedBasePath}/${item.slug}/`}>{item.title}</a>'), 'other episodes link');
assert(layout.includes('<h2 class="newsprint-comments-title">') && !layout.includes('<h3 class="newsprint-comments-title">'), 'comments heading is an h2');

// contents script: bundled, rebuilt per page load, h2 only, old id rule, no scroll spy
assert(!layout.includes('is:inline'), 'layout scripts are bundled (no nonce needed)');
for (const s of [
  "document.querySelector<HTMLDetailsElement>('details.blog-post-toc')",
  "list.innerHTML = '';",
  "prose.querySelectorAll<HTMLHeadingElement>('h2')",
  'if (headings.length < 2) {',
  "heading.id || slugifyHeading(heading.textContent || '') || `section-${index + 1}`",
  'heading.id = occurrence === 1 ? baseId : `${baseId}-${occurrence}`;',
  "link.textContent = heading.textContent?.trim() || '';",
  "getPropertyValue('--blog-shell-header-offset')",
  "window.scrollTo({ top, behavior: 'smooth' });",
  "toc.open = window.matchMedia('(min-width: 1024px)').matches;",
  "document.addEventListener('astro:page-load', initBlogPostToc);",
]) {
  assert(layout.includes(s), `contents script: ${s}`);
}
assert(!layout.includes('IntersectionObserver'), 'no scroll position highlight');

// CSS
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-post-byline')) && /border-bottom:\s*1px solid var\(--color-text-primary\)/.test(rule('.blog-post-byline')) && /justify-content:\s*space-between/.test(rule('.blog-post-byline')), 'byline: 2px ink rule above, 1px below, both ends');
assert(rule('.blog-post-toc').includes('var(--color-bg-secondary)'), 'contents on the secondary surface');
assert(rule('.blog-post-toc[hidden]').includes('display: none'), 'hidden contents stay hidden');
assert(/grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/.test(rule('.blog-post-pager')), 'pager: 2 cards');
assert(/grid-column:\s*2/.test(rule('.blog-post-pager-link--next')), 'next card stays on the right');
assert(rule('.blog-post-pager-title').includes('var(--font-blog-heading)') && /font-weight:\s*600/.test(rule('.blog-post-pager-title')), 'pager title Hahmlet 600');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-post-series-head')), 'series head: 2px ink rule');
assert(rule('.blog-post-series-ep').includes('var(--font-masthead)'), 'episode number in Newsreader');
const desktopAt = css.indexOf('/* Blog post A: desktop */');
const desktop = css.slice(desktopAt, css.indexOf('\n}\n', desktopAt));
assert(desktopAt > 0 && desktop.includes('@media (min-width: 1024px)') && /\.blog-post-toc-list\s*\{[^}]*columns:\s*2/.test(desktop), 'desktop: contents in 2 columns');
const mobileAt = css.indexOf('/* Blog post A: mobile */');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(mobileAt > 0 && mobile.includes('@media (max-width: 767px)'), 'blog post mobile block');
assert(/\.blog-post-byline\s*\{[^}]*flex-wrap:\s*wrap/.test(mobile), 'mobile: byline wraps');
assert(/\.blog-post-pager\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: pager one column');
assert(/\.blog-post-pager-link--next\s*\{[^}]*grid-column:\s*auto/.test(mobile), 'mobile: next card in flow');
// shared action bar: right 72px column from 1024px (no blog-only override)
assert(css.includes('  .reading-actions-layout--article {\n    display: grid;\n    grid-template-columns: minmax(0, 1fr) 72px;'), 'shared desktop action column');
assert(!/\.blog-[\w-]*\s+\.reading-actions-layout/.test(css), 'no blog-only action layout override');

console.log('blog-post-column.test.cjs passed');
```

기존 테스트(Edit 도구로, 각 `old` → `new`):

1. `frontend/tests/detail-rail-actions-placement.test.cjs`

   old:
   ```js
   assertIncludes(blogEn, 'showStickyActions={false}', 'blog EN inline actions disabled');
   assertIncludes(blogKo, 'showStickyActions={false}', 'blog KO inline actions disabled');
   ```
   new:
   ```js
   // Blog post A (2026-10-17): blog uses the inline actions too (right 72px column from 1024px, bottom bar below).
   if (blogEn.includes('showStickyActions={false}')) throw new Error('blog EN uses inline reading actions');
   if (blogKo.includes('showStickyActions={false}')) throw new Error('blog KO uses inline reading actions');
   ```

2. `frontend/tests/detail-rail-actions-placement.test.cjs`

   old:
   ```js
   assertIncludes(blogEn, '<ReadingActionsRail', 'blog EN right rail action wrapper');
   assertIncludes(blogKo, '<ReadingActionsRail', 'blog KO right rail action wrapper');
   ```
   new:
   ```js
   if (blogEn.includes('<ReadingActionsRail')) throw new Error('blog EN has no right rail');
   if (blogKo.includes('<ReadingActionsRail')) throw new Error('blog KO has no right rail');
   ```

3. `frontend/tests/blog-list-serial.test.cjs`

   old:
   ```js
   // shell: sidebar prop (default true). Only the list passes false; category and detail pages keep the sidebar.
   ```
   new:
   ```js
   // shell: sidebar prop (default true). The list and post pages pass false; category pages keep the sidebar.
   ```

4. `frontend/tests/blog-list-serial.test.cjs`

   old:
   ```js
   for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro', 'pages/ko/blog/category/[slug].astro', 'pages/en/blog/category/[slug].astro']) {
     assert(!read(p).includes('sidebar={false}'), `${p} keeps the sidebar`);
   }
   ```
   new:
   ```js
   for (const p of ['pages/ko/blog/category/[slug].astro', 'pages/en/blog/category/[slug].astro']) {
     assert(!read(p).includes('sidebar={false}'), `${p} keeps the sidebar`);
   }
   for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro']) {
     assert(read(p).includes('sidebar={false}'), `${p} is one column (blog post A)`);
   }
   ```

5. `frontend/tests/blog-sidebar-layout.test.cjs`

   old:
   ```js
   // The list page has no sidebar (and no drawer toggle); category pages keep the toolbar.
   assertNoInlineToolbar('frontend/src/pages/ko/blog/category/[slug].astro');
   assertNoInlineToolbar('frontend/src/pages/en/blog/category/[slug].astro');
   assertNoInlineToolbar('frontend/src/pages/ko/blog/[slug].astro');
   assertNoInlineToolbar('frontend/src/pages/en/blog/[slug].astro');
   ```
   new:
   ```js
   // The list and post pages have no sidebar (and no drawer toggle); category pages keep the toolbar.
   assertNoInlineToolbar('frontend/src/pages/ko/blog/category/[slug].astro');
   assertNoInlineToolbar('frontend/src/pages/en/blog/category/[slug].astro');
   ```

6. `frontend/tests/blog-detail-sidebar-structure.test.cjs`

   old:
   ```js
   const detailLoader = read('src/lib/pageData/blogDetailPage.ts');
   assert(detailLoader.includes("from './blogSidebar'"), 'Blog detail loader must reuse the shared sidebar helper');
   assert(!detailLoader.includes('.limit(4)'), 'Blog detail sidebar dataset must not be limited to 4 recent posts');
   assert(!detailLoader.includes(".neq('slug', pageSlug)"), 'Blog detail sidebar dataset must not exclude the current slug');
   ```
   new:
   ```js
   // Blog post A (2026-10-17): the post page has no sidebar. Its list window feeds locatePost (series position),
   // so it keeps the current post and the list page's 100-post window.
   const detailLoader = read('src/lib/pageData/blogDetailPage.ts');
   assert(!detailLoader.includes("from './blogSidebar'"), 'Blog detail loader must not build a sidebar dataset');
   assert(!detailLoader.includes('.limit(4)') && detailLoader.includes('.limit(100)'), 'Blog detail list window must match the list page (100 posts)');
   assert(!detailLoader.includes(".neq('slug', pageSlug)"), 'Blog detail list window must not exclude the current slug');
   ```

7. `frontend/tests/blog-detail-sidebar-structure.test.cjs`

   old:
   ```js
   const koDetail = read('src/pages/ko/blog/[slug].astro');
   assert(koDetail.includes('mode="detail"'), 'Korean blog detail page must render sidebar in detail mode');
   assert(koDetail.includes('currentCategory={post?.category}'), 'Korean blog detail page must pass the current post category to the sidebar');

   const enDetail = read('src/pages/en/blog/[slug].astro');
   assert(enDetail.includes('mode="detail"'), 'English blog detail page must render sidebar in detail mode');
   assert(enDetail.includes('currentCategory={post?.category}'), 'English blog detail page must pass the current post category to the sidebar');
   ```
   new:
   ```js
   const koDetail = read('src/pages/ko/blog/[slug].astro');
   assert(koDetail.includes('sidebar={false}') && !koDetail.includes('mode="detail"'), 'Korean blog detail page must render without the sidebar');

   const enDetail = read('src/pages/en/blog/[slug].astro');
   assert(enDetail.includes('sidebar={false}') && !enDetail.includes('mode="detail"'), 'English blog detail page must render without the sidebar');
   ```

8. `frontend/tests/blog-v2.test.cjs`

   old:
   ```js
   assert(/class="blog-article-category"[^>]*--cat-color/.test(layout), 'article meta shows the category as a color dot label');
   ```
   new:
   ```js
   assert(/class="blog-category-badge blog-post-byline-series"[^>]*--cat-color/.test(layout), 'byline shows the series as a color dot label');
   ```

9. `frontend/tests/blog-v2.test.cjs`

   old:
   ```js
   assert(!rule('.blog-toc-header').includes('uppercase'), 'toc header not uppercase');
   ```
   new:
   ```js
   assert(!rule('.blog-post-toc-summary').includes('uppercase'), 'contents label not uppercase');
   ```

10. `frontend/tests/blog-v2.test.cjs`

   old:
   ```js
   assert(rule('.blog-article-meta').includes('var(--font-blog-ui)'), 'article meta uses the blog UI font');
   ```
   new:
   ```js
   assert(rule('.blog-post-byline-meta').includes('var(--font-blog-ui)'), 'byline uses the blog UI font');
   ```

- [ ] **Step 2: 실패 확인**

Run:
```bash
node frontend/tests/blog-post-column.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-detail-sidebar-structure.test.cjs
node frontend/tests/blog-v2.test.cjs
node frontend/tests/blog-sidebar-layout.test.cjs
```
Expected:
- `blog-post-column`: FAIL "ko: post renders without the sidebar"
- `detail-rail-actions-placement`: FAIL "blog EN uses inline reading actions"
- `blog-list-serial`: FAIL "pages/ko/blog/[slug].astro is one column (blog post A)"
- `blog-detail-sidebar-structure`: FAIL "Blog detail loader must not build a sidebar dataset"
- `blog-v2`: FAIL "byline shows the series as a color dot label"
- `blog-sidebar-layout`: 기준선과 같은 "Blog sidebar panel must use the shared card radius"

- [ ] **Step 3: `blogDetailPage.ts` 전체 교체** (Read 후 Write 도구로). 바뀌는 곳: `./blogSidebar` import 삭제, `sidebarRows` → `listRows`, 목록 쿼리(`created_at desc`, `limit(100)`), `nextRes`/`nextPost` 삭제, `sidebarPosts` 계산·반환 삭제. 본문·번역 짝·좋아요·댓글 수·용어 렌더 경로는 그대로다.

```ts
import { renderMarkdown, renderMarkdownWithTerms, type TermsMap } from '../markdown';
import { fetchPublicTermIndex } from './publicTermIndex';
import { getAuthorizedSupabase, getPublicSupabase, type DetailPageContext } from './shared';
import { pickReferencedTerms } from './termReferences';

export const BLOG_DETAIL_PUBLIC_COLUMNS = [
  'id', 'slug', 'locale', 'status', 'title', 'excerpt', 'category', 'content',
  'published_at', 'updated_at', 'reading_time_min', 'tags', 'og_image_url',
  'translation_group_id', 'focus_items',
].join(', ');

export async function getBlogDetailPageData({ locale, slug, previewMode, locals }: DetailPageContext) {
  const pageSlug = slug;
  const publicSupabase = getPublicSupabase();
  const previewSupabase = previewMode ? getAuthorizedSupabase(locals.accessToken) : null;
  const detailSupabase = previewSupabase || publicSupabase;

  let post: any = null;
  let postError: string | null = null;

  if (detailSupabase && slug) {
    let query = detailSupabase
      .from('blog_posts')
      .select(BLOG_DETAIL_PUBLIC_COLUMNS)
      .eq('slug', pageSlug)
      .eq('locale', locale);

    if (!previewMode) {
      query = query.eq('status', 'published');
    }

    const { data, error } = await query.single();

    if (error && error.code !== 'PGRST116') {
      postError = error.message;
    } else {
      post = data;
    }
  }

  let listRows: any[] = [];
  let articleData: any = undefined;
  let pairedSlug: string | null = null;
  let isBookmarked = false;
  let isLiked = false;
  let likeCount = 0;
  let commentCount = 0;
  let handbookTermsMap: TermsMap = new Map();
  let handbookTermsJson: Record<string, any> = {};
  let htmlContent = '';

  if (post && publicSupabase) {
    const pairedLocale = locale === 'ko' ? 'en' : 'ko';

    const rawContent = post.content || '';

    // Track 1: terms fetch → termsMap build → markdown render (chained)
    // Runs in parallel with Track 2 DB queries so render time overlaps with I/O.
    const renderTrack = (async () => {
      const handbookTerms = await fetchPublicTermIndex(publicSupabase, locale);

      const tMap: TermsMap = new Map();
      const tJson: Record<string, any> = {};
      for (const entry of handbookTerms) {
        const termEntry = { slug: entry.slug, term: entry.term };
        tMap.set(entry.term.toLowerCase(), termEntry);
        if (entry.korean_name) tMap.set(entry.korean_name.toLowerCase(), termEntry);
        tJson[entry.slug] = {
          term: entry.term,
          korean_name: entry.korean_name || '',
          term_full: entry.term_full || '',
          categories: entry.categories || [],
          summary: entry.summary || '',
          definition: entry.definition || '',
          basic_plain: entry.basic_plain || '',
        };
      }

      const renderFn = tMap.size > 0
        ? (md: string) => renderMarkdownWithTerms(md, tMap)
        : (md: string) => renderMarkdown(md);
      const html = rawContent ? await renderFn(rawContent) : '';
      return { termsMap: tMap, termsJson: tJson, html };
    })();

    // Track 2: remaining DB queries (all parallel).
    // isBookmarked/isLiked stay false — hydrated client-side so HTML is cacheable.
    const [
      listRes,
      pairedRes,
      likeCountRes,
      commentCountRes,
    ] = await Promise.all([
      // Same window, order and columns as the blog list page (created_at desc, 100 posts), so the
      // episode number and previous/next computed by locatePost() match the list.
      publicSupabase
        .from('blog_posts')
        .select('title, slug, category, published_at')
        .eq('status', 'published')
        .eq('locale', locale)
        .order('created_at', { ascending: false })
        .limit(100),
      post.translation_group_id
        ? (previewMode && previewSupabase ? previewSupabase : publicSupabase)
            .from('blog_posts')
            .select('slug')
            .eq('translation_group_id', post.translation_group_id)
            .eq('locale', pairedLocale)
            .single()
        : Promise.resolve({ data: null }),
      publicSupabase
        .from('blog_likes')
        .select('id', { count: 'exact', head: true })
        .eq('post_id', post.id),
      publicSupabase
        .from('blog_comments')
        .select('id', { count: 'exact', head: true })
        .eq('post_id', post.id),
    ]);

    // Await render track (likely already done by now)
    const renderResult = await renderTrack;
    handbookTermsMap = renderResult.termsMap;
    handbookTermsJson = renderResult.termsJson;
    htmlContent = renderResult.html;

    listRows = listRes.data ?? [];
    pairedSlug = pairedRes.data?.slug ?? null;
    likeCount = likeCountRes.count ?? 0;
    commentCount = commentCountRes.count ?? 0;

    articleData = post.published_at
      ? { datePublished: post.published_at, dateModified: post.updated_at || post.published_at, image: post.og_image_url }
      : undefined;
  }

  const hasTerms = handbookTermsMap.size > 0;

  return {
    post,
    postError,
    recentPosts: listRows,
    articleData,
    pairedSlug,
    isBookmarked: previewMode ? false : isBookmarked,
    isLiked: previewMode ? false : isLiked,
    likeCount,
    commentCount,
    handbookTermsJson: pickReferencedTerms(handbookTermsJson, [htmlContent]),
    hasTerms,
    htmlContent,
  };
}
```

- [ ] **Step 4: `pages/ko/blog/[slug].astro` 전체 교체** (Read 후 Write 도구로)

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { supabase } from '../../../lib/supabase';
import { getBlogDetailPageData } from '../../../lib/pageData/blogDetailPage';
import { fetchCategories } from '../../../lib/pageData/blogCategories';
import { locatePost, toSerialProps } from '../../../lib/blogSerial.js';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';
import BlogShell from '../../../components/blog/BlogShell.astro';
import BlogArticleLayout from '../../../components/blog/BlogArticleLayout.astro';

const { slug } = Astro.params;
const pageSlug = slug ?? '';
const previewRequested = Astro.url.searchParams.get('preview') === '1';
const previewMode = previewRequested && !!Astro.locals.isAdmin;
const {
  post,
  postError,
  articleData,
  recentPosts,
  pairedSlug,
  isBookmarked,
  isLiked,
  likeCount,
  commentCount,
  handbookTermsJson,
  hasTerms,
  htmlContent,
} = await getBlogDetailPageData({
  locale: 'ko',
  slug: pageSlug,
  previewMode,
  locals: Astro.locals,
});

if (postError) {
  Astro.response.status = 503;
} else if (!post) {
  Astro.response.status = 404;
}

const dbCategories = supabase ? await fetchCategories(supabase) : [];
// Series position (episode, previous/next) from the same posts and rules as the blog list.
const serial = toSerialProps(locatePost(recentPosts, dbCategories, pageSlug), dbCategories, 'ko', post?.category);

const user = Astro.locals.user;
const accessToken = Astro.locals.accessToken;

const pageTitle = post ? post.title : '찾을 수 없음';
const pageDescription = post?.excerpt?.slice(0, 155) || undefined;
const altSlugValue = pairedSlug || undefined;
---

<MainLayout title={pageTitle} description={pageDescription} locale="ko" slug={`blog/${slug}/`} altSlug={altSlugValue} article={articleData} previewMode={previewMode} needsKatex={true}>
  <BlogShell locale="ko" sidebar={false}>
    {postError ? (
      <NewsprintNotice variant="error" message={t.ko['blog.error']} linkHref="/ko/blog/" linkLabel={t.ko['blog.back']} />
    ) : !post ? (
      <NewsprintNotice variant="notfound" message={t.ko['post.notfound']} linkHref="/ko/blog/" linkLabel={t.ko['blog.back']} />
    ) : (
      <BlogArticleLayout
        locale="ko"
        slug={pageSlug}
        title={post.title}
        excerpt={post.excerpt}
        publishedAt={post.published_at}
        readingTimeMin={post.reading_time_min}
        tags={post.tags}
        htmlContent={htmlContent}
        serial={serial}
        basePath="/ko/blog"
        isBookmarked={isBookmarked}
        itemId={post.id}
        itemType="blog"
        isAdmin={!!Astro.locals.isAdmin && !previewMode}
        isAuthenticated={!!user && !!accessToken}
        likeCount={likeCount}
        commentCount={commentCount}
        isLiked={isLiked}
        previewMode={previewMode}
      />
    )}
  </BlogShell>
</MainLayout>

{hasTerms && (
  <script type="application/json" id="handbook-terms-data" set:html={JSON.stringify(handbookTermsJson)} />
)}

<script>
  import '../../../scripts/bookmark';
  import '../../../scripts/likes';
  import '../../../scripts/comments';
  import '../../../scripts/handbook-popup';
  import '../../../scripts/contentFeedback';
  import { onSessionReady, type SessionInfo } from '../../../scripts/session';

  function recordReadingHistory(session: SessionInfo): void {
    if (document.body.dataset.previewMode === 'true' || !session.authenticated) return;
    const postId = document.querySelector('[data-item-id][data-item-type="blog"]')?.getAttribute('data-item-id');
    if (!postId) return;
    fetch('/api/user/reading-history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_type: 'blog', item_id: postId }),
    }).catch(() => {});
  }

  function initAdminActions(): void {
    if (document.body.dataset.previewMode === 'true') return;
    const actions = document.querySelector('.newsprint-admin-actions') as HTMLElement | null;
    if (!actions) return;

    const btn = actions.querySelector('.newsprint-admin-action-btn--unpublish');
    btn?.addEventListener('click', async () => {
      if (!confirm('이 글을 비공개로 전환할까요?')) return;

      const id = actions.dataset.toolbarId;
      const api = actions.dataset.toolbarApi;
      if (!id || !api) return;

      try {
        const res = await fetch(api, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, action: 'unpublish' }),
        });

        if (res.ok) {
          const editLink = actions.querySelector('a') as HTMLAnchorElement | null;
          window.location.href = editLink?.href || '/admin';
        } else {
          const err = await res.json().catch(() => ({ error: 'Unknown error' }));
          alert(`비공개 전환 실패: ${err.error || err.detail}`);
        }
      } catch {
        alert('비공개 전환 실패: 네트워크 오류');
      }
    });
  }

  document.addEventListener('astro:page-load', () => onSessionReady(recordReadingHistory));
  document.addEventListener('astro:page-load', initAdminActions);
</script>
```

- [ ] **Step 5: `pages/en/blog/[slug].astro` 전체 교체** (Read 후 Write 도구로). KO와 다른 곳은 `locale: 'en'`, `toSerialProps(…, 'en', post?.category)`, `'Not Found'`, `locale="en"`(MainLayout·BlogShell·BlogArticleLayout), `t.en[…]`·`/en/blog/`(NewsprintNotice 두 곳), `basePath="/en/blog"`, 관리자 비공개 전환 문구 3개뿐이다. 쓰이지 않던 `normalizeCategorySlug` import와 `masthead`/`editionMap`/`editionLabel`은 사라진다.

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { supabase } from '../../../lib/supabase';
import { getBlogDetailPageData } from '../../../lib/pageData/blogDetailPage';
import { fetchCategories } from '../../../lib/pageData/blogCategories';
import { locatePost, toSerialProps } from '../../../lib/blogSerial.js';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';
import BlogShell from '../../../components/blog/BlogShell.astro';
import BlogArticleLayout from '../../../components/blog/BlogArticleLayout.astro';

const { slug } = Astro.params;
const pageSlug = slug ?? '';
const previewRequested = Astro.url.searchParams.get('preview') === '1';
const previewMode = previewRequested && !!Astro.locals.isAdmin;
const {
  post,
  postError,
  articleData,
  recentPosts,
  pairedSlug,
  isBookmarked,
  isLiked,
  likeCount,
  commentCount,
  handbookTermsJson,
  hasTerms,
  htmlContent,
} = await getBlogDetailPageData({
  locale: 'en',
  slug: pageSlug,
  previewMode,
  locals: Astro.locals,
});

if (postError) {
  Astro.response.status = 503;
} else if (!post) {
  Astro.response.status = 404;
}

const dbCategories = supabase ? await fetchCategories(supabase) : [];
// Series position (episode, previous/next) from the same posts and rules as the blog list.
const serial = toSerialProps(locatePost(recentPosts, dbCategories, pageSlug), dbCategories, 'en', post?.category);

const user = Astro.locals.user;
const accessToken = Astro.locals.accessToken;

const pageTitle = post ? post.title : 'Not Found';
const pageDescription = post?.excerpt?.slice(0, 155) || undefined;
const altSlugValue = pairedSlug || undefined;
---

<MainLayout title={pageTitle} description={pageDescription} locale="en" slug={`blog/${slug}/`} altSlug={altSlugValue} article={articleData} previewMode={previewMode} needsKatex={true}>
  <BlogShell locale="en" sidebar={false}>
    {postError ? (
      <NewsprintNotice variant="error" message={t.en['blog.error']} linkHref="/en/blog/" linkLabel={t.en['blog.back']} />
    ) : !post ? (
      <NewsprintNotice variant="notfound" message={t.en['post.notfound']} linkHref="/en/blog/" linkLabel={t.en['blog.back']} />
    ) : (
      <BlogArticleLayout
        locale="en"
        slug={pageSlug}
        title={post.title}
        excerpt={post.excerpt}
        publishedAt={post.published_at}
        readingTimeMin={post.reading_time_min}
        tags={post.tags}
        htmlContent={htmlContent}
        serial={serial}
        basePath="/en/blog"
        isBookmarked={isBookmarked}
        itemId={post.id}
        itemType="blog"
        isAdmin={!!Astro.locals.isAdmin && !previewMode}
        isAuthenticated={!!user && !!accessToken}
        likeCount={likeCount}
        commentCount={commentCount}
        isLiked={isLiked}
        previewMode={previewMode}
      />
    )}
  </BlogShell>
</MainLayout>

{hasTerms && (
  <script type="application/json" id="handbook-terms-data" set:html={JSON.stringify(handbookTermsJson)} />
)}

<script>
  import '../../../scripts/bookmark';
  import '../../../scripts/likes';
  import '../../../scripts/comments';
  import '../../../scripts/handbook-popup';
  import '../../../scripts/contentFeedback';
  import { onSessionReady, type SessionInfo } from '../../../scripts/session';

  function recordReadingHistory(session: SessionInfo): void {
    if (document.body.dataset.previewMode === 'true' || !session.authenticated) return;
    const postId = document.querySelector('[data-item-id][data-item-type="blog"]')?.getAttribute('data-item-id');
    if (!postId) return;
    fetch('/api/user/reading-history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_type: 'blog', item_id: postId }),
    }).catch(() => {});
  }

  function initAdminActions(): void {
    if (document.body.dataset.previewMode === 'true') return;
    const actions = document.querySelector('.newsprint-admin-actions') as HTMLElement | null;
    if (!actions) return;

    const btn = actions.querySelector('.newsprint-admin-action-btn--unpublish');
    btn?.addEventListener('click', async () => {
      if (!confirm('Unpublish this item?')) return;

      const id = actions.dataset.toolbarId;
      const api = actions.dataset.toolbarApi;
      if (!id || !api) return;

      try {
        const res = await fetch(api, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, action: 'unpublish' }),
        });

        if (res.ok) {
          const editLink = actions.querySelector('a') as HTMLAnchorElement | null;
          window.location.href = editLink?.href || '/admin';
        } else {
          const err = await res.json().catch(() => ({ error: 'Unknown error' }));
          alert(`Unpublish failed: ${err.error || err.detail}`);
        }
      } catch {
        alert('Unpublish failed: network error');
      }
    });
  }

  document.addEventListener('astro:page-load', () => onSessionReady(recordReadingHistory));
  document.addEventListener('astro:page-load', initAdminActions);
</script>
```

- [ ] **Step 6: `BlogArticleLayout.astro` 전체 교체** (Read 후 Write 도구로. 차례 스크립트에 정규식 백슬래시가 있으므로 반드시 Write 도구)

```astro
---
// Blog post A (one column): crumb, title, dek, byline, contents, body + inline actions,
// then tags, admin actions, feedback, previous/next, series list and comments.
// Series position comes from the page (locatePost + toSerialProps in lib/blogSerial.js).
// Public HTML stays user-neutral: bookmark/like state is hydrated client-side.
import PreviewReadonlyBanner from '../common/PreviewReadonlyBanner.astro';
import StickyReadingActions from '../common/StickyReadingActions.astro';
import ReadingProgressBar from '../common/ReadingProgressBar.astro';
import ContentFeedback from '../common/ContentFeedback.astro';
import { formatBlogDate } from '../../lib/blogSerial.js';
import { t } from '../../i18n/index';

interface SerialLink {
  title: string;
  slug: string;
}

interface Props {
  locale: 'en' | 'ko';
  slug: string;
  title: string;
  excerpt?: string | null;
  publishedAt?: string | null;
  readingTimeMin?: number | null;
  tags?: string[] | null;
  htmlContent: string;
  serial: {
    categoryLabel: string | null;
    categoryHref: string | null;
    categoryColor: string | null;
    episode: number | null;
    total: number | null;
    episodes: SerialLink[];
    prev: SerialLink | null;
    next: SerialLink | null;
  };
  isBookmarked?: boolean;
  itemId?: string;
  itemType?: 'news' | 'blog' | 'term';
  basePath?: string;
  isAdmin?: boolean;
  isAuthenticated?: boolean;
  likeCount?: number;
  commentCount?: number;
  isLiked?: boolean;
  activePersona?: string | null;
  personaHtmlMap?: Record<string, string>;
  previewMode?: boolean;
  showStickyActions?: boolean;
}

const {
  locale,
  slug,
  title,
  excerpt,
  publishedAt,
  readingTimeMin,
  tags,
  htmlContent,
  serial,
  isBookmarked = false,
  itemId,
  itemType,
  basePath,
  isAdmin = false,
  isAuthenticated = false,
  likeCount = 0,
  commentCount = 0,
  isLiked = false,
  activePersona = null,
  personaHtmlMap,
  previewMode = false,
  showStickyActions = true,
} = Astro.props;

const personaLabels: Record<string, Record<string, string>> = {
  en: { beginner: 'Beginner', learner: 'Learner', expert: 'Expert' },
  ko: { beginner: '입문자', learner: '학습자', expert: '현직자' },
};
const showPersonaSwitcher = personaHtmlMap && Object.keys(personaHtmlMap).length > 1;

const isKo = locale === 'ko';
const episode = serial.episode ?? 0;
const total = serial.total ?? 0;
const isSeries = episode > 0 && total > 0;
const ep = (n: number) => (isKo ? `${n}화` : `Ep. ${n}`);

const dateLabel = formatBlogDate(publishedAt, locale, { year: true });
const readingLabel = readingTimeMin ? (isKo ? `약 ${readingTimeMin}분` : `${readingTimeMin} min read`) : '';
const bylineSeries = isSeries && serial.categoryLabel
  ? (isKo ? `${serial.categoryLabel} · ${total}편 중 ${episode}화` : `${serial.categoryLabel} · Ep. ${episode} of ${total}`)
  : '';
const catColor = serial.categoryColor || 'var(--color-border)';

const resolvedBasePath = basePath || `/${locale}/blog`;
const shareUrl = `${import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com'}${resolvedBasePath}/${slug}/`;
const articleRedirect = `${resolvedBasePath}/${slug}/`;
const commentRedirect = `${resolvedBasePath}/${slug}/#comments`;
const editHref = `/admin/blog/edit/${slug}`;
const unpublishApi = '/api/admin/blog/status';

const copy = {
  crumb: isKo ? '글 위치' : 'Post location',
  toc: isKo ? '이 글의 차례' : 'In this post',
  pager: isKo ? '이전·다음 글' : 'Previous and next posts',
  prev: isSeries ? `← ${ep(episode - 1)}` : (isKo ? '← 이전 글' : '← Previous'),
  next: isSeries ? `${ep(episode + 1)} →` : (isKo ? '다음 글 →' : 'Next →'),
  seriesMore: isKo ? `연재 ${total}편 · 전체 보기 →` : `${total} post${total === 1 ? '' : 's'} · View all →`,
  seriesCount: isKo ? `연재 ${total}편` : `${total} post${total === 1 ? '' : 's'}`,
  readingNow: isKo ? ' · 지금 읽는 글' : ' · Reading now',
  comments: isKo ? '댓글' : 'Comments',
  writeComment: isKo ? '댓글을 작성해주세요...' : 'Write a comment...',
  postComment: isKo ? '게시' : 'Post',
  loginToComment: isKo ? '댓글을 작성하려면 로그인하세요' : 'Log in to comment',
};

const previewCommentsReadonly = 'Preview mode · comments are read-only.';
---

<article class="newsprint-article">
  <header class="blog-article-header">
    <nav class="blog-post-crumb" aria-label={copy.crumb}>
      <a href={`/${locale}/blog/`}>← {t[locale]['blog.title']}</a>
      {serial.categoryLabel && (
        <>
          <span class="blog-post-crumb-sep" aria-hidden="true">·</span>
          {serial.categoryHref ? <a href={serial.categoryHref}>{serial.categoryLabel}</a> : <span>{serial.categoryLabel}</span>}
        </>
      )}
      {isSeries && (
        <>
          <span class="blog-post-crumb-sep" aria-hidden="true">·</span>
          <span>{ep(episode)}</span>
        </>
      )}
    </nav>
    {previewMode && (
      <>
        <!-- Admin preview -->
        <PreviewReadonlyBanner locale={locale} />
      </>
    )}
    <h1 class="blog-article-title">{title}</h1>
    {excerpt && <p class="blog-post-dek">{excerpt}</p>}
    <div class="blog-post-byline">
      <p class="blog-post-byline-meta"><strong>Amy</strong>{dateLabel && ` · ${dateLabel}`}{readingLabel && ` · ${readingLabel}`}</p>
      {bylineSeries && <span class="blog-category-badge blog-post-byline-series" style={`--cat-color: ${catColor}`}>{bylineSeries}</span>}
    </div>
    <details class="blog-post-toc" hidden>
      <summary class="blog-post-toc-summary">{copy.toc} (<span data-toc-count>0</span>)</summary>
      <ol class="blog-post-toc-list"></ol>
    </details>
  </header>

  {showPersonaSwitcher && (
    <div class="persona-switcher">
      {(['beginner', 'learner', 'expert'] as const).filter(p => personaHtmlMap![p]).map(p => (
        <button
          type="button"
          class={`persona-switcher-btn ${p === activePersona ? 'persona-switcher-btn--active' : ''}`}
          data-persona={p}
        >
          {personaLabels[locale]?.[p] || p}
        </button>
      ))}
    </div>
    <template id="persona-data" data-map={JSON.stringify(personaHtmlMap)}></template>
  )}

  <div class={`reading-actions-layout ${showStickyActions ? 'reading-actions-layout--article' : ''}`.trim()}>
    {showStickyActions && (
      <StickyReadingActions
        locale={locale}
        variant="blog"
        title={title}
        shareUrl={shareUrl}
        itemId={itemId}
        itemType={itemType}
        isBookmarked={isBookmarked}
        previewMode={previewMode}
        isAuthenticated={isAuthenticated}
        articleRedirect={articleRedirect}
        commentRedirect={commentRedirect}
        likeCount={likeCount}
        commentCount={commentCount}
        isLiked={isLiked}
      />
    )}
    <div class="reading-actions-layout__body">
      <div class="newsprint-prose newsprint-prose--no-dropcap">
        <Fragment set:html={htmlContent} />
      </div>

      {tags && tags.length > 0 && (
        <div class="blog-tags-footer">
          {tags.map(tag => (
            <span class="blog-mono-tag">{tag}</span>
          ))}
        </div>
      )}

      <!-- Admin Actions (admin only) -->
      {itemId && !previewMode && (
        <div class="newsprint-admin-actions" data-toolbar-id={itemId} data-toolbar-api={unpublishApi} data-admin-only hidden={!isAdmin}>
          <a href={editHref} class="newsprint-admin-action-btn">Edit</a>
          <button type="button" class="newsprint-admin-action-btn newsprint-admin-action-btn--unpublish">Unpublish</button>
        </div>
      )}

      <ContentFeedback
        sourceType="blog"
        sourceId={itemId ?? ''}
        locale={locale}
        isAuthenticated={isAuthenticated}
        loginUrl={`/api/auth/login?redirect=${encodeURIComponent(Astro.url.pathname)}`}
        previewMode={previewMode}
      />

      <div data-reading-end></div>

      {(serial.prev || serial.next) && (
        <nav class="blog-post-pager" aria-label={copy.pager}>
          {serial.prev && (
            <a class="blog-post-pager-link" href={`${resolvedBasePath}/${serial.prev.slug}/`}>
              <span class="blog-post-pager-label">{copy.prev}</span>
              <span class="blog-post-pager-title">{serial.prev.title}</span>
            </a>
          )}
          {serial.next && (
            <a class="blog-post-pager-link blog-post-pager-link--next" href={`${resolvedBasePath}/${serial.next.slug}/`}>
              <span class="blog-post-pager-label">{copy.next}</span>
              <span class="blog-post-pager-title">{serial.next.title}</span>
            </a>
          )}
        </nav>
      )}

      {isSeries && (
        <aside class="blog-post-series" aria-labelledby="blog-post-series-title">
          <div class="blog-post-series-head">
            <p id="blog-post-series-title" class="blog-post-series-title">{serial.categoryLabel}</p>
            {serial.categoryHref ? (
              <a class="blog-post-series-more" href={serial.categoryHref}>{copy.seriesMore}</a>
            ) : (
              <span class="blog-post-series-more">{copy.seriesCount}</span>
            )}
          </div>
          <ol class="blog-post-series-list">
            {serial.episodes.map((item, i) => (
              i + 1 === episode ? (
                <li class="blog-post-series-item blog-post-series-item--current">
                  <span class="blog-post-series-ep">{ep(i + 1)}</span>
                  <span class="blog-post-series-name" aria-current="page">{item.title}<span class="blog-post-series-now">{copy.readingNow}</span></span>
                </li>
              ) : (
                <li class="blog-post-series-item">
                  <span class="blog-post-series-ep">{ep(i + 1)}</span>
                  <a class="blog-post-series-name" href={`${resolvedBasePath}/${item.slug}/`}>{item.title}</a>
                </li>
              )
            ))}
          </ol>
        </aside>
      )}

      <!-- Comments Section -->
      <section
        id="comments"
        class="newsprint-comments"
        data-preview-mode={previewMode ? 'true' : 'false'}
        data-post-id={itemId}
        data-content-type={itemType === 'blog' ? 'blog' : 'news'}
        data-locale={locale}
        data-authenticated={isAuthenticated ? 'true' : 'false'}
        data-comment-redirect={commentRedirect}
      >
        <h2 class="newsprint-comments-title">{copy.comments} (<span data-comment-total>{commentCount}</span>)</h2>
        {previewMode && (
          <>
            <!-- Preview mode · comments are read-only. -->
            <p class="newsprint-preview-note">{previewCommentsReadonly}</p>
          </>
        )}
        <div data-comments-list class="newsprint-comments-list"></div>
        <div data-comment-form-wrapper>
          <form data-comment-form class="newsprint-comment-form" style="display:none;">
            <textarea
              data-comment-input
              placeholder={copy.writeComment}
              maxlength="2000"
              rows="3"
              class="newsprint-comment-input"
            ></textarea>
            <div class="newsprint-comment-form-actions">
              <span data-comment-charcount class="newsprint-comment-charcount"></span>
              <button type="submit" class="newsprint-comment-submit">{copy.postComment}</button>
            </div>
          </form>
          <button
            type="button"
            data-comment-login
            class="newsprint-comment-login"
            data-auth-gate
            data-auth-action="comment"
            data-auth-redirect={commentRedirect}
            style="display:none;"
          >
            <div class="newsprint-comment-login-box">
              <div class="newsprint-comment-login-input" aria-hidden="true">{copy.writeComment}</div>
              <div class="newsprint-comment-form-actions">
                <span class="newsprint-comment-charcount">0/2000</span>
                <span class="newsprint-comment-submit newsprint-comment-submit--disabled" aria-hidden="true">{copy.postComment}</span>
              </div>
              <span class="newsprint-comment-login-hint">{copy.loginToComment}</span>
            </div>
          </button>
        </div>
      </section>
    </div>
  </div>
</article>

<ReadingProgressBar locale={locale} />

<script src="../../scripts/share.ts"></script>

<script>
  // "이 글의 차례" / "In this post": the body's h2s in document order (h3 excluded), rebuilt on every page load.
  // Heading ids keep the rule of the removed right-rail contents: existing id → latin slug → section-{n}; duplicates get -{k}.
  // Stays hidden below two headings. Opens by default from 1024px (CSS cannot set the open attribute).
  function slugifyHeading(value: string): string {
    return value
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9\-]/g, '');
  }

  function readHeaderOffsetPx(): number {
    const shell = document.querySelector('.blog-shell');
    const styles = getComputedStyle(shell || document.documentElement);
    const rawValue = styles.getPropertyValue('--blog-shell-header-offset').trim();
    const numericValue = Number.parseFloat(rawValue);
    const rootFontSize = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;

    if (!Number.isFinite(numericValue)) {
      return 80;
    }

    return rawValue.endsWith('rem') ? numericValue * rootFontSize : numericValue;
  }

  function initBlogPostToc(): void {
    const toc = document.querySelector<HTMLDetailsElement>('details.blog-post-toc');
    const list = toc?.querySelector<HTMLOListElement>('.blog-post-toc-list');
    if (!toc || !list) return;

    list.innerHTML = '';
    const prose = document.querySelector('.newsprint-prose');
    const headings = prose
      ? Array.from(prose.querySelectorAll<HTMLHeadingElement>('h2')).filter((heading) => !!heading.textContent?.trim())
      : [];
    if (headings.length < 2) {
      toc.hidden = true;
      return;
    }

    const usedIds = new Map<string, number>();
    headings.forEach((heading, index) => {
      const baseId = heading.id || slugifyHeading(heading.textContent || '') || `section-${index + 1}`;
      const occurrence = (usedIds.get(baseId) || 0) + 1;
      usedIds.set(baseId, occurrence);
      heading.id = occurrence === 1 ? baseId : `${baseId}-${occurrence}`;

      const link = document.createElement('a');
      link.className = 'blog-post-toc-link';
      link.href = `#${heading.id}`;
      link.textContent = heading.textContent?.trim() || '';
      link.addEventListener('click', (event) => {
        event.preventDefault();
        const top = window.scrollY + heading.getBoundingClientRect().top - readHeaderOffsetPx() - 24;
        window.scrollTo({ top, behavior: 'smooth' });
      });

      const item = document.createElement('li');
      item.appendChild(link);
      list.appendChild(item);
    });

    const count = toc.querySelector('[data-toc-count]');
    if (count) count.textContent = String(headings.length);
    toc.open = window.matchMedia('(min-width: 1024px)').matches;
    toc.hidden = false;
  }

  document.addEventListener('astro:page-load', initBlogPostToc);
</script>

<script>
  function initPersonaSwitcher() {
    const template = document.getElementById('persona-data') as HTMLTemplateElement | null;
    if (!template) return;
    const map: Record<string, string> = JSON.parse(template.dataset.map || '{}');
    const prose = document.querySelector('.newsprint-prose');
    const btns = document.querySelectorAll<HTMLButtonElement>('.persona-switcher-btn');
    if (!prose || btns.length === 0) return;

    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        const p = btn.dataset.persona!;
        if (!map[p]) return;
        prose.innerHTML = map[p];
        btns.forEach(b => b.classList.remove('persona-switcher-btn--active'));
        btn.classList.add('persona-switcher-btn--active');
      });
    });
  }

  document.addEventListener('astro:page-load', initPersonaSwitcher);
</script>

<script>
  function initBlogCodeCopy() {
    document.querySelectorAll('.newsprint-prose pre').forEach(pre => {
      if (pre.querySelector('.blog-code-copy')) return;
      const btn = document.createElement('button');
      btn.className = 'blog-code-copy';
      btn.textContent = 'Copy';
      btn.addEventListener('click', async () => {
        const code = pre.querySelector('code');
        if (code) {
          await navigator.clipboard.writeText(code.textContent || '');
          btn.textContent = 'Copied!';
          setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
        }
      });
      (pre as HTMLElement).style.position = 'relative';
      pre.appendChild(btn);
    });
  }
  document.addEventListener('DOMContentLoaded', initBlogCodeCopy);
  initBlogCodeCopy();
</script>
```

- [ ] **Step 7: CSS 추가** (Edit 도구로) — `global.css`의 `/* ── Masthead (reuse newsprint pattern but in blog context) ── */` 주석 **바로 위**에 다음 블록을 넣는다(블록 끝의 빈 줄 한 줄 포함). `/* ── Tags Footer ── */` 블록 바로 뒤다. old_string은 그 주석 한 줄, new_string은 아래 블록 + 그 주석 한 줄이다.

```css
/* ── Blog post A: one column (crumb, dek, byline, contents, pager, series) ── */
.blog-post-crumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
  margin-bottom: 1.25rem;
  font-family: var(--font-blog-ui);
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.blog-post-crumb a {
  color: var(--color-text-secondary);
  text-decoration: none;
}

.blog-post-crumb a:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.blog-post-dek {
  margin: 0.4rem 0 0;
  font-size: 1.05rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.blog-post-byline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem 1.5rem;
  margin-top: 1rem;
  padding: 0.7rem 0;
  border-top: 2px solid var(--color-text-primary);
  border-bottom: 1px solid var(--color-text-primary);
}

.blog-post-byline-meta {
  margin: 0;
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.blog-post-byline-meta strong {
  font-family: var(--font-blog-heading);
  font-weight: 700;
  color: var(--color-text-primary);
}

.blog-post-toc {
  margin-top: 1.25rem;
  padding: 0.8rem 1rem;
  background: var(--color-bg-secondary);
  font-family: var(--font-blog-ui);
  font-size: 0.85rem;
}

.blog-post-toc[hidden] {
  display: none;
}

.blog-post-toc-summary {
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-muted);
}

.blog-post-toc-list {
  margin: 0.5rem 0 0;
  padding-left: 1.25rem;
  line-height: 1.9;
  color: var(--color-text-secondary);
}

.blog-post-toc-list li {
  break-inside: avoid;
}

.blog-post-toc-link {
  color: var(--color-text-secondary);
  text-decoration: none;
}

.blog-post-toc-link:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.blog-post-pager {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
  margin: 2rem 0 0;
}

.blog-post-pager-link {
  display: block;
  min-width: 0;
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  text-decoration: none;
  transition: border-color 150ms ease;
}

.blog-post-pager-link:hover {
  border-color: var(--color-text-muted);
}

/* "next" stays in the right column even when there is no "previous" */
.blog-post-pager-link--next {
  grid-column: 2;
  text-align: right;
}

.blog-post-pager-label {
  display: block;
  margin-bottom: 0.25rem;
  font-family: var(--font-blog-ui);
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.blog-post-pager-title {
  display: block;
  font-family: var(--font-blog-heading);
  font-size: 0.92rem;
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: -0.02em;
  overflow-wrap: anywhere;
}

.blog-post-series {
  margin: 2.25rem 0 0;
}

.blog-post-series-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 2px solid var(--color-text-primary);
}

.blog-post-series-title {
  margin: 0;
  font-family: var(--font-blog-heading);
  font-size: 1.1rem;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.03em;
  color: var(--color-text-primary);
}

.blog-post-series-more {
  flex-shrink: 0;
  font-family: var(--font-blog-ui);
  font-size: 0.78rem;
  color: var(--color-text-muted);
  text-decoration: none;
}

a.blog-post-series-more:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.blog-post-series-list {
  margin: 0.3rem 0 0;
  padding: 0;
  list-style: none;
}

.blog-post-series-item {
  display: grid;
  grid-template-columns: 2.6em minmax(0, 1fr);
  gap: 0.4rem;
  padding: 0.5rem 0;
  border-bottom: 1px dotted var(--color-border);
  font-size: 0.9rem;
}

.blog-post-series-ep {
  font-family: var(--font-masthead);
  font-size: 0.85rem;
  font-weight: 500;
  font-variant-numeric: lining-nums;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.blog-post-series-name {
  min-width: 0;
  font-family: var(--font-blog-heading);
  font-weight: 600;
  line-height: 1.45;
  letter-spacing: -0.02em;
  color: var(--color-text-secondary);
  text-decoration: none;
  overflow-wrap: anywhere;
}

a.blog-post-series-name:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.blog-post-series-item--current .blog-post-series-ep,
.blog-post-series-now {
  color: var(--color-accent);
}

.blog-post-series-item--current .blog-post-series-name {
  color: var(--color-text-primary);
}

.blog-post-series-now {
  font-family: var(--font-blog-ui);
  font-size: 0.75rem;
  font-weight: 600;
}

.blog-post-series + .newsprint-comments,
.blog-post-pager + .newsprint-comments {
  margin-top: 2.5rem;
}

/* Blog post A: desktop */
@media (min-width: 1024px) {
  .blog-post-toc-list {
    columns: 2;
    column-gap: 1.75rem;
  }
}

/* Blog post A: mobile */
@media (max-width: 767px) {
  .blog-post-byline {
    flex-wrap: wrap;
  }

  .blog-post-pager {
    grid-template-columns: minmax(0, 1fr);
  }

  .blog-post-pager-link--next {
    grid-column: auto;
  }
}

```

- [ ] **Step 8: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/blog-post-column.test.cjs
node frontend/tests/blog-serial.test.mjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-detail-sidebar-structure.test.cjs
node frontend/tests/blog-v2.test.cjs
node frontend/tests/blog-mobile-sidebar-structure.test.cjs
node frontend/tests/blog-toc-structure.test.cjs
node frontend/tests/public-detail-query-contract.test.cjs
node frontend/tests/public-term-index.test.cjs
node frontend/tests/blog-comment-fonts.test.cjs
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/news-article-briefing.test.cjs
node frontend/tests/blog-sidebar-layout.test.cjs
node frontend/tests/blog-title-fonts.test.cjs
node frontend/tests/sticky-reading-actions-structure.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 세 테스트를 뺀 모두 PASS(`blog-toc-structure`는 아직 남은 `BlogTOC.astro`를 읽어 PASS — Task 3에서 함께 지운다), 빌드 "Complete!".
- `blog-sidebar-layout` "Blog sidebar panel must use the shared card radius", `blog-title-fonts` "Missing IBM Plex Sans font import: IBM+Plex+Sans", `sticky-reading-actions-structure` "Missing helpful action marker: data-reading-action=\"helpful\"" — 기준선과 **같은 메시지**.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/lib/pageData/blogDetailPage.ts "frontend/src/pages/ko/blog/[slug].astro" "frontend/src/pages/en/blog/[slug].astro" frontend/src/components/blog/BlogArticleLayout.astro frontend/src/styles/global.css frontend/tests/blog-post-column.test.cjs frontend/tests/detail-rail-actions-placement.test.cjs frontend/tests/blog-list-serial.test.cjs frontend/tests/blog-sidebar-layout.test.cjs frontend/tests/blog-detail-sidebar-structure.test.cjs frontend/tests/blog-v2.test.cjs
git commit -m "feat: blog post as one column with series byline, contents, pager and series list"
```

---

## Task 3: 레일·옛 목차·경로 컴포넌트와 CSS 정리 (TDD)

**Files:**
- Delete (`git rm`): `frontend/src/components/blog/BlogTOC.astro`, `frontend/src/components/blog/BlogBreadcrumb.astro`, `frontend/src/components/common/ReadingActionsRail.astro`, `frontend/tests/blog-toc-structure.test.cjs`
- Modify: `frontend/src/components/common/StickyReadingActions.astro`(Edit 5곳), `frontend/src/styles/global.css`(삭제 스크립트), `frontend/src/i18n/index.ts`(**CRLF → Edit 도구만**, 2줄 삭제)
- Tests: `blog-post-column.test.cjs`, `detail-rail-actions-placement.test.cjs`, `sticky-reading-actions-structure.test.cjs`, `reading-actions-layout-regression.test.cjs`, `blog-sidebar-layout.test.cjs`(Edit), `reading-actions-editorial-subtle.test.cjs`(Read 후 Write로 전체 교체)

- [ ] **Step 1: 다른 사용처 확인** — 아래 결과가 기대와 다르면(다른 파일이 나오면) 그 항목은 지우지 말고 멈추고 보고한다.

Run:
```bash
git status --short -- frontend/src/components/blog/BlogTOC.astro frontend/src/components/blog/BlogBreadcrumb.astro frontend/src/components/common/ReadingActionsRail.astro frontend/src/components/common/StickyReadingActions.astro frontend/src/styles/global.css frontend/src/i18n/index.ts frontend/tests/blog-toc-structure.test.cjs frontend/tests/blog-post-column.test.cjs frontend/tests/detail-rail-actions-placement.test.cjs frontend/tests/sticky-reading-actions-structure.test.cjs frontend/tests/reading-actions-layout-regression.test.cjs frontend/tests/reading-actions-editorial-subtle.test.cjs frontend/tests/blog-sidebar-layout.test.cjs
grep -rnw "BlogTOC\|BlogBreadcrumb\|ReadingActionsRail\|placement\|placementClass" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rn "blog\.onThisPage" frontend/src
grep -rln "blog-toc\|blog-rail\|blog-breadcrumb\|blog-article-meta\|blog-article-category\|reading-actions-rail\|rail-placement\|newsprint-article-nav\|newsprint-nav-" frontend/src
```
Expected:
- status 출력 없음.
- 첫 grep: `ReadingActionsRail.astro`의 `placement="rail"` 1줄과 `StickyReadingActions.astro`의 5줄(5, 23, 58, 63, 126행)만. (`-w`라 `replacement` 같은 단어는 안 잡힌다.)
- 둘째 grep: `BlogTOC.astro` 1줄, `i18n/index.ts` 2줄.
- 셋째 grep: `BlogBreadcrumb.astro`, `BlogTOC.astro`, `ReadingActionsRail.astro`, `StickyReadingActions.astro`, `styles/global.css`만.

- [ ] **Step 2: 실패하는 단언 추가·테스트 갱신**

Edit 도구로(각 `old` → `new`):

1. `frontend/tests/detail-rail-actions-placement.test.cjs`

   old:
   ```js
   assertIncludes(readingActionsRail, 'placement?:', 'reading actions placement prop');
   ```
   new:
   ```js
   // The rail placement (ReadingActionsRail, blog only) was removed with blog post A (2026-10-17).
   if (readingActionsRail.includes('placement')) throw new Error('reading actions have no rail placement prop');
   ```

2. `frontend/tests/detail-rail-actions-placement.test.cjs`

   old:
   ```js
   assertIncludes(css, '.reading-actions--rail-placement {', 'desktop rail placement action styles');
   assertIncludes(css, '.newsprint-rail-stack {', 'newsprint rail stack wrapper styles');
   assertIncludes(css, '.blog-rail {', 'blog rail wrapper styles');
   assertIncludes(css, '.blog-rail .blog-toc {', 'blog TOC inside unified rail styles');
   ```
   new:
   ```js
   if (css.includes('.reading-actions--rail-placement')) throw new Error('rail placement action styles removed');
   assertIncludes(css, '.newsprint-rail-stack {', 'newsprint rail stack wrapper styles');
   if (css.includes('.blog-rail')) throw new Error('blog rail wrapper styles removed');
   if (css.includes('.blog-toc')) throw new Error('blog rail TOC styles removed');
   ```

3. `frontend/tests/sticky-reading-actions-structure.test.cjs`

   old:
   ```js
   assertIncludes(stickyActions, "const placementClass = placement === 'rail' ? 'reading-actions--rail-placement' : '';", 'placement class helper');
   assertIncludes(stickyActions, 'reading-actions reading-actions--article ${placementClass}', 'article action rail modifier');
   assertIncludes(stickyActions, 'reading-actions reading-actions--term reading-actions--article ${placementClass}', 'term action rail article modifier');
   ```
   new:
   ```js
   assertNotIncludes(stickyActions, 'placement', 'rail placement (removed with ReadingActionsRail)');
   assertIncludes(stickyActions, '<aside class="reading-actions reading-actions--article"', 'article action modifier');
   assertIncludes(stickyActions, 'class="reading-actions reading-actions--term reading-actions--article"', 'term action article modifier');
   ```

4. `frontend/tests/reading-actions-layout-regression.test.cjs`

   old:
   ```js
   assertIncludes(
     css,
     '.reading-actions--rail-placement .reading-actions__button:hover {',
     'desktop rail action hover feedback'
   );

   assertIncludes(
     css,
     '.reading-actions--rail-placement .reading-actions__button:focus-visible {',
     'desktop rail action focus-visible feedback'
   );
   ```
   new:
   ```js
   // The rail placement (ReadingActionsRail, blog only) was removed with blog post A (2026-10-17):
   // every detail page uses the inline article actions above.
   assertNotIncludes(
     css,
     '.reading-actions--rail-placement',
     'removed rail placement action styles'
   );
   ```

5. `frontend/tests/blog-sidebar-layout.test.cjs`

   old:
   ```js
   assert.ok(
     css.includes('width: 15.25rem;') && css.includes('flex: 0 0 15.25rem;'),
     'Desktop blog action and TOC rail should widen slightly to support a single-row action toolbar',
   );
   ```
   new:
   ```js
   assert.ok(
     !css.includes('.blog-rail'),
     'The blog action and TOC rail is removed (blog post A: inline actions + contents in the column)',
   );
   ```

6. `frontend/tests/blog-sidebar-layout.test.cjs`

   old:
   ```js
   assert.ok(
     css.includes('.blog-toc {') && css.includes('top: calc(var(--blog-shell-header-offset) + var(--blog-shell-rail-gap));'),
     'Blog TOC must align with the shared rail offset',
   );
   ```
   new:
   ```js
   assert.ok(
     !css.includes('.blog-toc'),
     'The right-rail blog TOC is removed (blog post A uses details.blog-post-toc)',
   );
   ```

7. `frontend/tests/blog-post-column.test.cjs`

   old:
   ```js
   console.log('blog-post-column.test.cjs passed');
   ```
   new:
   ```js
   // removed with the rail (Task 3): blog-detail-only components, the rail placement and their CSS
   for (const file of ['components/blog/BlogTOC.astro', 'components/blog/BlogBreadcrumb.astro', 'components/common/ReadingActionsRail.astro']) {
     assert(!fs.existsSync(path.join(src, file)), `${file} deleted`);
   }
   assert(!read('components/common/StickyReadingActions.astro').includes('placement'), 'StickyReadingActions: no rail placement');
   for (const gone of ['.blog-toc', '.blog-rail', '.blog-breadcrumb', '.blog-article-meta', '.blog-article-category', '.reading-actions-rail', '.reading-actions--rail-placement', '.newsprint-article-nav', '.newsprint-nav-']) {
     assert(!css.includes(gone), `unused CSS removed: ${gone}`);
   }
   // still used elsewhere: category pages (toolbar), news/handbook layouts and handbook-popup.ts (persona float)
   for (const kept of ['.blog-mobile-toolbar {', '.persona-float {', '.persona-float--back', '.blog-article-title {', '.blog-article-header {', '.blog-shell .newsprint-comments-title {']) {
     assert(css.includes(kept), `CSS kept: ${kept}`);
   }
   assert(!read('i18n/index.ts').includes("'blog.onThisPage'"), 'unused i18n key removed');

   console.log('blog-post-column.test.cjs passed');
   ```

`reading-actions-editorial-subtle.test.cjs` 전체 교체(Read 후 Write 도구로):

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

function assertNotIncludes(haystack, needle, label) {
  if (haystack.includes(needle)) {
    throw new Error(`Unexpected ${label}: ${needle}`);
  }
}

// Blog post A (2026-10-17): the editorial rail placement (ReadingActionsRail, blog only) is gone.
// News, handbook and blog details all use the inline article actions; keep them quiet and flat.
const css = read('frontend/src/styles/global.css');
const articleButtonBlock = css.split('\n.reading-actions--article .reading-actions__button {')[1]?.split('}')[0] || '';

assertNotIncludes(css, '.reading-actions--rail-placement', 'removed rail placement styles');

assertIncludes(
  articleButtonBlock,
  'color: var(--color-text-secondary);',
  'subtle article action text color'
);

assertIncludes(
  articleButtonBlock,
  'background: color-mix(in srgb, var(--color-bg-secondary) 92%, transparent);',
  'quiet article action surface'
);

assertNotIncludes(articleButtonBlock, 'box-shadow', 'raised article action buttons');
assertNotIncludes(articleButtonBlock, 'transform:', 'lifted article action buttons');

console.log('reading-actions-editorial-subtle.test.cjs passed');
```

Run:
```bash
node frontend/tests/blog-post-column.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/sticky-reading-actions-structure.test.cjs
node frontend/tests/reading-actions-layout-regression.test.cjs
node frontend/tests/reading-actions-editorial-subtle.test.cjs
node frontend/tests/blog-sidebar-layout.test.cjs
```
Expected (구현 전이라 전부 FAIL):
- `blog-post-column`: "components/blog/BlogTOC.astro deleted"
- `detail-rail-actions-placement`: "reading actions have no rail placement prop"
- `sticky-reading-actions-structure`: "Unexpected rail placement (removed with ReadingActionsRail): placement"
- `reading-actions-layout-regression`: "Unexpected removed rail placement action styles: .reading-actions--rail-placement"
- `reading-actions-editorial-subtle`: "Unexpected removed rail placement styles: .reading-actions--rail-placement"
- `blog-sidebar-layout`: "The blog action and TOC rail is removed (blog post A: inline actions + contents in the column)"(Step 6 뒤 기준선 메시지로 돌아온다)

- [ ] **Step 3: 파일 삭제**

```bash
git rm frontend/src/components/blog/BlogTOC.astro frontend/src/components/blog/BlogBreadcrumb.astro frontend/src/components/common/ReadingActionsRail.astro frontend/tests/blog-toc-structure.test.cjs
```

- [ ] **Step 4: `StickyReadingActions.astro`·i18n 수정** (Edit 도구로. `i18n/index.ts`는 CRLF라 Edit만)

1. `frontend/src/components/common/StickyReadingActions.astro`

   old:
   ```astro
     variant: 'news' | 'blog' | 'term';
     placement?: 'inline' | 'rail';
     title: string;
   ```
   new:
   ```astro
     variant: 'news' | 'blog' | 'term';
     title: string;
   ```

2. `frontend/src/components/common/StickyReadingActions.astro`

   old:
   ```astro
     variant,
     placement = 'inline',
     title,
   ```
   new:
   ```astro
     variant,
     title,
   ```

3. `frontend/src/components/common/StickyReadingActions.astro`

   old:
   ```astro
       };

   const placementClass = placement === 'rail' ? 'reading-actions--rail-placement' : '';
   ---
   ```
   new:
   ```astro
       };
   ---
   ```

4. `frontend/src/components/common/StickyReadingActions.astro`

   old:
   ```astro
       class={`reading-actions reading-actions--term reading-actions--article ${placementClass}`.trim()}
   ```
   new:
   ```astro
       class="reading-actions reading-actions--term reading-actions--article"
   ```

5. `frontend/src/components/common/StickyReadingActions.astro`

   old:
   ```astro
     <aside class={`reading-actions reading-actions--article ${placementClass}`.trim()} aria-label={locale === 'ko' ? '글 액션' : 'Reading actions'}>
   ```
   new:
   ```astro
     <aside class="reading-actions reading-actions--article" aria-label={locale === 'ko' ? '글 액션' : 'Reading actions'}>
   ```

6. `frontend/src/i18n/index.ts`

   old:
   ```ts
       'blog.title': 'IT Blog',
       'blog.onThisPage': 'On This Page',
   ```
   new:
   ```ts
       'blog.title': 'IT Blog',
   ```

7. `frontend/src/i18n/index.ts`

   old:
   ```ts
       'blog.title': 'IT 블로그',
       'blog.onThisPage': '이 페이지에서',
   ```
   new:
   ```ts
       'blog.title': 'IT 블로그',
   ```

- [ ] **Step 5: CSS 삭제** — 여러 덩어리를 Edit로 옮기기는 위험하므로 아래 스크립트를 쓴다.
  1. 다음 내용을 **Write 도구로** scratchpad에 `drop-blog-post-css.cjs`로 저장한다(repo 안에 만들지 않는다).

```js
// Run from the repo root: node <this file>
// Removes the CSS only the old blog post page used (article nav, breadcrumb, right rail + TOC, calendar meta line,
// ReadingActionsRail and the rail placement of StickyReadingActions). Each cut is checked by its line count;
// nothing is written unless every cut matches.
const fs = require('fs');

const file = 'frontend/src/styles/global.css';
const lines = fs.readFileSync(file, 'utf8').split('\n');

// Remove lines [start, end) where start = first line equal to `from` (minus `before` lines above it)
// and end = first line equal to `to` after it (minus `keep` lines above it).
function cut(name, from, to, expected, { before = 0, keep = 0 } = {}) {
  const at = lines.indexOf(from);
  if (at < 0) throw new Error(`${name}: start not found: ${from}`);
  const stop = lines.indexOf(to, at + 1);
  if (stop < 0) throw new Error(`${name}: end not found: ${to}`);
  const start = at - before;
  const end = stop - keep;
  if (end - start !== expected) {
    throw new Error(`${name}: expected ${expected} lines, found ${end - start} (lines ${start + 1}-${end})`);
  }
  lines.splice(start, end - start);
  console.log(`${name}: removed ${expected} lines from line ${start + 1}`);
}

// 1. "목록으로 / 다음 글" article nav (blog layout only), incl. .blog-shell .newsprint-nav-next-title and its 640px query
cut('article nav', '.newsprint-article-nav {', '   CATEGORY FILTER TABS', 84, { keep: 1 });
// 2. breadcrumb + right rail + rail TOC (incl. the 1280px / 1279px queries)
cut('breadcrumb + rail + toc', '/* ── Breadcrumb ── */', '/* ── Article Header ── */', 154);
// 3. calendar meta line + category label under the title
cut('article meta', '.blog-article-meta {', '/* ── Code Copy Button ── */', 30);
// 4. ReadingActionsRail wrapper
cut('actions rail wrapper', '.reading-actions-rail {', '.reading-actions-layout {', 12);
// 5. rail placement: mobile base
cut('rail placement base', '.reading-actions--rail-placement {', '.reading-actions__items {', 4);
// 6. rail placement: desktop reset
cut('rail placement desktop', '  .reading-actions--rail-placement {', '  .reading-actions__items {', 14);
// 7. rail placement: desktop four-button row
cut('rail placement row', '  .reading-actions--rail-placement .reading-actions__items--article {', '  .reading-actions__items--article {', 11);
// 8. rail placement: desktop buttons + .blog-rail overrides
cut('rail placement buttons', '  .reading-actions--rail-placement .reading-actions__button {', '  .reading-actions--article .reading-actions__share-wrapper {', 59);
// 9. rail placement: status + sticky-within-rail (keep the closing brace of the 1024px query)
cut('rail placement sticky', '  .reading-actions--rail-placement .reading-actions__status {', '/* ── HOMEPAGE ── */', 14, { before: 1, keep: 2 });

fs.writeFileSync(file, lines.join('\n'));
console.log('done');
```

  2. repo 루트에서 `node <scratchpad>/drop-blog-post-css.cjs` → 아래 출력(시작 줄 번호는 다른 세션 변경으로 달라질 수 있다. **줄 수**가 하나라도 다르면 스크립트가 아무것도 쓰지 않고 오류를 낸다 → 멈추고 보고):
     ```
     article nav: removed 84 lines from line 1790
     breadcrumb + rail + toc: removed 154 lines from line 10217
     article meta: removed 30 lines from line 10231
     actions rail wrapper: removed 12 lines from line 10623
     rail placement base: removed 4 lines from line 10653
     rail placement desktop: removed 14 lines from line 10832
     rail placement row: removed 11 lines from line 10838
     rail placement buttons: removed 59 lines from line 10868
     rail placement sticky: removed 14 lines from line 10887
     done
     ```
  - 지워지는 것: `.newsprint-article-nav`·`.newsprint-article-nav-row`·`.newsprint-nav-*`(`.blog-shell .newsprint-nav-next-title`, 640px 쿼리 포함), `/* ── Breadcrumb ── */` + `.blog-breadcrumb*`, `/* ── TOC (Right Rail) ── */` + `.blog-rail*`·`.blog-toc*`(1280/1279px 쿼리 포함), `.blog-article-meta`·`.blog-article-meta svg`·`.blog-article-category`·`::before`, `.reading-actions-rail`·`__content`, `.reading-actions--rail-placement`(기본 1개 + 1024px 쿼리 안의 리셋·4버튼 줄·`display: contents`·버튼/hover/focus/svg/metric/icon-only/count·`.blog-rail …` 4개·status·sticky-within-rail 주석과 블록). 1024px 쿼리의 닫는 `}`와 `/* ── Article Header ── */`, `/* ── Code Copy Button ── */`, `.reading-actions-layout {`, `.reading-actions__items {` 등은 남는다.

Run:
```bash
grep -n "blog-toc\|blog-rail\|blog-breadcrumb\|blog-article-meta\|blog-article-category\|reading-actions-rail\|rail-placement\|newsprint-article-nav\|newsprint-nav-" frontend/src/styles/global.css
grep -rnw "BlogTOC\|BlogBreadcrumb\|ReadingActionsRail\|placement\|placementClass" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rn "blog\.onThisPage" frontend/src
```
Expected: 셋 다 결과 없음.

- [ ] **Step 6: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/blog-post-column.test.cjs
node frontend/tests/detail-rail-actions-placement.test.cjs
node frontend/tests/reading-actions-layout-regression.test.cjs
node frontend/tests/reading-actions-editorial-subtle.test.cjs
node frontend/tests/blog-serial.test.mjs
node frontend/tests/blog-list-serial.test.cjs
node frontend/tests/blog-v2.test.cjs
node frontend/tests/blog-detail-sidebar-structure.test.cjs
node frontend/tests/blog-mobile-sidebar-structure.test.cjs
node frontend/tests/blog-comment-fonts.test.cjs
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/news-article-briefing.test.cjs
node frontend/tests/article-v2.test.cjs
node frontend/tests/font-roles.test.cjs
node frontend/tests/retro-decoration-removed.test.cjs
node frontend/tests/theme-palette.test.cjs
node frontend/tests/sticky-reading-actions-structure.test.cjs
node frontend/tests/blog-sidebar-layout.test.cjs
node frontend/tests/blog-title-fonts.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 세 테스트를 뺀 모두 PASS, 빌드 "Complete!".
- `sticky-reading-actions-structure` "Missing helpful action marker: data-reading-action=\"helpful\"", `blog-sidebar-layout` "Blog sidebar panel must use the shared card radius", `blog-title-fonts` "Missing IBM Plex Sans font import: IBM+Plex+Sans" — 기준선과 **같은 메시지**.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/common/StickyReadingActions.astro frontend/src/styles/global.css frontend/src/i18n/index.ts frontend/tests/blog-post-column.test.cjs frontend/tests/detail-rail-actions-placement.test.cjs frontend/tests/sticky-reading-actions-structure.test.cjs frontend/tests/reading-actions-layout-regression.test.cjs frontend/tests/reading-actions-editorial-subtle.test.cjs frontend/tests/blog-sidebar-layout.test.cjs
git commit -m "chore: remove blog rail, old TOC, breadcrumb and rail placement"
```

(`git rm`으로 stage된 파일 4개 삭제가 함께 커밋된다.)

---

## Task 4: 검증 (컨트롤러)

- [ ] 전체 테스트를 **이름 + 첫 오류 메시지로** 기준선(PASS 82 / FAIL 19)과 비교한다.
  ```bash
  for f in frontend/tests/*.cjs frontend/tests/*.mjs; do node "$f" >/dev/null 2>&1 && echo "PASS $(basename $f)" || echo "FAIL $(basename $f)"; done
  ```
  - 실패 목록은 기준선 19개와 같아야 한다(신규 FAIL 0). 실패 테스트의 첫 오류 메시지도 기준선과 같은지 본다(`node <file> 2>&1 | grep -m1 -E "^(\w*Error|AssertionError)"`).
  - 이름 변화는 `blog-post-column` 신규 PASS, `blog-toc-structure` 삭제뿐 → **PASS 82 / FAIL 19**.
- [ ] `cd frontend && npm run build` "Complete!".
- [ ] 브라우저(`.claude/launch.json`의 `frontend-dev`, 포트 4321) 매트릭스: 종이·순백·다크 × 1100px·375px × ko/en, 그리고 900px(하단 바·접힌 차례)
  - 대상: 학습 노트 2화 `/ko/blog/rag-ai-retrieval-augmented-generation/`, 1화(이전 없음 → 다음 카드가 오른쪽 칸), 5화(다음 없음), 짧은 글 `/ko/blog/importance-of-flow-over-features/`(연재 칸·연재 목록 없음, "← 이전 글"만). EN 발행 글은 0편이라 EN은 없는 글 404 안내가 정상이다.
  - 스크린샷(테마·폭·locale마다), 가로 넘침 0(`document.documentElement.scrollWidth <= window.innerWidth`)
  - 대비 검사: 경로 줄, 요약, 바이라인(muted), 분야 점 라벨, 차례 요약 줄·링크(secondary 배경 위), 이전·다음 라벨(muted)·제목, 연재 머리 오른쪽(muted), 회차 번호(muted), 지금 읽는 글(accent), 다크 포함
  - ≥1024px: 차례 열림·2단, 액션 막대가 본문 오른쪽 72px. <1024px: 차례 접힘·1단, 액션 하단 바. ≤767px: 바이라인 줄바꿈, 이전·다음 1단, 제목 약 1.8rem.
- [ ] 직접 클릭
  - 차례 링크 → 헤더에 가리지 않고 해당 h2로 부드럽게 스크롤. 다른 글로 ViewTransitions 이동 후 차례가 중복 없이 새 글 기준으로 다시 만들어짐.
  - 저장(비로그인 → 로그인 안내, 로그인 → 상태 반영), 좋아요, 댓글 수 링크(`#comments`), 공유 메뉴(X/LinkedIn/URL 복사), 용어 팝업, 코드 복사, 진행 바.
  - 이전·다음 카드, 연재 목록 링크(지금 글은 링크 아님), "전체 보기 →"(분야 페이지), 경로 줄 "← IT 블로그"·분야 링크.
  - 댓글 영역(h2 "댓글 (n)"), 관리자 로그인 시 Edit/Unpublish 노출.
  - 페이지의 `[data-item-id][data-item-type="blog"]`가 1개.
- [ ] 회귀: 분야 페이지 `/ko/blog/category/study/`(사이드바·서랍 토글·무한 스크롤 유지), 목록 `/ko/blog/` 정상, 뉴스·용어 상세의 액션 막대(1024px 이상 오른쪽 막대, 미만 하단 바)·떠 있는 "목록으로" 버튼 변화 없음.
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 5: 문서

- [ ] 스펙 [[2026-10-17-blog-post-column-design]] Status를 `implemented (2026-10-17)`로 바꾼다.
- [ ] 이 계획의 Status를 `done (2026-10-17)`로 바꾸고, 문서 끝에 "## 실행 결과 (2026-10-17)"(커밋 해시, 테스트 이름 비교 결과, 빌드, 매트릭스 결과, 계획 대비 변경, 후속)를 적는다.
- [ ] `ACTIVE_SPRINT.md`의 `REDESIGN-BLOG-LIST` 항목 **바로 다음 줄**에 추가한다.
  `- [x] **REDESIGN-BLOG-POST** — 블로그 글 상세를 칼럼 한 편(A)으로: 한 단(사이드바·레일 제거), 경로 줄(분야·n화), 요약, 바이라인(Amy · 연도 포함 KST 날짜 · 읽기 시간 / 분야 · N편 중 n화), 접히는 차례(h2), 공용 인라인 액션(1024px+ 오른쪽 막대), 같은 연재 앞·뒤 회차 이전·다음(순서 역전 버그 수정), 연재 목록, 댓글 h2, BlogTOC·BlogBreadcrumb·ReadingActionsRail·rail placement 삭제 — [[2026-10-17-blog-post-column-design]], [[2026-10-17-blog-post-column]]`
- [ ] `grep -rln "BlogTOC\|ReadingActionsRail\|BlogBreadcrumb\|blog-rail\|newsprint-article-nav\|placement=\"rail\"" vault --include=*.md`로 관련 노트를 찾는다. `90-Archive/`와 이번 스펙·계획, 지난 날짜의 완료된 계획 본문은 빼고, 블로그 상세의 **현재 구조**를 설명하는 노트만 최소한으로 고친다(예: `2026-10-15-site-redesign-phase7-blog.md`가 아직 `plans/`에 있으면 "글 상세는 2026-10-17 칼럼 한 편(A)으로 대체" 한 줄).
- [ ] 알려진 한계·후속을 실행 결과에 적는다: 본문 마크다운의 `# 제목`이 본문 안 `h1`이 되는 글(RAG 글), `reading_time_min`이 빈 글(바이라인 생략), 글 100편 상한(목록과 같음), 미리보기 초안은 목록에 없어 연재 표시·이전·다음 없음, 한글 제목 차례 id가 `section-{n}`이나 `llm---`처럼 읽기 어려운 형태(옛 규칙 유지), `BlogShell`의 `showTOC`/`toc` 슬롯이 쓰는 곳 없이 남음, EN 발행 글 0편.
- [ ] 커밋(고친 vault 노트 경로만 지정해 add한다. `vault/.obsidian/*`는 넣지 않는다):
  ```bash
  git add vault/09-Implementation/plans/2026-10-17-blog-post-column-design.md vault/09-Implementation/plans/2026-10-17-blog-post-column.md vault/09-Implementation/plans/ACTIVE_SPRINT.md
  git commit -m "docs: record blog post column redesign"
  ```
  (Task 5에서 고친 다른 vault 노트가 있으면 그 경로도 `git add`에 더한다.)

---

## 실행 결과 (2026-10-17)

- 커밋: `793afbba` 연재 위치 계산(locatePost·toSerialProps·연도 포함 날짜), `fd393dc4` 글 상세를 한 단 칼럼으로(경로 줄·바이라인·차례·인라인 액션·이전/다음·연재 목록, 다음 글 쿼리 제거), `d4fcb440` 레일·옛 목차·경로·레일 배치 삭제.
- 테스트: PASS 82 / FAIL 19, 기준선과 실패 이름·첫 오류 동일. 변화는 `blog-post-column` 추가, `blog-toc-structure` 삭제뿐. 빌드 성공(Task 2·3 후 각각). 계획 단계에서 scratch 복사본 + 운영 데이터 렌더로 사전 검증.
- 브라우저 클릭 검증(/ko/blog/rag-ai-retrieval-augmented-generation/): 차례 6개 링크·4번째 클릭 시 해당 제목으로 이동, 저장 버튼 1개, 공유 메뉴(X·LinkedIn·URL 복사) 열림, 용어 팝업 열림, 이전·다음 "← 1화 / 3화 →", 연재 목록 5편(2화 aria-current), 끝 블록 순서 태그 → reading-end → 이전·다음 → 연재 → 댓글, 댓글 제목 h2, 레일·사이드바 없음.
- 매트릭스: 종이·순백·다크 × 1100px·375px, 대상 2화·1화(이전 없음 → "2화 →"만)·5화(다음 없음 → "← 4화"만)·짧은 글(연재 없음, "← 이전 글") — 가로 넘침 0. 차례는 1100px 펼침·375px 접힘. 대비 스캔의 `reading-actions__count` 2.6~2.8은 스캐너가 `color(srgb …)` 배경을 잘못 읽은 오탐(실제 #5A544B on #EFEAE0 ≈ 6.5:1), 그 외 미달 0.
- 회귀: 분야 페이지(사이드바·모바일 토글 유지, 5건), 뉴스 상세 액션 막대(본문 오른쪽 72px, 저장 버튼 1개) 변화 없음. EN은 글 0편이라 상세는 Not Found 안내.
- 알려진 한계: 본문 마크다운의 `# 제목` 때문에 일부 글에 h1이 2개(콘텐츠 문제, 범위 밖). `BlogShell`의 `showTOC`/`toc` 슬롯은 사용처 없음(후속 정리 후보).
