# Blog Category System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 블로그 카테고리를 하드코딩에서 DB 기반으로 전환하고, 카테고리 필터 페이지 + Admin 관리 페이지를 구현한다.

**Architecture:** Supabase에 `category_groups` / `blog_categories` 테이블을 생성하고 기존 5개 카테고리를 seed. Frontend는 DB에서 카테고리를 fetch하여 사이드바, 카테고리 페이지, Admin 관리 페이지에서 사용. `categories.ts`는 하위 호환 전략으로 전환: 기존 함수 시그니처 유지 (뉴스/홈 소비자 보호) + 블로그 전용 DB 기반 함수 추가.

**Tech Stack:** Astro v5 (SSR), Supabase (PostgreSQL + RLS), Tailwind CSS v4, SortableJS (드래그앤드롭), vanilla JS

**Spec:** `vault/09-Implementation/plans/2026-03-20-blog-category-system-design.md`

---

## Key Decision: categories.ts 하위 호환 전략

`categories.ts`의 기존 함수들 (`getCategoryLabel`, `getCategoryColorVar` 등)은 뉴스, 홈, Newsprint 등 25개+ 파일에서 사용 중. 시그니처를 변경하면 전체 빌드가 깨짐.

**전략:**
1. 기존 함수/export **모두 유지** — 뉴스/홈/Newsprint 컴포넌트는 변경 없음
2. 블로그 전용 DB fetch 함수 **별도 추가** (`blogCategories.ts`)
3. 블로그 컴포넌트는 DB에서 받은 `BlogCategory[]`를 prop으로 받아 **직접 속성 접근** (`.label_ko`, `.color` 등)
4. 블로그 전용 하드코딩 배열만 제거 (`BLOG_CATEGORIES`, `BLOG_CATEGORY_GROUPS`, `BLOG_SIDEBAR_LABELS` 등)
5. Chunk 7에서 기존 함수 중 실제 미사용인 것만 정리

이 전략으로 **모든 커밋이 빌드 가능한 상태를 유지**한다.

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `supabase/migrations/00034_blog_category_system.sql` | DB 테이블 생성, seed, FK, RLS, triggers |
| `frontend/src/lib/pageData/blogCategories.ts` | DB에서 카테고리/그룹 fetch 함수 + 타입 |
| `frontend/src/components/blog/BlogCategoryHeader.astro` | 카테고리 페이지 헤더 컴포넌트 |
| `frontend/src/pages/ko/blog/category/[slug].astro` | KO 카테고리 페이지 |
| `frontend/src/pages/en/blog/category/[slug].astro` | EN 카테고리 페이지 |
| `frontend/src/pages/admin/blog/categories/index.astro` | Admin 카테고리 관리 페이지 |
| `frontend/src/pages/api/admin/blog/categories/list.ts` | API: 카테고리 목록 조회 |
| `frontend/src/pages/api/admin/blog/categories/save.ts` | API: 카테고리 생성/수정 |
| `frontend/src/pages/api/admin/blog/categories/delete.ts` | API: 카테고리 삭제 |
| `frontend/src/pages/api/admin/blog/categories/reorder.ts` | API: 순서 일괄 변경 |
| `frontend/src/pages/api/admin/blog/category-groups/list.ts` | API: 그룹 목록 |
| `frontend/src/pages/api/admin/blog/category-groups/save.ts` | API: 그룹 생성/수정 |
| `frontend/src/pages/api/admin/blog/category-groups/delete.ts` | API: 그룹 삭제 |

### Modified Files

| File | Change |
|------|--------|
| `frontend/src/lib/categories.ts` | 블로그 전용 배열/함수 제거, 기존 뉴스/홈 함수 유지 |
| `frontend/src/lib/pageData/blogSidebar.ts` | `BLOG_SUB_CATEGORIES` 참조를 파라미터 기반으로 전환 |
| `frontend/src/lib/pageData/blogDetailPage.ts` | `BLOG_CATEGORIES` import 제거, DB 카테고리 사용 |
| `frontend/src/components/blog/BlogSidebar.astro` | DB 카테고리 prop 사용 + 클릭 동작 분리 |
| `frontend/src/components/blog/BlogFeaturedCard.astro` | DB 카테고리 prop으로 라벨/색상 조회 |
| `frontend/src/components/blog/BlogListItem.astro` | DB 카테고리 prop으로 라벨/색상 조회 |
| `frontend/src/components/blog/BlogBreadcrumb.astro` | 카테고리 링크 URL → `/{locale}/blog/category/{slug}/` |
| `frontend/src/components/blog/BlogArticleLayout.astro` | DB 카테고리 prop 사용 |
| `frontend/src/pages/ko/blog/index.astro` | DB에서 카테고리 fetch, 하위 컴포넌트에 전달 |
| `frontend/src/pages/en/blog/index.astro` | 동일 |
| `frontend/src/pages/ko/blog/[slug].astro` | DB 카테고리 fetch, BlogArticleLayout에 전달 |
| `frontend/src/pages/en/blog/[slug].astro` | 동일 |
| `frontend/src/pages/api/admin/blog/save.ts` | `BLOG_CATEGORIES` 검증 제거 (FK가 대체) |
| `frontend/src/pages/admin/blog/edit/[slug].astro` | 카테고리 드롭다운을 DB 데이터로 전환 |
| `frontend/src/pages/admin/blog/index.astro` | 카테고리 필터를 DB 데이터로 전환 |
| `frontend/package.json` | SortableJS 의존성 추가 |

