# Unified Content Feedback System — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the handbook-only `term_feedback` system with a universal `content_feedback` system covering news, handbook, blog, and product pages, including an updated admin dashboard.

**Architecture:** New `content_feedback` DB table → new Astro API route (`content-feedback.ts`) → new `ContentFeedback.astro` component + `contentFeedback.ts` script mounted on all 4 detail page types → updated admin feedback dashboard. Data migrated from `term_feedback`, then old system removed.

**Tech Stack:** Supabase (PostgreSQL + RLS), Astro v5 SSR API routes, vanilla TypeScript, Tailwind CSS v4

**Spec:** `vault/09-Implementation/plans/2026-03-18-unified-content-feedback-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `supabase/migrations/00032_content_feedback.sql` | Table, RLS, indexes, data migration |
| `frontend/src/pages/api/user/content-feedback.ts` | GET/POST/DELETE API for content feedback |
| `frontend/src/components/common/ContentFeedback.astro` | Universal feedback section (replaces HandbookFeedback) |
| `frontend/src/scripts/contentFeedback.ts` | Client-side logic: buttons, bottom sheet, API calls |
| `frontend/tests/content-feedback-contract.test.cjs` | Contract tests for new system |

### Modified Files
| File | Changes |
|------|---------|
| `frontend/src/components/common/StickyReadingActions.astro` | Remove feedback buttons from `variant === 'term'` — replace with bookmark+share only (like news/blog variant) |
| `frontend/src/pages/ko/handbook/[slug].astro` | Mount ContentFeedback in page body (after reading-end, before admin actions) |
| `frontend/src/pages/en/handbook/[slug].astro` | Mount ContentFeedback |
| `frontend/src/pages/ko/news/[slug].astro` | Mount ContentFeedback |
| `frontend/src/pages/en/news/[slug].astro` | Mount ContentFeedback |
| `frontend/src/pages/ko/blog/[slug].astro` | Mount ContentFeedback |
| `frontend/src/pages/en/blog/[slug].astro` | Mount ContentFeedback |
| `frontend/src/pages/ko/products/[slug].astro` | Add `user` variable + Mount ContentFeedback |
| `frontend/src/pages/en/products/[slug].astro` | Add `user` variable + Mount ContentFeedback |
| `frontend/src/pages/admin/feedback/index.astro` | Switch from term_feedback → content_feedback, enable all source tabs |
| `frontend/src/pages/api/admin/feedback/archive.ts` | Change `term_feedback` → `content_feedback` table name |
| `frontend/src/styles/global.css` | Rename `.handbook-feedback-*` → `.content-feedback-*` CSS classes |

### Deleted Files (after migration verified)
| File | Reason |
|------|--------|
| `frontend/src/pages/api/user/term-feedback.ts` | Replaced by content-feedback.ts |
| `frontend/src/components/newsprint/HandbookFeedback.astro` | Replaced by ContentFeedback.astro |
| `frontend/src/scripts/handbookFeedback.ts` | Replaced by contentFeedback.ts |
| `frontend/tests/handbook-feedback-*.test.cjs` | Replaced by content-feedback-contract.test.cjs |

---

## Chunk 1: Database Migration + API Route

### Task 1: Create content_feedback migration

**Files:**
- Create: `supabase/migrations/00032_content_feedback.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- 00032_content_feedback.sql
-- Unified content feedback table (replaces term_feedback)

-- 1. Create table
CREATE TABLE content_feedback (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('news','handbook','blog','product')),
  source_id   UUID NOT NULL,
  locale      TEXT NOT NULL CHECK (locale IN ('ko','en')),
  reaction    TEXT NOT NULL CHECK (reaction IN ('positive','negative')),
  reason      TEXT,
  message     TEXT,
  archived    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, source_type, source_id, locale)
);

ALTER TABLE content_feedback ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_content_feedback_source ON content_feedback(source_type, source_id, locale);
CREATE INDEX idx_content_feedback_user ON content_feedback(user_id);
CREATE INDEX idx_content_feedback_archived ON content_feedback(archived);

-- 2. RLS policies — authenticated users own feedback
CREATE POLICY "cf_select_own" ON content_feedback FOR SELECT TO authenticated
  USING (auth.uid() = user_id);
CREATE POLICY "cf_insert_own" ON content_feedback FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);
CREATE POLICY "cf_update_own" ON content_feedback FOR UPDATE TO authenticated
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "cf_delete_own" ON content_feedback FOR DELETE TO authenticated
  USING (auth.uid() = user_id);

-- 3. RLS policies — admin read + update (for archiving)
CREATE POLICY "cf_admin_read_all" ON content_feedback FOR SELECT
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
CREATE POLICY "cf_admin_update_all" ON content_feedback FOR UPDATE
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

-- 4. Migrate data from term_feedback
INSERT INTO content_feedback (user_id, source_type, source_id, locale, reaction, reason, message, archived, created_at, updated_at)
SELECT user_id, 'handbook', term_id, locale,
  CASE reaction WHEN 'helpful' THEN 'positive' WHEN 'confusing' THEN 'negative' ELSE 'positive' END,
  CASE reaction WHEN 'confusing' THEN 'confusing' ELSE NULL END,
  message, COALESCE(archived, FALSE), created_at, updated_at
FROM term_feedback
WHERE reaction IN ('helpful', 'confusing');
```

- [ ] **Step 2: Verify migration syntax**

Run against Supabase Dashboard SQL editor (or local Supabase) to confirm no syntax errors.
Expected: table created, data migrated, RLS enabled.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/00032_content_feedback.sql
git commit -m "feat: add content_feedback table with RLS and data migration from term_feedback"
```

---

