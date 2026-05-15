# Quiz-Only News Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate daily news quiz generation from article body generation so quiz errors can be retried, validated, and fixed without regenerating the full digest.

**Architecture:** Daily digest writers generate only article/frontload/source content. After content is parsed, citation-substituted, cleaned, and post-processed, a separate quiz-only `gpt-5-mini` call generates all persona/locale quizzes for one digest type. The existing `_validate_and_shuffle_quiz_item` remains the final DB-facing guard, with one quiz-only retry before saving drafts without invalid quiz fields.

**Tech Stack:** FastAPI backend, OpenAI Chat Completions strict JSON schema, Pydantic models, Supabase `news_posts.guide_items`, pytest, ruff.

---

## Current Context

The current daily pipeline generates quizzes inside each persona writer response:

- `backend/services/agents/schemas/news_writer.py` requires `quiz_en` and `quiz_ko`.
- `backend/services/pipeline_digest.py` reads `data.get("quiz_en")` / `data.get("quiz_ko")` inside `_generate_digest`.
- `backend/services/pipeline_digest.py` later saves validated quizzes under `guide_items.quiz_poll_expert`, `guide_items.quiz_poll_learner`, and `guide_items.quiz_poll_beginner`.
- `backend/services/pipeline_quality.py` scores body/frontload quality, but does not score `guide_items.quiz_poll_*`.

This means a digest can receive a high QC score while quiz answer/explanation semantics are wrong. The fix should make quizzes a separate artifact generated from the final article bodies.

## Constraints

- Follow repository main-only workflow. Do not create a feature branch unless explicitly requested.
- Use `backend/.venv` for Python commands.
- Keep DB shape unchanged: frontend still expects `guide_items.quiz_poll_{persona}` with `question`, `options`, `answer`, and `explanation`.
- Keep existing user quiz response schema unchanged.
- Do not introduce a migration for this change.
- Keep the existing `_validate_and_shuffle_quiz_item` behavior and the negation repair guard.

---

### Task 1: Remove Quiz Fields From Daily Writer Schema

**Files:**
- Modify: `backend/services/agents/schemas/news_writer.py`
- Test: `backend/tests/test_news_writer_schema.py`

**Step 1: Write failing schema tests**

Update `backend/tests/test_news_writer_schema.py` so the daily writer schema no longer requires or exposes `quiz_en` / `quiz_ko`.

Expected assertions:

```python
schema = build_news_writer_json_schema(["https://example.com/a"])
props = schema["schema"]["properties"]
required = schema["schema"]["required"]

assert "quiz_en" not in props
assert "quiz_ko" not in props
assert "quiz_en" not in required
assert "quiz_ko" not in required
```

Keep `QuizOneLocale` tests for now only if the class is still reused by the new quiz-only schema. If moved, update imports accordingly.

**Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_news_writer_schema.py -q
```

Expected: FAIL because `quiz_en` and `quiz_ko` are still in the writer schema.

**Step 3: Modify schema**

In `backend/services/agents/schemas/news_writer.py`:

- Remove `quiz_en` and `quiz_ko` from `NewsWriterOutput`.
- Remove `quiz_en` and `quiz_ko` from the strict schema `required` list.
- Remove `quiz_en` and `quiz_ko` from `properties`.
- Keep `QuizOneLocale` only if Task 2 imports it from this file; otherwise move it into the new quiz schema module.

**Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_news_writer_schema.py -q
```

Expected: PASS.

---

### Task 2: Add Strict Quiz-Only Schema

**Files:**
- Create: `backend/services/agents/schemas/news_quiz.py`
- Test: `backend/tests/test_news_quiz_schema.py`

**Step 1: Write failing schema tests**

Create `backend/tests/test_news_quiz_schema.py`.

Test the new schema shape:

```python
from services.agents.schemas.news_quiz import build_news_quiz_json_schema


def test_quiz_schema_requires_all_persona_locale_keys():
    schema = build_news_quiz_json_schema()
    props = schema["schema"]["properties"]
    required = schema["schema"]["required"]

    for persona in ["expert", "learner", "beginner"]:
        for locale in ["en", "ko"]:
            key = f"{persona}_{locale}"
            assert key in props
            assert key in required


def test_quiz_item_uses_answer_index_contract():
    schema = build_news_quiz_json_schema()
    item = schema["schema"]["properties"]["expert_en"]
    assert item["required"] == ["question", "options", "answer_index", "explanation"]
    assert item["properties"]["answer_index"]["minimum"] == 0
    assert item["properties"]["answer_index"]["maximum"] == 3
    assert item["properties"]["options"]["minItems"] == 4
    assert item["properties"]["options"]["maxItems"] == 4
```

**Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_news_quiz_schema.py -q
```

Expected: FAIL because `news_quiz.py` does not exist.

**Step 3: Implement schema**

Create `backend/services/agents/schemas/news_quiz.py`.

Implementation outline:

```python
from __future__ import annotations

from typing import Any


DAILY_QUIZ_PERSONAS = ("expert", "learner", "beginner")
DAILY_QUIZ_LOCALES = ("en", "ko")


def _quiz_locale_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["question", "options", "answer_index", "explanation"],
        "properties": {
            "question": {"type": "string"},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 4,
                "maxItems": 4,
            },
            "answer_index": {"type": "integer", "minimum": 0, "maximum": 3},
            "explanation": {"type": "string"},
        },
    }


def build_news_quiz_json_schema() -> dict[str, Any]:
    properties = {
        f"{persona}_{locale}": _quiz_locale_schema()
        for persona in DAILY_QUIZ_PERSONAS
        for locale in DAILY_QUIZ_LOCALES
    }
    return {
        "name": "news_quiz_output",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": list(properties.keys()),
            "properties": properties,
        },
    }
```

**Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_news_quiz_schema.py -q
```

Expected: PASS.

---

### Task 3: Add Quiz-Only Prompt

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py`
- Test: `backend/tests/test_news_digest_prompts.py`

**Step 1: Write failing prompt test**

Add a test that imports `get_digest_quiz_prompt` and checks the important contract.

```python
from services.agents.prompts_news_pipeline import get_digest_quiz_prompt


def test_quiz_only_prompt_uses_final_body_and_forbids_contradictions():
    prompt = get_digest_quiz_prompt("research")

    assert "Generate quizzes only" in prompt
    assert "Use the final article bodies as the source of truth" in prompt
    assert "Do not introduce facts that are absent from the final body" in prompt
    assert "answer_index MUST point to the option your explanation treats as true" in prompt
    assert "The explanation MUST NOT contradict the selected option" in prompt
    assert "expert_en" in prompt
    assert "beginner_ko" in prompt
```

**Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_news_digest_prompts.py::test_quiz_only_prompt_uses_final_body_and_forbids_contradictions -q
```

Expected: FAIL because the function does not exist.

**Step 3: Implement prompt function**

Add `get_digest_quiz_prompt(digest_type: str) -> str` near existing digest prompt helpers.

Prompt requirements:

- Generate quizzes only.
- Use final article bodies as source of truth.
- Return exactly six keys: `expert_en`, `expert_ko`, `learner_en`, `learner_ko`, `beginner_en`, `beginner_ko`.
- Expert quiz: analytical but answerable from body.
- Learner quiz: conceptual/factual understanding.
- Beginner quiz: misconception check, not recall.
- No answer may be a date, company name, product name, benchmark score, funding amount, or raw number unless the persona is expert and the question explicitly checks a paper claim.
- `answer_index` must point to the option treated as true.
- Explanation must first justify the correct option, then optionally explain one tempting wrong option.
- Do not cite URLs in quiz fields.

**Step 4: Run prompt tests**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_news_digest_prompts.py -q
```

Expected: PASS.

---

### Task 4: Stop Reading Quizzes From Body Writer Responses

**Files:**
- Modify: `backend/services/pipeline_digest.py`
- Test: `backend/tests/test_pipeline_digest_validation.py`

**Step 1: Write failing test**

Add or update a test that mocks persona writer responses without `quiz_en` / `quiz_ko` and expects digest generation to continue.

Expected assertions:

```python
assert "quiz_poll_expert" in payload["guide_items"]
assert "quiz_poll_learner" in payload["guide_items"]
assert "quiz_poll_beginner" in payload["guide_items"]
```

The test should arrange the new quiz-only call to return valid quiz payloads.

**Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py -q
```

Expected: FAIL because `_generate_digest` still expects quiz fields from persona writer output.

**Step 3: Remove inline quiz capture**

In `backend/services/pipeline_digest.py`, remove this logic from the persona writer loop:

```python
quiz_en = data.get("quiz_en")
quiz_ko = data.get("quiz_ko")
if quiz_en or quiz_ko:
    persona_quizzes[persona_name] = {}
    ...
```

