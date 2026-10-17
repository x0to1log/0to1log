# AI 제품 상세 A(리뷰 지면) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** done (2026-10-18) — 실행 결과는 문서 끝 참조.

**Goal:** `/ko|en/products/{slug}/`를 섹션 11개가 같은 무게로 쌓인 페이지(ChatGPT 기준 4,365px)에서 가운데 한 단(본문 최대 900px)의 리뷰 지면으로 바꾼다. 위에서부터 "경로 줄(← AI 제품군 · 분야) → 머리(로고·원래 이름·한 줄 소개·분야/태그 | 스펙 상자: 가격·난이도·플랫폼·한국어 + 사이트 방문·찜) → 에디터 한마디(큰 인용) → 장단점 2칸 → 이렇게 써보세요(3개 + `details` 더 보기) → 주요 기능 · 이런 상황에 추천 2단 → 가격 → 시작하는 법 → 소개 → 한국어 메모 · 공식 자료 → 관련 뉴스 → 비슷한 도구(목록과 같은 `ProductRow`) → FAQ → 확인일 · 피드백 · 관리자"이다. 상세의 sticky 검색과 큰 하단 CTA를 없애고, 모바일(≤767px)에서는 스펙 상자의 버튼 줄을 화면 아래에 고정한다.

**Architecture:**
- 새 `components/products/ProductRow.astro`: 목록 `ProductCatalogSection.astro`의 줄 마크업(`li.product-row`)을 그대로 옮긴 컴포넌트. Props `product`, `locale`, 선택 `overflow`(목록용 `data-overflow`), `searchText`(목록용 `data-search-text`, 없으면 속성 생략). 목록 섹션과 상세 비슷한 도구가 함께 쓴다.
- `productsPage.ts`의 `fetchAlternatives` 매핑에 `name_original: p.name as string`을 더한다(쿼리 열·함수 순서 그대로). 비슷한 도구가 locale 이름("오픈클로우") 대신 원래 이름("OpenClaw")을 보인다.
- `ProductDetail.astro`를 새 구성으로 통째로 다시 쓴다(Props·관리자 마크업·관리자 스크립트 그대로). 분야 라벨은 `lib/productCatalog.js`의 `jumpLabel`(목록 바로가기 표)을 재사용한다. `#product-like-btn`은 스펙 상자 안에 한 벌만 둔다(`productLike.ts`가 이 id를 찾는다).
- ko/en `[slug].astro`: `ProductSearchBar`·`handbookSearchHints` import와 sticky 검색을 뺀다. `productLike`·`contentFeedback`, 503/404, `ContentFeedback` slot, `.product-detail-page` 래퍼는 그대로.
- CSS(`global.css`): Task 2에서 줄 범위 치환 스크립트로 상세 규칙을 새 레이아웃으로 바꾼다(머리 2열 `1fr 250px`, 2px 먹선 섹션 머리, 장단점 토큰 색, 시나리오 카드 한 줄 규칙, 지면식 가격표, `.product-detail-alts`, 기능/상황 2단, ≤767px 블록의 고정 버튼 바). Task 3에서 안 쓰게 된 규칙(상세 검색, hero, chip, content, bottom CTA, 639px hero 쿼리, editor note, `.product-grid--preview`, `.product-visit-btn--large`)을 삭제 스크립트로 지운다.
- `ProductSearchBar.astro`는 목록이 계속 쓰므로 남기고 `sticky` prop·분기만 없앤다(Task 3). `ProductCard.astro`는 서재가 쓰므로 남긴다.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-10-18-product-detail-review-design]] — 구현 전에 반드시 읽는다. 시안: `.superpowers/brainstorm/products/product-detail-v1.html`(A안).

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `frontend/src/pages/admin/pipeline-runs/*`, `frontend/src/lib/pageData/publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 **읽기만 하고 수정·stage하지 않는다**.
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- **백슬래시가 있는 파일은 Write/Edit 도구로만 작성한다.** Bash heredoc을 쓰면 백슬래시가 사라진다. 해당: 테스트 파일 전부(정규식), CSS 스크립트 두 개(`'\2212'`). 새/교체 파일은 전부 Write 도구로 만든다.
- 이 계획의 코드 블록은 **목록 밖**에 있고 들여쓰기가 없다. 보이는 그대로 쓴다. Edit의 old/new는 "old:" / "new:" 아래 블록 그대로다.
- Astro/JS 파일의 문자열에는 `\uXXXX` 이스케이프를 쓰지 않는다. `·`, `←`, `↗`, 한글은 **문자 그대로** 쓴다.
- 줄바꿈·인코딩
  - `components/products/ProductDetail.astro`는 작업 트리 **CRLF**(git 인덱스 LF, `core.autocrlf=true`)다. 이번에는 **통째로 다시 쓰므로** Read 후 Write로 교체한다(LF로 저장됨). 인덱스가 LF라 줄바꿈 차이는 diff에 나오지 않는다.
  - 나머지 대상(`ProductCatalogSection.astro`, `ProductSearchBar.astro`, `pages/{ko,en}/products/[slug].astro`, `lib/pageData/productsPage.ts`, `global.css`, 테스트 파일)은 LF다. 통째 교체 파일은 Read 후 Write, 부분 수정은 Edit 도구로 한다.
  - CSS는 줄 번호가 아니라 스크립트의 "그 줄과 정확히 같은 줄" 기준으로 찾는다. 스크립트는 줄 수가 하나라도 다르면 **아무것도 쓰지 않고** 오류를 낸다 → 멈추고 보고한다.
  - 기존 파일을 Write로 통째로 바꾸기 전에 반드시 Read로 먼저 읽는다(도구 요구사항).
- dev 서버(포트 4321)를 켠 채 `npm run build`를 돌리면 EPERM/EMFILE이 날 수 있다. 실패하면 재시도하지 말고 보고한다.

**지켜야 할 것**
- 공개 HTML은 user-neutral이다(CDN 캐시). 찜 상태는 지금처럼 `productLike.ts`가 클라이언트에서 채운다. 관리자 버튼 `data-admin-only hidden={!isAdmin}` 마크업은 **한 글자도 바꾸지 않는다**.
- 스크립트는 번들 `<script>`만 쓴다(이 계획에 `is:inline` 없음). `is:inline`이 필요해지면 반드시 `nonce={Astro.locals.cspNonce || ''}`를 붙인다.
- `#product-like-btn`, `#like-label`, `#like-count`, `data-product-id`, `data-liked`는 그대로(`productLike.ts`). 버튼 줄은 마크업상 **한 벌**이다. 모바일 고정은 CSS만으로 한다(`sticky` 아님 — 원래 위치가 머리라 스크롤하면 사라진다).
- 고정 바 z-index는 50: 로그인 안내 시트 `.auth-prompt`(z-index 300)보다 낮고, 쿠키 배너(z-index 9999)가 떠 있는 동안 바를 가리는 것은 허용(스펙).
- 목록 줄 마크업·클래스·data 속성은 바뀌지 않는다(`productCatalog.ts`는 `.product-cat-list > li.product-row`만 모은다 — 상세 비슷한 도구는 그 루트 밖).
- 남기는 것: `ProductCard.astro`(서재), `.product-grid`·`.product-card*`, `.handbook-search-sticky`(용어집), `.product-filter-search`(목록), `.product-detail-page { padding-top: 1.5rem; }`, `.product-detail-features`·`.product-detail-usecases`(스펙 삭제 목록 밖), `CARD_COLUMNS`(쿼리 변경 없음).

**테스트 기준선**(2026-10-18, 계획 작성 시 실제 repo에서 측정): **PASS 83 / FAIL 19**
- 기준선 FAIL 19개와 첫 오류 메시지
  - admin-live-preview — `src/pages/admin/blog/edit/[slug].astro must sync preview state into URL history`
  - admin-v1-structure — `Missing admin sidebar settings section: …`
  - article-deck-font — `ENOENT … pages\en\log\[slug].astro`
  - auth-prompt-library-preview — `ENOENT … scripts\handbookFeedback.ts`
  - blog-sidebar-categories — `Blog categories must define the main posting group in the requested order`
  - blog-sidebar-layout — `Blog sidebar panel must use the shared card radius`
  - blog-title-fonts — `Missing IBM Plex Sans font import: IBM+Plex+Sans`
  - comments-admin-delete-contract — `Missing render delete button from API capability: c.can_delete`
  - content-feedback-contract — `ReferenceError: describe is not defined`(상세 페이지 파일을 읽지만 첫 줄에서 죽는다. 같은 메시지여야 한다)
  - csp-inline-scripts — 첫 `Error:` 줄 없음(서버 필요, `fetch failed`)
  - detail-rail-copy — `Missing KO detail rail heading: 비슷한 뉴스 더 보기`
  - handbook-detail-table-overflow — `Handbook detail tables should define a compact horizontal scrollbar size on WebKit browsers`
  - handbook-search-recognition — `Handbook search input must define theme-specific input surface colors`(**주의**: 이 테스트는 CSS 전체에 `border-radius: 12px;`가 있는지도 본다. 지금 그 문자열은 Task 3에서 지우는 옛 639px 로고 규칙에만 있다. 새 로고 규칙이 `border-radius: 12px;`를 쓰므로 메시지가 유지된다 — 바꾸지 않는다)
  - log-list-created-order — `ENOENT … pages\en\log\index.astro`
  - navigation-shell-copy — `English back copy must point to AI News`
  - news-fact-pack-structure — `layout must include sources accordion toggle`
  - product-detail-scenarios-theme — `Scenario cards should use the theme background surface instead of a hard white fill` → **Task 2에서 PASS로 바뀐다(허용된 변화)**
  - public-slug-visibility — `Slug chip must be gated by showSlug`
  - sticky-reading-actions-structure — `Missing helpful action marker: data-reading-action="helpful"`
