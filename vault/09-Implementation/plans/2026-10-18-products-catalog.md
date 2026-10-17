# AI 제품군 목록 A(분야 카탈로그) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** ready

**Goal:** `/ko|en/products/`를 "분야 타일 10개가 각자 안에서 스크롤"하는 3열 격자에서 가운데 한 단(최대 1040px) 카탈로그로 바꾼다. 위에서부터 "제목 줄(`h1` AI 제품군 · AI 도구 N개 · C개 분야 + 검색) → 분야 바로가기 → 편집자 추천 5칸(편집자 노트 첫 문장) → 분야 섹션(머리 · 첫 문장 · 3열 목록 6줄 + "n개 모두 보기 →") → 맺음말 · 상표 고지"이다. 같은 제품을 두 번 렌더하던 `#filtered-grid`를 없애고, 분야 모두 보기(`?cat=`)와 검색(`?q=`)은 한 번 렌더한 줄을 보이기·숨기기만 한다.

**Architecture:**
- 순수 모듈 `lib/productCatalog.js`: `firstSentence`, `DIFFICULTY_LABELS`/`difficultyLabel`, `jumpLabel`, `orderPicks`, `catalogSections`(node 테스트 `product-catalog.test.mjs`).
- `productsPage.ts`: `CARD_COLUMNS`에 `difficulty`, 분야 열에 `description_ko/en`, 추천 제품만의 편집자 노트 쿼리(`.eq('featured', true)`)를 `Promise.all`에 추가. 반환에서 `spotlightProduct`를 빼고 `picks`(orderPicks + 노트)를 넣는다. 503 판정은 그대로(`categoriesRes.error || productsRes.error`).
- 새 컴포넌트 `ProductPicks.astro`(추천 칸), `ProductCatalogSection.astro`(분야 섹션 하나: 모든 제품 렌더, 7번째부터 `data-overflow`, 빈 "함께 쓰이는 도구" 상자).
- ko/en `index.astro`: 제목 줄(`ProductSearchBar` 그대로) · 돌아가기 버튼 · 바로가기 · 추천 · 섹션 · 결과 없음 · 맺음말 · 상표 고지. 번들 `<script>`가 `scripts/handbookSearchHints`와 새 `scripts/productCatalog.ts`를 import한다(두 locale이 같은 모드 스크립트를 쓴다).
- `ProductDetail.astro`는 난이도 표를 `DIFFICULTY_LABELS`에서 가져온다(한 곳 관리).
- Task 3에서 `ProductCategoryTile`·`ProductFilterBar`·`ProductSpotlight`·`productCategoryIcons.ts`, 옛 목록 CSS, 안 쓰는 i18n 키 3개, `product-filter-bar-mobile-sticky.test.cjs`를 지운다.

**Tech Stack:** Astro v5 SSR, `global.css`, 순수 Node 테스트(**repo 루트에서** `node frontend/tests/<file>`)

**Spec:** [[2026-10-18-products-catalog-design]] — 구현 전에 반드시 읽는다. 시안: `.superpowers/brainstorm/products/products-v1.html`(A안).

---

## 사전 정보 (실행자 필독)

**작업 규칙**
- 다른 세션과 작업 트리를 공유한다.
  - 각 파일을 수정하기 전에 `git status --short -- <file>`로 확인한다. 미커밋 변경이 있으면 BLOCKED로 보고한다.
  - 다른 세션 파일(`frontend/src/lib/admin/*`, `frontend/src/pages/admin/pipeline-runs/*`, `frontend/src/lib/pageData/publicTermIndex.ts`, `vault/.obsidian/*`, `docs/*`, `frontend/tests/pipeline-run-logs-pagination.test.cjs`, `frontend/tests/public-term-index-behavior.test.cjs`)은 **읽기만 하고 수정·stage하지 않는다**.
- `git add`/`git rm`은 계획에 적힌 경로만 지정한다. `-A`/`.`, stash, reset, checkout은 쓰지 않는다. 샌드박스가 거부하면 우회하지 말고 보고한다.
- 커밋 메시지는 적힌 그대로 쓴다. `Co-Authored-By`나 다른 trailer는 넣지 않는다. 브랜치는 `main`이고 push하지 않는다.
- **백슬래시가 있는 파일은 Write/Edit 도구로만 작성한다.** Bash heredoc을 쓰면 백슬래시가 사라진다. 해당: 테스트 파일 전부(정규식), Task 3의 CSS 삭제 스크립트. 새/교체 파일은 전부 Write 도구로 만든다.
- 이 계획의 코드 블록은 **목록 밖**에 있고 들여쓰기가 없다. 보이는 그대로 쓴다. Edit의 old/new는 "old:" / "new:" 아래 블록 그대로다.
- Astro/JS 파일의 문자열에는 `\uXXXX` 이스케이프를 쓰지 않는다. `·`, `←`, `→`, `…`, 한글은 **문자 그대로** 쓴다(이 계획의 코드 블록도 전부 문자 그대로다).
- 줄바꿈·인코딩
  - `lib/pageData/productsPage.ts`는 작업 트리에서 **CRLF와 LF가 섞여 있다**. Edit 대신 Read 후 **Write로 통째 교체**한다(LF로 저장됨). git 인덱스는 LF이고 `core.autocrlf=true`라 줄바꿈 차이는 diff에 나오지 않는다.
  - `components/products/ProductDetail.astro`와 `frontend/src/i18n/index.ts`는 작업 트리 **CRLF**다. **Edit 도구로만** 고친다(Write·sed 금지).
  - `pages/{ko,en}/products/index.astro`, `global.css`, 테스트 파일은 LF다. ko/en 페이지는 Read 후 Write로 통째 교체한다. CSS 규칙은 줄 번호가 아니라 셀렉터/주석으로 찾는다.
  - 기존 파일을 Write로 통째로 바꾸기 전에 반드시 Read로 먼저 읽는다(도구 요구사항).
- dev 서버(포트 4321)를 켠 채 `npm run build`를 돌리면 EPERM/EMFILE이 날 수 있다. 실패하면 재시도하지 말고 보고한다.

**지켜야 할 것**
- 공개 HTML은 user-neutral이다(CDN 캐시). `Astro.locals` 사용자 상태로 마크업을 가르지 않는다. 목록 줄·추천 칸에는 좋아요·저장 버튼이 없다(`productLike` import도 없앤다).
- 새 스크립트는 번들 `<script>`다(`is:inline` 아님 → nonce 불필요, 미들웨어가 모듈 스크립트에 nonce를 붙인다). `is:inline`을 써야 하면 반드시 `nonce={Astro.locals.cspNonce || ''}`를 붙인다(이 계획에는 없다).
- `.products-page`는 제품 **상세** 페이지(`pages/*/products/[slug].astro`)도 쓴다. 목록의 폭·여백은 루트에 더한 `product-catalog` 클래스(`.products-page.product-catalog`)로만 바꾼다. `.products-page` 규칙 자체는 건드리지 않는다.
- `ProductSearchBar.astro`는 고치지 않는다(상세 sticky 검색 공용). 목록에서는 `sticky` 없이 써서 `form.product-filter-search`가 되므로 `.product-filter-search` 규칙(기본 + 767px 쿼리 안)은 남긴다.
- 남기는 것: `ProductCard.astro`(서재·상세 대안), `.product-grid*`·`.product-card*`, `.product-pricing-badge`·`.product-difficulty-badge`(홈·서재·상세 공용, 새 칩 CSS 없음), `CARD_COLUMNS`의 `demo_media`(`fetchAlternatives` → 상세 대안 카드), i18n `products.heroSubtitle`(목록 meta description).

**테스트 기준선**(2026-10-18, 계획 작성 시 실제 repo에서 측정): **PASS 82 / FAIL 19**
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
  - handbook-detail-table-overflow, handbook-search-recognition, log-list-created-order, navigation-shell-copy, news-fact-pack-structure, public-slug-visibility, sticky-reading-actions-structure — 이번 작업과 무관
  - product-detail-scenarios-theme — `Scenario cards should use the theme background surface instead of a hard white fill`(`global.css`의 `.product-detail-scenario {` 한 줄만 본다. 이번 작업은 그 줄을 건드리지 않으므로 **같은 메시지**여야 한다)
- 제품 목록과 닿는 기존 통과 테스트(작업 뒤에도 PASS): `products-v2`, `public-list-query-budget`, `product-detail-search-sticky`, `public-error-cache-policy`(목록 503 정규식, `categoriesRes.error || productsRes.error`), `public-detail-query-contract`, `product-detail-admin-actions`, `handbook-index-shelves`(`.product-category-showcase` 부재), `product-auth-prompt-copy`(`productLike.ts`는 남는다). `grep -ln "products/index\|productsPage\|ProductFilterBar\|ProductCategoryTile\|product-filter\|product-cat-" frontend/tests/*`로 찾은 것이 전부다.
- 완료 후 기대값: `product-catalog`(mjs)·`products-catalog`(cjs) 신규 PASS, `product-filter-bar-mobile-sticky` 삭제 → **PASS 83 / FAIL 19, 실패 목록·첫 메시지 기준선과 동일, 신규 FAIL 0**. 다른 세션 변경으로 숫자가 흔들릴 수 있으니 판정은 **이름 + 첫 오류 메시지 기준**으로 한다.
- 기준선은 Task 1 전에 다시 잡는다(Task 4의 명령으로 결과를 파일에 저장해 둔다).

**현재 코드**
- `pages/{ko,en}/products/index.astro`(LF, 249줄씩, locale 문자열만 다름): `getProductsPageData` → `ProductFilterBar`(안에 `ProductSearchBar`) → `#products-back-all` → `#category-preview`(`CATEGORY_ORDER`로 정렬한 `ProductCategoryTile` 10개, 표에 없는 분야는 `indexOf = -1`이라 **앞**으로 감) → `#filtered-grid`(같은 123개를 `ProductCard`로 한 번 더) → `#product-search-no-results` → `.products-empty` → `.product-outro` → 상표 고지. 페이지 스크립트: `handbookSearchHints`·`productLike` import, 검색·분야 필터(`replaceState`), 타일 머리/더보기 클릭, `#태그` 클릭 검색. `h1`이 없다. `buildSearchText`(`pricingKo`·`categoryKo` 포함)는 그대로 옮긴다.
- `lib/pageData/productsPage.ts`(CRLF/LF 혼합, 443줄): `PRODUCT_CATEGORY_COLUMNS = 'id, label_en, label_ko, sort_order'`, `CARD_COLUMNS`(difficulty 없음). `getProductsPageData`는 분야·제품 두 쿼리 → locale 이름/한 줄 설명 해석 → 정렬(분야 → 추천 먼저 → featured_order → sort_order → 이름) → `spotlightProduct`(쓰는 곳 없음) → `productsByCategory`. 호출처는 두 목록 페이지뿐이다.
- `ProductSearchBar.astro`: `sticky`가 없으면 `form.product-filter-search[data-product-search-form]`, `input#product-search[name=q]`. 자체 submit 핸들러가 빈 검색어면 `preventDefault` 후 `location.href = form.action`(= 목록 새로고침)으로 보낸다.
- `ProductDetail.astro`(CRLF): `difficultyLabels` 표(`{ en, ko }`)를 자체 정의하고 `difficultyLabels[product.difficulty]?.[locale] ?? product.difficulty`로 쓴다.
- CSS(`global.css`): `/* AI PRODUCTS */` → `.products-page`(최대 1440px) → `Products Redesign — Spotlight + FilterBar + Flat Grid` 배너 · `.product-filter-bar`(sticky)·`.product-filter-tabs`·`.product-filter-tab*` → `.product-filter-search`·`.product-detail-*search*`(남김) → 767px 쿼리(`.product-filter-tabs*`·`.product-filter-tab` 삭제 대상, `.product-filter-search`·`.product-detail-search` 남김) → `/* --- Category Preview Section --- */` `.product-category-preview*`·`.product-category-see-all`·`.product-category-grid`·`.products-back-all`·`.product-cat-tile*`·`.product-cat-row*`·`.product-cat-tag`·1024px/560px 쿼리 → `@media (max-width: 360px)`(`.site-nav-pill`, 남김) → `/* --- Handbook category preview --- */`. 아래쪽에 `.product-outro*`(`.product-outro-cta`는 마크업 없음)·`.products-trademark-disclaimer`.
- Tailwind v4 preflight가 `[hidden]`에 `display: none !important`를 준다(번들 CSS에서 확인). 새 CSS의 `[hidden]` 규칙은 안전장치다.
- 운영 데이터(2026-10-18 anon으로 확인): 발행 123개, 분야 10개(전부 `description_ko/en` 있음, `sort_order` 1–10), 분야별 assistant 28 · image 17 · video 9 · audio 5 · coding 14 · workflow 12 · builder 11 · platform 10 · research 7 · community 10. 추천 5개 — ChatGPT(`featured_order` 1), 나머지 4개는 null(Google Antigravity · Google Notebook LM · Hugging Face · OpenClaw 순). 다섯 모두 `editor_note`/`editor_note_ko` 있음. 보조 분야로 assistant를 가진 다른 분야 제품 14개, coding 7개.

