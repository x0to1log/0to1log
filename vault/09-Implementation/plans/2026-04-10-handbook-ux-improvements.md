# Handbook UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve Advanced handbook page readability by (1) collapsing code blocks by default while preserving macOS-window style, (2) adding section-type-specific visual containers for pitfalls/dialogue/tradeoffs, and (3) introducing an Advanced-level sidebar checklist for judgment-level self-check.

**Architecture:** Three independent tracks grouped into two phases. Phase 1 is CSS/renderer-only (no DB, no prompt changes, no regen). Phase 2 adds new DB columns + prompt fields + regeneration-dependent changes, best timed with HB-MIGRATE-138 pilot batch.

**Tech Stack:** Astro v5, TypeScript, remark/rehype pipeline, Shiki, CSS variables, Pydantic v2, Supabase Postgres

---

## Context

### Why this change

After completing HB-REDESIGN (B/A/C, 2026-04-10) and the length/renderer cleanup session (2026-04-10), user reviewed the current Advanced handbook page and flagged three concrete UX concerns:

1. **Advanced is visually monotone** — 7 sections all rendered as `<h2> + paragraph flow`, no visual rhythm to help the reader scan. Compared to Basic's redesigned structure (hero card + 7 sections + sidebar checklist), Advanced feels like a wall of text.

2. **Code blocks dominate scroll real estate** — Advanced §3 "코드 또는 의사코드" produces 15+ line Python/YAML samples. An Expert reader often wants to confirm a concept without scrolling through the full implementation. The existing macOS-window style for code blocks is visually nice but not opt-in.

3. **No Advanced equivalent of Basic's "이해했나요?" checklist** — Basic has a sidebar self-check (`sidebar_checklist_ko/en`) that tests comprehension. Advanced has no parallel affordance for testing **judgment/application** — the higher cognitive levels expected of Expert readers.

