# Blog Category System Design

- **Date**: 2026-03-20
- **Status**: Draft
- **Approach**: B (Community-ready schema + Blog feature implementation)

## Overview

블로그 카테고리 시스템을 하드코딩에서 DB 기반으로 전환하고, 카테고리별 글 목록 페이지와 Admin 관리 페이지를 구현한다. 장기적으로 커뮤니티(게시판) 전환을 고려하여 스키마를 설계한다.

## Goals

1. 카테고리 클릭 시 해당 카테고리 글만 모아보는 페이지 제공
2. Admin에서 카테고리 전체 CRUD 관리 (추가/삭제/이름/색상/아이콘/순서/그룹/슬러그/설명/공개여부)
3. 커뮤니티 전환 시 스키마 마이그레이션 없이 기능 활성화만으로 확장 가능한 구조

## Non-Goals (현재 범위 밖)

- 유저 글쓰기 기능
- 역할 시스템 (Admin/Moderator/Member/Guest)
- 모더레이션 도구 (신고, 자동 숨김)
- 카테고리 구독/팔로우 UI
- 블로그/커뮤니티 URL 분리 (`/blog/` vs `/community/`)

---

## 1. DB Schema

### 1.1 `category_groups`

카테고리를 묶는 그룹 (현재: 주요 기록, 작은 노트).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `slug` | text | PK | `main`, `sub` 등 |
| `label_ko` | text | NOT NULL | 한국어 라벨 |
| `label_en` | text | NOT NULL | 영어 라벨 |
| `sort_order` | integer | NOT NULL DEFAULT 0 | 그룹 간 정렬 |
| `created_at` | timestamptz | NOT NULL DEFAULT now() | |
| `updated_at` | timestamptz | NOT NULL DEFAULT now() | |

Seed data:

| slug | label_ko | label_en | sort_order |
|------|----------|----------|------------|
| `main` | 주요 기록 | Main Posts | 0 |
| `sub` | 작은 노트 | Small Notes | 1 |

### 1.2 `blog_categories`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | uuid | PK, DEFAULT gen_random_uuid() | |
| `slug` | text | UNIQUE, NOT NULL | URL 식별자 |
| `label_ko` | text | NOT NULL | 한국어 라벨 |
| `label_en` | text | NOT NULL | 영어 라벨 |
| `description_ko` | text | nullable | 카테고리 설명 (한국어) |
| `description_en` | text | nullable | 카테고리 설명 (영어) |
| `color` | text | NOT NULL | hex 색상값 (예: `#3B82F6`) |
| `icon` | text | nullable | SVG path data |
| `group_slug` | text | FK -> category_groups.slug, NOT NULL | 소속 그룹 |
| `sort_order` | integer | NOT NULL DEFAULT 0 | 그룹 내 정렬 순서 |
| `is_visible` | boolean | NOT NULL DEFAULT true | 공개/비공개 |
| `write_mode` | text | NOT NULL DEFAULT 'admin_only' | `admin_only` / `members` / `approved_only` |
| `banner_url` | text | nullable | 카테고리 배너 이미지 (커뮤니티용) |
| `guidelines` | text | nullable | 글쓰기 가이드라인 (커뮤니티용) |
| `created_at` | timestamptz | NOT NULL DEFAULT now() | |
| `updated_at` | timestamptz | NOT NULL DEFAULT now() | |

Seed data (기존 5개 카테고리):

| slug | label_ko | label_en | color | icon | group_slug | sort_order |
|------|----------|----------|-------|------|------------|------------|
| `study` | 학습 노트 | Study Notes | `#6E9682` | `<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>` | `main` | 0 |
| `project` | 프로젝트 기록 | Project Log | `#8282AF` | `<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>` | `main` | 1 |
| `career` | 커리어 생각 | Career Thoughts | `#8C94AA` | `<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>` | `main` | 2 |
| `work-note` | 작업 메모 | Work Notes | `#6496AA` | `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/>` | `sub` | 0 |
| `daily` | 일상 | Daily Life | `#AA8282` | `<path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>` | `sub` | 1 |

모든 카테고리의 `write_mode`는 `admin_only`로 seed.
색상값은 dark 테마 기준. 테마별 색상 분기는 CSS에서 처리하되, DB에는 대표 색상 1개만 저장.

### 1.3 `category_subscriptions` (미래용, 구조만 생성)

