# 블로그 분야 페이지 재설계 (A 연재 목차) — Design Spec

**Status:** approved (2026-10-18)
**Mockup:** `.superpowers/brainstorm/blog2/category-v1.html` (A안)
**관련:** [[2026-10-17-blog-list-serial-design]], [[2026-10-17-blog-post-column-design]]

## 배경

- 분야 페이지(`/ko/blog/category/{slug}/`, `/en/blog/category/{slug}/`)는 왼쪽 폴더 트리(`BlogSidebar`) + 제목만 있는 목록(`BlogListItem`)이다. 공개 페이지 중 마지막으로 사이드바가 남은 곳이다.
- 해당 분야 글만 `eq('category', slug)` + `created_at` 내림차순으로 가져온다 → 학습 노트에서 3화가 맨 위, 1화가 맨 아래. 예전 분야 이름 `tech` 글은 나오지 않는다(목록·상세는 `tech → study` 정규화).
- 10개씩 끊어 보여주는 무한 스크롤이 있다(글은 분야당 최대 5편).
- 쿼리: 페이지 4개(분야 단건·글·분야 목록·그룹) + `BlogSidebar` 자체의 `fetchCategories`·`fetchCategoryGroups` → 약 6개.
- 이 경로는 공유 캐시 구역이라(`middleware.ts`, `publicCachePolicy.ts`) 인증을 건너뛴다 → `Astro.locals.isAdmin`이 항상 비어 있고, 현행 "숨김 분야는 관리자만" 분기는 실제로 항상 404다.
- 데이터(2026-10-18 운영): 분야 5개 — study(main, 5편), project(main, 5편), career(main, 0편), work-note(sub, 1편), daily(sub, 0편). **분야 설명은 전부 비어 있다.** EN 글 0편.
- 시안 A(연재 목차) / B(회차 카드) / C(기록 타임라인) 중 **A**를 골랐다(2026-10-18).

## 화면 구성 (가운데 한 단, 현행 `.blog-shell--single` 폭 820px)

모바일 메뉴 버튼(`.blog-mobile-toolbar`) 마크업을 없앤다.

1. **경로 줄** `nav.blog-cat-crumb`(aria-label "분야 위치" / "Field location"): "← IT 블로그" / "← IT Blog"(`/{locale}/blog/`) · 종류 "연재" / "Series"(kind series) 또는 "짧은 글" / "Short notes"(kind notes).
2. **h1** `h1.blog-cat-title`: 분야 라벨(`label_ko/en`, Hahmlet 700 약 2.5rem). 설명(`description_{locale}`)이 있으면 아래 `p.blog-cat-desc`, 없으면 생략.
3. **바이라인** `div.blog-cat-byline`: 위 2px 먹선, 아래 1px 먹선, 양 끝 정렬(글 1편 이상일 때만)
   - series: 왼쪽 분야 점 라벨(`--cat-color`) "연재 {N}편" / "{N}-part series" + " · {기간}". 오른쪽 링크 "1화부터 읽기 →" / "Start from Ep. 1 →"(1화 글 상세).
   - notes: 왼쪽 "짧은 글 {N}편" / "{N} short notes" + " · 마지막 글 {날짜}" / " · Latest {date}". 버튼 없음.
   - 기간: 날짜 있는 글의 가장 이른 날 ~ 가장 늦은 날(`formatBlogDate`, KST). 같은 날이면 한 날짜. 날짜 있는 글이 없으면 생략.
4. **목록** `ol.blog-serial-list.blog-cat-list`(목록 페이지의 줄 격자 CSS `.blog-serial-list .blog-list-item`을 그대로 받기 위해 `blog-serial-list` 클래스 필수). series면 `blog-cat-list--series`를 더한다.
   - 줄은 `BlogSerialItem`(`li.blog-list-item` + 줄 안의 저장 버튼 — `content-status.ts`가 가까운 `.blog-list-item`에 읽음 표시).
   - series: 오래된 순, `episode` = index + 1. 1화 강조는 CSS `.blog-cat-list--series > .blog-list-item:first-child .blog-serial-ep { color: var(--color-accent) }`.
   - notes: 최신순, 회차 없음, 분야 배지 생략(`categoryLabel` 안 넘김).
   - `BlogSerialItem`에 선택 prop `excerpt` 추가: 있으면 `<a class="blog-serial-title" ...>{post.title}</a>`(문자열 그대로 유지) 뒤에 `p.blog-serial-excerpt`를 렌더한다. CSS로 `grid-column: 2; grid-row: 2`(두 줄 clamp)를 줘서 4열 격자를 깨지 않는다. 목록 페이지는 넘기지 않으므로 변화 없음.
