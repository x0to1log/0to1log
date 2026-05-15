# 뉴스 파이프라인 v13 (2026-05-11)

**TL;DR**: 3-persona 확장 (beginner 추가) + quiz-only daily pipeline 분리 + infra hardening 2차 wave (flex→standard fallback, retry-storm cost capture, attempts_log) + 콘텐츠 톤/접근성 refinement (KO chatty 금지, EN acronym, calibrated scope). v12가 **URL compliance 한 축**의 진화였다면, v13은 **audience / pipeline / content / infra / observability 5축 동시 진화**. 평소 OpenAI / 우리 기록 ratio는 **3.5x → 1.0x**로 정확화 (May 7 retry storm postmortem 기반), 5/7+5/9 incident 재발 방지용 tier fallback 가드 추가.

---

## v12 → v13 한 줄 요약

| 축 | v12 (2026-04-23) | v13 (2026-05-11) |
|---|---|---|
| Audience | expert + learner (2-persona) | **expert + learner + beginner (3-persona)** |
| 파이프라인 모드 | daily digest 단일 | **daily digest + quiz-only news (2 modes)** |
| Quiz 스키마 | 없음 / legacy | **`answer_index` 0-3 standardized contract** |
| URL 처리 | `json_schema` enum (v12 핵심) | **+ classify tier×freshness gate, + Exa enrich tier gate** |
| Service tier 전략 | writer/QC 모두 flex | **flex on attempt 0 → standard on retry (no queue fallback)** |
| Retry timeout | 900s | **1200s + per-attempt cost capture + tier-aware extract** |
| Observability | tokens + cached + tier + reasoning_tokens | **+ attempts_log per-attempt timeline (admin debug_meta panel)** |
| KO 톤 | 일반 룰 | **rule 6 chatty marker 금지 (쉽게 말해 / 잖아요 / 죠 / 네요 등)** |
| EN 학습자 접근성 | KO-only acronym 룰 | **EN-side acronym expansion (both locales independent) + scope/scale calibration** |
| Cost tracking 정확도 | flex/cached 반영 (v12 추가분) | **+ retry-storm gap fix (gap A/B), tier-aware estimate** |
| Failure mode 대응 | 단순 retry | **timeout + tier fallback + tiktoken input estimation on no-response** |

---

## 왜 v13으로 갔나

5월 들어 **두 종류의 트리거**가 동시에 도래:

### Trigger 1 — Audience 확장 필요 (NQ-44)

학습자 모드를 honest review 했을 때 — 본문 길이 5-6k자, reading 9-10분, 한 단락에 약자 7개 (MTP/KV/MoE/vLLM/SGLang/Ollama/Apache 등) — 정의된 audience ("25-40세 비개발자 직장인, ChatGPT는 매일 쓰지만 논문 경험 0")와 disconnect가 분명함. v11 / v12 시기 learner는 "expert minus jargon"에 가까운 풀어쓴 신문체였지 진짜 "쉬운 뉴스"가 아니었다. **Audience를 정직하게 만들려면 (a) 학습자 본문 자체 재설계 OR (b) 진짜 입문자용 3rd persona 별도 추가**. v13에서는 (b) 경로 — 학습자/전문가는 보존, 그 아래 beginner를 옵션 layer로 둠.

### Trigger 2 — Infra fragility 재발 (5/7, 5/9 incident)

5/7 cron에서 `digest:research:learner` 3회 timeout (총 58분), `cost_usd=null` 기록. 5/9 cron에서 `digest:business:learner` 동일 패턴. 둘 다 **flex tier 큐 saturation**이 원인 — best-effort SLA라 OpenAI 쪽 트래픽 spike에 우리가 그대로 노출됐고, retry 3회를 같은 막힌 큐에 다시 줄세우는 게 도움이 안 됨. OpenAI 청구 $1.53 vs 우리 기록 $0.43 (**3.5x gap**) — gap의 큰 부분이 retry storm cost tracking 누락. v12에서 만든 비용 정확화는 success path만 cover했고, **failure path (timeout / 3-attempt-all-fail) 는 여전히 silent loss**였다는 게 드러남.

