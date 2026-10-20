# Rerun Published Guard — 막힌 재실행이 기록을 지우지 않게

> 상위: [[2026-10-13-news-pipeline-gpt6-upgrade]] 운영 결함 (RERUN-GUARD-01)
> 상태: 구현 (2026-10-20)

## 문제

`rerun_pipeline_stage` 순서: ① run을 `running`으로 claim → ② 재실행 단계 이후 로그 삭제 → ③ **그다음에** 발행 보호 검사 → 막히면 run을 `failed`로 기록.

발행된 날짜에 quiz 외 재실행(write / quality / beginner 등)을 누르면:
- 이미 끝난 실행의 단계 로그(작성·QC·저장·summary)가 지워짐 → 비용·QC 기록 소실.
- 성공한 run이 `failed`로 바뀜 → 어드민 Pipeline health 카드가 "daily run failed" **critical**로 표시 (최신 run이면).
- 화면 피드백 없음: 라우터는 즉시 202, run 상세 페이지는 응답과 상관없이 "Rerun started" alert.

## 설계

- 보호 검사를 `published_rerun_block_message(supabase, batch_id, from_stage, category)`로 분리. quiz는 `guide_items.quiz_poll_*`만 바꾸므로 기존처럼 허용.
- `rerun_pipeline_stage`: claim·로그 삭제 **전에** 검사 → 막히면 아무것도 건드리지 않고 failed 결과 반환 (직접 호출 경로 방어, 예: 09:00 write 복구).
- `/api/cron/pipeline-rerun`: background 등록 전에 같은 검사 → `422 published_protected` (뉴스 트리거와 같은 형식).
- 프론트: `handleRerunRequest`가 409/422를 그대로 전달 (`forwardPipelineTrigger`와 같은 규칙), run 상세 페이지는 실패 응답이면 "Rerun blocked: …" 표시.

## 검증

- 백엔드: 발행된 범위 write 재실행 → claim·삭제·run 갱신 없음 / 라우터 422 / quiz는 통과.
- 프론트: build + `pipeline-trigger-helper` 테스트에 422 전달 케이스.
