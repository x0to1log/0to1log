# Homepage Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat homepage layout with a Split Hero that immediately communicates who 0to1log is for and what it does, followed by hierarchical content sections.

**Architecture:** Create `HomeSplitHero.astro` to replace `HomeMasthead` + standalone `HomeHeroCard`. Restructure both locale index pages to use the new hierarchy: SplitHero → News (with featured headline) → Glossary+Products (2-col) → Blog. Remove the redundant "Start Here" section.

**Tech Stack:** Astro v5, Tailwind CSS v4 (custom CSS via `global.css`), TypeScript, existing `getHomePageData()` from `homePage.ts` (no data layer changes)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/components/home/HomeSplitHero.astro` | CREATE | Dark Split Hero section (value prop + today's news + trending terms) |
| `frontend/src/styles/global.css` | MODIFY | Add `--color-hero-bg` token + `.home-split-hero*` styles + `.home-spotlight-grid` + remove `.home-masthead*` and `.home-start-here*` |
| `frontend/src/pages/ko/index.astro` | MODIFY | Use `HomeSplitHero`, move `HomeHeroCard` into Section B, merge Glossary+Products, remove Section F |
| `frontend/src/pages/en/index.astro` | MODIFY | Same as `ko/index.astro` for English locale |
| `frontend/src/components/home/HomeMasthead.astro` | DELETE | Replaced by `HomeSplitHero` (only imported in the two index pages) |

---

## Chunk 1: CSS + New Component

### Task 1: Add CSS Token and Split Hero Styles

**Files:**
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: (Skip — no token needed)**

  `--color-hero-bg` is NOT added to `@theme {}`. The Split Hero background is a fixed dark value that must not be overridden by any theme. Use it as a literal `#1a1a2e` directly in `.home-split-hero { background: #1a1a2e; }` in Step 2 below. Do not add anything to the `@theme` block.

- [ ] **Step 2: Add `.home-split-hero` CSS block**

  Find the `/* Masthead */` comment block (around line 8691). Add the following **before** that comment:

  ```css
  /* Split Hero */
  .home-split-hero {
    background: #1a1a2e; /* fixed dark — intentionally theme-independent */
    color: #fff;
    padding: 1.5rem 1.5rem 2rem;
  }

  .home-split-hero-wordmark {
    font-family: var(--font-ui);
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    color: #8888aa;
    text-align: center;
    margin-bottom: 1.25rem;
  }

  .home-split-hero-inner {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 1.5rem;
    align-items: start;
  }

  .home-split-hero-left {
    border-right: 1px solid #333;
    padding-right: 1.5rem;
  }

  .home-split-hero-right {
    min-width: 0;
  }

  .home-split-hero-kicker {
    font-family: var(--font-ui);
    font-size: 0.7rem;
    color: #aaa;
    margin-bottom: 0.5rem;
  }

  .home-split-hero-headline {
    font-family: var(--font-display);
    font-size: clamp(1.15rem, 2.5vw, 1.5rem);
    font-weight: 800;
    line-height: 1.3;
    color: #fff;
    margin-bottom: 0.5rem;
  }

  .home-split-hero-sub {
    font-family: var(--font-body);
    font-size: 0.7rem;
    color: #bbb;
    line-height: 1.6;
    margin-bottom: 1rem;
  }

  .home-split-hero-cta {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .home-split-hero-cta-primary {
    background: #fff;
    color: #111;
    font-family: var(--font-ui);
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.4rem 0.9rem;
    border-radius: 4px;
    text-decoration: none;
    transition: opacity 0.15s;
  }

  .home-split-hero-cta-primary:hover {
    opacity: 0.85;
  }

  .home-split-hero-cta-secondary {
    border: 1px solid #666;
    color: #ccc;
    font-family: var(--font-ui);
    font-size: 0.7rem;
    padding: 0.4rem 0.9rem;
    border-radius: 4px;
    text-decoration: none;
    transition: border-color 0.15s, color 0.15s;
  }

  .home-split-hero-cta-secondary:hover {
    border-color: #aaa;
    color: #fff;
  }

  .home-split-hero-today-label {
    font-family: var(--font-ui);
    font-size: 0.6rem;
    letter-spacing: 0.1em;
    color: #666;
    margin-bottom: 0.5rem;
  }

  .home-split-hero-news {
    background: #252540;
    border-radius: 6px;
    padding: 0.65rem;
    margin-bottom: 0.6rem;
    text-decoration: none;
    display: block;
    transition: opacity 0.15s;
  }

  .home-split-hero-news:hover {
    opacity: 0.85;
  }

  .home-split-hero-news-kicker {
    font-family: var(--font-ui);
    font-size: 0.6rem;
    color: #8888cc;
    margin-bottom: 0.3rem;
  }

  .home-split-hero-news-title {
    font-family: var(--font-display);
    font-size: 0.78rem;
    font-weight: 700;
    line-height: 1.4;
    color: #eee;
  }

  .home-split-hero-trending-label {
    font-family: var(--font-ui);
    font-size: 0.6rem;
    letter-spacing: 0.1em;
    color: #666;
    margin-bottom: 0.4rem;
  }

  .home-split-hero-terms {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.4rem;
  }

  .home-split-hero-term {
    background: #252540;
    border-radius: 4px;
    padding: 0.5rem;
  }

  .home-split-hero-term-name {
    font-family: var(--font-display);
    font-size: 0.7rem;
    font-weight: 700;
    color: #eee;
    display: block;
  }

  .home-split-hero-term-def {
    font-family: var(--font-body);
    font-size: 0.6rem;
    color: #888;
    margin-top: 0.15rem;
  }

  @media (max-width: 639px) {
    .home-split-hero-inner {
      grid-template-columns: 1fr;
    }

    .home-split-hero-left {
      border-right: none;
      padding-right: 0;
      border-bottom: 1px solid #333;
      padding-bottom: 1.25rem;
    }
  }
  ```

