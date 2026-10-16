# 용어집 첫 화면 재설계 (B 분야별 서가 + A–Z 색인) — Design Spec

**Status:** implemented (2026-10-17) — [[2026-10-17-handbook-index-shelves]]
**Mockup:** `.superpowers/brainstorm/handbook/handbook-v1.html` (B안 + A안의 색인)
**관련:** [[2026-10-15-home-front-page-redesign-design]], [[2026-10-16-news-list-desks-design]], [[2026-10-15-site-redesign-phase6-handbook]]

## 배경

- 용어집 첫 화면(`/ko/handbook/`, `/en/handbook/`)은 발행 용어 114개를 이미 전부 불러온다(`getHandbookPageData`, `.limit(500)`). 그런데 처음 화면에는 용어 목록이 보이지 않는다.
  - `#search-results`는 비어 있고 숨겨져 있다. 검색하거나 분야 버튼을 눌러야 카드가 그려진다.
  - 첫 화면에 보이는 것은 "실시간 인기 용어 10", 분야 이름 목록, 분야 버튼 줄, 오른쪽 레일(소개, 많이 찾는 용어 3, 카테고리 둘러보기)뿐이다.
- 시안 A(사전 색인) / B(분야별 서가) / C(뉴스·목적) 중 **B에 A의 A–Z 색인을 붙인 안**을 골랐다.

## 화면 구성 (위에서 아래로)

1. **헤더 영역**: `NewsprintShell` 현행 그대로(호수 킥커, 관리자 편집 마스트헤드 `handbook_masthead`, subkicker).
2. **소개 한 줄**: `handbook_intro`(없으면 현행 레일 fallback 문구)를 마스트헤드 아래에 가운데 정렬, muted로 둔다. 현행 레일 "용어집 소개"를 옮긴 것이다.
3. **통계 줄**: `p.handbook-hero-stats` 현행 유지("N+ 용어 · M 카테고리").
   - N은 `fetchTermOfDay().total || allTerms.length`다. 정상이면 count(500 상한과 무관), count가 실패해 0이면 불러온 용어 수를 쓴다.
   - M은 소속 용어가 1개 이상인 정규 분야 수다(아래 서가 count 기준).
4. **검색**: `.handbook-search-sticky > input#handbook-search` 현행 그대로(힌트 회전, `#handbook-result-count`).
5. **오늘의 용어** `section.handbook-today`(데스크톱 2단 1.2fr : 1fr)
   - 왼쪽
     - 점 라벨: "오늘의 용어 · {호수}" / "Term of the day · {issue}"
     - 큰 이름(Hahmlet 700, 약 2.5rem). KO는 `korean_name || term`, EN은 `term`이다.
     - 보조 이름(Newsreader, muted). KO에 korean_name이 있으면 `term`을 쓴다.
     - 정의 1–2줄: `definition_{ko|en}`. 마크다운 `**`는 제거한 평문을 쓴다.
     - "풀이 읽기 →" / "Read the explainer →"(`/{locale}/handbook/{slug}/`)
   - 오른쪽 먹색 판(홈 키워드 판과 같은 스타일 규칙)
     - 라벨: "뉴스에서는 이렇게 쓰여요" / "How the news uses it"
     - 본문: `hero_news_context_{ko|en}`의 **첫 번째 비어 있지 않은 줄**. 앞뒤 공백을 지우고, 줄 앞의 `- `·`• ` 기호를 뗀다.
     - 값이 없으면 판을 렌더하지 않고 왼쪽 단이 전체 폭을 쓴다.
     - 다크 테마는 `--color-bg-tertiary` 면이다(홈 키워드 판·뉴스 주간 띠와 같은 규칙).
