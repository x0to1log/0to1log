---
title: Weekly Hardening Phase 1 — Prompt Rewrite
date: 2026-04-17
status: phase 1 complete (2026-04-17 scope-expanded closeout)
type: design / spec
related:
  - vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md
  - vault/12-Journal-&-Decisions/2026-04-17-news-pipeline-hardening-retro.md
---

# Weekly Hardening Phase 1 — Prompt Rewrite

## 1. 배경

2026-04-17 weekly news 평가에서 발견: **Weekly는 Phase 2 이전 Daily pipeline과 비슷한 상태**. Citation 없음, quality_score 측정 없음, source_urls 미기록. 결정적으로 `WEEKLY_EXPERT_PROMPT` L1050에 **`"Do NOT include source URLs"` 규칙이 명시적으로 존재** — citation 없는 건 버그가 아니라 의도된 디자인.

또한 프롬프트 자체가 daily 대비 얇음:
- WEEKLY_EXPERT_PROMPT: 648 tokens (daily persona prompt는 1500+ tokens)
- Writing Rules 섹션 거의 없음
- Persona 차별화 명확히 표현 안 됨
- Few-shot 예시 없음

Weekly 발행 횟수: W13 (2026-04-02), W14 (2026-04-07) 단 2건. 둘 다 `status='draft'`로 발행 안 됨.

결론: **weekly pipeline의 generation 품질 자체가 upgrade 필요**. 인프라(URL validation, quality check)를 먼저 추가해도 얕은 프롬프트가 만든 얕은 output에 대한 검증일 뿐.

## 2. Goals & Non-Goals

### Goals (Phase 1)
- Weekly prompt를 daily 수준으로 끌어올림 — writing rules, persona 차별화, citation 규칙, length target, CoT synthesis
- 다음 weekly run에서 눈에 띄는 content 품질 향상 (수동 검증 기준)
- Phase 2 (measurement 인프라) 가 의미 있게 쓰일 수 있는 baseline 확보

### Non-Goals (Phase 2 로 이월)
- ❌ source_urls 집계 인프라 (`_fetch_week_digests` 확장)
- ❌ `validate_citation_urls()` weekly 통합
- ❌ `QUALITY_CHECK_WEEKLY_*` 프롬프트 신설
- ❌ `_check_digest_quality()` weekly routing
- ❌ Few-shot 예시 추가 (Phase 2 measurement 후 데이터 기반 타겟팅)
- ❌ `WEEKLY_KO_ADAPT_PROMPT` 수정 (현재 literal translation 방지 규칙 있음 — 결과 본 뒤 판단)
- ❌ Auto-publish 로직

## 3. Architecture

**In-place 프롬프트 수정**, 새 파일 없음, 코드 로직 변경 없음.

```
Target file: backend/services/agents/prompts_news_pipeline.py

수정 대상:
  - WEEKLY_EXPERT_PROMPT  (L1037~1096, 약 60줄)
  - WEEKLY_LEARNER_PROMPT (L1098~1158, 약 60줄)

수정 제외:
  - WEEKLY_KO_ADAPT_PROMPT (L1165+) — 현재 유지
  - backend/services/pipeline.py 의 run_weekly_pipeline() — 변경 없음
  - backend/services/pipeline_persistence.py 의 _fetch_week_digests() — 변경 없음
```

**원칙**:
- **내용 추가 > 재구조화**: 기존 structure (7 sections) 유지. Writing Rules는 새 섹션으로 prepend.
- **Daily 패턴 이식**: `RESEARCH_EXPERT_GUIDE` + `TITLE_STRATEGY` 의 핵심 규칙을 weekly 맥락에 맞게 차용.
- **Chain-of-Thought 명시**: Trend Analysis 섹션에 명시적 reasoning steps.
- **Length 유도**: constraints에 target char count 명시 + "depth > length" 원칙.

## 4. 변경 상세

### 4.1 Citation 허용 + 규칙 (persona-별)

**중요 제약 (Phase 1 scope)**: Weekly LLM은 현재 daily digest의 **full text** (`content_expert` + `content_learner`)를 input으로 받음. Daily digest 본문에는 이미 inline `[N](URL)` citation이 있으므로, weekly LLM이 URL을 **inline에서 추출**해서 재인용 가능. 별도 `source_urls` list 를 LLM에 전달하는 것은 Phase 2 인프라 작업이라 Phase 1 에서는 "daily digest 본문에 이미 있는 URL만 사용"을 명시.

