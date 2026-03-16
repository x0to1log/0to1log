# IT Blog Knowledge Base 스타일 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** IT Blog 페이지를 Knowledge Base 스타일(왼쪽 폴더 트리 사이드바 + Featured 카드 + TOC)로 전면 교체

**Architecture:** 7개 새 blog 컴포넌트(`components/blog/`) 생성 → 4개 페이지(`en/ko blog list/detail`) 전면 교체 → CSS `.blog-*` 클래스 추가. 기존 newsprint 컴포넌트는 AI News/Handbook에서 계속 사용하므로 건드리지 않음.

**Tech Stack:** Astro v5, CSS custom properties, vanilla `<script>`, Supabase client-side queries

**Design Doc:** `docs/plans/2026-03-11-blog-kb-design.md`
**Reference Examples:** `frontend/examples/layout/example_blog_1.html`, `example_blog_2.html`

---

## Task 1: CSS — `.blog-*` 클래스 추가

**Files:**
- Modify: `frontend/src/styles/global.css` (파일 끝에 추가)

**Step 1:** `global.css` 끝에 블로그 전용 CSS 섹션 추가

```css
/* ═══════════════════════════════════════════════════════
   Blog — Knowledge Base Style
   ═══════════════════════════════════════════════════════ */

/* Shell: sidebar + main + optional TOC */
.blog-shell {
  display: flex;
  min-height: calc(100vh - 4rem);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
}

/* ── Left Sidebar ── */
.blog-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 4rem);
  position: sticky;
  top: 4rem;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent;
}

.blog-sidebar-search {
  padding: 0.75rem;
  border-bottom: 1px solid var(--color-border);
}

.blog-sidebar-search-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-family: var(--font-ui);
  font-size: 0.82rem;
  cursor: pointer;
  transition: border-color 150ms ease;
}

.blog-sidebar-search-btn:hover {
  border-color: var(--color-text-muted);
}

.blog-sidebar-search-kbd {
  font-family: var(--font-code);
  font-size: 0.7rem;
  background: var(--color-bg-secondary);
  padding: 0.15rem 0.4rem;
}

.blog-sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  font-size: 0.82rem;
  font-family: var(--font-ui);
}

.blog-folder-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.5rem;
  background: none;
  border: none;
  color: var(--color-text-primary);
  font-family: var(--font-ui);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.blog-folder-btn:hover {
  background: var(--color-accent-subtle);
}

.blog-folder-arrow {
  width: 16px;
  height: 16px;
  color: var(--color-text-muted);
  transition: transform 200ms ease;
  flex-shrink: 0;
}

.blog-folder-btn[aria-expanded="true"] .blog-folder-arrow {
  transform: rotate(90deg);
}

.blog-folder-children {
  margin-left: 1.5rem;
  padding-left: 0.5rem;
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.blog-folder-children[hidden] {
  display: none;
}

.blog-sidebar-link {
  display: block;
  padding: 0.35rem 0.5rem;
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: 0.8rem;
  transition: color 150ms ease, background-color 150ms ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.blog-sidebar-link:hover {
  color: var(--color-text-primary);
  background: var(--color-accent-subtle);
}

.blog-sidebar-link--active {
  color: var(--color-text-primary);
  font-weight: 600;
  background: color-mix(in srgb, var(--color-accent) 12%, transparent);
}

.blog-sidebar-footer {
  padding: 0.75rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.82rem;
}

.blog-sidebar-footer a {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--color-text-muted);
  text-decoration: none;
  padding: 0.35rem 0.5rem;
  transition: color 150ms ease;
}

.blog-sidebar-footer a:hover {
  color: var(--color-text-primary);
}

/* Mobile sidebar overlay */
.blog-sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(0, 0, 0, 0.4);
}

.blog-sidebar-overlay--open {
  display: block;
}

.blog-mobile-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  background: none;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  cursor: pointer;
}

@media (max-width: 1023px) {
  .blog-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    z-index: 91;
    transform: translateX(-100%);
    transition: transform 250ms ease;
  }

  .blog-sidebar--open {
    transform: translateX(0);
  }

  .blog-mobile-toggle {
    display: inline-flex;
  }
}

/* ── Main Content ── */
.blog-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}

.blog-main-inner {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem 1rem;
}

@media (min-width: 768px) {
  .blog-main-inner {
    padding: 2rem 1.5rem;
  }
}

/* ── Section Headers (mono, uppercase) ── */
.blog-section-header {
  font-family: var(--font-code);
  font-size: 0.7rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}

/* ── Featured Cards ── */
.blog-featured-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  margin-bottom: 2.5rem;
}

@media (min-width: 640px) {
  .blog-featured-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.blog-featured-card {
  display: block;
  padding: 1rem;
  border: 1px solid var(--color-border);
  text-decoration: none;
  color: inherit;
  transition: background-color 150ms ease, border-color 150ms ease;
  position: relative;
}

.blog-featured-card:hover {
  background: var(--color-accent-subtle);
  border-color: var(--color-text-muted);
}

.blog-featured-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.blog-featured-card-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.05rem;
  line-height: 1.3;
  color: var(--color-text-primary);
}

.blog-featured-card-arrow {
  width: 16px;
  height: 16px;
  color: var(--color-text-muted);
  opacity: 0;
  transition: opacity 150ms ease;
  flex-shrink: 0;
  margin-top: 0.15rem;
}

.blog-featured-card:hover .blog-featured-card-arrow {
  opacity: 1;
}

.blog-featured-card-excerpt {
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--color-text-secondary);
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.blog-featured-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.blog-mono-tag {
  font-family: var(--font-code);
  font-size: 0.68rem;
  padding: 0.15rem 0.45rem;
}

/* ── List Items (All Posts) ── */
.blog-list-section {
  display: flex;
  flex-direction: column;
}

.blog-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--color-border);
  text-decoration: none;
  color: inherit;
  transition: background-color 150ms ease;
  gap: 0.75rem;
}

.blog-list-item:hover {
  background: var(--color-accent-subtle);
  margin-inline: -0.75rem;
  padding-inline: 0.75rem;
}

.blog-list-item-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
}

.blog-list-item-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  color: var(--color-text-muted);
}

.blog-list-item-title {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-text-primary);
  transition: transform 150ms ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.blog-list-item:hover .blog-list-item-title {
  transform: translateX(4px);
}

.blog-list-item-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.blog-list-item-date {
  font-family: var(--font-code);
  font-size: 0.78rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.blog-list-item-category {
  font-family: var(--font-code);
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.1rem 0.35rem;
}

.blog-list-item--read {
  opacity: 0.6;
}

/* ── Breadcrumb ── */
.blog-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  color: var(--color-text-muted);
  margin-bottom: 1.5rem;
}

.blog-breadcrumb a {
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color 150ms ease;
}

.blog-breadcrumb a:hover {
  color: var(--color-text-primary);
}

.blog-breadcrumb-current {
  color: var(--color-text-primary);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

/* ── TOC (Right Rail) ── */
.blog-toc {
  width: 200px;
  flex-shrink: 0;
  padding-top: 6rem;
  padding-right: 1.5rem;
  position: sticky;
  top: 4rem;
  height: calc(100vh - 4rem);
  overflow-y: auto;
  scrollbar-width: none;
}

.blog-toc::-webkit-scrollbar {
  display: none;
}

.blog-toc-header {
  font-family: var(--font-code);
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--color-text-muted);
  margin-bottom: 0.75rem;
}

.blog-toc-nav {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.8rem;
}

.blog-toc-link {
  display: block;
  padding: 0.25rem 0 0.25rem 0.75rem;
  border-left: 2px solid transparent;
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color 150ms ease, border-color 150ms ease;
}

.blog-toc-link:hover {
  color: var(--color-text-primary);
}

.blog-toc-link--active {
  color: var(--color-text-primary);
  font-weight: 500;
  border-left-color: var(--color-accent);
}

.blog-toc-link--h3 {
  padding-left: 1.5rem;
}

@media (max-width: 1279px) {
  .blog-toc {
    display: none;
  }
}

/* ── Article Header ── */
.blog-article-header {
  margin-bottom: 2rem;
}

.blog-article-icon {
  font-size: 2.5rem;
  line-height: 1;
  margin-bottom: 0.75rem;
}

.blog-article-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(1.8rem, 3vw, 2.5rem);
  line-height: 1.15;
  margin-bottom: 0.6rem;
}

.blog-article-meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-family: var(--font-code);
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.blog-article-meta svg {
  width: 14px;
  height: 14px;
}

/* ── Code Copy Button ── */
.blog-code-copy {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  opacity: 0;
  transition: opacity 200ms ease;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  padding: 0.2rem 0.5rem;
  font-family: var(--font-code);
  font-size: 0.7rem;
  color: var(--color-text-muted);
  cursor: pointer;
}

pre:hover .blog-code-copy {
  opacity: 1;
}

.blog-code-copy:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

/* ── Tags Footer ── */
.blog-tags-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}

/* ── Masthead (reuse newsprint pattern but in blog context) ── */
.blog-masthead-section {
  text-align: center;
  margin-bottom: 1.5rem;
}

.blog-masthead-title {
  font-family: var(--font-masthead);
  font-weight: 900;
  font-size: clamp(2rem, 5vw, 3.5rem);
  line-height: 1.1;
  letter-spacing: -0.02em;
  text-transform: uppercase;
}

.blog-masthead-kicker {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--color-text-secondary);
}

.blog-masthead-subkicker {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-secondary);
  border-top: 3px double var(--color-border);
  border-bottom: 3px double var(--color-border);
  padding: 0.4rem 0.15rem;
  margin-top: 0.25rem;
}
```

