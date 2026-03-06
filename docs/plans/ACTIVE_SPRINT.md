# ACTIVE SPRINT — Phase 2A AI Core (Data Collection Base)

> **스프린트 시작:** 2026-03-06
> **목표:** 데이터 수집/랭킹 뼈대 완성 + 외부 API Mock 테스트
> **참조:** MASTER → `docs/IMPLEMENTATION_PLAN.md` | 스펙 → `docs/02~03`
> **이전 스프린트:** Phase 1b Analytics — 2026-03-06 게이트 전체 통과

---

## 스프린트 완료 게이트

- [ ] `cd backend && pytest tests/ -v` 전체 통과
- [ ] `cd frontend && npm run build` — 0 error
- [ ] 태스크 전체 `상태=done` + `체크=[x]` 일치
- [ ] `Current Doing` 슬롯이 비어 있음(`-`)
- [ ] 완료 태스크마다 `증거` 링크 최소 1개 존재

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시각 | Owner |
|---|---|---|---|
| P2-PIPE-BASE | doing | 2026-03-06 | Amy |

규칙:
- 문서 내 `상태: doing` 태스크가 있으면 이 표에는 반드시 1개만 기입한다.
- 문서 내 `상태: doing` 태스크가 0개면 표는 `-`를 유지한다.
- 태스크 상태 변경 시 이 표를 같은 커밋에서 함께 갱신한다.

---

## 상태 업데이트 규칙

- 혼합형 고정: `상태(todo/doing/review/done/blocked)` + `체크([ ]/[x])`를 함께 사용한다.
- `todo/review/doing/blocked`는 `체크: [ ]`로 유지한다.
- `done`은 반드시 `체크: [x]`로 변경한다.
- `상태`와 `체크`가 불일치하면 무효로 간주한다. 예: `상태: done` + `체크: [ ]` 금지.
- `증거`는 태스크 완료(`상태: done`) 시 필수이며, PR/로그/스크린샷 중 최소 1개 링크를 남긴다.

---

## 태스크 (실행 순서)

### 1. Pipeline 테이블 마이그레이션 `[P2-DB-01]`
- **체크:** [x]
- **상태:** done
- **산출물:** `supabase/migrations/00002_pipeline_tables.sql` (5개 테이블 + RLS)
- **완료 기준:** Supabase Dashboard에서 테이블 확인 + SQL 커밋
- **검증:** 마이그레이션 SQL 문법 정상 + posts ALTER 없음
- **증거:** commit d218890
- **참조:** 03 §3

### 2. Pydantic 스키마 + 의존성 `[P2-SCHEMA-01]`
- **체크:** [x]
- **상태:** done
- **산출물:** requirements.txt 업데이트 + models/ 스키마 (common, ranking, research, business)
- **완료 기준:** `python -c "from models.ranking import *"` 등 import 성공
- **검증:** 각 모델 import 테스트
- **증거:** commit 6596029
- **참조:** 02 §4

### 3. Security + Admin Auth + Rate Limiting `[P2-AUTH-01]`
- **체크:** [x]
- **상태:** done
- **산출물:** security.py 실구현 + main.py slowapi 등록
- **완료 기준:** 401/403 분리 동작 확인
- **검증:** require_admin 함수 + verify_cron_secret + slowapi 미들웨어
- **증거:** commit 7ec56fb
- **참조:** 03 §2

### 4. News Collection Service `[P2-COLLECT-01]`
- **체크:** [x]
- **상태:** done
- **산출물:** `services/news_collection.py` + `tests/test_news_collection.py`
- **완료 기준:** Mock 기반 단위테스트 전체 통과
- **검증:** `pytest tests/test_news_collection.py -v`
- **증거:** commit 65d8284
- **참조:** 02 §2

### 5. Pipeline Lock + Stale Recovery `[P2-PIPE-BASE]`
- **체크:** [ ]
- **상태:** doing
- **산출물:** `services/pipeline.py` + `tests/test_pipeline_lock.py`
- **완료 기준:** Lock 획득/스킵/stale recovery/failed 재시도 테스트 전체 통과
- **검증:** `pytest tests/test_pipeline_lock.py -v`
- **증거:** (완료 시 필수)
- **참조:** 02 §6

### 6. Vercel Cron Trigger `[P2-CRON-01]`
- **체크:** [ ]
- **상태:** todo
- **산출물:** `frontend/src/pages/api/trigger-pipeline.ts` + vercel.json cron 추가
- **완료 기준:** `npm run build` 0 errors + GET 핸들러 구현
- **검증:** 빌드 통과
- **증거:** (완료 시 필수)
- **참조:** 04 §5, 05 §4

---

## 의존성 흐름

```
P2-DB-01 → P2-SCHEMA-01 → P2-AUTH-01 → P2-COLLECT-01 → P2-PIPE-BASE → P2-CRON-01
```

---

## 다음 스프린트 예고

Phase 2A 게이트 통과 시 → **Phase 2B AI Core** (Agent 본체 + Admin CRUD + E2E + 배포)