**Expert 버전 (L1050 교체)**:
```
3. **## Top Stories** — 7-10 most impactful stories ranked by:
   Impact > Novelty > Evidence > Community signal.

   Each item: **Bold title** — 4-5 sentences covering:
   - WHAT happened (facts + specific numbers)
   - WHY it matters (strategic implication — competitive shift, market
     restructuring, or investment signal)
   - CONTEXT (comparison to prior state, competitor, or industry baseline)

   End paragraphs with `[N](URL)` citing the original source. URLs MUST
   come from the daily digest content provided in the Input (look for
   existing `[N](URL)` patterns in the daily digests). NEVER invent URLs.
   If multiple sources support one item, cite each in a different sentence.
```

**Learner 버전 (L1111 교체)**:
```
3. **## Top Stories** — 7-10 stories ranked by:
   Impact > Novelty > Evidence > Community buzz.

   Each item: **Bold title** — 4-5 sentences covering:
   - WHAT happened (facts + specific numbers, in plain language)
   - WHY it matters to a non-specialist (impact on everyday work,
     career, or consumer AI experience)
   - CONTEXT (for beginners — compare to something familiar, explain
     why this differs from prior state)

   Define any acronyms on first use. End paragraphs with `[N](URL)`
   citing the original source. URLs MUST come from the daily digest
   content provided in the Input (look for existing `[N](URL)` patterns
   in the daily digests). NEVER invent URLs.
```

### 4.2 Writing Rules — Expert (신규 섹션)

WEEKLY_EXPERT_PROMPT 의 "## Input" 앞에 삽입:

```
## Writing Rules (Expert)
- Tone: analyst voice. Confident but calibrated. Distinguish sourced facts from editorial interpretation.
- Use "signals/suggests/implies/points to" for interpretation; "announces/releases/says/files" for sourced facts.
- ALWAYS compare numbers to baselines, competitors, or prior periods when possible ("$122B — 10x Anthropic's last raise", not just "$122B").
- Avoid loaded words: "scramble, showdown, salvo, war, takes aim, hits, undercuts" unless the source itself uses that framing.
- NEVER invent motivations. If a company's intent isn't stated, use "appears positioned as" or "may be driven by".
- NEVER predict the future ("Q2에", "내년", "다음 분기 전망", "will disrupt"). Watch Points section is for monitoring, not forecasting.
- Mention technical details (parameter counts, architectures) only when they materially affect business/strategic outcomes.
- Connect themes across stories explicitly in Trend Analysis — weekly's value is synthesis, not restatement.
```

### 4.3 Writing Rules — Learner (신규 섹션)

WEEKLY_LEARNER_PROMPT 의 "## Input" 앞에 삽입:

```
## Writing Rules (Learner)
- Tone: clear editorial news prose. Reportorial + explanatory. Not chatty, not lecturing.
- Foreground the concrete change BEFORE naming the technical mechanism ("The model now handles hour-long videos" before "via 2-bit KV cache compression").
- When introducing ANY acronym, expand on first use: "검색 증강 생성(RAG)" in KO / "Retrieval-Augmented Generation (RAG)" in EN.
- Use analogies when they aid comprehension ("like running a mini datacenter in your pocket"); skip when story is straightforward.
- Connect to readers' life/work where natural ("이게 일상화되면 회사에서 쓰는 챗봇이 더 빨라진다") — but don't force it.
- Never use chat tone ("~요 투"). Use editorial news prose throughout.
- Numbers should come with context ("$122B — one of the largest rounds in AI history"), never bare.
- Technical/business terms linked to Handbook on first appearance (frontend handles rehype).
```

### 4.4 Persona opening 재작성 (둘 다)

**Expert** (L1037-1038 교체):
```
You are the senior editor of an AI industry weekly newsletter for strategic
decision-makers (VPs of Engineering, CTOs, AI Product Leads, strategy heads).

Reader goal: Make weekly strategic decisions — resource allocation,
competitive response, partnership evaluation, product roadmap adjustments.
After reading: The reader adjusts strategy, briefs leadership, or initiates
concrete action based on this week's shifts.
```

