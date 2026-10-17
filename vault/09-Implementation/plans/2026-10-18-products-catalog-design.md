# AI 제품군 목록 재설계 (A 분야 카탈로그) — Design Spec

**Status:** approved (2026-10-18)
**Mockup:** `.superpowers/brainstorm/products/products-v1.html` (A안)
**관련:** [[2026-10-16-news-list-desks-design]], [[2026-10-17-handbook-index-shelves-design]]

## 배경

- 제품 목록(`/ko/products/`, `/en/products/`)은 분야 타일 10개가 3열 격자에 놓이고, **타일마다 안에서 스크롤**된다. 한 화면에 분야당 4개만 보이고 페이지 스크롤과 겹친다.
- 같은 제품 123개를 타일용과 검색용(`#filtered-grid`의 `ProductCard`)으로 **두 번 렌더**한다.
- 페이지에 `h1`이 없다.
- 데이터(2026-10-17 운영 확인): 발행 123개, 분야 10개. `view_count`·`like_count` 전부 0, `released_at` 전부 null → 인기순·최신순 불가. `difficulty` 114개(beginner 44·intermediate 66·advanced 4), `editor_note_ko` 114개, `featured` 5개, `pricing` 57개(free 6·freemium 37·paid 14), 보조 분야가 있는 제품 82개, 로고 없는 제품 0개.
- 컬럼은 모두 존재한다(마이그레이션 00018: 분야 `description_ko/en`, `featured`, `featured_order` / 00029: `difficulty`, `editor_note(_ko)`). anon이 두 테이블을 읽을 수 있다.
- `getProductsPageData`의 호출처는 두 목록 페이지뿐이다.
- 시안 A(분야 카탈로그) / B(하고 싶은 일) / C(편집자 추천 데스크) 중 **A**를 골랐다(2026-10-18).

## 화면 구성 (가운데 한 단, 최대 약 1040px)

루트 `div.products-page#products-top`(현행 유지, 스크립트 바인딩 표시도 이 요소에 둔다).

1. **제목 줄** `header.product-catalog-head`: 아래 2px 먹선, 양 끝 정렬
   - 왼쪽: `h1` "AI 제품군" / "AI Products"(Hahmlet 700 약 2.1rem), 아래 줄 "AI 도구 {N}개 · {C}개 분야" / "{N} AI tools · {C} fields"
     - N = 렌더한 제품 수, C = 렌더한 분야 섹션 수
   - 오른쪽: 현행 `ProductSearchBar`(sticky=false, `#product-search`, 힌트 회전 유지). `ProductFilterBar` 래퍼는 쓰지 않는다.
   - 검색 폼 submit(Enter)은 목록 페이지에서 `preventDefault`한다(입력 이벤트로 이미 필터링 중이므로 새로고침하지 않는다). `ProductSearchBar`의 기존 submit 핸들러는 제품 상세용으로 그대로 둔다 — 목록 스크립트가 같은 폼에 submit 리스너를 하나 더 달아 막는다.
2. **분야 바로가기** `nav.product-catalog-jump`(aria-label "분야 바로가기" / "Jump to field"): 짧은 라벨 + 개수, 각각 `#cat-{id}` 앵커 링크. 아래 1px 선. 모바일은 한 줄 가로 스크롤(`overflow-x: auto`).
   - 짧은 라벨 표(분야 id 고정, 없는 id는 DB 라벨):
     - ko `{ assistant: '어시스턴트', image: '이미지', video: '영상', audio: '음성·음악', coding: '코딩', workflow: '워크플로우', builder: '앱 빌더', platform: '플랫폼', research: '리서치', community: '커뮤니티' }`
     - en `{ assistant: 'Assistants', image: 'Image', video: 'Video', audio: 'Audio', coding: 'Coding', workflow: 'Workflow', builder: 'App builders', platform: 'Platforms', research: 'Research', community: 'Community' }`