5. **다른 분야** `nav.blog-cat-others`(aria-label "다른 분야" / "Other fields"): 위 2px 먹선, "다른 분야" 라벨 + 지금 분야를 뺀 **보이는 분야**를 `sort_order` 순으로 "{라벨} {개수}" 링크. 0편 분야도 나열(개수 0). 개수는 불러온 100편 기준.
6. **0편 분야**: 바이라인·목록 대신 기존 빈 안내(`.blog-empty-state`, 현행 문구·`.blog-empty-icon`) + 다른 분야 줄.
7. **글 조회 실패**: 목록 페이지(`blog/index.astro`)와 같이 `Astro.response.status = 503` + `NewsprintNotice`(error). 빈 안내로 200을 내보내 캐시되지 않게 한다.

## 접근 규칙

- slug 없음 / DB 없음 → `/{locale}/blog/` 리다이렉트(현행).
- 분야 없음 → 404(현행). (`fetchCategoryBySlug`가 조회 오류도 null로 돌려 404가 되는 점은 현행 한계로 기록.)
- **숨김 분야(`is_visible = false`) → 항상 404.** 관리자 분기(`Astro.locals.isAdmin`)를 없앤다(이 경로에서는 항상 비어 있어 의미 없음).

## 데이터

- 글 쿼리를 목록·상세와 **같은 모양**으로: `blog_posts`에서 `id, title, slug, category, published_at, excerpt`, `status = 'published'`, 같은 locale, `order('created_at', desc)`, `limit(100)`.
- 분야: `fetchCategoryBySlug`(현행) + `fetchCategories`(현행). 페이지의 `fetchCategoryGroups` 호출은 제거한다(함수는 관리자 화면이 쓰므로 `blogCategories.ts`에 남김). 사이드바가 빠지므로 쿼리는 약 6개 → 3개.
- 순수 함수 `categoryPage(posts, categories, slug)`를 `lib/blogSerial.js`에 추가:
  - `category` = categories에서 slug 일치(호출 전에 페이지가 존재·보임을 확인).
  - `kind` = `category.group_slug === 'main' ? 'series' : 'notes'` (보이는 분야만 여기 오므로 hidden 경우 없음. main 외 그룹·null은 notes).
  - series: `buildBlogFront(posts, categories).series`에서 이 분야 항목의 `posts`(오래된 순), 없으면 `[]`.
  - notes: 정규화 분야(`normalizeBlogCategory`)가 slug인 글, 최신순(날짜 없는 글은 뒤).
  - `range`: 그 글들 중 날짜 있는 글의 `{ first, last }`(`published_at` 문자열), 없으면 null.
  - `counts`: 정규화 분야별 글 수 맵(불러온 글 전체 기준).
  - 반환 `{ kind, posts, range, counts }`.
- 같은 100편·같은 규칙이라 목록·상세·분야 페이지의 회차가 일치하고, `tech` 글은 study 연재에 들어간다.
- 공개 HTML 사용자 중립 유지.

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| 경로 첫 칸 | ← IT 블로그 | ← IT Blog |
| 종류 | 연재 / 짧은 글 | Series / Short notes |
| 바이라인(연재) | 연재 {N}편 · {기간} | {N}-part series · {range} |
| 바이라인(짧은 글) | 짧은 글 {N}편 · 마지막 글 {날짜} | {N} short notes · Latest {date} |
| 시작 버튼 | 1화부터 읽기 → | Start from Ep. 1 → |
| 다른 분야 | 다른 분야 | Other fields |

## 모바일 (≤767px)

- 좌우 여백은 현행 `.blog-main-inner` 규칙을 그대로 쓴다(새 값 안 정함). h1 약 1.9rem, 바이라인 두 줄 허용(버튼 아래로), 다른 분야 줄바꿈, 요약 줄은 제목 아래. 가로 넘침 0.

## BlogShell 정리

- 호출처 6곳(ko/en `blog/index.astro`, `blog/[slug].astro`, `blog/category/[slug].astro`)이 모두 한 단이 되므로 **`sidebar` prop을 없애고 `blog-shell--single`을 항상** 붙인다. `BlogSidebar` import, 오버레이, `sidebarPosts`·`currentSlug`·`currentCategory`·`totalCount`·`mode`·`showTOC` prop, `toc` 슬롯을 제거하고 호출처에서 해당 속성을 지운다.

## 없애는 것

