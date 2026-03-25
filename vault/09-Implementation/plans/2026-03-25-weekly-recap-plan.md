# Weekly Recap Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automated weekly recap pipeline that aggregates Mon-Fri daily digests into a single Weekly post with trend analysis, "Week in Numbers", bottom cards (term + tool), and Buttondown email integration (disabled by default).

**Architecture:** New `run_weekly_pipeline()` function in pipeline.py fetches the week's daily digests from DB, sends them to LLM with a weekly prompt (expert/learner x EN/KO = 4 calls), saves as `post_type='weekly'` in news_posts. Frontend adds a Weekly tab to the news list and renders bottom cards on the detail page.

**Tech Stack:** FastAPI, gpt-4.1, Supabase (PostgreSQL), Astro v5, Tailwind v4

---

## Chunk 1: Database + Backend Pipeline

### Task 1: DB Migration — add 'weekly' to post_type

**Files:**
- Create: `supabase/migrations/00041_weekly_post_type.sql`

- [ ] **Step 1: Write migration SQL**

```sql
-- 00041_weekly_post_type.sql
-- Allow 'weekly' as a post_type value for news_posts.

-- Drop the existing CHECK constraint (from 00001 initial schema)
ALTER TABLE news_posts
  DROP CONSTRAINT IF EXISTS news_posts_post_type_check;

-- Re-create with 'weekly' included
ALTER TABLE news_posts
  ADD CONSTRAINT news_posts_post_type_check
  CHECK (post_type IN ('research', 'business', 'weekly'));
```

- [ ] **Step 2: Run migration against Supabase**

```bash
cd backend && source .venv/Scripts/activate
python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or open('.env').read().split('DATABASE_URL=')[1].split('\n')[0])
conn.autocommit = True
cur = conn.cursor()
cur.execute(open('../supabase/migrations/00041_weekly_post_type.sql').read())
print('Migration applied')
conn.close()
"
```

- [ ] **Step 3: Verify constraint**

```bash
python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or open('.env').read().split('DATABASE_URL=')[1].split('\n')[0])
cur = conn.cursor()
cur.execute(\"SELECT conname, consrc FROM pg_constraint WHERE conrelid = 'news_posts'::regclass AND conname LIKE '%post_type%'\")
print(cur.fetchall())
conn.close()
"
```

Expected: `('news_posts_post_type_check', ... 'weekly' ...)`

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/00041_weekly_post_type.sql
git commit -m "feat(db): add 'weekly' to news_posts post_type constraint"
```

---

### Task 2: Config — add Buttondown + weekly settings

**Files:**
- Modify: `backend/core/config.py`

- [ ] **Step 1: Add config fields**

Add to the `Settings` class:

```python
    buttondown_api_key: str = ""
    weekly_email_enabled: bool = False
