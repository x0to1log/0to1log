# IT Blog 디자인 대공사 — Knowledge Base 스타일

## Context
IT Blog가 AI News와 동일한 NewsprintShell/카드를 공유하고 있어 개성이 없음. Knowledge Base 스타일 예시 2개(`frontend/examples/layout/example_blog_1.html`, `example_blog_2.html`)를 레퍼런스로 제공받음. newsprint 세리프 톤을 유지하면서 레이아웃과 인터랙션을 Knowledge Base 스타일로 전면 교체.

## Design Decisions (confirmed)
- **왼쪽 사이드바**: 카테고리 폴더 트리 (리스트 + 상세 모두 표시)
- **모바일 사이드바**: 햄버거 메뉴로 숨김 → 슬라이드 인
- **리스트 메인**: Pinned + Recent 하이브리드 (Featured 카드 + 시간순 리스트)
- **리스트 Right Rail**: 제거 → 사이드바가 탐색 역할 대체
- **상세 Right Rail**: TOC(Table of Contents)로 교체
- **상세 브레드크럼**: `Blog > Study > 글 제목`
- **태그**: JetBrains Mono 모노 폰트
- **섹션 헤더**: UPPERCASE + tracking-wider + 모노 폰트
- **코드 블록**: copy 버튼
- **hover**: arrow_outward 아이콘 등 인터랙션

## 왼쪽 사이드바 (BlogSidebar)

```
┌─────────────────────┐
│ [Search...     ⌘K]  │  ← 검색 트리거
├─────────────────────┤
│ ▼ 📂 Study          │  ← 펼침/접힘
│   ├─ React Hooks ●  │  ← 현재 글 하이라이트
│   ├─ Vector DBs     │
│   └─ RAG Basics     │
│                     │
│ ▶ 📂 Career         │  ← 접힌 상태
│ ▶ 📂 Project        │
├─────────────────────┤
│ All Posts (23)       │  ← 전체 글 바로가기
└─────────────────────┘
```

### 사이드바 동작
- 데스크톱: 항상 표시, 너비 ~260px, 왼쪽 고정
- 모바일: 숨김 → 햄버거(☰) 클릭 시 오버레이 슬라이드 인
- 카테고리 폴더: 클릭으로 펼치기/접기, 해당 카테고리 글 목록 표시
- 현재 보고 있는 글 하이라이트 (accent 배경)
- 상단 검색: 클릭 시 검색 모달 또는 글 필터링
- 하단: "All Posts" 링크로 전체 목록 이동

### 데이터
- Supabase에서 카테고리별 published 글 목록을 가져와 폴더 트리 구성
- 리스트/상세 페이지 모두 동일한 사이드바 데이터

## 리스트 페이지 구조

```
┌──────────────┬──────────────────────────────────┐
│ [Search ⌘K]  │          IT Blog                 │
│──────────────│     Builder's Notes              │
│ ▼ 📂 Study   │  Study · Career · Projects       │
│   ├─ Post 1  │──────────────────────────────────│
│   ├─ Post 2  │                                  │
│   └─ Post 3  │ FEATURED          (mono, upper)  │
│              │ ┌──────────┐ ┌──────────┐        │
│ ▶ 📂 Career  │ │ [Study]  │ │ [Career] │        │
│ ▶ 📂 Project │ │ Title    │ │ Title    │        │
│              │ │ Excerpt  │ │ Excerpt  │        │
│──────────────│ │ #react   │ │ #design  │        │
│ All (23)     │ └──────────┘ └──────────┘        │
│              │                                  │
│              │ ALL POSTS          (mono, upper)  │
│              │ ─────────────────────────         │
│              │ 📘 Post Title          Oct 24  ↗ │
│              │ ─────────────────────────         │
│              │ 📘 Post Title          Oct 22  ↗ │
│              │ ─────────────────────────         │
└──────────────┴──────────────────────────────────┘
(모바일: 사이드바 숨김, 메인만 풀 와이드 + ☰ 토글)
```

### 리스트 카드 (Featured)
- 2컬럼 그리드 (모바일 1컬럼)
- 카테고리 태그 [Study] — 카테고리 색상
- 제목 (세리프, bold)
- Excerpt 2줄 clamp
- 태그 (JetBrains Mono, 카테고리 accent 색상 배경)
- hover: 우상단 arrow_outward 아이콘 fade-in + 배경색 변화

### 리스트 아이템 (All Posts)
- 예시 1의 "Recently Edited" 패턴
- 아이콘 + 제목 + 날짜 + hover 시 제목 translate-x 애니메이션
- border-bottom 구분선
- 카테고리 태그 인라인 표시

## 상세 페이지 구조

