# Handbook Math Rendering Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix broken inline math (`$x_i$`, `$P(t_{1:n})$`) on handbook Advanced pages by converting math-like `$...$` patterns to `$$...$$` at render time, while leaving currency-like `$/시간`, `$10/hour` patterns untouched. No regen required.

**Architecture:** Add a small remark preprocessor that runs BEFORE `remark-math` in `handbookProcessor`. Walks text nodes, applies a regex to find `$...$` pairs, classifies content as math vs not-math via 4 simple rules (LaTeX commands, sub/superscripts, Greek letters, equation patterns), and rewrites math pairs to `$$...$$` so the existing `singleDollarTextMath: false` parser renders them as inline math via remark-math + KaTeX. Currency stays untouched and renders as literal text.

**Tech Stack:** TypeScript, unified/remark/rehype, mdast types, KaTeX (via existing rehype-katex), Playwright (visual verification)

---

## Context

### Why this change

**The bug**: User-reported (2026-04-11) that the LLM term page shows raw LaTeX text instead of rendered math:
```
$P(t_{1:n}) = P(t_1) \prod_{i=1}^{n-1} P(t_{i+1}\mid t_{1:i})$
$\mathrm{Attn}(Q,K,V)=\mathrm{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}+M\right)V$
```
These should render as KaTeX inline formulas but show as literal `$...$` text.

**Root cause** (DB verified):
- LLM published row: `body_advanced_ko` has 10 single-`$` characters, **0** `$$` block math
- embedding draft row: 16 `$` mixed with some `$$` (partial coverage)
- GPU draft row: 0 `$` (text-only section)

The LLM model produces inline math using natural LaTeX convention (`$x$` for inline, `$$x$$` for block), even though our prompt instructs `"use double-dollar signs: $$E=mc^2$$ (NOT single $)"`. Strict prompt enforcement isn't working — the LLM consistently mixes both forms.

**Why our renderer breaks it**: Commit `6b5f1f5` (HB-UX-01 series) set `remarkMath({ singleDollarTextMath: false })` in `handbookProcessor` to fix GPU's `$/시간` currency-vs-math conflict. Side effect: legitimate inline math also gets treated as literal text.

**Trade-off resolved**: Currency `$10`, `$/시간` and math `$x_i$`, `$\frac{a}{b}$` use the same delimiter character but have totally different content shapes. A content-classifier preprocessor can route them differently:
- math content → rewrite `$X$` to `$$X$$` (renders as inline math via remark-math)
- non-math content (currency) → leave alone (renders as literal text since `singleDollarTextMath: false`)

This is a **render-time fix**: no DB migration, no regen, no prompt change. The fix takes effect on all 52 published terms after deploy.

### Why not other approaches

- **Re-enable `singleDollarTextMath: true`**: re-introduces the GPU `$/시간` bug
- **Update prompt + regen all 138 terms**: expensive, doesn't fix existing content immediately, prompt enforcement already failed for the same instruction
- **One-time SQL migration to convert `$` to `$$`**: destructive, requires careful regex on multiple terms, hard to roll back, risks false positives on currency
- **Embed a real LaTeX parser**: massive overkill for ~5 pattern checks

### Intended outcome

