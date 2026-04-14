# Scoring V2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current EN-body-only digest score with a production-grade quality score that includes EN/KO body quality, frontload quality, deterministic checks, and structured issue penalties.

**Architecture:** Keep the existing digest generation pipeline and hard validation blockers, but replace the current single LLM-review pass with a layered scoring flow. The new flow computes deterministic sub-scores in code, runs separate LLM judges for expert body, learner body, and frontload quality, then applies severity-based issue penalties and score caps before saving a final `quality_score` plus breakdown metadata.

**Tech Stack:** FastAPI backend, Pydantic models, Supabase, OpenAI chat completions, pytest.

---

## Scope

Implement `scoring v2a` first:
- Add KO content into scoring inputs
- Add a frontload scorer for `title`, `excerpt`, and `focus_items`
- Change quality reviewer outputs to structured issues with severity
- Apply deterministic issue penalties and score caps in code
- Persist richer scoring breakdown in pipeline logs and saved payloads

Defer `scoring v2b`:
- Expand deterministic soft checks
- Calibrate score distributions on recent batches
- Add historical backfill utility

## Non-Goals

- Do not redesign digest generation prompts outside scoring-specific judge prompts
- Do not change hard blockers / save validators in this pass except where needed to expose their outputs to scoring
- Do not modify frontend/admin UI in this plan unless backend storage shape forces a small compatibility change

## Success Criteria

- A digest with strong EN body but weak KO or weak title/excerpt can no longer score in the high 90s
- A digest with structured `major` issues cannot score above the configured cap
- `quality_score` reflects EN+KO body quality, frontload quality, deterministic checks, and issue penalties
- `pipeline_logs.debug_meta` stores enough scoring detail to explain each final score
- Targeted tests cover new scoring inputs, issue penalties, and score caps

## Proposed Data Model

Keep `news_posts.quality_score` as the final scalar score.

Add richer scoring detail to:
- `pipeline_logs.debug_meta`
- `news_posts.fact_pack`

Suggested saved structure:

```json
{
  "quality_version": "v2",
  "quality_breakdown": {
    "deterministic": {
      "structure": 12,
      "traceability": 14,
      "locale": 8
    },
    "llm": {
      "expert_body": 16,
      "learner_body": 15,
      "frontload": 13
    }
  },
  "quality_issues": [
    {
      "severity": "major",
      "scope": "frontload",
      "category": "overclaim",
      "message": "Headline overstates competitive impact beyond source support"
    }
  ],
  "quality_caps_applied": ["frontload_overclaim_cap_89"],
  "structural_warnings": []
}
```

## Score Formula

```text
final_score =
  deterministic_score (0-40)
+ llm_score (0-60)
- issue_penalty
```

Where:

- `deterministic_score`
  - `structure_score` 0-15
  - `traceability_score` 0-15
  - `locale_score` 0-10
- `llm_score`
  - `expert_body_score` 0-20
  - `learner_body_score` 0-20
  - `frontload_score` 0-20
- `issue_penalty`
  - `major = -5`
  - `minor = -2`
  - capped at `-20`

## Score Caps

Apply caps after penalty:

- `major factual/source issue` -> max `84`
- `major frontload overclaim` -> max `89`
- `major locale quality issue` -> max `89`
- `major accessibility issue in learner` -> max `92`

If multiple caps apply, use the lowest cap.

## LLM Judge Outputs

All scoring prompts should return:

```json
{
  "score": 0,
  "subscores": {
    "sections": 0,
    "sources": 0,
    "language": 0
  },
  "issues": [
    {
      "severity": "major|minor",
      "scope": "expert_body|learner_body|frontload|ko|en",
      "category": "source|overclaim|accessibility|locale|structure|clarity",
      "message": "Short explanation"
    }
  ]
}
```

For body judges, `subscores` should match the persona:
- research expert: `sections`, `sources`, `depth`, `language`
- research learner: `sections`, `accessibility`, `sources`, `language`
- business expert: `sections`, `sources`, `analysis`, `language`
- business learner: `sections`, `accessibility`, `actionability`, `language`

For frontload judge:
- `factuality`
- `calibration`
- `clarity`
- `locale_alignment`

## Files To Modify

### Backend scoring orchestration
- Modify: `backend/services/pipeline.py`

### Prompt definitions
- Modify: `backend/services/agents/prompts_news_pipeline.py`

### Tests
- Modify: `backend/tests/test_pipeline_digest_validation.py`
- Modify: `backend/tests/test_news_digest_prompts.py`
- Create or modify: `backend/tests/test_pipeline_quality_scoring.py`

## Task 1: Add failing tests for v2 scoring inputs

