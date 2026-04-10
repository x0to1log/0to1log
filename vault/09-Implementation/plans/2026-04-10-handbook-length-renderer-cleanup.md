# Handbook Length Target Cleanup + Renderer $ Fix

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove unjustified per-section character length targets from handbook prompts (follow news_pipeline.py pattern) and fix the markdown renderer so that single `$` characters (currency, variables) don't conflict with math mode in handbook Advanced body.

**Architecture:** Two independent cleanup tracks merged into one plan.
1. **Renderer fix** — single-line config change in `frontend/src/lib/markdown.ts` (handbook Advanced processor) to disable inline `$...$` math parsing. News processor already has this fix with comment `"avoid $2 currency conflicts"`. Only handbook Advanced has the stale setting.
2. **Prompt length target removal** — sweep `backend/services/agents/prompts_advisor.py` removing 10+ per-section char targets that have no UI justification. Keep only the targets tied to real UI constraints: `definition` (Expert popup) and `hero_news_context` (hero card width). Align with established project pattern: `models/advisor.py:206-208` comment explicitly states "content shape is guided by the prompt, not enforced by Pydantic. Matches the news_pipeline.py pattern (zero length constraints anywhere)."

**Tech Stack:** Python (Pydantic + prompts), TypeScript (Astro + remark/rehype-katex), Supabase

---

## Context

### Why this change

During the HB-QM pilot (llm, gpu, embedding regen, commit `1ac2a4a`), a format audit surfaced two issues:

**Issue 1: GPU Advanced §2 "핵심 수식·아키텍처·도표" contains currency `$` that conflicts with markdown math.**

The LLM wrote:
```
- 단위 비용: $/시간, $/토큰(추론), $$/학습 스텝
- ... rps/$$ 편차가 커서 ...
```

The handbook Advanced markdown processor has `singleDollarTextMath: true`, so markdown interprets `$/시간, $/토큰` as inline math `/시간, ` — rendering breaks. This is a systemic risk for any cost/pricing content (inference-cost, trainium, bedrock, etc.), not a one-off GPU bug.

Investigation found the news processor already has `singleDollarTextMath: false` with comment `"News uses the default processor (singleDollarTextMath: false) to avoid $2 currency conflicts"`. The fix was never propagated to the handbook Advanced processor. The prompt already instructs `"use double-dollar signs: $$E = mc^2$$ (NOT single $)"`, so enabling inline `$...$` math serves no purpose and contradicts the prompt.

**Issue 2: EN §1 "Plain Explanation" consistently 30-35% above target (1230~1334 vs 700~1000 chars).**

Audit across 3 pilot terms showed KO §1 perfectly within 600~800 target (641~744 chars) but EN §1 uniformly overshooting. Investigation revealed the handbook prompt file has 10+ per-section character targets (`body_basic` 2800~4200, `basic_*_1_plain` 600~1000, `basic_*_2_example` 600~900, `scenario 150~200`, `body_advanced` 7000~10000, `adv_*_1_mechanism` 1000~1600, `adv_*_4_tradeoffs` 900~1400, `adv_*_5_pitfalls` 800~1300, etc.).

These are all **soft targets** inherited from old iterations, with **no UI constraint backing them**. News pipeline prompts have zero per-section char targets and produce quality content. The handbook `models/advisor.py` comment explicitly declares the same philosophy but the prompts never got cleaned up. English naturally uses 1.5-2x the char count of Korean for equivalent information, so a tight target that works for KO is wrong for EN by design.

### Intended outcome

- `$` characters in handbook Advanced body render as literal text (no more currency/math conflict) — immediate effect on all 138 existing terms, no regen needed
- LLM can produce naturally-sized sections without artificial char ceilings
- Prompt file is leaner and easier to maintain (removal of ~20 soft target phrases)
- Pilot 3 regen shows the new behavior preserves content quality

### What we are NOT changing

- `definition_ko/en` 200~400 chars — JUSTIFIED by Expert popup UI (`.handbook-popup-content` has `max-height: 260px`)
- `hero_news_context_ko/en` per-line 60~70 chars — JUSTIFIED by hero card per-line width
- Pydantic `min_length=2000` (basic) and `3000` (advanced) — fail-fast signal, no change
- `definition` `min_length=180` — already set for Expert popup use case, keep