- [ ] **Step 3: Add `.home-spotlight-grid` CSS for the 2-col Glossary+Products section**

  Add after the Split Hero block you just added:

  ```css
  /* Glossary + Products 2-col spotlight */
  .home-spotlight-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }

  .home-spotlight-col {
    min-width: 0;
  }

  .home-spotlight-col + .home-spotlight-col {
    border-left: 1px solid var(--color-border);
    padding-left: 1.5rem;
  }

  @media (max-width: 639px) {
    .home-spotlight-grid {
      grid-template-columns: 1fr;
    }

    .home-spotlight-col + .home-spotlight-col {
      border-left: none;
      padding-left: 0;
      border-top: 1px solid var(--color-border);
      padding-top: 1.25rem;
    }
  }
  ```

- [ ] **Step 4: Verify build passes**

  ```bash
  cd frontend && npm run build 2>&1 | tail -20
  ```

  Expected: `build complete` with 0 errors (CSS-only change, should be clean).

- [ ] **Step 5: Commit**

  ```bash
  cd frontend && git add src/styles/global.css
  git commit -m "feat: add home-split-hero and home-spotlight CSS"
  ```

---

### Task 2: Create `HomeSplitHero.astro`

**Files:**
- Create: `frontend/src/components/home/HomeSplitHero.astro`