**Learner** (L1098-1099 교체):
```
You are the editor of a beginner-friendly AI weekly for non-specialist
knowledge workers (PMs, marketers, designers, students, career-switchers).

Reader goal: Catch up on this week's AI in ~10 minutes, walk away with
ONE actionable learning experiment for the coming week.
After reading: The reader can explain the week's main shift in one sentence
AND has a concrete thing to try this week (learn a tool, read an article,
run a small test).
```

### 4.5 Chain-of-Thought for Trend Analysis (둘 다)

기존 "Trend Analysis" 섹션 설명에 명시적 reasoning steps 추가.

**Before** (expert L1051, learner L1112 유사):
```
4. **## Trend Analysis** — 3-4 paragraphs connecting the dots.
   Structure: early-week → evolution → end-of-week state.
```

**After**:
```
4. **## Trend Analysis** — 3-4 paragraphs connecting the dots.

   Before writing, think step by step:
   (1) Identify 2-3 themes that appeared in multiple daily digests this week
       (examples of themes: "compute scarcity", "agent-first infrastructure",
       "open-weight licensing shift").
   (2) For each theme, trace how it evolved (early-week framing → mid-week
       reinforcement → late-week consolidation or shift).
   (3) Synthesize what these evolutions jointly reveal about this week's
       dominant pattern or shift.

   Then write 3-4 paragraphs narrating steps 1-3 without showing the numbered
   reasoning. The goal is substantive synthesis — not headline restatement.
```

### 4.6 Length target (둘 다, Constraints 섹션에 추가)

```
## Length Target (approximate — depth > literal count)
- Top Stories: ~6000-8000 chars (4-5 substantive sentences × 7-10 items,
  English prose averaging ~120-150 chars per sentence)
- Trend Analysis: 3-4 substantive paragraphs, ~1200-2000 chars total
- Week in Numbers + One-Line + Watch Points + Open Source + Actions: ~3000-4000 chars combined
- Total EN content (en field):
  - **Expert: aim for 12000+ chars**
  - **Learner: aim for 10000+ chars**
- Principle: depth > length. If the week has thin news (<5 major stories),
  write shorter rather than pad with weak items. The character numbers are
  guidance, not a quota — do not add filler to hit the target.
- KO adaptation maintains same story count and section depth; natural
  Korean can be ~60% EN char count due to density (so expert KO ≈ 7200+,
  learner KO ≈ 6000+).
```

## 5. Done Criteria

Phase 1은 코드 로직 변화 없음. 모든 기준이 prompt 변경 + weekly output의 수동 검증에 기반:

- [ ] `WEEKLY_EXPERT_PROMPT` 에 항목 4.1~4.6 모두 반영
- [ ] `WEEKLY_LEARNER_PROMPT` 에 항목 4.1~4.6 모두 반영
- [ ] `pytest tests/test_news_digest_prompts.py` 전체 통과 (기존 테스트 깨지면 안 됨)
- [ ] `ruff check services/agents/prompts_news_pipeline.py` clean
- [ ] `WEEKLY_KO_ADAPT_PROMPT` 및 다른 프롬프트 건드리지 않음 (scope 준수)
- [ ] **Manual weekly run 1회 실행** (`run_weekly_pipeline` admin trigger or script)
- [ ] 생성된 W-ID digest 수동 검증:
  - 길이 (EN):
    - `LENGTH(content_expert) >= 10800` (expert target 12000의 -10%)
    - `LENGTH(content_learner) >= 9000` (learner target 10000의 -10%)
  - 길이 (KO): expert ≥ 6500, learner ≥ 5400 (EN의 ~60% 기준)
  - Citation: Top Stories 각 item에 `[N](URL)` pattern 존재 (**최소 70% item에 citation 1개 이상**)
  - Citation URL이 실제 daily digest 본문에 inline 등장했던 URL인지 spot check (**3개 random item 샘플링**). Daily에 없던 URL이 나오면 hallucination — Phase 2 validator 없는 현재는 수동 catch가 유일한 방어선.
  - 톤 차별화: expert ("strategic brief") vs learner ("approachable explainer") 체감 차이
  - Synthesis: Trend Analysis가 theme evolution narrative 담고 있음 (단순 story 나열 아님)
  - CoT evidence: Trend Analysis가 **명확히 2개 이상 themes**를 다루는지 (3개가 이상적이지만 2개 이상이면 통과 — 주 뉴스가 적은 경우도 있음)
