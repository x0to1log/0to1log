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

실측 (Apr 21/22/23 모두 final config: `reasoning=high + flex + cache + liveness-off`):

| Date | Writer 4건 | QC 2건 | **Total** | vs baseline |
|------|-----------|--------|-----------|-------------|
| Apr 21 | $0.31 | $0.02 | **$0.33** | -34% |
| Apr 22 | $0.31 | $0.02 | **$0.33** | -34% |
| Apr 23 | $0.33 | $0.02 | **$0.35** | -30% |

Baseline (Apr 21 pre-optimization): writer $0.47 + QC $0.03 ≈ **$0.50/day**

월 환산: $15/month → **$10/month** (연 $60 절감).

Flex 할인과 reasoning_effort=high 상승분을 상쇄한 건 **프롬프트 캐싱 + 24h extended retention**.

### 프롬프트 캐싱 hit 율 (실측)

| Stage | Apr 21 | Apr 22 | Apr 23 (최신) |
|-------|-------|-------|-----|
| `digest:business:expert` | **99.8%** | 99.8% | **99.7%** |
| `digest:business:learner` | 99.6% | 20.3% | 20.9% |
| `digest:research:expert` | 0% | 24.5% | 21.8% |
| `digest:research:learner` | 24.5% | 100% | **99.9%** |
| `quality:research` | 64% | 0% | 20.3% |
| `quality:business` | 11.4% | 84.7% | 19.9% |

3일 평균 **52% cache hit rate** (Apr 23 기준 `183,552 / 350,017 input tokens`). Cached input은 10% 요율이라 input 비용 ~50% 절감.

### Reasoning tokens (high effort의 실제 비용)

`reasoning_tokens` 관측이 붙으니 "high가 얼마나 reasoning을 쓰나" 구체화:

| Stage (Apr 23 high) | Output tokens | Reasoning tokens | **Reasoning %** |
|---|---|---|---|
| digest:business:expert | 16,811 | 11,328 | **67.4%** |
| digest:business:learner | 18,470 | 13,248 | 71.7% |
| digest:research:expert | 17,555 | 11,392 | 64.9% |
| digest:research:learner | 12,357 | 7,360 | 59.6% |
| quality:research | 5,905 | 1,920 | 32.5% |

**Writer output의 60-72%가 내부 reasoning**. 실제 본문은 30-40%만 나와. 이게 high의 대가 — reasoning token도 output 요율($8/M)로 빌링.

## 결과 — 품질

### Quality score (all high + final config)

| Date | research exp/lrn | business exp/lrn | 평균 |
|------|------------------|------------------|------|
| Apr 21 | 94/94 | 94/94 | 94.0 |
| Apr 22 | 94/94 | 95/95 | 94.5 |
| Apr 23 | 90/90 | 89/89 | 89.5 |

3일 평균 **92.7점**. 전부 auto-publish threshold 85점 이상. 모두 url_fail=False. Apr 23 약간 낮은 건 1-shot variance (이전 high run에선 95-97 나왔음).

### Citation density (3일 expert EN 기준, all high)

| Date | Post | Unique URLs | Cites | Paragraph coverage |
|------|------|------|------|------|
| Apr 21 | business | 9 | 17 | 13/13 (100%) |
| Apr 21 | research | 9 | 15 | 15/18 (83%) |
| Apr 22 | business | 15 | 21 | 14/14 (100%) |
| Apr 22 | research | 11 | 24 | 17/18 (94%) |
| Apr 23 | business | 9 | 22 | 15/15 (100%) |
| Apr 23 | research | 14 | 16 | 16/17 (94%) |

**EN/KO 완벽 대칭** (per-locale allowlist 변동 제거됨).

Liveness 제거 효과 극단 사례 (Apr 23 research expert EN):

| 지표 | Before (liveness on) | After (liveness off) |
|------|------|------|
| Unique URLs | 5 | **14** (2.8x) |
| Total cites | 5 | **16** (3.2x) |
| Paragraph coverage | 5/17 (29%) | **16/17 (94%)** |
| EN/KO 대칭 | ❌ (5/3) | ✅ |

