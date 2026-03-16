---
title: "Bugfix: 뉴스 파이프라인 cost/token 추적 및 핸드북 insert 검증"
tags:
  - bugfix
  - pipeline
  - cost-tracking
date: 2026-03-16
---

# Pipeline Bugfix Journal — 2026-03-16

> 뉴스 파이프라인의 cost/token 추적이 불완전하고, 핸드북 용어 insert가 실패해도 success로 기록되는 복합 버그 수정.

---

## 발견된 버그 목록

### 1. news_posts에 pipeline_tokens/pipeline_cost 미기록

- **파일**: `backend/services/pipeline.py` — `_generate_post()`
- **원인**: `news_posts` upsert 시 row dict에 `pipeline_tokens`, `pipeline_cost` 필드 누락
- **결과**: DB 컬럼은 존재하지만 항상 NULL
- **수정**: EN row에만 `cumulative_usage.get("tokens_used")` / `cumulative_usage.get("cost_usd")` 추가 (KO는 동일 LLM 호출이므로 제외)

### 2. pricing 모델명 매칭 순서 버그

- **파일**: `backend/services/agents/client.py` — `_resolve_pricing_key()`
- **원인**: dict 순회 시 "gpt-4o"가 "gpt-4o-mini"보다 먼저 매칭 → `"gpt-4o-mini-2024-07-18".startswith("gpt-4o")` = True
- **결과**: gpt-4o-mini 사용 시 ~17배 비싼 가격으로 기록
- **수정**: `sorted(key=len, reverse=True)` — 긴 키부터 매칭

### 3. pricing 테이블 불완전

- **파일**: `backend/services/agents/client.py` — `OPENAI_MODEL_PRICING_PER_1M`
- **원인**: gpt-4o, gpt-4o-mini만 존재. 새 모델 사용 시 cost_usd가 None
- **수정**: gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, o4-mini, o3, o3-mini 추가

### 4. 핸드북 용어 추출/생성 cost 추적 불완전

- **파일**: `backend/services/agents/advisor.py`
- **원인**:
  - `extract_terms_from_content()`: `completion_tokens`만 반환, `extract_usage_metrics()` 미사용
  - `_run_generate_term()`: run_id 없이 pipeline_logs에 직접 insert → Admin 페이지에서 보이지 않음
- **수정**:
  - `extract_terms_from_content()` → `extract_usage_metrics()` 사용하여 full usage dict 반환
  - `_run_generate_term()` → `merge_usage_metrics(usage1, usage2)` 반환
  - `pipeline.py` 호출부에서 `_log_stage(usage=...)` 전달

### 5. 파이프라인 중복 실행 시 데이터 고아 발생

- **파일**: `backend/routers/cron.py`, `backend/services/pipeline.py`
- **원인**: `pipeline_runs.run_key` UNIQUE 제약 → 같은 날짜 재실행 시 insert 실패하지만 warning으로 삼킴. 다른 기사가 뽑히면 이전 포스트가 고아로 남음
- **수정**:
  - `check_existing_batch()` — 기존 데이터 존재 여부 확인
  - `cleanup_existing_batch()` — force 시 기존 데이터 삭제 (published 보호)
  - cron 라우터: 409 Conflict (기존 데이터) / 422 (published 보호) 응답
  - Admin UI: confirm 다이얼로그로 덮어쓰기 확인

### 6. handbook_terms insert 결과 미검증 (가장 치명적)

- **파일**: `backend/services/pipeline.py` — `_extract_and_create_handbook_terms()`
- **원인**: `.insert(row).execute()` 결과를 확인하지 않음 → Supabase가 빈 응답 반환해도 success로 기록
- **결과**: pipeline_logs에 "handbook.auto_generate: success"지만 실제 DB에 용어 없음
- **수정**:
  - `result = supabase.table("handbook_terms").insert(row).execute()`
  - `if not result.data:` → failed로 기록
  - exception 시에도 `_log_stage("failed")` 기록
  - `news_posts` upsert에도 동일 패턴 적용

---

## 영향 범위

- **Backend**: `pipeline.py`, `client.py`, `advisor.py`, `cron.py`
- **Frontend**: `pipeline-analytics.astro`, `[runId].astro`, `run-pipeline.ts`, `pipelineTrigger.js`, `admin/index.astro`
- **테스트**: `test_handbook_advisor.py` 시그니처 업데이트

## 교훈

1. **Supabase insert 결과는 반드시 검증** — exception이 안 나도 data가 비어 있을 수 있음
2. **pricing 테이블은 새 모델 출시 때마다 업데이트** 필요
3. **run_id 없는 pipeline_logs는 Admin에서 보이지 않음** — 항상 run context 안에서 로깅
