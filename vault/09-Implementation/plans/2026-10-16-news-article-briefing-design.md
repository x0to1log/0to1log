# 기사 상세 재설계 (B 브리핑 먼저 + C 짝 기사) — Design Spec

**Status:** implemented (2026-10-17) — [[2026-10-16-news-article-briefing]]
**Mockup:** `.superpowers/brainstorm/article/article-v1.html` (B안 + C안의 짝 기사 링크)
**관련:** [[2026-10-16-news-list-desks-design]], [[2026-10-15-site-redesign-phase4-article]]

## 배경

- 홈(신문 1면)과 뉴스 목록(두 데스크)에 이어 뉴스 기사 상세(`/ko|en/news/[slug]/`)를 다시 설계한다.
- 지금 문제
  - 모든 기사 위에 "최신 AI 뉴스 모음집" 큰 마스트헤드와 킥커·subkicker 줄이 반복돼서 기사 제목이 첫 화면 아래로 밀린다.
  - 오른쪽 레일에 검색, 액션, 목차, 요약, 용어, 다음 글이 몰려 있어 본문 폭이 좁다.
- 시안 A(신문 기사면) / B(브리핑 먼저) / C(데스크 정체성 + 짝 기사) 중 **B에 C의 짝 기사 링크를 섞은 안**을 골랐다.
- 4단계(2026-10-15)의 "2단 유지 + 레일 정리" 결정을 이번에 **한 단 집중**으로 바꾼다.

## 화면 구성 (위에서 아래로)

1. **경로 줄** — `NewsprintShell` 새 prop `compact`
   - 큰 마스트헤드, 킥커, subkicker를 렌더하지 않는다.
   - 대신 한 줄 `<nav class="newsprint-crumb">`을 둔다: `← AI 뉴스 · 제212호 · 2026년 10월 15일`
     - 날짜는 기존 `data-local-date` 메커니즘을 그대로 쓴다.
     - 호수는 `publishedAt` 기준이다(현행 Shell과 같다).
   - 기존 Shell 사용처(목록, 용어집, 관리자)는 `compact` 기본값 `false`라서 변화가 없다.
2. **오른쪽 레일 제거**: `rail={false}`(뉴스 목록에서 추가한 prop). 본문은 `.newsprint-grid--full`이다.
   - Shell은 `compact`일 때 `.newsprint-main`에 `newsprint-main--article` 클래스를 추가한다.
   - `.newsprint-main--article`의 **전체 폭은 최대 800px**, 가운데 정렬이다(제목·브리핑·끝 블록 공통).
   - 데스크톱 인라인 액션 칼럼(72px + gap 0.9rem)을 뺀 본문 prose 폭은 약 714px다.
3. **제목 영역**: `NewsprintArticleLayout` 기존 마크업(topline, h1 `.newsprint-lead-title`, `.newsprint-deck`, 태그) 그대로다.
   - 제목 크기는 현행 `clamp(1.85rem, 2.8vw, 2.4rem)`을 유지한다. 이미 데스크톱에서 약 36–38px이다.
4. **짝 기사 링크 (C)** — 제목 영역 바로 아래, 판 선택 줄 위
   - `리서치 데스크는 이렇게 봤어요 → {제목}` 한 줄. 비즈니스 기사면 "리서치 데스크", 리서치 기사면 "비즈니스 데스크"다.
   - 데스크 색 2px 왼쪽 선: `--tier-paid`(비즈니스)·`--tier-freemium`(리서치). 뉴스 목록과 같은 토큰이다.
   - EN: `The research desk's take →` / `The business desk's take →`
   - sibling이 없으면(주간 정리, 한쪽 데스크만 발행된 날) 렌더하지 않는다.
