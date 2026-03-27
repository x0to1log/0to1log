# Webhook Settings Page UI Polish

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix bugs and improve UX of `/settings/webhooks/` page

**Architecture:** Single-file rewrite of `frontend/src/pages/settings/webhooks.astro` — HTML, CSS, script all scoped inside.

**Tech Stack:** Astro v5 scoped styles, vanilla JS, CSS variables from global.css

---

## Bugs to Fix

1. **i18n broken in card render** — `render()` uses string `.replace()` hack that hardcodes English labels. All card text (Active/Inactive, Test, Delete, Last fired, Failures) ignores `copy` object.
2. **Platform guide switch broken** — `data-discord/slack/custom` attributes never set on `#wh-guide` element. Changing platform dropdown shows empty guide text.
3. **Flash messages hardcoded English** — `flash('Webhook added!')`, `flash('Deleted')`, etc. ignore locale.

## UX Improvements

4. **Empty state icon** — Add envelope SVG icon above empty text for visual warmth.
5. **Platform SVG icons in cards** — Show Discord/Slack/globe icon next to label for instant recognition.
6. **URL masking** — Show `https://discord.com/api/w...k/abc123` instead of full URL. Reduces visual noise and minor security benefit.
7. **Card left border accent** — Color-code cards by platform (Discord: indigo, Slack: green, Custom: muted) using a 3px left border.
8. **Inactive card dimming** — Reduce opacity on inactive cards so active ones stand out.
9. **Delete confirmation i18n** — Use `copy.deleteConfirm` instead of hardcoded English `confirm()`.
10. **Webhook count indicator** — Show "2 / 5" in section title area so user knows remaining quota.

---

### Task 1: Fix i18n — Pass copy strings to script via data attributes

**Files:**
- Modify: `frontend/src/pages/settings/webhooks.astro`

**Step 1:** Add `data-*` attributes to `#wh-list` div to pass all i18n strings from Astro `copy` object to the client script.

HTML changes on `#wh-list`:
```html
<div id="wh-list"
  data-active={copy.active}
  data-inactive={copy.inactive}
  data-test={copy.test}
  data-delete={copy.delete}
  data-delete-confirm={copy.deleteConfirm}
  data-last-fired={copy.lastFired}
  data-failures={copy.failures}
  data-enable={isKo ? '활성화' : 'Enable'}
  data-disable={isKo ? '비활성화' : 'Disable'}
  data-added={isKo ? 'Webhook이 추가되었습니다.' : 'Webhook added!'}
  data-deleted={isKo ? '삭제되었습니다.' : 'Deleted.'}
  data-test-ok={copy.testOk}
  data-test-fail={copy.testFail}
></div>
```

**Step 2:** In `initWebhooks()`, read these from `list.dataset` and use them in `render()` and `flash()` calls instead of hardcoded strings.

**Step 3:** Build and verify.

Run: `cd frontend && npm run build 2>&1 | tail -3`

---

### Task 2: Fix platform guide switch

**Files:**
- Modify: `frontend/src/pages/settings/webhooks.astro`

**Step 1:** Add guide data attributes to `#wh-guide`:
```html
<p class="wh-guide" id="wh-guide"
  data-discord={copy.guideDiscord}
  data-slack={copy.guideSlack}
  data-custom={copy.guideCustom}
>{copy.guideDiscord}</p>
```

**Step 2:** Fix the `platformSelect` change handler to read from `guide.dataset`:
```js
platformSelect.addEventListener('change', () => {
  guide.textContent = guide.dataset[platformSelect.value] || '';
});
```

---

### Task 3: Platform icons + card left border + URL masking + inactive dimming

**Files:**
- Modify: `frontend/src/pages/settings/webhooks.astro`

**Step 1:** Add SVG icon map constant in script:
```js
const PLATFORM_ICONS: Record<string, string> = {
  discord: '<svg viewBox="0 0 24 24" ...>Discord path</svg>',
  slack: '<svg viewBox="0 0 24 24" ...>Slack path</svg>',
  custom: '<svg viewBox="0 0 24 24" ...>Globe path</svg>',
};
const PLATFORM_COLORS: Record<string, string> = {
  discord: '#5865F2',
  slack: '#4A154B',
  custom: 'var(--color-text-muted)',
};
```

**Step 2:** Update card HTML template:
- Add `style="border-left: 3px solid ${PLATFORM_COLORS[h.platform]}"` to `.wh-card`
- Add icon SVG before label
- Mask URL: show first 30 chars + `...` + last 8 chars

**Step 3:** Add CSS:
```css
.wh-card--inactive { opacity: 0.55; }
.wh-card-icon { width: 18px; height: 18px; flex-shrink: 0; }
```

---

### Task 4: Empty state icon + webhook count

**Files:**
- Modify: `frontend/src/pages/settings/webhooks.astro`

**Step 1:** Add bell/envelope SVG to empty state:
```html
<div id="wh-empty" class="wh-empty" hidden>
  <svg class="wh-empty-icon" ...>bell icon</svg>
  <p class="wh-empty-title">...</p>
  <p class="wh-empty-desc">...</p>
</div>
```

**Step 2:** Add count display near section title:
```html
<h2 class="wh-section-title">
  {copy.addTitle} <span id="wh-count" class="wh-count"></span>
</h2>
```

Update `render()` to set: `countEl.textContent = \`${webhooks.length} / 5\``

**Step 3:** CSS for empty icon and count:
```css
.wh-empty-icon { width: 40px; height: 40px; color: var(--color-text-muted); opacity: 0.4; margin-bottom: 0.75rem; }
.wh-count { font-size: 0.75rem; font-weight: 400; color: var(--color-text-muted); }
```

---

### Task 5: Build, verify, commit

**Step 1:** Run build:
```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: `Complete!`

**Step 2:** Commit:
```bash
git add frontend/src/pages/settings/webhooks.astro
git commit -m "fix: webhook settings page i18n + UI polish"
```
