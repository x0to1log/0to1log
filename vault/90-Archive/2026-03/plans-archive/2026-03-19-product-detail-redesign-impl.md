# Product Detail Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the AI product detail page to use a 2-column Hero (name+tagline left, logo+meta right) with story-flow section ordering (About → Features → UseCases → Getting Started → Pricing → News → Similar → FAQ).

**Architecture:** Pure frontend change — rewrite `ProductDetail.astro` HTML structure and update `global.css` CSS classes. No DB schema changes, no backend changes, no new data fetching.

**Tech Stack:** Astro v5, Tailwind-style CSS custom classes in `global.css`, server-side rendering (SSR)

**Spec:** `vault/09-Implementation/plans/2026-03-19-product-detail-redesign-design.md`

---

## File Map

| File | Change |
|------|--------|
| `frontend/src/components/products/ProductDetail.astro` | Full rewrite of HTML structure: Hero 2-col, Tags row, section reorder |
| `frontend/src/styles/global.css` | New/updated CSS: `.product-detail-hero`, `.product-detail-hero-left`, `.product-detail-hero-right`, `.product-detail-tags-row`, mobile breakpoint |

---

## Chunk 1: CSS — Hero 2-Column Layout

### Task 1: Rewrite Hero CSS in global.css

**Files:**
- Modify: `frontend/src/styles/global.css` (around line 10499)

- [ ] **Step 1: Locate the existing hero CSS block**

Open `frontend/src/styles/global.css` and find the block starting at `.product-detail-hero` (around line 10499).
Current structure has: `.product-detail-hero`, `.product-detail-hero-left`, `.product-detail-logo`, `.product-detail-hero-text`, `.product-detail-hero-actions`

- [ ] **Step 2: Replace hero CSS with 2-column layout**

Replace from `.product-detail-hero {` through the end of `.product-detail-hero-actions { ... }` with:

```css
/* Hero — 2컬럼 C-1: left (flex:3) name+tagline+CTA, right (flex:1) logo+meta */
.product-detail-hero {
  display: flex;
  align-items: flex-start;
  gap: 2rem;
  padding: 2rem 0 1rem;
}

.product-detail-hero-left {
  flex: 3;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

.product-detail-hero-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  flex-shrink: 0;
}

.product-detail-logo {
  width: 72px;
  height: 72px;
  object-fit: contain;
  border-radius: 14px;
  background: #fff;
  padding: 6px;
  flex-shrink: 0;
}

.product-detail-logo-fallback {
  width: 72px;
  height: 72px;
  border-radius: 14px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.product-detail-hero-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.product-detail-name {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.15;
}

.product-detail-name-ko {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  font-weight: 400;
}

.product-detail-tagline {
  font-size: 1rem;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.5;
  margin-top: 0.25rem;
}

.product-detail-hero-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.25rem;
}

/* Hero right column: platform chips + stats */
.product-detail-hero-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
}

.product-detail-hero-platforms {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.3rem;
}

.product-detail-hero-stats {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: center;
}

.product-detail-hero-stat {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
```

- [ ] **Step 3: Add Tags row CSS** (add immediately after the hero block above)

```css
/* Tags row — category link + tags, below Hero */
.product-detail-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0.75rem 0;
  border-top: 1px solid var(--color-border);
}
```

- [ ] **Step 4: Remove or repurpose the old Meta Chips block**

Find `.product-detail-meta {` (around line 10585) and delete the entire block including `.product-detail-meta`, `.product-detail-meta-row`. Keep `.product-detail-chip` and all its variants (`.product-detail-chip--category`, `--accent`, `--muted`, `--tag`, `--stat`) since they're still used in Tags row and Hero right.

- [ ] **Step 5: Update mobile breakpoint**

Find the existing mobile media query for `product-detail-hero` (around line 10696) and replace it with:

