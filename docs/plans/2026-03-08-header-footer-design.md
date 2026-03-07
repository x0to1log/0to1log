# Header/Footer Navigation Redesign — Design Doc

**Date:** 2026-03-08
**Author:** Amy (Solo)

## Problem

1. 푸터 카테고리 링크(AI News/Study/Career/Project)가 리스트 페이지 `NewsprintCategoryFilter`와 완전 중복
2. Portfolio가 비핵심 showcase surface인데 헤더에서 주요 네비게이션 공간 차지
3. 향후 사용자 로그인 + 앱 전환 시 네비게이션 요소가 늘어나는 것에 대한 IA 정리 필요

## Decision

**A안 채택 — 콘텐츠 네비게이션 유지 + 정리**

### Header

```
[0to1log]    [Log] [Handbook]     [🌙] [EN/한] [Sign In / 👤▾]
```

- Portfolio 제거 (비핵심)
- Log · Handbook 유지 (두 핵심 독립 섹션)
- 유틸리티: 테마 · 언어 · 로그인/아바타 드롭다운

### Footer

```
About · Portfolio · RSS
© 2026 0to1log. All rights reserved.
```

- 카테고리 링크 완전 제거 (CategoryFilter와 중복)
- 메타/보조 링크로 전환: About, Portfolio(여기서 접근 가능), RSS

### App Bottom Tab Mapping (Future)

| Web | App |
|-----|-----|
| Header: Log | Log tab |
| Header: Handbook | Handbook tab |
| Dropdown: My Library | Library tab |
| Dropdown: Sign In/Out | Profile tab |
| Footer: About/Portfolio/RSS | Settings or Profile sub |

## Alternatives Considered

- **B안 (유틸리티 헤더 + 섹션 서브바):** 역할 분리는 명확하지만 높이 2줄 차지
- **C안 (햄버거 통합):** 가장 깔끔하지만 핵심 섹션 발견성이 떨어짐

## Scope

- `Navigation.astro`: Portfolio 링크 1줄 제거
- `Footer.astro`: 카테고리 배열 → 메타 링크 배열로 교체