| Column | Type | Constraints |
|--------|------|-------------|
| `user_id` | uuid | FK -> auth.users ON DELETE CASCADE, NOT NULL |
| `category_id` | uuid | FK -> blog_categories.id ON DELETE CASCADE, NOT NULL |
| `created_at` | timestamptz | NOT NULL DEFAULT now() |
| PK | | (user_id, category_id) |

### 1.4 `pinned_posts` (미래용, 구조만 생성)

| Column | Type | Constraints |
|--------|------|-------------|
| `category_id` | uuid | FK -> blog_categories.id ON DELETE CASCADE, NOT NULL |
| `post_id` | uuid | FK -> blog_posts.id ON DELETE CASCADE, NOT NULL |
| `sort_order` | integer | NOT NULL DEFAULT 0 |
| `pinned_at` | timestamptz | NOT NULL DEFAULT now() |
| PK | | (category_id, post_id) |

### 1.5 `blog_posts` FK 연결

기존 `blog_posts.category`에 CHECK 제약조건(`blog_posts_category_check`)이 있으므로 먼저 제거한 후 FK를 추가한다.

```sql
-- 기존 CHECK 제약조건 제거 (00018에서 추가된 것)
ALTER TABLE blog_posts
DROP CONSTRAINT blog_posts_category_check;

-- FK 추가
ALTER TABLE blog_posts
ADD CONSTRAINT fk_blog_posts_category
FOREIGN KEY (category) REFERENCES blog_categories(slug)
ON UPDATE CASCADE
ON DELETE RESTRICT;
```

- `ON UPDATE CASCADE`: 슬러그 변경 시 글의 category도 자동 업데이트
- `ON DELETE RESTRICT`: 글이 있는 카테고리는 DB 레벨에서 삭제 차단 (application 레벨 + DB 레벨 이중 보호)

### 1.6 `updated_at` 자동 갱신

`moddatetime` 트리거로 UPDATE 시 `updated_at` 자동 갱신:

```sql
-- extension 활성화 (이미 활성화되어 있을 수 있음)
CREATE EXTENSION IF NOT EXISTS moddatetime;

CREATE TRIGGER set_blog_categories_updated_at
BEFORE UPDATE ON blog_categories
FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);

CREATE TRIGGER set_category_groups_updated_at
BEFORE UPDATE ON category_groups
FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);
```

### 1.7 RLS 정책

```sql
-- blog_categories
ALTER TABLE blog_categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blog_categories_select" ON blog_categories
FOR SELECT USING (
  is_visible = true
  OR EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

CREATE POLICY "blog_categories_admin_insert" ON blog_categories
FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

CREATE POLICY "blog_categories_admin_update" ON blog_categories
FOR UPDATE USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

CREATE POLICY "blog_categories_admin_delete" ON blog_categories
FOR DELETE USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

-- category_groups
ALTER TABLE category_groups ENABLE ROW LEVEL SECURITY;

CREATE POLICY "category_groups_select" ON category_groups
FOR SELECT USING (true);

CREATE POLICY "category_groups_admin_all" ON category_groups
FOR ALL USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

-- category_subscriptions
ALTER TABLE category_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "category_subscriptions_own" ON category_subscriptions
FOR ALL USING (auth.uid() = user_id);

-- pinned_posts
ALTER TABLE pinned_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pinned_posts_select" ON pinned_posts
FOR SELECT USING (true);

CREATE POLICY "pinned_posts_admin_all" ON pinned_posts
FOR ALL USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);
```

---

## 2. Category Page (Public)

### 2.1 URL

```
/{locale}/blog/category/{slug}/
```

Astro 파일 (기존 locale별 분리 패턴 유지):
- `src/pages/ko/blog/category/[slug].astro`
- `src/pages/en/blog/category/[slug].astro`

두 파일 모두 `prerender = false` (SSR).

### 2.2 Layout

기존 `BlogShell` 재활용 (사이드바 + 메인). 메인 영역 구성:

1. **카테고리 헤더** -- 아이콘, 라벨, 설명, 글 수. `banner_url` 있으면 배너 표시
2. **고정 글 영역** -- `pinned_posts` 데이터가 있을 때만 렌더링 (현재는 빈 상태로 숨겨짐)
3. **글 목록** -- 기존 `BlogListItem` 재활용, 카테고리 배지 생략 (이미 해당 카테고리 안)
4. **무한 스크롤** -- 기존 sentinel 기반 방식 동일, 10개 단위

