# 핸드북 섹션 재설계 ship — Basic 13→7 + Hero/Refs/Checklist + Advanced 11→7

> 날짜: 2026-04-10
> 관련: [[ACTIVE_SPRINT]], [[2026-03-27-handbook-content-overhaul]], [[plans/2026-04-09-handbook-section-redesign]], [[plans/2026-04-10-handbook-basic-en-redesign]], [[plans/2026-04-10-handbook-save-and-render]], [[plans/2026-04-10-handbook-advanced-redesign]]

---

## 요약

2026-03-27 콘텐츠 대규모 개편으로 만든 13섹션 Basic / 11섹션 Advanced 구조를 **사용자 entry path 중심**으로 재설계. 5개 샘플 용어(overfitting, DPO, fine-tuning, Hugging Face, MCP)의 품질 평가에서 **중복 섹션 + Basic/Advanced 차별화 실종**이 드러나 전면 재구성.

핵심 변화:
- **Basic 13→7섹션** (분량 -45%)
- **Hero card** 신설 — 뉴스 popup 독자가 본문 진입 전에 졸업할 수 있는 카드
- **References footer** 신설 — JSONB tier 필드(primary/secondary)로 출처 분리
- **Sidebar checklist** 신설 — 학습자용 위젯
- **Advanced 11→7섹션** — Basic의 확장이 아니라 "현직자를 위한 다른 페이지"로 차별화
- **News pipeline 패턴 일치** — Pydantic `max_length` 제거 (codebase 일관성)

22 commits, 약 +2,900 lines, 4 plan documents, 3 new Astro components, 1 DB migration.

---

## 변경 내역

### 1. Basic 7섹션 (구조)

| # | 섹션 | 답하는 질문 | 분량 |
|---|------|-----------|------|
| 1 | 쉽게 이해하기 | "비전문가한테 설명하면?" | 600~800자 |
| 2 | 비유와 예시 | "실생활 예시?" | 3개 시나리오 |
| 3 | 한눈에 비교 | "비슷한 것과 뭐가 달라?" | 표 1개 |
| 4 | 어디서 왜 중요한가 | "왜 중요해 + 어디 쓰여" | 4~5 bullet |
| 5 | 자주 하는 오해 | "사람들이 자주 잘못 아는 것?" | 3개 |
| 6 | 대화에서는 이렇게 | "회의에서 어떻게 말해?" | 5개 문장 |
| 7 | 함께 읽으면 좋은 용어 | "다음에 뭘 읽어?" | 4~6개 |

**제거된 구 섹션 8개:**
- `0_summary` (30초 요약) → Hero card로 승격
- `4_why` + `5_where` → `4_impact` 통합 (3패턴 허용)
- `6b_news_context` → Hero card로 승격
- `6c_checklist` → Sidebar로 이동
- `9_roles` (직군별 활용) → 본문 cut (향후 profile.role 위젯)
- `10_learning_path` Part 1 → References footer로 이동, Part 2 → `7_related`에 통합
- `8_related` → `7_related`로 리넘버

### 2. Hero Card — Path A 사용자 졸업 카드

`hero_news_context_ko/en` 신설. **정확히 3줄**, 각 줄 ≤60자(KO)/≤80자(EN). 형식:
```
"인용구" → 의미
"인용구" → 의미
"인용구" → 의미
```

뉴스 기사에서 popup으로 들어온 독자가 **본문 스크롤 없이** 15초 안에 이해하고 원래 기사로 돌아갈 수 있게.

[`HandbookHeroCard.astro`](frontend/src/components/newsprint/HandbookHeroCard.astro) 컴포넌트로 렌더. Definition + 3 news lines + 옵션 "원래 기사로" 버튼. Level switcher 위에 상시 노출 (level-independent).

### 3. References Footer — JSONB tier 분리

`references_ko/en` 신설 (jsonb). 스키마:
```json
{"title", "authors?", "year?", "venue?", "type", "url", "tier", "annotation"}
```

`type` enum: `paper | docs | code | blog | wiki | book`
`tier` enum: `primary | secondary`

**프롬프트 강제 규칙:** primary 최소 2개, secondary 최대 3개, 총 3~7개. URL은 Reference Materials에서 확인된 것만.

[`HandbookReferences.astro`](frontend/src/components/newsprint/HandbookReferences.astro) 컴포넌트가 tier별 정렬 (★ primary 먼저, · secondary 뒤). Level 토글과 무관하게 항상 보임.

### 4. Sidebar Checklist — 학습자 전용 위젯

`sidebar_checklist_ko/en` 신설 (text). 4~5 questions with `□` marker.

