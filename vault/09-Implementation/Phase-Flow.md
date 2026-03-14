---
title: Phase Flow
tags:
  - implementation
  - phases
  - frontend
source: docs/04_Frontend_Spec.md
---

# Phase Flow

프론트엔드 구현의 Phase별 범위와 마일스톤.

## Phase 1a — 뼈대 (2-3주)

| 기능 | 완료 기준 |
|---|---|
| Astro + Tailwind 초기 세팅 + 3테마 CSS 변수 | 테마 전환 시 모든 토큰 정상 반영 |
| Shiki css-variables 코드 블록 구문 강조 | 3테마 모두 구문 강조 정상, 테마 전환 시 깜빡임 없음 |
| 폰트 로딩 + 렌더링 테스트 (5개 항목) | 라이트 모드 코드 블록 가독성 포함 전부 통과 |
| BaseLayout (Nav + Footer + 스킵 네비게이션) | 데스크탑/모바일 반응형, 키보드 접근성 |
| Home (Hero + 하드코딩 더미 포스트) | 더미 데이터로 레이아웃 확인 |
| Vercel 배포 + 도메인 연결 (0to1log.com) | 프로덕션 URL 접속 가능 |

> [!note] Phase 1a 마일스톤
> 빈 껍데기지만 배포된 사이트. 테마, 폰트, 레이아웃 문제를 일찍 발견할 수 있다.

## Phase 1b — 데이터 연결 (2-3주)

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

> [!note] Phase 1b 마일스톤
> 실제 데이터가 연결된 MVP. 수동 포스트로 사이트 운영 가능.

## Phase 2 — AI 연동 UI

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

## Phase 3 — 고도화

| 기능 |
|---|
| AI Semantic Search (Cmd+K → `FastAPI /api/search/semantic` → pgvector) |
| Dynamic OG Image |
| Highlight to Share |
| Portfolio 인터랙티브 다이어그램 |
| AI Ops Dashboard UI |

## Phase 4 — 커뮤니티

| 기능 |
|---|
| 포인트 시스템 UI (`FastAPI /api/community/*`) |
| 돼지저금통 UI |
| Prediction Game UI (퀴즈/베팅, `FastAPI /api/community/*`) |
| 구독 권한 체크 UI (`FastAPI /api/subscription/me/access`) |

## Related

- [[Active-Sprint]] — 현재 진행 중인 태스크
- [[Implementation-Plan]] — 전체 구현 계획
- [[Frontend-Stack]] — 프론트엔드 기술 스택
- [[Checklists-&-DoD]] — 완료 기준 체크리스트
- [[Design-System]] — Phase 1a에서 구현하는 디자인 토큰
- [[AI-News-Page-Layouts]] — Phase 2에서 구현하는 페이지 레이아웃
