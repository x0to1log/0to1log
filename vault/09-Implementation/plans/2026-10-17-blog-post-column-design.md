# 블로그 글 상세 재설계 (A 칼럼 한 편) — Design Spec

**Status:** implemented (2026-10-17) — [[2026-10-17-blog-post-column]]
**Mockup:** `.superpowers/brainstorm/blogpost/post-v1.html` (A안)
**관련:** [[2026-10-17-blog-list-serial-design]], [[2026-10-16-news-article-briefing-design]], [[2026-10-17-handbook-term-entry-design]]

## 배경

- 글 상세(`/ko/blog/{slug}/`, `/en/blog/{slug}/`)는 세 칸이다: 왼쪽 폴더 트리, 가운데 본문, 오른쪽 레일(액션 + 목차). 본문이 좁다.
- 목록은 분야를 연재로, 발행 순서를 회차로 보여주지만([[2026-10-17-blog-list-serial-design]]) 상세에는 이 글이 몇 화인지 어디에도 없다.
- 끝의 "다음 글"은 `published_at`이 **더 이른** 글 중 가장 최근 글이다. 그래서 학습 노트 2화에서 1화로 거꾸로 간다.
- 시안 A(칼럼 한 편) / B(여백 주석) / C(연재 표지) 중 **A**를 골랐다(2026-10-17).

## 화면 구성 (가운데 한 단)

`BlogShell`에 `sidebar={false}`를 준다(목록과 같은 한 단, 사이드바·서랍 없음). `toc` 슬롯과 `showTOC`는 쓰지 않는다.

1. **경로 줄** `nav.blog-post-crumb`(aria-label "글 위치" / "Post location")
   - "← IT 블로그" 링크(`/{locale}/blog/`) · 분야 이름 · 연재 글이면 "{n}화" / "Ep. {n}"
   - 분야 이름: 정규화한 slug가 DB 분야에 있고 `is_visible`이면 분야 페이지 링크(`/{locale}/blog/category/{slug}/`), 숨김 분야면 링크 없는 라벨, DB에 없으면 생략한다.
   - 현행 `BlogBreadcrumb`(제목까지 나열)를 대신한다.
2. **제목** `h1.blog-article-title`(현행 클래스 유지, Hahmlet 700 약 2.5rem)
3. **요약** `p.blog-post-dek`: `excerpt`, 없으면 생략
4. **바이라인** `div.blog-post-byline`: 위 2px 먹선, 아래 1px 먹선, 양 끝 정렬
   - 왼쪽: "**Amy** · {날짜}" + 읽기 시간이 있으면 " · 약 {n}분" / " · {n} min read"
     - 날짜는 **연도 포함** KST: "2026년 3월 11일" / "Mar 11, 2026". `formatBlogDate(value, locale, { year: true })`로 옵션을 추가한다(목록은 기존 호출 그대로). 날짜가 없으면 날짜 칸을 생략한다.
   - 오른쪽(연재 글만): 분야 점 라벨(`--cat-color`) "{분야} · {N}편 중 {n}화" / "{Field} · Ep. {n} of {N}"
     - N = `series.posts.length`, n = `index + 1`.
   - 현행 `.blog-article-meta`(달력 아이콘 줄)를 없앤다.
5. **이 글의 차례** `details.blog-post-toc`
   - 요약 줄 `summary`: "이 글의 차례 ({k})" / "In this post ({k})"
   - 내용: `ol`, 본문 `.newsprint-prose` 안의 `h2`를 문서 순서대로 나열한다(`h3` 제외). 링크 텍스트는 `textContent`(용어 span 무시).
   - 서버 마크업은 비어 있는 `details`(`hidden`)이고, 스크립트가 채운다. `h2`가 **2개 미만**이면 계속 숨긴다.
   - 제목 id: 기존 `BlogTOC` 규칙을 옮긴다. 기존 id → 영문 slug → `section-{n}`, 중복은 `-{k}` 접미사. (한글 제목은 대부분 `section-{n}`이 된다.)
   - 클릭: 기존 `BlogTOC`의 헤더 오프셋 계산(`--blog-shell-header-offset`)으로 부드럽게 스크롤한다.
   - 열림 상태: 페이지 로드마다 `matchMedia('(min-width: 1024px)')`이면 `open`을 켠다(CSS로는 못 정함). 1024px 이상은 목록 2단(`columns: 2`), 미만은 접힌 채 1단.
   - 스크롤 위치 강조(현행 IntersectionObserver)는 없앤다.
   - 스크립트는 번들 한 번, `astro:page-load`마다 실행. `details.blog-post-toc`가 없으면 아무것도 하지 않고, 있으면 목록을 비운 뒤 다시 만든다(중복 방지).
