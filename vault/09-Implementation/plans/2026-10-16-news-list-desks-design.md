# 뉴스 목록 재설계 (E안 · 두 데스크) — Design Spec

**Status:** approved (2026-10-16)
**Mockup:** `.superpowers/brainstorm/news/news-list-v4.html` (E안)
**관련:** [[2026-10-15-home-front-page-redesign-design]], [[2026-10-14-site-redesign-soft-newsprint-design]]

## 배경

- 홈을 신문 1면으로 바꾼 뒤 뉴스 목록(`/ko/news/`, `/en/news/`)도 같은 방식으로 다시 설계한다.
- 지금 목록의 문제
  - 모든 카드가 같은 크기라서 "하루 2편(비즈니스·리서치) + 주 1편 주간 정리"라는 발행 리듬이 보이지 않는다.
  - 오른쪽 "최신 기사" 레일이 목록 내용과 겹친다.
  - 카드마다 붙은 해시태그 줄이 잡음이 된다.
- 시안 6개(A~F) 중 **E: 두 데스크가 마주 보는 지면**을 골랐다.
  - 같은 날 두 데스크가 같은 소식을 다른 관점으로 다루는 일이 많다(예: Gemini 4 Argon 출시, GPT-6 가격 인하).
  - 그래서 비교 구도 자체가 이 사이트의 형식이 된다.

## 화면 구성 (데스크톱 ≥768px, 탭 "전체" + 검색어 없음 = 데스크 모드)

1. **헤더 영역**: `NewsprintShell` 현행 유지(호수·날짜 킥커, 관리자 편집 마스트헤드, subkicker).
   - 마스트헤드 문구는 `site_content.news_masthead`(현재 "최신 AI 뉴스 모음집")다.
   - 문구를 "AI 뉴스"로 바꿀지는 Amy가 관리자 설정에서 정한다. 코드 기본값은 바꾸지 않는다.
2. **편집 노트**: `editorial_note`를 마스트헤드 아래 한 줄로 가운데 정렬해 보여준다(muted, 0.9rem).
   - 기존 레일에 있던 것을 옮긴다. 값이 없으면 렌더하지 않는다.
3. **검색창 + 탭**: 현행 위치·마크업·id 유지(`#news-search`, `NewsprintCategoryFilter`, `#news-result-count`, `#news-no-results`).
4. **오른쪽 레일 제거**
   - `NewsprintShell`에 `rail` prop(기본 `true`)을 추가한다.
   - 뉴스 목록은 `rail={false}`로 aside를 렌더하지 않고, 본문이 전체 폭(`.newsprint-grid--full`)을 쓴다.
   - "Start Here" 섹션(`start_here_sections`)은 뉴스 목록에서 더 이상 보이지 않는다. DB 값과 관리자 설정 항목은 그대로 둔다.
5. **두 데스크 지면** `#news-list-results.news-desks[data-mode="desks"]`
   - **열 제목 줄**: 비즈니스 데스크와 리서치 데스크 이름을 둔다. 아래쪽에 1px `--color-text-primary` 선을 긋는다.

     | | 왼쪽 | 가운데 | 오른쪽 |
     |---|---|---|---|
     | KO | "비즈니스 데스크 · 돈과 시장"(오른쪽 정렬) | 빈칸 | "리서치 데스크 · 논문과 기술" |
     | EN | "Business desk · Money and markets" | 빈칸 | "Research desk · Papers and tech" |

   - **날짜 줄(day row)**: `grid-template-columns: minmax(0,1fr) 92px minmax(0,1fr)`
     - 왼쪽: 비즈니스 칸(텍스트 오른쪽 정렬)
     - 가운데: 날짜 축. 큰 날짜 "10.15"(Newsreader 500, 1.5rem)와 요일 · 호수(0.7rem)를 쓴다. 날짜 축 세로선은 `--color-border`.
     - 오른쪽: 리서치 칸
     - 줄 사이: 점선
   - **기사 칸(desk cell)**
     - 제목: Hahmlet 700, 1.15rem
     - 요약: 1줄 말줄임, 0.82rem
     - 메타: 읽는 시간
     - 북마크 버튼
     - 오늘 줄의 제목은 1.4rem이다. 지금의 상단 헤드라인 3개를 대신한다.
   - **데스크 라벨**: 모든 칸에 점 라벨(`postTypeLabel(locale, type)`)을 DOM에 항상 렌더한다.
     - 데스크톱 데스크 모드에서는 위치로 데스크가 드러나므로 라벨을 시각적으로만 숨긴다(sr-only 패턴). `display:none`은 쓰지 않는다.
     - 화면 낭독기는 항상 "비즈니스"/"리서치"를 읽는다.
   - **빈 칸**: 그날 한쪽 유형 기사가 없으면 muted 문구를 둔다.
     - 이 placeholder는 `newsprint-card` 클래스와 data 속성을 갖지 않는 일반 요소(`.news-desk-empty`)다. 그래야 검색 결과 수와 빈 줄 판정에 섞이지 않는다.
     - "이날은 비즈니스 기사가 없어요" / "이날은 리서치 기사가 없어요"
     - EN: "No business story this day" / "No research story this day"
   - **오늘** 날짜 숫자는 accent 색이다. "오늘"/"Today" 표기를 붙인다.
   - **주간 정리 띠**: 그 주간 정리의 발행일(KST) 줄 바로 위에 전체 폭 띠로 넣는다.
     - 배경 `--color-text-primary`, 글자 `--color-bg-primary`. 다크 테마는 `--color-bg-tertiary` 배경과 `--color-text-primary` 글자(홈 키워드 판과 같은 규칙).
     - 내용: 라벨 "MM.DD · 주간 정리 · N분"(EN "Weekly · N min"), 제목(Hahmlet 700, 1.2rem), 북마크.