**스펙 해석·결정(실행자가 임의로 바꾸지 않는다)**
- `catalogSections(categories, productsByCategory, order, locale)`: 스펙의 3인자에 **`locale`을 더한다**. 각 항목의 `desc`(locale 설명)와 `lede`를 만들려면 locale이 필요해서다. `desc`는 해당 locale 열만 쓴다(다른 언어로 대체하지 않음, 둘 다 운영 데이터에 있음). 표에 없는 분야는 뒤에 `sort_order` 순(같으면 DB 순서 유지).
- `firstSentence`: 약어 뒤 마침표 판정은 약어 바로 앞이 영문자가 아닐 때만 한다("devs."는 단어 끝이라 문장 끝). `Bolt.new`처럼 마침표 뒤가 공백이 아니면 원래 문장 끝이 아니다.
- `orderPicks`는 입력 배열을 바꾸지 않는다(`filter`가 새 배열).
- 추천 노트 쿼리는 `.limit(50)`으로 상한을 둔다(운영 5행). 실패하면 노트만 null → 칸은 tagline. 503은 그대로 분야·제품 쿼리 실패일 때만.
- `ProductCardData.difficulty`는 선택 필드(`difficulty?:`)로 둔다(`fetchLikedProducts`는 이 열을 읽지 않는다).
- 루트: `div.products-page.product-catalog#products-top[data-also-label]`. "함께 쓰이는 도구" 머리 문구 틀(`{k}` 자리)을 `data-also-label`로 넘겨 스크립트 하나가 두 locale을 처리한다.
- 분야 섹션의 개수 `span.product-cat-count`는 `h2` 안에 둔다(제목과 함께 읽힘). "모두 보기" 버튼은 머리 오른쪽, 첫 문장 `p.product-cat-lede`와 전체 설명 `p.product-cat-desc[hidden]`은 머리 아래.
- `div.product-cat-also[hidden]`(빈 `h3` + `ol.product-cat-also-list`)은 **섹션마다** 목록 아래에 렌더한다(분야 모드에서 그 섹션 것만 채움). 목록 CSS는 `.product-cat-list, .product-cat-also-list`로 함께 준다. 복제 줄은 `.product-cat-list` 밖이라 원본 줄 수집·overflow 숨김 규칙에 걸리지 않는다.
- 스크립트는 `scripts/productCatalog.ts` 한 파일(두 페이지가 import). `astro:page-load`마다 + import 시 한 번 즉시 실행하고, `#products-top.product-catalog`의 `dataset.catalogReady`로 중복 바인딩을 막는다. 주소는 `history.replaceState(history.state, …)`(ClientRouter 상태 보존). `q`에는 앞뒤 공백을 뺀 검색어를 쓴다.
- Enter: 목록 스크립트가 같은 폼에 **capture 단계** submit 리스너를 달아 `preventDefault()` + `stopImmediatePropagation()` 후 즉시 필터링한다. 같은 요소의 capture 리스너가 먼저 실행되므로 `ProductSearchBar`의 "빈 검색어 → 목록으로 이동" 핸들러가 돌지 않는다(빈 Enter도 새로고침 없음).
- "모두 보기": 버튼을 기억하고 검색어를 비운 뒤 `cat` 설정 → 분야 모드 → 섹션 `scrollIntoView({ block: 'start' })`(섹션의 `scroll-margin-top`) → `h2.focus({ preventScroll: true })`. 돌아가기: 기본 모드 + 기억한 버튼으로 포커스(없으면 루트로 스크롤).
- 검색 모드에서 `.product-cat-desc`는 숨긴 채, 첫 문장·모두 보기 버튼도 숨긴다. 보이는 줄이 없는 섹션은 `hidden`.
- 레이아웃: 목록 폭은 `.products-page.product-catalog { max-width: 1072px; padding: 0 1rem }`(border-box → 본문 1040px). ≤767px는 `padding: 0 0.25rem`(+ `.main-public` 12px = 좌우 16px). 태블릿 규칙은 `@media (min-width: 768px) and (max-width: 1023px)`로 범위를 닫아 모바일 규칙과 섞이지 않게 한다.
- 스펙의 CSS 삭제 목록 외에 같은 블록 안의 죽은 규칙 `.product-category-preview*`, `.product-category-see-all`(마크업 없음), `.product-outro-cta`(i18n `products.outroCta`와 함께 사용처 없음)도 지운다(각각 grep으로 확인).
- 기존 테스트 처리
  - Task 2: `products-v2.test.cjs` 43–57행(필터 바 그림자·밑줄, 타일 파일 읽기, 타일 핸들러 문자열)을 카드 단언 두 줄만 남기고 지운다. 18행(`.product-spotlight` CSS 부재)은 컴포넌트 파일을 읽지 않고 삭제 후에도 참이므로 **남긴다**. `public-list-query-budget.test.cjs` 18행(`demoMediaFirst`)을 "목록 줄은 로고만, 데모 이미지 없음"으로 바꾼다(31행 `demo_media` 단언은 그대로).
  - Task 3: `product-detail-search-sticky.test.cjs` 58–66행(`ProductFilterBar.astro` 읽기)을 지우고, `product-filter-bar-mobile-sticky.test.cjs`는 **삭제**한다(지우는 CSS만 검사). 삭제 사실은 `products-catalog.test.cjs`에 단언을 더해 고정한다.

**계획 사전 검증(작성 시 scratchpad 복제본에서 수행)**
- `frontend/`(src, tests, public, scripts, examples, 설정 파일, `.env`; node_modules는 junction)+`supabase/` 복제본에 Task 1–3을 이 문서의 코드 그대로 적용했다(코드 블록은 dry-run 파일에서 직접 생성, 테스트·상세·CSS 수정은 "정확히 한 번 일치" 치환 스크립트로). 복제본 기준선은 실제 repo와 이름·첫 오류 메시지 기준 동일(PASS 82 / FAIL 19).
- 각 "실패 확인" Step은 적힌 메시지로 실패, 통과 확인 Step은 PASS. Task 1 뒤 **PASS 83**, Task 2 뒤 **PASS 84 / FAIL 19**, Task 3 뒤 **PASS 83 / FAIL 19**(바뀐 이름은 `product-catalog`·`products-catalog` 신규 PASS, `product-filter-bar-mobile-sticky` 삭제뿐), 실패 19개의 첫 오류 메시지가 기준선과 동일.
- `astro build` "Complete!"(Task 2 후, Task 3 후 두 번). CSS 삭제 스크립트 출력은 Step에 적힌 값과 같았다.
- dev 서버(운영 데이터, 포트 4399, 확인 후 종료) + 브라우저 DOM 검사
  - `/ko/products/` 200: `h1` "AI 제품군", 부제 "AI 도구 123개 · 10개 분야", 바로가기 "어시스턴트 28 | 이미지 17 | 영상 9 | 음성·음악 5 | 코딩 14 | 워크플로우 12 | 앱 빌더 11 | 플랫폼 10 | 리서치 7 | 커뮤니티 10", 추천 5칸("편집자 추천 1 ChatGPT 초안 작성, 디버그, 파일·음성 기반 빠른 리서치를 … 시도해볼 만합니다." 등, 긴 첫 문장은 "…"로 90자 이하), 섹션 10개, 섹션마다 렌더 줄 전부(assistant 28) · 보이는 줄 6(audio 5), 7번째 줄 `display: none`, "모두 보기" 버튼 9개(audio 없음), 1310px에서 목록 3열·추천 5열, 가로 넘침 없음, 추천 머리 `h2.sr-only`(position absolute). `<script>` 전부 nonce.
  - "28개 모두 보기" 클릭: 주소 `?cat=assistant`, 보이는 섹션 `cat-assistant`만, 28줄 보임, 전체 설명 보임·첫 문장·버튼 숨김, 추천·바로가기 숨김, 돌아가기 보임, "다른 분야에서 함께 쓰이는 도구 14개" + 14줄(복제본에 `data-overflow`/`hidden`/id 없음), 포커스 `#cat-assistant-title`. 돌아가기: 주소 비움, 섹션 10개, 복제 0, 포커스가 그 "모두 보기" 버튼으로.
  - 검색: "이미지" → `?q=이미지`, assistant 4 · image 17 · video 7 · coding 1 · builder 1 · platform 3(나머지 섹션 숨김, 모두 보기 0개, 추천 숨김), "chatgpt" → assistant 1 · image 1, "zzzxxqq" → 섹션 0 + 결과 없음 문구, 지우기 → 기본 모드. Enter(검색어 있음/없음) 모두 새로고침 없음(페이지 변수 유지), 빈 Enter 뒤 기본 모드.
  - `/en/products/?cat=coding` 직접 진입: "AI Products", "123 AI tools · 10 fields", "Assistants 28 | … | App builders 11 | Platforms 10 | …", "Pick 1 ChatGPT Worth trying if … and quick…"(영어 노트), 코딩 섹션만 14줄, "Also used for this (7)", "← All fields", "See all 28 →".
  - 375px(모바일 에뮬레이션): `document.documentElement.scrollWidth` 375(넘침 0), 화면 밖 요소 0(가로 스크롤 컨테이너 안 제외), 제목 줄 세로·좌우 16px·검색창 343px, `h1` 27.2px, 바로가기·추천 컨테이너만 가로 스크롤(추천 `display: flex` + `scroll-snap-type: x mandatory`), 목록 1열.
  - 900px: 추천 3열, 목록 2열, 바로가기 "코딩" 클릭 → `#cat-coding` 섹션 위쪽이 화면 86px 지점(가리지 않음).
  - 제품 상세 `/ko/products/chatgpt/` "초보자 OK", `/en/products/chatgpt/` "Beginner-friendly"(DIFFICULTY_LABELS 사용) 200.

---

## Task 1: 카탈로그 순수 함수 (TDD)

**Files:**
- Create: `frontend/src/lib/productCatalog.js`
- Test: `frontend/tests/product-catalog.test.mjs`(새 파일)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/lib/productCatalog.js frontend/tests/product-catalog.test.mjs`
Expected: 출력 없음(둘 다 아직 없음).

- [ ] **Step 1: 실패하는 테스트 작성** — Write 도구로 `frontend/tests/product-catalog.test.mjs`를 아래 내용 그대로 만든다.

```js
// frontend/tests/product-catalog.test.mjs
// Products catalog A (fields): first sentences, difficulty / jump labels, editor's picks order, section order.
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { firstSentence, DIFFICULTY_LABELS, difficultyLabel, jumpLabel, orderPicks, catalogSections } = await import(
  pathToFileURL(path.join(here, '../src/lib/productCatalog.js')).href
);

// --- firstSentence ---
assert.equal(firstSentence('모르는 게 있으면 검색 대신 물어보세요. 논문 요약까지 합니다.'), '모르는 게 있으면 검색 대신 물어보세요.', 'Korean sentence end');
assert.equal(firstSentence('바로 시작할 수 있습니다. 다음 문장'), '바로 시작할 수 있습니다.', 'Korean "…니다. 다음"');
assert.equal(firstSentence('Stop searching, start asking. Summarize papers.'), 'Stop searching, start asking.', 'English ". "');
assert.equal(firstSentence('Line one.\nLine two.'), 'Line one.', '".\\n" ends a sentence');
assert.equal(firstSentence('Really? Yes.'), 'Really?', '"?" ends a sentence');
assert.equal(firstSentence('Bolt.new and v0 build apps. More here.'), 'Bolt.new and v0 build apps.', 'a period inside a word is not an end');
assert.equal(firstSentence('Tools, e.g. Zapier and n8n, automate work. Next.'), 'Tools, e.g. Zapier and n8n, automate work.', '"e.g. " is not an end');
assert.equal(firstSentence('Docs, i.e. guides, etc. are here. Next.'), 'Docs, i.e. guides, etc. are here.', '"i.e." and "etc." are not ends');
assert.equal(firstSentence('Big devs. Small teams.'), 'Big devs.', '"devs." is a word, not "vs."');
assert.equal(firstSentence('문장부호 없는 설명'), '문장부호 없는 설명', 'no sentence end → whole text');
assert.equal(firstSentence('  앞뒤 공백.  '), '앞뒤 공백.', 'trimmed');
const long = 'Worth trying if you want a single chat thread for drafting, debugging, and quick research with files and voice; best suited for creators.';
const cut = firstSentence(long);
assert(cut.length <= 90, `cut to at most 90 chars (got ${cut.length})`);
assert(cut.endsWith('…'), 'cut ends with an ellipsis');
assert.equal(cut, 'Worth trying if you want a single chat thread for drafting, debugging, and quick…');
assert.equal(firstSentence('abcdefghijklmnop', 10), 'abcdefghi…', 'no space → cut at max − 1');
assert.equal(firstSentence('one two three four', 12), 'one two…', 'cut at the last space');
assert.equal(firstSentence(''), '');
assert.equal(firstSentence(null), '');
assert.equal(firstSentence(undefined), '');

// --- labels ---
assert.deepEqual(Object.keys(DIFFICULTY_LABELS), ['beginner', 'intermediate', 'advanced']);
assert.equal(difficultyLabel('ko', 'beginner'), '초보자 OK');
assert.equal(difficultyLabel('ko', 'intermediate'), '약간의 설정 필요');
assert.equal(difficultyLabel('ko', 'advanced'), '기술 설정 필요');
assert.equal(difficultyLabel('en', 'beginner'), 'Beginner-friendly');
assert.equal(difficultyLabel('en', 'intermediate'), 'Some setup needed');
assert.equal(difficultyLabel('en', 'advanced'), 'Technical setup');
assert.equal(difficultyLabel('ko', 'expert'), '', 'unknown difficulty');
assert.equal(difficultyLabel('en', null), '');
assert.equal(difficultyLabel('en', 'toString'), '', 'no prototype keys');

assert.equal(jumpLabel('ko', 'assistant', 'AI 어시스턴트'), '어시스턴트');
assert.equal(jumpLabel('ko', 'audio', 'AI 음성/음악'), '음성·음악');
assert.equal(jumpLabel('ko', 'builder', 'AI 앱 빌더'), '앱 빌더');
assert.equal(jumpLabel('en', 'assistant', 'AI Assistants'), 'Assistants');
assert.equal(jumpLabel('en', 'builder', 'App Builders'), 'App builders');
assert.equal(jumpLabel('en', 'community', 'Communities & Resources'), 'Community');
assert.equal(jumpLabel('ko', 'robotics', '로보틱스'), '로보틱스', 'unknown id → DB label');
assert.equal(jumpLabel('en', 'robotics', ''), 'robotics', 'no label → id');

// --- orderPicks ---
const prod = (name, featured, featured_order = null) => ({ name: `${name} (ko)`, name_original: name, featured, featured_order });
const picks = orderPicks([
  prod('OpenClaw', true),
  prod('Zeta', false, 0),
  prod('ChatGPT', true, 1),
  prod('Hugging Face', true),
  prod('Google Antigravity', true),
  prod('Claude', true, 2),
  prod('Google Notebook LM', true),
]);
assert.deepEqual(
  picks.map((p) => p.name_original),
  ['ChatGPT', 'Claude', 'Google Antigravity', 'Google Notebook LM', 'Hugging Face'],
  'featured_order first (null last), then brand name, at most 5',
);
assert.deepEqual(orderPicks([prod('B', true, 3), prod('A', true, 3)]).map((p) => p.name_original), ['A', 'B'], 'same order → name');
assert.deepEqual(orderPicks([]), []);
assert.deepEqual(orderPicks(null), []);
const input = [prod('B', true), prod('A', true)];
orderPicks(input);
assert.deepEqual(input.map((p) => p.name_original), ['B', 'A'], 'input is not reordered');