---

## Chunk 1: DB Migration

### Task 1: Supabase 마이그레이션 파일 작성

**Files:**
- Create: `supabase/migrations/00034_blog_category_system.sql`

- [ ] **Step 1: 마이그레이션 SQL 작성**

`supabase/migrations/00034_blog_category_system.sql` 파일을 생성한다. 내용은 아래 순서대로:

1. `moddatetime` extension 활성화
2. `category_groups` 테이블 생성 (slug PK, label_ko, label_en, sort_order, created_at, updated_at) + seed (main, sub)
3. `blog_categories` 테이블 생성 + seed (5개 카테고리, 아이콘 SVG 포함)
4. 기존 CHECK 제약조건 DROP: `ALTER TABLE blog_posts DROP CONSTRAINT blog_posts_category_check;`
5. `blog_posts.category` FK 추가: `ON UPDATE CASCADE ON DELETE RESTRICT`
6. `category_subscriptions` 테이블 생성 (미래용, user_id FK에 `ON DELETE CASCADE`)
7. `pinned_posts` 테이블 생성 (미래용)
8. 모든 테이블 RLS 활성화 + 정책 생성 (스펙 Section 1.7의 SQL 그대로)
9. `moddatetime` 트리거 생성 (blog_categories, category_groups)

참조할 데이터:
- seed 색상: study `#6E9682`, project `#8282AF`, career `#8C94AA`, work-note `#6496AA`, daily `#AA8282`
- seed 아이콘 SVG path: 스펙 문서 Section 1.2의 icon 컬럼 참조
- RLS SQL: 스펙 문서 Section 1.7 참조

- [ ] **Step 2: 로컬 DB에 마이그레이션 적용**

```bash
cd supabase && supabase db reset
```

마이그레이션이 에러 없이 적용되는지 확인.

- [ ] **Step 3: seed 데이터 확인**

```sql
SELECT * FROM category_groups ORDER BY sort_order;
SELECT slug, label_ko, color, group_slug, sort_order FROM blog_categories ORDER BY group_slug, sort_order;
```

기대: 2개 그룹 + 5개 카테고리 정상 조회.

- [ ] **Step 4: FK 동작 확인**

```sql
-- 삭제 제한 확인
DELETE FROM blog_categories WHERE slug = 'study';
-- 기대: ERROR (foreign key violation, 글이 있으므로)

-- cascade 확인
UPDATE blog_categories SET slug = 'study-test' WHERE slug = 'study';
SELECT DISTINCT category FROM blog_posts WHERE category = 'study-test';
-- 기대: 글의 category도 변경됨

-- 원복
UPDATE blog_categories SET slug = 'study' WHERE slug = 'study-test';
```

- [ ] **Step 5: 커밋**

```bash
git add supabase/migrations/00034_blog_category_system.sql
git commit -m "feat: add blog category system DB migration"
```

---

## Chunk 2: Frontend Data Layer

### Task 2: 카테고리 DB fetch 함수

**Files:**
- Create: `frontend/src/lib/pageData/blogCategories.ts`

- [ ] **Step 1: blogCategories.ts 작성**

타입 정의 + Supabase fetch 함수:

```typescript
import type { SupabaseClient } from '@supabase/supabase-js';

export interface BlogCategory {
  id: string;
  slug: string;
  label_ko: string;
  label_en: string;
  description_ko: string | null;
  description_en: string | null;
  color: string;
  icon: string | null;
  group_slug: string;
  sort_order: number;
  is_visible: boolean;
  write_mode: string;
  banner_url: string | null;
  guidelines: string | null;
}

export interface CategoryGroup {
  slug: string;
  label_ko: string;
  label_en: string;
  sort_order: number;
}

// 퍼블릭용: RLS가 is_visible 필터링 처리
export async function fetchCategories(supabase: SupabaseClient): Promise<BlogCategory[]> {
  const { data } = await supabase
    .from('blog_categories')
    .select('*')
    .order('group_slug')
    .order('sort_order');
  return data ?? [];
}

// 단일 카테고리 조회
export async function fetchCategoryBySlug(
  supabase: SupabaseClient, slug: string
): Promise<BlogCategory | null> {
  const { data } = await supabase
    .from('blog_categories')
    .select('*')
    .eq('slug', slug)
    .single();
  return data;
}

// 그룹 조회
export async function fetchCategoryGroups(supabase: SupabaseClient): Promise<CategoryGroup[]> {
  const { data } = await supabase
    .from('category_groups')
    .select('*')
    .order('sort_order');
  return data ?? [];
}

// Admin용: 카테고리 + 글 수 (admin의 auth token으로 호출 — RLS가 admin에게 전체 공개)
export async function fetchCategoriesWithPostCount(
  supabase: SupabaseClient
): Promise<(BlogCategory & { post_count: number })[]> {
  const { data: categories } = await supabase
    .from('blog_categories')
    .select('*')
    .order('group_slug')
    .order('sort_order');

  if (!categories) return [];

  const { data: counts } = await supabase
    .from('blog_posts')
    .select('category')
    .not('category', 'is', null);

  const countMap = new Map<string, number>();
  for (const row of counts ?? []) {
    countMap.set(row.category, (countMap.get(row.category) ?? 0) + 1);
  }

  return categories.map(cat => ({
    ...cat,
    post_count: countMap.get(cat.slug) ?? 0,
  }));
}
```

주의: `fetchAllCategories`를 service role로 호출하지 않는다. Admin은 본인의 auth token으로 호출하면 RLS 정책이 `is_visible` 무관하게 전체 조회를 허용한다 (CLAUDE.md: "Never use the Supabase Service Role Key in the frontend").

- [ ] **Step 2: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/lib/pageData/blogCategories.ts
git commit -m "feat: add blog categories DB fetch functions"
```

### Task 3: categories.ts 하위 호환 리팩터링

**Files:**
- Modify: `frontend/src/lib/categories.ts`
- Modify: `frontend/src/lib/pageData/blogSidebar.ts`
- Modify: `frontend/src/lib/pageData/blogDetailPage.ts`
- Modify: `frontend/src/pages/api/admin/blog/save.ts`

- [ ] **Step 1: categories.ts 수정 — 블로그 전용 배열만 제거**

**유지하는 것** (뉴스/홈/Newsprint 소비자 보호):
- `CategorySlug` 타입 (리터럴 유니온)
- `CATEGORY_LABELS` 맵 (뉴스 포함)
- `CATEGORY_COLOR_VARS` 맵
- `getCategoryLabel(locale, category)` — 기존 2-arg 시그니처
- `getCategoryColorVar(category)` — 기존 1-arg 시그니처
- `normalizeCategorySlug(category)`
- `NEWS_CATEGORY`
- `getDefaultCategories()`
- `getPostTypeLabel(locale, postType)`
- `POST_TYPE_LABELS` (내부 상수)

**제거하는 것** (블로그 전용, DB로 대체):
- `BlogCategorySlug` 타입
- `BlogCategoryGroupSlug` 타입
- `BLOG_SIDEBAR_LABELS` 맵
- `BLOG_GROUP_LABELS` 맵
- `BLOG_MAIN_CATEGORIES` 배열
- `BLOG_SUB_CATEGORIES` 배열
- `BLOG_CATEGORIES` 배열
- `BLOG_CATEGORY_GROUPS` 배열
- `getBlogSidebarLabel()` 함수
- `getBlogCategoryGroupLabel()` 함수

제거 시 grep으로 사용처 확인. 블로그 컴포넌트에서만 사용되는지 검증 (Task 5에서 해당 컴포넌트들도 수정하므로 괜찮음).

- [ ] **Step 2: blogSidebar.ts 수정**

`BLOG_SUB_CATEGORIES.includes(category)` 참조를 파라미터 기반으로 전환:
- `getBlogSidebarCategoryState`에 `subCategorySlugs: string[]` 파라미터 추가
- 호출측에서 DB 카테고리를 기반으로 sub 그룹의 slug 배열을 전달

- [ ] **Step 3: blogDetailPage.ts 수정**

`BLOG_CATEGORIES` import → 제거. 카테고리 기반 쿼리 필터가 있으면:
- `.in('category', BLOG_CATEGORIES)` → 별도 파라미터로 카테고리 slugs 받거나, 필터 자체를 제거 (FK 제약조건이 유효한 카테고리만 허용하므로)

- [ ] **Step 4: api/admin/blog/save.ts 수정**

`BLOG_CATEGORIES` import 제거. 카테고리 유효성 검증:
- 기존: `if (!BLOG_CATEGORIES.includes(category))` 하드코딩 체크
- 변경: 제거 — FK 제약조건이 유효하지 않은 카테고리를 DB 레벨에서 거부

- [ ] **Step 5: 빌드 확인**

```bash
cd frontend && npm run build
```

빌드가 반드시 성공해야 함. 실패 시 제거된 export를 아직 사용하는 파일이 있다는 의미이므로 해당 파일도 이 step에서 수정.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/categories.ts \
       frontend/src/lib/pageData/blogSidebar.ts \
       frontend/src/lib/pageData/blogDetailPage.ts \
       frontend/src/pages/api/admin/blog/save.ts
git commit -m "refactor: remove blog-specific hardcoded arrays from categories.ts"
```