**Files:**
- Modify: `backend/tests/test_pipeline_digest_validation.py`
- Create: `backend/tests/test_pipeline_quality_scoring.py`

**Step 1: Write a failing test for KO affecting score**

Add a test that:
- builds `PersonaOutput` with strong `en`
- intentionally weak or awkward `ko`
- expects the scoring orchestration to consider KO input instead of ignoring it

**Step 2: Run the test to verify it fails**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_quality_scoring.py -k "ko" -v
```

Expected:
- FAIL because current scoring only sends `expert.en` and `learner.en`

**Step 3: Write a failing test for frontload scoring**

Add a test that:
- uses a strong body
- uses an overclaiming headline/excerpt
- expects a frontload issue or score reduction path to exist

**Step 4: Run the test to verify it fails**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_quality_scoring.py -k "frontload" -v
```

Expected:
- FAIL because current scoring has no frontload scorer

**Step 5: Commit**

```bash
git add backend/tests/test_pipeline_quality_scoring.py backend/tests/test_pipeline_digest_validation.py
git commit -m "test: add failing scoring v2 coverage"
```

## Task 2: Add structured issue schema tests

**Files:**
- Modify: `backend/tests/test_news_digest_prompts.py`
- Modify: `backend/tests/test_pipeline_quality_scoring.py`

**Step 1: Write failing prompt tests**

Assert that each quality reviewer prompt now requires:
- structured `issues`
- `severity`
- `scope`
- `category`

**Step 2: Run the prompt tests to verify they fail**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_news_digest_prompts.py -k "quality" -v
```

Expected:
- FAIL because current prompts still return free-form issues

**Step 3: Write failing code test for issue penalties**

Add a unit test that:
- mocks a scoring response with one `major` and one `minor` issue
- expects `-7` total penalty and a cap to apply

**Step 4: Run the test to verify it fails**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_quality_scoring.py -k "issue_penalty" -v
```

Expected:
- FAIL because no structured issue penalty code exists yet

**Step 5: Commit**

```bash
git add backend/tests/test_news_digest_prompts.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "test: add structured scoring issue expectations"
```

## Task 3: Implement scoring payload builders

**Files:**
- Modify: `backend/services/pipeline.py`

**Step 1: Add helper to build body scoring payload**

Add a helper that creates a scoring input from:
- `expert.en`
- `expert.ko`
- `learner.en`
- `learner.ko`
- digest type
- optional source mix summary

**Step 2: Add helper to build frontload scoring payload**

Include:
- `title`
- `title_ko`
- `excerpt`
- `excerpt_ko`
- `focus_items`
- `focus_items_ko`
- digest type

**Step 3: Keep helpers pure and unit-testable**

No API calls inside helpers.

**Step 4: Run relevant tests**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_quality_scoring.py -k "payload" -v
```

Expected:
- PASS once helpers are wired

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "feat: add scoring v2 payload builders"
```

## Task 4: Update quality prompts to v2 schemas

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py`
- Modify: `backend/tests/test_news_digest_prompts.py`

**Step 1: Update body reviewer prompts**

Change all 4 prompts so they:
- expect EN+KO body quality
- emit structured issues with severity
- do not treat free-form issues as sufficient

**Step 2: Add a new frontload reviewer prompt**

Define a prompt dedicated to:
- factuality
- claim calibration
- clarity
- locale alignment

**Step 3: Run prompt tests**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_news_digest_prompts.py -v
```

Expected:
- PASS with updated schema checks

**Step 4: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py backend/tests/test_news_digest_prompts.py
git commit -m "feat: add scoring v2 reviewer prompts"
```

## Task 5: Replace current LLM scoring flow

**Files:**
- Modify: `backend/services/pipeline.py`
- Modify: `backend/tests/test_pipeline_quality_scoring.py`

**Step 1: Replace current 2-call scoring with 3-part scoring**

Run 3 judges:
- expert body
- learner body
- frontload

**Step 2: Parse structured issue arrays**

Normalize malformed results defensively:
- missing severity -> `minor`
- missing scope -> `unknown`
- missing category -> `general`

**Step 3: Convert each judge score into weighted sub-score**

Map raw `0-100` judge scores into:
- `0-20` expert body
- `0-20` learner body
- `0-20` frontload

**Step 4: Run failing tests to verify implementation**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_quality_scoring.py -k "frontload or ko or llm" -v
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "feat: wire scoring v2 llm judges"
```

## Task 6: Add deterministic scoring components

**Files:**
- Modify: `backend/services/pipeline.py`
- Modify: `backend/tests/test_pipeline_digest_validation.py`
- Modify: `backend/tests/test_pipeline_quality_scoring.py`

