# Daily Run Recovery — rank 이전 실패 자동 복구

> 상위 계획: [[2026-10-13-news-pipeline-gpt6-upgrade]] (파이프라인 점검 후속)
> 상태: 설계 (2026-10-20)

**Goal:** 07:12 KST daily 실행이 시작되지 않았거나 `rank` 이전에 죽은 날, 09:00 KST promote 크론이 전체 실행을 1회 다시 돌리고 승격까지 마쳐서 "그날 뉴스 없음"을 없앤다.

## 배경

- 09:00 KST `/api/cron/promote-drafts` → `recover_incomplete_daily_batch` → `promote_drafts` 순서.
- 현재 복구는 **`rank` 체크포인트가 있을 때만** 동작: 체크포인트의 카테고리 중 EN/KO 행이 없는 것만 `rerun_pipeline_stage(from_stage="write")`.
- 아래 경우는 `skipped`로 끝나고 아무도 다시 돌리지 않음:

| 상황 | 현재 결과 | 실제 예 |
|---|---|---|
| run 행 없음 (크론 미발화, Railway 다운, 트리거 500) | `no pipeline run found` → 그날 뉴스 없음 | 10-13 (Supabase pause — 이 경우는 복구도 불가) |
| `running` 상태로 멈춤 + rank 없음 (collect~ranking 중 프로세스 종료) | stale 처리 후 `missing rank checkpoint` | Railway 재배포가 07:12~07:16 KST에 겹치면 발생 |
| `failed` + rank 없음 (collect~ranking 예외) | `missing rank checkpoint` | — |
| `success` + 0 posts + rank 없음 (collect 0건 = "no news") | `missing rank checkpoint` | Tavily 장애 시 0건 → 조용히 success |

- 파이프라인은 Railway 프로세스 안의 `BackgroundTasks`로 실행 → 재배포·재시작 시 실행이 그대로 죽음. rank 이전 구간은 약 1~4분 (collect 20~34s, classify 11~56s, merge 15~54s, community 6~8s, summarize 5~49s, ranking 5~27s; 10-14~10-20 실측).

## 조사 결과 (재사용할 기존 패턴)

- `run_daily_pipeline`은 같은 `run_key`가 있으면 **run을 재사용** (`force_fresh=False`면 로그·체크포인트 보존, status만 `running`으로 갱신) → 전체 재실행에 그대로 쓸 수 있음.
- stale `running` 처리(75분, `.eq("status","running")` 조건부 update로 claim)는 이미 있음. 07:12 시작 run은 09:00에 108분 → stale.
- `promote_after_recovery` 파라미터, `promote_drafts(batch_id)`, `check_existing_batch`(posts 개수) 이미 있음.
- 관련 테스트: `tests/test_pipeline_rerun.py::test_recover_incomplete_daily_batch_recovers_missing_research_and_promotes`, `tests/test_cron.py::test_promote_drafts_attempts_incomplete_batch_recovery_first`.
- Vercel 크론 슬롯 추가 없이 09:00 크론에 얹는 기존 방식(retention prune과 같은 패턴) 유지.

## 설계

### 1. 복구 판단을 순수 함수로 분리

`_decide_daily_recovery(...) -> tuple[str, str]` (action, reason)

| 입력 상태 | action |
|---|---|
| run 없음 | `full_run` |
| `running` + stale 아님 | `skip` (still running) |
| rank 체크포인트 있음 | `write` (기존 경로) |
| rank 없음 + (`failed` / stale `running` / `success` & posts 0) | `full_run` |
| 이 batch의 posts 행이 하나라도 있음 + rank 없음 | `skip` (수동 작업 흔적 — 건드리지 않음) |
| 이미 full_run 복구를 시도함 | `skip` (1회 제한) |

- 순수 함수라 DB 없이 상태 조합 전부를 단위 테스트 가능.

### 2. `full_run` 경로