6. **본문 + 액션**: `BlogArticleLayout`의 기존 인라인 경로 `showStickyActions`(기본 true)를 켠다. 뉴스·용어 상세와 **같은 공용 CSS를 그대로** 쓴다.
   - `.reading-actions-layout--article` 안 첫 자식이 `StickyReadingActions`(variant="blog")다.
   - **1024px 이상: 본문 오른쪽 72px 세로 막대**(공용 CSS `grid-template-columns: minmax(0, 1fr) 72px`, 액션 `order: 2`). 1024px 미만: 하단 바. 시안의 "왼쪽" 대신 다른 상세 페이지와 같은 오른쪽으로 맞춘다(블로그 전용 재정의 없음).
   - 저장·좋아요·댓글 수·공유 동작과 data 속성은 그대로다. `[data-item-id][data-item-type="blog"]` 버튼은 페이지에 **하나**만 있어야 한다(레일을 없애므로 중복 없음).
   - 용어 팝업(`handbook-terms-data`, `handbook-popup`), 코드 복사, 진행 바, 페르소나 스위처는 그대로다.
7. **끝 블록**(본문 몸통 안, 순서대로)
   1. 태그 `.blog-tags-footer`(현행)
   2. 관리자 액션(현행)
   3. "도움이 됐나요?" `ContentFeedback`(현행)
   4. `data-reading-end`(현행 위치 유지: 피드백 다음)
   5. **이전·다음** `nav.blog-post-pager`(aria-label "이전·다음 글" / "Previous and next posts"), 2칸 카드
      - 연재 글: 같은 연재의 바로 앞·뒤 회차. 라벨 "← {n-1}화" / "{n+1}화 →" ("← Ep. {n-1}" / "Ep. {n+1} →")
      - 연재가 아닌 글: 전체 글(연재 회차 포함)의 `published_at` 순서로 앞·뒤. 더 이른 글이 이전. 라벨 "← 이전 글" / "다음 글 →" ("← Previous" / "Next →")
      - 한쪽이 없으면 그 칸은 비워 둔다(다음 카드는 오른쪽 칸에 머문다). 둘 다 없으면 렌더하지 않는다.
      - 각 카드: 라벨 + 제목(Hahmlet 600)
   6. **연재 목록** `aside.blog-post-series`(연재 글만, aria-labelledby로 머리 연결)
      - 머리: 위 2px 먹선 + 분야 이름(`p.blog-post-series-title`, 제목 태그 아님) + 오른쪽 "연재 {N}편 · 전체 보기 →" / "{N} posts · View all →"(분야 페이지 링크, 숨김 분야면 링크 생략)
      - `ol`: 회차 번호 + 제목 링크. 지금 글은 링크 대신 `aria-current="page"` 텍스트이고 accent 회차 번호 + " · 지금 읽는 글" / " · Reading now"
   7. 댓글 `#comments`(현행). 제목을 `h3` → **`h2`**로 올린다(클래스 `newsprint-comments-title` 유지). 블로그 레이아웃 안에서만 바꾼다.
   - 현행 `nav.newsprint-article-nav`("목록으로" + "다음 글")와 떠 있는 `persona-float--back` 버튼은 블로그 레이아웃에서 없앤다.

## 레이아웃 props

`BlogArticleLayout`:
- 추가: `serial` — 페이지가 계산해서 넘기는 객체
  ```ts
  serial: {
    categoryLabel: string | null; categoryHref: string | null; categoryColor: string | null;
    episode: number | null;        // n (연재 글만)
    total: number | null;          // N (연재 글만)
    episodes: { title: string; slug: string }[]; // 연재 글만, 오래된 순
    prev: { title: string; slug: string } | null;
    next: { title: string; slug: string } | null;
  }
  ```
- 제거: `backLabel`, `nextPost`, `categories`(분야 라벨·색은 `serial`로 받음). `basePath`는 공유 URL에 쓰므로 유지.
- en 페이지의 쓰이지 않는 `masthead` / `editionLabel` 값도 정리한다.

## 연재 위치 계산 (순수 함수)

`lib/blogSerial.js`에 추가한다.

```js
/**
 * @returns {{ series: {category, posts} | null, index: number, prev: object|null, next: object|null }}
 */
export function locatePost(posts, categories, slug)
```