### Task 2: Create content-feedback API route

**Files:**
- Create: `frontend/src/pages/api/user/content-feedback.ts`
- Reference: `frontend/src/pages/api/user/term-feedback.ts` (existing pattern)

**Key patterns from existing term-feedback.ts:**
- `authSupabase(accessToken)` helper for per-request Supabase client
- `json(body, status)` response helper
- `locals.user` and `locals.accessToken` for auth
- UPSERT with `onConflict` for idempotent writes

- [ ] **Step 1: Create the API route with validation constants**

Create `frontend/src/pages/api/user/content-feedback.ts`:

```typescript
import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

function authSupabase(accessToken: string) {
  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const VALID_SOURCE_TYPES = ['news', 'handbook', 'blog', 'product'] as const;
const VALID_LOCALES = ['ko', 'en'] as const;
const VALID_REACTIONS = ['positive', 'negative'] as const;

const VALID_REASONS: Record<string, string[]> = {
  news: ['inaccurate', 'hard_to_understand', 'too_shallow', 'other'],
  handbook: ['confusing', 'lacks_examples', 'outdated', 'other'],
  blog: ['not_helpful', 'lacks_depth', 'other'],
  product: ['inaccurate_info', 'not_useful', 'other'],
};

const MAX_MESSAGE_LENGTH = 500;
```

- [ ] **Step 2: Implement GET handler**

Append to the same file:

```typescript
export const GET: APIRoute = async ({ locals, url }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const source_type = url.searchParams.get('source_type');
  const source_id = url.searchParams.get('source_id');
  const locale = url.searchParams.get('locale');

  if (!source_type || !VALID_SOURCE_TYPES.includes(source_type as any)) {
    return json({ error: 'Invalid source_type' }, 400);
  }
  if (!source_id) {
    return json({ error: 'Missing source_id' }, 400);
  }
  if (!locale || !VALID_LOCALES.includes(locale as any)) {
    return json({ error: 'Invalid locale' }, 400);
  }

  const supabase = authSupabase(locals.accessToken);
  const { data, error } = await supabase
    .from('content_feedback')
    .select('reaction, reason, message')
    .eq('user_id', locals.user.id)
    .eq('source_type', source_type)
    .eq('source_id', source_id)
    .eq('locale', locale)
    .maybeSingle();

  if (error) return json({ error: error.message }, 500);

  return json({
    reaction: data?.reaction ?? null,
    reason: data?.reason ?? null,
    message: data?.message ?? null,
  });
};
```

- [ ] **Step 3: Implement POST handler**

Append to the same file:

```typescript
export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const body = await request.json();
  const { source_type, source_id, locale, reaction, reason, message } = body;

  if (!source_type || !VALID_SOURCE_TYPES.includes(source_type)) {
    return json({ error: 'Invalid source_type' }, 400);
  }
  if (!source_id) {
    return json({ error: 'Missing source_id' }, 400);
  }
  if (!locale || !VALID_LOCALES.includes(locale)) {
    return json({ error: 'Invalid locale' }, 400);
  }
  if (!reaction || !VALID_REACTIONS.includes(reaction)) {
    return json({ error: 'Invalid reaction' }, 400);
  }
  if (reaction === 'positive' && reason) {
    return json({ error: 'reason must be null for positive reaction' }, 400);
  }
  if (reaction === 'negative') {
    const allowed = VALID_REASONS[source_type];
    if (!reason || !allowed?.includes(reason)) {
      return json({ error: `Invalid reason for ${source_type}` }, 400);
    }
  }
  if (message && message.length > MAX_MESSAGE_LENGTH) {
    return json({ error: `Message exceeds ${MAX_MESSAGE_LENGTH} chars` }, 400);
  }

  const supabase = authSupabase(locals.accessToken);
  const payload = {
    user_id: locals.user.id,
    source_type,
    source_id,
    locale,
    reaction,
    reason: reaction === 'positive' ? null : reason,
    message: message?.trim() || null,
    updated_at: new Date().toISOString(),
  };

  const { data, error } = await supabase
    .from('content_feedback')
    .upsert(payload, { onConflict: 'user_id,source_type,source_id,locale' })
    .select('reaction, reason, message')
    .single();

  if (error) return json({ error: error.message }, 500);

  return json({ reaction: data.reaction, reason: data.reason, message: data.message });
};
```

- [ ] **Step 4: Implement DELETE handler**

Append to the same file:

```typescript
export const DELETE: APIRoute = async ({ locals, url }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const source_type = url.searchParams.get('source_type');
  const source_id = url.searchParams.get('source_id');
  const locale = url.searchParams.get('locale');

  if (!source_type || !source_id || !locale) {
    return json({ error: 'Missing required params' }, 400);
  }

  const supabase = authSupabase(locals.accessToken);
  const { error } = await supabase
    .from('content_feedback')
    .delete()
    .eq('user_id', locals.user.id)
    .eq('source_type', source_type)
    .eq('source_id', source_id)
    .eq('locale', locale);

  if (error) return json({ error: error.message }, 500);

  return json({ success: true });
};
```

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build passes with 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/api/user/content-feedback.ts
git commit -m "feat: add content-feedback API route (GET/POST/DELETE) with reason validation"
```

---

## Chunk 2: Frontend Component + Client Script + Page Mounting

### Task 3: Create ContentFeedback.astro component

**Files:**
- Create: `frontend/src/components/common/ContentFeedback.astro`
- Reference: `frontend/src/components/newsprint/HandbookFeedback.astro` (existing pattern)

**Key differences from HandbookFeedback.astro:**
- `sourceType` + `sourceId` instead of `termId`
- Generic copy ("이 콘텐츠가 도움이 되었나요?") instead of handbook-specific
- `data-source-type` and `data-source-id` attributes instead of `data-term-id`
- Buttons: 👍 positive / 👎 negative instead of helpful / confusing

- [ ] **Step 1: Create the component**

Create `frontend/src/components/common/ContentFeedback.astro`:

```astro
---
interface Props {
  sourceType: 'news' | 'handbook' | 'blog' | 'product';
  sourceId: string;
  locale: 'ko' | 'en';
  isAuthenticated: boolean;
  loginUrl: string;
  previewMode?: boolean;
}

