---
title: "프론트엔드 성능 최적화 — 뉴스 & 용어집 로딩 속도 개선"
tags:
  - performance
  - optimization
  - decision
  - frontend
date: 2026-03-17
---

> 날짜: 2026-03-17
> 관련 Phase: [[Phase-Flow]]
> 관련 문서: [[Frontend-Spec]]

# 프론트엔드 성능 최적화 — 뉴스 & 용어집 로딩 속도 개선

## 왜 이 글을 쓰는가

사이트 페이지 전환이 체감할 수 있을 정도로 느렸다. 특히 뉴스 목록/상세와 용어집(Handbook) 인덱스가 심했다. 분석 결과 **무제한 DB 쿼리, 중복/순차 마크다운 렌더링, render-blocking 리소스** 세 가지 축에서 병목이 발생하고 있었다.

---

## 발견된 병목 (Before)

### 1. 무제한 Supabase 쿼리

| 페이지 | 쿼리 | 문제 |
|--------|------|------|
| 뉴스 목록 (ko/en) | `news_posts` `.select(...)` `.order(...)` | `.limit()` 없음 — 전체 fetch |
| 뉴스 상세 | `handbook_terms` `.select(...)` `.eq('published')` | **전체 용어** fetch → 팝업 링킹에 사용하지만 실제로 3개만 표시 |
| 핸드북 인덱스 | `handbook_terms` `.select(...)` `.order('term')` | `.limit()` 없음 |
| 핸드북 카테고리 | `handbook_terms` `.contains('categories', [...])` | `.limit()` 없음 |

### 2. 마크다운 렌더링

| 페이지 | 문제 |
|--------|------|
| 뉴스 상세 | learner + expert + analysis를 **순차** `await renderMd()`. 게다가 `htmlContent`에서 **이미 렌더된 동일 마크다운을 다시 렌더** — 완전한 중복 |
| 핸드북 상세 | basic + advanced를 순차 렌더 |
| 공통 | `renderMarkdownWithTerms()`가 매 호출마다 unified processor(Shiki 포함)를 **새로 생성** |

### 3. 프론트엔드 리소스 로딩

| 리소스 | 문제 |
|--------|------|
| Google Fonts (3개) + NanumSquare | `<link rel="stylesheet">` — **render-blocking** |
| KaTeX CSS (24KB) | 모든 페이지에 로드 — 수식 없는 목록 페이지에서도 |
| 핸드북 검색 | 전체 용어를 숨긴 DOM 카드로 렌더 (data-def에 정의 전문 포함) → HTML 100KB+ |
| 검색/필터 입력 | debounce 없음 — 키 입력마다 DOM 전체 순회 |

---

## 적용한 최적화 (After)

### Tier 1 — Critical

**1. 뉴스 목록 `.limit(50)` + 미사용 컬럼 제거**
- `og_image_url` 컬럼을 `.select()`에서 제거 (카드 컴포넌트에서 미사용)
- `.limit(50)` 추가
- 파일: `ko/news/index.astro`, `en/news/index.astro`

**2. 뉴스 상세 handbook terms `.limit(200)`**
- 전체 용어 → 200개 제한 (인라인 용어 링킹에 충분)
- 파일: `newsDetailPage.ts`

**3. 마크다운 병렬화 + 중복 렌더 제거**
- `for` 순차 루프 → `Promise.all` 병렬
- `htmlContent = await renderMd(rawContent)` → `personaHtmlMap[activePersona]` 재사용 (동일 마크다운 재렌더 완전 제거)
- 파일: `newsDetailPage.ts`

**4. 핸드북 인덱스 DOM → JSON**
- 숨겨진 `#search-results` 내 500+ 카드 DOM → `<script type="application/json">` JSON 데이터
- 검색 최초 시점에 `DocumentFragment`로 카드 lazy 생성 (1회 생성 후 캐시)
- 파일: `ko/handbook/index.astro`, `en/handbook/index.astro`

### Tier 2 — High Priority

**5. 핸드북 상세 마크다운 병렬 렌더**
- `if (basic) await render(); if (advanced) await render();` → `Promise.all([...])`
- 파일: `handbookDetailPage.ts`

**6. 검색/필터 debounce 추가**
- 핸드북 인덱스, 카테고리 페이지, 뉴스 목록 검색, 기사 내 검색 — 150~200ms debounce
- `JSON.parse(categories)` 캐싱 (`__cats ??=` 패턴)
- 파일: 6개

**7. Google Fonts 비동기 로딩**
- `<link rel="stylesheet">` → CSP nonce 붙은 `<script is:inline>`으로 동적 `<link>` 생성
- render-blocking 제거 → FCP 200-500ms 개선 예상
- 파일: `Head.astro`

**8. KaTeX CSS 조건부 로딩**
- `Head.astro`에 `needsKatex` prop 추가
- 마크다운 렌더하는 상세 페이지([slug].astro)에서만 `needsKatex={true}` 전달
- 목록/인덱스 페이지에서 24KB 절감
- 파일: `Head.astro`, `MainLayout.astro`, 6개 상세 페이지

### Tier 3 — Safety

**9. unified processor 캐싱**
- `renderMarkdownWithTerms()` — `WeakMap<TermsMap, Processor>`로 요청 내 재사용
- 파일: `markdown.ts`

**10. 핸드북 쿼리 safety limit**
- `getHandbookPageData()` → `.limit(500)`
- `getHandbookCategoryPageData()` → `.limit(200)`
- 파일: `handbookPage.ts`

---

## 교훈

1. **가장 큰 성능 개선은 "안 해도 되는 일을 안 하는 것"** — 중복 마크다운 렌더 제거(동일 MD 2번 파싱), 사용 안 하는 컬럼 제거, 검색 전까지 DOM 생성 안 하기 등. 코드를 빠르게 만드는 것보다 불필요한 작업 자체를 없애는 게 훨씬 효과적.
2. **`.limit()` 없는 Supabase 쿼리는 시한폭탄** — 콘텐츠가 10개일 때는 문제 없지만, 100개 → 500개로 늘어나면 선형 증가. 모든 공개 쿼리에 합리적인 limit을 붙여야 한다.
3. **HTML data-* 속성에 긴 텍스트를 넣지 말 것** — 이전 MEMORY에도 기록했듯이, 정의 전문을 `data-def`에 넣으면 페이로드 폭증. JSON blob으로 분리하고 필요 시 JS로 접근하는 패턴이 정답.

---

## Related

- [[ACTIVE_SPRINT]] — 현재 스프린트
- [[Frontend-Spec]] — 프론트엔드 스펙
