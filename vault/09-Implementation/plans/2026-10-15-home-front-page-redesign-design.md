# 홈 1면 재설계 (A안) — Design Spec

**Status:** approved (2026-10-15)
**Mockup:** `.superpowers/brainstorm/home/home-v3.html` (A안)
**관련:** [[2026-10-14-site-redesign-soft-newsprint-design]], [[2026-10-14-homepage-front-strip]]

## 배경

Soft Newsprint V2 리디자인(1~8단계)을 마친 뒤에도 사이트의 전체 인상이 밋밋하다는 피드백이 나왔다.

- 1~8단계는 주로 장식을 걷어내는 작업이었고, 페이지 구도는 바꾸지 않았다.
- 홈의 첫 화면은 소개 문구와 버튼이 차지하고, 기사는 그 아래에 작게(제목 23px) 나온다.
- 기사에 이미지가 없으므로(`og_image_url` 전부 null), 무게는 글자 크기 대비와 구도로 만들어야 한다.

결정: **홈 첫 화면의 주인공을 오늘의 기사로 바꾸고, 진짜 신문 1면 구도로 다시 짠다.** 세 시안(A 신문 1면 / B 선언형 브랜드 / C 뉴스+학습 2단) 중 A를 골랐다.

## 화면 구성 (데스크톱, 위에서 아래로)

1. **헤더**: 현행 유지.
2. **마스트헤드**: "0to1log." — Newsreader 500, 약 76px, 가운데 정렬. 마침표만 accent 색.
   - 이 페이지의 유일한 `<h1>`이다. 텍스트는 "0to1log"이고 `aria-hidden`은 쓰지 않는다. 마침표는 `<span aria-hidden="true">`로 감싼다.
   - 제목 수준
     - 1면 제목: `<h2>`
     - 지난 지면 기사 제목, 용어명, 안내 제목: `<h3>`
     - "지난 지면"·"오늘의 용어" 같은 단 라벨: 시각적 라벨(`<p>`)로 둔다. 화면 낭독기를 위해 각 단을 `<section aria-label>`로 감싼다.
3. **날짜줄**: 위 2px `--color-text-primary`, 아래 1px 실선.
   - 왼쪽: 호수(`issueLabel`, 예: 제212호)
   - 가운데: KST 날짜(예: 2026년 10월 15일 목요일) · 모토("AI 뉴스와 용어를 기록하는 신문")
   - 오른쪽: "오늘 N건". 0건이면 생략한다.
4. **3단 지면**: 비율 1 : 2.1 : 1. 단 사이는 1px 세로선(`--color-border`)이다.
   - **가운데 — 1면**
     - 점 라벨: "오늘의 1면 · 비즈니스"
     - 제목: Hahmlet 700, 약 38px, `letter-spacing` -0.045em
     - 요약 문단(excerpt): 16px, 행간 1.7
     - 키워드 판(아래 규칙)
     - 메타 줄: "N분 · 같은 날 {postTypeLabel(sibling)}판: <짝 기사 링크>"
       - 라벨은 `postTypeLabel(locale, sibling.post_type)`에서 가져온다. 하드코딩하지 않는다.
       - `reading_time_min`이 null이면 "N분 ·"을 뺀다.
       - sibling이 없으면 짝 기사 부분을 뺀다.
       - 둘 다 없으면 메타 줄을 렌더하지 않는다.
     - 키워드 판과 메타 줄은 1면 `<article>` 안에 둔다.
   - **왼쪽 — 지난 지면**: 1면보다 이전 날짜의 기사 2건. 각 기사는 점 라벨 + 제목(Hahmlet 600, 18px) + 요약. 기사 사이는 점선으로 나눈다.
   - **오른쪽 — 오늘의 용어**
     - 큰 한글명(Hahmlet 700, 약 30px)과 영문명(Newsreader)
     - 정의
     - "풀이 읽기 →"
     - 그 아래 "뉴스 전체 보기 →"
5. **맨 아래 안내**: 1면 아래에 차분한 단락을 둔다.
   - 제목: "0to1log는 이런 곳이에요"
   - 본문: `home_intro`(관리자 편집). 없으면 현행 기본 문구를 쓴다.
   - 버튼 2개: "AI 뉴스 읽기 →"(먹색 기본 버튼), "용어집 보기"(보조).

## 키워드 판

- 먹색 면(`--color-text-primary` 배경, `--color-bg-primary` 글자)이다.
- 높이는 약 150px, radius 2px다.
- 오른쪽 위로 갈수록 진해지는 망점(radial-gradient) 패턴을 깐다.
- 왼쪽 위에 작은 글씨로 "오늘의 키워드"를 둔다.
- 페이지에서 먹색 블록은 이것 하나뿐이다.

**글자 선택 규칙** (`lead.tags`, 순서 그대로):

| 태그 수 | 작은 줄(위) | 큰 줄(Newsreader 500, 약 46px) |
|---|---|---|
| 2개 이상 | `tags[0]` | `tags[1]` |
| 1개 | 없음 | `tags[0]` |
| 0개 또는 null | 없음 | 1면 기사의 KST 날짜 "MM.DD" |