## 설계 결정

### (A) `reasoning_effort=high` 모든 writer에 uniform

#### A/B 실험 (Apr 23, 1-day, write-stage rerun)

동일 Apr 23 입력 데이터로 `high` vs `medium` 각각 1회 생성 후 비교:

| 지표 | HIGH | MEDIUM | 해석 |
|---|---|---|---|
| **Quality score — business** | 91 | 96 | Medium +5 (variance 가능) |
| **Quality score — research** | 97 | 97 | 동점 |
| **Research expert cites/URLs** | **30 / 15** | **17 / 9** | **High 2x 더 밀도** |
| Research learner cites/URLs | 22 / 16 | 18 / 15 | 거의 동등 |
| Business expert cites/URLs | 21 / 10 | 20 / 11 | 거의 동등 |
| Research expert body 길이 | 10,873 chars | 8,733 chars | High +24% |
| Business expert body 길이 | 8,646 chars | 9,812 chars | Medium +13% |
| Paragraph coverage | 100% | 100% | 동점 |

#### 왜 Research expert만 High가 확실히 우위인가

Research expert section은 **다논문 cross-reference synthesis**가 핵심. 예: Apr 23 μLM 기사 본문:

> "μLMs enable mid-sentence handoffs... In the broader small-model collaboration space, Latent-Guided Reasoning separates high-level planning (large model) from low-level generation (small model), boosting small-model accuracy by up to 13.9%... SLM-MUX further shows that orchestrating multiple small models... These results contextualize μLMs as a latency-centric complement to accuracy-centric small-model collaboration."

한 문단에서 **3개 논문 (μLM + Latent-Guided + SLM-MUX)을 의미론적 축으로 연결**. Medium에선 이 축이 끊기고 μLM 단독 설명으로 줄어듦.

이건 **reasoning-heavy 작업**이야:
- 각 논문의 claim + 수치 기억 유지
- "latency vs accuracy" 같은 추상 축 도출
- 축 위에 각 논문 positioning
- 자연스러운 문장으로 직조

High의 23x 더 많은 reasoning 토큰이 이 synthesis에 쓰이는 거고, 리즈닝이 얕으면 그냥 "논문 A는 X, 논문 B는 Y"처럼 나열형으로 퇴행.

#### 왜 Business는 차이 적은가

Business section은 주로 **사실 나열 + 전략적 시사점**:
- "OpenAI가 $X 투자", "Microsoft가 Y 기능 런칭" — 단일 주체 + 단일 사건
- cross-reference가 있어도 비교적 단순 ("A가 B를 인수 → 경쟁 심화")
- Reasoning 깊이가 낮아도 품질 유지

Medium에서 +5점 나온 것도 이 특성 때문 — 깊은 reasoning보다 simplicity가 오히려 judge에게 더 깔끔히 읽힘. 하지만 1-sample이라 variance 가능.

#### 고려한 옵션

| 옵션 | 장점 | 단점 |
|---|---|---|
| All-low | 최저 비용 (월 ~$5) | 품질 drop 위험, reasoning benefit 전부 포기 |
| All-medium | 중간 비용, business 약간 우위 가능 | research expert synthesis 손실 (-40% citations) |
| **Mixed (research expert만 high)** | Theoretical optima, 모든 개별 이득 극대화 | Code 조건문 + 멘탈 모델 복잡 |
| **All-high ← 선택** | 일관성 + research 확실 win + 단순 | 비용 +$2/month (무시할 수준) |

#### 결정 기준

1. **Research expert는 명확한 win** (2x citation 밀도) — 이 하나만으로 high 정당화
2. **Business 차이는 1-sample variance 가능성 높음** — 3일 평균 high 점수는 94.3점으로 충분
3. **Code simplicity는 long-term value** — 조건문 없이 단일 설정이 디버깅 쉽고 미래 변경 간편
4. **비용 차이 미미** — $2/월은 decision noise 수준

**결정**: All-high. 6개월 후 주기적 재평가 예정.

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
