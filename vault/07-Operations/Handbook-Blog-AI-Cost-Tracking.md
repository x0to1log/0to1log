---
title: Handbook & Blog AI Cost Tracking
status: partially-implemented
created: 2026-03-14
updated: 2026-03-15
tags:
  - operations
  - cost-tracking
---

# Handbook & Blog AI Cost Tracking

## Current State

News Pipeline은 `pipeline_logs` 테이블에 **스테이지별** AI 호출 비용/토큰을 기록 중 (2026-03-15 구현).
- `_log_stage()` 헬퍼 함수로 각 LLM 호출마다 `tokens_used`, `cost_usd`, `model_used`, `input_tokens`, `output_tokens`, `duration_ms` 기록
- `debug_meta` JSONB에 LLM 입출력, attempt 횟수 등 상세 정보 포함
- 상세: [[Pipeline-Stage-Logging-Schema]]

Handbook과 Blog의 AI 호출은 비용 추적 **미구현**:
- **Handbook**: AI advisor (`/api/admin/ai/handbook-advise`), AI-suggested term 생성
- **Blog**: AI advisor (`/api/admin/blog/ai/advise`), AI translation (`/api/admin/blog/ai/translate`)

이 호출들은 에디터에서 on-demand로 실행되며, 현재 응답만 반환하고 비용을 기록하지 않음.

## Future Plan

### 1. 백엔드 로깅 인프라

News Pipeline의 `_log_stage()` 패턴을 Handbook/Blog AI 호출에도 적용:
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
- `backend/services/pipeline.py` — `_log_stage()` (News Pipeline 구현 완료)
- [[Pipeline-Stage-Logging-Schema]] — debug_meta 스키마 상세