→ Trigger 1은 콘텐츠 진화, Trigger 2는 인프라 진화. 같은 sprint 안에서 처리되며 v13 패키지가 됨.

---

## 1. Audience 확장: 2-persona → 3-persona (+beginner)

### 구조 변경

```python
# backend/services/pipeline_digest.py
DAILY_DIGEST_PERSONAS: tuple[str, ...] = ("expert", "learner", "beginner")
REQUIRED_DAILY_DIGEST_PERSONAS: tuple[str, ...] = ("expert", "learner")
```

- **DAILY_DIGEST_PERSONAS**: 생성 시 시도할 페르소나 전체 (3개)
- **REQUIRED_DAILY_DIGEST_PERSONAS**: 발행 게이트 (2개 — expert/learner는 필수, beginner는 옵션)

→ **beginner가 실패해도 expert/learner만 있으면 publish 가능.** 새 persona 도입의 운영 리스크를 낮추는 보수적 접근. Beginner 콘텐츠가 안정화되면 REQUIRED에 추가 검토.

### 작업 단위

- `82332d55 feat: add beginner news persona` (5/13)
- `f7e87bf2 feat: add english beginner backfill support`
- `92ffbb06 fix: stabilize beginner persona news display`
- `62fe61cd feat: add beginner news quiz backfill`
- `d8b7c4cb feat: add beginner rerun admin controls`
- prototype: `backend/scripts/prototype_beginner_news.py` (1086 lines, audience 정의 + skeleton 실험)

### Sprint 추적

- **NQ-44 Beginner persona news experiment** (ACTIVE_SPRINT.md, doing, 2026-05-13 → 2026-05-20)
- 목표: 3페르소나 확장 전 입문자 뉴스 설계/내부 생성 실험
  - Research/Business 각각 맥락 해설형 포맷
  - 메인 2-3개 재선정 (전체 다 다루지 않고 가중치)
  - "가볍게 지나가도 되는 소식" 카테고리
  - 학습자 뉴스 이어읽기 경로
  - 비용/저장/UI 게이트 정의

### 관찰 윈도우

- 2026-05-20까지: beginner 콘텐츠 internal review (점수, 가독성, audience fit)
- Pass 시 REQUIRED 승격 검토
- Fail 시 retire 또는 추가 iteration

---

## 2. Quiz-only daily news 별도 파이프라인

### 분리 이유

- daily digest 안에서 quiz를 같이 생성하면 writer가 본문 + 퀴즈를 한 호출에 처리 → reasoning 부하 분산
- quiz는 본문보다 짧고 빠른 (max_tokens 작음) 다른 cost profile
- 별도 모드로 분리 시 backfill / regen이 독립적 (퀴즈만 다시, 본문은 보존)

### 작업 단위

- `6b43c560 docs: add quiz-only news pipeline plan` — `docs/plans/2026-05-15-quiz-only-news-pipeline.md` (629 lines)
- `2404bc15 feat: add quiz-only daily news generation`
- Quiz schema 별도: `backend/services/agents/schemas/news_quiz.py`

### Quiz answer_index 계약 표준화

`answer_index` 0-3 정수 emit + legacy text fallback. 관련 커밋:
- `ea70c571 docs(plan): cp voice normalization + quiz answer_index contract`
- `7fcd1eed feat(weekly-prompt): emit quiz answer_index 0-3 for weekly recap`
- `457f8bfd feat(news-writer-prompt): emit quiz answer_index 0-3 for daily`
- `6b40ec7c feat(news-writer): switch quiz schema to answer_index`
- `5c6fd8a0 fix(quiz): reject bool answer_index, sharpen precedence test, log question`
- `75f569b7 feat(quiz): validator accepts answer_index, legacy answer text fallback`