- [ ] **Step 1: Create the component**

  Create `frontend/src/components/home/HomeSplitHero.astro` with the following content:

  ```astro
  ---
  import type { HomeNewsPost, HomeHandbookTerm } from '../../lib/pageData/homePage';

  interface Props {
    locale: 'en' | 'ko';
    heroNews: HomeNewsPost | null;
    trendingTerms: HomeHandbookTerm[];
    newsHref: string;
    homeIntro?: string;
  }

  const { locale, heroNews, trendingTerms, newsHref, homeIntro } = Astro.props;
  const isKo = locale === 'ko';

  const kicker = isKo
    ? 'AI를 따라가고 싶은 개발자·기획자를 위한'
    : 'For developers and PMs who want to keep up with AI';

  const headline = isKo
    ? ['AI 뉴스 읽고,', '용어 쌓고,', '함께 해석하는 곳']
    : ['Read AI news,', 'build your vocabulary,', 'understand together'];

  const defaultIntro = isKo
    ? '빠르게 바뀌는 AI 흐름을 구독하고, 모르는 용어는 즉시 찾고, 내 아카이브를 쌓는 플랫폼'
    : 'Subscribe to fast-moving AI shifts, instantly look up terms you don\'t know, and build your own archive.';

  const subCopy = homeIntro || defaultIntro;

  const ctaPrimary = { label: isKo ? 'AI 뉴스 읽기 →' : 'Read AI News →', href: `/${locale}/news/` };
  const ctaSecondary = { label: isKo ? '용어집 보기' : 'Browse Glossary', href: `/${locale}/handbook/` };

  const todayLabel = isKo ? 'TODAY' : 'TODAY';
  const trendingLabel = isKo ? 'TRENDING TERMS' : 'TRENDING TERMS';

  const readingLabel = heroNews?.reading_time_min
    ? isKo ? `약 ${heroNews.reading_time_min}분` : `${heroNews.reading_time_min} min read`
    : null;
  ---

  <div class="home-split-hero">
    <div class="home-split-hero-wordmark">0TO1LOG</div>
    <div class="home-split-hero-inner">

      <!-- Left: Value proposition -->
      <div class="home-split-hero-left">
        <p class="home-split-hero-kicker">{kicker}</p>
        <h1 class="home-split-hero-headline">
          {headline.map((line) => <>{line}<br /></>)}
        </h1>
        <p class="home-split-hero-sub">{subCopy}</p>
        <div class="home-split-hero-cta">
          <a href={ctaPrimary.href} class="home-split-hero-cta-primary">{ctaPrimary.label}</a>
          <a href={ctaSecondary.href} class="home-split-hero-cta-secondary">{ctaSecondary.label}</a>
        </div>
      </div>

      <!-- Right: Today's snapshot -->
      <div class="home-split-hero-right">
        {heroNews && (
          <>
            <p class="home-split-hero-today-label">{todayLabel}</p>
            <a href={newsHref} class="home-split-hero-news">
              {readingLabel && (
                <p class="home-split-hero-news-kicker">◆ AI · {readingLabel}</p>
              )}
              <p class="home-split-hero-news-title">{heroNews.title}</p>
            </a>
          </>
        )}

        {trendingTerms.length > 0 && (
          <>
            <p class="home-split-hero-trending-label">{trendingLabel}</p>
            <div class="home-split-hero-terms">
              {trendingTerms.slice(0, 2).map((term) => (
                <div class="home-split-hero-term">
                  <span class="home-split-hero-term-name">{term.term}</span>
                  {(isKo ? term.definition_ko : term.definition_en) && (
                    <p class="home-split-hero-term-def">
                      {(isKo ? term.definition_ko : term.definition_en)?.slice(0, 60)}…
                    </p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

    </div>
  </div>
  ```