### 2.3 Empty / Error States

- **카테고리 없음** (slug 불일치): 404 반환
- **비공개 카테고리** (is_visible=false, 비-admin 접근): 404 반환
- **글이 0개인 카테고리**: 카테고리 헤더는 표시, 글 목록 영역에 "아직 작성된 글이 없습니다" 안내

### 2.4 Data Flow

```
[slug].astro (SSR)
  1. blog_categories에서 slug로 카테고리 조회 (없으면 404)
  2. 비공개(is_visible=false)이고 admin이 아니면 404
  3. 병렬 fetch:
     a. 해당 카테고리 published posts (created_at DESC, 배치 분할)
     b. pinned_posts (현재는 빈 결과)
     c. 유저 북마크/읽기 상태 (인증된 경우)
  4. BlogShell + 카테고리 헤더 + 글 목록 렌더링
```

### 2.5 SEO

- `<title>`: `{카테고리 라벨} | {사이트명}`
- `<meta description>`: 카테고리 설명 사용
- Canonical: `/{locale}/blog/category/{slug}/`
- hreflang: ko/en 쌍

### 2.6 새 컴포넌트

- `BlogCategoryHeader.astro` -- 카테고리 헤더 (아이콘, 라벨, 설명, 글 수, 배너)

기존 컴포넌트 재활용:
- `BlogShell.astro`
- `BlogListItem.astro`
- `BlogSidebar.astro` (수정 필요)

---

## 3. Sidebar Changes

### 3.1 클릭 동작 분리

현재: 카테고리명 클릭 -> 폴더 펼침/접힘

변경 후:
- **화살표(>) 클릭** -> 폴더 펼침/접힘 (기존 동작)
- **카테고리명 클릭** -> `/{locale}/blog/category/{slug}/`로 이동 (링크)

### 3.2 Active 상태

카테고리 페이지에 있을 때 해당 카테고리에 active 스타일 강조 (배경색, 폰트 굵기 등).

### 3.3 데이터 소스 변경

`BLOG_CATEGORIES` 하드코딩 -> DB에서 조회한 카테고리 목록 사용.
카테고리 데이터는 페이지 레벨에서 fetch 후 prop으로 전달.

---

## 4. Admin Category Management

### 4.1 URL

```
/admin/blog/categories/
```

### 4.2 목록 화면

- 그룹별로 카테고리 표시 (그룹 라벨 + 소속 카테고리)
- 각 카테고리: 드래그 핸들, 아이콘, 라벨, 슬러그, 글 수, [편집] 버튼
- 그룹 내 드래그로 순서 변경, 그룹 간 드래그로 이동 가능
- 상단 [+ 새 카테고리] 버튼
- 하단 [+ 새 그룹 추가] 버튼
- 각 그룹 헤더에 [그룹 편집] 버튼

### 4.3 카테고리 편집 (슬라이드 패널 또는 모달)

편집 가능 필드:
- 슬러그 (slug) -- 변경 시 "이 카테고리에 N개 글의 category 필드가 함께 변경됩니다" 경고 표시
- 라벨 KO/EN (label_ko, label_en)
- 설명 KO/EN (description_ko, description_en)
- 색상 (color) -- 컬러 피커
- 아이콘 (icon) -- 아이콘 선택 UI
- 그룹 (group_slug) -- 드롭다운
- 공개여부 (is_visible) -- 토글
- 쓰기 권한 (write_mode) -- 드롭다운 (admin_only / members / approved_only)
- 배너 이미지 (banner_url) -- 파일 업로드
- 가이드라인 (guidelines) -- 텍스트 에디터

### 4.4 삭제 정책

- 카테고리에 글이 있으면 삭제 불가 (DB FK `ON DELETE RESTRICT`로 이중 보호)
- "이 카테고리에 N개 글이 있습니다. 글을 다른 카테고리로 이동한 후 삭제해주세요." 안내
- 글이 0개일 때만 삭제 허용 (위험 영역에 배치)

### 4.5 그룹 편집

- 그룹명 KO/EN 변경 (인라인 편집)
- 그룹 삭제: 소속 카테고리 0개일 때만 허용

### 4.6 API Endpoints

기존 프로젝트의 action-based 엔드포인트 패턴을 따른다 (파일명 = 액션, POST body에 데이터 포함).

