# Weekly News Consolidation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute 5 workstreams (A-E) to eliminate dead `guide_items` fields, fix admin `post_type` corruption, add `excerpt`+`focus_items` to weekly, backfill W13/W14/W15, and clean residual JSONB keys.

**Architecture:** Backend Python (FastAPI + Supabase) edits within existing file/function boundaries; Astro frontend edits constrained to one component; pure docs/SQL for cleanup. A-C implement locally → push → Railway redeploy → D and E run against prod DB. One new file (unit test). No schema migrations.

**Tech Stack:** FastAPI, Supabase (PostgreSQL JSONB), OpenAI gpt-5/gpt-5-mini, Astro v5, TypeScript, pytest, ruff

**Design doc:** [[2026-04-19-weekly-consolidation]]

---

## Prerequisites

- Clean `git status` (or explicit user approval to proceed with pending changes)
- `backend/.venv` active for Python commands — or use `backend/.venv/Scripts/python.exe` directly on Windows
- Design doc approved and committed (done: `73255f3`)

---

## Task 1: Remove `PromptGuideItems` from backend models

**Files:**
- Modify: `backend/models/common.py` (remove class at line 12-17)
- Modify: `backend/models/posts.py` (line 5 import + line 45, 69 type annotation)

**Step 1:** Verify current class state

```bash
./backend/.venv/Scripts/python.exe -c "from models.common import PromptGuideItems; print(PromptGuideItems.model_fields.keys())"
```

Expected: `dict_keys(['one_liner', 'action_item', 'critical_gotcha', 'rotating_item', 'quiz_poll'])`

**Step 2:** Edit `backend/models/common.py` — delete the `PromptGuideItems` class block entirely. Keep the `QuizPoll` class and the imports.

**Step 3:** Edit `backend/models/posts.py`:
- Line 5: remove `PromptGuideItems` from the import line
- Line 45: `guide_items: Optional[PromptGuideItems] = None` → `guide_items: Optional[dict] = None`
- Line 69: same replacement

**Step 4:** Verify imports don't break

```bash
cd backend && ./.venv/Scripts/python.exe -c "from models.posts import PostDraftDetail, PostUpdateRequest; print('ok')"
```

Expected: `ok`

**Step 5:** Run full backend lint

```bash
./.venv/Scripts/python.exe -m ruff check backend/
```

Expected: `All checks passed!`

**Step 6:** Commit

```bash
git add backend/models/common.py backend/models/posts.py
git commit -m "chore(models): remove dead PromptGuideItems class"
```

---

## Task 2: Remove 4 dead fields from `prompts_advisor.py`

**Files:**
- Modify: `backend/services/agents/prompts_advisor.py` (lines 49-73, `_GENERATE_GUIDE_ITEMS` dict)

**Step 1:** Read lines 49-73 to locate the four sub-dicts (ai-news, study, career, project)

```bash
grep -n '"one_liner"\|"action_item"\|"critical_gotcha"\|"rotating_item"' backend/services/agents/prompts_advisor.py
```

Expected output: 16 lines (4 digest_types × 4 fields)

**Step 2:** For each of the 4 sub-dicts in `_GENERATE_GUIDE_ITEMS`, delete the 4 key entries: `"one_liner"`, `"action_item"`, `"critical_gotcha"`, `"rotating_item"`. Keep any other keys (if present) and the dict structure.

**Step 3:** Verify no more references

```bash
grep -n '"one_liner"\|"action_item"\|"critical_gotcha"\|"rotating_item"' backend/services/agents/prompts_advisor.py
```

Expected: no output

**Step 4:** Lint + import check

```bash
cd backend && ./.venv/Scripts/python.exe -m ruff check services/agents/prompts_advisor.py
./.venv/Scripts/python.exe -c "from services.agents.prompts_advisor import _GENERATE_GUIDE_ITEMS; print(list(_GENERATE_GUIDE_ITEMS.keys()))"
```

Expected: lint passes, keys list shows remaining digest_type names

**Step 5:** Commit

```bash
git add backend/services/agents/prompts_advisor.py
git commit -m "chore(advisor): remove dead one_liner/action_item/critical_gotcha/rotating_item suggestions"
```

---

## Task 3: Clean `openapi.json` (component + refs + required)

**Files:**
- Modify: `backend/openapi.json` at line 588, 905, 941-971