- 긴 태그는 줄바꿈을 허용한다. 큰 줄은 최대 2줄까지 보이고 넘치면 말줄임한다.
- 키워드 판은 장식이므로 링크가 아니다. 1면 제목 링크가 있으므로 따로 필요 없다.

## 데이터 규칙

쿼리 수는 현행과 같다(뉴스 1, 용어 count 1, 용어 1).

- 뉴스 쿼리 select에 `tags`를 추가한다. 최신 6건, 정렬은 현행(published_at desc, post_type asc) 그대로다.
- `selectFrontPage`를 확장한다. 순수 함수이고 `homeFront.js`에 둔다. 반환값은 다음과 같다.
  - `lead`: `news[0]`
  - `leadIsToday`: lead의 KST 날짜가 오늘인지
  - `sibling`: lead와 같은 KST 날짜이고 post_type이 다른 첫 기사. 없으면 null
  - `earlier`: lead보다 KST 날짜가 이른 기사 중 앞에서 2건
  - `todayCount`: 현행과 같다
  - `term`: 현행과 같다
  - `keyword`: `{ small: string|null, big: string }`. 위 표의 규칙을 따른다.
- 기존 반환 필드 `also`는 `sibling`으로 대체한다. 소비처는 `HomeFrontPage` 하나뿐이다.
- 1면 라벨
  - `leadIsToday`이면 "오늘의 1면 · {유형}"
  - 아니면 "최근 1면 · {M월 D일}". EN은 "Front page · {type}" / "Latest front page · {Mon D}".
- 뉴스가 0건이면(lead가 null)
  - 반환값: `keyword: null`, `sibling: null`, `earlier: []`, `leadIsToday: false`, `todayCount: 0`
  - 키워드 판은 렌더하지 않는다.
  - 1면·지난 지면 자리에 "아직 발행된 기사가 없어요"를 보여준다.
  - 마스트헤드, 날짜줄, 용어 단, 안내는 항상 렌더한다(기존 `(lead || term) &&` 래퍼 제거).
- 용어가 없으면 오른쪽 단에는 "뉴스 전체 보기 →"만 남긴다.

## 모바일 (≤767px)

- **DOM 순서 = 읽기 순서**: 1면 `<article>`(키워드 판·메타 줄 포함) → 오늘의 용어 → 지난 지면.
  - 데스크톱 3단 배치(지난 지면이 왼쪽)는 `grid-template-areas: "earlier lead term"`로 만든다.
  - 모바일은 영역 지정을 풀고 DOM 순서대로 한 단으로 쌓는다. `order`는 쓰지 않는다.
- 단 사이 세로선은 가로 점선으로 바꾼다.
- 크기
  - 마스트헤드: 약 48px
  - 날짜줄: 줄임형(호수 · "10월 15일 목" · 오늘 N건)
  - 1면 제목: 약 27px
  - 키워드 판: 높이 약 110px, 큰 줄 약 32px
- 페이지 가로 넘침은 0이어야 한다.

## 문구와 날짜 (KO / EN)

| 항목 | KO | EN |
|---|---|---|
| 모토 | AI 뉴스와 용어를 기록하는 신문 | A newspaper that keeps a record of AI news and terms (현행) |
| 1면 라벨 (오늘) | 오늘의 1면 · {유형} | Front page · {type} |
| 1면 라벨 (지난) | 최근 1면 · {M월 D일} | Latest front page · {Mon D} |
| 단 라벨 | 지난 지면 / 오늘의 용어 | Earlier pages / Term of the day |
| 키워드 판 라벨 | 오늘의 키워드 | Today's keyword |
| 메타 줄 | {N}분 · 같은 날 {유형}판: | {N} min · Same day, {type}: |
| 용어 링크 | 풀이 읽기 → | Read the explainer → |
| 전체 링크 | 뉴스 전체 보기 → | All news → |
| 빈 상태 | 아직 발행된 기사가 없어요 | No stories published yet |
| 오늘 건수 | 오늘 {N}건 | {N} today |
| 안내 제목 | 0to1log는 이런 곳이에요 | What 0to1log is |
| 안내 버튼 | AI 뉴스 읽기 → / 용어집 보기 | Read AI News → / Browse Glossary (현행) |

**날짜 형식** (모두 `timeZone: 'Asia/Seoul'`)
- 날짜줄(데스크톱): `{ year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }`
  - ko-KR: "2026년 10월 15일 목요일"
  - en-US: "Thursday, October 15, 2026"
- 날짜줄(모바일 줄임): `{ month: 'long', day: 'numeric', weekday: 'short' }`
  - "10월 15일 (목)" / "Thu, October 15"
  - 두 형식을 모두 렌더하고 CSS로 하나만 보이게 한다.
- 1면 지난 날짜: `{ month: 'long', day: 'numeric' }`. KO는 "10월 14일", EN은 `{ month: 'short', day: 'numeric' }`로 "Oct 14".
- 키워드 판 대체값 "MM.DD": 두 로케일 같은 형식이다. `kstDay(lead.published_at)`의 월·일을 쓴다.

