# Pipeline Controls Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add stuck timeout detection, manual cancel button, and news-only execution option to the admin pipeline controls.

**Architecture:** Frontend-driven timeout check on dashboard load, new cancel endpoint on backend, skip_handbook parameter threaded through the pipeline trigger chain.

**Tech Stack:** FastAPI (Python), Astro (TypeScript), Supabase PostgreSQL

---

### Task 1: Backend — Cancel endpoint + skip_handbook parameter

**Files:**
- Modify: `backend/routers/cron.py`
- Modify: `backend/services/pipeline.py`

**Step 1: Add cancel endpoint to cron.py**

Add after the handbook-extract endpoint:

```python
class PipelineCancelBody(BaseModel):
    run_id: str

@router.post("/pipeline-cancel", status_code=200)
async def cancel_pipeline_run(
    body: PipelineCancelBody,
    _secret=Depends(verify_cron_secret),
):
    """Cancel a running pipeline by marking it as failed."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(500, "Supabase not configured")
    try:
        supabase.table("pipeline_runs").update({
            "status": "failed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "last_error": "Cancelled by admin",
        }).eq("id", body.run_id).eq("status", "running").execute()
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"status": "cancelled", "run_id": body.run_id}
```

Import `get_supabase` from `core.database`.

**Step 2: Add skip_handbook to PipelineTriggerBody**

```python
class PipelineTriggerBody(BaseModel):
    mode: str = "resume"
    target_date: Optional[str] = None
    force: bool = False
    skip_handbook: bool = False
```

**Step 3: Pass skip_handbook through trigger_news_pipeline**

In `trigger_news_pipeline()`, pass `skip_handbook` to `run_daily_pipeline()`:

```python
skip_handbook = body.skip_handbook if body else False
# ... in _run():
result = await run_daily_pipeline(
    batch_id=batch_id, target_date=target_date, skip_handbook=skip_handbook,
)
```

**Step 4: Add skip_handbook to run_daily_pipeline**

In `pipeline.py`, add parameter and conditional:

```python
async def run_daily_pipeline(
    batch_id: str | None = None,
    target_date: str | None = None,
    skip_handbook: bool = False,
) -> PipelineResult:
```

Change the auto-trigger section:
```python
if total_posts > 0 and not skip_handbook:
    try:
        await run_handbook_extraction(batch_id)
    except Exception as e:
        logger.warning("Handbook extraction auto-trigger failed: %s", e)
```