→ 정수 기반 정답 식별이 frontend 렌더링/셔플링과 결합도 낮춤. Locale 변경 시 text가 달라져도 index는 유지.

---

## 3. 인프라 reliability 하드닝 (5/7, 5/9 incident 대응)

### 5/7 incident postmortem

- 22:18 UTC cron 시작
- 22:42 business:expert 19.8분 (timeout 한계 15분 근접)
- 23:26 research:learner 3 attempts × ~20min = 58.5분 → `failed after 3 attempts: Request timed out.`
- summary row total_cost=$0.214 (우리 기록), OpenAI 청구 $1.53 → **gap $1.31 unrecorded**
- 분석: timeout 900s가 flex 큐 saturation 날에 부족, retry storm은 cost record null

### 5/9 incident

- 같은 cron 안에서 4 digest 중 3개가 retry 필요
- research:expert att=2 (3rd attempt 성공), 1779s 총 소요
- business:learner att=3 failed (3회 모두 timeout)

→ **decompositional fixes 4개 layer:**

#### Layer A: timeout headroom

```python
# pipeline_digest.py
timeout=1200,  # was 900
# 2026-05-08: bumped after May 7 incident where business:expert took 19.8min
# and research:learner timed out 3x at the 15-min limit. Flex queue waits + 
# high reasoning need more headroom on busy days.
```

Commit: `6d178532 fix(news-pipeline): track cost on retry-storm timeouts + bump digest timeout`

#### Layer B: Cost capture on no-response failure (tiktoken estimate)

`extract_usage_metrics`는 response 객체 필요. timeout이면 response 없음 → 토큰/비용 null. 새 helper `estimate_failed_call_usage()` 추가:

```python
def estimate_failed_call_usage(messages, model_name, requested_service_tier="flex") -> dict:
    # tiktoken로 input 토큰 best-effort 추정
    # output_tokens=0 (timeout 시 부분 출력은 알 수 없음)
    # estimated=True 플래그
```

→ 호출 실패해도 input cost는 estimate로 기록. OpenAI는 어차피 청구함.

#### Layer C: Cost extraction을 parse 전으로 이동 (gap A fix)

```python
response = await with_flex_retry(_writer_call)
# v13: gap-A fix — extract IMMEDIATELY so any parse/validation failure below
# still keeps the cost on books
usage = extract_usage_metrics(response, model, requested_service_tier=tier_for_attempt)
cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
data = parse_ai_json(...)  # parse can fail; usage already recorded
```

→ `CitationSubstitutionError`, schema reject, JSON parse fail 발생해도 그 attempt의 cost는 잡힘.

#### Layer D: flex → standard tier fallback on retry

```python
for attempt in range(MAX_DIGEST_RETRIES + 1):
    # v13: flex on first attempt only; retries drop to standard tier
    # (no queue, real-time endpoint, ~2x cost). May 7+9 incidents both had
    # 3 attempts hit the 1200s timeout because the flex queue was saturated
    # AND we kept re-queueing into the same congested pool. Standard tier
    # has no queue so retries land fast.
    tier_for_attempt: str | None = "flex" if attempt == 0 else None
```

Commit: `db1ac147 fix(news-pipeline): drop flex on retry — switch to standard tier when flex queue saturates`

**비용 영향:** 평소 큐 한가하면 첫 시도 성공 → flex 그대로. 큐 막힌 날만 그 stage가 standard로 fallback → ~2x cost (50% 할인이 없어짐). **publish 실패 vs 일부 stage cost +50% 사이의 trade-off가 명확히 후자 쪽으로**.

**Cache 영향:** `prompt_cache_key`는 attempt 간 동일 유지 → flex→standard에서도 prefix cache 작동 가능 (OpenAI 내부 동작 미확정, cached_tokens 추적으로 측정 예정).

