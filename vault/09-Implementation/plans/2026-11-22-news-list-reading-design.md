# 뉴스 목록 읽기 개선 (B 날짜를 왼쪽으로) — Design Spec

**Status:** design approved (2026-11-22), 구현 전
**Mockup:** `.superpowers/brainstorm/newslist2/news-list-reading-v1.html` (B안)
**관련:** [[2026-10-16-news-list-desks-design]], [[2026-11-21-news-article-reading-design]]

## 배경

- 2026-10-16에 뉴스 목록을 "두 데스크가 마주 보는 지면"으로 바꿨다([[2026-10-16-news-list-desks-design]]). 가운데 날짜 축 양쪽에 비즈니스·리서치 기사가 놓인다.
- 2026-11-22 운영 화면(`/ko/news/`)에서 잰 값이다.
  - **오른쪽 정렬**: 비즈니스 칸의 제목·요약·읽는 시간이 오른쪽 정렬이다. 두 줄 제목은 줄마다 시작 위치가 다르고, 북마크는 글에서 먼 왼쪽 끝에 있다.
  - **요약문**: 13.1px 한 줄 말줄임. `word-break: keep-all`이 없다.
  - **빈 칸**: 날짜 줄 56개 중 비즈니스 9개, 리서치 3개가 비어 있다. 최근 12줄 중에는 6줄이 "이날은 비즈니스 기사가 없어요"다. 한 달 전 설계는 하루 2편을 전제로 했다.
  - **길이**: 일간 100건과 주간 20건을 한 번에 그린다. 데스크톱 11,917px, 모바일 24,637px. 11.13 다음이 10.27인데 달이 바뀌는 표시가 없다.
  - **주간 정리 띠**: 검은 배경, 가운데 정렬, 178px.
  - **첫 기사 위치**: 데스크톱 507px, 모바일 467px. 마스트헤드 영역이 153px다.
  - 오늘 줄의 "토 · 제249호 · 오늘"이 92px 날짜 칸에서 "오/늘"로 끊긴다.
- 시안 A(두 데스크 다듬기) / B(날짜를 왼쪽으로) / C(최신호 크게 + 한 줄 목록) 중 **B**를 골랐다.
- 함께 정한 것
  - 머리 부분: 마스트헤드를 줄인다(없애지 않는다).
  - 길이: 최근 2주만 먼저 보이고 "더 보기"로 펼친다.

## 범위

- 대상: `/ko/news/`, `/en/news/`. 세 테마.
- 바꾸지 않는 것: 기사 상세, 홈, 용어집 목록, 검색 스크립트(`newsListSearch.ts`), 탭 컴포넌트(`NewsprintCategoryFilter`), 데이터 쿼리, `buildDeskRows`의 출력.
- 카드 계약은 그대로다: `.newsprint-card` + `data-category`·`data-post-type`·`data-post-id`·`data-search-text`, 북마크 버튼, `newsprint-card-stretched-link`.

## 목록 본문 (데스크톱 ≥768px, 데스크 모드)

1. **날짜 줄** `.news-desk-row`: `grid-template-columns: 96px minmax(0,1fr) minmax(0,1fr)`, 영역 `"date business research"`, 칸 사이 1.75rem. 모든 글이 왼쪽 정렬이다.
   - DOM 순서는 지금 그대로 날짜 → 비즈니스 → 리서치다. 이제 화면 순서와 같다.
   - 가운데 세로선과 오른쪽 정렬, `row-reverse`를 없앤다.
2. **한쪽만 있는 줄** `.news-desk-row--solo`: 비즈니스와 리서치 중 하나만 있을 때 붙는다.
   - 그 기사가 2~3번째 칸을 함께 쓴다(`grid-column: 2 / 4`, 최대 폭 47.5rem).
   - 빈 칸 문구(`.news-desk-empty`)는 더 렌더하지 않는다. 문구 문자열도 지운다.
   - 위치로 데스크를 알 수 없으므로 색 점 라벨(`.news-desk-label`)을 보이게 한다. 양쪽이 다 있는 줄은 지금처럼 라벨을 화면에서만 숨긴다.
   - 같은 날 두 번째 줄(`--cont`)도 한쪽만 있으면 같은 규칙이다.