// --- catalogSections ---
const cat = (id, sort_order, extra = {}) => ({ id, label_ko: `${id} ko`, label_en: `${id} en`, description_ko: null, description_en: null, sort_order, ...extra });
const CATS = [
  cat('robotics', 0),
  cat('video', 3, { description_ko: '텍스트 한 줄에서 동영상이 만들어집니다. 광고와 단편 영화까지.', description_en: 'A single sentence becomes a video. Ads too.' }),
  cat('assistant', 1),
  cat('empty', 2),
  cat('legal', -1),
];
const BY = { robotics: [{ id: 'r1' }], video: [{ id: 'v1' }, { id: 'v2' }], assistant: [{ id: 'a1' }], empty: [], legal: [{ id: 'l1' }] };
const ORDER = ['assistant', 'image', 'video', 'empty'];
const sections = catalogSections(CATS, BY, ORDER, 'ko');
assert.deepEqual(sections.map((s) => s.category.id), ['assistant', 'video', 'legal', 'robotics'], 'fixed order, unknown fields after in sort_order, empty fields dropped');
assert.deepEqual(sections[1].products.map((p) => p.id), ['v1', 'v2']);
assert.equal(sections[1].desc, '텍스트 한 줄에서 동영상이 만들어집니다. 광고와 단편 영화까지.');
assert.equal(sections[1].lede, '텍스트 한 줄에서 동영상이 만들어집니다.');
assert.deepEqual([sections[0].desc, sections[0].lede], ['', ''], 'no description → empty desc and lede');
const en = catalogSections(CATS, BY, ORDER, 'en');
assert.deepEqual([en[1].desc, en[1].lede], ['A single sentence becomes a video. Ads too.', 'A single sentence becomes a video.']);
assert.deepEqual(catalogSections(CATS, {}, ORDER, 'ko'), [], 'no products → no sections');
assert.deepEqual(catalogSections(null, BY, ORDER, 'ko'), []);

console.log('product-catalog.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/product-catalog.test.mjs`
Expected: FAIL — `Error [ERR_MODULE_NOT_FOUND]: Cannot find module '…\frontend\src\lib\productCatalog.js'`

- [ ] **Step 3: 구현** — Write 도구로 `frontend/src/lib/productCatalog.js`를 만든다.

```js
// frontend/src/lib/productCatalog.js
// Pure helpers for the AI products catalog (A: fields) and the product detail page. No I/O.
// Sections follow a fixed field order; picks are the featured products; labels live here once.

// A period right after one of these is not the end of a sentence.
const ABBREVIATIONS = ['e.g.', 'i.e.', 'etc.', 'Inc.', 'vs.', 'Mr.', 'Dr.'];

function endsWithAbbreviation(head) {
  return ABBREVIATIONS.some((abbr) => {
    if (!head.endsWith(abbr)) return false;
    const before = head.slice(0, head.length - abbr.length);
    return !/[A-Za-z]$/.test(before); // "devs." is a word, not "vs."
  });
}

/**
 * First sentence of `text`, at most `max` characters ("…" included).
 * Sentence end = first /[.!?。](?=\s|$)/ that is not an English abbreviation; none → the whole text.
 * Too long → cut at the last space within max − 1 characters (or at max − 1 when there is none) + "…".
 */
export function firstSentence(text, max = 90) {
  const source = String(text ?? '').trim();
  if (!source) return '';
  let end = source.length;
  const pattern = /[.!?。](?=\s|$)/g;
  let match;
  while ((match = pattern.exec(source)) !== null) {
    const head = source.slice(0, match.index + 1);
    if (endsWithAbbreviation(head)) continue;
    end = match.index + 1;
    break;
  }
  const sentence = source.slice(0, end).trim();
  if (sentence.length <= max) return sentence;
  const room = sentence.slice(0, max - 1);
  const space = room.lastIndexOf(' ');
  return `${(space > 0 ? room.slice(0, space) : room).trimEnd()}…`;
}

/** Difficulty labels shared by the catalog rows and the product detail page. */
export const DIFFICULTY_LABELS = {
  beginner: { ko: '초보자 OK', en: 'Beginner-friendly' },
  intermediate: { ko: '약간의 설정 필요', en: 'Some setup needed' },
  advanced: { ko: '기술 설정 필요', en: 'Technical setup' },
};

const has = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

export function difficultyLabel(locale, value) {
  if (typeof value !== 'string' || !has(DIFFICULTY_LABELS, value)) return '';
  return DIFFICULTY_LABELS[value][locale === 'ko' ? 'ko' : 'en'];
}

// Short field names for the jump bar (field ids are fixed; unknown ids fall back to the DB label).
const JUMP_LABELS = {
  ko: {
    assistant: '어시스턴트',
    image: '이미지',
    video: '영상',
    audio: '음성·음악',
    coding: '코딩',
    workflow: '워크플로우',
    builder: '앱 빌더',
    platform: '플랫폼',
    research: '리서치',
    community: '커뮤니티',
  },
  en: {
    assistant: 'Assistants',
    image: 'Image',
    video: 'Video',
    audio: 'Audio',
    coding: 'Coding',
    workflow: 'Workflow',
    builder: 'App builders',
    platform: 'Platforms',
    research: 'Research',
    community: 'Community',
  },
};

export function jumpLabel(locale, id, fallback) {
  const table = JUMP_LABELS[locale === 'ko' ? 'ko' : 'en'];
  if (typeof id === 'string' && has(table, id)) return table[id];
  return fallback || id || '';
}

const PICK_LIMIT = 5;

/** Editor's picks: featured only, featured_order ascending (null last), then brand name, at most 5. */
export function orderPicks(products) {
  const nameOf = (p) => String(p.name_original ?? p.name ?? '');
  return (Array.isArray(products) ? products : [])
    .filter((p) => p && p.featured)
    .sort((a, b) => {
      const oa = a.featured_order ?? null;
      const ob = b.featured_order ?? null;
      if (oa !== ob) {
        if (oa === null) return 1;
        if (ob === null) return -1;
        return oa - ob;
      }
      return nameOf(a).localeCompare(nameOf(b));
    })
    .slice(0, PICK_LIMIT);
}

/**
 * Catalog sections: fields in `order` first, fields missing from it after them (DB sort_order),
 * fields without products dropped. Each item: { category, products, lede, desc }
 * (desc = the locale description, lede = its first sentence).
 */
export function catalogSections(categories, productsByCategory, order = [], locale = 'ko') {
  const list = Array.isArray(categories) ? categories.filter(Boolean) : [];
  const known = list
    .filter((c) => order.includes(c.id))
    .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
  const rest = list
    .filter((c) => !order.includes(c.id))
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  return [...known, ...rest]
    .map((category) => {
      const products = (productsByCategory && productsByCategory[category.id]) || [];
      const desc = String((locale === 'ko' ? category.description_ko : category.description_en) ?? '').trim();
      return { category, products, lede: firstSentence(desc), desc };
    })
    .filter((section) => section.products.length > 0);
}
```

- [ ] **Step 4: 통과 확인**

Run: `node frontend/tests/product-catalog.test.mjs`
Expected: `product-catalog.test.mjs passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/productCatalog.js frontend/tests/product-catalog.test.mjs
git commit -m "feat: add products catalog helpers"
```

---

## Task 2: 카탈로그 화면 (데이터·컴포넌트·페이지·스크립트·CSS·테스트)

**Files:**
- Modify: `frontend/src/lib/pageData/productsPage.ts`(Write로 전체 교체)
- Create: `frontend/src/components/products/ProductPicks.astro`, `frontend/src/components/products/ProductCatalogSection.astro`, `frontend/src/scripts/productCatalog.ts`
- Modify: `frontend/src/pages/ko/products/index.astro`, `frontend/src/pages/en/products/index.astro`(Write로 전체 교체)
- Modify: `frontend/src/components/products/ProductDetail.astro`(Edit 2곳), `frontend/src/styles/global.css`(Edit 1곳: 블록 추가)
- Test: `frontend/tests/products-catalog.test.cjs`(새 파일), `frontend/tests/products-v2.test.cjs`(Edit 1곳), `frontend/tests/public-list-query-budget.test.cjs`(Edit 1곳)

- [ ] **Step 0: 상태 확인**

Run:
```bash
git status --short -- frontend/src/lib/pageData/productsPage.ts frontend/src/components/products frontend/src/scripts/productCatalog.ts frontend/src/pages/ko/products frontend/src/pages/en/products frontend/src/styles/global.css frontend/tests/products-catalog.test.cjs frontend/tests/products-v2.test.cjs frontend/tests/public-list-query-budget.test.cjs
```
Expected: 출력 없음.

- [ ] **Step 1: 실패하는 구조 테스트 작성** — Write 도구로 `frontend/tests/products-catalog.test.cjs`를 아래 내용 그대로 만든다(Task 3에서 삭제 단언을 더한다).

```js
// frontend/tests/products-catalog.test.cjs
// Products catalog A (fields): head + jump bar + editor's picks + field sections; modes in scripts/productCatalog.ts.
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
  return all[0]; // first match = the base rule (media-query copies come later)
}

// pages
const copy = {
  ko: ['AI 도구 {shownCount}개 · {sections.length}개 분야', '← 모든 분야', 'aria-label="분야 바로가기"', 'data-also-label="다른 분야에서 함께 쓰이는 도구 {k}개"', '제품명, 로고 및 상표는 각 소유자의 자산입니다.'],
  en: ['{shownCount} AI tools · {sections.length} fields', '← All fields', 'aria-label="Jump to field"', 'data-also-label="Also used for this ({k})"', 'Product names, logos, and trademarks are the property of their respective owners.'],
};
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/products/index.astro`);
  for (const s of copy[locale]) assert(page.includes(s), `${locale}: copy ${s}`);
  assert(page.includes(`<h1 class="product-catalog-title">{t.${locale}['products.title']}</h1>`), `${locale}: h1`);
  assert(page.includes('<header class="product-catalog-head">') && page.includes('<ProductSearchBar locale={locale} />'), `${locale}: title row with the search bar`);
  assert(page.includes('<nav class="product-catalog-jump"') && page.includes('href={`#cat-${section.category.id}`}'), `${locale}: jump bar links to #cat-{id}`);
  assert(page.includes(`jumpLabel(locale, section.category.id, section.category.label_${locale})`), `${locale}: short jump labels`);
  assert(page.includes('<ProductPicks picks={picks} locale={locale} />'), `${locale}: editor's picks`);
  assert(page.includes('<ProductCatalogSection section={section} locale={locale} searchTexts={searchTexts} />'), `${locale}: field sections`);
  assert(page.includes('catalogSections(categories, productsByCategory, CATEGORY_ORDER, locale)'), `${locale}: sections from lib/productCatalog.js`);
  assert(page.includes('sections.reduce((sum, section) => sum + section.products.length, 0)'), `${locale}: N = rendered products`);
  assert(page.includes('id="products-top"') && page.includes('class="products-page product-catalog"'), `${locale}: root keeps #products-top`);
  assert(page.includes('<button type="button" class="product-catalog-back" hidden>'), `${locale}: hidden back button`);
  assert(page.includes('id="product-search-no-results"'), `${locale}: no-results line`);
  assert(page.includes('<section class="product-outro">') && page.includes('products-trademark-disclaimer'), `${locale}: outro + trademark notice stay`);
  assert(page.includes("import '../../../scripts/productCatalog';") && !page.includes('is:inline'), `${locale}: bundled catalog script`);
  assert(/if \(error\) Astro\.response\.status = 503;/.test(page), `${locale}: 503 on loader error`);
  for (const gone of ['ProductCategoryTile', 'ProductCard', 'ProductFilterBar', 'filtered-grid', 'category-preview', 'productLike', 'products-back-all', 'product-cat-tag', 'spotlight']) {
    assert(!page.includes(gone), `${locale}: ${gone} removed`);
  }
}

// components
const section = read('components/products/ProductCatalogSection.astro');
assert(section.includes('<section class="product-cat" id={`cat-${category.id}`} data-category={category.id}'), 'section id + data-category');
assert(section.includes('<h2 class="product-cat-title" id={titleId} tabindex="-1">'), 'focusable section heading');
assert(section.includes("{ko ? `${total}개 모두 보기 →` : `See all ${total} →`}") && section.includes('{total > PREVIEW_ROWS && ('), 'see-all button only above six rows');
assert(section.includes('const PREVIEW_ROWS = 6;'), 'six rows per field');
assert(section.includes('<p class="product-cat-lede">') && section.includes('<p class="product-cat-desc" hidden>'), 'lede + hidden full description');
for (const attr of ['data-search-text=', 'data-category={product.primary_category}', 'data-secondary-categories=', "data-overflow={index >= PREVIEW_ROWS ? '' : undefined}"]) {
  assert(section.includes(attr), `row attribute ${attr}`);
}
assert(section.includes('class="product-pricing-badge" data-pricing={product.pricing}') && section.includes('class="product-difficulty-badge" data-difficulty={product.difficulty}'), 'existing badge classes');
assert(section.includes('difficultyLabel(locale, product.difficulty)'), 'difficulty labels from lib/productCatalog.js');
assert(section.includes('{name}</span>') && section.includes('product.name_original ?? product.name'), 'brand name');
assert(section.includes('loading="lazy"') && section.includes('alt=""'), 'lazy decorative logo');
assert(section.includes('<div class="product-cat-also" hidden>'), 'hidden "also used" box');

const picks = read('components/products/ProductPicks.astro');
assert(picks.includes('<section class="product-picks" aria-labelledby="product-picks-title">'), 'picks section');
assert(picks.includes('<h2 id="product-picks-title" class="sr-only">') && picks.includes("'편집자 추천'") && picks.includes(`"Editor's picks"`), 'sr-only picks heading');
assert(picks.includes('{picks.length > 0 && ('), 'no picks → no section');
assert(picks.includes('<a class="product-pick" href={`/${locale}/products/${pick.slug}/`}>'), 'pick links to the product');
assert(picks.includes('`편집자 추천 ${index + 1}`') && picks.includes('`Pick ${index + 1}`'), 'pick labels');
assert(picks.includes('ko ? pick.editor_note_ko || pick.editor_note : pick.editor_note'), 'en never falls back to the ko note');
assert(picks.includes('firstSentence(note) || pick.tagline'), 'first sentence of the note, else the tagline');

