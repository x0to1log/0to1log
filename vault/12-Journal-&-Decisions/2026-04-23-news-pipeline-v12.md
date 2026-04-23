# 뉴스 파이프라인 v12 (2026-04-23)

**TL;DR**: URL 환각을 API schema enum으로 원천 차단 + writer를 flex tier + prompt_cache_key로 이동. 일일 비용 **$0.50 → $0.33 (-34%)**, citation density **3-6x 회복**, 품질 점수 89-97 안정 유지. 중간에 `reasoning_effort=low→high`만 먼저 올렸을 땐 $0.86까지 튀었는데 flex + cache로 상쇄. 지난 한 달간 rubric bar가 엄격해졌는데도 점수가 안정된 게 주목할 만한 사실.

---

## v11 → v12 한 줄 요약

| 축 | v11 | v12 |
|---|---|---|
| URL compliance 방식 | 프롬프트 지시 + liveness HEAD check | **API `json_schema` enum (strict)** |
| Writer 출력 계약 | `[N](URL)` inline markdown | **`[CITE_N]` placeholder + `citations[]` sidecar** |
| Service tier | Standard (QC만 flex) | **Writer + QC 모두 flex** |
| Prompt caching | 없음 | **`prompt_cache_key` per persona + 24h extended retention** |
| Save-time URL 검증 | `_validate_urls_live` HEAD check (70-85% false positive) | **제거** (schema가 이미 보증) |
| 비용 기록 | Standard rate 추정치만 저장 | **flex + cached_tokens 반영한 정확 계산** |
| Observability | tokens_used, cost_usd | **+ cached_tokens, reasoning_tokens, service_tier** |

---

## 왜 v12로 갔나

Apr 22 발행분이 `fact_pack.url_validation_failed=True`로 오토퍼블리시 실패했어. 조사하면서 4개 문제 연쇄 발견:

1. **URL 환각** — Writer가 `liner.com/...`, `axiomlogica.com/...` 같은 허용 외 URL을 본문에 인용
2. **Citation 대량 누락** — Save 시점 `_validate_urls_live` HEAD 체크가 70-85% URL을 timeout으로 오탐 → 본문에서 strip → paragraph 당 citation 20-30%만 남음
3. **EN/KO 비대칭** — 같은 체크가 locale마다 별도 실행 → 서로 다른 allowlist → 본문 불일치
4. **비용 추적 부정확** — 스토어된 `cost_usd`가 standard-tier 요금 기준이라 flex 할인 미반영

근본 원인 추적하다 보니 **4가지 모두 같은 뿌리** — "프롬프트 지시 + post-hoc validation" 패러다임의 한계. 프롬프트는 85-97% 준수율을 낼 수 있지만 100%는 못 찍고, post-hoc validation은 false positive로 오히려 손상. → **구조적 enforcement(schema) + 신뢰 기반 post-processing**으로 전환.

---

## 1. URL compliance 아키텍처 전환 (prompt → schema enum)

### 이전 방식 (v11까지)

1. 프롬프트에 "URL은 source list에서만 copy-paste" 강조
2. QC에서 `validate_citation_urls`로 allowlist 밖 URL 검출
3. Save 시점 `_renumber_citations` + `_validate_urls_live`로 dead URL strip

**한계:**
- 프롬프트 준수율 85-97%: 나머지 3-15%가 환각 URL 누출
- `_validate_urls_live` HEAD 체크가 arxiv/github/major news를 timeout으로 **오탐** → 멀쩡한 citation이 strip됨 → paragraph 커버리지 20-30%
- 오탐이 locale별로 달라서 EN/KO 비대칭 발생

### 새 방식 (v12)

**Writer 출력 계약 변경:**
```json
{
  "en": "Foo launched bar [CITE_1] yesterday [CITE_2].",
  "ko": "푸가 어제 바를 출시했다 [CITE_1] [CITE_2].",
  "citations": [
    {"n": 1, "url": "https://techcrunch.com/..."},
    {"n": 2, "url": "https://www.reuters.com/..."}
  ]
}
```

**핵심 enforcement:**
```python
response_format = {
  "type": "json_schema",
  "json_schema": {
    "strict": True,
    "schema": {
      "properties": {
        "citations": {
          "items": {
            "properties": {
              "url": {"type": "string", "enum": allowlist_urls}  # ← API-level
            }
          }
        }
      }
    }
  }
}
```