6. **목록에서 빼는 것**: 해시태그 줄, 카테고리 라벨("AI 뉴스" 킥커), 날짜 문자열(날짜 축이 대신한다).
   - 태그는 `data-search-text`에 계속 포함해서 검색에 쓰인다.

## 데스크 색

- 기존 토큰을 재사용하고 새 색은 만들지 않는다.
  - 비즈니스: `--tier-paid`(종이·순백 #B4472A, 다크 #E08A6A)
  - 리서치: `--tier-freemium`(종이·순백 #3E6FB0, 다크 #7FA6DE)
- 쓰는 곳은 세 군데뿐이다: 열 제목 글자, 칸의 점 라벨(모바일), 모바일 왼쪽 2px 선. 기사 제목은 기본 글자색이다.
- 두 색은 작은 글자(0.75rem)로 쓰이므로 세 테마 모두 bg-primary 위 4.5:1 이상이어야 한다. 테스트로 검사한다.
  - 기준에 못 미치면 해당 테마에서만 desk 전용 토큰으로 어둡게 보정한다.

## 탭·검색 시 (목록 모드)

- 탭이 "전체"가 아니거나 검색어가 있으면 `data-mode="list"`로 바꾼다.
  - 날짜 줄은 한 단이 된다: 날짜 축은 줄 맨 위 가로 머리("10.15 · 목 · 제212호" + 가는 선)로, 칸들은 그 아래에 쌓인다.
  - 빈 칸 문구는 숨긴다.
  - 칸마다 유형 점 라벨(비즈니스/리서치)이 보인다.
- 기존 동작은 그대로 재사용한다. 각 칸(주간 띠 포함)은 기존 카드 계약을 지킨다.
  - 클래스 `newsprint-card`
  - `data-category`, `data-post-type`, `data-post-id`, `data-search-text`
  - `NewsprintCategoryFilter`가 `data-filtered`, `newsListSearch`가 `data-search-matched`를 붙이고, 기존 CSS가 숨긴다.
- **새 스크립트 `scripts/newsDeskMode.ts`**
  - 모드를 계산하고, 보이는 칸이 하나도 없는 날짜 줄에 `data-row-empty="true"`를 붙여 숨긴다.
    - "보이는 칸"은 줄 안의 `.newsprint-card` 중 `data-filtered="false"`도 `data-search-matched="false"`도 아닌 것만 센다.
  - 초기화
    - 이벤트를 기다리지 않고 init에서 한 번 계산한다. 활성 탭(`aria-selected="true"`의 `data-filter`, 없으면 URL `post_type`)과 `#news-search` 값을 직접 읽는다.
    - 필터 컴포넌트의 첫 `newsprint:filter-change`가 이 스크립트보다 먼저 발행될 수 있기 때문이다.
    - `newsListSearch`와 같은 패턴을 따른다: `astro:page-load`와 모듈 로드 양쪽에서 init을 호출하고, `dataset.deskModeReady` 플래그로 리스너를 두 번 등록하지 않는다.
  - 기존 스크립트 이후에 동작해야 하므로 다음 신호에 반응한다.
    - `newsListSearch`가 `applySearch` 끝에 발행하는 새 이벤트 `news:list-updated`. 한 줄을 추가한다.
    - `newsprint:filter-change`
- 결과 수와 "검색 결과 없음"은 기존 `newsListSearch` 동작 그대로다.
- `scripts/newsListMultiHeadline.ts`는 삭제한다(헤드라인이 없어짐).

## 데이터

- 쿼리는 현행 그대로 유지한다.
  - 일간 business/research 최대 100편, 주간 최대 20편, `POSTS_FIELDS`
  - persona 제목 해석(`resolveDisplayTitleExcerpt`)
  - 오류 시 503
- **새 순수 모듈 `lib/newsDesks.js`**: `buildDeskRows(posts, now)` → `DeskEntry[]`
  - 입력: 일간과 주간을 합친 배열(순서 무관). 출력은 KST 날짜 내림차순이다.
  - `{ kind: 'weekly', day, post }`
    - 그날의 주간 정리 각각
    - 같은 날의 day row들보다 앞에 둔다.
  - `{ kind: 'day', day, showDate, isToday, business, research }`
    - 그날 비즈니스와 리서치를 published_at 내림차순으로 짝지운다. 행 수는 `max(비즈니스 수, 리서치 수)`다.
    - 첫 행만 `showDate: true`다.
    - 짝이 없는 쪽은 `null`이다.
  - `day`는 `kstDay(published_at)`(homeFront.js 재사용)다. published_at이 null인 글은 제외한다.
  - post_type이 business/research/weekly가 아니면 business 칸으로 보낸다(현행 카드 기본값과 같다).
- 날짜 표기
  - 큰 숫자: `MM.DD`
  - 요일: `toLocaleDateString(lang, { timeZone: 'Asia/Seoul', weekday: 'short' })`
  - 호수: `issueLabel(locale, issueNumber(new Date(day + 'T12:00:00+09:00')))`

## 컴포넌트

- **새 `components/newsprint/NewsDeskList.astro`**
  - props: `locale`, `entries`(buildDeskRows 결과에 display_title/excerpt가 들어간 posts)
  - 열 제목, 날짜 줄, 주간 띠를 렌더한다.
- **새 `components/newsprint/NewsDeskCell.astro`**
  - 칸 하나(제목·요약·읽는 시간·북마크). 북마크 버튼 마크업은 `NewsprintListCard`와 같다.
    - `newsprint-bookmark-icon`, `data-item-id`, `data-item-type="news"`, `data-bookmarked`
    - `scripts/bookmark` 계약
  - 공개 HTML은 user-neutral이므로 항상 `data-bookmarked="false"`다. 현행과 같다.
- **삭제**
  - `NewsprintHeadline.astro`, `NewsprintListCard.astro`, `NewsprintListRail.astro`(뉴스 목록 외 사용처 없음)
  - `scripts/newsListMultiHeadline.ts`
  - 관련 전용 CSS
    - `.newsprint-headline*` 전부
    - `.newsprint-rail-rank`, `.newsprint-rail-body`(ListRail 전용)
  - **`.newsprint-rail` 기본/sticky/모바일 규칙과 `-link`, `-meta`, `-date`, `-note`, `-divider`, `-stack`, `-search`는 지우지 않는다.**
    - HandbookListRail, HandbookSideRail, NewsprintSideRail, 상세 페이지가 공유한다.
    - 삭제 전에 각 셀렉터를 `frontend/src` 전체에서 grep해서 다른 사용처가 없는지 확인한다.
- 수정: `NewsprintShell.astro`(`rail` prop), `ko|en/news/index.astro`

## 모바일 (≤767px)

- 데스크 모드도 한 단이다.
  - 열 제목 줄은 숨긴다.
  - 날짜 줄 머리: 큰 날짜 + 가는 선 + 요일.
  - 그 아래 비즈니스 칸 → 리서치 칸 순서다.
  - 각 칸 왼쪽에 데스크 색 2px 선을 두고 padding-left를 준다. 점 라벨에 데스크 이름이 보인다.
- 빈 칸 문구는 모바일에서 숨긴다(세로 공간 절약).
- DOM 순서 = 읽기 순서: 날짜 → 비즈니스 → 리서치. 데스크톱 3열은 grid 영역으로 배치하고 `order`는 쓰지 않는다.
- 페이지 가로 넘침은 0이어야 한다.

## 테스트

- **새 `news-desks-select.test.mjs`**
  - 날짜 묶기와 KST 경계
  - 짝짓기: 2:2, 2:1, 0:1
  - 주간 정리 위치
  - 오늘 표시
  - null published_at 제외
  - 알 수 없는 post_type
- **새 `news-list-desks.test.cjs`**
  - ko/en 페이지가 `NewsDeskList`를 쓰고 `rail={false}`이다.
  - 칸이 카드 계약(클래스와 data 속성 4개)을 지킨다.
  - 목록에 해시태그와 카테고리 라벨이 없다.
  - 열 제목 KO/EN, 빈 칸 문구 KO/EN이 있다.
  - `newsDeskMode` import가 있고 `newsListMultiHeadline`이 없다.
  - CSS: 데스크 grid, 모바일 한 단, `data-mode="list"` 규칙, 다크 주간 띠 규칙
  - `--tier-paid`·`--tier-freemium`의 3테마 대비가 4.5:1 이상이다.
- **갱신**
  - `list-v2.test.cjs`
    - 삭제된 컴포넌트 3개(ListCard, Headline, ListRail)를 읽는 부분을 지운다.
    - `.newsprint-card`/탭/태그 CSS 계약 중 아직 유효한 것은 남긴다.
    - 대신 NewsDeskCell의 훅(`data-post-type=`, `newsprint-card-stretched-link`)을 검사한다.
  - `news-search-list-structure.test.cjs`: NewsprintHeadline·ListCard 단언을 NewsDeskCell `data-search-text=`로 바꾼다.
  - `list-v2.test.cjs`의 `.newsprint-headline-title`(700), `.newsprint-headline-kicker`(대문자 금지) 단언은 새 칸 제목 규칙 `.news-desk-title`(Hahmlet 700)과 라벨 규칙(대문자 금지)으로 바꾼다.
  - `news-headline-mobile-tags-wrap.test.cjs`(현재 PASS)
    - `NewsprintHeadline.astro` 읽기를 지운다.
    - `.newsprint-card-bottom`·`.newsprint-tags-inline` CSS 단언만 남긴 CSS 전용 테스트로 유지한다.
    - 이 두 규칙은 삭제되는 컴포넌트만 쓰던 것이라 사용처가 없어지지만, **이번 범위에서는 CSS를 그대로 둔다**.
      - `list-v2`의 해당 단언과 `.newsprint-tags-inline .newsprint-tag,\n.newsprint-article-tags .newsprint-tag` 결합 셀렉터를 건드리지 않기 위해서다.
      - 기사 상세 태그 스타일이 이 결합 셀렉터를 쓴다.
    - 사용처 없는 CSS 정리는 후속 작업으로 남긴다.
  - `font-roles.test.cjs`(현재 PASS): 48행 셀렉터 배열에서 `.newsprint-headline-deck`을 `.news-desk-excerpt`(새 요약 클래스)로 바꾼다.
  - `list-rail-copy.test.cjs`(이미 실패 중, 레일 삭제): 파일을 삭제한다.
  - `list-meta-order.test.cjs`(이미 실패 중, 존재하지 않는 `pages/en/log/`를 읽음): 삭제된 ListCard도 읽는 stale 테스트이므로 함께 삭제한다.
  - `newsListSearch`: 이벤트 발행 한 줄 추가에 맞는 단언을 추가한다.
- **유지 확인**
  - `public-list-query-budget`(limit 100)
  - `public-list-personalization`
  - `issue-number-shell`
  - `news-post-type-tab-order`(비즈니스 탭이 리서치보다 먼저)
- **검증 매트릭스**: 종이·순백·다크 × 1024px+·375px × ko/en
  - 스크린샷
  - 페이지 가로 넘침 0
  - 대비
  - 직접 클릭: 탭 비즈니스/리서치/주간 정리/전체, 검색("Gemini")과 지우기
  - 북마크 버튼이 보이는지(로그인 상태는 확인하지 않음)
- 전체 테스트를 기준선(PASS 70 / FAIL 23)과 이름으로 비교한다.
  - `list-rail-copy`·`list-meta-order`가 삭제되므로 FAIL은 21이 예상이다.
  - 신규 FAIL은 없어야 한다.

## 범위 밖

- 관리자 마스트헤드 문구 변경(Amy가 관리자 설정에서)
- 기사 상세 페이지
- 무한 스크롤·페이지네이션(현행 100편 창 유지)
