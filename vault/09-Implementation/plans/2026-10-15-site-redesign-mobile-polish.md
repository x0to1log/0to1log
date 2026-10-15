# 사이트 리디자인 — 모바일 보정

**Status:** done (2026-10-15)

**배경:** 8단계 이후 375px 점검(12개 페이지, 페이지 가로 넘침 0)에서 세 가지 문제를 발견했다.

## 변경
1. **영문 모바일 메뉴 줄바꿈**
   - 문제: `.site-primary-nav--mobile`이 5칸 균등 grid라서 "My Library"가 두 줄로 꺾인다.
   - 수정:
     - 칸 폭을 내용에 맞춘다: `repeat(5, auto)` + `justify-content: space-between`
     - `.site-nav-pill`에 `white-space: nowrap`
     - 360px 이하에서는 글자를 0.78rem으로 줄인다.
2. **제품 카테고리 타일의 이중 스크롤 (≤560px)**
   - 문제: 타일 높이가 380px로 고정돼 안쪽 스크롤이 생긴다.
   - 수정:
     - 모바일에서 타일 높이를 `auto`로 풀고 앞의 4개 행만 보인다.
     - 타일 아래에 `.product-cat-tile-more` 버튼("전체 보기 (N) →")을 둔다.
     - 버튼은 헤더 클릭과 같은 핸들러를 쓴다. ko/en 페이지 스크립트 셀렉터에 추가한다.
     - 데스크톱에서는 버튼을 숨긴다.
3. **제품 목록 검색창 아래 이중 선**
   - 수정: `.product-filter-bar`의 `border-bottom`을 제거해 제품 상세 검색창과 맞춘다.
   - 기존 테스트는 sticky, top, padding, 배경만 검사하므로 영향이 없다.

## 검증
- `products-v2`, `site-header-footer`, `product-filter-bar-mobile-sticky` 테스트
- 빌드
- 브라우저 375px과 데스크톱 폭에서 다음을 확인한다.
  - `/en/` 메뉴
  - `/ko/products/` 타일과 "전체 보기" 클릭 동작

## 커밋
`fix: mobile nav wrap, product tile scroll and filter bar rule`

---

## 실행 결과 (2026-10-15)

- 검증: products-v2·site-header-footer·product-filter-bar-mobile-sticky 통과, 빌드 성공. 브라우저 375px: /en/ 메뉴 한 줄, /en/products/ 타일 4개 + "See all N →" 클릭 시 ?cat= 필터 뷰 전환, 페이지 가로 넘침 0. 데스크톱(1024px): 타일 높이·레이아웃 변화 없음, 전체 보기 버튼 숨김.