- `run_daily_pipeline(batch_id=batch_id, target_date=None, skip_handbook=True, auto_publish=True)` — `target_date=None`이라 daily 수집 모드 (`days=2`), backfill 아님.
- 끝나면 `promote_drafts(batch_id)` 호출 (기존 `promote_after_recovery` 흐름과 같음). 크론 경로는 이미 복구 후 `promote_drafts`를 부르므로 중복 호출하지 않도록 반환값으로 정리.
- 발행 시각: 평소 ~09:00 → 복구일은 ~09:10~09:20 KST.

### 3. 1회 제한 + 기록

- run에 `recovery` 단계 로그를 남김: `debug_meta = {"action": "full_run", "reason": ..., "previous_status": ...}`.
- 판단 시 같은 run에 `recovery` 로그(action=full_run)가 있으면 `skip`. → 수동으로 promote 크론을 다시 눌러도 전체 실행이 반복되지 않음.
- 어드민 Pipeline health 카드에서 이 로그를 "자동 복구됨"으로 보여주는 건 후속 (이번 범위 아님).

### 범위 밖

- Supabase 자체 장애: DB가 없으면 판단도 기록도 불가 → 해결 대상 아님.
- 09:00 복구 실행 자체가 죽는 경우: 추가 재시도 없음 (어드민 실행 공백 표시로 확인).
- rank 이후 `write` 중 stale 판정 문제 (원래 run이 아직 쓰는 중인데 75분 넘으면 중복 작성 가능): 기존 동작, 별도 과제로 기록만.
- 퀴즈 부분 누락 표시: 별도 소과제.

## 검증

1. `_decide_daily_recovery` 단위 테스트: 위 표의 모든 행.
2. `recover_incomplete_daily_batch` 테스트 (DB·`run_daily_pipeline`·`promote_drafts` 전부 mock — 운영 Supabase 접속 금지, [[bug_backend_tests_hit_prod]]):
   - run 없음 → `run_daily_pipeline` 1회 호출 + promote
   - rank 있음 → 기존 `write` 경로 (회귀 없음)
   - `recovery` 로그 있음 → 호출 없음
3. 전체 `pytest` + `ruff`.
4. 배포 후: 운영에서 일부러 실패를 만들지는 않음. 다음 실제 실패일 또는 관찰 기간 중 promote 로그(`skipped` 사유)로 정상 판단 확인.

## 후속: RECOVERY-STALE-01 (2026-10-20)

- **문제:** stale 판정이 "시작 후 75분". 07:12 시작 run은 09:00에 항상 108분 → flex 재시도로 아직 작성 중인 run도 죽은 것으로 보고 write 복구 → 같은 글을 두 번 작성할 수 있음.
- **수정:** stale = **마지막 활동**(run 시작 / 최신 `pipeline_logs.created_at` 중 늦은 쪽) 이후 75분 무활동. 살아 있는 run의 최장 무로그 구간 = 페르소나 작성 1단계 (3회 × 1200s = 60분) → 75분이 덮음.
- **따라오는 문제와 처리:** 09:00에 "아직 실행 중"으로 건너뛴 run은 승격 크론 이후에 끝나서 draft로 남음 → cron run(`auto_publish`)이 09:00 KST 이후에 끝나면 `_promote_if_late`로 스스로 승격. 09:00 복구의 전체 재실행은 크론이 바로 승격하므로 `promote_when_late=False` (draft 경고 메일 중복 방지).
- **트레이드오프:** 07:45 KST 이후에 죽은 run은 09:00에 아직 stale이 아니라 복구되지 않음 (이전에는 무조건 stale). 이 경우 어드민 health 카드 / 다음 날 확인으로 수동 처리. 09:00 크론이 promote 시점에 research만 끝난 상태면 research는 크론이, business는 run이 승격 → 보류된 draft가 있으면 경고 메일이 두 번 갈 수 있음 (드묾, 허용).

## 운영 수칙 (코드 변경 없음)

- **07:10~07:30 KST에는 push하지 않기** (Railway 재배포가 실행 중인 파이프라인을 끊음).