---

## Critical files

| # | File | Change type |
|---|---|---|
| 1 | [frontend/src/lib/markdown.ts](frontend/src/lib/markdown.ts) | 1-line config flip |
| 2 | [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) | Remove ~20 char target phrases + length-related self-checks |
| 3 | [c:/tmp/regen_handbook.py](c:/tmp/regen_handbook.py) | Reuse existing pilot script (no change) |
| 4 | Supabase `handbook_terms` rows for llm/gpu/embedding | Re-apply regen as draft |

---

## Existing utilities to reuse

- [c:/tmp/regen_handbook.py](c:/tmp/regen_handbook.py) — parallel regen script, already supports `llm`, `gpu`, `embedding` keys
- [c:/tmp/apply_regen_to_db.py](c:/tmp/apply_regen_to_db.py) — reads `regen_<slug>_result.json` and updates DB row with `status='draft'`
- [c:/tmp/audit_format.py](c:/tmp/audit_format.py) + [c:/tmp/audit_format_advanced.py](c:/tmp/audit_format_advanced.py) — format auditors for regen results
- [c:/tmp/regen_backup/](c:/tmp/regen_backup/) — backup of original DB rows from earlier pilot (restore target if needed)

---

## Task 1: Fix renderer singleDollarTextMath for handbook Advanced

**Files:**
- Modify: `frontend/src/lib/markdown.ts` (handbookProcessor, around line 141)

**Step 1: Locate the handbookProcessor remarkMath config**

Run: `grep -n "handbookProcessor\|singleDollarTextMath" frontend/src/lib/markdown.ts`

Expected output includes a line like `remarkMath({ singleDollarTextMath: true })` inside the handbookProcessor definition.

**Step 2: Flip the flag**

Edit: change `{ singleDollarTextMath: true }` → `{ singleDollarTextMath: false }` in the handbookProcessor block only. Do NOT touch the default processor or terms processor (both already `false`).

**Step 3: Verify build passes**

Run: `cd frontend && npm run build`

Expected: build completes with 0 errors (warnings about prerendering are OK — pre-existing).

**Step 4: Commit**

```bash
git add frontend/src/lib/markdown.ts
git commit -m "fix(handbook): disable singleDollarTextMath for Advanced processor

Handbook Advanced processor was the only processor with inline \$...\$
math enabled, causing currency symbols (\$/hour, \$10/GB) to trigger
math mode and break rendering. News processor already has this fix
with comment 'avoid \$2 currency conflicts' — propagate to handbook.

Prompt already instructs 'use double-dollar signs: \$\$E=mc^2\$\$
(NOT single \$)', so disabling inline math aligns with prompt intent.
Block math (\$\$...\$\$) still works for Advanced §2 formulas.

Effect: immediate on all 138 existing handbook terms, no regen needed.
GPU term's '\$/시간, \$/토큰' in body_advanced_ko now renders as literal."
```

---