- 상세 문자열을 읽는 기존 테스트(`grep -ln "ProductDetail\|products/\[slug\]\|product-detail\|ProductSearchBar\|ProductCatalogSection\|ProductCard\|productsPage\|product-visit\|product-like\|fetchAlternatives\|product-row\|handbookSearchHints\|handbook-search-sticky\|border-radius: 12px" frontend/tests/*`로 찾은 전부)
  - 고침: `products-catalog`(Task 1: 줄 단언 → `ProductRow.astro`, `name_original` 단언 추가 / Task 2: `DIFFICULTY_LABELS` import 문자열, `demo_media` 문구), `product-detail-search-sticky`(Task 2: 상세 페이지 단언 삭제 / Task 3: 파일 삭제), `product-detail-search-spacing`(Task 3: 파일 삭제).
  - 그대로 통과해야 함: `products-v2`(`/* --- Product Detail: Pros & Cons --- */` ~ `/* --- Product Detail: Korean Note, Resources, Verified --- */` 구간에 #16a34a·#dc2626 없음 — 두 주석을 남긴다), `product-detail-admin-actions`(관리자 마크업·스크립트 문자열 그대로 → 수정 불필요), `public-error-cache-policy`, `public-detail-query-contract`(`getProductDetailData` ~ `fetchAlternatives` 위치로 자름 — 함수 순서 유지), `public-list-query-budget`, `product-auth-prompt-copy`, `product-catalog`(mjs), `list-v2`·`handbook-term-entry`(`.handbook-search-sticky` 남음), `handbook-search-recognition`·`content-feedback-contract`(기준선과 같은 FAIL 메시지).
- 기대값: Task 1 뒤 **PASS 83 / FAIL 19**(변화 없음), Task 2 뒤 **PASS 85 / FAIL 18**(`product-detail-review` 신규 PASS, `product-detail-scenarios-theme` FAIL→PASS), Task 3 뒤 **PASS 83 / FAIL 18**(`product-detail-search-sticky`·`product-detail-search-spacing` 삭제). 실패 18개의 첫 메시지는 기준선과 같아야 한다. 다른 세션 변경으로 숫자가 흔들릴 수 있으니 판정은 **이름 + 첫 오류 메시지 기준**으로 한다.
- 기준선은 Task 1 전에 다시 잡는다(Task 4의 명령으로 결과를 파일에 저장해 둔다).

**현재 코드**
- `ProductDetail.astro`(CRLF, 506줄): `header.product-detail-hero`(로고 72px·`h1.product-detail-name`·tagline·가격/난이도 배지·`✓ 한국어` 칩·플랫폼 텍스트·사이트 방문·`#product-like-btn`) → `.product-detail-tags-row`(분야는 영문 id `assistant`를 `.product-detail-chip--category`로) → `MediaGallery`(demo_media 있을 때) → `div.product-detail-content` 안에 소개·에디터 한마디·주요 기능·이런 상황·시나리오(전부)·장단점·시작하는 법·가격 정보·한국어 메모·참고 자료 → 관련 뉴스 → 비슷한 도구(`ProductCard` 4개, `alt.name_original ?? alt.name`) → FAQ 3종 → 확인일 → `.product-detail-bottom-cta` → 관리자 버튼 → `<slot />` → 관리자 스크립트(번들). `DIFFICULTY_LABELS`는 `lib/productCatalog.js`에서 import.
- `pages/{ko,en}/products/[slug].astro`(LF, 64줄, locale만 다름): `.product-detail-page` 안에 `<ProductSearchBar locale={locale} sticky={true} />` + `ProductDetail`(slot에 `ContentFeedback`). 스크립트: `contentFeedback`·`handbookSearchHints`·`productLike`.
- `ProductCatalogSection.astro`(LF, 87줄): `ol.product-cat-list` 안에 줄 마크업 직접 렌더(`data-search-text={searchTexts[product.id] ?? ''}`, `data-overflow={index >= PREVIEW_ROWS ? '' : undefined}`).
- `fetchAlternatives`(productsPage.ts 324행~): `CARD_COLUMNS`로 같은 분야 4개, 매핑에서 `name`을 locale 이름으로 바꾸고 `name_original`은 만들지 않는다(그래서 상세가 넘기는 `alt.name_original ?? alt.name`이 locale 이름이 됨).
- `ProductSearchBar.astro`: `sticky`면 `form.product-detail-search.handbook-search-sticky`, 아니면 `form.product-filter-search`. 상세 두 페이지만 `sticky={true}`를 쓴다.
- CSS(`global.css`): `/* AI PRODUCTS */` 아래 `.product-detail-page`·`.product-detail-search*`(기본 4규칙 + 767px 쿼리 안 2규칙). `.product-grid--preview`. `/* --- Detail page (single column, visual-first) --- */`부터 `.product-detail`, hero 계열, 로고, 이름, tagline, tags row, `.product-visit-btn(--large)`, `.product-like-btn`, 카드 찜·서재 규칙(남김), `.product-detail-chip*`, `/* Content */`, `.product-detail-section`, description, `/* Alternatives & FAQ */`(테두리), `/* Bottom CTA */`, `/* Mobile */ @media (max-width: 639px)`(hero), 섹션 제목(점 장식), 기능/상황 목록, 시작 단계, 난이도 점(남김), editor note, 시나리오(카드가 여러 줄 규칙이라 `product-detail-scenarios-theme`가 실패), 장단점(`/* --- Product Detail: Pros & Cons --- */`), 한국어 메모·자료·확인일, 가격표(+639px 쿼리), 관련 뉴스, `/* --- Product Detail: Alternatives --- */`·`FAQ`(테두리 중복), FAQ 항목, `/* --- Media gallery --- */`.
- 운영 데이터(2026-10-18 anon으로 확인): 발행 123개. 시나리오는 있는 제품 모두 5개(3개 이하인 제품 없음 → 운영에서는 항상 "2개 더 보기"). 장단점이 한쪽만 있는 제품 없음. `pricing_detail_ko` 없는 제품 예: anthropic-api, incerto, flowise, the-agent-skills-directory, alphaxiv. `korean_quality_note` 있는 제품: firebase-studio, geeknews, grok, hacker-news, qanda, vibe-index. ChatGPT는 `korean_support` false(스펙 상자 "미지원"), 보조 분야 없음.

**스펙 해석·결정(실행자가 임의로 바꾸지 않는다)**
- 본문 폭: `.product-detail { max-width: 932px; padding: 0 1rem }`(border-box → 본문 900px). ≤767px는 `padding: 0 0.25rem`(+ `.main-public` 12px = 좌우 16px).
- 머리 로고는 `alt=""`(바로 옆이 `h1`), 글자 대체는 `span.product-detail-logo-fallback[aria-hidden]`. 로고 모서리는 `border-radius: 12px`(위 handbook-search-recognition 주의 참고).
- 스펙 상자 `dl`의 행은 `div > dt + dd`. 조회수는 지금처럼 주석으로만 남긴다.
- 분야·태그 줄: 주 분야와 보조 분야(주 분야와 같은 것 제외)는 `a.product-detail-tag-cat`(`--secondary`) 짧은 라벨 링크, 태그는 `span.product-detail-tag` `#태그`. `jumpLabel`에 없는 id는 id 그대로.
- 시나리오: `SCENARIOS_SHOWN = 3`. 나머지는 `details.product-detail-more > summary` + 같은 `ol.product-detail-scenarios`(`start` 4, 번호 span도 4부터). 3개 이하면 `details` 없음.
- 장단점·기능/상황: 한쪽만 있으면 `> :only-child { grid-column: 1 / -1 }`로 전체 폭. 좋은 점/아쉬운 점 색은 `--color-success`/`--color-error` 토큰(세 테마 모두 정의됨).
- 섹션 순서는 스펙대로(한국어 메모 다음에 공식 자료). 섹션 간격은 `.product-detail-section { margin-top: 2.25rem }`(옛 `.product-detail-content` 래퍼 없음).
- 섹션 머리 `h2.product-detail-section-title`: 위 2px 먹선 + Hahmlet 700 1.2rem, 옛 점 장식(`::before`) 없음. 그래서 옛 `.product-detail-alternatives`/`.product-detail-faq` 위 1px 테두리 규칙(두 군데 중복)은 Task 2에서 지운다(먹선과 겹침). 클래스 자체는 마크업에 남는다.
- 가격 섹션 제목은 스펙대로 "가격"/"Pricing"(지금 "가격 정보"). 나머지 섹션 제목은 현행 문구.
- 가격표는 컨테이너 `overflow-x: auto`(표가 넓으면 안에서만 스크롤), 셀 테두리 대신 위·아래 1px 먹선 + 행 점선. 639px 쿼리는 767px 블록으로 옮긴다.
- 비슷한 도구: `ol.product-detail-alts`(`list-style: none`, 데스크톱 2열·모바일 1열) 안에 `<ProductRow product={alt} locale={locale} />`. 상세 줄에는 `data-search-text`·`data-overflow`가 렌더되지 않는다(undefined → 생략). `data-category`·`data-secondary-categories`는 남지만 상세 스크립트가 읽지 않는다.
- `ProductDetail`의 import는 `import { DIFFICULTY_LABELS, jumpLabel } from '../../lib/productCatalog.js';` 한 줄로 합친다 → `products-catalog.test.cjs` 127행의 import 문자열 단언을 이 줄로 바꾼다(스펙은 "유지"라고 했지만 같은 모듈 두 줄 import를 피한다. 단언의 뜻 — 난이도 표는 한 곳 — 은 그대로).
- 모바일 고정 바: `.product-detail-actions { position: fixed; left: 0; right: 0; bottom: 0; z-index: 50; padding: .75rem 1rem calc(.75rem + env(safe-area-inset-bottom)); border-top; background: var(--color-bg-primary) }`, 버튼 높이 44px → 바 높이 약 69px. `body:has(.product-detail-actions) { padding-bottom: calc(4.5rem + env(safe-area-inset-bottom)) }`(72px).
- 기존 테스트 처리
  - `product-detail-search-sticky.test.cjs`: Task 2에서 상세 페이지 단언(58–75행)을 지운다(남는 단언은 `ProductSearchBar` 존재·id·힌트·action과 상세 sticky CSS — Task 2 시점엔 아직 참). Task 3에서 상세 sticky CSS를 지우므로 **파일 삭제**하고, 남아 있던 `ProductSearchBar` 단언(id·힌트·action)은 `product-detail-review.test.cjs`의 Task 3 블록으로 옮긴다.
  - `product-detail-search-spacing.test.cjs`: `.product-detail-page` 여백과 `.product-detail-search` 여백만 본다 → Task 3에서 **파일 삭제**, `.product-detail-page` 여백 단언은 `product-detail-review.test.cjs`로 옮긴다.

**계획 사전 검증(작성 시 scratchpad 복제본에서 수행)**
- `frontend/`(src, tests, public, scripts, examples, 설정 파일, `.env`; node_modules는 junction) 복제본 두 개에서 수행했다. 첫 복제본에서 작성·수정하며 dev 렌더로 확인했고, 두 번째 깨끗한 복제본에 **이 문서의 코드 블록 원본 파일 그대로**(Write 대상은 파일 복사, Edit은 "정확히 한 번 일치" 치환, CSS는 이 문서의 두 스크립트) Task 1–3을 다시 적용했다. 두 복제본의 최종 `global.css`는 바이트 단위로 같다.
- 복제본 기준선은 실제 repo와 이름·첫 오류 메시지 기준 동일(PASS 83 / FAIL 19).
- 각 "실패 확인" Step은 적힌 메시지로 실패, 통과 확인 Step은 PASS. Task 1 뒤 **PASS 83 / FAIL 19**, Task 2 뒤 **PASS 85 / FAIL 18**, Task 3 뒤 **PASS 83 / FAIL 18**. 실패 18개의 첫 오류 메시지가 기준선과 동일(`handbook-search-recognition` 포함).
- `astro build` "Complete!"(Task 1·2·3 뒤 각각). CSS 스크립트 출력은 Step에 적힌 값과 같았다.
- dev 서버(운영 데이터, 포트 4401, 확인 후 종료) + 브라우저 DOM 검사
  - `/ko/products/chatgpt/` 200(1310px): `#product-like-btn` 1개, 경로 줄 "← AI 제품군 · 어시스턴트"(`/ko/products/`, `/ko/products/?cat=assistant`), `h1` "ChatGPT", 태그 줄 "어시스턴트 #AI 어시스턴트 #멀티모달 채팅 #생산성 도구", 스펙 "가격 Freemium | 난이도 초보자 OK | 플랫폼 Web | 한국어 미지원", 머리 열 `618px 250px`, 섹션 h2 순서 "에디터 한마디 → 장단점 → 이렇게 써보세요 → 주요 기능 → 이런 상황에 추천 → 가격 → 시작하는 법 → 소개 → 관련 뉴스 → 비슷한 도구 → FAQ", 시나리오 3개 보임 + "2개 더 보기"(안의 번호 4·5), 비슷한 도구 "OpenClaw · Google Notebook LM · Anima · Bubble.io"(원래 이름, 로고 `alt=""`, `data-search-text` 없음), 검색 폼 0, 하단 CTA 0, 사이트 방문 `target=_blank rel="noopener noreferrer"`, 시나리오 카드 배경 `rgb(239, 234, 224)`(종이 테마 bg-secondary), 관리자 버튼 `hidden`, 피드백 렌더, nonce 없는 `<script>` 0.
  - `/ko/products/flowise/`(가격표 없음): "가격" 섹션 없음, 스펙 "가격 정보 없음 · 난이도 약간의 설정 필요 · 한국어 미지원"(플랫폼 행 생략), `name_ko` "플로와이즈AI" 표시, 비슷한 도구 "Incerto · Bolt.new · Langflow · Firebase Studio".
  - `/ko/products/grok/`·`/en/products/grok/`(한국어 메모 있음): "소개 → 한국어 사용 경험 → 관련 뉴스" / "About → Korean Language Experience → Related News", 스펙 "Price Not listed · Difficulty Beginner-friendly · Platforms Web · iOS · Android · API · Korean Not supported".
  - `/en/products/chatgpt/`: "← AI Products · Assistants", "Editor's take → Pros and cons → Try It Like This → Key Features → Use Cases → Pricing → Getting Started → About → Related News → Similar Tools → FAQ", "Show 2 more".
  - 375px(모바일 에뮬레이션): chatgpt·grok·flowise·en chatgpt 모두 `scrollWidth` 375(넘침 0, 가격표는 컨테이너 안 343px), 머리 1열 343px, `dl` 2×2(146.5px ×2), `h1` 30.4px, 장단점·기능/상황 1열, 좌우 16px. 버튼 바 `position: fixed`, z-index 50, 높이 69px, 위쪽 743px로 맨 위·중간·맨 끝 스크롤에서 같음. 맨 끝에서 푸터 아래끝 740px < 바 위 743px(푸터를 가리지 않음, body padding-bottom 72px). 쿠키 배너가 떠 있는 동안은 배너가 바를 가림(스펙 허용), "필수만" 뒤 바 보임. "2개 더 보기" 클릭 → 펼침, 줄 2개 보임. 비로그인 찜 클릭 → `.auth-prompt`(z-index 300) 열림.
  - 회귀 `/ko/products/`(375px): 섹션 10개, 줄 123개(보이는 줄 59, `data-overflow` 64), 첫 줄 속성 `class, data-search-text, data-category, data-secondary-categories`(목록과 동일), 검색 폼 `product-filter-search`, "chatgpt" 입력 → `?q=chatgpt`, ChatGPT·DALL-E 3, 어시스턴트 "모두 보기" → `?cat=assistant`, 28줄 + 함께 쓰이는 도구 14개, 넘침 0.

---

## Task 1: `ProductRow` 추출 + 비슷한 도구 원래 이름 (TDD)

**Files:**
- Create: `frontend/src/components/products/ProductRow.astro`
- Modify: `frontend/src/components/products/ProductCatalogSection.astro`(Write 통째), `frontend/src/lib/pageData/productsPage.ts`(Edit 1곳)
- Test: `frontend/tests/products-catalog.test.cjs`(Edit 2곳)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/components/products frontend/src/lib/pageData/productsPage.ts frontend/tests/products-catalog.test.cjs`
Expected: 출력 없음.

- [ ] **Step 1: 실패하는 단언으로 바꾸기** — `frontend/tests/products-catalog.test.cjs`를 Edit 도구로 2곳 고친다.

1번(줄 마크업 단언 → `ProductRow.astro`) old:
```js
for (const attr of ['data-search-text=', 'data-category={product.primary_category}', 'data-secondary-categories=', "data-overflow={index >= PREVIEW_ROWS ? '' : undefined}"]) {
  assert(section.includes(attr), `row attribute ${attr}`);
}
assert(section.includes('class="product-pricing-badge" data-pricing={product.pricing}') && section.includes('class="product-difficulty-badge" data-difficulty={product.difficulty}'), 'existing badge classes');
assert(section.includes('difficultyLabel(locale, product.difficulty)'), 'difficulty labels from lib/productCatalog.js');
assert(section.includes('{name}</span>') && section.includes('product.name_original ?? product.name'), 'brand name');
assert(section.includes('loading="lazy"') && section.includes('alt=""'), 'lazy decorative logo');
```
1번 new:
```js
assert(section.includes("import ProductRow from './ProductRow.astro';") && section.includes('overflow={index >= PREVIEW_ROWS}'), 'rows come from ProductRow, data-overflow after six');
assert(section.includes("searchText={searchTexts[product.id] ?? ''}"), 'list rows carry their search text');
const row = read('components/products/ProductRow.astro');
for (const attr of ['data-search-text={searchText}', 'data-category={product.primary_category}', 'data-secondary-categories=', "data-overflow={overflow ? '' : undefined}"]) {
  assert(row.includes(attr), `row attribute ${attr}`);
}
assert(row.includes('<li\n  class="product-row"'), 'row root is li.product-row');
assert(row.includes('class="product-pricing-badge" data-pricing={product.pricing}') && row.includes('class="product-difficulty-badge" data-difficulty={product.difficulty}'), 'existing badge classes');
assert(row.includes('difficultyLabel(locale, product.difficulty)'), 'difficulty labels from lib/productCatalog.js');
assert(row.includes('{name}</span>') && row.includes('product.name_original ?? product.name'), 'brand name');
assert(row.includes('loading="lazy"') && row.includes('alt=""'), 'lazy decorative logo');
```

2번(`fetchAlternatives`의 `name_original`) old:
```js
assert(data.includes('picks: ProductPick[];'), 'ProductsPageData.picks');
```
2번 new:
```js
assert(data.includes('picks: ProductPick[];'), 'ProductsPageData.picks');
const altFn = data.slice(data.indexOf('export async function fetchAlternatives'), data.indexOf('// Detail page: related news'));
assert(altFn.includes('name_original: p.name as string,'), 'similar tools keep the brand name (name_original)');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/products-catalog.test.cjs`
Expected: FAIL — `AssertionError [ERR_ASSERTION]: rows come from ProductRow, data-overflow after six`

- [ ] **Step 3: 줄 컴포넌트** — Write 도구로 `frontend/src/components/products/ProductRow.astro`를 만든다(목록 줄 마크업 그대로, `data-search-text`·`data-overflow`만 prop으로).

```astro
---
// One product row: logo, brand name, one-line description, price and difficulty.
// Shared by the catalog field sections (ProductCatalogSection) and the detail page's similar tools.
// overflow / searchText are list-only (data-overflow, data-search-text); undefined attributes are omitted.
import type { ProductCardData } from '../../lib/pageData/productsPage';
import { t } from '../../i18n/index';
import { difficultyLabel } from '../../lib/productCatalog.js';

interface Props {
  product: ProductCardData;
  locale: 'en' | 'ko';
  overflow?: boolean;
  searchText?: string;
}

const { product, locale, overflow = false, searchText } = Astro.props;
const tr = t[locale] as Record<string, string>;
const name = product.name_original ?? product.name;
const pricingLabel = (value: string) => tr[`products.${value}`] ?? value;
---

<li
  class="product-row"
  data-search-text={searchText}
  data-category={product.primary_category}
  data-secondary-categories={(product.secondary_categories ?? []).join(',')}
  data-overflow={overflow ? '' : undefined}
>
  <a href={`/${locale}/products/${product.slug}/`}>
    <span class="product-catalog-logo">
      {product.logo_url ? (
        <img src={product.logo_url} alt="" width="30" height="30" loading="lazy" />
      ) : (
        <span class="product-catalog-logo-initial" data-category={product.primary_category}>{(name ?? '?').charAt(0)}</span>
      )}
    </span>
    <span class="product-row-text">
      <span class="product-row-name">{name}</span>
      {product.tagline && <span class="product-row-tagline">{product.tagline}</span>}
      {(product.pricing || product.difficulty) && (
        <span class="product-row-meta">
          {product.pricing && (
            <span class="product-pricing-badge" data-pricing={product.pricing}>{pricingLabel(product.pricing)}</span>
          )}
          {product.difficulty && (
            <span class="product-difficulty-badge" data-difficulty={product.difficulty}>
              {difficultyLabel(locale, product.difficulty) || product.difficulty}
            </span>
          )}
        </span>
      )}
    </span>
  </a>
</li>
```

- [ ] **Step 4: 분야 섹션이 줄 컴포넌트를 쓰게** — `frontend/src/components/products/ProductCatalogSection.astro`를 Read한 뒤 Write로 통째 교체한다(줄 마크업 → `ProductRow`, 더 안 쓰는 `t`·`difficultyLabel` import와 `tr`·`pricingLabel` 제거, 나머지 그대로).

```astro
---
// One field section of the products catalog (catalogSections in lib/productCatalog.js).
// Every product of the field is rendered; rows after the sixth carry data-overflow and stay hidden
// until the section is expanded (?cat= or search). The page script only shows/hides rows.
import type { ProductCardData, ProductCategory } from '../../lib/pageData/productsPage';
import ProductRow from './ProductRow.astro';

interface Props {
  section: { category: ProductCategory; products: ProductCardData[]; lede: string; desc: string };
  locale: 'en' | 'ko';
  searchTexts: Record<string, string>;
}

const PREVIEW_ROWS = 6;

const { section, locale, searchTexts } = Astro.props;
const { category, products, lede, desc } = section;
const ko = locale === 'ko';
const label = (ko ? category.label_ko : category.label_en) || category.id;
const total = products.length;
const titleId = `cat-${category.id}-title`;
---

<section class="product-cat" id={`cat-${category.id}`} data-category={category.id} aria-labelledby={titleId}>
  <div class="product-cat-head">
    <h2 class="product-cat-title" id={titleId} tabindex="-1">
      {label}
      <span class="product-cat-count">{ko ? `${total}개` : `${total}`}</span>
    </h2>
    {total > PREVIEW_ROWS && (
      <button type="button" class="product-cat-all" data-category={category.id}>
        {ko ? `${total}개 모두 보기 →` : `See all ${total} →`}
      </button>
    )}
  </div>
  {lede && <p class="product-cat-lede">{lede}</p>}
  {desc && <p class="product-cat-desc" hidden>{desc}</p>}

  <ol class="product-cat-list">
    {products.map((product, index) => (
      <ProductRow
        product={product}
        locale={locale}
        overflow={index >= PREVIEW_ROWS}
        searchText={searchTexts[product.id] ?? ''}
      />
    ))}
  </ol>

  <div class="product-cat-also" hidden>
    <h3 class="product-cat-also-title"></h3>
    <ol class="product-cat-also-list"></ol>
  </div>
</section>
```

- [ ] **Step 5: 비슷한 도구에 원래 이름** — `frontend/src/lib/pageData/productsPage.ts`를 Edit 도구로 1곳 고친다(`fetchAlternatives` 안, 쿼리·함수 순서 그대로).

old:
```ts
  return (data as unknown as ProductCardData[]).map((p) => ({
    ...p,
    name: (locale === 'ko' ? (p as any).name_ko || p.name : p.name) as string,
```
new:
```ts
  return (data as unknown as ProductCardData[]).map((p) => ({
    ...p,
    name_original: p.name as string,
    name: (locale === 'ko' ? (p as any).name_ko || p.name : p.name) as string,
```

- [ ] **Step 6: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/products-catalog.test.cjs
node frontend/tests/product-catalog.test.mjs
node frontend/tests/products-v2.test.cjs
node frontend/tests/public-list-query-budget.test.cjs
node frontend/tests/public-detail-query-contract.test.cjs
node frontend/tests/public-error-cache-policy.test.cjs
node frontend/tests/product-detail-search-sticky.test.cjs
node frontend/tests/product-detail-admin-actions.test.cjs
cd frontend && npm run build
```
Expected: 모두 `… passed`, 빌드 "Complete!". 목록 마크업은 바뀌지 않는다(렌더 결과 동일: `li.product-row`의 속성 `class`, `data-search-text`, `data-category`, `data-secondary-categories`, 7번째부터 `data-overflow`).

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/products/ProductRow.astro frontend/src/components/products/ProductCatalogSection.astro frontend/src/lib/pageData/productsPage.ts frontend/tests/products-catalog.test.cjs
git commit -m "fix: keep brand names on similar tools and extract ProductRow"
```

---

## Task 2: 리뷰 지면 상세 (컴포넌트·페이지·CSS·테스트)

**Files:**
- Modify: `frontend/src/components/products/ProductDetail.astro`(Write 통째), `frontend/src/pages/ko/products/[slug].astro`·`frontend/src/pages/en/products/[slug].astro`(Write 통째), `frontend/src/styles/global.css`(치환 스크립트)
- Test: `frontend/tests/product-detail-review.test.cjs`(새 파일), `frontend/tests/products-catalog.test.cjs`(Edit 2곳), `frontend/tests/product-detail-search-sticky.test.cjs`(Edit 1곳)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/components/products frontend/src/pages/ko/products frontend/src/pages/en/products frontend/src/styles/global.css frontend/tests/products-catalog.test.cjs frontend/tests/product-detail-search-sticky.test.cjs frontend/tests/product-detail-review.test.cjs`
Expected: 출력 없음(Task 1 커밋 후).

- [ ] **Step 1: 실패하는 구조 테스트 작성** — Write 도구로 `frontend/tests/product-detail-review.test.cjs`를 아래 내용 그대로 만든다(Task 3에서 삭제 단언 블록을 더한다).

```js
// frontend/tests/product-detail-review.test.cjs
// Product detail as a review page (A): crumb, head + facts box, editor's take first, similar tools as catalog rows.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');
function rules(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...css.matchAll(new RegExp(`(?:^|\\n)\\s*${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
}
function rule(selector) {
  const all = rules(selector);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[0];
}

// pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/products/[slug].astro`);
  assert(!page.includes('ProductSearchBar') && !page.includes('handbookSearchHints'), `${locale}: no search bar on the detail page`);
  assert(page.includes("import ProductDetail from '../../../components/products/ProductDetail.astro';") && page.includes('<ProductDetail product={product}'), `${locale}: ProductDetail`);
  assert(page.includes("import '../../../scripts/productLike';") && page.includes("import '../../../scripts/contentFeedback';"), `${locale}: like + feedback scripts`);
  assert(page.includes('<ContentFeedback') && page.includes('isAdmin={!!Astro.locals.isAdmin}'), `${locale}: feedback slot + admin prop`);
  assert(page.includes('<div class="product-detail-page">'), `${locale}: page wrapper stays`);
  assert(/if \(error\)[\s\S]*status = 503/.test(page) && /else if \(!product\)[\s\S]*status = 404/.test(page), `${locale}: 503 / 404`);
  assert(!page.includes('is:inline'), `${locale}: bundled scripts only`);
}

// component
const detail = read('components/products/ProductDetail.astro');
assert(detail.includes('<nav class="product-detail-crumb" aria-label={copy.crumb}>'), 'crumb nav');
assert(detail.includes("crumb: '제품 위치'") && detail.includes("crumb: 'Product location'"), 'crumb labels');
assert(detail.includes("back: '← AI 제품군'") && detail.includes("back: '← AI Products'"), 'crumb back link copy');
assert(detail.includes('jumpLabel(locale, product.primary_category, product.primary_category)'), 'short field label');
assert(detail.includes('const categoryHref = (id: string) => `/${locale}/products/?cat=${id}`;'), 'field links open ?cat=');
assert(detail.includes('<header class="product-detail-head">') && detail.includes('<h1 class="product-detail-name">{product.name_original}</h1>'), 'head + brand name h1');
assert(detail.includes('<aside class="product-detail-spec" aria-label={copy.facts}>') && detail.includes('<dl class="product-detail-spec-list">'), 'facts box');
assert(detail.includes("notListed: '정보 없음'") && detail.includes("notListed: 'Not listed'"), 'price not listed');
assert(detail.includes("supported: '지원'") && detail.includes("notSupported: 'Not supported'"), 'Korean support row');
assert.equal(detail.split('id="product-like-btn"').length - 1, 1, 'exactly one like button');
for (const kept of ['id="like-label"', 'id="like-count"', 'data-product-id={product.id}', "data-liked={isLiked ? 'true' : 'false'}"]) {
  assert(detail.includes(kept), `like button keeps ${kept}`);
}
assert(detail.includes('<div class="product-detail-actions">') && detail.includes('rel="noopener noreferrer"'), 'action row with the visit link');
assert(detail.indexOf('<div class="product-detail-actions">') > detail.indexOf('<aside class="product-detail-spec"'), 'action row sits inside the facts box');
assert(!detail.includes('product-detail-chip'), 'no chip classes (tags row uses new classes)');

const order = [
  'class="product-detail-verdict"',
  'class="product-detail-pros-cons"',
  'class="product-detail-scenarios"',
  'class="product-detail-pair"',
  'class="product-detail-pricing-table',
  'class="product-detail-steps"',
  'class="product-detail-description',
  'class="product-detail-korean-note"',
  'class="product-detail-news-list"',
  'class="product-detail-alts"',
  'product-detail-faq"',
];
let at = detail.indexOf('</header>');
for (const marker of order) {
  const next = detail.indexOf(marker);
  assert(next > at, `section order: ${marker}`);
  at = next;
}

assert(detail.includes('const SCENARIOS_SHOWN = 3;') && detail.includes('<details class="product-detail-more">'), 'scenarios: three, then details');
assert(detail.includes('{scenariosMore.length > 0 && ('), 'no details with three or fewer');
assert(detail.includes('more: (n: number) => `${n}개 더 보기`') && detail.includes('more: (n: number) => `Show ${n} more`'), 'show-more copy');
assert(detail.includes('{SCENARIOS_SHOWN + i + 1}'), 'numbering continues inside details');
assert(detail.includes("verdict: '에디터 한마디'") && detail.includes(`verdict: "Editor's take"`), "editor's take label");
assert(detail.includes("pros: '좋은 점'") && detail.includes("cons: 'What to watch'"), 'pros / cons labels');
assert(detail.includes("import ProductRow from './ProductRow.astro';") && detail.includes('<ProductRow product={alt} locale={locale} />'), 'similar tools use ProductRow');
assert(!detail.includes('import ProductCard from') && !detail.includes('<ProductCard') && !detail.includes('product-detail-bottom-cta') && !detail.includes('product-visit-btn--large'), 'no cards, no bottom CTA');
assert(detail.includes('data-admin-only') && detail.includes('hidden={!isAdmin}'), 'admin actions stay hidden for the public');
assert(detail.indexOf('newsprint-admin-actions') < detail.indexOf('<slot />'), 'admin actions before the slot');
assert(!detail.includes('is:inline'), 'bundled script only');

// row component
const section = read('components/products/ProductCatalogSection.astro');
assert(section.includes('<ProductRow'), 'catalog sections use ProductRow');

// data
const data = read('lib/pageData/productsPage.ts');
const altFn = data.slice(data.indexOf('export async function fetchAlternatives'), data.indexOf('// Detail page: related news'));
assert(altFn.includes('.select(CARD_COLUMNS)') && altFn.includes('name_original: p.name as string,'), 'similar tools: same query + brand name');

// CSS
assert(/grid-template-columns:\s*minmax\(0, 1fr\) 250px/.test(rule('.product-detail-head')), 'head: 2 columns (1fr : 250px)');
assert(/border-bottom:\s*2px solid var\(--color-text-primary\)/.test(rule('.product-detail-head')), 'head ink rule');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.product-detail-section-title')), 'section heads: ink rule');
assert(/grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/.test(rule('.product-detail-pros-cons')), 'pros / cons: 2 columns');
assert(/grid-column:\s*1 \/ -1/.test(rule('.product-detail-pros-cons > :only-child')), 'one side only → full width');
assert(/list-style:\s*none/.test(rule('.product-detail-alts')), 'similar tools list reset');
const mobileAt = css.indexOf('/* Product detail: mobile */');
assert(mobileAt > 0, 'detail mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(mobile.includes('@media (max-width: 767px) {'), 'mobile at 767px');
assert(/\.product-detail-head\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: head 1 column');
const bar = mobile.match(/\.product-detail-actions\s*\{([^}]*)\}/);
assert(bar && /position:\s*fixed/.test(bar[1]) && /z-index:\s*50;/.test(bar[1]) && /bottom:\s*0/.test(bar[1]), 'mobile: action row fixed at the bottom, z-index 50');
assert(bar[1].includes('env(safe-area-inset-bottom)'), 'mobile: action row clears the home indicator');
assert(/body:has\(\.product-detail-actions\)\s*\{[^}]*padding-bottom:\s*calc\([^}]*env\(safe-area-inset-bottom\)/.test(mobile), 'mobile: page bottom padding for the bar');
assert(/\.product-detail-pros-cons,\s*\n\s*\.product-detail-pair,\s*\n\s*\.product-detail-alts\s*\{[^}]*minmax\(0, 1fr\)/.test(mobile), 'mobile: pros/cons, pair, similar tools 1 column');
const scenarioLine = css.split('\n').find((line) => line.includes('.product-detail-scenario {'));
assert(scenarioLine && scenarioLine.includes('background: var(--color-bg-secondary'), 'scenario cards on the theme surface');
const prosCons = css.slice(css.indexOf('Pros & Cons'), css.indexOf('Korean Note'));
assert(prosCons.length > 0 && prosCons.includes('var(--color-success)') && prosCons.includes('var(--color-error)'), 'pros/cons colours from tokens');

console.log('product-detail-review.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/product-detail-review.test.cjs`
Expected: FAIL — `AssertionError [ERR_ASSERTION]: ko: no search bar on the detail page`

- [ ] **Step 3: 상세 컴포넌트** — `frontend/src/components/products/ProductDetail.astro`(CRLF)를 Read한 뒤 Write로 통째 교체한다. FAQ 3종·관리자 마크업·관리자 스크립트는 현행과 글자 그대로 같다.

```astro
---
// Product detail as a review page (A): crumb → head + facts box → editor's take → pros/cons →
// scenarios (first three, the rest in "show more") → features / use cases → pricing → getting started →
// about → Korean note → resources → related news → similar tools (ProductRow) → FAQ → verified / admin / slot.
// The like button lives once, in the facts box; on phones its action row is pinned to the bottom (CSS only).
import type { ProductDetailData, ProductCardData, RelatedNewsItem } from '../../lib/pageData/productsPage';
import { t } from '../../i18n/index';
import MediaGallery from './MediaGallery.astro';
import ProductRow from './ProductRow.astro';
import { DIFFICULTY_LABELS, jumpLabel } from '../../lib/productCatalog.js';

interface Props {
  product: ProductDetailData;
  htmlDescription: string;
  htmlPricingDetail?: string;
  locale: 'en' | 'ko';
  alternatives: ProductCardData[];
  relatedNews: RelatedNewsItem[];
  isLiked?: boolean;
  isAdmin?: boolean;
}

const { product, htmlDescription, htmlPricingDetail = '', locale, alternatives, relatedNews, isLiked = false, isAdmin = false } = Astro.props;
const tr = t[locale];
const ko = locale === 'ko';

const pricingLabel: Record<string, string> = {
  free: ko ? '무료' : 'Free',
  freemium: 'Freemium',
  paid: ko ? '유료' : 'Paid',
  enterprise: ko ? '기업용' : 'Enterprise',
};

const platformLabels: Record<string, string> = {
  web: 'Web', ios: 'iOS', android: 'Android', api: 'API', desktop: 'Desktop',
};

const features = ko && product.features_ko.length > 0
  ? product.features_ko : product.features;
const useCases = ko && product.use_cases_ko.length > 0
  ? product.use_cases_ko : product.use_cases;
const gettingStarted = ko && product.getting_started_ko.length > 0
  ? product.getting_started_ko : product.getting_started;
const scenarios = ko && product.scenarios_ko?.length > 0
  ? product.scenarios_ko : (product.scenarios ?? []);
const prosCons = ko && product.pros_cons_ko
  ? product.pros_cons_ko : product.pros_cons;
const pros = prosCons?.pros ?? [];
const cons = prosCons?.cons ?? [];
const editorNote = ko ? (product.editor_note_ko || product.editor_note) : product.editor_note;
const resources = product.official_resources ?? [];
const displayTags = product.display_tags ?? product.tags ?? [];
const difficultyLabels: Record<string, { en: string; ko: string }> = DIFFICULTY_LABELS;
const platforms = (product.platform ?? []).map((p) => platformLabels[p] ?? p);
const secondaryCategories = (product.secondary_categories ?? []).filter((c) => c && c !== product.primary_category);
const categoryHref = (id: string) => `/${locale}/products/?cat=${id}`;

// Scenarios: the first three stay visible, the rest continue the numbering inside <details>.
const SCENARIOS_SHOWN = 3;
const scenariosShown = scenarios.slice(0, SCENARIOS_SHOWN);
const scenariosMore = scenarios.slice(SCENARIOS_SHOWN);

const copy = ko
  ? {
      crumb: '제품 위치',
      back: '← AI 제품군',
      facts: '제품 정보',
      price: '가격',
      difficulty: '난이도',
      platforms: '플랫폼',
      korean: '한국어',
      notListed: '정보 없음',
      supported: '지원',
      notSupported: '미지원',
      verdict: '에디터 한마디',
      prosCons: '장단점',
      pros: '좋은 점',
      cons: '아쉬운 점',
      scenarios: '이렇게 써보세요',
      more: (n: number) => `${n}개 더 보기`,
      features: '주요 기능',
      useCases: '이런 상황에 추천',
      pricing: '가격',
      gettingStarted: '시작하는 법',
      about: '소개',
      koreanNote: '한국어 사용 경험',
      resources: '참고 자료',
      news: '관련 뉴스',
      similar: '비슷한 도구',
      verified: '최종 확인일',
    }
  : {
      crumb: 'Product location',
      back: '← AI Products',
      facts: 'Product facts',
      price: 'Price',
      difficulty: 'Difficulty',
      platforms: 'Platforms',
      korean: 'Korean',
      notListed: 'Not listed',
      supported: 'Supported',
      notSupported: 'Not supported',
      verdict: "Editor's take",
      prosCons: 'Pros and cons',
      pros: 'What works',
      cons: 'What to watch',
      scenarios: 'Try It Like This',
      more: (n: number) => `Show ${n} more`,
      features: 'Key Features',
      useCases: 'Use Cases',
      pricing: 'Pricing',
      gettingStarted: 'Getting Started',
      about: 'About',
      koreanNote: 'Korean Language Experience',
      resources: 'Resources',
      news: 'Related News',
      similar: 'Similar Tools',
      verified: 'Last verified',
    };

const editHref = `/admin/products/edit/${product.slug}`;
const unpublishApi = '/api/admin/products/status';
const adminActionCopy = locale === 'ko'
  ? {
      confirm: '이 제품을 비공개로 전환할까요?',
      errorPrefix: '비공개 전환 실패',
      networkError: '비공개 전환 실패: 네트워크 오류',
    }
  : {
      confirm: 'Unpublish this product?',
      errorPrefix: 'Unpublish failed',
      networkError: 'Unpublish failed: network error',
    };
---

<article class="product-detail" id="products-top">

  <nav class="product-detail-crumb" aria-label={copy.crumb}>
    <a href={`/${locale}/products/`}>{copy.back}</a>
    {product.primary_category && (
      <>
        <span class="product-detail-crumb-sep" aria-hidden="true">·</span>
        <a href={categoryHref(product.primary_category)}>{jumpLabel(locale, product.primary_category, product.primary_category)}</a>
      </>
    )}
  </nav>

  <header class="product-detail-head">
    <div class="product-detail-head-main">
      <div class="product-detail-identity">
        {product.logo_url ? (
          <img
            src={product.logo_url}
            alt=""
            class="product-detail-logo"
            width="52"
            height="52"
            loading="eager"
          />
        ) : (
          <span class="product-detail-logo-fallback" aria-hidden="true">
            {product.name_original.charAt(0)}
          </span>
        )}
        <div class="product-detail-title">
          <h1 class="product-detail-name">{product.name_original}</h1>
          {ko && product.name_ko && product.name_ko !== product.name_original && (
            <span class="product-detail-name-ko">{product.name_ko}</span>
          )}
        </div>
      </div>

      {product.tagline && (
        <p class="product-detail-tagline">{product.tagline}</p>
      )}

      {(product.primary_category || secondaryCategories.length > 0 || displayTags.length > 0) && (
        <div class="product-detail-tags-row">
          {product.primary_category && (
            <a href={categoryHref(product.primary_category)} class="product-detail-tag-cat">
              {jumpLabel(locale, product.primary_category, product.primary_category)}
            </a>
          )}
          {secondaryCategories.map((cat) => (
            <a href={categoryHref(cat)} class="product-detail-tag-cat product-detail-tag-cat--secondary">
              {jumpLabel(locale, cat, cat)}
            </a>
          ))}
          {displayTags.map((tag) => (
            <span class="product-detail-tag">#{tag}</span>
          ))}
        </div>
      )}
    </div>

    <aside class="product-detail-spec" aria-label={copy.facts}>
      <dl class="product-detail-spec-list">
        <div>
          <dt>{copy.price}</dt>
          <dd>
            {product.pricing ? (
              <span class="product-pricing-badge" data-pricing={product.pricing}>
                {pricingLabel[product.pricing] ?? product.pricing}
              </span>
            ) : copy.notListed}
          </dd>
        </div>
        {product.difficulty && (
          <div>
            <dt>{copy.difficulty}</dt>
            <dd>
              <span class="product-difficulty-badge" data-difficulty={product.difficulty}>
                {difficultyLabels[product.difficulty]?.[locale] ?? product.difficulty}
              </span>
            </dd>
          </div>
        )}
        {platforms.length > 0 && (
          <div>
            <dt>{copy.platforms}</dt>
            <dd>{platforms.join(' · ')}</dd>
          </div>
        )}
        <div>
          <dt>{copy.korean}</dt>
          <dd>{product.korean_support ? copy.supported : copy.notSupported}</dd>
        </div>
        {/* 조회수: 트래픽 충분해지면 다시 활성화 (product.view_count) */}
      </dl>

      <div class="product-detail-actions">
        <a
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          class="product-visit-btn"
        >
          {tr['products.visitSite']} ↗
        </a>
        <button
          id="product-like-btn"
          class:list={['product-like-btn', { 'product-like-btn--active': isLiked }]}
          data-product-id={product.id}
          data-liked={isLiked ? 'true' : 'false'}
          aria-label={ko ? '찜하기' : 'Like'}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill={isLiked ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          <span id="like-label">{ko ? (isLiked ? '찜됨' : '찜하기') : (isLiked ? 'Liked' : 'Like')}</span>
          <span id="like-count">{product.like_count.toLocaleString()}</span>
        </button>
      </div>
    </aside>
  </header>

  {product.demo_media.length > 0 && (
    <MediaGallery media={product.demo_media} />
  )}

  {editorNote && (
    <section class="product-detail-verdict" aria-labelledby="product-verdict-title">
      <h2 class="product-detail-verdict-label" id="product-verdict-title">{copy.verdict}</h2>
      <blockquote class="product-detail-verdict-quote">
        <p>{editorNote}</p>
      </blockquote>
    </section>
  )}

  {(pros.length > 0 || cons.length > 0) && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">{copy.prosCons}</h2>
      <div class="product-detail-pros-cons">
        {pros.length > 0 && (
          <div class="product-detail-pros">
            <h3 class="product-detail-pros-title">{copy.pros}</h3>
            <ul>
              {pros.map((p) => <li>{p}</li>)}
            </ul>
          </div>
        )}
        {cons.length > 0 && (
          <div class="product-detail-cons">
            <h3 class="product-detail-cons-title">{copy.cons}</h3>
            <ul>
              {cons.map((c) => <li>{c}</li>)}
            </ul>
          </div>
        )}
      </div>
    </section>
  )}

  {scenarios.length > 0 && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">{copy.scenarios}</h2>
      <ol class="product-detail-scenarios">
        {scenariosShown.map((s, i) => (
          <li class="product-detail-scenario">
            <span class="product-detail-scenario-num">{i + 1}</span>
            <div>
              <strong class="product-detail-scenario-title">{s.title}</strong>
              <p class="product-detail-scenario-steps">{s.steps}</p>
            </div>
          </li>
        ))}
      </ol>
      {scenariosMore.length > 0 && (
        <details class="product-detail-more">
          <summary>{copy.more(scenariosMore.length)}</summary>
          <ol class="product-detail-scenarios" start={SCENARIOS_SHOWN + 1}>
            {scenariosMore.map((s, i) => (
              <li class="product-detail-scenario">
                <span class="product-detail-scenario-num">{SCENARIOS_SHOWN + i + 1}</span>
                <div>
                  <strong class="product-detail-scenario-title">{s.title}</strong>
                  <p class="product-detail-scenario-steps">{s.steps}</p>
                </div>
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  )}

  {(features.length > 0 || useCases.length > 0) && (
    <div class="product-detail-pair">
      {features.length > 0 && (
        <section class="product-detail-section">
          <h2 class="product-detail-section-title">{copy.features}</h2>
          <ul class="product-detail-feature-list">
            {features.map((f) => <li>{f}</li>)}
          </ul>
        </section>
      )}
      {useCases.length > 0 && (
        <section class="product-detail-section">
          <h2 class="product-detail-section-title">{copy.useCases}</h2>
          <ul class="product-detail-usecase-list">
            {useCases.map((u) => <li>{u}</li>)}
          </ul>
        </section>
      )}
    </div>
  )}

  {htmlPricingDetail && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">{copy.pricing}</h2>
      <div class="product-detail-pricing-table prose" set:html={htmlPricingDetail} />
    </section>
  )}

  {gettingStarted.length > 0 && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">{copy.gettingStarted}</h2>
      <ol class="product-detail-steps">
        {gettingStarted.map((step, i) => (
          <li>
            <span class="product-detail-step-num">{i + 1}</span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </section>
  )}

  {htmlDescription && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">{copy.about}</h2>
      <div class="product-detail-description prose">
        <Fragment set:html={htmlDescription} />
      </div>
    </section>
  )}

  {product.korean_quality_note && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">{copy.koreanNote}</h2>
      <p class="product-detail-korean-note">{product.korean_quality_note}</p>
    </section>
  )}

  {resources.length > 0 && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">{copy.resources}</h2>
      <ul class="product-detail-resources">
        {resources.map((r) => (
          <li>
            <a href={r.url} target="_blank" rel="noopener noreferrer">{r.label} ↗</a>
          </li>
        ))}
      </ul>
    </section>
  )}

  {relatedNews.length > 0 && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">{copy.news}</h2>
      <ul class="product-detail-news-list">
        {relatedNews.map((news) => (
          <li>
            <a href={`/${locale}/news/${news.slug}/`}>{news.title}</a>
          </li>
        ))}
      </ul>
    </section>
  )}

  {alternatives.length > 0 && (
    <section class="product-detail-section product-detail-alternatives">
      <h2 class="product-detail-section-title">{copy.similar}</h2>
      <ol class="product-detail-alts">
        {alternatives.map((alt) => (
          <ProductRow product={alt} locale={locale} />
        ))}
      </ol>
    </section>
  )}

  <section class="product-detail-section product-detail-faq">
    <h2 class="product-detail-section-title">FAQ</h2>

    {product.pricing && (
      <details class="product-faq-item">
        <summary>
          {locale === 'ko'
            ? `${product.name_original}은(는) 무료인가요?`
            : `Is ${product.name_original} free?`}
        </summary>
        <p>
          {product.pricing === 'free'
            ? (locale === 'ko' ? '네, 무료로 사용할 수 있습니다.' : 'Yes, it is completely free to use.')
            : product.pricing === 'freemium'
              ? (locale === 'ko' ? '무료 플랜과 유료 플랜이 있습니다.' : 'It offers both free and paid plans.')
              : product.pricing === 'paid'
                ? (locale === 'ko' ? '유료 서비스입니다.' : 'It is a paid service.')
                : (locale === 'ko' ? '기업용 요금제입니다.' : 'Enterprise pricing. Contact sales.')}
          {product.pricing_note && ` ${product.pricing_note}`}
        </p>
      </details>
    )}

    {product.platform && product.platform.length > 0 && (
      <details class="product-faq-item">
        <summary>
          {locale === 'ko'
            ? `어떤 플랫폼에서 사용할 수 있나요?`
            : `What platforms is ${product.name_original} available on?`}
        </summary>
        <p>
          {locale === 'ko'
            ? `${product.platform.map(p => platformLabels[p] ?? p).join(', ')}에서 사용 가능합니다.`
            : `Available on ${product.platform.map(p => platformLabels[p] ?? p).join(', ')}.`}
        </p>
      </details>
    )}

    <details class="product-faq-item">
      <summary>
        {locale === 'ko'
          ? `한국어를 지원하나요?`
          : `Does ${product.name_original} support Korean?`}
      </summary>
      <p>
        {product.korean_support
          ? (locale === 'ko' ? '네, 한국어 UI를 지원합니다.' : 'Yes, it supports Korean language.')
          : (locale === 'ko' ? '현재 한국어는 지원하지 않습니다.' : 'Korean is not currently supported.')}
      </p>
    </details>
  </section>

  {product.verified_at && (
    <p class="product-detail-verified">
      {copy.verified}: {product.verified_at}
    </p>
  )}

  <div
    data-admin-only
    hidden={!isAdmin}
    class="newsprint-admin-actions"
    data-toolbar-id={product.id}
    data-toolbar-api={unpublishApi}
    data-confirm-message={adminActionCopy.confirm}
    data-error-prefix={adminActionCopy.errorPrefix}
    data-error-network={adminActionCopy.networkError}
  >
    <a href={editHref} class="newsprint-admin-action-btn">Edit</a>
    <button type="button" class="newsprint-admin-action-btn newsprint-admin-action-btn--unpublish">Unpublish</button>
  </div>

  <slot />
</article>

<script>
  function initProductAdminActions(): void {
    const actions = document.querySelector<HTMLElement>('.newsprint-admin-actions');
    if (!actions || actions.dataset.bound === 'true') return;

    const btn = actions.querySelector<HTMLButtonElement>('.newsprint-admin-action-btn--unpublish');
    if (!btn) return;

    actions.dataset.bound = 'true';

    btn.addEventListener('click', async () => {
      const confirmMessage = actions.dataset.confirmMessage || 'Unpublish this product?';
      if (!confirm(confirmMessage)) return;

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
          window.location.href = editLink?.href || '/admin/products';
        } else {
          const err = await res.json().catch(() => ({ error: 'Unknown error' }));
          const errorPrefix = actions.dataset.errorPrefix || 'Unpublish failed';
          alert(`${errorPrefix}: ${err.error || err.detail || 'Unknown error'}`);
        }
      } catch {
        alert(actions.dataset.errorNetwork || 'Unpublish failed: network error');
      }
    });
  }

  document.addEventListener('astro:page-load', initProductAdminActions);
  initProductAdminActions();
</script>
```

- [ ] **Step 4: KO 상세 페이지** — `frontend/src/pages/ko/products/[slug].astro`를 Read한 뒤 Write로 통째 교체한다(`ProductSearchBar` import·사용, `handbookSearchHints` import 삭제. 나머지 그대로).

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { getProductDetailData, fetchAlternatives, fetchRelatedNews } from '../../../lib/pageData/productsPage';
import ProductDetail from '../../../components/products/ProductDetail.astro';
import ContentFeedback from '../../../components/common/ContentFeedback.astro';

const locale = 'ko';
const { slug } = Astro.params;
const { product, htmlDescription, htmlPricingDetail, error } = await getProductDetailData(slug ?? '', locale);
const [alternatives, relatedNews] = product
  ? await Promise.all([
      fetchAlternatives(product.primary_category, slug ?? '', locale),
      fetchRelatedNews(product.name, product.url, locale),
    ])
  : [[], []];

if (error) {
  Astro.response.status = 503;
} else if (!product) {
  Astro.response.status = 404;
}

// Like state is hydrated client-side (productLike.ts) so this page stays CDN-cacheable.
---

<MainLayout
  title={product?.name ?? t.ko['products.notfound']}
  description={product?.tagline ?? undefined}
  locale={locale}
  slug={product ? `products/${product.slug}/` : ''}
  altSlug={product?.slug}
>
  {product ? (
    <div class="product-detail-page">
      <ProductDetail product={product} htmlDescription={htmlDescription} htmlPricingDetail={htmlPricingDetail} locale={locale} alternatives={alternatives} relatedNews={relatedNews} isAdmin={!!Astro.locals.isAdmin}>
        <ContentFeedback
          sourceType="product"
          sourceId={product.id}
          locale={locale}
          isAuthenticated={false}
          loginUrl={`/api/auth/login?redirect=${encodeURIComponent(Astro.url.pathname)}`}
        />
      </ProductDetail>
    </div>
  ) : (
    <div class="products-page">
      <p class="products-not-found">
        {error ?? t.ko['products.notfound']}
      </p>
      <a href="/ko/products/" class="products-back-link">← {t.ko['products.back']}</a>
    </div>
  )}
</MainLayout>

<script>
  import '../../../scripts/contentFeedback';
  import '../../../scripts/productLike';
</script>
```

- [ ] **Step 5: EN 상세 페이지** — `frontend/src/pages/en/products/[slug].astro`를 Read한 뒤 Write로 통째 교체한다.

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { getProductDetailData, fetchAlternatives, fetchRelatedNews } from '../../../lib/pageData/productsPage';
import ProductDetail from '../../../components/products/ProductDetail.astro';
import ContentFeedback from '../../../components/common/ContentFeedback.astro';

const locale = 'en';
const { slug } = Astro.params;
const { product, htmlDescription, htmlPricingDetail, error } = await getProductDetailData(slug ?? '', locale);
const [alternatives, relatedNews] = product
  ? await Promise.all([
      fetchAlternatives(product.primary_category, slug ?? '', locale),
      fetchRelatedNews(product.name, product.url, locale),
    ])
  : [[], []];

if (error) {
  Astro.response.status = 503;
} else if (!product) {
  Astro.response.status = 404;
}

// Like state is hydrated client-side (productLike.ts) so this page stays CDN-cacheable.
---

<MainLayout
  title={product?.name ?? t.en['products.notfound']}
  description={product?.tagline ?? undefined}
  locale={locale}
  slug={product ? `products/${product.slug}/` : ''}
  altSlug={product?.slug}
>
  {product ? (
    <div class="product-detail-page">
      <ProductDetail product={product} htmlDescription={htmlDescription} htmlPricingDetail={htmlPricingDetail} locale={locale} alternatives={alternatives} relatedNews={relatedNews} isAdmin={!!Astro.locals.isAdmin}>
        <ContentFeedback
          sourceType="product"
          sourceId={product.id}
          locale={locale}
          isAuthenticated={false}
          loginUrl={`/api/auth/login?redirect=${encodeURIComponent(Astro.url.pathname)}`}
        />
      </ProductDetail>
    </div>
  ) : (
    <div class="products-page">
      <p class="products-not-found">
        {error ?? t.en['products.notfound']}
      </p>
      <a href="/en/products/" class="products-back-link">← {t.en['products.back']}</a>
    </div>
  )}
</MainLayout>

<script>
  import '../../../scripts/contentFeedback';
  import '../../../scripts/productLike';
</script>
```

- [ ] **Step 6: CSS 치환**

1. Write 도구로 scratchpad에 `restyle-product-detail.cjs`를 아래 내용 그대로 만든다(repo 밖, 커밋하지 않음).

```js
// Restyles the product detail page (A: review page) in frontend/src/styles/global.css.
// Each step replaces lines [start, end): start = the only line equal to `from`, end = first line equal to `to` after it.
// The line count must match `expected`, otherwise nothing is written. Run from the repo root.
const fs = require('fs');

const file = 'frontend/src/styles/global.css';
const lines = fs.readFileSync(file, 'utf8').split('\n');

function replace(name, from, to, expected, text) {
  const start = lines.indexOf(from);
  if (start < 0) throw new Error(`${name}: start not found: ${from}`);
  if (lines.indexOf(from, start + 1) >= 0) throw new Error(`${name}: start is not unique: ${from}`);
  const end = lines.indexOf(to, start + (expected === 0 ? 0 : 1));
  if (end < 0) throw new Error(`${name}: end not found: ${to}`);
  if (end - start !== expected) {
    throw new Error(`${name}: expected ${expected} lines, found ${end - start} (lines ${start + 1}-${end})`);
  }
  const added = text === '' ? [] : text.replace(/^\n/, '').split('\n');
  lines.splice(start, end - start, ...added);
  console.log(`${name}: replaced ${expected} lines at line ${start + 1} with ${added.length}`);
}

// 1. page column: one column, 900px of content
replace('page column', '/* --- Detail page (single column, visual-first) --- */', '/* Hero — 2컬럼 C-1: left(flex:3) name+tagline+CTA, right(flex:1) logo+meta */', 13, String.raw`
/* --- Detail page (A: review page, one column) --- */
.product-detail {
  max-width: 932px;
  margin: 0 auto;
  padding: 0 1rem 2.5rem;
}
`);

// 2. logo 52px (radius 12px: also the last "border-radius: 12px;" handbook-search-recognition looks for once the old 639px rules go)
replace('logo', '.product-detail-logo {', '.product-detail-hero-text {', 24, String.raw`
.product-detail-logo,
.product-detail-logo-fallback {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 12px;
}

.product-detail-logo {
  object-fit: contain;
  background: #fff;
  padding: 4px;
}

.product-detail-logo-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-secondary);
  font-family: var(--font-heading);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--color-text-secondary);
}
`);

// 3. name / Korean name / tagline
replace('name + tagline', '.product-detail-name {', '.product-detail-hero-meta {', 23, String.raw`
.product-detail-name {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.035em;
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
}

.product-detail-name-ko {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.product-detail-tagline {
  margin: 0.85rem 0 0;
  font-size: 1.05rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}
`);

// 4. crumb, head grid, tags row, facts box, action row, editor's take
replace('head + facts box', '/* Tags row — category + tags, Hero 바로 아래 */', '.product-visit-btn {', 9, String.raw`
/* Crumb, head (identity + facts box), tags row, editor's take */
.product-detail-crumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 1rem;
  font-family: var(--font-ui);
  font-size: 0.82rem;
}

.product-detail-crumb a {
  color: var(--color-text-secondary);
  text-decoration: none;
}

.product-detail-crumb a:hover {
  color: var(--color-accent);
}

.product-detail-crumb-sep {
  color: var(--color-text-muted);
}

.product-detail-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 250px;
  gap: 2rem;
  align-items: start;
  padding-bottom: 1.5rem;
  border-bottom: 2px solid var(--color-text-primary);
}

.product-detail-identity {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  min-width: 0;
}

.product-detail-title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.2rem 0.6rem;
  min-width: 0;
}

.product-detail-tags-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.75rem;
  margin-top: 0.9rem;
  font-family: var(--font-ui);
  font-size: 0.8rem;
}

.product-detail-tag-cat {
  font-weight: 600;
  color: var(--color-text-secondary);
  text-decoration: none;
}

.product-detail-tag-cat--secondary {
  font-weight: 500;
  color: var(--color-text-muted);
}

.product-detail-tag-cat:hover {
  color: var(--color-accent);
}

.product-detail-tag {
  color: var(--color-text-muted);
}

.product-detail-spec {
  padding: 0.9rem 1rem 1rem;
  border: 1px solid var(--color-border);
}

.product-detail-spec-list {
  display: grid;
  gap: 0.55rem;
  margin: 0;
}

.product-detail-spec-list > div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  padding-bottom: 0.55rem;
  border-bottom: 1px dotted var(--color-border);
}

.product-detail-spec-list dt {
  font-family: var(--font-ui);
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.product-detail-spec-list dd {
  margin: 0;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 600;
  text-align: right;
  color: var(--color-text-primary);
}

.product-detail-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.9rem;
}

.product-detail-actions .product-visit-btn {
  flex: 1;
  justify-content: center;
}

.product-detail-verdict {
  margin-top: 2rem;
}

.product-detail-verdict-label {
  margin: 0 0 0.6rem;
  font-family: var(--font-ui);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--color-accent);
}

.product-detail-verdict-quote {
  margin: 0;
  padding: 0;
  border: 0;
}

.product-detail-verdict-quote p {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 1.2rem;
  font-weight: 600;
  line-height: 1.65;
  letter-spacing: -0.02em;
  color: var(--color-text-primary);
}
`);

// 5. section spacing (sections no longer sit inside .product-detail-content)
replace('section spacing', '.product-detail-section {', '.product-detail-description {', 4, String.raw`
.product-detail-section {
  margin-top: 2.25rem;
}
`);

// 6. old "Alternatives & FAQ" borders (the section heads carry the rule now)
replace('old alternatives/faq borders', '/* Alternatives & FAQ */', '/* Bottom CTA */', 11, '');

// 7. section head: 2px ink rule + Hahmlet, no dot
replace('section title', '/* --- Product Detail: Features & Use Cases --- */', '.product-detail-features,', 22, String.raw`
/* --- Product Detail: section heads, Features & Use Cases --- */
.product-detail-section-title {
  margin: 0 0 1rem;
  padding-top: 0.6rem;
  border-top: 2px solid var(--color-text-primary);
  font-family: var(--font-heading);
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--color-text-primary);
}
`);

// 8. scenario card (one line: product-detail-scenarios-theme reads the selector line) + Newsreader numbers
replace('scenario card', '.product-detail-scenario {', '.product-detail-scenario-title {', 22, String.raw`
.product-detail-scenario { display: grid; grid-template-columns: 1.5rem minmax(0, 1fr); gap: 0.75rem; padding: 0.85rem 1rem; border-radius: var(--radius-sm); background: var(--color-bg-secondary); }