const { sourceType, sourceId, locale, isAuthenticated = false, loginUrl, previewMode = false } = Astro.props;

const copy =
  locale === 'ko'
    ? {
        title: '이 콘텐츠가 도움이 되었나요?',
        body: '피드백은 콘텐츠 개선에 활용됩니다.',
        positive: '도움이 됐어요',
        negative: '별로에요',
        thanks: '감사합니다! 피드백이 기록되었습니다.',
        error: '피드백 저장에 실패했습니다.',
        previewNote: 'Preview mode · feedback is read-only.',
      }
    : {
        title: 'Was this content helpful?',
        body: 'Your feedback helps us improve.',
        positive: 'Helpful',
        negative: 'Not great',
        thanks: 'Thanks! Your feedback has been recorded.',
        error: 'Failed to save feedback.',
        previewNote: 'Preview mode · feedback is read-only.',
      };
---

<section
  class="content-feedback"
  aria-label={copy.title}
  data-content-feedback
  data-preview-mode={previewMode ? 'true' : 'false'}
  data-source-type={sourceType}
  data-source-id={sourceId}
  data-locale={locale}
  data-authenticated={isAuthenticated ? 'true' : 'false'}
  data-auth-action="feedback"
  data-login-url={loginUrl}
  data-thanks={copy.thanks}
  data-error={copy.error}
>
  <div class="content-feedback-inner">
    <div class="content-feedback-copy">
      <h3 class="content-feedback-title">{copy.title}</h3>
      <p class="content-feedback-body">{copy.body}</p>
      {previewMode && <p class="content-feedback-preview-note">{copy.previewNote}</p>}
      <p class="content-feedback-status" data-feedback-status aria-live="polite" hidden></p>
    </div>
    <div class="content-feedback-actions">
      <button
        type="button"
        class="content-feedback-btn content-feedback-btn--positive"
        aria-label={copy.positive}
        aria-pressed="false"
        data-reaction="positive"
        data-auth-action="feedback"
        aria-disabled={previewMode ? 'true' : undefined}
        tabindex={previewMode ? '-1' : undefined}
        disabled={previewMode}
      >
        {copy.positive}
      </button>
      <button
        type="button"
        class="content-feedback-btn content-feedback-btn--negative"
        aria-label={copy.negative}
        aria-pressed="false"
        data-reaction="negative"
        data-auth-action="feedback"
        aria-disabled={previewMode ? 'true' : undefined}
        tabindex={previewMode ? '-1' : undefined}
        disabled={previewMode}
      >
        {copy.negative}
      </button>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/common/ContentFeedback.astro
git commit -m "feat: add ContentFeedback.astro universal feedback component"
```

---

### Task 4: Create contentFeedback.ts client script

**Files:**
- Create: `frontend/src/scripts/contentFeedback.ts`
- Reference: `frontend/src/scripts/handbookFeedback.ts` (existing pattern)

**Key changes from handbookFeedback.ts:**
- API endpoint: `/api/user/content-feedback` instead of `/api/user/term-feedback`
- Bottom Sheet: reason radio buttons (sourceType-dependent) instead of helpful/confusing toggle
- Params: `source_type` + `source_id` instead of `term_id`
- 👍 positive = immediate POST (no sheet); 👎 negative = open sheet with reasons

- [ ] **Step 1: Create the reason config and Bottom Sheet builder**

Create `frontend/src/scripts/contentFeedback.ts`:

```typescript
import { openAuthPrompt } from './auth-prompt';

/* ── Reason config per source type ─────────────────────── */

type SourceType = 'news' | 'handbook' | 'blog' | 'product';

interface ReasonOption {
  value: string;
  ko: string;
  en: string;
}

const REASONS: Record<SourceType, ReasonOption[]> = {
  news: [
    { value: 'inaccurate', ko: '부정확함', en: 'Inaccurate' },
    { value: 'hard_to_understand', ko: '이해하기 어려움', en: 'Hard to understand' },
    { value: 'too_shallow', ko: '깊이가 부족함', en: 'Too shallow' },
    { value: 'other', ko: '기타', en: 'Other' },
  ],
  handbook: [
    { value: 'confusing', ko: '설명이 혼란스러움', en: 'Confusing explanation' },
    { value: 'lacks_examples', ko: '예시가 부족함', en: 'Lacks examples' },
    { value: 'outdated', ko: '정보가 오래됨', en: 'Outdated information' },
    { value: 'other', ko: '기타', en: 'Other' },
  ],
  blog: [
    { value: 'not_helpful', ko: '도움 안 됨', en: 'Not helpful' },
    { value: 'lacks_depth', ko: '내용이 부족함', en: 'Lacks depth' },
    { value: 'other', ko: '기타', en: 'Other' },
  ],
  product: [
    { value: 'inaccurate_info', ko: '정보가 부정확함', en: 'Inaccurate info' },
    { value: 'not_useful', ko: '유용하지 않음', en: 'Not useful' },
    { value: 'other', ko: '기타', en: 'Other' },
  ],
};

/* ── Helpers ───────────────────────────────────────────── */

