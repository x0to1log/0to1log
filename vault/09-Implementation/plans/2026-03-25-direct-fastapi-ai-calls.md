# Direct FastAPI AI Calls — Bypass Vercel 60s Timeout

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Admin AI advisor calls bypass the Vercel serverless proxy and hit FastAPI directly from the browser, eliminating the 60-second Hobby plan timeout.

**Architecture:** Each admin editor page injects `fastApiUrl` and `accessToken` via a small `<script is:inline define:vars>` block. The bundled `<script>` reads `window.__adminAiConfig` and uses it for AI fetch calls. Non-AI admin API calls (save, status, delete) stay on the Astro proxy — they're fast and don't need this.

**Tech Stack:** Astro `define:vars`, FastAPI CORS (already configured), Supabase access token from `Astro.locals.accessToken`

---

## Context

### Current Flow (broken)
```
Browser → Vercel Serverless (60s limit) → Railway FastAPI → OpenAI
```

### New Flow
```
Browser → Railway FastAPI (no timeout) → OpenAI
```

### Files Overview

| Editor | AI fetch location | Backend endpoint |
|--------|------------------|-----------------|
| News | `admin/edit/[slug].astro:873` | `/api/admin/ai/advise` |
| Handbook | `admin/handbook/edit/[slug].astro:820` | `/api/admin/ai/handbook-advise` |
| Blog advise | `admin/blog/edit/[slug].astro:911` | `/api/admin/blog-ai/advise` |
| Blog translate | `admin/blog/edit/[slug].astro:1128` | `/api/admin/blog-ai/translate` |
| Products | `admin/products/edit/[slug].astro:1218` | `/api/admin/product-ai/generate` |

### Key Constraints

- `sb-access-token` cookie is `httpOnly: true` — JS cannot read it
- CLAUDE.md: "Do not expose access tokens into the DOM via `data-*` attributes"
- Solution: `<script is:inline define:vars>` injects into script closure, not DOM attributes
- FastAPI CORS already allows `https://0to1log.com` with `Authorization` header
- `FASTAPI_URL` is server-side only (`import.meta.env.FASTAPI_URL`)

---

### Task 1: Create shared admin AI config injector

**Files:**
- Create: `frontend/src/components/admin/AdminAiConfig.astro`

**Step 1: Create the component**

This component injects `fastApiUrl` + `accessToken` into `window.__adminAiConfig` via a secure inline script. It's used by all 4 editors.

```astro
---
// AdminAiConfig.astro — injects AI backend config into browser script scope
// Only used on admin editor pages (behind auth middleware)
const fastApiUrl = import.meta.env.FASTAPI_URL || '';
const accessToken = Astro.locals.accessToken || '';
const nonce = Astro.locals.cspNonce || '';
---
<script is:inline nonce={nonce} define:vars={{ fastApiUrl, accessToken }}>
  window.__adminAiConfig = { fastApiUrl, accessToken };
</script>
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS (0 errors)

**Step 3: Commit**

```bash
git add frontend/src/components/admin/AdminAiConfig.astro
git commit -m "feat: add AdminAiConfig component for direct FastAPI AI calls"
```

---

### Task 2: News editor — direct FastAPI call

**Files:**
- Modify: `frontend/src/pages/admin/edit/[slug].astro`

**Step 1: Add AdminAiConfig import and component**

In frontmatter, add:
```typescript
import AdminAiConfig from '../../../components/admin/AdminAiConfig.astro';
```

In the HTML body (before the main `<script>` block), add:
```html
<AdminAiConfig />
```

**Step 2: Modify AI fetch to use direct FastAPI URL**

Change the fetch call at ~line 873 from:
```typescript
const res = await fetch('/api/admin/ai/advise', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({...}),
});
```

To:
```typescript
const aiConfig = (window as any).__adminAiConfig;
const aiUrl = aiConfig?.fastApiUrl
  ? `${aiConfig.fastApiUrl}/api/admin/ai/advise`
  : '/api/admin/ai/advise';
const aiHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
if (aiConfig?.accessToken) aiHeaders['Authorization'] = `Bearer ${aiConfig.accessToken}`;

const res = await fetch(aiUrl, {
  method: 'POST',
  headers: aiHeaders,
  body: JSON.stringify({...}),
});
```

Note: The fallback to `/api/admin/ai/advise` ensures it works in dev (where FASTAPI_URL might not be set).

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/pages/admin/edit/[slug].astro
git commit -m "feat(news): direct FastAPI call for AI advisor — bypass Vercel 60s"
```

---

### Task 3: Handbook editor — direct FastAPI call

**Files:**
- Modify: `frontend/src/pages/admin/handbook/edit/[slug].astro`

**Step 1: Add AdminAiConfig import and component**

Same pattern as Task 2: import `AdminAiConfig` and add `<AdminAiConfig />` before main script.