## Task 2: Remove length targets from KO definition + basic sections

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py` (KO block around lines 608-900)

**Note:** Do NOT touch `definition_ko` length targets — those are justified by Expert popup UI.

**Step 1: Locate KO length targets**

Run:
```bash
grep -n "chars\|문자" backend/services/agents/prompts_advisor.py | head -40
```

Record line numbers of all `target X~Y chars` / `X~Y 문자` phrases in the KO block (roughly lines 608-900). Exclude `definition_ko` (lines 608-640) and `hero_news_context_ko` (around line 640-660 if present).

**Step 2: Remove KO body_basic overall target**

Find the heading:
```
## body_basic — Basic (target 2800~4200 chars, 7 sections)
```

Change to:
```
## body_basic — Basic (7 sections)
```

**Step 3: Remove basic_ko_1_plain char target**

Find:
```
- **basic_ko_1_plain** (쉽게 이해하기, target 600~800 chars):
```

Change to:
```
- **basic_ko_1_plain** (쉽게 이해하기):
```

Inside the section body, also remove any `X~Y 문자` phrases from paragraph instructions. Keep structural guidance like `"문제 → 해결 → 메커니즘 흐름"` and qualitative hints like `"간결하고 밀도 있게"`.

**Step 4: Remove basic_ko_2_example char targets**

Find:
```
- **basic_ko_2_example** (비유와 예시, target 600~900 chars, EXACTLY 3 scenarios):
```

Change to:
```
- **basic_ko_2_example** (비유와 예시, EXACTLY 3 scenarios):
```

Remove any `(each scenario 150~200 chars)` or similar char count hints inside the body. Keep the "EXACTLY 3 scenarios" count constraint — that's structural, not a char target.

**Step 5: Remove other basic_ko section char targets**

For `basic_ko_4_impact`, `basic_ko_5_caution`, `basic_ko_6_comm`, `basic_ko_7_related` — scan each section's instruction block and remove any `target X~Y chars` or `X~Y 문자` phrases. Keep count constraints like `4~5 bullets`, `EXACTLY 3`, etc.

**Step 6: Update KO JSON schema example**

Find the JSON schema example block that contains:
```
"basic_ko_1_plain": "문제 → 해결 → 메커니즘 600~800자 본문",
```

Change the value string to remove the `600~800자` phrase. Keep the structural hint:
```
"basic_ko_1_plain": "문제 → 해결 → 메커니즘 본문",
```

Repeat for other schema example lines that contain char counts (if any).

**Step 7: Remove KO self-check length items**

Find the KO Self-Check block (around line 850). Remove any `✓ basic_ko_X_... is X~Y chars` items. Keep `✓ basic_ko_X_... has EXACTLY N bullets` items.

**Step 8: Lint check**

Run: `cd backend && .venv/Scripts/ruff check services/agents/prompts_advisor.py`

Expected: `All checks passed!`

---

## Task 3: Remove length targets from EN definition + basic sections

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py` (EN block around lines 970-1280)

**Note:** Do NOT touch `definition_en` length targets.

**Step 1: Mirror Task 2 on EN block**

Apply the same pattern as Task 2 but in the EN section:
- Remove `## body_basic — Basic (target 2800~4200 chars, 7 sections)` → `(7 sections)` (check if already done by Task 2 — EN might share this heading or have its own)
- `basic_en_1_plain` (Plain Explanation, target 700~1000 chars) → `(Plain Explanation)`
- `basic_en_2_example` (Examples & Analogies, target 600~900 chars, EXACTLY 3 scenarios) → `(Examples & Analogies, EXACTLY 3 scenarios)`
- Remove `150~200 chars` or similar from scenario inner instructions
- Remove char targets from basic_en_4 through basic_en_7
- Update EN JSON schema example: `"basic_en_1_plain": "Problem → solution → mechanism, 700~1000 chars"` → `"Problem → solution → mechanism"`
- Remove EN self-check length items

**Step 2: Lint check**

Run: `cd backend && .venv/Scripts/ruff check services/agents/prompts_advisor.py`

Expected: `All checks passed!`

---