---

## Chunk 3: 블로그 페이지 DB 전환

### Task 4: 블로그 index 페이지 DB 전환

**Files:**
- Modify: `frontend/src/pages/ko/blog/index.astro`
- Modify: `frontend/src/pages/en/blog/index.astro`

- [ ] **Step 1: ko/blog/index.astro 수정**

서버 코드에서:
1. `fetchCategories(supabase)`, `fetchCategoryGroups(supabase)` 호출 추가
2. 조회한 `categories`, `groups`를 `BlogSidebar`, `BlogFeaturedCard`, `BlogListItem`에 prop으로 전달
3. 기존 `BLOG_CATEGORIES` import가 있으면 제거

- [ ] **Step 2: en/blog/index.astro 동일 수정**

- [ ] **Step 3: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/pages/ko/blog/index.astro frontend/src/pages/en/blog/index.astro
git commit -m "refactor: blog index pages fetch categories from DB"
```

### Task 5: 블로그 컴포넌트 DB 전환

**Files:**
- Modify: `frontend/src/components/blog/BlogSidebar.astro`
- Modify: `frontend/src/components/blog/BlogFeaturedCard.astro`
- Modify: `frontend/src/components/blog/BlogListItem.astro`
- Modify: `frontend/src/components/blog/BlogBreadcrumb.astro`
- Modify: `frontend/src/components/blog/BlogArticleLayout.astro`

- [ ] **Step 1: BlogSidebar.astro 수정**

주요 변경:
1. Props에 `categories: BlogCategory[]`와 `groups: CategoryGroup[]` 추가
2. 기존 `BLOG_CATEGORIES`, `BLOG_CATEGORY_GROUPS`, `getBlogSidebarLabel`, `getBlogCategoryGroupLabel` import 제거
3. `CATEGORY_ICONS` 하드코딩 제거 → DB의 `category.icon` 필드 사용
4. 카테고리 라벨/색상 → `category.label_ko` / `category.color` 직접 접근
5. 그룹 라벨 → `group` 객체에서 직접 접근
6. 클릭 동작 분리:

```html
<!-- 변경 전: 카테고리 전체가 button -->
<button class="blog-folder-btn">
  <svg class="blog-folder-arrow">...</svg>
  <span>{categoryLabel}</span>
</button>

<!-- 변경 후: 화살표는 button, 이름은 link -->
<div class="blog-folder-header">
  <button class="blog-folder-arrow-btn" type="button" aria-expanded="...">
    <svg class="blog-folder-arrow">...</svg>
  </button>
  <a class="blog-folder-category-link" href={`/${locale}/blog/category/${category.slug}/`}>
    <svg class="blog-folder-icon" set:html={category.icon} style={`color: ${category.color}`} .../>
    <span>{category[`label_${locale}`]}</span>
    <span class="blog-folder-count">({count})</span>
  </a>
</div>
```

7. `<script>` 블록: `.blog-folder-arrow-btn` 클릭 시 펼침/접힘
8. 현재 카테고리 페이지에 있을 때 active 스타일

- [ ] **Step 2: BlogFeaturedCard.astro 수정**

- Props에 `categories: BlogCategory[]` 추가
- 카테고리 라벨: `categories.find(c => c.slug === post.category)?.[`label_${locale}`]`
- 카테고리 색상: `categories.find(c => c.slug === post.category)?.color`
- 기존 `getCategoryLabel`, `getCategoryColorVar` import 제거

- [ ] **Step 3: BlogListItem.astro 수정**

BlogFeaturedCard와 동일 패턴.

- [ ] **Step 4: BlogBreadcrumb.astro 수정**

- Props에 `categories: BlogCategory[]` 추가 (라벨 조회용)
- 카테고리 링크 URL 변경:
  - 기존: `/{locale}/blog/?category={category}` (query param)
  - 변경: `/{locale}/blog/category/{slug}/` (카테고리 페이지)

- [ ] **Step 5: BlogArticleLayout.astro 수정**

- Props에 `categories: BlogCategory[]` 추가
- 기존 `getCategoryLabel(locale, post.category)`, `getCategoryColorVar(post.category)` 호출 → DB 데이터 직접 접근으로 변경
- BlogBreadcrumb에 `categories` prop 전달

- [ ] **Step 6: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 7: 로컬 확인**

```bash
cd frontend && npm run dev
```

확인:
- 블로그 메인 → 사이드바 카테고리 정상 표시
- 카테고리명 클릭 → 카테고리 페이지 이동 시도 (아직 404 — 카테고리 페이지 미구현)
- 화살표 클릭 → 폴더 펼침/접힘
- Featured 카드, 리스트 아이템의 카테고리 배지 정상

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/blog/
git commit -m "refactor: blog components use DB category data"
```

