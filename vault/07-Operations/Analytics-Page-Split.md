---
title: Analytics Page Split — Pipeline vs Site
status: in-progress
created: 2026-03-14
tags:
  - operations
  - analytics
  - admin
---

# Analytics Page Split

## 결정

기존 `/admin/pipeline-analytics`를 두 페이지로 분리:

| 페이지 | URL | 목적 |
|--------|-----|------|
| Pipeline Costs | `/admin/pipeline-analytics` | AI 파이프라인 비용/토큰/품질 추적 |
| Site Analytics | `/admin/analytics` | 컨텐츠 통계 + GA4 + Clarity |

## Pipeline Costs (`/admin/pipeline-analytics`)

기존 News 탭 내용만 유지:
- 5개 stat 카드 (Runs, Total Cost, Avg Cost, Tokens, Quality)
- 4개 Chart.js 차트 (Cost/Run, Stacked Cost, Tokens, Quality Trend)
- Stage Statistics 테이블
- 향후 Handbook/Blog AI 비용 로깅 추가 시 탭 확장 → [[Handbook-Blog-AI-Cost-Tracking]]

## Site Analytics (`/admin/analytics`)

### Phase 1 (즉시 구현)
- 컨텐츠 통계: Handbook terms 현황, Blog posts 현황 (기존 탭 내용 이동)
- Clarity 외부 링크 바로가기
- GA4 placeholder (서비스 계정 설정 전)

### Phase 2 (Google Cloud 서비스 계정 설정 후)
- GA4 Data API 연동: 페이지뷰, 세션, Top Pages, 트래픽 소스
- 백엔드 엔드포인트: `/api/admin/analytics/ga4`
- Python `google-analytics-data` 패키지
- 필요: Google Cloud 서비스 계정 JSON 키 → Railway 환경변수

## Sidebar 변경

- "Pipeline Costs" → `/admin/pipeline-analytics`
- "Site Analytics" → `/admin/analytics`

## Related

- [[Handbook-Blog-AI-Cost-Tracking]]
- `frontend/src/pages/admin/pipeline-analytics.astro`
- `frontend/src/pages/admin/analytics.astro` (신규)
- `frontend/src/components/admin/AdminSidebar.astro`