```
POST /api/admin/blog/categories/list.ts        -> 전체 카테고리 + 그룹 목록 (글 수 포함)
POST /api/admin/blog/categories/save.ts        -> 카테고리 생성 또는 수정 (body에 id 유무로 구분)
POST /api/admin/blog/categories/delete.ts      -> 카테고리 삭제 (body: { id })
POST /api/admin/blog/categories/reorder.ts     -> 순서 일괄 업데이트 (body: [{ id, sort_order, group_slug }])

POST /api/admin/blog/category-groups/list.ts   -> 그룹 목록
POST /api/admin/blog/category-groups/save.ts   -> 그룹 생성 또는 수정
POST /api/admin/blog/category-groups/delete.ts -> 그룹 삭제 (body: { slug })
```

모든 엔드포인트: `accessToken` + `isAdmin` 체크 필수.

---

## 5. Migration Strategy

### 5.1 순서

1. `moddatetime` extension 활성화
2. `category_groups` 테이블 생성 + seed + RLS + trigger
3. `blog_categories` 테이블 생성 + seed (기존 5개, 아이콘 SVG 포함) + RLS + trigger
4. `blog_posts.category` 기존 CHECK 제약조건(`blog_posts_category_check`) 제거
5. `blog_posts.category` FK 연결 (`ON UPDATE CASCADE ON DELETE RESTRICT`)
6. `category_subscriptions`, `pinned_posts` 테이블 생성 (빈 상태) + RLS

### 5.2 Frontend 코드 전환

1. `lib/pageData/blogCategories.ts` 신규 -- DB fetch 함수
2. `lib/categories.ts` 리팩터링 -- 하드코딩 제거, DB 데이터 기반 유틸 함수로 전환
3. `BlogSidebar.astro` -- DB 카테고리 사용 + 클릭 동작 분리 (화살표=펼침, 이름=링크)
4. `BlogFeaturedCard.astro`, `BlogListItem.astro` -- DB 카테고리 데이터 사용
5. `BlogBreadcrumb.astro` -- 카테고리 링크를 `/{locale}/blog/category/{slug}/`로 변경 (기존: query param 기반)
6. `ko/blog/index.astro`, `en/blog/index.astro` -- 카테고리 데이터를 DB에서 fetch 후 하위 컴포넌트에 전달
7. `ko/blog/category/[slug].astro`, `en/blog/category/[slug].astro` 신규 -- 카테고리 페이지
8. `BlogCategoryHeader.astro` 신규 -- 카테고리 헤더 컴포넌트
9. Admin 카테고리 관리 페이지 + API 엔드포인트 신규

### 5.3 하위 호환

- `normalizeCategorySlug()` (`tech` -> `study`) 유지 -- 레거시 데이터 보호
- 기존 블로그 URL (`/{locale}/blog/{slug}/`) 변경 없음
- 카테고리 페이지는 새 URL (`/{locale}/blog/category/{slug}/`)이므로 충돌 없음
- CSS 변수 (`--color-cat-*`)는 DB의 hex 값으로 대체. 기존 테마별 색상은 inline style로 전환

---

## 6. Community Transition Path

현재 설계가 커뮤니티 전환을 지원하는 방식:

| 커뮤니티 기능 | 현재 상태 | 전환 시 필요 작업 |
|-------------|----------|----------------|
| 카테고리 = 게시판 | `write_mode` 컬럼 존재 | `members`/`approved_only`로 변경만 |
| 유저 글쓰기 | 미구현 | 글쓰기 폼 + `write_mode` 체크 로직 |
| 구독 | 테이블 존재 (빈 상태) | 구독 UI + API 추가 |
| 고정 글 | 테이블 존재 (빈 상태) | Admin에서 핀 설정 UI 추가 |
| 게시판 설명/배너 | 컬럼 존재 (nullable) | Admin에서 입력, 카테고리 페이지에서 표시 |
| 글쓰기 가이드라인 | 컬럼 존재 (nullable) | 글쓰기 폼 상단에 표시 |
| 블로그/커뮤니티 URL 분리 | 미구현 | `write_mode` 기반 라우팅 분기 추가 |
| 역할 시스템 | 미구현 | 별도 설계 필요 |
| 모더레이션 | 미구현 | 별도 설계 필요 |

스키마 마이그레이션 없이 프론트엔드 기능 추가만으로 전환 가능.
