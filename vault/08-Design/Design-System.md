---
title: Design System
tags:
  - design
  - theme
  - tokens
  - typography
source: docs/04_Frontend_Spec.md
---

# Design System

0to1log의 3-테마 디자인 시스템. ==CSS Variable 토큰== 기반으로 Light(종이) / White / Dark 세 가지 무드를 하나의 브랜드 아래 통합한다. Surface Hierarchy로 깊이감을 표현하고, 일관된 타이포그래피와 간격 체계로 콘텐츠 가독성을 최우선으로 설계한다.

## 3-Theme System (Soft Newsprint)

| 테마 | 셀렉터 | 컨셉 | `--bg-primary` | `--bg-secondary` | `--text-primary` | `--text-secondary` | `--accent` | `--border` |
|---|---|---|---|---|---|---|---|---|
| **Light** (기본, 종이) | `[data-theme="light"]` | 따뜻한 종이 | `#F7F4EE` | `#EFEAE0` | `#24211D` | `#5A544B` | `#B4472A` | `#D9D2C5` |
| **White** | `[data-theme="white"]` | 쿨 화이트 | `#FFFFFF` | `#F3F5F8` | `#16181B` | `#4D5057` | `#2448A8` | `#E3E4E7` |
| **Dark** | `[data-theme="dark"]` | 웜 잉크 | `#181715` | `#121110` | `#ECE7DD` | `#B3ACA0` | `#E3774F` | `#35322D` |

> [!note]
> 상세 팔레트와 `theme.js` 구조는 [[Color-Theme]] 참조. 저장된 `pink`는 `light`로, `midnight`는 `dark`로 마이그레이션된다.

## CSS Variable Tokens

테마 전환은 `<html>` 요소의 `[data-theme]` 속성 셀렉터로 제어한다. 모든 컬러는 CSS 변수 토큰으로 정의되며, 테마가 바뀌면 변수값만 교체된다.

**토큰 네이밍 컨벤션:**

| 프리픽스 | 용도 | 예시 |
|---|---|---|
| `--color-bg-*` | 배경 (Surface 레벨) | `--color-bg-primary`, `--color-bg-secondary`, `--color-bg-tertiary` |
| `--color-text-*` | 텍스트 | `--color-text-primary`, `--color-text-secondary`, `--color-text-muted` |
| `--color-accent` | 인터랙션 강조 | `--color-accent`, `--color-accent-hover` |
| `--color-accent-glow` | 호버 시 외곽 그림자 | `rgba(accent, 0.15)` |
| `--color-accent-subtle` | 인라인 코드/태그 배경 | `rgba(accent, 0.08)` |
| `--color-border` | 테두리, 구분선 | `--color-border` |
| `--color-temp-*` | 뉴스 온도 지표 | `--color-temp-1` ~ `--color-temp-5` |

**토큰 사용 컨텍스트:**

| 토큰 | 사용하는 곳 | 사용하지 않는 곳 |
|---|---|---|
| `bg-primary` | 페이지 배경, 풀스크린 모달 뒤 | 카드 내부, 인풋 배경 |
| `bg-secondary` | 카드, Nav, 사이드바, 모달 | 코드 블록, 인풋, 페이지 배경 |
| `bg-tertiary` | 코드 블록, 인풋, 테이블 헤더 | 카드 배경, 페이지 배경 |
| `accent` | CTA 버튼, 활성 탭, 링크, 호버 보더 | 본문 텍스트, 배경, 장식 |
| `text-muted` | placeholder, 비활성 탭 | 본문, 제목 (WCAG 미달) |

> [!important]
> `accent` 컬러는 "사용자의 시선을 끌어야 하는 인터랙티브 요소"에만 사용한다. 한 화면에서 accent가 3개 이상 동시에 보이면 강조 효과가 희석된다.

## Surface Hierarchy

"어두운 배경 위 밝은 카드" — 상위 Level 배경 위에 하위 Level을 올려 깊이감을 만든다.

| Level | 토큰 | 용도 | 예시 |
|---|---|---|---|
| **Level 0** | `--color-bg-primary` | 페이지 전체 배경 (가장 뒤) | 메인 페이지, 풀스크린 모달 뒤 |
| **Level 1** | `--color-bg-secondary` | 카드, 모달, 드로어, Nav | 뉴스 카드, 사이드바, 드롭다운 |
| **Level 2** | `--color-bg-tertiary` | Level 1 안의 중첩 요소 | 코드 블록, 인풋 필드, 테이블 헤더 |

> [!note]
> 같은 Level끼리 중첩하지 않는다. Level 0 위에 Level 1, Level 1 안에 Level 2 순서를 지킨다.

## Typography

### Font Stack

| 변수 | 폰트 | 용도 |
|---|---|---|
| `--font-masthead` | ==Newsreader== 500 | 마스트헤드, 로고 |
| `--font-display` / `--font-heading` | ==Hahmlet== 400/600/700 | 히어로, 헤딩 (블로그 포함) |
| `--font-body` / `--font-ui` | ==Pretendard== 400-800 | 본문, UI 전반 (한영 혼용) |
| `--font-code` | JetBrains Mono, D2Coding, monospace | 코드 블록, 인라인 코드 |

한글에는 이탤릭을 쓰지 않고, 헤딩은 `word-break: keep-all` + `text-wrap: balance`를 적용한다. 상세는 [[Typography]].

### Font Licensing