---

## 4. Observability: attempts_log per-attempt timeline

### v12까지의 가시성

- `pipeline_logs` stage row 1개 per stage
- debug_meta JSON에 tokens / tier / cached / reasoning
- `attempts` 카운터 표시 (최종 attempt 번호만)

### v13 추가

각 attempt마다 entry push:

```json
"attempts_log": [
  {"attempt": 1, "tier": "flex",     "duration_s": 1200.1, "status": "failed",
   "error_class": "TimeoutError", "error_message": "Request timed out."},
  {"attempt": 2, "tier": "standard", "duration_s":  580.4, "status": "success",
   "ko_recovered": false, "en_recovered": false}
]
```

상태 가능값: `success` / `schema_reject` / `failed`. error_message는 200자 truncate. ko/en recovered 플래그도 success 시 함께 (recovery call 비용 visibility).

### Frontend 적용 비용

**0.** 기존 admin Stage Timeline의 `<details>debug_meta</details>` collapsible JSON 패널이 attempts_log key를 자동 렌더. 별도 UI 작업 불필요.

### 효과

- 5/7-5/9 같은 retry storm 재현 시 어드민 한 번 클릭으로 attempt별 tier/duration/error 식별
- Tier fallback이 실제로 fire했는지 verify (5/10, 5/11 cron에서는 fire 안 했음, all flex success)
- 비용 변동의 stage 단위 분해 (retry로 standard 친 attempt = 그 stage 비용 spike)

Commit: `8c46bba6 feat(observability): per-attempt timeline in digest writer debug_meta`

---

## 5. 콘텐츠 톤 / 접근성 refinement

### 5-1. KO chatty marker 금지 (rule 6, LEARNER_KO_LANGUAGE_RULE)

**Trigger**: 5/6 research-digest-ko learner 본문 vision section에 `쉽게 말해`가 mid-paragraph로 등장. QC가 "conversational marker breaking news-style prose"로 플래그.

**Rule 6 추가** (`prompts_news_pipeline.py`):
- 금지: `쉽게 말해`, `사실은`, `~잖아요`, `~죠`, `~네요`, `~거든요`, `말이지`, `있죠`, `그런 거지`
- 대체: `즉`, `다시 말해`, `요컨대`
- ✅/❌ 예시 페어 + Why 설명 + pre-submit scan 체크리스트

Commit: `d062cb44 feat(news-prompt): forbid chatty conversational KO markers in news prose`

### 5-2. EN-side acronym expansion (both locales independent)

**Trigger**: 5/8 research-digest 학습자 EN 본문에 `RAG`가 expansion 없이 등장 → 학습자 accessibility 4/10점. KO는 `검색 증강 생성(RAG)`로 잘 처리됨. 기존 룰은 "Korean style" 예시만 있어서 모델이 KO-only로 해석.

**Rule 변경**: 양 locale 독립 expansion 요구 + 양쪽 ✅/❌ 예시 + 8개 representative 약자 리스트 (RAG, LLM, MoE, RLHF, DPO, CoT, SFT, MCP) + "examples, not exhaustive" framing.

→ **Long closed list (27개 초안)** vs **short representative (8개)** trade-off에서 후자 선택. 짧은 리스트가 generalize 더 잘 됨 (모델이 "이 카테고리" 인식, 닫힌 집합으로 해석 X).

Commits: `520a20b6 fix(news-prompt): EN-side acronym expansion + scope-claim calibration` + `8533a5ab fix(news-prompt): slim acronym list 27 → 8 + drop AGI duplicate`

### 5-3. Calibrated scope/scale claims (frontload)

**Trigger**: 5/8 research-digest frontload에 `13 baselines falter` / `13개 기준 모델이 흔들린다`. Quality reviewer claim_strength **7/10** — 강한 scope/strength 단어 사용했지만 본문에 specific 숫자 backing 약함.

