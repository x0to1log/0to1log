# Handbook Advanced Prompt Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Advanced 본문을 Basic과 차별화되는 "현직자 흐름"(메커니즘→코드→트레이드오프→함정→대화→관련) 7섹션으로 재설계해, 길이만 다른 Basic의 확장이 아니라 "다른 질문에 답하는 다른 페이지"가 되도록 만든다.

**Architecture:** Call 3(`GENERATE_ADVANCED_PROMPT` KO)와 Call 4(`GENERATE_ADVANCED_EN_PROMPT` EN) 두 시스템 프롬프트를 재작성한다. `ADVANCED_SECTIONS_KO/EN` 섹션 조립 리스트를 11→7개로 교체하고, section count warning을 9→7로 조정하고, `TYPE_DEPTH_GUIDES` 참조 키를 신규 섹션 키에 맞게 업데이트한다. DB 스키마·Pydantic 모델·프론트엔드 렌더링은 건드리지 않음 (Advanced body도 여전히 `body_advanced_ko/en` 단일 컬럼에 concat 저장).

**Tech Stack:** Python 3.11, OpenAI Python SDK, Pydantic v2, pytest

**Commit:** `70a0e77` (KO Basic 재설계) + Plan B 완료 + Plan A 완료 이후 작업. Plan C가 가장 큰 프롬프트 변경이므로 맨 마지막.

---

## Context for the implementer