function resolveRedirect(root: HTMLElement): string {
  return root.dataset.authRedirect || `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

/* ── Bottom Sheet ──────────────────────────────────────── */

function createFeedbackSheet(sourceType: SourceType, locale: string): HTMLElement {
  const isKo = locale === 'ko';
  const reasons = REASONS[sourceType];
  const sheet = document.createElement('div');
  sheet.className = 'feedback-sheet';
  sheet.setAttribute('role', 'dialog');
  sheet.setAttribute('aria-label', isKo ? '피드백 보내기' : 'Send feedback');

  const reasonsHtml = reasons
    .map(
      (r) => `
    <label class="feedback-sheet-reason">
      <input type="radio" name="feedback-reason" value="${r.value}" />
      <span>${isKo ? r.ko : r.en}</span>
    </label>`,
    )
    .join('');

  sheet.innerHTML = `
    <button class="feedback-sheet-close" aria-label="${isKo ? '닫기' : 'Close'}">&times;</button>
    <h3 class="feedback-sheet-title">${isKo ? '어떤 점이 아쉬웠나요?' : 'What could be better?'}</h3>
    <div class="feedback-sheet-reasons">${reasonsHtml}</div>
    <textarea class="feedback-sheet-textarea" placeholder="${isKo ? '추가 의견이 있다면... (선택사항)' : 'Additional comments (optional)'}" maxlength="500"></textarea>
    <button type="button" class="feedback-sheet-submit" disabled>${isKo ? '제출하기' : 'Submit'}</button>
  `;
  return sheet;
}

function openFeedbackSheet(opts: {
  sourceType: SourceType;
  sourceId: string;
  locale: string;
  existingReason: string | null;
  existingMessage: string | null;
  onSuccess: () => void;
}): void {
  const { sourceType, sourceId, locale, existingReason, existingMessage, onSuccess } = opts;
  const isKo = locale === 'ko';

  const backdrop = document.createElement('div');
  backdrop.className = 'feedback-sheet-backdrop';
  document.body.appendChild(backdrop);

  const sheet = createFeedbackSheet(sourceType, locale);
  document.body.appendChild(sheet);

  let selectedReason = existingReason;

  // restore existing state
  if (selectedReason) {
    const radio = sheet.querySelector<HTMLInputElement>(`input[value="${selectedReason}"]`);
    if (radio) {
      radio.checked = true;
      (sheet.querySelector('.feedback-sheet-submit') as HTMLButtonElement).disabled = false;
    }
  }
  if (existingMessage) {
    (sheet.querySelector('.feedback-sheet-textarea') as HTMLTextAreaElement).value = existingMessage;
  }

  // reason radios
  sheet.querySelectorAll<HTMLInputElement>('input[name="feedback-reason"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      selectedReason = radio.value;
      (sheet.querySelector('.feedback-sheet-submit') as HTMLButtonElement).disabled = false;
    });
  });

  // submit
  sheet.querySelector('.feedback-sheet-submit')?.addEventListener('click', async () => {
    if (!selectedReason) return;
    const submitBtn = sheet.querySelector('.feedback-sheet-submit') as HTMLButtonElement;
    const textarea = sheet.querySelector('.feedback-sheet-textarea') as HTMLTextAreaElement;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="btn-spinner"></span>${isKo ? '보내는 중...' : 'Sending...'}`;

    try {
      const res = await fetch('/api/user/content-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: sourceType,
          source_id: sourceId,
          locale,
          reaction: 'negative',
          reason: selectedReason,
          message: textarea.value.trim() || null,
        }),
      });

      if (!res.ok) {
        submitBtn.disabled = false;
        submitBtn.textContent = isKo ? '제출하기' : 'Submit';
        return;
      }

      // success
      const title = sheet.querySelector('.feedback-sheet-title');
      const reasons = sheet.querySelector('.feedback-sheet-reasons');
      const ta = sheet.querySelector('.feedback-sheet-textarea');
      title?.remove(); reasons?.remove(); ta?.remove(); submitBtn.remove();

      const success = document.createElement('div');
      success.className = 'feedback-sheet-success';
      success.textContent = isKo ? '감사합니다! 피드백이 전달되었습니다.' : 'Thank you! Your feedback has been sent.';
      sheet.querySelector('.feedback-sheet-close')!.after(success);

      onSuccess();
      setTimeout(() => close(), 1500);
    } catch {
      submitBtn.disabled = false;
      submitBtn.textContent = isKo ? '제출하기' : 'Submit';
    }
  });

  // close helpers
  function close() {
    backdrop.classList.remove('feedback-sheet-backdrop--open');
    sheet.classList.remove('feedback-sheet--open');
    setTimeout(() => { backdrop.remove(); sheet.remove(); }, 250);
  }
  backdrop.addEventListener('click', close);
  sheet.querySelector('.feedback-sheet-close')?.addEventListener('click', close);
  document.addEventListener('keydown', function esc(e) {
    if (e.key === 'Escape') { close(); document.removeEventListener('keydown', esc); }
  });

  // open animation
  requestAnimationFrame(() => {
    backdrop.classList.add('feedback-sheet-backdrop--open');
    sheet.classList.add('feedback-sheet--open');
  });
}
```

- [ ] **Step 2: Add the main init function**

Append to the same file:

```typescript
/* ── Main init ────────────────────────────────────────── */

