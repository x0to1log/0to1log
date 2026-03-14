---
title: Mobile UX
tags:
  - design
  - mobile
  - responsive
source: docs/04_Frontend_Spec.md
---

# Mobile UX

모바일 퍼스트 반응형 설계.

> [!note] 0to1log의 주요 유입 경로는 SNS 공유(X, LinkedIn)이며 대부분 모바일 트래픽이다. **모바일을 기본 설계 대상으로, 데스크탑을 확장으로** 접근한다.

## Mobile-First 원칙

- Base CSS = 모바일 스타일
- `@media (min-width: 640px)` 이상에서 데스크탑 확장
- Persona Switcher 모바일: 아이콘 + 축약어 조합 (`🌱 비전공 / 📚 학습 / 🔧 현직`)
- 활성 탭만 accent-subtle 배경 하이라이트
- 각 탭 최소 터치 영역: 44px x 44px

## Responsive Differences

| 요소 | 데스크탑 | 모바일 (<640px) |
|---|---|---|
| Navigation | 풀 링크 + 아이콘 (top bar) | 햄버거 → 풀스크린 드로어 (backdrop blur) |
| Persona Switcher | "입문자 / 학습자 / 현직자" 풀 텍스트 | "🌱 입문 / 📚 학습 / 🔧 현직" 아이콘+축약 |
| 5블록 가이드 | 모두 펼침 상태 | 아코디언 (One-Liner만 기본 펼침) |
| 코드 블록 | 전체 표시 | 가로 스크롤 + "← 스크롤 →" 힌트 (1회) |
| Today's AI Pick | 2열 카드 그리드 | 1열 세로 스택 |
| Admin 에디터 (Phase 2) | 좌우 분할 | 편집 / 미리보기 탭 전환 |
| 검색 모달 | 중앙 모달 (max-width 600px) | 풀스크린 모달 |
| 피드백 위젯 | 인라인 | 스크롤 80%+ 시 sticky bar |
| 댓글 | 인라인 | 인라인 (textarea 높이 자동 확장) |

## Touch Interactions

- 모든 터치 타겟: 최소 **44px x 44px** (WCAG 2.5.5)
- 버튼 간 간격: 최소 **8px** (오터치 방지)
- 풀스크린 드로어: 왼쪽 엣지 스와이프 열기, 오른쪽 스와이프 닫기
- 코드 블록: 첫 번째 코드 블록에만 "← 스크롤 →" 오버레이 힌트 (3초 후 fade-out)

## Mobile Performance

- **이미지**: `loading="lazy"` + `srcset` 반응형 (모바일용 작은 해상도)
- **폰트**: Pretendard 동적 서브셋 사용 (전체 woff2 다운로드 방지)
- **애니메이션**: 모바일에서는 복잡한 spring → 간단한 fade로 대체
- **읽기 인디케이터**: 모바일에서는 하단 슬림 바 (40px), 본문 스크롤 시 fade-in

## Related

- [[Component-States]]
- [[AI-News-Page-Layouts]]
- [[Design-System]]
- [[Animations-&-Transitions]]
- [[Accessibility]]