6. **분야별 서가** `section.handbook-shelves`
   - 머리 줄: "분야별 서가" / "Shelves by field"
   - 분야 순서는 `getHandbookCategories()`의 정규 순서다. **용어가 0개인 분야는 숨긴다**(현재 math-statistics).
   - 그리드: 데스크톱 3열. 용어가 가장 많은 분야(현재 llm-genai 50개)는 `handbook-shelf--wide`로 2행을 차지한다. 나머지는 1칸씩이다.
   - 각 서가
     - 위 2px 먹선
     - 분야 이름(Hahmlet 700)과 오른쪽 큰 숫자(Newsreader, accent)
     - 용어 목록: 넓은 서가는 6개 + 각 줄에 정의 1줄(`**` 제거 평문), 나머지는 4개(이름만)
     - "{N}개 모두 보기 →" / "All {N} →"(`/{locale}/handbook/category/{slug}/`. 기존 분야 페이지)
   - **숫자(count) = 소속 기준**: `categories`에 그 slug를 포함한 용어 수다. 분야 페이지의 `.contains('categories',[slug])`와 같은 기준이라, 링크를 눌렀을 때 보이는 개수와 일치한다. `wide` 선택과 통계 줄 M도 이 count를 쓴다.
   - **목록에 놓는 위치 = 첫 정규 분야**: 각 용어는 `categories` 중 `getHandbookCategories()`에 있는 첫 slug의 서가에만 놓인다(중복 노출 방지). 정규 분야가 하나도 없는 용어는 서가에서 빠지지만 A–Z 색인에는 남는다.
   - **빈 서가 채우기(2026-10-17 추가)**: 첫 정규 분야로 놓인 용어가 목표 수(6/4)보다 적으면 그 분야 소속 용어 중 아직 어느 서가에도 없는 용어로 채우고, 그래도 모자라면 다른 서가에 이미 보인 소속 용어(중복)로 채운다(각 단계 trending → `term` 알파벳 순). 숫자만 있고 목록이 빈 서가를 막는다.
   - 서가 안 용어 순서: 현행 trending 쿼리의 조회수 순서에 든 용어를 먼저, 나머지는 `term` 알파벳 순이다(순수 함수로 결정, 아래 "데이터").
7. **A–Z 색인** `section.handbook-az`
   - 알파벳 바
     - A–Z 26자 + `#`(숫자·기타로 시작)
     - 용어가 있는 글자는 `<a href="#az-{L}">`, 없는 글자는 muted `<span aria-hidden="true">`
     - 데스크톱은 줄바꿈, 모바일은 가로 스크롤(`overflow-x:auto`)이다. 페이지 가로 넘침은 0이어야 한다.
   - 사전
     - 그룹 `<div class="handbook-az-group" id="az-{L}">`: 큰 글자 머리(Newsreader) + 목록
     - 각 줄: 표시 이름(Hahmlet 600) ↔ 오른쪽 보조 이름(Newsreader, muted) → 상세 링크
     - 데스크톱은 3단 `column-count` + `column-rule`, 태블릿은 2단, 모바일은 1단이다.
   - 그룹 기준은 `term`의 첫 글자를 대문자로 바꾼 값(A–Z가 아니면 `#`)이다. 그룹 안은 `term` 알파벳 순이다(`localeCompare('en')`).
   - 그룹 앵커가 sticky 헤더와 검색창 아래로 숨지 않도록 `.handbook-az-group { scroll-margin-top: calc(var(--header-h, 4rem) + 4.5rem); }`를 둔다.
   - 색인은 페이지가 불러오는 용어 범위(현행 `.limit(500)`, 쿼리 예산 테스트로 고정)를 따른다. 500개를 넘으면 색인은 앞 500개까지만 보인다. 알려진 한계로 기록하고, 통계 줄 N은 count로 정확히 표시한다.
     - KO 표시 이름은 `korean_name || term`, 보조 이름은 `term`(korean_name이 있고 다를 때만)이다.
8. 검색 결과 영역(`#search-results`, `#handbook-no-results`)은 현행 그대로다.

## 없애는 것

- `section.handbook-trending`(실시간 인기 용어 10). 조회수 쿼리는 서가 안 정렬용으로 계속 쓴다.
- `section#handbook-showcase.product-category-showcase`(분야 이름 목록)
- `#handbook-controls`(분야 버튼 줄)
- 오른쪽 레일 `HandbookListRail` → Shell `rail={false}`. 컴포넌트는 이 페이지 전용이므로 삭제하고, 이를 읽는 테스트를 갱신하거나 삭제한다.
- 페이지별 하드코딩 `handbookTags`, 두 페이지 파일의 미사용 `PREVIEW_COUNT`와 `termsByCategory` 사용부
  - `termsByCategory`는 `handbookPage.ts`가 반환한다. 다른 사용처(분야 페이지 등)를 grep해서 없으면 반환값에서도 제거한다.