## Task 4: Remove length targets from KO + EN advanced sections

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py` (advanced block around lines 1522-1700)

**Step 1: Locate Advanced section heading**

Find:
```
## body_advanced — Advanced (target 7,000~10,000 chars, 7 sections)
```

Change to:
```
## body_advanced — Advanced (7 sections)
```

**Step 2: Remove adv section char targets (both languages)**

Locate each of these and remove the `target X~Y chars` phrase:

- `adv_ko_1_mechanism` / `adv_en_1_mechanism` (around 1000~1600)
- `adv_ko_4_tradeoffs` / `adv_en_4_tradeoffs` (around 900~1400)
- `adv_ko_5_pitfalls` / `adv_en_5_pitfalls` (around 800~1300)
- Any other adv_*_N_* sections with char targets

Search command:
```bash
grep -n "adv_.*target.*chars" backend/services/agents/prompts_advisor.py
```

Handle each match. Keep structural hints (section purpose, bullet counts) but drop char counts.

**Step 3: Remove Advanced self-check length items**

Find advanced self-check block (search for `adv_.*chars`):
```bash
grep -n "adv_.*chars" backend/services/agents/prompts_advisor.py
```

Remove items like `✓ adv_en_1_mechanism is 1000~1600 chars with ...` — keep only the structural half of the sentence: `✓ adv_en_1_mechanism has formal definition + flow + complexity/algorithm steps`.

**Step 4: Lint check**

Run: `cd backend && .venv/Scripts/ruff check services/agents/prompts_advisor.py`

Expected: `All checks passed!`

---

## Task 5: Final sweep — verify no orphaned length targets

**Step 1: Grep for remaining targets**

Run:
```bash
grep -n "target.*chars\|target.*문자\|\d\{3\}~\d\{4\} chars" backend/services/agents/prompts_advisor.py
```

Expected output: only `definition_ko`, `definition_en`, and maybe `hero_news_context_*` (if expressed in chars). No `basic_*` or `adv_*` section matches.

**Step 2: Grep for self-check length items**

Run:
```bash
grep -n "is at least\|is [0-9]\+~[0-9]\+ chars\|[0-9]\+ chars with" backend/services/agents/prompts_advisor.py
```

Expected: only `definition_ko`/`definition_en` (`at least 180 chars`) items remain.

**Step 3: Verify tests still pass**

Run:
```bash
cd backend && .venv/Scripts/python -m pytest tests/test_handbook_advisor.py tests/test_basic_en_sections.py tests/test_advanced_sections.py -v --tb=short
```

Expected: all tests pass. `test_related_terms_returns_db_existence` is pre-existing failure (network call blocked in tests) — unrelated to this task.

If any test fails due to length assumption, investigate and update the fixture rather than re-adding the length target.

**Step 4: Commit prompt cleanup**

```bash
git add backend/services/agents/prompts_advisor.py
git commit -m "refactor(handbook): remove per-section char length targets

Handbook prompts had 10+ per-section char targets (basic \u00a71-7, adv \u00a71-7,
overall body_basic 2800~4200, body_advanced 7000~10000) with no UI
justification. News pipeline prompts have zero per-section targets
and produce quality content.

Audit of pilot 3 (llm/gpu/embedding) showed KO \u00a71 perfectly within
target (641~744) but EN \u00a71 uniformly overshooting (1230~1334 vs
700~1000) \u2014 English naturally needs 1.5~2x the char count of Korean
for equivalent information. Tight target is wrong by design.

Kept targets (UI-justified):
- definition_ko/en 200~400 chars \u2014 Expert popup max-height 260px
- hero_news_context_ko/en per-line 60~70 \u2014 hero card width

Removed (arbitrary, inherited):
- body_basic 2800~4200
- basic_*_1_plain 600~800/700~1000
- basic_*_2_example 600~900, scenario 150~200
- body_advanced 7000~10000
- adv_*_1_mechanism 1000~1600
- adv_*_4_tradeoffs 900~1400
- adv_*_5_pitfalls 800~1300
- Self-check length items for removed targets

Pydantic min_length (2000 basic, 3000 advanced) unchanged \u2014 fail-fast
signal, no max. Aligns with models/advisor.py:206-208 policy comment."
```

---

## Task 6: Re-regen 3 pilot terms with cleaned prompt

**Files:**
- Use: `c:/tmp/regen_handbook.py`

**Step 1: Run 3 regens in parallel (background)**

Open 3 background terminals or use the background Bash pattern. Each command:

```bash
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py llm > c:/tmp/regen_llm_log.txt 2>&1
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py gpu > c:/tmp/regen_gpu_log.txt 2>&1
cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/regen_handbook.py embedding > c:/tmp/regen_embedding_log.txt 2>&1
```

Each takes 30-90 seconds. Wait for all 3 to complete.

**Step 2: Verify result files exist**

Run: `ls -la c:/tmp/regen_llm_result.json c:/tmp/regen_gpu_result.json c:/tmp/regen_embedding_result.json`

Expected: all 3 files with recent timestamps, ~50KB each.

**Step 3: Spot-check that lengths are natural (not forced)**

Run:
```bash
cd backend && .venv/Scripts/python -c "
import json
for slug in ['llm', 'gpu', 'embedding']:
    with open(f'c:/tmp/regen_{slug}_result.json', 'r', encoding='utf-8') as f:
        d = json.load(f)
    print(f'{slug}:')
    print(f'  definition_ko: {len(d[\"definition_ko\"])}')
    print(f'  definition_en: {len(d[\"definition_en\"])}')
    print(f'  body_basic_ko: {len(d[\"body_basic_ko\"])}')
    print(f'  body_basic_en: {len(d[\"body_basic_en\"])}')
    print(f'  body_advanced_ko: {len(d[\"body_advanced_ko\"])}')
    print(f'  body_advanced_en: {len(d[\"body_advanced_en\"])}')