## 컴포넌트

- `HomeFrontPage.astro`: 마스트헤드, 날짜줄, 3단 지면으로 다시 쓴다.
- `HomeSplitHero.astro`는 삭제하고 새 `HomeIntro.astro`를 만든다(맨 아래 안내 구역).
  - 클래스 접두사는 `.home-intro-*`
  - props: `locale`, `homeIntro`
- 함께 지우는 것
  - HomeSplitHero의 번들 `<script>`(타이프라이터/회전 단어)
  - `global.css`의 `.home-split-hero*` 규칙 전부(639px에서 `.home-split-hero-sub`를 숨기던 규칙 포함)
  - `.home-type-*` 규칙
  - 그 밖에 HomeSplitHero에서만 쓰던 규칙
- 호수·날짜·오늘 건수는 이제 `HomeFrontPage`의 날짜줄이 표시한다. index는 `todayCount`를 HomeIntro에 넘기지 않는다.
- `ko/index.astro`, `en/index.astro`: 순서를 `HomeFrontPage` → `HomeIntro`로 바꾼다.
- 1면 CSS는 `.home-front-*`로 둔다. 쓰이지 않게 된 기존 `.home-front-*` 규칙은 삭제한다.

## 유지할 것

- 공개 페이지는 CDN에 캐시되므로 SSR 출력은 사용자 정보와 무관해야 한다. `Astro.locals.user`를 쓰지 않는다.
- 헤더, 테마 3종(종이·순백·다크), 글꼴 역할, 점 라벨 규칙, `issue.js`, `postType.js`
- 모든 `<script is:inline>`에 nonce를 붙인다. 새 인라인 스크립트는 필요 없을 것으로 본다.

## 테스트

- `home-front-select.test.mjs` 확장:
  - lead, leadIsToday, sibling, earlier 선택
  - keyword 규칙 3가지(태그 2개 이상, 1개, 없음)
  - 뉴스 0건
- `home-front-query-budget`: 쿼리 수가 그대로인지 확인한다(tags 추가만 허용).
- 구조 테스트는 새 구조에 맞게 갱신한다.
  - **`home-front-page.test.cjs`** 에서 삭제·대체할 단언
    - `(lead || term) &&` 래퍼 → 마스트헤드·날짜줄이 항상 렌더되는지로 대체
    - hero가 `todayCount={front.todayCount}`를 받는지 → 날짜줄의 오늘 건수로 대체
    - "오늘의 1면 / Today's front page" 섹션 제목 → 1면 라벨 규칙(오늘/최근)으로 대체
  - **`home-hero-v2.test.cjs`, `home-hero-copy.test.cjs`** — 단언마다 옮길 곳이 다르다.
    - 주의: `home-hero-v2`는 파일 맨 위에서 `HomeSplitHero.astro`를 읽는다. 이 읽기를 `HomeFrontPage`/`HomeIntro`로 바꾸지 않으면 단언이 하나도 실행되기 전에 ENOENT로 멈춘다.
    - **`HomeFrontPage.astro` / `.home-front-*`로 옮긴다**
      - 워드마크 정규식. 이제 h1이므로 새 마크업 클래스에 맞게 다시 쓴다.
      - KO 모토
      - `issue.js` 사용
      - `todayCount?: number` prop
      - `todayCount > 0` 가드
      - 호수 표시 요소(날짜줄)
    - **삭제한다**
      - 헤드라인 배열 단언(`home-hero-copy`)
      - `.home-split-hero-headline`, `.home-split-hero-wordmark`, `.home-split-hero`, `.home-type-target` CSS 규칙 단언
      - 639px sub-hide 단언. 안내 본문은 모바일에서도 보여야 한다.
    - **새로 단언한다**
      - 소스와 CSS 어디에도 `data-type-words`, `.home-type-*`, `home-split-hero`가 없는지
      - `HomeIntro.astro`가 `homeIntro`를 렌더하는지, 버튼 2개가 있는지
    - **그대로 둔다**: `ko/index.astro`·`en/index.astro`의 intro 문구 단언, 관리자 설정 동기화 단언
  - 새로 단언할 것
    - h1이 하나뿐이고 그것이 마스트헤드인지
    - grid-template-areas
    - 키워드 판
    - `postTypeLabel` 사용
    - EN 문구
- 검증 매트릭스: 종이·순백·다크 × 데스크톱(≥1024px)·모바일(375px)
  - 브라우저 스크린샷
  - 페이지 가로 넘침 0
  - 대비 검사
- 전체 테스트를 기준선(PASS 70 / FAIL 23)과 이름으로 비교한다. 신규 실패는 없어야 한다.

## 범위 밖

- 관리자 "1면 키워드" 입력 칸(키워드 판 ③안) — 필요하면 나중에
- 홈 외 페이지 구도 재설계 — 홈 결과를 보고 결정
- 뉴스 이미지·썸네일 도입