**Step 5: Run tests and lint**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short && .venv/Scripts/python.exe -m ruff check .`

**Step 6: Commit**

```
git add backend/routers/cron.py backend/services/pipeline.py
git commit -m "feat(backend): add pipeline cancel endpoint + skip_handbook option"
```

---

### Task 2: Frontend — Cancel proxy + skip_handbook in trigger

**Files:**
- Modify: `frontend/src/lib/admin/pipelineTrigger.js`
- Modify: `frontend/src/pages/api/admin/run-pipeline.ts`

**Step 1: Add cancel route to pipelineTrigger.js**

Add a new export function:

```javascript
export async function handleCancelRequest(env, runId) {
  const config = getPipelineConfig(env);
  if (!config) {
    return jsonResponse({ error: 'Missing configuration' }, 500);
  }
  try {
    const response = await fetch(`${config.backendUrl}/api/cron/pipeline-cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-cron-secret': config.cronSecret },
      body: JSON.stringify({ run_id: runId }),
      signal: AbortSignal.timeout(8000),
    });
    const data = await response.json();
    return jsonResponse({ ok: response.ok, data }, response.ok ? 200 : 502);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return jsonResponse({ error: 'Cancel request failed', message }, 502);
  }
}
```

**Step 2: Add skip_handbook to forwardPipelineTrigger**

In `forwardPipelineTrigger()`, add `skipHandbook` parameter:

```javascript
async function forwardPipelineTrigger(env, mode = 'resume', targetDate = null, force = false, skipHandbook = false) {
  // ... in payload:
  if (skipHandbook) payload.skip_handbook = true;
}

export async function handleAdminTriggerRequest(env, mode = 'resume', targetDate = null, force = false, skipHandbook = false) {
  return forwardPipelineTrigger(env, mode, targetDate, force, skipHandbook);
}
```

**Step 3: Update run-pipeline.ts**

Parse `skip_handbook` from request body and forward:

```typescript
let skipHandbook = false;
// in try block:
if (payload?.skip_handbook === true) {
  skipHandbook = true;
}
return handleAdminTriggerRequest(env, mode, targetDate, force, skipHandbook);
```

**Step 4: Build**

Run: `cd frontend && npm run build`

**Step 5: Commit**

```
git add frontend/src/lib/admin/pipelineTrigger.js frontend/src/pages/api/admin/run-pipeline.ts
git commit -m "feat(frontend): add cancel proxy + skip_handbook parameter forwarding"
```

---

### Task 3: Frontend — Dashboard UI (timeout + cancel + checkbox)

**Files:**
- Modify: `frontend/src/pages/admin/index.astro`
- Create: `frontend/src/pages/api/admin/pipeline-cancel.ts`

**Step 1: Create cancel API route**

```typescript
// frontend/src/pages/api/admin/pipeline-cancel.ts
import type { APIRoute } from 'astro';
import { handleCancelRequest } from '../../../lib/admin/pipelineTrigger.js';
// Copy requireAdminFromCookies from run-pipeline.ts or import shared

export const prerender = false;

export const POST: APIRoute = async ({ cookies, request }) => {
  // Admin auth check (same as run-pipeline.ts)
  // ...
  let runId = '';
  try {
    const payload = await request.json();
    runId = payload?.run_id || '';
  } catch {}
  if (!runId) {
    return new Response(JSON.stringify({ error: 'Missing run_id' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
  }
  const env = { CRON_SECRET: import.meta.env.CRON_SECRET, FASTAPI_URL: import.meta.env.FASTAPI_URL };
  return handleCancelRequest(env, runId);
};
```

**Step 2: Add timeout detection in frontmatter**

In `index.astro` frontmatter, after fetching `lastRun`:

```typescript
// Auto-detect stuck runs (running for > 30 minutes)
const STUCK_TIMEOUT_MS = 30 * 60 * 1000;
const isStuck = lastRun?.status === 'running' &&
  lastRun?.started_at &&
  (Date.now() - new Date(lastRun.started_at).getTime()) > STUCK_TIMEOUT_MS;

if (isStuck && lastRun?.id) {
  try {
    await sb.from('pipeline_runs').update({
      status: 'failed',
      finished_at: new Date().toISOString(),
      last_error: 'Pipeline timed out (>30 minutes)',
    }).eq('id', lastRun.id).eq('status', 'running');
    lastRun.status = 'failed';
    lastRunError = 'Pipeline timed out (>30 minutes)';
  } catch {}
}
```

**Step 3: Add Cancel button (visible when running)**

In the pipeline actions area, add:

```html
{lastRun?.status === 'running' && (
  <button type="button" class="admin-btn-danger" id="cancel-pipeline-btn"
          data-run-id={lastRun.id}>
    Cancel
  </button>
)}
```

**Step 4: Add "Include handbook" checkbox**

After the Run Pipeline button:

```html
<label class="admin-checkbox-label" style="font-size:0.8rem;color:var(--color-text-muted);display:inline-flex;align-items:center;gap:0.3rem">
  <input type="checkbox" id="include-handbook" checked />
  Include handbook
</label>
```

**Step 5: Add JS handlers**

Cancel button handler:
```javascript
const cancelBtn = document.getElementById('cancel-pipeline-btn');
if (cancelBtn) {
  cancelBtn.addEventListener('click', async () => {
    const runId = cancelBtn.dataset.runId;
    cancelBtn.textContent = 'Cancelling...';
    cancelBtn.setAttribute('disabled', 'true');
    try {
      await fetch('/api/admin/pipeline-cancel', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId }),
      });
      setTimeout(() => window.location.reload(), 1000);
    } catch {
      cancelBtn.textContent = 'Failed';
    }
  });
}
```

Wire up skip_handbook checkbox in the pipeline trigger:
```javascript
const handbookCheckbox = document.getElementById('include-handbook') as HTMLInputElement | null;
// In the pipeline trigger body:
const skipHandbook = handbookCheckbox && !handbookCheckbox.checked;
// Add to reqBody:
if (skipHandbook) reqBody.skip_handbook = true;
```

**Step 6: Build**

Run: `cd frontend && npm run build`

**Step 7: Commit**

```
git add frontend/src/pages/admin/index.astro frontend/src/pages/api/admin/pipeline-cancel.ts
git commit -m "feat(frontend): pipeline cancel button, stuck timeout, handbook checkbox"
```