3. **열 제목 줄**: 같은 3칸 격자. 첫 칸은 비우고, 두 제목 모두 왼쪽 정렬이다.
4. **날짜 칸**: 큰 날짜(Newsreader 500, 1.6rem), 그 아래 "요일 · 호수"(0.7rem, 줄바꿈 금지).
   - 오늘이면 날짜 숫자가 accent 색이고, "오늘"/"Today"를 따로 한 줄(`.news-desk-today`, accent 700)로 둔다.
5. **기사 칸**
   - 제목: Hahmlet 700, 1.19rem, 줄 간격 1.4. 오늘 줄은 1.4rem 유지.
   - 요약: 0.9rem, 줄 간격 1.65, 두 줄 말줄임, `word-break: keep-all`.
   - 북마크: 제목 오른쪽.
   - 읽는 시간: 그대로.

## 주간 정리와 달 구분

- **주간 정리** `.news-desk-weekly`: 배경을 없애고 위 2px·아래 1px `--color-text-primary` 선으로 구분한다. 격자 `96px minmax(0,1fr)`.
  - 첫 칸: "주간 정리"/"Weekly"(700)와 "11.15 · 제243호"(Newsreader, muted).
  - 둘째 칸: 기존 `NewsDeskCell`(제목, 북마크, 요약 한 줄, 읽는 시간). 칸 안의 점 라벨은 첫 칸과 겹치므로 화면에서만 숨긴다.
  - 다크 테마 전용 배경 규칙은 지운다.
- **달 구분선** `.news-desk-month`: 가장 최근 달을 뺀 각 달의 첫 항목 앞에 "2026년 10월"/"October 2026"과 가는 선을 둔다.

## 최근 2주 + 더 보기

- 새 순수 함수 `addListBreaks(entries)`를 `frontend/src/lib/newsDesks.js`에 둔다. `buildDeskRows`의 결과를 받아 달 구분 항목(`{kind:'month'}`)을 끼우고 각 항목에 `older`(boolean)를 붙인다.
  - "최근"의 경계는 작은 함수 `recentCutoff(days)` 하나가 정한다. 기본 제안은 **발행된 날 14개**(달력 14일이 아니다)다. 최종 기준은 구현 때 Amy가 정한다.
- `NewsDeskList`는 `older`인 항목에 `data-older="true"`를 붙이고, 목록 끝에 버튼을 둔다: "이전 기사 더 보기 N편" / "Show earlier stories N". N은 접힌 기사 수다. 접힌 것이 없으면 버튼을 렌더하지 않는다.
- 접기는 CSS다: `.news-desks[data-mode="desks"]:not([data-expanded="true"]) [data-older="true"] { display: none }`.
  - 기사는 지금처럼 모두 DOM에 있다. 검색어가 있거나 탭이 "전체"가 아니면 `data-mode="list"`가 되어 접기가 풀리고 전체에서 찾는다. 검색 스크립트는 바꾸지 않는다.
  - 목록 모드와 펼친 뒤에는 버튼을 숨긴다.
- 버튼 동작은 `newsDeskMode.ts`에 더한다.
  - 누르면 `data-expanded="true"`를 쓰고 `sessionStorage`(`news-list-expanded`)에 기억한다. 초기화할 때 값이 있으면 펼친 채로 시작한다(기사를 읽고 돌아왔을 때 위치를 잃지 않게).
  - 누른 뒤 포커스를 새로 보이는 첫 기사 링크로 옮긴다(버튼이 사라지므로).
  - `sessionStorage`를 못 쓰면 조용히 넘어간다.
- 자바스크립트가 꺼진 환경에서는 접힌 기사를 펼칠 수 없다. 검색과 탭도 같은 조건이므로 받아들인다. 링크는 DOM에 있어 검색 엔진에는 보인다.

