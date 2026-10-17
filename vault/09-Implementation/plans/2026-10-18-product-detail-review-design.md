# 제품 상세 재설계 (A 리뷰 지면) — Design Spec

**Status:** approved (2026-10-18)
**Mockup:** `.superpowers/brainstorm/products/product-detail-v1.html` (A안)
**관련:** [[2026-10-18-products-catalog-design]], [[2026-10-17-handbook-term-entry-design]]

## 배경

- 제품 상세(`/ko/products/{slug}/`, `/en/products/{slug}/`)는 섹션 11개(소개·에디터 한마디·주요 기능·이런 상황·이렇게 써보세요·장단점·시작하는 법·가격·관련 뉴스·비슷한 도구·FAQ)가 같은 무게로 쌓여 ChatGPT 기준 4,365px다. 판단에 필요한 내용(에디터 한마디, 장단점)이 먼저 읽히지 않는다.
- 데이터(2026-10-18 운영 확인, 발행 123개): `description_ko`·`features_ko`·`use_cases_ko`·`getting_started_ko`·`scenarios_ko`(대개 5개)·`pros_cons_ko`·`editor_note_ko` 각 114개, `pricing_detail_ko` 55개, `korean_quality_note` 6개, `platform` 109개, `demo_media`·`official_resources`·`thumbnail_url`·`pricing_note` 0개.
- "비슷한 도구"는 `ProductCard`가 locale 이름(예: "오픈클로우")을 보여 목록(원래 이름 "OpenClaw")과 다르다. (`ProductDetail`은 `alt.name_original ?? alt.name`을 넘기지만 `fetchAlternatives` 결과에 `name_original`이 없어서 locale 이름이 된다 — 아래 "컴포넌트"에서 매핑을 추가해 고친다.)
- 상단에 sticky 검색(`ProductSearchBar sticky`)이 있다. 다른 상세 페이지에는 검색이 없다.
- 시안 A(리뷰 지면) / B(사용 설명서) / C(판정 먼저) 중 **A**를 골랐다(2026-10-18).

## 화면 구성 (가운데 한 단, 최대 약 900px)

루트 `article.product-detail#products-top`(현행 유지).

1. **경로 줄** `nav.product-detail-crumb`(aria-label "제품 위치" / "Product location"): "← AI 제품군" / "← AI Products"(`/{locale}/products/`) · 주 분야 짧은 라벨(`jumpLabel(locale, id, id)`, 링크 `/{locale}/products/?cat={id}`).
   - 분야 라벨은 목록의 짧은 라벨 표를 재사용한다(상세는 분야 테이블을 조회하지 않는다).
2. **머리** `header.product-detail-head`: 2열(1fr : 250px), 아래 2px 먹선
   - 왼쪽
     - 로고(52px, `logo_url` 없으면 첫 글자 네모) + `h1.product-detail-name`(원래 이름 `name_original`, Hahmlet 700 약 2.5rem). ko이고 `name_ko`가 원래 이름과 다르면 이름 옆에 작게(현행 규칙).
     - 한 줄 소개 `p.product-detail-tagline`(locale tagline)
     - 분야·태그 줄 `div.product-detail-tags-row`: 주 분야·보조 분야는 짧은 라벨 링크(`?cat=`), 태그는 `#태그` 텍스트(현행 display_tags). 지금의 영문 id 표시(`assistant`)를 라벨로 바꾼다.
   - 오른쪽 스펙 상자 `aside.product-detail-spec`(aria-label "제품 정보" / "Product facts")
     - `dl` 행: 가격(기존 `.product-pricing-badge[data-pricing]`, 없으면 "정보 없음" / "Not listed"), 난이도(기존 `.product-difficulty-badge`, 없으면 행 생략), 플랫폼(`platform` 라벨 " · " 연결, 없으면 행 생략), 한국어("지원" / "미지원", "Supported" / "Not supported")
     - 버튼 줄: 사이트 방문 `a.product-visit-btn`(새 창, `rel="noopener noreferrer"`) + 찜 `button#product-like-btn`(현행 마크업·id·data 속성·`#like-label`·`#like-count` 그대로 — `productLike.ts`가 이 id를 찾는다)
   - `MediaGallery`: `demo_media`가 있을 때만 머리 아래(현행 조건 유지, 현재 0개).
