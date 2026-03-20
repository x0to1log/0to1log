# Pipeline Controls 강화 설계

> 파이프라인: [[AI-News-Pipeline-Design]]
> 운영: [[AI-News-Pipeline-Operations]]

---

## 1. Stuck 타임아웃 (P0)

### 문제
파이프라인이 에러로 중단되어도 status가 "running"으로 남아 영원히 stuck.

### 해결
프론트엔드 체크 방식 — 대시보드 로드 시 `started_at + 30분 < now()`인 "running" run을 자동 감지:
- UI에서 "Timed out" 표시
- API 호출로 DB status를 "failed" + last_error = "Pipeline timed out" 업데이트

### 구현
- `frontend/src/pages/admin/index.astro` — frontmatter에서 stuck 체크 + 자동 업데이트
- 30분 임계치 (뉴스 파이프라인 평균 3~5분, handbook 포함 시 10~15분)

---

## 2. 수동 취소 버튼 (P0)

### 문제
비싼 파이프라인을 실행 중일 때 멈출 방법이 없음.

### 해결
대시보드에서 "running" 상태일 때 **Cancel** 버튼 표시:
- 클릭 → 백엔드 API → `pipeline_runs.status = 'failed'`, `last_error = 'Cancelled by admin'`
- 실제 백그라운드 태스크는 즉시 중단 불가 (Python 한계) → 하지만 status 변경으로 UI 정상화
- 다음 실행은 정상적으로 가능

### 구현
- `backend/routers/cron.py` — `POST /api/cron/pipeline-cancel` 엔드포인트
- `frontend/src/pages/admin/index.astro` — Cancel 버튼 (running일 때만)
- `frontend/src/lib/admin/pipelineTrigger.js` — cancel 요청 프록시

---

## 3. 뉴스만 실행 옵션 (P1)

### 문제
Run Pipeline을 누르면 항상 handbook 추출도 같이 트리거. 뉴스만 뽑고 싶을 때가 있음.

### 해결
Run Pipeline 버튼 옆에 체크박스: "Include handbook extraction" (기본 체크됨).
- 체크 해제 → `skip_handbook: true` 전달
- 백엔드: skip_handbook이면 `run_handbook_extraction()` 자동 트리거 스킵

### 구현
- `frontend/src/pages/admin/index.astro` — 체크박스 UI + 요청에 파라미터 추가
- `backend/routers/cron.py` — `PipelineTriggerBody`에 `skip_handbook: bool = False`
- `backend/services/pipeline.py` — `run_daily_pipeline()`에 `skip_handbook` 파라미터

---

## Related

- [[AI-News-Pipeline-Design]]
- [[AI-News-Pipeline-Operations]]
- [[Pipeline-Stage-Logging-Schema]]