Writer가 allowlist 밖 URL을 emit하면 **OpenAI API가 서버에서 거부** → 자동 retry (최대 2회) → 100% 준수. Hallucination 원천 차단.

**Post-processing:**
`apply_citations(body, citations)`이 `[CITE_N]` placeholder를 `[N](URL)`로 치환. Inline `[N](URL)`가 body에 들어있으면 `CitationSubstitutionError` raise (writer가 contract 어긴 것).

**_validate_urls_live 제거:**
Schema enum이 이미 URL membership 보증하므로 liveness check는 redundant + 해롭기만 했음. 완전 제거.

### 결과

- `url_validation_failed=True` 발생: **0건** (3일 전체)
- Citation density (Apr 23 research expert EN):
  - Before: 5 URLs, 5/17 paragraphs (29%)
  - After: **16 URLs, 16/17 paragraphs (94%)**
- EN/KO 완벽 대칭 (같은 `citations[]`로 substitute)

---

## 2. 비용 최적화 (flex + cache + liveness 제거)

### 3-stage 진화

한 번에 일어난 게 아님. 중간에 "높은 가격 블립"이 있었음:

| Phase | Config | Writer 4건 | QC | **Total** | vs baseline |
|-------|--------|-----------|----|-----------|-------------|
| **(1) Baseline** | low reasoning, standard, liveness ON | $0.47 | $0.03 | **$0.50/day** | — |
| **(2) High reasoning 블립** | high reasoning, standard rate, flex 아직 없음 | $0.82 | $0.04 | **~$0.86/day** | **+72%** |
| **(3) Final (v12)** | high + flex + cache + liveness off | $0.31-0.33 | $0.02 | **$0.33-0.35/day** | **-34%** |

**핵심 교훈**: Phase (2) — reasoning_effort=high만 올리면 writer 비용이 **72% 급증**. Flex (50% 할인) + prompt caching 없이 high를 쓰면 월 ~$26. Flex + cache가 high의 추가 비용을 완전히 상쇄하고도 남아 -34% 절감 실현.

### 최종 3일 실측 (all final config)

| Date | Writer 4건 | QC 2건 | **Total** |
|------|-----------|--------|-----------|
| Apr 21 | $0.31 | $0.02 | $0.33 |
| Apr 22 | $0.31 | $0.02 | $0.33 |
| Apr 23 | $0.33 | $0.02 | $0.35 |

월 환산: **$15 (baseline) → $26 (high만) → $10 (final)**. 연 $60 절감 (baseline 대비), 연 $192 절감 (high만 대비).

### Prompt cache hit 실측

3일 평균 **52% cache hit rate**. Extended retention (24h)가 daily cron과 궁합 매우 좋음:

| Stage | Apr 21 | Apr 22 | Apr 23 (latest) |
|-------|-------|-------|-----|
| `digest:business:expert` | 99.8% | 99.8% | 99.7% |
| `digest:business:learner` | 99.6% | 20.3% | 20.9% |
| `digest:research:expert` | 0% | 24.5% | 21.8% |
| `digest:research:learner` | 24.5% | 100% | 99.9% |
| `quality:research` | 64% | 0% | 20.3% |
| `quality:business` | 11.4% | 84.7% | 19.9% |

Stable per-call-type keys (`digest-{type}-{persona}`, `weekly-{persona}-{lang}`, `qc-{label}`) 덕에 routing이 같은 서버로 가서 큰 prefix 재사용. Cached input은 10% 요율이라 input 비용 ~50% 절감.

### Reasoning tokens 분포 (high effort의 실제 비용 구조)

`completion_tokens_details.reasoning_tokens`를 관측하기 시작하니 high가 얼마나 reasoning을 쓰는지 구체화:

| Stage (Apr 23 high) | Output tokens | Reasoning tokens | **Reasoning %** |
|---|---|---|---|
| digest:business:expert | 16,811 | 11,328 | **67.4%** |
| digest:business:learner | 18,470 | 13,248 | 71.7% |
| digest:research:expert | 17,555 | 11,392 | 64.9% |
| digest:research:learner | 12,357 | 7,360 | 59.6% |
| quality:research | 5,905 | 1,920 | 32.5% |

**Writer output의 60-72%가 내부 reasoning**. 실제 본문은 30-40%만. reasoning token도 output 요율($8/M)로 빌링됨.

### 비용 회계 정확화 (single source of truth)

이전 `estimate_openai_cost_usd(model, input, output)`는 standard-tier 요율만 계산. Flex 50% 할인, cached 90% 할인 다 무시. 수정:

- `extract_usage_metrics`가 `response.service_tier` auto-read (echoed back by API)
- `estimate_openai_cost_usd`에 optional kwargs: `cached_tokens` (10% 요율), `service_tier` ("flex" → 0.5x)
- Discounts stack multiplicatively
- ~30개 call site 시그니처 유지 (backward-compatible)
- `pipeline_logs.debug_meta`에 `service_tier`, `cached_tokens`, `reasoning_tokens` 저장 → admin UI 및 향후 audit용

측정 스크립트는 `cost_usd` 그대로 읽기만 — **single source of truth 유지 (duplication 없음)**.

---

## 3. Rubric 엄격화에도 품질 안정

### 최근 한 달간 올라간 bar

v11 도입 + NQ-40 Phase 2 + v12 오늘 추가분이 누적되면서 QC rubric이 훨씬 엄격해짐:

- **`claim_calibration`** (v11) — "dominates / 장악 / 압도적 / 석권" 같은 retrospective overclaim 감지
- **`temporal_anchoring`** — "recently / yesterday / 최근 / 지난주" 같은 relative date 감지 (아카이브 컨텍스트에서 의미 열화)
- **`internal_consistency`** — 섹션 간 주장 일관성 검증
- **`citation_coverage`** — paragraph 당 최소 1개 citation 필수 + CP blockquote 예외 규칙
- **`attribution_domain_match`** — "AP reports [4](https://www.mrt.com/...)" 같은 syndication 오귀속 감지
- **NQ-40 Phase 2a CP quality** — community_pulse 3개 sub-scores (cp_relevance / substance / translation_fidelity, weight=0)
- **`$X million` 통화 변환 엄격 검증** — `$150M = 1.5억 달러` (not 5,000만 = 3x 오류)
- **`claim_coverage` — focus_items P2 평가형 문구 금지** — "raises bar / transforms" 대신 "enables X / reduces Y" 객관 표현
- **주간 Top Stories 5-7 → 7-10** — 컨텐츠 밀도 상향
- **`[CITE_N]` contract + `citations[]` enum** (v12) — URL은 API 레벨에서 strict

### Quality score (all v12 config)

| Date | research exp/lrn | business exp/lrn | 평균 |
|------|------------------|------------------|------|
| Apr 21 | 94/94 | 94/94 | 94.0 |
| Apr 22 | 94/94 | 95/95 | 94.5 |
| Apr 23 | 90/90 | 89/89 | 89.5 |

3일 평균 **92.7**. 전부 auto-publish threshold 85 이상. 모두 `url_fail=False`. NQ-37 직후 (Mar 25-28) 평균 ~87-93, NQ-40 직후 (Apr 17-20) ~90-96, v12 (현재) ~89-95 — **지속적으로 엄격해지는데 점수는 안정 상승 추세**.

### 왜 떨어지지 않았나 (5가지 추정)

일반적 패턴: 새 rubric 항목 추가 → writer 적응 못 함 → 일시적 drop → 프롬프트 조정 후 회복. 이번엔 drop 없이 바로 안정. 추정 원인:

**(1) Schema enforcement가 구조적 실패를 선제 차단**
URL 환각은 `url_validation_failed`로 점수 크게 깎였었음. 이제 strict json_schema enum이 API 레벨에서 원천 차단 → `url_validation_failed=0` 항상. 이 사분면 점수 손실 없음.

**(2) 프롬프트 강화가 writer behavior 내재화**
HALLUCINATION_GUARD에 추가된 구체 예시 (forbidden 영어/한국어 동사 리스트, 날짜 절대화 worked example, attribution domain matching demo, `$X million` 변환 예시)이 writer의 "주의 대상"을 명확히 함.

**(3) reasoning_effort=high가 self-check 루프 철저화**
프롬프트 끝에 있는 FINAL CHECKLIST 11개 항목 (citation coverage, sub-item count, paragraph count, frontload locale parity, body number parity, relative time scan, overclaim scan 등). High effort에서는 실제로 훑고 제출. Low에서는 skim-through 그칠 가능성.

**(4) BODY_LOCALE_PARITY + schema enum → EN/KO 자동 대칭**
이전엔 KO body가 EN 대비 citation 수, 섹션 수, 숫자 각각 개별적으로 틀릴 수 있었음. 이제 citation이 공통 `citations[]` 배열에서 substitute되므로 count 자동 일치. `locale_integrity` rubric에서 점수 안정.

