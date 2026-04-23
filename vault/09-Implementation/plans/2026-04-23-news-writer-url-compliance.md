# News Writer URL Compliance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate URL hallucination in daily news writer by (a) tuning GPT-5 reasoning params, (b) migrating writer output to strict JSON schema with `citations[].url` as an allowlist enum so hallucinated URLs are rejected at the API layer.

**Architecture:** Three phases executed in order.
- **Phase 0 — Baseline**: Regenerate Apr 23 news from scratch (discard current state) and confirm the existing Level 0 gate (`url_validation_failed=True` → `auto_publish_eligible=False` → `promote_drafts` skips) actually prevents bad publishes when rules are followed. This gives us a known-good comparison point.
- **Phase 1 — Quick wins (params)**: Raise writer's `reasoning_effort` from default `low` → `high`, keep QC at `low` (QC is verification, not generation). Remove the now-dead `temperature=0.4` kwarg (compat layer strips it silently). Measure URL hallucination rate before/after on 2-3 runs.
- **Phase 2 — Schema enforcement (architectural)**: Migrate writer output from `response_format={"type": "json_object"}` → strict `json_schema` mode. Add `citations: [{n, url}]` field where `url` is an `enum` of `fact_pack.news_items[].url`. Switch body text to `[CITE_N]` placeholders; substitute in post-processing. The OpenAI API now rejects hallucinated URLs before we ever see them.

**Tech Stack:** Python 3.11, OpenAI Python SDK (chat.completions with `response_format`), Pydantic v2, pytest, Supabase, FastAPI (Railway), Astro frontend (for admin editor — no changes here).

**Non-goals (explicit):**
- Weekly writer migration (same approach; deferred to a follow-up plan once Phase 2 is proven on daily)
- CP (community_pulse) writer migration (separate pipeline, smaller attack surface)
- QC-side structural changes (QC output is already narrow scoring JSON)

**Key reference files (read before starting any task):**
- `backend/services/agents/client.py:37-92` — GPT-5 compat layer (`_apply_gpt5_compat`, `compat_create_kwargs`, `build_completion_kwargs`)
- `backend/services/pipeline_digest.py:629-658` — writer call site
- `backend/services/pipeline_quality.py:999-1035` — `validate_citation_urls` (URL allowlist check)
- `backend/services/pipeline_persistence.py:72-130` — `promote_drafts` (gate enforcement)
- `backend/services/agents/prompts_news_pipeline.py:577-629` — `HALLUCINATION_GUARD`, URL rules

---

## Current State (for the executor)

The writer currently runs `gpt-5` with these effective kwargs after the compat layer:

```python
# What code passes:
chat.completions.create(
    model="gpt-5",
    messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
    response_format={"type": "json_object"},
    temperature=0.4,              # ← silently stripped by _apply_gpt5_compat
    max_tokens=24000,             # ← rewritten to max_completion_tokens=72000
)

# What the API actually receives:
chat.completions.create(
    model="gpt-5",
    messages=[...],
    response_format={"type": "json_object"},
    max_completion_tokens=72000,
    reasoning_effort="low",       # ← injected by _apply_gpt5_compat default
)
```

Writer JSON output shape (per `parse_ai_json` in `pipeline_digest.py:651-658`):
```json
{
  "headline": "...", "headline_ko": "...",
  "excerpt": "...", "excerpt_ko": "...",
  "en": "... [1](https://example.com/a) ... [2](https://example.com/b) ...",
  "ko": "... [1](https://example.com/a) ... [2](https://example.com/b) ...",
  "tags": [...], "focus_items": [...], "focus_items_ko": [...],
  "quiz": {...}
}
```

URL validation runs in QC (`_check_digest_quality`) — it extracts `[N](URL)` pairs from `en`/`ko` and compares against `fact_pack.news_items[].url`. Unknown URLs set `fact_pack.url_validation_failed=True` + `fact_pack.auto_publish_eligible=False`. Cron `promote_drafts` then leaves the post in `draft` status.

The Apr 23 research failure was not a gate failure — the gate worked. It was bypassed manually by `c:\tmp\publish_apr23.py` which set `auto_publish_eligible=True` and `status=published` while the hardcoded marker strip silently missed the actual hallucinated URLs (`liner.com/review/...`, `axiomlogica.com/...`). The gate itself is sound.

---

## Chunk 1: Phase 0 — Baseline Validation

### Task 0.1: Revert Apr 23 research posts to draft

**Files:**
- Run: `c:\tmp\revert_apr23_to_draft.py` (new, temporary script — do NOT commit)
- Reference: `c:\tmp\apr23_backup.json` (existing backup from prior run)

**Step 1: Write the revert script**

Create `c:\tmp\revert_apr23_to_draft.py`:

```python
"""Revert Apr 23 daily news posts to pre-bypass state.
Sets status=draft, restores fact_pack flags so gate logic governs re-publishing.
"""
import io, json, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(r"c:\Users\amy\Desktop\0to1log\backend\.env")
sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"],
)

SLUGS = [
    "2026-04-23-research-digest",
    "2026-04-23-research-digest-ko",
    "2026-04-23-business-digest",
    "2026-04-23-business-digest-ko",
]

rows = sb.table("news_posts").select("id,slug,fact_pack").in_("slug", SLUGS).execute().data
for row in rows:
    fp = row.get("fact_pack") or {}
    fp["auto_publish_eligible"] = False
    fp["manual_bypass_reverted_at"] = "2026-04-23T00:00:00Z"
    sb.table("news_posts").update({"status": "draft", "fact_pack": fp}).eq("id", row["id"]).execute()
    print(f"  {row['slug']}: reverted to draft")
```

**Step 2: Run the script**

Run: `cd c:\Users\amy\Desktop\0to1log\backend && .venv\Scripts\python c:\tmp\revert_apr23_to_draft.py`

Expected output: 4 lines, each "reverted to draft".

**Step 3: Verify via DB query**

Run:
```bash
cd c:\Users\amy\Desktop\0to1log\backend && .venv\Scripts\python -c "
import os
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
sb = create_client(os.environ['SUPABASE_URL'], os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])
rows = sb.table('news_posts').select('slug,status').like('slug', '2026-04-23%').execute().data
for r in rows: print(f'{r[\"slug\"]}: {r[\"status\"]}')
"
```

Expected: all 4 rows show `draft`.

**Step 4: Commit — N/A**

No code changes. Script is temporary and lives in `c:\tmp\`.

---

### Task 0.2: Regenerate Apr 23 news via admin pipeline

**Files:**
- Trigger via: frontend admin UI (`/admin`) or direct API call
- Read: `backend/routers/admin.py` (to confirm endpoint path)

**Step 1: Locate the admin regenerate endpoint**

Run: `grep -n "api/admin/news" backend/routers/admin.py` (or use the Grep tool).

Expected: endpoint `POST /api/admin/news` or similar. Copy exact path.

**Step 2: Delete existing Apr 23 rows (full fresh run)**

Run:
```bash
cd c:\Users\amy\Desktop\0to1log\backend && .venv\Scripts\python -c "
import os
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
sb = create_client(os.environ['SUPABASE_URL'], os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])
for slug_prefix in ['2026-04-23-research-digest', '2026-04-23-business-digest']:
    sb.table('news_posts').delete().like('slug', f'{slug_prefix}%').execute()
print('Deleted Apr 23 news_posts rows')
"
```

Expected: "Deleted Apr 23 news_posts rows".

**Step 3: Trigger regeneration**

Open `http://localhost:4321/admin` → "Generate News" → set date to 2026-04-23 → click.

OR direct API (if backend running locally):
```bash
curl -X POST "http://localhost:8000/api/admin/news" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"batch_date": "2026-04-23"}'
```

Expected: `202 Accepted`. Check Railway logs for pipeline completion (~5-10 min).

**Step 4: Inspect URL validation outcome**

Run:
```bash
cd c:\Users\amy\Desktop\0to1log\backend && .venv\Scripts\python -c "
import os, json
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
sb = create_client(os.environ['SUPABASE_URL'], os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])
rows = sb.table('news_posts').select('slug,status,quality_score,fact_pack').like('slug', '2026-04-23%').execute().data
for r in rows:
    fp = r.get('fact_pack') or {}
    print(f'{r[\"slug\"]:<42} status={r[\"status\"]:<10} score={r.get(\"quality_score\")} url_fail={fp.get(\"url_validation_failed\")} unknown={len(fp.get(\"url_validation_failures\") or [])}')
"
```

Expected outcomes:
- **Best case**: `url_fail=False` for all 4 rows → gate passes naturally, confirms writer CAN comply sometimes.
- **Typical case**: 1-3 rows with `url_fail=True` → gate correctly keeps them as `draft`. This is the baseline we'll improve in Phase 1-2.
- **Bad case**: `url_fail=True` but `status=published` → gate is broken, STOP and investigate `promote_drafts` before proceeding.

**Step 5: Record baseline in plan**

Append to this plan file under a new heading `## Phase 0 Baseline Results` with: date of run, url_fail count per post, unknown URLs per post.

**Step 6: Commit**

```bash
git add vault/09-Implementation/plans/2026-04-23-news-writer-url-compliance.md
git commit -m "docs(plan): record Phase 0 baseline for URL compliance plan"
```

---

## Chunk 2: Phase 1 — GPT-5 Param Tuning

### Task 1.1: Add per-call `reasoning_effort` override to compat layer

**Files:**
- Modify: `backend/services/agents/client.py:42-64` (`_apply_gpt5_compat`)
- Test: `backend/tests/test_agents_client.py` (may need to create if absent)

**Step 1: Check if test file exists**

Run: `ls backend/tests/ | grep -i client`

If no `test_agents_client.py` exists, create it in Step 2.

**Step 2: Write the failing test**

Create/modify `backend/tests/test_agents_client.py`:

```python
from backend.services.agents.client import _apply_gpt5_compat


def test_gpt5_default_reasoning_effort_is_low():
    kwargs = {"model": "gpt-5", "max_tokens": 1000, "temperature": 0.4}
    out = _apply_gpt5_compat(kwargs, "gpt-5")
    assert out["reasoning_effort"] == "low"
    assert "temperature" not in out
    assert out["max_completion_tokens"] == 3000


def test_gpt5_caller_can_override_reasoning_effort_to_high():
    kwargs = {"model": "gpt-5", "max_tokens": 1000, "reasoning_effort": "high"}
    out = _apply_gpt5_compat(kwargs, "gpt-5")
    assert out["reasoning_effort"] == "high"


def test_non_gpt5_model_untouched():
    kwargs = {"model": "gpt-4.1", "max_tokens": 1000, "temperature": 0.4}
    out = _apply_gpt5_compat(kwargs, "gpt-4.1")
    assert out["temperature"] == 0.4
    assert "reasoning_effort" not in out
```

**Step 3: Run the test**

Run: `cd backend && .venv\Scripts\pytest tests/test_agents_client.py -v`

Expected: `test_gpt5_caller_can_override_reasoning_effort_to_high` should **PASS already** because line 61 (`if ... and "reasoning_effort" not in kwargs:`) already respects caller override. The default-low and non-gpt5 tests should also pass.

**If any fails**: the existing `_apply_gpt5_compat` is broken — fix before proceeding.

**Step 4: Commit (tests only, no code change needed)**

```bash
git add backend/tests/test_agents_client.py
git commit -m "test: cover gpt-5 compat reasoning_effort override"
```

---

### Task 1.2: Plumb `reasoning_effort` through `build_completion_kwargs`

**Files:**
- Modify: `backend/services/agents/client.py:76-92` (`build_completion_kwargs`)
- Test: `backend/tests/test_agents_client.py` (extend)

**Step 1: Write the failing test**

Append to `backend/tests/test_agents_client.py`:

```python
from backend.services.agents.client import build_completion_kwargs


def test_build_completion_kwargs_passes_reasoning_effort_to_gpt5():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
        reasoning_effort="high",
    )
    assert out["reasoning_effort"] == "high"


def test_build_completion_kwargs_omits_reasoning_effort_when_none():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
    )
    # Still gets the default "low" from _apply_gpt5_compat
    assert out["reasoning_effort"] == "low"
```

**Step 2: Run test — expect failure**

Run: `cd backend && .venv\Scripts\pytest tests/test_agents_client.py::test_build_completion_kwargs_passes_reasoning_effort_to_gpt5 -v`

