# AI 용어집 메인 페이지 리디자인 — 하이브리드 설계

> Status: Approved (2026-03-16)
> Pattern: 카테고리 프리뷰 메인 + 별도 카테고리 페이지

## Context

현재 용어집 메인 페이지는 96+ 용어를 모두 평면 나열하고 pill 버튼으로 필터링. 유저가 어떤 카테고리에 어떤 용어가 있는지 한눈에 파악하기 어려움. AI 제품군 페이지처럼 카테고리별 프리뷰 + 별도 카테고리 페이지로 리디자인.

## 디자인

### 1. 메인 페이지 (`/{locale}/handbook/`)

#### 구조 (위에서 아래로)
1. **신문 masthead** (기존 유지): "AI 용어집", "CS · AI · Infra", subkicker
2. **통계 배지**: "96+ 용어 · 11 카테고리"
3. **검색창** (기존 sticky 유지)
4. **카테고리 필터 pills** (기존 유지 — 아이콘 포함 pill, 클릭 시 프리뷰 섹션으로 스크롤)
5. **카테고리 프리뷰 섹션** (11개 반복):
   - 카테고리 아이콘 + 이름 + 용어 수
   - "모두 보기 →" 버튼 → `/handbook/category/{cat-slug}/`
   - 용어 카드 그리드 (4개 프리뷰)
6. **검색 결과 뷰** (검색 시 프리뷰 숨기고 전체 리스트 표시)

#### 데이터
- 기존 `handbook_terms` 쿼리에서 카테고리별 그룹핑 (products 패턴 참고)
- `getHandbookPageData(locale)` 헬퍼 함수 생성 (productsPage.ts 패턴)
- 반환: `{ categories, termsByCategory, totalTerms }`

### 2. 카테고리 페이지 (`/{locale}/handbook/category/[slug].astro`)

#### 구조
1. **뒤로가기 링크**: "← 용어집"
2. **카테고리 헤더**: 아이콘 + 이름 + 설명 + 용어 수
3. **카테고리 내 검색** (선택사항)
4. **전체 용어 카드 리스트** (기존 handbook-card 스타일 재사용)
5. **사이드바**: 다른 카테고리 링크 목록 (HandbookListRail 패턴 재사용)

#### 데이터
- `handbook_terms` WHERE categories @> '{ai-ml}' AND status = 'published'
- 사이드바: 전체 카테고리 목록 (`getHandbookCategories()`)

### 3. 카테고리 설명 데이터

- `handbookCategories.ts`에 `description_ko`/`description_en` 필드 추가
- 각 카테고리의 한 줄 설명 (카테고리 페이지 헤더용)

## 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/lib/pageData/handbookPage.ts` | 신규 — 메인 페이지 데이터 헬퍼 |
| `frontend/src/lib/handbookCategories.ts` | 카테고리 설명 추가 |
| `frontend/src/pages/ko/handbook/index.astro` | 메인 페이지 리디자인 |
| `frontend/src/pages/en/handbook/index.astro` | 동일 |
| `frontend/src/pages/ko/handbook/category/[slug].astro` | 신규 — 카테고리 페이지 |
| `frontend/src/pages/en/handbook/category/[slug].astro` | 신규 |
| `frontend/src/styles/global.css` | 카테고리 프리뷰 섹션 CSS |

## 검증

1. `cd frontend && npm run build`
2. 메인 → 카테고리 프리뷰 섹션 11개 표시
3. "모두 보기" 클릭 → 카테고리 페이지 이동
4. 카테고리 페이지 → 해당 카테고리 용어만 표시
5. 검색 → 프리뷰 숨기고 전체 리스트 표시
6. 모바일 반응형 확인