.product-detail-scenario-num,
.product-detail-step-num {
  min-width: 1.5rem;
  font-family: var(--font-masthead);
  font-size: 1.15rem;
  font-weight: 600;
  font-variant-numeric: lining-nums;
  line-height: 1.3;
  color: var(--color-accent);
  flex-shrink: 0;
}
`);

// 9. "show more" scenarios + pros/cons (good/bad tokens, never #16a34a / #dc2626)
replace('more + pros/cons', '/* --- Product Detail: Pros & Cons --- */', '/* --- Product Detail: Korean Note, Resources, Verified --- */', 57, String.raw`
.product-detail-more {
  margin-top: 0.5rem;
}

.product-detail-more > summary {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 44px;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-accent);
  cursor: pointer;
  list-style: none;
}

.product-detail-more > summary::-webkit-details-marker {
  display: none;
}

.product-detail-more > summary::after {
  content: '+';
  font-weight: 400;
}

.product-detail-more[open] > summary::after {
  content: '\2212';
}

.product-detail-more > .product-detail-scenarios {
  margin-top: 0.25rem;
}

/* --- Product Detail: Pros & Cons --- */
.product-detail-pros-cons {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 2rem;
}

.product-detail-pros-cons > :only-child {
  grid-column: 1 / -1;
}