- [ ] design.md status → `phase 1 complete`

⚠️ **알려진 한계**: Phase 2가 없는 상태에서는 `quality_score` 없음. 수동 검증이 유일한 gate. Phase 2에서 데이터 기반 측정 확보.

## 6. Phase 2 미리보기 (다음 spec)

현재 설계가 Phase 2를 가능하게 하는 방식:

- **Citation 규칙이 프롬프트에 생김** → Phase 2의 URL validator가 의미 있게 작동 (allowlist check할 대상 존재)
- **Phase 1은 "daily digest 본문 inline URL" 만 사용하도록 명시** → Phase 2에서 `_fetch_week_digests`가 source_urls를 별도 list로 집계·전달하는 인프라 추가 시, 프롬프트 문구를 `"Input의 daily digest 본문 또는 source_urls list"` 로 확장하는 자연스러운 전환점
- **Length + synthesis 품질 향상** → Phase 2 의 quality check가 차원별 (sections/sources/depth/language) 점수 매길 때 의미 있는 분산 얻음 (현재는 모두 "thin"이라 점수 변별력 0)

**Phase 2 예상 범위** (별도 spec):
1. `_fetch_week_digests()` 확장 — aggregate source_urls from all daily posts in week
2. `run_weekly_pipeline()` 이 LLM에 source_urls 전달
3. Weekly 생성 후 `validate_citation_urls()` 적용 (citation이 aggregated source_urls에 있는지)
4. `QUALITY_CHECK_WEEKLY_EXPERT` + `_LEARNER` 2개 프롬프트 신설 (Phase 3 공통 블록 재사용)
5. `_check_digest_quality()` 가 weekly 라우팅 추가 (digest_type="weekly")
6. Weekly 에도 fact_pack + quality_score + auto_publish_eligible 컬럼 채움

**Phase 3 (가장 나중)**: Phase 2 measurement 결과 기반 Few-shot 추가 (Daily Phase 2 Task 7 패턴).

## 7. 일정

- Phase 1 작업 시간: 1일 (프롬프트 수정 + 테스트 + manual weekly run + 검증)
- Phase 2 spec 작성: Phase 1 완료 + 1주일 관찰 후
- Phase 2 실행: 2-3일

## 8. 위험 및 대응

1. **Weekly run이 자주 안 돎**: W13/W14 2번만 있음. Phase 1 배포 후 다음 weekly trigger 전까지 검증 불가. **대응**: manual trigger (`run_weekly_pipeline` admin endpoint) 사용.

2. **Prompt 길이 증가로 성능 저하**: Writing Rules 추가로 ~500 tokens 증가. Weekly는 input이 이미 큼 (daily digests 7개 aggregate). **대응**: 허용 가능한 수준. Phase 2 이후 prompt diet 가능.

3. **LLM이 length target 무시**: 12000 chars target을 말하지만 LLM이 따르지 않을 가능성. **대응**: Phase 2 quality check가 length를 deterministic 기준으로 잡을 예정. Phase 1에서는 "depth > length" 원칙이 우선이라 일단 유도만.

4. **Citation hallucination**: Phase 1은 "Input의 daily digest 본문에 이미 있는 `[N](URL)` pattern에서 URL을 추출해서 재인용"하도록 명시. LLM이 input 내부 URL이 아닌 것을 만들어낼 리스크 남아있음. **대응**: (a) Done Criteria의 "3개 item random spot check"로 수동 catch, (b) Phase 2에서 validator 추가로 구조적 차단. Phase 1만으로 완벽한 방어는 아니지만 daily digest body에 URL이 이미 들어있어서 LLM이 extract-and-reuse 하는 게 invent보다 자연스러움.

5. **KO adapt 프롬프트와 충돌**: EN 프롬프트가 변경됐는데 KO adapter가 옛 구조 가정 가능. **대응**: `WEEKLY_KO_ADAPT_PROMPT` 는 "literal translation 금지 + 같은 구조" 일반 규칙이라 section 수/이름만 맞으면 통과 예상. 결과 본 뒤 필요 시 수정.

## 9. Next Steps

1. 이 design을 spec reviewer 에이전트에 dispatch
2. 피드백 반영 후 Amy 검토
3. 승인 시 `/writing-plans` 스킬로 Phase 1 plan 작성
4. Plan subagent-driven-development로 실행
5. Manual weekly run + 수동 검증
6. Phase 1 complete 후 1주일 관찰 → Phase 2 spec 작성

