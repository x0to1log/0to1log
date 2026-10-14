# Color Theme

> 3개 테마 컬러 시스템 (Soft Newsprint). 대상 파일: `frontend/src/styles/global.css` (`[data-theme=...]` 블록), `frontend/src/lib/theme.js`

## 테마 개요

| 테마 | 라벨 (KO / EN) | 성격 | 배경 | 텍스트 | 액센트 | colorScheme |
|------|------|------|------|------|------|------|
| **Light** (기본) | 종이 / Paper | 따뜻한 종이 | `#F7F4EE` | `#24211D` | 테라코타 `#B4472A` | light |
| **White** | 화이트 / White | 쿨 화이트 | `#FFFFFF` | `#16181B` | 블루 `#2448A8` | light |
| **Dark** | 다크 / Dark | 웜 잉크 | `#181715` | `#ECE7DD` | 코랄 `#E3774F` | dark |

- 토글 순서: light → white → dark.
- 저장값 `localStorage.theme`: 폐기된 `pink`는 `light`로, `midnight`는 `dark`로 마이그레이션된다. 저장값이 없으면 OS 설정을 따른다.
- 카테고리 색(`--color-cat-*`)은 모든 테마에서 `var(--color-accent)`로 통일.
- 모든 텍스트/액센트 쌍은 WCAG AA 통과 (`frontend/tests/theme-palette.test.cjs`가 강제).

## 팔레트

| 토큰 | light | white | dark |
|---|---|---|---|
| bg-primary | #F7F4EE | #FFFFFF | #181715 |
| bg-secondary | #EFEAE0 | #F3F5F8 | #121110 |
| bg-tertiary | #E6E0D3 | #E9EDF2 | #23211E |
| bg-card | #F2EEE6 | #FAFBFC | #1E1C1A |
| input-surface | #FBF9F5 | #FFFFFF | #1F1D1B |
| text-primary | #24211D | #16181B | #ECE7DD |
| text-secondary | #5A544B | #4D5057 | #B3ACA0 |
| text-muted | #6B6459 | #6B6F76 | #948D82 |
| border | #D9D2C5 | #E3E4E7 | #35322D |
| accent | #B4472A | #2448A8 | #E3774F |
| accent-hover | #9C3C22 | #1C3A8A | #EC8A65 |
| success | #2E6F57 | #2E6F57 | #6FA67A |
| warning | #855C08 | #855C08 | #D4A843 |
| error | #A63A2E | #B3362F | #E07067 |

Shiki 토큰: light/white는 같은 종이 계열(keyword `#8B3A3A`, string `#2E6F57`, function `#5B4A8A`), dark는 keyword `#E3A27C`, string `#8FAE7E`, function `#B8A9D4`. 주석색은 AA 확보를 위해 light `#615A50`, white `#5E6269`, dark `#948D82`.

## 단일 소스 `theme.js`

`frontend/src/lib/theme.js`가 테마 이름·색·마이그레이션의 유일한 정의다.

| export | 용도 |
|---|---|
| `THEMES` | 순환 순서 `['light','white','dark']` |
| `THEME_COLORS` | `meta[theme-color]` 값 (= `--color-bg-primary`) |
| `LEGACY_THEMES` | `{ pink: 'light', midnight: 'dark' }` |
| `readTheme` / `applyTheme` / `nextTheme` | 읽기(+레거시 값 마이그레이션) / 적용 / 다음 테마 |
| `THEME_BOOT_SCRIPT` | FOUC 방지 인라인 스크립트 문자열. `MainLayout`과 `auth/callback`에 주입 |

테마 색을 바꿀 때는 `theme.js`의 `THEME_COLORS`와 `global.css`의 `--color-bg-primary`를 함께 맞춘다. Navigation / AdminSidebar는 `theme.js`를 import해서 쓴다 (별도 색 객체 없음).