.product-detail-pros-title,
.product-detail-cons-title {
  margin: 0 0 0.35rem;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 700;
}

.product-detail-pros-title {
  color: var(--color-success);
}

.product-detail-cons-title {
  color: var(--color-error);
}

.product-detail-pros ul,
.product-detail-cons ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
}

.product-detail-pros li,
.product-detail-cons li {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-bottom: 1px dotted var(--color-border);
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.product-detail-pros li::before,
.product-detail-cons li::before {
  flex-shrink: 0;
  width: 0.8rem;
  font-weight: 700;
}

.product-detail-pros li::before {
  content: '+';
  color: var(--color-success);
}

.product-detail-cons li::before {
  content: '\2212';
  color: var(--color-error);
}
`);

// 10. pricing table as a print table (ink rules, no boxed cells); the 639px query goes (767px block below)
replace('pricing table', '/* --- Product Detail: Pricing Table --- */', '/* --- Product Detail: Related News --- */', 43, String.raw`
/* --- Product Detail: Pricing Table --- */
.product-detail-pricing-table {
  overflow-x: auto;
  font-size: 0.88rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.product-detail-pricing-table table {
  width: 100%;
  margin: 0.25rem 0;
  border-collapse: collapse;
  border-top: 1px solid var(--color-text-primary);
  border-bottom: 1px solid var(--color-text-primary);
}

.product-detail-pricing-table th,
.product-detail-pricing-table td {
  padding: 0.55rem 0.75rem 0.55rem 0;
  border: 0;
  border-bottom: 1px dotted var(--color-border);
  text-align: left;
  vertical-align: top;
}

.product-detail-pricing-table th {
  font-family: var(--font-ui);
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-text-primary);
}
`);

// 11. similar tools list (ProductRow) instead of the old alternatives / FAQ borders
replace('similar tools', '/* --- Product Detail: Alternatives --- */', '.product-faq-item {', 14, String.raw`
/* --- Product Detail: Similar tools (ProductRow) --- */
.product-detail-alts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 1.6rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
`);

// 12. features / use cases pair + phone layout (fixed action row), before the media gallery block
replace('pair + mobile', '/* --- Media gallery --- */', '/* --- Media gallery --- */', 0, String.raw`
/* --- Product Detail: features / use cases side by side --- */
.product-detail-pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 2rem;
}

