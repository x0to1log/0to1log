---
title: Handbook Selection Hardening — Long Session
date: 2026-04-20
tags:
  - journal
  - handbook
  - selection-gate
  - quality-judge
  - definition-spec
---

# Handbook Selection Hardening — Long Session (2026-04-19 → 2026-04-20)

> **세션 기간:** 하루를 넘긴 마라톤 세션
> **커밋 수:** 20+
> **플랜 완료:** `2026-04-17-handbook-term-selection-hardening-plan.md` 4 chunks (0/A/C/B) 전부 shipped
> **Definition spec iteration:** 5회 (1→2 hard→2-3→1→1-2)
> **다음 단계:** Admin UI queue review flow (이번 세션 밖, 외부 blocker)

---

## 세션 의도와 실제 진로

**의도:** 2026-04-17 에 쓴 plan 의 4 chunk 를 순서대로 구현하기.

**실제:** Chunk 0 직후 Amy 가 "우리 handbook 퀄리티는 어때?" 로 pivot → Agentic UX / MCP / RLHF 등 실제 생성 → definition 길이 문제에 빠짐 → 5 iteration 후 "현상 수용" → selection gate 로 복귀 → A/C/B 완료 → 다시 "definition 어떡하지" → 6번째 iteration (1-2 sent 스펙) → 부분 성공 (KO) / 부분 수용 (EN).

**교훈:** 원래 plan 의 4 chunk 는 "쉬운 길", definition/quality 쪽은 "진짜 어려운 길". 세션의 대부분 시간이 **원래 plan 에 없던 정의 품질 작업** 에 들어감. 이건 실패가 아니라 발견 — 플랜 작성 당시엔 보이지 않던 문제가 실제 콘텐츠 확인하자마자 폭로됨.

---

## 주요 변화

### 1. Queue 시스템 살아남 (Chunk 0)

**문제:** `ExtractedTerm` Pydantic 모델에 `confidence` 필드가 빠져있어 LLM 이 생성한 `confidence: "low"` 가 silent drop. `term_info.get("confidence", "high")` 가 항상 `"high"` → 큐 가드가 never fire. 2026-03-23 commit `b0b4fda` 부터 누적된 버그.

**수정:** `ExtractedTerm` 에 `confidence: Literal["high", "low"] = "high"` 필드 + `extra="allow"` 추가. 커밋 `606bfa7`.

**검증:** 첫 live run 에서 4/13 term 이 `status='queued'` 로 라우트됨. 큐가 처음으로 accumulate 했음.

### 2. Batch 정리 (2026-04-17)

**Archive 5:** Gabriel's Horn (수학), Hermes Web UI (product), AI Mode (feature), Prism (중의성), Firefly AI Assistant (제품명 variant)
**Publish 7:** OpenAI Codex, Three-Phase Transformer, Value Gradient Flow, Self-Supervised Pretext Tasks, Visual Instruction Tuning, RoPE, GPT-Rosalind

**발견:** Amy 의 편집 판단이 있어야 scope 결정 가능. 이것이 이후 Chunk A (scope gate) 의 모티브.

### 3. Learner popup dead code 제거

기존 코드:
```javascript
if (isLearner && data.summary) ...
else if (isLearner && data.basic_plain) ...
else if (data.definition) ...
```

데이터 확인: 0% 의 learner popup 이 tier 3 (definition fallback) 에 도달. 완전히 dead code.

커밋 `c7b3a52` — 구조적으로 명확하게 (learner branch / expert branch 분리).

### 4. Selection hardening plan 4 chunks — 완료

원래 plan 의 4 chunk 를 전부 shipped. 상세는 plan doc retro 에 있음. 짧게:

- **Chunk A (scope gate):** HR/규제/compliance 블록리스트 + regex + product allowlist. Reject + `pipeline_logs` 기록.
- **Chunk C (Korean validator):** 음차 금지, Hangul 최소치, global-name exception. Queue 라우팅.
- **Chunk B (entity grounding):** verbatim 매칭 + compound fabrication 탐지. Queue 라우팅.

