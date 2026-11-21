# 뉴스 기사 본문 읽기 개선 (B 머리 정리 + 기사형 본문) — Design Spec

**Status:** design approved (2026-11-21), 구현 전
**Mockup:** `.superpowers/brainstorm/article2/article-reading-v1.html` (B안)
**관련:** [[2026-10-16-news-article-briefing-design]], [[2026-10-14-site-redesign-soft-newsprint-design]]

## 배경

- 2026-10-17에 기사 상세를 "브리핑 먼저 + 짝 기사"로 바꿨다([[2026-10-16-news-article-briefing-design]]). 구조는 자리를 잡았지만 읽는 경험에 문제가 남아 있다.
- 2026-11-21 운영 화면(`/ko/news/2026-11-21-business-digest-ko/`)에서 잰 값이다.
  - **단어 중간 줄바꿈**: `.newsprint-prose`와 `.newsprint-deck`에 `word-break: keep-all`이 없다. "가/격에", "17/일", "요/청할"처럼 끊긴다. 제목에는 이미 있다.
  - **깨진 굵은 글씨**: 본문에 `**`가 그대로 보인다(`**46%인 반면, … 성공률은25%**`). 닫는 `**` 앞이 문장부호이고 뒤가 한글이면 CommonMark가 강조의 끝으로 보지 않는다.
  - **굵은 글씨 과다**: 본문 2,919자 중 414자(14%)가 굵다. 문장이 통째로 굵다. 프롬프트는 이미 "핵심 용어·회사·숫자만 굵게"라고 지시한다(`prompts_news_pipeline.py:473`).
  - **본문 시작 위치**: 데스크톱 820px, 모바일(390×844) 974px. 경로 줄, 킥커 줄, 제목, 요약문, 태그, 짝 기사, 판 선택, 브리핑이 쌓여 있다. 날짜와 "AI 뉴스"가 두 번씩 나온다.
  - **크기 위계**: 요약문 21.6px, 분류 h2("Big Tech") 23.2px, 실제 기사 제목 h3 17.9px, 본문 16px, 브리핑 14px 회색. 분류가 기사 제목보다 크고, 가장 중요한 브리핑이 가장 작다.
  - **소제목 간격**: h3 아래 6.4px라 제목과 본문이 붙어 보인다.
  - **떠 있는 막대**: 판 선택 막대(`#persona-float`)가 본문 마지막 줄을 가린다. 모바일은 위 검색창, 아래 판 선택 막대, 하단 액션 바가 동시에 떠 있다.
- 시안 A(조판만 수리) / B(머리 정리 + 기사형 본문) / C(여백 주석 지면) 중 **B**를 골랐다.
- 함께 정한 것
  - 굵은 글씨는 **화면에서 정리**한다. 프롬프트와 DB 원문은 건드리지 않는다.
  - 떠 있는 막대는 **내려 읽을 때 숨기고 올릴 때 보인다**.

## 범위

- 대상: 공개 뉴스 기사 상세 `/ko/news/[slug]/`, `/en/news/[slug]/`. 일간(비즈니스·리서치)과 주간, 세 테마(light·white·dark), 세 판(입문·학습·전문) 모두.
- `NewsprintArticleLayout`은 관리자 뉴스·블로그 편집 미리보기도 쓴다. 그래서 바뀌는 것은 모두 새 prop `newsReading`(기본 `false`)으로 켠다.
  - 공개 뉴스 페이지 두 곳만 `newsReading`을 넘긴다.
  - 레이아웃은 `newsReading`일 때 루트 `<article>`에 `newsprint-article--news` 클래스를 붙인다.
  - 새 CSS의 범위 선택자는 두 가지다. 기사 안의 요소는 `.newsprint-article--news …`, 기사 밖에 렌더되는 요소(경로 줄, 모바일 검색창)는 `body:has(.newsprint-article--news) …`.
