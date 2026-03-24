# 결정: 3티어 LLM 모델 구조 도입

> 날짜: 2026-03-24
> 맥락: 전체 AI advisor 38개 LLM 호출 감사 후 모델 적합성 분석

---

## 문제

기존 2티어 구조 (gpt-4.1 main + gpt-4.1-mini light)에서 **판단/추론 태스크**에 gpt-4.1을 사용.
gpt-4.1은 콘텐츠 생성에 강하지만, 팩트체크·분류·품질 평가 같은 **다단계 추론**에는 o-series가 더 적합.

## 결정

3티어 모델 구조 도입:

| 티어 | 모델 | 용도 |
|------|------|------|
| **main** | `gpt-4.1` | 콘텐츠 생성, 번역, 장문 작성 |
| **light** | `gpt-4.1-mini` | SEO, 키워드, 단순 추출, 코퍼스 |
| **reasoning** | `o4-mini` | 팩트체크, 분류, 품질 평가, 랭킹 |

## 변경된 호출

### main → reasoning (o4-mini)
- News: factcheck, deepverify (claim extraction + verification), conceptcheck
- Handbook: self_critique, quality_check
- Ranking: rank_candidates, classify_candidates

### main → light (gpt-4.1-mini)
- Product: Call 2 (enrichment — scenarios, pros_cons, difficulty)

### Temperature 조정
- Product Call 1: 0.6 → 0.4 (사실 추출 비중이 높아서)
- Product Call 2: 0.6 → 0.5

## 기술 고려사항

- o4-mini는 `max_tokens` 대신 `max_completion_tokens` 사용
- o4-mini는 `response_format: json_object` 미지원 → `build_completion_kwargs()` 헬퍼로 자동 분기
- `is_o_series()` 판별 함수로 o1/o3/o4 계열 통합 처리

## 영향

- 팩트체크/랭킹 품질 향상 예상 (추론 특화 모델)
- Product enrichment 비용 ~80% 절감 (main → light)
- 전체 비용은 유사 (o4-mini input $1.10/1M vs gpt-4.1 $2.00/1M)

## 파일

- `backend/core/config.py` — `openai_model_reasoning` 추가
- `backend/services/agents/client.py` — `is_o_series()`, `build_completion_kwargs()` 헬퍼
- `backend/services/agents/advisor.py` — factcheck, deepverify, conceptcheck, self_critique, quality_check
- `backend/services/agents/ranking.py` — rank_candidates, classify_candidates
- `backend/services/agents/product_advisor.py` — Call 2 model + temp 변경
