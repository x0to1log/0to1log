# 파이프라인 최적화 계획

> 날짜: 2026-03-17
> 관련: [[AI-News-Pipeline-Design]], [[2026-03-16-daily-digest-design]]

---

## 현재 상태

| 항목 | 수치 |
|------|------|
| 총 실행 시간 | ~3분 |
| LLM 호출 수 | 28-30회/일 |
| 일일 비용 | ~$1.25-1.50 |
| 병렬화 | Tavily 수집만 병렬, 나머지 순차 |

## 병목 분석

```
[순차 실행 — 현재]
Collect(5s) → Classify(15s) → Research 다이제스트(25s) → Business 다이제스트(25s) → 핸드북(100s)
                                   ↑ 대기                    ↑ 대기              ↑ 대기
총: ~170s
```

---

## 최적화 계획

### OPT-01: Research + Business 다이제스트 병렬화
- **현재**: Research 3 페르소나(순차) → Business 3 페르소나(순차) = ~50s
- **변경**: `asyncio.gather(research, business)` = ~25s
- **절감**: 시간 ~25s (50%)
- **수정 파일**: `pipeline.py` — `run_daily_pipeline()` 내 다이제스트 생성 루프
- **리스크**: 없음 (독립 데이터, OpenAI 동시 호출 제한은 tier 3 이상 충분)

### OPT-02: 핸드북 4-call 중 Call 2 + Call 3 병렬화
- **현재**: Call 1(KO Basic) → Call 2(EN Basic) → Call 3(KO Adv) → Call 4(EN Adv) = ~20s/용어
- **변경**: Call 1 → `asyncio.gather(Call 2, Call 3)` → Call 4 = ~15s/용어
- **절감**: 용어당 ~5s, 5개 기준 ~25s
- **수정 파일**: `advisor.py` — `_run_generate_term()`
- **리스크**: Call 2, 3이 Call 1의 definition을 context로 받으므로 Call 1 완료 후 실행 필수. Call 4는 Call 3의 KO context 필요 → Call 2\|\|3 → Call 4 순서 유지.

### OPT-03: 핸드북 용어 동시 생성 (2개씩)
- **현재**: 용어 5개 × 15s = 75s (순차)
- **변경**: 2개씩 병렬 = ~45s
- **절감**: ~30s (40%)
- **수정 파일**: `pipeline.py` — `_extract_and_create_handbook_terms()` 루프
- **리스크**: OpenAI rate limit (tier 3 기준 RPM 5000이므로 2개 동시 문제 없음)

### OPT-04: 데드 코드 정리
- `_generate_post()` — v3 다이제스트 전환 후 미사용. 제거.
- `_filter_terms_with_llm()` — 호출부 이미 제거. 함수 자체도 제거.
- **리스크**: 없음 (git history에 보존)

---

## 적용 후 예상

```
[병렬 실행 — 최적화 후]
Collect(5s) → Classify(15s) → Research + Business 병렬(25s) → 핸드북 병렬(45s)
총: ~90s (현재 대비 47% 단축)
```

| 항목 | 현재 | 최적화 후 | 절감 |
|------|------|----------|------|
| 총 실행 시간 | ~170s | ~90s | **47%** |
| 비용 | ~$1.25-1.50 | 동일 | 0% (병렬화는 비용 불변) |
| LLM 호출 수 | ~28-30 | ~28-30 | 0% (호출 수 불변) |

---

## 구현 순서

1. OPT-01 (다이제스트 병렬) — 가장 간단, 효과 큼
2. OPT-02 (핸드북 call 병렬) — 의존성 순서 주의 필요
3. OPT-03 (용어 동시 생성) — 세마포어로 동시 실행 제한
4. OPT-04 (데드 코드 정리) — 마지막에 클린업

## 검증

- `ruff check .` + `pytest tests/ -v` 통과
- 파이프라인 1회 실행 → pipeline_logs에서 총 시간 비교
- 모든 페르소나 3개 완성 확인 (누락 없음)

---

## Related

- [[AI-News-Pipeline-Design]] — 파이프라인 전체 설계
- [[2026-03-16-daily-digest-design]] — v3 다이제스트 설계
- [[2026-03-16-auto-publish-roadmap]] — 자동 발행 로드맵