**Step 2:** 빌드 확인

```bash
cd frontend && npm run build
```

**Step 3:** 커밋

```bash
git add frontend/src/styles/global.css
git commit -m "feat(blog): add Knowledge Base style CSS classes"
```

---

## Task 2: i18n — 블로그 번역 키 추가

**Files:**
- Modify: `frontend/src/i18n/index.ts`

**Step 1:** blog 관련 키 추가 (기존 키 유지, 새 키 추가)

추가할 키:
```typescript
// EN
'blog.featured': 'Featured',
'blog.allPosts': 'All Posts',
'blog.onThisPage': 'On This Page',
'blog.search': 'Search...',
'blog.allPostsCount': 'All Posts',
'blog.folder.study': 'Study',
'blog.folder.career': 'Career',
'blog.folder.project': 'Project',

// KO
'blog.featured': '추천 글',
'blog.allPosts': '전체 글',
'blog.onThisPage': '이 페이지에서',
'blog.search': '검색...',
'blog.allPostsCount': '전체 글',
'blog.folder.study': '학습',
'blog.folder.career': '커리어',
'blog.folder.project': '프로젝트',
```

**Step 2:** 커밋

```bash
git add frontend/src/i18n/index.ts
git commit -m "feat(blog): add i18n keys for Knowledge Base layout"
```