## 머리 부분

- `NewsprintShell`에 선택 prop `tight`(기본 `false`)를 더한다. 켜면 `<header>`에 `newsprint-header--tight`가 붙는다.
  - 마스트헤드 글자: `clamp(2.2rem, 8vw, 4.5rem)` → `clamp(1.7rem, 4.4vw, 2.4rem)`. 위아래 여백도 줄인다.
- 뉴스 목록 두 페이지만 `tight`를 넘기고 `subkicker`는 넘기지 않는다. 보조 줄이 렌더되지 않는다.
  - 관리자 설정의 `news_subkicker` 값과 설정 항목은 그대로 둔다. 목록 페이지에서 읽지 않을 뿐이다.
- 호수·날짜 줄, 편집 노트, 검색창, 탭은 그대로다. 용어집 목록과 관리자 화면은 `tight`를 넘기지 않으므로 변화가 없다.

## 목록 모드와 모바일

- **목록 모드**(검색어가 있거나 탭이 "전체"가 아님): 지금처럼 한 단이다. 열 제목 줄, 달 구분선, 더 보기 버튼을 숨긴다. 라벨은 보인다.
- **모바일(<768px)**: 지금의 한 단 구조(날짜 → 기사, 왼쪽 2px 데스크 색 선)를 유지한다. 요약 두 줄, 가벼운 주간 정리, 달 구분선, 더 보기, 줄인 마스트헤드가 적용된다.

## 문구 (KO / EN)

| 위치 | KO | EN |
|---|---|---|
| 오늘 표시 | 오늘 | Today |
| 주간 정리 첫 칸 | 주간 정리 | Weekly |
| 달 구분선 | 2026년 10월 | October 2026 |
| 더 보기 버튼 | 이전 기사 더 보기 · N편 | Show earlier stories · N |

- 지우는 문구: "이날은 비즈니스 기사가 없어요", "이날은 리서치 기사가 없어요", "No business story this day", "No research story this day".

## 하지 않는 것

- 서버에서 기사를 나눠 보내거나(페이지네이션) 검색을 서버로 옮기지 않는다.
- 탭·검색창의 모양과 위치를 바꾸지 않는다.
- 새 색 토큰과 새 폰트를 추가하지 않는다.

## 테스트·확인

- 단위 테스트(`tests/news-desks-select.test.mjs`에 추가): `addListBreaks`의 달 구분 위치, `older` 경계, 달 구분 항목의 `older`, 빈 입력, 해가 바뀌는 경우. `monthLabel`의 KO/EN 형식.
- 구조 테스트(`tests/news-list-desks.test.cjs` 수정): 영역 순서 `"date business research"`, `--solo` 클래스, 빈 칸 문구와 다크 주간 규칙이 없음, 더 보기 버튼과 접기 규칙, `tight` prop, 요약문 `keep-all`.
- 그대로 통과해야 하는 것: `list-v2`, `news-search-list-structure`, `font-roles`, `retro-decoration-removed`, `handbook-term-entry`, `issue-number-shell`.
- 시작 전부터 실패하는 테스트 16개는 손대지 않는다(목록은 [[2026-11-21-news-article-reading]] 참조).
- `cd frontend && npm run build` 오류 0.
- 실제 화면: 데스크톱 1280과 모바일 390, 종이·다크 테마.
  - 한쪽만 있는 날이 넓게 나오고 라벨이 보인다. 양쪽 다 있는 날은 두 칸이다.
  - 더 보기를 누르면 나머지가 펼쳐지고, 기사에 들어갔다 돌아와도 펼친 상태다.
  - 검색어를 넣거나 탭을 바꾸면 접힌 기사까지 결과에 나온다.
  - 첫 기사 위치와 페이지 길이를 바꾸기 전과 비교해 적는다.

## 열린 항목

- "최근"의 최종 기준(위 "최근 2주 + 더 보기").