1. **Advanced는 현재 11섹션 구조** ([advisor.py:1111-1137](backend/services/agents/advisor.py#L1111-L1137)):
   `1_technical`, `2_formulas`, `3_howworks`, `4_code`, `5_practical`, `10_when_to_use`, `11_pitfalls`, `6_why`, `7_comm`, `8_refs`, `9_related`

2. **재설계 목표는 7섹션**:
   - `1_mechanism` ← 기존 `1_technical` + `3_howworks` 병합
   - `2_formulas` (그대로)
   - `3_code` ← 기존 `4_code` 리넘버링
   - `4_tradeoffs` ← 기존 `10_when_to_use` 리네임
   - `5_pitfalls` ← 기존 `5_practical` 후반부 + `11_pitfalls` 병합
   - `6_comm` ← 기존 `7_comm` 리넘버링
   - `7_related` ← 기존 `9_related` 리넘버링

3. **완전 삭제되는 기존 섹션**:
   - `5_practical` 전반부 (use cases) — `1_mechanism` 말미 1문단에 흡수
   - `6_why` — Basic `4_impact`가 충분히 커버함
   - `8_refs` — **`references_ko/en` footer로 이동 (이미 Basic이 생성 담당)**

4. **Basic과의 차별화 매트릭스** (plan 2026-04-09 §7 참조):
   | 항목 | Basic | Advanced |
   |---|---|---|
   | 비유 | 있음 | 없음 |
   | 코드 | 없음 | 있음 |
   | 수식 | 없음 | 있음 |
   | 사용 맥락 | "세상에서 어디 쓰이나" | "프로덕션에서 어떻게 깨지나" |
   | 비교 성격 | 개념 차이 | 기술 트레이드오프 |
   | 대화 톤 | Slack/회의 일상 | PR 리뷰/설계 문서/incident |
   | 관련 용어 | 학습 다음 단계 | 선행·대안·확장 |

5. **References가 Advanced에서 빠지는 이유**: Basic Call 1에서 `references_ko`, Call 2에서 `references_en`이 생성되고 level-independent footer에 렌더됨. Advanced가 별도로 refs를 생성하면 중복이 되므로 완전 제거.

**Read before starting:**
- [`vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md`](vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md) — §5.3 Advanced 섹션 스펙, §7 차별화 매트릭스
- [`backend/services/agents/prompts_advisor.py:570-795`](backend/services/agents/prompts_advisor.py#L570-L795) — KO Basic 프롬프트 (형식 기준)
- [`backend/services/agents/prompts_advisor.py:867-964`](backend/services/agents/prompts_advisor.py#L867-L964) — 현재 KO Advanced 프롬프트 (교체 대상)
- [`backend/services/agents/prompts_advisor.py:967-1064`](backend/services/agents/prompts_advisor.py#L967-L1064) — 현재 EN Advanced 프롬프트 (교체 대상)
- [`backend/services/agents/advisor.py:1111-1137`](backend/services/agents/advisor.py#L1111-L1137) — `ADVANCED_SECTIONS_KO/EN`
- [`backend/services/agents/prompts_handbook_types.py:87-160`](backend/services/agents/prompts_handbook_types.py#L87-L160) — `TYPE_DEPTH_GUIDES` (섹션 키 참조 업데이트 필요)
- [`backend/services/agents/advisor.py:1646-1656`](backend/services/agents/advisor.py#L1646-L1656) — section count warning (Advanced threshold 9)

---

### Task 1: Advanced 섹션 리스트 교체 (KO + EN)

**Files:**
- Modify: `backend/services/agents/advisor.py:1111-1137`

**Step 1: Write failing test**

Create `backend/tests/test_advanced_sections.py`:

```python
"""Test that ADVANCED_SECTIONS_{KO,EN} match the 7-section redesign (Plan C)."""
from services.agents.advisor import ADVANCED_SECTIONS_KO, ADVANCED_SECTIONS_EN


def test_advanced_sections_ko_has_7_entries():
    assert len(ADVANCED_SECTIONS_KO) == 7


def test_advanced_sections_en_has_7_entries():
    assert len(ADVANCED_SECTIONS_EN) == 7


def test_advanced_sections_ko_keys():
    expected = [
        "adv_ko_1_mechanism",
        "adv_ko_2_formulas",
        "adv_ko_3_code",
        "adv_ko_4_tradeoffs",
        "adv_ko_5_pitfalls",
        "adv_ko_6_comm",
        "adv_ko_7_related",
    ]
    assert [k for k, _ in ADVANCED_SECTIONS_KO] == expected


def test_advanced_sections_en_keys():
    expected = [
        "adv_en_1_mechanism",
        "adv_en_2_formulas",
        "adv_en_3_code",
        "adv_en_4_tradeoffs",
        "adv_en_5_pitfalls",
        "adv_en_6_comm",
        "adv_en_7_related",
    ]
    assert [k for k, _ in ADVANCED_SECTIONS_EN] == expected


def test_advanced_sections_no_legacy_keys():
    """Removed sections: refs, why, practical (full form), howworks, technical."""
    legacy_ko = {
        "adv_ko_1_technical", "adv_ko_3_howworks", "adv_ko_5_practical",
        "adv_ko_6_why", "adv_ko_8_refs", "adv_ko_9_related",
        "adv_ko_10_when_to_use", "adv_ko_11_pitfalls",
    }
    ko_keys = {k for k, _ in ADVANCED_SECTIONS_KO}
    assert legacy_ko.isdisjoint(ko_keys), f"Legacy keys leaked: {legacy_ko & ko_keys}"

    legacy_en = {
        "adv_en_1_technical", "adv_en_3_howworks", "adv_en_5_practical",
        "adv_en_6_why", "adv_en_8_refs", "adv_en_9_related",
        "adv_en_10_when_to_use", "adv_en_11_pitfalls",
    }
    en_keys = {k for k, _ in ADVANCED_SECTIONS_EN}
    assert legacy_en.isdisjoint(en_keys)
```

**Step 2: Run test and verify failure**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_advanced_sections.py -v`
Expected: multiple FAILs (current lists have 11 entries with legacy keys).

**Step 3: Edit `ADVANCED_SECTIONS_KO` and `ADVANCED_SECTIONS_EN`**

Replace lines 1111-1137:
```python
ADVANCED_SECTIONS_KO = [
    ("adv_ko_1_mechanism", "## 기술적 정의와 동작 원리"),
    ("adv_ko_2_formulas", "## 핵심 수식·아키텍처·도표"),
    ("adv_ko_3_code", "## 코드 또는 의사코드"),
    ("adv_ko_4_tradeoffs", "## 트레이드오프와 언제 무엇을 쓰나"),
    ("adv_ko_5_pitfalls", "## 프로덕션 함정"),
    ("adv_ko_6_comm", "## 업계 대화 맥락"),
    ("adv_ko_7_related", "## 선행·대안·확장 개념"),
]

ADVANCED_SECTIONS_EN = [
    ("adv_en_1_mechanism", "## Technical Definition & How It Works"),
    ("adv_en_2_formulas", "## Formulas, Architecture, and Diagrams"),
    ("adv_en_3_code", "## Code or Pseudocode"),
    ("adv_en_4_tradeoffs", "## Tradeoffs — When to Use What"),
    ("adv_en_5_pitfalls", "## Production Pitfalls"),
    ("adv_en_6_comm", "## Industry Communication"),
    ("adv_en_7_related", "## Prerequisites, Alternatives, and Extensions"),
]
```

**Step 4: Run tests to verify pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_advanced_sections.py -v`
Expected: 5/5 PASS.

**Step 5: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_advanced_sections.py
git commit -m "feat(handbook): Advanced 섹션 리스트 11→7 재정렬"
```

---

### Task 2: Section count warning Advanced threshold

**Files:**
- Modify: `backend/services/agents/advisor.py:1646-1656`

**Step 1: Update the threshold**

Find the warning block that currently reads:
```python
elif adv_content.count("## ") < 9:
    warnings.append(f"body_advanced_{lang}: only {adv_content.count('## ')}/9 sections")
```

Change both `9`s to `7`. Also update the comment:
```python
# Basic: 7 sections (post-redesign, both KO and EN).
# Advanced: 9 sections (both languages, not yet redesigned).
```
→
```python
# Basic: 7 sections. Advanced: 7 sections. (Post-redesign, both languages.)
```

**Step 2: Add a regression test**

Append to `backend/tests/test_advanced_sections.py`:

```python
def test_advanced_warning_threshold_is_seven():
    """Post-redesign: Advanced section count warning at <7 sections."""
    import inspect
    from services.agents import advisor

    source = inspect.getsource(advisor)
    assert 'adv_content.count("## ") < 7' in source
    assert 'adv_content.count("## ") < 9' not in source
```

**Step 3: Run test, verify pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_advanced_sections.py::test_advanced_warning_threshold_is_seven -v`
Expected: PASS (after Step 1 edit).

**Step 4: Commit**

```bash
git add backend/services/agents/advisor.py backend/tests/test_advanced_sections.py
git commit -m "feat(handbook): Advanced section count warning 9→7"
```

---

### Task 3: `TYPE_DEPTH_GUIDES` 섹션 키 참조 업데이트

**Files:**
- Modify: `backend/services/agents/prompts_handbook_types.py:87-160`

**Step 1: Read current `TYPE_DEPTH_GUIDES`**

The dict contains 8 type-specific blocks. Each block uses placeholder `adv_*_N_<oldname>` references like:
- `adv_*_1_technical` → should be `adv_*_1_mechanism`
- `adv_*_3_howworks` → merged into `1_mechanism`
- `adv_*_4_code` → `adv_*_3_code`
- `adv_*_5_practical` → merged into `5_pitfalls`
- `adv_*_10_when_to_use` → `adv_*_4_tradeoffs`
- `adv_*_11_pitfalls` → `adv_*_5_pitfalls`
- `adv_*_6_why` → DELETED (remove references)
- `adv_*_7_comm` → `adv_*_6_comm`
- `adv_*_8_refs` → DELETED (now in references footer)
- `adv_*_9_related` → `adv_*_7_related`

**Step 2: Apply the rename systematically**

For each of the 8 type blocks (model_architecture, hardware_infra, concept, product_platform, metric_benchmark, technique_method, protocol_format_data, protocol_format, workflow_pattern), rewrite the bullet points to use the new section keys.

**Example — `model_architecture` block transformation:**

Before:
```python
    "model_architecture": """## Type-Specific Depth: Algorithm/Model
- adv_*_1_technical: Include time/space complexity (Big O). Reference the original paper if applicable.
- adv_*_2_formulas: Full mathematical formulation with derivation steps, not just final formula. Include loss function, gradient update rules.
- adv_*_3_howworks: Data flow diagram description. Input → layers/steps → output. Include tensor shapes if applicable.
- adv_*_4_code: Production-grade code (NOT hello world). Include error handling, type hints, real library usage (torch, sklearn). Min 15 lines.
- adv_*_5_practical: Include benchmark comparisons (accuracy, latency, memory) with specific numbers from reference materials. If no benchmarks are available in references, state "Public benchmarks not yet available" rather than inventing numbers.
- CRITICAL: Do NOT fabricate paper titles, arXiv IDs, author names, or publication venues. Only cite papers from the Reference Materials provided. If no paper reference is available, write "See official documentation" instead.""",
```

After:
```python
    "model_architecture": """## Type-Specific Depth: Model Architecture
- adv_*_1_mechanism: Formal technical definition + data flow (input → layers/steps → output) + tensor shapes where relevant. Include time/space complexity (Big O). Reference the original paper if it appears in Reference Materials.
- adv_*_2_formulas: Full mathematical formulation with derivation steps, not just the final formula. Include loss function and gradient update rules.
- adv_*_3_code: Production-grade code (NOT hello world). Error handling, type hints, real library usage (torch, sklearn). Min 15 substantial lines.
- adv_*_4_tradeoffs: Decision framework — when to use this architecture vs alternatives. Include benchmark comparisons (accuracy, latency, memory) with numbers from Reference Materials. State "Public benchmarks not yet available" rather than inventing numbers.
- adv_*_5_pitfalls: Production failure modes — gradient instability, memory explosion, convergence problems, data leakage. Each with mitigation.
- CRITICAL: Do NOT fabricate paper titles, arXiv IDs, author names, or venues. Only cite papers from Reference Materials. If none available, write "See official documentation" instead.""",
```

Apply similar transformations to the remaining 7 type blocks. For blocks that used `adv_*_6_why` or `adv_*_8_refs`, simply delete those lines since those sections no longer exist.

**Step 3: Similarly update `TYPE_SECTION_WEIGHTS`**

The `TYPE_SECTION_WEIGHTS` dict ([prompts_handbook_types.py:201-281](backend/services/agents/prompts_handbook_types.py#L201-L281)) contains `section_guide` prose that references section roles. These are more loosely worded but should be audited to ensure no mentions of "section refs" or "section 6_why" leak through.

Quick scan: `grep -n "6_why\|8_refs\|when_to_use\|11_pitfalls\|1_technical\|3_howworks" backend/services/agents/prompts_handbook_types.py`
Any match = edit to use new names or remove.

**Step 4: Run existing handbook tests**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_handbook_advisor.py -v -k "generate" --tb=short`
Expected: 4/4 PASS. These tests don't exercise the prompt text directly but catch import errors.

**Step 5: Commit**

```bash
git add backend/services/agents/prompts_handbook_types.py
git commit -m "feat(handbook): TYPE_DEPTH_GUIDES 섹션 키 참조를 Advanced 7섹션으로 업데이트"
```

---

### Task 4: `GENERATE_ADVANCED_PROMPT` (KO) 재작성

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py:867-964`

**Step 1: Read the current prompt and Basic KO prompt as template**

Read `prompts_advisor.py:867-964` (legacy KO Advanced) and `prompts_advisor.py:570-795` (post-redesign KO Basic).

Note the Basic prompt's overall skeleton:
- Header paragraph + DOMAIN CONTEXT + GROUNDING_RULES + LANGUAGE RULE
- Page Architecture block
- Section key descriptions (with GOOD/BAD examples)
- Output JSON Structure
- Self-Check
- Quality Rules
- Markdown + Table rules

**Step 2: Write the replacement prompt**

Replace `GENERATE_ADVANCED_PROMPT` (lines 867-964) with:

```python
GENERATE_ADVANCED_PROMPT = """\
You are a technical education writer for 0to1log, an AI/tech handbook platform.

Generate KOREAN content only. English content will be generated in a separate call.

Generate ADVANCED-level KOREAN body for a handbook term. This is Call 3 of 4 — you handle Korean engineer-level content only. The term's definition and Basic body (from Call 1) are provided as context.

DOMAIN CONTEXT:
- Focus on the AI/IT meaning. Note cross-field differences if applicable.
- Base content on established facts from official docs and papers.
""" + GROUNDING_RULES + """
LANGUAGE RULE:
- Korean headers and Korean body text. Technical terms (Transformer, API, fine-tuning) may remain in English where natural in Korean tech writing.
- Do NOT use bilingual headers like "한국어 / English". Korean only.

## Page Architecture Reminder

This handbook page has FIVE rendering zones. Advanced body fills ONE of them:

1. Hero Card — already generated in Call 1. Do NOT duplicate definition or news context.
2. Basic body — already generated in Call 1. Do NOT repeat concepts covered there.
3. **Advanced body** ← YOU generate 7 sections here.
4. References footer — already generated in Call 1 (`references_ko`). Do NOT generate reference lists, reading lists, or link collections here. If you need to cite a source, reference it inline with minimal context and let the footer handle it.
5. Sidebar checklist — already generated in Call 1. Not your concern.

**IMPORTANT**: The old advanced sections `adv_ko_1_technical`, `adv_ko_3_howworks`, `adv_ko_5_practical`, `adv_ko_6_why`, `adv_ko_8_refs`, `adv_ko_9_related`, `adv_ko_10_when_to_use`, `adv_ko_11_pitfalls` no longer exist. Do NOT output them. Their content has been merged or moved as described below.

## Basic vs Advanced Differentiation

You are writing for a **senior developer / ML engineer / tech lead** who already read the Basic version (or already knows the basics). The Advanced body must answer DIFFERENT questions than Basic:

| Question | Basic answered | Advanced answers (YOU) |
|---|---|---|
| What is it? | Plain analogy | Formal definition + data flow |
| Show me | Scenarios + comparison table | Code, math, architecture |
| Where used | External world uses | Production failures and fixes |
| How to compare | Concept differences | Technical trade-offs (cost, latency, complexity) |
| Communication | Slack casual | PR review / design doc / incident postmortem tone |
| What to read next | Learning sequence | Prerequisites + alternatives + extensions |

**Do NOT restate Basic.** Do NOT include analogies, non-technical examples, or "why this matters for business" — that's the Basic's job. Assume the reader has CS fundamentals and can read code and math.

---

## body_advanced — 심화 (목표 6,500~9,000자, 7개 섹션)

### Section key descriptions (Korean — adv_ko_*):

- **adv_ko_1_mechanism** (기술적 정의와 동작 원리, 목표 900~1,400자):
  Formal definition at paper/reference-doc precision. Then internal data flow and mechanism.
  구성: (1) 형식적 정의와 주요 구성요소 2~3문장 (2) 데이터/제어 흐름 서술 (3) 핵심 알고리즘 단계 (번호 리스트) 또는 복잡도 (Big O). Cite papers only from Reference Materials.
  **Must NOT**: re-explain what the term is at an intro level (Basic did that). No analogies. No "easy to understand" framing.
  GOOD opening: "Transformer는 self-attention 연산을 핵심으로 하는 시퀀스-투-시퀀스 아키텍처다. 인코더/디코더 각각은 multi-head attention과 position-wise FFN으로 구성되며, 모든 토큰 간 관계를 O(n²) 시간에 병렬 계산한다."
  BAD opening: "Transformer는 문장을 이해하는 새로운 방식이다." ← Basic tone.

- **adv_ko_2_formulas** (핵심 수식·아키텍처·도표, 조건부):
  Mathematical formulation with derivation + architecture diagrams (text-based) + technical comparison tables. 수식 있으면 반드시, 없으면 비교표/구조표만.
  Use `$$formula$$` for math. Never single `$` (reserved for currency).
  NEVER put math inside table cells — they don't render. Use bullet lists for formula comparisons.
  Example: Attention formula `$$\\text{{Attention}}(Q, K, V) = \\text{{softmax}}\\left(\\frac{{QK^T}}{{\\sqrt{{d_k}}}}\\right)V$$`

- **adv_ko_3_code** (코드 또는 의사코드, 15줄+):
  Real production-grade code. Python/JS preferred. Language tag required: ` ```python `.
  Min 15 substantial lines (excluding blanks, comments, single-brace lines).
  Include: error handling, type hints, realistic usage. Use only standard library + widely-available packages (torch, sklearn, pandas, numpy, requests).
  **Must NOT**: pseudocode with "..." placeholders, hello-world fragments, marketing-style API calls with no error paths.

- **adv_ko_4_tradeoffs** (트레이드오프와 언제 무엇을 쓰나, 목표 800~1,200자):
  Decision framework for when to use this vs alternatives. Formerly `10_when_to_use`.
  구성: **이럴 때 적합** 3~4개 + **이럴 때 부적합** 3~4개. 각 부적합 항목은 대안 기술 이름 명시 필수.
  For each suitable/unsuitable scenario: include **one concrete technical reason** (cost, latency, accuracy, memory, team complexity).
  GOOD (모델): "이럴 때 적합: 이미지+텍스트 동시 분석이 필요한 고객 지원 챗봇 (멀티모달 입력이 핵심), 100페이지+ 문서에서 표와 그래프를 함께 해석 / 이럴 때 부적합: 단순 텍스트 챗봇 — GPT-5.2가 더 저렴하고 충분, 실시간 음성 통화 — 레이턴시 200ms+ (Whisper 추천)"
  GOOD (phenomenon 대응): "이럴 때 주의: IID 가정이 약한 시계열 데이터, 소규모 표본 + 고복잡 모델 조합, 훈련-테스트 분할이 시간적으로 겹칠 때 / 이럴 때 덜 문제: 대규모 대표 샘플 + 정규화가 이미 걸린 파이프라인"

- **adv_ko_5_pitfalls** (프로덕션 함정, 목표 700~1,100자):
  Real failure modes engineers hit in production. Formerly merged from `5_practical` (후반부) + `11_pitfalls`.
  구성: 3~4개 mistake-solution 쌍. 형식: `실수: 구체적 상황 -> 해결: 대응법`. 각 실수는 실제 엔지니어링 경험에서 나온 것이어야 함.
  GOOD: "실수: context window를 꽉 채우면 응답 품질이 급락한다 -> 해결: 입력을 70% 이하로 유지, 나머지는 RAG로 분리."
  GOOD: "실수: embedding 모델을 교체하면 기존 벡터 DB 전체를 재인덱싱해야 한다 -> 해결: 초기에 embedding 모델을 신중히 선택하고 버전 락을 건다."
  BAD: "실수: 튜토리얼 없이 시작하면 어렵다 -> 해결: 공식 문서를 읽는다." (너무 막연)

- **adv_ko_6_comm** (업계 대화 맥락, 6~8개 문장):
  Sentences as they appear in **PR reviews, design docs, architecture reviews, incident postmortems** — not casual Slack.
  **Bold key terms** with `**`. Include specific context: version numbers, metrics, team names.
  Tone: precise, engineering-y, sometimes post-incident reflective.
  GOOD: "- '**v2 rollout**에서 **p99 latency가 350ms → 510ms**로 튀었습니다. **MoE layer**의 **expert routing**이 특정 토큰에 쏠리는 패턴을 확인했고, 다음 스프린트에 **aux loss**를 추가할 예정입니다.'"
  GOOD: "- '**DPO 실험**에서 **chosen/rejected gap**이 안정적으로 수렴하지 않아, **β를 0.1 → 0.3**으로 올렸더니 선호 반영이 뚜렷해졌습니다. trade-off는 **reference model에 대한 KL**이 커지는 것.'"
  BAD: "- '이 기술이 정말 좋네요!'" (casual, no technical substance)

- **adv_ko_7_related** (선행·대안·확장 개념, 4~6개):
  Related terms categorized: **Prerequisites** (learn first), **Alternatives** (competitors), **Extensions** (what comes next).
  형식: `- **용어** (prerequisite|alternative|extension) — 기술적 관계 + 왜 이 관점에서 중요한가`
  Do NOT repeat Basic's `7_related` learning-flow framing. Here, focus on **technical dependency** and **system design choice**.
  GOOD: "- **Multi-head attention** (prerequisite) — single-head attention의 한계(표현력 제약)를 풀기 위해 제안된 구조. Transformer를 이해하려면 먼저 잡아야 함."
  GOOD: "- **Mamba** (alternative) — state space model 기반으로 O(n²) → O(n)으로 복잡도 개선. long-context에서 트레이드오프 비교 대상."
  GOOD: "- **Mixture of Experts** (extension) — Transformer 기반 FFN을 expert pool로 확장. 파라미터 확장 + 추론 비용 제어를 동시에 노림."

---

## Output JSON Structure

```json
{{
  "adv_ko_1_mechanism": "기술적 정의 + 데이터 흐름 + 복잡도",
  "adv_ko_2_formulas": "수식과 도표 ($$로 감싼 LaTeX)",
  "adv_ko_3_code": "```python\\n...\\n```",
  "adv_ko_4_tradeoffs": "이럴 때 적합: ...\\n이럴 때 부적합: ...",
  "adv_ko_5_pitfalls": "실수: ... -> 해결: ...\\n실수: ... -> 해결: ...",
  "adv_ko_6_comm": "- \\"문장 1\\"\\n- \\"문장 2\\"\\n- ...",
  "adv_ko_7_related": "- **용어** (prerequisite|alternative|extension) — 관계"
}}
```

## Self-Check (verify before responding)
✓ No section repeats content from Basic (no analogies, no "easy to understand" framing, no non-technical examples)
✓ `adv_ko_1_mechanism` starts with formal definition, not an intro line
✓ `adv_ko_2_formulas` has actual math OR technical comparison tables (not just descriptions)
✓ `adv_ko_3_code` has 15+ substantial lines with error handling and type hints
✓ `adv_ko_4_tradeoffs` has 3+ suitable + 3+ unsuitable cases, each unsuitable names an alternative
✓ `adv_ko_5_pitfalls` has 3+ concrete mistake-solution pairs from real engineering
✓ `adv_ko_6_comm` has 6~8 sentences in PR review / design doc / incident tone (not Slack)
✓ `adv_ko_7_related` has 4~6 entries, each tagged (prerequisite|alternative|extension)
✓ NO output fields for: `adv_ko_1_technical`, `adv_ko_3_howworks`, `adv_ko_5_practical`, `adv_ko_6_why`, `adv_ko_8_refs`, `adv_ko_9_related`, `adv_ko_10_when_to_use`, `adv_ko_11_pitfalls` — these keys have been replaced or removed

## Quality Rules
- Only generate fields that are EMPTY in the input. Preserve existing non-empty fields.
- FACTUAL ACCURACY: Only include examples you are confident about. If unsure, do NOT claim it.
- NO REPETITION across sections: each section must add NEW information.
- **References go in `references_ko` footer (generated in Call 1). Do NOT list references, reading lists, or link collections in Advanced sections.**
- Do NOT fabricate paper titles, arXiv IDs, or author names.

## Markdown Formatting
- Use **bold** for key terms
- Use bullet points for lists, NOT inline numbering like "1) 2) 3)"
- Use code blocks with language tags for code examples
- Do NOT use `###` sub-headings inside body sections — section H2 is added by the system

## Table Rules
- MUST be comparison/contrast or technical spec tables — NOT simple definitions
- Include actual numbers, formulas, or architectural comparisons
- Math formulas: `$$formula$$` only (NOT single $). Single $ is reserved for currency.
- NEVER put math inside markdown table cells — they will not render. Use bullet lists for formula comparisons.

Respond in JSON format only."""
```

**Step 3: Run ruff**

Run: `cd backend && .venv/Scripts/python -m ruff check services/agents/prompts_advisor.py`
Expected: All checks passed!

**Step 4: Commit**

```bash
git add backend/services/agents/prompts_advisor.py
git commit -m "feat(handbook): GENERATE_ADVANCED_PROMPT (KO) 재작성 — 7섹션 + Basic 차별화"
```

---

### Task 5: `GENERATE_ADVANCED_EN_PROMPT` (EN) 재작성

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py:967-1064`

**Step 1: Mirror Task 4 in English**

Replace `GENERATE_ADVANCED_EN_PROMPT` with an English version following the same structure as the KO prompt. Every section description, GOOD/BAD example, and Self-Check item should be in English. Field keys use `adv_en_*`.

Key adjustments:
- Target length: 7,000~10,000 chars (English is more verbose)
- Tone for `adv_en_6_comm`: "PR review / design doc / incident postmortem — not Slack"
- Use the same 8-type differentiation principle

Draft the prompt following the exact skeleton of Task 4, just translate all Korean prose to English. Keep the same structural rules (7 sections, no refs, no why, Basic differentiation matrix).

**Step 2: Run ruff + existing tests**

Run:
```bash
cd backend && .venv/Scripts/python -m ruff check services/agents/prompts_advisor.py
cd backend && .venv/Scripts/python -m pytest tests/test_handbook_advisor.py -v -k "generate" --tb=short
```
Expected: ruff pass, 4/4 generate tests pass.

**Step 3: Commit**

```bash
git add backend/services/agents/prompts_advisor.py
git commit -m "feat(handbook): GENERATE_ADVANCED_EN_PROMPT 재작성 — KO 미러"
```

---

### Task 6: `advisor.py` advanced call context update

**Files:**
- Modify: `backend/services/agents/advisor.py` — find where KO Advanced and EN Advanced prompts are called.

**Step 1: Locate advanced call sites**

Run: `grep -n "GENERATE_ADVANCED_PROMPT\|GENERATE_ADVANCED_EN_PROMPT\|advanced_prompt" backend/services/agents/advisor.py`

Expected locations (approximate):
- Around line 1363-1400 — `advanced_prompt = f"{user_prompt}\n\n--- Context from Call 1 ---\nDefinition (KO): {basic_data.get('definition_ko', '')}\nDefinition (EN): {basic_data.get('definition_en', '')}"`

**Step 2: Add Basic body as context**

The post-redesign Advanced prompt explicitly references "already generated Basic body". The LLM needs to see the Basic body it must complement without duplicating.

Extend the context concatenation:
```python
advanced_prompt = (
    f"{user_prompt}\n\n"
    f"--- Context from Call 1 ---\n"
    f"Definition (KO): {basic_data.get('definition_ko', '')}\n"
    f"Definition (EN): {basic_data.get('definition_en', '')}\n"
    f"\n--- Basic KO body (do NOT duplicate) ---\n"
    f"{_assemble_markdown(basic_data, BASIC_SECTIONS_KO)[:3000]}\n"
    f"\n--- Basic EN body (do NOT duplicate) ---\n"
    f"{_assemble_markdown(basic_data, BASIC_SECTIONS_EN)[:3000] if any(k.startswith('basic_en_') for k in basic_data) else '(not yet generated)'}"
)
```

Truncate each Basic body to 3000 chars (max 6000 extra tokens) to keep context budget reasonable. Advanced prompt itself is ~4000 tokens + this context ~1500 tokens, well under `max_tokens=16000`.

**Step 3: Commit**

```bash
git add backend/services/agents/advisor.py
git commit -m "feat(handbook): Advanced call에 Basic body를 context로 전달 (중복 방지)"
```

---

### Task 7: Validation — 5개 용어 전체 regen + 차별화 검증

**Step 1: Update `c:/tmp/analyze_regen.py` to also check Advanced**

Add helper functions:
```python
def analyze_advanced(data, term_label):
    body = data.get("body_advanced_ko", "")
    sections = re.findall(r"^## (.+)$", body, re.MULTILINE)
    print(f"\n--- ADVANCED {term_label} ---")
    print(f"length: {len(body)} chars, sections: {len(sections)}")
    for s in sections:
        print(f"  - {s}")

    # Differentiation check: Advanced must have things Basic doesn't
    basic_body = data.get("body_basic_ko", "")

    has_code_adv = "```" in body
    has_code_basic = "```" in basic_body
    has_math_adv = "$$" in body
    has_math_basic = "$$" in basic_body

    print(f"\n  Differentiation vs Basic:")
    print(f"    code block:   Basic={'✗' if not has_code_basic else '⚠️'}  Advanced={'✓' if has_code_adv else '✗'}")
    print(f"    math ($$):    Basic={'✗' if not has_math_basic else '⚠️'}  Advanced={'✓' if has_math_adv else '✗'}")
    print(f"    Basic→Advanced length ratio: {len(body)/max(len(basic_body),1):.2f}x")
```

Call it in the `analyze()` function after the Basic analysis.

**Step 2: Regenerate 5 terms (overfitting, dpo, fine-tuning, hugging-face, mcp)**

Run in parallel (each ~90-120s):
```bash
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py overfitting
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py dpo
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py fine-tuning
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py hugging-face
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py mcp
```

**Step 3: Run analysis**

Run: `PYTHONIOENCODING=utf-8 python c:/tmp/analyze_regen.py`

Verify for each term:
- [ ] Advanced body has 7 sections (not 9, not 11)
- [ ] Advanced body has `$$` math (for model_architecture, concept, metric_benchmark types) OR table (for product, workflow types)
- [ ] Advanced body has ` ``` ` code block
- [ ] Advanced length ratio (Advanced/Basic) is 2.0~3.0x
- [ ] Advanced does NOT contain reference list or link collection
- [ ] Advanced `6_comm` bullets sound technical (version numbers, metrics, incident-style phrasing)

**Step 4: Differentiation matrix validation**

Complete the 7-item matrix from plan 2026-04-09 §7 for each term. Each cell should be concretely true:

| 항목 | Basic | Advanced |
|---|---|---|
| 비유 | ? | ? |
| 코드 | ? | ? |
| 수식 | ? | ? |
| 사용 맥락 | ? | ? |
| 비교 성격 | ? | ? |
| 대화 톤 | ? | ? |
| 관련 용어 | ? | ? |

**Pass criterion: at least 5 of 7 rows must show clear differentiation.**

**Step 5: Spot-check for duplication**

For each term, pick 3 random paragraphs from Advanced and verify they don't restate Basic content. Any restatement (same example, same analogy, same sentence structure) = iterate on prompt.

**Step 6: If failures — iterate, else commit validation report**

If validation fails:
- Edit the prompt text (Task 4 or 5) to tighten the rule
- Re-run regen for affected terms
- Re-validate

If validation passes, append a validation note to the plan file:
```bash
echo "## Validation Results (2026-XX-XX)

5/5 terms pass 7-section structure, differentiation matrix 5+/7 on all." \
  >> vault/09-Implementation/plans/2026-04-10-handbook-advanced-redesign.md
git add vault/09-Implementation/plans/2026-04-10-handbook-advanced-redesign.md
git commit -m "docs(plan): Advanced 재설계 검증 완료"
```

---

### Task 8: Plan closure — sprint status update

**Files:**
- Modify: `vault/09-Implementation/plans/ACTIVE_SPRINT.md`

**Step 1: Mark HB-REDESIGN-C as done**

**Step 2: Commit**

```bash
git add vault/09-Implementation/plans/ACTIVE_SPRINT.md
git commit -m "chore: sprint sync — HB-REDESIGN-C done"
```

---

## Success Criteria

- [ ] `ADVANCED_SECTIONS_KO/EN` have exactly 7 entries with new keys
- [ ] Section count warning threshold is 7 for Advanced (both languages)
- [ ] `TYPE_DEPTH_GUIDES` no longer references deleted keys (`1_technical`, `3_howworks`, `6_why`, `8_refs`, `10_when_to_use`, `11_pitfalls`)
- [ ] `GENERATE_ADVANCED_PROMPT` and `GENERATE_ADVANCED_EN_PROMPT` fully rewritten
- [ ] Advanced call receives Basic body as context
- [ ] All 5 sample terms regenerated with 7 Advanced sections
- [ ] Differentiation matrix passes on 5+/7 rows for all 5 terms
- [ ] `ruff check` passes
- [ ] Existing generate tests (4/4) + new `test_advanced_sections.py` pass

## Rollback Plan

If prompt rewrites cause quality degradation:
```bash
git revert <commit-sha-of-task-4>  # Revert KO prompt
git revert <commit-sha-of-task-5>  # Revert EN prompt
```
Structural changes (Task 1-3, 6) should remain — they're backward-compatible with old prompts if the prompts are reverted.

## Out of Scope (explicit)

- Frontend rendering changes for Advanced (already covered by Plan A — body_advanced_ko/en still the same concat column)
- DB schema changes (Advanced uses existing `body_advanced_ko/en` columns)
- EN Advanced prompt field naming — stays `adv_en_*` following existing convention
- Advanced-specific references (removed — moved to unified `references_ko/en` footer)
- Revalidating the 3-pattern rule for `basic_ko_4_impact` — that's Basic only

## Related

- [[2026-04-09-handbook-section-redesign]] — Master redesign spec (§5.3 Advanced, §7 differentiation matrix)
- [[2026-04-10-handbook-basic-en-redesign]] — Plan B (EN Basic prompt, precedes this)
- [[2026-04-10-handbook-save-and-render]] — Plan A (DB + frontend, precedes this)