---

## Task 3: BlogSidebar 컴포넌트

**Files:**
- Create: `frontend/src/components/blog/BlogSidebar.astro`

**Step 1:** 컴포넌트 작성

Props:
```typescript
interface SidebarPost {
  title: string;
  slug: string;
  category: string;
}

interface Props {
  locale: 'en' | 'ko';
  posts: SidebarPost[];
  currentSlug?: string;
  totalCount: number;
}
```

구현 내용:
- 검색 트리거 버튼 (⌘K 표시)
- Study/Career/Project 폴더 각각 `<button>` + 자식 글 목록
- 현재 slug 매칭 시 `.blog-sidebar-link--active`
- 하단 "All Posts (N)" 링크
- 폴더 펼치기/접기 `<script>` (바닐라)
- 모바일 오버레이 닫기 로직

카테고리별 글 그룹핑: `posts.filter(p => p.category === 'study')` 등

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/components/blog/BlogSidebar.astro
git commit -m "feat(blog): add BlogSidebar folder tree component"
```

---

## Task 4: BlogShell 컴포넌트

**Files:**
- Create: `frontend/src/components/blog/BlogShell.astro`

**Step 1:** 컴포넌트 작성

Props:
```typescript
interface Props {
  locale: 'en' | 'ko';
  sidebarPosts: SidebarPost[];
  currentSlug?: string;
  totalCount: number;
  showTOC?: boolean;
}
```

구현:
```html
<div class="blog-shell">
  <BlogSidebar locale={locale} posts={sidebarPosts} currentSlug={currentSlug} totalCount={totalCount} />
  <div class="blog-sidebar-overlay" data-sidebar-overlay></div>
  <div class="blog-main">
    <slot />  <!-- 메인 콘텐츠 -->
  </div>
  {showTOC && <slot name="toc" />}
