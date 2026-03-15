# ACTIVE SPRINT — AI News Pipeline v2

> **스프린트 시작:** 2026-03-15
> **목표:** AI News Pipeline v2 백엔드 구현 (수집 → 팩트 추출 → 3 페르소나 생성 → 저장)
> **설계 참조:** `vault/04-AI-System/AI-News-Pipeline-Design.md`
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

### 11. 파이프라인 과거 날짜 백필 지원 `[NP2-BACKFILL-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 어드민이 과거 날짜를 지정하여 파이프라인을 실행할 수 있게 지원
- **산출물:** `news_collection.py` (target_date + start_date/end_date), `cron.py` (PipelineTriggerBody), 어드민 UI 날짜 선택기
- **완료 기준:** 어드민 대시보드에서 과거 날짜 선택 → 해당 날짜 뉴스 수집 + draft 저장
- **의존성:** NP2-CRON-01

### 12. 스테이지별 로깅 + 백필 검증 UI `[NP2-OBSERVE-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 파이프라인 각 LLM 단계의 입출력/토큰/비용/attempt을 기록하고, Run Detail에서 확인 가능하게
- **산출물:** `pipeline.py` (_log_stage 헬퍼 + 6~8개 스테이지 로깅), `[runId].astro` (Run Context, 백필 배지, Created Posts)
- **완료 기준:** Run Detail에서 각 스테이지 debug_meta 확인 + input/output 토큰 칩 표시 + 생성된 포스트 목록
- **의존성:** NP2-BACKFILL-01

### 13. Handbook 프롬프트 2회 호출 분리 `[HB-SPLIT-01]`
- **체크:** [x]
- **상태:** done
- **목적:** Generate 액션을 2회 LLM 호출(메타+Basic / Advanced)로 분리하여 콘텐츠 퀄리티 향상
- **산출물:** `advisor.py` (generate 로직 분리), `prompts_advisor.py` (프롬프트 재작성 완료)
- **완료 기준:** AI Generate → 2회 호출 실행 → Basic/Advanced 독립 생성 + KO/EN 헤더 분리 확인
- **의존성:** 없음
- **설계 참조:** [[2026-03-15-handbook-quality-design]], [[Handbook-Prompt-Redesign]]

### 14. Handbook DB 모델 확장 `[HB-MODEL-01]`
- **체크:** [x]
- **상태:** done
- **목적:** `term_full`, `korean_full` 컬럼 추가 + 프론트엔드 에디터 반영
- **산출물:** Supabase 마이그레이션, 에디터 UI 필드 추가
- **완료 기준:** 어드민 에디터에서 4개 명칭 필드(term, term_full, korean_name, korean_full) 입력/표시
- **의존성:** 없음

### 15. Handbook 비용/토큰 추적 `[HB-COST-01]`
- **체크:** [x]
- **상태:** done
- **목적:** Handbook AI 호출의 input/output 토큰, 비용을 pipeline_logs에 기록
- **산출물:** `advisor.py`에 `_log_stage()` 호출 추가 (handbook.generate.basic, handbook.generate.advanced)
- **완료 기준:** Handbook AI Generate 실행 → pipeline_logs에 2개 스테이지 로그 기록 확인
- **의존성:** HB-SPLIT-01

### 16. Pipeline Analytics에 Handbook 탭 추가 `[HB-ANALYTICS-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 어드민 pipeline-analytics 페이지에서 Handbook AI 비용/토큰을 News와 분리 확인
- **산출물:** `pipeline-analytics.astro` Handbook 탭 추가
- **완료 기준:** News / Handbook 탭 전환 → 각각의 비용/토큰 차트 표시
- **의존성:** HB-COST-01

### 17. 파이프라인 분리: News Run + Handbook Run `[PIPE-SPLIT-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 뉴스 파이프라인과 용어 추출을 별도 pipeline_runs로 분리
- **산출물:** `pipeline.py` (run_handbook_extraction), `cron.py` (/handbook-extract), Retry Handbook 버튼
- **완료 기준:** 뉴스 run 완료 → 용어 run 자동 트리거 + 실패 시 Retry 버튼

### 18. pipeline_logs 기록 안 되는 버그 `[BUG-LOGS-01]`
- **체크:** [x]
- **상태:** done
- **원인:** `_log_stage()`에서 `attempt=None`, `debug_meta=None`을 명시적으로 전달 → NOT NULL DEFAULT 컬럼에 NULL insert 시도 → PostgREST 거부 → try/except에서 조용히 무시
- **해결:** None인 필드를 INSERT dict에서 제외하여 DB DEFAULT 사용

### 20. Pipeline Runs 페이지 News/Handbook 탭 분리 `[RUNS-TAB-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** Pipeline Runs 페이지에서 뉴스 run과 핸드북 run을 탭으로 구분
- **산출물:** `pipeline-runs/index.astro` — News/Handbook 탭 + run_key prefix 필터링

### 19. Supabase 마이그레이션 실행 `[DB-MIGRATE-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** term_full, korean_full 컬럼을 프로덕션 DB에 추가
- **SQL:** `ALTER TABLE handbook_terms ADD COLUMN IF NOT EXISTS term_full text, ADD COLUMN IF NOT EXISTS korean_full text;`
- **실행 위치:** Supabase 대시보드 SQL Editor

---

## 의존성 순서

```
[News Pipeline v2]
NP2-MODEL-01 ─┬─→ NP2-FACTS-01 ──→ NP2-PERSONA-01 ─┐
               │                                       │
NP2-COLLECT-01 → NP2-RANK-01 → NP2-REACT-01 ─────────┤
                                                       ↓
                                              NP2-PIPE-01 → NP2-CRON-01 → NP2-E2E-01 → NP2-DEPLOY-01

[Handbook Quality]
HB-SPLIT-01 ✅ → HB-COST-01 ✅ → HB-ANALYTICS-01 ✅
HB-MODEL-01 ✅

[Pipeline Split & Fixes]
PIPE-SPLIT-01 ✅
BUG-LOGS-01 (미해결)
DB-MIGRATE-01 (수동 실행 필요)
```

---

## 이전 스프린트 요약

> Phase 3A-SEC (2026-03-08~09) — 게이트 전체 통과, 12개 태스크 완료.
> - CSP nonce 기반 전환, unsafe-inline 제거
> - Open Redirect 수정, strict-dynamic 추가
> - OAuth 보안 강화

> AI News Pipeline v1 (2026-03-10~14) — 삭제됨.
> - 콘텐츠 길이 검증 실패로 반복 장애 → 코드 + DB 전체 삭제 후 v2 재설계

## Related Plans

- [[plans/2026-03-15-news-pipeline-v2-impl|Pipeline v2 구현]]
- [[plans/2026-03-13-business-partial-resume-and-fail-fast|부분 실행 + Fail-Fast]]
- [[plans/2026-03-15-handbook-quality-design|Handbook 퀄리티 시스템 설계]]
- [[Handbook-Prompt-Redesign|Handbook 프롬프트 재설계]]
