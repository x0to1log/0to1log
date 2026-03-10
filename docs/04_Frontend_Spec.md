# 🎨 0to1log — Frontend Spec

> **문서 버전:** v2.3  
> **최종 수정:** 2026-03-05  
> **작성자:** Amy (Solo)  
> **상태:** Planning  
> **상위 문서:** `01_Project_Overview.md`

---

### v2.2 변경 이력

| 항목 | v2.1 | v2.2 | 이유 |
|---|---|---|---|
| Frontend 데이터 연동 | Supabase 중심 서술 | Supabase 직결 + FastAPI 경계 하이브리드 명시 | 03/05 문서와 호출 경계 일치 |
| `src/lib/api.ts` 정의 | 단순 FastAPI 호출 래퍼 | 검색/커뮤니티/권한/관리 API용 도메인 래퍼로 확장 | 범용 API 백엔드 전환 반영 |
| 기능별 호출 경로 | 일부 기능만 암시 | Cmd+K/Admin AI/커뮤니티/구독 경로 명시 | 구현/테스트 기준 고정 |

---

## 1. 기술 스택

> Naming boundary: public-facing `Log` copy is now `AI News`, internal/admin `Log` copy is now `Posts`, and route compatibility remains `/{locale}/log/`.
> Navigation shell contract: Web = `[Brand] [Primary Nav] [Utilities]`; Mobile/App = `[Brand/Page] [Profile or Settings]` + primary nav exposed separately.

| 기술 | 버전 | 역할 |
|---|---|---|
| **Astro** | v5.0+ | 콘텐츠 중심 프레임워크 (SSG/SSR), Islands Architecture |
| **Tailwind CSS** | v4.0 | 유틸리티 기반 스타일링 |
| **MDX** | - | 마크다운 + 인터랙티브 컴포넌트 |
| **Motion One** | - | 마이크로 인터랙션, Spring 물리 애니메이션 |
| **View Transitions API** | Astro 내장 | 페이지 전환 애니메이션 |
| **Supabase JS SDK** | - | 콘텐츠 읽기/단순 CRUD 직결, 인증 |
| **Custom API Wrapper (`src/lib/api.ts`)** | - | FastAPI 범용 도메인 API 호출 (검색/커뮤니티/권한/관리) |

### Astro Islands 전략

Astro의 Islands Architecture를 활용하여, 대부분의 페이지는 정적 HTML로 렌더링하고 인터랙션이 필요한 컴포넌트만 선택적으로 하이드레이션한다.

| 컴포넌트 | 하이드레이션 | 이유 |
|---|---|---|
| 글 본문, 레이아웃, 네비게이션 | 없음 (정적 HTML) | JS 불필요, 최대 성능 |
| Persona Switcher | `client:visible` | 뷰포트 진입 시 활성화 |
| Cmd+K 검색 모달 | `client:idle` | 페이지 로드 후 대기 |
| 댓글 시스템 | `client:visible` | 스크롤 시 하단에서 활성화 |
| Admin 에디터 | `client:load` | 즉시 완전 인터랙티브 필요 |
| 테마 토글 | `client:load` | FOUC 방지, 즉시 로드 |

### 페이지별 렌더링 전략 (SSG / SSR)

Astro `hybrid` 모드를 사용하여 기본은 SSG(정적 생성), 필요한 페이지만 SSR(서버 사이드 렌더링)로 전환한다. 매일 AI NEWS가 자동 발행되는 블로그 특성상, 데이터가 자주 바뀌는 페이지와 정적 페이지를 명확히 구분해야 한다.

Astro `hybrid` 모드 사용: `output: 'hybrid'` + `adapter: vercel()`. 기본 SSG, 페이지별 SSR 선택.

| 페이지 | 렌더링 모드 | 설정 | 이유 |
|---|---|---|---|
| **Home** (`/`) | SSR | `prerender = false` | Today's AI Pick이 매일 바뀜 |
| **Log** (`/log`) | SSR | `prerender = false` | 매일 2개 자동 발행, 항상 최신 목록 필요 |
| **Post Detail** (`/log/[slug]`) | SSG + on-demand revalidation | `prerender = true` (기본) | 발행 후 내용이 거의 안 바뀜. 파이프라인 발행 시 revalidate 호출 |
| **Portfolio** (`/portfolio`) | SSG | `prerender = true` (기본) | 정적 콘텐츠, 수동 업데이트 시에만 재빌드 |
| **Admin** (`/admin/*`) | SSR | `prerender = false` | 항상 최신 데이터 + 인증 체크 필요 |

- SSR 페이지: `export const prerender = false;` 선언
- SSG 페이지: `prerender = true`가 기본값이므로 별도 선언 불필요
- **Post Detail on-demand revalidation:** `/api/revalidate` is called server-side only, and must validate `REVALIDATE_SECRET` before triggering `__vercel_revalidate=1`.

---

## 2. 디자인 시스템

### 2-1. 디자인 방향성

**컨셉:** 하나의 브랜드, 세 개의 무드.

- **Dark (기본):** 🖤 Cyberpunk Editorial — 시크한 다크 모드 기반에 Neon Pink 포인트
- **Light (기본):** 🌸 Soft Pink Editorial — 파스텔 핑크 + 웜 크림 배경의 따뜻하고 부드러운 무드
- **Midnight Blue (부옵션):** 🌊 Deep Ocean — 차분하고 신뢰감 있는 깊은 블루 계열

**핵심 원칙:**
- 콘텐츠가 주인공. 장식이 콘텐츠를 방해하지 않는다
- 액센트 컬러는 강조와 인터랙션에만 사용 — 과용하지 않는다
- 코드 블록과 긴 글의 가독성을 최우선으로 설계한다
- 모바일에서도 코드 블록이 깨지지 않는다

### 2-2. Surface Hierarchy 규칙

```
Level 0: --color-bg-primary    → 페이지 전체 배경 (가장 뒤)
Level 1: --color-bg-secondary  → 카드, 모달, 드로어, Nav (페이지 위에 떠 있는 요소)
Level 2: --color-bg-tertiary   → Level 1 안의 중첩 요소 (코드 블록, 인풋, 테이블 헤더)

원칙: 상위 Level 배경 위에 하위 Level을 올린다. 같은 Level끼리 중첩하지 않는다.
```

### 2-3. 토큰 사용 컨텍스트

| 토큰 | 사용하는 곳 | 사용하지 않는 곳 |
|---|---|---|
| `bg-primary` | 페이지 배경, 풀스크린 모달 뒤 | 카드 내부, 인풋 배경 |
| `bg-secondary` | 카드, Nav(스크롤 시), 사이드바, 드롭다운, 모달 | 코드 블록, 인풋 필드, 페이지 배경 |
| `bg-tertiary` | 코드 블록, 인풋 필드, 테이블 헤더, 토글 비활성 | 카드 배경, 페이지 배경 |
| `text-primary` | 제목, 본문, CTA 텍스트 | placeholder, 비활성 UI |
| `text-secondary` | 부제목, 메타(날짜, 읽기 시간), 태그 라벨 | 제목, 본문 |
| `text-muted` | placeholder, 비활성 탭, 보조 설명 | 본문, 제목, 중요 정보 (WCAG 미달) |
| `border` | 카드 테두리, 구분선, 인풋 기본 테두리 | 강조 요소, CTA |
| `accent` | CTA 버튼, 활성 탭 언더라인, 링크, 호버 보더 | 본문 텍스트, 배경, 장식 |
| `accent-glow` | 호버 시 보더 외곽 shadow, CTA glow | 텍스트, 일반 배경 |
| `accent-subtle` | 인라인 코드 배경, 태그 배경, 활성 필터 배경 | 일반 텍스트 배경, 큰 영역 |

