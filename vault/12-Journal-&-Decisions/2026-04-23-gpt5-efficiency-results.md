# GPT-5 Efficiency Overhaul — Results (2026-04-23)

**TL;DR**: Writer + QC 일일 비용 ~34% 감소 ($0.50 → $0.33), citation density 3-6x 회복, 품질 점수 유지 (91-97). 프롬프트 캐싱 평균 50% 적중. URL hallucination은 schema enum으로 API 레벨 차단.

---

## 왜 했나

Apr 22 원래 발행본이 오토퍼블리시 실패 — `fact_pack.url_validation_failed=True`로 게이트에 걸림. 조사하면서 여러 층의 문제 발견:

1. **URL hallucination**: Writer가 `liner.com/...`, `axiomlogica.com/...` 같은 허용 외 URL을 본문에 인용
2. **Citation 대량 누락**: Save 시점 `_validate_urls_live` HEAD 체크가 70-85% URL을 timeout으로 오탐 → 본문에서 strip → paragraph 당 citation 20-30%만 남음
3. **EN/KO 비대칭**: 같은 체크가 locale마다 별도 실행 → 서로 다른 allowlist → 본문 불일치
4. **비용 추적 부정확**: 스토어된 `cost_usd`가 standard-tier 요금 기준이라 flex 할인 미반영

## 한 일

### 1) URL compliance plan (`vault/09-Implementation/plans/2026-04-23-news-writer-url-compliance.md`)

- Writer output 계약 재설계: `[CITE_N]` placeholder + `citations[]` 배열
- OpenAI strict `json_schema` + `citations[].url: enum [allowlist]` → **API가 허용 외 URL 거부**
- `apply_citations()` post-processor: placeholder → `[N](URL)` 치환
- 프롬프트 4곳 업데이트 (HALLUCINATION_GUARD, Writing Rules 1, 템플릿 예시, FINAL CHECKLIST)

### 2) GPT-5 efficiency plan (`vault/09-Implementation/plans/2026-04-23-gpt5-efficiency.md`)

- `service_tier="flex"` 적용: daily writer + QC + weekly writer (50% 할인)
- `with_flex_retry` helper (429 exponential backoff)
- `prompt_cache_key` per persona (`digest-{type}-{persona}`, `weekly-{persona}-{lang}`, `qc-{label}`)
- `reasoning_effort="high"` for all writers (uniform — A/B 후 단순성 선택)
- `_apply_gpt5_compat`에 temperature strip 유지 (legacy caller 보호)

### 3) Liveness check 제거 (citation 복원 결정타)

`_validate_urls_live` HEAD 체크가 arxiv/github/major news를 timeout으로 오탐. Strict schema + enum이 이미 hallucination 차단하므로 liveness는 중복 + 피해 커서 제거.

### 4) 비용 회계 정확화 (single source of truth)

- `extract_usage_metrics`가 `response.service_tier` auto-read → flex 자동 반영
- `estimate_openai_cost_usd` optional kwargs: `cached_tokens` (10% 요율), `service_tier` ("flex" → 0.5x)
- ~30개 call site 시그니처 유지 (backward compat)
- `reasoning_tokens` 추출 + `pipeline_logs.debug_meta` + admin UI chip

## 결과 — 비용

실측 (Apr 21/22/23 final config rerun):

| Date | Writer 4건 | QC 2건 | **Total** | vs baseline |
|------|-----------|--------|-----------|-------------|
| Apr 21 | $0.31 | $0.02 | **$0.33** | -34% |
| Apr 22 | $0.31 | $0.02 | **$0.33** | -34% |
| Apr 23 | $0.33 | $0.02 | **$0.35** | -30% |

Baseline (Apr 21 pre-optimization): writer $0.47 + QC $0.03 ≈ **$0.50/day**

월 환산: $15/month → **$10/month** (연 $60 절감).

Flex 할인과 reasoning_effort=high 상승분을 상쇄한 건 **프롬프트 캐싱**:

| Stage | Apr 21 cache hit % | Apr 22 | Apr 23 (earlier, cache 미웜업) |
|-------|-------|-------|-----|
| `digest:business:expert` | **99.8%** | 99.8% | 0% |
| `digest:business:learner` | 99.6% | 20.3% | 0% |
| `digest:research:expert` | 0% | 24.5% | 0% |
| `digest:research:learner` | 24.5% | 100% | 0% |
| `quality:research` | 64% | 0% | 10.7% |