**Step 1:** Preferred — regenerate from FastAPI if possible

```bash
cd backend && ./.venv/Scripts/python.exe -c "
import json
from main import app
with open('openapi.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
print('regenerated')
"
```

If `main` imports or dev DB access fails, fall back to manual edit (step 2).

**Step 2:** Manual edit (if regeneration fails)
- Remove the `PromptGuideItems` object from `components.schemas` (line 941-971 range, including the full object)
- At line 588 and 905 replace `"$ref": "#/components/schemas/PromptGuideItems"` with `{"type": "object", "nullable": true}`
- The `required: [...]` array at line 965-970 disappears with the component removal; no separate action needed

**Step 3:** Verify JSON validity

```bash
./.venv/Scripts/python.exe -c "import json; json.load(open('backend/openapi.json')); print('valid json')"
```

Expected: `valid json`

**Step 4:** Grep for any lingering refs

```bash
grep -c "PromptGuideItems" backend/openapi.json
```

Expected: `0`

**Step 5:** Commit

```bash
git add backend/openapi.json
git commit -m "chore(openapi): drop PromptGuideItems schema and refs"
```

---

## Task 4: Clean `NewsprintArticleLayout.astro` (interface + render blocks)

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro`

**Step 1:** Edit the `interface GuideItems` block (around line 15-23). Remove ONLY these field lines:

```typescript
one_liner?: string;
action_item?: string;
critical_gotcha?: string;
rotating_item?: string;
```

**KEEP**: `quiz_poll?: QuizPoll | null;`, `weekly_quiz_expert?: QuizPoll[];`, `weekly_quiz_learner?: QuizPoll[];`, `excerpt_learner?: string;` (if present).

**Step 2:** Update `hasGuideItems` condition (around line 137). Remove references to the 4 removed fields. After edit, the condition should only check quiz presence (daily and weekly).

Before:
```typescript
const hasGuideItems = guideItems && (guideItems.one_liner || guideItems.action_item || guideItems.critical_gotcha || guideItems.rotating_item || hasQuizData || hasWeeklyQuizData);
```

After:
```typescript
const hasGuideItems = guideItems && (hasQuizData || hasWeeklyQuizData);
```

**Step 3:** Remove 4 dead render blocks (currently around line 396-422). Each block has the pattern `{guideItems!.FIELD && (...)}`. Remove all 4 blocks for one_liner / action_item / critical_gotcha / rotating_item. **KEEP** the `activeQuiz` block and the `activeWeeklyQuizzes` block.

**Step 4:** Frontend build

```bash
cd frontend && npm run build
```

Expected: `Complete!` with 0 errors. Warnings OK if unrelated.

**Step 5:** Grep sanity

```bash
grep -c "one_liner\|action_item\|critical_gotcha\|rotating_item" frontend/src/components/newsprint/NewsprintArticleLayout.astro
```

Expected: `0`

**Step 6:** Commit

```bash
git add frontend/src/components/newsprint/NewsprintArticleLayout.astro
git commit -m "chore(frontend): remove dead guide_items render blocks"
```

---

## Task 5: Update vault design docs

**Files:**
- Modify: `vault/02-Architecture/Database-Schema-Overview.md` line 34
- Modify: `vault/04-AI-System/Quality-Gates-&-States.md` line 31

**Step 1:** Read current line 34 of Database-Schema-Overview:

```bash
sed -n '30,40p' vault/02-Architecture/Database-Schema-Overview.md
```

**Step 2:** Edit line 34. Current:
```
| **5블록** | `guide_items` (JSONB) | `{one_liner, action_item, critical_gotcha, rotating_item, quiz_poll}` |
```
Replace with:
```
| **가이드 블록** | `guide_items` (JSONB) | daily: `{quiz_poll_expert, quiz_poll_learner, sources_expert, sources_learner, excerpt_learner, title_learner}` · weekly: `{week_numbers, week_tool, week_terms, weekly_quiz_expert, weekly_quiz_learner, excerpt_learner, title_learner}` |
```

**Step 3:** Edit `Quality-Gates-&-States.md` line 31. Current:
```
| **PromptGuideItems** | 5블록: one_liner, action_item, critical_gotcha, rotating_item, quiz_poll |
```
Replace with:
```
| **guide_items (JSONB)** | daily: persona별 quiz_poll + sources_*. weekly: week_numbers, week_tool, week_terms, weekly_quiz_*, excerpt_learner. PromptGuideItems 클래스는 2026-04-19 제거됨. |
```

**Step 4:** Commit

```bash
git add vault/02-Architecture/Database-Schema-Overview.md vault/04-AI-System/Quality-Gates-&-States.md
git commit -m "docs(vault): update schema docs to reflect removed dead fields"
```

---

## Task 6: Add `weekly` option to admin `post_type` dropdown

**Files:**
- Modify: `frontend/src/pages/admin/edit/[slug].astro` (around line 180-184)

**Step 1:** Locate the current dropdown

```bash
grep -n "post-type" frontend/src/pages/admin/edit/\[slug\].astro
```

**Step 2:** Add the `weekly` option. Current block:

```astro
<select id="edit-post-type" class="admin-select" style="width:100%;">
  <option value="" selected={!post?.post_type}>—</option>
  <option value="research" selected={post?.post_type === 'research'}>Research</option>
  <option value="business" selected={post?.post_type === 'business'}>Business</option>