> **액센트 사용 원칙:** accent 컬러는 "사용자의 시선을 끌어야 하는 인터랙티브 요소"에만 사용한다. 정적 텍스트나 장식에는 쓰지 않는다. 한 화면에서 accent가 동시에 3개 이상 보이면 강조 효과가 희석되므로, 시각적 우선순위를 고려하여 가장 중요한 요소에만 적용한다.

### 2-4. 컬러 토큰 — 세 가지 테마

#### Dark Mode (기본) — 🖤 Cyberpunk Neon Pink

```css
[data-theme="dark"] {
  /* Surface */
  --color-bg-primary: #0f0f0f;          /* Deep Charcoal — Level 0 */
  --color-bg-secondary: #1a1a1a;        /* Card / Surface — Level 1 */
  --color-bg-tertiary: #242424;         /* Code Block / Input — Level 2 */

  /* Text */
  --color-text-primary: #f5f5f5;        /* 본문 텍스트 */
  --color-text-secondary: #a0a0a0;      /* 부제목, 메타 */
  --color-text-muted: #666666;          /* 비활성 텍스트 (WCAG 미달 — 장식용 한정) */

  /* Border */
  --color-border: #2a2a2a;

  /* Accent — Neon Pink */
  --color-accent: #ff2d78;
  --color-accent-hover: #ff4d91;
  --color-accent-glow: rgba(255, 45, 120, 0.15);
  --color-accent-subtle: rgba(255, 45, 120, 0.08);

  /* Status */
  --color-success: #00d68f;
  --color-warning: #ffaa00;
  --color-error: #ff4d4f;

  /* News Temperature */
  --color-temp-1: #666666;              /* 일반 */
  --color-temp-2: #a0a0a0;
  --color-temp-3: #ff8c42;              /* 주목 */
  --color-temp-4: #ff5e5e;
  --color-temp-5: #ff2d78;              /* 혁신적 — Neon Pink */
}
```

#### Light Mode (기본) — 🌸 Soft Pink Editorial

```css
[data-theme="light"] {
  /* Surface — 웜 파스텔 핑크 계열 */
  --color-bg-primary: #FFFDF9;          /* 크림 화이트 — Level 0 */
  --color-bg-secondary: #F5ECCD;        /* 웜 크림 — Level 1 (카드, 모달) */
  --color-bg-tertiary: #FCC8C2;         /* 피치 핑크 — Level 2 (코드 블록, 인풋) */

  /* Text — 웜 다크 톤 */
  --color-text-primary: #2D2024;        /* 웜 다크 브라운 */
  --color-text-secondary: #6B5460;      /* 모브 그레이 */
  --color-text-muted: #A8929C;          /* 연한 모브 (WCAG 미달 — 장식용 한정) */

  /* Border */
  --color-border: #F0DDD5;              /* 연한 피치 테두리 */

  /* Accent — Deep Rose Pink */
  --color-accent: #D94070;
  --color-accent-hover: #E85A88;
  --color-accent-glow: rgba(255, 135, 171, 0.2);    /* #FF87AB 기반 */
  --color-accent-subtle: rgba(255, 135, 171, 0.12);  /* #FF87AB 기반 */

  /* Status */
  --color-success: #2E8B57;
  --color-warning: #D4940A;
  --color-error: #C53030;

  /* News Temperature — 핑크 그라데이션 */
  --color-temp-1: #A8929C;
  --color-temp-2: #D4A0A0;
  --color-temp-3: #E87A8A;
  --color-temp-4: #D94070;
  --color-temp-5: #FF87AB;              /* 파스텔 핑크 강조 — #FF87AB 활용 */
}
```

#### Midnight Blue (부옵션) — 🌊 Deep Ocean

```css
[data-theme="midnight"] {
  /* Surface — 딥 오션 블루 계열 */
  --color-bg-primary: #051923;          /* Deep Ocean — Level 0 */
  --color-bg-secondary: #003554;        /* Navy — Level 1 */
  --color-bg-tertiary: #006494;         /* Ocean Blue — Level 2 */

  /* Text — 차가운 화이트 계열 */
  --color-text-primary: #E4F0F6;        /* Ice Blue */
  --color-text-secondary: #8ABED0;      /* Muted Sky */
  --color-text-muted: #4A7A8F;          /* Faded Ocean (WCAG 미달 — 장식용 한정) */

  /* Border */
  --color-border: #0A4D6E;

  /* Accent — Sky Blue */
  --color-accent: #00A6FB;
  --color-accent-hover: #33B8FC;
  --color-accent-glow: rgba(0, 166, 251, 0.15);
  --color-accent-subtle: rgba(0, 166, 251, 0.08);

  /* Status */
  --color-success: #00d68f;
  --color-warning: #ffaa00;
  --color-error: #ff6b6b;

  /* News Temperature — 블루 그라데이션 */
  --color-temp-1: #4A7A8F;
  --color-temp-2: #0582CA;              /* Amy 컬러칩 활용 */
  --color-temp-3: #00A6FB;
  --color-temp-4: #33B8FC;
  --color-temp-5: #66D4FF;              /* 가장 밝은 스카이 블루 */
}
```

### 2-5. 접근성 대비 검증 (세 테마 전부)

| 테마 | 조합 | 대비 비율 | WCAG AA |
|---|---|---|---|
| **Dark** | text-primary on Level 0 | 18.1:1 | ✅ |
| Dark | text-secondary on Level 0 | 7.3:1 | ✅ |
| Dark | accent on Level 0 | 5.2:1 | ✅ |
| Dark | accent on Level 1 | 4.6:1 | ✅ |
| Dark | text-muted on Level 0 | 3.7:1 | ❌ 장식용 한정 |
| **Light** | text-primary on Level 0 | ~15:1 | ✅ |
| Light | text-secondary on Level 0 | ~6.8:1 | ✅ |
| Light | accent on Level 0 | ~5.1:1 | ✅ |
| Light | accent on Level 1 | ~4.6:1 | ✅ (경계) |
| Light | text-muted on Level 0 | ~2.8:1 | ❌ 장식용 한정 |
| **Midnight** | text-primary on Level 0 | ~15.5:1 | ✅ |
| Midnight | text-secondary on Level 0 | ~7.8:1 | ✅ |
| Midnight | accent on Level 0 | ~7.0:1 | ✅ |
| Midnight | accent on Level 1 | ~4.6:1 | ✅ (경계) |
| Midnight | text-muted on Level 0 | ~3.5:1 | ❌ 장식용 한정 |

> **원칙:** `text-muted`는 모든 테마에서 WCAG AA를 통과하지 못하므로, 의미 있는 정보를 전달하는 텍스트에는 사용하지 않는다. placeholder, 비활성 힌트 등 보조 정보에만 한정한다.

### 2-6. 타이포그래피

#### 폰트 스택

```css
:root {
  /* Display — 히어로, 섹션 타이틀 (영문 전용) */
  --font-display: 'Clash Display', 'Pretendard', sans-serif;

  /* Body — 본문, UI 전반 (한영 혼용) */
  --font-body: 'Satoshi', 'Pretendard', sans-serif;

  /* Code — 코드 블록, 인라인 코드 */
  --font-code: 'JetBrains Mono', 'D2Coding', monospace;
}
```

#### 폰트 라이선스 확인

| 폰트 | 배포처 | 라이선스 | 상업적 사용 |
|---|---|---|---|
| **Clash Display** | Fontshare (Indian Type Foundry) | ITF Free Font License | ✅ 100% 무료 |
| **Satoshi** | Fontshare (Indian Type Foundry) | ITF Free Font License | ✅ 100% 무료 |
| **Pretendard** | GitHub (orioncactus) | SIL Open Font License | ✅ 무료 (폰트 단독 판매 제외) |
| **JetBrains Mono** | JetBrains | SIL Open Font License | ✅ 무료 |
| **D2Coding** | D2 (네이버) | SIL Open Font License | ✅ 무료 |