5. **판 선택 줄**: 마크업은 현행 그대로다(입문판/학습판/전문판, `persona-switcher`, `#persona-float`). **위치는 옮긴다.**
   - 현재 순서: 제목 → 요약 → 태그 → divider → `.newsprint-article-find` → Fact Pack → Core Analysis → `.switcher-bar` → prose
   - 바뀐 순서: `.switcher-bar`와 `<template id="persona-data">`를 짝 기사 링크 바로 다음, 브리핑 앞으로 옮긴다. find bar보다 위다.
   - persona 스크립트는 id·class로 찾으므로 영향이 없다. float의 IntersectionObserver도 switcher 자체를 관찰하므로 그대로 동작한다.
   - 새 순서: 제목 영역 → 짝 링크 → 판 선택 → 브리핑 → find → Fact Pack → Core Analysis → prose
6. **30초 브리핑** — 판 선택 줄 바로 아래
   - `focusItems`(레일 "이 글의 요약"과 같은 데이터, 판과 무관) 3개를 큰 번호(Newsreader 1.75rem, accent)와 함께 3열 그리드로 놓는다. 배경 `--color-bg-secondary`, radius 2px.
   - 라벨: "30초 브리핑" / "30-second briefing"
   - focusItems가 비면 렌더하지 않는다.
     - 현행 fallback 문구는 `lib/articleRail.ts`의 고정값이다. fallback일 때도 렌더할지는 아래 "데이터"를 따른다.
   - 모바일은 1열 목록이다(번호 + 문장).
   - **"한 줄 요약" 문장은 브리핑에 넣지 않는다.** 판마다 본문 안에 있어 판 전환과 동기화해야 하기 때문이다. 본문 첫 섹션에 그대로 남는다.
7. **본문**: 현행 그대로다.
   - find bar, Fact Pack, Core Analysis, prose(용어 하이라이트·팝업·인용), "한눈에 보기"(퀴즈)
   - 액션: 아래 "액션"을 따른다.
8. **기사 끝 블록** — 레이아웃의 새 named slot `after-guide`. "한눈에 보기" 다음, 출처 앞에 렌더된다.
   - **이 기사의 용어**: `relatedTerms` 최대 3개를 한 줄 목록으로 둔다. 각 줄은 한글명(Hahmlet 700) + 영문명(Newsreader, muted) + 정의 1–2줄 + 링크다.
   - **이 소식, 두 데스크의 시선 (C)**: sibling이 있을 때만 2단 카드다.
     - 왼쪽: "지금 읽은 글" + 현재 기사 제목(링크 없음)
     - 오른쪽: sibling 데스크 라벨 + 제목 + 요약 1줄(링크)
     - 모바일은 1단이다.
9. 이후 현행 순서 그대로: 출처 → 관리자 버튼 → `[data-reading-end]` → 피드백 → 댓글
10. **다음 읽어볼 글**: 페이지에서 레이아웃 다음에 렌더한다(주간 카드와 같은 위치). `similarPosts` 최대 3개다.
    - 유형 라벨은 `postTypeLabel(locale, type)`이다(SideRail의 하드코딩 "Research/Business"를 쓰지 않는다).

## 액션 (좋아요·댓글·북마크·공유·읽은 비율)

- 기존 인라인 배치를 그대로 쓴다: 뉴스 페이지가 `showStickyActions={true}`(레이아웃 기본값)를 넘긴다.
  - 데스크톱(≥1024px): 본문 오른쪽 72px **세로 고정 막대**(`reading-actions-layout--article`). 진행 막대가 포함된다.
  - 모바일: 하단 고정 바(현행 레일 액션의 모바일 동작과 같다).
- 스펙 승인 시 "머리 아래 가로 얇은 바"로 설명했으나, 이미 테스트된 기존 부품(블로그에서 쓰던 인라인 배치)을 재사용하기 위해 **본문 옆 세로 고정 막대로 바꾼다**. 사용자 검토 시 알린다.
- 다음 훅은 모두 현행 마크업 그대로다.
  - `[data-like-btn]`, `.newsprint-bookmark-icon[data-item-id][data-item-type]`, `.newsprint-share-wrapper`, `[data-reading-action="comments"]`, 읽은 비율
  - 읽음 기록 스크립트가 쓰는 `[data-item-id][data-item-type="news"]`는 인라인 액션의 북마크 버튼이 제공한다(레일에서 옮겨 옴).
