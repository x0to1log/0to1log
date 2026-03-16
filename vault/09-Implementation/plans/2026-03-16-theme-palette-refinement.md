# Theme Palette Refinement

> 4개 테마 색상 팔레트 조정 계획. 브레인스토밍 결과 정리.

## 변경 대상

| 테마 | 방향 | 상태 |
|------|------|------|
| **Dark** | 딥 브라운 — 배경만 더 깊게, 톤 유지 | ✅ 확정 |
| **Midnight** | 쿨 잉크 — 블루-그레이 언더톤 전환 | ✅ 확정 |
| **Light** | 배경 간격 확대 + 코퍼 액센트 + 카테고리 색상환 분배 | ✅ 확정 |
| **Pink** | 변경 없음 | ✅ 유지 |

---

## Dark — 딥 브라운

배경만 ~30% 더 어둡게. 텍스트, 액센트, 카테고리 전부 동일.

### 배경

| 역할 | 현재 | 변경 |
|------|------|------|
| primary | `#1F1A17` | `#18140F` |
| secondary | `#191512` | `#120F0C` |
| tertiary | `#25201C` | `#1F1A15` |
| input-surface | `#2A2420` | 비례 조정 필요 |
| border | `#433B32` | `#3D3529` |

### 텍스트 (변경 없음)

- primary: `#E0D8C3`
- secondary: `#A39D8E`
- muted: `#948C7E`

### 액센트 & 상태 (변경 없음)

- accent: `#C3A370` / hover: `#D4B882`
- success: `#5A8E5D` / warning: `#D4A843` / error: `#A8524B`

### 카테고리 (변경 없음)

기존 값 유지.

### Shiki (변경 없음)

기존 Warm Sepia 팔레트 유지.

---

## Midnight — 쿨 잉크

