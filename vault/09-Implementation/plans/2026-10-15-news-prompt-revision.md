# News Prompt Revision — 관찰된 오류의 원인 수정

> 상위 계획: [[2026-10-13-news-pipeline-gpt6-upgrade]] / 관련: [[2026-10-15-frontload-claim-grounding]]
> 상태: 구현 중 (2026-10-15)

## 감사 결과 (`/prompt-audit news`, 기준 [[2026-03-18-prompt-audit-fixes]])
- C2 인용 매핑 ✅ (`[CITE_N]` + allowlist), M3 ✅, H1 (JSON 문구 31곳 반복) / M4 (프롬프트 이름) 경미 → 이번 범위 제외
- M1 날짜 형식 규칙 없음 → W1과 함께 해결

## 수정 범위 (Amy 승인 2026-10-15)

| # | 관찰된 오류 | 원인 | 수정 |
|---|---|---|---|
| W1 | 09-28 "former President" | writer 프롬프트에 날짜 없음, 그러면서 "as of <absolute date>" 요구 | `get_digest_prompt(..., batch_date)` → DATE CONTEXT 블록 (직함·시점은 출처 표기, 자체 지식으로 'former' 등 금지) |
| W2 | 10-15 EN excerpt "95% off" | FINAL CHECKLIST 5번이 KO frontload만 검사 | EN headline/excerpt/focus_items 포함, 출처에 없는 수치·이름 제거 |
| W3 | 10-12 "efficiency metrics shifting budgets" 등 해석성 과장 | focus_items P2 지침이 "'enables X', 'reduces Y', 'shifts Z'" 메커니즘 표현을 권장 | "출처가 밝힌 영향만, 출처에 없는 시장·예산 변화 추론 금지"로 교체 (평가형 금지는 유지) |
| ~~Q1~~ | 퀴즈 정답 번호 오류 | **제외:** 퀴즈 프롬프트 끝 "Consistency Guard"에 이미 "answer_index MUST point to the option your explanation treats as true" 있음 → 같은 규칙 반복은 효과 없음. 퀴즈 정답 검증 단계(Task 1.6)가 담당 | — |
| QC1 | 09-23 "50%" 과잉 판정 | number_grounding에 출처 자체 반올림 기준 없음 | 출처가 밝힌 수치(출처의 반올림 포함)는 근거 있음, 0/4점은 없거나 모순일 때만 |
| WK1 | W33 KO "최대" vs "이상" 모순 | KO adapt에 수량 한정어 보존 규칙 없음 | over/at least/up to/about → 이상/최소/최대/약 보존 |

## 검증
- 프롬프트 내용 테스트 (`tests/test_news_digest_prompts.py`) — 각 항목 1개 이상
- A/B: 10-14, 10-15 checkpoint로 수정 전/후 writer 재작성 → sol 채점 비교 (`scripts/ab_daily_models.py`, 약 $2). checkpoint가 남은 날짜가 이 둘뿐 (09-30 이전 삭제 사고)
- 지표: frontload major 수, 차단 cap, quality score, 비용

## A/B 결과 (2026-10-15, 작성 gpt-5, 채점 gpt-6.1-sol + 현재 QC 코드로 동일 재채점, $2.5)
수정 전 = HEAD 임시 worktree, 수정 후 = 작업 트리. 각 1회.

| 글 | 전 score | 후 score | 전 차단 | 후 차단 | 전 frontload raw | 후 frontload raw |
|---|---|---|---|---|---|---|
| 10-14 research | 74 | 75 | major | 없음 | 72 | 90 |
| 10-14 business | 71 | 70 | major | major | 75 | 78 |
| 10-15 research | 72 | 78 | major ×2 | 없음 | 69 | 77 |
| 10-15 business | 75 | 79 | major | 없음 | 84 | 87 |

- gate(T=70) 자동 발행: **0/4 → 3/4**. frontload raw 평균 +8.
- 사라진 major: "provenance/anomaly defense로 이동"(shift 주장), "Vals Index 1위", "금융 업무용 포지셔닝", "유료 사용자 대상" → 출처에 없는 영향·위치·조건 주장 (W3 대상 유형)
- 남은 major: 10-14 business "AISI 배포 전 접근권 회복" (수정 전에도 동일). 관계·해석성 과장 → 프롬프트·결정적 검사로 어려움, sol QC가 draft로 막는 영역
- 비용: $0.53→$0.57, $0.52→$0.74. 10-15 증가분은 writer 인용 번호 오류 (`[CITE_[7]]`) 재시도 — 무작위 실패로 보임
- 한계: 2일 × 1회 표본. W1(날짜)은 해당 사례가 없어 미측정 → 배포 후 운영 결과로 확인