</select>
```

Replace with:

```astro
<select id="edit-post-type" class="admin-select" style="width:100%;">
  <option value="" selected={!post?.post_type}>—</option>
  <option value="research" selected={post?.post_type === 'research'}>Research</option>
  <option value="business" selected={post?.post_type === 'business'}>Business</option>
  <option value="weekly"
          selected={post?.post_type === 'weekly'}
          disabled={post?.post_type !== 'weekly'}>Weekly</option>
</select>
```

**Step 3:** Frontend build + type check

```bash
cd frontend && npm run build
```

Expected: `Complete!` with 0 errors.

**Step 4:** Commit

```bash
git add frontend/src/pages/admin/edit/\[slug\].astro
git commit -m "fix(admin): add weekly option to post_type dropdown to prevent corruption"
```

---

## Task 7: Extend `WEEKLY_EXPERT_PROMPT` + `WEEKLY_LEARNER_PROMPT`

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (WEEKLY_EXPERT_PROMPT at line ~1084, WEEKLY_LEARNER_PROMPT at line ~1211)

**Step 1:** Locate the JSON output format sections of both prompts

```bash
grep -n '"headline":\|"en":\|"week_numbers":\|"week_tool":\|"weekly_quiz":' backend/services/agents/prompts_news_pipeline.py
```

**Step 2:** In `WEEKLY_EXPERT_PROMPT`:

Add to the JSON schema description (alongside existing fields):
```
"excerpt": "1-2 sentences that make readers click. MUST differ from the body's 'This Week in One Line' section",
"focus_items": ["Exactly 3 bullets, EN 5-12 words each. P1=what shifted this week, P2=why it matters, P3=what to watch next week"]
```

Also add to the output JSON example (the second code block that shows the output shape):
```json
"excerpt": "A strategic reshuffle week: Anthropic gated cyber models while Meta doubled down on product-native AI.",
"focus_items": [
  "Meta Muse Spark launch redefines product-native AI",
  "Anthropic Glasswing gates high-risk cyber capability",
  "Watch Nvidia's response to $122B OpenAI raise"
]
```

**Step 3:** In `WEEKLY_LEARNER_PROMPT`: same JSON additions, but with plain-language guidance:

```
"excerpt": "1-2 sentences, plain language, click-worthy for non-specialist readers. MUST differ from body's 'This Week in One Line'",
"focus_items": ["Exactly 3 bullets, EN 5-12 words each. P1=what shifted, P2=why it matters for general readers, P3=what to watch"]
```

**Step 4:** Lint

```bash
cd backend && ./.venv/Scripts/python.exe -m ruff check services/agents/prompts_news_pipeline.py
```

Expected: `All checks passed!`

**Step 5:** Commit

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(weekly): add excerpt + focus_items to EN weekly prompts matching daily pattern"
```

---

## Task 8: Extend `WEEKLY_KO_ADAPT_PROMPT`

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (WEEKLY_KO_ADAPT_PROMPT at line ~1344)

**Step 1:** Locate the current marker instruction for `weekly_quiz_ko`

```bash
grep -n "ENGLISH WEEKLY QUIZ\|weekly_quiz_ko" backend/services/agents/prompts_news_pipeline.py
```

**Step 2:** Add a parallel section for the META marker (right after the quiz marker section in the prompt). Text:

```
## English Meta Block (excerpt + focus_items)

The user message may also end with a marker `---ENGLISH META (JSON, translate to excerpt_ko + focus_items_ko)---` followed by a JSON object containing `excerpt` and `focus_items` fields. Translate those 1:1 into `excerpt_ko` and `focus_items_ko`:

- `excerpt_ko`: Korean translation of `excerpt`. Natural Korean, same intent.
- `focus_items_ko`: Korean translations of `focus_items` array, preserving the same order and count.

If the marker is absent, omit both fields from output.
```

**Step 3:** Add the two new fields to the KO_ADAPT JSON output schema:

```
"excerpt_ko": "Korean translation of the EN excerpt",
"focus_items_ko": ["Korean translations of EN focus_items in same order"]
```

**Step 4:** Lint + format test

```bash
cd backend && ./.venv/Scripts/python.exe -m ruff check services/agents/prompts_news_pipeline.py
./.venv/Scripts/python.exe -c "
from services.agents.prompts_news_pipeline import WEEKLY_KO_ADAPT_PROMPT, get_weekly_ko_prompt
p = get_weekly_ko_prompt('expert')
assert 'excerpt_ko' in p, 'excerpt_ko missing'
assert 'focus_items_ko' in p, 'focus_items_ko missing'
assert 'ENGLISH META' in p, 'META marker missing'
print('ok')
"
```

Expected: `All checks passed!` + `ok`

**Step 5:** Commit

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(weekly): add excerpt_ko + focus_items_ko to KO adapter prompt + META marker"
```

---

## Task 9: Write `_validate_focus_items` helper with unit tests

**Files:**
- Modify: `backend/services/pipeline.py` (add helper near `_validate_and_shuffle_weekly_quiz`)
- Create: `backend/tests/test_weekly_focus_items.py`

**Step 1 (TDD):** Write the failing test first

Create `backend/tests/test_weekly_focus_items.py`:

```python
"""Unit tests for _validate_focus_items helper."""
from services.pipeline import _validate_focus_items


class TestValidation:
    def test_happy_path_three_items(self):
        items = ['a', 'b', 'c']
        assert _validate_focus_items(items) == ['a', 'b', 'c']

    def test_rejects_wrong_count(self):
        assert _validate_focus_items(['a', 'b']) == []
        assert _validate_focus_items(['a', 'b', 'c', 'd']) == []
        assert _validate_focus_items([]) == []

    def test_rejects_non_list(self):
        assert _validate_focus_items(None) == []
        assert _validate_focus_items('a,b,c') == []
        assert _validate_focus_items({'a': 1}) == []

    def test_strips_whitespace(self):
        assert _validate_focus_items(['  a  ', 'b', 'c']) == ['a', 'b', 'c']

    def test_rejects_empty_string_item(self):
        assert _validate_focus_items(['a', '', 'c']) == []
        assert _validate_focus_items(['a', '   ', 'c']) == []

    def test_stringifies_non_string_items(self):
        # Defensive: LLM might return a number or bool
        assert _validate_focus_items([1, 2, 3]) == ['1', '2', '3']
```

**Step 2:** Run test to verify failure

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_weekly_focus_items.py -v
```

Expected: `ImportError` or `AttributeError` (function not yet defined)

**Step 3:** Implement `_validate_focus_items` in `backend/services/pipeline.py` right below `_validate_and_shuffle_weekly_quiz`:

```python
def _validate_focus_items(items: Any) -> list[str]:
    """Normalize LLM focus_items output to exactly 3 non-empty strings, else [].

    All-or-nothing by design: partial focus_items list confuses the sidebar more
    than missing them entirely.
    """
    if not isinstance(items, list) or len(items) != 3:
        return []
    cleaned = [str(item).strip() for item in items]
    if any(not c for c in cleaned):
        return []
    return cleaned
```