// data
const data = read('lib/pageData/productsPage.ts');
const cardColumns = data.match(/const CARD_COLUMNS =[\s\S]*?;/)[0];
assert(/difficulty/.test(cardColumns), 'cards carry difficulty');
assert(!/editor_note/.test(cardColumns), 'card query does not ship editor notes');
assert(/demo_media/.test(cardColumns), 'demo_media stays (detail alternatives)');
assert(/const PRODUCT_CATEGORY_COLUMNS = 'id, label_en, label_ko, description_ko, description_en, sort_order';/.test(data), 'field descriptions');
const listFn = data.slice(data.indexOf('export async function getProductsPageData'), data.indexOf('// Detail page'));
assert(listFn.includes(".select(PICK_NOTE_COLUMNS)") && listFn.includes(".eq('featured', true)"), 'featured note query');
assert(data.includes("const PICK_NOTE_COLUMNS = 'id, editor_note, editor_note_ko';"), 'note columns');
assert(listFn.includes('categoriesRes.error || productsRes.error'), '503 only for the two list queries');
assert(listFn.includes('notesRes.error ? [] : notesRes.data'), 'failed note query → tagline fallback');
assert(listFn.includes('orderPicks(resolvedProducts)'), 'picks ordered by orderPicks');
assert(!data.includes('spotlightProduct'), 'spotlightProduct removed');
assert(data.includes('picks: ProductPick[];'), 'ProductsPageData.picks');

// script
const script = read('scripts/productCatalog.ts');
assert(script.includes('const DEBOUNCE_MS = 150;'), 'debounce 150ms');
assert(script.includes("root.dataset.catalogReady === 'true'") && script.includes("root.dataset.catalogReady = 'true';"), 'binding guard');
assert(script.includes("document.addEventListener('astro:page-load', initProductCatalog);"), 'runs on every page load');
assert(script.includes("querySelectorAll<HTMLElement>('.product-cat-list > li.product-row')"), 'original rows collected once');
const cloneAt = script.indexOf('row.cloneNode(true)');
assert(cloneAt > 0, 'also rows are clones');
const afterClone = script.slice(cloneAt, cloneAt + 200);
assert(afterClone.includes("removeAttribute('data-overflow')") && afterClone.includes("removeAttribute('hidden')"), 'clones drop data-overflow and hidden');
assert(script.includes("replaceChildren()"), 'also list emptied when leaving the field');
assert(script.includes("history.replaceState(history.state, '', url.toString())"), 'URL via replaceState');
assert(script.includes('event.preventDefault();') && script.includes('event.stopImmediatePropagation();') && script.includes('}, true);'), 'Enter never reloads');
assert(script.includes("params.get('cat')") && script.includes('fieldIds.has(initialField)'), 'only rendered fields apply from ?cat=');
assert(script.includes("focus({ preventScroll: true })") && script.includes('returnTo.focus()'), 'focus moves to the field and back');

// CSS
assert(/grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/.test(rule('.product-cat-list,\n.product-cat-also-list')), 'rows: 3 columns');
assert(/grid-template-columns:\s*repeat\(5, minmax\(0, 1fr\)\)/.test(rule('.product-picks-list')), 'picks: 5 columns');
assert(/display:\s*none/.test(rule('.product-cat-list > [data-overflow]')), 'rows after six hidden');
assert(/display:\s*block/.test(rule('.product-cat[data-expanded] .product-cat-list > [data-overflow]:not([hidden])')), 'expanded field shows every row');
assert(rule('.product-cat').includes('scroll-margin-top: calc(var(--header-h, 4rem) + 1rem)'), 'anchors clear the fixed header');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.product-cat-head')), 'field ink rule');
assert(/border-bottom:\s*2px solid var\(--color-text-primary\)/.test(rule('.product-catalog-head')), 'title ink rule');
const tabletAt = css.indexOf('@media (min-width: 768px) and (max-width: 1023px) {\n  .product-picks-list');
assert(tabletAt > 0, 'catalog tablet block');
const tablet = css.slice(tabletAt, css.indexOf('\n}\n', tabletAt));
assert(/\.product-picks-list\s*\{[^}]*repeat\(3, minmax\(0, 1fr\)\)/.test(tablet), 'tablet: picks 3 columns');
assert(/\.product-cat-also-list\s*\{[^}]*repeat\(2, minmax\(0, 1fr\)\)/.test(tablet), 'tablet: rows 2 columns');
const mobileAt = css.indexOf('/* Products catalog: mobile */');
assert(mobileAt > 0, 'catalog mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.product-cat-also-list\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: rows 1 column');
assert(/\.product-catalog-jump-list\s*\{[^}]*overflow-x:\s*auto/.test(mobile), 'mobile: jump bar scrolls sideways');
assert(/\.product-picks-list\s*\{[^}]*overflow-x:\s*auto[^}]*scroll-snap-type:\s*x mandatory/.test(mobile), 'mobile: picks scroll sideways');
assert(/\.product-catalog-title\s*\{[^}]*font-size:\s*1\.7rem/.test(mobile), 'mobile: smaller h1');

// one label table for the detail page too
const detail = read('components/products/ProductDetail.astro');
assert(detail.includes("import { DIFFICULTY_LABELS } from '../../lib/productCatalog.js';"), 'ProductDetail imports DIFFICULTY_LABELS');
assert(!detail.includes("beginner: { en: 'Beginner-friendly'"), 'no second difficulty table');

