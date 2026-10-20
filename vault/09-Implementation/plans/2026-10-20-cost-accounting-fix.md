# Cost Accounting Fix — QC 비용 누락 + 대시보드 이중 집계

> 상위: [[2026-10-13-news-pipeline-gpt6-upgrade]] 개선 순서 5번 (COST-QC-01)
> 상태: 구현 (2026-10-20)

## 실측 (최근 30일 `pipeline_logs`, 2026-10-20)

- **QC 비용 누락:** daily run의 `summary` 비용 < 단계별 합계. gpt-5-mini QC 시절(09-21~09-28) 차이 약 $0.02, sol QC(10-15~) 약 $0.10/run.
  - 원인: `_check_digest_quality`가 `cumulative_usage`를 인자로 받지만 합치지 않음. weekly(`_check_weekly_quality`)는 `cumulative_usage.update(merge_usage_metrics(...))`로 합침 → 같은 패턴 적용.
  - 실패 경로(judge 불가 → `RuntimeError`)도 이미 쓴 비용이므로 합침.
- **대시보드 이중 집계:** `admin/index.astro`의 "AI Cost"(30일)와 마지막 실행 카드가 `summary` 행까지 더함. `summary` = 단계 합계라 daily 비용이 2배.
  - 30일 표시 $17.53 → 실제 약 $9.8. 10-20 run 카드 $1.57 → 실제 $0.79.
  - `pipeline-analytics.astro`(`excludeStages`)와 `pipeline-runs/index.astro`는 이미 `summary` 제외 → 대시보드만 같은 규칙 적용.

## 범위 밖

- `pipelineCostMetrics.js`의 `MODEL_PRICING_PER_1M`이 gpt-5 계열만 있음 → GPT-6 로그는 "절감액 추정"에서 unpriced. 기록 비용(`cost_usd`)은 백엔드가 계산하므로 정확. NP-GPT6-CLEANUP 때 같이 정리.

## 검증

- 백엔드: QC 성공·실패 모두 `cumulative_usage`에 judge 비용이 더해지는 테스트.
- 프론트: build + 로컬 대시보드 AI Cost가 단계 합계와 맞는지 확인.
- 배포 후 다음 daily run: `summary` 비용 ≈ 단계별 합계.