- `buildBlogFront(posts, categories)`를 그대로 써서 연재를 만든다(분야 정규화 `tech → study` 포함).
- 글이 어느 연재에 있으면: `series`, `index`(0부터), 같은 연재 안의 `prev`/`next`.
- 연재에 없으면: `series = null`, `index = -1`. `prev`/`next`는 날짜 있는 **전체 글**(연재 회차 포함)을 오래된 순으로 정렬한 목록에서의 앞·뒤다. 현재 글에 날짜가 없으면 둘 다 null.
- `slug`가 목록에 없으면(예: 미리보기 초안): `{ series: null, index: -1, prev: null, next: null }`.
- `serial` props는 ko/en 페이지에서 중복 계산하지 않도록 같은 파일의 `toSerialProps(located, categories, locale)`가 만든다(분야 라벨·링크·색, 회차, 회차 목록, prev/next를 `{title, slug}`로). 숨김 분야면 `categoryHref = null`, DB에 없는 분야면 `categoryLabel = null`. `locatePost`와 함께 단위 테스트한다.
- `buildBlogFront` JSDoc의 `id` 필수 표기를 선택(`id?`)으로 고친다(읽지 않는 필드).

## 데이터

- 글 목록 쿼리를 **목록 페이지와 같은 모양**으로 맞춘다: `blog_posts`에서 `status = 'published'`, 같은 locale, `order('created_at', desc)`, `limit(100)`, 열은 `title, slug, category, published_at`. 그래야 목록의 "2화"가 상세에서도 2화다(같은 100편, 같은 규칙).
- **"다음 글" 전용 쿼리(`nextRes`)를 없앤다.** `blogDetailPage.ts`의 `.from('blog_posts')`는 4개 → **3개**(본문, 목록, 번역 짝)가 된다. 순서 역전 버그도 사라진다.
- 분야는 페이지가 이미 부르는 `fetchCategories`(`select *`: `group_slug`, `is_visible`, `sort_order`, 라벨, `color` 포함)를 쓴다.
- `blogDetailPage.ts`의 반환값에서 `nextPost`, `sidebarPosts`를 없앤다. `recentPosts`를 페이지가 `locatePost`에 넘긴다. `buildBlogSidebarDataset`/`toSidebarPost` import도 상세에서는 없앤다(분야 페이지는 계속 사용).
- 미리보기 모드에서 현재 글이 목록에 없으면 연재 표시·이전·다음이 없다(의도된 동작).
- 공개 HTML은 계속 사용자 중립이다.

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| 경로 첫 칸 | ← IT 블로그 | ← IT Blog |
| 회차 | {n}화 | Ep. {n} |
| 바이라인 날짜 | 2026년 3월 11일 | Mar 11, 2026 |
| 바이라인 오른쪽 | {분야} · {N}편 중 {n}화 | {Field} · Ep. {n} of {N} |
| 읽기 시간 | 약 {n}분 | {n} min read |
| 차례 | 이 글의 차례 ({k}) | In this post ({k}) |
| 이전·다음 (연재) | ← {n}화 / {n}화 → | ← Ep. {n} / Ep. {n} → |
| 이전·다음 (그 외) | ← 이전 글 / 다음 글 → | ← Previous / Next → |
| 연재 머리 오른쪽 | 연재 {N}편 · 전체 보기 → | {N} posts · View all → |
| 지금 글 | · 지금 읽는 글 | · Reading now |

## 모바일·태블릿

- ≤767px: 좌우 16px 여백, 제목 약 1.8rem, 바이라인 두 줄 허용(오른쪽 칸이 아래로), 이전·다음 1단.
- <1024px: 차례 접힘·1단, 액션 하단 바(공용 CSS).
- 가로 넘침 0.

## 없애는 것

- 상세 페이지의 `ReadingActionsRail` 사용, `toc` 슬롯, `.blog-mobile-toolbar` 마크업(사이드바 토글). `.blog-mobile-toolbar` **CSS는 남긴다**(분야 페이지 사용).
- 파일 삭제: `components/blog/BlogTOC.astro`, `components/blog/BlogBreadcrumb.astro`, `components/common/ReadingActionsRail.astro` (모두 블로그 상세 전용임을 리뷰에서 확인, 구현 시 grep 재확인).
- 레일 배치 코드 삭제: `StickyReadingActions`의 `placement="rail"` 분기와 `.reading-actions--rail-placement*`, `.blog-rail .reading-actions--rail-placement` CSS — `ReadingActionsRail`만 썼다. 구현 시 grep으로 다른 사용처가 없음을 확인하고, 있으면 남긴다.
- CSS 삭제: `.blog-toc*`, `.blog-rail*`, `.blog-breadcrumb*`, `.blog-article-meta`, `.blog-article-category`, `.reading-actions-rail*`, `.newsprint-article-nav*`, `.newsprint-nav-*`(`.blog-shell .newsprint-nav-next-title` 포함 — 블로그 레이아웃만 썼다).
- 남기는 것: `.persona-float*`(뉴스·용어 레이아웃과 `handbook-popup.ts` 사용).
- i18n `blog.onThisPage`: 다른 사용처가 없으면 삭제한다.