```

- [ ] **Step 2: Commit**

```bash
git add backend/core/config.py
git commit -m "feat(config): add Buttondown API key + weekly email toggle"
```

---

### Task 3: Weekly digest prompt

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (add at end)

- [ ] **Step 1: Write weekly prompt constants**

Add `WEEKLY_EXPERT_PROMPT` and `WEEKLY_LEARNER_PROMPT` at the end of the file. Each prompt:
- Takes the week's daily digest contents as input
- Outputs markdown with sections: "이번 주 한 줄", "이번 주 숫자" (3-5 key numbers), "TOP 뉴스" (7-10 items with daily digest links), "이번 주 트렌드 분석" (3-4 paragraphs), "주목할 포인트" (unresolved storylines), "그래서 나는?" (action items)
- Expert: decision-making perspective, concise, impact-focused
- Learner: learning perspective, friendly, background explanations
- Also outputs JSON fields: `headline` (one-liner), `week_numbers` (array of {value, label}), `week_tool` ({name, description, url})
- Language matches locale (EN prompt for EN output, KO for KO)

```python
WEEKLY_EXPERT_PROMPT = """You are the senior editor of an AI industry weekly newsletter.
Your reader is a tech lead or VP of Engineering who needs to stay current on AI developments for strategic decisions.

## Input
You will receive the full text of this week's daily AI digests (Monday-Friday, Research + Business).

## Output Structure (Markdown)
Write the weekly recap in {language}.

### Sections (in order)
1. **## 이번 주 한 줄** (ko) / **## This Week in One Line** (en)
   One punchy sentence summarizing the week's dominant theme.

2. **## 이번 주 숫자** (ko) / **## Week in Numbers** (en)
   3-5 key numbers from this week's news. Format:
   - **$2B** — OpenAI new funding round
   - **40%** — GPT-5 reasoning improvement
   Each number must come from the daily digests. Do not fabricate.

3. **## TOP 뉴스** (ko) / **## Top Stories** (en)
   7-10 most important stories ranked by impact. Each item:
   - **Bold title** — 2-3 sentence summary explaining WHY it matters for decision-makers
   Do NOT include source URLs. These are summaries of daily digest content.

4. **## 이번 주 트렌드 분석** (ko) / **## Trend Analysis** (en)
   3-4 paragraphs analyzing the week's flow. Connect dots between stories.
   Write from a decision-making perspective: "What does this mean for my team/company?"
   Structure: Monday developments -> how they evolved -> Friday state.

5. **## 주목할 포인트** (ko) / **## Watch Points** (en)
   2-3 unresolved storylines from this week's news.
   NOT predictions. Only observations grounded in this week's actual news.
   Format: bullet points with brief explanation of why it's worth watching.

6. **## 그래서 나는?** (ko) / **## So What Do I Do?** (en)
   3-5 concrete decision points or actions as bullet list.
   Format: `- **If [situation]**: [specific action] — because [reasoning from this week]`

## Also output this JSON block at the very end, fenced with ```json:
{{
  "headline": "one-line summary in {language}",
  "headline_en": "one-line summary in English (always)",
  "week_numbers": [
    {{"value": "$2B", "label": "OpenAI funding round"}},
    ...
  ],
  "week_tool": {{
    "name": "Tool Name",
    "description": "One sentence about what it does and why it's relevant this week",
    "url": "https://..."
  }}
}}

## Rules
- Every fact must come from the provided daily digests. Do not add outside knowledge.
- Write in {language} throughout (except headline_en which is always English).
- Do not repeat the same story across multiple sections.
- Week in Numbers: only numbers explicitly stated in the digests.
"""

WEEKLY_LEARNER_PROMPT = """You are the editor of a beginner-friendly AI weekly newsletter.
Your reader is a developer, PM, or student learning about AI who wants a clear weekly summary.

## Input
You will receive the full text of this week's daily AI digests (Monday-Friday, Research + Business).

## Output Structure (Markdown)
Write the weekly recap in {language}.

### Sections (in order)
1. **## 이번 주 한 줄** (ko) / **## This Week in One Line** (en)
   One friendly sentence summarizing what happened this week.

2. **## 이번 주 숫자** (ko) / **## Week in Numbers** (en)
   3-5 key numbers with brief context explaining what each means.
   Format:
   - **$2B** — OpenAI raised $2 billion in new funding (this is one of the largest AI funding rounds ever)

3. **## TOP 뉴스** (ko) / **## Top Stories** (en)
   7-10 stories ranked by importance. Each item:
   - **Bold title** — 2-3 sentence summary with background context for someone who may not follow AI daily
   Explain acronyms and jargon on first use.

4. **## 이번 주 트렌드 분석** (ko) / **## Trend Analysis** (en)
   3-4 paragraphs explaining the week's story arc in plain language.
   Write from a learning perspective: "What happened and why does it matter?"
   Help the reader understand the big picture, not just individual events.

5. **## 주목할 포인트** (ko) / **## Watch Points** (en)
   2-3 things to keep an eye on. Frame as: "If you see this keyword next week, here's the context."
   NOT predictions. Only based on actual news from this week.

6. **## 그래서 나는?** (ko) / **## So What Can I Do?** (en)
   3-5 concrete learning actions or things to try. Numbered list.
   Format: `1. **[Action]**: [what to do and why] — no source links`

## Also output this JSON block at the very end, fenced with ```json:
{{
  "headline": "one-line summary in {language}",
  "headline_en": "one-line summary in English (always)",
  "week_numbers": [
    {{"value": "$2B", "label": "OpenAI raised $2 billion in new funding"}},
    ...
  ],
  "week_tool": {{
    "name": "Tool Name",
    "description": "Beginner-friendly description of what it does and how to get started",
    "url": "https://..."
  }}
}}

## Rules
- Every fact must come from the provided daily digests. Do not add outside knowledge.
- Write in {language} throughout (except headline_en which is always English).
- Explain technical terms on first use.
- Week in Numbers: only numbers explicitly stated in the digests, with beginner-friendly context.
"""