### Task 6: 블로그 detail 페이지 + Admin 에디터 DB 전환

**Files:**
- Modify: `frontend/src/pages/ko/blog/[slug].astro`
- Modify: `frontend/src/pages/en/blog/[slug].astro`
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro`
- Modify: `frontend/src/pages/admin/blog/index.astro`

- [ ] **Step 1: ko/blog/[slug].astro 수정**

서버 코드에서 `fetchCategories(supabase)` 추가. 결과를 BlogSidebar, BlogArticleLayout (→ BlogBreadcrumb) 등에 `categories` prop으로 전달.

- [ ] **Step 2: en/blog/[slug].astro 동일 수정**

- [ ] **Step 3: admin/blog/edit/[slug].astro 수정**

- 기존 `BLOG_CATEGORIES` import 제거
- 카테고리 드롭다운: `fetchCategories(supabase)` 결과로 `<option>` 동적 생성
- 이제 Admin이 추가한 새 카테고리도 드롭다운에 자동 표시됨

- [ ] **Step 4: admin/blog/index.astro 수정**

- 카테고리 필터 드롭다운이 하드코딩되어 있으면 DB 데이터로 전환
- `fetchCategories(supabase)` 결과로 필터 옵션 동적 생성

- [ ] **Step 5: 빌드 확인 + 로컬 확인**

```bash
cd frontend && npm run build
cd frontend && npm run dev
```

블로그 상세 페이지 + Admin 에디터 정상 동작 확인.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/pages/ko/blog/[slug].astro \
       frontend/src/pages/en/blog/[slug].astro \
       frontend/src/pages/admin/blog/edit/[slug].astro \
       frontend/src/pages/admin/blog/index.astro
git commit -m "refactor: blog detail and admin pages use DB categories"
```

---

## Chunk 4: 카테고리 페이지

### Task 7: BlogCategoryHeader 컴포넌트

**Files:**
- Create: `frontend/src/components/blog/BlogCategoryHeader.astro`
- Modify: `frontend/src/styles/global.css` (CSS 추가)

- [ ] **Step 1: BlogCategoryHeader.astro 작성**

```typescript
interface Props {
  locale: 'en' | 'ko';
  category: BlogCategory;
  postCount: number;
}
```

구조:
```html
<header class="blog-category-header" style={`--category-color: ${category.color}`}>
  {category.banner_url && (
    <img class="blog-category-banner" src={category.banner_url} alt="" />
  )}
  <div class="blog-category-header-content">
    <div class="blog-category-title">
      {category.icon && (
        <svg class="blog-category-icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.8"
             stroke-linecap="round" stroke-linejoin="round"
             set:html={category.icon} />
      )}
      <h1>{category[`label_${locale}`]}</h1>
    </div>
    {description && <p class="blog-category-description">{description}</p>}
    <span class="blog-category-count">
      {locale === 'ko' ? `${postCount}개의 글` : `${postCount} posts`}
    </span>
  </div>
</header>
```

CSS를 `global.css`에 추가: `.blog-category-header`, `.blog-category-title`, `.blog-category-icon` (color: `var(--category-color)` 사용), `.blog-category-description`, `.blog-category-count`.