After deploy:
- `/ko/handbook/llm/?level=advanced` §2 핵심 수식 — all formulas render as proper inline KaTeX
- `/ko/handbook/embedding/?level=advanced` §2 — same fix for any single-$ math
- `/ko/handbook/gpu/?level=advanced` — unchanged (no math to break in the first place)
- News articles — unchanged behavior (default processor doesn't get the new plugin, OR optionally also gets it for consistency)

### What we are NOT changing

- `singleDollarTextMath` flag — stays `false` in all 3 processors
- DB content — no migration
- Prompts — no change to prompts_advisor.py
- KaTeX config — unchanged
- News currency rendering — unchanged

---

## Critical files

| # | File | Change type |
|---|---|---|
| 1 | [frontend/src/lib/remarkConvertInlineMathDollars.ts](frontend/src/lib/remarkConvertInlineMathDollars.ts) (NEW) | New remark plugin (~50 lines) |
| 2 | [frontend/src/lib/markdown.ts](frontend/src/lib/markdown.ts) | Wire plugin into handbookProcessor (1 import + 1 `.use()` line) |

---

## Existing code reused

- [unified/remark visit pattern](frontend/src/lib/rehypeHandbookSectionMarkers.ts) — use the same `visit(tree, 'text', ...)` style for walking the AST. The plugin is mdast-level (text nodes BEFORE remark-rehype runs).
- [mdast `Text` and `Root` types](frontend/src/lib/rehypeHandbookSectionMarkers.ts:1) — already imported elsewhere via the `mdast` package (or via `unist`)
- `unist-util-visit` — already in dependencies (used by `rehypeStripDel`, `rehypeHandbookSectionMarkers`, `rehypeCodeWindow`)
- handbookProcessor in [markdown.ts:138-150](frontend/src/lib/markdown.ts#L138-L150) — already established pipeline that we wire one new step into

---

## Test strategy

**No formal test suite.** This is a frontend rendering plugin where the verification path is:
1. Build verification (TypeScript compilation + Astro build)
2. Visual verification via Playwright (live page content checks before/after)
3. Optional: an inline self-test in dev (run the plugin on sample input, log output, remove before commit)

The plan uses **manual test** in Step 1 of Task 1 — run the regex/classifier function against known inputs (LLM formulas, GPU currency, embedding mixed) and confirm classification. This is faster than setting up Vitest just for one plugin.

If we later add a `frontend/test/` directory with Vitest, this plugin should get a test file then. For now, manual verification is sufficient given the small scope.

---

## Task 1: Create the math classifier function

**Files:**
- Create: `frontend/src/lib/remarkConvertInlineMathDollars.ts`

**Step 1: Create the file with classifier function only (no plugin yet)**

```typescript
import type { Root, Text } from 'mdast';
import { visit } from 'unist-util-visit';

/**
 * Decide whether the content inside a $...$ pair looks like LaTeX math.
 *
 * True positives we want to catch (math):
 *   x_i, t^n, P(t_{1:n}), \frac{a}{b}, \sum_{i=1}^{n}, \mathrm{Attn},
 *   τ, θ, π, E=mc^2
 *
 * True negatives we want to leave alone (currency, plain text):
 *   $10, $/시간, $/hour, $50/GB
 *
 * Heuristic order matters: cheaper checks first.
 */
export function looksLikeMath(content: string): boolean {
  // 1. LaTeX command: backslash followed by letters (\frac, \sum, \mathrm, \theta, \mid, ...)
  if (/\\[a-zA-Z]+/.test(content)) return true;

  // 2. Subscript/superscript: _ or ^ followed by a letter, digit, or opening brace
  //    Matches: x_i, t^n, P^{...}, a_1, c^2
  //    Does NOT match: a_b_c without context, just "_" alone
  if (/[_^][a-zA-Z0-9{]/.test(content)) return true;

  // 3. Greek letters in Unicode (commonly used in LLM/ML formulas)
  if (/[α-ωΑ-Ω]/.test(content)) return true;

  // 4. Equation pattern: equals sign with letters, short content (avoids matching long prose)
  if (/=/.test(content) && /[a-zA-Z]/.test(content) && content.length < 80) return true;

  return false;
}
```

**Step 2: Manually test the classifier**

Add a temporary `__test__` block at the bottom of the file (will remove after verification):

```typescript
// __TEMPORARY MANUAL TEST — remove before commit__
if (import.meta.url === `file://${process.argv[1]}`) {
  const cases: Array<[string, boolean]> = [
    // True positives (math)
    ['P(t_{1:n}) = P(t_1) \\prod_{i=1}^{n-1} P(t_{i+1}\\mid t_{1:i})', true],
    ['\\mathrm{Attn}(Q,K,V)=\\mathrm{softmax}', true],
    ['d_k', true],
    ['x_i', true],
    ['E=mc^2', true],
    ['\\frac{a}{b}', true],
    ['\\sum_{i=1}^{n}', true],
    ['τ=0.7', true],
    ['θ_t', true],
    // True negatives (not math)
    ['/시간', false],
    ['/hour', false],
    ['10/hour', false],
    ['50', false],
    ['plain text here', false],
  ];
  let pass = 0, fail = 0;
  for (const [input, expected] of cases) {
    const got = looksLikeMath(input);
    const ok = got === expected;
    if (ok) pass++; else fail++;
    console.log(`${ok ? 'PASS' : 'FAIL'}: looksLikeMath(${JSON.stringify(input)}) = ${got} (expected ${expected})`);
  }
  console.log(`\n${pass}/${pass + fail} passed`);
}
```

Run:
```bash
cd c:/Users/amy/Desktop/0to1log/frontend && npx tsx src/lib/remarkConvertInlineMathDollars.ts
```

Expected:
```
PASS: looksLikeMath("P(t_{1:n}) = P(t_1) ...") = true (expected true)
PASS: looksLikeMath("\\mathrm{Attn}...") = true (expected true)
... (all 14 PASS)
14/14 passed
```

If any FAIL, fix the heuristic and re-run before proceeding.

**Step 3: Remove the manual test block**

Delete the `if (import.meta.url === ...)` block. The file should contain only the imports and `looksLikeMath` function (no plugin yet — that's Task 2).

**Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit src/lib/remarkConvertInlineMathDollars.ts 2>&1 | head -10`

Expected: no errors. If type errors on `Root`/`Text` imports, switch to `import type { Root, Text } from 'mdast'` (already in plan).

**Step 5: No commit yet** — Task 2 finishes the plugin. Hold the file for now.

---

## Task 2: Add the remark plugin function

**Files:**
- Modify: `frontend/src/lib/remarkConvertInlineMathDollars.ts` (add plugin function)

**Step 1: Append the plugin export to the file**

Add below `looksLikeMath`:

```typescript
/**
 * Match $...$ pairs on a single line. Greedy lazy: shortest match.
 *
 * Excludes:
 * - Cross-line content (no \n inside)
 * - Empty content ($$  is handled by remark-math directly)
 * - Already-double-dollar ($$X$$  pre-exists; the regex only matches odd-count pairs)
 */
const INLINE_DOLLAR_RE = /\$([^$\n]+?)\$/g;

/**
 * Remark plugin: convert math-looking $X$ pairs to $$X$$ inside text nodes.
 *
 * Runs BEFORE remark-math. The downstream parser is configured with
 * singleDollarTextMath: false, so:
 * - $$X$$ pairs we produce → parsed as math (inline if mid-paragraph)
 * - $X$ pairs we leave alone → stay as literal text
 *
 * Currency-like patterns ($10, $/시간) are left alone because they don't
 * match looksLikeMath() heuristics.
 */
export default function remarkConvertInlineMathDollars() {
  return (tree: Root) => {
    visit(tree, 'text', (node: Text) => {
      if (!node.value.includes('$')) return;

      let changed = false;
      const newValue = node.value.replace(INLINE_DOLLAR_RE, (match, inner) => {
        // Skip if inner is empty after trimming (defensive)
        if (!inner.trim()) return match;

        if (looksLikeMath(inner)) {
          changed = true;
          return `$$${inner}$$`;
        }
        return match;
      });

      if (changed) {
        node.value = newValue;
      }
    });
  };
}
```

The full file should now be:
- Imports
- `looksLikeMath` function (from Task 1)
- `INLINE_DOLLAR_RE` constant
- Default export `remarkConvertInlineMathDollars`

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit src/lib/remarkConvertInlineMathDollars.ts 2>&1 | head -10`

Expected: no errors.

**Step 3: No commit yet** — wait until plugin is wired and build passes.

---

## Task 3: Wire the plugin into handbookProcessor

**Files:**
- Modify: `frontend/src/lib/markdown.ts` (add 1 import + 1 `.use()` call)

**Step 1: Add the import**

Find line 14 (existing imports of plugins):
```typescript
import rehypeHandbookTerms, { type TermsMap } from './rehypeHandbookTerms';
import rehypeCodeWindow from './rehypeCodeWindow';
import rehypeHandbookSectionMarkers from './rehypeHandbookSectionMarkers';
```

Add below it:
```typescript
import remarkConvertInlineMathDollars from './remarkConvertInlineMathDollars';
```

**Step 2: Wire into handbookProcessor**

Find the handbookProcessor block around lines 138-152. Current state:
```typescript
const handbookProcessor = unified()
  .use(remarkParse)
  .use(remarkGfm, { singleTilde: false })
  .use(remarkMath, { singleDollarTextMath: false })
  .use(remarkRehype, { allowDangerousHtml: true })
  ...
```

Insert `remarkConvertInlineMathDollars` BETWEEN `remarkGfm` and `remarkMath`:
```typescript
const handbookProcessor = unified()
  .use(remarkParse)
  .use(remarkGfm, { singleTilde: false })
  .use(remarkConvertInlineMathDollars)
  .use(remarkMath, { singleDollarTextMath: false })
  .use(remarkRehype, { allowDangerousHtml: true })
  ...
```

**Order matters**: must run AFTER `remarkParse` (so AST exists) and BEFORE `remarkMath` (so the rewritten `$$X$$` gets parsed as math nodes by remark-math).

**Step 3: Decide on terms processor**

The terms processor (used for handbook Basic with auto-linked terms, around line 170-188) has the same `singleDollarTextMath: false` config. Basic body rarely has math, but for consistency add the same plugin to that processor too.

In the same pattern, add `.use(remarkConvertInlineMathDollars)` after `.use(remarkGfm, { singleTilde: false })` in the termsProcessor block. This ensures Basic body math (rare but possible) also renders correctly.

**Step 4: Skip default processor (news)**

Do NOT add the plugin to the default `processor` (line 119-130). News articles don't have LaTeX math, and adding the plugin there is unnecessary overhead. If a future news article needs math, revisit then.

**Step 5: Build verification**

Run: `cd frontend && npm run build 2>&1 | tail -15`

Expected: `Server built in NN.NNs` and `Complete!` with 0 errors. The pre-existing `Astro.request.headers` warnings on prerendered pages are unrelated and OK.

If build fails:
- TypeScript error in plugin → check `Root`/`Text` import path (try `'unist'` if `'mdast'` fails)
- Module not found → verify the plugin file exists and the import path is correct

**Step 6: No commit yet** — visual verification first.

---

## Task 4: Visual verification with Playwright

**Files:**
- None (read-only verification)

**Step 1: Local dev server**

Run: `cd frontend && npm run dev` (in a separate terminal, or use existing dev server)

Wait for `Local: http://localhost:4321/`.

**Step 2: Open LLM Advanced page**

Navigate to: `http://localhost:4321/ko/handbook/llm/?level=advanced`

(Or use Playwright MCP tools if available.)

**Step 3: Visual checks for §2 핵심 수식·아키텍처·도표**

In the rendered page:
- [ ] Chain rule formula `P(t_{1:n}) = P(t_1) \prod...` renders as KaTeX (visible mathematical typesetting, not raw LaTeX text)
- [ ] Attention formula `\mathrm{Attn}(Q,K,V)=...` renders as KaTeX
- [ ] Subscripts `t_{1:n}`, `d_k` render as proper subscripts (small lowered text)
- [ ] Superscripts `K^\top` render as superscripts
- [ ] Greek letters τ, θ render correctly
- [ ] No raw `$` characters visible around formulas

**Step 4: Visual checks for §5 프로덕션 함정 (regression check)**

Scroll to §5:
- [ ] Pitfalls list still shows yellow callouts (commit `7571d36` styling unchanged)
- [ ] Bold "실수:" / "해결:" labels present
- [ ] No regression — looks identical to before this fix

**Step 5: Visual check for GPU page (no regression)**

Navigate to: `http://localhost:4321/ko/handbook/gpu/?level=advanced`

- [ ] No broken `$` characters anywhere
- [ ] §2 section (which is text + bullets, no math) renders normally
- [ ] If GPU has any cost notation `$10/hour`, `$/시간` style — must render as literal text, not math

**Step 6: Visual check for embedding page**

Navigate to: `http://localhost:4321/ko/handbook/embedding/?level=advanced`

- [ ] §2 formulas render as KaTeX (16 `$` chars in DB content should now all show as math or literal as appropriate)
- [ ] Existing `$$` block math (already at positions 1019, 2495 in DB) still renders correctly — no double-conversion

**Step 7: Mobile check**

Resize browser to 375px wide:
- [ ] LLM §2 formulas still render (KaTeX inline math wraps within line width)
- [ ] No horizontal scroll caused by long formulas

**Step 8: If any check fails**

- Math not rendering → check browser DevTools console for KaTeX errors. May indicate the plugin runs in wrong order or the rewrite produces malformed `$$X$$`.
- GPU currency now rendering as math → `looksLikeMath` heuristic was too greedy. Check the specific content that triggered false positive and tighten the rule.
- Pitfalls callout broken → unrelated regression, investigate separately.

---

## Task 5: Commit

**Files:**
- Stage: `frontend/src/lib/remarkConvertInlineMathDollars.ts`
- Stage: `frontend/src/lib/markdown.ts`

**Step 1: Verify build is still passing**

Run: `cd frontend && npm run build 2>&1 | tail -3`

Expected: `Complete!`

**Step 2: Commit**

```bash
cd c:/Users/amy/Desktop/0to1log
git add frontend/src/lib/remarkConvertInlineMathDollars.ts frontend/src/lib/markdown.ts
git commit -m "$(cat <<'EOF'
fix(handbook): smart math/currency $ classifier — render inline math without breaking currency

LLM term §2 핵심 수식 was rendering raw LaTeX text like
'$P(t_{1:n}) = P(t_1) \\prod_{i=1}^{n-1} ...$' because commit 6b5f1f5
disabled singleDollarTextMath in handbookProcessor (to fix GPU currency
$/시간 conflict).

Fix: new remark preprocessor remarkConvertInlineMathDollars runs BEFORE
remark-math. It walks text nodes, finds \$X\$ pairs, classifies content
via 4 heuristics (LaTeX commands, sub/superscripts, Greek letters, short
equations), and rewrites math to \$\$X\$\$ which the existing
singleDollarTextMath:false parser handles as inline math via KaTeX.

Currency stays untouched ($10, $/시간 don't match the math heuristics).

Wired into handbookProcessor + termsProcessor (handbook Basic). Default
news processor unchanged — news doesn't have LaTeX math.

Effect: immediate on all 52 published terms after deploy. No regen, no
DB migration, no prompt change. Reverts trivially.

Verified visually with Playwright on /ko/handbook/llm/?level=advanced —
all 5 formulas in §2 now render as KaTeX inline math.
EOF
)"
```

**Step 3: Verify commit**

Run: `git log -1 --stat`

Expected:
- 1 file created: `remarkConvertInlineMathDollars.ts`
- 1 file modified: `markdown.ts` (a few lines added)
- ~50-60 insertions total

---

## Task 6: Sprint update

**Files:**
- Modify: `vault/09-Implementation/plans/ACTIVE_SPRINT.md` (add HB-UX-07 done entry)

**Step 1: Add HB-UX-07 to sprint table**

Open `vault/09-Implementation/plans/ACTIVE_SPRINT.md`. Find the HB-UX section (the table that has HB-UX-01 through HB-UX-06).

Add one new row:
```markdown
| HB-UX-07 | done | Math/currency $ classifier preprocessor — fix LLM/embedding inline math rendering broken by HB-UX-01 series side effect | P0 | (this commit's SHA) |
```

Update the retrospective notes section to mention:
> 2026-04-11 LLM 페이지 시각 검수에서 HB-UX-01 시리즈의 두 번째 silent failure 발견 — singleDollarTextMath: false가 GPU 통화는 fix했지만 LLM 수식을 깨뜨림. HB-UX-07 preprocessor가 둘 다 만족시키는 분기 로직 도입.

**Step 2: Commit sprint update**

```bash
git add vault/09-Implementation/plans/ACTIVE_SPRINT.md
git commit -m "docs(sprint): HB-UX-07 done — math/currency $ classifier preprocessor"
```

---

## Verification (end-to-end)

After all tasks:

1. **Build:** `cd frontend && npm run build` — 0 errors
2. **Live verification (post-deploy):** open `https://0to1log.com/ko/handbook/llm/?level=advanced` and confirm §2 formulas render as KaTeX
3. **Regression check:** open `https://0to1log.com/ko/handbook/gpu/?level=advanced` — no math, no broken `$` characters
4. **Cross-locale:** open `/en/handbook/llm/?level=advanced` — same fix applies (handbookProcessor handles both locales)
5. **Cache:** Vercel deploy invalidates the in-memory `htmlCache` automatically (new server instance)

---

## Rollback plan

If the preprocessor causes a regression:

1. Revert the commit: `git revert <commit-sha>`
2. Rebuild and redeploy: `cd frontend && npm run build`

The change is contained to 1 new file + 1 modified file. Reverting restores the previous behavior (broken inline math, working currency).

If a specific term has issues post-fix but most are fine, that term likely has unusual content (e.g., regex matched something it shouldn't). Tighten `looksLikeMath` heuristic and re-deploy.

---

## Notes for executor

- **Order of plugin matters**: `remarkConvertInlineMathDollars` MUST run after `remarkParse` and `remarkGfm` (so the AST is built and tables/strikethrough are processed) and BEFORE `remarkMath` (so rewritten `$$X$$` gets recognized as math nodes).
- **Why preprocessor not postprocessor**: rewriting at mdast text-node level is safer than rehype HTML manipulation. The downstream remark-math + rehype-katex pipeline is unchanged.
- **Why not match `$$X$$` already**: the regex `/\$([^$\n]+?)\$/g` won't match `$$X$$` properly (it would match the inner `$X$` but then leave the outer `$`s alone). Existing `$$X$$` content is left alone because remark-math handles it directly. Only odd-count single-`$` pairs are touched.
- **`unist-util-visit` versioning**: the project already uses this for other plugins. Same import style works.
- **`mdast` types vs `unist`**: prefer `import type { Root, Text } from 'mdast'` for clarity. If TypeScript complains, fall back to typing as `any`.
- **Manual test in Task 1 Step 2**: this is intentionally inline because the project doesn't have a Vitest setup. Run it once to gain confidence in the heuristic, then remove the test block. Don't commit the test code.
- **Don't touch prompts**: this fix avoids any prompt change. The LLM continues to mix `$` and `$$` naturally; the renderer handles both.
- **Don't migrate DB content**: render-time fix means existing 52 published terms benefit immediately without touching stored content.
- **GPU is the canary**: GPU's `$/시간` content is the regression risk. If GPU still renders correctly after the fix, the heuristic is safe.

---

## Out of scope

- Prompt changes (LLM continues to use natural LaTeX `$` for inline)
- DB content migration
- Vitest setup for plugin testing (manual test for now)
- News article math support (no current need)
- Block math `$$X$$` standalone (already works via remark-math, unchanged)