console.log('products-catalog.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/products-catalog.test.cjs`
Expected: FAIL — `AssertionError [ERR_ASSERTION]: ko: copy AI 도구 {shownCount}개 · {sections.length}개 분야`

- [ ] **Step 3: 데이터 계층** — `frontend/src/lib/pageData/productsPage.ts`를 Read한 뒤 Write로 아래 내용 그대로 통째 교체한다(바뀌는 곳: `orderPicks` import, `ProductCardData.difficulty?`, `ProductPick` 타입, `ProductsPageData.picks`, 분야 열 `description_ko, description_en`, `CARD_COLUMNS`의 `difficulty`, `PICK_NOTE_COLUMNS`, 세 번째 쿼리, `spotlightProduct` → `picks`. 상세·대안·관련 뉴스·서재·홈 함수는 글자 하나 바뀌지 않는다).

```ts
import { createClient } from '@supabase/supabase-js';
import { supabase } from '../supabase';
import { getPublicSupabase } from './shared';
import { renderMarkdown } from '../markdown';
import { resolveLocalizedProductTags } from '../productTags';
import { orderPicks } from '../productCatalog.js';

// =============================================================================
// Types
// =============================================================================

export interface ProductCategory {
  id: string;
  label_en: string;
  label_ko: string;
  description_en: string | null;
  description_ko: string | null;
  icon: string | null;
  sort_order: number;
}

export interface ProductCardData {
  id: string;
  slug: string;
  name: string;
  name_original: string;
  tagline: string | null;
  logo_url: string | null;
  thumbnail_url: string | null;
  pricing: string | null;
  platform: string[] | null;
  korean_support: boolean;
  primary_category: string;
  secondary_categories: string[] | null;
  featured: boolean;
  featured_order: number | null;
  demo_media: Array<{ type: string; url: string }> | null;
  view_count: number;
  sort_order: number | null;
  tags: string[] | null;
  tags_ko: string[] | null;
  display_tags: string[] | null;
  difficulty?: 'beginner' | 'intermediate' | 'advanced' | null;
}

/** Featured product on the catalog page, with the editor note for its one-line pitch. */
export interface ProductPick extends ProductCardData {
  editor_note: string | null;
  editor_note_ko: string | null;
}

export interface ProductDetailData {
  id: string;
  slug: string;
  name: string;
  name_original: string;
  name_ko: string | null;
  url: string;
  tagline: string | null;
  tagline_ko: string | null;
  description: string | null;
  description_ko: string | null;
  primary_category: string;
  secondary_categories: string[] | null;
  logo_url: string | null;
  thumbnail_url: string | null;
  demo_media: Array<{ type: string; url: string; caption?: string }>;
  tags: string[] | null;
  tags_ko: string[] | null;
  display_tags: string[] | null;
  platform: string[] | null;
  korean_support: boolean;
  released_at: string | null;
  pricing: string | null;
  pricing_note: string | null;
  view_count: number;
  like_count: number;
  features: string[];
  features_ko: string[];
  use_cases: string[];
  use_cases_ko: string[];
  getting_started: string[];
  getting_started_ko: string[];
  pricing_detail: string | null;
  pricing_detail_ko: string | null;
  scenarios: Array<{ title: string; steps: string }>;
  scenarios_ko: Array<{ title: string; steps: string }>;
  pros_cons: { pros: string[]; cons: string[] } | null;
  pros_cons_ko: { pros: string[]; cons: string[] } | null;
  difficulty: 'beginner' | 'intermediate' | 'advanced' | null;
  editor_note: string | null;
  editor_note_ko: string | null;
  official_resources: Array<{ label: string; url: string }>;
  verified_at: string | null;
  korean_quality_note: string | null;
}

export interface ProductsPageData {
  categories: ProductCategory[];
  picks: ProductPick[];
  allProducts: ProductCardData[];
  productsByCategory: Record<string, ProductCardData[]>;
  totalProducts: number;
  error: string | null;
}

export interface ProductDetailPageData {
  product: ProductDetailData | null;
  htmlDescription: string;
  htmlPricingDetail: string;
  error: string | null;
}

export interface HomeFeaturedProduct {
  id: string;
  slug: string;
  name: string;
  name_ko: string | null;
  tagline: string | null;
  tagline_ko: string | null;
  logo_url: string | null;
  pricing: string | null;
  korean_support: boolean;
}

export const PRODUCT_DETAIL_PUBLIC_COLUMNS = [
  'id', 'slug', 'name', 'name_ko', 'url', 'tagline', 'tagline_ko',
  'description', 'description_ko', 'primary_category', 'secondary_categories',
  'logo_url', 'thumbnail_url', 'demo_media', 'tags', 'tags_ko', 'platform',
  'korean_support', 'released_at', 'pricing', 'pricing_note', 'view_count',
  'like_count', 'features', 'features_ko', 'use_cases', 'use_cases_ko',
  'getting_started', 'getting_started_ko', 'pricing_detail', 'pricing_detail_ko',
  'scenarios', 'scenarios_ko', 'pros_cons', 'pros_cons_ko', 'difficulty',
  'editor_note', 'editor_note_ko', 'official_resources', 'verified_at',
  'korean_quality_note',
].join(', ');

// =============================================================================
// List page
// =============================================================================

const PRODUCT_CATEGORY_COLUMNS = 'id, label_en, label_ko, description_ko, description_en, sort_order';
const CARD_COLUMNS =
  'id, slug, name, name_ko, tagline, tagline_ko, logo_url, thumbnail_url, pricing, platform, korean_support, primary_category, secondary_categories, featured, featured_order, demo_media, view_count, sort_order, tags, tags_ko, difficulty';
// Editor notes ship only for the featured rows (the picks), not on every card.
const PICK_NOTE_COLUMNS = 'id, editor_note, editor_note_ko';

export async function getProductsPageData(locale: 'en' | 'ko'): Promise<ProductsPageData> {
  if (!supabase) {
    return { categories: [], picks: [], allProducts: [], productsByCategory: {}, totalProducts: 0, error: null };
  }

  const [categoriesRes, productsRes, notesRes] = await Promise.all([
    supabase.from('ai_product_categories').select(PRODUCT_CATEGORY_COLUMNS).order('sort_order'),
    supabase
      .from('ai_products')
      .select(CARD_COLUMNS)
      .eq('is_published', true)
      .eq('archived', false)
      .order('sort_order')
      .order('name')
      .limit(200),
    supabase
      .from('ai_products')
      .select(PICK_NOTE_COLUMNS)
      .eq('is_published', true)
      .eq('archived', false)
      .eq('featured', true)
      .limit(50),
  ]);

  if (categoriesRes.error || productsRes.error) {
    const message = categoriesRes.error?.message || productsRes.error?.message || 'Product list lookup failed.';
    return { categories: [], picks: [], allProducts: [], productsByCategory: {}, totalProducts: 0, error: message };
  }

  const categories = (categoriesRes.data ?? []) as unknown as ProductCategory[];
  const allProducts = (productsRes.data ?? []) as unknown as ProductCardData[];

  // Category sort order map for grouping products by category
  const catOrder = Object.fromEntries(categories.map((c) => [c.id, c.sort_order]));

  const resolvedProducts = allProducts.map((p) => ({
    ...p,
    name: (locale === 'ko' ? (p as any).name_ko || p.name : p.name) as string,
    name_original: p.name as string,
    tagline: (locale === 'ko' ? (p as any).tagline_ko || p.tagline : p.tagline) as string | null,
    display_tags: resolveLocalizedProductTags(p, locale),
  }));

  // Sort: category order → featured first (by featured_order) → sort_order → name
  resolvedProducts.sort((a, b) => {
    const catA = catOrder[a.primary_category] ?? 99;
    const catB = catOrder[b.primary_category] ?? 99;
    if (catA !== catB) return catA - catB;
    const fa = a.featured ? 0 : 1;
    const fb = b.featured ? 0 : 1;
    if (fa !== fb) return fa - fb;
    if (a.featured && b.featured) {
      const oa = a.featured_order ?? 99;
      const ob = b.featured_order ?? 99;
      if (oa !== ob) return oa - ob;
    }
    const sortA = a.sort_order ?? 99;
    const sortB = b.sort_order ?? 99;
    if (sortA !== sortB) return sortA - sortB;
    return a.name.localeCompare(b.name);
  });

  // Editor's picks: featured rows in pick order + their editor notes.
  // A failed note query only drops the notes (cards fall back to the tagline); the page stays 200.
  const notesById = new Map<string, { editor_note: string | null; editor_note_ko: string | null }>(
    ((notesRes.error ? [] : notesRes.data) ?? []).map((row: any) => [row.id, row]),
  );
  const picks: ProductPick[] = (orderPicks(resolvedProducts) as ProductCardData[]).map((p) => {
    const note = notesById.get(p.id);
    return { ...p, editor_note: note?.editor_note ?? null, editor_note_ko: note?.editor_note_ko ?? null };
  });

  // Group by category for preview mode
  const productsByCategory: Record<string, ProductCardData[]> = {};
  for (const cat of categories) {
    productsByCategory[cat.id] = resolvedProducts.filter((p) => p.primary_category === cat.id);
  }

  return { categories, picks, allProducts: resolvedProducts, productsByCategory, totalProducts: resolvedProducts.length, error: null };
}

// =============================================================================
// Detail page
// =============================================================================

export async function getProductDetailData(
  slug: string,
  locale: 'en' | 'ko',
): Promise<ProductDetailPageData> {
  const db = getPublicSupabase();
  if (!db) {
    return { product: null, htmlDescription: '', htmlPricingDetail: '', error: 'Database unavailable.' };
  }

  const { data, error } = await db
    .from('ai_products')
    .select(PRODUCT_DETAIL_PUBLIC_COLUMNS)
    .eq('slug', slug)
    .eq('is_published', true)
    .eq('archived', false)
    .single();

  if (error) {
    // PGRST116 = no rows found
    if (error.code === 'PGRST116') {
      return { product: null, htmlDescription: '', htmlPricingDetail: '', error: null };
    }
    return { product: null, htmlDescription: '', htmlPricingDetail: '', error: error.message };
  }

  const raw = data as any;

  // Resolve locale fields
  const product: ProductDetailData = {
    id: raw.id,
    slug: raw.slug,
    name: (locale === 'ko' ? raw.name_ko || raw.name : raw.name) as string,
    name_original: raw.name as string,
    name_ko: raw.name_ko,
    url: raw.url,
    tagline: (locale === 'ko' ? raw.tagline_ko || raw.tagline : raw.tagline) as string | null,
    tagline_ko: raw.tagline_ko,
    description: raw.description,
    description_ko: raw.description_ko,
    primary_category: raw.primary_category,
    secondary_categories: raw.secondary_categories,
    logo_url: raw.logo_url,
    thumbnail_url: raw.thumbnail_url,
    demo_media: (raw.demo_media as Array<{ type: string; url: string; caption?: string }>) ?? [],
    tags: raw.tags,
    tags_ko: raw.tags_ko,
    display_tags: resolveLocalizedProductTags(raw, locale),
    platform: raw.platform,
    korean_support: raw.korean_support ?? false,
    released_at: raw.released_at,
    pricing: raw.pricing,
    pricing_note: raw.pricing_note,
    view_count: raw.view_count ?? 0,
    like_count: raw.like_count ?? 0,
    features: (raw.features as string[]) ?? [],
    features_ko: (raw.features_ko as string[]) ?? [],
    use_cases: (raw.use_cases as string[]) ?? [],
    use_cases_ko: (raw.use_cases_ko as string[]) ?? [],
    getting_started: (raw.getting_started as string[]) ?? [],
    getting_started_ko: (raw.getting_started_ko as string[]) ?? [],
    pricing_detail: raw.pricing_detail ?? null,
    pricing_detail_ko: raw.pricing_detail_ko ?? null,
    scenarios: (raw.scenarios as Array<{ title: string; steps: string }>) ?? [],
    scenarios_ko: (raw.scenarios_ko as Array<{ title: string; steps: string }>) ?? [],
    pros_cons: raw.pros_cons ?? null,
    pros_cons_ko: raw.pros_cons_ko ?? null,
    difficulty: raw.difficulty ?? null,
    editor_note: raw.editor_note ?? null,
    editor_note_ko: raw.editor_note_ko ?? null,
    official_resources: (raw.official_resources as Array<{ label: string; url: string }>) ?? [],
    verified_at: raw.verified_at ?? null,
    korean_quality_note: raw.korean_quality_note ?? null,
  };

  const rawDescription =
    locale === 'ko' ? raw.description_ko || raw.description : raw.description;

  const htmlDescription = rawDescription ? await renderMarkdown(rawDescription) : '';

  const rawPricing = locale === 'ko'
    ? raw.pricing_detail_ko || raw.pricing_detail
    : raw.pricing_detail;
  const htmlPricingDetail = rawPricing ? await renderMarkdown(rawPricing) : '';

  return { product, htmlDescription, htmlPricingDetail, error: null };
}

// =============================================================================
// Detail page: alternatives
// =============================================================================

export async function fetchAlternatives(
  category: string,
  excludeSlug: string,
  locale: 'en' | 'ko',
  limit = 4,
): Promise<ProductCardData[]> {
  const db = getPublicSupabase();
  if (!db) return [];
  const { data } = await db
    .from('ai_products')
    .select(CARD_COLUMNS)
    .eq('primary_category', category)
    .eq('is_published', true)
    .eq('archived', false)
    .neq('slug', excludeSlug)
    .order('featured', { ascending: false })
    .order('sort_order')
    .limit(limit);
  if (!data) return [];
  return (data as unknown as ProductCardData[]).map((p) => ({
    ...p,
    name: (locale === 'ko' ? (p as any).name_ko || p.name : p.name) as string,
    tagline: (locale === 'ko' ? (p as any).tagline_ko || p.tagline : p.tagline) as string | null,
    display_tags: resolveLocalizedProductTags(p, locale),
  }));
}

// =============================================================================
// Detail page: related news
// =============================================================================

export interface RelatedNewsItem {
  slug: string;
  title: string;
  published_at: string;
}

export async function fetchRelatedNews(
  productName: string,
  productUrl: string,
  locale: 'en' | 'ko' = 'en',
  limit = 5,
): Promise<RelatedNewsItem[]> {
  const db = getPublicSupabase();
  if (!db) return [];

  // Search news_posts where title contains product name
  const { data } = await db
    .from('news_posts')
    .select('slug, title, published_at')
    .eq('status', 'published')
    .eq('locale', locale)
    .ilike('title', `%${productName}%`)
    .order('published_at', { ascending: false })
    .limit(limit);

  return (data ?? []) as RelatedNewsItem[];
}

// =============================================================================
// Homepage featured
// =============================================================================

// =============================================================================
// Library page: liked products
// =============================================================================

export async function fetchLikedProducts(
  accessToken: string,
  locale: 'en' | 'ko',
): Promise<ProductCardData[]> {
  const db = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  const { data, error } = await db
    .from('ai_product_likes')
    .select(`
      product_id,
      ai_products (
        id, slug, name, name_ko, tagline, tagline_ko,
        logo_url, thumbnail_url, demo_media,
        pricing, platform, korean_support,
        primary_category, featured, featured_order,
        view_count, sort_order, tags, tags_ko, is_published, archived
      )
    `)
    .order('created_at', { ascending: false });

  if (error || !data) return [];

  return data
    .map((row: any) => {
      const p = row.ai_products;
      if (!p) return null;
      if (!p.is_published || p.archived) return null;
      return {
        id: p.id,
        slug: p.slug,
        name: (locale === 'ko' ? p.name_ko || p.name : p.name) as string,
        name_original: p.name as string,
        tagline: (locale === 'ko' ? p.tagline_ko || p.tagline : p.tagline) as string | null,
        logo_url: p.logo_url,
        thumbnail_url: p.thumbnail_url,
        pricing: p.pricing,
        platform: p.platform,
        korean_support: p.korean_support ?? false,
        primary_category: p.primary_category,
        featured: p.featured ?? false,
        featured_order: p.featured_order,
        demo_media: p.demo_media ?? [],
        view_count: p.view_count ?? 0,
        sort_order: p.sort_order ?? null,
        tags: p.tags ?? null,
        tags_ko: p.tags_ko ?? null,
        display_tags: resolveLocalizedProductTags(p, locale),
      } as ProductCardData;
    })
    .filter((p): p is ProductCardData => p !== null);
}

// =============================================================================
// Homepage featured
// =============================================================================

export async function fetchHomeFeaturedProducts(): Promise<HomeFeaturedProduct[]> {
  if (!supabase) return [];

  const { data, error } = await supabase
    .from('ai_products')
    .select('id, slug, name, name_ko, tagline, tagline_ko, logo_url, pricing, korean_support')
    .eq('is_published', true)
    .eq('archived', false)
    .eq('featured', true)
    .order('featured_order')
    .limit(5);

  if (error) return [];
  return (data ?? []) as HomeFeaturedProduct[];
}
```

- [ ] **Step 4: 추천 칸 컴포넌트** — Write 도구로 `frontend/src/components/products/ProductPicks.astro`를 만든다.

```astro
---
// Editor's picks row on the products catalog (featured products, see orderPicks in lib/productCatalog.js).
// One line per pick = first sentence of the editor note (ko: ko note → en note, en: en note only), else the tagline.
import type { ProductPick } from '../../lib/pageData/productsPage';
import { firstSentence } from '../../lib/productCatalog.js';

interface Props {
  picks: ProductPick[];
  locale: 'en' | 'ko';
}

const { picks, locale } = Astro.props;
const ko = locale === 'ko';

const lineOf = (pick: ProductPick) => {
  const note = ko ? pick.editor_note_ko || pick.editor_note : pick.editor_note;
  return firstSentence(note) || pick.tagline || '';
};
---

{picks.length > 0 && (
  <section class="product-picks" aria-labelledby="product-picks-title">
    <h2 id="product-picks-title" class="sr-only">{ko ? '편집자 추천' : "Editor's picks"}</h2>
    <ol class="product-picks-list">
      {picks.map((pick, index) => {
        const name = pick.name_original ?? pick.name;
        const line = lineOf(pick);
        return (
          <li>
            <a class="product-pick" href={`/${locale}/products/${pick.slug}/`}>
              <span class="product-pick-label">{ko ? `편집자 추천 ${index + 1}` : `Pick ${index + 1}`}</span>
              <span class="product-pick-name">
                <span class="product-catalog-logo">
                  {pick.logo_url ? (
                    <img src={pick.logo_url} alt="" width="28" height="28" loading="lazy" />
                  ) : (
                    <span class="product-catalog-logo-initial" data-category={pick.primary_category}>{(name ?? '?').charAt(0)}</span>
                  )}
                </span>
                <span>{name}</span>
              </span>
              {line && <span class="product-pick-line">{line}</span>}
            </a>
          </li>
        );
      })}
    </ol>
  </section>
)}
```

- [ ] **Step 5: 분야 섹션 컴포넌트** — Write 도구로 `frontend/src/components/products/ProductCatalogSection.astro`를 만든다.

```astro
---
// One field section of the products catalog (catalogSections in lib/productCatalog.js).
// Every product of the field is rendered; rows after the sixth carry data-overflow and stay hidden
// until the section is expanded (?cat= or search). The page script only shows/hides rows.
import type { ProductCardData, ProductCategory } from '../../lib/pageData/productsPage';
import { t } from '../../i18n/index';
import { difficultyLabel } from '../../lib/productCatalog.js';

interface Props {
  section: { category: ProductCategory; products: ProductCardData[]; lede: string; desc: string };
  locale: 'en' | 'ko';
  searchTexts: Record<string, string>;
}

const PREVIEW_ROWS = 6;

const { section, locale, searchTexts } = Astro.props;
const { category, products, lede, desc } = section;
const ko = locale === 'ko';
const tr = t[locale] as Record<string, string>;
const label = (ko ? category.label_ko : category.label_en) || category.id;
const total = products.length;
const titleId = `cat-${category.id}-title`;
const pricingLabel = (value: string) => tr[`products.${value}`] ?? value;
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
    {products.map((product, index) => {
      const name = product.name_original ?? product.name;
      return (
        <li
          class="product-row"
          data-search-text={searchTexts[product.id] ?? ''}
          data-category={product.primary_category}
          data-secondary-categories={(product.secondary_categories ?? []).join(',')}
          data-overflow={index >= PREVIEW_ROWS ? '' : undefined}
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
      );
    })}
  </ol>

  <div class="product-cat-also" hidden>
    <h3 class="product-cat-also-title"></h3>
    <ol class="product-cat-also-list"></ol>
  </div>
</section>
```

- [ ] **Step 6: 모드 스크립트** — Write 도구로 `frontend/src/scripts/productCatalog.ts`를 만든다.

```ts
// frontend/src/scripts/productCatalog.ts
// Products catalog (/ko|en/products/) modes. Rows are rendered once on the server; this only shows/hides them.
// - default: jump bar + picks + every field (six rows each)
// - field (?cat=id, "See all"): that field only, every row, full description, "also used for this" clones
// - search (?q=): every field expanded, rows whose data-search-text contains the query
// Bundled module (not is:inline): runs on every astro:page-load; #products-top carries the binding guard.

const DEBOUNCE_MS = 150;

function initProductCatalog(): void {
  const root = document.getElementById('products-top');
  const input = document.getElementById('product-search') as HTMLInputElement | null;
  if (!root || !input || root.dataset.catalogReady === 'true') return;
  if (!root.classList.contains('product-catalog')) return;
  root.dataset.catalogReady = 'true';

  const sections = Array.from(root.querySelectorAll<HTMLElement>('section.product-cat'));
  // Original rows, collected once: clones added to the "also" lists later are never filtered.
  const rows = Array.from(root.querySelectorAll<HTMLElement>('.product-cat-list > li.product-row'));
  const browse = Array.from(root.querySelectorAll<HTMLElement>('.product-catalog-jump, .product-picks'));
  const backButton = root.querySelector<HTMLButtonElement>('.product-catalog-back');
  const noResults = document.getElementById('product-search-no-results');
  const alsoLabel = root.dataset.alsoLabel || '{k}';
  const fieldIds = new Set(sections.map((section) => section.dataset.category || ''));
  let lastSeeAll: HTMLButtonElement | null = null;
  let timer: number | undefined;

  const show = (el: Element | null, visible: boolean) => {
    if (el) (el as HTMLElement).hidden = !visible;
  };
  const part = (section: HTMLElement, selector: string) => section.querySelector<HTMLElement>(selector);

  function clearAlso(): void {
    root!.querySelectorAll<HTMLElement>('.product-cat-also').forEach((box) => {
      box.hidden = true;
      box.querySelector('ol')?.replaceChildren();
    });
  }

  function showDefault(): void {
    clearAlso();
    browse.forEach((el) => show(el, true));
    sections.forEach((section) => {
      section.hidden = false;
      delete section.dataset.expanded;
      show(part(section, '.product-cat-lede'), true);
      show(part(section, '.product-cat-desc'), false);
      show(part(section, '.product-cat-all'), true);
    });
    rows.forEach((row) => { row.hidden = false; });
    show(backButton, false);
    show(noResults, false);
  }

  function showField(id: string): void {
    showDefault();
    const target = sections.find((section) => section.dataset.category === id);
    if (!target) return;
    browse.forEach((el) => show(el, false));
    sections.forEach((section) => { section.hidden = section !== target; });
    target.dataset.expanded = '';
    show(part(target, '.product-cat-lede'), false);
    show(part(target, '.product-cat-desc'), true);
    show(part(target, '.product-cat-all'), false);

    const box = part(target, '.product-cat-also');
    const list = box?.querySelector('ol');
    const also = rows.filter((row) => (
      row.dataset.category !== id
      && (row.dataset.secondaryCategories || '').split(',').includes(id)
    ));
    if (box && list && also.length > 0) {
      also.forEach((row) => {
        const copy = row.cloneNode(true) as HTMLElement;
        copy.removeAttribute('data-overflow');
        copy.removeAttribute('hidden');
        list.appendChild(copy);
      });
      const title = box.querySelector('h3');
      if (title) title.textContent = alsoLabel.replace('{k}', String(also.length));
      box.hidden = false;
    }
    show(backButton, true);
  }

  function showSearch(query: string): void {
    showDefault();
    clearAlso();
    browse.forEach((el) => show(el, false));
    const visibleBySection = new Map<HTMLElement, number>();
    rows.forEach((row) => {
      const match = (row.dataset.searchText || '').includes(query);
      row.hidden = !match;
      const section = row.closest<HTMLElement>('section.product-cat');
      if (section && match) visibleBySection.set(section, (visibleBySection.get(section) || 0) + 1);
    });
    let total = 0;
    sections.forEach((section) => {
      const count = visibleBySection.get(section) || 0;
      total += count;
      section.hidden = count === 0;
      section.dataset.expanded = '';
      show(part(section, '.product-cat-lede'), false);
      show(part(section, '.product-cat-all'), false);
    });
    show(noResults, total === 0);
    show(backButton, true);
  }

  function setParams(update: (params: URLSearchParams) => void): void {
    const url = new URL(window.location.href);
    update(url.searchParams);
    history.replaceState(history.state, '', url.toString());
  }

  function applyQuery(): void {
    window.clearTimeout(timer);
    const raw = input!.value.trim();
    if (raw) {
      setParams((params) => { params.set('q', raw); params.delete('cat'); });
      showSearch(raw.toLowerCase());
    } else {
      setParams((params) => { params.delete('q'); params.delete('cat'); });
      showDefault();
    }
  }

  input.addEventListener('input', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(applyQuery, DEBOUNCE_MS);
  });

  // Enter: filter in place. Capture phase + stopImmediatePropagation so ProductSearchBar's own
  // submit handler (detail pages: go to the list) never reloads this page.
  input.form?.addEventListener('submit', (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    applyQuery();
  }, true);

  root.querySelectorAll<HTMLButtonElement>('.product-cat-all').forEach((button) => {
    button.addEventListener('click', () => {
      const id = button.dataset.category || '';
      if (!fieldIds.has(id)) return;
      lastSeeAll = button;
      window.clearTimeout(timer);
      input!.value = '';
      setParams((params) => { params.delete('q'); params.set('cat', id); });
      showField(id);
      const section = sections.find((s) => s.dataset.category === id);
      section?.scrollIntoView({ block: 'start' });
      section?.querySelector<HTMLElement>('.product-cat-title')?.focus({ preventScroll: true });
    });
  });

  backButton?.addEventListener('click', () => {
    window.clearTimeout(timer);
    input!.value = '';
    setParams((params) => { params.delete('q'); params.delete('cat'); });
    showDefault();
    const returnTo = lastSeeAll && lastSeeAll.isConnected ? lastSeeAll : null;
    lastSeeAll = null;
    if (returnTo) returnTo.focus();
    else root!.scrollIntoView({ block: 'start' });
  });

  const params = new URLSearchParams(window.location.search);
  const initialQuery = (params.get('q') || '').trim();
  const initialField = params.get('cat') || '';
  if (initialQuery) {
    input.value = initialQuery;
    showSearch(initialQuery.toLowerCase());
  } else if (initialField && fieldIds.has(initialField)) {
    showField(initialField);
  }
}

document.addEventListener('astro:page-load', initProductCatalog);
initProductCatalog();
```

- [ ] **Step 7: KO 목록 페이지** — `frontend/src/pages/ko/products/index.astro`를 Read한 뒤 Write로 통째 교체한다.

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { getProductsPageData } from '../../../lib/pageData/productsPage';
import { catalogSections, jumpLabel } from '../../../lib/productCatalog.js';
import ProductSearchBar from '../../../components/products/ProductSearchBar.astro';
import ProductPicks from '../../../components/products/ProductPicks.astro';
import ProductCatalogSection from '../../../components/products/ProductCatalogSection.astro';

const locale = 'ko';
const { categories, allProducts, productsByCategory, picks, error } = await getProductsPageData(locale);
if (error) Astro.response.status = 503;

// Fixed field order. Fields missing from this list follow in DB sort_order; empty fields are skipped.
const CATEGORY_ORDER = [
  'assistant', 'image', 'video',
  'audio', 'coding', 'workflow',
  'builder', 'platform', 'research',
  'community',
];
const sections = catalogSections(categories, productsByCategory, CATEGORY_ORDER, locale);
const shownCount = sections.reduce((sum, section) => sum + section.products.length, 0);

const pricingKo: Record<string, string> = { free: '무료', freemium: '무료 프리미엄', paid: '유료', enterprise: '기업용' };
const categoryKo: Record<string, string> = { assistant: '어시스턴트 챗봇', image: '이미지 디자인', video: '영상 비디오', audio: '오디오 음악 음성', coding: '코딩 개발 IDE', workflow: '자동화 워크플로우', builder: '앱빌더 노코드', platform: '플랫폼 API', research: '리서치 논문', community: '커뮤니티' };

const buildSearchText = (product: typeof allProducts[0]) =>
  [
    product.name,
    (product as any).name_ko,
    product.tagline,
    (product as any).tagline_ko,
    product.pricing,
    product.pricing ? pricingKo[product.pricing] : null,
    product.primary_category,
    categoryKo[product.primary_category],
    ...(product.platform ?? []),
    ...(product.tags ?? []),
    ...((product as any).tags_ko ?? []),
    ...((product as any).display_tags ?? []),
  ].filter(Boolean).join(' ').toLowerCase();

const searchTexts = Object.fromEntries(allProducts.map((product) => [product.id, buildSearchText(product)]));
---

<MainLayout
  title={t.ko['products.title']}
  description={t.ko['products.heroSubtitle']}
  locale={locale}
  slug="products/"
>
  <div class="products-page product-catalog" id="products-top" data-also-label="다른 분야에서 함께 쓰이는 도구 {k}개">
    {error && <p class="products-error">{t.ko['products.error']}</p>}

    <header class="product-catalog-head">
      <div>
        <h1 class="product-catalog-title">{t.ko['products.title']}</h1>
        <p class="product-catalog-sub">AI 도구 {shownCount}개 · {sections.length}개 분야</p>
      </div>
      <ProductSearchBar locale={locale} />
    </header>

    <button type="button" class="product-catalog-back" hidden>← 모든 분야</button>

    {sections.length > 0 && (
      <nav class="product-catalog-jump" aria-label="분야 바로가기">
        <ul class="product-catalog-jump-list">
          {sections.map((section) => (
            <li>
              <a href={`#cat-${section.category.id}`}>
                {jumpLabel(locale, section.category.id, section.category.label_ko)}
                <span class="product-catalog-jump-count">{section.products.length}</span>
              </a>
            </li>
          ))}
        </ul>
      </nav>
    )}

    <ProductPicks picks={picks} locale={locale} />

    {sections.map((section) => (
      <ProductCatalogSection section={section} locale={locale} searchTexts={searchTexts} />
    ))}

    <p id="product-search-no-results" class="products-search-no-results" hidden>
      {t.ko['products.searchNoResults']}
    </p>

    {allProducts.length === 0 && !error && (
      <p class="products-empty">{t.ko['products.empty']}</p>
    )}

    <section class="product-outro">
      <h2 class="product-outro-title">{t.ko['products.outroTitle']}</h2>
      <p class="product-outro-body">{t.ko['products.outroBody']}</p>
    </section>

    <p class="products-trademark-disclaimer">
      제품명, 로고 및 상표는 각 소유자의 자산입니다. 별도 표기가 없는 한, 0to1log는 나열된 회사와 제휴, 보증 또는 후원 관계가 없습니다.
    </p>
  </div>
</MainLayout>

<script>
  import '../../../scripts/handbookSearchHints';
  import '../../../scripts/productCatalog';
</script>
```

- [ ] **Step 8: EN 목록 페이지** — `frontend/src/pages/en/products/index.astro`를 Read한 뒤 Write로 통째 교체한다(`buildSearchText`는 현행처럼 ko와 같다).

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { getProductsPageData } from '../../../lib/pageData/productsPage';
import { catalogSections, jumpLabel } from '../../../lib/productCatalog.js';
import ProductSearchBar from '../../../components/products/ProductSearchBar.astro';
import ProductPicks from '../../../components/products/ProductPicks.astro';
import ProductCatalogSection from '../../../components/products/ProductCatalogSection.astro';

const locale = 'en';
const { categories, allProducts, productsByCategory, picks, error } = await getProductsPageData(locale);
if (error) Astro.response.status = 503;

// Fixed field order. Fields missing from this list follow in DB sort_order; empty fields are skipped.
const CATEGORY_ORDER = [
  'assistant', 'image', 'video',
  'audio', 'coding', 'workflow',
  'builder', 'platform', 'research',
  'community',
];
const sections = catalogSections(categories, productsByCategory, CATEGORY_ORDER, locale);
const shownCount = sections.reduce((sum, section) => sum + section.products.length, 0);

const pricingKo: Record<string, string> = { free: '무료', freemium: '무료 프리미엄', paid: '유료', enterprise: '기업용' };
const categoryKo: Record<string, string> = { assistant: '어시스턴트 챗봇', image: '이미지 디자인', video: '영상 비디오', audio: '오디오 음악 음성', coding: '코딩 개발 IDE', workflow: '자동화 워크플로우', builder: '앱빌더 노코드', platform: '플랫폼 API', research: '리서치 논문', community: '커뮤니티' };

const buildSearchText = (product: typeof allProducts[0]) =>
  [
    product.name,
    (product as any).name_ko,
    product.tagline,
    (product as any).tagline_ko,
    product.pricing,
    product.pricing ? pricingKo[product.pricing] : null,
    product.primary_category,
    categoryKo[product.primary_category],
    ...(product.platform ?? []),
    ...(product.tags ?? []),
    ...((product as any).tags_ko ?? []),
    ...((product as any).display_tags ?? []),
  ].filter(Boolean).join(' ').toLowerCase();

const searchTexts = Object.fromEntries(allProducts.map((product) => [product.id, buildSearchText(product)]));
---

<MainLayout
  title={t.en['products.title']}
  description={t.en['products.heroSubtitle']}
  locale={locale}
  slug="products/"
>
  <div class="products-page product-catalog" id="products-top" data-also-label="Also used for this ({k})">
    {error && <p class="products-error">{t.en['products.error']}</p>}

    <header class="product-catalog-head">
      <div>
        <h1 class="product-catalog-title">{t.en['products.title']}</h1>
        <p class="product-catalog-sub">{shownCount} AI tools · {sections.length} fields</p>
      </div>
      <ProductSearchBar locale={locale} />
    </header>

    <button type="button" class="product-catalog-back" hidden>← All fields</button>

    {sections.length > 0 && (
      <nav class="product-catalog-jump" aria-label="Jump to field">
        <ul class="product-catalog-jump-list">
          {sections.map((section) => (
            <li>
              <a href={`#cat-${section.category.id}`}>
                {jumpLabel(locale, section.category.id, section.category.label_en)}
                <span class="product-catalog-jump-count">{section.products.length}</span>
              </a>
            </li>
          ))}
        </ul>
      </nav>
    )}

    <ProductPicks picks={picks} locale={locale} />

    {sections.map((section) => (
      <ProductCatalogSection section={section} locale={locale} searchTexts={searchTexts} />
    ))}

    <p id="product-search-no-results" class="products-search-no-results" hidden>
      {t.en['products.searchNoResults']}
    </p>

    {allProducts.length === 0 && !error && (
      <p class="products-empty">{t.en['products.empty']}</p>
    )}

    <section class="product-outro">
      <h2 class="product-outro-title">{t.en['products.outroTitle']}</h2>
      <p class="product-outro-body">{t.en['products.outroBody']}</p>
    </section>

    <p class="products-trademark-disclaimer">
      Product names, logos, and trademarks are the property of their respective owners. Unless otherwise indicated, 0to1log is not affiliated with, endorsed by, or sponsored by any of the companies listed.
    </p>
  </div>
