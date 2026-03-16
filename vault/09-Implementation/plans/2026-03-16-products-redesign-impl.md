# AI Products 페이지 리디자인 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** AI Products 목록 페이지를 Replicate explore 스타일의 대시보드/디스커버리 UI로 리디자인한다.

**Architecture:** 기존 카테고리별 섹션 레이아웃을 Featured Spotlight(1개) + Sticky 필터바 + 플랫 그리드로 교체. 카드를 스크린샷/프리뷰 중심으로 리디자인. DB 스키마 변경 없이 프론트엔드만 변경.

**Tech Stack:** Astro v5, Tailwind CSS v4 (global.css 커스텀), Supabase, vanilla JS

**Design doc:** `vault/09-Implementation/plans/2026-03-16-products-redesign-design.md`

---

## Task 1: Data Layer — `productsPage.ts` 쿼리 변경

**Files:**
- Modify: `frontend/src/lib/pageData/productsPage.ts`

**Step 1: ProductCardData 타입에 필드 추가**

`ProductCardData` 인터페이스에 `demo_media`와 `view_count` 추가:

```ts
export interface ProductCardData {
  id: string;
  slug: string;
  name: string;
  tagline: string | null;
  logo_url: string | null;
  thumbnail_url: string | null;
  pricing: string | null;
  platform: string[] | null;
  korean_support: boolean;
  primary_category: string;
  featured: boolean;
  featured_order: number | null;
  demo_media: Array<{ type: string; url: string }> | null;  // NEW
  view_count: number;  // NEW
}
```

**Step 2: CARD_COLUMNS에 새 필드 추가**

```ts
const CARD_COLUMNS =
  'id, slug, name, tagline, logo_url, thumbnail_url, pricing, platform, korean_support, primary_category, featured, featured_order, demo_media, view_count';
```

**Step 3: getProductsPageData 반환 구조 변경**

`productsByCategory` → `allProducts` (플랫 배열), `featuredProducts` → `spotlightProduct` (1개):

```ts
export interface ProductsPageData {
  categories: ProductCategory[];
  spotlightProduct: ProductCardData | null;
  allProducts: ProductCardData[];
  totalProducts: number;
  error: string | null;
}
```

`getProductsPageData()` 함수 본문 변경:

```ts
export async function getProductsPageData(locale: 'en' | 'ko'): Promise<ProductsPageData> {
  if (!supabase) {
    return { categories: [], spotlightProduct: null, allProducts: [], totalProducts: 0, error: null };
  }

  const [categoriesRes, productsRes] = await Promise.all([
    supabase.from('ai_product_categories').select('*').order('sort_order'),
    supabase
      .from('ai_products')
      .select(CARD_COLUMNS)
      .eq('is_published', true)
      .order('sort_order')
      .order('name'),
  ]);

  if (categoriesRes.error) {
    return { categories: [], spotlightProduct: null, allProducts: [], totalProducts: 0, error: categoriesRes.error.message };
  }

  const categories = (categoriesRes.data ?? []) as ProductCategory[];
  const allProducts = (productsRes.data ?? []) as ProductCardData[];

  const resolvedProducts = allProducts.map((p) => ({
    ...p,
    name: (locale === 'ko' ? (p as any).name_ko || p.name : p.name) as string,
    tagline: (locale === 'ko' ? (p as any).tagline_ko || p.tagline : p.tagline) as string | null,
  }));

  // Spotlight: 가장 높은 featured_order를 가진 featured 제품 1개
  const spotlightProduct = resolvedProducts
    .filter((p) => p.featured)
    .sort((a, b) => (a.featured_order ?? 99) - (b.featured_order ?? 99))[0] ?? null;

  return { categories, spotlightProduct, allProducts: resolvedProducts, totalProducts: resolvedProducts.length, error: null };
}
```

**Step 4: Build check**

Run: `cd frontend && npx astro check 2>&1 | head -20`
Expected: 타입 에러 발생 (페이지에서 아직 이전 구조 참조). 이것은 다음 태스크에서 수정.

**Step 5: Commit**