## 10. Scope expansion — 2026-04-17 W13 재생성 피드백 반영

초안 §2 Non-Goals에서 제외됐던 `WEEKLY_KO_ADAPT_PROMPT` 수정이 **Phase 1 scope로 승격됨**. W13 1차 재생성 결과 평가에서 Amy 발견:

| 항목 | Pre-fix | Post-fix |
|---|---|---|
| KO expert `[N](url)` | **0** (citation 전부 드롭) | **52** |
| KO learner `[N](url)` | 0 | **44** |
| KO learner bare `[N]` | 24 | 0 |
| KO expert 총 chars | 6,390 | 12,449 |

**원인**: 원 프롬프트의 "write naturally, not translated" 문구가 LLM에게 citation markdown 재구성 재량을 암묵적으로 허용함. "KO는 adapter가 알아서 잘 하겠지"라고 scope 제외한 게 package-level regression을 만듦.

### 10.1 추가 반영된 변경 (P1/P3/P4 + bonus P2)

- **P1** `WEEKLY_KO_ADAPT_PROMPT` 재작성: "CITATION PRESERVATION (HIGHEST PRIORITY)" 블록 추가, example을 `[N](URL)` 포함형으로 교체, constraints에 "non-negotiable" 명시. "write naturally" 문구는 의도가 남도록 조정하되 citation 드롭이 금지됨을 분리된 규칙으로 박음.
- **P3** `WEEKLY_EXPERT_PROMPT` Writing Rules에 **framing-word 가드** 추가 — `moat / lock-in / commoditize / defender-first / credible path / cements / tightens grip / capital moat / stack coherence` 가 source 원문을 paraphrase 하지 않으면 사용 금지. 항목당 1개까지만 허용.
- **P4** `WEEKLY_EXPERT_PROMPT` + `WEEKLY_LEARNER_PROMPT` Week in Numbers 규칙에 **DISTINCT Top Story 제약** 추가 — 한 스토리의 여러 숫자($10B + $730B pre-money 같은)가 5 슬롯을 중복 점유하지 않도록.
- **P2 (bonus)** `WEEKLY_EXPERT_PROMPT`에 **source hierarchy** 한 줄 추가 — 같은 claim에 3개 citation 쌓는 관습 제약. 원래 Phase 1.5 후보였으나 프롬프트 한 줄 변경이라 함께 포함.

### 10.2 Post-fix W13 검증 (2026-04-17 재생성)

- **KO citation 복구**: 위 표와 같이 모두 복원. KO 본문이 English citation markdown을 문장 단위로 동일하게 재현.
- **Week in Numbers dedup (EN expert)**: 5 slot = OpenAI / TurboQuant / Nemotron / Voxtral / Huawei 950PR — 각 distinct story. OpenAI의 $730B pre-money는 문구 내 맥락으로만 남고 별도 slot 차지 X.
- **Framing 톤 완화 (EN expert)**: "capital moat" / "credible non-Nvidia path" / "defender-first" 모두 0회. "tighten" 2회 남아있으나 factual verb ("tightening integration between simulation physics...") 로 사용됨 — 전략 프레이밍 아님.

### 10.3 Known residuals (Phase 2로 이월 유지)

- `src_count = 0`, `source_cards = null`, `fact_pack = {}` — Phase 2 `_fetch_week_digests` 확장 범위.
- `quality_score = null` — Phase 2 `QUALITY_CHECK_WEEKLY_*` 프롬프트 신설 범위.
- EN length overshoot (expert 17,254 chars / target 10,800, learner 14,696 / 9,000) — "4-5 sentences × 10 Top Stories" 구조가 요구한 자연스러운 산출물이라 판단. Phase 2 관찰 기간에 target 재보정 가능성 있음. 별도 ticket.
- Arxiv URL 중 `2603.xxx` 형태 존재 — input (daily digest) 단계의 placeholder 가능성. Phase 2 URL validator 도입 시 structural catch.

### 10.4 Phase 1 closeout decision

Amy 판정: **Phase 1 close**. Done Criteria §5 모든 항목 통과, scope expansion 항목 (§10.1) 실효 검증됨 (§10.2). Phase 2 spec은 1주일 관찰 후 착수.