**3-bucket 처분 설계가 코드로 정확히 내려옴:** A=reject+log, B/C=queue. 같은 "validator fail" 이어도 처분이 다름.

**테스트 72개** 통과 (17 scope + 9 Korean + 9 grounding + 17 advisor + 20 quality checks).

### 5. Quality judge 재설계 (plan 에 없던 작업)

**문제:** 같은 Agentic UX content 를 3번 judge 돌리면 advanced 점수 5, 7, 74 — 10배 편차. 원인: broad 4 dimension × 0-25, no anchor, no evidence 요구, LLM 이 직접 total 계산.

**수정 (커밋 `8249e9d` + `14cc11d`):**
- 10 sub-score × 0-10, evidence 필드 필수 (Chain-of-Thought anchor)
- Code-side aggregation (LLM 산수 안 믿음)
- 4-anchor scale (10/7/4/0) + 명시 기준
- `source_grounding` sub-score 제거 (handbook 은 references 필드 별도 존재, news 와 다름)
- Judge context 6000 → 12000 chars (format marker truncation 버그 수정)

**재측정:** 동일 content 3회 run, advanced 범위 60-75 (이전 5-74). **분산 4.6× 감소**.

### 6. Definition 스펙 5 iteration

Plan 에 없던 큰 작업. Amy 의 "뉴스 팝업 5-8초 읽기" 목표 때문에 촉발.

| Iter | 스펙 | 결과 |
|---|---|---|
| 1 | 2-4 → 2-3 sent, 250-350 EN | EN 500-600자 |
| 2 | 2 sent hard | Amy push-back (언어 rhythm 무시) |
| 3 | 2-3 sent asymmetric (KO 2, EN 3) | EN 여전히 600자 |
| 4 | Scope discipline + 6 GOOD 예시 + conceptual vs algorithmic | EN 637-714자 |
| 5 | **1-2 sent, encyclopedia-lede** | **KO target 달성** (141자), EN 여전히 600-700 |

**교훈:** LLM 의 Wikipedia-lede prior 는 수학/알고리즘 중심 term 에서 특히 완고함. 5 iteration 으로도 EN 길이 못 잡음. Prompt 한계 확정.

**Amy 결정 (2026-04-20):** 현 상태 accept. Post-gen LLM rewrite 옵션은 deferred (memory 기록됨: `project_handbook_en_def_length.md`). 5-8초 UX goal 은 미달성이지만 콘텐츠 품질 자체는 B 범위에서 수용 가능.

### 7. GOOD 예시 6개 카테고리 커버

Amy 가 "카테고리 관통" 질문 → Overfitting (concept), Transformer (architecture), RLHF (training), MCP (protocol), PyTorch (tool), Claude (product). 각 카테고리의 "nearing trap" (enumeration of primitives / pipeline stages / RFCs / features / variants) 제거. Scope discipline rule 이 term_type 관계없이 일반화되도록 구성.

---

## 주요 발견 / 학습

### "Backend 고치기" 와 "Backend 고친 걸 사용하기" 는 다름

LLM 이 이미 첫 문장에 완벽한 encyclopedia-lede 를 쓰는데, 우리가 4 iteration 을 "전체를 짧게 만들기" 에 쓰고 있었음. "출력 고치기" vs "출력 사용 고치기" 를 혼동한 classic case. Frontend first-sentence extraction 은 여전히 유효한 옵션이지만 Amy 는 "너무 간단" 이라 기각 — backend fix 를 원함.

### LLM prior 는 prompt rule 보다 강함 (수학-heavy term)

Agentic UX, RLHF, MCP, KD, DPO — 모두 수학/알고리즘 있는 term. Prompt 에 "algorithm detail 금지" 를 어떻게 써도 결국 sentence 2, 3 에 수식 keyword 들어감. Korean 은 이런 경향 약함 (언어 자체 compression 특성 + Korean tech 글의 다른 스타일 prior).

### Variance ≠ Content quality

Quality judge 가 5/74 차이를 내다가 우리가 고친 뒤 60-75 안정. 이건 **judge 의 개선** 이지 content 품질 변화 아님. Metric 을 믿기 전에 metric 자체를 검증해야 함. 3번 돌려서 분산 측정이 그 검증.

