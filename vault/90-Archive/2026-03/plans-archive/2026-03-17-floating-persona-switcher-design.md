# 플로팅 페르소나 전환 탭 — 디자인 문서

날짜: 2026-03-17

## 문제 정의

페르소나 전환 탭(초보자/학습자/전문가)이 아티클 상단에 정적으로 위치해, 글을 읽다가 수준이 맞지 않을 때 탭을 바꾸려면 상단까지 스크롤해야 하는 불편함이 있음. 또한 신규 방문자가 이 기능의 존재를 인지하기 어려움.

## 목표

- 글 읽는 도중 **언제든** 페르소나를 전환할 수 있게 함
- 기능의 **존재를 자연스럽게 인지**시킴 (신규 방문자 포함)
- 기존 UI(액션 바, 헤더)와 충돌 없이 독립적으로 동작

## 결정된 접근 방식: 하단 중앙 플로팅 pill

### 등장 조건

`IntersectionObserver`로 원래 `.persona-switcher`의 뷰포트 이탈을 감지.
- 원래 탭이 뷰포트 밖으로 나가면 → 플로팅 탭 등장
- 원래 탭이 다시 보이면 → 플로팅 탭 퇴장

### 시각 디자인

원래 `.persona-switcher` 스타일을 기반으로 아래 차이점 적용:
- `backdrop-filter: blur(8px)` + `box-shadow` 추가 (플로팅 느낌)
- 터치 타겟: 버튼 padding 살짝 확대 (모바일 44px 이상)
- 최초 등장 시 짧은 pulse 애니메이션 1회 (발견성 향상)

### 위치

| 환경 | 위치 |
|------|------|
| 모바일 | `position: fixed; bottom: 5.75rem + 0.75rem; left: 50%; transform: translateX(-50%)` |
| 데스크탑 | `position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%)` |

`z-index: 89` (기존 액션 바 z-index: 90 바로 아래)

### 등장/퇴장 애니메이션

- 등장: `translateY(12px) opacity:0` → `translateY(0) opacity:1` (250ms ease-out)
- 퇴장: `translateY(0) opacity:1` → `translateY(12px) opacity:0` (200ms ease-in)
- `prefers-reduced-motion`: 애니메이션 없이 즉시 show/hide

### 상태 동기화

- 플로팅 탭에서 변경 → 원래 탭 active 상태 동기화
- 원래 탭에서 변경 → 플로팅 탭 active 상태 동기화
- 기존 `newsprint:article-content-updated` 커스텀 이벤트 재활용

## 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/components/newsprint/NewsprintArticleLayout.astro` | 플로팅 탭 HTML + JS 추가 |
| `frontend/src/styles/global.css` | `.persona-float` CSS 추가 |