## 테스트

- `tests/blog-serial.test.mjs`에 추가: `locatePost`
  - 연재 2화 → series, index 1, prev 1화, next 3화
  - 첫 화 prev null, 마지막 화 next null
  - 짧은 글 → series null, 전체 글 날짜순 앞·뒤(연재 회차 포함)
  - 목록에 없는 slug → 모두 null, 날짜 없는 짧은 글 → prev/next null
  - `tech` 분야 글이 `study` 연재에 들어감
  - `formatBlogDate(..., { year: true })` KST 연도 포함, 옵션 없으면 기존 출력 그대로
- 새 구조 테스트 `tests/blog-post-column.test.cjs`
  - ko/en 페이지: `sidebar={false}`, `ReadingActionsRail`·`slot="toc"`·`blog-mobile-toolbar` 없음, `locatePost` 사용, `serial=` 전달
  - 레이아웃: 경로 줄, 바이라인, `details.blog-post-toc` + `hidden`, `StickyReadingActions`가 `.reading-actions-layout--article`의 첫 자식(`placement` 없음), 끝 블록 순서(태그 → 피드백 → reading-end → pager → series → comments), 댓글 `h2`, `newsprint-article-nav`·`persona-float--back` 없음
  - 데이터: `.lt('published_at'` 없음, `.from('blog_posts')` 정확히 3개, 목록 쿼리 `limit(100)` + `created_at` 정렬
  - 삭제 파일 부재, 삭제 CSS 부재
- 기존 테스트 갱신(구현 계획에서 각 단언을 새 기준으로 바꾸거나 지움):
  - `detail-rail-actions-placement.test.cjs`(30-46: `showStickyActions={false}`, `<ReadingActionsRail`, `.blog-rail` CSS)
  - `blog-list-serial.test.cjs`(15-17: 상세에 `sidebar={false}` 없음 단언 → 반대로)
  - `blog-sidebar-layout.test.cjs`(60: `.blog-toc`, 87-88: 상세의 `blog-mobile-toolbar` 필수 → 분야 페이지만)
  - `blog-detail-sidebar-structure.test.cjs`(23: `'./blogSidebar'` import)
  - `blog-toc-structure.test.cjs`(삭제 또는 새 차례 스크립트 기준)
  - `blog-v2.test.cjs`(53, 56-63: 메타·카테고리·toc)
  - `reading-actions-editorial-subtle.test.cjs`, `reading-actions-layout-regression.test.cjs`(36-46: 레일 배치)
  - `sticky-reading-actions-structure.test.cjs`(31-33: `placementClass`)
  - `detail-rail-actions-placement.test.cjs`의 27(`placement?:`), 48(`.reading-actions--rail-placement {`)도 함께
- 전체 스위트: 실패 목록을 기준선과 이름으로 비교, 신규 FAIL 0. `npm run build` 성공.
- 브라우저
  - 3테마 × 1100px·375px × ko/en, 가로 넘침 0, 대비 미달 0 (+ 900px에서 하단 바·접힌 차례 확인)
  - 대상: 학습 노트 2화(rag-ai-retrieval-augmented-generation), 1화(이전 없음), 5화(다음 없음), 짧은 글(importance-of-flow-over-features)
  - 클릭: 차례 이동, 저장, 공유 메뉴, 용어 팝업, 이전·다음, 연재 목록 링크, 댓글 영역
  - 회귀: 분야 페이지 사이드바 유지, 목록 페이지 정상, 뉴스·용어 상세의 액션 막대 변화 없음

## 범위 밖 (기록만)

- 일부 글은 마크다운 본문에 `# 제목`이 있어 본문 안에 `h1`이 하나 더 생긴다(예: RAG 글 "검색하는 AI는 어떻게 작동할까"). 콘텐츠 문제라 이번에는 건드리지 않는다.
- `reading_time_min`이 비어 있는 글이 있다(바이라인에서 생략).
- 글이 100편을 넘는 경우(목록과 같은 한계).
- 분야 페이지 재설계.