| 폰트 | 라이선스 | 상업적 사용 |
|---|---|---|
| Newsreader | SIL Open Font License | 무료 |
| Hahmlet | SIL Open Font License | 무료 |
| Pretendard | SIL Open Font License | 무료 |
| JetBrains Mono | SIL Open Font License | 무료 |
| D2Coding | SIL Open Font License | 무료 |

### Type Scale

| 클래스 | 사이즈 | line-height | letter-spacing | 용도 |
|---|---|---|---|---|
| `.text-display-xl` | 3.5rem | 1.1 | -0.02em | Hero |
| `.text-display-lg` | 2.5rem | 1.2 | -0.015em | 섹션 타이틀 |
| `.text-heading` | 1.75rem | 1.3 | — | 포스트 제목 |
| `.text-subheading` | 1.25rem | 1.4 | — | 소제목 |
| `.text-body` | 1rem | 1.75 | — | 본문 |
| `.text-small` | 0.875rem | 1.5 | — | 메타, 캡션 |
| `.text-code` | 0.875rem | 1.6 | — | 코드 |

## Spacing System

- ==4px 베이스 그리드==, Tailwind 기본 spacing scale 사용
- 콘텐츠 최대 너비: `--max-width-content: 720px` (글 본문 가독성 최적)
- 와이드 레이아웃: `--max-width-wide: 1080px` (글 리스트, 포트폴리오)
- 풀 레이아웃: `--max-width-full: 1280px` (Admin 대시보드)

**반응형 브레이크포인트:**

| 토큰 | 값 |
|---|---|
| `--bp-mobile` | 640px |
| `--bp-tablet` | 768px |
| `--bp-desktop` | 1024px |
| `--bp-wide` | 1280px |

## Component Styles

### Buttons

| 타입 | 스타일 | 호버 |
|---|---|---|
| **Primary** | `bg: accent` | glow 확산 효과 |
| **Secondary** | `border: accent`, 투명 배경 | 배경 힌트 |
| **Ghost** | 테두리 없음 | 배경 힌트 |

### Cards

- 배경: `--color-bg-secondary` (Level 1)
- 테두리: `1px solid var(--color-border)`
- 둥근 모서리: `border-radius: 12px`
- 호버: `border-color: var(--color-accent)` + 미세한 glow 효과 (`accent-glow`)

### Input Fields

- 배경: `--color-bg-tertiary` (Level 2)
- 포커스 시 accent 링 표시

### Inline Code

- 배경: `--color-accent-subtle`
- `border-radius: 4px`, `padding: 2px 6px`

### Code Blocks

- 배경: `--color-bg-tertiary` (Level 2)
- 우측 상단: 언어 태그 + 원클릭 복사 버튼
- 모바일: 가로 스크롤 허용, ==폰트 축소 없음==

## Code Highlighting

==Shiki `css-variables` 모드==를 사용하여 모든 구문 강조 컬러를 CSS 변수로 제어한다. 빌드 타임 인라인 스타일 대신 CSS 변수를 사용하므로, 별도의 테마 파일 없이 3개 테마를 모두 지원한다.

**Astro 설정:** `shikiConfig: { theme: 'css-variables' }`

**테마별 Shiki 토큰 매핑 (값은 `global.css`의 `[data-theme]` 블록):**

| 토큰 | Light | White | Dark |
|---|---|---|---|
| `--shiki-token-keyword` | `#8B3A3A` | `#8B3A3A` | `#E3A27C` |
| `--shiki-token-string` | `#2E6F57` | `#2E6F57` | `#8FAE7E` |
| `--shiki-token-function` | `#5B4A8A` | `#5B4A8A` | `#B8A9D4` |
| `--shiki-token-comment` | `#615A50` | `#5E6269` | `#948D82` |
| `--shiki-token-constant` | `#9C3C22` | `#1C3A8A` | `#E3774F` |
| `--shiki-color-background` | `var(--color-bg-tertiary)` | `var(--color-bg-tertiary)` | `var(--color-bg-tertiary)` |

> [!note]
> 테마 전환 시 코드 블록도 CSS transition으로 자연스럽게 전환된다. `--shiki-color-background`는 Surface Level 2 토큰을 재사용한다.

## Theme Switching

**우선순위:** `localStorage` 수동 선택 → OS `prefers-color-scheme` → 기본값 `light`

**적용 방식:** `document.documentElement.setAttribute('data-theme', theme)` — 로직은 `frontend/src/lib/theme.js`(`readTheme`/`applyTheme`/`nextTheme`)에 모여 있다.

**전환 UI:** Nav 토글이 light → white → dark 순으로 순환 (라벨 종이/화이트/다크, EN Paper/White/Dark). 선택값은 `localStorage`에 저장.

**CSS 전환:** 테마 변경 시 smooth CSS transitions 적용으로 자연스러운 전환 효과

> [!important]
> **FOUC 방지:** `<head>` 인라인 스크립트로 페이지 렌더 전에 `data-theme` 속성을 즉시 설정해야 한다. `theme.js`의 `THEME_BOOT_SCRIPT`가 이 스크립트를 생성한다. 이 스크립트는 반드시 `<head>` 내부, 스타일시트보다 앞에 위치해야 테마 깜빡임(Flash of Unstyled Content)을 방지할 수 있다.

## Related
- [[Component-States]] — 컴포넌트 상태 정의
- [[Animations-&-Transitions]] — 애니메이션 & 트랜지션

## See Also
- [[Frontend-Stack]] — 디자인이 동작하는 프론트엔드 (02-Architecture)
- [[Brand-Identity]] — 브랜드 정체성과 보이스 (08-Design)
