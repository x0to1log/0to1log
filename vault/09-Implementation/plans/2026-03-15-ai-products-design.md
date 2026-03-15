# AI Products — 아키텍처 & 컴포넌트 설계

> Date: 2026-03-15
> Status: Approved
> Feature: AI Products 페이지
> 관련: `vault/03-Features/AI-Products.md`

---

## 결정 사항 요약

| 항목 | 결정 | 이유 |
|---|---|---|
| 레이아웃 | Magazine Landing (Option A) | Hero + 카테고리별 섹션 = 초보자 감동 극대화 |
| 상세 페이지 | 별도 `/[slug]/` 페이지 | SEO + 공유 링크 + 기존 news/handbook 패턴 일치 |
| 데이터 | Supabase DB (SSR fetch) | 어드민 관리, 동적 콘텐츠 |
| i18n | DB 다국어 필드 + i18n namespace | `/en/` `/ko/` slug 동일, locale만 분기 |

---

## 파일 구조

```
frontend/src/
├── pages/
│   ├── en/products/
│   │   ├── index.astro          # 전체 목록 (SSR)
│   │   └── [slug].astro         # 상세 페이지 (SSR)
│   └── ko/products/
│       ├── index.astro
│       └── [slug].astro
│
├── components/products/
│   ├── ProductHero.astro         # Hero 섹션 (featured 제품 대형 카드)
│   ├── CategoryNav.astro         # sticky 카테고리 탭 (전체/이미지/영상/...)
│   ├── CategorySection.astro     # 카테고리 에디토리얼 + 카드 리스트
│   ├── ProductCard.astro         # 목록용 카드
│   ├── ProductDetail.astro       # 상세 페이지 레이아웃
│   └── MediaGallery.astro        # 이미지/영상 슬라이드
│
└── lib/pageData/
    └── productsPage.ts           # DB fetch 함수 모음
```

---

## 데이터 흐름

```
index.astro (SSR, prerender = false)
  └─ productsPage.ts
       ├─ fetchFeaturedProducts()     → ProductHero
       ├─ fetchCategories()           → CategoryNav + CategorySection headers
       └─ fetchProductsByCategory()   → ProductCard ×N per category

[slug].astro (SSR, prerender = false)
  └─ fetchProductBySlug(slug)         → ProductDetail + MediaGallery
       └─ 404 redirect if not found
```

---

## 컴포넌트 상세

### ProductHero.astro
- featured 제품 최대 5개, 대형 카드 레이아웃
- 썸네일 배경 + 이름 + tagline + 가격 배지 + "자세히 보기" 링크
- 데스크탑: 가로 슬라이드 or 그리드. 모바일: 세로 스택

### CategoryNav.astro
- 페이지 스크롤 시 sticky 고정
- 탭 클릭 → 해당 카테고리 섹션으로 앵커 스크롤
- 활성 카테고리 하이라이트 (IntersectionObserver로 감지)

### CategorySection.astro
- 카테고리 아이콘 + 이름 + 에디토리얼 설명 (2~3줄)
- 제품 카드 그리드 (3열 데스크탑 / 2열 태블릿 / 1열 모바일)

### ProductCard.astro
- 로고 + 이름 + 가격 배지 (무료/Freemium/유료)
- tagline 한 줄 + 플랫폼 아이콘 + 한국어 지원 여부
- hover 시 간단한 팝오버 미리보기

### ProductDetail.astro
- 상단: 로고 + 이름 + tagline + "사이트 방문" CTA
- MediaGallery: 이미지/영상 슬라이드
- 에디토리얼 설명 (마크다운 렌더링)
- 가격 정보 + 플랫폼 + 출시일 + 한국어 지원
- 태그 목록 + 좋아요 버튼

### MediaGallery.astro
- demo_media jsonb 배열을 순회
- type=image → `<img>`, type=video → `<video>` or YouTube embed
- 썸네일 클릭 → 전체 화면 lightbox (plain `<script>` 구현)

---

## i18n

`src/i18n/index.ts`에 `products` 네임스페이스 추가:

```ts
products: {
  hero_title: { en: "The AI Era: Make Anything", ko: "AI로 무엇이든 만드는 시대" },
  category_all: { en: "All", ko: "전체" },
  visit_site: { en: "Visit Site", ko: "사이트 방문" },
  free: { en: "Free", ko: "무료" },
  freemium: { en: "Freemium", ko: "Freemium" },
  paid: { en: "Paid", ko: "유료" },
  enterprise: { en: "Enterprise", ko: "기업용" },
  korean_support: { en: "Korean", ko: "한국어 지원" },
  // ...
}
```

- 제품 콘텐츠(name, tagline, description)는 DB의 `*_ko` 필드로 처리
- `*_ko` 비어있으면 EN 필드 fallback

---

## Navigation 변경


`Navigation.astro`의 `navItems` 배열에 추가:

```ts
// EN copy
{ href: '/en/products/', label: 'AI Products' }

// KO copy
{ href: '/ko/products/', label: 'AI 제품군' }
```

---

## 메인 홈 페이지 연동

`frontend/src/lib/pageData/homePage.ts`에서 `fetchFeaturedProducts(limit=5)` 호출 →
홈 페이지에 "주목할 AI 도구" 섹션으로 노출 (별도 컴포넌트).

## Related Plans

- [[plans/2026-03-15-ai-products-schema|AI Products 스키마]]
- [[plans/2026-03-15-category-nav-mobile-design|카테고리 모바일]]