def get_weekly_prompt(persona: str, language: str) -> str:
    """Get the system prompt for weekly recap generation.

    Args:
        persona: "expert" or "learner"
        language: "English" or "Korean"
    """
    template = WEEKLY_EXPERT_PROMPT if persona == "expert" else WEEKLY_LEARNER_PROMPT
    return template.replace("{language}", language)
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(prompts): add weekly recap prompts for expert/learner"
```

---

### Task 4: Weekly pipeline function

**Files:**
- Modify: `backend/services/pipeline.py` (add `run_weekly_pipeline` function)

- [ ] **Step 1: Add ISO week helper**

Add near the top of pipeline.py, after existing imports:

```python
def _iso_week_id(d: date | None = None) -> str:
    """Return ISO week string like '2026-W13'."""
    if d is None:
        d = datetime.strptime(today_kst(), "%Y-%m-%d").date()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"
```

- [ ] **Step 2: Add `_fetch_week_digests` helper**

Fetches Mon-Fri daily digests for a given ISO week from `news_posts`:

```python
async def _fetch_week_digests(
    supabase, week_id: str, locale: str,
) -> list[dict]:
    """Fetch daily digests for the given ISO week and locale."""
    # Parse week_id to get Monday-Sunday date range
    iso_year, iso_week = week_id.split("-W")
    monday = datetime.strptime(f"{iso_year}-W{int(iso_week)}-1", "%G-W%V-%u").date()
    sunday = monday + timedelta(days=6)

    result = supabase.table("news_posts").select(
        "slug, title, post_type, content_expert, content_learner, published_at, guide_items"
    ).eq("locale", locale) \
     .eq("category", "ai-news") \
     .in_("post_type", ["research", "business"]) \
     .gte("created_at", monday.isoformat()) \
     .lte("created_at", sunday.isoformat() + "T23:59:59") \
     .order("created_at", desc=False) \
     .execute()

    return result.data or []
```

- [ ] **Step 3: Add `_fetch_week_handbook_terms` helper**

```python
async def _fetch_week_handbook_terms(supabase, week_id: str, locale: str) -> list[dict]:
    """Fetch handbook terms created/published this week."""
    iso_year, iso_week = week_id.split("-W")
    monday = datetime.strptime(f"{iso_year}-W{int(iso_week)}-1", "%G-W%V-%u").date()
    sunday = monday + timedelta(days=6)

    result = supabase.table("handbook_terms").select(
        "slug, term, korean_term, definition_en, definition_ko"
    ).eq("status", "published") \
     .gte("created_at", monday.isoformat()) \
     .lte("created_at", sunday.isoformat() + "T23:59:59") \
     .limit(3) \
     .execute()

    return result.data or []