```css
@media (max-width: 639px) {
  .product-detail-hero {
    flex-direction: column;
    gap: 1rem;
  }

  .product-detail-hero-right {
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 1rem;
    width: 100%;
  }

  .product-detail-hero-meta {
    align-items: flex-start;
  }

  .product-detail-hero-platforms {
    justify-content: flex-start;
  }

  .product-detail-name {
    font-size: 1.5rem;
  }
}
```

- [ ] **Step 6: Build check (CSS only)**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: `✓ Completed` with no errors

- [ ] **Step 7: Commit CSS**

```bash
git add frontend/src/styles/global.css
git commit -m "feat(products): add 2-column hero CSS and tags-row for detail page redesign"
```

---

## Chunk 2: Astro — Rewrite ProductDetail.astro

### Task 2: Rewrite ProductDetail.astro HTML structure

**Files:**
- Modify: `frontend/src/components/products/ProductDetail.astro`

- [ ] **Step 1: Read the current file**

Read `frontend/src/components/products/ProductDetail.astro` fully before making any changes.

- [ ] **Step 2: Replace the `<article>` body**

Keep the frontmatter (lines 1–37) unchanged. Replace everything from `<article class="product-detail"...>` onwards with the new structure below:

```astro
<article class="product-detail" id="products-top">

  <!-- ① Hero: 2컬럼 C-1 -->
  <header class="product-detail-hero">
    <!-- Left: name + tagline + CTA -->
    <div class="product-detail-hero-left">
      <div class="product-detail-hero-text">
        <h1 class="product-detail-name">{product.name_original}</h1>
        {locale === 'ko' && product.name_ko && product.name_ko !== product.name_original && (
          <span class="product-detail-name-ko">{product.name_ko}</span>
        )}
        {product.tagline && (
          <p class="product-detail-tagline">{product.tagline}</p>
        )}
      </div>
      <div class="product-detail-hero-actions">
        {product.pricing && (
          <span class="product-pricing-badge" data-pricing={product.pricing}>
            {pricingLabel[product.pricing] ?? product.pricing}
          </span>
        )}
        <a
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          class="product-visit-btn"
        >
          {tr['products.visitSite']} ↗
        </a>
      </div>
    </div>

    <!-- Right: logo + platform + korean + stats -->
    <div class="product-detail-hero-right">
      {product.logo_url ? (
        <img
          src={product.logo_url}
          alt={product.name_original}
          class="product-detail-logo"
          width="72"
          height="72"
          loading="eager"
        />
      ) : (
        <div class="product-detail-logo-fallback">
          {product.name_original.charAt(0)}
        </div>
      )}
      <div class="product-detail-hero-meta">
        {product.platform && product.platform.length > 0 && (
          <div class="product-detail-hero-platforms">
            {product.korean_support && (
              <span class={`product-detail-chip product-detail-chip--accent`}>
                ✓ {locale === 'ko' ? '한국어' : 'Korean'}
              </span>
            )}
            {product.platform.map((p) => (
              <span class="product-detail-chip">{platformLabels[p] ?? p}</span>
            ))}
          </div>
        )}
        <div class="product-detail-hero-stats">
          <span class="product-detail-hero-stat">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            {product.view_count.toLocaleString()}
          </span>
          {product.like_count > 0 && (
            <span class="product-detail-hero-stat">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
              {product.like_count.toLocaleString()}
            </span>
          )}
        </div>
      </div>
    </div>
  </header>

  <!-- ② Tags 행: category + tags -->
  {(product.primary_category || (product.tags && product.tags.length > 0)) && (
    <div class="product-detail-tags-row">
      {product.primary_category && (
        <a href={`/${locale}/products/?cat=${product.primary_category}`} class="product-detail-chip product-detail-chip--category">
          {product.primary_category}
        </a>
      )}
      {product.tags && product.tags.map((tag) => (
        <span class="product-detail-chip product-detail-chip--tag">#{tag}</span>
      ))}
    </div>
  )}

  <!-- ③ Media Gallery (Hero 아래) -->
  {product.demo_media.length > 0 && (
    <MediaGallery media={product.demo_media} />
  )}

  <!-- ④–⑧ Main content sections -->
  <div class="product-detail-content">

    <!-- ④ About -->
    {htmlDescription && (
      <section class="product-detail-section">
        <h2 class="product-detail-section-title">
          {locale === 'ko' ? '소개' : 'About'}
        </h2>
        <div class="product-detail-description prose">
          <Fragment set:html={htmlDescription} />
        </div>
      </section>
    )}

    <!-- ⑤ Key Features -->
    {features.length > 0 && (
      <section class="product-detail-section">
        <h2 class="product-detail-section-title">
          {locale === 'ko' ? '주요 기능' : 'Key Features'}
        </h2>
        <ul class="product-detail-feature-list">
          {features.map((f) => <li>{f}</li>)}
        </ul>
      </section>
    )}

    <!-- ⑥ Use Cases -->
    {useCases.length > 0 && (
      <section class="product-detail-section">
        <h2 class="product-detail-section-title">
          {locale === 'ko' ? '이런 상황에 추천' : 'Use Cases'}
        </h2>
        <ul class="product-detail-usecase-list">
          {useCases.map((u) => <li>{u}</li>)}
        </ul>
      </section>
    )}

    <!-- ⑦ Getting Started -->
    {gettingStarted.length > 0 && (
      <section class="product-detail-section">
        <h2 class="product-detail-section-title">
          {locale === 'ko' ? '시작하는 법' : 'Getting Started'}
        </h2>
        <ol class="product-detail-steps">
          {gettingStarted.map((step, i) => (
            <li>
              <span class="product-detail-step-num">{i + 1}</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </section>
    )}

    <!-- ⑧ Pricing 상세 -->
    {pricingDetailMd && (
      <section class="product-detail-section">
        <h2 class="product-detail-section-title">
          {locale === 'ko' ? '가격 정보' : 'Pricing'}
        </h2>
        <div class="product-detail-pricing-table" set:html={pricingDetailMd} />
      </section>
    )}

  </div>

  <!-- ⑨ Related News -->
  {relatedNews.length > 0 && (
    <section class="product-detail-section">
      <h2 class="product-detail-section-title">
        {locale === 'ko' ? '관련 뉴스' : 'Related News'}
      </h2>
      <ul class="product-detail-news-list">
        {relatedNews.map((news) => (
          <li>
            <a href={`/${locale}/news/${news.slug}/`}>{news.title}</a>
          </li>
        ))}
      </ul>
    </section>
  )}

  <!-- ⑩ Similar Tools -->
  {alternatives.length > 0 && (
    <section class="product-detail-section product-detail-alternatives">
      <h2 class="product-detail-section-title">
        {locale === 'ko' ? '비슷한 도구' : 'Similar Tools'}
      </h2>
      <div class="product-grid product-grid--preview">
        {alternatives.map((alt) => {
          const firstImg = alt.demo_media?.find((m) => m.type === 'image');
          return (
            <ProductCard
              href={`/${locale}/products/${alt.slug}/`}
              name={alt.name_original ?? alt.name}
              tagline={alt.tagline}
              logoUrl={alt.logo_url}
              thumbnailUrl={alt.thumbnail_url}
              demoMediaFirst={firstImg?.url ?? null}
              pricing={alt.pricing}
              platform={alt.platform}
              koreanSupport={alt.korean_support}
              locale={locale}
              categoryId={alt.primary_category}
              viewCount={alt.view_count}
            />
          );
        })}
      </div>
    </section>
  )}

  <!-- ⑪ FAQ -->
  <section class="product-detail-section product-detail-faq">
    <h2 class="product-detail-section-title">FAQ</h2>

    {product.pricing && (
      <details class="product-faq-item">
        <summary>
          {locale === 'ko'
            ? `${product.name_original}은(는) 무료인가요?`
            : `Is ${product.name_original} free?`}
        </summary>
        <p>
          {product.pricing === 'free'
            ? (locale === 'ko' ? '네, 무료로 사용할 수 있습니다.' : 'Yes, it is completely free to use.')
            : product.pricing === 'freemium'
              ? (locale === 'ko' ? '무료 플랜과 유료 플랜이 있습니다.' : 'It offers both free and paid plans.')
              : product.pricing === 'paid'
                ? (locale === 'ko' ? '유료 서비스입니다.' : 'It is a paid service.')
                : (locale === 'ko' ? '기업용 요금제입니다.' : 'Enterprise pricing. Contact sales.')}
          {product.pricing_note && ` ${product.pricing_note}`}
        </p>
      </details>
    )}

    {product.platform && product.platform.length > 0 && (
      <details class="product-faq-item">
        <summary>
          {locale === 'ko'
            ? `어떤 플랫폼에서 사용할 수 있나요?`
            : `What platforms is ${product.name_original} available on?`}
        </summary>
        <p>
          {locale === 'ko'
            ? `${product.platform.map(p => platformLabels[p] ?? p).join(', ')}에서 사용 가능합니다.`
            : `Available on ${product.platform.map(p => platformLabels[p] ?? p).join(', ')}.`}
        </p>
      </details>
    )}

    <details class="product-faq-item">
      <summary>
        {locale === 'ko'
          ? `한국어를 지원하나요?`
          : `Does ${product.name_original} support Korean?`}
      </summary>
      <p>
        {product.korean_support
          ? (locale === 'ko' ? '네, 한국어 UI를 지원합니다.' : 'Yes, it supports Korean language.')
          : (locale === 'ko' ? '현재 한국어는 지원하지 않습니다.' : 'Korean is not currently supported.')}
      </p>
    </details>
  </section>

  <!-- ⑫ Bottom CTA -->
  <div class="product-detail-bottom-cta">
    <a
      href={product.url}
      target="_blank"
      rel="noopener noreferrer"
      class="product-visit-btn product-visit-btn--large"
    >
      {product.name_original} {tr['products.visitSite']} ↗
    </a>
  </div>

  <slot />
</article>
```