- `.persona-float`의 하단 오프셋(모바일 하단 바 위)은 현행 값을 유지한다.

## 레일에서 빠지는 것

- `NewsprintTOC`: 뉴스 기사 전용이라 페이지에서 import를 제거하고 컴포넌트와 전용 CSS(`.newsprint-toc*`)를 삭제한다. 삭제 전에 grep으로 사용처가 없는지 확인한다.
- 레일 검색 폼(`.newsprint-rail-search`): 제거한다.
  - 모바일 sticky 검색(`.handbook-search-sticky--detail`)과 `syncSearchBarVisibility`는 현행 그대로다. 이 검색은 ≥1024px에서 `display:none`이다.
  - 데스크톱에서는 검색창을 따로 두지 않는다. 기사 안 찾기(find bar)와 헤더 내비게이션이 남는다.
  - 데스크톱에서 검색창을 다시 보이게 하면 인라인 액션 칼럼(top 5.75rem, z-index 200)과 겹친다. 용어집 상세도 같은 클래스를 쓰므로 CSS를 바꾸지 않는다.
- `ReadingActionsRail`·`NewsprintSideRail`은 블로그·용어집·관리자가 쓰므로 **삭제하지 않는다**. 뉴스 기사 페이지에서만 쓰지 않는다.

## 데이터

- `lib/pageData/newsDetailPage.ts`에 **sibling 쿼리 1개**를 추가한다. 기존 병렬 단계에 넣는다.
  - 조건
    - `post.post_type`이 `business` 또는 `research`이고, `post.published_at`이 있으며 `deskDayRange(kstDay(post.published_at))`가 null이 아닐 때만 실행한다. 아니면 쿼리 없이 `sibling = null`이다.
    - 관리자 미리보기의 초안은 `published_at`이 null일 수 있다. `toISOString()` 예외가 `Promise.all` 구성 중에 나지 않게 하기 위해서다.
    - `news_posts`, `status = 'published'`(프리뷰 모드에서도 published만), `locale` 같음
    - `post_type`이 반대 데스크
    - `published_at`이 현재 기사의 KST 날짜 범위 안: `[day 00:00+09:00, 다음 날 00:00+09:00)`. `day = kstDay(post.published_at)`(`lib/homeFront.js`)다.
  - 정렬과 개수: `published_at desc`, `.limit(1)`, `.maybeSingle()`
  - 컬럼은 새 상수 `NEWS_SIBLING_COLUMNS = 'id, slug, title, title_learner, title_beginner, excerpt, post_type, reading_time_min'`이다(와일드카드 금지 테스트 준수).
  - 오류는 로그만 남기고 `null`로 처리한다. 페이지 503을 유발하지 않는다.
  - 표시 제목은 `resolveDisplayTitleExcerpt(sibling, 'learner')`다.
    - **리터럴 learner**를 쓰는 이유: 캐시되는 HTML은 learner 고정이고(`news-persona-cache-policy`), `getEffectivePersona(locals.profile)`은 미리보기에서 관리자 프로필을 읽기 때문이다.
    - 판을 전환해도(클라이언트) 짝 기사 제목은 바뀌지 않는다. 의도된 동작이다.
  - 반환 필드: `sibling: { slug, title, excerpt, post_type, reading_time_min } | null`
- KST 날짜 범위 계산은 순수 함수 `deskDayRange(day)`로 만들어 `lib/newsDesks.js`에 추가하고 단위 테스트를 붙인다.
  - 반환값은 `{ start, end }` ISO 문자열이다.
  - `day`가 `YYYY-MM-DD` 형식이 아니거나 null이면 `null`을 반환한다.