3. **에디터 한마디** `section.product-detail-verdict`: 라벨 "에디터 한마디" / "Editor's take"(`h2`, accent 작은 글씨) + 노트 전체를 큰 인용(`blockquote`, Hahmlet 600 약 1.2rem). 노트 규칙은 현행(ko: `editor_note_ko || editor_note`, en: `editor_note`). 없으면 생략.
4. **장단점** `section`(`h2` "장단점" / "Pros and cons"): 좌우 2칸 "좋은 점" / "What works"(+ 표시, good 색) · "아쉬운 점" / "What to watch"(− 표시, bad 색). 한쪽만 있으면 그 칸만. 둘 다 없으면 생략. 모바일은 위아래.
5. **이렇게 써보세요** `section`(`h2` 현행 문구): 번호 목록(번호는 Newsreader accent). **처음 3개**만 보이고 나머지는 `details.product-detail-more`의 `summary` "{n}개 더 보기" / "Show {n} more" 안에 같은 목록으로 이어 번호를 매긴다(JS 없음). 3개 이하면 `details` 없음.
6. **주요 기능 · 이런 상황에 추천**: 데스크톱 2단(각 `section` + `h2` 현행 문구), 한쪽만 있으면 1단 전체 폭. 모바일 1단.
7. **가격** `section`(`h2` "가격" / "Pricing"): `pricing_detail` 렌더 HTML(현행 `htmlPricingDetail`, 표 스타일을 지면 표로 정리). 없으면 생략.
8. **시작하는 법** `section`: 번호 단계(현행 데이터).
9. **소개** `section`: `htmlDescription`(현행). 없으면 생략.
10. **한국어 품질 메모** `section`: `korean_quality_note`가 있을 때만(현행). 이어서 **공식 자료**(`official_resources`, 현행 조건부 섹션 유지, 현재 0개).
   - 한국어 지원 여부는 스펙 상자 행("지원/미지원")으로만 보여주고, 머리의 `✓ 한국어` 칩은 없앤다.
11. **끝 블록**
    1. 관련 뉴스 `section`: 제목 링크(현행 데이터, 최대 현행 개수).
    2. 비슷한 도구 `section`: `ol` + 목록 페이지와 **같은 줄 컴포넌트** `ProductRow`(로고·원래 이름·한 줄 설명·가격·난이도). `ProductCard` 대신 쓴다.
    3. FAQ `section`: 현행 `details` 3종 그대로.
    4. 확인일(`verified_at` 있을 때만, 현행), 피드백(slot의 `ContentFeedback`), 관리자 버튼(현행 `data-admin-only` 그대로).
   - 맨 아래 큰 "사이트 방문" 버튼(`.product-detail-bottom-cta`)은 없앤다(스펙 상자·모바일 하단 바와 중복).

섹션 머리 `h2`는 공통 클래스 `product-detail-section-title`(위 2px 먹선 + Hahmlet 700 약 1.2rem)로 통일한다. 3번 에디터 한마디만 작은 accent 라벨형.

## 모바일 (≤767px)

- 좌우 16px, 이름 약 1.9rem, 머리 1열(스펙 상자가 아래로).
- 스펙 상자의 `dl`은 2×2 격자.
- 버튼 줄 `div.product-detail-actions`는 마크업상 **스펙 상자 안에 한 벌만** 둔다(`#product-like-btn` 중복 금지). ≤767px에서는 이 줄을 `position: fixed; left: 0; right: 0; bottom: 0; z-index: 50` + 배경·위 1px 선 + `padding-bottom: calc(.75rem + env(safe-area-inset-bottom))`로 화면 아래에 고정한다. z-index는 로그인 안내 시트(`AuthPromptSheet`, z-index 300)보다 낮아야 한다(찜 버튼이 그 시트를 연다). 푸터까지 가리지 않도록 `body:has(.product-detail-actions)`에 바 높이 + `env(safe-area-inset-bottom)`만큼 `padding-bottom`을 준다(≤767px). (`sticky`는 요소의 원래 위치가 머리라 스크롤하면 사라지므로 쓰지 않는다.)
- 쿠키 배너(`CookieConsent`, fixed bottom, z-index 9999)가 떠 있는 동안에는 버튼 바를 가린다 — 허용한다(배너를 닫으면 보임).
- 장단점·기능/상황 1단. 가로 넘침 0.

## 컴포넌트