.product-detail-pair > :only-child {
  grid-column: 1 / -1;
}

/* Product detail: mobile */
@media (max-width: 767px) {
  .product-detail {
    padding: 0 0.25rem 2rem;
  }

  .product-detail-head {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.25rem;
  }

  .product-detail-name {
    font-size: 1.9rem;
  }

  .product-detail-spec-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.6rem 1rem;
  }

  .product-detail-spec-list > div {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.15rem;
  }

  .product-detail-spec-list dd {
    text-align: left;
  }

  .product-detail-actions {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 50;
    margin: 0;
    padding: 0.75rem 1rem calc(0.75rem + env(safe-area-inset-bottom));
    border-top: 1px solid var(--color-border);
    background: var(--color-bg-primary);
  }

  .product-detail-actions .product-visit-btn,
  .product-detail-actions .product-like-btn {
    min-height: 44px;
  }

  body:has(.product-detail-actions) {
    padding-bottom: calc(4.5rem + env(safe-area-inset-bottom));
  }

  .product-detail-pros-cons,
  .product-detail-pair,
  .product-detail-alts {
    grid-template-columns: minmax(0, 1fr);
  }

  .product-detail-verdict-quote p {
    font-size: 1.1rem;
  }

  .product-detail-pricing-table th,
  .product-detail-pricing-table td {
    padding: 0.45rem 0.5rem 0.45rem 0;
    font-size: 0.82rem;
  }
}
`);

fs.writeFileSync(file, lines.join('\n'));
console.log('done');
```