Keep the `persona_quizzes` variable only if Task 5 uses it as the output of the quiz-only helper.

**Step 4: Run test**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py -q
```

Expected: still FAIL until Task 5 implements quiz-only generation.

---

### Task 5: Implement Quiz-Only Generator

**Files:**
- Modify: `backend/services/pipeline_digest.py`
- Test: `backend/tests/test_pipeline_digest_validation.py`
- Test: `backend/tests/test_weekly_quiz_shuffle.py`

**Step 1: Write failing behavior tests**

Add tests covering:

1. Quiz-only generator receives final post-processed bodies, not raw source articles.
2. Valid quiz-only payload saves `guide_items.quiz_poll_{persona}` for EN and KO rows.
3. Invalid quiz-only payload retries once.
4. Invalid after retry does not fail digest save; it saves content without bad quiz fields and logs a warning stage.

Expected test shape:

```python
assert payload["guide_items"]["quiz_poll_expert"]["question"]
assert payload["guide_items"]["quiz_poll_learner"]["answer"] in payload["guide_items"]["quiz_poll_learner"]["options"]
assert payload["guide_items"]["quiz_poll_beginner"]["answer"] in payload["guide_items"]["quiz_poll_beginner"]["options"]
```

**Step 2: Run tests to verify failures**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py -q
```

Expected: FAIL because helper does not exist.

**Step 3: Implement helper**

Add helper in `backend/services/pipeline_digest.py`:

```python
async def _generate_digest_quizzes(
    *,
    digest_type: str,
    personas: dict[str, PersonaOutput],
    client: Any,
    supabase: Any,
    run_id: str,
) -> tuple[dict[str, dict[str, dict]], dict[str, Any]]:
    ...
```

Use:

- `settings.openai_model_light`
- `response_format={"type": "json_schema", "json_schema": build_news_quiz_json_schema()}`
- `max_tokens` around `2500`
- `reasoning_effort="low"` or default if the compatibility helper requires omission
- `service_tier="flex"`
- `prompt_cache_key=f"quiz-{digest_type}"`

Build user input from final bodies:

```text
Digest type: research

## expert_en
<final expert EN markdown>

## expert_ko
<final expert KO markdown>

...
```

Do not include raw source article text. The quiz should test the final published article.

**Step 4: Normalize output through existing validator**

For each returned key:

- Split key into persona and locale.
- Pass raw item to `_validate_and_shuffle_quiz_item(raw, label=f"Daily quiz {digest_type}/{persona}/{locale}")`.
- If valid, store in `persona_quizzes[persona][locale]`.
- If any required persona/locale quiz is invalid, retry once.
- After retry, keep valid quizzes and omit invalid ones. Do not fabricate fallback quiz.

**Step 5: Log quiz stage**

Use `_log_stage`:

- success stage: `quiz:{digest_type}`
- failed or partial stage: `quiz:{digest_type}`
- `debug_meta`: include valid count, missing keys, retry count.
- usage: merge quiz usage into cumulative usage.

**Step 6: Run tests**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py backend\tests\test_weekly_quiz_shuffle.py -q
```

Expected: PASS.

---

### Task 6: Wire Quiz-Only Generator After Body Post-Processing

**Files:**
- Modify: `backend/services/pipeline_digest.py`
- Test: `backend/tests/test_pipeline_digest_validation.py`

**Step 1: Move quiz generation to the correct pipeline location**

Call `_generate_digest_quizzes` only after:

- citation substitution has already happened,
- `_clean_writer_output` has already happened,
- locale recovery has already happened,
- `_find_digest_blockers` has passed,
- `_check_digest_quality` has completed or immediately before saving rows.

Preferred location: after `_check_digest_quality`, before `for locale in ("en", "ko"):` save loop.

Reason: quiz generation should use the final body that will be saved.

**Step 2: Ensure persona rerun preservation works**

For `from_stage="beginner"` reruns:

- If only beginner is regenerated, quiz-only generation should still read preserved expert/learner bodies from `personas`.
- It can regenerate all six quiz fields for that digest type. This is acceptable because quizzes are cheap and should stay consistent with final body.

**Step 3: Ensure quality-only rerun does not regenerate quizzes**

`from_stage="quality"` currently skips `_generate_digest`; leave it unchanged. Quality-only reruns should not call quiz generation.

**Step 4: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py backend\tests\test_pipeline_rerun.py -q
```

Expected: PASS.

---