- 새 `components/products/ProductRow.astro`: 목록 `ProductCatalogSection.astro`의 줄 마크업(`li.product-row` + `a` + 로고·이름·한 줄·메타)을 그대로 옮긴다. Props: `product`, `locale`, 선택 `overflow`(목록용 `data-overflow`), `searchText`(목록용). 목록 섹션과 상세 비슷한 도구가 함께 쓴다. 목록의 마크업·클래스·data 속성은 바뀌지 않는다(목록 테스트·스크립트 유지).
- 표시 이름은 `name_original`(없으면 `name`). `fetchAlternatives`(productsPage.ts)는 `CARD_COLUMNS`로 조회하고 `name`을 locale 이름으로 바꾸면서 `name_original`을 만들지 않는다 → 매핑에 `name_original: p.name as string`(원본 행의 원래 이름)을 **추가한다**(쿼리 열 변경 없음). 함수 순서·이름은 유지한다(`public-detail-query-contract` 테스트가 위치로 자른다).
- `ProductRow`: `data-search-text={searchText}`로 쓴다(값이 undefined면 Astro가 속성을 생략). 로고 `alt=""`(이름이 바로 옆에 있음). 상세의 비슷한 도구 목록은 `ol.product-detail-alts`(`list-style: none`, 목록의 `.product-cat-list` 리셋에 기대지 않음).
- 비슷한 도구 줄은 목록 스크립트(`productCatalog.ts`)의 루트 밖이라 스크립트가 건드리지 않는다.
- `ProductDetail.astro`는 위 구성으로 다시 쓴다. Props 변경 없음(페이지 쪽 호출 유지).

## 데이터

- 쿼리 변경 없음. `PRODUCT_DETAIL_PUBLIC_COLUMNS`, `fetchAlternatives`(`CARD_COLUMNS`, 이미 `difficulty` 포함), `fetchRelatedNews` 그대로.
- 공개 HTML 사용자 중립 유지(찜 상태는 현행처럼 `productLike.ts`가 클라이언트에서 채움).

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| 경로 첫 칸 | ← AI 제품군 | ← AI Products |
| 스펙 | 가격 · 난이도 · 플랫폼 · 한국어 | Price · Difficulty · Platforms · Korean |
| 가격 없음 | 정보 없음 | Not listed |
| 한국어 | 지원 / 미지원 | Supported / Not supported |
| 에디터 한마디 | 에디터 한마디 | Editor's take |
| 장단점 | 장단점 · 좋은 점 · 아쉬운 점 | Pros and cons · What works · What to watch |
| 시나리오 더 보기 | {n}개 더 보기 | Show {n} more |

나머지 섹션 제목은 현행 문구를 쓴다.

## 없애는 것

- 상세 페이지의 `ProductSearchBar`(sticky) 사용, 큰 하단 CTA, 상세의 `ProductCard` 사용.
- `ProductSearchBar.astro`: 목록 페이지가 계속 쓰므로 **남긴다**. `sticky` prop과 `product-detail-search handbook-search-sticky` 분기는 **제거**한다(목록은 sticky 없이 씀).
- 추가 CSS 삭제(상세 전용, grep 확인 후): `.product-detail-search*`, `.product-grid--preview`, `.product-detail-chip*` 전체(`--accent`·`--muted`·`--tag`·`--stat` 포함 — 새 태그 줄은 새 클래스), `@media (max-width: 639px)`의 옛 hero 모바일 규칙, `.product-detail-content`, `.product-detail-editor-note*`(새 verdict 클래스로 대체). 모바일 기준은 사이트 공통 767px로 통일한다.
- `ProductCard.astro`: 서재(`library/index.astro`)가 쓰므로 **남긴다**.
- CSS 삭제(다른 사용처 없음 grep 확인 후): `.product-detail-bottom-cta`, `.product-visit-btn--large`, `.product-detail-hero*`(새 머리로 대체). 나머지 삭제 대상은 아래 "추가 CSS 삭제" 목록.
- `.handbook-search-sticky`는 용어집이 쓰므로 남긴다.

## 테스트