Cache TTL이 24h extended retention으로 확장되면서 같은 `prompt_cache_key`가 연속 호출에서 큰 prefix를 재사용. 관측된 평균 50% hit.

## 결과 — 품질

### Quality score

| Date | research exp/lrn | business exp/lrn |
|------|------------------|------------------|
| Apr 21 | 94/94 | 94/94 |
| Apr 22 | 94/94 | 95/95 |
| Apr 23 | 95-97/95-97 | 91-96/91-96 |

전부 auto-publish threshold 85점 이상. 모두 url_fail=False.

### Citation density

Liveness 제거 효과 (Apr 23 research expert EN 기준):

| 지표 | Before (liveness on) | After (liveness off) |
|------|------|------|
| Unique URLs | 5 | **16** (3.2x) |
| Total cites | 5 | **30** (6x) |
| Paragraph coverage | 5/17 (29%) | **17/17 (100%)** |
| EN/KO 대칭 | ❌ | ✅ |

3일 평균 (final config): **EN/KO 완벽 대칭, 100% paragraph coverage, 9-16 unique URL/post**.

## 설계 결정

### (A) `reasoning_effort=high` 모든 writer에 uniform

1-day A/B에서 Apr 23 medium은:
- Business 품질 +5점 (medium 우위)
- Research expert citation 반토막 (30 → 17, 다논문 synthesis 손실)
- Research learner는 동등

고려한 옵션:
- Mixed (research expert만 high) — theoretical optima이나 code complexity
- All-low — 과한 비용 절감, 품질 drop 위험
- **All-high — 선택**: 일관성 + research expert 확실한 win + 비용 차이 $2/month로 무시할 수준

### (B) Liveness check 완전 제거

대안: timeout 드롭을 "살아있음"으로 해석 (benefit-of-doubt). 하지만 schema enum이 이미 URL 정당성 보장하므로 liveness 자체가 redundant. 완전 제거.

### (C) 비용 회계는 single source of truth 유지

측정 스크립트가 cost 재계산하면 "2 system" 안티패턴. `estimate_openai_cost_usd`만 single truth로. `response.service_tier`를 auto-detect해서 call site 변경 0개.

## 교훈

1. **Schema enum이 compliance의 정답**: 프롬프트는 85-97% 준수율, schema는 100%. Multi-layer (prompt + schema + post-process strip)를 쓰되 strip은 schema로 단일화.
2. **False positive는 정확도보다 비싸다**: Liveness 70-85% false positive → 독자가 보는 citation 90% 감소. "안전"하다고 믿었던 검증이 사실 손상의 주범.
3. **`prompt_cache_key`는 low-hanging fruit**: Code 5줄 추가, 비용 30% 절감 효과. Extended retention(24h)가 daily cron과 궁합 매우 좋음.
4. **Single source of truth 원칙**: 비용 계산을 두 곳에 두면 drift 필연. 한 함수에서만.
5. **1-sample A/B는 신호가 약하다**: Business medium +5점은 variance일 수 있음. 복잡도-이득 trade에서 단순성이 이김.

## Follow-up

- [ ] Weekly writer도 `reasoning_effort=medium` A/B 실험 (별도 Task, 이번 plan Chunk 3에 plan 존재)
- [ ] Prompt 구조 재배치 (common block을 앞으로) — cache hit rate 추가 향상 여부 측정 후 결정 (plan Chunk 2.5, conditional)
- [ ] Advisor/blog_advisor/product_advisor audit — 같은 플레이북 적용 가능한지

## 참고

- URL compliance 플랜: `vault/09-Implementation/plans/2026-04-23-news-writer-url-compliance.md`
- Efficiency 플랜: `vault/09-Implementation/plans/2026-04-23-gpt5-efficiency.md`
- 커밋 범위: `0e79525`(reasoning_effort 파라미터 추가) → `51be812`(reasoning_tokens observability) — 총 21 커밋
- Admin UI: `/admin/pipeline-runs/{runId}` 에서 stage별 In/Out/Reasoning/Cached/Tier/Cost/Quality chip 확인 가능
- 진단 스크립트: `backend/scripts/measure_cached_tokens.py`