#### 한국어 폰트 — Pretendard 선정 이유

Noto Sans KR 대신 Pretendard 선택: Inter + 본고딕 기반 네오 그로테스크로 Satoshi와 자연스러운 혼용, 9 굵기 + 가변 폰트, 동적 서브셋 로딩 최적화.

#### Phase 1 렌더링 테스트 항목

- Clash Display + Pretendard 혼용 baseline alignment
- Satoshi + Pretendard 16px 본문 크기/행간 균형
- 모바일 375px 한국어 줄바꿈 자연스러움
- `font-display: swap` FOUT 허용 범위
- 라이트 모드 코드 블록(`#FCC8C2` 배경) 구문 강조 가독성 — 문제 시 `#FFF5F2`로 오버라이드

#### 타이포 스케일

```css
.text-display-xl  { font-size: 3.5rem; line-height: 1.1; letter-spacing: -0.02em; }  /* Hero */
.text-display-lg  { font-size: 2.5rem; line-height: 1.2; letter-spacing: -0.015em; } /* 섹션 타이틀 */
.text-heading     { font-size: 1.75rem; line-height: 1.3; }                           /* 포스트 제목 */
.text-subheading  { font-size: 1.25rem; line-height: 1.4; }                           /* 소제목 */
.text-body        { font-size: 1rem; line-height: 1.75; }                             /* 본문 */
.text-small       { font-size: 0.875rem; line-height: 1.5; }                          /* 메타, 캡션 */
.text-code        { font-size: 0.875rem; line-height: 1.6; }                          /* 코드 */
```

### 2-7. 간격 & 레이아웃

```css
/* 콘텐츠 최대 너비 */
--max-width-content: 720px;    /* 글 본문 — 가독성 최적 */
--max-width-wide: 1080px;      /* 글 리스트, 포트폴리오 */
--max-width-full: 1280px;      /* Admin 대시보드 */

/* 반응형 브레이크포인트 */
--bp-mobile: 640px;
--bp-tablet: 768px;
--bp-desktop: 1024px;
--bp-wide: 1280px;
```

### 2-8. 컴포넌트 스타일 가이드

**카드:**
- 배경: `--color-bg-secondary` (Level 1)
- 테두리: `1px solid var(--color-border)`
- 호버 시: `border-color: var(--color-accent)` + 미세한 glow
- 둥근 모서리: `border-radius: 12px`

**버튼:**
- Primary: `bg-accent` + 호버 시 glow 확산
- Secondary: `border-accent` + 투명 배경
- Ghost: 테두리 없음, 호버 시 배경 힌트

**코드 블록:**
- 배경: `--color-bg-tertiary` (Level 2)
- 우측 상단: 언어 태그 + 원클릭 복사 버튼
- 모바일: 가로 스크롤 허용, 폰트 축소 없음

**인라인 코드:**
- 배경: `--color-accent-subtle`
- `border-radius: 4px`, `padding: 2px 6px`

### 2-9. 코드 블록 구문 강조 전략

Astro 기본 Shiki는 빌드 타임에 인라인 스타일(`style="color: #e06c75"`)을 생성하여, 테마가 전환되어도 코드 블록 색상이 고정되는 문제가 있다. 이를 방지하기 위해 **Shiki `css-variables` 모드**를 사용하여 모든 구문 강조 컬러를 CSS 변수로 제어한다.

Astro 설정: `shikiConfig: { theme: 'css-variables' }` — 인라인 스타일 대신 CSS 변수 사용.

#### 테마별 Shiki 토큰 매핑

| 토큰 | Dark (One Dark Pro) | Light (GitHub Light) | Midnight (Night Owl) |
|---|---|---|---|
| `--shiki-token-keyword` | `#c678dd` 보라 | `#d73a49` 빨강 | `#c792ea` 연보라 |
| `--shiki-token-string` | `#98c379` 초록 | `#22863a` 초록 | `#addb67` 연두 |
| `--shiki-token-function` | `#61afef` 파랑 | `#6f42c1` 보라 | `#82aaff` 하늘 |
| `--shiki-token-comment` | `#5c6370` 회색 | `#6a737d` 회색 | `#637777` 바다회색 |
| `--shiki-token-constant` | `#d19a66` 주황 | `#005cc5` 파랑 | `#f78c6c` 산호 |
| `--shiki-token-punctuation` | `#abb2bf` | `#24292e` | `#d6deeb` |
| `--shiki-color-text` | `#abb2bf` | `#24292e` | `#d6deeb` |
| `--shiki-color-background` | `var(--color-bg-tertiary)` | `var(--color-bg-tertiary)` | `var(--color-bg-tertiary)` |

> 테마 전환 시 코드 블록도 CSS transition으로 자연스럽게 바뀜. `--shiki-color-background`만 오버라이드 가능.

---

## 3. 페이지별 UI 설계

### 3-1. Home ( `/` )

```
┌──────────────────────────────────────────────────┐
│  [Nav] Logo    Home  Log  Portfolio    🔍  🌙 👤 │
├──────────────────────────────────────────────────┤
│                                                  │
│         ╔══════════════════════════╗              │
│         ║   0  →  1  l o g        ║  ← 타이포    │
│         ║   AI Engineer's Journey ║    애니메이션  │
│         ╚══════════════════════════╝              │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │  🔍 "AI에게 무엇이든 물어보세요"    💬       │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  ── Today's AI Pick ──────────────────────────── │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ 🔬 Research  │  │ 💼 Business  │              │
│  │ GPT-5 아키텍 │  │ Cursor $60M  │              │
│  │ 처 분석...   │  │ 투자 유치... │              │
│  │ 🔥🔥🔥🔥    │  │ 🔥🔥🔥      │              │
│  └──────────────┘  └──────────────┘              │
│                                                  │
│  ── Recent Posts ─────────────────────────────── │
│                                                  │
│  [카테고리 필터: All | AI NEWS | Study | Career]  │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ Post Card                          2h ago   │ │
│  │ 제목 ...                                    │ │
│  │ 한 줄 요약 ...              [태그] [태그]   │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
├──────────────────────────────────────────────────┤
│  [Footer] © 0to1log · GitHub · LinkedIn          │
└──────────────────────────────────────────────────┘
```

**Hero Section:**
- "0 → 1 log" 타이포그래피 애니메이션 (Clash Display, 글자별 staggered fade-in)
- 서브카피: "AI Engineer's Journey" — 타이핑 효과
- 아래 화살표 또는 스크롤 힌트

**Today's AI Pick:**
- 매일 자동 생성되는 Research + Business 포스트 2장 카드
- 뉴스 온도에 따라 불꽃 아이콘 개수 차등 표시
- 카드 호버 시 accent 보더 glow

**AI Semantic Search Bar:**
- Placeholder: "AI에게 무엇이든 물어보세요"
- 우측 미니 챗봇 아이콘
- Phase 3 전까지는 기본 키워드 검색으로 동작, Phase 3에서 시맨틱 검색으로 업그레이드

### 3-2. Log ( `/log` )

```
┌──────────────────────────────────────────────────┐
│  [Nav]                                           │
├──────────────────────────────────────────────────┤
│                                                  │
│  All Posts                          총 N개의 글  │
│                                                  │
│  [All] [AI NEWS] [Study] [Career] [Project]       │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ 🔬 [Research] GPT-5 아키텍처 분석    3h ago │ │
│  │ Critical Gotcha: API 비용 2.5배 증가...     │ │
│  │ #openai #gpt-5            ⏱ 5min read      │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ 💼 [Business] Cursor $60M 투자 유치  5h ago │ │
│  │ 코딩 AI 시장의 판도가 바뀌고 있습니다...    │ │
│  │ #cursor #startup          ⏱ 7min read      │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  [Load More]                                     │
└──────────────────────────────────────────────────┘
```