- CSS
  - `.handbook-filter-btn`과 함께 묶인 미사용 `.handbook-difficulty-btn` 셀렉터 그룹 전체
  - `.handbook-controls`, `.handbook-filter-row`
  - `.handbook-trending*`
  - `#handbook-showcase` 오버라이드와 이 페이지 전용 `.product-category-showcase*`
  - `.newsprint-rail-category-*`
  - 모든 항목은 삭제 전 `frontend/src` grep으로 다른 사용처가 없는지 확인한다.
  - **`.handbook-result-count`는 뉴스 목록도 쓰므로 유지한다.**

## 검색·필터 동작 (인라인 스크립트 수정)

- **검색 모드**: 검색어가 있거나 URL에 `?category=`가 있을 때다.
  - `.handbook-today`, `.handbook-shelves`, `.handbook-az`를 숨긴다. 현행 trending/showcase 숨김 대상을 이것으로 바꾼다.
  - `#search-results`에 카드를 그린다(현행 `ensureCards`/`filter`).
- **분야 필터**: 버튼이 없어지므로 활성 분야는 **URL `?category=` 값에서만** 읽는다.
  - **정규 slug(`getHandbookCategories()`)일 때만** 적용한다. 알 수 없는 값은 무시하고 기본 모드로 둔다.
  - 해제 링크
    - 서버가 결과 수 줄(`#handbook-result-count`) **바깥, 바로 앞**에 숨긴 `<a id="handbook-active-filter" href="/{locale}/handbook/" hidden data-labels='{"llm-genai":"LLM · 생성AI",...}'>`을 렌더한다.
    - 스크립트는 활성 분야가 있을 때 `textContent = "{label} · 전체 보기로"`(EN `"{label} · Back to all"`)로 채우고 `hidden`을 해제한다.
    - 결과 수 요소의 `textContent` 갱신이 링크를 지우지 않도록 별도 요소로 둔다.
- **기본 모드**(검색어 없음, 정규 분야 없음)
  - 숨김: `#search-results`, `#handbook-no-results`, `#handbook-result-count`, `#handbook-active-filter`
  - 보임: `.handbook-today`, `.handbook-shelves`, `.handbook-az`
  - `ensureCards()`를 호출하지 않는다.
  - 현행 sentinel/IntersectionObserver(20개씩 무한 스크롤) 코드는 **완전히 삭제**한다. 색인이 전체 목록을 대신한다.
  - 검색어를 지워 기본 모드로 돌아올 때도 같은 숨김을 적용한다(결과 없음 안내가 남지 않게).
- 스크립트 이중 바인딩을 막는다(`dataset.handbookIndexReady` 가드, `astro:page-load` + 즉시 실행 유지).
- `content-status:refresh` 발행은 카드를 그린 뒤 그대로 유지한다(`public-list-personalization` 계약).

## 데이터

- **기존 쿼리 유지**: 전체 용어 `getHandbookPageData`(limit 500, 필드 그대로), 조회수 상위 10 trending 쿼리, site content
- **오늘의 용어 — 홈과 같은 쿼리를 공유한다(추가 쿼리 2개: count + 1행)**
  - JS 정렬로 홈을 흉내 내면 DB 정렬 규칙(collation)과 500 상한 때문에 어긋날 수 있다. 그래서 홈의 쿼리를 공유 모듈로 뽑는다.
  - **새 `lib/pageData/termOfDay.ts`**: `fetchTermOfDay(db, locale, now, extraColumns = '')`
    - 홈 현행 로직을 그대로 옮긴다: published count(head) → `termIndex(now, count)` → `order('slug', { ascending: true }).range(i, i).maybeSingle()`
    - select는 `term, slug, korean_name, definition:definition_{ko|en}`와 `extraColumns`다.
    - 반환값: `{ term: row | null, total: count }`. 오류는 로그만 남기고 `{ term: null, total: 0 }`이다.
  - `homeFrontPage.ts`는 이 함수를 호출하도록 바꾼다(동작 동일).
    - 뉴스 쿼리와 `fetchTermOfDay`를 `Promise.all`로 병렬 실행해 홈 응답 시간이 늘지 않게 한다.
    - `home-front-query-budget.test.cjs`의 **용어 쿼리 단언 전부**를 `termOfDay.ts` 기준으로 옮긴다: `handbook_terms` 2회, `count: 'exact', head: true`, `.range(i, i)`, `.order('slug'`, `definition:${definitionField}`, `termIndex(`
    - 홈 파일에는 뉴스 `.limit(6)`, `selectFrontPage(`, `fetchTermOfDay(` 단언만 남긴다.
  - 용어집은 `extraColumns = 'hero_news_context_ko'`(EN `_en`)로 호출한다. 판 본문과 통계 줄 N(=total)을 함께 얻는다.
  - 오류나 빈 값이면 오늘의 용어 섹션 또는 판을 생략한다. 503을 만들지 않는다.