- [ ] **Step 2: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/components/blog/BlogCategoryHeader.astro frontend/src/styles/global.css
git commit -m "feat: add BlogCategoryHeader component"
```

### Task 8: 카테고리 페이지

**Files:**
- Create: `frontend/src/pages/ko/blog/category/[slug].astro`
- Create: `frontend/src/pages/en/blog/category/[slug].astro`

- [ ] **Step 1: ko/blog/category/[slug].astro 작성**

```typescript
export const prerender = false;
```

서버 코드:
1. `Astro.params.slug`에서 slug 추출
2. `fetchCategoryBySlug(supabase, slug)` → 없으면 `return Astro.redirect('/404')`  또는 404 응답
3. `category.is_visible === false && !locals.isAdmin` → 404
4. 병렬 fetch (Promise.all):
   - 해당 카테고리 published posts: `supabase.from('blog_posts').select('*').eq('category', slug).eq('status', 'published').eq('locale', locale).order('created_at', { ascending: false })`
   - 전체 카테고리 + 그룹 (사이드바용): `fetchCategories(supabase)`, `fetchCategoryGroups(supabase)`
   - 유저 북마크/읽기 상태 (인증 시)
5. 글 목록을 10개 단위 배치로 분할 (기존 blog index 패턴)
6. `BlogShell` + `BlogCategoryHeader` + `BlogListItem` 목록 렌더링
7. 무한 스크롤 sentinel (기존 blog index의 `<script>` 패턴 그대로 복사)

SEO (`Head` 컴포넌트):
- title: `${category[`label_${locale}`]} | 0to1`
- description: `category[`description_${locale}`]` 또는 기본값
- canonical: `/${locale}/blog/category/${slug}/`
- hreflang: ko ↔ en 쌍

Empty state:
- 글 0개 → "아직 작성된 글이 없습니다" / "No posts yet" 표시

- [ ] **Step 2: en/blog/category/[slug].astro 작성**

ko 버전과 동일 구조, locale만 `en`.

- [ ] **Step 3: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: 로컬 확인**

```bash
cd frontend && npm run dev
```

확인:
- `/ko/blog/category/study/` → 학습 카테고리 헤더 + 해당 글 목록
- `/ko/blog/category/nonexistent/` → 404
- 사이드바 카테고리명 클릭 → 카테고리 페이지로 이동
- 무한 스크롤
- 브레드크럼 정상
- `/en/blog/category/study/` → EN 버전 확인

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/ko/blog/category/ frontend/src/pages/en/blog/category/
git commit -m "feat: add blog category filter pages"
```

---

## Chunk 5: Admin API Endpoints

### Task 9: 카테고리 API 엔드포인트

**Files:**
- Create: `frontend/src/pages/api/admin/blog/categories/list.ts`
- Create: `frontend/src/pages/api/admin/blog/categories/save.ts`
- Create: `frontend/src/pages/api/admin/blog/categories/delete.ts`
- Create: `frontend/src/pages/api/admin/blog/categories/reorder.ts`

모든 엔드포인트는 기존 `api/admin/blog/save.ts` 패턴을 따름:
- `export const POST: APIRoute`
- `const accessToken = locals.accessToken; if (!accessToken) return 401`
- `if (!locals.isAdmin) return 403`
- `const body = await request.json()`
- try/catch + JSON 응답

- [ ] **Step 1: list.ts 작성**

- admin의 auth token으로 `blog_categories` 전체 조회 (RLS가 admin에게 전체 공개)
- 각 카테고리에 `post_count` 추가 (`blog_posts`에서 category별 COUNT)
- `category_groups`도 함께 조회
- 응답: `{ categories: [...], groups: [...] }`

- [ ] **Step 2: save.ts 작성**

- body: `{ id?, slug, label_ko, label_en, description_ko?, description_en?, color, icon?, group_slug, sort_order, is_visible, write_mode, banner_url?, guidelines? }`
- `id` 없으면 INSERT, 있으면 UPDATE
- slug 유니크 위반 시 `{ error: "이미 사용 중인 슬러그입니다" }` + 409 반환
- slug 변경은 `ON UPDATE CASCADE`로 blog_posts 자동 반영 (DB 레벨)
- 응답: 저장된 카테고리 데이터

- [ ] **Step 3: delete.ts 작성**

- body: `{ id }`
- 해당 카테고리에 blog_posts 존재 여부 확인:
  ```typescript
  const { count } = await supabase.from('blog_posts').select('id', { count: 'exact', head: true }).eq('category', category.slug);
  if (count && count > 0) return { error: `이 카테고리에 ${count}개의 글이 있습니다. 글을 다른 카테고리로 이동한 후 삭제해주세요.` } + 400
  ```
- 없으면 DELETE
- DB FK `ON DELETE RESTRICT`가 이중 보호

- [ ] **Step 4: reorder.ts 작성**

- body: `{ items: [{ id, sort_order, group_slug }] }`
- 각 항목별 UPDATE: `supabase.from('blog_categories').update({ sort_order, group_slug }).eq('id', id)`
- 순차 실행 (Supabase JS에서 트랜잭션 직접 지원 안 함 — 항목 수가 적으므로 순차 UPDATE 허용)

