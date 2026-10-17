# 블로그 목록 재설계 (A 연재 칼럼) — Design Spec

**Status:** implemented (2026-10-17) — [[2026-10-17-blog-list-serial]]
**Mockup:** `.superpowers/brainstorm/blog2/blog-v1.html` (A안)
**관련:** [[2026-10-15-site-redesign-phase7-blog]], [[2026-10-16-news-list-desks-design]]

## 배경

- 블로그 목록(`/ko/blog/`, `/en/blog/`)은 같은 글을 세 번 보여준다: 왼쪽 폴더 트리, 추천 4편, 모든 글.
- 발행 글은 11편(학습 노트 5, 프로젝트 기록 5, 작업 메모 1)이고, 같은 분야의 글이 사실상 연재다.
- 시안 A(연재 칼럼) / B(책 목차) / C(현행 정리) 중 **A**를 골랐다.
- 연재 이름은 **분야 이름 그대로**, 소개는 **분야 설명**, 회차는 **발행 순서**로 정했다(2026-10-17 결정 ①).
- 글 상세와 분야 페이지는 이번 범위가 아니다(사이드바 유지).

## 화면 구성 (목록 페이지, 가운데 한 단 최대 820px)

1. **마스트헤드**: `h1.blog-masthead-title`("–도록: do log"), `p.blog-masthead-tagline` 현행 유지
2. **필자 줄** `div.blog-byline`: 위 2px 먹선, 아래 1px 먹선
   - 왼쪽: "**Amy** · {N}편 · 마지막 글 {M월 D일}" / "**Amy** · {N} posts · Latest {Mon D}"
     - N은 발행 글 수(불러온 범위)다.
     - 날짜는 가장 최근 `published_at`(KST)이다.
   - 오른쪽: 글 검색 `input#blog-search`(placeholder "글 검색" / "Search posts")
3. **최신 글** `section.blog-lead`(2단 1fr : 200px)
   - 왼쪽
     - 분야 점 라벨(`--cat-color` = DB color, 7단계 B안 규칙) + " · 최신" / " · Latest"
     - 제목 `h2`(Hahmlet 700, 약 2rem, 링크)
     - 요약(`excerpt`, 없으면 생략)
     - 날짜
     - **북마크 버튼은 두지 않는다.** 같은 글이 연재 회차에도 있는데 `content-status.ts`가 같은 id의 첫 버튼에만 상태를 적용하기 때문이다. 북마크·읽음 표시는 연재 회차 줄에서만 한다.
     - 읽음 표시도 최신 글 블록에는 적용하지 않는다(의도된 동작).
   - 오른쪽(왼쪽 세로선)
     - 큰 숫자(연재 수) + "개의 연재" / "series"
     - 연재별 "{분야} {n}편" 줄
   - 글이 0편이면 섹션 대신 현행 빈 상태(`.blog-empty-state`)를 보인다.
4. **연재** `section.blog-series-grid`(데스크톱 2열, 모바일 1열)
   - 대상: `group_slug = 'main'`이고 `is_visible`이며 글이 1편 이상인 분야. 순서는 `sort_order`다.
   - 각 연재 `article.blog-series`
     - 머리: 위 2px 먹선 + 분야 이름 `h2`(Hahmlet 700, `/{locale}/blog/category/{slug}/` 링크) + 오른쪽 "{n}편" / "{n} posts"
     - 소개: `description_{ko|en}`(없으면 생략)
     - 회차 목록
       - 같은 분야 글을 `published_at` 오름차순으로 정렬한다. 1번부터 "{n}화" / "Ep. {n}"을 붙인다.
       - 목록은 `ol`이다. 각 줄은 새 마크업 `li.blog-list-item`이다(`BlogListItem` 컴포넌트는 `<article>`이라 재사용하지 않는다).
         - 내용: 회차 번호(Newsreader, muted) + 제목(Hahmlet 600, 링크) + 날짜 + 북마크 버튼
         - 북마크 버튼 `.newsprint-bookmark-icon[data-item-id][data-item-type="blog"][data-bookmarked="false"]`은 **반드시 그 `li` 안에** 있어야 한다. `content-status.ts`의 `applyReadState`가 가장 가까운 `.blog-list-item`을 찾아 `blog-list-item--read`를 붙이기 때문이다.
         - `.blog-list-item-icon` 슬롯 클래스는 쓰지 않는다.
       - 연재당 최대 표시 수는 정하지 않는다(현재 5편). 글이 많아지는 경우는 범위 밖이다.
5. **짧은 글** `section.blog-short-notes`
   - 대상: `group_slug = 'sub'`이고 `is_visible`인 분야의 글, 최신순이다.
   - 머리: `h2` "짧은 글" / "Short notes"
   - 목록은 `ol`이다. 각 줄 `li.blog-list-item`: 분야 점 라벨 + 제목 링크 + 날짜 + 북마크(같은 `li` 안 규칙)
   - 글이 0편이면 렌더하지 않는다.