**기존 룰**: body-level overclaim ban (`dominates`, `장악`, `석권` 등 positive 방향) — frontload에는 sibling rule 없음.

**v13 추가**: LEARNER_TITLE_STRATEGY에 "Calibrated scope/scale claims" 섹션. Negative-direction overclaim도 ban (`falter`, `흔들린다`, `광범위 부진`). 대안 2종:
1. Specific count: `"13 of 25 baselines score below 50%"` / `"25개 기준 모델 중 13개가 50% 미만"`
2. Acceptable softening: `"show gaps on N tasks"` / `"N개 과제에서 격차를 보임"`

+ pre-submit scan에 통합 (acronym + scope + speculation 3종 일괄 체크).

### 5-4. Learner digest 본문 refinement

- `0c1cbadc fix: strengthen learner digest paragraph depth` — paragraph 깊이 확보
- `a02abc00 fix(news): prune weak stories and tune learner density` — 약한 story 가지치기, density 튜닝

→ "분량 길지만 묽음" 패턴 대응. 본격적 learner redesign은 보류 (NQ-44 beginner 트랙이 우선).

---

## 6. 소스 품질 게이트 강화

### 6-1. Classify 단계 tier × freshness matrix gate

`vault/09-Implementation/plans/2026-05-04-classify-tier-freshness-gate.md` 기반. Classify prompt에 TIER × freshness 매트릭스 게이트가 primary filter로 들어감.

Commits: `ea737330 feat(classify): tier x freshness matrix gate as primary classification filter`, `cef376b6 fix(classify): address review issues`, `3d05dceb test(classify): regression test`, `bea9222c test(classify): tighten 4 weak assertions`

### 6-2. Enrich 단계 Exa find_similar tier gate

5/6 research-digest source_cards에 9개 TIER-3 leak (labs.scale.com, llm-stats.com, dev.to, oreilly.com, pointofai.com 등). Classify-stage gate가 enrich에는 적용 안 됨. `_enrich_source_passes_quality`에 TIER 1/2/3 로직 + known-trusted-media override 추가 (axios.com 등 NQ-43 케이스 보존).

Commit: `e97f48d5 feat(news-enrich): tier gate on Exa find_similar results`

### 6-3. 일반 hardening

- `3c498abf fix: harden news source and weekly quality guards`
- `0798cfb1 fix(news-writer): strip LaTeX math wrappers around currency / numeric values` — `$$1.5$$` 같은 KaTeX wrap 사고 차단 + DB 일회성 cleanup (133 instances across 12 posts)

---

## 7. 비용 정확도 실측 (v13 deployment 후)

### Ratio 변천

| 날짜 (KST cron) | 우리 기록 (cron only) | OpenAI 청구 (cron only) | Ratio |
|---|---|---|---|
| 5/7 | $0.214 | $1.53 | **3.51x** ❌ retry storm + flex 4곳 누락 |
| 5/8 | (cron 실패) | — | — |
| 5/9 | (cron 실패) | — | — |
| 5/10 | $0.338 | ~$0.34 (rerun 제외) | **1.00x** ✅ |
| 5/11 | $0.280 | ~$0.31 (rerun 제외) | **1.0-1.1x** ✅ |

### 차이를 닫은 항목 4가지

1. **flex 4 곳 추가** (`0ec99cb2`) — `persona_writer`, `fact_extractor`, focus_items_ko fallback, quotes_ko fallback이 v12까지 standard rate. v13에서 flex 적용 + `extract_usage_metrics(..., requested_service_tier="flex")` 동기화.
2. **Retry storm cost capture** (`6d178532`) — Layer B/C/D fixes
3. **Tier fallback** (`db1ac147`) — retry attempt가 standard tier 쓰는 경우의 tier-aware extract
4. **Rerun 활동 인식** — admin manual rerun ($0.20-0.23/회)이 OpenAI 청구의 일부. cron-only로 reconcile 시 단순 cron 합산이 아닌 reruns 별도 식별 필요

