# Prompt Remaining Fixes — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 9 remaining prompt issues from re-audit (confidence alignment, depth calibration, hallucination warnings, format specs).

**Architecture:** All changes are prompt text edits in 3 files. No code logic changes. 67 existing tests must pass.

**Tech Stack:** Python string templates, ruff, pytest

---

## File Structure

| File | Changes |
|------|---------|
| `backend/services/agents/prompts_advisor.py` | #1 KO/EN confidence alignment, #7 (skip — too risky) |
| `backend/services/agents/prompts_news_pipeline.py` | #4 focus_items example, #5 max paragraph count, #9 present tense edge case |
| `backend/services/agents/prompts_handbook_types.py` | #2 depth rubric expansion, #3 paper hallucination warning, #6 benchmark fallback, #8 section minimum |

---

## Chunk 1: High Priority (Issues #1, #2, #3)

### Task 1: advisor.py — KO/EN confidence alignment + news_pipeline — format fixes

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py`
- Modify: `backend/services/agents/prompts_news_pipeline.py`

- [ ] **Step 1: Fix #1 — Align KO/EN product mapping confidence**

In `prompts_advisor.py`, find `basic_en_5_where` (~line 686). Current EN version says "If uncertain, write 'may be used in ~'". Change to match the stricter KO standard.

Replace:
```
Only state product-technology mappings confirmed in Reference Materials. Do NOT guess "X uses Y". If uncertain, write "may be used in ~" instead.
```

With:
```
Only state product-technology mappings confirmed in Reference Materials. Do NOT guess "X uses Y". If uncertain, OMIT the example entirely rather than hedging.
```

- [ ] **Step 2: Fix #4 — Add focus_items concrete examples in news pipeline**

In `prompts_news_pipeline.py`, find the focus_items JSON definition (~line 213-214). Replace:

```
  "focus_items": ["1 sentence, 5-12 words: what changed", "1 sentence: why it matters", "1 sentence: what to watch"],
  "focus_items_ko": ["1문장 15-40자: 오늘 무엇이 달라졌는가", "1문장: 지금 왜 중요한가", "1문장: 다음에 무엇을 지켜볼 것인가"],
```

With:
```
  "focus_items": ["OpenAI releases real-time voice API for developers", "Inference costs drop 60%, enabling new use cases", "Watch for Google and Meta's competitive response this month"],
  "focus_items_ko": ["OpenAI, 개발자용 실시간 음성 API 출시", "추론 비용 60% 하락으로 새로운 활용 가능", "이번 달 Google·Meta의 경쟁 대응 주목"],
```

- [ ] **Step 3: Fix #5 — Add max paragraph count per persona**

In `prompts_news_pipeline.py`, find writing rule 7 (~line 193). Replace:
```
7. Each news item's paragraph count follows the persona guide (Expert: 3-4, Learner: 2-3, Beginner: 1-2). Include context for numbers (compare to industry averages or competitors).
```

With:
```
7. Each news item's paragraph count follows the persona guide (Expert: 3-4, Learner: 2-3). Do NOT exceed 4 paragraphs per item. Include context for numbers (compare to industry averages or competitors).
```

- [ ] **Step 4: Fix #9 — Clarify present tense rule**

In `prompts_news_pipeline.py`, find writing rule 8 (~line 194). Replace:
```
8. These news items were collected TODAY — write in present tense for events, do not reference them as past events from weeks ago.
```

With:
```
8. Write in present tense for the news itself ("GPT-5 is released", "Nvidia announces") even if the event happened days ago. Avoid past framing ("Last week...", "A few days ago...").
```

- [ ] **Step 5: Lint + test**

```bash
cd backend && .venv/Scripts/python.exe -m ruff check services/agents/prompts_advisor.py services/agents/prompts_news_pipeline.py
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/agents/prompts_advisor.py backend/services/agents/prompts_news_pipeline.py
git commit -m "fix(prompts): align KO/EN confidence, focus_items examples, max paragraphs, present tense"
```

---

### Task 2: handbook_types.py — Depth rubric, hallucination warnings, benchmark fallback

**Files:**
- Modify: `backend/services/agents/prompts_handbook_types.py`

- [ ] **Step 1: Fix #2 — Expand depth scoring rubric from 3 to 5 tiers**

In `prompts_handbook_types.py`, find the scoring examples section in `HANDBOOK_QUALITY_CHECK_PROMPT`. Replace the current 3-point depth examples:
```
- depth 22 (excellent): Production code with error handling, benchmark comparison with real numbers
- depth 12 (mediocre): Blog-post explanations, hello-world code
- depth 5 (poor): Wikipedia-level definitions only
```

With 5-tier rubric:
```
- depth 23-25: Production code + architecture diagrams + math proofs + benchmark comparisons with cited sources
- depth 18-22: Production code + detailed explanations + some benchmarks
- depth 13-17: Working code + adequate explanations but lacking depth/benchmarks
- depth 8-12: Partial code or simplified explanations, blog-post level
- depth 0-7: Conceptual only, no implementation examples, Wikipedia-level
```

Apply same 5-tier pattern to accuracy, uniqueness, completeness:
```
- accuracy 23-25: All claims cite reference materials, verifiable numbers, no fabricated mappings
- accuracy 18-22: Most claims sourced, minor uncited statements
- accuracy 13-17: Mix of sourced and unsourced claims
- accuracy 8-12: Vague "widely used" statements, some fabricated product claims
- accuracy 0-7: Fabricated URLs, wrong product-technology mappings