```bash
git add frontend/src/lib/pageData/productsPage.ts
git commit -m "feat(products): refactor data layer for flat grid redesign"
```

---

## Task 2: ProductSpotlight 컴포넌트 신규 작성

**Files:**
- Create: `frontend/src/components/products/ProductSpotlight.astro`

**Step 1: 컴포넌트 작성**

```astro
---
import type { ProductCardData } from '../../lib/pageData/productsPage';

interface Props {
  product: ProductCardData | null;
  locale: 'en' | 'ko';
}

const { product, locale } = Astro.props;
if (!product) return;

const pricingLabel: Record<string, string> = {
  free: locale === 'ko' ? '무료' : 'Free',
  freemium: 'Freemium',
  paid: locale === 'ko' ? '유료' : 'Paid',
  enterprise: locale === 'ko' ? '기업용' : 'Enterprise',
};

// 이미지 우선순위: demo_media[0] (image) > thumbnail_url > null
const firstImage = product.demo_media?.find((m) => m.type === 'image');
const imageUrl = firstImage?.url ?? product.thumbnail_url;
const ctaLabel = locale === 'ko' ? '자세히 보기' : 'View Details';
---

<section class="product-spotlight">
  <a href={`/${locale}/products/${product.slug}/`} class="product-spotlight-link">
    <div class="product-spotlight-image-wrap">
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={product.name}
          class="product-spotlight-image"
          loading="eager"
        />
      ) : (
        <div class="product-spotlight-image-fallback" data-category={product.primary_category}>
          {product.logo_url ? (
            <img src={product.logo_url} alt="" class="product-spotlight-fallback-logo" />
          ) : (
            <span class="product-spotlight-fallback-initial">{product.name.charAt(0)}</span>
          )}
        </div>
      )}
    </div>
    <div class="product-spotlight-info">
      <h2 class="product-spotlight-name">{product.name}</h2>
      {product.tagline && <p class="product-spotlight-tagline">{product.tagline}</p>}
      <div class="product-spotlight-meta">
        {product.pricing && (
          <span class="product-pricing-badge" data-pricing={product.pricing}>
            {pricingLabel[product.pricing] ?? product.pricing}
          </span>
        )}
        <span class="product-spotlight-cta">{ctaLabel} &rarr;</span>
      </div>
    </div>
  </a>
</section>
```

**Step 2: Commit**

```bash
git add frontend/src/components/products/ProductSpotlight.astro
git commit -m "feat(products): add ProductSpotlight component"
```

---

## Task 3: ProductFilterBar 컴포넌트 신규 작성

**Files:**
- Create: `frontend/src/components/products/ProductFilterBar.astro`

**Step 1: 컴포넌트 작성**