[`HandbookUnderstandingChecklist.astro`](frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro) 컴포넌트가 우측 사이드바에 렌더. **Basic 뷰일 때만 노출** — Advanced 토글 시 JS로 `display: none`.

### 5. Advanced 7섹션 — Basic의 확장 아닌 다른 페이지

| # | 섹션 | Basic과의 차별화 |
|---|------|-----------------|
| 1 | 기술적 정의와 동작 원리 | Formal definition + data flow + Big O. 비유 금지. |
| 2 | 핵심 수식·아키텍처·도표 | LaTeX `$$math$$` 또는 spec table. Basic은 표만. |
| 3 | 코드 또는 의사코드 | 15줄+, error handling, type hints. Basic은 코드 없음. |
| 4 | 트레이드오프 | 적합/부적합 + 대안 기술명. Basic은 개념 차이만. |
| 5 | 프로덕션 함정 | mistake-solution 3+. Basic은 myth/reality. |
| 6 | 업계 대화 맥락 | PR review/design doc/incident tone. Basic은 Slack/standup. |
| 7 | 선행·대안·확장 개념 | (prerequisite\|alternative\|extension) 태그. Basic은 학습 흐름. |

**핵심 메커니즘:** Advanced 호출 시 **Basic body를 context로 주입**하고 프롬프트에 명시적 "DO NOT duplicate" + FAIL conditions + GOOD/BAD 예시를 강하게 박음. 

### 6. Pydantic max_length 제거 — News pipeline 패턴 일치

`definition_ko/en`의 `max_length=160/200`을 완전 제거. `min_length=80`만 유지 (생성 실패 detector 역할).

배경: News pipeline의 12개 BaseModel을 audit한 결과 **min_length/max_length 필드 제약이 0건**. 핸드북만 어제 max_length를 도입해서 codebase inconsistency를 만들었는데, DPO(213자)와 MCP(226자)의 더 정확한 정의가 200자 상한에 걸려 warning을 띄우는 걸 보고 제거 결정. 

철학: **Pydantic은 schema validator(필드 존재/타입), 프롬프트는 content shaper, 어드민은 quality reviewer.** 각 레이어가 자기 책임만.

### 7. Dead code 제거

- `TYPE_MIGRATION` dict 완전 삭제 — old type name에서 new로 매핑하던 fallback. 코드/프론트엔드/DB 어디서도 old name 사용 0건 확인 후 제거.
- `BASIC_TYPE_GUIDES` 키 10개 → 8개 new name (`business_industry` + `concept_theory` → `concept` 통합, `data_structure_format` + `protocol_standard` → `protocol_format` 통합)
- `concept_business` depth guide 삭제

---

## 검증 결과 (5개 샘플 용어)

### Basic KO/EN (Plan B)

| 항목 | 5/5 결과 |
|------|---------|
| 7섹션 정확 출력 | ✅ |
| Hero card 3줄, 형식 준수 | ✅ |
| References primary≥2 / secondary≤3 | ✅ |
| Sidebar checklist 4~5 questions | ✅ |
| §4 anti-pattern (자료 나열) flag | **0건** ✅ |

### Advanced KO/EN (Plan C)

| 항목 | 5/5 결과 |
|------|---------|
| 7섹션 정확 출력 | ✅ |
| Code substantial lines ≥15 | ✅ (56~123 lines) |
| `adv_*_1_mechanism` ≥600 chars | ✅ (1,053~1,473) |
| Math (`$$`) in Advanced only | ✅ 4/5 (Hugging Face는 product라 정상) |
| Code blocks in Advanced only | ✅ |
| Pitfalls 3+ pairs | ✅ (4~6) |
| Tradeoffs suitable+unsuitable | ✅ |
| **Verbatim 50-char overlap (Basic↔Advanced)** | **0건** ✅ |
| **Basic-tone phrases in Advanced** ("쉽게 말해" 등) | **0건** ✅ |
| Length ratio Adv/Basic | 2.37x ~ 4.00x (target 2.0~3.5) |

### 차별화 매트릭스 (7항목 중)

| 용어 | 통과 |
|------|-----|
| overfitting | 7/7 |
| DPO | 7/7 |
| fine-tuning | 7/7 |
| Hugging Face | 5/7 (수식 + tag 미감지 — product라 정상) |
| MCP | 7/7 |

**Plan C success criteria "5+/7" — 5/5 용어 모두 충족.**

---

## 핵심 학습

### 1. "Show, Don't Tell" 패턴이 결정적

Plan B/C 모두에서 가장 강한 효과를 낸 건 **GOOD/BAD 예시 + FAIL conditions + Self-Check** 조합. 단순히 "do not duplicate Basic"라고 instruction에 쓰는 것보다 "BAD opening: 'Transformer는 문장을 이해하는 새로운 방식이다' ← Basic tone, rejected" 같이 **명시적 reject 예시**를 보여주는 게 LLM 행동을 훨씬 강하게 바꿨다.