</MainLayout>

<script>
  import '../../../scripts/handbookSearchHints';
  import '../../../scripts/productCatalog';
</script>
```

- [ ] **Step 9: 제품 상세의 난이도 표** — `frontend/src/components/products/ProductDetail.astro`(CRLF)를 **Edit 도구로** 2곳 고친다.

1번 old:
```astro
import ProductCard from './ProductCard.astro';
```
1번 new:
```astro
import ProductCard from './ProductCard.astro';
import { DIFFICULTY_LABELS } from '../../lib/productCatalog.js';
```

2번 old:
```astro
const difficultyLabels: Record<string, { en: string; ko: string }> = {
  beginner: { en: 'Beginner-friendly', ko: '초보자 OK' },
  intermediate: { en: 'Some setup needed', ko: '약간의 설정 필요' },
  advanced: { en: 'Technical setup', ko: '기술 설정 필요' },
};
```
2번 new:
```astro
const difficultyLabels: Record<string, { en: string; ko: string }> = DIFFICULTY_LABELS;
```

(쓰는 줄 `{difficultyLabels[product.difficulty]?.[locale] ?? product.difficulty}`는 그대로다.)

- [ ] **Step 10: CSS 추가** — `frontend/src/styles/global.css`를 Edit 도구로 고친다. 파일에 한 번만 있는 주석 줄 앞에 카탈로그 블록을 넣는다.

old:
```css
/* --- Handbook category preview --- */
```
new:
```css
/* --- Products catalog (A: fields) --- */
.products-page.product-catalog {
  max-width: 1072px;
  padding: 0 1rem;
}