**카테고리 필터:** 탭 형태, 활성 탭에 accent 언더라인 애니메이션

**포스트 카드 정보:**
- post_type 아이콘 (🔬 Research / 💼 Business)
- 카테고리 태그, 제목 + one_liner 미리보기
- 태그, 읽기 시간, 발행 시간
- 뉴스 온도 표시 (카드 좌측 얇은 컬러 바)

### 3-3. Post Detail ( `/log/[slug]` )

#### Research 포스트 레이아웃

```
┌──────────────────────────────────────────────────┐
│  ← Back to Log                                   │
│                                                  │
│  [AI NEWS · Research]              2026-03-04    │
│                                                  │
│  GPT-5 아키텍처 심층 분석:                       │
│  추론 성능은 올랐지만, 비용은?                    │
│                                                  │
│  🔥🔥🔥🔥  ⏱ 8min read                         │
│                                                  │
│  ── 💡 The One-Liner ─────────────────────────── │
│  "AI가 문제를 풀 때 더 오래 생각하게 만드는       │
│   기술이 나왔습니다"                              │
│                                                  │
│  ── 본문 ─────────────────────────────────────── │
│  (content_original — 단일 기술 심화 버전)         │
│                                                  │
│  ── 🎯 Action Item ───────────────────────────── │
│  ── ⚠️ Critical Gotcha ──────────────────────── │
│  ── 🔄 [회전 항목] ───────────────────────────── │
│  ── 🎲 Today's Quiz ──────────────────────────── │
│                                                  │
│  ── 📎 Sources ───────────────────────────────── │
│  ── 💬 Comments ──────────────────────────────── │
│  도움이 되었나요? [👍] [👎]                       │
└──────────────────────────────────────────────────┘
```

#### Business 포스트 레이아웃

```
┌──────────────────────────────────────────────────┐
│  ← Back to Log                                   │
│                                                  │
│  [AI NEWS · Business]              2026-03-04    │
│                                                  │
│  Cursor $60M 투자 유치:                          │
│  코딩 AI 시장의 새로운 판도                       │
│                                                  │
│  🔥🔥🔥  ⏱ 7min read                           │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │  [비전공자]  [학습자]  [현직자]           │    │
│  │   ^^^^^^^^ (accent 활성 언더라인)         │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ── 💡 The One-Liner ─────────────────────────── │
│  ── 본문 (페르소나별 전환) ───────────────────── │
│  ── 🎯 Action Item ───────────────────────────── │
│  ── ⚠️ Critical Gotcha ──────────────────────── │
│  ── 🔄 [회전 항목] ───────────────────────────── │
│  ── 🎲 Today's Quiz/Poll ─────────────────────── │
│                                                  │
│  ── 📰 Related News ──────────────────────────── │
│  │ 🏢 Big Tech: Google, Gemini 2.5 Flash...    │ │
│  │ 💰 Industry: 지난 24시간 내 소식 없음        │ │
│  │ 🛠 New Tools: Anthropic, Claude Code 출시... │ │
│                                                  │
│  ── 📎 Sources ───────────────────────────────── │
│  ── 💬 Comments ──────────────────────────────── │
│  도움이 되었나요? [👍] [👎]                       │
└──────────────────────────────────────────────────┘
```

**Persona Switcher:**
- Business 포스트 상단에만 노출. Research 포스트에서는 렌더링하지 않음
- 3개 탭: 비전공자 / 학습자 / 현직자
- 활성 탭: accent 언더라인 + 미세 glow
- 전환 시 본문 영역만 crossfade 애니메이션으로 교체 (전체 리로드 없음)
- 기본 선택: 쿠키에 저장된 페르소나

**Related News 섹션:**
- Business 포스트 하단에만 노출
- 3개 카테고리 (Big Tech / Industry & Biz / New Tools)
- 각각 아이콘 + 한 줄 요약. "없음" 메시지도 동일 레이아웃으로 표시

**읽기 인디케이터 (Reading Progress):**

기존의 상단 스크롤 바(페이지 전체 기준) 대신, **본문 `<article>` 영역 기준**의 읽기 진행률 + 남은 시간을 표시한다. 댓글, Related News, Footer는 진행률에서 제외.

데스크탑 — 우측 세로 레일 (본문 우측 여백에 고정):

```
                              ┌──┐
    본문 텍스트 ...           │░░│
    본문 텍스트 ...           │██│ ← 현재 위치
    본문 텍스트 ...           │██│
                              │  │
                              └──┘
                              ~3min
```

- 본문 max-width 720px, 화면 1024px+ 일 때 우측 여백에 얇은 세로 바
- 하단에 남은 읽기 시간 텍스트 (DB `reading_time_min` 필드 × 남은 비율로 역산)
- 본문을 가리지 않으며 시선 방해 최소화

태블릿 + 모바일 — 하단 슬림 바 (화면 하단 고정):

```
├────────────────────────────┤
│ ████████████░░░░  68% · ~3min │  ← 하단 고정 (40px)
└────────────────────────────┘
```

- 높이 40px 이하, 본문 스크롤 시작 시 fade-in
- 100% 도달 시 "✅ 다 읽었어요!" → 2초 후 fade-out

반응형 기준:

| 화면 폭 | 읽기 인디케이터 형태 | 이유 |
|---|---|---|
| 1024px+ (데스크탑) | 우측 세로 레일 | 본문 720px + 좌우 여백 충분 |
| 768~1023px (태블릿) | 하단 슬림 바 | 본문 720px 넣으면 우측 여백 부족 |
| ~767px (모바일) | 하단 슬림 바 | 동일 |

> **왜 상단 바 대신 이것인가:** 상단 2px 바는 전체 페이지 스크롤 기준이라 본문 끝을 알 수 없고, 퍼센트만으로는 심리적 동기가 약하다. "~3min left"라는 남은 시간 정보가 "조금만 더 읽자"는 동기를 만든다.

### 3-4. Portfolio ( `/portfolio` )

