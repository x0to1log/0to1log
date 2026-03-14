---
title: Animations & Transitions
tags:
  - design
  - animation
  - transitions
source: docs/04_Frontend_Spec.md
---

# Animations & Transitions

페이지 전환과 마이크로 인터랙션.

## View Transitions API

- Astro 내장 지원: `transitions: true` 설정
- 페이지 간 이동 시 부드러운 crossfade
- 글 리스트 → 글 상세: 카드가 확장되는 느낌의 morph 트랜지션
- `transition:name` 디렉티브로 요소 간 매핑

## Motion One Micro-Interactions

| 요소 | 애니메이션 | 트리거 |
|---|---|---|
| Hero 타이포그래피 | 글자별 staggered fade-in + slide-up | 로드 시 |
| 카드 목록 | staggered fade-in (각 100ms 딜레이) | 스크롤 진입 시 |
| Persona Switcher | 언더라인 spring slide | 탭 클릭 시 |
| 본문 전환 | crossfade (opacity, 150ms) | 페르소나 전환 시 |
| 버튼 호버 | scale(1.02) + glow 확산 | 호버 시 |
| 뉴스 온도 바 | width 0→100% ease-out | 카드 진입 시 |
| 읽기 인디케이터 | fade-in/out + 바 높이 연동 | 본문 스크롤 진입/이탈 시 |

## Reduced Motion

`prefers-reduced-motion: reduce` 미디어 쿼리 대응:
- 모든 `animation-duration`과 `transition-duration`을 `0.01ms`로 강제
- 모바일에서는 복잡한 spring → 간단한 fade로 대체

> [!important] 모든 motion은 `prefers-reduced-motion` 체크 필수. 성능 우선: `transform`과 `opacity`만 애니메이션 (layout thrashing 방지).

## Related

- [[Design-System]]
- [[Mobile-UX]]
- [[Frontend-Stack]]
- [[Accessibility]]