- [ ] **Step 3: Build check**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: `✓ Completed` with no errors

- [ ] **Step 4: Commit Astro**

```bash
git add frontend/src/components/products/ProductDetail.astro
git commit -m "feat(products): rewrite detail page to C-1 hero layout and story-flow section order"
```

---

## Chunk 3: Verification

### Task 3: Manual verification checklist

- [ ] **Step 1: Start dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: Check a product WITH logo and demo_media**

Open `http://localhost:4321/ko/products/chatgpt/` (or any product with logo + screenshots)

Verify:
- Hero: 이름+tagline+CTA가 왼쪽, 로고+platform+stats가 오른쪽
- Tags 행이 Hero 아래 별도 행으로 표시됨
- Media Gallery가 Tags 행 아래에 위치함
- 섹션 순서: About → Key Features → Use Cases → Getting Started → Pricing → Related News → Similar Tools → FAQ

- [ ] **Step 3: Check a product WITHOUT logo**

Open a product that has no `logo_url`.

Verify:
- 우측에 이니셜 문자가 흰 배경 박스에 표시됨

- [ ] **Step 3b: Check a product WITHOUT demo_media**

Open a product that has no screenshots/videos (most products currently).

Verify:
- Media Gallery 섹션이 표시되지 않음
- Tags 행 바로 아래 About 섹션이 시작됨
- 레이아웃이 깨지지 않음

- [ ] **Step 4: Check mobile layout (DevTools)**

DevTools에서 width 390px (iPhone 14)로 변경

Verify:
- Hero가 단일 컬럼으로 fallback됨 (이름 먼저, 로고+메타 아래)
- Tags 행이 줄바꿈됨

- [ ] **Step 5: EN 페이지 확인**

Open `http://localhost:4321/en/products/chatgpt/`

Verify:
- `name_ko` 서브텍스트가 표시되지 않음 (EN 페이지에는 불필요)

- [ ] **Step 6: Final push**

```bash
git push origin main
```