2. repo 루트에서 `node <scratchpad>/restyle-product-detail.cjs` → 아래 출력(시작 줄 번호는 다른 세션 변경으로 달라질 수 있다. **줄 수**가 하나라도 다르면 스크립트가 아무것도 쓰지 않고 오류를 낸다 → 멈추고 보고):
```
page column: replaced 13 lines at line 13444 with 7
logo: replaced 24 lines at line 13465 with 25
name + tagline: replaced 23 lines at line 13497 with 23
head + facts box: replaced 9 lines at line 13550 with 152
section spacing: replaced 4 lines at line 13901 with 4
old alternatives/faq borders: replaced 11 lines at line 13922 with 0
section title: replaced 22 lines at line 13976 with 12
scenario card: replaced 22 lines at line 14080 with 14
more + pros/cons: replaced 57 lines at line 14108 with 98
pricing table: replaced 43 lines at line 14239 with 33
similar tools: replaced 14 lines at line 14298 with 10
pair + mobile: replaced 0 lines at line 14346 with 79
done
```

- 바뀌는 것: `.product-detail`(900px 한 단), 로고 52px, 이름 2.5rem·tagline, 경로 줄·머리 2열·태그 줄·스펙 상자·버튼 줄·에디터 한마디(새 규칙, 옛 tags row 자리), `.product-detail-section` 간격, 옛 `/* Alternatives & FAQ */` 테두리 삭제, 섹션 머리(먹선, 점 없음), 시나리오 카드 한 줄 규칙 + Newsreader 번호, 더 보기 + 장단점(토큰 색, 두 주석 유지), 가격표, 옛 `/* --- Product Detail: Alternatives --- */`·`FAQ` 테두리 → `.product-detail-alts`, `/* --- Media gallery --- */` 앞에 기능/상황 2단 + `/* Product detail: mobile */` 767px 블록.
- 남는 것(Task 3에서 지움): `.product-detail-search*`, `.product-grid--preview`, hero 계열, `.product-visit-btn--large`, `.product-detail-chip*`, `/* Content */`, `/* Bottom CTA */`, `/* Mobile */` 639px hero 쿼리, editor note. 새 규칙이 뒤에 오거나 같은 셀렉터를 바꿨으므로 화면에는 영향이 없다(639px 쿼리의 로고 48px만 Task 3 전까지 남는다).