### Stress test 대기

5/10, 5/11은 flex 큐가 calm한 날 → tier fallback fire 안 함. 5/7-5/9 같은 큐 saturation 날 재현되면 그때 진짜 검증. attempts_log timeline으로 detection 가능.

---

## 8. 통합 교훈

1. **Audience를 정직하게 보지 않으면 redesign 결정 회피로 이어진다.** Learner mode honest review에서 "이건 expert minus jargon이지 쉬운 뉴스가 아님"이라는 진단이 나왔는데, v11/v12까지 학습자 prompt만 미세 조정하며 우회. v13에서 두 갈래 — 학습자 redesign 보류, beginner 별도 트랙. 정직한 진단이 별도 트랙 결정의 트리거.

2. **Best-effort SLA는 best-effort cost tracking을 의미한다.** Flex tier는 가격이 50% 싼 대신 latency variance가 큼. cost tracking도 success path만 cover하면 stress 날에 silent gap. **인프라 선택이 observability 요구사항을 정의함** — flex를 쓰면 retry 비용 추적도 의무.

3. **Cache key는 retry path까지 동일하게 유지해야 한다.** Tier fallback (flex→standard) 시 cache key가 stable이면 OpenAI prefix cache가 carry-over할 가능성. 매 attempt마다 cache key를 다르게 했으면 retry 비용이 더 컸을 것. **affinity는 retry safety의 일부**.

4. **Per-attempt observability는 stage-level의 보강이지 대체가 아니다.** Langfuse 같은 외부 도구를 도입하기 전에 — stage-row 안의 debug_meta에 `attempts_log` 추가만으로 retry storm 진단이 SQL 30분 → 클릭 1번으로. 95% 가시성 충족. 외부 도구는 "사용자-facing AI" 단계에서 재검토.

5. **Prompt 룰의 list는 짧고 "examples, not exhaustive"가 generalize 더 잘 된다.** 27개 acronym 닫힌 리스트 → 8개 representative + open framing. 닫힌 리스트는 모델이 "이것만 처리" 해석. 짧은 리스트 + 카테고리 framing이 "이런 종류는 모두 처리" 해석으로 일반화.

6. **Confidence가 아닌 sclass를 ban해야 한다.** v12 body-level overclaim ban은 positive 방향 (dominates / 장악). v13에서 부족 발견 — negative 방향 (falter / 흔들린다)도 동일한 calibration 문제. **방향 비대칭 룰은 사각지대를 만든다** — symmetric calibration이 더 robust.

7. **Stress fix는 평상시 검증 못 한다.** 5/10-5/11이 평온해서 tier fallback이 fire 안 함 = fix가 실제로 작동하는지 미검증. 다음 stress 날까지 confidence는 "그래야 한다" 수준. observability (attempts_log)가 그날의 측정 도구. **Latent verification은 production observability에 책임을 위임하는 것**.

8. **새 페르소나는 옵션 layer로 안전하게 introduce 가능.** beginner를 DAILY_DIGEST_PERSONAS에는 추가하되 REQUIRED_DAILY_DIGEST_PERSONAS에는 추가하지 않음 → 생성 실패해도 expert/learner만 있으면 publish. **롤백이 자연스럽게 가능한 architecture**. v14에서 beginner가 안정되면 REQUIRED 승격.

---

## 9. Follow-up