- `.newsprint-main--article`은 용어집 상세도 쓰므로 범위 선택자로 쓰지 않는다.
- 관리자 뉴스 편집의 보이는 미리보기는 공개 페이지를 `?preview=1`로 불러오는 iframe이라 새 모양이 그대로 나온다. 같은 페이지의 숨겨진 레이아웃 인스턴스(`display:none`)와 관리자 블로그 편집은 `newsReading`을 넘기지 않으므로 변화가 없다.

## 머리 부분 (위에서 아래로)

1. **메타 한 줄**: `NewsprintShell`의 compact 경로 줄(`.newsprint-crumb`)을 넓혀 쓴다.
   - 내용: `← AI 뉴스 · 비즈니스 데스크 · 제249호 · 2026년 11월 21일 · 읽는 데 9분`
   - Shell에 선택 prop 두 개를 더한다: 데스크 라벨(강조색 600)과 읽는 시간. 둘 다 완성된 문자열로 받는다. 둘 다 없으면 지금과 같게 렌더한다(용어집 상세는 변화 없음).
   - 문자열은 뉴스 페이지가 만든다. `postTypeLabel`은 "비즈니스"/"Business"만 돌려주므로, 비즈니스·리서치에는 페이지가 " 데스크"/" desk"를 붙이고 주간 정리는 그대로 쓴다.
   - Shell의 기존 식 `{crumbItems ? (`와 `issueLabel(locale, issueNumber(displayDate))`는 문자열 그대로 남긴다. `handbook-term-entry`, `issue-number-shell` 테스트가 이 문자열을 단정한다.
   - 날짜는 기존 `data-local-date` 메커니즘과 형식을 그대로 쓴다. 시안의 "11월 21일 토요일" 형식으로 바꾸지 않는다.
   - `newsReading`일 때 레이아웃의 `.newsprint-article-topline`(킥커, 읽는 시간, 날짜)은 렌더하지 않는다.
   - 좁은 화면에서는 줄바꿈된다(`flex-wrap`).
2. **제목** `.newsprint-lead-title`: 크기 유지. 아래 간격 0.45rem → 0.85rem.
3. **요약문** `.newsprint-deck`: 18px(1.125rem) 고정, 줄 간격 1.65, `word-break: keep-all`, 최대 폭 40rem.
4. **판·짝 기사 줄** `.news-edition-bar`(새 래퍼): 위 2px `--color-text-primary` 선, 아래 1px `--color-border` 선.
   - 왼쪽: 판 선택. `.switcher-bar`, `.persona-switcher`, `.persona-switcher-btn(--active)`, `data-persona`, `<template id="persona-data">`는 그대로 둔다. 모양만 세그먼트 버튼으로 바꾼다(활성: 배경 `--color-text-primary`, 글자 `--color-bg-primary`).
   - "판 선택" 라벨은 화면에서만 숨긴다(sr-only). 양쪽 장식선 `.switcher-bar-line`은 `newsReading`일 때 렌더하지 않는다.
   - 오른쪽: 짝 기사 링크 `.newsprint-twin-link`. 한 줄로 줄이고 넘치면 말줄임한다. 데스크 색은 라벨 글자에만 쓴다(왼쪽 2px 선 제거).
   - sibling이 없으면 판 선택만, 판이 하나뿐이면 짝 기사만 렌더한다. 둘 다 없으면 줄 전체를 렌더하지 않는다.
5. **30초 브리핑** `.news-briefing`: 배경 상자를 없애고 세로 번호 목록으로 바꾼다.
   - 번호: Newsreader 500, 1.3rem, accent. 문장: 본문과 같은 크기와 색, `keep-all`.
   - 아래에 1px 선을 긋고 다음 블록과 30px 띄운다.
   - 브리핑 다음 순서는 지금 그대로다: 기사 안 찾기(find bar) → Fact Pack → Core Analysis → 본문.
6. **없애는 것**(`newsReading`일 때): 제목 아래 `.newsprint-divider`, 머리의 태그 줄.
7. **태그**는 기사 끝으로 옮긴다: `after-guide` 슬롯 다음, 출처 앞. 마크업과 클래스(`.newsprint-article-tags`)는 그대로다.

## 본문 조판 (`.newsprint-article--news .newsprint-prose`)