```astro
---
import type { ProductCategory } from '../../lib/pageData/productsPage';
import { t } from '../../i18n/index';
import { getCategoryIcon } from '../../lib/productCategoryIcons';

interface Props {
  categories: ProductCategory[];
  locale: 'en' | 'ko';
}

const { categories, locale } = Astro.props;
const tr = t[locale];
---

<div class="product-filter-bar">
  <nav class="product-filter-tabs" aria-label={tr['products.title']}>
    <button class="product-filter-tab active" data-category="all" type="button">
      {tr['products.categoryAll']}
    </button>
    {categories.map((cat) => (
      <button
        class="product-filter-tab"
        data-category={cat.id}
        type="button"
      >
        <span class="product-filter-tab-icon" set:html={getCategoryIcon(cat.id)} />
        <span>{locale === 'ko' ? cat.label_ko : cat.label_en}</span>
      </button>
    ))}
  </nav>
  <div class="product-filter-search">
    <input
      type="search"
      id="product-search"
      class="handbook-search-input"
      placeholder={tr['products.searchPlaceholder']}
      aria-label={tr['products.searchPlaceholder']}
      autocomplete="off"
      data-placeholder-hints={JSON.stringify(
        locale === 'ko'
          ? ['ChatGPT, Claude, Gemini...', '이미지 생성 도구는?', '무료로 쓸 수 있는 AI는?', '코딩 도구 찾기', '영상 만드는 AI는?', '한국어 지원 AI 도구']
          : ['ChatGPT, Claude, Gemini...', 'Image generation tools', 'Free AI tools', 'Find coding assistants', 'Video creation AI', 'Korean language support']
      )}
    />
  </div>
</div>

<script>
  document.addEventListener('astro:page-load', () => {
    const tabs = document.querySelectorAll<HTMLButtonElement>('.product-filter-tab');
    if (tabs.length === 0) return;

    let activeCategory = 'all';

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const cat = tab.dataset.category ?? 'all';
        activeCategory = cat;

        // Update active tab
        tabs.forEach((t) => t.classList.toggle('active', t.dataset.category === cat));

        // Update URL
        const url = new URL(window.location.href);
        if (cat === 'all') url.searchParams.delete('cat');
        else url.searchParams.set('cat', cat);
        history.replaceState(null, '', url.toString());

        // Dispatch custom event for grid filtering
        document.dispatchEvent(new CustomEvent('product-filter', { detail: { category: cat } }));
      });
    });

    // Initialize from URL
    const urlCat = new URLSearchParams(location.search).get('cat') ?? 'all';
    if (urlCat !== 'all') {
      activeCategory = urlCat;
      tabs.forEach((t) => t.classList.toggle('active', t.dataset.category === urlCat));
      document.dispatchEvent(new CustomEvent('product-filter', { detail: { category: urlCat } }));
    }
  });
</script>
```

**Step 2: Commit**

```bash
git add frontend/src/components/products/ProductFilterBar.astro
git commit -m "feat(products): add ProductFilterBar component with category + search"
```

---

## Task 4: ProductCard 리디자인 — 스크린샷 중심

**Files:**
- Modify: `frontend/src/components/products/ProductCard.astro`

**Step 1: ProductCard.astro 전체 교체**

```astro
---
interface Props {
  href: string;
  name: string;
  tagline: string | null;
  logoUrl: string | null;
  thumbnailUrl: string | null;
  demoMediaFirst: string | null;
  pricing: string | null;
  platform: string[] | null;
  koreanSupport: boolean;
  locale: 'en' | 'ko';
  searchText?: string;
  categoryId: string;
  viewCount: number;
}

const {
  href, name, tagline, logoUrl, thumbnailUrl, demoMediaFirst,
  pricing, platform, koreanSupport, locale, searchText, categoryId, viewCount,
} = Astro.props;

const pricingLabel: Record<string, string> = {
  free: locale === 'ko' ? '무료' : 'Free',
  freemium: 'Freemium',
  paid: locale === 'ko' ? '유료' : 'Paid',
  enterprise: locale === 'ko' ? '기업용' : 'Enterprise',
};

// 이미지 우선순위: demoMediaFirst > thumbnailUrl > fallback
const imageUrl = demoMediaFirst ?? thumbnailUrl;

// 조회수 포매팅
const formatViews = (n: number) => {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
};
---

<a href={href} class="product-card" data-search-text={searchText} data-category={categoryId}>
  <div class="product-card-thumbnail">
    {imageUrl ? (
      <img src={imageUrl} alt={name} class="product-card-thumb-img" loading="lazy" />
    ) : (
      <div class="product-card-thumb-fallback" data-category={categoryId}>
        {logoUrl ? (
          <img src={logoUrl} alt="" class="product-card-thumb-fallback-logo" />
        ) : (
          <span class="product-card-thumb-fallback-initial">{name.charAt(0)}</span>
        )}
      </div>
    )}
  </div>

  <div class="product-card-body">
    <div class="product-card-header">
      {logoUrl && imageUrl && (
        <img src={logoUrl} alt="" class="product-card-logo" width="24" height="24" loading="lazy" />
      )}
      <span class="product-card-name">{name}</span>
    </div>

    {tagline && <p class="product-card-tagline">{tagline}</p>}

    <div class="product-card-meta">
      {pricing && (
        <span class="product-pricing-badge" data-pricing={pricing}>
          {pricingLabel[pricing] ?? pricing}
        </span>
      )}
      {viewCount > 0 && (
        <span class="product-card-views">{formatViews(viewCount)} views</span>
      )}
      {koreanSupport && (
        <span class="product-korean-badge">
          {locale === 'ko' ? '한국어' : 'KR'}
        </span>
      )}
    </div>
  </div>
</a>
```

