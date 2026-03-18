# Prompt Audit Fixes — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 52 prompt issues across 3 priority levels (P0 critical → P1 high → P2 medium) to improve reliability, consistency, and token efficiency.

**Architecture:** All changes are in 3 prompt files. No new files. Each priority level is one task with one commit. Tests validate no regressions (67 existing tests must pass).

**Tech Stack:** Python string templates, ruff linter, pytest

**Spec Reference:** `vault/09-Implementation/plans/2026-03-18-prompt-audit-fixes.md`

---

## File Structure

All modifications — no new files:

| File | Responsibility | Changes |
|------|---------------|---------|
| `backend/services/agents/prompts_advisor.py` | Handbook + editor prompts | P0: C1, C3. P1: H2, H3. P2: M1-M3, M5 |
| `backend/services/agents/prompts_news_pipeline.py` | News digest prompts | P0: C2. P1: H1. P2: M1, M3, M4 |
| `backend/services/agents/prompts_handbook_types.py` | Type classification + quality | P1: H3, H4. P2: M5 |

---

## Chunk 1: P0 Critical Fixes

### Task 1: P0 — URL hallucination, citation mapping, factual error prevention

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py`
- Modify: `backend/services/agents/prompts_news_pipeline.py`

- [ ] **Step 1: Fix C1 — URL hallucination prevention in handbook prompts**

In `prompts_advisor.py`, find the refs section descriptions for KO advanced (~line 770) and EN advanced (~line 851). After each "실제로 존재하는 URL만 포함" / "Only include URLs you are confident exist", append:

```
Do NOT fabricate URLs. If you cannot verify a URL exists from the reference materials provided, OMIT it entirely. Prefer URLs from the Reference Materials section above.
```

- [ ] **Step 2: Fix C2 — Citation-source mapping in news prompts**

In `prompts_news_pipeline.py`, update the Perplexity-style citation rule (appears 2 times, ~line 120 and ~line 187). Change from:

```
1. Cite sources Perplexity-style: place small linked numbers at the end of the paragraph, like "...문장 끝. [1](URL1) [2](URL2)". Do NOT write "자세한 내용은 ~에서 확인하세요" or "Read more at ~". Just the numbered links, nothing else. This applies to BOTH English AND Korean content.
```

To:

```
1. Cite sources Perplexity-style at the end of each paragraph: "...문장 끝. [1](URL1) [2](URL2)". Every [N] MUST use a real URL from the news items provided above — never fabricate a citation. Do NOT write "자세한 내용은 ~에서 확인하세요" or "Read more at ~". This applies to BOTH English AND Korean content.
```

- [ ] **Step 3: Fix C3 — Product-technology factual error prevention in handbook prompts**

In `prompts_advisor.py`, find `basic_ko_5_where` section description (~line 598). After "확실한 사례만 작성 — 불확실하면 쓰지 마", append:

```
 제품-기술 매핑은 Reference Materials에서 확인된 것만 사용. 추측으로 "X가 Y를 사용한다"고 쓰지 마. 불확실하면 "~에 활용될 수 있다" 표현 사용.
```

Find the equivalent EN section `basic_en_5_where` (~line 695) and append:

```
 Only state product-technology mappings confirmed in Reference Materials. Do NOT guess "X uses Y". If uncertain, write "may be used in ~" instead.
```

- [ ] **Step 4: Lint + test**

```bash
cd backend && .venv/Scripts/python.exe -m ruff check services/agents/prompts_advisor.py services/agents/prompts_news_pipeline.py
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```
Expected: All checks passed, 67 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/agents/prompts_advisor.py backend/services/agents/prompts_news_pipeline.py
git commit -m "fix(prompts): P0 — URL hallucination guard, citation mapping, factual error prevention"
```

---

## Chunk 2: P1 High Priority Fixes