Decisions from brainstorm:
- **No emojis in UI** — user feedback: "이모지 사용은 AI 티가 많이 난다". CSS-only visual signaling (colors, borders, typography) preferred.
- **Code should collapse to the existing macOS-window header** — not a different style. Reuse dots + language label + toggle button. Click to expand reveals the code body.
- **Tradeoffs 2-column layout** for §4 specifically — "적합한 경우" / "피해야 할 경우" as side-by-side cards.
- **Pitfalls callout** for §5 specifically — yellow left-border + tinted background, no warning icon.
- **Advanced sidebar checklist** should test judgment/application (Bloom's taxonomy levels 3-5), not comprehension.

### What we are NOT changing

- Basic layout (already redesigned, user satisfied)
- Existing Advanced prompt 7-section structure (HB-REDESIGN-C locked it down)
- Existing references tier (★ primary / · secondary) — user confirmed design is fine
- Existing code block macOS-window header (red/yellow/green dots, lang label, Copy button) — reuse as-is
- News processor or terms processor — only `handbookProcessor` gets the collapsible code

### Intended outcome

- **Phase 1 ships CSS-only improvements** immediately visible on all 52 published terms. No regen, no DB change, no prompt change beyond optional heading hint for §5 pitfalls.
- **Phase 2 introduces a new `sidebar_checklist_advanced` field + 2-column tradeoffs layout** via new rehype plugin. Timed with HB-MIGRATE-138 regen so the new field is populated in bulk.

---

## Critical files

| # | File | Phase | Change type |
|---|---|---|---|
| 1 | [frontend/src/lib/rehypeCodeWindow.ts](frontend/src/lib/rehypeCodeWindow.ts) | 1 | Add `collapsible` option, emit toggle button + line count |
| 2 | [frontend/src/lib/markdown.ts](frontend/src/lib/markdown.ts) | 1 | Pass `{ collapsible: true }` to rehypeCodeWindow in handbookProcessor only |
| 3 | [frontend/src/styles/global.css](frontend/src/styles/global.css) | 1 | Add `.code-window--collapsible`, `.code-window--collapsed` styles + toggle affordances |
| 4 | [frontend/src/scripts/code-toggle.ts](frontend/src/scripts/code-toggle.ts) (new) | 1 | Click handler for collapse/expand toggle |
| 5 | [frontend/src/pages/ko/handbook/[slug].astro](frontend/src/pages/ko/handbook/[slug].astro) + EN | 1 | Import code-toggle script |
| 6 | [frontend/src/styles/global.css](frontend/src/styles/global.css) | 1 | Add `.hb-pitfall-callout`, `.hb-dialogue-quote` styles |
| 7 | [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) | 1 | Hint for §5 pitfalls: each pitfall under `### 함정 제목` heading so CSS can target |
| 8 | New rehype plugin `frontend/src/lib/rehypeHandbookSectionCards.ts` | 2 | Detect §4 "적합한 경우"/"피해야 할 경우" pair → wrap in 2-col grid |
| 9 | [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) | 2 | Add `sidebar_checklist_advanced_ko/en` field + generation instructions |
| 10 | [backend/models/advisor.py](backend/models/advisor.py) | 2 | Add `sidebar_checklist_advanced_ko/en: str = ""` to `GenerateTermResult` |
| 11 | Supabase `handbook_terms` table | 2 | SQL migration: add 2 text columns |
| 12 | [frontend/src/lib/pageData/handbookDetailPage.ts](frontend/src/lib/pageData/handbookDetailPage.ts) | 2 | Fetch new fields, compute advanced checklist |
| 13 | [frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro](frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro) | 2 | Accept `level` prop, swap content on level switch |

---

## Existing code reused

- [rehypeCodeWindow.ts](frontend/src/lib/rehypeCodeWindow.ts) — macOS-window wrapper, extend with collapsible option. Do NOT rewrite the core logic.
- [global.css](frontend/src/styles/global.css) `.code-window-header`, `.code-window-dots`, `.code-copy-btn` — existing styles for macOS dots and copy button. New `.code-window--collapsible` styles build ON TOP, don't replace.
- [HandbookUnderstandingChecklist.astro](frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro) — existing Basic checklist component. Phase 2 adds a `level` prop to swap content, don't create a second component.
- [prompts_advisor.py](backend/services/agents/prompts_advisor.py) `sidebar_checklist_ko/en` section — Phase 2 mirrors the pattern for Advanced, don't invent a new pattern.

---

## Phase 1: CSS/Renderer Only (no regen required)

### Task 1: Extend rehypeCodeWindow with `collapsible` option

**Files:**
- Modify: `frontend/src/lib/rehypeCodeWindow.ts`

**Step 1: Read current implementation to understand the AST manipulation**

Run: `cat frontend/src/lib/rehypeCodeWindow.ts`

Expected: a function that wraps Shiki `<pre>` elements in a `<div class="code-window">` with a header containing dots, language label, and Copy button.

**Step 2: Add `options` parameter with `collapsible` flag**

Change the function signature:
```ts
interface CodeWindowOptions {
  collapsible?: boolean;
}

export default function rehypeCodeWindow(options: CodeWindowOptions = {}) {
  const { collapsible = false } = options;
  return (tree: Root) => {
    // ... existing visit logic
  };
}
```

**Step 3: Inside the visit callback, count lines of the code block**

Before creating `headerChildren`, compute the line count from the code text:
```ts
// Extract code text from <pre><code> for line counting
const codeElement = node.children.find(
  (c): c is Element => c.type === 'element' && c.tagName === 'code'
);
let lineCount = 0;
if (codeElement) {
  const text = extractTextContent(codeElement);
  lineCount = text.split('\n').filter(line => line.length > 0).length;
}
```

Helper `extractTextContent` iterates children recursively and joins `text` type values.

**Step 4: Add line count + toggle button to header when collapsible**

Insert before the Copy button:
```ts
if (collapsible) {
  headerChildren.push({
    type: 'element',
    tagName: 'span',
    properties: { className: ['code-window-lines'] },
    children: [{ type: 'text', value: `${lineCount} lines` }],
  });
  headerChildren.push({
    type: 'element',
    tagName: 'button',
    properties: {
      className: ['code-toggle-btn'],
      'data-code-toggle': '',
      'aria-label': 'Toggle code visibility',
    },
    children: [{ type: 'text', value: '펼치기 ▾' }],
  });
}
```

**Step 5: Add `code-window--collapsible` and `code-window--collapsed` classes to the wrapper**

```ts
const wrapperClasses = ['code-window'];
if (collapsible) {
  wrapperClasses.push('code-window--collapsible', 'code-window--collapsed');
}
const wrapper: Element = {
  type: 'element',
  tagName: 'div',
  properties: { className: wrapperClasses },
  children: [header, node],
};
```

**Step 6: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep rehypeCodeWindow`

Expected: no type errors. If errors, fix the HAST type imports.

### Task 2: Pass `collapsible: true` to handbookProcessor only

**Files:**
- Modify: `frontend/src/lib/markdown.ts`

**Step 1: Find the 3 processors and their rehypeCodeWindow calls**

Run: `grep -n "rehypeCodeWindow" frontend/src/lib/markdown.ts`

Expected: 3 usage lines (default processor, handbookProcessor, terms processor).

**Step 2: Change handbookProcessor only**

Change `.use(rehypeCodeWindow)` to `.use(rehypeCodeWindow, { collapsible: true })` in the **handbookProcessor block only**.

Leave the default processor and terms processor with their bare `.use(rehypeCodeWindow)` call — news and Basic stay expanded by default.

**Step 3: Build verification**

Run: `cd frontend && npm run build 2>&1 | tail -20`

Expected: build succeeds with 0 errors.

### Task 3: Add CSS for collapsible state

**Files:**
- Modify: `frontend/src/styles/global.css` (around existing `.code-window` rules, lines 1315-1430)

**Step 1: Locate existing `.code-window` block**

Run: `grep -n "code-window " frontend/src/styles/global.css | head -5`

**Step 2: Append new collapsible styles after the existing `.code-window` block**

Insert after the scrollbar styles (around line 1430):

```css
/* ========== Collapsible code window (handbook advanced only) ========== */
.code-window--collapsible .code-window-lines {
  color: var(--color-text-muted);
  font-size: 0.7rem;
  font-family: var(--font-code);
  margin-right: 0.5rem;
}

.code-window--collapsible .code-toggle-btn {
  color: var(--color-text-muted);
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  min-width: 2.25rem;
  min-height: 2.25rem;
  padding: 0.35rem 0.5rem;
  margin-left: 0.375rem;
  cursor: pointer;
  font-family: var(--font-code);
  font-size: 0.75rem;
}

.code-window--collapsible .code-toggle-btn:hover {
  color: var(--color-text-primary);
  border-color: var(--color-accent);
}

.code-window--collapsible.code-window--collapsed pre {
  display: none;
}

.code-window--collapsible.code-window--collapsed .code-window-header {
  border-bottom: none;
}

.code-window--collapsible.code-window--collapsed .code-copy-btn {
  display: none;
}
```

**Step 3: Frontend build**

Run: `cd frontend && npm run build`

Expected: 0 errors.

### Task 4: Add client-side toggle script

**Files:**
- Create: `frontend/src/scripts/code-toggle.ts`

**Step 1: Create the script file**

Contents:
```ts
/**
 * Code window collapse/expand toggle.
 * Active on handbook Advanced pages where rehypeCodeWindow({ collapsible: true })
 * adds [data-code-toggle] buttons.
 */
document.addEventListener('click', (event) => {
  const target = event.target as HTMLElement;
  if (!target.matches('[data-code-toggle]')) return;

  const win = target.closest('.code-window--collapsible');
  if (!win) return;

  const isCollapsed = win.classList.toggle('code-window--collapsed');
  target.textContent = isCollapsed ? '펼치기 ▾' : '접기 ▴';
});
```

**Step 2: Import the script in handbook detail pages**

Files to modify:
- `frontend/src/pages/ko/handbook/[slug].astro`
- `frontend/src/pages/en/handbook/[slug].astro`

Find the existing `<script>` imports near the bottom of each page. Add:
```astro
<script>
  import '../../../scripts/code-toggle.ts';
</script>
```

Place it with other script imports (e.g., near the existing handbook level switcher script).

**Step 3: Build verification**

Run: `cd frontend && npm run build`

Expected: 0 errors.

**Step 4: Manual visual verification**

Start dev server: `cd frontend && npm run dev`

Open `http://localhost:4321/ko/handbook/gpu/?level=advanced` and:
1. Confirm `## 코드 또는 의사코드` section shows collapsed code window (header only with `●●● python · 32 lines    펼치기 ▾`)
2. Click `펼치기 ▾` — code body reveals, button becomes `접기 ▴`, Copy button appears
3. Click `접기 ▴` — collapses again

Also check `/ko/news/[any-slug]` — a news article with a code block (if any) should stay EXPANDED (default processor, no collapsible).

### Task 5: Commit Phase 1.1 (code collapse)

```bash
git add frontend/src/lib/rehypeCodeWindow.ts frontend/src/lib/markdown.ts frontend/src/styles/global.css frontend/src/scripts/code-toggle.ts frontend/src/pages/ko/handbook/[slug].astro frontend/src/pages/en/handbook/[slug].astro
git commit -m "feat(handbook): collapsible code blocks in Advanced — macOS window header always visible

HB-UX-01: Advanced §3 code sections are now collapsed by default.
The existing macOS-window header (red/yellow/green dots + language label)
stays visible, plus a line count and 펼치기/접기 toggle button.

- rehypeCodeWindow now accepts { collapsible } option
- handbookProcessor alone passes collapsible: true (news + basic stay expanded)
- CSS: .code-window--collapsed hides <pre>, keeps header
- Client-side toggle script handles click events

Rationale: Expert readers often want to confirm a concept without scrolling
through 30+ lines of Python. Opt-in reveals preserves reading flow."
```

### Task 6: Pitfalls callout styling for §5

**Files:**
- Modify: `frontend/src/styles/global.css`
- Modify: `backend/services/agents/prompts_advisor.py` (optional: hint that §5 items use `### 제목` sub-headings so CSS can target a container)

**Step 1: Read current §5 prompt to see what markdown shape is produced**

Run: `grep -A 10 "adv_ko_5_pitfalls\|adv_en_5_pitfalls" backend/services/agents/prompts_advisor.py | head -40`

Expected: instruction for "3+ concrete mistake-solution pairs" but no specific heading structure.

**Step 2: Decide: container scope strategy**

Option A (zero prompt change): style the whole `## 프로덕션 함정` section's content wrapper.
- Requires a rehype plugin that detects the h2 title and wraps the section body.
- More complex.

Option B (small prompt change): instruct the LLM to structure each pitfall under a sub-heading or a bullet pattern, then style that pattern.
- Simpler — e.g., `- **제목**: 설명` bullets can be wrapped by existing markdown renderer in `<ul><li><strong>`.
- CSS can target `.newsprint-prose h2:has(#프로덕션-함정) + * li` and style each `li` as a callout card.

**Recommended: Option B** (existing markdown patterns + targeted CSS).

The prompt already produces bullets for §5. Add CSS that targets §5's `li` elements specifically:

```css
/* Pitfalls callout — §5 only */
.newsprint-prose h2[id*="프로덕션-함정"] + ul > li,
.newsprint-prose h2[id*="production-pitfalls"] + ul > li {
  list-style: none;
  padding: 0.75rem 1rem 0.75rem 1.25rem;
  margin: 0.75rem 0 0 0;
  background: color-mix(in srgb, var(--color-warning) 8%, transparent);
  border-left: 3px solid var(--color-warning);
  border-radius: var(--radius-sm);
}

.newsprint-prose h2[id*="프로덕션-함정"] + ul,
.newsprint-prose h2[id*="production-pitfalls"] + ul {
  list-style: none;
  padding: 0;
}
```

**Note:** `[id*=...]` matches auto-generated GitHub-flavored heading IDs. Verify the actual IDs by inspecting a rendered page (or adjust to `[id^=...]`).

**Step 3: Verify `--color-warning` exists**

Run: `grep -n "color-warning" frontend/src/styles/global.css | head -5`

Expected: at least one definition. If not, add one to the `@theme` block:
```css
--color-warning: oklch(0.78 0.17 80);  /* muted amber */
```

**Step 4: Build verification**

Run: `cd frontend && npm run build`

Expected: 0 errors.

**Step 5: Visual verification**

Open a handbook page with advanced level and confirm §5 items appear with yellow left border + tinted background.

### Task 7: Industry dialogue blockquote styling for §6

**Files:**
- Modify: `frontend/src/styles/global.css`

**Step 1: Check current blockquote styling in `.newsprint-prose`**

Run: `grep -B 1 -A 5 "newsprint-prose blockquote" frontend/src/styles/global.css`

Expected: some existing blockquote rules. Note the current border/padding.

**Step 2: Enhance blockquote in handbook Advanced §6 context**

Decision: apply across all `.newsprint-prose blockquote` since Advanced §6 is the main use case, and any other use (rare) benefits too.

Add or replace:
```css
.newsprint-prose blockquote {
  border-left: 3px solid var(--color-accent);
  padding: 0.75rem 1rem 0.75rem 1.25rem;
  margin: 1rem 0;
  font-style: italic;
  color: var(--color-text-secondary);
  background: color-mix(in srgb, var(--color-accent) 4%, transparent);
}

.newsprint-prose blockquote p:last-child {
  margin-bottom: 0;
}

.newsprint-prose blockquote p:last-child:has(+ p:first-child)::before,
.newsprint-prose blockquote p:not(:first-child) {
  font-style: normal;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}
```

The last rule styles the attribution line (e.g., `— vendor engineering blog`) differently from the quote body.

**Step 3: Build verification**

Run: `cd frontend && npm run build`

### Task 8: Commit Phase 1.2 (callout + blockquote)

```bash
git add frontend/src/styles/global.css
git commit -m "feat(handbook): section-type visual containers for pitfalls + dialogue

HB-UX-02: §5 프로덕션 함정 bullets now render as warning callouts —
yellow left border + tinted background. CSS-only, no prompt change.
Targets \`h2[id*=프로덕션-함정] + ul > li\` so only §5 is affected.

HB-UX-03: §6 업계 대화 맥락 blockquotes get accent-color left border +
italic quote body + muted attribution line. Applies to all
.newsprint-prose blockquotes (handbook + elsewhere as fallback).

No emojis used — colors + typography + borders signal section type.
No prompt/DB/regen changes. Effect is immediate on all 52 published terms."
```

---

## Phase 2: Tradeoffs Grid + Advanced Checklist (regen-dependent)

> **Timing note:** Phase 2 is best executed DURING HB-MIGRATE-138 pilot batch, so the new `sidebar_checklist_advanced_*` field is populated in the same regen pass. Running Phase 2 code changes NOW is fine, but the new DB field will stay empty until next regen.

### Task 9: Add new rehype plugin for tradeoffs 2-column

**Files:**
- Create: `frontend/src/lib/rehypeHandbookSectionCards.ts`
- Modify: `frontend/src/lib/markdown.ts` (wire into handbookProcessor)
- Modify: `frontend/src/styles/global.css`
- Modify: `backend/services/agents/prompts_advisor.py` (ensure §4 uses the `### 적합한 경우` / `### 피해야 할 경우` heading pair)

**Step 1: Write the rehype plugin**

Contents of `frontend/src/lib/rehypeHandbookSectionCards.ts`:

```ts
import type { Root, Element } from 'hast';
import { visit } from 'unist-util-visit';

/**
 * Detects §4 tradeoffs "적합한 경우" / "피해야 할 경우" heading pair
 * (or EN equivalents: "When to use" / "When to avoid") and wraps the
 * following sibling lists in a 2-column grid container.
 *
 * Input markdown structure:
 *
 *   ## 트레이드오프와 언제 무엇을 쓰나
 *   ### 적합한 경우
 *   - item 1
 *   - item 2
 *   ### 피해야 할 경우
 *   - item 1
 *   - item 2
 *
 * Output HTML:
 *
 *   <div class="hb-tradeoff-grid">
 *     <div class="hb-tradeoff-col hb-tradeoff-col--positive">
 *       <h3>적합한 경우</h3>
 *       <ul>...</ul>
 *     </div>
 *     <div class="hb-tradeoff-col hb-tradeoff-col--negative">
 *       <h3>피해야 할 경우</h3>
 *       <ul>...</ul>
 *     </div>
 *   </div>
 */

const POSITIVE_PATTERNS = [/^적합한 경우/, /^쓸 때/, /^When to use/i];
const NEGATIVE_PATTERNS = [/^피해야 할 경우/, /^쓰지 말/, /^When to avoid/i, /^When NOT to use/i];

function matchesPattern(text: string, patterns: RegExp[]): boolean {
  return patterns.some(p => p.test(text.trim()));
}

function extractHeadingText(node: Element): string {
  const texts: string[] = [];
  for (const child of node.children) {
    if (child.type === 'text') texts.push(child.value);
    else if (child.type === 'element') texts.push(extractHeadingText(child));
  }
  return texts.join('');
}

export default function rehypeHandbookSectionCards() {
  return (tree: Root) => {
    visit(tree, 'element', (node, index, parent) => {
      if (!parent || index === undefined) return;
      if (node.tagName !== 'h3') return;

      const headingText = extractHeadingText(node);
      if (!matchesPattern(headingText, POSITIVE_PATTERNS)) return;

      // Find the following <ul>/<ol> and then look for the negative h3 + list
      const siblings = (parent as Element).children;
      let positiveListIdx = -1;
      let negativeHeadingIdx = -1;
      let negativeListIdx = -1;

      for (let i = index + 1; i < siblings.length; i++) {
        const s = siblings[i];
        if (s.type !== 'element') continue;
        if (positiveListIdx === -1 && (s.tagName === 'ul' || s.tagName === 'ol')) {
          positiveListIdx = i;
          continue;
        }
        if (s.tagName === 'h3' && negativeHeadingIdx === -1) {
          const text = extractHeadingText(s);
          if (matchesPattern(text, NEGATIVE_PATTERNS)) {
            negativeHeadingIdx = i;
          } else {
            break;  // a different h3, stop searching
          }
          continue;
        }
        if (negativeHeadingIdx !== -1 && (s.tagName === 'ul' || s.tagName === 'ol')) {
          negativeListIdx = i;
          break;
        }
      }

      if (positiveListIdx === -1 || negativeHeadingIdx === -1 || negativeListIdx === -1) return;

      const positiveCol: Element = {
        type: 'element',
        tagName: 'div',
        properties: { className: ['hb-tradeoff-col', 'hb-tradeoff-col--positive'] },
        children: [node, siblings[positiveListIdx]],
      };
      const negativeCol: Element = {
        type: 'element',
        tagName: 'div',
        properties: { className: ['hb-tradeoff-col', 'hb-tradeoff-col--negative'] },
        children: [siblings[negativeHeadingIdx], siblings[negativeListIdx]],
      };
      const grid: Element = {
        type: 'element',
        tagName: 'div',
        properties: { className: ['hb-tradeoff-grid'] },
        children: [positiveCol, negativeCol],
      };

      // Replace the 4 consecutive elements with the grid
      (parent as Element).children.splice(index, negativeListIdx - index + 1, grid);
    });
  };
}
```

**Step 2: Wire into handbookProcessor**

Edit `frontend/src/lib/markdown.ts` — in the handbookProcessor block, add the new plugin BEFORE `rehypeCodeWindow`:

```ts
import rehypeHandbookSectionCards from './rehypeHandbookSectionCards';

const handbookProcessor = unified()
  .use(remarkParse)
  .use(remarkGfm)
  .use(remarkMath, { singleDollarTextMath: false })
  .use(remarkRehype, { allowDangerousHtml: true })
  .use(rehypeRaw)
  .use(rehypeSanitize, sanitizeSchema)
  .use(rehypeKatex)
  .use(rehypeShiki, shikiOptions)
  .use(rehypeHandbookSectionCards)  // ← new
  .use(rehypeCodeWindow, { collapsible: true })
  .use(rehypeStringify);
```

**Step 3: Add CSS for the grid**

In `global.css`:

```css
.hb-tradeoff-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin: 1rem 0;
}

.hb-tradeoff-col {
  padding: 0.875rem 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.hb-tradeoff-col--positive {
  border-left: 3px solid var(--color-success);
  background: color-mix(in srgb, var(--color-success) 4%, transparent);
}

.hb-tradeoff-col--negative {
  border-left: 3px solid var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 4%, transparent);
}

.hb-tradeoff-col h3 {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-primary);
}

.hb-tradeoff-col ul {
  margin: 0;
  padding-left: 1.25rem;
}

@media (max-width: 640px) {
  .hb-tradeoff-grid {
    grid-template-columns: 1fr;
  }
}
```

Verify `--color-success` and `--color-danger` exist in the theme. Add if missing.

**Step 4: Update §4 prompt to enforce heading structure**

In `backend/services/agents/prompts_advisor.py`, find the `adv_ko_4_tradeoffs` and `adv_en_4_tradeoffs` sections. Add/clarify the structure:

KO prompt addition:
```
**구조 강제 (2-column 렌더링용):**
아래 형식을 정확히 따라라 — 프론트엔드가 이 heading 쌍을 감지해 2-col 카드로 렌더링한다.

### 적합한 경우
- bullet 1 ...
- bullet 2 ...
- bullet 3 ...

### 피해야 할 경우
- bullet 1 ...
- bullet 2 ...
- bullet 3 ...

다른 heading (예: "Best fit", "Alternatives") 금지. 정확히 이 두 제목만.
```

EN prompt addition (mirror): `### When to use` / `### When to avoid`.

Update rehype plugin `POSITIVE_PATTERNS` / `NEGATIVE_PATTERNS` to match whatever headings the prompt enforces.

**Step 5: Build verification**

Run: `cd frontend && npm run build`
Run: `cd backend && .venv/Scripts/ruff check services/agents/prompts_advisor.py`

Expected: both pass.

**Step 6: Manual verification (needs regen)**

This change takes full effect only after a term is regenerated with the new heading structure. For now, visual verification requires editing a draft term's `body_advanced_ko` in the admin editor to use the `### 적합한 경우` / `### 피해야 할 경우` pattern, save, and reload.

### Task 10: Add `sidebar_checklist_advanced_*` fields

**Files:**
- Modify: Supabase migration
- Modify: `backend/models/advisor.py`
- Modify: `backend/services/agents/prompts_advisor.py`
- Modify: `frontend/src/lib/pageData/handbookDetailPage.ts`
- Modify: `frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro`
- Modify: `frontend/src/pages/ko/handbook/[slug].astro` + EN
- Modify: `frontend/src/pages/api/admin/handbook/save.ts`
- Modify: `frontend/src/pages/admin/handbook/edit/[slug].astro`

**Step 1: SQL migration**

Via Supabase MCP `execute_sql`:
```sql
ALTER TABLE handbook_terms
ADD COLUMN sidebar_checklist_advanced_ko text,
ADD COLUMN sidebar_checklist_advanced_en text;
```

Verify:
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'handbook_terms' AND column_name LIKE 'sidebar_checklist%';
```

Expected: 4 rows (ko/en × basic/advanced).

**Step 2: Extend Pydantic model**

Edit `backend/models/advisor.py`:
```python
class GenerateTermResult(BaseModel):
    # ... existing fields ...
    sidebar_checklist_ko: str = ""
    sidebar_checklist_en: str = ""
    sidebar_checklist_advanced_ko: str = ""  # NEW
    sidebar_checklist_advanced_en: str = ""  # NEW
```

**Step 3: Add field generation to Advanced prompt**

In `backend/services/agents/prompts_advisor.py`, find `GENERATE_ADVANCED_PROMPT` (around line 1349+). Add a new section near the end of the KO prompt body:

```markdown
## sidebar_checklist_advanced_ko (4~5 질문)

독자가 Advanced 내용을 실제로 이해했는지 **판단/적용 수준**에서 자가 점검하는 질문 4~5개.
Basic의 "이해했나요?" (comprehension)와 달리 **judgment / application / analysis** 수준이어야 함.

형식: `□ 질문` (각 질문 뒤에 `\n\n`)

**BAD (Basic 수준 — 이미 basic_checklist에 있는 comprehension 질문):**
□ X가 무엇인가요?
□ X와 Y는 어떻게 다른가요?

**GOOD (Advanced 수준 — judgment/application):**
□ 단일 GPU와 8-GPU 클러스터 중 어느 쪽이 본인 워크로드에 필요한지 판단하는 기준 3가지를 말할 수 있나요?
□ FP8을 도입했을 때 정확도 regression을 잡기 위한 검증 절차를 설명할 수 있나요?
□ 이 기법 대신 TPU나 Trainium을 고려해야 할 상황은 언제인가요?
□ MLPerf 벤치마크와 실제 production 성능이 차이 나는 이유 3가지를 꼽을 수 있나요?
```

Mirror for EN with `sidebar_checklist_advanced_en`.

Also add to the JSON schema example and Self-check block.

**Step 4: Update save endpoint to persist new fields**

Edit `frontend/src/pages/api/admin/handbook/save.ts`:
- Add `sidebar_checklist_advanced_ko, sidebar_checklist_advanced_en` to destructuring
- Include in the row object sent to Supabase

**Step 5: Update admin editor form**

Edit `frontend/src/pages/admin/handbook/edit/[slug].astro`:
- Add 2 textarea fields for `sidebar_checklist_advanced_ko/en` in the redesign fields section
- Load from term data, save via existing form flow

**Step 6: Update page data loader**

Edit `frontend/src/lib/pageData/handbookDetailPage.ts`:
- Add `sidebar_checklist_advanced_ko, sidebar_checklist_advanced_en` to the SELECT
- Expose as `sidebarChecklistAdvanced` in the computed return object

**Step 7: Update checklist component to accept `level` prop**

Edit `frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro`:

```astro
---
interface Props {
  checklistBasic: string;
  checklistAdvanced: string;
  level: 'basic' | 'advanced';
  locale: 'ko' | 'en';
}

const { checklistBasic, checklistAdvanced, level, locale } = Astro.props;

const content = level === 'advanced' ? checklistAdvanced : checklistBasic;
const heading = level === 'advanced'
  ? (locale === 'ko' ? '판단할 수 있나요?' : 'Can you decide?')
  : (locale === 'ko' ? '이해했나요?' : 'Check your understanding');

// Parse □ prefixed lines (existing logic)
// ...
---
```

**Step 8: Update handbook detail page to pass both fields + current level**

Edit `frontend/src/pages/ko/handbook/[slug].astro` + EN equivalent:
- Pass `checklistBasic={sidebarChecklist}` and `checklistAdvanced={sidebarChecklistAdvanced}` to `<HandbookUnderstandingChecklist>`
- Existing level switcher script should update the heading + content on toggle

Level switcher JS enhancement:
```js
const checklistEl = document.querySelector('.handbook-understanding-checklist');
if (checklistEl) {
  const basicContent = checklistEl.dataset.basic;
  const advancedContent = checklistEl.dataset.advanced;
  // swap content and heading based on level
}
```

This requires the component to emit `data-basic` and `data-advanced` on the container so client-side JS can swap.

**Step 9: Build + test**

Run:
```bash
cd backend && .venv/Scripts/ruff check . && .venv/Scripts/python -m pytest tests/test_handbook_advisor.py -v
cd frontend && npm run build
```

Expected: all pass.

### Task 11: Commit Phase 2

Two commits (separation of concerns):

**Commit A — tradeoff grid rehype plugin:**
```bash
git add frontend/src/lib/rehypeHandbookSectionCards.ts frontend/src/lib/markdown.ts frontend/src/styles/global.css backend/services/agents/prompts_advisor.py
git commit -m "feat(handbook): §4 tradeoffs 2-column grid via rehype plugin

HB-UX-04: Advanced §4 트레이드오프 section now renders as a 2-column
card grid when the prompt produces '### 적합한 경우' / '### 피해야 할 경우'
heading pair. Green left border for positive column, red for negative.

- New rehypeHandbookSectionCards plugin detects the heading pair
- Wired into handbookProcessor only (handbook advanced)
- Prompt §4 structure enforced for both KO and EN
- Mobile: collapses to 1-col stack (<640px)

Effect fully visible only after regen — existing 52 terms still use
old flowing prose layout. Will take effect during HB-MIGRATE-138 pilot batch."
```

**Commit B — advanced checklist field:**
```bash
git add backend/services/agents/prompts_advisor.py backend/models/advisor.py frontend/src/lib/pageData/handbookDetailPage.ts frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro frontend/src/pages/ko/handbook/[slug].astro frontend/src/pages/en/handbook/[slug].astro frontend/src/pages/api/admin/handbook/save.ts frontend/src/pages/admin/handbook/edit/[slug].astro
git commit -m "feat(handbook): Advanced sidebar checklist '판단할 수 있나요?'

HB-UX-05: Advanced level now shows a judgment/application-level self-check
in the sidebar, complementing Basic's '이해했나요?' comprehension checklist.

- New DB columns: sidebar_checklist_advanced_ko/en
- Pydantic field added to GenerateTermResult
- Advanced prompt generates 4~5 judgment-level questions
- HandbookUnderstandingChecklist component accepts level prop
- Level switcher JS swaps heading + content on Basic↔Advanced toggle
- Admin editor form supports editing the new fields

Bloom's taxonomy framing: Basic = comprehension, Advanced = application/
analysis/evaluation. Questions focus on 'when to pick X over Y', 'how to
validate', 'failure mode recognition' — not 'what is X'.

Existing 52 terms have empty advanced checklist until regen. Component
falls back to hiding if content empty."
```

---

## Verification checklist (end-to-end)

### Phase 1 (immediate effect on all 52 terms)

- [ ] `cd frontend && npm run build` passes
- [ ] `grep -n "collapsible" frontend/src/lib/rehypeCodeWindow.ts` shows new option
- [ ] `grep -n "collapsible" frontend/src/lib/markdown.ts` shows `{ collapsible: true }` in handbookProcessor only
- [ ] Visual check: `/ko/handbook/gpu/?level=advanced` shows code collapsed by default, clickable
- [ ] Visual check: `/ko/handbook/gpu/` (Basic) and `/ko/news/[any]` code blocks stay expanded
- [ ] Visual check: §5 pitfalls show yellow left border + tinted background
- [ ] Visual check: §6 dialogue quotes show accent-color border + italic

### Phase 2 (full effect requires regen)

- [ ] Supabase: `SELECT column_name FROM information_schema.columns WHERE column_name LIKE 'sidebar_checklist_advanced%'` returns 2 rows
- [ ] `cd backend && pytest tests/test_handbook_advisor.py` passes
- [ ] Admin editor shows 2 new textarea fields for advanced checklist
- [ ] Regen 1 pilot term (e.g., `gpu`) and verify:
  - `sidebar_checklist_advanced_ko` populated with 4-5 judgment questions
  - Advanced page sidebar shows "판단할 수 있나요?" heading
  - Level switcher swaps checklist content on toggle
  - §4 tradeoffs renders as 2-column grid (if prompt produces heading pair)

---

## Rollback plan

**Phase 1 rollback:**
```bash
git revert <commit-sha>  # revert the relevant Phase 1 commit(s)
cd frontend && npm run build
```
No DB or data impact.

**Phase 2 rollback:**
```bash
# Revert code commits
git revert <commit-sha>

# DB rollback (optional — columns can stay empty and unused)
# ALTER TABLE handbook_terms DROP COLUMN sidebar_checklist_advanced_ko, DROP COLUMN sidebar_checklist_advanced_en;
```
Pilot terms that had advanced checklist populated will lose it if columns are dropped. Safer: leave the columns, revert only code.

---

## Notes for executor

- **Do NOT touch Basic layout** — user confirmed Basic is satisfactory. All changes target Advanced rendering only.
- **No emojis** in any new UI element. Use CSS (colors, borders, typography) for visual signaling. This is a firm requirement, not a preference.
- **macOS window dots stay** — red/yellow/green circles are the existing design, reused as-is for collapsed state.
- **Scope collapsible to handbookProcessor only.** News and Basic keep expanded code blocks.
- **§5 CSS targets `h2[id*=프로덕션-함정]`** — if heading ID format differs from expected, inspect a built page first and adjust the selector. GitHub Flavored Markdown heading slugs lower-case Latin chars; Korean characters may pass through or be URL-encoded depending on the slugger.
- **Phase 2 timing:** tradeoff grid plugin works immediately for any term where prompt-enforced `### 적합한 경우` / `### 피해야 할 경우` headings exist. Existing terms (generated before prompt change) will NOT trigger the grid — they'll render as normal h3 + list. Full effect after HB-MIGRATE-138 regen.
- **Advanced checklist fallback:** if `sidebar_checklist_advanced_ko` is empty (existing 52 terms before regen), the checklist component should HIDE on Advanced level — don't show an empty box. Basic level continues to show the existing `sidebar_checklist_ko`.