3. **편집자 추천** `section.product-picks`(aria-labelledby, 머리 `h2.sr-only` "편집자 추천" / "Editor's picks")
   - 대상: `featured = true`, `featured_order` 오름차순(null은 뒤) → 표시 이름순, 최대 5개. 0개면 렌더하지 않는다.
   - 칸 `a.product-pick`(상세 링크): 라벨 "편집자 추천 {n}" / "Pick {n}"(accent) + 로고(28px) + 표시 이름(Hahmlet 700) + 한 줄
     - 한 줄 = 편집자 노트 첫 문장. ko: `editor_note_ko || editor_note`, en: `editor_note`만(한국어 노트로 대체하지 않음, 상세 페이지와 같은 규칙). 노트가 없으면 locale 한 줄 설명(`tagline`).
   - 1024px 이상 5열(칸 사이 점선), 768~1023px 3열 줄바꿈, 모바일 가로 스크롤 카드(`scroll-snap`).
   - 아래 1px 먹선.
4. **분야 섹션** `section.product-cat#cat-{id}[data-category]` × 분야 수
   - 순서: 현행 `CATEGORY_ORDER`. 표에 없는 분야는 **뒤**에 DB `sort_order` 순으로 붙인다(현행 `indexOf = -1`이 앞으로 가는 문제 수정). 제품 0개 분야는 렌더하지 않는다.
   - `scroll-margin-top: calc(var(--header-h, 4rem) + 1rem)`(앵커 이동 시 고정 헤더에 가리지 않게).
   - 머리: 위 2px 먹선 + `h2.product-cat-title`(tabindex="-1") 분야 라벨(DB `label_ko/en`) + 개수 "{n}개" / "{n}" + 설명 첫 문장(`p.product-cat-lede`) + 오른쪽 버튼 "{n}개 모두 보기 →" / "See all {n} →"(`button.product-cat-all[data-category]`, n > 6일 때만)
   - 전체 설명 `p.product-cat-desc`(`hidden`, 모두 보기 모드에서만 보임). 설명이 없으면 둘 다 생략.
   - 목록 `ol.product-cat-list`: 1024px 이상 3열, 768~1023px 2열, 모바일 1열. 해당 분야(주 분야 기준)의 **모든 제품**을 렌더하고 7번째부터 `li`에 `data-overflow`를 단다. 숨김 CSS는 `.product-cat-list > [data-overflow]`로 범위를 한정한다.
   - 줄 `li.product-row`(`data-search-text`, `data-category`, `data-secondary-categories`) 안의 `a`(상세 링크):
     - 로고 `img`(30px, `loading="lazy"`, alt="") — `logo_url`이 없으면 첫 글자 네모(현행 대체 규칙)
     - 표시 이름(Hahmlet 600)
     - 한 줄 설명(`tagline`, 두 줄 clamp)
     - 메타 줄: 기존 `.product-pricing-badge[data-pricing]`(pricing 있을 때만) + 기존 `.product-difficulty-badge[data-difficulty]`(difficulty 있을 때만). 새 칩 CSS를 만들지 않는다.
   - 표시 이름: `name_original`(브랜드 원어 이름, 현행 타일과 같음). 정렬의 이름 비교는 데이터 계층 현행(locale 이름) 그대로.
   - 정렬: 데이터 계층 현행(추천 먼저 → `featured_order` → `sort_order` → 이름).
5. **맺음말** `section.product-outro`, **상표 고지**: 현행 그대로.

## 라벨

- 가격: 기존 i18n 키 `products.free` / `products.freemium` / `products.paid` / `products.enterprise`(ko: 무료 / Freemium / 유료 / 기업용, en: Free / Freemium / Paid / Enterprise).
- 난이도: 제품 상세의 라벨을 그대로 쓴다 — beginner "초보자 OK" / "Beginner-friendly", intermediate "약간의 설정 필요" / "Some setup needed", advanced "기술 설정 필요" / "Technical setup".
  - 표를 `lib/productCatalog.js`의 `DIFFICULTY_LABELS`로 옮기고 `ProductDetail.astro`도 이것을 import한다(한 곳에서 관리).
- 검색 텍스트(`buildSearchText`)는 현행 그대로(ko의 '무료 프리미엄' 포함).

