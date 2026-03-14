# ACTIVE SPRINT — AI News Pipeline v2

> **스프린트 시작:** 2026-03-15
> **목표:** AI News Pipeline v2 백엔드 구현 (수집 → 팩트 추출 → 3 페르소나 생성 → 저장)
> **설계 참조:** `vault/04-AI-System/AI-News-Pipeline-v2-Design.md`
> **이전 스프린트:** Phase 3A-SEC — 2026-03-09 게이트 전체 통과

---

## 스프린트 완료 게이트

- [ ] 파이프라인 1회 실행 → research + business 포스트 draft 저장 성공
- [ ] 3 페르소나 × 2 언어(EN+KO) 본문이 news_posts에 저장됨
- [ ] 에러 처리: 인프라 에러 재시도, 길이 미달 시 draft 저장 (파이프라인 안 죽음)
- [ ] `ruff check .` 통과
- [ ] `pytest tests/ -v` 통과
- [ ] Railway 배포 후 cron 트리거로 실제 실행 확인

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시점 | Owner |
|---|---|---|---|
| - | - | - | - |

---

## 태스크 (실행 순서)

### 1. Pydantic 모델 정의 `[NP2-MODEL-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 팩트 추출 결과, 페르소나 출력 JSON의 스키마 정의
- **산출물:** `backend/models/news_pipeline.py` (신규)
- **완료 기준:** FactPack, PersonaOutput, PipelineResult 모델 정의 + ruff 통과
- **의존성:** 없음

### 2. 뉴스 수집 모듈 `[NP2-COLLECT-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** Tavily API로 AI 뉴스 후보 수집 + 중복 제거
- **산출물:** `backend/services/news_collection.py` (신규)
- **완료 기준:** Tavily 호출 → 후보 리스트 반환 + 테스트
- **의존성:** 없음

### 3. LLM 랭킹 `[NP2-RANK-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 후보 뉴스를 LLM이 평가 → research 1건 + business 1건 선정
- **산출물:** `backend/services/agents/ranking.py` (신규)
- **완료 기준:** 랭킹 결과 반환 + 테스트
- **의존성:** NP2-COLLECT-01

### 4. 커뮤니티 반응 수집 `[NP2-REACT-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 선정된 뉴스에 대한 Reddit/HN/X 반응을 Tavily로 추가 수집
- **산출물:** `backend/services/news_collection.py`에 함수 추가
- **완료 기준:** 뉴스 URL/제목 → 커뮤니티 반응 텍스트 반환 + 테스트
- **의존성:** NP2-RANK-01

### 5. 팩트 추출 (LLM Call 1) `[NP2-FACTS-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 뉴스 원문 + 컨텍스트 + 커뮤니티 반응 → 구조화된 팩트 JSON
- **산출물:** `backend/services/agents/fact_extractor.py` (신규)
- **완료 기준:** 팩트 JSON 반환 (핵심 사실, 수치, 출처, 반응 요약) + 테스트
- **의존성:** NP2-MODEL-01, NP2-REACT-01

### 6. 페르소나 생성 (LLM Call 2~4) `[NP2-PERSONA-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 팩트 JSON → 현직자/학습자/입문자 각각 EN+KO 동시 생성
- **산출물:** `backend/services/agents/persona_writer.py` (신규)
- **완료 기준:** 3 페르소나 × EN+KO 본문 반환 + handbook_terms 목록 활용 + 테스트
- **의존성:** NP2-MODEL-01, NP2-FACTS-01

### 7. 파이프라인 오케스트레이터 `[NP2-PIPE-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 수집 → 랭킹 → 반응수집 → 팩트추출 → 페르소나 → 저장 전체 흐름
- **산출물:** `backend/services/pipeline.py` (신규)
- **완료 기준:** `run_daily_pipeline(batch_id)` 함수 동작 + draft 저장 + 에러 처리
- **의존성:** NP2-COLLECT-01 ~ NP2-PERSONA-01 전부

### 8. Cron 엔드포인트 `[NP2-CRON-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** `/api/cron/news-pipeline` POST 엔드포인트 복원
- **산출물:** `backend/routers/cron.py` (신규)
- **완료 기준:** 202 응답 + BackgroundTasks로 파이프라인 실행 + cron_secret 검증
- **의존성:** NP2-PIPE-01

### 9. E2E 검증 — 로컬 실행 `[NP2-E2E-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 로컬에서 파이프라인 1회 실행 → Supabase에 draft 저장 확인
- **산출물:** 실행 로그 + DB 확인
- **완료 기준:** research + business 포스트 모두 3 페르소나 × EN+KO 저장됨
- **의존성:** NP2-CRON-01

### 10. 배포 + 실제 cron 실행 `[NP2-DEPLOY-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** Railway 배포 후 cron 트리거로 실제 뉴스 생성
- **산출물:** Railway 로그 + Supabase draft 확인
- **완료 기준:** 실제 AI 뉴스로 draft 생성 성공
- **의존성:** NP2-E2E-01

---

## 의존성 순서

```
NP2-MODEL-01 ─┬─→ NP2-FACTS-01 ──→ NP2-PERSONA-01 ─┐
               │                                       │
NP2-COLLECT-01 → NP2-RANK-01 → NP2-REACT-01 ─────────┤
                                                       ↓
                                              NP2-PIPE-01 → NP2-CRON-01 → NP2-E2E-01 → NP2-DEPLOY-01
```

---

## 이전 스프린트 요약

> Phase 3A-SEC (2026-03-08~09) — 게이트 전체 통과, 12개 태스크 완료.
> - CSP nonce 기반 전환, unsafe-inline 제거
> - Open Redirect 수정, strict-dynamic 추가
> - OAuth 보안 강화

> AI News Pipeline v1 (2026-03-10~14) — 삭제됨.
> - 콘텐츠 길이 검증 실패로 반복 장애 → 코드 + DB 전체 삭제 후 v2 재설계
