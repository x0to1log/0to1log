# Color Theme

> 4개 테마 컬러 시스템. 대상 파일: `frontend/src/styles/global.css`

## 테마 개요

| 테마 | 성격 | 배경 톤 | 액센트 | colorScheme |
|------|------|---------|--------|-------------|
| **Dark** | 딥 브라운 뉴스프린트 | 웜 다크 브라운 | 골드 `#C3A370` | dark |
| **Midnight** | 쿨 잉크 밤하늘 | 블루-그레이 다크 | 샴페인 `#C4B07A` | dark |
| **Light** | 크림 종이 | 웜 베이지 | 에스프레소 `#6B4226` | light |
| **Pink** | 체리 블로썸 | 연핑크 | 코랄핑크 `#E8496A` | light |

## 현재 팔레트 (적용 중)

### Dark — 딥 브라운

```css
--color-bg-primary: #18140F;
--color-bg-secondary: #120F0C;
--color-bg-tertiary: #1F1A15;
--color-input-surface: #221D18;
--color-text-primary: #E0D8C3;
--color-text-secondary: #A39D8E;
--color-text-muted: #948C7E;
--color-border: #3D3529;
--color-accent: #C3A370;
--color-accent-hover: #D4B882;
--color-accent-glow: rgba(195, 163, 112, 0.15);
--color-accent-subtle: rgba(195, 163, 112, 0.08);
--color-success: #5A8E5D;
--color-warning: #D4A843;
--color-error: #A8524B;
--color-shadow: rgba(0, 0, 0, 0.35);
--noise-opacity: 0.025;

/* Category Colors */
--color-cat-ainews: #D46A58;
--color-cat-study: #7A8B78;
--color-cat-career: #A09080;
--color-cat-project: #8888A0;
--color-cat-work-note: #6E8C92;
--color-cat-daily: #A97C68;

/* Shiki — Warm Sepia */
--shiki-token-keyword: #D4A87C;
--shiki-token-string: #8FAE7E;
--shiki-token-function: #B8A9D4;
--shiki-token-comment: #948C7E;
--shiki-token-constant: #C3A370;
--shiki-token-punctuation: #E0D8C3;
--shiki-color-text: #E0D8C3;
```

### Midnight — 쿨 잉크

```css
--color-bg-primary: #08090E;
--color-bg-secondary: #101218;
--color-bg-tertiary: #1A1C25;
--color-input-surface: #0C0D14;
--color-text-primary: #C8CDD8;
--color-text-secondary: #A0A6B4;
--color-text-muted: #7E8596;
--color-border: #2E3242;
--color-accent: #C4B07A;
--color-accent-hover: #D4C08A;
--color-accent-glow: rgba(196, 176, 122, 0.15);
--color-accent-subtle: rgba(196, 176, 122, 0.08);
--color-success: #4E9A6B;
--color-warning: #C9A044;
--color-error: #B85450;
--color-shadow: rgba(0, 0, 0, 0.6);
--noise-opacity: 0.025;

/* Category Colors — cool shift */
--color-cat-ainews: #D06858;
--color-cat-study: #6E9682;
--color-cat-career: #8C94AA;
--color-cat-project: #8282AF;
--color-cat-work-note: #6496AA;
--color-cat-daily: #AA8282;

/* Shiki — Cool Ink */
--shiki-token-keyword: #D4C08A;
--shiki-token-string: #6E9682;
--shiki-token-function: #8282AF;
--shiki-token-comment: #7E8596;
--shiki-token-constant: #C4B07A;
--shiki-token-punctuation: #C8CDD8;
--shiki-color-text: #C8CDD8;
```

### Light — 크림 종이

```css
--color-bg-primary: #F4F1EA;
--color-bg-secondary: #E3DCCC;
--color-bg-tertiary: #D3CCB8;
--color-input-surface: #EAE5D5;
--color-text-primary: #333333;
--color-text-secondary: #555555;
--color-text-muted: #736B63;
--color-border: #ADA192;
--color-accent: #6B4226;
--color-accent-hover: #7E5030;
--color-accent-glow: rgba(107, 66, 38, 0.15);
--color-accent-subtle: rgba(107, 66, 38, 0.08);
--color-success: #2E6F57;
--color-warning: #B8860B;
--color-error: #8B3A3A;
--color-shadow: rgba(43, 36, 26, 0.12);
--noise-opacity: 0.04;

/* Category Colors */
--color-cat-ainews: #B03E2E;
--color-cat-study: #3A7348;
--color-cat-career: #6B5B90;
--color-cat-project: #3E6088;
--color-cat-work-note: #2D7478;
--color-cat-daily: #B07030;

/* Shiki — Newspaper */
--shiki-token-keyword: #8B3A3A;
--shiki-token-string: #2E6F57;
--shiki-token-function: #5B4A8A;
--shiki-token-comment: #888888;
--shiki-token-constant: #6B4226;
--shiki-token-punctuation: #333333;
--shiki-color-text: #333333;
```

### Pink — 체리 블로썸

```css
--color-bg-primary: #FFF5F7;
--color-bg-secondary: #FFE8ED;
--color-bg-tertiary: #FFD8E0;
--color-input-surface: #FFF0F4;
--color-text-primary: #2D1F22;
--color-text-secondary: #4D3B40;
--color-text-muted: #6E5459;
--color-border: #F4A8B8;
--color-accent: #E8496A;
--color-accent-hover: #D43860;
--color-accent-glow: rgba(232, 73, 106, 0.18);
--color-accent-subtle: rgba(232, 73, 106, 0.10);
--color-success: #3D7A40;
--color-warning: #A06E28;
--color-error: #C9384A;
--color-shadow: rgba(60, 20, 30, 0.15);

/* Category Colors */
--color-cat-ainews: #A34535;
--color-cat-study: #556653;
--color-cat-career: #756350;
--color-cat-project: #606075;
--color-cat-work-note: #4E6770;
--color-cat-daily: #8A6156;

/* Shiki — Cherry */
--shiki-token-keyword: #C9384A;
--shiki-token-string: #3A6A4C;
--shiki-token-function: #4B5B8A;
--shiki-token-comment: #8E6070;
--shiki-token-constant: #E8496A;
--shiki-token-punctuation: #2D1F22;
--shiki-color-text: #2D1F22;
```

## themeColors 동기화 포인트

테마 색상 변경 시 아래 3곳도 반드시 동기화:

| 파일 | 용도 |
|------|------|
| `MainLayout.astro` (line ~43) `tc` 객체 | FOUC 방지 — CSS 로드 전 배경색 |
| `Navigation.astro` (line ~301) `themeColors` | 브라우저 `meta[theme-color]` |
| `AdminSidebar.astro` (line ~217) `themeColors` | Admin 테마 전환 |

현재 값:
```
MainLayout:    { dark: '#18140F', light: '#F4F1EA', pink: '#FFF0F3', midnight: '#08090E' }
Navigation:    { dark: '#18140F', light: '#F4F1EA', pink: '#FFF0F3', midnight: '#08090E' }
AdminSidebar:  { dark: '#18140F', light: '#F4F1EA', pink: '#FFF0F3' }
```

## 원본 팔레트 (변경 전)

리팩터링 전 원본은 `vault/09-Implementation/plans/2026-03-16-theme-palette-refinement.md` 하단에 백업.
