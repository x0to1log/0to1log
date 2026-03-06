# ACTIVE SPRINT — Phase 2B-OPS (Backend Feature Freeze)

> **스프린트 시작:** 2026-03-07
> **목표:** AI Agent 3종 구현 + Admin CRUD 실구현 + OpenAPI 스키마 고정
> **참조:** MASTER → `docs/IMPLEMENTATION_PLAN.md` | 스펙 → `docs/02~03`
> **이전 스프린트:** Phase 2A — 2026-03-07 게이트 전체 통과

---

## 스프린트 완료 게이트

- [x] OpenAPI 문서 고정 (목록/상세/에러 응답 스키마 포함) — 12 schemas, 6 endpoints
- [x] `cd backend && pytest tests/ -v` 전체 통과 — 49 passed
- [x] 외부 네트워크 호출 차단 환경에서 테스트 통과 (httpx block_network autouse fixture)
- [x] 401/403 분리 동작 확인 — test_admin.py TestAuthSplit 4 tests
- [x] 태스크 전체 `상태=done` + `체크=[x]` 일치
- [x] `Current Doing` 슬롯이 비어 있음(`-`)
- [x] 완료 태스크마다 `증거` 링크 최소 1개 존재

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시각 | Owner |
|---|---|---|---|
| - | - | - | - |

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

### 1. OpenAPI 스키마 확정 `[P2B-CONTRACT-00]`
- **체크:** [x]
- **상태:** done
- **목적:** 프론트(2C) 작업을 위한 API 응답 스키마 선고정
- **산출물:** `backend/openapi.json` + `models/posts.py` 응답 모델 8종 + 라우터 response_model 적용
- **완료 기준:** 목록/상세/에러 응답 스키마가 문서에 존재하고 프론트 Mock과 계약 일치
- **검증:** `python -c "from main import app; import json; print(json.dumps(app.openapi(), indent=2))"` 실행 → 응답 스키마 확인
- **증거:** openapi.json 생성 완료 (12 schemas, 6 endpoints, 20 tests passed)
- **참조:** 03 §4, IMPLEMENTATION_PLAN §3 2B Gate
- **의존성:** 없음

### 2. AI Agent 로직 + Prompt 튜닝 `[P2B-API-01]`
- **체크:** [x]
- **상태:** done
- **목적:** Ranking(gpt-4o-mini) / Research Engineer(gpt-4o) / Business Analyst(gpt-4o) 에이전트 구현
- **산출물:** `backend/services/agents/` (ranking.py, research.py, business.py, prompts.py, client.py)
- **완료 기준:** 네트워크 차단 Mock 환경에서 단위테스트 전체 통과
- **검증:** `pytest tests/test_agents.py -v` — 10 passed (네트워크 차단 autouse 픽스처 적용)
- **증거:** 30 tests passed (기존 20 + agent 10), httpx block_network fixture
- **참조:** 02 §2-4, 03 §5
- **의존성:** P2B-CONTRACT-00

### 3. Admin CRUD 엔드포인트 `[P2B-API-02]`
- **체크:** [x]
- **상태:** done
- **목적:** 501 스텁을 실구현으로 교체 (list/get/publish/update)
- **산출물:** `backend/routers/admin.py` 실구현 + `backend/tests/test_admin.py`
- **완료 기준:** Admin 200/201/204 정상 + 비인가 401/403 분리 테스트 통과
- **검증:** `pytest tests/test_admin.py -v` — 13 passed (auth 4 + CRUD 9)
- **증거:** 401/403 분리 확인, dependency_overrides mock, Supabase mock
- **참조:** 03 §4
- **의존성:** P2B-CONTRACT-00

### 4. Cron endpoint skeleton `[P2B-CRON-00]`
- **체크:** [x]
- **상태:** done
- **목적:** Vercel Cron이 찌를 진입점 뼈대 (Secret 검증 + 202 반환만)
- **산출물:** `backend/routers/cron.py` (response_model 적용) + `backend/tests/test_cron.py`
- **완료 기준:** valid secret → 202, invalid secret → 401 테스트 통과
- **검증:** `pytest tests/test_cron.py -v` — 6 passed
- **증거:** 401 (missing/invalid/empty secret) + 202 (valid) + 응답 스키마 검증
- **참조:** 04 §5, 05 §4
- **의존성:** 없음 (에이전트 호출 연동은 Phase 2D)

---

## 의존성 흐름

```
P2B-CONTRACT-00 → P2B-API-01
P2B-CONTRACT-00 → P2B-API-02
P2B-CRON-00 (독립 — 에이전트 연동은 2D)
```

---

## 이전 스프린트 요약 (Phase 2A)

> Phase 2A (2026-03-06 ~ 03-07) — 게이트 전체 통과, 6개 태스크 완료.
> - DB 마이그레이션 (`supabase/migrations/00002_pipeline_tables.sql`, 5개 테이블 + RLS)
> - Pydantic 스키마 정의 (ranking, research, business, common)
> - 뉴스 수집 서비스 Mock 테스트 완료 (Tavily/HN/GitHub + dedup)
> - 파이프라인 Lock/Stale Recovery 구현 및 테스트 (8 passed)
> - Security 미들웨어 + Vercel Cron Trigger skeleton 완료

---

## 다음 스프린트 예고

Phase 2B 게이트 통과 시 → **Phase 2C-EXP** (프론트 경험 고도화: Newsprint 테마, 다국어, 반응형/접근성 QA)

---

## 2C-EXP Addendum (Stitch Compatibility)

- [x] `2C-UI-01` Prototype compatibility cleanup completed
  Evidence: `frontend/example_dark.html`, `frontend/example_light.html`, `frontend/example_list.html`
- [x] `2C-UI-02` `/en|ko/log` list/detail style migration completed
  Evidence: `frontend/src/pages/en/log/index.astro`, `frontend/src/pages/ko/log/index.astro`, `frontend/src/pages/en/log/[slug].astro`, `frontend/src/pages/ko/log/[slug].astro`
- [x] `2C-QA-01` Preview routes added for visual validation
  Evidence: `frontend/src/pages/preview/newsprint-dark.astro`, `frontend/src/pages/preview/newsprint-light.astro`