- uniqueness 23-25: Zero overlap with basic content, advanced-only insights and code
- uniqueness 18-22: Minimal overlap, mostly new content
- uniqueness 13-17: Some repeated analogies or examples from basic
- uniqueness 8-12: Significant overlap, rephrased basic content
- uniqueness 0-7: Essentially the same content as basic

- completeness 23-25: All 9 sections substantive (min 200 chars each), no thin sections
- completeness 18-22: 8-9 sections substantive, 1 thin
- completeness 13-17: 6-7 sections substantive, 2-3 thin
- completeness 8-12: 4-5 sections substantive, rest thin or empty
- completeness 0-7: Multiple empty sections, incomplete coverage
```

- [ ] **Step 2: Fix #3 — Add paper/arXiv hallucination warning**

In `prompts_handbook_types.py`, find `algorithm_model` in TYPE_DEPTH_GUIDES (~line 56). After the last bullet, add:
```
- CRITICAL: Do NOT fabricate paper titles, arXiv IDs, author names, or publication venues. Only cite papers from the Reference Materials provided. If no paper reference is available, write "See official documentation" instead.
```

Add similar warning to `concept_theory` guide (~line 80):
```
- CRITICAL: Do NOT fabricate paper citations or textbook references. Only cite sources from Reference Materials. If unavailable, omit the citation.
```

- [ ] **Step 3: Fix #6 — Benchmark data fallback when unavailable**

In `prompts_handbook_types.py`, find `algorithm_model` guide's `adv_*_5_practical` line (~line 72). Change:
```
- adv_*_5_practical: Include benchmark comparisons (accuracy, latency, memory) with specific numbers from reference materials.
```

To:
```
- adv_*_5_practical: Include benchmark comparisons (accuracy, latency, memory) with specific numbers from reference materials. If no benchmarks are available in references, state "Public benchmarks not yet available" rather than inventing numbers.
```

Apply same pattern to `metric_measure` guide (~line 100) and `product_brand` guide (~line 88).

- [ ] **Step 4: Fix #8 — Add section minimum char counts**

In `prompts_handbook_types.py`, at the end of `get_type_depth_guide()` function, add a universal rule that applies to all types. Change:
```python
def get_type_depth_guide(term_type: str) -> str:
    """Return type-specific depth instructions for advanced prompt injection."""
    return TYPE_DEPTH_GUIDES.get(term_type, TYPE_DEPTH_GUIDES["concept_theory"])
```

To:
```python
_SECTION_MINIMUM = """
## Section Quality Minimums
- Each advanced section: minimum 200 characters of substantive content
- adv_*_1_technical: minimum 400 characters (most important section)
- adv_*_4_code: minimum 15 lines of substantial code (if code applies to this type)
- Empty or placeholder sections ("TBD", "N/A") are NOT acceptable — omit the section key entirely if not applicable"""


def get_type_depth_guide(term_type: str) -> str:
    """Return type-specific depth instructions for advanced prompt injection."""
    guide = TYPE_DEPTH_GUIDES.get(term_type, TYPE_DEPTH_GUIDES["concept_theory"])
    return f"{guide}\n\n{_SECTION_MINIMUM}"
```

- [ ] **Step 5: Lint + test**

```bash
cd backend && .venv/Scripts/python.exe -m ruff check services/agents/prompts_handbook_types.py
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit + push all**

```bash
git add backend/services/agents/prompts_handbook_types.py
git commit -m "fix(prompts): depth rubric 5-tier, paper hallucination warning, benchmark fallback, section minimums"
git push
```

---

## Verification

1. `ruff check .` — 0 errors
2. `pytest tests/` — 67 passed
3. Manual: Generate a handbook term → check quality_check breakdown scores align with new rubric
4. Manual: Check advanced content doesn't fabricate arXiv IDs
5. Manual: Check focus_items format matches new examples