</div>
```

모바일 햄버거 토글은 페이지 마크업에서 처리 (BlogShell 안에 토글 버튼 포함하지 않음 — 각 페이지의 masthead 영역에 배치)

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/components/blog/BlogShell.astro
git commit -m "feat(blog): add BlogShell layout component"
```

---

## Task 5: BlogFeaturedCard 컴포넌트

**Files:**
- Create: `frontend/src/components/blog/BlogFeaturedCard.astro`

**Step 1:** 컴포넌트 작성

Props (NewsprintHeadline과 유사하되 Knowledge Base 스타일):
```typescript
interface Props {
  href: string;
  title: string;
  excerpt?: string | null;
  category?: string | null;
  tags?: string[] | null;
  locale: 'en' | 'ko';
}
```

HTML 구조:
- `.blog-featured-card` (link)
- `.blog-featured-card-top` (title + arrow icon)
- `.blog-featured-card-excerpt` (2줄 clamp)
- `.blog-featured-card-tags` (mono 태그)
- 카테고리 색상 배경 태그: `style="background: color-mix(in srgb, ${catColor} 15%, transparent); color: ${catColor}"`

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/components/blog/BlogFeaturedCard.astro
git commit -m "feat(blog): add BlogFeaturedCard component"
```

---

## Task 6: BlogListItem 컴포넌트

**Files:**
- Create: `frontend/src/components/blog/BlogListItem.astro`

**Step 1:** 컴포넌트 작성

Props:
```typescript
interface Props {
  href: string;
  title: string;
  category?: string | null;
  publishedAt?: string | null;
  locale: 'en' | 'ko';
  isRead?: boolean;
}
```

HTML 구조 — 예시 1의 "Recently Edited" 패턴:
- `.blog-list-item` (link)
- 좌: 아이콘(article svg) + 제목 (hover translate-x)
- 우: 카테고리 태그 + 날짜 (mono)

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/components/blog/BlogListItem.astro
git commit -m "feat(blog): add BlogListItem component"
```

---

## Task 7: BlogBreadcrumb 컴포넌트

**Files:**
- Create: `frontend/src/components/blog/BlogBreadcrumb.astro`

**Step 1:** 컴포넌트 작성

Props:
```typescript
interface Props {
  locale: 'en' | 'ko';
  category?: string | null;
  title: string;
}
```

HTML: `Blog > [Category] > [Title]` with links

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/components/blog/BlogBreadcrumb.astro
git commit -m "feat(blog): add BlogBreadcrumb component"
```

---

## Task 8: BlogTOC 컴포넌트

**Files:**
- Create: `frontend/src/components/blog/BlogTOC.astro`

**Step 1:** 컴포넌트 작성

Props:
```typescript
interface Props {
  locale: 'en' | 'ko';
}
```

서버에서는 빈 TOC 컨테이너만 렌더링. 클라이언트 `<script>`에서:
1. `.newsprint-prose`의 h2/h3 수집
2. TOC nav에 링크 생성 (h3는 `.blog-toc-link--h3`)
3. IntersectionObserver로 현재 위치 추적 → `.blog-toc-link--active` 토글
4. 스무스 스크롤

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/components/blog/BlogTOC.astro
git commit -m "feat(blog): add BlogTOC with scroll tracking"
```

---

## Task 9: BlogArticleLayout 컴포넌트

**Files:**
- Create: `frontend/src/components/blog/BlogArticleLayout.astro`

**Step 1:** 컴포넌트 작성

기존 `NewsprintArticleLayout.astro`의 기능을 Knowledge Base 스타일로 재구현:
- BlogBreadcrumb
- 카테고리 아이콘 + 제목 + mono 메타
- `.newsprint-prose` (기존 prose 스타일 재사용)
- 코드 블록 copy 버튼 스크립트
- Engagement bar (like/comment/bookmark/share — 기존 패턴 유지)
- Comments 섹션
- 하단 태그 (.blog-tags-footer + .blog-mono-tag)
- Related Posts (선택적)