**Step 4:** Run tests — verify pass

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_weekly_focus_items.py -v
```

Expected: all 6 tests PASS

**Step 5:** Lint

```bash
./.venv/Scripts/python.exe -m ruff check services/pipeline.py tests/test_weekly_focus_items.py
```

Expected: `All checks passed!`

**Step 6:** Commit

```bash
git add backend/services/pipeline.py backend/tests/test_weekly_focus_items.py
git commit -m "feat(weekly): add _validate_focus_items helper with tests"
```

---

## Task 10: Pipeline KO adapter input extension + row save logic

**Files:**
- Modify: `backend/services/pipeline.py` `_gen_weekly_persona` (around line 2018-2033)
- Modify: `backend/services/pipeline.py` `run_weekly_pipeline` row save (around line 2180-2220)

**Step 1:** Extend KO adapter input. Locate the block just before the KO adapter call:

```bash
grep -n "ENGLISH WEEKLY QUIZ\|ko_input = " backend/services/pipeline.py
```

Current logic builds `ko_input` with quiz marker. Extend it:

```python
import json as _json
en_content = en_data.get("en", "")
en_quiz = en_data.get("weekly_quiz") or []
en_excerpt = (en_data.get("excerpt") or "").strip()
en_focus = en_data.get("focus_items") or []

ko_input_parts = [en_content]
if en_quiz:
    ko_input_parts.append(
        "---ENGLISH WEEKLY QUIZ (JSON, translate to weekly_quiz_ko)---\n"
        + _json.dumps(en_quiz, ensure_ascii=False, indent=2)
    )
if en_excerpt or en_focus:
    meta = {"excerpt": en_excerpt, "focus_items": en_focus}
    ko_input_parts.append(
        "---ENGLISH META (JSON, translate to excerpt_ko + focus_items_ko)---\n"
        + _json.dumps(meta, ensure_ascii=False, indent=2)
    )
ko_input = "\n\n".join(ko_input_parts)
```

Pass `ko_input` (not `en_content`) to the KO adapter call.

**Step 2:** Extend row save. Locate the locale loop (around line 2180-2220). Find where `locale_guide` and `row` are built.

After the existing `excerpt_learner` computation (or if missing, add):

```python
# locale-appropriate key selection
excerpt_key = "excerpt" if locale == "en" else "excerpt_ko"
focus_key = "focus_items" if locale == "en" else "focus_items_ko"

excerpt = (expert_data.get(excerpt_key) or learner_data.get(excerpt_key) or "").strip()
excerpt_learner = (learner_data.get(excerpt_key) or "").strip()

# focus_items: prefer expert, locale-level (matches daily pattern)
focus_raw = expert_data.get(focus_key) or learner_data.get(focus_key) or []
focus_items = _validate_focus_items(focus_raw)

# Guard excerpt length (LLM runaway defense)
if len(excerpt) > 1000:
    excerpt = excerpt[:1000].rstrip() + '…'
```

Update the `row` dict:
```python
row = {
    ...,
    "excerpt": excerpt or None,
    "focus_items": focus_items,
    ...,  # (existing fields continue)
}
```

Update `locale_guide`:
```python
locale_guide["excerpt_learner"] = excerpt_learner
```

**Step 3:** Lint

```bash
cd backend && ./.venv/Scripts/python.exe -m ruff check services/pipeline.py
```

Expected: `All checks passed!`

**Step 4:** Run all weekly tests

```bash
./.venv/Scripts/python.exe -m pytest tests/test_weekly_quiz_shuffle.py tests/test_weekly_focus_items.py -v
```

Expected: all pass (14 + 6 = 20 tests)

**Step 5:** Commit

```bash
git add backend/services/pipeline.py
git commit -m "feat(weekly): pipeline excerpt + focus_items save + KO META marker passthrough"
```

---

## Task 11: Full lint + build verification

**Step 1:** Backend lint

```bash
cd backend && ./.venv/Scripts/python.exe -m ruff check .
```

Expected: `All checks passed!`

**Step 2:** Backend tests

```bash
./.venv/Scripts/python.exe -m pytest tests/ -v --tb=short -x
```

Expected: all existing tests pass (no regression)

**Step 3:** Frontend build

```bash
cd ../frontend && npm run build
```

Expected: `Complete!` with 0 errors

**Step 4:** Git status check — should be clean

```bash
git status
```

Expected: `nothing to commit, working tree clean` (all prior tasks committed)

**Step 5:** Do NOT commit — this is verification only.

---

## Task 12: Push to main + wait for Railway

**Step 1:** Show ahead-count

```bash
git log --oneline origin/main..HEAD
```

Expected: 7-9 commits (Task 1-10 commits)

**Step 2:** Push

```bash
git push origin main
```

**Step 3:** Wait for Railway redeploy. Poll Railway logs or status for deployed commit hash matching latest local hash. Typically ~2 minutes.

**Step 4:** Sanity check against deployed URL

```bash
curl -s https://api.0to1log.com/health
```

Expected: `{"status":"ok"}` or similar

---

## Task 13: Execute Workstream D — backfill W13/W14/W15

**Step 1:** Run backfill in sequence with logging

```bash
cd backend && PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -c "
import sys, asyncio, logging
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
from services.pipeline import run_weekly_pipeline

