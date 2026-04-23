# Handbook Judge Rubric Contract Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Each task ends with a commit. Do NOT batch unrelated changes into one commit.

**Goal:** Fix 4 real bugs in the handbook quality-judge contract that depress scoring validity, plus 1 minor prompt wording drift. These bugs must land **before the Seed 800 campaign** because they systematically bias or noise-up scores that flow into `quality_score` and `generation_gate`.

**Architecture:** 5 independent tasks ordered from highest impact to lowest. Tasks 1-3 fix the judge rubric contract; Task 4 fixes a regen-path prompt bug; Task 5 fixes a minor wording drift. All changes are in two files: `backend/services/agents/prompts_handbook_types.py` (judge) and `backend/services/agents/advisor.py` (pipeline). No new DB migration, no new infrastructure.

**Tech Stack:** Python 3.11+, OpenAI SDK (`openai>=1.x`), pytest for the 1 new unit test.

---

## Background — Verified 2026-04-24

### The 4 bugs (ranked)

| # | Severity | Location | Bug |
|---|---|---|---|
| 1 | P1 | [prompts_handbook_types.py:917](backend/services/agents/prompts_handbook_types.py#L917) | `format_compliance` requires "references as structured array" but judge only sees body text, not the references array (stored separately) — criterion is unobservable → judge guesses or hallucinates evidence |
| 2 | P1 | [advisor.py:2810,2825](backend/services/agents/advisor.py#L2810) + [prompts_handbook_types.py:878-1034](backend/services/agents/prompts_handbook_types.py#L878) | Judge receives `body_advanced_ko + "\n\n" + body_advanced_en` concatenated (no labels, no contract) — judge doesn't know these are two parallel locale versions of the same term, so `internal_non_redundancy` / `non_redundancy` systematically depressed by normal cross-locale parallelism |
| 3 | P2 | [prompts_handbook_types.py:900,938](backend/services/agents/prompts_handbook_types.py#L900) | Rubric header says "10 sub-scores" but the JSON schema has 9 fields and `_ADVANCED_MAX_RAW=90` expects 9 — prompt/code drift, risk of judge fabricating a 10th sub-score |
| 4 | P2 | [advisor.py:2679-2692](backend/services/agents/advisor.py#L2679) | `resp4b` (EN advanced regen) sends `user_prompt=advanced_prompt` — that variable was built at ~line 2266 **before Call 2 (EN basic) completed**, containing the placeholder `"(Basic EN not yet generated — Call 2 runs in parallel)"`. Regen against placeholder context defeats anti-duplication |
| 5 | minor | [prompts_advisor.py](backend/services/agents/prompts_advisor.py) | Call 1 prompt described as "Korean only" but schema requires `definition_en` — wording drift |

### Why these must land before Seed 800

- **Bug 1 (references criterion)**: Every `format_compliance` score is noise right now. The 800-term cohort would have ~800 noisy `format_compliance` evaluations flowing into `structural_completeness` totals.
- **Bug 2 (bilingual contract)**: Systematically depresses `non_redundancy` / `internal_non_redundancy` — two of the 9/10 sub-scores — across every bilingual term. If Seed 800 runs on the current rubric, all 800 scores carry this bias and we'd need a full rescore campaign.
- **Bug 3** is cosmetic but compounds bug 2 — if judge tries to produce a 10th sub-score it doesn't exist, schema parsing may choke.
- **Bug 4** only affects the regen minority path but is worth fixing in the same batch since we're touching advisor.py.

### What is already correct (do NOT re-touch)

- The 18 `prompt_cache_key` values in `advisor.py` (Task 2 from the 2026-04-23 plan). Don't rename.
- The writer-QC mirror blocks in `prompts_advisor.py` already say "9 sub-scores" for advanced (I wrote them correctly). Only the judge's `HANDBOOK_QUALITY_CHECK_PROMPT` says "10" — fix there.
- The writer-QC mirror's `format_compliance` bullet currently mirrors the judge's wording (includes "references as structured array"). When we fix the judge (Task 1), we must update the writer mirror in lockstep to keep the mirror faithful.

---

## Task 1: Remove unobservable references criterion from `format_compliance` (judge + writer mirror)

**Severity: P1. Shipping this alone makes every future `format_compliance` score meaningful instead of noisy.**

**Files:**
- Modify: [backend/services/agents/prompts_handbook_types.py:917](backend/services/agents/prompts_handbook_types.py#L917)
- Modify: [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) — Writer-QC mirror blocks in `GENERATE_ADVANCED_PROMPT` (KO) and `GENERATE_ADVANCED_EN_PROMPT` (EN). Search for the string `format_compliance` — should find 1 occurrence in each advanced prompt.

### Step 1: Edit the judge rubric

In `backend/services/agents/prompts_handbook_types.py`, find line 917:

Current:
```
- **format_compliance**: `❌ Mistake:`/`✅ Fix:` markers in pitfalls, `(prerequisite)`/`(alternative)`/`(extension)` tags in relations, references as structured array
```

Change to:
```
- **format_compliance**: `❌ Mistake:`/`✅ Fix:` markers in the Pitfalls section, `(prerequisite)`/`(alternative)`/`(extension)` tags in the Relations section. (References array is NOT part of the submitted content — do not score its structure.)
```

The explicit "do not score" suffix is important — without it, the judge may still try to score references from memory of the prior rubric.

### Step 2: Edit the writer-QC mirror — advanced KO

In `backend/services/agents/prompts_advisor.py`, find the Writer-QC mirror block inside `GENERATE_ADVANCED_PROMPT` (Korean, Task 7 addition, look for `품질 평가 기준 미리보기` and `format_compliance`). The `format_compliance` entry currently reads something like:

```
`format_compliance` (`❌ Mistake:`/`✅ Fix:`, `(prerequisite)`/`(alternative)`/`(extension)` tags, structured references)
```

Change to:
```
`format_compliance` (`❌ Mistake:`/`✅ Fix:` 마커, `(prerequisite)`/`(alternative)`/`(extension)` 태그 — references 배열은 평가 대상 아님)
```

### Step 3: Edit the writer-QC mirror — advanced EN

In `GENERATE_ADVANCED_EN_PROMPT` find the corresponding mirror block and update:

```
`format_compliance` (`❌ Mistake:`/`✅ Fix:` markers, `(prerequisite)`/`(alternative)`/`(extension)` tags — references array is not part of evaluated content)
```

### Step 4: Syntax check

Run:
```bash
python -c "import ast; ast.parse(open('backend/services/agents/prompts_handbook_types.py', encoding='utf-8').read()); ast.parse(open('backend/services/agents/prompts_advisor.py', encoding='utf-8').read()); print('SYNTAX_OK')"
```
Expected: `SYNTAX_OK`

### Step 5: Stage only target files

```bash
git add backend/services/agents/prompts_handbook_types.py backend/services/agents/prompts_advisor.py
git diff --cached --stat
```
Expected: `2 files changed, 3 insertions(+), 3 deletions(-)` (approximate — 3 single-line replacements).

Scan `git diff --cached` — should show ONLY the three format_compliance edits. If anything else appears, `git restore --staged <file>` and investigate.

### Step 6: Commit

```bash
git commit -m "fix(handbook): remove unobservable references criterion from format_compliance (judge + writer mirror)"
```

No `Co-Authored-By`.

---

## Task 2: Bilingual rubric contract — tell judge the content is two parallel locales

**Severity: P1. Biggest impact of this plan. Fixing this makes the `non_redundancy` / `internal_non_redundancy` sub-scores valid.**

This task has two parts: (A) label the locale sections in the judge's user message, (B) add a "Bilingual Content Contract" section to both judge prompts. Without (A), (B)'s references to "KO section" / "EN section" are meaningless.

**Files:**
- Modify: [backend/services/agents/advisor.py:2810](backend/services/agents/advisor.py#L2810) — `adv_combined` construction
- Modify: [backend/services/agents/advisor.py:2825](backend/services/agents/advisor.py#L2825) — `basic_combined` construction
- Modify: [backend/services/agents/prompts_handbook_types.py:878-939](backend/services/agents/prompts_handbook_types.py#L878) — `HANDBOOK_QUALITY_CHECK_PROMPT`
- Modify: [backend/services/agents/prompts_handbook_types.py:971-1034](backend/services/agents/prompts_handbook_types.py#L971) — `BASIC_QUALITY_CHECK_PROMPT`

### Step 1: Write the failing test

Create `backend/tests/test_handbook_judge_bilingual.py`:

```python
"""Verify bilingual labeling is present in the user message fed to the judge."""
from services.agents.advisor import _build_bilingual_judge_content


def test_builds_labeled_bilingual_content():
    result = _build_bilingual_judge_content("KO body here", "EN body here")
    assert "## Korean (KO)" in result
    assert "## English (EN)" in result
    assert "KO body here" in result
    assert "EN body here" in result
    # KO must appear before EN (stable order for caching)
    assert result.index("## Korean (KO)") < result.index("## English (EN)")


def test_handles_missing_en():
    result = _build_bilingual_judge_content("KO only", "")
    assert "## Korean (KO)" in result
    assert "KO only" in result
    # Missing locale explicitly noted
    assert "## English (EN)" in result
    assert "(no English content provided)" in result


def test_handles_missing_ko():
    result = _build_bilingual_judge_content("", "EN only")
    assert "## Korean (KO)" in result
    assert "(no Korean content provided)" in result
    assert "## English (EN)" in result
    assert "EN only" in result


def test_strips_whitespace_for_comparison():
    result = _build_bilingual_judge_content("  \n\n  ", "EN body")
    assert "(no Korean content provided)" in result
    assert "EN body" in result
```

### Step 2: Run test to verify it fails

```bash
cd backend && .venv/Scripts/activate && pytest tests/test_handbook_judge_bilingual.py -v
```
Expected: FAIL with `ImportError: cannot import name '_build_bilingual_judge_content'`

### Step 3: Implement the helper

In `backend/services/agents/advisor.py`, add this helper function at module level (near other handbook helpers, e.g., just before `_check_handbook_quality` at line 1151):

```python
def _build_bilingual_judge_content(ko_body: str, en_body: str) -> str:
    """Construct a labeled user message for the bilingual quality judge.

    The judge sees KO and EN content as two parallel locale versions of the
    same term. Labels are required so the judge's Bilingual Content Contract
    (see HANDBOOK_QUALITY_CHECK_PROMPT / BASIC_QUALITY_CHECK_PROMPT) can
    reference "the KO section" / "the EN section" meaningfully.

    Missing locales are preserved as explicit placeholders so the judge can
    downscore the missing-language sub-scores instead of silently treating
    them as "present but empty".
    """
    ko_section = ko_body.strip() if ko_body and ko_body.strip() else "(no Korean content provided)"
    en_section = en_body.strip() if en_body and en_body.strip() else "(no English content provided)"
    return f"## Korean (KO)\n\n{ko_section}\n\n## English (EN)\n\n{en_section}"
```

### Step 4: Run test to verify it passes

```bash
cd backend && pytest tests/test_handbook_judge_bilingual.py -v
```
Expected: 4 PASS.

### Step 5: Wire the helper into both quality call sites

In `backend/services/agents/advisor.py`, replace line 2810:

Before:
```python
adv_combined = f"{data.get('body_advanced_ko', '')}\n\n{data.get('body_advanced_en', '')}"
```

After:
```python
adv_combined = _build_bilingual_judge_content(
    data.get("body_advanced_ko", ""),
    data.get("body_advanced_en", ""),
)
```

And line 2825:

Before:
```python
basic_combined = f"{data.get('body_basic_ko', '')}\n\n{data.get('body_basic_en', '')}"
```

After:
```python
basic_combined = _build_bilingual_judge_content(
    data.get("body_basic_ko", ""),
    data.get("body_basic_en", ""),
)
```

### Step 6: Add Bilingual Content Contract to both judge prompts

In `backend/services/agents/prompts_handbook_types.py`, find `HANDBOOK_QUALITY_CHECK_PROMPT` starting at line 878.

Insert the following block **between the "Required Output Format" section and the "Sub-dimensions" heading** (around line 900, immediately before `## Sub-dimensions (10 sub-scores)`):

```
## Bilingual Content Contract

The user message contains TWO parallel locale versions of the same term, labeled `## Korean (KO)` and `## English (EN)`. These are intentional translations of each other, not independent content. Apply these rules:

- **Same idea expressed in both KO and EN is NOT redundancy.** `internal_non_redundancy` measures repetition WITHIN each locale only — e.g., the same example paraphrased across multiple sections of `body_advanced_ko`. Cross-locale parallelism is expected and MUST NOT be penalized.
- **Score each sub-score as the weaker of the two locales.** If KO looks strong and EN looks weak on `mechanism_clarity`, the term as a whole is weak on that dimension — return the lower score. Rationale: a term that only works in one language isn't a good handbook entry.
- **Cite evidence with locale labels.** Always prefix evidence with `[KO]` or `[EN]` (e.g., `[KO] section 'Mechanism' contains specific parameter counts (175B, 12 layers)`). Never mix quotes from both locales in one evidence field.
- **If one locale is a placeholder** (`(no Korean content provided)` or similar), treat that locale as score 0 on all content-dependent sub-scores and mention the missing locale in the evidence.
```

Apply the **same block** to `BASIC_QUALITY_CHECK_PROMPT` (line 971), inserted immediately before its `## Sub-dimensions (10 sub-scores)` heading.

### Step 7: Syntax check

```bash
python -c "import ast; ast.parse(open('backend/services/agents/advisor.py', encoding='utf-8').read()); ast.parse(open('backend/services/agents/prompts_handbook_types.py', encoding='utf-8').read()); print('SYNTAX_OK')"
```

### Step 8: Run the test again plus a quick grep sanity

```bash
cd backend && pytest tests/test_handbook_judge_bilingual.py -v
```
Expected: 4 PASS (unchanged).

```bash
grep -n "Bilingual Content Contract" backend/services/agents/prompts_handbook_types.py
```
Expected: 2 hits (one per prompt).

### Step 9: Stage only target files

```bash
git add backend/services/agents/advisor.py backend/services/agents/prompts_handbook_types.py backend/tests/test_handbook_judge_bilingual.py
git diff --cached --stat
```
Expected: 3 files changed, roughly 40-60 insertions, 2 deletions.

Scan `git diff --cached` to confirm no unrelated content is staged.

### Step 10: Commit

```bash
git commit -m "fix(handbook): add bilingual content contract so judge stops flagging normal KO↔EN parallelism as redundancy"
```

---

## Task 3: Fix "10 sub-scores" → "9 sub-scores" drift in advanced judge prompt

**Severity: P2. Cosmetic but real — prevents judge from inventing a 10th sub-score.**

**Files:**
- Modify: [backend/services/agents/prompts_handbook_types.py:900](backend/services/agents/prompts_handbook_types.py#L900)

### Step 1: Edit

Find line 900:
```
## Sub-dimensions (10 sub-scores)
```

Change to:
```
## Sub-dimensions (9 sub-scores)
```

Verify the basic version at line 993 already says `## Sub-dimensions (10 sub-scores)` — THAT ONE IS CORRECT (basic has 3+3+2+2=10 fields, see schema at lines 1016-1033). Do NOT change the basic prompt.

### Step 2: Sanity grep

```bash
grep -n "Sub-dimensions" backend/services/agents/prompts_handbook_types.py
```
Expected output:
```
900:## Sub-dimensions (9 sub-scores)
993:## Sub-dimensions (10 sub-scores)
```

### Step 3: Syntax check

```bash
python -c "import ast; ast.parse(open('backend/services/agents/prompts_handbook_types.py', encoding='utf-8').read()); print('SYNTAX_OK')"
```

### Step 4: Stage + commit

```bash
git add backend/services/agents/prompts_handbook_types.py
git diff --cached --stat
```
Expected: `1 file changed, 1 insertion(+), 1 deletion(-)`.

```bash
git commit -m "fix(handbook): advanced rubric says 9 sub-scores to match the 9-field schema"
```

---

## Task 4: Fix EN advanced regen using KO-context prompt (`resp4b`)

**Severity: P2. Only fires on critique-driven regen, but fix is small and isolates correctness.**

**Files:**
- Modify: [backend/services/agents/advisor.py:2679-2692](backend/services/agents/advisor.py#L2679)

### Context to understand before editing

Read `backend/services/agents/advisor.py` lines 2240–2450 in full. Specifically note:

- Around line 2246: `en_basic_prompt` is constructed from `user_prompt` + the Call 1 definition context. This is for Call 2 (EN basic).
- Around line 2266: `advanced_prompt` is constructed using `basic_ko_body_for_ctx` (real) and `basic_en_body_for_ctx` which at construction time is `"(Basic EN not yet generated — Call 2 runs in parallel)"` because Call 2 hasn't completed yet.
- Around line 2395–2440: Call 4 (initial EN advanced) runs AFTER Call 2 completes. It uses `advanced_en_prompt` (or similar) which is built with the now-real EN basic body.

Grep to find the exact variable name Call 4 uses:
```bash
grep -n "call4_task\|advanced_en_prompt\|advanced_en_system" backend/services/agents/advisor.py | head -20
```

Confirm the correct variable name for "advanced EN user prompt, built after Call 2 completed."

### Step 1: Identify the right variable

Expected finding: Call 4 at around line 2410 sends a user-prompt variable that contains the completed EN basic body. The regen at line 2684 sends `advanced_prompt` — the KO-oriented variant with placeholder EN basic. The fix is to change line 2684's `"content": advanced_prompt` to `"content": <correct_en_variable>`.

If you cannot find an exact `advanced_en_prompt` equivalent variable, construct one inline at the regen site by rebuilding it with the now-available `en_basic_data`. Template (adapt variable names to what's in scope at the regen site):

```python
fresh_en_basic_body = _assemble_markdown(en_basic_data, BASIC_SECTIONS_EN)[:3000] if en_basic_data else "(Basic EN not available)"
advanced_en_regen_prompt = (
    f"{user_prompt}\n\n"
    f"--- Context from Call 1 ---\n"
    f"Definition (EN): {definition_context}\n"
    f"Definition (KO): {definition_ko_context}\n"
    f"Term Type: {term_type}\n"
    f"Term Subtype: {term_subtype or 'none'}\n"
    f"\n--- Basic KO body (DO NOT duplicate analogies, examples, or phrasing) ---\n"
    f"{basic_ko_body_for_ctx}\n"
    f"\n--- Basic EN body (DO NOT duplicate) ---\n"
    f"{fresh_en_basic_body}"
)
```

Prefer reusing an existing variable if one already has the correct content.

### Step 2: Make the edit

Replace the user-message content in `resp4b` at line 2684 with the correct variable. The rest of the `compat_create_kwargs(...)` call stays unchanged (including `prompt_cache_key="hb-regen-en-advanced"`, `reasoning_effort="high"`, `service_tier="flex"`).

### Step 3: Syntax check

```bash
python -c "import ast; ast.parse(open('backend/services/agents/advisor.py', encoding='utf-8').read()); print('SYNTAX_OK')"
```

### Step 4: (Optional) Smoke-import

```bash
cd backend && python -c "from services.agents.advisor import generate_handbook_content; print('IMPORT_OK')"
```

### Step 5: Stage + commit

```bash
git add backend/services/agents/advisor.py
git diff --cached --stat
```
Expected: `1 file changed, ~2-12 insertions(+), 1 deletion(-)` depending on whether you reused a variable or built one inline.

```bash
git commit -m "fix(handbook): EN advanced regen uses fresh EN-context prompt instead of KO-phase prompt with placeholder"
```

---

## Task 5: Fix Call 1 prompt wording drift — "Korean only" vs required `definition_en`

**Severity: Minor. Cosmetic wording fix. Writer's actual behavior is already correct (produces both definitions); this just cleans up the documentation inside the prompt so future readers don't get confused.**

**Files:**
- Modify: [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) — `GENERATE_BASIC_PROMPT` around line 545 (description) and the schema block requiring `definition_en` (around line 970)

### Step 1: Locate the drift

```bash
grep -n "Korean only\|korean only" backend/services/agents/prompts_advisor.py
```

Expected: 1 hit near the top of `GENERATE_BASIC_PROMPT` that describes Call 1 as "Korean only".

Also check:
```bash
grep -n "definition_en" backend/services/agents/prompts_advisor.py | head -5
```

Confirm `definition_en` is in the schema requirements for Call 1.

### Step 2: Rewrite the wording

Change the "Korean only" description to accurately reflect what Call 1 produces. Suggested phrasing:

> Call 1 produces term metadata, **bilingual definitions** (KO + EN), and the Korean Basic body. (EN Basic body is generated by Call 2 in parallel.)

Adapt to match the surrounding prompt's tone (the KO prompt should describe this in Korean).

### Step 3: Syntax check

```bash
python -c "import ast; ast.parse(open('backend/services/agents/prompts_advisor.py', encoding='utf-8').read()); print('SYNTAX_OK')"
```

### Step 4: Stage + commit

```bash
git add backend/services/agents/prompts_advisor.py
git diff --cached --stat
```
Expected: `1 file changed, ~1-3 insertions(+), 1-3 deletions(-)`.

```bash
git commit -m "docs(handbook): describe Call 1 as bilingual-definitions + KO basic to match actual behavior"
```

---

## Out of Scope (separate plan)

1. **Two-locale schema for judge output.** A fully correct solution for P1-1 (bilingual rubric) would have the judge return `{ko: {...sub_scores}, en: {...sub_scores}}` and aggregate in code. This plan takes the lighter "single output with min aggregation in prompt" approach because:
   - Lower risk (no schema migration, no code changes to `_aggregate_quality_sub_scores`)
   - Fixes the immediate bias
   - Leaves room for a proper two-locale schema in a follow-up plan
2. **`json_schema` strict migration** for handbook calls. News pipeline uses strict JSON schemas; handbook still uses `json_object` + post-validation. Larger refactor, separate plan.
3. **Per-term-type sub-score weights.** Identified in the 2026-04-23 scoring-system forward-thinking audit. Needs its own plan.
4. **Rescore 57 already-published terms** with the fixed rubric. Needs a batch-job plan, not code changes.

---

## Success Criteria (all tasks shipped when all hold)

- [ ] `grep -c "references as structured array" backend/services/agents/prompts_handbook_types.py` returns 0
- [ ] `grep -c "references as structured array\|structured references" backend/services/agents/prompts_advisor.py` returns 0 (writer mirror updated)
- [ ] `grep -n "_build_bilingual_judge_content" backend/services/agents/advisor.py` shows 3 hits (1 definition + 2 call sites)
- [ ] `grep -c "Bilingual Content Contract" backend/services/agents/prompts_handbook_types.py` returns 2 (both prompts)
- [ ] `grep -n "## Sub-dimensions" backend/services/agents/prompts_handbook_types.py` shows `900:## Sub-dimensions (9 sub-scores)` and `993:## Sub-dimensions (10 sub-scores)`
- [ ] `pytest backend/tests/test_handbook_judge_bilingual.py -v` → 4 passing
- [ ] `resp4b` at advisor.py:~2679 uses an EN-context prompt (not the KO-phase `advanced_prompt` with placeholder)
- [ ] `grep -c "Korean only" backend/services/agents/prompts_advisor.py` returns 0
- [ ] Manual regression: regenerate 1 existing term end-to-end; confirm `pipeline_logs.debug_meta->>'service_tier'` on the 3 QC calls = `"flex"` or `"default"` (both acceptable), no pipeline errors.

---

## Related Plans

- Prior batch (shipped 2026-04-23): `2026-04-23-handbook-gpt5-and-writer-qc-mirror.md` — GPT-5 efficiency + writer-QC mirror
- Prior selection hardening (shipped 2026-04-20): `2026-04-17-handbook-term-selection-hardening-plan.md`
- Forward-thinking scoring audit notes (from 2026-04-23 conversation): per-term-type weights, two-locale schema, gold-standard corpus — candidates for future plans.
