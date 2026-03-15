---
title: Current Sprint
tags:
  - meta
  - sprint
---

# CURRENT SPRINT — Pipeline v2 Rewrite

> **스프린트 시작:** 2026-03-14
> **목표:** News Pipeline v2 — Expert-First 2-Call Cascade + 전문 번역으로 전면 재작성
> **참조:** `docs/03_Backend_AI_Spec.md` v4.0, `docs/IMPLEMENTATION_PLAN.md`
> **이전 스프린트:** Phase 3A-SEC 완료 (2026-03-09)

---

> [!important] 핵심 변경
> - Business 생성: 5 calls → **2-Call Expert-First Cascade**
> - 번역: 섹션별 8-26 calls → **전문 번역 2 calls** (포스트당 1회)
> - 파이프라인: 병렬 → **순차**, artifact 시스템 제거
> - 페르소나 분량: 차등(300-1200자) → **동일(min 5,000자)**, 서술 방식으로만 차별화
> - 코드: ~3,565줄 → ~1,315줄 (63% 감소 목표)

## 스프린트 완료 게이트

- [ ] `prompts.py` — BUSINESS_EXPERT_PROMPT + BUSINESS_DERIVE_PROMPT + 단순화된 TRANSLATE_SYSTEM_PROMPT
- [ ] `models/business.py` — 모든 persona min 5,000자로 통일
- [ ] `business.py` — Expert-First 2-Call Cascade (~200줄)
- [ ] `translate.py` — 전문 번역 (~150줄)
- [ ] `pipeline.py` — 순차 오케스트레이터, artifact 제거 (~600줄)
- [ ] Frontend — pipeline-runs 페이지 artifact UI 제거
- [ ] `pytest backend/tests/` 전체 통과
- [ ] 태스크 전체 `상태=done` + `체크=[x]` 일치

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시점 | Owner |
|---|---|---|---|
| PV2-PROMPT-01 | doing | 2026-03-14 | Amy |

---

## 태스크 (실행 순서)

### 1. prompts.py 재작성 `[PV2-PROMPT-01]`
- **체크:** [ ]
- **상태:** doing
- **목적:** Business 프롬프트 2개 분리 + 번역 프롬프트 단순화
- **산출물:** `backend/services/agents/prompts.py`
- **완료 기준:**
  - `RANKING_SYSTEM_PROMPT` 유지
  - `RESEARCH_SYSTEM_PROMPT` 유지 (필요 시 정리)
  - `BUSINESS_SYSTEM_PROMPT` → `BUSINESS_EXPERT_PROMPT` + `BUSINESS_DERIVE_PROMPT`
  - `TRANSLATE_SYSTEM_PROMPT` → 전문 번역용으로 단순화
- **검증:** Python import 에러 없음
- **의존성:** 없음 (docs/03 v4 스펙 기반)

### 2. models/business.py 업데이트 `[PV2-MODEL-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** persona 최소 길이 통일 + 불필요 상수 제거
- **산출물:** `backend/models/business.py`
- **완료 기준:**
  - `EN_MIN_CONTENT_CHARS = 5000` (기존 3000)
  - `EN_MIN_ANALYSIS_CHARS = 2500` (기존 2000)
  - 섹션별 shrink ratio/floor 상수 제거
- **검증:** `python -c "from backend.models.business import BusinessPost"` 성공
- **의존성:** 없음

### 3. business.py 재작성 `[PV2-BIZ-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** Expert-First 2-Call Cascade로 전면 재작성
- **산출물:** `backend/services/agents/business.py` (~200줄)
- **완료 기준:**
  - `generate_business_expert()`: Call 1 — fact_pack + source_cards + analysis + expert
  - `derive_business_personas()`: Call 2 — expert 기반 learner + beginner 파생
  - `generate_business_post()`: 위 2개 순차 호출 + BusinessPost 조립
  - 단순 2회 재시도 (포스트 전체 단위)
  - `BusinessGenerationError`, partial_state, stage 로직 제거
- **검증:** `python -c "from backend.services.agents.business import generate_business_post"` 성공
- **의존성:** PV2-PROMPT-01, PV2-MODEL-01

### 4. translate.py 재작성 `[PV2-TRANS-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 전문 번역으로 전면 재작성
- **산출물:** `backend/services/agents/translate.py` (~150줄)
- **완료 기준:**
  - `translate_post()`: 포스트 전체 마크다운 1회 호출 번역
  - 섹션 분할/shrink ratio/recovery pass 전체 제거
  - metadata 번역 유지 (title, excerpt, tags, guide_items)
  - 단순 2회 재시도 (포스트 전체 단위)
- **검증:** `python -c "from backend.services.agents.translate import translate_post"` 성공
- **의존성:** PV2-PROMPT-01

### 5. pipeline.py 재작성 `[PV2-PIPE-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 순차 오케스트레이터로 전면 재작성
- **산출물:** `backend/services/pipeline.py` (~600줄)
- **완료 기준:**
  - 순차 흐름: Research EN → KO → Business Expert → Derive → KO → Editorial
  - `acquire_pipeline_lock` / `release_pipeline_lock` 유지
  - `_save_post`, `log_pipeline_stage` 유지
  - Novelty gate (중복 방지) 유지
  - Resume: "저장된 EN 재사용 → KO만 재번역" 단순 패턴
  - Artifact 시스템 전체 제거 (partial state, recovery)
- **검증:** `python -c "from backend.services.pipeline import run_daily_pipeline"` 성공
- **의존성:** PV2-BIZ-01, PV2-TRANS-01

### 6. 프론트엔드 최소 수정 `[PV2-FE-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** pipeline-runs 페이지에서 artifact resume UI 제거
- **산출물:** `frontend/src/pages/admin/pipeline-runs/[runId].astro`
- **완료 기준:** artifact 관련 UI 요소 제거, 나머지 정상 렌더링
- **검증:** `cd frontend && npm run build` 0 error
- **의존성:** 없음

### 7. 테스트 업데이트 `[PV2-TEST-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** v2 아키텍처에 맞게 테스트 파일 업데이트
- **산출물:** `backend/tests/` 관련 파일
- **완료 기준:**
  - `test_business_retry.py` — 단일 호출 패턴으로 변경
  - `test_business_fact_pack.py` — 통합 출력 테스트
  - `test_translation_strategy.py` — 전문 번역 테스트
  - `test_pipeline_resume.py` — artifact 테스트 제거, EN 재사용 테스트 유지
- **검증:** `cd backend && python -m pytest tests/ -v` 전체 통과
- **의존성:** PV2-PIPE-01

### 8. 전체 검증 `[PV2-VERIFY-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 전체 테스트 통과 + 빌드 확인
- **산출물:** 테스트 결과 로그
- **완료 기준:**
  - `cd backend && python -m pytest tests/ -v` 전체 통과
  - `cd frontend && npm run build` 0 error
  - 코드 총 줄수 목표 대비 확인
- **검증:** 위 명령어 모두 성공
- **의존성:** PV2-TEST-01, PV2-FE-01

---

## Related

- [[Implementation-Plan]] — Phase 흐름 + 게이트
- [[AI-News-Pipeline-Design]] — v4 파이프라인 다이어그램
- [[Quality-Gates-&-States]] — 재시도 정책
- [[Prompt-Guides]] — Expert-First Cascade 프롬프트 설명
- [[Cost-Model-&-Stage-AB]] — v4 비용 테이블