- **새 순수 모듈 `lib/handbookShelves.js`**(단위 테스트 대상)
  - `buildShelves(terms, categorySlugs, trendingSlugs)` → `[{ slug, count, wide, items }]`
    - count는 소속 기준(`categories.includes(slug)`)이다.
    - items 후보는 첫 정규 분야가 그 slug인 용어다.
    - count 0인 분야는 제외한다.
    - count 최다 1개가 `wide`다(동률이면 정규 순서에서 앞선 것).
    - items는 wide면 6개, 아니면 4개다. trending 순서가 먼저, 그다음 `term` 알파벳 순(`localeCompare('en')`)이다.
  - `plainDefinition(text)` → `**` 제거 + 앞뒤 공백 정리
  - `buildAzIndex(terms)` → `{ letters: [{ letter, has }], groups: [{ letter, items }] }`
    - letters는 A–Z + `#` 27개다.
    - groups는 용어가 있는 글자만, 글자 순서대로다. `#`는 마지막이다.
  - `firstNewsLine(text)` → 첫 비어 있지 않은 줄(기호 제거) 또는 ''
- `publicTermIndex.ts`는 **수정하지 않는다**(다른 세션 작업 중).

## 컴포넌트

- 새 파일
  - `components/handbook/HandbookToday.astro`(오늘의 용어 + 판)
  - `components/handbook/HandbookShelves.astro`
  - `components/handbook/HandbookAzIndex.astro`
- 수정
  - `pages/{ko,en}/handbook/index.astro`: 섹션 교체, 레일 제거, `rail={false}`, 인라인 스크립트 수정
  - `lib/pageData/handbookPage.ts`: 반환값 `termsByCategory`만 제거한다. grep으로 다른 사용처가 없을 때만이다. 쿼리는 그대로다.
    - `PREVIEW_COUNT`는 페이지 파일에 있으므로 페이지에서 지운다.
- 삭제: `components/newsprint/HandbookListRail.astro`
  - 전용 CSS를 정리한다: `.newsprint-rail-category-*` 등. **다른 사용처를 grep으로 확인한 뒤에만 지운다**(공유 `.newsprint-rail*` 기본 규칙은 유지).
  - 쓰이지 않게 되는 `.handbook-trending*`, `#handbook-showcase` 오버라이드, `.product-category-showcase*`(이 페이지 전용), `.handbook-controls`/`.handbook-filter-*`(사용처 확인 후)도 정리한다.

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| 오늘의 용어 라벨 | 오늘의 용어 · {제N호} | Term of the day · {No. N} |
| 풀이 링크 | 풀이 읽기 → | Read the explainer → |
| 판 라벨 | 뉴스에서는 이렇게 쓰여요 | How the news uses it |
| 서가 머리 | 분야별 서가 | Shelves by field |
| 서가 링크 | {N}개 모두 보기 → | All {N} → |
| 색인 머리 | A–Z 색인 | A–Z index |
| 분야 필터 해제 | {분야} · 전체 보기로 | {Field} · Back to all |

분야 이름은 `getHandbookCategoryLabel(locale, slug)`(현행)을 쓴다.

## 모바일 (≤767px)