for wk in ['2026-W13', '2026-W14', '2026-W15']:
    print(f'=== Backfilling {wk} ===')
    result = asyncio.run(run_weekly_pipeline(week_id=wk))
    print(f'{wk}: status={result.status} errors={result.errors}')
    if result.status != 'success':
        print('ABORT — investigate before proceeding')
        break
" 2>&1 | tee /tmp/backfill.log
```

Expected: 3 × `status=success errors=[]`. Total ~8 minutes. Cost ~$0.45.

**Step 2:** Verify row-level fields for all 6 rows

```bash
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
from core.database import get_supabase
sb = get_supabase()
ok = True
for slug_base in ['2026-w13-weekly-digest', '2026-w14-weekly-digest', '2026-w15-weekly-digest']:
    for locale in ['en', 'ko']:
        slug = slug_base if locale == 'en' else slug_base + '-ko'
        r = sb.table('news_posts').select('*').eq('slug', slug).eq('locale', locale).single().execute()
        d = r.data
        gi = d.get('guide_items') or {}
        checks = {
            'excerpt not empty': bool(d.get('excerpt')),
            'focus_items len 3': isinstance(d.get('focus_items'), list) and len(d['focus_items']) == 3,
            'content_analysis null': d.get('content_analysis') is None,
            'weekly_quiz_expert len 3': len(gi.get('weekly_quiz_expert', [])) == 3,
            'weekly_quiz_learner len 3': len(gi.get('weekly_quiz_learner', [])) == 3,
            'excerpt_learner not empty': bool(gi.get('excerpt_learner')),
        }
        failed = [k for k, v in checks.items() if not v]
        status = 'OK' if not failed else 'FAIL: ' + ', '.join(failed)
        print(f'{slug} [{locale}]: {status}')
        if failed: ok = False
print()
print('OVERALL:', 'OK' if ok else 'FAIL')
"
```

Expected: All 6 rows `OK`, overall `OK`.

**Step 3:** Browser smoke test

Visit these URLs, confirm:
- `https://0to1log.com/ko/news/2026-w13-weekly-digest-ko/` — excerpt in list card area, focus_items in sidebar, quiz 3 items, NO "핵심 분석" JSON dump
- Same for W14, W15 (EN and KO)

**Step 4:** No commit — DB-only operation. Note result in next sprint update commit.

---

## Task 14: Execute Workstream E — JSONB residual key cleanup

**Step 1:** Preflight — count affected rows

```bash
cd backend && PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
from core.database import get_supabase
sb = get_supabase()
# Use execute_sql raw if available, else plain select
res = sb.rpc('execute_sql', {'query': \"SELECT post_type, COUNT(*) FROM news_posts WHERE guide_items ?| array['one_liner','action_item','critical_gotcha','rotating_item'] GROUP BY post_type\"}).execute() if False else None
# Fallback: count via python scan
all_posts = sb.table('news_posts').select('id, post_type, guide_items').execute().data or []
dead_keys = {'one_liner', 'action_item', 'critical_gotcha', 'rotating_item'}
count_by_type = {}
for p in all_posts:
    gi = p.get('guide_items') or {}
    if any(k in gi for k in dead_keys):
        pt = p.get('post_type') or '(null)'
        count_by_type[pt] = count_by_type.get(pt, 0) + 1
print('Rows with dead keys:', count_by_type)
print('Total:', sum(count_by_type.values()))
"
```

Expected: some count (likely daily posts dominate).

**Step 2:** Execute cleanup via python (not raw SQL — using supabase client)

```bash
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
from core.database import get_supabase
sb = get_supabase()
all_posts = sb.table('news_posts').select('id, guide_items').execute().data or []
dead_keys = ['one_liner', 'action_item', 'critical_gotcha', 'rotating_item']
updated = 0
for p in all_posts:
    gi = p.get('guide_items') or {}
    to_remove = [k for k in dead_keys if k in gi]
    if not to_remove:
        continue
    new_gi = {k: v for k, v in gi.items() if k not in dead_keys}
    sb.table('news_posts').update({'guide_items': new_gi}).eq('id', p['id']).execute()
    updated += 1
print(f'Cleaned {updated} rows')
"
```