### Task 7: Update Prompt Tests and Remove Obsolete Inline Quiz Expectations

**Files:**
- Modify: `backend/tests/test_news_digest_prompts.py`
- Modify: `backend/tests/test_pipeline_digest_validation.py`
- Modify: `backend/tests/test_news_writer_schema.py`

**Step 1: Remove old expectations**

Remove assertions that daily digest persona prompts must include `quiz_en` / `quiz_ko` in the writer output schema.

Do not remove beginner quiz intent tests entirely. Move those assertions to `get_digest_quiz_prompt`.

**Step 2: Add quiz-only prompt expectations**

Assert:

- expert/learner/beginner differentiation exists.
- beginner quiz is a misconception check.
- quiz uses final body as source of truth.
- answer/explanation contradiction is forbidden.

**Step 3: Run test suite slice**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_news_writer_schema.py backend\tests\test_news_quiz_schema.py backend\tests\test_news_digest_prompts.py backend\tests\test_pipeline_digest_validation.py -q
```

Expected: PASS.

---

### Task 8: Add Operational Visibility

**Files:**
- Modify: `backend/services/pipeline_digest.py`
- Test: `backend/tests/test_pipeline_digest_validation.py`
- Optional Modify: `frontend/src/pages/admin/pipeline-runs/[runId].astro`
- Optional Test: `frontend/tests/admin-pipeline-runs-structure.test.cjs`

**Step 1: Backend log coverage**

Ensure `_log_stage` emits `quiz:{digest_type}` with:

```python
debug_meta={
    "valid_quiz_count": valid_count,
    "missing_quiz_keys": missing_keys,
    "retry_count": retry_count,
    "model": settings.openai_model_light,
}
```

**Step 2: Admin UI decision**

If admin stage timeline already renders unknown stages generically, do not change frontend.

Only modify frontend if current UI filters stage labels and hides `quiz:*`.

**Step 3: Run tests**

Backend:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py -q
```

Frontend only if touched:

```powershell
cd frontend; npm test -- admin-pipeline-runs-structure.test.cjs
```

Expected: PASS.

---

### Task 9: End-to-End Verification Without Live Publishing

**Files:**
- No code changes expected.

**Step 1: Run unit test slice**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m pytest backend\tests\test_news_writer_schema.py backend\tests\test_news_quiz_schema.py backend\tests\test_news_digest_prompts.py backend\tests\test_pipeline_digest_validation.py backend\tests\test_pipeline_rerun.py backend\tests\test_weekly_quiz_shuffle.py -q
```

Expected: PASS.

**Step 2: Run lint**

Run:

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python -m ruff check backend\services\agents\schemas\news_writer.py backend\services\agents\schemas\news_quiz.py backend\services\agents\prompts_news_pipeline.py backend\services\pipeline_digest.py backend\tests\test_news_writer_schema.py backend\tests\test_news_quiz_schema.py backend\tests\test_news_digest_prompts.py backend\tests\test_pipeline_digest_validation.py
```

Expected: PASS.

**Step 3: Optional dry run**

If OpenAI/Supabase credentials are available and the user explicitly wants a dry run, run a non-publishing pipeline rerun against a safe batch or local mocks. Do not overwrite published rows unless the user asks.

---

### Task 10: Commit

**Files:**
- Stage only files touched for quiz-only generation.
- Do not include unrelated dirty files unless they are part of the same user-approved commit.

**Step 1: Inspect status**

Run:

```powershell
git status --short
```

Expected: show quiz-only files plus existing unrelated dirty files from prior work.

**Step 2: Stage exact files**

Run:

```powershell
git add backend/services/agents/schemas/news_writer.py backend/services/agents/schemas/news_quiz.py backend/services/agents/prompts_news_pipeline.py backend/services/pipeline_digest.py backend/tests/test_news_writer_schema.py backend/tests/test_news_quiz_schema.py backend/tests/test_news_digest_prompts.py backend/tests/test_pipeline_digest_validation.py docs/plans/2026-05-15-quiz-only-news-pipeline.md
```

Include `backend/services/pipeline.py` and `backend/tests/test_weekly_quiz_shuffle.py` only if the existing negation repair change is intended to be part of this commit.

**Step 3: Commit**

Run:

```powershell
git commit -m "fix: generate news quizzes after digest bodies"
```

Expected: commit succeeds.

**Step 4: Push only if requested**

Run:

```powershell
git push origin main
```

Expected: push succeeds.