### Task 2: P1 — Token efficiency, few-shot examples, score definitions, type disambiguation

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py`
- Modify: `backend/services/agents/prompts_news_pipeline.py`
- Modify: `backend/services/agents/prompts_handbook_types.py`

- [ ] **Step 1: Fix H1 — Extract repeated blocks as constants in prompts_news_pipeline.py**

At the top of `prompts_news_pipeline.py` (after imports), add:

```python
_HANDBOOK_LINK_SECTION = """
## Handbook Linking
- Technical/business terms should be linked to Handbook in the BODY TEXT where they first appear — readers learn in context, not in a separate section
- Available handbook terms: {handbook_slugs}
- Link format: [Term Display Name](/handbook/slug/)
- Only link terms that appear naturally in context. Do not force links.
"""
```

Replace the 2 duplicate handbook linking blocks (~line 102-109 and ~line 166-173) with:

```python
handbook_section = _HANDBOOK_LINK_SECTION.format(handbook_slugs=", ".join(handbook_slugs[:200])) if handbook_slugs else ""
```

- [ ] **Step 2: Fix H2 — Add few-shot examples to quality check prompt in prompts_handbook_types.py**

In `HANDBOOK_QUALITY_CHECK_PROMPT`, after the breakdown definition, before the Output JSON, add:

```
## Scoring Examples

### Score 85+ (Excellent)
- depth 22: Production-grade code with error handling, benchmark comparison with numbers
- accuracy 23: All claims cite reference materials, no fabricated product-technology mappings
- uniqueness 22: Zero overlap with basic content, advanced-only concepts
- completeness 21: All 9 sections substantive (min 200 chars each)

### Score 50-60 (Needs Work)
- depth 12: Blog-post level explanations, hello-world code examples
- accuracy 15: Some claims without sources, vague "widely used" statements
- uniqueness 13: Repeats analogies/examples from basic section
- completeness 10: 2-3 sections are thin (under 100 chars)

### Score 30 (Poor)
- depth 5: Wikipedia-level definitions only
- accuracy 10: Fabricated URLs, wrong product-technology mappings
- uniqueness 10: Essentially rephrased basic content
- completeness 5: Multiple empty sections
```

- [ ] **Step 3: Fix H2 — Add few-shot examples to self-critique prompt**

In `SELF_CRITIQUE_PROMPT`, after "If score >= 75, set needs_improvement to false", add:

```
## Examples

### Pass (score=82)
{{"needs_improvement": false, "weak_sections": [], "improvements": [], "score": 82}}

### Fail (score=55)
{{"needs_improvement": true, "weak_sections": ["adv_ko_4_code", "adv_ko_5_practical"], "improvements": [{{"section": "adv_ko_4_code", "issue": "Only 5 lines, no error handling", "suggestion": "Add production example with type hints, try/except, real library usage (15+ lines)"}}, {{"section": "adv_ko_5_practical", "issue": "No benchmark numbers", "suggestion": "Add specific performance comparison: latency, memory, accuracy vs alternatives"}}], "score": 55}}
```

- [ ] **Step 4: Fix H3 — Define score interpretation in quality check**

In `HANDBOOK_QUALITY_CHECK_PROMPT`, after the "Universal Criteria" section, add:

```
## Score Interpretation
- score = depth + accuracy + uniqueness + completeness (each 0-25, sum = 0-100)
- 80+: Senior-engineer reference quality. Ready for publication.
- 60-79: Acceptable with minor improvements. Review recommended.
- 40-59: Blog-post level. Needs significant depth improvement.
- <40: Insufficient. Major revision or restart needed.
```

- [ ] **Step 5: Fix H4 — Type classification disambiguation in prompts_handbook_types.py**

In `CLASSIFY_TERM_PROMPT`, after the 10 type definitions and before "## Output", add:

```
## Disambiguation Rules
- If a term is both a tool AND a product, choose based on pricing: free/open-source = infrastructure_tool, commercial/paid = product_brand
  - PyTorch = infrastructure_tool (free framework)
  - GitHub Copilot = product_brand (paid commercial service)
  - TensorFlow = infrastructure_tool (free framework)
  - AWS SageMaker = product_brand (paid cloud service)
- If a term could be algorithm OR technique: algorithm has formal math specification, technique is a repeatable practice
  - Gradient Descent = algorithm_model (has convergence proof)
  - Data Augmentation = technique_method (family of practices, no single algorithm)
- Hybrid terms: choose the PRIMARY use case the reader would look up
```

- [ ] **Step 6: Lint + test**

```bash
cd backend && .venv/Scripts/python.exe -m ruff check services/agents/prompts_advisor.py services/agents/prompts_news_pipeline.py services/agents/prompts_handbook_types.py
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 7: Commit**

```bash
git add backend/services/agents/prompts_advisor.py backend/services/agents/prompts_news_pipeline.py backend/services/agents/prompts_handbook_types.py
git commit -m "fix(prompts): P1 — token efficiency, few-shot examples, score definitions, type disambiguation"
```