## 모드 (클라이언트 스크립트, 한 번 렌더한 줄을 보이기·숨기기만)

- 초기화 때 원본 줄 목록(`.product-cat-list > li.product-row`)을 **한 번** 모아 배열로 들고 있는다. 이후 필터링은 이 배열만 대상으로 한다(복제 줄 제외).
- **기본**: 위 구성. 주소에 `cat`/`q` 없음.
- **분야 모두 보기** (`?cat={id}`)
  - 해당 섹션만 보이고 다른 섹션·추천·바로가기는 숨긴다. 섹션에 `data-expanded`를 달아 `data-overflow` 줄도 보이게 한다. 전체 설명을 보이고 첫 문장 줄과 "모두 보기" 버튼을 숨긴다.
  - 섹션 아래 `div.product-cat-also`(`hidden`)를 채운다: 머리 `h3` "다른 분야에서 함께 쓰이는 도구 {k}개" / "Also used for this ({k})" + `ol` — 원본 줄 중 다른 섹션에 있고 `data-secondary-categories`에 이 분야가 있는 줄을 `cloneNode(true)`로 복제해 넣는다. 복제본에서 `data-overflow`와 `hidden`을 지운다(복제본에 id는 없다). k = 0이면 숨긴 채 둔다. 모드를 나갈 때 비운다.
  - 맨 위 `button.product-catalog-back`(`hidden`) "← 모든 분야" / "← All fields"를 보인다.
  - 포커스: "모두 보기"를 누르면 그 섹션 `h2`로 포커스를 옮긴다. 돌아가기를 누르면 기본 모드로 돌리고, 직전에 누른 "모두 보기" 버튼(남아 있으면)으로 포커스를 돌린다.
  - `?cat=`이 렌더된 분야가 아니면 기본 모드로 둔다.
- **검색** (`?q=`)
  - 입력할 때마다(150ms 디바운스) 분야 모드를 해제(`cat` 제거)하고 추천·바로가기·`product-cat-also`를 숨긴다. 모든 섹션을 펼친 상태(`data-expanded`)로 두고, 원본 줄 중 `data-search-text`가 검색어(소문자, 앞뒤 공백 제거)를 포함하는 줄만 보인다(`hidden` 속성 토글). 보이는 줄이 없는 섹션은 통째로 `hidden`. "모두 보기" 버튼과 첫 문장 줄은 숨긴다.
  - 전체 0개면 `#product-search-no-results`(현행 문구)를 보인다.
  - 돌아가기 버튼을 보인다. 검색어를 지우거나 돌아가기를 누르면 기본 모드(검색어 비움).
  - 주소: `q` 설정·삭제는 `history.replaceState`(현행). 처음 로드 시 `q`가 있으면 검색 모드, 없고 `cat`이 있으면 분야 모드.
- 숨긴 요소는 `hidden` 속성으로 숨겨 보조기기에서도 빠지게 한다.
- 스크립트는 번들 `<script>`(is:inline 아님)로 두고 `astro:page-load`마다 실행한다. `#products-top`에 `dataset.catalogReady`가 있으면 다시 묶지 않는다(뷰 전환으로 DOM이 바뀌면 새 요소라 다시 묶임).

## 데이터

- `CARD_COLUMNS`에 `difficulty`를 추가한다.
- `PRODUCT_CATEGORY_COLUMNS`에 `description_ko, description_en`을 추가한다(타입 `ProductCategory`에 이미 있음).
- 편집자 노트는 **추천 제품만** 가져온다: `ai_products`에서 `id, editor_note, editor_note_ko`를 `is_published = true`, `archived = false`, `featured = true`로 조회하는 작은 쿼리를 기존 `Promise.all`에 추가한다(5행). 전체 목록 쿼리에 노트 열을 넣지 않는다(전송량).
  - 이 쿼리가 실패하면 **추천 칸 한 줄을 tagline으로 대체**하고 페이지는 정상(200)이다. 503 판정은 현행 `categoriesRes.error || productsRes.error` 그대로 둔다(`public-error-cache-policy` 테스트 정규식 유지).