- [ ] **Step 5: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/pages/api/admin/blog/categories/
git commit -m "feat: add admin category CRUD API endpoints"
```

### Task 10: 그룹 API 엔드포인트

**Files:**
- Create: `frontend/src/pages/api/admin/blog/category-groups/list.ts`
- Create: `frontend/src/pages/api/admin/blog/category-groups/save.ts`
- Create: `frontend/src/pages/api/admin/blog/category-groups/delete.ts`

- [ ] **Step 1: list.ts 작성**

동일 인증 패턴. `category_groups` 전체 조회, sort_order 순.

- [ ] **Step 2: save.ts 작성**

- body: `{ original_slug?, slug, label_ko, label_en, sort_order }`
- `original_slug` 없으면 INSERT (새 그룹), 있으면 UPDATE
- 그룹 slug 변경 시: `original_slug`로 기존 레코드 찾아 `slug` 업데이트. `blog_categories.group_slug` FK도 CASCADE 필요 — 단, 현재 FK에 CASCADE 없으므로 application 레벨에서 `blog_categories`의 `group_slug`도 함께 업데이트.

- [ ] **Step 3: delete.ts 작성**

- body: `{ slug }`
- 소속 카테고리 존재 확인: `supabase.from('blog_categories').select('id', { count: 'exact', head: true }).eq('group_slug', slug)`
- 있으면 에러, 없으면 DELETE

- [ ] **Step 4: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/api/admin/blog/category-groups/
git commit -m "feat: add admin category groups API endpoints"
```

---

## Chunk 6: Admin 카테고리 관리 페이지

### Task 11: SortableJS 설치

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 설치**

```bash
cd frontend && npm install sortablejs
```

- [ ] **Step 2: 커밋**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add sortablejs dependency"
```

### Task 12: Admin 카테고리 관리 페이지

**Files:**
- Create: `frontend/src/pages/admin/blog/categories/index.astro`
- Modify: `frontend/src/styles/global.css` (admin CSS 추가)

- [ ] **Step 1: 서버 코드**

기존 `/admin/blog/index.astro` 패턴:
- `export const prerender = false`
- `Astro.locals.accessToken`, `Astro.locals.isAdmin` 체크
- `fetchCategoriesWithPostCount(supabase)`, `fetchCategoryGroups(supabase)` 호출

- [ ] **Step 2: 목록 HTML**

그룹별 카테고리 표시:
- 각 그룹 섹션: 헤더 (그룹 라벨 + 총 글 수 + [그룹 편집]) + 카테고리 리스트
- 각 카테고리 행: 드래그 핸들(☰) + 아이콘(SVG, `set:html={cat.icon}`) + 라벨 + 슬러그(muted) + 글 수 + [편집] 버튼
- 각 카테고리 행에 `data-id`, `data-slug`, `data-group`, `data-post-count` 등 data 속성
- 상단 [+ 새 카테고리] 버튼
- 하단 [+ 새 그룹 추가] 버튼
- 각 그룹 리스트 컨테이너에 `data-group-slug` 속성 (SortableJS 그룹 간 이동용)

CSS: `global.css`에 `.admin-categories-*` 셀렉터 추가.

- [ ] **Step 3: 편집 모달 HTML**

슬라이드 패널 (기존 admin 에디터 스타일 참고):
- slug: `<input>` — 변경 시 "이 카테고리에 N개 글의 category 필드가 함께 변경됩니다" 경고 (`data-post-count`로 동적 표시)
- label_ko, label_en: `<input>`
- description_ko, description_en: `<textarea>`
- color: `<input type="color">`
- icon: `<select>` 프리셋 + SVG 미리보기 (기존 5개 아이콘 + "커스텀 SVG" 옵션)
- group_slug: `<select>` (DB 그룹 목록)
- is_visible: `<input type="checkbox">`
- write_mode: `<select>` (admin_only / members / approved_only)
- banner_url: `<input>` (URL 입력, 파일 업로드는 추후)
- guidelines: `<textarea>`
- 위험 영역: 삭제 버튼 (post_count > 0이면 disabled + 안내 메시지)

그룹 편집: 인라인 편집 (라벨 KO/EN input 표시 → 저장/취소)

- [ ] **Step 4: `<script>` 블록 — API 연동 + 드래그앤드롭**

```javascript
import Sortable from 'sortablejs';

