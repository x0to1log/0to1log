# Handbook Fact Check Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Quick Check (factcheck) and Deep Verify (deepverify) AI actions to the handbook editor

**Architecture:** Extend `HandbookAdviseRequest.action` to accept "factcheck" and "deepverify", reuse existing news editor prompts (`FACTCHECK_SYSTEM_PROMPT`, `DEEPVERIFY_*`), add buttons + result renderers to handbook editor UI

**Tech Stack:** FastAPI backend (Python), Astro frontend (TypeScript), existing OpenAI + Tavily integration

---

### Task 1: Backend — Extend handbook action types

**Files:**
- Modify: `backend/models/advisor.py:146`

**Step 1: Update HandbookAdviseRequest action Literal**

Change line 146 from:
```python
action: Literal["related_terms", "translate", "generate"]
```
to:
```python
action: Literal["related_terms", "translate", "generate", "factcheck", "deepverify"]
```

**Step 2: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_handbook_advisor.py -v --tb=short`
Expected: All pass (no test depends on action enum exhaustively)

**Step 3: Commit**

```bash
git add backend/models/advisor.py
git commit -m "feat(backend): add factcheck/deepverify to handbook action types"
```

---

### Task 2: Backend — Add factcheck/deepverify handlers to handbook advisor

**Files:**
- Modify: `backend/services/agents/advisor.py` — `run_handbook_advise()` function

**Step 1: Add factcheck/deepverify branches**

In `run_handbook_advise()` (around line 388), add two new elif branches before the else:

```python
elif req.action == "factcheck":
    # Build content from all handbook fields for checking
    content_parts = [
        f"Term: {req.term}",
        f"Definition (KO): {req.definition_ko}" if req.definition_ko else "",
        f"Definition (EN): {req.definition_en}" if req.definition_en else "",
        f"Body Basic (KO):\n{req.body_basic_ko}" if req.body_basic_ko else "",
        f"Body Basic (EN):\n{req.body_basic_en}" if req.body_basic_en else "",
        f"Body Advanced (KO):\n{req.body_advanced_ko}" if req.body_advanced_ko else "",
        f"Body Advanced (EN):\n{req.body_advanced_en}" if req.body_advanced_en else "",
    ]
    content = "\n\n".join(p for p in content_parts if p)
    # Reuse news factcheck flow
    fake_req = AiAdviseRequest(
        action="factcheck", post_id="", title=req.term,
        content=content, category="study",
    )
    data, model, tokens = await _run_simple_action(fake_req, client, model)
    return data, model, tokens, []

elif req.action == "deepverify":
    content_parts = [
        f"Term: {req.term}",
        f"Definition (KO): {req.definition_ko}" if req.definition_ko else "",
        f"Definition (EN): {req.definition_en}" if req.definition_en else "",
        f"Body Basic (KO):\n{req.body_basic_ko}" if req.body_basic_ko else "",
        f"Body Basic (EN):\n{req.body_basic_en}" if req.body_basic_en else "",
        f"Body Advanced (KO):\n{req.body_advanced_ko}" if req.body_advanced_ko else "",
        f"Body Advanced (EN):\n{req.body_advanced_en}" if req.body_advanced_en else "",
    ]
    content = "\n\n".join(p for p in content_parts if p)
    fake_req = AiAdviseRequest(
        action="deepverify", post_id="", title=req.term,
        content=content, category="study",
    )
    data, model, tokens = await _run_deepverify(fake_req, client, model)
    return data, model, tokens, []
```

Note: `_run_simple_action()` handles factcheck via the `ACTION_CONFIG` dict (line 73). `_run_deepverify()` is the existing 2-step deep verify function. Both are already implemented for news.

**Step 2: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short`
Expected: All 55 pass

**Step 3: Run lint**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check .`
Expected: All checks passed

**Step 4: Commit**

```bash
git add backend/services/agents/advisor.py
git commit -m "feat(backend): add factcheck/deepverify handlers for handbook terms"
```

---

### Task 3: Frontend — Add factcheck/deepverify buttons to handbook editor

**Files:**
- Modify: `frontend/src/pages/admin/handbook/edit/[slug].astro`

**Step 1: Add two buttons to AI panel**

After the existing Translate button (around line 286), add:

```html
<hr class="admin-ai-divider" />
<button class="admin-ai-action-btn" data-ai-action="factcheck" type="button">
  Quick Check
</button>
<button class="admin-ai-action-btn admin-ai-action-btn--wide" data-ai-action="factcheck-deep" type="button">
  Deep Verify
</button>
```

Note: Use `factcheck-deep` as the data attribute to differentiate from `factcheck` in the click handler — map it to `deepverify` action in the JS.

**Step 2: Update runHandbookAi to handle factcheck/deepverify**

In the `runHandbookAi()` function, add mapping for the new actions. The action sent to the backend should be `factcheck` or `deepverify`.

In the click handler (around line 1249), add mapping:
```javascript
let backendAction = action;
if (action === 'factcheck-deep') backendAction = 'deepverify';
```

**Step 3: Add result renderers**

Add `renderFactcheck()` and `renderDeepverify()` functions. Reference the news editor's existing implementations (`admin/edit/[slug].astro` lines 1011, 1172) for the exact render pattern:

For factcheck — render verdict cards with ✅/⚠️/❌ icons.
For deepverify — render verdict cards with source URLs.

Both should use existing `.admin-ai-result-card` CSS patterns.

In the result handler section of `runHandbookAi()`, add:
```javascript
if (action === 'factcheck' || backendAction === 'factcheck') {
    renderFactcheck(result);
} else if (action === 'factcheck-deep' || backendAction === 'deepverify') {
    renderDeepverify(result);
}
```

**Step 4: Build**

Run: `cd frontend && npm run build`
Expected: Complete! (0 errors)

**Step 5: Commit**

```bash
git add frontend/src/pages/admin/handbook/edit/\[slug\].astro
git commit -m "feat(frontend): add Quick Check and Deep Verify buttons to handbook editor"
```

---

### Task 4: Verify end-to-end

**Step 1:** Deploy backend to Railway (or test locally)
**Step 2:** Go to `/admin/handbook/edit/{any-term}`
**Step 3:** Click "Quick Check" — verify verdict cards appear
**Step 4:** Click "Deep Verify" — verify verdict cards with source URLs appear
**Step 5:** Check `pipeline_logs` for `handbook.factcheck` entries (if logging was added)

---

## Files Summary

| File | Change |
|------|--------|
| `backend/models/advisor.py` | Add factcheck/deepverify to action Literal |
| `backend/services/agents/advisor.py` | Add 2 elif branches in run_handbook_advise() |
| `frontend/.../handbook/edit/[slug].astro` | Add 2 buttons + 2 result renderers |