**Step 2: Commit**

```bash
git add frontend/src/components/products/ProductCard.astro
git commit -m "feat(products): redesign ProductCard with screenshot-first layout"
```

---

## Task 5: EN/KO Products 페이지 재구성

**Files:**
- Modify: `frontend/src/pages/en/products/index.astro`
- Modify: `frontend/src/pages/ko/products/index.astro`

**Step 1: EN 페이지 전체 교체**

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { getProductsPageData } from '../../../lib/pageData/productsPage';
import ProductSpotlight from '../../../components/products/ProductSpotlight.astro';
import ProductFilterBar from '../../../components/products/ProductFilterBar.astro';
import ProductCard from '../../../components/products/ProductCard.astro';

const locale = 'en';
const { categories, spotlightProduct, allProducts, totalProducts, error } = await getProductsPageData(locale);

const buildSearchText = (product: typeof allProducts[0]) =>
  [
    product.name,
    product.tagline,
    product.pricing,
    product.primary_category,
    ...(product.platform ?? []),
  ].filter(Boolean).join(' ').toLowerCase();

const getFirstImageUrl = (product: typeof allProducts[0]) => {
  const first = product.demo_media?.find((m) => m.type === 'image');
  return first?.url ?? null;
};
---

<MainLayout
  title={t.en['products.title']}
  description={t.en['products.heroSubtitle']}
  locale={locale}
>
  <div class="products-page" id="products-top">
    {error && <p class="products-error">{t.en['products.error']}</p>}

    <ProductSpotlight product={spotlightProduct} locale={locale} />

    <ProductFilterBar categories={categories} locale={locale} />

    <div class="product-grid">
      {allProducts.map((product) => (
        <ProductCard
          href={`/${locale}/products/${product.slug}/`}
          name={product.name}
          tagline={product.tagline}
          logoUrl={product.logo_url}
          thumbnailUrl={product.thumbnail_url}
          demoMediaFirst={getFirstImageUrl(product)}
          pricing={product.pricing}
          platform={product.platform}
          koreanSupport={product.korean_support}
          locale={locale}
          searchText={buildSearchText(product)}
          categoryId={product.primary_category}
          viewCount={product.view_count}
        />
      ))}
    </div>

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
  </div>
</MainLayout>

<script>
  import '../../../scripts/handbookSearchHints';

  document.addEventListener('astro:page-load', () => {
    const input = document.getElementById('product-search') as HTMLInputElement | null;
    if (!input) return;
    const noResults = document.getElementById('product-search-no-results');
    const cards = Array.from(document.querySelectorAll<HTMLElement>('.product-card'));

    let currentCategory = 'all';
    let currentQuery = '';

    function applyFilters() {
      const q = currentQuery.trim().toLowerCase();
      let totalVisible = 0;

      cards.forEach((card) => {
        const text = card.dataset.searchText ?? '';
        const cat = card.dataset.category ?? '';

        const matchesCategory = currentCategory === 'all' || cat === currentCategory;
        const matchesSearch = !q || text.includes(q);
        const visible = matchesCategory && matchesSearch;

        if (visible) { card.removeAttribute('hidden'); totalVisible++; }
        else card.setAttribute('hidden', '');
      });

      if (noResults) {
        if (totalVisible === 0 && (q || currentCategory !== 'all')) noResults.removeAttribute('hidden');
        else noResults.setAttribute('hidden', '');
      }
    }

    // Search input
    input.addEventListener('input', () => {
      currentQuery = input.value;
      const url = new URL(window.location.href);
      if (currentQuery) url.searchParams.set('q', currentQuery);
      else url.searchParams.delete('q');
      history.replaceState(null, '', url.toString());
      applyFilters();
    });

    // Category filter (from ProductFilterBar)
    document.addEventListener('product-filter', ((e: CustomEvent) => {
      currentCategory = e.detail.category;
      applyFilters();
    }) as EventListener);

    // Initialize from URL
    const params = new URLSearchParams(location.search);
    const urlQ = params.get('q') ?? '';
    const urlCat = params.get('cat') ?? 'all';
    if (urlQ) { input.value = urlQ; currentQuery = urlQ; }
    if (urlCat !== 'all') currentCategory = urlCat;
    if (urlQ || urlCat !== 'all') applyFilters();
  });
