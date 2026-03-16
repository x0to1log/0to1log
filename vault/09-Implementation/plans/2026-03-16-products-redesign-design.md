# AI Products 페이지 리디자인 — 대시보드/디스커버리 스타일

> Date: 2026-03-16
> Status: Approved
> Feature: AI Products 페이지 리디자인
> Reference: Replicate explore 페이지 (`replicate.com/explore`)
> 이전 설계: `vault/09-Implementation/plans/2026-03-15-ai-products-design.md`

---

## 동기

현재 AI Products 페이지는 "매거진 + 카탈로그" 스타일 — Hero 캐러셀 → 카테고리별 섹션 분리 → 각 섹션 내 카드 그리드. Replicate explore 페이지의 대시보드/디스커버리 느낌으로 리디자인:
- 스크린샷/비주얼 중심 카드
- 카테고리 섹션 분리 제거 → 플랫 그리드 + 필터 탭
- Featured spotlight 1개 → 바로 탐색 흐름

---

## 결정 사항 요약

| 항목 | 현재 | 변경 후 | 이유 |
|---|---|---|---|
| 페이지 흐름 | Hero(5개) → 카테고리 네비 → 카테고리별 섹션 | Spotlight(1개) → 필터바 → 플랫 그리드 | 탐색 중심 UX |
| 카드 비주얼 | 40×40 로고 + 텍스트 중심 | 큰 스크린샷(demo_media) + 태그라인 prominent | Replicate 스타일 정보 밀도 |
| 카테고리 표시 | 섹션 분리 (anchor scroll) | 필터 탭 (클릭 시 그리드 필터링) | 플랫 그리드 패턴 |
| 이미지 없는 제품 | 이니셜 placeholder | 카테고리 그라디언트 배경 + 큰 로고 | 시각적 풍부함 유지 |
| 데이터 레이어 | 변경 없음 | 변경 없음 | 기존 Supabase 쿼리 재사용 |

---

## 페이지 구조

```
┌─────────────────────────────────────────────┐
│  Featured Spotlight (1개 제품, 와이드 카드)    │
│  ┌───────────────────────────────────────┐   │
│  │ [스크린샷 크게]                        │   │
│  │ 제품명 · 태그라인 · 가격 · CTA        │   │
│  └───────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│  Filter Bar (sticky)                         │
│  [전체] [어시스턴트] [이미지] [...] | 🔍검색  │
├─────────────────────────────────────────────┤
│  Flat Product Grid                           │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │[스샷] │ │[스샷] │ │[그라] │ │[스샷] │       │
│  │이름   │ │이름   │ │이름   │ │이름   │       │
│  │태그라인│ │태그라인│ │태그라인│ │태그라인│       │
│  │뱃지   │ │뱃지   │ │뱃지   │ │뱃지   │       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│  (4열 데스크탑 / 3열 태블릿 / 2열 모바일)     │
├─────────────────────────────────────────────┤
│  Outro                                       │
└─────────────────────────────────────────────┘
```

---

## 컴포넌트 변경 상세

### 1. ProductSpotlight.astro (신규, ProductHero 대체)

Featured 제품 1개를 와이드 카드로 표시.

```
Props:
  product: ProductCardData (featured_order=1인 제품)
  locale: 'en' | 'ko'

레이아웃:
  - 와이드 카드 (전체 폭, 높이 ~280px)
  - 좌: 스크린샷 (demo_media[0] 또는 thumbnail_url)
  - 우: 제품명 + 태그라인 (큰 폰트) + 가격 뱃지 + "자세히 보기" CTA
  - Fallback (이미지 없음): 카테고리 그라디언트 배경
  - 모바일: 세로 스택 (이미지 위, 텍스트 아래)
```

### 2. ProductFilterBar.astro (신규, CategoryNav 대체)

카테고리 필터 탭 + 검색을 하나의 sticky 바로 통합.

```
Props:
  categories: ProductCategory[]
  locale: 'en' | 'ko'

레이아웃:
  - 좌: 카테고리 필터 탭들 (수평 스크롤, "전체" 포함)
  - 우: 검색 입력창
  - sticky (top 고정, z-index)

동작:
  - 탭 클릭 → JS로 그리드 내 카드 show/hide (카테고리 필터)
  - 검색 입력 → 기존 data-search-text 기반 필터링
  - "전체" 탭: 모든 카드 표시
  - 활성 탭 하이라이트 (accent 색상)
  - 필터 + 검색 조합 가능 (AND 조건)
```

### 3. ProductCard.astro (리디자인)

기존 로고+텍스트 카드를 스크린샷 중심으로 재구성.

