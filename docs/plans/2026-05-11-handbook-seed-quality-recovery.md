# Handbook Seed Quality Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make seed-generated handbook drafts safe to review by preventing broken markdown/code, reducing overlong advanced sections, and aligning content shape with term type.

**Architecture:** Add deterministic post-generation validators first, then tighten type-aware generation controls, then remediate the three generated drafts. The pipeline should save draft content only after syntax/markdown/shape checks pass or after clearly recording blocking warnings.

**Tech Stack:** FastAPI backend, Supabase, OpenAI handbook generation pipeline, Python pytest, Astro admin UI.

---

## Priority Overview

### P0: Stop Broken Drafts From Looking Acceptable

**Why:** These are objective failures that can ship visibly broken content.

**Checklist:**
- Code fences are syntax-checked when marked as Python.
- Literal JSON Schema identifiers like `$ref`, `$defs`, `$schema` do not trigger math rendering.
- Mixed-language artifacts such as `실행语의미` are flagged.
- Seed quality scores can be saved with `source='seed'`.
- Seed rollup logs do not double-count stage costs.

**Current status:**
- Done: structured-section slice crash fixed.
- Done: seed quality score DB constraint expanded.
- Done: seed rollup logs normalized to non-billable rollups.
- Remaining: code fence validator, markdown dollar sanitizer, mixed-script artifact validator.

### P1: Add Content Shape Guardrails

**Why:** The drafts are not failing because the model cannot write; they fail because the output shape is too permissive.

**Checklist:**
- For `capability_feature_spec`, suppress `adv_*_specs` unless the term is a model, product, benchmark, hardware, or measurable system.
- Add max length budgets by section: basic sections compact, advanced explanation moderate, code section capped.
- If code section exceeds budget, request pseudocode or concise skeleton rather than full tutorial code.
- Enforce KO/EN symmetry for code mode and section role, not identical code length.
- Store structural warnings in pipeline logs and return them to admin generation responses.

### P2: Fix Prompt Framing by Term Type

**Why:** `Structured Outputs` and `Computer Use` drifted into provider docs/tutorial mode.

**Checklist:**
- `capability_feature_spec` advanced should prioritize mechanism, boundary, validation, failure handling, and operational tradeoffs.
- Provider examples should be capped to 2 representative examples unless the term is explicitly provider-specific.
- Product/model version claims should be avoided unless grounded by selected official references.
- Foundational terms should not default to long real-code examples unless the concept is inherently implementation-oriented.
- Code prompt should ask for minimal runnable example or pseudocode, not production framework wrappers.

### P3: Remediate Existing Three Drafts

**Why:** The three generated drafts are visible in admin and should either become useful review candidates or be marked for regeneration.

**Checklist:**
- `In-Context Learning`: reduce MMR/example-selection overfocus, compress EN definition, simplify code to conceptual pseudocode, keep references.
- `Structured Outputs`: remove parameters/FLOPs/spec section, escape `$ref/$defs/$schema`, replace invalid code snippet, rewrite advanced around constrained decoding and validation rather than provider enumeration.
- `Computer Use`: remove `MODEL = "gpt-5.4"` hardcode, shorten EN advanced, replace long Playwright harness with concise host-loop pseudocode, fix mixed-language artifact, keep safety boundary.
- Re-run quality checks for all three after remediation.

### P4: Admin/Review Visibility

**Why:** A blocked draft should be obvious before Amy opens the full editor.

**Checklist:**
- Show seed generation warnings or quality gate summary in admin draft/edit view if data is available.
- Ensure `advanced_quality < 55` or malformed code blocks are visible as review blockers.
- Keep status as `draft`, but make blocked/review-required distinguishable from clean draft.

### P5: Regression Tests

**Why:** These failures are deterministic enough to pin with tests.