.product-catalog-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem 2rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--color-text-primary);
}

.product-catalog-title {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 2.1rem;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.05em;
  color: var(--color-text-primary);
}

.product-catalog-sub {
  margin: 0.3rem 0 0;
  font-family: var(--font-ui);
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

.product-catalog-head .product-filter-search {
  flex: 0 1 320px;
  max-width: 320px;
  margin: 0;
  padding: 0;
}

.product-catalog-back {
  display: inline-flex;
  align-items: center;
  margin-top: 0.9rem;
  padding: 0.3rem 0;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-accent);
  background: none;
  border: none;
  cursor: pointer;
}

.product-catalog-back:hover {
  text-decoration: underline;
}

.product-catalog-back[hidden],
.product-cat-all[hidden] {
  display: none;
}

.product-catalog-jump {
  border-bottom: 1px solid var(--color-border);
}

.product-catalog-jump-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1.1rem;
  margin: 0;
  padding: 0.6rem 0;
  list-style: none;
}

.product-catalog-jump-list a {
  font-family: var(--font-ui);
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--color-text-primary);
  text-decoration: none;
}

.product-catalog-jump-list a:hover {
  color: var(--color-accent);
}

.product-catalog-jump-count {
  margin-left: 0.25rem;
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
  font-weight: 500;
  color: var(--color-text-muted);
}

.product-catalog-logo {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  overflow: hidden;
  border-radius: 7px;
  background: var(--color-bg-secondary);
}

.product-catalog-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.product-catalog-logo-initial {
  font-family: var(--font-heading);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-text-muted);
}

/* Editor's picks: 5 columns ≥1024px, 3 columns 768–1023px, sideways cards on phones */
.product-picks {
  margin-top: 0.9rem;
  border-bottom: 1px solid var(--color-text-primary);
}

.product-picks-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin: 0;
  padding: 0;
  list-style: none;
}

.product-picks-list > li {
  min-width: 0;
  border-right: 1px dotted var(--color-border);
}

.product-picks-list > li:last-child {
  border-right: 0;
}

.product-pick {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  height: 100%;
  padding: 0.25rem 0.9rem 0.9rem;
  color: inherit;
  text-decoration: none;
}

.product-picks-list > li:first-child .product-pick {
  padding-left: 0;
}

.product-pick-label {
  font-family: var(--font-ui);
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-accent);
}

.product-pick-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  font-family: var(--font-heading);
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--color-text-primary);
}

.product-pick-name .product-catalog-logo {
  width: 28px;
  height: 28px;
}

.product-pick:hover .product-pick-name {
  color: var(--color-accent);
}

.product-pick-line {
  font-size: 0.8rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

/* Field sections: 3 columns ≥1024px, 2 columns 768–1023px, 1 column on phones */
.product-cat {
  margin-top: 1.6rem;
  scroll-margin-top: calc(var(--header-h, 4rem) + 1rem);
}

.product-cat-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.25rem 1rem;
  padding-top: 0.5rem;
  border-top: 2px solid var(--color-text-primary);
}

.product-cat-title {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--color-text-primary);
}

.product-cat-title:focus:not(:focus-visible) {
  outline: none;
}

.product-cat-count {
  margin-left: 0.5rem;
  font-family: var(--font-ui);
  font-size: 0.8rem;
  font-weight: 400;
  letter-spacing: 0;
  color: var(--color-text-muted);
}

.product-cat-all {
  flex: 0 0 auto;
  padding: 0.2rem 0;
  font-family: var(--font-ui);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-accent);
  background: none;
  border: none;
  cursor: pointer;
}

.product-cat-all:hover {
  text-decoration: underline;
}

.product-cat-lede,
.product-cat-desc {
  margin: 0.3rem 0 0;
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.product-cat-desc {
  max-width: 46rem;
}

.product-cat-list,
.product-cat-also-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  column-gap: 1.6rem;
  margin: 0.2rem 0 0;
  padding: 0;
  list-style: none;
}

.product-cat-list > [data-overflow] {
  display: none;
}

.product-cat[data-expanded] .product-cat-list > [data-overflow]:not([hidden]) {
  display: block;
}

.product-row {
  min-width: 0;
  border-bottom: 1px dotted var(--color-border);
}

.product-row > a {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 0.65rem;
  padding: 0.65rem 0;
  color: inherit;
  text-decoration: none;
}

.product-row-text {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.product-row-name {
  font-family: var(--font-heading);
  font-size: 0.92rem;
  font-weight: 600;
  letter-spacing: -0.025em;
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
}

.product-row > a:hover .product-row-name {
  color: var(--color-accent);
}

.product-row-tagline {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.product-row-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.75rem;
  margin-top: 0.1rem;
}

.product-cat-also {
  margin-top: 1.4rem;
}

.product-cat-also-title {
  margin: 0;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border);
  font-family: var(--font-heading);
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--color-text-primary);
}

@media (min-width: 768px) and (max-width: 1023px) {
  .product-picks-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    row-gap: 0.5rem;
  }

  .product-picks-list > li:nth-child(3n) {
    border-right: 0;
  }

  .product-picks-list > li:nth-child(3n + 1) .product-pick {
    padding-left: 0;
  }

  .product-cat-list,
  .product-cat-also-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* Products catalog: mobile */
