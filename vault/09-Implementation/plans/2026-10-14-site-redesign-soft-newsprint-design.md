---
title: 사이트 리디자인 — Soft Newsprint (V2)
date: 2026-10-14
status: design-approved
tags: [design, frontend, redesign, theme]
---

# 사이트 리디자인 — Soft Newsprint (V2)

## 1. 배경과 목표

현재 공개 사이트는 "레트로 신문" 컨셉인데, 실제 신문처럼 보이지 않고 레트로 테마를 덧입힌 것처럼 보인다. 원인은 네 가지다.

- 모든 글꼴 역할이 Lora(책 본문용 세리프) 하나로 몰려 있다.
- 기본 테마가 갈색 다크(`dark`, #171311)다.
- 이중선, 드롭캡, 노이즈가 구조 없이 장식으로만 얹혀 있다.
- 전반적으로 무겁고 딱딱하다.

**목표:** 신문의 *구조*(선, 점, 망점, 단 구성, 호수)는 살리고 무게는 빼서 **"부드러운 신문"**으로 다시 만든다.

### 결정 과정 요약 (브레인스토밍, 2026-10-14)

| 라운드 | 보여준 것 | 반응 |
|---|---|---|
| 1 | 모던 에디토리얼, 테크 미니멀, 학습 노트, 대담한 매거진 | 테크는 "AI 티", 학습 노트는 별로 |
| 2 | 스위스, 리서치 저널, 아카이브, 한국 독립 매거진 | 모두 별로 |
| 취향 테스트 | 한 번에 변수 하나씩 비교 | 밝은 바탕 · 명조 제목 · 여유 · 색은 풍부와 절제 사이 · 진지 |
| 팔레트 | 웜 / 쿨 / 내추럴 | 쿨(② 순백+잉크 블루)과 웜(① 크림+테라코타) 모두 OK |
| 레트로 신문 | 1930 브로드시트, 1960 한국 일간지, 미드센추리 | 브로드시트 OK. 그러나 "고집인가?" 하는 의문 |
| 브로드시트 실화면 | 홈, 모바일, 기사 | 블랙레터 제호가 과하고, 너무 레트로하고 딱딱함. **선과 점은 좋음** |
| 힘 빼기 | V1 신문 80% / **V2 신문 55%, 점 모티프** / V3 신문 30% | **V2 채택** |
| 테마 | V2 × 종이 / 화이트 / 다크 | 세 가지 모두 유지 |

**교훈:** 사용자는 레퍼런스가 없을 때 완성 시안 비교보다 *단일 변수 비교*(취향 테스트)에 더 명확하게 반응했다. 신문 컨셉 자체가 문제가 아니라 *강도*가 문제였다.

## 2. 디자인 원칙

1. **1면은 신문답게, 본문은 읽기 편하게.** 신문 장치는 홈, 목록, 기사 머리에 집중한다. 기사 본문은 1단으로 읽기 편하게 둔다.
2. **점과 선에는 의미가 하나씩만 있다.** 아래 표에 없는 용도로는 쓰지 않는다.

   | 요소 | 의미 | 예시 |
   |---|---|---|
   | 실점 ● (`--acc`) | 지금 위치 · 카테고리 | 현재 메뉴 아래 점, 카테고리 라벨 앞 점, TOC 현재 항목, 제호 마침표 |
   | 점선 (dotted) | 항목 구분 | 목록 항목 사이, 출처 목록, 핵심 정리 항목 사이 |
   | 점 줄 (dot rule) | 제호 아래 구분 | 헤더의 점 패턴 줄 |
   | 실선 1px | 구조 경계 | 메뉴 아래, 바이라인 위 |
   | 망점 (halftone) | 사진 | 뉴스 썸네일과 히어로 이미지 |

3. **장식은 아껴 쓴다.** 다음은 쓰지 않는다: 블랙레터, 이중선, 겹테두리 박스, 대문자 small-caps 라벨, 페이지 전체 노이즈, 본문 양쪽 정렬.

## 3. 테마 (3개)

| key | 이름 | bg | ink | accent | 비고 |
|---|---|---|---|---|---|
| `light` | 종이 (**기본**) | #F7F4EE | #24211D | #C2502F 주황 | 기존 `light` 키를 재사용한다 |
| `white` | 화이트 | #FFFFFF | #16181B | #2448A8 잉크 블루 | 신규 |
| `dark` | 다크 | #181715 | #ECE7DD | #E3774F 밝은 주황 | 기존 `dark` 값을 교체한다 |

- 보조 토큰: `--sub`, `--body`, `--mute`, `--line`, `--dotline`, `--surf`. 시안 값은 `.superpowers/brainstorm/3462-*/v2-themes.html`에 있다.
- 기존 토큰 이름(`--color-bg-primary`, `--color-text-*`, `--color-accent`, `--color-border` 등)은 **유지하고 값만 교체**한다. `src` 전체에서 `var(--color-*)` 사용처가 약 2,000곳이라, 이름을 유지하면 사이트 대부분이 자동으로 따라온다.
- **기존 테마 정리:** `global.css`에서 `pink`, `midnight` 토큰 블록을 삭제한다. 테마별 오버라이드 셀렉터도 함께 정리한다(`[data-theme="pink"|"midnight"|"light"] …`, 예: `.newsprint-type-badge--*` 760–775행).
- **카테고리 색 (`--color-cat-*`):** 토큰은 유지하고 세 테마 모두 값을 `--color-accent`와 같게 둔다. 사용처를 건드리지 않고 "accent 하나로 통일"(§5)을 달성하기 위해서다. 토큰 자체 삭제는 페이지별 단계에서 사용처를 정리하면서 한다.
- **코드 블록 색 (Shiki `--shiki-*`):** `light`와 `white`는 같은 라이트 코드 팔레트를 공유한다(현재 `light` 값 기준으로 새 배경 대비 확인). `dark`는 현재 dark Shiki 값을 유지하고 새 배경 #181715에서 대비만 확인한다. KaTeX는 `currentColor`를 상속하므로 별도 작업이 없다(1단계 검증에서 확인).

#### 테마 로직 단일화 (중요)
현재 테마 이름, 색 맵, 순환 순서가 **8개 파일에 각자 하드코딩**되어 있다.
- `MainLayout.astro`: FOUC 스크립트, after-swap 핸들러
- `ThemeToggle.astro`: dark/light/pink만 순환
- `Navigation.astro:384`: dark/light/pink/midnight, 아이콘, `data-*-label`
- `admin/AdminSidebar.astro:256`
- `pages/auth/callback.astro`: 인라인 pink/midnight CSS
- `pages/preview/newsprint-{dark,light,pink}.astro`

→ **`src/lib/theme.ts` 하나로 모은다.** 담을 것은 다음과 같다.
- `THEMES = ['light','white','dark']`, `DEFAULT_THEME = 'light'`
- `THEME_COLORS`: theme-color 메타용
- `COLOR_SCHEME`: light/white → light, dark → dark
- `LEGACY_MAP = { pink:'light', midnight:'dark' }`
- `normalizeTheme(v)`: legacy 값은 매핑하고, 알 수 없는 값이나 null은 null을 반환한다(호출부에서 OS 기준 기본값 적용).
- `applyTheme(theme)`: `data-theme`, `colorScheme`, theme-color 메타를 **함께** 설정하고 localStorage에 저장한다.

인라인 스크립트(MainLayout의 FOUC와 after-swap, `auth/callback.astro`의 인라인 스크립트)는 모듈을 import할 수 없다. 그래서 같은 상수를 `define:vars`로 주입하거나 빌드 시 문자열로 삽입하고, 값의 출처는 `theme.ts` 하나로 유지한다. after-swap 핸들러도 `applyTheme`과 같은 처리(colorScheme, theme-color 포함)를 한다. Navigation, ThemeToggle, AdminSidebar는 모두 `theme.ts`를 사용한다.

- **기본값과 fallback:** 저장값이 없거나 알 수 없는 값이면, OS가 다크 모드일 때 `dark`, 아니면 `light`. 현재 컴포넌트들의 `'dark'` fallback을 모두 이 규칙으로 바꾼다.
- **토글 순서:** `light → white → dark` (공개 사이트와 관리자 동일).
- **i18n:** `themePink`, `themeMidnight` 키를 삭제하고 `themeWhite`를 추가한다(라벨: 종이 / 화이트 / 다크, EN: Paper / White / Dark).
- **preview 페이지:** `preview/newsprint-pink.astro`는 localStorage에 `pink`를 다시 써넣으므로 **1단계에서 삭제**한다. dark/light preview도 1단계에서 삭제하거나 새 테마로 교체한다.
- **망점 사진의 다크 처리:** 다크 테마에서는 망점을 반전(`invert` + `screen` 블렌드)해 밝은 점으로 보이게 한다.

## 4. 타이포그래피

| 역할 | 글꼴 | 비고 |
|---|---|---|
| 제호 (masthead) | Newsreader 500 | `0to1log` + 주황 마침표. `font-variant-numeric: lining-nums` 필수 (아래 참고) |
| 제목 · 헤드라인 · 용어명 · 핵심 정리 claim | **Hahmlet** 600 | 한글 명조. `word-break: keep-all`, `text-wrap: balance` |
| 본문 · UI · 메타 | **Pretendard** 400–700 | 기존 CDN 그대로 사용 |
| 코드 | JetBrains Mono | 기존 그대로 |

- **lining-nums가 필요한 이유:** old-style 숫자에서는 "0to1"이 "oto1"로 보인다. 시안에서 실제로 발견한 문제다.
- **역할 토큰 재분리:** 현재는 `--font-*`가 전부 Lora로 몰려 있다. 위 표대로 다시 나눈다.
  - `--font-masthead` → `'Newsreader', 'Hahmlet', serif`
  - `--font-blog-masthead` → `'Hahmlet', serif`. 블로그 마스트헤드는 한글("도록: do log")이 섞여 있는데 Newsreader에는 한글 글리프가 없다.
  - `--font-display`, `--font-heading`, `--font-article-heading`, `--font-blog-heading` → Hahmlet
  - `--font-body`, `--font-ui`, `--font-sans`, `--font-article-deck`, `--font-blog-body`, `--font-blog-ui` → Pretendard
  - Lora를 언로드하므로 Lora를 참조하는 토큰은 **하나도 남지 않아야 한다**(`grep -r "Lora\|Gowun\|Playfair" src`가 0건).
- **폰트 로딩 정리 (`Head.astro`):** Lora, Playfair Display, Gowun Batang을 제거한다. Hahmlet(400/600/700)과 Newsreader(500)를 추가한다. Playfair는 이미 미사용 상태로 로드되고 있었다.
  - `pages/admin/analytics.astro`가 제거되는 글꼴을 참조하므로 함께 교체한다.
- **Pretendard 굵기:** `global.css`의 `@font-face`는 현재 400/700/800만 로드한다. 디자인에 필요한 **500/600을 추가**하고, 쓰지 않는 800은 제거를 검토한다.
- **기본 크기:**
  - 기사 본문 17px / 행간 1.9
  - 기사 제목 34px
  - 홈 머리기사 30–32px
  - 모바일 머리기사 25px

## 5. 공통 컴포넌트 규칙

> **2026-10-14 변경 (2단계 착수 시 결정, A안):** 큰 제호 + 모토 + 호수/날짜의 두 줄 헤더를 모든 페이지에 두면 뉴스·용어집의 페이지 제호(NewsprintShell 키커)와 호수·날짜가 중복되고, "오늘 N건"은 모든 페이지에 DB 조회를 추가하게 된다. 그래서 공통 헤더는 **한 줄 + 점 줄**로 두고, 호수·날짜는 페이지 제호 쪽에 한 번만 둔다. 큰 제호 + 모토는 홈(3단계)에서만 쓴다. 실제 신문도 제호는 1면에만 있다.

- **헤더 (공통, 데스크톱)**
  - 한 줄: 왼쪽 제호 `0to1log` + 주황 마침표, 가운데 섹션 메뉴(현재 메뉴는 아래 주황 점), 오른쪽 유틸리티 아이콘.
  - 배경은 페이지와 같은 `--color-bg-primary`. 헤더 아래 경계는 실선 대신 **점 줄**.
- **헤더 (모바일)**
  - 기존 구조 유지(제호 + 페이지 라벨, 유틸리티, 아래 5칸 섹션 메뉴). 같은 마침표·점 표시와 점 줄을 쓴다.
- **호수·날짜 (NewsprintShell 키커)**
  - **제N호:** 창간일 상수 `ISSUE_EPOCH = 2026-03-18`(DB 첫 발행 뉴스 날짜, KST)부터 표시 날짜(KST)까지 일수 + 1. DB 조회 없이 결정적으로 계산한다. 하드코딩 `'제01권 · 제10호'`와 사이트 콘텐츠 `volume_issue`를 대체한다. 기사 페이지는 발행일 기준 호수가 된다. EN 표기는 `No. N`.
  - **오늘 N건:** 공통 헤더에서는 제외한다. 홈(3단계)에서 이미 불러오는 뉴스 데이터로만 표시한다.
- **푸터:** 위쪽 경계는 점 줄. 제호 `0to1log.`와 모토, 링크(대문자·넓은 자간 없이), 저작권 줄. 배경은 `--color-bg-primary`.
- **카테고리 라벨:** 주황 점 + 600 굵기 텍스트. 카테고리별 색 구분은 없애고 accent 하나로 통일한다.
- **목록:** 카드 없이 점선으로 구분한다. 메타(카테고리 · 읽는 시간)는 작은 회색, 그 아래 Hahmlet 제목.
- **오늘의 용어 · 퀴즈 박스:** `--surf` 면 + radius 4px. 은은한 "면"은 이 둘에만 쓴다.
- **망점 사진:** `.halftone` 유틸리티. 실제 이미지에 dot 그라디언트 × 이미지 × `contrast()` 처리를 하고, 테마별로 다크 반전한다. 구현 시 성능을 검증한다(LCP 이미지에 filter를 적용해도 괜찮은지).

## 6. 페이지별 레이아웃

### 홈 (2026-10-14 확정: Hero + 오늘의 1면)
> 3월 20일 결정("홈은 Hero만")을 존중해 신문 1면 전체 대신 Hero + 한 줄 1면으로 정했다. [[2026-10-14-homepage-front-strip]]
- **Hero:** 큰 제호 `0to1log.`(Newsreader) → 모토 → 호수 줄(제N호 · 날짜 · 오늘 N건, N>0일 때만) → 키커 → 타이핑 헤드라인 → 소개(모바일에서 숨김) → CTA 2개.
- **오늘의 1면:** 점 줄 아래. 왼쪽은 머리기사(최신 기사, 같은 날 기사가 있으면 점선 아래 한 줄 추가), 오른쪽은 오늘의 용어(발행 용어 전체 중 호수 % 개수 번째, slug 순). 모바일은 1단.
- 데이터: `lib/pageData/homeFrontPage.ts`(뉴스 1번 + 용어 개수 1번 + 용어 1행 1번), 선택 로직은 `lib/homeFront.js`.

### 뉴스 기사
- 3단 그리드: TOC 140px / 본문 / 용어 여백 180px. 모바일에서는 1단으로 접는다.
- 머리: 카테고리 → Hahmlet 제목 → 덱.
- 바이라인 줄: 실선 위, 점선 아래. 왼쪽 "제N호 · 날짜 · N분 · 출처 N", 오른쪽 **입문판 · 학습판 · 전문판**.
  - 기존 `persona-switcher`의 beginner, learner, expert를 이 표현으로 바꾼다. 현재 판은 주황 점으로 표시한다. EN 라벨: Beginner · Learner · Expert edition.
  - 플로팅 버전(`persona-float`)도 같은 표현을 쓴다.
- 히어로 망점 사진.
- **핵심 정리 (fact pack):** 실제 데이터는 숫자가 아니라 `{claim, why_it_matters}` 텍스트다. 시안의 "50% / +18p"는 예시였다. 데이터와 콘텐츠는 바꾸지 않는다.
  - 항목들을 점선으로 구분한 세로 목록(데스크톱에서 항목이 3개 이하면 3칸 가로)으로 보여준다.
  - `claim`은 Hahmlet 600 17px, `why_it_matters`는 Pretendard `--sub` 13px.
- **본문:** 1단 17px, 좌측 정렬, 드롭캡 없음.
- **용어 사이드노트:**
  - 본문의 용어에 형광펜 하이라이트(accent 16% 하단 그라디언트)와 위첨자 번호를 붙인다.
  - 오른쪽 여백 "이 기사의 용어"에 정의와 "핸드북 →" 링크를 둔다.
  - 데이터는 기존 `relatedTerms`를 쓴다. 지금은 `[slug].astro` → `NewsprintSideRail`로 전달되고 있다.
  - **오른쪽 레일 재구성:** 기존 `NewsprintSideRail`이 오른쪽 180px 칸이 된다. 순서는 ① 이 기사의 용어(relatedTerms) → ② 함께 읽을 기사(similarPosts) → ③ 주목할 항목(focusItems)이다. 기존 콘텐츠는 하나도 버리지 않는다.
  - TOC(`NewsprintTOC`)와 `ReadingActionsRail`은 왼쪽 140px 칸으로 옮긴다. 현재 `ReadingActionsRail`은 TOC와 SideRail을 **함께 감싸는 래퍼**(`ko/news/[slug].astro:180-199`)이므로 이 래퍼를 분리해야 한다. 같은 래퍼를 쓰는 en 뉴스 페이지와 핸드북 상세 페이지도 영향을 받는다. 핸드북은 6단계에서 새 구조를 적용하고, 4단계에서는 기존 구조가 깨지지 않게만 한다.
  - **본문 매칭 (4단계 범위):** 렌더된 본문에서 각 relatedTerm의 표시명(ko/en)이 **처음 등장하는 곳 1회만** 하이라이트하고 레일 순서대로 번호를 붙인다. 매칭되지 않는 용어는 레일에 번호 없이 표시한다. 코드 블록, 링크, 제목 안의 텍스트는 매칭하지 않는다.
  - **페르소나 전환과의 관계:** 본문 HTML은 `personaHtmlMap`으로 클라이언트에서 교체된다. 매칭은 서버에서 **판(edition)마다 각각** 적용해 두거나, 교체 후 다시 실행해야 한다. 그렇지 않으면 판을 바꿀 때 하이라이트가 사라진다. 서버 측 적용을 우선 검토한다.
  - **모바일:** 레일은 본문 아래 "이 기사의 용어" 섹션으로 내려간다. 하이라이트를 탭하면 해당 항목으로 스크롤한다. 팝오버는 만들지 않는다.
- **퀴즈:** `--surf` 박스, 2×2 보기.
- **출처:** 번호(주황) + 점선 목록.
- 기존 기능(댓글, 기사 내 검색, ReadingActionsRail, 관리자 액션)은 유지하고 스타일만 맞춘다.

### 뉴스 목록 · 핸드북 · 블로그 · 제품 · 기타
위 공통 규칙을 적용한다. 각 단계 시작 시 **해당 페이지의 시안을 1장 확인한 뒤** 구현한다.
- 핸드북: 용어 = 사전
- 블로그: 칼럼 성격

## 7. 구현 전략: 기반 먼저, 그다음 페이지별

`main` 브랜치에서 단계마다 배포 가능한 상태를 유지한다. 순서는 다음과 같다.

1. **기반**
   - 테마 토큰 3개 교체와 pink/midnight 삭제, `--color-cat-*`과 Shiki 정리
   - `lib/theme.ts` 단일화(위 8개 파일 전환), 마이그레이션, fallback, i18n, preview 페이지 정리
   - 폰트 역할 분리(blog 토큰 포함), 로딩 교체, Pretendard 500/600 추가
   - 레트로 장식 제거:
     - 드롭캡: `global.css` 1207, 1218, 1966행 부근
     - 이중선: `3px double` 527, 541, 2062, 2131, 5890, 10054–10055행 부근 (`grep "double" global.css` 0건이 완료 기준)
     - 노이즈: `--noise-opacity`와 body의 SVG 노이즈(~2395행)
     - small-caps 키커: `.newsprint-kicker` 등
   - 결과: 사이트 전체가 새 색과 글꼴로 바뀐다.
2. **공통 헤더/푸터**: Navigation, Footer, ThemeToggle, 모바일 헤더.
3. **홈**
4. **뉴스 기사** (사이드노트 포함)
5. **뉴스 목록**
6. **핸드북** (목록, 상세, 카테고리)
7. **블로그**
8. **제품 · about · 기타** (preview 페이지는 1단계에서 이미 정리됨)

**CSS 정리 방침:** 각 단계에서 손대는 영역의 CSS는 `global.css`(14,193줄)에서 `styles/<area>.css`로 분리하고, 죽은 CSS는 삭제한다. 한 번에 전체를 리팩터링하지 않는다.

**계획 분리:** 구현 계획은 단계별로 따로 쓴다. 먼저 **1단계(기반)** 계획만 작성해 실행한다. 2–4단계 계획은 1단계 결과를 보고 작성한다. 5–8단계는 각 단계 시작 시 시안 1장을 확인한 뒤 계획한다.

**en/ko 중복:** `pages/en`과 `pages/ko`는 같은 컴포넌트를 공유하므로 컴포넌트 수준에서 수정한다. 페이지 파일에 하드코딩된 라벨이 있으면 두 언어 모두 확인한다.

**관리자 페이지는 범위 밖이다.** 새 토큰이 자동 적용되고, 깨지는 곳(대비, 가독성)만 최소한으로 수정한다.

## 8. 검증 (단계별 완료 기준)

- 3개 테마 × 데스크톱/모바일(375px) 스크린샷으로 확인한다. 시각 버그는 computed style뿐 아니라 스크린샷으로도 확인한다.
- 텍스트 대비 WCAG AA: 본문 4.5:1, 큰 글씨 3:1. 특히 `--mute`와 dark 테마의 accent를 확인한다.
- 기존 테마 저장값(pink, midnight, 미설정)으로 접속했을 때 깨지지 않는지 확인한다.
- `npm run build`와 기존 frontend 테스트를 통과해야 한다.
- 폰트 교체 후 LCP와 CLS가 회귀하지 않는지 확인한다.

## 9. 범위 밖

- URL과 IA, 메뉴 구조 변경
- 콘텐츠와 프롬프트 변경
- 관리자 리디자인
- Framer Motion 도입 (금지 규칙)

## 참고

- 시안 HTML: `.superpowers/brainstorm/3462-1791971561/` (`softer-v2.html`, `v2-themes.html`, `v2-apply.html`). gitignore 대상이므로 로컬에만 있다.
- 관련 노트: [[Design-System]], [[Color-Theme]], [[Typography]], [[Brand-Identity]]. 구현 완료 후 이 노트들을 갱신해야 한다.