- 분야 페이지의 `BlogSidebar`·`.blog-mobile-toolbar`·`BlogCategoryHeader`·`BlogListItem` 사용, 무한 스크롤 스크립트(`data-blog-batch`, `data-blog-sentinel`). 같은 `<script>`의 `import '../../../../scripts/bookmark'`는 **유지**한다.
- 파일 삭제(다른 사용처 없음 확인 완료, 구현 시 재확인): `components/blog/BlogSidebar.astro`, `lib/pageData/blogSidebar.ts`, `components/blog/BlogCategoryHeader.astro`, `components/blog/BlogListItem.astro`.
- CSS 삭제(사용처 없음 확인 후): `.blog-sidebar*`, `.blog-sidebar-overlay`, `.blog-folder*`, `.blog-mobile-toolbar`, `.blog-mobile-toggle`, `.blog-category-header*`, `.blog-category-banner`, `.blog-category-title*`, `.blog-category-icon`, `.blog-category-description`, `.blog-category-count`, `.blog-list-section`, `.blog-list-batch`, `.blog-scroll-sentinel`, `BlogListItem` 전용 규칙(`.blog-list-item-title` 등), 변수 `--blog-shell-rail-gap`·`--blog-shell-panel-radius`(다른 사용처 없을 때). ≤1023px 블록은 `.blog-shell { display: block }` 같은 공용 규칙을 남기고 사이드바 규칙만 골라 지운다.
- 남기는 것: `.blog-list-item`, `.blog-list-item:hover`, `.blog-list-item--read`(목록·`content-status`·테스트), `.blog-category-badge`, `.blog-empty-state`, `.blog-empty-icon`.
- i18n 삭제: `blog.allPostsCount`(ko/en, `BlogSidebar`만 사용).

## 테스트

- `tests/blog-serial.test.mjs`에 `categoryPage`: series(study 순서·tech 포함·회차), notes(최신순·날짜 없는 글 뒤), 빈 main(kind series, `[]`), sub 분야(notes), 알 수 없는/null 그룹(notes), range(같은 날 → first = last, 날짜 없음 → null), counts.
- 새 구조 테스트 `tests/blog-category-toc.test.cjs`: ko/en 페이지 — `BlogSidebar`·`BlogCategoryHeader`·`BlogListItem`·`blog-mobile-toolbar`·`data-blog-sentinel`·`isAdmin` 없음, `categoryPage` 사용, `limit(100)` + `created_at`, 503 + `NewsprintNotice`, 숨김 → 404, `scripts/bookmark` import, 경로 줄·h1·바이라인·`ol.blog-serial-list.blog-cat-list`·`BlogSerialItem`(excerpt 전달)·다른 분야·빈 안내. `BlogSerialItem`의 `excerpt` + `blog-serial-title` 문자열 유지. `BlogShell`에 `sidebar` prop 없음·`blog-shell--single` 고정·호출처에 `sidebar=` 없음. CSS: 새 규칙 존재(1화 강조, excerpt grid 위치), 삭제 대상 부재, 남기는 규칙 존재. 삭제 파일 부재. i18n `blog.allPostsCount` 없음.
- 기존 테스트 갱신·삭제 — 계획 단계에서 각 파일을 읽고 정확히 정한다:
  - 사이드바 전용: `blog-detail-sidebar-behavior.test.mjs`, `blog-detail-sidebar-structure.test.cjs`, `blog-mobile-sidebar-structure.test.cjs`, `blog-sidebar-categories.test.cjs`, `blog-sidebar-layout.test.cjs` → 대상이 모두 사라지면 파일 삭제, 남는 단언이 있으면 새 테스트로 옮김.
  - `blog-list-serial.test.cjs`(12-20·25 `sidebar={false}`·`class:list`, 129 유지 CSS 단언), `blog-post-column.test.cjs`(13 `sidebar={false}`, 135 유지 CSS 단언), `blog-v2.test.cjs`, `blog-bookmark-card-contract.test.cjs`, `blog-category-badge-font.test.cjs`, `blog-title-fonts.test.cjs`(22 `.blog-list-item-title`), `public-list-personalization.test.cjs`(읽기만 — 깨지지 않게 유지).
  - 그 밖에 분야 페이지·`BlogShell`·삭제 CSS 문자열을 읽는 테스트를 grep으로 모두 찾는다.
- 전체 스위트: 실패 목록을 기준선과 이름으로 비교, 신규 FAIL 0(삭제·추가·FAIL→PASS는 의도된 변화로 기록). `npm run build` 성공.
- 브라우저: 3테마 × 1100px·375px × ko/en, 가로 넘침 0, 대비 미달 0. 대상: study(연재 5편), work-note(짧은 글 1편), career(0편), en study(0편 빈 안내). 클릭: "1화부터 읽기" → 1화 글, 저장 버튼(줄당 1개), 다른 분야 링크, 경로 줄. 회차가 목록·글 상세와 일치하는지 대조. 회귀: 목록 페이지·글 상세(BlogShell 정리 영향 없음, 폭 동일).

## 범위 밖 (기록만)

- 분야 설명 데이터 입력(전부 비어 있음).
- 글 100편 초과(목록과 같은 한계), 개수도 100편 기준.
- 분야 조회 오류가 404로 캐시되는 현행 한계.
- 분야 배너·아이콘(데이터는 있으나 새 화면에서 쓰지 않음).