**Step 1: Add `structure_score` helper**

Use existing validation information where possible:
- section presence
- correct headings
- paragraph structure
- list formatting

**Step 2: Add `traceability_score` helper**

Use:
- citation presence
- `source_urls` vs citations
- source metadata consistency
- license-sensitive wording checks where already available

**Step 3: Add `locale_score` helper**

Use:
- EN/KO section parity
- locale purity
- KO heading consistency

**Step 4: Make stale supporting-depth logic explicit**

Do not rely on removed `[LEAD]/[SUPPORTING]` tags.
Instead derive item depth from current cleaned `###` blocks.

**Step 5: Run tests**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py backend\tests\test_pipeline_quality_scoring.py -v
```

Expected:
- PASS

**Step 6: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_digest_validation.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "feat: add scoring v2 deterministic checks"
```

## Task 7: Apply issue penalties and score caps

**Files:**
- Modify: `backend/services/pipeline.py`
- Modify: `backend/tests/test_pipeline_quality_scoring.py`

**Step 1: Add issue penalty helper**

Rules:
- `major = -5`
- `minor = -2`
- cap total issue penalty at `-20`

**Step 2: Add score cap helper**

Rules:
- major factual/source -> `max 84`
- major frontload overclaim -> `max 89`
- major locale -> `max 89`
- major learner accessibility -> `max 92`

**Step 3: Compose final score**

```python
final_score = min(
    score_cap,
    deterministic_score + llm_score - issue_penalty - structural_penalty,
)
```

**Step 4: Run tests**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_quality_scoring.py -k "cap or penalty or final_score" -v
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "feat: add scoring v2 penalties and caps"
```

## Task 8: Persist richer scoring metadata

**Files:**
- Modify: `backend/services/pipeline.py`
- Modify: `backend/tests/test_pipeline.py`

**Step 1: Expand `pipeline_logs.debug_meta`**

Include:
- `quality_version`
- deterministic subscores
- llm subscores
- `quality_issues`
- `quality_caps_applied`

**Step 2: Expand saved `fact_pack`**

Add:
- `quality_version`
- `quality_breakdown`

**Step 3: Keep `news_posts.quality_score` as scalar**

Do not break existing consumers.

**Step 4: Run tests**

Run:

```bash
backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline.py backend\tests\test_pipeline_quality_scoring.py -v
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "feat: persist scoring v2 breakdown"
```

## Task 9: Calibrate against recent batches

**Files:**
- Create: `backend/scripts/rescore_recent_batches.py`
- Modify: `backend/tests/test_pipeline_quality_scoring.py`

**Step 1: Add a script to recompute scores for recent draft batches**

Inputs:
- run id
- batch id
- optional dry-run

Outputs:
- old score
- new score
- breakdown

**Step 2: Use it on recent known batches**

Check at least:
- `2026-04-13`
- `2026-04-14`

**Step 3: Record expected qualitative distribution**

Target:
- weak drafts should land `<85`
- good but imperfect drafts `85-92`
- exceptional rare `93+`

**Step 4: Commit**

```bash
git add backend/scripts/rescore_recent_batches.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "chore: add scoring v2 calibration script"
```

## Task 10: Final verification

**Files:**
- No new files unless bug fixes are required

**Step 1: Run focused backend test suite**

Run:

```bash
backend\.venv\Scripts\python -m pytest \
  backend\tests\test_news_digest_prompts.py \
  backend\tests\test_pipeline_digest_validation.py \
  backend\tests\test_pipeline_quality_scoring.py \
  backend\tests\test_pipeline.py \
  -v
```

**Step 2: Dry-run rescoring on a known recent batch**

Run:

```bash
backend\.venv\Scripts\python backend\scripts\rescore_recent_batches.py --batch 2026-04-14 --dry-run
```

**Step 3: Confirm score sanity**

Checklist:
- no issue-bearing digest receives 100
- body-only strong but frontload-weak digest is pulled down
- KO-localization issues visibly affect score
- issue caps apply deterministically

**Step 4: Final commit**

```bash
git add backend
git commit -m "feat: implement scoring v2 for daily digests"
```

## Notes For Implementation

- Reuse existing hard blockers. Do not duplicate save-validation logic inside scoring.
- Keep v1-compatible fields during rollout. Add `quality_version="v2"` instead of replacing old keys silently.
- Be defensive when parsing LLM judge output. Scoring should degrade gracefully, not explode the pipeline.
- Prefer pure helper functions for deterministic scoring so they are easy to unit test.
- Avoid making `quality_score` depend on Supabase writes or network side effects.
- Do not touch unrelated handbook/advisor dirty files in the working tree.

