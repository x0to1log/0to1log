# Home News Carousel Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 홈페이지 최신 AI 뉴스 섹션을 가로 스크롤 carousel로 교체 — 지난 7일치 뉴스 전체를 균일한 카드로 표시, 무한 루프 nav 버튼 + dash indicator 포함.

**Architecture:** `HomeNewsCarousel.astro` 신규 컴포넌트가 carousel track + nav 버튼 + indicator를 포함. 데이터 레이어는 7일 필터 + fallback 로직 추가. 기존 `HomeHeroCard` + `HomeNewsCard` 혼합 레이아웃을 단일 균일 카드 carousel로 대체. JS는 컴포넌트 내 plain `<script>` 블록으로 처리(Astro 규칙: `client:load` 금지).

**Tech Stack:** Astro v5, CSS scroll-snap (no external library), plain `<script>` (vanilla JS), Supabase (date filter)

---

## 파일 구조

| 파일 | 작업 |
|------|------|
| `frontend/src/lib/pageData/homePage.ts` | 수정 — news 쿼리에 7일 필터 + fallback 로직 |
| `frontend/src/components/home/HomeNewsCarousel.astro` | 신규 — carousel 컴포넌트 (track + nav + indicator + script) |
| `frontend/src/pages/en/index.astro` | 수정 — HomeHeroCard/HomeNewsCard 제거, HomeNewsCarousel 사용 |
| `frontend/src/pages/ko/index.astro` | 수정 — 동일 |
| `frontend/src/styles/global.css` | 수정 — carousel CSS 추가, home-news-featured grid 제거 |

`HomeHeroCard.astro`는 홈에서 제거되지만 파일은 유지 (향후 다른 곳 사용 가능성).

---

## Task 1: 데이터 레이어 — 7일 필터 + fallback

**Files:**
- Modify: `frontend/src/lib/pageData/homePage.ts:53-61`

- [ ] **Step 1: `homePage.ts` 열기 — 현재 news 쿼리 확인**

현재 코드 (53-61번째 줄):
```ts
supabase
  .from('news_posts')
  .select('id, title, slug, post_type, published_at, tags, reading_time_min, excerpt')
  .eq('status', 'published')
  .eq('locale', locale)
  .order('published_at', { ascending: false })
  .limit(4),
```

- [ ] **Step 2: news 쿼리를 7일 필터 + fallback 구조로 교체**

`getHomePageData` 함수 상단(supabase 체크 이후)에 날짜 계산 추가:
```ts
const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
```

Promise.all 첫 번째 항목을 두 개로 분리 (7일치 + fallback):
```ts
const [recentNewsRes, fallbackNewsRes, termsRes, blogRes, sc, featuredProducts, fallbackTermsRes] = await Promise.all([
  supabase
    .from('news_posts')
    .select('id, title, slug, post_type, published_at, tags, reading_time_min, excerpt')
    .eq('status', 'published')
    .eq('locale', locale)
    .gte('published_at', sevenDaysAgo)
    .order('published_at', { ascending: false })
    .limit(20),

  supabase
    .from('news_posts')
    .select('id, title, slug, post_type, published_at, tags, reading_time_min, excerpt')
    .eq('status', 'published')
    .eq('locale', locale)
    .order('published_at', { ascending: false })
    .limit(10),

  // ... 나머지 기존 쿼리들 동일
]);
```

반환 직전 news 병합 로직 추가:
```ts
let news = (recentNewsRes.data ?? []) as HomeNewsPost[];
if (news.length < 3) {
  const fallbackNews = (fallbackNewsRes.data ?? []) as HomeNewsPost[];
  const existingIds = new Set(news.map((n) => n.id));
  const extras = fallbackNews.filter((n) => !existingIds.has(n.id));
  news = [...news, ...extras].slice(0, 10);
}
```

- [ ] **Step 3: 빌드 확인**
```bash
cd frontend && npm run build
```
Expected: 0 errors

---

## Task 2: `HomeNewsCarousel.astro` 신규 컴포넌트

**Files:**
- Create: `frontend/src/components/home/HomeNewsCarousel.astro`

- [ ] **Step 1: 컴포넌트 파일 생성**