순수 블랙(#000) → 블루-그레이 언더톤. 텍스트를 쿨 실버로, 액센트를 스틸 블루로 전환. Dark(웜 골드)과 확실히 차별화.

### 배경

| 역할 | 현재 | 변경 |
|------|------|------|
| primary | `#000000` | `#08090E` |
| secondary | `#111111` | `#101218` |
| tertiary | `#1C1C1C` | `#1A1C25` |
| input-surface | `#0D0D0D` | 비례 조정 필요 |
| border | `#5A5348` | `#2E3242` |

### 텍스트

| 역할 | 현재 | 변경 |
|------|------|------|
| primary | `#D1C7B7` (웜크림) | `#C8CDD8` (쿨실버) |
| secondary | `#B8AEA0` | `#A0A6B4` |
| muted | `#A0968A` | `#7E8596` |

### 액센트 & 상태

| 역할 | 현재 | 변경 |
|------|------|------|
| accent | `#C3A370` (골드) | `#8EAAC8` (스틸블루) |
| accent-hover | `#D4B882` | 비례 조정 필요 |
| accent-glow | `rgba(195,163,112,0.15)` | `rgba(142,170,200,0.15)` |
| accent-subtle | `rgba(195,163,112,0.08)` | `rgba(142,170,200,0.08)` |
| success | `#52875A` | `#4E9A6B` |
| warning | `#C99B38` | `#C9A044` |
| error | `#A04842` | `#B85450` |

### 카테고리 — 쿨톤 시프트

| 카테고리 | 현재 | 변경 |
|----------|------|------|
| ai-news | `#D46A58` | `#D06858` |
| study | `#7A8B78` | `#6E9682` |
| career | `#A09080` | `#8C94AA` |
| project | `#8888A0` | `#8282AF` |
| work-note | `#6E8C92` | `#6496AA` |
| daily | `#A97C68` | `#AA8282` |

### Shiki — 쿨 잉크 팔레트 (조정 필요)

기존 Warm Sepia에서 쿨 방향으로 시프트. 구체적 값은 구현 시 결정.

---

## Light — 배경 간격 확대 + 코퍼 액센트 + 카테고리 분배

문제: ① 카테고리 색이 갈색 계열로 뭉침 ② 배경 3단계 구분 약함 ③ 브라운 액센트가 본문에 묻힘.

### 배경 — 단계 간격 넓히기

| 역할 | 현재 | 변경 |
|------|------|------|
| primary | `#F4F1EA` | `#F4F1EA` (유지) |
| secondary | `#E9E4D9` | `#E3DCCC` |
| tertiary | `#DDD8CC` | `#D3CCB8` |
| input-surface | `#E9E4D9` | `#EAE5D5` |
| border | `#B5AA9C` | `#ADA192` |

### 텍스트 (변경 없음)

- primary: `#333333`
- secondary: `#555555`
- muted: `#736B63`

### 액센트 — 깊은 코퍼

| 역할 | 현재 | 변경 |
|------|------|------|
| accent | `#8B5F3C` (머드브라운) | `#A85A2A` (깊은코퍼) |
| accent-hover | `#A0724D` | `#BE6830` |
| accent-glow | `rgba(139,95,60,0.15)` | `rgba(168,90,42,0.15)` |
| accent-subtle | `rgba(139,95,60,0.08)` | `rgba(168,90,42,0.08)` |

### 상태색 (변경 없음)

- success: `#2E6F57` / warning: `#B8860B` / error: `#8B3A3A`

### 카테고리 — 색상환 고르게 분배

| 카테고리 | 현재 | 변경 | 색상 계열 |
|----------|------|------|----------|
| ai-news | `#993D30` | `#B03E2E` | 빨강 (채도↑) |
| study | `#4D5E4B` | `#3A7348` | 초록 (채도↑) |
| career | `#6B5B4B` | `#6B5B90` | 보라 (갈색→보라) |
| project | `#585870` | `#3E6088` | 파랑 (더 선명) |
| work-note | `#45626A` | `#2D7478` | 틸 (채도↑) |
| daily | `#7B5648` | `#B07030` | 앰버 (갈색→오렌지) |

### Shiki (변경 없음)

기존 Newspaper 팔레트 유지. accent 관련 토큰(`--shiki-token-constant`)만 코퍼로 동기화.

---

## Pink — 변경 없음

현재 팔레트 유지.

---

## 원본 팔레트 (변경 전 백업)

### Dark (원본)

```css
--color-bg-primary: #1F1A17;
--color-bg-secondary: #191512;
--color-bg-tertiary: #25201C;
--color-input-surface: #2A2420;
--color-text-primary: #E0D8C3;
--color-text-secondary: #A39D8E;
--color-text-muted: #948C7E;
--color-border: #433B32;
--color-accent: #C3A370;
--color-accent-hover: #D4B882;
--color-accent-glow: rgba(195, 163, 112, 0.15);
--color-accent-subtle: rgba(195, 163, 112, 0.08);
--color-success: #5A8E5D;
--color-warning: #D4A843;
--color-error: #A8524B;
--color-shadow: rgba(0, 0, 0, 0.35);
--color-cat-ainews: #D46A58;
--color-cat-study: #7A8B78;
--color-cat-career: #A09080;
--color-cat-project: #8888A0;
--color-cat-work-note: #6E8C92;
--color-cat-daily: #A97C68;
```

### Midnight (원본)

```css
--color-bg-primary: #000000;
--color-bg-secondary: #111111;
--color-bg-tertiary: #1C1C1C;
--color-input-surface: #0D0D0D;
--color-text-primary: #D1C7B7;
--color-text-secondary: #B8AEA0;
--color-text-muted: #A0968A;
--color-border: #5A5348;
--color-accent: #C3A370;
--color-accent-hover: #D4B882;
--color-accent-glow: rgba(195, 163, 112, 0.15);
--color-accent-subtle: rgba(195, 163, 112, 0.08);
--color-success: #52875A;
--color-warning: #C99B38;
--color-error: #A04842;
--color-shadow: rgba(0, 0, 0, 0.6);
--color-cat-ainews: #D46A58;
--color-cat-study: #7A8B78;
--color-cat-career: #A09080;
--color-cat-project: #8888A0;
--color-cat-work-note: #6E8C92;
--color-cat-daily: #A97C68;
```

### Light (원본)

```css
--color-bg-primary: #F4F1EA;
--color-bg-secondary: #E9E4D9;
--color-bg-tertiary: #DDD8CC;
--color-input-surface: #E9E4D9;
--color-text-primary: #333333;
--color-text-secondary: #555555;
--color-text-muted: #736B63;
--color-border: #B5AA9C;
--color-accent: #8B5F3C;
--color-accent-hover: #A0724D;
--color-accent-glow: rgba(139, 95, 60, 0.15);
--color-accent-subtle: rgba(139, 95, 60, 0.08);
--color-success: #2E6F57;
--color-warning: #B8860B;
--color-error: #8B3A3A;
--color-shadow: rgba(43, 36, 26, 0.12);
--color-cat-ainews: #993D30;
--color-cat-study: #4D5E4B;
--color-cat-career: #6B5B4B;
--color-cat-project: #585870;
--color-cat-work-note: #45626A;
--color-cat-daily: #7B5648;
```

### themeColors 객체 (원본)

```
MainLayout.astro:  { dark: '#241F1C', light: '#F4F1EA', pink: '#FFF0F3', midnight: '#1A1A1A' }
Navigation.astro:  { dark: '#1F1A17', light: '#F4F1EA', pink: '#FFF0F3', midnight: '#1A1A1A' }
AdminSidebar.astro: { dark: '#1F1A17', light: '#F4F1EA', pink: '#FFF0F3' }
```

---

## 참고

- 대상 파일: `frontend/src/styles/global.css` (lines 48-206)
- Navigation.astro, MainLayout.astro의 `themeColors` 객체도 동기화 필요
- WCAG AA 4.5:1 대비비 준수 확인 필요
