# Weekly Per-Persona Regeneration Implementation Plan

**Goal:** Allow regenerating a single persona (expert or learner) of a weekly post via admin button, so partial-failure cases (one persona succeeded, the other failed) can be recovered without rerunning the full pipeline.

**Why:** Weekly writer hits OpenAI flex-tier capacity limits, failing expert OR learner randomly ~50% of runs. Partial save leaves posts with one persona empty. Retrying the full pipeline wastes 4 writer calls (~$0.27) to fix 1 failed call.

**Architecture:**
- Extract weekly persona generation into a standalone callable helper (previously a nested closure in `run_weekly_pipeline`).
- Add a synchronous admin endpoint `POST /api/admin/weekly/regenerate` that fetches digests, calls the helper for one persona, updates the existing news_posts row, recomputes quality, logs stages.
- Add admin UI buttons on the weekly post editor.

**Scope:** Backend endpoint first (usable via curl), frontend UI second. Tests minimal (auth + extraction correctness).

---

## Task 1: Backend — extract helper + add endpoint

### 1.1: Extract persona generator

**File:** `backend/services/pipeline.py` (~line 2411)

Move `_gen_weekly_persona` out of `run_weekly_pipeline`'s closure. New module-level function signature:

```python
async def _generate_weekly_persona_content(
    *,
    persona: str,           # "expert" or "learner"
    daily_text: str,        # persona_inputs[persona] — already built by caller
    supabase,
    run_id: str,
    model: str,
    client,
    cumulative_usage: dict,  # mutated in-place
    all_errors: list,        # appended in-place
) -> dict | None:
    """Generate one persona's EN + KO weekly content. Returns {en, ko, headline, ...} or None on failure."""
```

Body: identical to current closure body. Replace closure variables with parameters.

In `run_weekly_pipeline`, replace the inline `_gen_weekly_persona(p)` calls with the new function.

### 1.2: Add regen helper

**File:** `backend/services/pipeline.py` (new function, near `run_weekly_pipeline`)

```python
async def regenerate_weekly_persona(week_id: str, persona: str) -> dict:
    """Regenerate ONE persona's weekly content + update existing posts.

    Fetches daily digests + existing rows, runs the persona writer, merges into
    existing content_expert/content_learner columns, recomputes quality, updates
    both en + ko rows.

    Raises HTTPException-style dict on failure; returns {"status": ..., "quality_score": ...}
    on success.
    """
```

Flow:
1. Validate `persona in ("expert", "learner")`
2. Fetch digests via `_fetch_week_digests(supabase, week_id, "en")` + `"ko"`
3. Build persona input (same 2390-2403 logic, but for one persona only)
4. Create a new `pipeline_runs` row with `run_key=f"weekly-regen-{week_id}-{persona}-{timestamp}"`
5. Call `_generate_weekly_persona_content(...)` → returns `{en, ko, headline, ...}`
6. Fetch existing `news_posts` rows for slug=`{week_id.lower()}-weekly-digest` (en + ko)
7. For each locale: overwrite `content_{persona}` + `title`/`title_learner` only
8. Re-run `_check_weekly_quality` with BOTH personas' current content (so score reflects the merged state)
9. Update `quality_score` + `fact_pack.quality_breakdown` etc. on both rows
10. Update `pipeline_runs.status = "success"`
11. Return summary

### 1.3: Add admin endpoint

**File:** `backend/routers/admin_ai.py`

```python
from pydantic import BaseModel

class WeeklyRegenBody(BaseModel):
    week_id: str           # e.g., "2026-W16"
    persona: str           # "expert" or "learner"

@router.post("/weekly/regenerate")
async def regenerate_weekly_persona_endpoint(
    body: WeeklyRegenBody,
    _user=Depends(require_admin),
):
    """Regenerate one persona of a weekly post. Synchronous — waits for completion."""
    from services.pipeline import regenerate_weekly_persona
    try:
        result = await regenerate_weekly_persona(body.week_id, body.persona)
        return result
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        logger.exception("Weekly regen failed")
        raise HTTPException(500, detail=str(e))
```

### 1.4: Tests

**File:** `backend/tests/test_weekly_regen.py` (new, ~3 tests)

1. `test_generate_weekly_persona_content_standalone`: mock OpenAI, verify helper returns expected dict shape when called directly (proves extraction works).
2. `test_weekly_regen_endpoint_requires_auth`: POST without Bearer → 401; POST with non-admin → 403.
3. `test_weekly_regen_invalid_persona`: persona="invalid" → 400.

### 1.5: Commit

```
feat(weekly): per-persona regeneration endpoint

Extracts _gen_weekly_persona into a reusable module-level helper and
adds POST /api/admin/weekly/regenerate for per-persona recovery. Avoids
rerunning the full weekly pipeline when one of the 4 writer calls fails
due to flex-tier capacity.
```

---

## Task 2: Frontend — buttons on weekly edit page

### 2.1: Astro proxy route

**File:** `frontend/src/pages/api/admin/weekly/regenerate.ts` (new)

Mirror existing admin proxy pattern — forward Bearer token from server locals to Railway backend `/api/admin/weekly/regenerate`.

### 2.2: Buttons on post editor

**File:** `frontend/src/pages/admin/news/edit/[slug].astro`

Conditional on `post.post_type === 'weekly'`, add a footer section with two buttons:
- "Regenerate Expert" → POST `/api/admin/weekly/regenerate` with `{week_id, persona: 'expert'}`
- "Regenerate Learner" → same, `persona: 'learner'`

Show status indicator during request (can take 5-10 min). Refresh page on success.

`week_id` derivation: from slug `2026-w16-weekly-digest` → `2026-W16`.

### 2.3: Commit

```
feat(admin/weekly): per-persona regen buttons on post editor
```

---

## Task 3: Recover W16 expert

After Task 1 deploys:

```bash
curl -X POST "$FASTAPI_URL/api/admin/weekly/regenerate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"week_id": "2026-W16", "persona": "expert"}'
```

(Or via UI after Task 2.)

---

## Out of scope (later)

- Retry ladder for transient 500/connection errors in `with_flex_retry` — next plan.
- `pipeline_runs.status = "partial"` DB constraint fix (separate DB migration).
- `news_posts.updated_at` auto-bump on update.

## Rollback

Each task is one commit. Revert by SHA if needed.