| 요소 | 지금 | 바뀐 값 |
|---|---|---|
| 본문 | 16px / 1.8 | 17px(1.0625rem) / 1.85 |
| 줄바꿈 | 글자 단위 | `word-break: keep-all; overflow-wrap: break-word` |
| 문단 간격 | 0.95rem | 1.1rem |
| 분류 h2 (바로 뒤에 h3) | Hahmlet 23.2px + 윗선 | Pretendard 700, 0.78rem, 자간 0.08em, accent, 오른쪽으로 이어지는 1px 선. 위 2.9rem |
| 그 밖의 h2 | 23.2px + 윗선 | 크기 유지, 아래 0.75rem |
| 첫 h2 (`> h2:first-child`) | 23.2px | 작은 라벨(muted, 0.78rem 700) |
| 첫 h2 바로 다음 문단 | 본문 | Hahmlet 600, 1.22rem, 줄 간격 1.6 |
| 기사 제목 h3 | 17.9px 600 + 왼쪽 3px 막대 | Hahmlet 700, clamp(1.25rem, 1.8vw, 1.44rem), 줄 간격 1.4, 막대 없음, 위 0.9rem · 아래 0.9rem |
| strong | 700 | 600 |

- 분류 h2는 `h2:has(+ h3)`로 고른다. 마크업과 파이프라인 출력은 바꾸지 않는다.
- 분류 h2 바로 다음 h3는 위 간격을 줄여 꼬리표와 한 묶음으로 보이게 한다.
- 폭 `max-width: 42rem`은 그대로다.
- Core Analysis의 `.newsprint-prose--analysis`에도 글자 크기·줄바꿈·strong·제목(h2, h3) 규칙을 똑같이 적용한다. 한 기사 안에서 제목 모양이 둘로 갈리지 않게 하기 위해서다. 첫 h2 라벨과 첫 문단 세리프 처리만 본문 prose(`:not(.newsprint-prose--analysis)`)에 한정한다.
- 기사 제목 h3의 위 간격은 분류 h2 바로 다음일 때 0.9rem, 같은 분류 안의 두 번째 소식부터는 2rem이다.
- 판 전환은 `.newsprint-prose`의 내용을 바꿔 끼우므로 CSS만으로 세 판에 모두 적용된다.

## 굵은 글씨 정리

- 새 순수 함수 `normalizeNewsBold(md)`를 `frontend/src/lib/newsBold.js`에 둔다(`lib/newsDesks.js`와 같은 형식, `.mjs` 단위 테스트).
- 호출 위치: `lib/pageData/newsDetailPage.ts`의 `renderMd`에 넘기기 직전. 본문과 세 판 모두 같은 경로를 지난다.
  - `lib/markdown.ts`의 공용 렌더러는 바꾸지 않는다(블로그·제품·용어집·관리자 미리보기 영향 없음).
  - 렌더 캐시 키는 입력 문자열의 해시라 따로 손댈 필요가 없다.