- 오늘의 용어는 1단이다(판은 정의 아래).
- 서가는 1열이다(wide도 1칸).
- 색인 바는 가로 스크롤, 사전은 1단이다.
- 가로 넘침은 0이어야 한다.

## 테스트

- **새 `handbook-shelves.test.mjs`**(순수 함수)
  - 소속 기준 count, 첫 정규 분야 배치, 비정규 분야만 가진 용어 제외
  - 0개 분야 제외, wide 선택과 동률 처리, items 수(6/4), trending 우선 정렬
  - `plainDefinition`의 `**` 제거
  - A–Z: 27자, `#` 그룹(숫자 시작), 그룹 내 정렬
  - `firstNewsLine`: 빈 줄 건너뛰기, `- ` 제거, null이면 ''
- **새 `handbook-index-shelves.test.cjs`**(구조)
  - ko/en 페이지가 세 컴포넌트를 쓰고 `rail={false}`이다.
  - `HandbookListRail`·`handbook-trending`·`handbook-showcase`·`handbook-filter-btn`이 없다.
  - `?category=` 처리, 해제 링크, 이중 바인딩 가드, `content-status:refresh` 유지
  - 문구 KO/EN, 색인 앵커 `id="az-`
  - CSS: 서가 3열과 wide 2행, 색인 3단과 모바일 1단, 색인 바 모바일 `overflow-x: auto`, 다크 판 규칙, `.handbook-az-group` `scroll-margin-top`
  - 스크립트: `#handbook-active-filter` + `data-labels`, sentinel/IntersectionObserver 없음, 정규 slug 검사
- **새 `term-of-day.test.cjs`**
  - `termOfDay.ts`: count(head), `termIndex`, `order('slug'`, `.range(i, i)`
  - `homeFrontPage.ts`·handbook 페이지 데이터가 `fetchTermOfDay`를 호출한다.
- **갱신**
  - `home-front-query-budget`: `handbook_terms` 쿼리 단언을 `termOfDay.ts` 기준으로 옮긴다. 홈 파일에는 `fetchTermOfDay(` 호출 단언을 둔다.
  - `handbook-v2` 단언 교체(그 밖의 `.handbook-card*`·pill 단언은 유지. 카드는 검색 결과와 분야 페이지에서 계속 쓰인다)
    - `.handbook-filter-btn[aria-pressed]` active `::after` → 삭제
    - `.handbook-trending` 단일 블록과 점선 `li` → `.handbook-shelf`가 `border-top: 2px solid var(--color-text-primary)`, 서가 li 점선
    - `#handbook-showcase .product-category-showcase-card {` → `.handbook-az-dict`가 `column-count: 3`, 모바일 `column-count: 1`
    - `.handbook-filter-row` nowrap → 모바일 `.handbook-az-bar`가 `overflow-x: auto`
  - `handbook-library-copy`: 레일 문구("About This Glossary", "용어집 소개") 단언을 소개 한 줄의 fallback 문구 단언으로 옮긴다.
  - `handbook-category-icons`: `HandbookListRail.astro`를 읽으므로 레일 삭제와 **같은 커밋에서 삭제**한다(이미 stale한 옛 slug 기준 테스트).
- **유지**: `public-list-query-budget`, `public-term-index`, `public-list-personalization`, `issue-number-shell`, `handbook-search-recognition`, `list-v2`, `product-detail-search-sticky`
- **검증 매트릭스**
  - 종이·순백·다크 × ≥1024px·375px × ko/en
  - 직접 확인: 검색 "MCP" 입력·지우기, `?q=RAG`, `?category=llm-genai`와 해제 링크, 색인 글자 클릭 이동, 서가 "모두 보기" 링크
  - 오늘의 용어가 홈과 같은지 확인한다.
  - 가로 넘침 0, 대비 검사
- 전체 테스트는 이름 기준으로 비교한다. 신규 FAIL은 0이어야 한다.

## 범위 밖

- 용어 상세 페이지, 분야(category) 페이지 디자인
- `publicTermIndex.ts`(다른 세션)
- 검색 카드 innerHTML 이스케이프 개선(기존 이슈. 별도 후보로 기록)