document.addEventListener('DOMContentLoaded', () => {
  // 1. 드래그앤드롭 초기화
  // 각 [data-group-slug] 컨테이너에 Sortable 인스턴스 생성
  // group: 'categories' → 그룹 간 이동 허용
  // onEnd: reorder API 호출 (변경된 항목의 id, sort_order, group_slug 수집)

  // 2. [편집] 클릭 → 모달에 data 속성값 채우기 → 모달 표시
  // [저장] 클릭 → save API fetch → 성공 시 페이지 새로고침

  // 3. [+ 새 카테고리] → 빈 모달 → save API (id 없음)

  // 4. [삭제] → confirm() → delete API → 성공 시 페이지 새로고침

  // 5. 그룹 편집/추가/삭제 → category-groups API 연동

  // 6. slug 변경 감지 → 경고 메시지 표시/숨김
});
```

`client:load` 사용 안 함. nonce 불필요 — 일반 `<script>` 블록은 Astro가 번들링.

- [ ] **Step 5: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: 로컬 확인**

```bash
cd frontend && npm run dev
```

확인:
- `/admin/blog/categories/` → 그룹별 카테고리 목록
- 카테고리 편집 → 저장 → 목록 반영
- 새 카테고리 추가 → 블로그 사이드바에 표시
- 드래그 순서 변경 → 새로고침 후 유지
- 글 있는 카테고리 삭제 → 차단 + 안내
- 그룹 편집/추가/삭제
- 슬러그 변경 → 경고 → 저장 후 블로그에서 정상 접근

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/pages/admin/blog/categories/index.astro frontend/src/styles/global.css
git commit -m "feat: add admin category management page"
```

---

## Chunk 7: 정리 및 검증

### Task 13: 하드코딩 잔여 참조 정리

- [ ] **Step 1: 미사용 참조 스캔**

```bash
cd frontend && grep -rn "BLOG_CATEGORIES\|BLOG_CATEGORY_GROUPS\|BLOG_MAIN_CATEGORIES\|BLOG_SUB_CATEGORIES\|BlogCategorySlug\|BlogCategoryGroupSlug\|BLOG_SIDEBAR_LABELS\|BLOG_GROUP_LABELS\|getBlogSidebarLabel\|getBlogCategoryGroupLabel" src/ --include="*.ts" --include="*.astro"
```

결과가 있으면 해당 파일 수정. 결과가 없으면 정리 완료.

- [ ] **Step 2: categories.ts 미사용 export 제거**

Task 3에서 제거했어야 하지만 빌드 호환 때문에 남겨둔 것 중, 더 이상 참조가 없는 것들 최종 제거.

- [ ] **Step 3: CSS 변수 정리**

`global.css`에서 `--color-cat-*` 변수가 블로그 컴포넌트에서 더 이상 사용되지 않는지 확인. 뉴스/Newsprint에서 아직 사용 중이면 유지. 블로그에서만 사용되던 것들은 제거 대상이지만, 뉴스 카테고리(`--color-cat-ainews`)와 공유 변수이므로 전체 스캔 후 판단.

- [ ] **Step 4: 빌드 확인**

```bash
cd frontend && npm run build
```

에러 0 확인.

- [ ] **Step 5: 커밋**

```bash
git add -A
git commit -m "chore: clean up remaining hardcoded category references"
```

### Task 14: 전체 기능 검증

- [ ] **Step 1: 전체 빌드**

```bash
cd frontend && npm run build
```

에러 0.

- [ ] **Step 2: E2E 수동 검증 체크리스트**

퍼블릭 블로그:
- [ ] `/ko/blog/` → 사이드바 카테고리 정상 표시
- [ ] 사이드바 카테고리명 클릭 → 카테고리 페이지 이동
- [ ] 사이드바 화살표 클릭 → 폴더 펼침/접힘
- [ ] `/ko/blog/category/study/` → 학습 카테고리 글만 표시
- [ ] 카테고리 헤더: 아이콘, 라벨, 설명, 글 수
- [ ] 무한 스크롤 동작
- [ ] 존재하지 않는 카테고리 → 404
- [ ] 블로그 상세 → 브레드크럼 카테고리 링크가 카테고리 페이지로 연결
- [ ] EN 버전 동일 동작

Admin:
- [ ] `/admin/blog/categories/` → 그룹별 카테고리 목록
- [ ] 카테고리 추가 → 저장 → 블로그 사이드바에 표시
- [ ] 카테고리 편집 (라벨, 색상) → 블로그에 반영
- [ ] 카테고리 순서 드래그 → 사이드바 순서 변경
- [ ] 카테고리 삭제 (글 0개) → 성공
- [ ] 카테고리 삭제 (글 있음) → 차단 + 안내
- [ ] 그룹 추가/편집/삭제
- [ ] 슬러그 변경 → 경고 확인 → 변경 후 기존 글 정상 접근

뉴스/홈 (regression 없음 확인):
- [ ] `/ko/` → 홈 뉴스 카드 정상 표시
- [ ] `/ko/news/` → Newsprint 레이아웃 정상
- [ ] Admin 블로그 에디터 → 카테고리 드롭다운에 DB 카테고리 표시

- [ ] **Step 3: 최종 커밋 + 푸시**

```bash
git push origin main
```