**Step 2: Modify AI fetch at ~line 820**

Same pattern as Task 2, but endpoint is `/api/admin/ai/handbook-advise`:
```typescript
const aiConfig = (window as any).__adminAiConfig;
const aiUrl = aiConfig?.fastApiUrl
  ? `${aiConfig.fastApiUrl}/api/admin/ai/handbook-advise`
  : '/api/admin/ai/handbook-advise';
const aiHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
if (aiConfig?.accessToken) aiHeaders['Authorization'] = `Bearer ${aiConfig.accessToken}`;
```

**Step 3: Verify build + commit**

```bash
cd frontend && npm run build
git add frontend/src/pages/admin/handbook/edit/[slug].astro
git commit -m "feat(handbook): direct FastAPI call for AI advisor — bypass Vercel 60s"
```

---

### Task 4: Blog editor — direct FastAPI calls (2 endpoints)

**Files:**
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro`

**Step 1: Add AdminAiConfig import and component**

Same pattern.

**Step 2: Modify AI advise fetch at ~line 911**

Endpoint: `/api/admin/blog-ai/advise`

**Step 3: Modify AI translate fetch at ~line 1128**

Endpoint: `/api/admin/blog-ai/translate`

Both use the same `aiConfig` pattern. Define `aiConfig` once at the top of the script:
```typescript
const aiConfig = (window as any).__adminAiConfig;
function getAiUrl(path: string): string {
  return aiConfig?.fastApiUrl ? `${aiConfig.fastApiUrl}${path}` : path;
}
function getAiHeaders(): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  if (aiConfig?.accessToken) h['Authorization'] = `Bearer ${aiConfig.accessToken}`;
  return h;
}
```

Then both calls use:
```typescript
const res = await fetch(getAiUrl('/api/admin/blog-ai/advise'), {
  method: 'POST', headers: getAiHeaders(), body: JSON.stringify({...}),
});
```

**Step 4: Verify build + commit**

```bash
cd frontend && npm run build
git add frontend/src/pages/admin/blog/edit/[slug].astro
git commit -m "feat(blog): direct FastAPI call for AI advisor — bypass Vercel 60s"
```

---

### Task 5: Products editor — direct FastAPI call

**Files:**
- Modify: `frontend/src/pages/admin/products/edit/[slug].astro`

**Step 1: Add AdminAiConfig import and component**

Same pattern.

**Step 2: Modify AI generate fetch at ~line 1218**

Endpoint: `/api/admin/product-ai/generate`

Same `aiConfig` / `getAiUrl` / `getAiHeaders` pattern.

**Step 3: Verify build + commit**

```bash
cd frontend && npm run build
git add frontend/src/pages/admin/products/edit/[slug].astro
git commit -m "feat(products): direct FastAPI call for AI advisor — bypass Vercel 60s"
```

---

### Task 6: Remove timeout from Astro proxy routes (cleanup)

**Files:**
- Modify: `frontend/src/pages/api/admin/ai/advise.ts`
- Modify: `frontend/src/pages/api/admin/ai/handbook-advise.ts`
- Modify: `frontend/src/pages/api/admin/blog/ai/advise.ts`
- Modify: `frontend/src/pages/api/admin/blog/ai/translate.ts`
- Modify: `frontend/src/pages/api/admin/products/ai/generate.ts`

**Step 1: Remove AbortSignal.timeout from all 5 proxy routes**

These proxy routes are now fallback-only (dev mode). Remove the `signal: AbortSignal.timeout(...)` lines. Keep the routes functional as fallback.

Example change in each file:
```typescript
// Before
const res = await fetch(`${backendUrl}/...`, {
  ...
  signal: AbortSignal.timeout(120_000),
});

// After
const res = await fetch(`${backendUrl}/...`, {
  ...
});
```

Also update the error message from "120s" to generic:
```typescript
// Before
error: isTimeout ? 'Request timed out (120s)' : 'Backend unreachable'
// After
error: 'Backend unreachable'
```

And remove the timeout-related catch logic (isTimeout check, 504 status).

**Step 2: Verify build + commit**

```bash
cd frontend && npm run build
git add frontend/src/pages/api/admin/
git commit -m "chore: remove timeout from AI proxy routes (now fallback-only)"
```

---

### Task 7: Final verification

**Step 1: Run full build**

Run: `cd frontend && npm run build`
Expected: PASS (0 errors)

**Step 2: Grep to verify no stale patterns**

```bash
# All AI fetch calls should use getAiUrl or aiConfig pattern
grep -rn "fetch('/api/admin/ai/" frontend/src/pages/admin/
grep -rn "fetch('/api/admin/blog/ai/" frontend/src/pages/admin/
grep -rn "fetch('/api/admin/products/ai/" frontend/src/pages/admin/
```

Expected: 0 matches (all converted to direct calls)

**Step 3: Push**

```bash
git push origin main
```