- 새 구조 테스트 `tests/product-detail-review.test.cjs`
  - ko/en 페이지: `ProductSearchBar`·`handbookSearchHints` import 없음(힌트 스크립트는 `[data-placeholder-hints]`만 찾는데 상세에는 더 이상 없음 — 두 페이지에서 import 제거), `ProductDetail` 사용 유지, `productLike` import 유지, 503/404 분기와 `ContentFeedback` 유지.
  - `ProductDetail.astro`: 경로 줄(`jumpLabel`, `?cat=`), `h1.product-detail-name`, 스펙 상자 `dl`, `#product-like-btn` **정확히 1개**, 섹션 순서(verdict → 장단점 → 시나리오 → 기능/상황 → 가격 → 시작 → 소개 → 한국어 메모 → 뉴스 → 비슷한 도구 → FAQ), 시나리오 `details` "더 보기", `ProductRow` 사용, `ProductCard`·`product-detail-bottom-cta` 없음, `data-admin-only` 유지, `<slot />` 유지.
  - `ProductRow.astro` 존재, `ProductCatalogSection.astro`가 사용.
  - CSS: 2열 머리, ≤767px 1열 + 버튼 줄 `position: fixed` + `z-index: 50` + `body:has(.product-detail-actions)` 하단 여백, 장단점 2칸/1칸.
  - 데이터: `fetchAlternatives` 매핑에 `name_original`.
- 기존 테스트 갱신·삭제:
  - `products-catalog.test.cjs` 54-60: 줄 마크업 단언(`data-search-text=`, 배지 클래스, `difficultyLabel(locale, product.difficulty)`, `{name}</span>`, `product.name_original ?? product.name`, `loading="lazy"`, `alt=""`, `data-category={product.primary_category}`, `data-secondary-categories=`)의 대상 파일을 `ProductRow.astro`로 바꾸고, overflow 단언은 섹션의 `overflow={index >= PREVIEW_ROWS}` + 줄의 `data-overflow={overflow ? '' : undefined}`로 바꾼다. 126-127(`ProductDetail`이 `DIFFICULTY_LABELS` import): 새 `ProductDetail`도 `DIFFICULTY_LABELS`를 import해 쓰므로 유지한다.
  - `products-v2.test.cjs` 41: CSS의 `/* Pros & Cons */` ~ `/* Korean Note */` 주석 사이 구간에 #16a34a·#dc2626이 없어야 한다 → 두 주석 앵커를 새 CSS에도 두고 good/bad 색은 토큰(이 두 색 아님)으로.
  - `product-detail-scenarios-theme.test.cjs`(현재 기준선 FAIL): 새 시나리오 목록에도 `.product-detail-scenario {` 규칙을 두고 `background: var(--color-bg-secondary` 를 쓰면 통과로 바뀐다 — 그렇게 한다(실패 → 통과는 허용되는 변화).
  - `product-detail-search-sticky.test.cjs`, `product-detail-search-spacing.test.cjs`: 상세 검색 제거에 맞춰 상세 검색 단언을 삭제(파일 전체가 상세 검색만 다루면 파일 삭제). `.product-detail-page` 래퍼는 유지한다(페이지 폭 컨테이너).
  - `product-detail-admin-actions.test.cjs`: 관리자 마크업 유지에 맞춰 확인·갱신.
  - 읽기만 하고 깨지지 않아야 하는 테스트: `public-error-cache-policy`, `content-feedback-contract`, `public-detail-query-contract`.
  - 그 밖에 상세 문자열을 읽는 테스트는 계획 단계에서 grep으로 모두 찾는다.
- 전체 스위트: 실패 목록을 기준선과 이름으로 비교, 신규 FAIL 0. `npm run build` 성공.
- 브라우저: 3테마 × 1100px·375px × ko/en, 가로 넘침 0, 대비 미달 0. 대상: chatgpt(가격표 있음), 가격표 없는 제품 1개, `korean_quality_note` 있는 제품 1개. 클릭: 경로 줄 분야 링크(`?cat=` 모드로 열림), 사이트 방문(새 창 속성), 찜(비로그인 → 로그인 안내), 시나리오 더 보기, FAQ 펼침, 비슷한 도구 링크, 모바일 하단 버튼 바(스크롤 중 고정). 회귀: 목록 페이지(줄 마크업·검색·모두 보기), 서재 카드.

## 범위 밖 (기록만)

- 스크린샷·공식 자료 데이터 없음(갤러리는 조건부 유지).
- "잘 맞는 사람 / 다른 선택" 같은 새 필드(C안 요소).
- 조회수 표시(현행 주석 처리 유지).
