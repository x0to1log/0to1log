# 핸드북 판정 검증 — 발행/보관 결정과 비교 (2026-11-14)

> 상위: [[2026-10-26-claude-api-migration]], [[opus-rescore-2026-11-13]]
> 목적: 판정 점수(Opus 5.5)가 Amy의 발행/보관 결정을 가르는지 확인. 판정끼리의 비교(sol vs Opus)로는 어느 쪽이 맞는지 알 수 없었음.
> 방식: 읽기 전용, DB 기록 없음. `backend/scripts/validate_handbook_judge.py`. 판정 입력 자르기 제거(`3d818010`) 이후의 코드로 채점.
> 대상: `source = pipeline`이고 본문 4개가 모두 있는 용어 — published 34, archived 20. 그중 20개(상태별 10)는 한 번 더 채점.
> 비용: $13.91 (1차 $10.08 + 반복 $3.83), 용어당 ~$0.19
> 원자료: `judge-pipeline.jsonl`, `judge-pipeline-repeat.jsonl`, 전체 표 `report-generated.md`

## 결과

| 점수 | published 평균 (sd) | archived 평균 (sd) | AUC | 95% 구간 |
|---|---|---|---|---|
| advanced, 판정만 | 56.2 (10.9) | 52.1 (17.8) | 0.54 | 0.35–0.73 |
| advanced, 감점 후 | 39.9 (21.4) | 35.3 (24.4) | 0.59 | 0.41–0.75 |
| basic, 판정만 | 63.9 (9.9) | 59.2 (10.0) | 0.63 | 0.46–0.78 |
| basic, 감점 후 | 48.3 (20.0) | 42.6 (17.4) | 0.58 | 0.41–0.73 |
| 구조 감점 (코드) | 16.6 (11.6) | 16.2 (9.1) | 0.50 | 0.34–0.65 |

AUC = 발행된 용어가 보관된 용어보다 점수가 높을 확률. 0.5면 신호 없음.

게이트 70 통과: advanced published 5/33, archived 0/18. basic published 7/31, archived 0/19.

같은 본문을 두 번 채점:

| | 용어 수 | 평균 절대 차이 | 최대 | 70 기준 결과 바뀜 |
|---|---|---|---|---|
| advanced | 18 | 2.3 | 6 | 0/18 |
| basic | 17 | 3.2 | 9 | 0/17 |

## 해석

- **점수가 발행/보관을 가른다는 증거가 없다.** 모든 구간에 0.5가 들어간다. 다만 아래 한계 때문에 "판정이 무용하다"는 결론도 아니다.
- **Opus 판정은 스스로와는 일관된다.** 반복 차이 평균 2~3점. sol–Opus 차이(sd 8.1, [[opus-rescore-2026-11-13]])는 채점 잡음이 아니라 두 모델의 의견 차이다.
- **발행된 용어 대부분이 지금 게이트를 통과하지 못한다** (advanced 28/33 미달). 발행분 다수는 3월 형식(`term_type` 없음, 구조 감점 22~27)이라 현재 루브릭·구조 검사와 맞지 않는다. 게이트 70은 "보관될 글을 걸러내는" 기준이 아니라 "현재 형식을 따르는가"에 가깝게 작동한다.
- **구조 감점은 발행/보관과 무관하다** (AUC 0.50).

## 한계

- 표본 34 대 20. AUC 구간 폭이 ±0.18.
- **보관 사유가 품질이 아닌 용어가 섞여 있다.** archived 최고점은 `iso-42001`(74), `hermes-web-ui`(72), `mixture-of-experts`(71)로, 범위 밖·중복으로 보관됐을 가능성이 높다 (**검증 안 된 가설** — Amy 확인 필요).
- 발행 시기와 형식이 섞여 있다 (3월 형식 vs 5월 형식). 점수는 형식 차이도 함께 잰다.

## 별도 발견 — 판정 출력 구조

- **채점 실패 (점수 없음):** 1차 108회 중 7회, 반복 40회 중 5회. 같은 용어가 다른 회차에는 채점됨 → 간헐적.
- **세부 점수 위치가 틀림:** 1차 advanced 12/54, basic 12/54. 세부 점수가 다른 항목 아래에 들어가거나(예: `technical_depth.factual_correctness`), 빠지거나(8개), 중복(10~12개)됨. `_aggregate_quality_sub_scores`는 들어온 대로 더해 고정 분모(90/100)로 나누므로 빠지면 점수가 내려가고 중복되면 올라간다.
- 반복 차이에 주는 영향은 작다 (정상 구조끼리 평균 2.1~2.3, 한쪽이라도 틀리면 3.2~4.6). 판정 간 불일치의 주원인은 아님.
- 대응안: 판정 호출을 `json_schema` 구조화 출력으로 바꾸고, 집계를 기대하는 세부 점수 이름 기준으로 한다.

## 보관 사유 확인 요청 (Amy)

품질 때문에 보관한 것만 골라 다시 비교하면 더 정확하다. advanced 판정 점수 순:

iso-42001 74 · hermes-web-ui 72 · mixture-of-experts 71 · gabriels-horn 69 · three-phase-transformer 68 · latent-moe 67 · value-gradient-flow 66 · acquihire 59 · llm-internals 59 · flashattention-4 58 · ai-robotics 48 · supply-chain-vulnerability 44 · agentic-access-management 37 · collaboration 36 · ai-native-framework 33 · firefly-ai-assistant 30 · nvidia-blackwell 24 · nvidia-dgx-cloud 23 · agentic-ux (점수 없음) · openai-frontier (점수 없음)