### 3-bucket 처분 설계 (accept / queue / reject+log) 가 코드 에 깨끗이 내려옴

설계 결정이 명료하면 구현도 명료. "언제 reject, 언제 queue" 를 한 번 정리하자 A/B/C 모두 동일 패턴으로 깔끔 구현.

### Schema convention discovery 가 compound interest

A.4 구현 중 implementer 가 `pipeline_logs` 의 실제 스키마 (`pipeline_type`, `debug_meta` nested event) 를 발견. 그 convention 을 C.4, B.2 가 재사용. Log consistency 자연히 확보됨 — `WHERE pipeline_type IN ('handbook.scope_gate', 'handbook.korean_gate', 'handbook.grounding_gate')` 로 3 gate 통합 review 가능.

### Test-append 패턴이 유지보수 자산

`backend/tests/test_handbook_validators.py` 에 3 validator 테스트 (35개) 전부 축적. 파일 3개 대신 1개로 관리. 다음 validator 추가 시 여기에 append 만.

### 세션 피로와 plan 벗어남 사이의 trade-off

Plan 준수만 고집했으면 "왜 handbook 컨텐츠가 이상하지?" 질문에 답 못 함. 하지만 pivot 했기에 "정의 길이 문제 해결 못 함" 이라는 known limitation 도 명시적으로 기록됨. **Pivot 자체가 실패 아님 — 기록 안 되면 실패**.

---

## Deferred (memory + plan retro 에 기록됨)

1. **Post-gen EN compression** — UX goal 되살아날 때. $0.001-0.005/term, guaranteed target length.
2. **Admin UI queue review flow** — `status='queued'` 가 handbook_terms 에 쌓이는데 Amy 가 검토할 UI 없음. **blocker** but 이번 세션 범위 밖.
3. **`term_type`-aware scope gate 활성화** — 현재 extraction 시점에 term_type 없어서 product_platform_service 자동 reject 가 dormant.
4. **Orphan `handbook_quality_scores.term_id` backfill** — 과거 생성물 중 term 생성 전에 쓰여서 `term_id=NULL` 인 rows.

---

## 주간 모니터링 쿼리

이번 세션의 가장 실용적 산출물. 매주 한 번 돌리면 3 gate 의 실전 효과 보임:

```sql
SELECT
  pipeline_type,
  debug_meta->>'event' AS event,
  debug_meta->>'term' AS term,
  debug_meta->>'reason' AS reason,
  COUNT(*) AS occurrences,
  MAX(created_at) AS last_seen
FROM pipeline_logs
WHERE pipeline_type IN (
        'handbook.scope_gate',
        'handbook.korean_gate',
        'handbook.grounding_gate'
      )
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY 1, 2, 3, 4
ORDER BY occurrences DESC;
```

결정 도출 방법:
- 같은 term 이 scope_gate 에 반복 등장 → 블록리스트 조정 or 그 term 이 왜 반복 제안되는지 확인
- korean_gate 가 빈번하되 대부분 `korean_name=""` 이면 프롬프트가 잘 작동 (transliteration 대신 empty 반환)
- grounding_gate 가 거의 안 찍히면 (2026-04-17 예측대로) Chunk B 투자 덜 해도 됨

---

## 관련 파일

- Plan + retro: `vault/09-Implementation/plans/2026-04-17-handbook-term-selection-hardening-plan.md`
- 이전 측정 plan: `vault/09-Implementation/plans/2026-04-16-handbook-quality-measurement-plan.md`
- Auto-memory: `project_handbook_en_def_length.md` (EN 길이 known limit)
- 코드 구조:
  - `backend/services/handbook_validators.py` (3 validator)
  - `backend/services/handbook_quality_config.py` (7 config block)
  - `backend/services/agents/prompts_handbook_types.py` (quality judge prompts)
  - `backend/services/agents/prompts_advisor.py` (GENERATE_BASIC_PROMPT definition 섹션)
  - `backend/services/pipeline.py` (3 gate wire-in)