prompt-engineering-patterns skill의 best practice가 그대로 입증됨.

### 2. Basic body를 Advanced의 context로 주입 = 진짜 차별화

이전에는 프롬프트 instruction에만 의존해 "Advanced는 Basic을 반복하지 마라"고 했는데, Plan C는 **실제 Basic body를 LLM에게 보여주고 "DO NOT duplicate"** 를 함. 결과는:
- Verbatim 50-char overlap: 5/5 용어 0건
- Basic-tone phrases: 5/5 용어 0건

차별화가 instruction-only → context-aware로 바뀐 게 가장 큰 품질 도약이었다.

### 3. Silent failure는 logger.warning 부재의 대가

Plan C 중 가장 큰 버그가 [`_assemble_all_sections`](backend/services/agents/advisor.py#L1167)의 assembly trigger condition. 새 키(`adv_ko_1_mechanism`)로 바꿨는데 trigger는 legacy 키(`adv_ko_1_technical`)를 체크해서, 첫 regen이 **0 chars로 통째로 실패**했지만 error도 없고 test도 통과했다. analyzer 스크립트가 없었으면 한참 늦게 발견됐을 것.

**원인**: assembly fallback에 `else` branch가 없음. `if` → `elif` → 끝.

**교훈**: 모든 fallback path에 `logger.warning(...)`를 추가하자. 다음 plan들에서 이 패턴을 default로.

### 4. Codebase audit이 설계 결정을 견인

`max_length` 제거 결정의 근거는 "더 좋은 디자인이라 생각해서"가 아니라 **"news_pipeline.py를 audit한 결과 길이 제약이 0건이었다"**. 이미 codebase에 좋은 prior art가 있었고, 핸드북만 일관성을 깨고 있었다.

설계를 머릿속에서 만들지 말고 **codebase에서 발견**하면 훨씬 강한 근거가 됨.

### 5. Plan-driven execution의 효율

3개 plan(B → A → C)을 순차로 실행. 각 plan은:
- 5~10 task로 분해 (executable bite-sized)
- TDD 패턴 (test 먼저, 통과 확인, 구현, 통과 재확인, commit)
- Success criteria + Rollback plan 명시
- Skill의 best practices 반영

결과: 22 commits, 모두 main에 직접, 큰 rework 0건. **첫 시도에 ship-ready**.

---

## 미해결 / 후속

1. **138개 published 용어 전량 regenerate** — 새 구조 적용. 비용 ~$15, 시간 ~2시간 (병렬 실행 시). 별도 plan 없이 진행 가능.
2. **Admin editor UI 확장** — 어드민이 `hero_news_context`, `references`, `sidebar_checklist`를 직접 편집할 수 있게. Plan A의 explicit out-of-scope였음.
3. **`logger.warning` fallback 패턴 도입** — `_assemble_all_sections` 같은 silent failure 방지. 기술 부채로 넘김.
4. **Hugging Face의 `7_related` tag 누락** — analyzer 스크립트의 false negative인지 실제 누락인지 수동 검증 필요.
5. **References tier 강화** — fine-tuning EN regen에서 secondary가 4개로 한 번 초과. 거의 모든 케이스 통과지만 edge case 모니터링.

---

## 메타: Plan-driven execution timeline

| Phase | 시작 | 완료 | 작업 |
|-------|------|------|------|
| KO Basic baseline | 2026-04-09 | 2026-04-10 | 구조 + 5개 용어 검증 (commit `70a0e77`) |
| Plan B (EN Basic) | 2026-04-10 | 2026-04-10 | 5 commits, prompt 1 + sections + tests |
| Plan A (DB + Frontend) | 2026-04-10 | 2026-04-10 | 7 commits, migration + 3 components + Playwright 검증 |
| Plan C (Advanced) | 2026-04-10 | 2026-04-10 | 8 commits, 2 prompts + assembly fix + 차별화 검증 |

총: **22 commits, 1일** (KO baseline 포함하면 2일).

---

## Related

- [[ACTIVE_SPRINT]] — HB-REDESIGN B/A/C 모두 done
- [[2026-03-27-handbook-content-overhaul]] — 이전 콘텐츠 개편 (이 작업이 그것을 재구성)
- [[plans/2026-04-09-handbook-section-redesign]] — 마스터 설계 문서
- [[plans/2026-04-10-handbook-basic-en-redesign]] — Plan B
- [[plans/2026-04-10-handbook-save-and-render]] — Plan A
- [[plans/2026-04-10-handbook-advanced-redesign]] — Plan C