- [ ] **Step 2: Verify build passes**

  ```bash
  cd frontend && npm run build 2>&1 | tail -20
  ```

  Expected: `build complete` with 0 type errors. (Component is not yet imported anywhere — that's fine for a build check.)

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/components/home/HomeSplitHero.astro
  git commit -m "feat: add HomeSplitHero component"
  ```

---

## Chunk 2: Page Updates

### Task 3: Update `ko/index.astro`

**Files:**
- Modify: `frontend/src/pages/ko/index.astro`

- [ ] **Step 1: Replace imports**

  Current frontmatter imports `HomeMasthead` and `HomeHeroCard`. Replace those two lines:
  ```astro
  import HomeMasthead from '../../components/home/HomeMasthead.astro';
  import HomeHeroCard from '../../components/home/HomeHeroCard.astro';
  ```
  With:
  ```astro
  import HomeSplitHero from '../../components/home/HomeSplitHero.astro';
  import HomeHeroCard from '../../components/home/HomeHeroCard.astro';
  ```
  (`HomeHeroCard` is still needed for the featured headline inside Section B.)

- [ ] **Step 2: Replace `<!-- Section A: Masthead -->` and `<!-- Hero Headline -->` blocks**

  Remove:
  ```astro
  <!-- Section A: Masthead -->
  <HomeMasthead locale={locale} />

  <!-- Hero Headline -->
  {heroNews ? (
    <HomeHeroCard
      href={`/ko/news/${heroNews.slug}`}
      title={heroNews.title}
      excerpt={heroNews.excerpt}
      category="ai-news"
      publishedAt={heroNews.published_at}
      readingTimeMin={heroNews.reading_time_min}
      tags={heroNews.tags}
      locale={locale}
      postType={heroNews.post_type}
    />
  ) : (
    <p class="home-coming-soon">{t.ko['home.comingSoon']}</p>
  )}
  ```

  Replace with:
  ```astro
  <!-- Section A: Split Hero -->
  <HomeSplitHero
    locale={locale}
    heroNews={heroNews}
    trendingTerms={terms.slice(0, 2)}
    newsHref={heroNews ? `/ko/news/${heroNews.slug}` : '/ko/news/'}
    homeIntro={homeIntro}
  />
  ```

- [ ] **Step 3: Add `HomeHeroCard` inside `<!-- Section B: Latest AI News -->`**

  Current Section B:
  ```astro
  <!-- Section B: Latest AI News -->
  {moreNews.length > 0 && (
    <section class="home-section">
      <HomeSectionHeader ... />
      <div class="home-news-grid">
        {moreNews.map((post) => ( <HomeNewsCard ... /> ))}
      </div>
    </section>
  )}
  ```

  Replace with:
  ```astro
  <!-- Section B: Latest AI News -->
  {(heroNews || moreNews.length > 0) && (
    <section class="home-section">
      <HomeSectionHeader
        title={t.ko['home.latestNews']}
        viewAllHref="/ko/news/"
        viewAllLabel={t.ko['home.viewAll']}
      />
      {heroNews && (
        <HomeHeroCard
          href={`/ko/news/${heroNews.slug}`}
          title={heroNews.title}
          excerpt={heroNews.excerpt}
          category="ai-news"
          publishedAt={heroNews.published_at}
          readingTimeMin={heroNews.reading_time_min}
          tags={heroNews.tags}
          locale={locale}
          postType={heroNews.post_type}
        />
      )}
      {moreNews.length > 0 && (
        <div class="home-news-grid">
          {moreNews.map((post) => (
            <HomeNewsCard
              href={`/ko/news/${post.slug}`}
              title={post.title}
              excerpt={post.excerpt}
              category="ai-news"
              publishedAt={post.published_at}
              readingTimeMin={post.reading_time_min}
              tags={post.tags}
              locale={locale}
              postType={post.post_type}
            />
          ))}
        </div>
      )}
    </section>
  )}
  ```

- [ ] **Step 4: Replace `<!-- Section C: Glossary Spotlight -->` and `<!-- Section E: Featured AI Products -->` with a merged 2-column section**

  Remove both Section C and Section E blocks entirely. Replace them with:
  ```astro
  <!-- Section C+E: Glossary + AI Products (2-col) -->
  {(terms.length > 0 || featuredProducts.length > 0) && (
    <section class="home-section">
      <div class="home-spotlight-grid">
        {terms.length > 0 && (
          <div class="home-spotlight-col">
            <HomeSectionHeader
              title={t.ko['home.glossarySpotlight']}
              viewAllHref="/ko/handbook/"
              viewAllLabel={t.ko['home.viewAll']}
            />
            <div class="home-term-grid">
              {terms.slice(0, 3).map((term) => (
                <HomeTermCard
                  href={`/ko/handbook/${term.slug}`}
                  term={term.term}
                  koreanName={term.korean_name}
                  definition={term.definition_ko}
                  categories={term.categories}
                  locale={locale}
                />
              ))}
            </div>
          </div>
        )}
        {featuredProducts.length > 0 && (
          <div class="home-spotlight-col">
            <HomeSectionHeader
              title={t.ko['home.featuredProducts']}
              viewAllHref="/ko/products/"
              viewAllLabel={t.ko['home.viewAll']}
            />
            <div class="home-product-grid">
              {featuredProducts.slice(0, 3).map((product) => (
                <HomeProductCard
                  href={`/ko/products/${product.slug}/`}
                  name={product.name}
                  tagline={product.tagline_ko || product.tagline}
                  logoUrl={product.logo_url}
                  pricing={product.pricing}
                  locale={locale}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )}
  ```

- [ ] **Step 5: Remove `<!-- Section F: Start Here -->`**

  Delete the entire block:
  ```astro
  <!-- Section F: Start Here -->
  <section class="home-section home-start-here">
    ...
  </section>
  ```

- [ ] **Step 6: Verify build passes**

  ```bash
  cd frontend && npm run build 2>&1 | tail -20
  ```

  Expected: `build complete`, 0 type errors.

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/pages/ko/index.astro
  git commit -m "feat: update ko homepage — SplitHero + merged spotlight sections"
  ```

---

### Task 4: Update `en/index.astro`

**Files:**
- Modify: `frontend/src/pages/en/index.astro`

Apply the same changes as Task 3, but with the `en` locale. Differences from the Korean version:

- `locale = 'en'`
- `href` prefixes use `/en/` instead of `/ko/`
- `definition={term.definition_en}` (not `definition_ko`)
- `tagline={product.tagline}` (not `tagline_ko || tagline`)
- `t.en[...]` for all translation keys
- Blog list aria-label: `"Recent blog posts"` (already English in the current file)
- `homeIntro` fallback string is already English in the page frontmatter — pass as-is

- [ ] **Step 1: Replace imports** (same as Task 3 Step 1 but in `en/index.astro`)

- [ ] **Step 2: Replace Masthead + Hero blocks** with `HomeSplitHero`:

  ```astro
  <!-- Section A: Split Hero -->
  <HomeSplitHero
    locale={locale}
    heroNews={heroNews}
    trendingTerms={terms.slice(0, 2)}
    newsHref={heroNews ? `/en/news/${heroNews.slug}` : '/en/news/'}
    homeIntro={homeIntro}
  />
  ```

- [ ] **Step 3: Add `HomeHeroCard` inside Section B** (same pattern as Task 3 Step 3, `/en/news/${heroNews.slug}` for hrefs)

- [ ] **Step 4: Replace Sections C+E with merged spotlight** (same pattern as Task 3 Step 4 with these locale differences):
  - `viewAllHref="/en/handbook/"` and `"/en/products/"`
  - `definition={term.definition_en}` (not `definition_ko`)
  - `tagline={product.tagline}` (not `tagline_ko || tagline`)
  - `href={`/en/handbook/${term.slug}`}` and `href={`/en/products/${product.slug}/`}`
  - `t.en[...]` for all translation keys

- [ ] **Step 5: Remove Section F** (the English "Start Here" block)

- [ ] **Step 6: Verify build passes**

  ```bash
  cd frontend && npm run build 2>&1 | tail -20
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/pages/en/index.astro
  git commit -m "feat: update en homepage — SplitHero + merged spotlight sections"
  ```

---

## Chunk 3: Cleanup

### Task 5: Remove Unused Files and CSS

**Files:**
- Modify: `frontend/src/styles/global.css`
- Delete: `frontend/src/components/home/HomeMasthead.astro`

- [ ] **Step 1: Confirm `HomeMasthead` is no longer imported**

  ```bash
  grep -r "HomeMasthead" frontend/src/
  ```

  Expected: no results (after Tasks 3 and 4 are complete).

- [ ] **Step 2: Delete `HomeMasthead.astro`**

  ```bash
  rm frontend/src/components/home/HomeMasthead.astro
  ```

- [ ] **Step 3: Remove `.home-masthead*` and `.home-start-here*` CSS from `global.css`**

  **Masthead block:** Find the `/* Masthead */` comment (around line 8692). Delete from that comment line through — and including — the closing `}` of the `@media (max-width: 639px)` block that contains `.home-masthead-top`, `.home-masthead-kicker-left`, `.home-masthead-kicker-right`, and `.home-masthead-pillars` responsive rules. The masthead block ends after those media query rules. Confirm the full extent by checking that `.home-hero-card` (the next section, `/* Hero card */`) is still intact after the deletion.

  **Start Here block:** Find the `/* Start Here */` comment. Delete from that comment line through — and including — the closing `}` of its `@media (min-width: 768px)` block (the one containing `grid-template-columns: repeat(5, 1fr)`). Confirm that the content immediately following in the CSS file is unrelated to `home-start-here`.

- [ ] **Step 4: Verify build passes after cleanup**

  ```bash
  cd frontend && npm run build 2>&1 | tail -20
  ```

  Expected: `build complete`, 0 errors.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/styles/global.css
  git rm frontend/src/components/home/HomeMasthead.astro
  git commit -m "chore: remove HomeMasthead and unused CSS after homepage redesign"
  ```

---

## Verification

- [ ] **Visual check — Korean homepage**

  Start dev server and open `http://localhost:4321/ko/` in browser:
  ```bash
  cd frontend && npm run dev
  ```
  Confirm:
  1. Dark Split Hero renders at top with brand wordmark, headline copy, 2 CTAs
  2. Right panel shows today's news and (if `is_favourite` terms exist) trending terms
  3. Section B "Latest AI News" shows a large headline card + 3 sub-cards below
  4. Section C+E shows Glossary and AI Products side by side
  5. Section D Blog renders unchanged
  6. No "Start Here" section at bottom
  7. Mobile (< 640px): hero stacks to 1 column, spotlight stacks to 1 column

- [ ] **Visual check — English homepage**

  Open `http://localhost:4321/en/` and confirm same structure with English copy.

- [ ] **Final build**

  ```bash
  cd frontend && npm run build 2>&1 | tail -5
  ```

  Expected: `build complete`, 0 errors, 0 warnings.