6. **나머지 글**: 연재·짧은 글 본문 어디에도 속하지 않는 글은 짧은 글 **끝**에 같은 형식으로 최신순으로 붙인다.
   - 해당하는 경우: 정규화 후에도 분야 slug가 DB에 없음, 숨김(`is_visible = false`) 분야(그룹 무관), main·sub 외의 그룹
   - 글이 목록에서 사라지지 않게 하기 위해서다.
   - `group_slug`는 NOT NULL이라 "그룹 미지정" 경우는 없다.
   - 나머지 글이 있고 짧은 글 본문이 0이면 짧은 글 섹션은 나머지 글만으로 렌더한다.

## 없애는 것 (목록 페이지에서만)

- 왼쪽 사이드바(`BlogSidebar`)와 모바일 서랍 토글(`.blog-mobile-toolbar`, `[data-sidebar-toggle]`)
  - `BlogShell`에 `sidebar` prop(기본 `true`)을 추가하고, 목록은 `sidebar={false}`로 넘긴다. 분야·상세 페이지는 기본값 그대로라 변화가 없다.
- 분야 탭 줄 `nav.blog-category-tabs`(목록 페이지만. 분야 페이지에서 쓰면 유지)
- 추천 4편(`BlogFeaturedCard` 그리드)과 "모든 글" 배치·sentinel 무한 스크롤
- 사용처가 없어지는 컴포넌트·CSS는 grep으로 확인 후 정리한다. `BlogFeaturedCard`는 목록 전용이면 삭제한다. `BlogListItem`은 분야 페이지가 쓰므로 유지한다.

## 검색

- 새 인라인(또는 번들) 스크립트로 `#blog-search` 입력을 150ms 디바운스로 처리한다. 제목(대소문자 무시) 부분 일치다.
  - 일치하지 않는 `.blog-list-item`은 `hidden`으로 숨긴다(연재·짧은 글 모두).
  - 보이는 회차가 0인 `.blog-series`·`.blog-short-notes`는 숨긴다.
  - 검색어가 있으면 최신 글 섹션(`.blog-lead`)을 숨긴다. 결과 목록에 같은 글이 이미 있기 때문이다.
  - 전부 0이면 `#blog-search-empty`("일치하는 글이 없어요" / "No posts match", `role="status"` `aria-live="polite"`)를 보인다.
  - 검색어를 지우면 전부 원래대로 돌린다.
- 이중 바인딩 가드(`dataset.blogSearchReady`), `astro:page-load` 대응
- 번들 `<script>`를 쓰면 nonce 문제가 없다. `<script is:inline>`이면 nonce가 필수다.

## 데이터

- 기존 글 쿼리는 그대로다(`id, title, slug, category, published_at, tags, reading_time_min, excerpt`, published, locale, limit 100).
  - 회차·최신 계산은 `published_at` 기준이다. 쿼리 정렬(현행 `created_at desc`)은 바꾸지 않는다. 순수 함수가 다시 정렬한다.
- 분야: 기존 `fetchCategories`(group_slug, sort_order, is_visible, label, description, color 포함)
- 묶음 이름은 필요 없다. 연재·짧은 글은 `group_slug` 값만으로 나눈다.
- **새 순수 모듈 `lib/blogSerial.js`**: `buildBlogFront(posts, categories)` → `{ lead, series: [{ category, posts }], shortNotes, total, latestAt }`
  - 각 글의 분야는 먼저 `normalizeCategorySlug()`(`lib/categories.ts`, `tech` → `study`)로 정규화한다. 순수 모듈에서 import가 어려우면 같은 규칙을 함께 옮기고 테스트로 고정한다.
  - `lead`: `published_at` 최신 1편. 없으면 null.
  - `series`: main·visible·글 있음, `sort_order` 순. posts는 `published_at` 오름차순이다.
  - `shortNotes`: visible sub 분야 글(내림차순) 뒤에 나머지 글(내림차순)을 붙인 배열
- **날짜 표기는 페이지 전체가 `timeZone: 'Asia/Seoul'`이다**(필자 줄, 회차, 짧은 글, 최신 글).
  - 서버는 UTC로 돌기 때문에, 타임존 없이 `toLocaleDateString`을 쓰면 00–09시 KST 글의 날짜가 줄마다 달라진다.
  - `published_at`이 null인 글은 날짜가 없는 것으로 다룬다. 회차 정렬에서는 맨 뒤, 최신 판정에서는 제외한다.
  - 최신 글도 자기 연재의 회차 목록에 그대로 포함된다(중복 허용: 최신 글 강조 + 연재 맥락).