---

## Chunk 3: P2 Medium Priority Fixes

### Task 3: P2 — Consistency, code standards, structural cleanup

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py`
- Modify: `backend/services/agents/prompts_news_pipeline.py`
- Modify: `backend/services/agents/prompts_handbook_types.py`

- [ ] **Step 1: Fix M1 — Score range standardization**

In `prompts_news_pipeline.py`, find any `0.0-1.0` score ranges in RANKING_SYSTEM_PROMPT (~line 20) and CLASSIFICATION_SYSTEM_PROMPT (~line 53). Change to `0-100` integer:

```
"score": 85  // 0-100 integer, not 0.0-1.0 float
```

Update corresponding code in `backend/services/agents/ranking.py` if it parses float scores.

- [ ] **Step 2: Fix M2 — Code quality standards in handbook prompts**

In `prompts_advisor.py`, find `adv_ko_4_code` description (~line 766). Replace:

```
- **adv_ko_4_code**: 실제 코드 스니펫 또는 구현 패턴. Python/JavaScript 우선. 코드 블록에 언어 태그 필수 (```python).
```

With:

```
- **adv_ko_4_code**: 실제 코드 스니펫. Python/JavaScript 우선. 코드 블록에 언어 태그 필수 (```python). 최소 15줄 (빈줄, 주석, 단독 괄호 제외). 에러 핸들링, 타입 힌트 포함. 표준 라이브러리 + 널리 사용되는 패키지만 (torch, sklearn, pandas, numpy, requests).
```

Same for EN equivalent (~line 847).

- [ ] **Step 3: Fix M3 — Structural clarity improvements**

In `prompts_news_pipeline.py`, find the section header pattern `**## One-Line Summary (ko: ## 한 줄 요약)**`. Add a clarifying rule to the Writing Rules section:

```
N. Section headers: When writing EN content, use the English header name only. When writing KO content, use the Korean header name only. Do NOT include "(ko: ...)" in the actual output.
```

Add focus_items format constraint near the focus_items JSON definition:

```
"focus_items": ["15-40자 한국어 or 5-12 words English per item — 1 sentence each, no bullets"]
```

Add excerpt vs summary distinction:

```
- excerpt: Marketing teaser that raises curiosity (different angle from headline)
- one-line summary (first section): Factual summary of today's key developments
- These MUST be different — excerpt sells the click, summary delivers the answer
```

- [ ] **Step 4: Fix M4 — RANKING vs CLASSIFICATION clarity**

In `prompts_news_pipeline.py`, add comments above each prompt:

```python
# SELECTION: Pick ONE best article per category (used in v2 pipeline, kept for compatibility)
RANKING_SYSTEM_PROMPT = ...

# CLASSIFICATION: Select 3-5 articles per category (used in v4 pipeline)
CLASSIFICATION_SYSTEM_PROMPT = ...
```

- [ ] **Step 5: Fix M5 — Extract repeated constants in prompts_advisor.py**

At the top of `prompts_advisor.py`, add:

```python
_JSON_RESPONSE_RULE = "Respond in JSON format only. Do not include any text outside the JSON object."
```

Replace all instances of "Respond in JSON format only" (8+ occurrences) with `{_JSON_RESPONSE_RULE}` in f-strings or direct reference.

- [ ] **Step 6: Lint + test**

```bash
cd backend && .venv/Scripts/python.exe -m ruff check .
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

- [ ] **Step 7: Commit + push all**

```bash
git add backend/services/agents/prompts_advisor.py backend/services/agents/prompts_news_pipeline.py backend/services/agents/prompts_handbook_types.py
git commit -m "fix(prompts): P2 — consistency, code standards, structural cleanup, constant extraction"
git push
```

---

## Verification

1. `ruff check .` — 0 errors
2. `pytest tests/ -v --tb=short` — 67 passed
3. `npm run build` (frontend) — Complete (no prompt changes affect frontend, but verify)
4. Manual: 어드민에서 핸드북 "Generate All Fields" 실행 → URL이 reference materials에서만 나오는지 확인
5. Manual: 뉴스 파이프라인 실행 → citation `[1](URL)`이 실제 뉴스 소스 URL인지 확인
6. Pipeline logs: `handbook.quality_check` 점수가 scoring examples 기준과 일치하는지 확인