Run:
```bash
grep -n "^\.product-detail-scenario {" frontend/src/styles/global.css
grep -n "^/\* --- Product Detail: Pros & Cons --- \*/\|^/\* --- Product Detail: Korean Note, Resources, Verified --- \*/\|^/\* Product detail: mobile \*/" frontend/src/styles/global.css
```
Expected: 첫 줄 1줄(`background: var(--color-bg-secondary);`가 같은 줄에 있음). 둘째 줄 3줄(장단점 주석 → 한국어 메모 주석 → 모바일 주석 순).

- [ ] **Step 7: 기존 테스트 갱신** (Edit 도구로)

`frontend/tests/products-catalog.test.cjs` 1번 old:
```js
assert(detail.includes("import { DIFFICULTY_LABELS } from '../../lib/productCatalog.js';"), 'ProductDetail imports DIFFICULTY_LABELS');
```
1번 new:
```js
assert(detail.includes("import { DIFFICULTY_LABELS, jumpLabel } from '../../lib/productCatalog.js';"), 'ProductDetail imports DIFFICULTY_LABELS (and the short field labels)');
```

`frontend/tests/products-catalog.test.cjs` 2번 old:
```js
assert(/demo_media/.test(cardColumns), 'demo_media stays (detail alternatives)');
```
2번 new:
```js
assert(/demo_media/.test(cardColumns), 'demo_media stays (card query unchanged)');
```

`frontend/tests/product-detail-search-sticky.test.cjs` old(상세 페이지 단언 삭제):
```js
[
  'src/pages/en/products/[slug].astro',
  'src/pages/ko/products/[slug].astro',
].forEach((file) => {
  const source = read(file);
  assert(
    source.includes("import ProductSearchBar from '../../../components/products/ProductSearchBar.astro';"),
    `${file} should import the shared product search component`,
  );
  assert(
    source.includes('sticky={true}'),
    `${file} should render the search bar in sticky detail mode`,
  );
  assert(
    source.includes("import '../../../scripts/handbookSearchHints';"),
    `${file} should initialize the rotating product search hints on detail pages`,
  );
});

const globalCss = read('src/styles/global.css');
```
new:
```js
const globalCss = read('src/styles/global.css');
```

`product-detail-admin-actions.test.cjs`는 고치지 않는다(관리자 마크업·스크립트 문자열과 "slot 앞" 순서가 그대로라 통과).

- [ ] **Step 8: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/product-detail-review.test.cjs
node frontend/tests/products-catalog.test.cjs
node frontend/tests/product-catalog.test.mjs
node frontend/tests/products-v2.test.cjs
node frontend/tests/product-detail-scenarios-theme.test.cjs
node frontend/tests/product-detail-search-sticky.test.cjs
node frontend/tests/product-detail-search-spacing.test.cjs
node frontend/tests/product-detail-admin-actions.test.cjs
node frontend/tests/product-auth-prompt-copy.test.cjs
node frontend/tests/public-error-cache-policy.test.cjs
node frontend/tests/public-detail-query-contract.test.cjs
node frontend/tests/public-list-query-budget.test.cjs
node frontend/tests/handbook-search-recognition.test.cjs
node frontend/tests/content-feedback-contract.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 두 테스트를 뺀 모두 `… passed`(`product-detail-scenarios-theme`는 이번에 통과로 바뀐다). 빌드 "Complete!".
- `handbook-search-recognition` FAIL `Handbook search input must define theme-specific input surface colors`, `content-feedback-contract` FAIL `ReferenceError: describe is not defined` — 기준선과 **같은 메시지**.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/components/products/ProductDetail.astro 'frontend/src/pages/ko/products/[slug].astro' 'frontend/src/pages/en/products/[slug].astro' frontend/src/styles/global.css frontend/tests/product-detail-review.test.cjs frontend/tests/products-catalog.test.cjs frontend/tests/product-detail-search-sticky.test.cjs
git commit -m "feat: product detail as a review page"
```

---

## Task 3: 상세 검색·hero·chip 등 안 쓰는 상세 CSS와 테스트 정리 (TDD)

**Files:**
- Modify: `frontend/src/components/products/ProductSearchBar.astro`(Write 통째), `frontend/src/styles/global.css`(삭제 스크립트)
- Delete: `frontend/tests/product-detail-search-sticky.test.cjs`, `frontend/tests/product-detail-search-spacing.test.cjs`
- Test: `frontend/tests/product-detail-review.test.cjs`(Edit 1곳: 삭제 단언)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/components/products/ProductSearchBar.astro frontend/src/styles/global.css frontend/tests/product-detail-review.test.cjs frontend/tests/product-detail-search-sticky.test.cjs frontend/tests/product-detail-search-spacing.test.cjs`
Expected: 출력 없음(Task 2 커밋 후).

- [ ] **Step 1: 실패하는 단언 추가** — `frontend/tests/product-detail-review.test.cjs`의 마지막 줄 앞에 Edit 도구로 블록을 넣는다(블록 끝과 `console.log` 사이 빈 줄 한 줄).

old:
```js
console.log('product-detail-review.test.cjs passed');
```
new:
```js
// removed pieces (Task 3)
const searchBar = read('components/products/ProductSearchBar.astro');
assert(!searchBar.includes('sticky') && searchBar.includes('class="product-filter-search"'), 'ProductSearchBar: no sticky detail mode');
assert(searchBar.includes('id="product-search"') && searchBar.includes('data-placeholder-hints') && searchBar.includes('action={`/${locale}/products/`}'), 'ProductSearchBar keeps the list search (id, hints, action)');
for (const gone of ['.product-detail-search', '.product-grid--preview', '.product-detail-chip', '.product-detail-hero', '.product-detail-content', '.product-detail-editor-note', '.product-detail-bottom-cta', '.product-visit-btn--large']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(!/@media \(max-width: 639px\) \{\s*\n\s*\.product-detail/.test(css), 'no 639px product detail query (767px only)');
assert(/padding-top:\s*1\.5rem/.test(rule('.product-detail-page')), 'page wrapper spacing stays');
assert(css.includes('.handbook-search-sticky {') && css.includes('.product-filter-search {') && css.includes('.product-card {'), 'shared styles stay');
for (const gone of ['product-detail-search-sticky.test.cjs', 'product-detail-search-spacing.test.cjs']) {
  assert(!fs.existsSync(path.join(__dirname, gone)), `deleted: tests/${gone}`);
}

console.log('product-detail-review.test.cjs passed');

console.log('product-detail-review.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/product-detail-review.test.cjs`
Expected: FAIL — `AssertionError [ERR_ASSERTION]: ProductSearchBar: no sticky detail mode`

- [ ] **Step 3: 사용처가 없음을 확인**

Run:
```bash
grep -rn "product-detail-search\|product-grid--preview\|product-detail-chip\|product-detail-hero\|product-detail-content\|product-detail-editor-note\|product-detail-bottom-cta\|product-visit-btn--large" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rn "sticky" frontend/src/components/products frontend/src/pages/ko/products frontend/src/pages/en/products
grep -rln "product-detail-search\|product-grid--preview\|product-detail-chip\|product-detail-hero\|product-detail-content\|product-detail-editor-note\|product-detail-bottom-cta\|product-visit-btn--large" frontend/tests
```
Expected:
- 첫 줄: `ProductSearchBar.astro:19`의 `sticky ? 'product-detail-search handbook-search-sticky' : 'product-filter-search',` 한 줄뿐(`ProductDetail`·페이지·다른 컴포넌트 결과 없음).
- 둘째 줄: `ProductSearchBar.astro`의 6행(`sticky?: boolean;`)·9행(`const { locale, sticky = false } = Astro.props;`)·19행뿐(상세 페이지에 `sticky={true}` 없음).
- 셋째 줄: `product-detail-review.test.cjs`(부재 단언), `product-detail-search-spacing.test.cjs`, `product-detail-search-sticky.test.cjs`뿐.
- 하나라도 다르면 멈추고 보고한다.

- [ ] **Step 4: 검색 바의 sticky 모드 제거** — `frontend/src/components/products/ProductSearchBar.astro`를 Read한 뒤 Write로 통째 교체한다(`sticky` prop과 분기만 제거, 폼 id·힌트·action·submit 핸들러 그대로).

```astro
---
import { t } from '../../i18n/index';

interface Props {
  locale: 'en' | 'ko';
}

const { locale } = Astro.props;
const tr = t[locale];

const placeholderHints = locale === 'ko'
  ? ['ChatGPT, Claude, Gemini...', '이미지 생성 도구는?', '무료로 쓸 수 있는 AI는?', '코딩 도구 찾기', '영상 만드는 AI는?', '한국어 지원 AI 도구']
  : ['ChatGPT, Claude, Gemini...', 'Image generation tools', 'Free AI tools', 'Find coding assistants', 'Video creation AI', 'Korean language support'];
---

<form
  class="product-filter-search"
  action={`/${locale}/products/`}
  method="get"
  data-product-search-form
>
  <input
    type="search"
    id="product-search"
    name="q"
    class="handbook-search-input"
    placeholder={tr['products.searchPlaceholder']}
    aria-label={tr['products.searchPlaceholder']}
    autocomplete="off"
    data-placeholder-hints={JSON.stringify(placeholderHints)}
  />
</form>

<script>
  document.addEventListener('astro:page-load', () => {
    document.querySelectorAll<HTMLFormElement>('[data-product-search-form]').forEach((form) => {
      if (form.dataset.productSearchBound === 'true') return;
      form.dataset.productSearchBound = 'true';

      form.addEventListener('submit', (event) => {
        const input = form.querySelector<HTMLInputElement>('input[name="q"]');
        if (!input) return;

        const trimmed = input.value.trim();
        if (trimmed) {
          input.value = trimmed;
          return;
        }

        event.preventDefault();
        window.location.href = form.action;
      });
    });
  });
</script>
```

- [ ] **Step 5: 안 쓰는 상세 CSS 삭제**

1. Write 도구로 scratchpad에 `drop-product-detail-css.cjs`를 아래 내용 그대로 만든다(repo 밖, 커밋하지 않음).

```js
// Removes the product detail CSS the review layout no longer uses (detail search, hero, chips,
// content wrapper, bottom CTA, old 639px hero query, editor note, preview grid, large visit button).
// Each cut removes lines [start - before, end): start = the only line equal to `from`, end = first line equal to `to` after it.
// The line count must match `expected`, otherwise nothing is written. Run from the repo root.
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

// 1. sticky detail search (base rules); .product-detail-page stays
cut('detail search', '.product-detail-search {', '@media (max-width: 767px) {', 20);
// 2–3. detail search inside the 767px query (.product-filter-search rules and the query stay)
cut('mobile detail search', '  .product-detail-search {', '  .product-filter-search .handbook-search-input {', 5);
cut('mobile detail search input', '  .product-detail-search .handbook-search-input {', '}', 7, { before: 1 });
// 4. preview grid modifier (detail alternatives were the only user)
cut('preview grid', '.product-grid--preview {', '@media (max-width: 767px) {', 4);
// 5–7. old hero
cut('hero', '/* Hero — 2컬럼 C-1: left(flex:3) name+tagline+CTA, right(flex:1) logo+meta */', '.product-detail-logo,', 14);
cut('hero text', '.product-detail-hero-text {', '.product-detail-name {', 7);
cut('hero meta/actions/platform/stat', '.product-detail-hero-meta {', "/* Crumb, head (identity + facts box), tags row, editor's take */", 30);
// 8. large visit button (bottom CTA)
cut('large visit button', '.product-visit-btn--large {', '/* ── Product Like Button (Detail Page) ────────────────────────────────────── */', 5);
// 9. chips + content wrapper
cut('chips + content', '.product-detail-chip {', '.product-detail-section {', 76);
// 10. bottom CTA + old 639px hero query
cut('bottom cta + 639px hero', '/* Bottom CTA */', '/* --- Product Detail: section heads, Features & Use Cases --- */', 54);
// 11. old editor note (replaced by .product-detail-verdict)
cut('editor note', '/* --- Product Detail: Editor Note --- */', '/* --- Product Detail: Scenarios --- */', 15);

fs.writeFileSync(file, lines.join('\n'));
console.log('done');
```