```

- [ ] **Step 4: Add main `run_weekly_pipeline` function**

```python
async def run_weekly_pipeline(
    week_id: str | None = None,
) -> PipelineResult:
    """Generate weekly recap from daily digests.

    Flow: fetch week's dailies -> LLM weekly summary (expert/learner x EN/KO) -> save draft.
    """
    if week_id is None:
        # Default: previous week (run on Sunday)
        last_week = datetime.strptime(today_kst(), "%Y-%m-%d").date() - timedelta(days=7)
        week_id = _iso_week_id(last_week)

    supabase = get_supabase()
    if not supabase:
        return PipelineResult(batch_id=week_id, errors=["Supabase not configured"])

    run_id = str(uuid.uuid4())
    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "run_key": f"weekly-{week_id}",
            "status": "running",
        }).execute()
    except Exception as e:
        logger.warning("Weekly run already exists for %s: %s", week_id, e)
        return PipelineResult(batch_id=week_id, status="skipped", message=f"Duplicate: {week_id}")

    all_errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}
    total_posts = 0

    try:
        from services.agents.prompts_news_pipeline import get_weekly_prompt

        for locale in ("en", "ko"):
            language = "English" if locale == "en" else "Korean"

            # Fetch daily digests
            digests = await _fetch_week_digests(supabase, week_id, locale)
            if not digests:
                all_errors.append(f"No daily digests found for {week_id} {locale}")
                continue

            # Build input text from dailies
            daily_text = ""
            for d in digests:
                daily_text += f"\n\n--- {d['post_type'].upper()} ({d.get('published_at', '')}) ---\n"
                daily_text += f"# {d['title']}\n"
                if d.get("content_expert"):
                    daily_text += f"\n## Expert\n{d['content_expert']}\n"
                if d.get("content_learner"):
                    daily_text += f"\n## Learner\n{d['content_learner']}\n"

            # Fetch handbook terms for bottom card
            week_terms = await _fetch_week_handbook_terms(supabase, week_id, locale)

            # Generate per persona
            personas: dict[str, dict] = {}  # {persona: {content, json_data}}
            client = get_openai_client()

            for persona in ("expert", "learner"):
                t_p = time.monotonic()
                system_prompt = get_weekly_prompt(persona, language)

                try:
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=settings.openai_model_main,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": daily_text},
                            ],
                            temperature=0.5,
                            max_tokens=6000,
                        ),
                        timeout=120,
                    )

                    raw = response.choices[0].message.content or ""
                    usage = extract_usage_metrics(response)
                    merge_usage_metrics(cumulative_usage, usage)

                    # Parse JSON block from end of response
                    json_data = {}
                    if "```json" in raw:
                        json_str = raw.split("```json")[-1].split("```")[0].strip()
                        json_data = parse_ai_json(json_str, f"weekly-{persona}-{locale}")
                        # Remove JSON block from markdown content
                        content = raw[:raw.rfind("```json")].strip()
                    else:
                        content = raw

                    personas[persona] = {"content": content, "json_data": json_data}

                    _log_stage(
                        supabase, run_id, f"weekly:{persona}:{locale}", "success", t_p,
                        usage=usage, post_type="weekly",
                    )

                except Exception as e:
                    logger.warning("Weekly %s %s %s failed: %s", week_id, persona, locale, e)
                    all_errors.append(f"weekly {persona} {locale}: {e}")
                    _log_stage(
                        supabase, run_id, f"weekly:{persona}:{locale}", "failed", t_p,
                        error_message=str(e), post_type="weekly",
                    )

            if not personas:
                continue

            # Build row
            expert_data = personas.get("expert", {})
            learner_data = personas.get("learner", {})
            expert_json = expert_data.get("json_data", {})
            learner_json = learner_data.get("json_data", {})

            headline = expert_json.get("headline") or learner_json.get("headline") or f"AI Weekly — {week_id}"
            headline_en = expert_json.get("headline_en") or headline

            slug = f"{week_id.lower()}-weekly-digest" if locale == "en" else f"{week_id.lower()}-weekly-digest-ko"

            # Reading time
            text = expert_data.get("content", "") or learner_data.get("content", "")
            if locale == "ko":
                char_count = len([c for c in text if c.strip() and c not in '.,!?;:()[]{}"\'-—...#*_~`|/>'])
                reading_time = max(1, round(char_count / 500))
            else:
                reading_time = max(1, round(len(text.split()) / 200))

            guide_items = {
                "week_numbers": expert_json.get("week_numbers", []),
                "week_tool": expert_json.get("week_tool") or learner_json.get("week_tool", {}),
                "week_terms": [
                    {
                        "slug": t["slug"],
                        "term": t.get("term") or t.get("korean_term", ""),
                        "definition": t.get(f"definition_{locale}", ""),
                    }
                    for t in week_terms[:2]
                ],
            }

            row = {
                "title": headline,
                "slug": slug,
                "locale": locale,
                "category": "ai-news",
                "post_type": "weekly",
                "status": "draft",
                "content_expert": expert_data.get("content", ""),
                "content_learner": learner_data.get("content", ""),
                "pipeline_batch_id": week_id,
                "reading_time_min": reading_time,
                "guide_items": guide_items,
            }

            try:
                supabase.table("news_posts").upsert(
                    row, on_conflict="slug,locale"
                ).execute()
                total_posts += 1
                logger.info("Saved weekly %s draft: %s", locale, slug)
            except Exception as e:
                all_errors.append(f"Save weekly {locale}: {e}")

        # Buttondown email (disabled by default)
        if settings.weekly_email_enabled and total_posts > 0:
            try:
                await _send_weekly_email(supabase, week_id)
            except Exception as e:
                logger.warning("Weekly email failed: %s", e)
                all_errors.append(f"Email: {e}")

        status = "success" if total_posts > 0 and not all_errors else "partial" if total_posts > 0 else "failed"
        supabase.table("pipeline_runs").update({
            "status": status,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "summary": {"total_posts": total_posts, "errors": all_errors},
        }).eq("id", run_id).execute()

        return PipelineResult(
            batch_id=week_id,
            status=status,
            total_posts=total_posts,
            errors=all_errors,
            usage=cumulative_usage,
        )

    except Exception as e:
        logger.error("Weekly pipeline failed: %s", e, exc_info=True)
        supabase.table("pipeline_runs").update({
            "status": "failed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "summary": {"error": str(e)},
        }).eq("id", run_id).execute()
        return PipelineResult(batch_id=week_id, status="failed", errors=[str(e)])