```
변경 Props (추가):
  thumbnailUrl: string | null  (이미지 프리뷰)
  demoMediaFirst: string | null (demo_media[0].url)
  categoryId: string  (필터링 + fallback 그라디언트용)
  viewCount: number (조회수 표시)

레이아웃:
  ┌──────────────────────┐
  │                      │
  │  스크린샷 / 프리뷰    │  ← 카드 상단 60%
  │  (aspect-ratio 16/10) │
  │                      │
  ├──────────────────────┤
  │ 로고(24px) 제품명     │  ← 카드 하단 40%
  │ 태그라인 (2줄 clamp)  │
  │ 가격뱃지 · 조회수     │
  └──────────────────────┘

이미지 우선순위:
  1. demoMediaFirst (demo_media[0].url, type=image인 경우)
  2. thumbnailUrl (thumbnail_url)
  3. Fallback: 카테고리별 CSS 그라디언트 + 큰 로고/이니셜

Fallback 그라디언트 (카테고리별):
  assistant → warm gold (#C3A370 → #8B6D3F)
  image     → violet-blue (#7C3AED → #4338CA)
  video     → coral-red (#EF4444 → #DC2626)
  audio     → emerald (#10B981 → #059669)
  coding    → cyan (#06B6D4 → #0891B2)
  workflow  → amber (#F59E0B → #D97706)
  builder   → indigo (#6366F1 → #4F46E5)
  platform  → slate (#64748B → #475569)
  research  → teal (#14B8A6 → #0D9488)
  community → rose (#F43F5E → #E11D48)
```

### 4. 제거/미사용 컴포넌트

| 컴포넌트 | 처리 |
|---|---|
| ProductHero.astro | ProductSpotlight로 대체 |
| CategoryNav.astro | ProductFilterBar로 통합 |
| CategorySection.astro | 제거 (플랫 그리드로 대체) |
| product-category-showcase 섹션 (index.astro 인라인) | 제거 |

---

## 데이터 레이어 변경

### productsPage.ts 변경

```
기존 getProductsPageData() 반환:
  { categories, featuredProducts, productsByCategory, totalProducts, error }

변경 후 getProductsPageData() 반환:
  { categories, spotlightProduct, allProducts, totalProducts, error }

변경점:
  - productsByCategory → allProducts (플랫 배열, 카테고리 분리 안 함)
  - featuredProducts(5개) → spotlightProduct(1개)
  - CARD_COLUMNS에 thumbnail_url, demo_media, view_count, primary_category 추가
```

### ProductCardData 타입 확장

```ts
// 기존 필드 유지 + 추가
export interface ProductCardData {
  // ... existing fields ...
  thumbnail_url: string | null;    // 이미 있음
  demo_media: Array<{ type: string; url: string }> | null;  // 추가
  view_count: number;              // 추가
  primary_category: string;        // 이미 있음 (필터용)
}
```

---

## 페이지 흐름 (index.astro)

```
ProductSpotlight (spotlightProduct)
  ↓
ProductFilterBar (categories, sticky)
  ↓
<div class="product-grid">
  ProductCard × N (allProducts, 필터링은 JS)
</div>
  ↓
No results 메시지
  ↓
Outro
```

### JS 동작

1. **카테고리 필터**: 탭 클릭 → `data-category` 속성 기반 show/hide
2. **검색 필터**: 입력 → `data-search-text` 기반 show/hide
3. **조합**: 카테고리 AND 검색 동시 적용
4. **URL 동기화**: `?q=검색어&cat=coding` 형태로 상태 유지

---

## 스타일 변경

### 제거할 CSS 클래스

```
.product-hero, .product-hero-*
.product-category-nav, .product-category-tab
.product-category-section, .product-category-header
.product-category-grid, .product-category-description
.product-category-showcase, .product-category-showcase-*
```

### 추가할 CSS 클래스

```css
/* Spotlight */
.product-spotlight { ... }
.product-spotlight-image { ... }
.product-spotlight-info { ... }

/* Filter Bar */
.product-filter-bar { position: sticky; ... }
.product-filter-tabs { ... }
.product-filter-tab { ... }
.product-filter-tab.active { ... }
.product-filter-search { ... }

/* Grid */
.product-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);  /* 데스크탑 */
  gap: 1.25rem;
}

/* Card (리디자인) */
.product-card { ... }
.product-card-thumbnail { aspect-ratio: 16/10; ... }
.product-card-thumbnail-fallback { background: var(--gradient); ... }
.product-card-body { ... }
.product-card-stats { ... }

/* 반응형 */
@media (max-width: 1024px) { .product-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 768px)  { .product-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px)  { .product-grid { grid-template-columns: 1fr; } }
```

---

## 영향 범위

| 파일 | 변경 유형 |
|---|---|
| `pages/en/products/index.astro` | 구조 리디자인 |
| `pages/ko/products/index.astro` | 동일 변경 |
| `components/products/ProductSpotlight.astro` | 신규 |
| `components/products/ProductFilterBar.astro` | 신규 |
| `components/products/ProductCard.astro` | 리디자인 |
| `components/products/ProductHero.astro` | 제거 |
| `components/products/CategoryNav.astro` | 제거 |
| `components/products/CategorySection.astro` | 제거 |
| `lib/pageData/productsPage.ts` | 쿼리 변경 |
| `styles/global.css` | CSS 교체 |
| `i18n/index.ts` | 키 추가/제거 |

### 변경 없음

- `pages/en/products/[slug].astro` — 상세 페이지 그대로
- `components/products/ProductDetail.astro` — 그대로
- `components/products/MediaGallery.astro` — 그대로
- `components/products/HomeProductCard.astro` — 홈페이지 카드 그대로
- Admin 페이지 전체 — 그대로
- DB 스키마 — 변경 없음 (기존 demo_media, thumbnail_url 활용)