2. repo 루트에서 `node <scratchpad>/drop-product-detail-css.cjs` → 아래 출력(시작 줄 번호는 달라질 수 있다. **줄 수**가 다르면 아무것도 쓰지 않고 오류 → 멈추고 보고):
```
detail search: removed 20 lines from line 11888
mobile detail search: removed 5 lines from line 11894
mobile detail search input: removed 7 lines from line 11900
preview grid: removed 4 lines from line 13169
hero: removed 14 lines from line 13415
hero text: removed 7 lines from line 13440
hero meta/actions/platform/stat: removed 30 lines from line 13463
large visit button: removed 5 lines from line 13635
chips + content: removed 76 lines from line 13733
bottom cta + 639px hero: removed 54 lines from line 13754
editor note: removed 15 lines from line 13833
done
```

- 지워지는 것: `.product-detail-search`·`.product-detail-search.handbook-search-sticky`·`body:has(…) .product-detail-search.handbook-search-sticky`·`.product-detail-search .handbook-search-input`(기본 + 767px 쿼리 안 2규칙), `.product-grid--preview`, `/* Hero — 2컬럼 … */` `.product-detail-hero`·`-hero-identity`·`-hero-text`·`-hero-meta`·`-hero-actions`·`/* Hero right column … */` `-hero-platform-text`·`-hero-stat`, `.product-visit-btn--large`, `.product-detail-chip*`(category·category-secondary·accent·muted·tag·stat), `/* Content */ .product-detail-content`, `/* Bottom CTA */ .product-detail-bottom-cta`, `/* Mobile */ @media (max-width: 639px)`(hero·로고·이름·태그·chip), `/* --- Product Detail: Editor Note --- */` `.product-detail-editor-note`·`p`.
- 남는 것: `.product-detail-page`, 767px 쿼리의 `.product-filter-search` 두 규칙과 닫는 `}`, `@media (max-width: 360px)`, `.product-grid` 및 767/479px 쿼리, 새 로고·이름·머리 규칙, `.product-visit-btn`·`.product-like-btn`·카드 찜·서재 규칙, `.product-detail-section`·description, 난이도 점, 시나리오 이하 Task 2 규칙.

Run:
```bash
grep -n "product-detail-search\|product-grid--preview\|product-detail-chip\|product-detail-hero\|product-detail-content\|product-detail-editor-note\|product-detail-bottom-cta\|product-visit-btn--large" frontend/src/styles/global.css
grep -n "^\.product-detail-page {\|^\.handbook-search-sticky {\|border-radius: 12px;" frontend/src/styles/global.css
```
Expected: 첫 줄 결과 없음. 둘째 줄 3줄(`.handbook-search-sticky {`, `.product-detail-page {`, 새 로고 규칙의 `  border-radius: 12px;`).

- [ ] **Step 6: 상세 검색 테스트 삭제**

```bash
git rm frontend/tests/product-detail-search-sticky.test.cjs frontend/tests/product-detail-search-spacing.test.cjs
```

- [ ] **Step 7: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/product-detail-review.test.cjs
node frontend/tests/products-catalog.test.cjs
node frontend/tests/products-v2.test.cjs
node frontend/tests/product-detail-scenarios-theme.test.cjs
node frontend/tests/product-detail-admin-actions.test.cjs
node frontend/tests/list-v2.test.cjs
node frontend/tests/handbook-term-entry.test.cjs
node frontend/tests/handbook-search-recognition.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 테스트를 뺀 모두 `… passed`, 빌드 "Complete!".
- `handbook-search-recognition` FAIL `Handbook search input must define theme-specific input surface colors` — 기준선과 **같은 메시지**(`Handbook search input must use a softer rounded corner`가 나오면 Task 2의 로고 `border-radius: 12px;`가 빠진 것 → 멈추고 보고).

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/products/ProductSearchBar.astro frontend/src/styles/global.css frontend/tests/product-detail-review.test.cjs
git commit -m "chore: remove product detail search, hero, chips and unused detail CSS"
```

(`git rm`으로 stage된 테스트 2개 삭제가 함께 커밋된다.)

---

## Task 4: 검증 (컨트롤러)

- [ ] 전체 테스트를 **이름 + 첫 오류 메시지로** 기준선(PASS 83 / FAIL 19)과 비교한다.
  ```bash
  for f in frontend/tests/*.cjs frontend/tests/*.mjs; do node "$f" >/dev/null 2>&1 && echo "PASS $(basename $f)" || echo "FAIL $(basename $f)"; done
  ```
  - 실패 목록은 기준선 19개에서 `product-detail-scenarios-theme`만 빠진 18개여야 한다(신규 FAIL 0). 실패 테스트의 첫 오류 메시지도 기준선과 같은지 본다(`node <file> 2>&1 | grep -m1 -E "^[A-Za-z]*Error( \[[A-Z_]+\])?: "`).
  - 이름 변화는 `product-detail-review` 신규 PASS, `product-detail-scenarios-theme` FAIL→PASS, `product-detail-search-sticky`·`product-detail-search-spacing` 삭제뿐 → **PASS 83 / FAIL 18**.
- [ ] `cd frontend && npm run build` "Complete!".
- [ ] 브라우저(`.claude/launch.json`의 `frontend-dev`, 포트 4321) 매트릭스: 종이·순백·다크 × 1100px·375px × ko/en, 대상 `chatgpt`(가격표 있음), `flowise`(가격표 없음), `grok`(한국어 메모 있음)
  - 스크린샷(테마·폭·locale마다), 가로 넘침 0(`document.documentElement.scrollWidth <= window.innerWidth`, 가격표는 컨테이너 안 스크롤만 허용)
  - 대비 검사: 경로 줄(secondary/muted), 태그 줄(secondary·muted), 스펙 `dt`(muted)·`dd`, 에디터 한마디 라벨(accent)·인용, 좋은 점/아쉬운 점 제목·기호(success/error), 시나리오 번호(accent, bg-secondary 위)·본문(secondary), "더 보기"(accent), 가격표, 비슷한 도구 줄, 고정 바 버튼(다크 포함)
  - ≥768px: 머리 2열(오른쪽 250px 스펙 상자), 장단점 2칸, 기능/상황 2단, 비슷한 도구 2열. ≤767px: 머리 1열, `dl` 2×2, 이름 약 1.9rem, 장단점·기능/상황·비슷한 도구 1열, 좌우 16px, 버튼 바가 화면 아래 고정(스크롤 중에도), 페이지 맨 끝에서 푸터가 바에 가리지 않음.
- [ ] 직접 클릭
  - 경로 줄 분야 링크 → 목록 `?cat=` 모드로 열림, "← AI 제품군" → 목록.
  - 사이트 방문(새 창, `rel="noopener noreferrer"`), 찜(비로그인 → 로그인 안내 시트가 바 위로 열림), 로그인 상태에서 찜 토글·개수(가능하면).
  - "2개 더 보기" 펼침·접힘(번호 4·5 이어짐), FAQ 펼침, 비슷한 도구 줄 → 해당 상세, 관련 뉴스 링크.
  - 모바일 하단 버튼 바: 스크롤 중 고정, 쿠키 배너가 떠 있으면 배너가 위(허용), 닫으면 바 보임.
  - 다른 페이지 → 상세(ClientRouter 이동) 뒤 찜 버튼이 한 번만 묶이는지(클릭 한 번에 요청 한 번).
- [ ] 회귀: 목록 페이지(줄 마크업·검색·모두 보기·`?cat=` 진입), 서재 `library`의 제품 카드(`ProductCard`), 홈의 제품 카드.
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 5: 문서

- [ ] 스펙 [[2026-10-18-product-detail-review-design]] Status를 `implemented (YYYY-MM-DD)`로 바꾼다.
- [ ] 이 계획의 Status를 `done (YYYY-MM-DD) — 실행 결과는 문서 끝 참조.`로 바꾸고, 문서 끝에 "## 실행 결과 (YYYY-MM-DD)"(커밋 해시, 테스트 이름 비교 결과, 빌드, 매트릭스·클릭 결과, 계획 대비 변경, 후속)를 적는다.
- [ ] `ACTIVE_SPRINT.md`의 `REDESIGN-PRODUCTS` 항목 아래 `- **증거:** 커밋 267a792d, ee88786e, 996d6c37, …` 줄 **바로 다음 줄**에 추가한다(그 아래 `27e00b48` 증거 줄은 건드리지 않는다).
  ```
  - [x] **REDESIGN-PRODUCT-DETAIL** — AI 제품 상세를 리뷰 지면(A)으로: 경로 줄(← AI 제품군 · 분야), 머리 + 스펙 상자(가격·난이도·플랫폼·한국어, 사이트 방문·찜 한 벌), 에디터 한마디 큰 인용 먼저, 장단점 2칸, 시나리오 3개 + 더 보기, 기능·상황 2단, 비슷한 도구는 목록과 같은 ProductRow(원래 이름), 모바일 하단 고정 버튼 바, 상세 sticky 검색·하단 CTA·옛 hero/chip CSS 삭제 — [[2026-10-18-product-detail-review-design]], [[2026-10-18-product-detail-review]]
    - **증거:** 커밋 <Task 1>, <Task 2>, <Task 3>, 신규 FAIL 0, 빌드 성공, <매트릭스·클릭 요약>
  ```
- [ ] `grep -rln "ProductSearchBar sticky\|product-detail-hero\|product-detail-chip\|product-detail-search\|product-detail-bottom-cta" vault --include=*.md`로 관련 노트를 찾는다. `90-Archive/`와 이번 스펙·계획, 지난 날짜의 완료된 계획 본문은 빼고, 제품 상세의 **현재 구조**를 설명하는 노트만 최소한으로 고친다(예: `plans/`에 남아 있는 상세 설계 노트가 있으면 "상세는 2026-10-18 리뷰 지면(A)으로 대체" 한 줄).
- [ ] 알려진 한계·후속을 실행 결과에 적는다: 스크린샷·공식 자료 데이터 없음(갤러리·자료 섹션은 조건부로만 존재), "잘 맞는 사람 / 다른 선택" 새 필드(C안) 범위 밖, 조회수 표시 주석 유지, 운영 데이터에 시나리오 3개 이하·장단점 한쪽만인 제품이 없어 그 분기는 테스트 문자열로만 확인, 쿠키 배너가 떠 있는 동안 모바일 버튼 바가 가려짐(스펙 허용).
- [ ] 커밋(고친 vault 노트 경로만 지정해 add한다. `vault/.obsidian/*`는 넣지 않는다):
  ```bash
  git add vault/09-Implementation/plans/2026-10-18-product-detail-review-design.md vault/09-Implementation/plans/2026-10-18-product-detail-review.md vault/09-Implementation/plans/ACTIVE_SPRINT.md
  git commit -m "docs: record product detail review redesign"
  ```
  (Task 5에서 고친 다른 vault 노트가 있으면 그 경로도 `git add`에 더한다.)

---

## 실행 결과 (2026-10-18)

- 커밋: `3d697589` 비슷한 도구 원래 이름 + ProductRow 추출, `12e2f1b0` 제품 상세를 리뷰 지면으로(경로 줄·스펙 상자·에디터 한마디·장단점·시나리오 더 보기·2단·가격·끝 블록, 상세 검색 제거), `12475893` 상세 검색 sticky 분기·옛 hero·칩·미사용 CSS 삭제.
- 테스트: PASS 83 / FAIL 18(기준선 83 / 19). 변화는 `product-detail-review` 추가, `product-detail-search-sticky`·`-spacing` 삭제, `product-detail-scenarios-theme` FAIL→PASS. 나머지 18개 실패는 이름·첫 오류 동일, 신규 FAIL 0. 빌드 성공(각 Task 후). 계획 단계에서 scratch 복사본 + 운영 데이터 렌더로 사전 검증.
- 브라우저 클릭 검증(/ko/products/chatgpt/): 페이지 높이 4,365px → 3,342px, `#product-like-btn` 1개, h2 순서 에디터 한마디 → 장단점 → 이렇게 써보세요 → 주요 기능 → 이런 상황 → 가격 → 시작하는 법 → 소개 → 관련 뉴스 → 비슷한 도구 → FAQ, 경로 줄 `/ko/products/?cat=assistant`, 사이트 방문 `_blank noopener noreferrer`, 시나리오 3개 + "2개 더 보기", FAQ 펼침, 찜(비로그인) → 로그인 시트, 비슷한 도구 원래 이름(OpenClaw·Google Notebook LM·Anima·Bubble.io), 상세 검색 없음.
- 매트릭스: 종이·순백·다크 × 1100px·375px, 대상 chatgpt·flowise(가격표 없음 → h2 9개)·grok(한국어 메모)·en chatgpt — 가로 넘침 0, 대비 미달 0. 375px 버튼 바 `position: fixed` / z-index 50, 페이지 끝에서 푸터 하단 728px < 바 상단 731px(가림 없음). 쿠키 배너가 떠 있으면 바를 가림(스펙에서 허용).
- 회귀: 목록 `/ko/products/?q=chatgpt` 2줄, 123줄 모두 `data-search-text` 유지.
- 계획 단계 결정: 로고 `border-radius: 12px`(다른 테스트 기준선 메시지 보존), import 단언 갱신, 중복 테두리 규칙 정리, 가격 제목 "가격". 실행 중 계획의 중복 `console.log` 한 줄 제거.