```

- [ ] **Step 5: Add `_send_weekly_email` stub**

```python
async def _send_weekly_email(supabase, week_id: str) -> None:
    """Send weekly recap via Buttondown API. Disabled by default."""
    import httpx

    if not settings.buttondown_api_key:
        logger.info("Buttondown API key not set, skipping email")
        return

    # Fetch the saved weekly post (EN version for email)
    slug = f"{week_id.lower()}-weekly-digest"
    result = supabase.table("news_posts").select("title, content_expert") \
        .eq("slug", slug).eq("locale", "en").single().execute()

    if not result.data:
        logger.warning("No weekly post found for email: %s", slug)
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.buttondown.com/v1/emails",
            headers={"Authorization": f"Token {settings.buttondown_api_key}"},
            json={
                "subject": result.data["title"],
                "body": result.data["content_expert"],
                "status": "draft",  # Always draft — Amy sends manually
            },
        )
        resp.raise_for_status()
        logger.info("Weekly email draft created in Buttondown for %s", week_id)
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/pipeline.py
git commit -m "feat(pipeline): add run_weekly_pipeline with Buttondown stub"
```

---

### Task 5: Cron endpoint + admin trigger

**Files:**
- Modify: `backend/routers/cron.py`

- [ ] **Step 1: Add weekly trigger endpoint**

```python
@router.post("/weekly", status_code=202)
async def trigger_weekly_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    body: dict | None = None,
    _secret=Depends(verify_cron_secret),
):
    """Trigger weekly recap generation. Returns 202 immediately."""
    week_id = (body or {}).get("week_id")

    async def _run():
        from services.pipeline import run_weekly_pipeline
        result = await run_weekly_pipeline(week_id=week_id)
        logger.info("Weekly pipeline result: %s", result)

    background_tasks.add_task(_run)
    return {"status": "accepted", "week_id": week_id or "auto (previous week)"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/routers/cron.py
git commit -m "feat(cron): add /cron/weekly endpoint for weekly recap"
```

---

## Chunk 2: Frontend

### Task 6: News list — add Weekly tab

**Files:**
- Modify: `frontend/src/pages/ko/news/index.astro`
- Modify: `frontend/src/pages/en/news/index.astro`

- [ ] **Step 1: Add 'weekly' to postTypeItems**

In both locale files, update the `postTypeItems` array:

```typescript
// ko/news/index.astro
const postTypeItems = [
  { value: 'business', label: getPostTypeLabel('ko', 'business') },
  { value: 'research', label: getPostTypeLabel('ko', 'research') },
  { value: 'weekly', label: 'Weekly Recap' },
];

// en/news/index.astro
const postTypeItems = [
  { value: 'business', label: getPostTypeLabel('en', 'business') },
  { value: 'research', label: getPostTypeLabel('en', 'research') },
  { value: 'weekly', label: 'Weekly Recap' },
];
```

- [ ] **Step 2: Update headline selection to exclude weekly**

The headline card uses `posts.find(p => p.post_type === 'business')`. Weekly posts should not be the headline:

```typescript
const headline = posts.find(p => p.post_type === 'business' && p.post_type !== 'weekly') ?? null;
```

- [ ] **Step 3: Add Weekly Recap badge to NewsprintListCard**

In `NewsprintListCard.astro`, add a "Weekly Recap" badge when `postType === 'weekly'`:

Check existing component for `postType` prop and add badge rendering.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ko/news/index.astro frontend/src/pages/en/news/index.astro frontend/src/components/newsprint/NewsprintListCard.astro
git commit -m "feat(frontend): add Weekly tab to news list + badge"
```

---

### Task 7: News detail — bottom cards (term + tool)

**Files:**
- Modify: `frontend/src/pages/ko/news/[slug].astro` (and en equivalent)
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts`

- [ ] **Step 1: Parse guide_items for weekly cards in newsDetailPage.ts**

In the page data function, extract `week_terms`, `week_tool`, `week_numbers` from `guide_items` when `post_type === 'weekly'`.

- [ ] **Step 2: Render bottom cards in news detail page**

After the article content, conditionally render:

```html
{post.post_type === 'weekly' && (
  <div class="weekly-bottom-cards">
    {weekTerms.length > 0 && (
      <div class="weekly-card">
        <h3>이번 주 용어</h3>
        {weekTerms.map(t => (
          <a href={`/${locale}/handbook/${t.slug}/`}>
            <strong>{t.term}</strong> — {t.definition}
          </a>
        ))}
      </div>
    )}
    {weekTool?.name && (
      <div class="weekly-card">
        <h3>이번 주 도구</h3>
        <a href={weekTool.url} target="_blank" rel="noopener">
          <strong>{weekTool.name}</strong> — {weekTool.description}
        </a>
      </div>
    )}
  </div>
)}
```

- [ ] **Step 3: Add CSS for bottom cards**

```css
.weekly-bottom-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
}
.weekly-card {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.weekly-card h3 {
  font-family: var(--font-heading);
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
  margin-bottom: var(--space-2);
}
@media (max-width: 640px) {
  .weekly-bottom-cards { grid-template-columns: 1fr; }
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ko/news/[slug].astro frontend/src/pages/en/news/[slug].astro frontend/src/lib/pageData/newsDetailPage.ts frontend/src/styles/global.css
git commit -m "feat(frontend): weekly recap bottom cards (term + tool)"
```

---

### Task 8: Admin — "Generate Weekly" button

**Files:**
- Modify: `frontend/src/pages/admin/analytics.astro` (or pipeline admin page)

- [ ] **Step 1: Add Generate Weekly button**

Add a button next to the existing pipeline trigger that calls the weekly endpoint:

```html
<button id="btn-generate-weekly" class="admin-btn admin-btn-secondary">
  Generate Weekly Recap
</button>
```

- [ ] **Step 2: Add JS handler**

```javascript
const btnWeekly = document.getElementById('btn-generate-weekly');
btnWeekly?.addEventListener('click', async () => {
  if (!confirm('Generate weekly recap for last week?')) return;
  btnWeekly.disabled = true;
  btnWeekly.textContent = 'Generating...';
  try {
    const res = await fetch('/api/admin/trigger-weekly', { method: 'POST' });
    const data = await res.json();
    alert(data.status === 'accepted' ? 'Weekly pipeline started!' : 'Failed: ' + JSON.stringify(data));
  } finally {
    btnWeekly.disabled = false;
    btnWeekly.textContent = 'Generate Weekly Recap';
  }
});
```

- [ ] **Step 3: Add admin API route for weekly trigger**

Create `frontend/src/pages/api/admin/trigger-weekly.ts`:

```typescript
import type { APIRoute } from 'astro';

export const POST: APIRoute = async ({ locals }) => {
  const BACKEND = import.meta.env.FASTAPI_URL || 'https://api.0to1log.com';
  const secret = import.meta.env.CRON_SECRET;

  const res = await fetch(`${BACKEND}/cron/weekly`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-cron-secret': secret,
    },
  });

  const data = await res.json();
  return new Response(JSON.stringify(data), { status: res.status });
};
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/admin/analytics.astro frontend/src/pages/api/admin/trigger-weekly.ts
git commit -m "feat(admin): add Generate Weekly Recap button + API route"
```

---

## Chunk 3: Verification + Push

### Task 9: Build verification

- [ ] **Step 1: Backend lint**

```bash
cd backend && source .venv/Scripts/activate && python -m ruff check services/pipeline.py services/agents/prompts_news_pipeline.py routers/cron.py
```

- [ ] **Step 2: Frontend build**

```bash
cd frontend && npm run build
```

Fix any type errors.

- [ ] **Step 3: Final commit + push**

```bash
git push origin main
```

---

### Task 10: E2E test — manual weekly generation

- [ ] **Step 1: Trigger weekly pipeline from admin**

Click "Generate Weekly Recap" in admin, or:

```bash
curl -X POST https://api.0to1log.com/cron/weekly \
  -H "x-cron-secret: $CRON_SECRET" \
  -H "Content-Type: application/json"
```

- [ ] **Step 2: Verify draft created**

Check admin news list for weekly post. Verify:
- post_type = 'weekly'
- content_expert and content_learner both populated
- guide_items contains week_numbers, week_tool, week_terms

- [ ] **Step 3: Verify frontend Weekly tab**

Navigate to `/ko/news/` and click "Weekly Recap" tab. Verify the weekly post appears with badge.

- [ ] **Step 4: Verify bottom cards on detail page**

Click into the weekly post. Verify:
- Term card shows with handbook link
- Tool card shows with external link
- "Week in Numbers" section renders in content
