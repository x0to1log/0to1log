# Admin UI Redesign — Design Document

**Date**: 2026-03-08
**Status**: Approved

## Summary

어드민 UI를 Notion/Linear 스타일의 에디터 중심 인터페이스로 전면 리디자인.
투박한 현재 UI → 세련되고 집중력 있는 작업 환경으로 개선.

## Design Decisions

| 항목 | 결정 |
|------|------|
| 방향 | 에디터 중심 (Notion/Linear 스타일) |
| 범위 | 대시보드 + 에디터 + 전체 톤 |
| 색상 | 현재 사이트 테마(light/dark/pink) CSS 변수 활용 |
| 사이드바 | 풀 항목 (네비게이션 + 최근 편집 + 통계 + 사이트 보기/로그아웃) |

## Layout: Dashboard Home (`/admin`)

대시보드는 3-column 레이아웃으로 모든 정보를 한 눈에 제공.

```
┌──────────────────────────────────────────────────┐
│  Logo / Admin         사이트 보기 · 로그아웃       │
├──────────┬───────────────────────┬───────────────┤
│          │                       │               │
│  Posts   │  메인 콘텐츠 영역       │  통계 패널     │
│  Handbook│  (포스트/핸드북 리스트)  │  · 12 Posts   │
│          │                       │  · 8 Terms    │
│ ──────── │  + New Post            │  · 3 Draft    │
│ 최근 편집 │  검색 + 필터            │               │
│  · Post A│  ┌─────────────────┐  │ ──────────── │
│  · Term B│  │ 제목  상태  날짜  │  │  최근 활동    │
│  · Post C│  │ 제목  상태  날짜  │  │  · 편집 이력  │
│          │  │ ...             │  │               │
│          │  └─────────────────┘  │               │
└──────────┴───────────────────────┴───────────────┘
```

### Sidebar (~220px 고정)
- **네비게이션**: Posts, Handbook
- **최근 편집**: 최근 작업한 포스트/용어 3~5개 (빠른 접근)
- **통계**: 총 Posts 수, Terms 수, Draft 수
- **하단**: 사이트 보기 링크, 로그아웃

### Main Content (리스트)
- Notion 데이터베이스 스타일 테이블/카드
- 상단: `+ New Post` 버튼 + 검색 + 필터(상태, 카테고리)
- 각 행: 제목, 상태 뱃지(pill), 카테고리, 날짜
- 상태 뱃지: `Published` = 초록 pill, `Draft` = 회색 pill

### Right Panel (통계/활동)
- 간단한 카운트 통계
- 최근 활동 로그

## Layout: Editor Page (`/admin/edit/[slug]`)

에디터 페이지는 사이드바 없이 콘텐츠 편집에 집중.

```
┌──────────────────────────────────────────────────┐
│  ← Back    Post Title Here          Save Publish │
├──────────────────────────────────┬───────────────┤
│                                  │               │
│   카테고리 · 태그 (인라인)         │  AI Suggest.  │
│                                  │               │
│   ┌────────────────────────┐     │  · 제안 1      │
│   │                        │     │  · 제안 2      │
│   │   Milkdown Editor      │     │  · 요약 생성   │
│   │   (전체 높이, 집중 모드)  │     │               │
│   │                        │     │               │
│   │                        │     │               │
│   └────────────────────────┘     │               │
│                                  │               │
└──────────────────────────────────┴───────────────┘
```

### Top Bar
- **좌측**: ← 뒤로가기 (대시보드로)
- **중앙**: 제목 (인라인 편집, 큰 폰트, Notion "Untitled" 스타일)
- **우측**: Save 버튼, Publish/Unpublish 버튼

### Editor Area
- 제목 아래: 카테고리, 태그를 인라인 pill로 표시
- Milkdown Crepe 에디터: 넓은 영역, 충분한 높이
- Draft/Preview 토글: 상단 탭으로 전환

### AI Suggestions Panel (우측)
- 접었다 펼 수 있는 패널 (~280px)
- AI 제안, 요약 생성 등 (Phase 2 기능이지만 UI 자리 확보)
- 닫으면 에디터가 전체 너비 차지

## Layout: Handbook Editor (`/admin/handbook/edit/[slug]`)

포스트 에디터와 동일한 구조 원칙 적용.

- 사이드바 없이 편집 집중
- 상단: ← Back + Term 이름 + Save
- 다국어 탭 (KO/EN): 에디터 영역 내부
- 각 섹션(definition, explanation, example 등): 정리된 폼 레이아웃
- AI Suggestions 우측 패널 동일

## Style Guide

- **색상**: `global.css`의 기존 테마 CSS 변수 (`--color-bg-primary`, `--color-accent` 등)
- **사이드바 배경**: `--color-bg-secondary`
- **버튼**: rounded pill, hover 시 미세한 배경 변화
- **상태 뱃지**: pill 형태, Published=초록, Draft=회색
- **전환**: `transition: 150ms ease`
- **폰트**: 기존 serif 스택 유지
- **간격**: 여유로운 padding/margin (cramped → spacious)

## Files to Change

| File | Change |
|------|--------|
| `components/admin/AdminSidebar.astro` | **신규** — 사이드바 컴포넌트 |
| `components/admin/AdminHeader.astro` | 삭제 또는 breadcrumb으로 대체 |
| `pages/admin/index.astro` | 3-column 대시보드 레이아웃 |
| `pages/admin/handbook/index.astro` | 동일 패턴 적용 |
| `pages/admin/edit/[slug].astro` | 사이드바 없는 에디터 중심 레이아웃 |
| `pages/admin/handbook/edit/[slug].astro` | 동일 패턴 적용 |
| `styles/global.css` | `.admin-*` 클래스 전면 교체 |