- 반환값: `spotlightProduct`를 **제거**하고 `picks`를 추가한다. `ProductsPageData` 타입도 맞춘다.
  - picks = 해석된 `allProducts`의 featured 줄을 `orderPicks`로 정렬(최대 5)하고, 노트 쿼리 결과를 `id`로 붙인 것(`editor_note`, `editor_note_ko`). 노트 쿼리가 실패하면 두 필드는 null이고 칸은 tagline을 쓴다.
- 순수 함수(`lib/productCatalog.js`, node 테스트 가능):
  - `firstSentence(text, max = 90)`: 앞뒤 공백 제거. 첫 문장 끝 = 정규식 `/[.!?。](?=\s|$)/`의 첫 위치(포함). 단, 영어 약어 `e.g.` `i.e.` `etc.` `Inc.` `vs.` `Mr.` `Dr.` 뒤의 마침표는 문장 끝으로 보지 않는다. 끝을 못 찾으면 전체. 결과가 max자를 넘으면 max−1자 안의 마지막 공백에서 자르고 "…"를 붙인다(…포함 max자 이하, 공백이 없으면 max−1자에서 자름). 빈 값이면 `''`.
  - `DIFFICULTY_LABELS` + `difficultyLabel(locale, value)`(모르는 값 `''`).
  - `orderPicks(products)`: featured만, `featured_order`(null 뒤) → `name_original` 이름순, 최대 5.
  - `catalogSections(categories, productsByCategory, order)`: `order` 순서 → 표에 없는 분야는 뒤에 `sort_order` 순, 0개 분야 제외. 각 항목 `{ category, products, lede, desc }`(lede = desc의 `firstSentence`).
  - `jumpLabel(locale, id, fallback)`: 위 짧은 라벨 표.
- 공개 HTML은 사용자 중립 유지.

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| h1 | AI 제품군 | AI Products |
| 부제 | AI 도구 {N}개 · {C}개 분야 | {N} AI tools · {C} fields |
| 추천 라벨 | 편집자 추천 {n} | Pick {n} |
| 모두 보기 | {n}개 모두 보기 → | See all {n} → |
| 돌아가기 | ← 모든 분야 | ← All fields |
| 함께 쓰이는 도구 | 다른 분야에서 함께 쓰이는 도구 {k}개 | Also used for this ({k}) |

## 모바일·태블릿

- ≤767px: 좌우 16px, h1 약 1.7rem, 제목 줄은 세로로 쌓고 검색창은 전체 폭. 바로가기·추천은 컨테이너 안 가로 스크롤, 페이지 가로 넘침 0. 목록 1열.
- 768~1023px: 추천 3열 줄바꿈, 목록 2열.

## 없애는 것

- 목록 페이지의 `ProductFilterBar`, `ProductCategoryTile`, `ProductCard`, `#category-preview`, `#filtered-grid`, `#products-back-all`, 태그 칩 클릭 검색, `productLike` import.
- 파일 삭제(구현 시 grep 재확인):
  - `components/products/ProductCategoryTile.astro`, `components/products/ProductFilterBar.astro`
  - `components/products/ProductSpotlight.astro`(이미 미사용)
  - `lib/productCategoryIcons.ts`(유일한 호출처가 타일)
- 남기는 것: `ProductCard.astro`(서재 `library/index.astro`, `ProductDetail.astro`가 사용), `ProductSearchBar.astro`(상세 sticky 검색), `.product-pricing-badge`(홈·서재·상세 공용), `.product-difficulty-badge`, `.product-grid`·`.product-card*`(서재·상세가 쓰면).
- CSS 삭제(각각 다른 사용처 없음을 grep으로 확인한 뒤): `.product-category-grid`, `.product-cat-tile*`(`.product-cat-tile-icon` 포함), `.product-cat-row*`, `.product-cat-tag`, `.products-back-all`, `.product-filter-bar`, `.product-filter-tabs`, `.product-filter-tab*`.
- i18n 삭제(사용처 없음 확인 후): `products.categoryAll`, `products.heroTitle`, `products.outroCta`.