```
┌──────────────┬────────────────────────────┬──────────────┐
│ [Search ⌘K]  │ Blog > Study > React Hooks │ ON THIS PAGE │
│──────────────│                            │──────────────│
│ ▼ 📂 Study   │ 📘                         │ Why Hooks?   │
│   ├─ Post 1  │ Understanding React Hooks  │ useState ●   │
│   ├─ Hooks ● │ Oct 24 · 5 min · Study     │   Rules      │
│   └─ Post 3  │                            │ useEffect    │
│              │ Content with drop-cap...   │              │
│ ▶ 📂 Career  │                            │              │
│ ▶ 📂 Project │ ## Why Hooks?              │              │
│              │ paragraph...               │              │
│──────────────│                            │              │
│ All (23)     │ ```code block  [Copy]```   │              │
│              │                            │              │
│              │ ─────────────────          │              │
│              │ #react #frontend           │              │
│              │ ♥ 12  💬 3  🔖             │              │
│              │ ─── Related Posts ───      │              │
│              │ [card] [card] [card]       │              │
└──────────────┴────────────────────────────┴──────────────┘
(모바일: 사이드바 숨김, TOC 숨김 → 메인 풀 와이드)
```

### 상세 헤더
- 브레드크럼: `Blog > [Category] > [Title]`
- 큰 아이콘 (📘 or 카테고리별 아이콘)
- 제목 (세리프, 큰 사이즈)
- 메타: 날짜 + 읽기 시간 + 카테고리 (mono)

### 우측 TOC (rail 교체)
- "ON THIS PAGE" 헤더 (mono, uppercase)
- 헤딩 기반 네비게이션
- 현재 위치 하이라이트 (accent 색상 border-left)
- h3는 들여쓰기
- sticky, 스크롤 추적 (IntersectionObserver)

### 코드 블록
- Copy 버튼 (hover 시 표시)
- 기존 newsprint-prose 코드 스타일 확장

### 글 하단
- 태그 (mono, 색상 배경)
- Engagement bar (좋아요, 댓글, 북마크)
- Related Posts 카드 (선택적)

## newsprint 톤 유지 요소
- **폰트**: Playfair Display (masthead, heading), Lora/Noto Serif KR (body) — 변경 없음
- **컬러**: 기존 warm palette (--color-bg-primary, --color-accent 등) — 변경 없음
- **카테고리 색상**: --color-cat-study/career/project — 재사용
- **masthead + kicker + subkicker**: 기존 newsprint 패턴 유지
- **구분선 스타일**: border-bottom, double border 등 유지

## 차별화 요소 (예시에서 차용)
- **모노 폰트 메타**: 태그, 날짜, 섹션 헤더에 JetBrains Mono
- **UPPERCASE 섹션 헤더**: `FEATURED`, `ALL POSTS`, `ON THIS PAGE`
- **hover 인터랙션**: arrow_outward 아이콘, translate-x, 배경색 전환
- **TOC rail**: 헤딩 기반 네비게이션 + 스크롤 추적
- **브레드크럼**: 상세 페이지 상단
- **코드 copy 버튼**: 기술 블로그 UX
- **Pinned/Featured 카드**: 2컬럼 그리드 카드 상단 배치
- **왼쪽 폴더 트리 사이드바**: 카테고리별 글 탐색

## Files to create/modify

### 새 컴포넌트
1. `frontend/src/components/blog/BlogSidebar.astro` — 카테고리 폴더 트리 사이드바
2. `frontend/src/components/blog/BlogShell.astro` — 블로그 전용 레이아웃
3. `frontend/src/components/blog/BlogFeaturedCard.astro` — Featured 카드
4. `frontend/src/components/blog/BlogListItem.astro` — 리스트 아이템
5. `frontend/src/components/blog/BlogTOC.astro` — Table of Contents
6. `frontend/src/components/blog/BlogBreadcrumb.astro` — 브레드크럼
7. `frontend/src/components/blog/BlogArticleLayout.astro` — 상세 페이지 레이아웃

### 수정
8. `frontend/src/pages/en/blog/index.astro` — 전면 교체
9. `frontend/src/pages/ko/blog/index.astro` — 동일
10. `frontend/src/pages/en/blog/[slug].astro` — 전면 교체
11. `frontend/src/pages/ko/blog/[slug].astro` — 동일
12. `frontend/src/styles/global.css` — `.blog-*` CSS 추가
13. `frontend/src/i18n/index.ts` — blog 번역 키 추가

### 기존 재사용
- `NewsprintCategoryFilter.astro` — 카테고리 필터 탭
- `categories.ts` — BLOG_CATEGORIES, getCategoryColorVar
- `bookmark.ts` — 북마크 스크립트
- `i18n/index.ts` — 기존 blog 번역 키

## Reference
- `frontend/examples/layout/example_blog_1.html` — Knowledge Base 리스트 페이지
- `frontend/examples/layout/example_blog_2.html` — Knowledge Base 상세 페이지