- 브리핑의 focusItems
  - `post.focus_items`가 비어 fallback 문구일 때는 브리핑을 렌더하지 않는다. 고정 문구를 "30초 브리핑"으로 보여주지 않기 위해서다.
  - 이를 위해 `newsDetailPage.ts`가 `focusItemsAreFallback: boolean`을 함께 반환한다.
- 나머지 데이터와 캐시 정책은 변경하지 않는다(user-neutral, `publicCachePolicy`, persona 기본 learner).

## 컴포넌트

- **수정 `NewsprintShell.astro`**: `compact?: boolean`(기본 false), `backHref?: string`, `backLabel?: string`
  - compact면 header 대신 crumb nav를 렌더하고 `.newsprint-main`에 `newsprint-main--article`을 붙인다.
  - `masthead`는 `masthead?: string`으로 optional이 된다. compact가 아닌데 값이 없으면 빈 문자열로 렌더한다(기존 호출부는 모두 값을 넘긴다).
  - 뉴스 기사 페이지는 `masthead`·`editionLabel`·`subkicker`를 더 이상 넘기지 않는다. 페이지의 `editionMap`·`editionLabel` 변수도 삭제한다.

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| 경로 줄 back 링크(`backLabel`, 페이지가 넘김) | AI 뉴스 | AI News |
| 짝 기사 링크(비즈니스 기사에서) | 리서치 데스크는 이렇게 봤어요 → | The research desk's take → |
| 짝 기사 링크(리서치 기사에서) | 비즈니스 데스크는 이렇게 봤어요 → | The business desk's take → |
| 브리핑 라벨 | 30초 브리핑 | 30-second briefing |
| 용어 블록 제목 | 이 기사의 용어 | Terms in This Article |
| 두 데스크 카드 제목 | 이 소식, 두 데스크의 시선 | Two desks on this story |
| 두 데스크 카드 현재 글 라벨 | 지금 읽은 글 | You just read |
| 다음 글 제목 | 다음 읽어볼 글 | Read Next |
| 데스크 라벨 | `postTypeLabel(locale, type)` | 〃 |

## 컴포넌트 (계속)
- **수정 `NewsprintArticleLayout.astro`**(관리자 숨김 사용처는 새 props가 없으므로 변화 없음)
  - 새 optional props: `briefingItems?: string[]`, `sibling?: {...} | null`
  - 짝 기사 링크와 브리핑 마크업을 위 순서로 렌더한다.
  - named slot `after-guide`를 "한눈에 보기" 다음, 출처 앞에 둔다.
- **새 `components/newsprint/NewsTwinDesks.astro`**: "이 소식, 두 데스크의 시선" 카드(현재 제목, sibling, locale)
- **새 `components/newsprint/NewsArticleTerms.astro`**: 기사 끝 용어 목록(relatedTerms, locale)
- **새 `components/newsprint/NewsReadNext.astro`**: 다음 읽어볼 글(similarPosts, locale)
- **수정 `pages/{ko,en}/news/[slug].astro`**
  - `compact` + `rail={false}`
  - `showStickyActions` 제거(기본 true)
  - 레일 Fragment 삭제
  - 새 props와 slot 연결, ReadNext 추가
  - 미사용 import 정리(`NewsprintTOC`, `NewsprintSideRail`, `ReadingActionsRail`)
- **삭제**: `NewsprintTOC.astro` + 전용 CSS. 다른 사용처가 없을 때만 삭제한다.

## 모바일 (≤767px)

- 경로 줄 → 제목 → 짝 기사 링크 → 판 선택 → 브리핑(1열) → 본문 → 끝 블록(1단) → 하단 고정 액션 바
- 가로 넘침 0. 짝 기사 링크의 긴 제목은 줄바꿈한다.

