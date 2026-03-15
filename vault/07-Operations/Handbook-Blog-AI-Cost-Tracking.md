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

### 1. Handbook 비용 추적 (구현 중)

Generate 액션이 2회 LLM 호출로 분리됨에 따라 각각 별도 기록:

| pipeline_type | 용도 | 기록 내용 |
|--------------|------|---------|
| `handbook.generate.basic` | 메타 + Basic 생성 (호출 1) | input/output 토큰, cost, model, debug_meta |
| `handbook.generate.advanced` | Advanced 생성 (호출 2) | input/output 토큰, cost, model, debug_meta |
| `handbook.extract` | 뉴스 → 용어 자동 추출 | 추출된 용어 목록, 토큰, 비용 |

- `pipeline_runs` 없이 `pipeline_logs` 단독 기록 (on-demand 실행)
- `pipeline_type` prefix로 News(`collect`, `rank`, ...) vs Handbook(`handbook.*`) 필터링
- **자동 vs 수동 구분**: `debug_meta.source` = `"pipeline"` (뉴스 파이프라인 자동 추출) 또는 `"manual"` (어드민 에디터 수동 생성)

### 1-1. 자동/수동 분리 그래프 (구현 예정)

Analytics Handbook 탭에:
- **자동 비용 시계열**: `debug_meta.source = "pipeline"` 필터
- **수동 비용 시계열**: `debug_meta.source = "manual"` 필터
- **합산 비용 시계열**: 두 source 합산
- 기존 summary 카드 + 호출 테이블 유지

### 2. Blog 비용 추적 (미구현)

| pipeline_type | 용도 |
|--------------|------|
| `blog.advise` | Blog AI advisor |
| `blog.translate` | Blog 번역 |

### 3. Analytics 탭 확장

`/admin/pipeline-analytics` 페이지에 탭 추가:
- **News** (현재) — 뉴스 파이프라인 비용/토큰
- **Handbook** — 용어 생성/추출/번역 비용/토큰
- **Blog** — 블로그 AI 비용/토큰 (향후)

### 선행 조건

- ~~`pipeline_logs` 테이블이 non-pipeline 호출도 수용 가능한지 검토~~ → **수용 가능 확인** (pipeline_type prefix로 구분)
- Handbook Generate 2회 호출 분리 구현 → [[Handbook-Prompt-Redesign]] 참조

## Related

- [[Pipeline-Bilingual-Generation-Idea]]
- `frontend/src/pages/admin/pipeline-analytics.astro`
- `backend/services/pipeline.py` — `_log_stage()` (News Pipeline 구현 완료)
- [[Pipeline-Stage-Logging-Schema]] — debug_meta 스키마 상세