- [ ] **NQ-44 beginner 콘텐츠 internal review** — 2026-05-20까지 점수/가독성/audience fit 평가
- [ ] **Tier fallback stress 검증** — 다음 flex 큐 saturation 날 (예측 불가) attempts_log로 fire 확인
- [ ] **Persona writer + fact extractor에도 retry-storm 패턴 적용** — 디지스트만큼 high-blast-radius는 아니지만 (per-news, smaller token budget) 동일 패턴이 더 안전
- [ ] **Cached_tokens 회복 추이** — 5/8-5/9 prompt 수정으로 invalidate된 cache가 며칠 안에 재적재되는지 (5/10, 5/11 cached=0 관찰됨)
- [ ] **Rerun 활동을 summary row에 직접 합산** — 현재 rerun summary는 total_cost=$0.000 (stage row에는 정상 기록되지만 집계 안 됨). admin UI에서 daily total 표시 시 reconciliation 어려움
- [ ] **NQ-30 auto-publish threshold 재조정** — v11 rubric v2 적용 후 기존 85 기준 너무 엄격. 1주 관찰 후 80 검토 (sprint task)
- [ ] **Learner redesign 진짜 결정** — beginner 트랙이 안정화되면 학습자 모드는 (a) 그대로 둘지 (b) practitioner로 격상할지 (c) 진짜 audience-honest redesign할지 결정

---

## 참고

### 관련 플랜

- `vault/09-Implementation/plans/2026-05-04-classify-tier-freshness-gate.md` — Classify gate
- `docs/plans/2026-05-15-quiz-only-news-pipeline.md` — Quiz-only mode (629 lines)
- `vault/09-Implementation/plans/2026-04-26-cp-voice-and-quiz-contract.md` — Quiz contract precursor

### 관련 커밋 (main, chronological)

**Source quality + LaTeX:**
- `0798cfb1` — strip LaTeX math wrappers around currency
- `ea737330`, `cef376b6`, `3d05dceb`, `bea9222c` — classify tier × freshness gate
- `e97f48d5` — enrich Exa tier gate
- `3c498abf` — news source + weekly quality guards

**Cost tracking + tier:**
- `0ec99cb2` — flex tier to 4 missed call sites
- `6d178532` — retry-storm cost capture + timeout 1200s
- `db1ac147` — flex→standard tier fallback on retry
- `8c46bba6` — attempts_log per-attempt observability

**Prompt tone + accessibility:**
- `d062cb44` — KO chatty marker rule 6
- `520a20b6` — EN acronym expansion + scope calibration
- `8533a5ab` — slim acronym list 27 → 8

**Quiz + Beginner persona:**
- `ea70c571`, `7fcd1eed`, `457f8bfd`, `6b40ec7c`, `5c6fd8a0`, `75f569b7` — answer_index contract
- `82332d55` — beginner news persona
- `f7e87bf2` — english beginner backfill
- `92ffbb06` — stabilize beginner persona display
- `62fe61cd` — beginner news quiz backfill
- `0c1cbadc` — learner digest paragraph depth
- `a02abc00` — prune weak stories + tune learner density
- `6b43c560` — quiz-only news pipeline plan
- `2404bc15` — quiz-only daily news generation
- `d8b7c4cb` — beginner rerun admin controls

**Admin / observability surface:**
- `895463e9` — split queries per tab
- `27605bc6` — paginate pipeline run logs
- `39cae06f` — Quality Score Trend logic alignment

### Admin 확인

`/admin/pipeline-runs/{runId}` — Stage Timeline 카드:
- 기존 chip: **Tokens · In · Out · Reasoning · Cached · Tier · Cost · Quality · Retries**
- 새 (debug_meta JSON panel 내): **attempts_log array per attempt**

### 진단 스크립트

- `backend/scripts/prototype_beginner_news.py` — Beginner persona 콘텐츠 실험
- `backend/scripts/measure_cached_tokens.py` — Stage별 cache hit + reasoning 분포
- `backend/scripts/rescore_recent_batches.py` — Quality 재채점

### 이전 버전

- v12 (2026-04-23): URL compliance schema enum + flex/cache + 비용 정확화
- v11 (2026-04-21): writer-QC mirror + infra
- v10 (2026-04-01): gpt-5 전환
- v9, v8, v7, v3, v1 postmortem — 각 journal 참조