</script>
```

**Step 2: KO 페이지 — 동일 구조, locale='ko'**

EN 페이지와 동일하되 다음만 변경:
- `const locale = 'ko';`
- 모든 `t.en[...]` → `t.ko[...]`
- `data-placeholder-hints`의 한국어 힌트는 ProductFilterBar 내에서 처리됨

**Step 3: Build check**

Run: `cd frontend && npx astro check 2>&1 | head -30`
Expected: 기존 컴포넌트(ProductHero, CategoryNav, CategorySection) import 제거되었으므로 에러 없어야 함.

**Step 4: Commit**

```bash
git add frontend/src/pages/en/products/index.astro frontend/src/pages/ko/products/index.astro
git commit -m "feat(products): rebuild EN/KO pages with spotlight + flat grid layout"
```

---

## Task 6: CSS — 기존 스타일 제거 + 신규 스타일 추가

**Files:**
- Modify: `frontend/src/styles/global.css`

**Step 1: 기존 CSS 제거**

`global.css`에서 다음 블록들을 제거 (line ~8118–8524):
- `.product-hero` ~ `.product-hero-stat-sep` (8118–8159)
- `.product-category-showcase` ~ 관련 responsive (8162–8275)
- `.product-hero-cards` ~ `.product-hero-card-tagline` (8277–8356)
- `.product-category-section` ~ `.product-category-empty` (8467–8523)
- `.product-category-grid` (8513–8517)
- `.product-category-header` ~ `.product-category-description` (8476–8511)
- `.product-category-nav` ~ 관련 responsive (8390–8464)

유지할 CSS:
- `.product-sticky-toolbar` (8372–8387) — 제거 (FilterBar에서 대체)
- `.product-search-bar` (8358–8370) — 제거 (FilterBar에 통합)
- `.product-pricing-badge` (8616+) — 유지
- `.product-korean-badge`, `.product-platform-*` — 유지
- `.product-card` 기존 (8526–8614) — 제거 (새 카드로 교체)
- `.product-outro*` — 유지
- `.products-page`, `.products-error`, `.products-empty` — 유지
- `.products-search-no-results` — 유지

**Step 2: 신규 CSS 추가**

제거한 자리에 다음 CSS 블록을 추가:

```css
/* ================================================================
   Products Redesign — Spotlight + FilterBar + Flat Grid
   ================================================================ */

/* --- Spotlight --- */
.product-spotlight {
  padding: 1.5rem 0 1rem;
}

.product-spotlight-link {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.2s ease;
}

.product-spotlight-link:hover {
  border-color: var(--color-accent);
}

.product-spotlight-image-wrap {
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background-color: var(--color-bg-secondary);
}