대부분의 로직을 기존 `NewsprintArticleLayout.astro`에서 복사하되:
- newsprint-article-header → blog-article-header + blog-breadcrumb
- 우측 rail (NewsprintSideRail) 사용 안 함 → BlogTOC가 BlogShell에서 처리

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/components/blog/BlogArticleLayout.astro
git commit -m "feat(blog): add BlogArticleLayout with breadcrumb and code copy"
```

---

## Task 10: Blog 리스트 페이지 교체 (EN)

**Files:**
- Modify: `frontend/src/pages/en/blog/index.astro` (전면 교체)

**Step 1:** 기존 코드를 새 구조로 교체

데이터 로직 유지 (Supabase 쿼리, 북마크, 읽기 기록 등)

레이아웃 변경:
- `NewsprintShell` → `BlogShell`
- `NewsprintHeadline` → `BlogFeaturedCard` (최신 2~3개)
- `NewsprintListCard` → `BlogListItem` (나머지)
- `NewsprintCategoryFilter` 재사용 (필터 탭)
- `NewsprintListRail` 제거
- masthead 섹션: `.blog-masthead-section` (kicker, title, subkicker)
- 모바일 ☰ 토글 버튼 추가
- 섹션 헤더: "FEATURED", "ALL POSTS" (`.blog-section-header`)

사이드바 데이터: 별도 쿼리 또는 전체 posts에서 `{title, slug, category}` 추출

**Step 2:** 빌드 확인

```bash
cd frontend && npm run build
```

**Step 3:** 커밋

```bash
git add frontend/src/pages/en/blog/index.astro
git commit -m "feat(blog): replace EN blog list with Knowledge Base layout"
```

---

## Task 11: Blog 리스트 페이지 교체 (KO)

**Files:**
- Modify: `frontend/src/pages/ko/blog/index.astro`

**Step 1:** EN 버전을 KO로 복제, locale/copy 변경

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/pages/ko/blog/index.astro
git commit -m "feat(blog): replace KO blog list with Knowledge Base layout"
```

---

## Task 12: Blog 상세 페이지 교체 (EN)

**Files:**
- Modify: `frontend/src/pages/en/blog/[slug].astro`

**Step 1:** 기존 코드를 새 구조로 교체

데이터 로직 유지 (Supabase 쿼리, 읽기 기록, 좋아요, 댓글, handbook popups 등)

레이아웃 변경:
- `NewsprintShell` → `BlogShell` (showTOC=true)
- `NewsprintArticleLayout` → `BlogArticleLayout`
- `NewsprintSideRail` → `BlogTOC` (slot="toc")
- `NewsprintNotice` 재사용 (에러/빈 상태)

사이드바 데이터: 같은 카테고리의 최근 글 목록

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/pages/en/blog/[slug].astro
git commit -m "feat(blog): replace EN blog detail with KB layout + TOC"
```

---

## Task 13: Blog 상세 페이지 교체 (KO)

**Files:**
- Modify: `frontend/src/pages/ko/blog/[slug].astro`

**Step 1:** EN 버전을 KO로 복제, locale/copy 변경

**Step 2:** 빌드 확인 → 커밋

```bash
git add frontend/src/pages/ko/blog/[slug].astro
git commit -m "feat(blog): replace KO blog detail with KB layout + TOC"
```

---

## Task 14: 최종 빌드 검증 & 커밋

**Step 1:** 전체 빌드

```bash
cd frontend && npm run build
```

**Step 2:** 전체 변경사항 커밋 (만약 누락된 파일이 있다면)

```bash
git add -A
git status
git commit -m "feat(blog): complete Knowledge Base style redesign"
```

**Step 3:** 브라우저 확인 체크리스트
- [ ] `/en/blog/` — 사이드바 + Featured + All Posts
- [ ] `/ko/blog/` — 동일 (한국어)
- [ ] `/en/blog/[slug]` — 사이드바 + 브레드크럼 + 본문 + TOC
- [ ] 모바일: 사이드바 ☰ 토글, TOC 숨김
- [ ] 3 테마 (dark/light/pink)
- [ ] 카테고리 필터 동작
- [ ] 폴더 펼치기/접기
- [ ] TOC 스크롤 추적
- [ ] 코드 블록 copy 버튼
- [ ] 북마크/좋아요/댓글 동작

## Related Plans

- [[plans/2026-03-11-blog-kb-design|Blog KB 설계]]