- 캐시 정책·user-neutral 변경 없음. 북마크·읽음은 클라이언트 hydration 그대로다(`newsprint-bookmark-icon[data-item-id][data-item-type="blog"]`, `.blog-list-item`).

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| 필자 줄 | Amy · {N}편 · 마지막 글 {M월 D일} | Amy · {N} posts · Latest {Mon D} |
| 검색 placeholder / aria-label | 글 검색 | Search posts |
| 최신 라벨 | {분야} · 최신 | {Field} · Latest |
| 연재 요약 | {k}개의 연재 / {분야} {n}편 | {k} series / {Field} · {n} |
| 연재 편수 | {n}편 | {n} posts |
| 회차 | {n}화 | Ep. {n} |
| 짧은 글 머리 | 짧은 글 | Short notes |
| 검색 결과 없음 | 일치하는 글이 없어요 | No posts match |

분야 이름과 설명은 DB `label_{ko|en}`, `description_{ko|en}`을 쓴다.

## 모바일 (≤767px)

- 필자 줄은 줄바꿈한다(검색 입력은 아래 줄에서 전체 폭).
- 최신 글은 1단이다(요약 블록은 아래).
- 연재는 1열이다.
- 가로 넘침은 0이어야 한다.

## 테스트

- **새 `blog-serial.test.mjs`**(순수 함수)
  - lead 선택(null 날짜 제외)
  - 연재 대상(main·visible·글 있음)과 sort_order
  - 회차 오름차순과 null 날짜 맨 뒤
  - shortNotes(sub + 미분류, 내림차순)
  - total, latestAt, 빈 입력
- **새 `blog-list-serial.test.cjs`**(구조)
  - ko/en 목록: `sidebar={false}`, `BlogFeaturedCard`·`data-blog-sentinel`·`blog-category-tabs` 없음, `buildBlogFront(`
  - 연재·짧은 글 마크업: `.blog-series`, `li.blog-list-item`, 북마크 계약
  - 검색 스크립트: 가드, `#blog-search-empty`
  - KO/EN 문구
  - CSS: 2열과 모바일 1열, 필자 줄 이중선
- **갱신**
  - `blog-v2`: 탭·featured 관련 목록 단언을 새 구조로 바꾼다.
  - `blog-mobile-sidebar-structure`: 목록 페이지의 사이드바 소유 단언을 분야·상세 기준으로 바꾼다.
  - `blog-bookmark-card-contract`: FeaturedCard 삭제 시 해당 단언을 연재 줄 마크업으로 옮긴다.
  - `blog-detail-sidebar-structure`: index 페이지의 `mode="index"` 단언 → 목록은 `sidebar={false}` 단언으로 바꾼다. 분야·상세 단언은 유지한다.
  - `blog-category-badge-font`: `BlogFeaturedCard.astro`를 읽으므로 삭제와 함께 해당 단언을 지운다(나머지 유지).
  - `blog-sidebar-layout`(이미 실패 중): index의 `blog-mobile-toolbar` 단언을 분야 페이지 기준으로 옮긴다.
  - `blog-title-fonts`, `blog-section-heading-font`(이미 실패 중): 삭제되는 `.blog-featured-card-title`·`.blog-section-header` 의존 단언이 있으면 정리한다. 이름 기준 비교에서 신규 FAIL이 아니어야 한다.
  - `public-list-personalization`: content-status hydration 유지를 확인한다.
  - i18n `blog.featured`·`blog.allPosts` 키가 더 이상 쓰이지 않으면 제거한다(grep).
- **유지 확인**: `library-blog-items-contract`, `blog-detail-sidebar-behavior`, `blog-toc-structure`, `detail-rail-actions-placement`, `public-cache-policy`, `font-roles`, `retro-decoration-removed`
- **새 단언 추가**
  - `blog-serial.test.mjs`: `tech` → `study` 정규화, 숨김 분야 글이 짧은 글 끝으로 가는지
  - `blog-list-serial.test.cjs`: `timeZone: 'Asia/Seoul'`, 최신 글 블록에 북마크 버튼 없음, 연재 줄 북마크가 `li.blog-list-item` 안
  - 헤딩 수준: 최신 글·연재·짧은 글이 `h2`
- **검증 매트릭스**
  - 종이·순백·다크 × ≥1024px·375px × ko/en
  - 직접 확인: 검색 입력·결과 없음·지우기, 연재 제목 링크(분야 페이지), 북마크 버튼 존재, 회차 순서
  - 분야 페이지·글 상세가 그대로인지 회귀 확인
  - 가로 넘침 0, 대비 검사
- 전체 테스트는 이름 기준 비교, 신규 FAIL은 0이어야 한다.

## 범위 밖

- 글 상세 재설계(다음 단계: 기사 상세처럼 경로 줄 + 한 단 + 세로 액션 막대 후보)
- 분야 페이지 디자인
- 연재 편집 순서·연재 전용 이름(관리자 기능)
- 글 100편 상한