Expected: count matches Step 1.

**Step 3:** Verify zero remaining

```bash
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -c "
from core.database import get_supabase
sb = get_supabase()
all_posts = sb.table('news_posts').select('guide_items').execute().data or []
dead = ['one_liner', 'action_item', 'critical_gotcha', 'rotating_item']
residual = sum(1 for p in all_posts if any(k in (p.get('guide_items') or {}) for k in dead))
print(f'Residual rows with dead keys: {residual}')
assert residual == 0
"
```

Expected: `Residual rows with dead keys: 0`

**Step 4:** No commit — DB-only operation.

---

## Task 15: Sprint update + memory commit

**Step 1:** Update `ACTIVE_SPRINT.md` — mark CONSOL-A through CONSOL-E done with evidence commit hashes.

Add to Current Doing table (at bottom):

```markdown
| CONSOL-A | Dead guide_items fields 완전 제거 (models/advisor/frontend/openapi/vault) | done | 2026-04-19 | 2026-04-19 |
| CONSOL-B | Admin post_type 드롭다운 weekly 옵션 추가 | done | 2026-04-19 | 2026-04-19 |
| CONSOL-C | Weekly excerpt + focus_items 프롬프트 + pipeline (daily 패턴 일치) | done | 2026-04-19 | 2026-04-19 |
| CONSOL-D | W13/W14/W15 백필 실행 + 검증 | done | 2026-04-19 | 2026-04-19 |
| CONSOL-E | 기존 daily `guide_items` dead 키 JSONB 정리 | done | 2026-04-19 | 2026-04-19 |
```

(Fill in actual commit hashes from git log before commit.)

**Step 2:** Verify memory is still accurate

Check `C:\Users\amy\.claude\projects\c--Users-amy-Desktop-0to1log\memory\MEMORY.md` — no updates needed unless new patterns emerged during execution.

**Step 3:** Commit sprint update

```bash
git add vault/09-Implementation/plans/ACTIVE_SPRINT.md
git commit -m "docs(sprint): mark CONSOL-A~E done"
```

**Step 4:** Push

```bash
git push origin main
```

**Step 5:** Move plan docs to archive (optional, per CLAUDE.md convention):

Consider moving:
- `vault/09-Implementation/plans/2026-04-19-weekly-consolidation.md` → `vault/90-Archive/2026-04/plans-completed/`
- `vault/09-Implementation/plans/2026-04-19-weekly-consolidation-plan.md` → same

Skip this step for now — user can archive after visual confirmation.

---

## Summary of Commits Expected

Tasks produce approximately 10-11 commits in this order:

1. `chore(models): remove dead PromptGuideItems class` (T1)
2. `chore(advisor): remove dead ... suggestions` (T2)
3. `chore(openapi): drop PromptGuideItems schema and refs` (T3)
4. `chore(frontend): remove dead guide_items render blocks` (T4)
5. `docs(vault): update schema docs to reflect removed dead fields` (T5)
6. `fix(admin): add weekly option to post_type dropdown` (T6)
7. `feat(weekly): add excerpt + focus_items to EN weekly prompts` (T7)
8. `feat(weekly): add excerpt_ko + focus_items_ko to KO adapter` (T8)
9. `feat(weekly): add _validate_focus_items helper with tests` (T9)
10. `feat(weekly): pipeline excerpt + focus_items save + KO META marker passthrough` (T10)
11. `docs(sprint): mark CONSOL-A~E done` (T15)

**Push**: after T11 (before backfill). Then one more push after T15.

---

## Rollback Strategy

If any task fails blockingly:
- **T1-T10 (code)**: `git reset --hard HEAD~N` to drop that task's commit(s), fix, retry
- **T12 (push)**: revert via new commit if deploy breaks; Railway rolls back on failed healthcheck
- **T13 (backfill)**: drafts can be rerun repeatedly; no data loss
- **T14 (JSONB cleanup)**: keys were all NULL, no recovery needed; re-run idempotent

---

## References

- Design doc: [[2026-04-19-weekly-consolidation]]
- Related: [[2026-04-19-weekly-content-v2]] (weekly quiz precedent)
- Memory: `project_weekly_editorial.md` (editorial direction)
