# Handbook Writer Skeleton Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task-by-task.

**Goal:** Replace rule-based prompt patterns ("write Relations with these tags") with **structured-output skeleton patterns** (JSON schema enforcement) for the 2 sub-scores that judge evidence repeatedly flags as "format/specifics missing": `format_compliance` and `concrete_specifics`. Plus bump max_completion_tokens to fix EN truncation.

**Architecture:** 3 independent tasks. Task 1 = Relations schema. Task 2 = Specs schema. Task 3 = token budget. All orthogonal — can execute and verify independently. Each task touches `prompts_advisor.py` (writer prompts) + `advisor.py` (assembly + token budget).

**Tech Stack:** Python 3.11+, OpenAI SDK 2.x, Pydantic for schema, pytest.

---

## Background — Diagnosed 2026-04-24 from VIT/RoPE smoke evidence

VIT advanced score 68 (C), RoPE advanced 45 (D). Judge evidence cites these recurring problems:

| Problem | Sub-score impact | Root cause | Pattern fix |
|---|---|---|---|
| "no Relations section using explicit `(prerequisite)/(alternative)/(extension)` tags" | format_compliance: 4/10 | Prompt has rules but emits string field — LLM produces prose | Structured Output (Pydantic) |
| "no parameter counts, FLOPs, exact latency numbers" | concrete_specifics: 4/10 | Prompt asks "include if available" — LLM silently omits | Structured Output (Pydantic) + Show-Don't-Tell (few-shot) |
| "EN code block truncated mid-function" | required_sections_present: 7/10 | max_completion_tokens=16000 × 3 = 48000 — reasoning_effort=high eats budget | max_tokens bump |