```astro
---
import HomeNewsCard from './HomeNewsCard.astro';
import type { HomeNewsPost } from '../../lib/pageData/homePage';

interface Props {
  news: HomeNewsPost[];
  locale: 'en' | 'ko';
  baseHref: string;
}

const { news, locale, baseHref } = Astro.props;
const prevLabel = locale === 'ko' ? '이전' : 'Previous';
const nextLabel = locale === 'ko' ? '다음' : 'Next';
---

<div class="home-carousel" data-carousel>
  <div class="home-carousel-track" data-carousel-track>
    {news.map((post) => (
      <div class="home-carousel-slide">
        <HomeNewsCard
          href={`${baseHref}${post.slug}`}
          title={post.title}
          excerpt={post.excerpt}
          category="ai-news"
          publishedAt={post.published_at}
          readingTimeMin={post.reading_time_min}
          tags={post.tags}
          locale={locale}
          postType={post.post_type}
        />
      </div>
    ))}
  </div>

  <div class="home-carousel-nav">
    <button class="home-carousel-btn" data-carousel-prev aria-label={prevLabel}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M10 12L6 8L10 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
    <div class="home-carousel-indicator" data-carousel-indicator></div>
    <button class="home-carousel-btn" data-carousel-next aria-label={nextLabel}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
  </div>
</div>

<script>
  document.querySelectorAll<HTMLElement>('[data-carousel]').forEach((carousel) => {
    const track = carousel.querySelector<HTMLElement>('[data-carousel-track]')!;
    const slides = track.querySelectorAll<HTMLElement>('.home-carousel-slide');
    const prevBtn = carousel.querySelector<HTMLButtonElement>('[data-carousel-prev]');
    const nextBtn = carousel.querySelector<HTMLButtonElement>('[data-carousel-next]');
    const indicator = carousel.querySelector<HTMLElement>('[data-carousel-indicator]');

    const total = slides.length;
    if (total === 0) return;

    let currentIndex = 0;
    const MAX_DASHES = 10;
    const dashCount = Math.min(total, MAX_DASHES);

    // Build indicator dashes
    if (indicator) {
      for (let i = 0; i < dashCount; i++) {
        const dash = document.createElement('span');
        dash.className = 'home-carousel-dash';
        if (i === 0) dash.classList.add('home-carousel-dash--active');
        indicator.appendChild(dash);
      }
    }

    function getSlideWidth(): number {
      return slides[0].offsetWidth + 16; // card width + gap (1rem = 16px)
    }

    function updateIndicator(index: number) {
      if (!indicator) return;
      const dashes = indicator.querySelectorAll<HTMLElement>('.home-carousel-dash');
      const dashIndex = total > MAX_DASHES
        ? Math.round((index / (total - 1)) * (MAX_DASHES - 1))
        : index;
      dashes.forEach((d, i) => {
        d.classList.toggle('home-carousel-dash--active', i === dashIndex);
      });
    }

    function scrollToIndex(index: number) {
      currentIndex = ((index % total) + total) % total; // wrap around
      track.scrollTo({ left: currentIndex * getSlideWidth(), behavior: 'smooth' });
      updateIndicator(currentIndex);
    }

    prevBtn?.addEventListener('click', () => scrollToIndex(currentIndex - 1));
    nextBtn?.addEventListener('click', () => scrollToIndex(currentIndex + 1));

    // Sync currentIndex on manual scroll
    let scrollTimer: ReturnType<typeof setTimeout>;
    track.addEventListener('scroll', () => {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(() => {
        const sw = getSlideWidth();
        if (sw > 0) {
          currentIndex = Math.round(track.scrollLeft / sw);
          updateIndicator(currentIndex);
        }
      }, 50);
    }, { passive: true });
  });
</script>
```

- [ ] **Step 2: 빌드 확인**
```bash
cd frontend && npm run build
```
Expected: 0 errors

---

## Task 3: `en/index.astro` 수정

**Files:**
- Modify: `frontend/src/pages/en/index.astro`

- [ ] **Step 1: import 교체**

제거:
```astro
import HomeHeroCard from '../../components/home/HomeHeroCard.astro';
import HomeNewsCard from '../../components/home/HomeNewsCard.astro';
```

추가:
```astro
import HomeNewsCarousel from '../../components/home/HomeNewsCarousel.astro';
```

- [ ] **Step 2: frontmatter 로직 정리**

제거:
```astro
const heroNews = news[0] ?? null;
const moreNews = news.slice(1, 4);
```
(carousel은 전체 `news` 배열을 그대로 사용)

- [ ] **Step 3: Section B 마크업 교체**

기존:
```astro
{news.length > 0 && (
  <section class="home-section home-section--news">
    <HomeSectionHeader ... />
    <div class="home-news-featured">
      {heroNews && (<HomeHeroCard href={`/en/news/${heroNews.slug}`} ... />)}
      {moreNews.slice(0, 2).map((post) => (
        <HomeNewsCard href={`/en/news/${post.slug}`} ... />
      ))}
    </div>
  </section>
)}
```