## 테스트

- **`news-desks-select.test.mjs` 추가 단언**
  - `deskDayRange('2026-10-15')` → `{ start: '2026-10-14T15:00:00.000Z', end: '2026-10-15T15:00:00.000Z' }`
  - `deskDayRange(null)`과 `deskDayRange('bad')`는 `null`이다.
- **레이아웃 순서 단언**: `.newsprint-twin-link` < `switcher-bar` < `news-briefing` < `newsprint-article-find`(소스 인덱스 순서)
- **새 `news-article-briefing.test.cjs`**
  - ko/en 페이지: `compact`, `rail={false}`, `showStickyActions={false}` 없음, `NewsprintTOC`/`ReadingActionsRail`/`NewsprintSideRail` import 없음, `NewsReadNext` 사용
  - 레이아웃: briefing·sibling props, `after-guide` slot이 출처 앞에 있다. DOM 순서는 제목 → 짝 링크 → 판 선택 → 브리핑.
  - Shell: compact 분기, crumb
  - 데이터: `NEWS_SIBLING_COLUMNS` select, `.limit(1)`, 반대 데스크 조건, `deskDayRange` 사용, sibling 오류가 503을 만들지 않음, `focusItemsAreFallback`
  - KO/EN 문구: 브리핑, 데스크 링크, 두 데스크의 시선, 용어, 다음 글
  - CSS: 800px 칼럼, 브리핑 3열 + 모바일 1열, 짝 링크 데스크 색 토큰
- **갱신**
  - `detail-rail-actions-placement.test.cjs`: 뉴스 페이지의 `showStickyActions={false}`와 `<ReadingActionsRail` 단언을 반대로 바꾼다(인라인 액션 사용, 레일 래퍼 없음). 블로그·용어집 단언은 유지한다.
  - `article-v2.test.cjs`: `NewsprintSideRail`의 "이 기사의 용어" 단언은 SideRail이 남으므로 유지한다. 새 `NewsArticleTerms`에 같은 KO/EN 제목이 있는지 추가로 단언한다.
  - `public-detail-query-contract`: 새 select가 상수를 쓰는지 확인한다. 필요하면 해당 테스트 규칙에 맞춘다.
  - `NewsprintTOC` 삭제 시 이를 읽는 테스트가 있으면 갱신한다(grep).
- **유지 확인**: `news-persona-cache-policy`, `news-persona-title-switcher`, `news-article-find-structure`, `admin-live-preview`, `content-feedback-contract`, `issue-number-shell`, `hreflang-alt-slug`, `csp-inline-scripts`, `sticky-reading-actions-structure`, `reading-actions-*`
- **검증 매트릭스**
  - 종이·순백·다크 × 1024px+·375px × ko/en
  - 짝 기사 있는 기사(비즈니스·리서치 각 1)와 주간 정리 기사
  - 직접 클릭: 판 전환(제목·요약·본문·퀴즈 변화), 용어 팝업, 본문 찾기(`?q=`), 북마크 버튼 존재, 공유 메뉴 열림, 댓글 영역, 짝 기사 링크 이동
  - 가로 넘침 0, 대비 검사
  - 관리자 미리보기(`?preview=1`)는 로그인이 필요하므로 렌더 오류가 없는지만 코드로 확인한다.
- 전체 테스트: 이름 기준으로 기준선과 비교한다. 신규 FAIL은 0이어야 한다.

## 범위 밖

- 블로그·용어집 상세 레이아웃(공유 부품은 건드리지 않음)
- 판 전환 스크립트의 `.newsprint-prose` 선택 버그(분석 블록이 먼저 잡힘), `NewsprintTOC`의 `astro:page-load` 미대응 — 별도 수정 후보(TOC는 삭제되므로 후자는 사라짐)
- 오래된 테스트 `news-fact-pack-structure`, `detail-rail-copy`, `article-deck-font` 정리