Expected: FAIL (signature doesn't accept `reasoning_effort`).

**Step 3: Add `reasoning_effort` param**

Edit `backend/services/agents/client.py:76-92`:

```python
def build_completion_kwargs(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.3,
    response_format: dict | None = None,
    reasoning_effort: str | None = None,
) -> dict:
    """Build kwargs for chat.completions.create, handling model differences."""
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if _uses_max_completion_tokens(model):
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
    kwargs["temperature"] = temperature
    if response_format:
        kwargs["response_format"] = response_format
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    return _apply_gpt5_compat(kwargs, model)
```

**Step 4: Run tests**

Run: `cd backend && .venv\Scripts\pytest tests/test_agents_client.py -v`

Expected: all pass.

**Step 5: Commit**

```bash
git add backend/services/agents/client.py backend/tests/test_agents_client.py
git commit -m "feat(agents): add reasoning_effort param to build_completion_kwargs"
```

---

### Task 1.3: Raise writer `reasoning_effort` to `high`

**Files:**
- Modify: `backend/services/pipeline_digest.py:636-648` (writer `chat.completions.create` call)

**Step 1: Read the current call**

Read `backend/services/pipeline_digest.py:629-660` to confirm the exact shape of the `compat_create_kwargs` call.

**Step 2: Add `reasoning_effort="high"` kwarg + remove dead `temperature`**

Edit lines 636-648:

```python
response = await asyncio.wait_for(
    client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            # temperature removed: stripped by gpt-5 compat layer
            max_tokens=24000,
            reasoning_effort="high",
        )
    ),
    timeout=240,
)
```

Note: bump `timeout=240` → `timeout=480` (8 min). High reasoning effort ~2-3x slower.

**Step 3: Manual verification (no unit test — this is a tuning change)**

Re-run Apr 23 regeneration (same procedure as Task 0.2 Steps 2-4).

Record new baseline under `## Phase 1 Run 1 Results` heading in this plan file. Compare to Phase 0 baseline.

Expected delta: `url_fail=True` count should drop (target: 0-1 out of 4 posts, down from baseline).

**Step 4: If improvement is clear, commit**

```bash
git add backend/services/pipeline_digest.py
git commit -m "feat(news): raise writer reasoning_effort to high for URL compliance"
```

**Step 5: If no improvement or regression, open an investigation note**

Create `vault/12-Journal-&-Decisions/2026-04-23-reasoning-effort-null-result.md` with observed outcomes. Do NOT revert (high effort has other benefits: better claim calibration, better translation parity). Proceed to Phase 2.

---

### Task 1.4: Remove dead `temperature` kwargs elsewhere

**Files:**
- Modify: `backend/services/pipeline.py:2395-2420` (weekly writer)
- Modify: `backend/services/pipeline_quality.py:441-480` (QC calls)
- Keep temperature for non-gpt5 call sites (if any).

**Step 1: Grep for remaining `temperature=` usages with gpt-5**

Run: `grep -rn "temperature=" backend/services/ | grep -v test_ | grep -v __pycache__`

Categorize each hit:
- Goes to `compat_create_kwargs(settings.openai_model_main, ...)` where `openai_model_main="gpt-5"` → **dead code, remove**
- Uses explicit non-gpt5 model → keep

**Step 2: Remove dead `temperature` kwargs**

For each confirmed-dead site (weekly writer, daily QC expert/learner), remove the `temperature=X.X` line.

**Step 3: Run full test suite**

Run: `cd backend && .venv\Scripts\pytest tests/ -v --tb=short`

Expected: no regressions.

**Step 4: Commit**

```bash
git add backend/services/pipeline.py backend/services/pipeline_quality.py
git commit -m "chore(agents): remove dead temperature kwargs from gpt-5 call sites"
```

---

## Chunk 3: Phase 2 — JSON Schema with Enum Allowlist

### Task 2.1: Define Pydantic schema for writer output

**Files:**
- Create: `backend/services/agents/schemas/news_writer.py`
- Test: `backend/tests/test_news_writer_schema.py`

**Step 1: Write the failing test**

Create `backend/tests/test_news_writer_schema.py`:

```python
import pytest
from pydantic import ValidationError
from backend.services.agents.schemas.news_writer import (
    NewsWriterOutput,
    Citation,
    build_news_writer_json_schema,
)


def test_valid_output_passes():
    data = {
        "headline": "Foo launches bar",
        "headline_ko": "푸가 바 출시",
        "excerpt": "summary",
        "excerpt_ko": "요약",
        "en": "Foo launched [CITE_1] today.",
        "ko": "푸는 오늘 [CITE_1] 출시했다.",
        "citations": [{"n": 1, "url": "https://example.com/a"}],
        "tags": ["ai"],
        "focus_items": ["foo"],
        "focus_items_ko": ["푸"],
        "quiz": {"en": {"q": "Q?", "a": "A", "options": ["A","B","C","D"]},
                 "ko": {"q": "Q?", "a": "A", "options": ["A","B","C","D"]}},
    }
    out = NewsWriterOutput(**data)
    assert out.citations[0].url == "https://example.com/a"


def test_empty_citations_allowed_for_zero_citation_body():
    data = {
        "headline": "x", "headline_ko": "x",
        "excerpt": "x", "excerpt_ko": "x",
        "en": "No citations here.", "ko": "인용 없음.",
        "citations": [],
        "tags": [], "focus_items": [], "focus_items_ko": [],
        "quiz": {"en": {"q":"Q","a":"A","options":["A","B","C","D"]},
                 "ko": {"q":"Q","a":"A","options":["A","B","C","D"]}},
    }
    NewsWriterOutput(**data)  # should not raise


def test_citation_without_url_rejected():
    with pytest.raises(ValidationError):
        Citation(n=1, url="")


def test_build_schema_embeds_enum_from_allowlist():
    allowlist = ["https://a.com", "https://b.com/p"]
    schema = build_news_writer_json_schema(allowlist)
    citation_item = schema["schema"]["properties"]["citations"]["items"]
    assert citation_item["properties"]["url"]["enum"] == allowlist
    assert schema["strict"] is True
    assert citation_item["additionalProperties"] is False


def test_build_schema_with_empty_allowlist_uses_placeholder():
    # Edge case: if fact_pack has no URLs, schema must still be valid.
    # Expected behavior: empty allowlist raises, OR uses a single placeholder
    # like ["about:blank"] to keep enum non-empty. Pick one and document.
    with pytest.raises(ValueError):
        build_news_writer_json_schema([])
```

**Step 2: Run tests — expect failures**

Run: `cd backend && .venv\Scripts\pytest tests/test_news_writer_schema.py -v`

Expected: all FAIL (module not found).

**Step 3: Create the schema module**

Create `backend/services/agents/schemas/__init__.py` (empty).

Create `backend/services/agents/schemas/news_writer.py`:

```python
"""Pydantic + JSON schema for news writer strict output.

The OpenAI `response_format={"type": "json_schema", "strict": true, ...}` mode
rejects responses where `citations[].url` is not in the enum (the allowlist
derived from fact_pack.news_items). Body text references citations by
placeholder [CITE_N] rather than inline [N](URL) — substitution happens in
post-processing (see apply_citations in pipeline_digest).
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    n: int = Field(ge=1, le=50)
    url: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("url must start with http(s)://")
        return v


class QuizOneLocale(BaseModel):
    q: str
    a: str
    options: list[str] = Field(min_length=4, max_length=4)


class QuizBlock(BaseModel):
    en: QuizOneLocale
    ko: QuizOneLocale


class NewsWriterOutput(BaseModel):
    headline: str
    headline_ko: str
    excerpt: str
    excerpt_ko: str
    en: str
    ko: str
    citations: list[Citation]
    tags: list[str]
    focus_items: list[str]
    focus_items_ko: list[str]
    quiz: QuizBlock


def build_news_writer_json_schema(allowlist_urls: list[str]) -> dict[str, Any]:
    """Build OpenAI strict json_schema with citations[].url as an enum."""
    if not allowlist_urls:
        raise ValueError(
            "Cannot build writer schema with empty allowlist — "
            "fact_pack.news_items must have at least one URL."
        )
    # Dedup while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for u in allowlist_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return {
        "name": "news_writer_output",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "headline","headline_ko","excerpt","excerpt_ko",
                "en","ko","citations","tags","focus_items","focus_items_ko","quiz",
            ],
            "properties": {
                "headline": {"type": "string"},
                "headline_ko": {"type": "string"},
                "excerpt": {"type": "string"},
                "excerpt_ko": {"type": "string"},
                "en": {"type": "string"},
                "ko": {"type": "string"},
                "citations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["n", "url"],
                        "properties": {
                            "n": {"type": "integer", "minimum": 1, "maximum": 50},
                            "url": {"type": "string", "enum": unique},
                        },
                    },
                },
                "tags": {"type": "array", "items": {"type": "string"}},
                "focus_items": {"type": "array", "items": {"type": "string"}},
                "focus_items_ko": {"type": "array", "items": {"type": "string"}},
                "quiz": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["en", "ko"],
                    "properties": {
                        "en": _quiz_locale_schema(),
                        "ko": _quiz_locale_schema(),
                    },
                },
            },
        },
    }


def _quiz_locale_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["q", "a", "options"],
        "properties": {
            "q": {"type": "string"},
            "a": {"type": "string"},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 4,
                "maxItems": 4,
            },
        },
    }
```

**Step 4: Run tests — all should pass**

Run: `cd backend && .venv\Scripts\pytest tests/test_news_writer_schema.py -v`

Expected: all 5 tests PASS.

**Step 5: Commit**

```bash
git add backend/services/agents/schemas/__init__.py backend/services/agents/schemas/news_writer.py backend/tests/test_news_writer_schema.py
git commit -m "feat(news): add strict json_schema with citation enum for writer"
```

---

### Task 2.2: Implement placeholder → `[N](URL)` substitution

**Files:**
- Create: `backend/services/agents/citation_substitution.py`
- Test: `backend/tests/test_citation_substitution.py`

**Step 1: Write the failing test**

Create `backend/tests/test_citation_substitution.py`:

```python
import pytest
from backend.services.agents.citation_substitution import (
    apply_citations,
    CitationSubstitutionError,
)


def test_simple_substitution():
    body = "Foo launched [CITE_1] today."
    citations = [{"n": 1, "url": "https://example.com/a"}]
    out = apply_citations(body, citations)
    assert out == "Foo launched [1](https://example.com/a) today."


def test_multiple_placeholders_same_citation():
    body = "A [CITE_1] and B [CITE_1]."
    citations = [{"n": 1, "url": "https://a.com"}]
    out = apply_citations(body, citations)
    assert out == "A [1](https://a.com) and B [1](https://a.com)."


def test_multiple_distinct_citations():
    body = "[CITE_1] then [CITE_2] then [CITE_3]."
    citations = [
        {"n": 1, "url": "https://a.com"},
        {"n": 2, "url": "https://b.com"},
        {"n": 3, "url": "https://c.com"},
    ]
    out = apply_citations(body, citations)
    assert "[1](https://a.com)" in out
    assert "[2](https://b.com)" in out
    assert "[3](https://c.com)" in out


def test_missing_citation_raises():
    body = "See [CITE_5]."
    citations = [{"n": 1, "url": "https://a.com"}]
    with pytest.raises(CitationSubstitutionError) as exc:
        apply_citations(body, citations)
    assert "5" in str(exc.value)


def test_unused_citation_is_ignored():
    body = "No placeholder here."
    citations = [{"n": 1, "url": "https://a.com"}]
    out = apply_citations(body, citations)
    assert out == "No placeholder here."


def test_no_citations_no_placeholders():
    assert apply_citations("plain text", []) == "plain text"


def test_lone_inline_url_in_body_raises():
    # Writer should NOT emit inline [N](URL). Fail loud so we catch regressions.
    body = "Oops [1](https://rogue.com) here."
    citations = []
    with pytest.raises(CitationSubstitutionError) as exc:
        apply_citations(body, citations)
    assert "inline" in str(exc.value).lower()
```

**Step 2: Run — expect failures**

Run: `cd backend && .venv\Scripts\pytest tests/test_citation_substitution.py -v`

Expected: all FAIL (module not found).

**Step 3: Implement**

Create `backend/services/agents/citation_substitution.py`:

```python
"""Substitute [CITE_N] placeholders with [N](URL) markdown links.

Writer emits placeholder-only bodies (body text says `[CITE_1]`), and a
`citations: [{n, url}]` sidecar list whose `url` values are constrained by
the OpenAI strict json_schema enum (= fact_pack.news_items[].url). This
module converts placeholders into the final markdown form.

Defensive: also rejects raw `[N](URL)` patterns in the body — if those slip
through, the writer has ignored the output contract and we want a loud
failure, not silent publication.
"""
from __future__ import annotations
import re
from typing import Mapping, Sequence

_PLACEHOLDER_RE = re.compile(r"\[CITE_(\d+)\]")
_INLINE_CITATION_RE = re.compile(r"\[(\d+)\]\(https?://[^)\s]+\)")


class CitationSubstitutionError(Exception):
    """Raised when body+citations don't form a coherent output."""


def apply_citations(body: str, citations: Sequence[Mapping[str, object]]) -> str:
    """Replace [CITE_N] with [N](URL). Raise if inconsistent."""
    if not body:
        return body

    # Guard: writer must not emit inline [N](URL) — bodies should use [CITE_N].
    inline_match = _INLINE_CITATION_RE.search(body)
    if inline_match:
        raise CitationSubstitutionError(
            f"body contains inline citation {inline_match.group(0)!r}; "
            f"writer should emit [CITE_N] placeholders instead"
        )

    url_by_n: dict[int, str] = {}
    for c in citations:
        n = int(c["n"])
        url = str(c["url"])
        url_by_n[n] = url

    missing: list[int] = []

    def _sub(m: re.Match) -> str:
        n = int(m.group(1))
        if n not in url_by_n:
            missing.append(n)
            return m.group(0)
        return f"[{n}]({url_by_n[n]})"

    result = _PLACEHOLDER_RE.sub(_sub, body)

    if missing:
        raise CitationSubstitutionError(
            f"body references [CITE_{sorted(set(missing))}] but citations list "
            f"has only n={sorted(url_by_n)}"
        )

    return result
```

**Step 4: Run tests**

Run: `cd backend && .venv\Scripts\pytest tests/test_citation_substitution.py -v`

Expected: all 7 tests PASS.

**Step 5: Commit**

```bash
git add backend/services/agents/citation_substitution.py backend/tests/test_citation_substitution.py
git commit -m "feat(news): add citation placeholder substitution"
```

---

### Task 2.3: Update writer prompts to emit placeholders

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py:577-593` (`HALLUCINATION_GUARD`)
- Modify: writer prompts referencing citation format (search for `[N](URL)` in file)

**Step 1: Find all writer prompt references to `[N](URL)`**

Run: `grep -n '\[N\](URL)\|inline citation\|\[N\]' backend/services/agents/prompts_news_pipeline.py`

Expected hits: `HALLUCINATION_GUARD` (line 589-593) + citation format block at line ~179 + possibly others.

**Step 2: Rewrite `HALLUCINATION_GUARD` Citations section**

Replace lines 589-593 of `prompts_news_pipeline.py`:

```python
HALLUCINATION_GUARD = """## Hallucination Guard (CRITICAL — applies to headline, excerpt, AND body)

Every NUMBER, COMPANY name, PRODUCT name, PERSON name, and DATE in your output MUST appear in the source articles provided. NEVER invent quotes, statistics, prices, dates, or motivations. NEVER attribute intent to a company unless the source explicitly states it.

**NEVER predict the future or use forward-looking speculation verbs.** [existing content unchanged]

**NEVER use retrospective/present-tense overclaim language** [existing content unchanged]

**Absolute-date preference** [existing content unchanged]

When unsure, omit rather than fabricate.

**Citations (MANDATORY FORMAT — strict schema enforces this)**:
- In the body (`en` and `ko` fields), reference sources using the placeholder form `[CITE_N]` where N is a 1-indexed integer. Example: "Foo shipped bar [CITE_1] yesterday [CITE_2]."
- NEVER write inline markdown links like `[1](https://...)` in the body — the post-processor rejects them and the output will be invalidated.
- Emit a separate `citations` array: `[{"n": 1, "url": "<exact URL from source list>"}, {"n": 2, "url": "<...>"}]`.
- The `url` field is constrained by the API to the allowlist of source URLs — any URL not in the allowlist causes a schema validation failure and triggers a retry. Save your output (and token budget): **copy URLs verbatim from the source list, do NOT re-type them or fill in from memory**.
- Every `[CITE_N]` placeholder must have a matching entry in `citations`. Every citations entry should be referenced at least once in the body; unused entries are tolerated but wasteful.
- If a claim has no supporting URL in the source list, drop the claim or rephrase without citation — do NOT invent a URL.

**Attribution must match URL domain.** [existing content unchanged]
"""
```

**Step 3: Rewrite the line-179 citation format block**

Find the block at ~line 179 (search for `Format: \[N\]\(URL\)` or similar), replace with:

```
Citations: use placeholder form [CITE_N] at the END of relevant paragraphs. Do NOT inline the URL. The `citations` array holds the actual URLs.
```

**Step 4: Search for any remaining stale instructions**

Run: `grep -n '\[N\](URL)\|inline citation' backend/services/agents/prompts_news_pipeline.py`

Expected: zero hits (or only in commented-out / historical notes).

Fix any remaining live instructions to match the new contract.

**Step 5: No unit test (prompt text) — commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(news): update writer prompts to emit [CITE_N] placeholders"
```

---

### Task 2.4: Wire the strict schema into writer call + add substitution pass

**Files:**
- Modify: `backend/services/pipeline_digest.py:629-690` (writer loop)

**Step 1: Read the current loop**

Read `backend/services/pipeline_digest.py:629-720` to see where `persona_output.en`/`.ko` is populated and where `_clean_writer_output` runs.

**Step 2: Build allowlist + schema, swap response_format, apply substitution**

Edit the writer call block. Inside the `for persona_name in (...)` loop, above the `chat.completions.create` call, add:

```python
# Build allowlist from fact_pack for strict schema enforcement
allowlist_urls = [
    item["url"]
    for item in (fact_pack.get("news_items") or [])
    if isinstance(item, dict) and item.get("url")
]
if not allowlist_urls:
    # Writer cannot run without a non-empty allowlist — should never happen
    # with a well-formed fact_pack.
    raise RuntimeError(
        f"fact_pack.news_items has no URLs for {digest_type}/{persona_name}; "
        f"cannot build strict schema"
    )

from backend.services.agents.schemas.news_writer import build_news_writer_json_schema
from backend.services.agents.citation_substitution import apply_citations, CitationSubstitutionError

writer_schema = build_news_writer_json_schema(allowlist_urls)
```

Then change the `response_format` kwarg in the `chat.completions.create` call:

```python
response_format={
    "type": "json_schema",
    "json_schema": writer_schema,
},
```

After parsing `data` (~line 651), add substitution:

```python
data = parse_ai_json(
    response.choices[0].message.content,
    f"Digest-{digest_type}-{persona_name}",
)

# NEW: substitute [CITE_N] placeholders with [N](URL) markdown links.
citations = data.get("citations") or []
try:
    body_en = apply_citations(data.get("en", ""), citations)
    body_ko = apply_citations(data.get("ko", ""), citations)
except CitationSubstitutionError as sub_err:
    logger.error(
        "Citation substitution failed for %s/%s on attempt %d: %s",
        digest_type, persona_name, attempt, sub_err,
    )
    if attempt < MAX_DIGEST_RETRIES:
        continue  # retry
    raise  # exhausted retries

persona_output = PersonaOutput(
    en=_clean_writer_output(body_en),
    ko=_clean_writer_output(body_ko),
)
```

**Step 3: Run existing pipeline tests**

Run: `cd backend && .venv\Scripts\pytest tests/ -v --tb=short -k "digest or pipeline"`

Expected: no regressions.

**Step 4: Commit**

```bash
git add backend/services/pipeline_digest.py
git commit -m "feat(news): wire strict json_schema + citation substitution into writer"
```

---

### Task 2.5: Handle OpenAI `validation_error` gracefully

**Files:**
- Modify: `backend/services/pipeline_digest.py` (writer try/except around `chat.completions.create`)

**Step 1: Read existing error handling**

Read `backend/services/pipeline_digest.py:660-720` (the `except` blocks inside the retry loop).

**Step 2: Add specific handling for strict-schema rejection**

Inside the `for attempt in range(MAX_DIGEST_RETRIES + 1):` try block:

```python
try:
    response = await asyncio.wait_for(...)
except asyncio.TimeoutError:
    logger.warning("Writer timeout on attempt %d for %s/%s", attempt, digest_type, persona_name)
    if attempt < MAX_DIGEST_RETRIES:
        continue
    raise
except openai.BadRequestError as e:
    # OpenAI returns BadRequestError when strict schema validation fails
    # (after its own internal retries). This usually means the writer can't
    # comply with the enum. Log the full error — do not swallow silently.
    logger.error(
        "Writer strict-schema rejection on attempt %d for %s/%s: %s",
        attempt, digest_type, persona_name, e,
    )
    if attempt < MAX_DIGEST_RETRIES:
        continue
    raise
```

Add `import openai` at the top of the file if not present.

**Step 3: Run tests**

Run: `cd backend && .venv\Scripts\pytest tests/ -v --tb=short -k "digest"`

Expected: no regressions.

**Step 4: Commit**

```bash
git add backend/services/pipeline_digest.py
git commit -m "feat(news): handle openai BadRequestError (strict-schema reject) with retry"
```

---

### Task 2.6: End-to-end validation on Apr 23

**Files:**
- No code changes.

**Step 1: Delete Apr 23 again**

Repeat Task 0.2 Step 2 (delete Apr 23 rows).

**Step 2: Trigger regeneration**

Repeat Task 0.2 Step 3.

**Step 3: Inspect result**

Repeat Task 0.2 Step 4 query. Also check for inline URLs in body:

```bash
cd c:\Users\amy\Desktop\0to1log\backend && .venv\Scripts\python -c "
import os, re
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
sb = create_client(os.environ['SUPABASE_URL'], os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])
rows = sb.table('news_posts').select('slug,content_expert,content_learner,fact_pack').like('slug', '2026-04-23%').execute().data
INLINE = re.compile(r'\[\d+\]\(https?://[^)]+\)')
for r in rows:
    fp = r.get('fact_pack') or {}
    allowed = {i['url'] for i in (fp.get('news_items') or []) if isinstance(i, dict) and i.get('url')}
    for field in ('content_expert','content_learner'):
        body = r.get(field) or ''
        urls = [m.group(0) for m in INLINE.finditer(body)]
        unknown = [u for u in urls if u.split('](')[1][:-1] not in allowed]
        if unknown:
            print(f'{r[\"slug\"]}/{field}: {len(unknown)} unknown')
            for u in unknown[:3]:
                print(f'  {u}')
"
```

Expected: zero unknown URLs across all 4 posts × 2 body fields.

**Step 4: Record Phase 2 results**

Append `## Phase 2 Results` section to this plan with: date, 4-post × url_fail status, any BadRequestError logs from Railway.

**Step 5: Commit the result record**

```bash
git add vault/09-Implementation/plans/2026-04-23-news-writer-url-compliance.md
git commit -m "docs(plan): record Phase 2 end-to-end validation on Apr 23"
```

---

## Chunk 4: Rollout Gate

### Task 3.1: Keep Level 0 gate as defense-in-depth (no code change, review only)

**Step 1: Re-read `promote_drafts` logic**

Read `backend/services/pipeline_persistence.py:72-130` and confirm:
- Reads `fact_pack.auto_publish_eligible`
- Skips promotion if `False`
- Sends alert email for sub-threshold drafts

**Step 2: Verify `url_validation_failed` still sets `auto_publish_eligible=False`**

Read `backend/services/pipeline_quality.py:600-650` (the URL validation outcome block).

Expected: the conditional `if url_validation_failed: fact_pack["auto_publish_eligible"] = False` is still present and unchanged by Phase 2 work.

**Rationale:** Even with API-level enum enforcement, the Level 0 gate protects against edge cases:
- `fact_pack.news_items` parsing bugs that produce a valid-but-wrong allowlist
- Future writer code paths that bypass the schema (e.g., manual retries, partial edits)
- Any post-processing that re-introduces inline URLs

Keep the gate. No code change in this task — just a written confirmation.

**Step 3: Note in plan**

Append a paragraph under `## Phase 2 Results` explaining the defense-in-depth rationale.

---

### Task 3.2: Merge to main and monitor 3 daily runs

**Step 1: Ensure all commits on main**

Run: `git log --oneline -20` to review Phase 1+2 commits.

**Step 2: Push**

Run: `git push origin main`

Railway auto-deploys. Confirm via Railway dashboard.

**Step 3: Monitor 3 daily runs (Apr 24, 25, 26)**

Each day, post-cron, query:

```bash
cd c:\Users\amy\Desktop\0to1log\backend && .venv\Scripts\python -c "
import os, sys
from datetime import date
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
sb = create_client(os.environ['SUPABASE_URL'], os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_KEY'])
target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
rows = sb.table('news_posts').select('slug,status,quality_score,fact_pack').like('slug', f'{target}%').execute().data
for r in rows:
    fp = r.get('fact_pack') or {}
    print(f'{r[\"slug\"]:<42} status={r[\"status\"]:<10} score={r.get(\"quality_score\")} url_fail={fp.get(\"url_validation_failed\")}')
" 2026-04-24
```

Expected: `url_fail=False` for 100% of posts × 3 days.

**Step 4: Record results + close plan**

Append `## Post-Rollout Monitoring (Apr 24-26)` section with the 3-day results.

If all pass: archive this plan.

```bash
git mv vault/09-Implementation/plans/2026-04-23-news-writer-url-compliance.md vault/90-Archive/2026-04/plans-completed/2026-04-23-news-writer-url-compliance.md
git commit -m "docs(plan): archive completed URL compliance plan"
```

If any `url_fail=True` appears: DO NOT archive. Open an investigation note in `vault/12-Journal-&-Decisions/` describing the failure mode and update the plan with a Phase 3 section.

---

## Chunk 5: Followups (deferred — not part of this plan)

These are NOT tasks to execute now. They are documented so future-you knows the natural next steps.

- **Weekly writer migration**: Apply Phase 2 pattern to `backend/services/pipeline.py:2395-2420`. Weekly has a different output shape (per-persona, 2 locales, top-stories structure). Estimate: 1 day, similar decomposition.
- **CP writer migration**: Community Pulse entries are already per-item structured; no migration needed.
- **Weekly QC `validate_citation_urls` confirmation**: Already calls the same function (`pipeline_quality.py:1164`). No work required but double-check after weekly migration.
- **Observability dashboard**: Add daily count of `url_validation_failed=True` to admin dashboard for trend visibility. Nice-to-have, not blocking.

---

## Decision Log

- **2026-04-23**: Plan created. Root cause of Apr 23 research bypass: manual script set `auto_publish_eligible=True + status=published` with a hardcoded marker-based strip that missed actual hallucinated URLs (`liner.com`, `axiomlogica.com`). The existing Level 0 gate was SOUND; it was bypassed by me. Lesson: any manual publish override should re-run `validate_citation_urls` as a pre-flight.
- **2026-04-23**: Chose strict json_schema + enum over tool-call citation API because it keeps output shape closest to current (single JSON response, no tool round-trips) while giving API-level URL enforcement.
- **2026-04-23**: Deferred weekly migration. Daily is the higher-volume / higher-risk surface; weekly gets the fix fast-follow once the pattern is proven.