**Checklist:**
- Test Python code fence syntax validator catches ellipsis-style invalid snippets.
- Test markdown sanitizer preserves currency but escapes/schema-wraps `$ref`, `$defs`, `$schema`.
- Test capability terms do not receive model-style specs sections.
- Test mixed-script artifact detection flags Korean text containing isolated Chinese artifacts.
- Test seed-generated quality scores accept `source='seed'`.
- Test seed summary rollups do not contribute duplicate `cost_usd`/`tokens_used`.

---

## Task 1: Code Fence And Markdown Safety Validators

**Files:**
- Modify: `backend/services/agents/advisor.py`
- Test: `backend/tests/test_handbook_generation_flow.py`

**Step 1: Write failing tests**

Add tests for:
- Python code fence with `client.responses.create(..., foo=1)`-style invalid syntax.
- Text containing `$ref/$defs/$schema`.
- KO text containing `실행语의미`.

**Step 2: Implement validators**

Add small pure functions:
- `_validate_python_code_fences(markdown: str) -> list[str]`
- `_sanitize_schema_dollar_identifiers(text: str) -> str`
- `_detect_mixed_script_artifacts(text: str) -> list[str]`

**Step 3: Wire into postprocess**

Run these after `_assemble_all_sections()` and before save. For now, fix safe text issues automatically and add warnings for code/artifact failures.

**Step 4: Verify**

Run:

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_handbook_generation_flow.py -q
```

Expected: pass.

## Task 2: Capability Term Section Shape Controls

**Files:**
- Modify: `backend/services/agents/prompts_handbook_types.py`
- Modify: `backend/services/agents/advisor.py`
- Test: `backend/tests/test_handbook_generation_flow.py`

**Step 1: Write failing test**

Assert `Structured Outputs`-like `capability_feature_spec` output does not include `adv_*_specs`.

**Step 2: Implement shape rule**

Only include specs sections for term types/subtypes where model specs, hardware specs, benchmark metrics, or product version specs are relevant.

**Step 3: Verify**

Run handbook generation flow tests.

## Task 3: Code Section Length And Mode Guardrails

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py`
- Modify: `backend/services/agents/advisor.py`
- Test: `backend/tests/test_handbook_generation_flow.py`

**Step 1: Write failing test**

Assert overlong code sections produce a warning or are downgraded to concise pseudocode.

**Step 2: Implement guardrail**

For non-library/non-framework terms, prefer pseudocode or short host-loop examples. Cap code section body to a configured character budget before final save unless explicitly allowed.

**Step 3: Verify**

Run related tests and one dry-run generation candidate.

## Task 4: Remediate Existing Drafts

**Files:**
- Use DB updates through a small one-off backend script if needed.
- Optional create: `backend/scripts/remediate_seed_drafts.py`

**Step 1: Fix `In-Context Learning`**

Compress advanced, reduce code, remove overfocus on MMR.

**Step 2: Fix `Structured Outputs`**

Remove specs, fix `$ref/$defs`, replace invalid code, make provider details supporting not central.

**Step 3: Fix `Computer Use`**

Shorten code, remove model hardcode, fix mixed-language artifact, strengthen host-execution boundary.

**Step 4: Re-run quality checks**

Record new quality scores and confirm admin draft content is readable.

## Task 5: Admin Visibility

**Files:**
- Modify: `frontend/src/pages/admin/handbook/index.astro` or relevant admin list file.
- Modify: `frontend/src/pages/admin/handbook/edit/[slug].astro`
- Test: frontend structural/admin tests where available.

**Step 1: Inspect current warning data path**

Confirm whether pipeline log warnings are accessible from the draft list or edit page.

**Step 2: Add minimal warning surface**

Show review blockers for seed drafts when the latest pipeline log has warnings or quality gate blocked.

**Step 3: Verify**

Run frontend tests and manually inspect admin.

---

## Execution Order

1. Task 1 first, because it prevents visible broken rendering and invalid code.
2. Task 2 second, because it fixes the `Structured Outputs` shape problem at source.
3. Task 3 third, because it controls the biggest readability issue.
4. Task 4 fourth, because remediation should happen after validators are in place.
5. Task 5 last, because admin visibility depends on stable warning data.