- 규칙
  - 줄 단위로 처리한다. 코드 펜스(```` ``` ````, `~~~`) 안, 인라인 코드 안, `$$…$$` 수식 안은 건드리지 않는다.
  - 한 줄에서 `**`를 왼쪽부터 짝짓는다. 짝이 없는 `**`와 `***…***`는 그대로 둔다.
  - 안쪽이 통째로 링크(`**[라벨](URL)**`)면 그대로 둔다.
  - **목록 라벨은 길이와 상관없이 굵게 남긴다.** 목록 항목 맨 앞의 굵은 글씨 바로 뒤에 `:` 또는 ` —`가 오는 경우다(`- **조건이라면**: …`, `- **46%** — …`). "전략 판단" 목록에서 한 항목만 굵기가 풀리는 일을 막는다.
  - 안쪽이 **길면** `**`를 떼고 보통 글씨로 내보낸다.
  - 안쪽이 **짧으면** `<strong>…</strong>`로 내보낸다. 파서의 flanking 규칙을 거치지 않으므로 한글이 붙어 깨지던 경우가 함께 해결된다. `rehypeRaw`와 sanitize 스키마가 `strong`을 이미 허용한다.
- **"길다"의 기준**은 함수 안의 작은 판정 함수 하나로 분리한다. 기본 제안은 "공백 포함 24자 초과이거나 문장 끝(`.` `?` `!`)으로 끝남"이다. 최종 규칙은 구현 때 Amy가 정한다.

## 떠 있는 막대

- **새 스크립트를 만들지 않는다.** 헤더가 이미 스크롤 방향을 추적한다(`Navigation.astro`, 5px 기준). 내려가는 동안 헤더에 `site-header--fixed site-header--hidden`이 붙고, 올리면 `--hidden`이 빠진다. 이 상태를 CSS로 읽는다.
  - "내려 읽는 중" = `body:has(.site-header--fixed.site-header--hidden)`
- 내려 읽는 중에 바뀌는 것
  - **판 선택 막대** `.newsprint-article--news .persona-float`: 숨긴다(opacity 0, `pointer-events: none`, 살짝 이동).
    - 키보드 포커스가 막대 안에 있으면 숨기지 않는다. `:has(:focus-visible)`로 판정한다. `:focus-within`은 쓰지 않는다. 마우스로 판을 누른 뒤에도 버튼에 포커스가 남아 막대가 계속 떠 있게 되기 때문이다.
  - **모바일 검색창** `body:has(.newsprint-article--news) .handbook-search-sticky--detail`: 투명하게 만들지 않고 `position: static`으로 바꿔 화면에 붙지 않게 한다.
    - 헤더는 스크롤이 헤더 높이를 넘는 순간 방향과 상관없이 숨김 상태가 된다. 그때 검색창은 아직 경로 줄 아래 제자리에 보인다. 투명하게 만들면 기사 맨 위에 빈 칸이 생긴다.
    - `static`과 `sticky`는 차지하는 자리가 같아서 레이아웃이 움직이지 않는다. 올리면 다시 `sticky`가 되어 헤더 아래에 나타난다.
    - 입력 중(`:focus-within`)에는 `sticky`를 유지한다.
- 헤더의 판정을 그대로 물려받는다: 아주 느린 스크롤(프레임당 5px 이하)에서는 상태가 바뀌지 않고, 문서 맨 끝에서 막대를 다시 띄우는 처리는 없다. 둘 다 받아들인다.
- 새 규칙은 `body:has(…)` 접두를 유지해 기존 `.persona-float--back` 규칙(0,3,1)보다 명시도가 높아야 한다.
- 기존 표시 조건은 그대로 겹쳐진다: 판 선택 막대는 `.persona-float--visible`일 때만, 검색창은 `data-hidden-by-find`가 없을 때만 보인다.
- **판이 하나뿐인 기사의 `.persona-float--back`**(목록으로 돌아가기)은 지금 반대로 동작한다: 내려갈 때만 보인다(`global.css`의 `body:has(…--hidden) .persona-float--back`). 뉴스 기사에서는 이것도 뒤집어, 올릴 때(`.site-header--fixed:not(.site-header--hidden)`) 보이고 내려갈 때 숨긴다. 기존 규칙보다 명시도가 높은 선택자로 덮어쓴다.
- 용어집 상세는 같은 클래스를 쓰지만 `.newsprint-article--news`가 없으므로 지금 동작 그대로다.
- `prefers-reduced-motion`에서는 전환 없이 바로 바뀐다.
- 모바일 하단 액션 바와 데스크톱 세로 액션 막대는 바꾸지 않는다.

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| 메타 줄 데스크 | 비즈니스 데스크 / 리서치 데스크 / 주간 정리 | Business desk / Research desk / Weekly |
| 메타 줄 읽는 시간 | 읽는 데 N분 | N min read |
| 짝 기사 라벨 | 리서치 데스크의 시선 → / 비즈니스 데스크의 시선 → | The research desk's take → / The business desk's take → |

- 30초 브리핑, 판 이름은 지금 문구 그대로다.

## 모바일 (<768px)

- 메타 줄은 줄바꿈된다. 판·짝 기사 줄은 두 줄로 쌓인다(판 선택이 전체 폭, 짝 기사가 그 아래).
- 본문 17px, 기사 제목 h3 1.25rem. 좌우 여백은 지금 그대로다.
- 목표: 본문 시작 위치가 974px에서 844px(한 화면) 안으로 들어온다.

## 하지 않는 것

- 관리자 블로그 편집 미리보기에는 적용하지 않는다(`newsReading` 미전달).
- 용어집·블로그 본문의 `keep-all` 적용, 뉴스 목록의 오른쪽 정렬·빈 칸·"오/늘" 줄바꿈은 이번 범위가 아니다.
- 프롬프트의 굵은 글씨 규칙, DB에 저장된 원문은 바꾸지 않는다.
- 새 색 토큰과 새 폰트를 추가하지 않는다. Hahmlet은 지금 불러오는 600·700만 쓴다.

## 테스트·확인

- 단위 테스트 `tests/news-bold-normalize.test.mjs`
  - 한글이 붙은 닫는 `**`(`**46%**다`), 긴 문장 굵기 해제, 짧은 용어 유지, 링크 굵기 유지, 목록 라벨 유지(긴 라벨 포함), 코드 펜스·인라인 코드·`$$` 수식 보존, 짝 없는 `**`와 `***` 보존, 주간 숫자 목록 유지.
- 구조 테스트 `tests/news-article-reading.test.cjs`(새 파일)
  - 공개 뉴스 페이지 두 곳이 `newsReading`을 넘긴다. 관리자 편집 페이지는 넘기지 않는다.
  - 레이아웃: `newsprint-article--news`, `.news-edition-bar`, 태그가 `after-guide` 뒤에 있다.
  - CSS: `.newsprint-article--news .newsprint-prose`에 `keep-all`이 있고, 헤더 숨김 상태에서 `.persona-float`와 검색창을 숨기는 규칙이 있다.
- 기존 테스트
  - 새 구조에 맞게 고친다: `news-article-briefing`(순서와 짝 기사 문구를 단정한다). `news-persona-title-switcher`, `news-article-find-structure`, `article-v2`, `sticky-reading-actions-structure`는 돌려 보고 깨지는 것만 고친다.
  - 그대로 통과해야 한다: `handbook-term-entry`, `issue-number-shell`(Shell 문자열 단정).
  - 지금도 실패하는 테스트가 16개 있다(`article-deck-font`, `sticky-reading-actions-structure`, `news-fact-pack-structure` 등, 목록은 구현 계획 참조). 이번에 손대지 않는다.
- 테스트는 npm 스크립트 없이 파일을 하나씩 `node`로 실행한다. 파일마다 기준 경로가 다르므로(`__dirname` 또는 저장소 루트) 실행 위치는 구현 계획에서 파일별로 적는다.
- `cd frontend && npm run build`가 오류 0으로 통과한다.
- 실제 화면 확인: 일간 비즈니스·리서치 기사 각 1건과 주간 정리 1건을 데스크톱(1280)과 모바일(390), 세 테마, 세 판에서 본다.
  - 단어 중간 줄바꿈과 `**` 노출이 없다.
  - 판을 바꿔도 제목·요약문·본문·퀴즈가 지금처럼 바뀐다.
  - 내려 읽을 때 막대가 숨고, 올리면 돌아온다. 키보드 포커스가 막대 안에 있으면 숨지 않는다. 마우스로 판을 바꾼 뒤에는 다시 숨는다.
  - 모바일에서 기사 맨 위를 조금 내렸을 때 검색창 자리에 빈 칸이 생기지 않는다.
  - 주간 정리와 전문판처럼 첫 섹션이 "한 줄 요약"이 아닌 글에서 첫 문단의 세리프 처리가 어색하지 않은지 본다. 어색하면 그 처리를 일간 기사로 한정한다.

## 열린 항목

- "긴 굵은 글씨"의 최종 판정 규칙(위 "굵은 글씨 정리").
- 인용 번호(`[1]`)가 줄 맨 앞에 혼자 떨어지는 경우가 있다. 이번에는 다루지 않고, 구현 뒤 화면에서 눈에 띄면 따로 정한다.