```
┌──────────────────────────────────────────────────┐
│  [Nav]                                           │
├──────────────────────────────────────────────────┤
│                                                  │
│  Portfolio                                       │
│  "0에서 1을 만드는 과정의 기록"                    │
│                                                  │
│  ── 🏗 Service Architecture ──────────────────── │
│  ┌─────────────────────────────────────────────┐ │
│  │  (0to1log 파이프라인 인터랙티브 다이어그램)  │ │
│  │  Tavily → Ranking → Research/Business →     │ │
│  │  Editorial → Supabase                       │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  ── 📊 Project Case Studies ──────────────────── │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ 0to1log      │  │ Project #2   │              │
│  │ 문제 → 설계  │  │ 문제 → 설계  │              │
│  │ → 결과 측정  │  │ → 결과 측정  │              │
│  └──────────────┘  └──────────────┘              │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Service Architecture Diagram:** 파이프라인 시각화, 노드 호버 시 설명 툴팁, accent 연결선 + 데이터 흐름 애니메이션

### 3-5. Admin ( `/admin` )

#### Phase 1 — 최소 구성 (에디터 없음)

```
┌──────────────────────────────────────────────────┐
│  [Admin Nav] Dashboard                           │
├──────────────────────────────────────────────────┤
│                                                  │
│  ── 📋 Posts ─────────────────────────────────── │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ GPT-5 아키텍처 분석           published     │ │
│  │ 2026-03-04         [Status ▼] [Delete]      │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ Cursor 투자 유치              draft         │ │
│  │ 2026-03-04         [Status ▼] [Delete]      │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  [+ New Post → Supabase Dashboard 외부 링크]     │
│                                                  │
└──────────────────────────────────────────────────┘
```

- 글 목록 (제목, status, 발행일)
- status 변경 드롭다운 (draft → published → archived)
- 삭제 버튼 (확인 모달)
- "새 글" 버튼 → Supabase Dashboard 외부 링크

> **Phase 1에서 에디터를 최소화하는 이유:** AI 파이프라인이 없는 Phase 1에서는 수동 포스트 몇 개만 작성하면 되므로, Supabase Dashboard에서 직접 편집하는 것으로 충분하다. Phase 2에서 에디터를 한 번에 제대로 만들어 이중 개발을 방지한다.

#### Phase 2 — 풀 에디터

```
┌──────────────────────────────────────────────────────────────┐
│  [Editor Nav] ← Back    Save Draft    Publish                │
├──────────────────────────┬───────────────────────────────────┤
│                          │                                   │
│  ## 마크다운 편집창       │  ## 실시간 미리보기                │
│                          │                                   │
│  제목: ___________       │  [비전공자] [학습자] [현직자]      │
│  카테고리: [dropdown]    │                                   │
│  태그: ___________       │  (선택된 페르소나 버전 미리보기)    │
│                          │                                   │
│  ---                     │  ---                              │
│  # 본문                  │  렌더링된 본문                     │
│  ...                     │  ...                              │
│                          │                                   │
│                          ├───────────────────────────────────┤
│                          │  ## AI 제안 패널                   │
│                          │                                   │
│                          │  Editorial Verdict: needs_revision│
│                          │  accuracy: 6/10                   │
│                          │                                   │
│                          │  💡 제안 1: "출처 추가 필요"       │
│                          │  [Apply]                          │
│                          │                                   │
│                          │  [🔄 재검수 요청]                 │
│                          │  [✨ AI 재생성]                    │
│                          │                                   │
└──────────────────────────┴───────────────────────────────────┘
```

- **좌측:** 마크다운 편집창 (메타데이터 입력 + 본문)
- **우측 상단:** 실시간 미리보기 (페르소나 탭 전환 가능)
- **우측 하단:** AI 제안 패널 (Editorial 피드백 + 수정 제안 클릭 반영)
- **호출 경로:** 재검수/재생성/수동 초안 생성은 `FastAPI /api/admin/ai/*` 경유

---

## 4. 핵심 컴포넌트 상태 정의

### Post Card

| 상태 | UI 표현 |
|---|---|
| **Loading** | 카드 틀 유지 + 내부 텍스트 영역 shimmer(skeleton) 애니메이션. 3개 placeholder |
| **Empty** | "아직 발행된 글이 없습니다" 메시지 + 글쓰기 권유 (Admin이면 "새 글 작성" 버튼) |
| **Error** | "글을 불러오는 데 실패했습니다" + [다시 시도] 버튼 |
| **Success** | 정상 카드 렌더링 |

### Persona Switcher

| 상태 | UI 표현 |
|---|---|
| **첫 방문 (쿠키 없음)** | "비전공자" 탭 기본 활성 + "읽기 수준을 선택하세요" 툴팁 (1회만, dismiss 후 쿠키 저장) |
| **쿠키 있음** | 저장된 페르소나 탭 자동 활성, 알림 없음 |
| **전환 중** | 이전 탭 텍스트 fade-out → 새 탭 텍스트 fade-in (150ms), 언더라인 spring slide |
| **전환 실패** | 이전 버전 유지 + "전환에 실패했습니다" 토스트 (3초 후 자동 닫힘) |
| **Research 포스트** | Switcher 컴포넌트 자체를 렌더링하지 않음 (`post_type === 'research'` 조건) |

#### Persona ???? ??

- ??? ???: DB ??? ??
- DB ?? ??? ?? ??
- ? ? ??? `beginner`
- ??? ? 1? ???: ?? ?? ?? DB? ?? ??? DB? upsert
- ?? persona ???? ??? `learner -> beginner` ??? ??

### Comment Section

| 상태 | UI 표현 |
|---|---|
| **비로그인** | 댓글 목록은 보임 + 작성 영역에 "댓글을 작성하려면 로그인하세요" + [Google] [GitHub] 버튼 |
| **로그인 + 댓글 없음** | "첫 번째 댓글을 남겨보세요!" 메시지 + 작성 input |
| **로그인 + 댓글 있음** | 댓글 목록 + 작성 input |
| **작성 중** | 작성 버튼 → spinner + 비활성 (중복 방지) |
| **작성 실패** | 작성 중이던 텍스트 유지 + "댓글 등록에 실패했습니다" + [다시 시도] |
| **삭제 확인** | "정말 삭제하시겠습니까?" 인라인 확인 (모달 아님) + [삭제] [취소] |
| **Loading** | 댓글 영역 skeleton 3개 |
| **스팸 방지 throttle** | 댓글 작성 후 30초간 작성 버튼 비활성 + "N초 후 다시 작성할 수 있습니다" 카운트다운 표시 |
| **연속 실패** | 3회 연속 실패 시 "잠시 후 다시 시도해주세요" + 60초 쿨다운 |

> **참고:** 서버 사이드 스팸 방어(Supabase RLS rate limiting, 봇 차단)는 `05_Infrastructure.md`에서 다룬다. 여기서는 사용자에게 보이는 프론트엔드 레벨 throttle만 정의한다.

### Today's AI Pick (Home)

| 상태 | UI 표현 |
|---|---|
| **정상** | Research 카드 + Business 카드 2장 나란히 |
| **Research "뉴스 없음"** | Research 카드에 "오늘 기술 뉴스 없음" 표시 (muted 톤) + Business 카드 정상 |
| **둘 다 없음** | "오늘 AI 뉴스가 아직 준비되지 않았습니다" 안내 + 최근 글 리스트로 대체 |
| **Loading** | 2장 카드 skeleton |

### Cmd+K Search Modal

| 상태 | UI 표현 |
|---|---|
| **대기** | 빈 input + "검색어를 입력하세요" placeholder + 최근 검색어 3개 표시 |
| **입력 중** | 디바운스 300ms 후 결과 요청 |
| **결과 있음** | 포스트 제목 + 카테고리 + 매칭 snippet 리스트 (최대 5개) |
| **결과 없음** | "검색 결과가 없습니다" + 다른 키워드 제안 |
| **오류** | "검색에 실패했습니다" + 재시도 안내 |
| **Phase 1~2** | 기본 키워드 필터링 (클라이언트 사이드) |
| **Phase 3** | `FastAPI /api/search/semantic` 경유 pgvector 시맨틱 검색 |

---

## 5. 공통 컴포넌트

### 5-1. Navigation

```
┌──────────────────────────────────────────────────┐
│  [Logo]    Home   Log   Portfolio    🔍   🌙  👤 │
└──────────────────────────────────────────────────┘
```

| 요소 | 동작 |
|---|---|
| Logo | 클릭 시 Home, accent 글로우 호버 |
| 네비 링크 | Home, Log, Portfolio — 활성 페이지 accent 언더라인 |
| 🔍 검색 | Cmd+K 모달 트리거 |
| 🌙 테마 토글 | Dark ↔ Light 전환 (OS 설정 기본) |
| 👤 프로필 | 비로그인: 로그인 버튼 / 로그인: 드롭다운 (페르소나 설정, 테마 설정, 로그아웃) |

- 스크롤 시 배경 blur 효과 (backdrop-filter)
- 모바일: 햄버거 메뉴 → 풀스크린 드로어

### 5-2. Post Card

```
┌─────────────────────────────────────────────────┐
│ ▎┌───────────────────────────────────────────┐  │
│ ▎│ 🔬 [AI NEWS · Research]        3h ago    │  │
│ ▎│                                           │  │
│ ▎│ GPT-5 아키텍처 심층 분석                   │  │
│ ▎│ "AI가 더 오래 생각하게 만드는 기술"         │  │
│ ▎│                                           │  │
│ ▎│ #openai #gpt-5      🔥🔥🔥🔥  ⏱ 8min   │  │
│ ▎└───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
  ▎← 뉴스 온도 컬러 바 (좌측 3px)
```

- 좌측 세로 바: `news_temperature` 값에 따른 온도 컬러
- 호버: 보더 accent glow + translateY(-2px)
- one_liner를 부제목으로 표시

### 5-3. Feedback Widget

```
도움이 되었나요?  [👍 12]  [👎 2]
```

- 포스트 최하단. 클릭 시 optimistic update
- 비로그인도 가능 (쿠키로 중복 방지)
- 모바일: 스크롤 80% 이상 시 sticky bar로 노출

---

## 6. 모바일 UX

### 설계 원칙

0to1log의 주요 유입 경로는 SNS 공유(X, LinkedIn)이며, 이 트래픽의 대부분이 모바일이다. 따라서 **모바일을 기본 설계 대상으로, 데스크탑을 확장으로** 접근한다.

### Persona Switcher (모바일)

**문제:** "비전공자 / 학습자 / 현직자" 한국어 3탭이 375px 화면에서 글씨가 잘릴 수 있음.

**해결:** 아이콘 + 축약어 조합

```
[Mobile: < 640px]
┌────────────────────────────────┐
│  [🌱 비전공]  [📚 학습]  [🔧 현직]  │
│     ^^^^^^^^                          │
│     ── accent ──                      │
└────────────────────────────────┘
```

- 활성 탭만 배경 하이라이트 (accent-subtle)
- 각 탭 최소 터치 영역: 44px × 44px

### 모바일 포스트 읽기 경험

```
[Mobile Post View]
┌──────────────────────────┐
│ ← Back            Share 📤│
│                          │
│ [AI NEWS · Business]     │
│                          │
│ 제목제목제목제목          │
│ 제목 두 줄까지           │
│                          │
│ 🔥🔥🔥  5min  3h ago    │
│                          │
│ [🌱 비전공] [📚 학습] [🔧 현직] │
│                          │
│ 💡 The One-Liner         │
│ 한 문장 요약...           │
│                          │
│ 본문 (full width, 16px)  │
│                          │
│ ┌──────────────────────┐ │
│ │ ```python      → scroll│
│ └──────────────────────┘ │
│                          │
│ ── 5블록 가이드 ──        │
│ (아코디언: One-Liner만    │
│  기본 펼침, 나머지 접힘)   │
│                          │
│ ── Related News ──       │
│ ── Comments ──           │
│ [👍 12] [👎 2]           │
└──────────────────────────┘
```

### 데스크탑 vs 모바일 차이점

| 요소 | 데스크탑 | 모바일 (<640px) |
|---|---|---|
| **Nav** | 풀 링크 + 아이콘 | 햄버거 → 풀스크린 드로어 (backdrop blur) |
| **Persona Switcher** | "비전공자 / 학습자 / 현직자" 풀 텍스트 | "🌱 비전공 / 📚 학습 / 🔧 현직" 아이콘+축약 |
| **5블록 가이드** | 모두 펼침 상태 | 아코디언 (One-Liner만 기본 펼침) |
| **코드 블록** | 전체 표시 | 가로 스크롤 + "← 스크롤 →" 힌트 (1회) |
| **Today's AI Pick** | 2열 카드 | 1열 세로 스택 |
| **Admin 에디터 (Phase 2)** | 좌우 분할 | 편집 / 미리보기 탭 전환 |
| **검색 모달** | 중앙 모달 (max-width 600px) | 풀스크린 모달 |
| **피드백 위젯** | 인라인 | 스크롤 80%+ 시 sticky bar |
| **댓글** | 인라인 | 인라인 (textarea 높이 자동 확장) |

### 모바일 터치 인터랙션

- 모든 터치 타겟: 최소 44px × 44px (WCAG 2.5.5)
- 버튼 간 간격: 최소 8px (오터치 방지)
- 풀스크린 드로어: 왼쪽 엣지 스와이프 열기, 오른쪽 스와이프 닫기
- 코드 블록: 첫 번째 코드 블록에만 "← 스크롤 →" 오버레이 힌트 (3초 후 fade-out)

### 모바일 성능

- 이미지: `loading="lazy"` + `srcset` 반응형 (모바일용 작은 해상도)
- 폰트: Pretendard 동적 서브셋 사용 (전체 woff2 다운로드 방지)
- 애니메이션: 모바일에서는 복잡한 spring → 간단한 fade로 대체
- 읽기 인디케이터: 모바일에서는 하단 슬림 바 (40px), 본문 스크롤 시 fade-in

---

## 7. 애니메이션 & 트랜지션

### 7-1. 페이지 전환 (View Transitions API)

- Astro 설정: `transitions: true`
- 페이지 간 이동 시 부드러운 crossfade
- 글 리스트 → 글 상세: 카드가 확장되는 느낌의 morph 트랜지션

### 7-2. 마이크로 인터랙션 (Motion One)

| 요소 | 애니메이션 | 타이밍 |
|---|---|---|
| Hero 타이포그래피 | 글자별 staggered fade-in + slide-up | 로드 시 |
| 카드 목록 | staggered fade-in (각 100ms 딜레이) | 스크롤 진입 시 |
| Persona Switcher | 언더라인 spring slide | 탭 클릭 시 |
| 본문 전환 | crossfade (opacity, 150ms) | 페르소나 전환 시 |
| 버튼 호버 | scale(1.02) + glow 확산 | 호버 시 |
| 뉴스 온도 바 | width 0→100% ease-out | 카드 진입 시 |
| 읽기 인디케이터 | fade-in/out + 바 높이 연동 | 본문 스크롤 진입/이탈 시 |

### 7-3. 애니메이션 원칙

- **성능 우선:** `transform`과 `opacity`만 애니메이션 (layout thrashing 방지)
- **prefers-reduced-motion 존중:** `@media (prefers-reduced-motion: reduce)` → 모든 animation/transition-duration을 0.01ms로 강제
- **모바일 절제:** 복잡한 spring → 간단한 fade로 대체

---

## 8. 테마 전환

### 세 가지 테마 전환 구조

**테마 우선순위:** ① localStorage 수동 선택 (dark/light/midnight) → ② OS `prefers-color-scheme` → ③ 기본값: dark

적용 방식: `document.documentElement.setAttribute('data-theme', theme)`. FOUC 방지를 위해 `<head>` 인라인 스크립트로 초기 테마 즉시 적용.

### 전환 UI

- **Nav 토글 (🌙/☀️):** Dark ↔ Light 빠른 전환. 메인 기능.
- **프로필 드롭다운 > "테마 설정":** 3가지 선택지
  - "시스템 설정 따르기" (Dark/Light 자동 전환)
  - "Dark" (수동 고정)
  - "Light" (수동 고정)
  - "Midnight Blue" (수동 고정 — 부옵션)
- 선택값은 localStorage에 저장. Phase 4 로그인 시 프로필 동기화.

---

## 9. 접근성 (a11y)

### 키보드 네비게이션

| 요소 | Tab 이동 | Enter/Space | Esc |
|---|---|---|---|
| Nav 링크 | ✅ 순서대로 포커스 | 해당 페이지로 이동 | - |
| Persona Switcher | ✅ 탭 간 이동 | 해당 페르소나 활성화 | - |
| 테마 토글 | ✅ 포커스 | Dark ↔ Light 전환 | - |
| Cmd+K 검색 | Cmd+K로 열기 | 선택된 결과로 이동 | 모달 닫기 |
| 댓글 작성 | ✅ textarea 포커스 | - (Enter=줄바꿈) | - |
| 좋아요 버튼 | ✅ 포커스 | 좋아요 토글 | - |
| 드롭다운 | ✅ 포커스 | 열기 | 닫기 |
| 5블록 아코디언 | ✅ 각 항목 포커스 | 펼치기/접기 토글 | - |

### 포커스 스타일

- `:focus-visible` → `outline: 2px solid var(--color-accent)`, `outline-offset: 2px`, `border-radius: 4px`
- `:focus:not(:focus-visible)` → `outline: none` (마우스 클릭 시 포커스 링 숨김)

### ARIA 라벨

| 컴포넌트 | ARIA 적용 |
|---|---|
| Persona Switcher | `role="tablist"`, 각 탭 `role="tab"` + `aria-selected`, 본문 `role="tabpanel"` + `aria-labelledby` |
| 뉴스 온도 | `aria-label="뉴스 중요도: N단계 (5단계 중)"` |
| 테마 토글 | `aria-label="다크 모드로 전환"` / `"라이트 모드로 전환"` (상태에 따라 동적) |
| 검색 모달 | `role="dialog"` + `aria-modal="true"` + `aria-label="글 검색"` |
| 피드백 위젯 | `aria-label="이 글이 도움이 되었나요?"`, 각 버튼 `aria-pressed` |
| 읽기 인디케이터 | `role="progressbar"` + `aria-valuenow` + `aria-label="읽기 진행률: N%, 약 M분 남음"` |
| 코드 블록 복사 | `aria-label="코드 복사"`, 복사 완료 시 `aria-live="polite"` 영역에 "복사되었습니다" |
| 댓글 결과 | 성공/실패 시 `aria-live="polite"` 영역으로 스크린 리더 알림 |

### 시맨틱 HTML 원칙

```html
<main>
  <article>
    <h1>포스트 제목</h1>
    <h2>본문 소제목</h2>
    <h2>Action Item</h2>
    <h2>Critical Gotcha</h2>
    <h2>Related News</h2>
    <section aria-label="댓글">
      <h2>댓글</h2>
    </section>
  </article>
</main>
<!-- nav, main, article, aside, footer 시맨틱 태그 사용 -->
<!-- 장식용 이미지: alt="" (빈 문자열) / 의미 있는 이미지: 설명적 alt -->
```

### 추가 접근성 항목

- **스킵 네비게이션:** 페이지 최상단에 "본문으로 건너뛰기" 링크 (Tab 첫 포커스, 시각적으로 숨김, 포커스 시 노출)
- **언어 선언:** `<html lang="ko">`
- **동적 콘텐츠 알림:** 페르소나 전환, 댓글 추가 시 `aria-live="polite"` 사용
- **고대비 모드:** `prefers-contrast: more` 미디어 쿼리 대응 — 테두리 진하게, glow 효과 제거

---

## 10. SEO & 성능

### SEO

- **메타 태그:** 포스트별 동적 title, description, og:image
- **구조화 데이터:** JSON-LD (Article, BlogPosting)
- **sitemap.xml:** Astro 자동 생성
- **RSS 피드:** `/rss.xml` 자동 생성
- **Canonical URL:** 페르소나별 URL이 아닌 단일 URL (중복 콘텐츠 방지)

### 성능 목표

| 지표 | 목표 | 측정 방법 |
|---|---|---|
| **LCP** | < 1.5s | Vercel Analytics (자동) |
| **Lighthouse Performance** | 90+ | 주요 페이지 변경 시 Chrome DevTools 수동 체크 |

**자동 모니터링:** Vercel Analytics 활성화 (무료 티어 포함). Core Web Vitals 대시보드에서 LCP, CLS, INP 자동 추적.

**수동 체크:** 주요 페이지 변경 시 Lighthouse 1회 실행. 목표 미달 시 원인 분석 후 이슈 등록.

### 폰트 로딩 전략

```html
<!-- 핵심 폰트 preload (전부 셀프 호스팅) -->
<link rel="preload" href="/fonts/clash-display.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/satoshi.woff2" as="font" type="font/woff2" crossorigin>

<!-- Pretendard: 동적 서브셋 셀프 호스팅 -->
<!-- /public/fonts/pretendard/ 에 woff2 파일 + CSS 배치 -->
<link rel="stylesheet" href="/fonts/pretendard/pretendard-dynamic-subset.css" />

<!-- fallback: font-display: swap -->
```

> **왜 셀프 호스팅인가:** Pretendard만 jsDelivr CDN에 의존하면 CDN 장애 시 한국어 텍스트가 시스템 고딕으로 폴백되며, 한글 폰트는 글자 폭 차이가 커서 레이아웃 시프트가 발생한다. 동적 서브셋 파일은 유니코드 레인지별로 쪼개져 있어 각 수십KB이므로 셀프 호스팅 용량 부담이 적다. 외부 의존성을 줄여 빌드-배포 안정성을 확보한다.

---

## 11. 데이터 연동 전략 (Supabase 직결 + FastAPI 경계)

### 클라이언트 초기화

```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  import.meta.env.PUBLIC_SUPABASE_URL,
  import.meta.env.PUBLIC_SUPABASE_ANON_KEY
);
```

### Supabase 직결 패턴 (읽기/단순 CRUD)

```typescript
// 글 목록 조회 (SSG 시 빌드 타임)
const { data: posts } = await supabase
  .from('news_posts')
  .select('id, title, slug, category, post_type, one_liner, news_temperature, tags, reading_time_min, published_at')
  .eq('status', 'published')
  .order('published_at', { ascending: false });

// 글 상세 조회
const { data: post } = await supabase
  .from('news_posts')
  .select('*')
  .eq('slug', slug)
  .eq('status', 'published')
  .single();

// 단순 댓글 CRUD
const { error } = await supabase
  .from('comments')
  .insert({ post_id, content, user_id });
```

### 데이터 접근 경계 정책

| 작업 유형 | 호출 경로 | 이유 |
|---|---|---|
| 콘텐츠 읽기(리스트/상세) | Frontend → Supabase 직접 | 응답 지연 최소화, 단순 조회 |
| 단순 댓글 CRUD/좋아요 | Frontend → Supabase 직접 | RLS로 권한 통제 가능 |
| 시맨틱 검색(Cmd+K) | Frontend → FastAPI | 임베딩/랭킹 로직 캡슐화 |
| 포인트/퀴즈/베팅 | Frontend → FastAPI | 트랜잭션/치트 방지 |
| 구독 권한 검증 | Frontend → FastAPI | 결제 상태 검증, 시크릿 보호 |
| Admin AI 기능(초안/검수/재작성) | Frontend → FastAPI | OpenAI 키 비노출, 비즈니스 로직 집중 |

### FastAPI 호출 래퍼 (`src/lib/api.ts`)

```typescript
// src/lib/api.ts
const API_BASE = import.meta.env.PUBLIC_FASTAPI_URL;

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    credentials: "include",
  });

  if (!res.ok) throw new Error(`API request failed: ${res.status}`);
  return res.json() as Promise<T>;
}
```

> `src/lib/api.ts`는 검색/커뮤니티/구독 권한/Admin AI 도메인의 FastAPI 호출을 공통화하는 레이어로 사용한다.

### Supabase 인증 흐름 (댓글/기본 로그인)

```typescript
// 소셜 로그인 (댓글용)
async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.href }
  });
}

supabase.auth.onAuthStateChange((event, session) => {
  // UI 업데이트
});
```

---

## 12. 에러 핸들링 UI

### Fallback 정책

| 실패 상황 | Fallback |
|---|---|
| 글 목록 로드 실패 | "글을 불러오는 데 실패했습니다" + [다시 시도] |
| 페르소나 전환 실패 | 이전 버전 유지 + "전환에 실패했습니다" 토스트 |
| 댓글 작성 실패 | 작성 중이던 텍스트 유지 + 에러 메시지 + [다시 시도] |
| 검색 실패 | "검색에 실패했습니다" + 기본 키워드 검색으로 폴백 |
| 이미지 로드 실패 | 카테고리별 기본 placeholder 이미지 |
| Admin AI 기능 실패 | 에러 상세 표시 + "수동으로 작성하기" 옵션 |

### 에러 UI 원칙

- 에러 메시지는 사용자 친화적 한국어 (기술 에러 코드 숨김)
- 항상 "다음에 할 수 있는 행동"을 함께 제시
- Optimistic Update 패턴: 댓글 좋아요 등 즉시 반영 후, 실패 시 롤백

---

## 13. 디렉토리 구조

```
src/
├── components/
│   ├── common/
│   │   ├── Navigation.astro
│   │   ├── Footer.astro
│   │   ├── ThemeToggle.astro        (client:load)
│   │   ├── SearchModal.astro        (client:idle)
│   │   ├── SkipNavigation.astro     (접근성: 본문으로 건너뛰기)
│   │   └── ReadingIndicator.tsx     (client:visible, 읽기 진행률 + 남은 시간)
│   ├── post/
│   │   ├── PostCard.astro
│   │   ├── PersonaSwitcher.tsx      (client:visible, React Island)
│   │   ├── RelatedNews.astro
│   │   ├── PromptGuideBlocks.astro
│   │   ├── FeedbackWidget.tsx       (client:visible)
│   │   └── CommentSection.tsx       (client:visible)
│   ├── home/
│   │   ├── HeroSection.astro
│   │   ├── TodaysAIPick.astro
│   │   └── RecentPosts.astro
│   ├── portfolio/
│   │   ├── ArchitectureDiagram.astro
│   │   └── CaseStudyCard.astro
│   └── admin/
│       ├── PostList.tsx              (client:load — Phase 1)
│       ├── DraftList.tsx             (client:load — Phase 2)
│       ├── PostEditor.tsx            (client:load — Phase 2)
│       ├── AIPanel.tsx               (client:load — Phase 2)
│       └── PipelineStatus.tsx        (client:load — Phase 2)
├── layouts/
│   ├── BaseLayout.astro             (공통 head, nav, footer, 스킵 네비게이션)
│   ├── PostLayout.astro             (글 상세 레이아웃)
│   └── AdminLayout.astro            (Admin 전용)
├── pages/
│   ├── index.astro                  (Home)
│   ├── log/
│   │   ├── index.astro              (글 리스트)
│   │   └── [slug].astro             (글 상세)
│   ├── portfolio/
│   │   └── index.astro
│   ├── admin/
│   │   ├── index.astro              (Phase 1: 글 목록 / Phase 2: 대시보드)
│   │   ├── drafts.astro             (Phase 2)
│   │   ├── new.astro                (Phase 2)
│   │   └── edit/[id].astro          (Phase 2)
│   └── api/
│       └── trigger-pipeline.ts      (Vercel Cron 프록시)
├── lib/
│   ├── supabase.ts                  (클라이언트 초기화)
│   └── api.ts                       (FastAPI 범용 도메인 호출 래퍼)
├── styles/
│   ├── global.css                   (CSS 변수, 폰트, 리셋, 세 테마 정의)
│   └── code-theme.css               (코드 블록 구문 강조)
└── content/                         (MDX 콘텐츠, 필요시)
```

---

## 14. Phase별 Frontend 구현 범위

### Phase 1a — 뼈대 (2~3주)

| 기능 | 완료 기준 |
|---|---|
| Astro + Tailwind 초기 세팅 + 3테마 CSS 변수 | 테마 전환 시 모든 토큰 정상 반영 |
| Shiki css-variables 코드 블록 구문 강조 | 3테마 모두 구문 강조 정상, 테마 전환 시 깜빡임 없음 |
| 폰트 로딩 + 렌더링 테스트 (5개 항목) | 라이트 모드 코드 블록 가독성 포함 전부 통과 |
| BaseLayout (Nav + Footer + 스킵 네비게이션) | 데스크탑/모바일 반응형, 키보드 접근성 |
| Home (Hero + 하드코딩 더미 포스트) | 더미 데이터로 레이아웃 확인 |
| Vercel 배포 + 도메인 연결 (0to1log.com) | 프로덕션 URL 접속 가능 |

> **Phase 1a 마일스톤:** 빈 껍데기지만 배포된 사이트. 테마, 폰트, 레이아웃 문제를 일찍 발견할 수 있다.

### Phase 1b — 데이터 연결 (2~3주)

| 기능 | 완료 기준 |
|---|---|
| Supabase 연동 (글 목록/상세 조회) | 실제 DB 데이터로 페이지 렌더링 |
| Astro hybrid 모드 설정 (SSR/SSG 페이지 분리) | Home, Log = SSR / Post Detail, Portfolio = SSG |
| Log (글 리스트 + 카테고리 필터) | 카테고리 필터 작동, 정렬 정상 |
| Post Detail (마크다운 렌더링 + 코드 블록) | Shiki 구문 강조 + 3테마 반영 |
| Portfolio (기본 구조) | 정적 레이아웃 |
| Admin (최소 CRUD — 글 목록 + status 변경) | Supabase Dashboard 외부 링크로 새 글 작성 |
| ARIA 라벨 + 키보드 네비게이션 + 포커스 스타일 | 스크린 리더 테스트 통과 |
| Vercel Analytics 활성화 | Core Web Vitals 대시보드 확인 가능 |

> **Phase 1b 마일스톤:** 실제 데이터가 연결된 MVP. 수동 포스트로 사이트 운영 가능.

### Phase 2 — AI 연동 UI

| 기능 |
|---|
| Persona Switcher (Business 포스트) |
| Today's AI Pick 카드 (Research + Business) |
| 뉴스 온도 시각화 |
| Related News 섹션 |
| "뉴스 없음" 공지 UI |
| Admin 풀 에디터 (AI 제안 패널 포함, `FastAPI /api/admin/*`) |
| 읽기 인디케이터 (데스크탑 우측 레일 + 태블릿/모바일 하단 바) |
| 5블록 구조 UI 컴포넌트 (모바일 아코디언) |
| 댓글 시스템 (스팸 throttle 포함) |
| 피드백 위젯 (모바일 sticky bar) |

### Phase 3 — 고도화

| 기능 |
|---|
| AI Semantic Search (Cmd+K → `FastAPI /api/search/semantic` → pgvector) |
| Dynamic OG Image |
| Highlight to Share |
| Portfolio 인터랙티브 다이어그램 |
| AI Ops Dashboard UI |

### Phase 4 — 커뮤니티

| 기능 |
|---|
| 포인트 시스템 UI (`FastAPI /api/community/*`) |
| 돼지저금통 UI |
| Prediction Game UI (퀴즈/베팅, `FastAPI /api/community/*`) |
| 구독 권한 체크 UI (`FastAPI /api/subscription/me/access`) |


---


## 15. Policy Addendum (v2.3)

### 15-1. Persona Preference Priority
- Logged-in user: DB preference first
- If DB is empty, use cookie
- If both are missing, default to `beginner`
- One-time sync on login: if cookie exists and DB is empty, upsert cookie value to DB
- Persona content fallback order: `learner -> beginner`

### 15-2. Revalidate Security Boundary
- `/api/revalidate` must return `401` when `REVALIDATE_SECRET` is invalid
- Do not call `/api/revalidate` from client components
- Allow only server-side calls (FastAPI or Vercel server route)
- Do not expose revalidate helper in public `src/lib/api.ts` wrapper

### 15-3. Verification Criteria
- Zero direct `/api/revalidate` fetch calls in client bundle
- Persona resolution follows `DB > cookie > beginner` consistently