교체:
```astro
{news.length > 0 && (
  <section class="home-section home-section--news">
    <HomeSectionHeader
      title={t.en['home.latestNews']}
      viewAllHref="/en/news/"
      viewAllLabel={t.en['home.viewAll']}
    />
    <HomeNewsCarousel news={news} locale={locale} baseHref="/en/news/" />
  </section>
)}
```

- [ ] **Step 4: 빌드 확인**
```bash
cd frontend && npm run build
```
Expected: 0 errors

---

## Task 4: `ko/index.astro` 수정

**Files:**
- Modify: `frontend/src/pages/ko/index.astro`

Task 3과 동일한 변경, locale/href만 다름:

- [ ] **Step 1: import 교체** (Task 3 Step 1 동일)

- [ ] **Step 2: frontmatter 정리** (Task 3 Step 2 동일)

- [ ] **Step 3: Section B 마크업 교체**

```astro
{news.length > 0 && (
  <section class="home-section home-section--news">
    <HomeSectionHeader
      title={t.ko['home.latestNews']}
      viewAllHref="/ko/news/"
      viewAllLabel={t.ko['home.viewAll']}
    />
    <HomeNewsCarousel news={news} locale={locale} baseHref="/ko/news/" />
  </section>
)}
```

- [ ] **Step 4: 빌드 확인**
```bash
cd frontend && npm run build
```
Expected: 0 errors

---

## Task 5: CSS — global.css

**Files:**
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: 기존 `.home-news-featured` 그리드 블록 제거**

제거 대상 (약 8970~9010번째 줄):
```css
/* Featured news: mobile → tablet → desktop */
.home-news-featured { ... }
.home-news-featured .home-hero-card { ... }
.home-news-featured .home-hero-card:hover { ... }
.home-news-featured .home-news-card { ... }
@media (min-width: 640px) { .home-news-featured ... }
@media (min-width: 1024px) { .home-news-featured ... }
```

`.home-hero-card` 관련 스타일은 `HomeHeroCard.astro` 파일이 남아있으므로 유지.

- [ ] **Step 2: Carousel CSS 추가** (`.home-news-featured` 블록이 있던 자리에)

```css
/* ── News Carousel ── */
.home-carousel {
  position: relative;
}

.home-carousel-track {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  padding-bottom: 0.25rem;
}

.home-carousel-track::-webkit-scrollbar {
  display: none;
}

.home-carousel-slide {
  flex-shrink: 0;
  scroll-snap-align: start;
  width: calc(100% - 2.5rem);
  display: flex;
}

.home-carousel-slide .home-news-card {
  flex: 1;
  min-height: 180px;
}

@media (min-width: 640px) {
  .home-carousel-slide {
    width: calc(50% - 0.5rem);
  }
}

@media (min-width: 1024px) {
  .home-carousel-slide {
    width: calc(33.333% - 0.75rem);
  }
}

/* Nav */
.home-carousel-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.25rem;
}

.home-carousel-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color 150ms ease, color 150ms ease, background-color 150ms ease;
}

.home-carousel-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background-color: var(--color-accent-subtle);
}

/* Indicator */
.home-carousel-indicator {
  display: flex;
  gap: 0.375rem;
  align-items: center;
}

.home-carousel-dash {
  width: 1.5rem;
  height: 2px;
  border-radius: 2px;
  background: var(--color-border);
  transition: background-color 150ms ease, width 150ms ease;
}

.home-carousel-dash--active {
  background: var(--color-accent);
  width: 2.5rem;
}
```

- [ ] **Step 3: 최종 빌드 확인**
```bash
cd frontend && npm run build
```
Expected: 0 errors, 0 warnings (prerender warning 제외)

- [ ] **Step 4: 커밋**
```bash
git add frontend/src/lib/pageData/homePage.ts \
        frontend/src/components/home/HomeNewsCarousel.astro \
        frontend/src/pages/en/index.astro \
        frontend/src/pages/ko/index.astro \
        frontend/src/styles/global.css
git commit -m "feat(home): 최신 뉴스 섹션 carousel로 교체 — 7일 필터, 무한 루프 nav, dash indicator"
```

---

## 체크리스트

- [ ] 7일치 뉴스 < 3개일 때 fallback 최근 10개로 채워짐
- [ ] 모바일: 카드 1개 + 오른쪽 peek 보임
- [ ] 태블릿: 카드 2개 + peek 보임
- [ ] 데스크탑: 카드 3개 + peek 보임
- [ ] next 버튼: 마지막 카드에서 첫 카드로 루프
- [ ] prev 버튼: 첫 카드에서 마지막 카드로 루프
- [ ] 수동 스크롤/스와이프 시 indicator 동기화
- [ ] en/ko 양쪽 모두 작동 확인
- [ ] 빌드 0 errors