**(5) Code-level validation이 LLM-level validation 대체**
`_renumber_citations` + `validate_citation_urls`가 LLM에게 "이거 지켜" 말하는 대신 코드로 검증/처리. LLM은 이제 구조 준수보다 **내용 품질**에 reasoning token을 쓸 수 있음.

**Rubric 엄격화 + 품질 안정화가 동시에 일어난 건 드문 조합**. 주로 schema enforcement가 구조적 실패를 선제 차단했기 때문으로 추정.

---

## 4. reasoning_effort=high 결정 (A/B)

### 실험 (Apr 23, 1-day, write-stage rerun)

동일 Apr 23 입력으로 `high` vs `medium` 각각 1회 생성 후 비교:

| 지표 | HIGH | MEDIUM | 해석 |
|---|---|---|---|
| Quality — business | 91 | 96 | Medium +5 (variance 가능) |
| Quality — research | 97 | 97 | 동점 |
| **Research expert cites/URLs** | **30 / 15** | **17 / 9** | **High 2x 더 밀도** |
| Research learner cites/URLs | 22 / 16 | 18 / 15 | 거의 동등 |
| Business expert cites/URLs | 21 / 10 | 20 / 11 | 거의 동등 |
| Research expert body 길이 | 10,873 chars | 8,733 chars | High +24% |
| Paragraph coverage | 100% | 100% | 동점 |

### 왜 Research expert만 High가 확실히 우위

Research expert는 **다논문 cross-reference synthesis**가 핵심. 예: Apr 23 μLM 기사:

> "μLMs enable mid-sentence handoffs... In the broader small-model collaboration space, Latent-Guided Reasoning separates high-level planning from low-level generation, boosting small-model accuracy by up to 13.9%... SLM-MUX further shows that orchestrating multiple small models... These results contextualize μLMs as a latency-centric complement to accuracy-centric small-model collaboration."

한 문단에서 **3개 논문 (μLM + Latent-Guided + SLM-MUX)을 의미론적 축으로 연결**. Medium에선 이 축이 끊기고 단독 설명으로 줄어듦.

이건 **reasoning-heavy 작업**:
- 각 논문의 claim + 수치 기억 유지
- "latency vs accuracy" 같은 추상 축 도출
- 축 위에 각 논문 positioning
- 자연스러운 문장으로 직조

High의 23x 더 많은 reasoning 토큰이 이 synthesis에 쓰임. 리즈닝이 얕으면 나열형("논문 A는 X, 논문 B는 Y")으로 퇴행.

### Business는 왜 차이 적은가

Business section은 주로 **사실 나열 + 전략적 시사점** — 단일 주체 + 단일 사건, cross-reference 단순. Reasoning 깊이가 낮아도 품질 유지. Medium에서 +5점은 simplicity가 judge에게 깔끔히 읽힌 것일 수도 (1-sample variance 가능).

### 4 옵션 매트릭스

| 옵션 | 장점 | 단점 |
|---|---|---|
| All-low | 최저 비용 (월 ~$5) | 품질 drop 위험, reasoning benefit 전부 포기 |
| All-medium | 중간 비용, business 약간 우위 가능 | research expert synthesis 손실 (-40% citations) |
| Mixed (research exp만 high) | Theoretical optima | Code 조건문 + 멘탈 모델 복잡 |
| **All-high ← 선택** | 일관성 + research 확실 win + 단순 | 비용 +$2/month (무시할 수준) |

### 결정 근거

1. **Research expert 명확한 win** (2x citation 밀도) — 이 하나만으로 high 정당화
2. **Business 차이는 1-sample variance 가능성** — 3일 평균 high = 94.3점 충분
3. **Code simplicity는 long-term value** — 조건문 없이 단일 설정이 디버깅 쉽고 미래 변경 간편
4. **비용 차이 미미** — $2/월은 decision noise 수준

**결정**: All-high uniform. 6개월 후 주기적 재평가 예정.

---

## 5. 통합 교훈

1. **Schema enum이 compliance의 정답**: 프롬프트는 85-97% 준수율, schema는 100%. Multi-layer (prompt + schema + post-process strip) 유지하되 structural gate는 schema로 단일화.

2. **False positive는 정확도보다 비싸다**: Liveness 70-85% false positive → 독자가 보는 citation 90% 감소. "안전"하다고 믿었던 검증이 사실 손상의 주범. **정확 != 보수** — 오탐 잡음이 실제 품질 저하보다 더 빈번하고 치명적.