"
```

Expected:
- `definition_ko/en` still 200~450 chars (UI target preserved)
- `body_basic_ko` ≥ 2000, probably 2500~3500
- `body_basic_en` ≥ 2000, probably 3000~5000 (naturally longer than KO)
- `body_advanced_ko` ≥ 3000
- `body_advanced_en` ≥ 3000

---

## Task 7: Re-audit format — currency $ should still be flagged (expected, renderer handles it)

**Files:**
- Use: `c:/tmp/audit_format.py`, `c:/tmp/audit_format_advanced.py`

**Step 1: Run basic audit**

Run: `cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/audit_format.py`

Expected: Previously identified EN §1 length warnings should NOT appear (the audit script's "expected 700~1000 chars" check in `issues_in_section` step §1 is now arbitrary — update audit to remove that check if noisy, or simply accept the noise since targets were removed).

If the length check in `audit_format.py` still triggers, that's the audit being out of sync with the prompt — acceptable for this task, update if bothering.

**Step 2: Run advanced audit**

Run: `cd backend && PYTHONPATH=. .venv/Scripts/python c:/tmp/audit_format_advanced.py`

Expected: single-$ math warning for GPU **may still appear** if the LLM generates `$/시간` again — but now the renderer handles it safely. The audit is correct that the content has `$`, but the rendering outcome is safe because of Task 1 (renderer config flip).

To confirm renderer behavior, open the rendered page in browser (Step 3 below).

**Step 3: Visual verification via frontend build**

Run: `cd frontend && npm run build`

Expected: build succeeds. Start dev server (`npm run dev`) and open `http://localhost:4321/ko/handbook/gpu/?level=advanced` (or equivalent preview path) to visually confirm:
- `$/시간, $/토큰` renders as literal text in the §2 section
- `$$...$$` block formulas (if any) render as math
- No KaTeX error messages

If the renderer still renders `$/시간` as math, investigate: Task 1 might not have taken effect (browser cache, wrong file, etc.).

---

## Task 8: Apply regen to DB + commit operational changes

**Files:**
- Use: `c:/tmp/apply_regen_to_db.py`

**Step 1: Apply 3 regens to DB as draft**

Run:
```bash
cd backend && PYTHONPATH=. PYTHONIOENCODING=utf-8 .venv/Scripts/python c:/tmp/apply_regen_to_db.py
```

Expected output:
```
[llm]
  definition_ko: XXX chars
  ...
  ✅ UPDATED → status='draft'

[gpu]
  ...
  ✅ UPDATED → status='draft'

[embedding]
  ...
  ✅ UPDATED → status='draft'
```

**Step 2: Verify DB state**

Via Supabase MCP or SQL:
```sql
SELECT slug, status, length(definition_ko), length(body_basic_ko), length(body_advanced_ko)
FROM handbook_terms
WHERE slug IN ('llm', 'gpu', 'embedding');
```

Expected: all 3 have `status='draft'` with updated lengths. Status `draft` hides them from public view until explicit publish.

**Step 3: Check overall published count**

```sql
SELECT status, count(*) FROM handbook_terms GROUP BY status;
```

Expected: published count remains 49 (the 3 terms were already draft from previous pilot). If different, investigate.

**Step 4: No code commit needed for Task 8**

DB changes do not produce file diffs. The operational regen is a runtime action, not a code change. Task 1, 5 commits already capture the code-level changes.

If regen logs need preservation, save to vault:
```bash
cp c:/tmp/regen_llm_log.txt vault/12-Journal-&-Decisions/2026-04-10-pilot-regen-v3-llm.log
# ...etc
```
(optional, skip if not needed for audit trail)

---

## Task 9: Manual visual verification + sign-off