@media (max-width: 767px) {
  .products-page.product-catalog {
    padding: 0 0.25rem;
  }

  .product-catalog-head {
    flex-direction: column;
    align-items: stretch;
  }

  .product-catalog-title {
    font-size: 1.7rem;
  }

  .product-catalog-head .product-filter-search {
    flex: none;
    width: 100%;
    max-width: none;
  }

  .product-catalog-jump-list {
    flex-wrap: nowrap;
    gap: 1rem;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scrollbar-width: none;
  }

  .product-catalog-jump-list::-webkit-scrollbar {
    display: none;
  }

  .product-picks-list {
    display: flex;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scroll-snap-type: x mandatory;
    scrollbar-width: none;
  }

  .product-picks-list::-webkit-scrollbar {
    display: none;
  }

  .product-picks-list > li {
    flex: 0 0 78%;
    scroll-snap-align: start;
  }

  .product-cat-list,
  .product-cat-also-list {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* --- Handbook category preview --- */
```

- [ ] **Step 11: 기존 테스트 갱신** (Edit 도구로)

`frontend/tests/products-v2.test.cjs` old:
```js
// Cards: no lift on hover, filter bar without shadow
assert(!rules('.product-card:hover').some((r) => /transform/.test(r)), 'product card does not lift on hover');
assert(!/border-radius|box-shadow/.test(rule('.product-card')), 'product card is not a boxed card');
assert(!/box-shadow/.test(rule('.product-filter-bar')), 'filter bar has no shadow');

// Mobile: tiles don't scroll inside the page; a "see all" button opens the category
const tile = fs.readFileSync(path.join(__dirname, '..', 'src', 'components', 'products', 'ProductCategoryTile.astro'), 'utf8');
assert(tile.includes('class="product-cat-tile-more"') && tile.includes('data-category={categoryId}'), 'tile has a see-all button');
assert(/\.product-cat-tile\s*\{\s*height:\s*auto;/.test(css), 'phone tiles are not fixed height');
assert(/\.product-cat-row:nth-child\(n \+ 5\)\s*\{\s*display:\s*none;/.test(css), 'phone tiles show the first four rows');
for (const loc of ['ko', 'en']) {
  const page = fs.readFileSync(path.join(__dirname, '..', 'src', 'pages', loc, 'products', 'index.astro'), 'utf8');
  assert(page.includes("'.product-cat-tile-header, .product-cat-tile-more'"), `${loc}: see-all shares the header click handler`);
}
assert(!/border-bottom/.test(rule('.product-filter-bar')), 'no rule under the search bar (tiles carry their own top rule)');
```
new:
```js
// Cards: no lift on hover
assert(!rules('.product-card:hover').some((r) => /transform/.test(r)), 'product card does not lift on hover');
assert(!/border-radius|box-shadow/.test(rule('.product-card')), 'product card is not a boxed card');
```

`frontend/tests/public-list-query-budget.test.cjs` old:
```js
  assert.match(productsPage, /demoMediaFirst/, `${locale} product cards must preserve rendered demo image fallback`);
```
new:
```js
  assert.doesNotMatch(productsPage, /demoMediaFirst|demo_media/, `${locale} catalog rows render logos only (no demo images on the list)`);
```

- [ ] **Step 12: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/products-catalog.test.cjs
node frontend/tests/product-catalog.test.mjs
node frontend/tests/products-v2.test.cjs
node frontend/tests/public-list-query-budget.test.cjs
node frontend/tests/product-detail-search-sticky.test.cjs
node frontend/tests/product-filter-bar-mobile-sticky.test.cjs
node frontend/tests/public-error-cache-policy.test.cjs
node frontend/tests/public-detail-query-contract.test.cjs
node frontend/tests/product-detail-admin-actions.test.cjs
node frontend/tests/product-auth-prompt-copy.test.cjs
node frontend/tests/handbook-index-shelves.test.cjs
node frontend/tests/product-detail-scenarios-theme.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 테스트를 뺀 모두 PASS(`product-filter-bar-mobile-sticky`·`product-detail-search-sticky`는 지울 CSS·파일이 아직 있어서 통과한다), 빌드 "Complete!".
- `product-detail-scenarios-theme` "Scenario cards should use the theme background surface instead of a hard white fill" — 기준선과 **같은 메시지**.

- [ ] **Step 13: 커밋**

```bash
git add frontend/src/lib/pageData/productsPage.ts frontend/src/components/products/ProductPicks.astro frontend/src/components/products/ProductCatalogSection.astro frontend/src/components/products/ProductDetail.astro frontend/src/scripts/productCatalog.ts frontend/src/pages/ko/products/index.astro frontend/src/pages/en/products/index.astro frontend/src/styles/global.css frontend/tests/products-catalog.test.cjs frontend/tests/products-v2.test.cjs frontend/tests/public-list-query-budget.test.cjs
git commit -m "feat: products list as a field catalog with editor's picks"
```

---

## Task 3: 타일·필터 바·스포트라이트와 옛 CSS·i18n 정리 (TDD)

**Files:**
- Delete: `frontend/src/components/products/ProductCategoryTile.astro`, `frontend/src/components/products/ProductFilterBar.astro`, `frontend/src/components/products/ProductSpotlight.astro`, `frontend/src/lib/productCategoryIcons.ts`, `frontend/tests/product-filter-bar-mobile-sticky.test.cjs`
- Modify: `frontend/src/styles/global.css`(삭제 스크립트), `frontend/src/i18n/index.ts`(Edit 4곳)
- Test: `frontend/tests/products-catalog.test.cjs`(Edit 1곳: 삭제 단언), `frontend/tests/product-detail-search-sticky.test.cjs`(Edit 1곳)

- [ ] **Step 0: 상태 확인**

Run: `git status --short -- frontend/src/components/products frontend/src/lib/productCategoryIcons.ts frontend/src/styles/global.css frontend/src/i18n/index.ts frontend/tests/products-catalog.test.cjs frontend/tests/product-detail-search-sticky.test.cjs frontend/tests/product-filter-bar-mobile-sticky.test.cjs`
Expected: 출력 없음(Task 2 커밋 후).

- [ ] **Step 1: 실패하는 단언 추가** — `frontend/tests/products-catalog.test.cjs`의 마지막 줄 `console.log('products-catalog.test.cjs passed');` **바로 위**에 아래 블록을 Edit 도구로 넣는다(블록 끝과 `console.log` 사이 빈 줄 한 줄).

```js
// old list pieces are gone (Task 3)
for (const gone of ['components/products/ProductCategoryTile.astro', 'components/products/ProductFilterBar.astro', 'components/products/ProductSpotlight.astro', 'lib/productCategoryIcons.ts']) {
  assert(!fs.existsSync(path.join(src, gone)), `deleted: ${gone}`);
}
for (const gone of ['.product-category-grid', '.product-category-preview', '.product-category-see-all', '.product-cat-tile', '.product-cat-row', '.product-cat-tag', '.products-back-all', '.product-filter-bar', '.product-filter-tab', '.product-outro-cta']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(css.includes('.product-filter-search {') && css.includes('.product-pricing-badge,') && css.includes('.product-card {'), 'shared product styles stay');
const i18n = read('i18n/index.ts');
for (const key of ['products.categoryAll', 'products.heroTitle', 'products.outroCta']) {
  assert(!i18n.includes(`'${key}'`), `unused i18n key removed: ${key}`);
}
assert(i18n.includes("'products.heroSubtitle'") && i18n.includes("'products.outroTitle'"), 'used product keys stay');

```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/products-catalog.test.cjs`
Expected: FAIL — `AssertionError [ERR_ASSERTION]: deleted: components/products/ProductCategoryTile.astro`

- [ ] **Step 3: 사용처가 없음을 확인**

Run:
```bash
grep -rn "ProductCategoryTile\|ProductFilterBar\|ProductSpotlight\|productCategoryIcons\|getCategoryIcon" frontend/src frontend/tests
grep -rn "product-category-grid\|product-category-preview\|product-category-see-all\|product-cat-tile\|product-cat-row\|product-cat-tag\|products-back-all\|product-filter-bar\|product-filter-tab\|product-outro-cta" frontend/src --include=*.astro --include=*.ts --include=*.js
grep -rn "products\.heroTitle\|products\.categoryAll\|products\.outroCta" frontend/src
grep -rn 'products\.\${' frontend/src
```
Expected:
- 첫 줄: 지울 파일 자신(`ProductCategoryTile.astro`의 `getCategoryIcon` import, `productCategoryIcons.ts`의 정의)과 테스트 `products-catalog.test.cjs`(부재 단언), `product-detail-search-sticky.test.cjs` 58–65행, `products-v2.test.cjs` 18행(`.product-spotlight` CSS 부재 문구)뿐. 페이지·다른 컴포넌트 결과 없음.
- 둘째 줄: `ProductCategoryTile.astro`, `ProductFilterBar.astro` 안의 결과뿐.
- 셋째 줄: `frontend/src/i18n/index.ts`의 정의 6줄뿐.
- 넷째 줄: `ProductCatalogSection.astro`의 ``tr[`products.${value}`]``(가격 라벨: free/freemium/paid/enterprise) 한 줄뿐 — 지울 키와 무관.
- 하나라도 다르면 멈추고 보고한다.

- [ ] **Step 4: 파일 삭제**

```bash
git rm frontend/src/components/products/ProductCategoryTile.astro frontend/src/components/products/ProductFilterBar.astro frontend/src/components/products/ProductSpotlight.astro frontend/src/lib/productCategoryIcons.ts frontend/tests/product-filter-bar-mobile-sticky.test.cjs
```

- [ ] **Step 5: `product-detail-search-sticky.test.cjs`에서 필터 바 단언 삭제** (Edit 도구로)

old:
```js
const filterBar = read('src/components/products/ProductFilterBar.astro');
assert(
  filterBar.includes("import ProductSearchBar from './ProductSearchBar.astro';"),
  'ProductFilterBar should reuse the shared ProductSearchBar component',
);
assert(
  filterBar.includes('<ProductSearchBar locale={locale} />'),
  'ProductFilterBar should render the extracted ProductSearchBar',
);

[
```
new:
```js
[
```

- [ ] **Step 6: 안 쓰는 i18n 키 삭제** — `frontend/src/i18n/index.ts`(CRLF)를 **Edit 도구로** 4곳 고친다.

1번(en) old:
```ts
    'products.title': 'AI Products',
    'products.heroTitle': 'The AI Era: Make Anything',
    'products.heroSubtitle': 'Tools that were once exclusive to experts are now available to everyone.',
    'products.categoryAll': 'All',
```
1번 new:
```ts
    'products.title': 'AI Products',
    'products.heroSubtitle': 'Tools that were once exclusive to experts are now available to everyone.',
```

2번(en) old:
```ts
    'products.outroCta': 'Browse by category to find the right tool for you.',
    'cookie.message': '🍪 We use cookies to improve your experience.',
```
2번 new:
```ts
    'cookie.message': '🍪 We use cookies to improve your experience.',
```

3번(ko) old:
```ts
    'products.title': 'AI 제품군',
    'products.heroTitle': '떠오르는 모든 상상을, AI로 제작',
    'products.heroSubtitle': '창작 · 업무 · 개발 · 디자인 · 모든 작업을 AI로',
    'products.categoryAll': '전체',
```
3번 new:
```ts
    'products.title': 'AI 제품군',
    'products.heroSubtitle': '창작 · 업무 · 개발 · 디자인 · 모든 작업을 AI로',
```

4번(ko) old:
```ts
    'products.outroCta': '카테고리를 둘러보며 나에게 맞는 도구를 찾아보세요.',
    'cookie.message': '🍪 사용자 경험 개선을 위해 쿠키를 사용합니다.',
```
4번 new:
```ts
    'cookie.message': '🍪 사용자 경험 개선을 위해 쿠키를 사용합니다.',
```

- [ ] **Step 7: 옛 목록 CSS 삭제**

1. Write 도구로 scratchpad에 `drop-products-css.cjs`를 아래 내용 그대로 만든다(repo 밖, 커밋하지 않음).

```js
// Removes the old products-list CSS (filter bar/tabs, category tiles, preview, back-all, outro CTA).
// Run from the repo root: node <scratchpad>/drop-products-css.cjs
const fs = require('fs');

const file = 'frontend/src/styles/global.css';
const lines = fs.readFileSync(file, 'utf8').split('\n');

// Remove lines [start, end) where start = first line equal to `from` (minus `before` lines above it)
// and end = first line equal to `to` after it (minus `keep` lines above it).
function cut(name, from, to, expected, { before = 0, keep = 0 } = {}) {
  const at = lines.indexOf(from);
  if (at < 0) throw new Error(`${name}: start not found: ${from}`);
  if (lines.indexOf(from, at + 1) >= 0) throw new Error(`${name}: start is not unique: ${from}`);
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

// 1. "Products Redesign" banner + sticky filter bar + filter tabs (base)
cut('filter bar + tabs', '   Products Redesign — Spotlight + FilterBar + Flat Grid', '.product-filter-search {', 78, { before: 1 });
// 2. filter tabs inside the 767px query (the query and .product-filter-search stay)
cut('mobile filter tabs', '  .product-filter-tabs {', '  .product-filter-search {', 21);
// 3. category preview + tile grid + back-all + tiles + rows + tags + see-all, incl. the 1024px / 560px queries
cut('category tiles', '/* --- Category Preview Section --- */', '@media (max-width: 360px) {', 321);
// 4. outro CTA line (i18n products.outroCta is removed too)
cut('outro cta', '.product-outro-cta {', '.products-trademark-disclaimer {', 7);

fs.writeFileSync(file, lines.join('\n'));
console.log('done');
```

2. repo 루트에서 `node <scratchpad>/drop-products-css.cjs` → 아래 출력(시작 줄 번호는 다른 세션 변경으로 달라질 수 있다. **줄 수**가 하나라도 다르면 스크립트가 아무것도 쓰지 않고 오류를 낸다 → 멈추고 보고):
```
filter bar + tabs: removed 78 lines from line 11873
mobile filter tabs: removed 21 lines from line 11909
category tiles: removed 321 lines from line 11934
outro cta: removed 7 lines from line 14437
done
```

- 지워지는 것: `Products Redesign — Spotlight + FilterBar + Flat Grid` 배너 주석 · `/* --- Filter Bar --- */` · `.product-filter-bar` · `.product-filter-tabs` · `.product-filter-tab`(+`:hover`·`.active`·`.active::after`·`-icon`·`-icon svg`), 767px 쿼리 안 `.product-filter-tabs`·`::-webkit-scrollbar`·`.product-filter-tab`, `/* --- Category Preview Section --- */`부터 `.product-category-preview*` · `.product-category-see-all*` · `/* --- Product category grid … */` `.product-category-grid` · `.products-back-all*` · `.product-cat-tile*` · `.product-cat-row*` · `.product-cat-tag*` · `.product-cat-row .product-pricing-badge` · `.product-cat-tile-more` · 1024px/560px 쿼리, `.product-outro-cta`.
- 남는 것: `.products-page`, `.product-filter-search`(기본·767px 쿼리), `.product-detail-page`·`.product-detail-search*`, 767px 쿼리의 닫는 `}`, `@media (max-width: 360px) { .site-nav-pill … }`, 새 카탈로그 블록, `.product-outro`·`-title`·`-body`, `.products-trademark-disclaimer`.

Run:
```bash
grep -n "product-category-\|product-cat-tile\|product-cat-row\|product-cat-tag\|products-back-all\|product-filter-bar\|product-filter-tab\|product-outro-cta" frontend/src/styles/global.css
grep -n "^\.product-filter-search {\|^  \.product-filter-search {\|^@media (max-width: 360px) {" frontend/src/styles/global.css
```
Expected: 첫 줄 결과 없음. 둘째 줄 3줄(`.product-filter-search {` 기본, 767px 쿼리 안, 360px 쿼리).

- [ ] **Step 8: 통과 확인**

Run (repo 루트):
```bash
node frontend/tests/products-catalog.test.cjs
node frontend/tests/product-catalog.test.mjs
node frontend/tests/product-detail-search-sticky.test.cjs
node frontend/tests/products-v2.test.cjs
node frontend/tests/public-list-query-budget.test.cjs
node frontend/tests/handbook-index-shelves.test.cjs
node frontend/tests/public-error-cache-policy.test.cjs
node frontend/tests/product-detail-admin-actions.test.cjs
node frontend/tests/product-detail-scenarios-theme.test.cjs
cd frontend && npm run build
```
Expected:
- 마지막 테스트를 뺀 모두 PASS, 빌드 "Complete!".
- `product-detail-scenarios-theme` 기준선과 **같은 메시지**.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/styles/global.css frontend/src/i18n/index.ts frontend/tests/products-catalog.test.cjs frontend/tests/product-detail-search-sticky.test.cjs
git commit -m "chore: remove product tiles, filter bar, spotlight and old list CSS"
```

(`git rm`으로 stage된 파일 5개 삭제가 함께 커밋된다.)

---

## Task 4: 검증 (컨트롤러)

- [ ] 전체 테스트를 **이름 + 첫 오류 메시지로** 기준선(PASS 82 / FAIL 19)과 비교한다.
  ```bash
  for f in frontend/tests/*.cjs frontend/tests/*.mjs; do node "$f" >/dev/null 2>&1 && echo "PASS $(basename $f)" || echo "FAIL $(basename $f)"; done
  ```
  - 실패 목록은 기준선 19개와 같아야 한다(신규 FAIL 0). 실패 테스트의 첫 오류 메시지도 기준선과 같은지 본다(`node <file> 2>&1 | grep -m1 -E "^[A-Za-z]*Error( \[[A-Z_]+\])?: "`).
  - 이름 변화는 `product-catalog`·`products-catalog` 신규 PASS, `product-filter-bar-mobile-sticky` 삭제뿐 → **PASS 83 / FAIL 19**.
- [ ] `cd frontend && npm run build` "Complete!".
- [ ] 브라우저(`.claude/launch.json`의 `frontend-dev`, 포트 4321) 매트릭스: 종이·순백·다크 × 1100px·900px·375px × ko/en
  - 스크린샷(테마·폭·locale마다), 가로 넘침 0(`document.documentElement.scrollWidth <= window.innerWidth`)
  - 대비 검사: 부제(muted), 바로가기 개수(muted), 추천 라벨(accent)·한 줄(secondary), 분야 개수(muted)·첫 문장(secondary)·"모두 보기"(accent), 줄 한 줄 설명(secondary), 가격·난이도 칩, 돌아가기(accent), 다크 포함
  - ≥1024px: 추천 5열(점선 구분), 목록 3열. 768–1023px: 추천 3열 줄바꿈, 목록 2열. ≤767px: 제목 줄 세로·검색 전체 폭, `h1` 약 1.7rem, 바로가기·추천 가로 스크롤(추천 스냅), 목록 1열, 좌우 16px.
- [ ] 직접 클릭
  - 바로가기 앵커(헤더에 가리지 않음, 고정 헤더가 보이는 상태 포함), 추천 칸 → 상세.
  - "28개 모두 보기"(어시스턴트: 28줄 + "다른 분야에서 함께 쓰이는 도구 14개", 포커스가 섹션 제목) → 돌아가기(포커스가 그 버튼으로), `?cat=coding` 직접 진입, `?cat=없는값`은 기본 모드.
  - 검색 "이미지", "chatgpt", 결과 없음, 지우기, Enter(검색어 있음·없음) 새로고침 없음, `?q=claude` 직접 진입.
  - 다른 페이지 → 목록(ClientRouter 이동) 뒤 모드가 한 번만 묶이는지(모두 보기 한 번 클릭에 복제 줄이 중복되지 않음).
  - 줄 → 제품 상세 링크.
- [ ] 회귀: 제품 상세(난이도 라벨 ko/en, sticky 검색, 빈 검색어 Enter → 목록 이동은 상세에서만), 서재 `library`의 제품 카드, 홈의 제품 카드(가격 점 칩).
- [ ] 발견한 문제는 `fix:` 커밋으로 남긴다.

## Task 5: 문서

- [ ] 스펙 [[2026-10-18-products-catalog-design]] Status를 `implemented (YYYY-MM-DD)`로 바꾼다.
- [ ] 이 계획의 Status를 `done (YYYY-MM-DD)`로 바꾸고, 문서 끝에 "## 실행 결과 (YYYY-MM-DD)"(커밋 해시, 테스트 이름 비교 결과, 빌드, 매트릭스 결과, 계획 대비 변경, 후속)를 적는다.
- [ ] `ACTIVE_SPRINT.md`의 `REDESIGN-BLOG-POST` 항목 **바로 다음 줄**에 추가한다.
  `- [x] **REDESIGN-PRODUCTS** — AI 제품군 목록을 분야 카탈로그(A)로: 가운데 한 단, h1 + 제품·분야 수 + 검색, 분야 바로가기, 편집자 추천 5칸(편집자 노트 첫 문장), 분야 섹션(3열 6줄 + 모두 보기, 타일 안 스크롤 제거), ?cat= 분야 모드(함께 쓰이는 도구), ?q= 검색(한 번 렌더한 줄만 보이기·숨기기, 중복 렌더 제거), 난이도 라벨 공용화, 타일·필터 바·스포트라이트 삭제 — [[2026-10-18-products-catalog-design]], [[2026-10-18-products-catalog]]`
- [ ] `grep -rln "ProductCategoryTile\|ProductFilterBar\|product-cat-tile\|productCategoryIcons\|filtered-grid" vault --include=*.md`로 관련 노트를 찾는다. `90-Archive/`와 이번 스펙·계획, 지난 날짜의 완료된 계획 본문은 빼고, 제품 목록의 **현재 구조**를 설명하는 노트만 최소한으로 고친다(예: `2026-10-15-site-redesign-phase8a-products.md`가 아직 `plans/`에 있으면 "목록은 2026-10-18 분야 카탈로그(A)로 대체" 한 줄).
- [ ] 알려진 한계·후속을 실행 결과에 적는다: 인기순·최신순 없음(조회·출시일 데이터 없음), 가격 미입력 66개(가격 칩 없음), 한국어 지원 4개, EN 추천 칸은 영어 노트만 써서 긴 첫 문장이 "…"로 잘림, 분야 설명은 locale 열만 사용.
- [ ] 커밋(고친 vault 노트 경로만 지정해 add한다. `vault/.obsidian/*`는 넣지 않는다):
  ```bash
  git add vault/09-Implementation/plans/2026-10-18-products-catalog-design.md vault/09-Implementation/plans/2026-10-18-products-catalog.md vault/09-Implementation/plans/ACTIVE_SPRINT.md
  git commit -m "docs: record products catalog redesign"
  ```
  (Task 5에서 고친 다른 vault 노트가 있으면 그 경로도 `git add`에 더한다.)