function initContentFeedback(): void {
  document.querySelectorAll<HTMLElement>('[data-content-feedback]').forEach((root) => {
    if (root.dataset.feedbackInit === 'true') return;
    root.dataset.feedbackInit = 'true';

    const sourceType = root.dataset.sourceType as SourceType;
    const sourceId = root.dataset.sourceId;
    const locale = root.dataset.locale;
    const isAuthenticated = root.dataset.authenticated === 'true';
    const previewMode = root.dataset.previewMode === 'true';
    const thanksMessage = root.dataset.thanks || 'Thanks!';
    const errorMessage = root.dataset.error || 'Failed to save.';
    const status = root.querySelector<HTMLElement>('[data-feedback-status]');
    const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>('[data-reaction]'));

    if (!sourceType || !sourceId || !locale || buttons.length === 0) return;

    let currentReaction: string | null = null;
    let currentReason: string | null = null;
    let currentMessage: string | null = null;

    const setSelectedReaction = (reaction: string | null) => {
      currentReaction = reaction;
      buttons.forEach((btn) => {
        const isSelected = btn.dataset.reaction === reaction;
        btn.classList.toggle('is-selected', isSelected);
        btn.ariaPressed = isSelected ? 'true' : 'false';
      });
    };

    const setStatus = (msg: string) => {
      if (status) {
        status.textContent = msg;
        status.hidden = !msg;
      }
    };

    // load existing feedback on mount
    const loadExisting = async () => {
      if (!isAuthenticated) return;
      try {
        const res = await fetch(
          `/api/user/content-feedback?source_type=${encodeURIComponent(sourceType)}&source_id=${encodeURIComponent(sourceId)}&locale=${encodeURIComponent(locale)}`,
        );
        if (!res.ok) return;
        const data = await res.json();
        if (data.reaction) setSelectedReaction(data.reaction);
        currentReason = data.reason ?? null;
        currentMessage = data.message ?? null;
      } catch {
        // silent — progressive enhancement
      }
    };

    // button click handlers
    buttons.forEach((btn) => {
      btn.addEventListener('click', async () => {
        const reaction = btn.dataset.reaction;
        if (!reaction || previewMode) return;

        if (!isAuthenticated) {
          openAuthPrompt({ action: 'feedback', redirectTo: resolveRedirect(root) });
          return;
        }

        // negative → open bottom sheet with reasons
        if (reaction === 'negative') {
          openFeedbackSheet({
            sourceType,
            sourceId,
            locale,
            existingReason: currentReason,
            existingMessage: currentMessage,
            onSuccess: () => {
              setSelectedReaction('negative');
              setStatus(thanksMessage);
            },
          });
          return;
        }

        // positive → immediate POST
        btn.disabled = true;
        setStatus('');

        try {
          const res = await fetch('/api/user/content-feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              source_type: sourceType,
              source_id: sourceId,
              locale,
              reaction: 'positive',
            }),
          });

          if (res.status === 401) {
            openAuthPrompt({ action: 'feedback', redirectTo: resolveRedirect(root) });
            return;
          }

          if (!res.ok) {
            setStatus(errorMessage);
            return;
          }

          setSelectedReaction('positive');
          currentReason = null;
          currentMessage = null;
          setStatus(thanksMessage);
        } catch {
          setStatus(errorMessage);
        } finally {
          btn.disabled = false;
        }
      });
    });

    void loadExisting();
  });
}