**Step 1: Open admin editor to each draft**

- `/admin/handbook/edit/llm` — review all sections
- `/admin/handbook/edit/gpu` — **specifically check Advanced §2 formulas section** for `$` handling
- `/admin/handbook/edit/embedding` — review for content quality

Verify:
- Definition 200~450 chars, reads as technical summary
- 7 Basic sections present, natural length (not artificially short or long)
- 7 Advanced sections present
- Hero card news context 3 lines each with `"quote" → meaning`
- References populated, primary ≥2
- Sidebar checklist 4~5 items
- No "요약:" / "Takeaway:" prefix in §3 glance section
- GPU Advanced §2: dollar signs render as literal, no broken math rendering

**Step 2: Decide: publish or revise**

If quality is good:
- Update `status='published'` in admin editor UI or via SQL:
  ```sql
  UPDATE handbook_terms SET status='published' WHERE slug IN ('llm', 'gpu', 'embedding');
  ```
- This promotes the 3 terms back to public visibility with improved content.

If quality has issues:
- Document the issue in this plan file under a new section `## Findings from re-regen`
- Decide whether to adjust prompts further or restore from `c:/tmp/regen_backup/` backups
- Do NOT promote to published

---

## Verification checklist (end-to-end)

Before marking this plan complete:

- [ ] Frontend build passes (`cd frontend && npm run build`)
- [ ] Backend lint passes (`cd backend && .venv/Scripts/ruff check services/agents/prompts_advisor.py models/advisor.py`)
- [ ] Backend tests pass except known pre-existing failure (`pytest tests/test_handbook_advisor.py`)
- [ ] `grep -n "target.*chars" backend/services/agents/prompts_advisor.py` returns only `definition` matches
- [ ] 3 regen JSONs exist and have `status='draft'` in DB
- [ ] Visual spot-check in admin editor confirms GPU Advanced §2 renders currency `$` as literal
- [ ] Commit 1 (renderer fix) and Commit 2 (prompt cleanup) both landed on `main`

---

## Rollback plan

**If renderer fix breaks existing content:**
1. Revert `frontend/src/lib/markdown.ts:141` back to `{ singleDollarTextMath: true }`
2. Rebuild: `cd frontend && npm run build`
3. Deploy

**If prompt cleanup causes regression (LLM produces badly formed content):**
1. Revert `backend/services/agents/prompts_advisor.py` to state before this plan: `git revert <commit>`
2. Re-regen 3 pilot terms (content returns to prior behavior)

**If 3 pilot terms now render worse than before:**
1. Restore from backup:
   ```bash
   cd backend && .venv/Scripts/python -c "
   import json
   from core.database import get_supabase
   sb = get_supabase()
   for slug in ['llm', 'gpu', 'embedding']:
       with open(f'c:/tmp/regen_backup/{slug}_backup_20260410_151737.json') as f:
           row = json.load(f)
       # Strip fields that should not be updated (id, timestamps)
       for k in ['id', 'created_at', 'updated_at']:
           row.pop(k, None)
       sb.table('handbook_terms').update(row).eq('slug', slug).execute()
   "
   ```

---

## Notes for executor

- **Do NOT touch `definition_ko/en` length targets.** They exist because Expert popup has hard CSS constraint (`max-height: 260px`).
- **Do NOT touch Pydantic `min_length` values.** They are fail-fast signals, not content shape constraints. Unchanged `min_length=180` for definition, `min_length=2000` for basic body, `min_length=3000` for advanced body.
- **The renderer fix (Task 1) takes effect immediately on all 138 existing handbook rows** — no migration, no regen needed. The prompt cleanup (Tasks 2-5) only affects future generations.
- **Pilot 3 (llm, gpu, embedding) are currently `status='draft'`** from earlier pilot (commit `1ac2a4a`). They are hidden from users. After this plan, they are re-regen'd but remain `draft` until explicit publish in Task 9.
- **If `audit_format.py` flags EN §1 length as "overshoot 700~1000"**, that's the audit being out of sync. Update the audit script's `issues_in_section` step 1 to remove the `500 < c < 1200` check, or simply ignore the warning. It is no longer a valid issue after this plan.