## 테스트

- 새 node 테스트 `tests/product-catalog.test.mjs`
  - `firstSentence`: 한국어 "…니다. 다음" / 영어 ". " / ".\n" / 약어 "e.g. " 무시 / 문장부호 없음 / 길이 초과(…포함 max 이하) / 빈 값
  - `difficultyLabel`(ko/en, 모르는 값), `jumpLabel`(표 + 대체)
  - `orderPicks`(null 순서, 최대 5, 이름 tie-break)
  - `catalogSections`(순서 고정, 모르는 분야 뒤, 0개 분야 제외, lede)
- 새 구조 테스트 `tests/products-catalog.test.cjs`
  - ko/en 페이지: `h1`, `product-catalog-jump`, `product-picks`, `section.product-cat`, `li.product-row` data 속성 3종, `data-overflow`, `#product-search-no-results`, `product-catalog-back`, `product-cat-also`, outro·상표 고지 유지. `ProductCategoryTile`·`ProductCard`·`ProductFilterBar`·`filtered-grid`·`category-preview`·`productLike` 없음.
  - 데이터: `difficulty`, `description_ko`, featured 노트 쿼리(`.eq('featured', true)`), 전체 카드 쿼리에 `editor_note` 없음, `spotlightProduct` 없음, `categoriesRes.error || productsRes.error` 유지.
  - 스크립트: 디바운스 150, `cloneNode(true)` 후 `data-overflow`·`hidden` 제거, `replaceState`, `catalogReady` 가드, submit `preventDefault`.
  - CSS: 3열 / 2열 / 1열, `.product-cat-list > [data-overflow]` 숨김과 `[data-expanded]` 해제, 모바일 가로 스크롤 컨테이너, `scroll-margin-top`.
  - `ProductDetail.astro`가 `DIFFICULTY_LABELS`를 import.
- 기존 테스트 갱신·삭제:
  - `products-v2.test.cjs`: 46-57(`.product-filter-bar` 규칙, `ProductCategoryTile.astro` 읽기, 타일 핸들러 문자열) 삭제. 18-44(spotlight 아닌 thumb-fallback·tier·badge 단언)와 60은 유지 — spotlight 단언이 있으면 `ProductSpotlight` 삭제에 맞춰 함께 삭제.
  - `product-filter-bar-mobile-sticky.test.cjs`: 삭제하는 CSS만 검사하므로 **파일 삭제**.
  - `product-detail-search-sticky.test.cjs`: 58-66(`ProductFilterBar.astro` 읽기) 삭제, 상세 단언 유지.
  - `public-list-query-budget.test.cjs`: 18(`demoMediaFirst`)만 새 구조 기준으로 바꾼다. `CARD_COLUMNS`의 `demo_media`는 **유지**한다(`fetchAlternatives` → 상세 대안 카드가 사용). 31행 단언은 그대로.
  - 그 밖에 목록 페이지 문자열을 읽는 테스트는 계획 단계에서 grep으로 모두 찾는다.
- 전체 스위트: 실패 목록을 기준선과 이름으로 비교, 신규 FAIL 0. `npm run build` 성공.
- 브라우저: 3테마 × 1100px·900px·375px × ko/en, 가로 넘침 0, 대비 미달 0. 클릭: 바로가기 앵커(헤더에 안 가림), 추천 칸 링크, 모두 보기(어시스턴트: 28줄 + 함께 쓰이는 도구, 포커스 이동), `?cat=coding` 직접 진입, 돌아가기(포커스 복귀), 검색("이미지", "chatgpt", 결과 없음, 지우기, Enter 새로고침 없음), 제품 상세 링크. 회귀: 제품 상세(난이도 라벨, sticky 검색), 서재·홈의 제품 카드.

## 범위 밖 (기록만)

- 인기순·최신순 정렬(조회·출시일 데이터 없음).
- 가격 미입력 66개, 한국어 지원 4개 — 데이터 문제.
- 제품 상세 페이지 재설계.
