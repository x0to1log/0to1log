---
title: Handbook & Blog AI Cost Tracking
status: planned
created: 2026-03-14
tags:
  - operations
  - cost-tracking
  - future
---

# Handbook & Blog AI Cost Tracking

## Current State

News Pipeline만 `pipeline_logs` 테이블에 AI 호출 비용/토큰을 기록 중.

Handbook과 Blog의 AI 호출은 비용 추적 미구현:
- **Handbook**: AI advisor (`/api/admin/ai/handbook-advise`), AI-suggested term 생성
- **Blog**: AI advisor (`/api/admin/blog/ai/advise`), AI translation (`/api/admin/blog/ai/translate`)

이 호출들은 에디터에서 on-demand로 실행되며, 현재 응답만 반환하고 비용을 기록하지 않음.

## Future Plan

### 1. 백엔드 로깅 인프라

각 AI API 호출에 `log_pipeline_stage()` 또는 유사한 로깅 함수를 추가:
- `pipeline_type` prefix: `handbook.advise`, `blog.advise`, `blog.translate`
- `tokens_used`, `cost_usd`, `model_used` 기록
- `debug_meta`에 input/output 토큰 분리 기록

### 2. Analytics 탭 확장

`/admin/pipeline-analytics` 페이지의 Handbook/Blog 탭에:
- AI 호출 비용 시계열 차트 추가
- 호출 빈도, 평균 비용, 모델 사용 통계 추가
- 현재 "AI cost tracking planned for a future phase" placeholder 교체

### 선행 조건

- Handbook/Blog AI 호출 로깅 인프라 구축
- `pipeline_logs` 테이블이 non-pipeline 호출도 수용 가능한지 검토 (또는 별도 테이블)

## Related

- [[Pipeline-Bilingual-Generation-Idea]]
- `frontend/src/pages/admin/pipeline-analytics.astro`
- `backend/services/pipeline.py` — `log_pipeline_stage()`
