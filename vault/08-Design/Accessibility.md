---
title: Accessibility
tags:
  - design
  - a11y
  - accessibility
source: docs/04_Frontend_Spec.md
---

# Accessibility

키보드 접근성, ARIA, 시맨틱 HTML.

## Keyboard Navigation

모든 인터랙티브 요소는 Tab으로 접근 가능해야 한다.

| 요소 | Tab 이동 | Enter/Space | Esc |
|---|---|---|---|
| Nav 링크 | 순서대로 포커스 | 해당 페이지로 이동 | - |
| Persona Switcher | 탭 간 이동 | 해당 페르소나 활성화 | - |
| 테마 토글 | 포커스 | Dark ↔ Light 전환 | - |
| Cmd+K 검색 | Cmd+K로 열기 | 선택된 결과로 이동 | 모달 닫기 |
| 댓글 작성 | textarea 포커스 | - (Enter=줄바꿈) | - |
| 좋아요 버튼 | 포커스 | 좋아요 토글 | - |
| 드롭다운 | 포커스 | 열기 | 닫기 |
| 5블록 아코디언 | 각 항목 포커스 | 펼치기/접기 토글 | - |

## Focus Styles

- `:focus-visible` → `outline: 2px solid var(--color-accent)`, `outline-offset: 2px`, `border-radius: 4px`
- `:focus:not(:focus-visible)` → `outline: none` (마우스 클릭 시 포커스 링 숨김)
- 모든 테마(dark, light, midnight)에서 대응

## ARIA Components

| 컴포넌트 | ARIA 적용 |
|---|---|
| Persona Switcher | `role="tablist"`, 각 탭 `role="tab"` + `aria-selected`, 본문 `role="tabpanel"` + `aria-labelledby` |
| 뉴스 온도 | `aria-label="뉴스 중요도: N단계 (5단계 중)"` |
| 테마 토글 | `aria-label` 동적 전환 ("다크 모드로 전환" / "라이트 모드로 전환") |
| 검색 모달 | `role="dialog"` + `aria-modal="true"` + `aria-label="글 검색"` |
| 피드백 위젯 | `aria-label="이 글이 도움이 되었나요?"`, 각 버튼 `aria-pressed` |
| 읽기 인디케이터 | `role="progressbar"` + `aria-valuenow` + `aria-label="읽기 진행률: N%, 약 M분 남음"` |
| 코드 블록 복사 | `aria-label="코드 복사"`, 복사 완료 시 `aria-live="polite"` 영역에 "복사되었습니다" |
| 댓글 결과 | 성공/실패 시 `aria-live="polite"` 영역으로 스크린 리더 알림 |

## Semantic HTML

- `<main>`, `<article>`, `<section>`, `<nav>`, `<aside>`, `<footer>` 시맨틱 태그 사용
- Heading hierarchy: `<h1>` → `<h2>` 순서 준수 (포스트 제목 → 소제목, Action Item, Critical Gotcha 등)
- 장식용 이미지: `alt=""` (빈 문자열) / 의미 있는 이미지: 설명적 `alt`
- 댓글 섹션: `<section aria-label="댓글">`

## Additional

- **스킵 네비게이션**: 페이지 최상단에 "본문으로 건너뛰기" 링크 (Tab 첫 포커스, 시각적으로 숨김, 포커스 시 노출)
- **언어 선언**: `<html lang="ko">`
- **동적 콘텐츠 알림**: 페르소나 전환, 댓글 추가 시 `aria-live="polite"` 사용
- **고대비 모드**: `prefers-contrast: more` 미디어 쿼리 대응 — 테두리 진하게, glow 효과 제거

## Related
- [[Design-System]] — 상위 디자인 시스템
- [[Mobile-UX]] — 접근성이 중요한 모바일