These match the [Pattern 1: Structured Output with Pydantic] and [Pattern 4: Show, Don't Tell] from prompt-engineering-patterns. Current prompts already follow [Pattern 6: Role-Based] well — they have rich rules and good examples — but lack **schema enforcement**.

**Estimated uplift if all 3 tasks ship:** Advanced score average +7-15 points (D/C → B/A territory).

### Files to touch
- `backend/services/agents/prompts_advisor.py` — `GENERATE_ADVANCED_PROMPT` (KO) and `GENERATE_ADVANCED_EN_PROMPT` (EN), specifically the schema/output sections around lines 1841-1853 and the EN equivalent
- `backend/services/agents/advisor.py` — `_assemble_markdown` (line 1995), `ADVANCED_SECTIONS_KO/EN` (lines 1968-1992), generation call max_tokens (lines ~2204, 2380, 2393, 2456, etc.)
- `backend/tests/test_handbook_writer_skeleton.py` (NEW) — assembly tests for structured fields

### What stays unchanged
- The Relations RULES (prerequisite/alternative/extension definitions, common misclassifications, domain examples) — these stay verbatim in the prompt. We only change the OUTPUT schema, not the rule taxonomy.
- BASIC prompts — judge evidence shows basic scores are fine (B/A range). Skip basic for this batch.
- All other writer sections (mechanism, formulas, code, pitfalls, tradeoffs, comm) — leave alone.

---

## Task Order Rationale

1. **Task 3 first (max_tokens bump)** — smallest change, cheapest test, biggest direct mitigation of EN truncation. Can be verified by single smoke run.
2. **Task 1 (Relations structured)** — single highest-leverage sub-score uplift (format_compliance 4→9-10). Mechanical schema change.
3. **Task 2 (Specs structured)** — highest cognitive lift, requires few-shot example design. Last to verify cumulative gain.

After all 3 tasks: smoke regen on RoPE + VIT, compare sub-score deltas vs the post-hotfix baseline (RoPE 45 advanced, VIT 68 advanced).

---

## Task 1: Bump `max_tokens` for handbook generation calls (24000 → reasoning headroom)

**Severity: First — smallest change, fixes EN truncation directly.**

**Why before others:** Tasks 2 and 3 add MORE structured content to the output. Without enough token budget, structured fields exacerbate truncation. Bumping budget first is the foundation.

**Files:**
- Modify: `backend/services/agents/advisor.py` — 8 generation call sites (Calls 1-4 + 1b-4b)

### Step 1: Identify call sites

Grep for the 8 generation `max_tokens=16000`:

```bash
cd backend && grep -n "max_tokens=16000" services/agents/advisor.py | head -10
```

Expected: 8 hits, all in `_run_generate_term`, identifiable by surrounding `prompt_cache_key="hb-generate-*"` or `hb-regen-*`.

### Step 2: Bump each to 24000

For each of the 8 sites, change:
```python
max_tokens=16000,
```
to:
```python
max_tokens=24000,
```

Rationale: `client.py:_apply_gpt5_compat` triples for gpt-5 reasoning overhead, so effective `max_completion_tokens` becomes 72000 (was 48000). With reasoning_effort="high" consuming ~10000-15000 reasoning tokens, that leaves 50000+ for output. EN advanced bodies are typically 8000-15000 chars (~3000-5000 tokens) — 50000 is generous headroom.

### Step 3: Cost impact assessment

Per-call cost increase: zero baseline (you only pay for tokens actually emitted). Risk: if writer fills budget with verbose content, output cost rises. Mitigation: writer prompts already have structural section limits (e.g., "4-6 entries"). Empirically expect <10% cost rise.

### Step 4: Syntax check + smoke

```bash
python -c "import ast; ast.parse(open('backend/services/agents/advisor.py', encoding='utf-8').read()); print('SYNTAX_OK')"
```

### Step 5: Stage + commit

```bash
git add backend/services/agents/advisor.py
git diff --cached --stat
```

Expected: `1 file changed, 8 insertions(+), 8 deletions(-)`.

```bash
git commit -m "fix(handbook): bump generation max_tokens 16000→24000 to clear reasoning_effort=high overhead"
```

### Step 6: Smoke verify

After Tasks 1-3 all done, single smoke regen will verify EN code blocks no longer truncated.

---

## Task 2: Structured Relations field (format_compliance fix)

**Severity: Highest single-sub-score uplift. Mechanical schema enforcement replaces fragile string format.**

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py` — `GENERATE_ADVANCED_PROMPT` and `GENERATE_ADVANCED_EN_PROMPT`, specifically the `adv_*_7_related` section spec + Output JSON Structure
- Modify: `backend/services/agents/advisor.py` — `_assemble_markdown` (line 1995-2002), to render structured Relations
- Add: `backend/tests/test_handbook_writer_skeleton.py` (new) — assembly tests

### Schema design

Replace `adv_*_7_related` string with structured object:

```json
{
  "prerequisites": [
    {"term": "Seq2Seq", "relationship": "the fixed-vector bottleneck attention removes — understanding it makes attention's motivation concrete"}
  ],
  "alternatives": [
    {"term": "Mamba", "relationship": "state space model bringing cost from O(n²) to O(n) — relevant contemporary alternative for long-context"}
  ],
  "extensions": [
    {"term": "Mixture of Experts", "relationship": "extends Transformer FFN into an expert pool — natural evolution on attention-based architectures"}
  ]
}
```

Total entries across all 3 categories = 4-6 (matches current "4-6 entries" rule).

### Step 1: Write assembly tests (TDD)

Create `backend/tests/test_handbook_writer_skeleton.py`:

```python
"""Tests for structured Relations field rendering in _assemble_markdown."""
from services.agents.advisor import _assemble_markdown, ADVANCED_SECTIONS_KO, ADVANCED_SECTIONS_EN


def test_renders_structured_relations_ko():
    raw = {
        "adv_ko_1_mechanism": "Mechanism content",
        "adv_ko_7_related": {
            "prerequisites": [
                {"term": "Self-Attention", "relationship": "Q·K^T 내적이 RoPE의 전제"}
            ],
            "alternatives": [
                {"term": "Sinusoidal PE", "relationship": "절대 위치, 일반화 약함"}
            ],
            "extensions": [
                {"term": "ALiBi", "relationship": "거리 페널티 직접 부여"}
            ],
        },
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    # Renders structured object as canonical bullet format with tags BEFORE term
    assert "- (prerequisite) **Self-Attention** — Q·K^T 내적이 RoPE의 전제" in md
    assert "- (alternative) **Sinusoidal PE** — 절대 위치, 일반화 약함" in md
    assert "- (extension) **ALiBi** — 거리 페널티 직접 부여" in md
    # Header preserved
    assert "## 선행·대안·확장 개념" in md


def test_renders_structured_relations_en():
    raw = {
        "adv_en_7_related": {
            "prerequisites": [{"term": "Seq2Seq", "relationship": "fixed-vector bottleneck"}],
            "alternatives": [{"term": "Mamba", "relationship": "O(n) cost"}],
            "extensions": [{"term": "MoE", "relationship": "expert pool"}],
        },
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_EN)
    assert "- (prerequisite) **Seq2Seq** — fixed-vector bottleneck" in md
    assert "- (alternative) **Mamba** — O(n) cost" in md
    assert "- (extension) **MoE** — expert pool" in md


def test_renders_string_relations_backward_compat():
    """Old format (markdown blob) still renders verbatim."""
    raw = {
        "adv_ko_7_related": "- (prerequisite) **Foo** — manually-written prose",
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "- (prerequisite) **Foo** — manually-written prose" in md


def test_handles_empty_relations_gracefully():
    raw = {"adv_ko_7_related": {"prerequisites": [], "alternatives": [], "extensions": []}}
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    # Empty structured field → section omitted (consistent with empty string behavior)
    assert "## 선행·대안·확장 개념" not in md


def test_handles_partial_relations():
    raw = {
        "adv_ko_7_related": {
            "prerequisites": [{"term": "X", "relationship": "Y"}],
            # alternatives + extensions missing keys entirely
        },
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "- (prerequisite) **X** — Y" in md
```

Run:
```bash
cd backend && pytest tests/test_handbook_writer_skeleton.py -v
```
Expected: all FAIL (assembly doesn't yet handle structured field).

### Step 2: Update `_assemble_markdown` to handle dict input

In `backend/services/agents/advisor.py` around line 1995, replace:

```python
def _assemble_markdown(data: dict, sections: list[tuple[str, str]]) -> str:
    """Assemble section-per-key JSON data into markdown with H2 headers."""
    parts = []
    for key, header in sections:
        content = data.get(key, "").strip()
        if content:
            parts.append(f"{header}\n{content}")
    return "\n\n".join(parts)
```

with:

```python
def _render_structured_relations(rel: dict) -> str:
    """Render structured Relations dict as canonical (tag) **term** — relationship bullets.

    Tag-first order: `(prerequisite) **Term** — relationship` (matches the writer
    prompt's rule that the parenthesized tag precedes the bolded term).
    """
    bullets: list[str] = []
    for category, tag in (("prerequisites", "prerequisite"), ("alternatives", "alternative"), ("extensions", "extension")):
        for entry in rel.get(category, []) or []:
            term = (entry.get("term") or "").strip()
            relationship = (entry.get("relationship") or "").strip()
            if term and relationship:
                bullets.append(f"- ({tag}) **{term}** — {relationship}")
    return "\n".join(bullets)


def _assemble_markdown(data: dict, sections: list[tuple[str, str]]) -> str:
    """Assemble section-per-key JSON data into markdown with H2 headers.

    Section value can be a string (legacy) or a dict (structured fields like
    `adv_*_7_related`). Dicts are rendered through their type-specific renderer;
    strings pass through verbatim. Empty values omit the section entirely.
    """
    parts: list[str] = []
    for key, header in sections:
        raw_value = data.get(key)
        if isinstance(raw_value, dict):
            # Currently only Relations uses structured form; future structured
            # fields can dispatch by key suffix here.
            if key.endswith("_7_related"):
                content = _render_structured_relations(raw_value).strip()
            else:
                content = ""  # unknown structured field — drop rather than serialize raw dict
        else:
            content = (raw_value or "").strip() if isinstance(raw_value, str) else ""
        if content:
            parts.append(f"{header}\n{content}")
    return "\n\n".join(parts)
```

### Step 3: Run tests, verify pass

```bash
cd backend && pytest tests/test_handbook_writer_skeleton.py -v
```
Expected: all 5 PASS.

### Step 4: Update writer prompts — `GENERATE_ADVANCED_PROMPT` (KO)

In `backend/services/agents/prompts_advisor.py`, locate the Output JSON Structure block in `GENERATE_ADVANCED_PROMPT`. Find the line:

```json
  "adv_ko_7_related": "- (prerequisite|alternative|extension) **Term** — relationship"
```

Replace with:

```json
  "adv_ko_7_related": {
    "prerequisites": [
      {"term": "...", "relationship": "기술적 의존 관계 + 왜 먼저 알아야 하는지"}
    ],
    "alternatives": [
      {"term": "...", "relationship": "동일 문제를 다른 방식으로 풀이 + 왜 그 방식이 의미 있는지"}
    ],
    "extensions": [
      {"term": "...", "relationship": "이 용어 위에 쌓이는 변형/확장 + 어떤 한계를 푸는지"}
    ]
  }
```

Also locate the section spec for `adv_ko_7_related` (the rules block, not the schema). Update its Format hint from:

> Format: `- (prerequisite|alternative|extension) **Term** — relationship + why it matters`

to:

> **Output as structured JSON object** (not prose). Each entry has `term` (string) and `relationship` (string explaining the technical link + why it matters from this angle). The renderer auto-formats as `- (prerequisite) **Term** — relationship`.
>
> Total entries across all three categories: 4-6.

Keep the rich rules block (categorization rules, common misclassifications, domain examples) unchanged. Those rules apply to populating the new structured fields exactly the same way.

### Step 5: Update writer prompts — `GENERATE_ADVANCED_EN_PROMPT` (EN)

Same edit pattern in the EN prompt. Schema becomes:

```json
  "adv_en_7_related": {
    "prerequisites": [
      {"term": "...", "relationship": "technical dependency + why it must be understood first"}
    ],
    "alternatives": [
      {"term": "...", "relationship": "currently-competing approach + why it's the relevant alternative"}
    ],
    "extensions": [
      {"term": "...", "relationship": "what builds on top + what limit it pushes past"}
    ]
  }
```

Section spec hint: same as KO but in English.

### Step 6: Syntax check

```bash
python -c "import ast; ast.parse(open('backend/services/agents/prompts_advisor.py', encoding='utf-8').read()); ast.parse(open('backend/services/agents/advisor.py', encoding='utf-8').read()); print('SYNTAX_OK')"
```

### Step 7: Stage + commit

```bash
git add backend/services/agents/advisor.py backend/services/agents/prompts_advisor.py backend/tests/test_handbook_writer_skeleton.py
git diff --cached --stat
```
Expected: `3 files changed, ~80-100 insertions, ~10-15 deletions`.

```bash
git commit -m "feat(handbook): structured Relations schema replaces prose blob (format_compliance fix)"
```

### Step 8: Smoke verify (after Task 3 too)

Single regen — confirm Relations section renders with all `(prerequisite) / (alternative) / (extension)` tags, judge format_compliance ≥ 7.

---

## Task 3: Structured Specs field (concrete_specifics fix)

**Severity: Second-highest sub-score uplift. Forces writer to be explicit about missing data instead of silently omitting.**

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py` — both advanced prompts
- Modify: `backend/services/agents/advisor.py` — `ADVANCED_SECTIONS_KO/EN`, `_assemble_markdown` dispatch, render helper
- Modify: `backend/tests/test_handbook_writer_skeleton.py` — add specs assembly tests

### Schema design

Add new field `adv_*_specs` (placed in section ordering AFTER mechanism, BEFORE formulas):

```json
{
  "parameters": "175B" | "not_published",
  "context_window": "2048" | "not_published",
  "training_data": "300B tokens (Common Crawl + Books)" | "not_published",
  "compute_cost": "3640 PF-days" | "not_published",
  "benchmarks": [
    {"name": "Science QA", "score": "92.53%", "context": "LLaVA paper Table 5, single-shot"}
  ],
  "latency_throughput": "..." | "not_published"
}
```

Rules embedded in prompt:
- Each numeric field: either a specific value with unit, OR the literal string `"not_published"` (must be explicit — empty string or omission forbidden).
- `benchmarks` array: 0+ entries, each with `name`, `score`, `context`. If paper publishes none, return `[]` and ALSO mention "the original paper does not report benchmark numbers" in `adv_*_1_mechanism`.

### Step 1: Add new section to ordering

In `advisor.py` `ADVANCED_SECTIONS_KO`, insert AFTER `1_mechanism` BEFORE `2_formulas`:

```python
ADVANCED_SECTIONS_KO = [
    ("adv_ko_1_mechanism", "## 기술적 정의와 동작 원리"),
    ("adv_ko_specs",       "## 핵심 스펙 (parameters, FLOPs, 벤치마크)"),  # NEW
    ("adv_ko_2_formulas",  "## 핵심 수식·아키텍처·도표"),
    ...
]
```

Same insertion in `ADVANCED_SECTIONS_EN`:

```python
ADVANCED_SECTIONS_EN = [
    ("adv_en_1_mechanism", "## Technical Definition & How It Works"),
    ("adv_en_specs",       "## Key Specifications (parameters, FLOPs, benchmarks)"),  # NEW
    ("adv_en_2_formulas",  "## Formulas, Architecture, and Diagrams"),
    ...
]
```

### Step 2: Add render helper + dispatch

In `_assemble_markdown`, add dispatch for `_specs` keys (similar to Relations dispatch):

```python
def _render_structured_specs(specs: dict) -> str:
    """Render structured Specs dict as a definition list / bullet block.

    Fields with literal "not_published" are kept and rendered as
    "*(not published)*" so the explicit gap is visible to readers and judge.
    Empty benchmarks list renders as "(none reported in original paper)".
    """
    lines: list[str] = []
    field_order = [
        ("parameters", "Parameters"),
        ("context_window", "Context window"),
        ("training_data", "Training data"),
        ("compute_cost", "Compute cost"),
        ("latency_throughput", "Latency / throughput"),
    ]
    for key, label in field_order:
        value = (specs.get(key) or "").strip() if isinstance(specs.get(key), str) else ""
        if value == "not_published":
            lines.append(f"- **{label}**: *(not published)*")
        elif value:
            lines.append(f"- **{label}**: {value}")
    benchmarks = specs.get("benchmarks") or []
    if benchmarks:
        lines.append("- **Benchmarks**:")
        for b in benchmarks:
            name = (b.get("name") or "").strip()
            score = (b.get("score") or "").strip()
            ctx = (b.get("context") or "").strip()
            if name and score:
                ctx_part = f" — {ctx}" if ctx else ""
                lines.append(f"  - {name}: {score}{ctx_part}")
    elif lines:
        # Some fields populated but no benchmarks — still note explicitly
        lines.append("- **Benchmarks**: *(none reported in original paper)*")
    return "\n".join(lines)
```

In `_assemble_markdown`, extend the dict dispatch:

```python
if isinstance(raw_value, dict):
    if key.endswith("_7_related"):
        content = _render_structured_relations(raw_value).strip()
    elif key.endswith("_specs"):
        content = _render_structured_specs(raw_value).strip()
    else:
        content = ""
```

### Step 3: Add specs tests to test file

```python
def test_renders_structured_specs_with_values_and_not_published():
    raw = {
        "adv_ko_specs": {
            "parameters": "175B",
            "context_window": "not_published",
            "training_data": "300B tokens",
            "compute_cost": "not_published",
            "latency_throughput": "not_published",
            "benchmarks": [
                {"name": "MMLU", "score": "65.3%", "context": "5-shot, original paper Table 4"},
            ],
        },
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "## 핵심 스펙" in md
    assert "- **Parameters**: 175B" in md
    assert "- **Context window**: *(not published)*" in md
    assert "- **Training data**: 300B tokens" in md
    assert "- MMLU: 65.3% — 5-shot, original paper Table 4" in md


def test_renders_specs_with_no_benchmarks():
    raw = {
        "adv_en_specs": {
            "parameters": "8B",
            "benchmarks": [],
        },
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_EN)
    assert "Parameters**: 8B" in md
    assert "*(none reported in original paper)*" in md


def test_specs_section_omitted_when_all_fields_empty():
    raw = {"adv_ko_specs": {}}
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "## 핵심 스펙" not in md
```

### Step 4: Update writer prompts — schema + section spec for `adv_*_specs`

In `GENERATE_ADVANCED_PROMPT` (KO), Output JSON Structure section, ADD between `adv_ko_1_mechanism` and `adv_ko_2_formulas`:

```json
  "adv_ko_specs": {
    "parameters": "구체 수치(예: '175B') 또는 'not_published'",
    "context_window": "구체 수치(예: '2048 tokens') 또는 'not_published'",
    "training_data": "구체 수치(예: '300B tokens (Common Crawl + Books)') 또는 'not_published'",
    "compute_cost": "구체 수치(예: '3640 PF-days') 또는 'not_published'",
    "latency_throughput": "구체 수치(예: '50ms/token, 20 tok/s on A100') 또는 'not_published'",
    "benchmarks": [
      {"name": "벤치마크 이름", "score": "구체 점수(단위 포함)", "context": "어떤 setup인지 (예: '5-shot, original paper Table 4')"}
    ]
  },
```

ADD a section spec block before `adv_ko_2_formulas` rules:

```
- **adv_ko_specs** (Key Specifications, structured object):
  Concrete numerical specs that anchor the term in measurable reality. **Each numeric
  field MUST be either a specific value with units OR the literal string "not_published".**
  Empty strings, "N/A", or omission are forbidden — the explicit "not_published" signals
  to the reader that you checked and the original paper/spec does not publish it.

  Show, don't tell:
  ✅ GOOD: "parameters": "175B" (decoder-only, 96 transformer layers)
  ✅ GOOD: "parameters": "not_published" (the original Anthropic post does not state Claude 3.5 Sonnet's parameter count)
  ❌ BAD:  "parameters": "" (empty — never use this)
  ❌ BAD:  "parameters": "large" (vague — give a number or 'not_published')
  ❌ BAD:  field omitted entirely (always include the key, with 'not_published' if needed)

  benchmarks: array of 0+ entries from the term's paper or official spec. If the paper
  reports none, return [] and mention this explicitly in adv_ko_1_mechanism.

  This section is rendered as a bullet list immediately after the mechanism section so
  the judge and reader see concrete numbers up front.
```

Same translation pattern in `GENERATE_ADVANCED_EN_PROMPT`.

### Step 5: Run tests + syntax check

```bash
cd backend && pytest tests/test_handbook_writer_skeleton.py -v
python -c "import ast; ast.parse(open('backend/services/agents/prompts_advisor.py', encoding='utf-8').read()); ast.parse(open('backend/services/agents/advisor.py', encoding='utf-8').read()); print('SYNTAX_OK')"
```
Expected: 8 tests pass (5 from Task 2 + 3 new specs tests).

### Step 6: Stage + commit

```bash
git add backend/services/agents/advisor.py backend/services/agents/prompts_advisor.py backend/tests/test_handbook_writer_skeleton.py
git diff --cached --stat
```

Expected: 3 files changed, ~80-120 insertions, minimal deletions.

```bash
git commit -m "feat(handbook): structured Specs schema with not_published sentinel (concrete_specifics fix)"
```

---

## Verification Plan (after all 3 tasks shipped)

1. **Smoke regen RoPE** — compare advanced sub-scores vs prior post-hotfix run (acc 20, uniq 11, tech_depth 7, struct 11):
   - Expect format_compliance: 4 → 9-10 (Relations now structured)
   - Expect concrete_specifics: 0 → 4-7 ("not_published" or actual numbers visible)
   - Expect required_sections_present: 7 → 9-10 (no truncation)
   - Total advanced expected: 45 → 60+ (D → C/B)

2. **Smoke regen VIT** — compare advanced sub-scores vs post-hotfix VIT (acc 14, uniq 17, tech_depth 24, struct 11):
   - Expect format_compliance: 4 → 9-10
   - Expect concrete_specifics: 4 → 7-9 (LLaVA reports parameters/training data, writer should now surface them)
   - Total advanced expected: 68 → 78+ (C → B/A)

3. **Backward-compat check** — confirm OLD pre-published terms (with prose `_7_related` strings) still render correctly via the string passthrough branch in `_assemble_markdown`. Pull 1 random old term from DB and inspect rendered HTML.

---

## Out of Scope (future plans)

1. **Basic prompts restructure** — basic scores already at A/B; not worth the prompt churn.
2. **Migration of historical handbook_terms** — old terms keep prose Relations; only NEW regenerations get structured. Acceptable since `_assemble_markdown` is backward-compat.
3. **Pydantic enforcement at parse time** — Adding a `Pydantic schema validator` to `parse_ai_json` for these new fields. Currently the writer's `parse_ai_json` does not validate against a schema — if LLM emits malformed dict, it just renders empty. A future plan can add strict validation + retry on schema failure.
4. **Per-term-type field gating** — Some term_types (e.g., `concept`, `phenomenon`) don't have meaningful parameter counts. Future: skip Specs section for those types entirely instead of rendering all "not_published".
5. **Judge sub-score calibration** — Judge's conservatism on factual_correctness ("verify can't") and non_redundancy ("cross-section context-sharing") is a separate plan to calibrate.

---

## Success Criteria (all 3 tasks shipped when these hold)

- [ ] `grep -n "max_tokens=16000" backend/services/agents/advisor.py | wc -l` returns 0
- [ ] `grep -n "max_tokens=24000" backend/services/agents/advisor.py | wc -l` returns 8
- [ ] `pytest backend/tests/test_handbook_writer_skeleton.py -v` → 8 passing
- [ ] `_render_structured_relations` and `_render_structured_specs` exist in `advisor.py`
- [ ] Smoke regen of RoPE shows format_compliance ≥ 7 in handbook_quality_scores
- [ ] Smoke regen of VIT shows total advanced ≥ 75
- [ ] No regression on basic scores

---

## Related Plans

- 2026-04-23-handbook-gpt5-and-writer-qc-mirror.md — shipped GPT-5 efficiency + writer-QC mirror
- 2026-04-24-handbook-judge-rubric-contract-fixes.md — shipped bilingual contract + truncation hotfix
- 2026-04-23-handbook-seed-800.md — Seed 800 batch (this plan unblocks)

---

## Skill Patterns Applied

- **Pattern 1: Structured Output with Pydantic** — Relations + Specs schemas
- **Pattern 4: Show, Don't Tell** — `not_published` examples in spec, JSON skeleton in schema
- **Pattern 6: Role-Based System Prompts** — preserved (we don't touch the role/rules layer, only the output schema layer)
