# Handbook Save Path + Frontend Render Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 재설계된 Basic 섹션 구조(hero card + references footer + sidebar checklist)가 실제로 DB에 저장되고 public 핸드북 페이지에 렌더링되도록 저장 경로와 프론트엔드를 확장한다.

**Architecture:** (1) `handbook_terms` 테이블에 6개 컬럼 추가 (`hero_news_context_ko/en`, `references_ko/en` jsonb, `sidebar_checklist_ko/en`), (2) admin save API(`frontend/src/pages/api/admin/handbook/save.ts`)가 신규 필드를 통과시키고, (3) `getHandbookDetailPageData()`가 조회에 포함시키고, (4) `[slug].astro`가 Hero Card · References Footer · Understanding Checklist 3개 블록을 렌더링. Level switcher는 body만 교체, 새 블록은 항상 표시.

**Tech Stack:** Supabase Postgres (JSONB), Astro v5 SSR, TypeScript, Tailwind v4

**Commit:** `70a0e77` (KO redesign) + Plan B completion 이후 작업. Plan B가 선행이면 EN 필드도 함께 렌더 가능.

---

## Context for the implementer

1. **재설계된 Basic 섹션 구조는 이미 백엔드 생성 경로에 완비돼 있지만, 현재 DB에는 저장되지 않는다.** `_assemble_all_sections` ([advisor.py:1150-1198](backend/services/agents/advisor.py#L1150-L1198))가 데이터 dict에 `hero_news_context_ko` 등을 pass-through로 내려주지만, `handbook_terms` 테이블에 해당 컬럼이 없어서 저장 시점에 drop된다.
2. **Frontend detail 페이지는 이미 `HandbookSideRail` 사이드바 + `<p class="handbook-definition">` 영역을 갖고 있다.** Hero card는 definition 블록 바로 아래에 삽입하고, References footer는 본문 아래에, Understanding checklist는 사이드바에 추가한다. Level switcher는 현재 `prose.innerHTML = map[level]`로 body만 교체하므로 신규 3개 블록은 건드리지 않아야 한다.
3. **Admin editor(`/admin/handbook/edit/[slug]`)는 이번 plan에서 수정하지 않는다.** Admin은 당분간 AI Generate 결과를 **직접 저장 경로를 통해** 반영하고, 수동 편집 UI는 후속 작업. 이번 plan의 scope는 "save API + public render"만.

**Read before starting:**
- [`supabase/migrations/00012_handbook_difficulty_levels.sql`](supabase/migrations/00012_handbook_difficulty_levels.sql), [`00019_handbook_term_names.sql`](supabase/migrations/00019_handbook_term_names.sql) — 기존 handbook_terms 스키마 참고
- [`frontend/src/pages/api/admin/handbook/save.ts`](frontend/src/pages/api/admin/handbook/save.ts) — save endpoint 전체 (전체 122줄)
- [`frontend/src/lib/pageData/handbookDetailPage.ts`](frontend/src/lib/pageData/handbookDetailPage.ts) — detail page data loader
- [`frontend/src/pages/ko/handbook/[slug].astro`](frontend/src/pages/ko/handbook/%5Bslug%5D.astro) — detail page template
- [`frontend/src/components/newsprint/HandbookSideRail.astro`](frontend/src/components/newsprint/HandbookSideRail.astro) — 사이드바
- [`vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md`](vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md) — §4 레이아웃, §11 렌더링 계약
- [`backend/services/agents/advisor.py:1150-1198`](backend/services/agents/advisor.py#L1150-L1198) — pass-through logic

**Dependencies:**
- Supabase MCP available for migration apply.
- `frontend/` dev server: `cd frontend && npm run dev`
- Build verify: `cd frontend && npm run build` (must pass with 0 errors per frontend/CLAUDE.md)

---

### Task 1: DB migration — 6 new columns

**Files:**
- Create: `supabase/migrations/00048_handbook_redesign_columns.sql`

**Step 1: Write migration SQL**

Create `supabase/migrations/00048_handbook_redesign_columns.sql`:

```sql
-- Handbook Basic section redesign (2026-04-10)
-- Adds level-independent fields for hero card, references footer, and sidebar checklist.
-- Related plan: vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md

ALTER TABLE handbook_terms
  ADD COLUMN IF NOT EXISTS hero_news_context_ko text,
  ADD COLUMN IF NOT EXISTS hero_news_context_en text,
  ADD COLUMN IF NOT EXISTS references_ko jsonb,
  ADD COLUMN IF NOT EXISTS references_en jsonb,
  ADD COLUMN IF NOT EXISTS sidebar_checklist_ko text,
  ADD COLUMN IF NOT EXISTS sidebar_checklist_en text;

-- No RLS changes — existing handbook_terms policies already cover all columns.

COMMENT ON COLUMN handbook_terms.hero_news_context_ko IS
  'Hero card: 3-line news quote block shown above Basic/Advanced level switcher';
COMMENT ON COLUMN handbook_terms.references_ko IS
  'References footer: JSON array of {title, authors, year, venue, type, url, tier, annotation}';
COMMENT ON COLUMN handbook_terms.sidebar_checklist_ko IS
  'Sidebar understanding-check block shown in right rail during Basic view';
```

**Step 2: Apply migration via Supabase MCP**

Use `mcp__claude_ai_Supabase__apply_migration` with:
- project_id: `luwipptjfyjsleqouasj`
- name: `handbook_redesign_columns`
- query: (the SQL above)

**Step 3: Verify columns exist**

Use `mcp__claude_ai_Supabase__execute_sql` with:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'handbook_terms'
  AND column_name IN (
    'hero_news_context_ko','hero_news_context_en',
    'references_ko','references_en',
    'sidebar_checklist_ko','sidebar_checklist_en'
  )
ORDER BY column_name;
```
Expected: 6 rows returned, jsonb type for `references_*`, text type for others.

**Step 4: Commit**

```bash
git add supabase/migrations/00048_handbook_redesign_columns.sql
git commit -m "feat(db): handbook_terms 재설계 컬럼 추가 — hero/references/checklist"
```

---

### Task 2: Admin save endpoint — accept new fields

**Files:**
- Modify: `frontend/src/pages/api/admin/handbook/save.ts`

**Step 1: Read current save.ts**

Already read above. Note the `row` object construction at line 58-74.

**Step 2: Extend the destructuring + row object**

Replace the destructuring block (lines 32-48) with:
```ts
const {
  id,
  term,
  term_full,
  slug,
  korean_name,
  korean_full,
  categories,
  related_term_slugs,
  is_favourite,
  definition_ko,
  body_basic_ko,
  body_advanced_ko,
  definition_en,
  body_basic_en,
  body_advanced_en,
  // Level-independent fields (2026-04-10 redesign)
  hero_news_context_ko,
  hero_news_context_en,
  references_ko,
  references_en,
  sidebar_checklist_ko,
  sidebar_checklist_en,
  source,
} = body;
```

Replace the `row` object (lines 58-74) with:
```ts
const row = {
  term,
  term_full: term_full || null,
  slug: finalSlug,
  korean_name: korean_name || null,
  korean_full: korean_full || null,
  categories: normalizeTags(Array.isArray(categories) ? categories : (categories ? [categories] : []), 4),
  related_term_slugs: related_term_slugs || [],
  is_favourite: is_favourite ?? false,
  definition_ko: definition_ko || null,
  body_basic_ko: body_basic_ko || null,
  body_advanced_ko: body_advanced_ko || null,
  definition_en: definition_en || null,
  body_basic_en: body_basic_en || null,
  body_advanced_en: body_advanced_en || null,
  // Level-independent fields
  hero_news_context_ko: hero_news_context_ko || null,
  hero_news_context_en: hero_news_context_en || null,
  references_ko: Array.isArray(references_ko) ? references_ko : null,
  references_en: Array.isArray(references_en) ? references_en : null,
  sidebar_checklist_ko: sidebar_checklist_ko || null,
  sidebar_checklist_en: sidebar_checklist_en || null,
  updated_at: new Date().toISOString(),
};
```

**Step 3: Run frontend type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No new errors introduced by this file.

**Step 4: Smoke-test the endpoint**

Start frontend dev server: `cd frontend && npm run dev`
In a separate shell, POST a test payload with curl:
```bash
curl -X POST http://localhost:4321/api/admin/handbook/save \
  -H "Content-Type: application/json" \
  -H "Cookie: <copy-from-browser-authenticated-session>" \
  -d '{
    "term": "Test Term Redesign",
    "slug": "test-term-redesign",
    "hero_news_context_ko": "\"test quote\" → meaning",
    "references_ko": [{"title":"t","type":"paper","url":"https://x","tier":"primary","annotation":"a"}],
    "sidebar_checklist_ko": "□ q1\n\n□ q2"
  }'
```
Expected: 201 Created (insert path), returned JSON contains the new fields.

**Alternative** if no browser session handy: use Supabase MCP to manually insert a test row and confirm columns persist. Then delete it.

**Step 5: Clean up test row**

Run via Supabase MCP: `DELETE FROM handbook_terms WHERE slug = 'test-term-redesign';`

**Step 6: Commit**

```bash
git add frontend/src/pages/api/admin/handbook/save.ts
git commit -m "feat(admin): handbook save endpoint — 신규 redesign 필드 통과"
```

---

### Task 3: Detail page data loader — include new fields

**Files:**
- Modify: `frontend/src/lib/pageData/handbookDetailPage.ts`

**Step 1: Read the current loader**

Run: `Read frontend/src/lib/pageData/handbookDetailPage.ts`

Find the Supabase `.select()` call that fetches the term. Currently it likely uses `*` or an explicit column list.

**Step 2: Identify where the term is fetched**

Look for a pattern like:
```ts
const { data: term } = await supabase
  .from('handbook_terms')
  .select('*')  // or explicit columns
  .eq('slug', slug)
  .single();
```

**Step 3: Add new fields to the return type**

Find the return interface/type and add:
```ts
interface HandbookDetailData {
  // ... existing fields
  heroNewsContext?: string | null;   // localized by locale
  references?: ReferenceItem[] | null;
  sidebarChecklist?: string | null;
}

interface ReferenceItem {
  title: string;
  authors?: string;
  year?: number;
  venue?: string;
  type: 'paper' | 'docs' | 'code' | 'blog' | 'wiki' | 'book';
  url: string;
  tier: 'primary' | 'secondary';
  annotation: string;
}
```

Place these next to the existing types in the file.

**Step 4: Localize the new fields**

Similar to how `definition` and `body_basic/advanced` are localized with `localField()`, add:
```ts
const heroNewsContext = localField(term, 'hero_news_context', locale) || null;
const references = locale === 'ko' ? term.references_ko : term.references_en;
const sidebarChecklist = localField(term, 'sidebar_checklist', locale) || null;
```

Check if `localField()` supports `jsonb` — it probably only handles text. For `references`, use direct property access as shown above, with fallback to the other locale if empty:
```ts
const references =
  (locale === 'ko' ? term.references_ko : term.references_en) ??
  (locale === 'ko' ? term.references_en : term.references_ko) ??
  null;
```

**Step 5: Include in the returned object**

Add to the return object:
```ts
return {
  // ... existing fields
  heroNewsContext,
  references,
  sidebarChecklist,
  // ...
};
```

**Step 6: Verify type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

**Step 7: Commit**

```bash
git add frontend/src/lib/pageData/handbookDetailPage.ts
git commit -m "feat(handbook): detail page loader — hero/references/checklist 필드 조회"
```

---

### Task 4: Hero Card component

**Files:**
- Create: `frontend/src/components/newsprint/HandbookHeroCard.astro`
- Reference: `frontend/src/styles/global.css` (for theme tokens)

**Step 1: Create HandbookHeroCard.astro**

```astro
---
interface Props {
  definition: string | null;
  newsContext: string | null;   // raw string with \n-separated lines
  backUrl?: string;
  locale: 'ko' | 'en';
}

const { definition, newsContext, backUrl, locale } = Astro.props;

// Parse news context into lines (defensive: may be empty or malformed)
const lines = (newsContext || '')
  .split('\n')
  .map(l => l.trim())
  .filter(Boolean)
  .slice(0, 3);

const hasContext = lines.length > 0;
const backLabel = locale === 'ko' ? '원래 기사로 돌아가기' : 'Back to article';
---

{(definition || hasContext) && (
  <aside class="handbook-hero-card" aria-label={locale === 'ko' ? '핵심 요약' : 'Key summary'}>
    {definition && (
      <p class="handbook-hero-card__definition" set:html={definition.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')} />
    )}
    {hasContext && (
      <>
        <h2 class="handbook-hero-card__heading">
          {locale === 'ko' ? '뉴스에서 이렇게 쓰여' : 'As seen in the news'}
        </h2>
        <ul class="handbook-hero-card__news-list">
          {lines.map(line => (
            <li class="handbook-hero-card__news-line">{line}</li>
          ))}
        </ul>
      </>
    )}
    {backUrl && (
      <a href={backUrl} class="handbook-hero-card__back">{backLabel}</a>
    )}
  </aside>
)}

<style>
  .handbook-hero-card {
    border: 1px solid var(--color-border);
    background: var(--color-surface-subtle);
    padding: 1rem 1.25rem;
    margin: 1rem 0 1.5rem;
    border-radius: 6px;
  }
  .handbook-hero-card__definition {
    font-size: 1rem;
    line-height: 1.55;
    margin: 0 0 0.75rem;
    color: var(--color-text);
  }
  .handbook-hero-card__heading {
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--color-text-muted);
    margin: 0.75rem 0 0.5rem;
    font-weight: 600;
  }
  .handbook-hero-card__news-list {
    list-style: none;
    padding: 0;
    margin: 0 0 0.75rem;
  }
  .handbook-hero-card__news-line {
    font-size: 0.875rem;
    line-height: 1.5;
    color: var(--color-text);
    padding: 0.25rem 0;
    border-bottom: 1px dashed var(--color-border-subtle);
  }
  .handbook-hero-card__news-line:last-child {
    border-bottom: none;
  }
  .handbook-hero-card__back {
    display: inline-block;
    font-size: 0.8125rem;
    color: var(--color-text-muted);
    text-decoration: none;
    border-bottom: 1px solid currentColor;
  }
  .handbook-hero-card__back:hover {
    color: var(--color-text);
  }
</style>
```

**Step 2: Confirm theme tokens exist**

Run: `grep -n "color-surface-subtle\|color-border-subtle" frontend/src/styles/global.css`
If `color-border-subtle` doesn't exist, change the CSS to use `color-border` with `opacity: 0.5` instead.

**Step 3: Run build to catch Astro syntax errors**

Run: `cd frontend && npm run build 2>&1 | tail -30`
Expected: Build succeeds (but the component isn't imported yet, so it just needs to be syntactically valid).

**Step 4: Commit**

```bash
git add frontend/src/components/newsprint/HandbookHeroCard.astro
git commit -m "feat(handbook): HandbookHeroCard 컴포넌트 — definition + 뉴스 3줄"
```

---

### Task 5: References Footer component

**Files:**
- Create: `frontend/src/components/newsprint/HandbookReferences.astro`

**Step 1: Create component**

```astro
---
interface ReferenceItem {
  title: string;
  authors?: string;
  year?: number;
  venue?: string;
  type: 'paper' | 'docs' | 'code' | 'blog' | 'wiki' | 'book';
  url: string;
  tier: 'primary' | 'secondary';
  annotation: string;
}

interface Props {
  references: ReferenceItem[] | null | undefined;
  locale: 'ko' | 'en';
}

const { references, locale } = Astro.props;
const heading = locale === 'ko' ? '참고 자료' : 'References';

// Sort: primary first, then by type rank (paper > docs > code > book > wiki > blog)
const typeRank: Record<ReferenceItem['type'], number> = {
  paper: 0, docs: 1, code: 2, book: 3, wiki: 4, blog: 5,
};
const sorted = [...(references || [])].sort((a, b) => {
  if (a.tier !== b.tier) return a.tier === 'primary' ? -1 : 1;
  return (typeRank[a.type] ?? 99) - (typeRank[b.type] ?? 99);
});

const typeLabel: Record<ReferenceItem['type'], string> = {
  paper: locale === 'ko' ? '논문' : 'Paper',
  docs: locale === 'ko' ? '공식 문서' : 'Docs',
  code: locale === 'ko' ? '코드' : 'Code',
  blog: locale === 'ko' ? '블로그' : 'Blog',
  wiki: 'Wiki',
  book: locale === 'ko' ? '도서' : 'Book',
};
---

{sorted.length > 0 && (
  <section class="handbook-references" aria-label={heading}>
    <h2 class="handbook-references__heading">{heading}</h2>
    <ul class="handbook-references__list">
      {sorted.map(ref => (
        <li class={`handbook-references__item handbook-references__item--${ref.tier}`}>
          <div class="handbook-references__meta">
            <span class={`handbook-references__tier handbook-references__tier--${ref.tier}`}>
              {ref.tier === 'primary' ? '★' : '·'}
            </span>
            <span class="handbook-references__type">{typeLabel[ref.type]}</span>
            {ref.year && <span class="handbook-references__year">{ref.year}</span>}
          </div>
          <a href={ref.url} target="_blank" rel="noopener noreferrer" class="handbook-references__link">
            {ref.title}
          </a>
          {ref.authors && <span class="handbook-references__authors">{ref.authors}</span>}
          {ref.venue && <span class="handbook-references__venue">{ref.venue}</span>}
          {ref.annotation && (
            <p class="handbook-references__annotation">{ref.annotation}</p>
          )}
        </li>
      ))}
    </ul>
  </section>
)}

<style>
  .handbook-references {
    margin: 2rem 0 1rem;
    padding: 1rem 0 0;
    border-top: 1px solid var(--color-border);
  }
  .handbook-references__heading {
    font-size: 0.875rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--color-text-muted);
    margin: 0 0 0.75rem;
    font-weight: 600;
  }
  .handbook-references__list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .handbook-references__item {
    padding: 0.5rem 0;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  .handbook-references__item + .handbook-references__item {
    border-top: 1px dashed var(--color-border);
  }
  .handbook-references__item--primary {
    font-weight: 500;
  }
  .handbook-references__meta {
    display: inline-flex;
    gap: 0.5rem;
    color: var(--color-text-muted);
    font-size: 0.75rem;
    margin-right: 0.5rem;
  }
  .handbook-references__tier--primary {
    color: var(--color-accent, inherit);
  }
  .handbook-references__link {
    color: var(--color-text);
    text-decoration: underline;
    text-decoration-color: var(--color-border);
  }
  .handbook-references__link:hover {
    text-decoration-color: currentColor;
  }
  .handbook-references__authors,
  .handbook-references__venue {
    display: block;
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin-top: 0.125rem;
  }
  .handbook-references__annotation {
    font-size: 0.8125rem;
    color: var(--color-text-muted);
    margin: 0.25rem 0 0;
    line-height: 1.5;
  }
</style>
```

**Step 2: Build verify**

Run: `cd frontend && npm run build 2>&1 | tail -30`
Expected: No new errors.

**Step 3: Commit**

```bash
git add frontend/src/components/newsprint/HandbookReferences.astro
git commit -m "feat(handbook): HandbookReferences 컴포넌트 — primary/secondary tier 정렬"
```

---

### Task 6: Understanding Checklist component

**Files:**
- Create: `frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro`

**Step 1: Create component**

```astro
---
interface Props {
  checklist: string | null | undefined;
  locale: 'ko' | 'en';
}

const { checklist, locale } = Astro.props;
const heading = locale === 'ko' ? '이해 체크리스트' : 'Understanding check';

// Parse lines prefixed with □ or [ ]
const items = (checklist || '')
  .split('\n')
  .map(l => l.trim())
  .filter(Boolean)
  .map(l => l.replace(/^(\u25a1|\[\s*\])\s*/, ''))
  .filter(Boolean);
---

{items.length > 0 && (
  <section class="handbook-checklist" aria-label={heading}>
    <h3 class="handbook-checklist__heading">{heading}</h3>
    <ul class="handbook-checklist__list">
      {items.map(item => (
        <li class="handbook-checklist__item">
          <span class="handbook-checklist__marker" aria-hidden="true">□</span>
          <span class="handbook-checklist__text">{item}</span>
        </li>
      ))}
    </ul>
  </section>
)}

<style>
  .handbook-checklist {
    padding: 0.875rem;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    background: var(--color-surface-subtle);
    margin-top: 1rem;
  }
  .handbook-checklist__heading {
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--color-text-muted);
    margin: 0 0 0.625rem;
    font-weight: 600;
  }
  .handbook-checklist__list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .handbook-checklist__item {
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
    padding: 0.375rem 0;
    font-size: 0.8125rem;
    line-height: 1.45;
  }
  .handbook-checklist__marker {
    flex-shrink: 0;
    color: var(--color-text-muted);
    font-size: 1rem;
    line-height: 1;
  }
  .handbook-checklist__text {
    color: var(--color-text);
  }
</style>
```

**Step 2: Build verify + commit**

Run: `cd frontend && npm run build 2>&1 | tail -30`
Then:
```bash
git add frontend/src/components/newsprint/HandbookUnderstandingChecklist.astro
git commit -m "feat(handbook): HandbookUnderstandingChecklist 컴포넌트 — Basic 뷰 사이드바"
```

---

### Task 7: Wire Hero Card + References into [slug].astro (KO)

**Files:**
- Modify: `frontend/src/pages/ko/handbook/[slug].astro`

**Step 1: Import new components + extend page data destructuring**

Near the top imports (around line 11), add:
```astro
import HandbookHeroCard from '../../../components/newsprint/HandbookHeroCard.astro';
import HandbookReferences from '../../../components/newsprint/HandbookReferences.astro';
import HandbookUnderstandingChecklist from '../../../components/newsprint/HandbookUnderstandingChecklist.astro';
```

Find the `getHandbookDetailPageData` destructuring (around line 24-45) and add:
```astro
const {
  term,
  termError,
  definition,
  levelHtmlMap,
  activeLevel,
  htmlContent,
  showLevelSwitcher,
  relatedArticles,
  relatedTerms,
  sameCategoryTerms,
  handbookTermsJson,
  isBookmarked,
  learningStatus,
  learningProgressId,
  heroNewsContext,     // NEW
  references,          // NEW
  sidebarChecklist,    // NEW
} = await getHandbookDetailPageData({ ... });
```

**Step 2: Insert Hero Card right after `<p class="handbook-definition">`**

Find the block around [slug].astro:121-123 that renders the definition:
```astro
{definition && (
  <p class="handbook-definition" set:html={definition.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')} />
)}
```

Replace with:
```astro
<HandbookHeroCard
  definition={definition}
  newsContext={heroNewsContext}
  locale={locale}
/>
```

Note: the hero card component already handles rendering the definition internally, so the old `<p class="handbook-definition">` becomes redundant. Remove it (or keep only if there's no hero content — the component already handles empty state).

**Step 3: Insert References footer after `<Fragment set:html={htmlContent} />`**

Find the body render block around [slug].astro:176-180:
```astro
{htmlContent && (
  <div class="newsprint-prose newsprint-prose--no-dropcap" id="handbook-body">
    <Fragment set:html={htmlContent} />
  </div>
)}
```

Directly after the closing `</div>`, add:
```astro
<HandbookReferences references={references} locale={locale} />
```

**Step 4: Insert Understanding Checklist into HandbookSideRail slot**

Find the `<Fragment slot="rail">` block around [slug].astro:223-253. Inside the existing rail content (after `<HandbookSideRail ... />`), add:
```astro
{activeLevel === 'basic' && (
  <HandbookUnderstandingChecklist checklist={sidebarChecklist} locale={locale} />
)}
```

**Important:** `activeLevel` is a server-side value, meaning it only matches the initial level. When the user toggles to Advanced, the JS switcher doesn't currently hide the sidebar checklist. You have two options:
- (a) **Server-only**: render only when initial load is Basic. Toggling Advanced leaves the checklist visible until page reload. Simplest.
- (b) **JS toggle**: extend the level switcher JS to also hide/show `.handbook-checklist` on level change.

**Choose (b)** — extend the level switcher in the existing `initLevelSwitcher` script ([slug].astro:369-424). In the `setActiveLevel(level)` function, after the `prose.innerHTML = map[level]` line, add:
```typescript
// Hide/show sidebar understanding checklist based on level
const checklistEl = document.querySelector<HTMLElement>('.handbook-checklist');
if (checklistEl) {
  checklistEl.style.display = level === 'basic' ? '' : 'none';
}
```

**Step 5: Build verify**

Run: `cd frontend && npm run build 2>&1 | tail -30`
Expected: Build succeeds, no new errors.

**Step 6: Dev server smoke test**

Run: `cd frontend && npm run dev`
Open a published handbook term in browser (e.g., `/ko/handbook/rag/`).
Visual check:
- [ ] Definition + hero card visible above level switcher
- [ ] References footer visible below body (if term has references in DB)
- [ ] Understanding checklist visible in right rail during Basic view
- [ ] Toggle to Advanced: checklist disappears, references still visible

Note: Terms that haven't been regenerated with the new prompts won't have hero/references/checklist data → those blocks should simply not render (empty state). Verify an un-regenerated term still looks normal.

**Step 7: Commit**

```bash
git add frontend/src/pages/ko/handbook/[slug].astro
git commit -m "feat(handbook): [slug].astro KO — hero card + references + checklist 배치"
```

---

### Task 8: Wire Hero Card + References into [slug].astro (EN)

**Files:**
- Modify: `frontend/src/pages/en/handbook/[slug].astro`

**Step 1: Compare EN and KO [slug].astro structures**

Run: `diff frontend/src/pages/ko/handbook/[slug].astro frontend/src/pages/en/handbook/[slug].astro`
They should be nearly identical except for the `locale = 'en'` line and some label strings.

**Step 2: Apply the same changes from Task 7 to EN page**

Repeat every edit from Task 7 Step 1-4 in the EN file. The component props will automatically pick up `locale='en'`.

**Step 3: Build + commit**

```bash
cd frontend && npm run build 2>&1 | tail -30
git add frontend/src/pages/en/handbook/[slug].astro
git commit -m "feat(handbook): [slug].astro EN — hero card + references + checklist 배치"
```

---

### Task 9: End-to-end test — regenerate + save + view 1 term

**Files:**
- Use existing: `c:/tmp/regen_handbook.py`

**Step 1: Pick one published term to test with**

Use the MCP tool to verify current DB state:
```sql
SELECT slug, hero_news_context_ko IS NOT NULL AS has_hero, references_ko IS NOT NULL AS has_refs, sidebar_checklist_ko IS NOT NULL AS has_checklist
FROM handbook_terms
WHERE status = 'published'
LIMIT 5;
```
Expected: all columns NULL (no term has the new fields yet).

**Step 2: Regenerate `overfitting` and apply new fields to the DB**

The regen script currently saves JSON to `c:/tmp/` but doesn't persist to DB. You need to:
1. Regenerate with the script.
2. Manually PATCH the term in DB with the new fields using Supabase MCP:

```python
import json
data = json.load(open("c:/tmp/regen_overfitting_result.json", encoding="utf-8"))
update_payload = {
    "hero_news_context_ko": data.get("hero_news_context_ko"),
    "hero_news_context_en": data.get("hero_news_context_en"),
    "references_ko": data.get("references_ko"),
    "references_en": data.get("references_en"),
    "sidebar_checklist_ko": data.get("sidebar_checklist_ko"),
    "sidebar_checklist_en": data.get("sidebar_checklist_en"),
    "body_basic_ko": data.get("body_basic_ko"),
    "body_basic_en": data.get("body_basic_en"),
    "definition_ko": data.get("definition_ko"),
    "definition_en": data.get("definition_en"),
}
```

Run via Supabase MCP `execute_sql`:
```sql
UPDATE handbook_terms
SET
  hero_news_context_ko = '<value>',
  references_ko = '<json>'::jsonb,
  sidebar_checklist_ko = '<value>',
  body_basic_ko = '<value>',
  definition_ko = '<value>'
WHERE slug = 'overfitting';
```

(Use parameterized values through MCP rather than raw SQL concatenation.)

**Step 3: Visual QA in dev server**

Start: `cd frontend && npm run dev`
Visit: `http://localhost:4321/ko/handbook/overfitting/`

Confirm:
- [ ] Hero card renders with 3 news quote lines
- [ ] Body shows 7 sections (없음: 30초 요약, 직군별, 체크리스트)
- [ ] References footer shows 5 items (2 primary, 3 secondary) properly sorted
- [ ] Sidebar shows Understanding Checklist with 5 questions
- [ ] Toggle to Advanced: body changes, hero/references stay, checklist hides
- [ ] Toggle back to Basic: checklist reappears

**Step 4: Commit any fix-up tweaks**

If visual issues arise (spacing, colors, missing styles), fix and commit:
```bash
git add frontend/src/components/newsprint/
git commit -m "style(handbook): hero card / references 시각 조정"
```

---

### Task 10: Plan closure — sprint status update

**Files:**
- Modify: `vault/09-Implementation/plans/ACTIVE_SPRINT.md`

**Step 1: Mark HB-REDESIGN-A as done**

Find HB-REDESIGN-A row and change `todo` → `done`.

**Step 2: Commit**

```bash
git add vault/09-Implementation/plans/ACTIVE_SPRINT.md
git commit -m "chore: sprint sync — HB-REDESIGN-A done"
```

---

## Success Criteria

- [ ] Migration `00048_handbook_redesign_columns.sql` applied, 6 new columns exist
- [ ] Admin save endpoint accepts and persists new fields (smoke-tested)
- [ ] Detail page data loader returns `heroNewsContext`, `references`, `sidebarChecklist`
- [ ] 3 new Astro components exist and pass `npm run build`
- [ ] KO and EN `[slug].astro` render hero card + references footer + sidebar checklist
- [ ] Level toggle correctly shows/hides sidebar checklist (visible in Basic only)
- [ ] End-to-end test: 1 term regenerated, DB updated, page renders all 3 new blocks

## Rollback Plan

If frontend issues arise:
```bash
git revert <commit-sha-of-task-7>  # Reverts [slug].astro changes
git revert <commit-sha-of-task-8>
```
DB columns are additive (nullable) so no migration rollback needed unless explicitly requested.

## Out of Scope (explicit)

- Admin editor UI for hero/references/checklist fields (separate follow-up)
- Bulk regeneration of 138 published terms (Phase 3 — "Handbook Quality Sweep")
- EN Basic prompt redesign (Plan B — must complete before this plan to fully exercise EN rendering)
- JSON-LD structured data for references (HQ-11, separate)
- "Coming soon" badge rendering for orphan related terms (separate)

## Related

- [[2026-04-09-handbook-section-redesign]] — Master redesign spec
- [[2026-04-10-handbook-basic-en-redesign]] — Plan B (EN prompt, run first)
- [[2026-04-10-handbook-advanced-redesign]] — Plan C (Advanced prompts, run last)