.product-spotlight-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-spotlight-image-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.product-spotlight-image-fallback[data-category="assistant"] { background: linear-gradient(135deg, #C3A370, #8B6D3F); }
.product-spotlight-image-fallback[data-category="image"] { background: linear-gradient(135deg, #7C3AED, #4338CA); }
.product-spotlight-image-fallback[data-category="video"] { background: linear-gradient(135deg, #EF4444, #DC2626); }
.product-spotlight-image-fallback[data-category="audio"] { background: linear-gradient(135deg, #10B981, #059669); }
.product-spotlight-image-fallback[data-category="coding"] { background: linear-gradient(135deg, #06B6D4, #0891B2); }
.product-spotlight-image-fallback[data-category="workflow"] { background: linear-gradient(135deg, #F59E0B, #D97706); }
.product-spotlight-image-fallback[data-category="builder"] { background: linear-gradient(135deg, #6366F1, #4F46E5); }
.product-spotlight-image-fallback[data-category="platform"] { background: linear-gradient(135deg, #64748B, #475569); }
.product-spotlight-image-fallback[data-category="research"] { background: linear-gradient(135deg, #14B8A6, #0D9488); }
.product-spotlight-image-fallback[data-category="community"] { background: linear-gradient(135deg, #F43F5E, #E11D48); }

.product-spotlight-fallback-logo {
  width: 80px;
  height: 80px;
  object-fit: contain;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,0.3));
}

.product-spotlight-fallback-initial {
  font-family: var(--font-display);
  font-size: 3rem;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.product-spotlight-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 1.5rem 1.5rem 1.5rem 0;
  gap: 0.75rem;
}

.product-spotlight-name {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.25;
}

.product-spotlight-tagline {
  font-size: 1rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.product-spotlight-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.25rem;
}

.product-spotlight-cta {
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-accent);
}

@media (max-width: 767px) {
  .product-spotlight-link {
    grid-template-columns: 1fr;
  }
  .product-spotlight-info {
    padding: 1rem;
  }
  .product-spotlight-name {
    font-size: 1.2rem;
  }
}

/* --- Filter Bar --- */
.product-filter-bar {
  position: sticky;
  top: var(--toolbar-top, 0px);
  z-index: 20;
  background: color-mix(in srgb, var(--color-bg-primary) 85%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: top 300ms ease;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0.75rem 0;
}

.product-filter-tabs {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
  padding: 0 1rem 0.5rem;
  margin: 0;
}

.product-filter-tab {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 1rem;
  font-size: 0.82rem;
  font-family: var(--font-ui);
  color: var(--color-text-secondary);
  background-color: transparent;
  text-decoration: none;
  border: 1px solid var(--color-border);
  border-radius: 9999px;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.15s ease;
}

.product-filter-tab:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border-color: var(--color-text-muted);
}

.product-filter-tab.active {
  background-color: var(--color-text-primary);
  color: var(--color-bg-primary);
  border-color: var(--color-text-primary);
  font-weight: 500;
}

.product-filter-tab-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0.75;
}

.product-filter-tab-icon svg {
  width: 14px;
  height: 14px;
}

.product-filter-search {
  max-width: 600px;
  margin: 0 auto;
  padding: 0 1rem;
  width: 100%;
}

.product-filter-search .handbook-search-input {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

@media (max-width: 767px) {
  .product-filter-tabs {
    flex-wrap: nowrap;
    justify-content: flex-start;
    overflow-x: auto;
    scrollbar-width: none;
    -webkit-mask-image: linear-gradient(to right, #000 85%, transparent);
    mask-image: linear-gradient(to right, #000 85%, transparent);
    padding-right: 2.5rem;
  }
  .product-filter-tabs::-webkit-scrollbar { display: none; }

  .product-filter-tab {
    font-size: 0.75rem;
    padding: 0.4rem 0.75rem;
  }

  .product-filter-search {
    max-width: 100%;
    padding: 0 0.75rem;
  }

  .product-filter-search .handbook-search-input {
    min-height: 2.5rem;
    font-size: 0.85rem;
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
  }
}

/* --- Flat Product Grid --- */
.product-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  padding: 1.5rem 0;
}

@media (max-width: 1279px) {
  .product-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 767px) {
  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }
}

@media (max-width: 479px) {
  .product-grid {
    grid-template-columns: 1fr;
  }
}

/* --- Product Card (redesigned) --- */
.product-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  background-color: var(--color-bg-primary);
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.product-card:hover {
  border-color: var(--color-accent);
  transform: translateY(-2px);
}

.product-card:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.product-card[hidden] {
  display: none;
}

.product-card-thumbnail {
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background-color: var(--color-bg-secondary);
}

.product-card-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s ease;
}

.product-card:hover .product-card-thumb-img {
  transform: scale(1.03);
}

.product-card-thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Category gradient fallbacks */
.product-card-thumb-fallback[data-category="assistant"] { background: linear-gradient(135deg, #C3A370, #8B6D3F); }
.product-card-thumb-fallback[data-category="image"] { background: linear-gradient(135deg, #7C3AED, #4338CA); }
.product-card-thumb-fallback[data-category="video"] { background: linear-gradient(135deg, #EF4444, #DC2626); }
.product-card-thumb-fallback[data-category="audio"] { background: linear-gradient(135deg, #10B981, #059669); }
.product-card-thumb-fallback[data-category="coding"] { background: linear-gradient(135deg, #06B6D4, #0891B2); }
.product-card-thumb-fallback[data-category="workflow"] { background: linear-gradient(135deg, #F59E0B, #D97706); }
.product-card-thumb-fallback[data-category="builder"] { background: linear-gradient(135deg, #6366F1, #4F46E5); }
.product-card-thumb-fallback[data-category="platform"] { background: linear-gradient(135deg, #64748B, #475569); }
.product-card-thumb-fallback[data-category="research"] { background: linear-gradient(135deg, #14B8A6, #0D9488); }
.product-card-thumb-fallback[data-category="community"] { background: linear-gradient(135deg, #F43F5E, #E11D48); }

.product-card-thumb-fallback-logo {
  width: 48px;
  height: 48px;
  object-fit: contain;
  filter: drop-shadow(0 2px 6px rgba(0,0,0,0.3));
}

.product-card-thumb-fallback-initial {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 2px 6px rgba(0,0,0,0.3);
}

.product-card-body {
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
}

.product-card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.product-card-logo {
  width: 24px;
  height: 24px;
  object-fit: contain;
  border-radius: 4px;
  flex-shrink: 0;
}

.product-card-name {
  font-family: var(--font-ui);
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-card-tagline {
  font-size: 0.78rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: auto;
}

.product-card-views {
  font-size: 0.72rem;
  font-family: var(--font-ui);
  color: var(--color-text-muted);
}
```

**Step 3: Build check**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: Build succeeds with 0 errors.

**Step 4: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat(products): replace products CSS with spotlight + flat grid styles"
```

---

## Task 7: 미사용 컴포넌트 정리

**Files:**
- Delete: `frontend/src/components/products/ProductHero.astro`
- Delete: `frontend/src/components/products/CategoryNav.astro`
- Delete: `frontend/src/components/products/CategorySection.astro`

**Step 1: 삭제 전 참조 확인**

Run: `grep -r "ProductHero\|CategoryNav\|CategorySection" frontend/src/pages/ frontend/src/components/`
Expected: 참조 없음 (이전 태스크에서 페이지를 이미 변경했으므로).

**Step 2: 파일 삭제**

```bash
rm frontend/src/components/products/ProductHero.astro
rm frontend/src/components/products/CategoryNav.astro
rm frontend/src/components/products/CategorySection.astro
```

**Step 3: Build check**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: 0 errors.

**Step 4: Commit**

```bash
git add -u frontend/src/components/products/
git commit -m "chore(products): remove replaced ProductHero, CategoryNav, CategorySection"
```

---

## Task 8: 최종 검증 — Build + 시각 확인

**Step 1: Full build**

Run: `cd frontend && npm run build`
Expected: 0 errors.

**Step 2: Dev 서버로 시각 확인**

Run: `cd frontend && npm run dev`

확인 사항:
- [ ] `/en/products/` — Spotlight 카드 표시, 필터바 sticky, 그리드 4열
- [ ] `/ko/products/` — 동일 구조, 한국어 텍스트
- [ ] 카테고리 탭 클릭 → 그리드 필터링 동작
- [ ] 검색 입력 → 필터링 동작
- [ ] 카테고리 + 검색 조합 동작
- [ ] 모바일 뷰포트 — 그리드 2→1열, 탭 가로 스크롤
- [ ] 이미지 없는 카드 — 카테고리 그라디언트 fallback 표시
- [ ] 4개 테마 (dark, light, pink, midnight) 모두 정상 렌더링
- [ ] `/en/products/[slug]` — 상세 페이지 영향 없음

**Step 3: Final commit (if any fix needed)**

```bash
git commit -m "fix(products): address visual QA issues from redesign"
```