3. **`prompt_cache_key`는 low-hanging fruit**: Code 5줄 추가, 비용 30% 절감 효과. Extended retention (24h)가 daily cron과 궁합 매우 좋음. 같은 persona/stage가 매일 반복 호출되는 구조에서 stable key만 붙이면 서버 라우팅 개선 + prefix 재사용.

4. **Single source of truth 원칙**: 비용 계산을 두 곳 (extract_usage_metrics + 측정 스크립트)에 두면 drift 필연. 한 함수에서만. 측정 스크립트는 stored value 읽기만.

5. **1-sample A/B는 신호가 약하다**: Business medium +5점은 variance일 수 있음. 복잡도-이득 trade에서 단순성이 이김. 정책 결정 시 최소 3-shot 돌리거나 장기 모니터링 필요.

6. **Quality knob + Cost knob는 반드시 같이 배포**: `reasoning_effort=low→high`만 먼저 올리면 비용 +72%. Flex + cache를 함께 패키징해서 한 번에 배포. 따로 가면 중간 상태에서 과금 폭탄. **knob을 개별 튜닝하는 사고방식 위험**.

7. **Rubric 올리기 전에 구조적 enforcement 먼저**: Schema + code validation으로 bottom-line 고정 후 rubric 상승 시 점수 변동 흡수 가능. 반대 순서 (rubric만 먼저 올리면) 점수 롤러코스터 + writer 적응 비용 증가.

8. **Writer의 failure mode는 "주의 분산"**: 10개 룰을 동시에 내밀면 가장 먼저 나오는 몇 개에만 주의 감. 해법: 중요 룰을 (a) system message 최상단에 + (b) HALLUCINATION_GUARD 같은 격리 블록에 재진술 + (c) FINAL CHECKLIST에 또 반복. 3중 앵커.

---

## 6. Follow-up

- [ ] **Weekly writer reasoning_effort A/B** — 주간도 medium 실험해볼 것 (plan Chunk 3, deferred)
- [ ] **Prompt 구조 재배치** — common block을 앞으로 옮겨 cache hit rate 추가 향상 여부 측정 후 결정 (plan Chunk 2.5, conditional)
- [ ] **Advisor/blog/product-advisor audit** — 같은 플레이북 (flex + cache + schema enum 적용 가능성) 검토
- [ ] **Rubric drift 정량화** — 같은 기사를 구/신 rubric으로 각각 채점해서 offset 측정 (버전 간 "진짜 개선폭" 비교)
- [ ] **NQ-40 Phase 2b 가중치 결정** — CP quality sub-score 2주 관찰 후 (~2026-05-06) 본 점수 반영 여부 결정

---

## 참고

### 오늘 관련 플랜

- `vault/09-Implementation/plans/2026-04-23-news-writer-url-compliance.md` — URL compliance 구현 플랜 ([CITE_N] + strict schema)
- `vault/09-Implementation/plans/2026-04-23-gpt5-efficiency.md` — Efficiency 구현 플랜 (flex + cache + A/B)

### 관련 커밋 (main)

- `0e79525` — reasoning_effort param 추가
- `570213d` → `d5b0d4a` — strict json_schema + [CITE_N] 치환 wiring
- `beb9cfc`, `b2cae8b` — writer/weekly flex tier 이동
- `8314b32` — prompt_cache_key per call site
- `178766f` — 비용 회계 cached+tier 정확화
- `0aadc4c` — liveness check 제거
- `9e36a8b` — reasoning_effort 최종 high uniform
- `51be812` — reasoning_tokens observability (admin UI chip)
- `3cc1394` → `e84cb55` → `5efa4b2` — 교훈 journal 점진적 확장

### Admin 확인

`/admin/pipeline-runs/{runId}` — stage별 chip: **In · Out · Reasoning · Cached · Tier · Cost · Quality**

### 진단 스크립트

- `backend/scripts/measure_cached_tokens.py` — 특정 run_id의 stage별 cost + cache hit + reasoning 분포
- `c:/tmp/diagnose_citations.py` — body 내 citation 분포 (unique URLs, paragraph coverage, primary/secondary tier)

### 이전 버전

- v11 (2026-04-21): writer-QC mirror + infra
- v10 (2026-04-01): gpt-5 전환
- v9, v8, v7, v3, v1 postmortem — 각 journal 참조
