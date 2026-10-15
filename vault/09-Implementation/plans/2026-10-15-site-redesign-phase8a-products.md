# 사이트 리디자인 8a단계(제품 페이지) Implementation Plan

**Status:** in progress

**Goal:** 제품 목록·상세 페이지를 Soft Newsprint V2로 정리한다. 가격·난이도는 **결정 B**에 따라 등급 색을 점(6px)에만 쓰고, 글자는 기본색으로 둔다.

**Architecture:** `global.css`의 `.product-*` 규칙만 수정한다. 데이터 로딩, 스크립트, 찜하기와 관리자 훅, 마크업 구조는 그대로 둔다. 사용되지 않는 `.product-spotlight*` CSS는 삭제한다(`ProductSpotlight.astro`는 어디서도 import하지 않는다).

## 결정 B — 등급 점 색

| 값 | 종이/순백 | 다크 |
|---|---|---|
| free · beginner | #3F8F5E | #6FBF8A |
| freemium | #3E6FB0 | #7FA6DE |
| paid · advanced | #B4472A | #E08A6A |
| enterprise | #7A5BA8 | #A98BD6 |
| intermediate | #B8860B | #D9AE4A |

- 토큰 `--tier-*`를 `:root`에 두고, `[data-theme="dark"]`에서 다시 정의한다.
- `.product-pricing-badge`, `.product-difficulty-badge`
  - 기본 스타일: 배경·패딩·radius 없이 `inline-flex`, 굵기 600, 색 `--color-text-secondary`
  - 점: `::before`에 6px 원, 색은 `var(--dot)`
  - `[data-pricing]`, `[data-difficulty]` 값마다 `--dot`만 지정한다.
- `.product-korean-badge`도 같은 점 라벨로 바꾸고, 점 색은 accent를 쓴다.

## 보존할 훅 (Supabase 세션 인계)
- 찜하기
  - 상세: `#product-like-btn`, `.product-like-btn--active`
  - 카드: `.product-card-like`, `.product-card-like--active`
- 이미지: 이미지 lazy·decoding 속성, `public/product-logos` 파일명
- 관리자: `.newsprint-admin-actions`
- 테스트 계약
  - `.product-filter-bar`의 sticky 블록(top, padding, 불투명 배경). 이 블록에서는 그림자만 제거한다.
  - 모바일 `.product-filter-tabs` 블록
  - `product-detail-search-*`
  - `.product-detail-scenario {`가 `background: var(--color-bg-secondary`를 유지해야 한다.

## 변경 목록
1. Spotlight CSS 블록(`/* --- Spotlight --- */` ~ 모바일 미디어쿼리)을 삭제한다.
2. 필터 바·검색창
   - 필터 바와 `.product-filter-search .handbook-search-input`의 box-shadow를 제거한다.
   - `.product-filter-tab`
     - 기본: 알약 테두리와 배경 없이 텍스트만 남긴다.
     - active: 아래 4px 점으로 표시한다.
3. 카테고리 타일(목록 첫 화면)
   - `.product-cat-tile`
     - 배경, 둥근 상자, 테두리를 모두 걷어낸다.
     - 위쪽 테두리만 남긴다: `border-top: 1px solid var(--color-text-primary)`
   - `.product-cat-tile-header`: 배경을 없애고, 아래쪽 구분선을 점선으로 바꾼다.
   - `.product-cat-tile-count`: 알약 모양을 없애고 글자만 남긴다.
   - `.product-cat-row`
     - radius를 없애고 행 사이를 점선으로 나눈다.
     - hover 시 이름에 accent 색을 넣는다.
4. 제품 카드(필터·검색 결과)
   - `.product-card`
     - 상자, 그림자, translate hover를 없앤다.
     - 아래쪽만 점선 테두리로 남기고, hover 시 이름에 accent 색을 넣는다.
   - 썸네일
     - 4px radius
     - 카테고리별 그라디언트 10개를 삭제한다.
     - 대체 썸네일(fallback)은 `--color-bg-secondary` 면 위에 로고를 둔다.
     - 로고는 그림자 대신 흰 바탕에 1px border를 쓴다.
     - 이니셜은 그림자 없이 `--color-text-muted`로 표시한다.
   - 이름은 Hahmlet 600으로 바꾼다.
5. 상세
   - 이름: Hahmlet 700, `letter-spacing: -0.03em`
   - 칩
     - `.product-detail-chip`: 배경과 패딩을 없앤다. 카테고리는 굵기 600 글자만, 태그는 기존 `#tag` 텍스트를 그대로 쓴다.
     - `--accent` 칩: 점 라벨로 바꾼다.
   - 섹션 제목의 3px 막대 → 6px accent 점
   - 단계·시나리오 번호: 원 배경을 없애고 accent 숫자(Hahmlet 700)만 남긴다.
   - 시나리오 카드
     - radius는 4px로 줄인다.
     - 배경은 `var(--color-bg-secondary)`를 유지한다(테스트 계약).
   - 장단점
     - 빨강·초록을 없앤다. 제목은 muted 색에 굵기 700.
     - 항목 앞 기호: `＋`는 text-primary 색, `−`는 muted 색
     - 항목 사이를 점선으로 나눈다.
   - 에디터 노트: radius를 0으로 하고 배경을 없앤다. 2px accent 왼쪽 선은 유지한다.
   - 사이트 방문 버튼: 사이트 기본 CTA처럼 `--color-text-primary` 배경과 4px radius로 바꾼다.
   - 기능 목록 기호 ✦ → 6px accent 점

## 테스트
- 새 테스트: `frontend/tests/products-v2.test.cjs`
  - Spotlight 규칙이 없다.
  - 썸네일 fallback에 그라디언트가 없다.
  - pricing·difficulty 배지에 배경과 99px radius가 없고, `::before` 점이 있다.
  - `--tier-free` 토큰이 있다.
  - 장단점에 `#16a34a`, `#dc2626`가 없다.
- 기존 product 테스트
  - `product-detail-scenarios-theme`는 기존 실패다. `.product-detail-scenario {` 규칙이 한 줄이 아니어서 실패한다. 이번 범위가 아니다.
  - 그 밖의 기존 product 테스트는 모두 통과를 유지해야 한다.
- 기준선: PASS 68 / FAIL 23. 신규 FAIL은 없어야 한다.

## 커밋
- `feat: soft newsprint products list and detail with tier dot labels`
