# Warmup 30 — Opus 5.5 판정 재채점 (2026-11-13)

> 상위: [[2026-10-23-handbook-seed-claude]], [[2026-10-26-claude-api-migration]]
> 목적: 핸드북 판정을 gpt-6.1-sol → Claude Opus 5.5로 바꾸면서 생성 게이트(55/70)를 다시 맞추기 위한 기준 자료
> 방식: 읽기 전용. DB의 현재 draft 본문을 `rescore_existing_handbook_quality(run_semantic=True)`로 재채점, DB 기록 없음. 원자료 `opus-rescore-2026-11-13.jsonl`
> 비용: $5.50 (30용어 × 판정 2회, 빈 응답 2건 재실행 포함)

## 기준선 확인

- sol 점수는 생성 직후 기록분 (`handbook_quality_scores`, `term_slug` 기준 — seed 행은 `term_id`가 비어 있음). 본문 수정 이후 채점이 안 된 용어 0개 → 같은 본문을 두 판정이 채점한 비교.
- 1차 실행에서 Opus 빈 응답 2건 (World Model basic, Reward Shaping advanced): 파서가 빈 문자열을 받음. 같은 요청 재현 3/3 정상 → 간헐적. 원인은 **검증 안 된 가설** (텍스트 블록이 빈 응답). `claude_client`에 빈 JSON 응답 1회 재시도 + 엄격 파싱 실패 시 응답 형태 로그 추가.

## 결과

| | sol 평균 (sd) | Opus 평균 (sd) | 차이 평균 (sd) | 상관 r | 차이 ≥10 |
|---|---|---|---|---|---|
| advanced | 70.3 (6.8) | 70.7 (7.3) | +0.4 (8.1) | 0.34 | 5 |
| basic | 74.9 (7.0) | 71.2 (6.3) | −3.7 (6.3) | 0.56 | 8 |

현재 게이트(55/70) 적용 시:

| | pass | review | blocked |
|---|---|---|---|
| sol | 14 | 16 | 0 |
| Opus | 11 | 18 | 1 (SGLang 53/56) |

- 게이트 결과 일치 **14/30**. 불일치 16개는 거의 모두 70 경계 근처 (예: Knowledge Graph 68/82 review → 78/74 pass, C2PA 71/77 pass → 64/71 review).

## 해석

- **척도 이동은 작다.** advanced는 평균이 같고, basic만 Opus가 ~4점 낮다. 기준선을 크게 옮길 근거는 없음.
- **문제는 이동이 아니라 일치도.** advanced r=0.34 — 두 판정이 "어느 용어가 더 나은가"에 대해 거의 다른 의견. 이 데이터만으로는 어느 쪽이 맞는지 알 수 없음 (사람 판단 필요).
- 판정 한 번의 흔들림(같은 모델 반복 채점 편차)은 측정 안 함 → 70 근처의 pass/review 구분은 판정 잡음보다 정밀하지 않을 수 있음 (**검증 안 된 가설**).

## 결정 (2026-11-13, Amy)

- **게이트 55/70 유지** (advanced·basic 모두). 평균 이동이 작아 기준을 옮길 근거 부족. basic은 Opus 기준으로 약간 엄격해짐 (pass 14 → 11).
- 이후 관찰: 시드 실행에서 70 경계 근처 review 비율, Amy 검수 결과와 Opus 판정의 일치 여부.