document.addEventListener('astro:page-load', initContentFeedback);
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/scripts/contentFeedback.ts
git commit -m "feat: add contentFeedback.ts client script with reason-based bottom sheet"
```

---

### Task 5: Update CSS classes

**Files:**
- Modify: `frontend/src/styles/global.css` (lines ~6399-6524)

- [ ] **Step 1: Rename `.handbook-feedback-*` → `.content-feedback-*`**

In `frontend/src/styles/global.css`, find all `.handbook-feedback` class selectors and rename:
- `.handbook-feedback` → `.content-feedback`
- `.handbook-feedback-inner` → `.content-feedback-inner`
- `.handbook-feedback-copy` → `.content-feedback-copy`
- `.handbook-feedback-title` → `.content-feedback-title`
- `.handbook-feedback-body` → `.content-feedback-body`
- `.handbook-feedback-preview-note` → `.content-feedback-preview-note`
- `.handbook-feedback-status` → `.content-feedback-status`
- `.handbook-feedback-actions` → `.content-feedback-actions`
- `.handbook-feedback-btn` → `.content-feedback-btn`
- `.handbook-feedback-btn--confusing` → `.content-feedback-btn--negative`
- `.handbook-feedback-btn--helpful` → `.content-feedback-btn--positive`

Also add CSS for the new reason radio buttons in the Bottom Sheet:

```css
/* ── Feedback Sheet — Reason radios ── */
.feedback-sheet-reasons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-block: 0.75rem;
}
.feedback-sheet-reason {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: border-color 0.15s, background-color 0.15s;
}
.feedback-sheet-reason:hover {
  border-color: var(--color-accent);
}
.feedback-sheet-reason:has(input:checked) {
  border-color: var(--color-accent);
  background: color-mix(in srgb, var(--color-accent) 8%, transparent);
}
.feedback-sheet-reason input[type="radio"] {
  accent-color: var(--color-accent);
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build passes.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat: rename handbook-feedback CSS to content-feedback, add reason radio styles"
```

---

### Task 6: Update StickyReadingActions to remove old feedback buttons

**Files:**
- Modify: `frontend/src/components/common/StickyReadingActions.astro`

The `variant === 'term'` branch currently embeds `data-handbook-feedback` with helpful/confusing buttons. Since feedback now lives as a standalone section at page bottom, the term variant should show only bookmark + share (no feedback buttons).

- [ ] **Step 1: Update the term variant**

In `StickyReadingActions.astro`, replace the `variant === 'term'` branch:
- Remove `data-handbook-feedback`, `data-term-id`, `data-thanks-helpful`, `data-thanks-confusing`, `data-error` attributes from the `<aside>` tag
- Remove the `reading-actions__group--primary` div containing helpful/confusing buttons
- Keep only the `reading-actions__group--secondary` div (bookmark + share)
- Remove the `data-feedback-status` paragraph
- Remove feedback-related copy entries (`helpful`, `confusing`, `thanksHelpful`, `thanksConfusing`, `error`)

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/common/StickyReadingActions.astro
git commit -m "refactor: remove feedback buttons from StickyReadingActions term variant"
```

---

### Task 7: Mount ContentFeedback on all detail pages

**Files:**
- Modify: `frontend/src/pages/ko/handbook/[slug].astro`
- Modify: `frontend/src/pages/en/handbook/[slug].astro`
- Modify: `frontend/src/pages/ko/news/[slug].astro`
- Modify: `frontend/src/pages/en/news/[slug].astro`
- Modify: `frontend/src/pages/ko/blog/[slug].astro`
- Modify: `frontend/src/pages/en/blog/[slug].astro`
- Modify: `frontend/src/pages/ko/products/[slug].astro`
- Modify: `frontend/src/pages/en/products/[slug].astro`

**Pattern for each page:**
1. Add import: `import ContentFeedback from '...components/common/ContentFeedback.astro';` (adjust relative path)
2. Add `<script>import '...scripts/contentFeedback';</script>` block
3. Mount `<ContentFeedback>` at the correct location with appropriate props

**Important:** Each page must have `user` variable available (from `Astro.locals.user`). Handbook, news, and blog pages already have this. Product pages do NOT — must add it.

- [ ] **Step 1: Mount on handbook pages (ko + en)**

Both handbook `[slug].astro` files — add after `<div data-reading-end></div>` and learning check, before admin actions:

```astro
import ContentFeedback from '../../../components/common/ContentFeedback.astro';
```

```astro
<ContentFeedback
  sourceType="handbook"
  sourceId={term.id}
  locale={locale}
  isAuthenticated={!!user}
  loginUrl={`/api/auth/login?redirect=${encodeURIComponent(Astro.url.pathname)}`}
  previewMode={previewMode}
/>
```

Add script import at bottom:
```astro
<script>
import '../../../scripts/contentFeedback';
</script>
```

- [ ] **Step 2: Mount on news pages (ko + en)**

Both news `[slug].astro` files. Mount after `<div data-reading-end></div>`, before comments section.

```astro
import ContentFeedback from '../../../components/common/ContentFeedback.astro';
```

```astro
<ContentFeedback
  sourceType="news"
  sourceId={post.id}
  locale={locale}
  isAuthenticated={!!user}
  loginUrl={`/api/auth/login?redirect=${encodeURIComponent(Astro.url.pathname)}`}
  previewMode={previewMode}
/>
```

```astro
<script>
import '../../../scripts/contentFeedback';
</script>
```

- [ ] **Step 3: Mount on blog pages (ko + en)**

Both blog `[slug].astro` files. Mount after article body, before next post navigation.

```astro
import ContentFeedback from '../../../components/common/ContentFeedback.astro';
```

```astro
<ContentFeedback
  sourceType="blog"
  sourceId={post.id}
  locale={locale}
  isAuthenticated={!!user}
  loginUrl={`/api/auth/login?redirect=${encodeURIComponent(Astro.url.pathname)}`}
  previewMode={previewMode}
/>
```

```astro
<script>
import '../../../scripts/contentFeedback';
</script>
```

Note: Blog pages DO have `previewMode` variable — pass it.

- [ ] **Step 4: Mount on product pages (ko + en)**

Both product `[slug].astro` files need a new `user` variable. Add to frontmatter:
```astro
const user = Astro.locals.user;
```

Then mount after the bottom CTA button, before `</article>` close:

```astro
import ContentFeedback from '../../../components/common/ContentFeedback.astro';
```

```astro
<ContentFeedback
  sourceType="product"
  sourceId={product.id}
  locale={locale}
  isAuthenticated={!!user}
  loginUrl={`/api/auth/login?redirect=${encodeURIComponent(Astro.url.pathname)}`}
/>
```

```astro
<script>
import '../../../scripts/contentFeedback';
</script>
```

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build passes with 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ko/handbook/[slug].astro frontend/src/pages/en/handbook/[slug].astro
git add frontend/src/pages/ko/news/[slug].astro frontend/src/pages/en/news/[slug].astro
git add frontend/src/pages/ko/blog/[slug].astro frontend/src/pages/en/blog/[slug].astro
git add frontend/src/pages/ko/products/[slug].astro frontend/src/pages/en/products/[slug].astro
git commit -m "feat: mount ContentFeedback on all detail pages (news, handbook, blog, product)"
```

---

## Chunk 3: Admin Dashboard Update + Cleanup + Tests

> **Note:** Tasks 8-11 complete the system migration.

### Task 8: Update admin feedback dashboard

**Files:**
- Modify: `frontend/src/pages/admin/feedback/index.astro` (existing, 424 lines)
- Modify: `frontend/src/pages/api/admin/feedback/archive.ts` (change table name)

**Changes needed:**
1. Query `content_feedback` instead of `term_feedback`
2. JOIN against all 4 content tables (news_posts, handbook_terms, blog_posts, ai_products)
3. Enable all source tabs (News, Blog, Product — currently disabled)
4. Update filter logic for `positive/negative` instead of `helpful/confusing`
5. Add reason tag display
6. Update archive API endpoint to use `content_feedback`

- [ ] **Step 1: Update data fetching query**

Change the Supabase query from `term_feedback` to `content_feedback`. The admin page currently queries:
```typescript
supabase.from('term_feedback').select('*, handbook_terms(term, slug)')
```

Replace with a query that fetches all content feedback with content titles. Since Supabase JS client doesn't support the complex CASE JOIN from the spec, fetch feedback rows first, then batch-fetch content titles by source_type:

```typescript
// Fetch all feedback
const { data: feedbackRows } = await supabase
  .from('content_feedback')
  .select('*')
  .order('updated_at', { ascending: false });

// Batch fetch content titles per type
const newsIds = feedbackRows?.filter(r => r.source_type === 'news').map(r => r.source_id) ?? [];
const handbookIds = feedbackRows?.filter(r => r.source_type === 'handbook').map(r => r.source_id) ?? [];
const blogIds = feedbackRows?.filter(r => r.source_type === 'blog').map(r => r.source_id) ?? [];
const productIds = feedbackRows?.filter(r => r.source_type === 'product').map(r => r.source_id) ?? [];

const [newsRes, handbookRes, blogRes, productRes] = await Promise.all([
  newsIds.length ? supabase.from('news_posts').select('id, title, slug').in('id', newsIds) : { data: [] },
  handbookIds.length ? supabase.from('handbook_terms').select('id, term, slug').in('id', handbookIds) : { data: [] },
  blogIds.length ? supabase.from('blog_posts').select('id, title, slug').in('id', blogIds) : { data: [] },
  productIds.length ? supabase.from('ai_products').select('id, name, slug').in('id', productIds) : { data: [] },
]);

// Build title/slug lookup maps
const titleMap = new Map<string, { title: string; slug: string }>();
for (const r of newsRes.data ?? []) titleMap.set(r.id, { title: r.title, slug: r.slug });
for (const r of handbookRes.data ?? []) titleMap.set(r.id, { title: r.term, slug: r.slug });
for (const r of blogRes.data ?? []) titleMap.set(r.id, { title: r.title, slug: r.slug });
for (const r of productRes.data ?? []) titleMap.set(r.id, { title: r.name, slug: r.slug });

// Enrich feedback rows
const feedbacks = (feedbackRows ?? []).map(row => ({
  ...row,
  content_title: titleMap.get(row.source_id)?.title ?? '(삭제된 콘텐츠)',
  content_slug: titleMap.get(row.source_id)?.slug ?? null,
}));
```

- [ ] **Step 2: Update source tab filtering**

Enable all tabs and filter by `source_type`:

```javascript
// Client-side tab filtering
const activeTab = 'all'; // default
const filteredByTab = activeTab === 'all'
  ? feedbacks
  : feedbacks.filter(f => f.source_type === activeTab);
```

Tab HTML — remove `disabled` from News, Blog, Product tabs.

- [ ] **Step 3: Update reaction display**

Change `helpful/confusing` badges to `positive/negative`:
- `positive` → 👍 green badge
- `negative` → 👎 red badge + reason tag

- [ ] **Step 4: Update editor link routing**

Content title click → route to correct editor based on `source_type`:
```javascript
function getEditorUrl(sourceType: string, slug: string | null): string {
  if (!slug) return '#';
  switch (sourceType) {
    case 'news': return `/admin/posts/edit/${slug}`;
    case 'handbook': return `/admin/handbook/edit/${slug}`;
    case 'blog': return `/admin/blog/edit/${slug}`;
    case 'product': return `/admin/products/edit/${slug}`;
    default: return '#';
  }
}
```

- [ ] **Step 5: Update archive endpoint**

Change archive/restore fetch from `term_feedback` → `content_feedback`:
```javascript
await fetch('/api/admin/feedback-archive', {
  method: 'POST',
  body: JSON.stringify({ id: feedbackId, archived: !currentArchived }),
});
```

- [ ] **Step 6: Update archive API endpoint**

In `frontend/src/pages/api/admin/feedback/archive.ts`, change line 34:

```typescript
// Before:
.from('term_feedback')
// After:
.from('content_feedback')
```

- [ ] **Step 7: Verify build + visual check**

```bash
cd frontend && npm run build
```

Then manually verify at `/admin/feedback/` — tabs should all be active, data should display with new reaction format.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/admin/feedback/index.astro frontend/src/pages/api/admin/feedback/archive.ts
git commit -m "feat: update admin feedback dashboard + archive API for content_feedback"
```

---

### Task 9: Remove old feedback system files

**Files:**
- Delete: `frontend/src/pages/api/user/term-feedback.ts`
- Delete: `frontend/src/components/newsprint/HandbookFeedback.astro`
- Delete: `frontend/src/scripts/handbookFeedback.ts`
- Delete: `frontend/tests/handbook-feedback-api-contract.test.cjs`
- Delete: `frontend/tests/handbook-feedback-layout.test.cjs`
- Delete: `frontend/tests/handbook-feedback-order.test.cjs`
- Delete: `frontend/tests/news-handbook-feedback-copy.test.cjs`

- [ ] **Step 1: Remove old files**

```bash
git rm frontend/src/pages/api/user/term-feedback.ts
git rm frontend/src/components/newsprint/HandbookFeedback.astro
git rm frontend/src/scripts/handbookFeedback.ts
git rm frontend/tests/handbook-feedback-api-contract.test.cjs
git rm frontend/tests/handbook-feedback-layout.test.cjs
git rm frontend/tests/handbook-feedback-order.test.cjs
git rm frontend/tests/news-handbook-feedback-copy.test.cjs
```

- [ ] **Step 2: Grep for leftover references**

```bash
cd frontend && grep -r "term-feedback\|handbookFeedback\|HandbookFeedback\|handbook-feedback" src/ --include="*.ts" --include="*.astro" -l
```

Expected: No results. If any file still references old names, update them.

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build passes with 0 errors.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove old term_feedback system files (replaced by content_feedback)"
```

---

### Task 10: Write contract tests

**Files:**
- Create: `frontend/tests/content-feedback-contract.test.cjs`

- [ ] **Step 1: Write the test file**

```javascript
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

describe('Content Feedback — Contract Tests', () => {
  // API
  test('content-feedback API exists with GET/POST/DELETE', () => {
    const api = fs.readFileSync(path.join(root, 'src/pages/api/user/content-feedback.ts'), 'utf8');
    expect(api).toContain('export const GET');
    expect(api).toContain('export const POST');
    expect(api).toContain('export const DELETE');
    expect(api).toContain("from('content_feedback')");
    expect(api).toContain('source_type');
    expect(api).toContain('source_id');
  });

  test('API validates reason per source_type', () => {
    const api = fs.readFileSync(path.join(root, 'src/pages/api/user/content-feedback.ts'), 'utf8');
    expect(api).toContain('VALID_REASONS');
    expect(api).toContain('inaccurate');
    expect(api).toContain('confusing');
    expect(api).toContain('not_helpful');
    expect(api).toContain('inaccurate_info');
  });

  // Component
  test('ContentFeedback.astro has correct data attributes', () => {
    const comp = fs.readFileSync(path.join(root, 'src/components/common/ContentFeedback.astro'), 'utf8');
    expect(comp).toContain('data-content-feedback');
    expect(comp).toContain('data-source-type');
    expect(comp).toContain('data-source-id');
    expect(comp).toContain('data-reaction="positive"');
    expect(comp).toContain('data-reaction="negative"');
  });

  // Script
  test('contentFeedback.ts calls content-feedback API', () => {
    const script = fs.readFileSync(path.join(root, 'src/scripts/contentFeedback.ts'), 'utf8');
    expect(script).toContain('/api/user/content-feedback');
    expect(script).toContain('source_type');
    expect(script).toContain('initContentFeedback');
    expect(script).toContain('REASONS');
  });

  // Pages mount the component
  const pages = [
    'src/pages/ko/news/[slug].astro',
    'src/pages/en/news/[slug].astro',
    'src/pages/ko/handbook/[slug].astro',
    'src/pages/en/handbook/[slug].astro',
    'src/pages/ko/blog/[slug].astro',
    'src/pages/en/blog/[slug].astro',
    'src/pages/ko/products/[slug].astro',
    'src/pages/en/products/[slug].astro',
  ];

  pages.forEach((pagePath) => {
    test(`${pagePath} imports ContentFeedback and contentFeedback script`, () => {
      const content = fs.readFileSync(path.join(root, pagePath), 'utf8');
      expect(content).toContain('ContentFeedback');
      expect(content).toContain('contentFeedback');
    });
  });

  // Old system removed
  test('old term-feedback system is removed', () => {
    expect(fs.existsSync(path.join(root, 'src/pages/api/user/term-feedback.ts'))).toBe(false);
    expect(fs.existsSync(path.join(root, 'src/components/newsprint/HandbookFeedback.astro'))).toBe(false);
    expect(fs.existsSync(path.join(root, 'src/scripts/handbookFeedback.ts'))).toBe(false);
  });

  // StickyReadingActions no longer has feedback buttons
  test('StickyReadingActions term variant has no feedback buttons', () => {
    const sticky = fs.readFileSync(path.join(root, 'src/components/common/StickyReadingActions.astro'), 'utf8');
    expect(sticky).not.toContain('data-handbook-feedback');
    expect(sticky).not.toContain('data-reaction="helpful"');
    expect(sticky).not.toContain('data-reaction="confusing"');
  });

  // Admin archive API uses content_feedback
  test('admin archive API uses content_feedback table', () => {
    const archive = fs.readFileSync(path.join(root, 'src/pages/api/admin/feedback/archive.ts'), 'utf8');
    expect(archive).toContain("from('content_feedback')");
    expect(archive).not.toContain("from('term_feedback')");
  });

  // CSS
  test('CSS uses content-feedback classes', () => {
    const css = fs.readFileSync(path.join(root, 'src/styles/global.css'), 'utf8');
    expect(css).toContain('.content-feedback');
    expect(css).toContain('.content-feedback-btn--positive');
    expect(css).toContain('.content-feedback-btn--negative');
    expect(css).toContain('.feedback-sheet-reasons');
    expect(css).not.toContain('.handbook-feedback');
  });

  // Admin dashboard
  test('admin feedback page queries content_feedback', () => {
    const admin = fs.readFileSync(path.join(root, 'src/pages/admin/feedback/index.astro'), 'utf8');
    expect(admin).toContain('content_feedback');
    expect(admin).not.toContain('term_feedback');
  });
});
```

- [ ] **Step 2: Run tests**

```bash
cd frontend && npx jest tests/content-feedback-contract.test.cjs --verbose
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/content-feedback-contract.test.cjs
git commit -m "test: add contract tests for unified content feedback system"
```

---

### Task 11: Final verification

- [ ] **Step 1: Full build check**

```bash
cd frontend && npm run build
```

- [ ] **Step 2: Run all tests**

```bash
cd frontend && npx jest --verbose
```

- [ ] **Step 3: Grep for any remaining old references**

```bash
cd frontend && grep -r "term_feedback\|term-feedback\|HandbookFeedback\|handbookFeedback\|handbook-feedback" src/ -l
```

Expected: No results.

- [ ] **Step 4: Verify migration file is ready**

Confirm `supabase/migrations/00032_content_feedback.sql` exists and has correct SQL.

- [ ] **Step 5: Final commit (if any fixes needed)**

```bash
git add -A && git commit -m "chore: final cleanup for unified content feedback system"
```
