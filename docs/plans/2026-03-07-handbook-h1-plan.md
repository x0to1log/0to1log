# Tech Handbook H1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Notion Tech Handbook 데이터를 Supabase로 마이그레이션하고, `/handbook/` 이중 언어 페이지 + 어드민 검수 워크플로우를 구현한다.

**Architecture:** Supabase `handbook_terms` 테이블에 이중 언어(`_ko`/`_en` 접미사) 데이터 저장. 프론트엔드는 기존 Astro SSR + newsprint 패턴을 따른다. 어드민은 Supabase Auth JWT로 직접 CRUD (백엔드 불필요).

**Tech Stack:** Astro v5, Supabase (PostgreSQL + RLS), Tailwind CSS v4, unified/remark (Markdown)

**Design Doc:** `docs/08_Handbook.md` — 비즈니스 전략, 스키마 근거, UX 와이어프레임 참조

**Schema Note:** Current handbook runtime uses `categories TEXT[]` after `00007_handbook_multi_category.sql`. Any older single-`category` examples below are legacy H1 notes unless explicitly updated.


---

## Task 1: Create handbook_terms migration

**Files:**
- Create: `supabase/migrations/00006_handbook_terms.sql`

**Reference:** Design doc Section 2 (Supabase 테이블 설계)

**Step 1: Write migration SQL**

```sql
-- 00006_handbook_terms.sql
-- Handbook: Tech glossary terms (bilingual EN/KO)
-- Reference: docs/08_Handbook.md

CREATE TABLE IF NOT EXISTS handbook_terms (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 공통 메타 (언어 무관)
    term                    TEXT NOT NULL,
    slug                    TEXT UNIQUE NOT NULL,
    korean_name             TEXT,
    difficulty              TEXT CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    categories              TEXT[],
    related_term_slugs      TEXT[],
    is_favourite            BOOLEAN DEFAULT FALSE,

    -- 한국어 콘텐츠
    definition_ko              TEXT,
    plain_explanation_ko       TEXT,
    technical_description_ko   TEXT,
    example_analogy_ko         TEXT,
    body_markdown_ko           TEXT,

    -- 영어 콘텐츠
    definition_en              TEXT,
    plain_explanation_en       TEXT,
    technical_description_en   TEXT,
    example_analogy_en         TEXT,
    body_markdown_en           TEXT,

    -- 워크플로우
    status                  TEXT NOT NULL DEFAULT 'draft'
                            CHECK (status IN ('draft', 'published', 'archived')),

    -- Migration tracking
    notion_page_id          TEXT,

    -- Timestamps
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    published_at            TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handbook_slug ON handbook_terms(slug);
CREATE INDEX IF NOT EXISTS idx_handbook_categories ON handbook_terms USING GIN (categories);
CREATE INDEX IF NOT EXISTS idx_handbook_difficulty ON handbook_terms(difficulty);
CREATE INDEX IF NOT EXISTS idx_handbook_status ON handbook_terms(status);

-- RLS
ALTER TABLE handbook_terms ENABLE ROW LEVEL SECURITY;

CREATE POLICY "handbook_read" ON handbook_terms FOR SELECT
    USING (
        status = 'published'
        OR EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );

CREATE POLICY "handbook_write" ON handbook_terms FOR INSERT
    WITH CHECK (
        EXISTS (SELECT 1 FROM admin_users au WHERE au.email = auth.email())
    );

CREATE POLICY "handbook_update" ON handbook_terms FOR UPDATE
    USING (
        EXISTS (SELECT 1 FROM admin_users au WHERE au.email = auth.email())
    );

CREATE POLICY "handbook_delete" ON handbook_terms FOR DELETE
    USING (
        EXISTS (SELECT 1 FROM admin_users au WHERE au.email = auth.email())
    );
```

**Step 2: Run migration**

Run in Supabase Dashboard SQL Editor or:
```bash
npx supabase db push
```

**Step 3: Verify table exists**

Run in SQL Editor:
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'handbook_terms' ORDER BY ordinal_position;
```
Expected: 21 columns listed.

**Step 4: Commit**

```bash
git add supabase/migrations/00006_handbook_terms.sql
git commit -m "feat: create handbook_terms table with bilingual schema"
```

---

## Task 2: Create handbook utility functions

**Files:**
- Create: `frontend/src/lib/handbookCategories.ts`
- Create: `frontend/src/lib/handbookUtils.ts`
- Create: `frontend/tests/handbook-utils.test.cjs`

**Reference:** Design doc Section 0 (카테고리 상수) + Section 4 (locale별 필드 선택)

**Step 1: Write handbook categories helper**

Create `frontend/src/lib/handbookCategories.ts`:

```typescript
import type { Locale } from '../i18n/index';

export type HandbookCategorySlug =
  | 'ai-ml'
  | 'db-data'
  | 'backend'
  | 'frontend-ux'
  | 'network'
  | 'security'
  | 'os-core'
  | 'devops'
  | 'performance'
  | 'web3';

const HANDBOOK_CATEGORY_LABELS: Record<HandbookCategorySlug, Record<Locale, string>> = {
  'ai-ml':        { en: 'AI/ML & Algorithm',              ko: 'AI/ML & 알고리즘' },
  'db-data':      { en: 'DB / Data Infra',                ko: 'DB / 데이터 인프라' },
  'backend':      { en: 'Backend / Service Architecture',  ko: '백엔드 / 서비스 아키텍처' },
  'frontend-ux':  { en: 'Frontend & UX/UI',               ko: '프론트엔드 & UX/UI' },
  'network':      { en: 'Network / Communication',         ko: '네트워크 / 통신' },
  'security':     { en: 'Security / Access Control',       ko: '보안 / 접근 제어' },
  'os-core':      { en: 'OS / Core Principle',             ko: 'OS / 핵심 원리' },
  'devops':       { en: 'DevOps / Operation',              ko: 'DevOps / 운영' },
  'performance':  { en: 'Performance / Cost Mgt',          ko: '성능 / 비용 관리' },
  'web3':         { en: 'Decentralization / Web3',         ko: '탈중앙화 / Web3' },
};

export function getHandbookCategoryLabel(locale: Locale, category?: string | null): string | null {
  if (!category) return null;
  return HANDBOOK_CATEGORY_LABELS[category as HandbookCategorySlug]?.[locale] ?? category;
}

export function getHandbookCategories(): HandbookCategorySlug[] {
  return Object.keys(HANDBOOK_CATEGORY_LABELS) as HandbookCategorySlug[];
}
```

**Step 2: Write locale field helper**

Create `frontend/src/lib/handbookUtils.ts`:

```typescript
import type { Locale } from '../i18n/index';

/** Pick a bilingual field value with KO fallback */
export function localField(term: Record<string, any>, field: string, locale: Locale): string {
  return term[`${field}_${locale}`] || term[`${field}_ko`] || '';
}

/** Difficulty badge color */
export function difficultyColor(difficulty?: string | null): string {
  switch (difficulty) {
    case 'beginner': return 'var(--color-cat-ainews)';
    case 'intermediate': return 'var(--color-cat-study)';
    case 'advanced': return 'var(--color-cat-career)';
    default: return 'var(--color-border)';
  }
}

/** Difficulty label */
export function difficultyLabel(locale: Locale, difficulty?: string | null): string {
  const labels: Record<string, Record<Locale, string>> = {
    beginner:     { en: 'Beginner',     ko: '입문' },
    intermediate: { en: 'Intermediate', ko: '중급' },
    advanced:     { en: 'Advanced',     ko: '고급' },
  };
  if (!difficulty) return '';
  return labels[difficulty]?.[locale] ?? difficulty;
}
```

**Step 3: Write test**

Create `frontend/tests/handbook-utils.test.cjs`:

```javascript
const fs = require('fs');
const path = require('path');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

// Verify handbookCategories.ts exists and has correct exports
const catFile = fs.readFileSync(
  path.join(__dirname, '..', 'src/lib/handbookCategories.ts'), 'utf8'
);
assert(catFile.includes("'ai-ml'"), 'Must include ai-ml category');
assert(catFile.includes("'web3'"), 'Must include web3 category');
assert(catFile.includes('getHandbookCategoryLabel'), 'Must export getHandbookCategoryLabel');
assert(catFile.includes('getHandbookCategories'), 'Must export getHandbookCategories');

// Verify handbookUtils.ts exists and has correct exports
const utilFile = fs.readFileSync(
  path.join(__dirname, '..', 'src/lib/handbookUtils.ts'), 'utf8'
);
assert(utilFile.includes('localField'), 'Must export localField');
assert(utilFile.includes('difficultyColor'), 'Must export difficultyColor');
assert(utilFile.includes('difficultyLabel'), 'Must export difficultyLabel');
assert(utilFile.includes("_ko"), 'localField must fallback to _ko');

console.log('handbook-utils: all assertions passed');
```

**Step 4: Run test**

```bash
node frontend/tests/handbook-utils.test.cjs
```
Expected: `handbook-utils: all assertions passed`

**Step 5: Commit**

```bash
git add frontend/src/lib/handbookCategories.ts frontend/src/lib/handbookUtils.ts frontend/tests/handbook-utils.test.cjs
git commit -m "feat: add handbook category + locale utility functions"
```

---

## Task 3: Add i18n strings

**Files:**
- Modify: `frontend/src/i18n/index.ts`

**Reference:** Design doc Section 4, Task H1-FE-01

**Step 1: Add handbook keys to i18n**

Add to `en` object (after existing keys):

```typescript
'nav.handbook': 'Handbook',
'handbook.title': 'Tech Handbook',
'handbook.subtitle': 'CS · AI · Infra',
'handbook.empty': 'No terms yet.',
'handbook.error': 'Failed to load terms. Please try again shortly.',
'handbook.back': 'Back to Handbook',
'handbook.notfound': 'Term not found.',
'handbook.allCategories': 'All',
'handbook.search': 'Search terms...',
'handbook.searchNoResults': 'No matching terms found.',
'handbook.relatedArticles': 'Related Articles',
'handbook.relatedTerms': 'Related Terms',
'handbook.translationPending': 'Translation in progress',
```

Add to `ko` object:

```typescript
'nav.handbook': '핸드북',
'handbook.title': '기술 핸드북',
'handbook.subtitle': 'CS · AI · Infra',
'handbook.empty': '아직 용어가 없습니다.',
'handbook.error': '용어를 불러오는 데 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.',
'handbook.back': '핸드북으로 돌아가기',
'handbook.notfound': '해당 용어를 찾을 수 없습니다.',
'handbook.allCategories': '전체',
'handbook.search': '용어 검색...',
'handbook.searchNoResults': '일치하는 용어가 없습니다.',
'handbook.relatedArticles': '관련 기사',
'handbook.relatedTerms': '관련 개념',
'handbook.translationPending': '번역 준비 중',
```

**Step 2: Build verify**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/i18n/index.ts
git commit -m "feat: add handbook i18n strings (en/ko)"
```

---

## Task 4: Create Handbook list pages

**Files:**
- Create: `frontend/src/pages/en/handbook/index.astro`
- Create: `frontend/src/pages/ko/handbook/index.astro`

**Reference:** Design doc Section 4, Task H1-FE-02. Pattern: `frontend/src/pages/en/log/index.astro`

**Step 1: Create EN list page**

Create `frontend/src/pages/en/handbook/index.astro`:

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { supabase } from '../../../lib/supabase';
import { getHandbookCategoryLabel } from '../../../lib/handbookCategories';
import { localField, difficultyLabel, difficultyColor } from '../../../lib/handbookUtils';
import NewsprintShell from '../../../components/newsprint/NewsprintShell.astro';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';

const locale = 'en';
let terms: any[] = [];
let fetchError: string | null = null;

if (supabase) {
  const { data, error } = await supabase
    .from('handbook_terms')
    .select('term, slug, korean_name, definition_ko, definition_en, plain_explanation_ko, plain_explanation_en, difficulty, category, is_favourite')
    .eq('status', 'published')
    .order('term', { ascending: true });

  if (error) {
    console.error('[handbook-list-en] Supabase error:', error.message);
    fetchError = error.message;
  } else {
    terms = data ?? [];
  }
}

const categories = Array.from(
  new Set(terms.map((t) => t.category).filter(Boolean))
);
---

<MainLayout title={t[locale]['handbook.title']} locale={locale} slug="handbook/">
  <NewsprintShell
    locale={locale}
    masthead="Tech Handbook"
    editionLabel="CS · AI · Infra"
    subkicker={['Glossary', 'Reference', 'Learn']}
  >
    {/* Search + Filters — Task 7에서 구현, 여기는 placeholder */}
    <div id="handbook-controls" style="margin-bottom: 1.5rem;">
      <input
        type="text"
        id="handbook-search"
        placeholder={t[locale]['handbook.search']}
        style="width: 100%; padding: 0.75rem 1rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); font-family: var(--font-body); font-size: 0.9rem;"
      />
      <div id="handbook-filters" style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.75rem;">
        <button class="handbook-filter-btn active" data-filter="all" style="padding: 0.25rem 0.75rem; border: 1px solid var(--color-border); background: var(--color-bg-secondary); color: var(--color-text); cursor: pointer; font-size: 0.8rem;">
          {t[locale]['handbook.allCategories']}
        </button>
        {categories.map((cat) => (
          <button class="handbook-filter-btn" data-filter={cat} style="padding: 0.25rem 0.75rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text-muted); cursor: pointer; font-size: 0.8rem;">
            {getHandbookCategoryLabel(locale, cat)}
          </button>
        ))}
      </div>
    </div>

    {fetchError ? (
      <NewsprintNotice
        variant="error"
        message={t[locale]['handbook.error']}
        linkHref={`/${locale}/handbook/`}
        linkLabel={t[locale]['handbook.back']}
      />
    ) : terms.length === 0 ? (
      <NewsprintNotice variant="empty" message={t[locale]['handbook.empty']} />
    ) : (
      <div id="handbook-list">
        {terms.map((term) => {
          const def = localField(term, 'definition', locale);
          return (
            <a
              href={`/${locale}/handbook/${term.slug}/`}
              class="handbook-card"
              data-category={term.category || ''}
              data-term={term.term}
              data-korean={term.korean_name || ''}
              data-def={def}
              style="display: block; padding: 1rem; border-bottom: 1px solid var(--color-border); text-decoration: none; color: inherit;"
            >
              <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                {term.difficulty && (
                  <span style={`font-size: 0.7rem; padding: 0.1rem 0.4rem; border: 1px solid ${difficultyColor(term.difficulty)}; color: ${difficultyColor(term.difficulty)};`}>
                    {difficultyLabel(locale, term.difficulty)}
                  </span>
                )}
                {term.category && (
                  <span style="font-size: 0.7rem; color: var(--color-text-muted);">
                    {getHandbookCategoryLabel(locale, term.category)}
                  </span>
                )}
              </div>
              <div style="font-family: var(--font-display); font-size: 1.1rem; font-weight: 600;">
                {term.term}
              </div>
              {term.korean_name && (
                <div style="font-size: 0.85rem; color: var(--color-text-muted); margin-top: 0.1rem;">
                  {term.korean_name}
                </div>
              )}
              {def && (
                <div style="font-size: 0.85rem; color: var(--color-text-muted); margin-top: 0.35rem; line-height: 1.4;">
                  {def.length > 120 ? def.slice(0, 120) + '...' : def}
                </div>
              )}
            </a>
          );
        })}
      </div>
    )}

    <div id="handbook-no-results" style="display: none;">
      <NewsprintNotice variant="empty" message={t[locale]['handbook.searchNoResults']} />
    </div>
  </NewsprintShell>
</MainLayout>

<script>
  function initHandbookFilters(): void {
    const search = document.getElementById('handbook-search') as HTMLInputElement | null;
    const list = document.getElementById('handbook-list');
    const noResults = document.getElementById('handbook-no-results');
    const filterBtns = document.querySelectorAll('.handbook-filter-btn');
    if (!search || !list) return;

    let activeCategory = 'all';

    function filter(): void {
      const query = search!.value.toLowerCase().trim();
      const cards = list!.querySelectorAll('.handbook-card') as NodeListOf<HTMLElement>;
      let visible = 0;

      cards.forEach((card) => {
        const cat = card.dataset.category || '';
        const term = (card.dataset.term || '').toLowerCase();
        const korean = (card.dataset.korean || '').toLowerCase();
        const def = (card.dataset.def || '').toLowerCase();

        const matchesCategory = activeCategory === 'all' || cat === activeCategory;
        const matchesSearch = !query || term.includes(query) || korean.includes(query) || def.includes(query);

        card.style.display = matchesCategory && matchesSearch ? 'block' : 'none';
        if (matchesCategory && matchesSearch) visible++;
      });

      if (noResults) {
        noResults.style.display = visible === 0 && (query || activeCategory !== 'all') ? 'block' : 'none';
      }
    }

    search.addEventListener('input', filter);

    filterBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        filterBtns.forEach((b) => {
          (b as HTMLElement).classList.remove('active');
          (b as HTMLElement).style.background = 'var(--color-bg)';
          (b as HTMLElement).style.color = 'var(--color-text-muted)';
        });
        (btn as HTMLElement).classList.add('active');
        (btn as HTMLElement).style.background = 'var(--color-bg-secondary)';
        (btn as HTMLElement).style.color = 'var(--color-text)';
        activeCategory = (btn as HTMLElement).dataset.filter || 'all';
        filter();
      });
    });
  }

  document.addEventListener('astro:page-load', initHandbookFilters);
  initHandbookFilters();
</script>
```

**Step 2: Create KO list page**

Create `frontend/src/pages/ko/handbook/index.astro`:

Same file but with these changes:
- `const locale = 'ko';`
- Console log prefix: `[handbook-list-ko]`
- No other changes — all locale-dependent text uses `t[locale][...]`

**Step 3: Build verify**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 4: Commit**

```bash
git add frontend/src/pages/en/handbook/index.astro frontend/src/pages/ko/handbook/index.astro
git commit -m "feat: add handbook list pages (en/ko) with search + category filter"
```

---

## Task 5: Create Handbook detail pages

**Files:**
- Create: `frontend/src/pages/en/handbook/[slug].astro`
- Create: `frontend/src/pages/ko/handbook/[slug].astro`

**Reference:** Design doc Section 4, Task H1-FE-03. Pattern: `frontend/src/pages/en/log/[slug].astro`

**Step 1: Create EN detail page**

Create `frontend/src/pages/en/handbook/[slug].astro`:

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { t } from '../../../i18n/index';
import { supabase } from '../../../lib/supabase';
import { getHandbookCategoryLabel } from '../../../lib/handbookCategories';
import { localField, difficultyLabel, difficultyColor } from '../../../lib/handbookUtils';
import { renderMarkdown } from '../../../lib/markdown';
import NewsprintShell from '../../../components/newsprint/NewsprintShell.astro';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';

const locale = 'en';
const { slug } = Astro.params;
const pageSlug = slug ?? '';

let term: any = null;
let termError: string | null = null;

if (supabase && slug) {
  const { data, error } = await supabase
    .from('handbook_terms')
    .select('*')
    .eq('slug', pageSlug)
    .eq('status', 'published')
    .single();

  if (error && error.code !== 'PGRST116') {
    console.error('[handbook-detail-en] Supabase error:', error.message);
    termError = error.message;
  } else {
    term = data;
  }
}

if (!term && !termError) {
  Astro.response.status = 404;
}

// Locale-aware field selection with KO fallback
const definition = term ? localField(term, 'definition', locale) : '';
const plainExplanation = term ? localField(term, 'plain_explanation', locale) : '';
const technicalDescription = term ? localField(term, 'technical_description', locale) : '';
const exampleAnalogy = term ? localField(term, 'example_analogy', locale) : '';
const bodyMarkdown = term ? localField(term, 'body_markdown', locale) : '';
const htmlContent = bodyMarkdown ? await renderMarkdown(bodyMarkdown) : '';

// Check if showing fallback KO content
const isEnFallback = term && locale === 'en' && !term.definition_en && term.definition_ko;

// Related articles from posts table
let relatedArticles: any[] = [];
if (supabase && term) {
  const { data: articles } = await supabase
    .from('posts')
    .select('title, slug, category, published_at')
    .eq('status', 'published')
    .contains('tags', [term.term.toLowerCase()])
    .limit(5);
  relatedArticles = articles ?? [];
}

// Related terms
let relatedTerms: any[] = [];
if (supabase && term?.related_term_slugs?.length) {
  const { data: related } = await supabase
    .from('handbook_terms')
    .select('term, slug, korean_name, difficulty')
    .eq('status', 'published')
    .in('slug', term.related_term_slugs);
  relatedTerms = related ?? [];
}

// SEO
const pageTitle = term
  ? (locale === 'ko' && term.korean_name
    ? `${term.term} (${term.korean_name})`
    : term.term)
  : t[locale]['handbook.notfound'];
const pageDescription = definition ? definition.slice(0, 150) : '';
---

<MainLayout
  title={`${pageTitle} — Tech Handbook`}
  description={pageDescription}
  locale={locale}
  slug={`handbook/${pageSlug}/`}
>
  <NewsprintShell locale={locale} masthead="Tech Handbook" editionLabel={term?.category ? getHandbookCategoryLabel(locale, term.category) || '' : ''}>
    {termError ? (
      <NewsprintNotice
        variant="error"
        message={t[locale]['handbook.error']}
        linkHref={`/${locale}/handbook/`}
        linkLabel={t[locale]['handbook.back']}
      />
    ) : !term ? (
      <NewsprintNotice
        variant="notfound"
        message={t[locale]['handbook.notfound']}
        linkHref={`/${locale}/handbook/`}
        linkLabel={t[locale]['handbook.back']}
      />
    ) : (
      <article>
        {/* Back link */}
        <a href={`/${locale}/handbook/`} style="font-size: 0.85rem; color: var(--color-text-muted); text-decoration: none; display: inline-block; margin-bottom: 1rem;">
          ← {t[locale]['handbook.back']}
        </a>

        {/* Translation pending banner */}
        {isEnFallback && (
          <div style="padding: 0.5rem 1rem; background: var(--color-bg-secondary); border: 1px solid var(--color-border); margin-bottom: 1rem; font-size: 0.85rem; color: var(--color-text-muted);">
            {t[locale]['handbook.translationPending']}
          </div>
        )}

        {/* Header */}
        <header style="margin-bottom: 1.5rem;">
          <h1 style="font-family: var(--font-display); font-size: 2rem; font-weight: 700; margin: 0;">
            {term.term}
          </h1>
          {term.korean_name && (
            <p style="font-size: 1rem; color: var(--color-text-muted); margin: 0.25rem 0 0;">
              {term.korean_name}
            </p>
          )}
          <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; align-items: center;">
            {term.difficulty && (
              <span style={`font-size: 0.75rem; padding: 0.15rem 0.5rem; border: 1px solid ${difficultyColor(term.difficulty)}; color: ${difficultyColor(term.difficulty)};`}>
                {difficultyLabel(locale, term.difficulty)}
              </span>
            )}
            {term.category && (
              <span style="font-size: 0.75rem; color: var(--color-text-muted);">
                {getHandbookCategoryLabel(locale, term.category)}
              </span>
            )}
          </div>
        </header>

        {/* Infobox: Definition + Plain Explanation + Example */}
        <div style="padding: 1.25rem; border: 1px solid var(--color-border); background: var(--color-bg-secondary); margin-bottom: 2rem;">
          {definition && (
            <div style="margin-bottom: 0.75rem;">
              <strong style="font-size: 0.8rem; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em;">
                {locale === 'ko' ? '정의' : 'Definition'}
              </strong>
              <p style="margin: 0.25rem 0 0; line-height: 1.5;">{definition}</p>
            </div>
          )}
          {plainExplanation && (
            <div style="margin-bottom: 0.75rem;">
              <strong style="font-size: 0.8rem; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em;">
                {locale === 'ko' ? '쉬운 설명' : 'Plain Explanation'}
              </strong>
              <p style="margin: 0.25rem 0 0; line-height: 1.5;">{plainExplanation}</p>
            </div>
          )}
          {exampleAnalogy && (
            <div>
              <strong style="font-size: 0.8rem; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em;">
                {locale === 'ko' ? '예시 / 비유' : 'Example / Analogy'}
              </strong>
              <p style="margin: 0.25rem 0 0; line-height: 1.5;">{exampleAnalogy}</p>
            </div>
          )}
        </div>

        {/* Body markdown */}
        {htmlContent && (
          <div class="newsprint-prose">
            <Fragment set:html={htmlContent} />
          </div>
        )}

        {/* Related Terms */}
        {relatedTerms.length > 0 && (
          <div style="margin-top: 2.5rem; padding-top: 1.5rem; border-top: 1px solid var(--color-border);">
            <h2 style="font-family: var(--font-display); font-size: 1.1rem; margin-bottom: 0.75rem;">
              {t[locale]['handbook.relatedTerms']}
            </h2>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
              {relatedTerms.map((rt) => (
                <a
                  href={`/${locale}/handbook/${rt.slug}/`}
                  style="padding: 0.35rem 0.75rem; border: 1px solid var(--color-border); text-decoration: none; color: var(--color-text); font-size: 0.85rem;"
                >
                  {rt.term}
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Related Articles */}
        {relatedArticles.length > 0 && (
          <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid var(--color-border);">
            <h2 style="font-family: var(--font-display); font-size: 1.1rem; margin-bottom: 0.75rem;">
              {t[locale]['handbook.relatedArticles']}
            </h2>
            {relatedArticles.map((article) => (
              <a
                href={`/${locale}/log/${article.slug}/`}
                style="display: block; padding: 0.5rem 0; text-decoration: none; color: var(--color-text); border-bottom: 1px solid var(--color-border);"
              >
                <span style="font-size: 0.9rem;">{article.title}</span>
                {article.published_at && (
                  <span style="font-size: 0.75rem; color: var(--color-text-muted); margin-left: 0.5rem;">
                    {new Date(article.published_at).toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US')}
                  </span>
                )}
              </a>
            ))}
          </div>
        )}
      </article>
    )}
  </NewsprintShell>
</MainLayout>
```

**Step 2: Create KO detail page**

Create `frontend/src/pages/ko/handbook/[slug].astro`:

Same file but with:
- `const locale = 'ko';`
- Console log prefix: `[handbook-detail-ko]`

**Step 3: Build verify**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 4: Commit**

```bash
git add frontend/src/pages/en/handbook/[slug].astro frontend/src/pages/ko/handbook/[slug].astro
git commit -m "feat: add handbook detail pages (en/ko) with infobox, related terms/articles"
```

---

## Task 6: Add Handbook to Navigation

**Files:**
- Modify: `frontend/src/components/Navigation.astro`

**Reference:** Design doc Section 4, Task H1-FE-04

**Step 1: Add Handbook link**

In `frontend/src/components/Navigation.astro`, find the nav links div and add Handbook between Log and Portfolio:

```astro
<!-- Find this line: -->
<a href={`/${locale}/log/`} class="newsprint-nav-link">Log</a>
<!-- Add after it: -->
<a href={`/${locale}/handbook/`} class="newsprint-nav-link">Handbook</a>
<!-- Before: -->
<a href="/portfolio/" class="newsprint-nav-link">Portfolio</a>
```

Also update `altPath` calculation to handle handbook routes:

```astro
const altPath = altSlug
  ? `/${altLocale}/log/${altSlug}/`
  : currentPath.replace(`/${locale}/`, `/${altLocale}/`);
```

The existing `currentPath.replace` already handles `/handbook/` paths correctly — no change needed.

**Step 2: Write test**

Create `frontend/tests/handbook-nav.test.cjs`:

```javascript
const fs = require('fs');
const path = require('path');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const nav = fs.readFileSync(
  path.join(__dirname, '..', 'src/components/Navigation.astro'), 'utf8'
);

assert(nav.includes('/handbook/'), 'Navigation must include handbook link');
assert(
  nav.indexOf('/handbook/') > nav.indexOf('/log/'),
  'Handbook link must appear after Log link'
);
assert(
  nav.indexOf('/handbook/') < nav.indexOf('/portfolio/'),
  'Handbook link must appear before Portfolio link'
);

console.log('handbook-nav: all assertions passed');
```

**Step 3: Run test**

```bash
node frontend/tests/handbook-nav.test.cjs
```
Expected: `handbook-nav: all assertions passed`

**Step 4: Build verify**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 5: Commit**

```bash
git add frontend/src/components/Navigation.astro frontend/tests/handbook-nav.test.cjs
git commit -m "feat: add Handbook link to navigation"
```

---

## Task 7: Create admin Supabase auth helper

**Files:**
- Create: `frontend/src/lib/supabaseAdmin.ts`

**Context:** Admin pages need an authenticated Supabase client (with user JWT) for RLS-gated writes. The existing `supabase.ts` uses anon key only. Middleware already extracts `accessToken` from cookies into `Astro.locals.accessToken`.

**Step 1: Create admin Supabase client factory**

Create `frontend/src/lib/supabaseAdmin.ts`:

```typescript
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/**
 * Create a Supabase client authenticated with the user's JWT.
 * Use this in admin pages for RLS-gated writes.
 * The middleware (src/middleware.ts) already validates the token.
 */
export function createAdminSupabase(accessToken: string): SupabaseClient | null {
  const url = import.meta.env.PUBLIC_SUPABASE_URL;
  const key = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;

  return createClient(url, key, {
    global: {
      headers: { Authorization: `Bearer ${accessToken}` },
    },
  });
}
```

**Step 2: Build verify**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/lib/supabaseAdmin.ts
git commit -m "feat: add authenticated Supabase client helper for admin pages"
```

---

## Task 8: Create admin handbook list page

**Files:**
- Create: `frontend/src/pages/admin/handbook/index.astro`

**Reference:** Design doc Section 5, Task H1-ADMIN-01

**Step 1: Create admin list page**

Create `frontend/src/pages/admin/handbook/index.astro`:

```astro
---
export const prerender = false;

import MainLayout from '../../../layouts/MainLayout.astro';
import { createAdminSupabase } from '../../../lib/supabaseAdmin';
import { getHandbookCategoryLabel } from '../../../lib/handbookCategories';
import { difficultyLabel } from '../../../lib/handbookUtils';
import NewsprintNotice from '../../../components/newsprint/NewsprintNotice.astro';

const accessToken = Astro.locals.accessToken;
if (!accessToken) return Astro.redirect('/admin/login');

const supabase = createAdminSupabase(accessToken);
let terms: any[] = [];
let fetchError: string | null = null;

if (supabase) {
  const { data, error } = await supabase
    .from('handbook_terms')
    .select('term, slug, korean_name, difficulty, category, status, definition_ko, definition_en, plain_explanation_ko, plain_explanation_en, body_markdown_ko, body_markdown_en, updated_at')
    .order('updated_at', { ascending: false });

  if (error) {
    console.error('[admin-handbook] Supabase error:', error.message);
    fetchError = error.message;
  } else {
    terms = data ?? [];
  }
}

// Content completeness check
function isFieldComplete(val: string | null | undefined): boolean {
  return Boolean(val && val.trim().length > 0);
}
---

<MainLayout title="Handbook Admin" locale="en" slug="admin/handbook/">
  <div style="max-width: 900px; margin: 2rem auto; padding: 0 1rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
      <h1 style="font-family: var(--font-display); font-size: 1.75rem; margin: 0;">Handbook Admin</h1>
      <a href="/admin/" style="font-size: 0.85rem; color: var(--color-text-muted);">← Back to Admin</a>
    </div>

    {/* Status filter tabs */}
    <div id="status-tabs" style="display: flex; gap: 1rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--color-border); padding-bottom: 0.5rem;">
      <button class="status-tab active" data-status="all" style="background: none; border: none; cursor: pointer; font-size: 0.9rem; padding: 0.25rem 0; color: var(--color-text); border-bottom: 2px solid var(--color-accent);">
        All ({terms.length})
      </button>
      <button class="status-tab" data-status="draft" style="background: none; border: none; cursor: pointer; font-size: 0.9rem; padding: 0.25rem 0; color: var(--color-text-muted); border-bottom: 2px solid transparent;">
        Draft ({terms.filter(t => t.status === 'draft').length})
      </button>
      <button class="status-tab" data-status="published" style="background: none; border: none; cursor: pointer; font-size: 0.9rem; padding: 0.25rem 0; color: var(--color-text-muted); border-bottom: 2px solid transparent;">
        Published ({terms.filter(t => t.status === 'published').length})
      </button>
    </div>

    {fetchError ? (
      <NewsprintNotice variant="error" message={fetchError} />
    ) : terms.length === 0 ? (
      <NewsprintNotice variant="empty" message="No handbook terms yet." />
    ) : (
      <div id="admin-term-list">
        {terms.map((term) => {
          const koComplete = isFieldComplete(term.definition_ko);
          const enComplete = isFieldComplete(term.definition_en);
          return (
            <div
              class="admin-term-card"
              data-status={term.status}
              style="padding: 1rem; border: 1px solid var(--color-border); margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center;"
            >
              <div>
                <div style="font-weight: 600; font-size: 1rem;">
                  {term.term}
                  {term.korean_name && (
                    <span style="font-weight: 400; color: var(--color-text-muted); margin-left: 0.5rem; font-size: 0.85rem;">
                      {term.korean_name}
                    </span>
                  )}
                </div>
                <div style="font-size: 0.8rem; color: var(--color-text-muted); margin-top: 0.25rem; display: flex; gap: 1rem;">
                  <span>KO: {koComplete ? '✅' : '❌'}</span>
                  <span>EN: {enComplete ? '✅' : '❌'}</span>
                  <span>{getHandbookCategoryLabel('en', term.category) || '—'}</span>
                  <span>{difficultyLabel('en', term.difficulty) || '—'}</span>
                  <span style={`padding: 0.1rem 0.4rem; font-size: 0.7rem; border: 1px solid ${term.status === 'published' ? 'green' : 'orange'}; color: ${term.status === 'published' ? 'green' : 'orange'};`}>
                    {term.status}
                  </span>
                </div>
              </div>
              <div style="display: flex; gap: 0.5rem;">
                <a
                  href={`/admin/handbook/edit/${term.slug}/`}
                  style="padding: 0.35rem 0.75rem; border: 1px solid var(--color-border); text-decoration: none; color: var(--color-text); font-size: 0.8rem;"
                >
                  Edit
                </a>
              </div>
            </div>
          );
        })}
      </div>
    )}
  </div>
</MainLayout>

<script>
  function initStatusFilter(): void {
    const tabs = document.querySelectorAll('.status-tab');
    const cards = document.querySelectorAll('.admin-term-card');

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => {
          (t as HTMLElement).classList.remove('active');
          (t as HTMLElement).style.color = 'var(--color-text-muted)';
          (t as HTMLElement).style.borderBottom = '2px solid transparent';
        });
        (tab as HTMLElement).classList.add('active');
        (tab as HTMLElement).style.color = 'var(--color-text)';
        (tab as HTMLElement).style.borderBottom = '2px solid var(--color-accent)';

        const status = (tab as HTMLElement).dataset.status;
        cards.forEach((card) => {
          const cardStatus = (card as HTMLElement).dataset.status;
          (card as HTMLElement).style.display =
            status === 'all' || cardStatus === status ? 'flex' : 'none';
        });
      });
    });
  }

  document.addEventListener('astro:page-load', initStatusFilter);
  initStatusFilter();
</script>
```

**Step 2: Build verify**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/pages/admin/handbook/index.astro
git commit -m "feat: add admin handbook list page with status filter + completeness badges"
```

---

## Task 9: Create admin handbook edit page

**Files:**
- Create: `frontend/src/pages/admin/handbook/edit/[slug].astro`

**Reference:** Design doc Section 5, Task H1-ADMIN-01 (편집 페이지)

**Step 1: Create admin edit page**

Create `frontend/src/pages/admin/handbook/edit/[slug].astro`:

```astro
---
export const prerender = false;

import MainLayout from '../../../../layouts/MainLayout.astro';
import { createAdminSupabase } from '../../../../lib/supabaseAdmin';
import { getHandbookCategories, getHandbookCategoryLabel } from '../../../../lib/handbookCategories';
import { renderMarkdown } from '../../../../lib/markdown';

const { slug } = Astro.params;
const pageSlug = slug ?? '';
const accessToken = Astro.locals.accessToken;
if (!accessToken) return Astro.redirect('/admin/login');

const supabase = createAdminSupabase(accessToken);
let term: any = null;
let fetchError: string | null = null;

if (supabase && slug) {
  const { data, error } = await supabase
    .from('handbook_terms')
    .select('*')
    .eq('slug', pageSlug)
    .single();

  if (error) {
    fetchError = error.code === 'PGRST116' ? '404' : error.message;
  } else {
    term = data;
  }
}

const categories = getHandbookCategories();
const previewHtmlKo = term?.body_markdown_ko ? await renderMarkdown(term.body_markdown_ko) : '';
const previewHtmlEn = term?.body_markdown_en ? await renderMarkdown(term.body_markdown_en) : '';
---

<MainLayout title={`Edit: ${term?.term || pageSlug}`} locale="en" slug={`admin/handbook/edit/${pageSlug}/`}>
  <div style="max-width: 900px; margin: 2rem auto; padding: 0 1rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
      <h1 style="font-family: var(--font-display); font-size: 1.5rem; margin: 0;">
        Edit: {term?.term || pageSlug}
      </h1>
      <a href="/admin/handbook/" style="font-size: 0.85rem; color: var(--color-text-muted);">← Back to List</a>
    </div>

    {/* Feedback banner */}
    <div id="feedback" style="display: none; padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.9rem;"></div>

    {fetchError === '404' ? (
      <p>Term not found.</p>
    ) : fetchError ? (
      <p>Error: {fetchError}</p>
    ) : term ? (
      <form id="edit-form">
        {/* Common fields */}
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
          <div>
            <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 0.25rem;">Term</label>
            <input id="f-term" type="text" value={term.term} style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text);" />
          </div>
          <div>
            <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 0.25rem;">Korean Name</label>
            <input id="f-korean-name" type="text" value={term.korean_name || ''} style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text);" />
          </div>
          <div>
            <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 0.25rem;">Category</label>
            <select id="f-category" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text);">
              <option value="">—</option>
              {categories.map((cat) => (
                <option value={cat} selected={term.category === cat}>
                  {getHandbookCategoryLabel('en', cat)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 0.25rem;">Difficulty</label>
            <select id="f-difficulty" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text);">
              <option value="">—</option>
              <option value="beginner" selected={term.difficulty === 'beginner'}>Beginner</option>
              <option value="intermediate" selected={term.difficulty === 'intermediate'}>Intermediate</option>
              <option value="advanced" selected={term.difficulty === 'advanced'}>Advanced</option>
            </select>
          </div>
        </div>

        {/* Language tabs */}
        <div style="display: flex; gap: 1rem; border-bottom: 1px solid var(--color-border); margin-bottom: 1rem;">
          <button type="button" class="lang-tab active" data-lang="ko" style="background: none; border: none; cursor: pointer; padding: 0.5rem 0; border-bottom: 2px solid var(--color-accent); color: var(--color-text);">
            한국어 (KO)
          </button>
          <button type="button" class="lang-tab" data-lang="en" style="background: none; border: none; cursor: pointer; padding: 0.5rem 0; border-bottom: 2px solid transparent; color: var(--color-text-muted);">
            English (EN)
          </button>
        </div>

        {/* KO fields */}
        <div id="fields-ko" class="lang-fields">
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Definition (KO)</label>
            <textarea id="f-definition-ko" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); resize: vertical;">{term.definition_ko || ''}</textarea>
          </div>
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Plain Explanation (KO)</label>
            <textarea id="f-plain-ko" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); resize: vertical;">{term.plain_explanation_ko || ''}</textarea>
          </div>
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Technical Description (KO)</label>
            <textarea id="f-tech-ko" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); resize: vertical;">{term.technical_description_ko || ''}</textarea>
          </div>
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Example / Analogy (KO)</label>
            <textarea id="f-example-ko" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); resize: vertical;">{term.example_analogy_ko || ''}</textarea>
          </div>
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Body Markdown (KO)</label>
            <textarea id="f-body-ko" rows="12" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); font-family: monospace; font-size: 0.85rem; resize: vertical;">{term.body_markdown_ko || ''}</textarea>
          </div>
        </div>

        {/* EN fields (hidden by default) */}
        <div id="fields-en" class="lang-fields" style="display: none;">
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Definition (EN)</label>
            <textarea id="f-definition-en" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); resize: vertical;">{term.definition_en || ''}</textarea>
          </div>
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Plain Explanation (EN)</label>
            <textarea id="f-plain-en" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); resize: vertical;">{term.plain_explanation_en || ''}</textarea>
          </div>
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Technical Description (EN)</label>
            <textarea id="f-tech-en" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); resize: vertical;">{term.technical_description_en || ''}</textarea>
          </div>
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Example / Analogy (EN)</label>
            <textarea id="f-example-en" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); resize: vertical;">{term.example_analogy_en || ''}</textarea>
          </div>
          <div style="margin-bottom: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600;">Body Markdown (EN)</label>
            <textarea id="f-body-en" rows="12" style="width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); font-family: monospace; font-size: 0.85rem; resize: vertical;">{term.body_markdown_en || ''}</textarea>
          </div>
        </div>

        {/* Action buttons */}
        <div style="display: flex; gap: 0.75rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--color-border);">
          <button type="button" id="btn-save" style="padding: 0.5rem 1.25rem; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); cursor: pointer;">
            Save Draft
          </button>
          <button type="button" id="btn-publish" style="padding: 0.5rem 1.25rem; border: 1px solid green; background: var(--color-bg); color: green; cursor: pointer;">
            {term.status === 'published' ? 'Update & Keep Published' : 'Publish'}
          </button>
          {term.status === 'published' && (
            <button type="button" id="btn-unpublish" style="padding: 0.5rem 1.25rem; border: 1px solid orange; background: var(--color-bg); color: orange; cursor: pointer;">
              Unpublish (→ Draft)
            </button>
          )}
        </div>

        <p style="font-size: 0.8rem; color: var(--color-text-muted); margin-top: 0.5rem;">
          Status: <strong>{term.status}</strong>
          {term.published_at && ` · Published: ${new Date(term.published_at).toLocaleString()}`}
        </p>
      </form>
    ) : null}
  </div>
</MainLayout>

<script define:vars={{ termId: term?.id, currentStatus: term?.status }}>
  function initHandbookEdit() {
    const tabs = document.querySelectorAll('.lang-tab');
    const fieldsKo = document.getElementById('fields-ko');
    const fieldsEn = document.getElementById('fields-en');
    const feedback = document.getElementById('feedback');
    const btnSave = document.getElementById('btn-save');
    const btnPublish = document.getElementById('btn-publish');
    const btnUnpublish = document.getElementById('btn-unpublish');

    // Language tab switching
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => {
          t.classList.remove('active');
          t.style.color = 'var(--color-text-muted)';
          t.style.borderBottom = '2px solid transparent';
        });
        tab.classList.add('active');
        tab.style.color = 'var(--color-text)';
        tab.style.borderBottom = '2px solid var(--color-accent)';
        const lang = tab.dataset.lang;
        if (fieldsKo) fieldsKo.style.display = lang === 'ko' ? 'block' : 'none';
        if (fieldsEn) fieldsEn.style.display = lang === 'en' ? 'block' : 'none';
      });
    });

    function showFeedback(msg, isError) {
      if (!feedback) return;
      feedback.style.display = 'block';
      feedback.style.background = isError ? '#fee' : '#efe';
      feedback.style.color = isError ? '#c00' : '#060';
      feedback.style.border = `1px solid ${isError ? '#fcc' : '#cfc'}`;
      feedback.textContent = msg;
      setTimeout(() => { feedback.style.display = 'none'; }, 3000);
    }

    function getFormData() {
      return {
        term: document.getElementById('f-term')?.value || '',
        korean_name: document.getElementById('f-korean-name')?.value || null,
        category: document.getElementById('f-category')?.value || null,
        difficulty: document.getElementById('f-difficulty')?.value || null,
        definition_ko: document.getElementById('f-definition-ko')?.value || null,
        plain_explanation_ko: document.getElementById('f-plain-ko')?.value || null,
        technical_description_ko: document.getElementById('f-tech-ko')?.value || null,
        example_analogy_ko: document.getElementById('f-example-ko')?.value || null,
        body_markdown_ko: document.getElementById('f-body-ko')?.value || null,
        definition_en: document.getElementById('f-definition-en')?.value || null,
        plain_explanation_en: document.getElementById('f-plain-en')?.value || null,
        technical_description_en: document.getElementById('f-tech-en')?.value || null,
        example_analogy_en: document.getElementById('f-example-en')?.value || null,
        body_markdown_en: document.getElementById('f-body-en')?.value || null,
        updated_at: new Date().toISOString(),
      };
    }

    async function saveTerm(extraFields = {}) {
      const data = { ...getFormData(), ...extraFields };
      const supabaseUrl = document.querySelector('meta[name="x-supabase-url"]')?.getAttribute('content');
      const supabaseKey = document.querySelector('meta[name="x-supabase-key"]')?.getAttribute('content');

      // Use fetch to call Supabase REST API directly
      const res = await fetch(`${supabaseUrl}/rest/v1/handbook_terms?id=eq.${termId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'apikey': supabaseKey,
          'Authorization': `Bearer ${document.cookie.split('sb-access-token=')[1]?.split(';')[0] || ''}`,
          'Prefer': 'return=minimal',
        },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }
    }

    if (btnSave) {
      btnSave.addEventListener('click', async () => {
        try {
          await saveTerm({ status: 'draft' });
          showFeedback('Draft saved.', false);
        } catch (e) {
          showFeedback('Save failed: ' + e.message, true);
        }
      });
    }

    if (btnPublish) {
      btnPublish.addEventListener('click', async () => {
        const formData = getFormData();
        // Validation
        if (!formData.term.trim()) { showFeedback('Term is required.', true); return; }
        if (!formData.definition_ko?.trim()) { showFeedback('KO Definition is required to publish.', true); return; }
        if (!formData.category) { showFeedback('Category is required to publish.', true); return; }

        try {
          await saveTerm({
            status: 'published',
            published_at: currentStatus !== 'published' ? new Date().toISOString() : undefined,
          });
          showFeedback('Published!', false);
          setTimeout(() => location.reload(), 1000);
        } catch (e) {
          showFeedback('Publish failed: ' + e.message, true);
        }
      });
    }

    if (btnUnpublish) {
      btnUnpublish.addEventListener('click', async () => {
        try {
          await saveTerm({ status: 'draft' });
          showFeedback('Unpublished → Draft.', false);
          setTimeout(() => location.reload(), 1000);
        } catch (e) {
          showFeedback('Unpublish failed: ' + e.message, true);
        }
      });
    }
  }

  document.addEventListener('astro:page-load', initHandbookEdit);
  initHandbookEdit();
</script>
```

**Important:** The client-side save uses Supabase REST API directly via `fetch()`. We need to expose `PUBLIC_SUPABASE_URL` and `PUBLIC_SUPABASE_ANON_KEY` to the client. Add meta tags to the page head, or use a simpler pattern: pass env vars via `define:vars`.

**Alternative (simpler):** Replace the client-side fetch with a form action that posts to the same Astro page (SSR server-side handling). This is more Astro-idiomatic. However, the above pattern works and matches the existing admin edit page's client-side approach.

**Step 2: Build verify**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/pages/admin/handbook/edit/[slug].astro
git commit -m "feat: add admin handbook edit page with KO/EN tabs and save/publish actions"
```

---

## Task 10: Create Notion → Supabase migration script

**Files:**
- Create: `scripts/migrate-handbook-from-notion.ts`

**Reference:** Design doc Section 3, Task H1-DB-02

**Context:** This is a one-time script. Uses Notion MCP (or Notion API) to fetch Words DB, then inserts into Supabase. Run manually, not in CI.

**Step 1: Create migration script**

Create `scripts/migrate-handbook-from-notion.ts`:

```typescript
/**
 * One-time migration: Notion Words DB → Supabase handbook_terms
 *
 * Usage:
 *   npx tsx scripts/migrate-handbook-from-notion.ts
 *
 * Requires .env:
 *   NOTION_API_KEY=secret_xxx
 *   SUPABASE_URL=https://xxx.supabase.co
 *   SUPABASE_SERVICE_ROLE_KEY=eyJxxx  (service role, not anon)
 *   NOTION_WORDS_DB_ID=xxx            (Notion Words database ID)
 */

import { Client } from '@notionhq/client';
import { createClient } from '@supabase/supabase-js';
import 'dotenv/config';

const notion = new Client({ auth: process.env.NOTION_API_KEY });
const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);
const dbId = process.env.NOTION_WORDS_DB_ID!;

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
}

function richTextToPlain(richText: any[]): string {
  return richText?.map((rt: any) => rt.plain_text).join('') || '';
}

// Category mapping: Notion relation → slug
const CATEGORY_MAP: Record<string, string> = {
  'AI/ML & Algorithm': 'ai-ml',
  'DB / Data Infra': 'db-data',
  'Backend / Service Architecture': 'backend',
  'Frontend & UX/UI': 'frontend-ux',
  'Network / Communication': 'network',
  'Security / Access Control': 'security',
  'OS / Core Principle': 'os-core',
  'DevOps / Operation': 'devops',
  'Performance / Cost Mgt': 'performance',
  'Decentralization / Web3': 'web3',
};

async function getBlockChildren(blockId: string): Promise<string> {
  const blocks: any[] = [];
  let cursor: string | undefined;

  do {
    const res = await notion.blocks.children.list({
      block_id: blockId,
      start_cursor: cursor,
    });
    blocks.push(...res.results);
    cursor = res.has_more ? res.next_cursor! : undefined;
  } while (cursor);

  // Simple block → markdown conversion
  return blocks.map((block: any) => {
    const type = block.type;
    if (!block[type]) return '';

    switch (type) {
      case 'paragraph':
        return richTextToPlain(block.paragraph.rich_text) + '\n';
      case 'heading_1':
        return '# ' + richTextToPlain(block.heading_1.rich_text) + '\n';
      case 'heading_2':
        return '## ' + richTextToPlain(block.heading_2.rich_text) + '\n';
      case 'heading_3':
        return '### ' + richTextToPlain(block.heading_3.rich_text) + '\n';
      case 'bulleted_list_item':
        return '- ' + richTextToPlain(block.bulleted_list_item.rich_text) + '\n';
      case 'numbered_list_item':
        return '1. ' + richTextToPlain(block.numbered_list_item.rich_text) + '\n';
      case 'code':
        const lang = block.code.language || '';
        return '```' + lang + '\n' + richTextToPlain(block.code.rich_text) + '\n```\n';
      case 'quote':
        return '> ' + richTextToPlain(block.quote.rich_text) + '\n';
      case 'divider':
        return '---\n';
      case 'toggle':
        const summary = richTextToPlain(block.toggle.rich_text);
        return `<details>\n<summary>${summary}</summary>\n\n</details>\n`;
      default:
        return '';
    }
  }).join('\n');
}

async function main() {
  console.log('Fetching Notion Words DB...');

  const pages: any[] = [];
  let cursor: string | undefined;

  do {
    const res = await notion.databases.query({
      database_id: dbId,
      start_cursor: cursor,
    });
    pages.push(...res.results);
    cursor = res.has_more ? res.next_cursor! : undefined;
  } while (cursor);

  console.log(`Found ${pages.length} terms.`);

  for (const page of pages) {
    const props = page.properties;
    const term = richTextToPlain(props['Term']?.title || []);
    if (!term) { console.log('  Skipping page with no term'); continue; }

    const slug = slugify(term);
    const koreanName = richTextToPlain(props['Korean (한글명)']?.rich_text || []);
    const definition = richTextToPlain(props['Definition (정의)']?.rich_text || []);
    const plainExplanation = richTextToPlain(props['Plain Explanation (쉬운 설명)']?.rich_text || []);
    const technicalDescription = richTextToPlain(props['Technical Description (기술적 설명)']?.rich_text || []);
    const exampleAnalogy = richTextToPlain(props['Example/Analogy (예시/비유)']?.rich_text || []);
    const difficulty = props['Difficulty']?.select?.name?.toLowerCase() || null;
    const isFavourite = props['Favourite']?.checkbox || false;

    // Category (relation) — fetch the related page title
    let category: string | null = null;
    const catRelation = props['Category']?.relation || [];
    if (catRelation.length > 0) {
      try {
        const catPage = await notion.pages.retrieve({ page_id: catRelation[0].id });
        const catTitle = richTextToPlain((catPage as any).properties?.Name?.title || []);
        category = CATEGORY_MAP[catTitle] || catTitle;
      } catch { /* skip */ }
    }

    // Related Terms (self-relation) — fetch slugs
    const relatedSlugs: string[] = [];
    const relatedRelation = props['Related Terms (관련 개념)']?.relation || [];
    for (const rel of relatedRelation) {
      try {
        const relPage = await notion.pages.retrieve({ page_id: rel.id });
        const relTerm = richTextToPlain((relPage as any).properties?.['Term']?.title || []);
        if (relTerm) relatedSlugs.push(slugify(relTerm));
      } catch { /* skip */ }
    }

    // Body markdown (page content)
    const bodyMarkdown = await getBlockChildren(page.id);

    console.log(`  Inserting: ${term} (${slug})`);

    const { error } = await supabase.from('handbook_terms').upsert({
      term,
      slug,
      korean_name: koreanName || null,
      difficulty,
      category,
      related_term_slugs: relatedSlugs.length ? relatedSlugs : null,
      is_favourite: isFavourite,
      definition_ko: definition || null,
      plain_explanation_ko: plainExplanation || null,
      technical_description_ko: technicalDescription || null,
      example_analogy_ko: exampleAnalogy || null,
      body_markdown_ko: bodyMarkdown || null,
      // EN fields intentionally NULL
      definition_en: null,
      plain_explanation_en: null,
      technical_description_en: null,
      example_analogy_en: null,
      body_markdown_en: null,
      status: 'draft',
      notion_page_id: page.id,
    }, { onConflict: 'slug' });

    if (error) {
      console.error(`  ERROR inserting ${term}:`, error.message);
    }
  }

  console.log('Migration complete.');
}

main().catch(console.error);
```

**Step 2: Add required dependencies (if not already present)**

```bash
cd frontend/.. && npm install --save-dev @notionhq/client dotenv
```

Or run from project root. The script uses `npx tsx` to execute TypeScript directly.

**Step 3: Commit script (do NOT run yet — needs env vars)**

```bash
git add scripts/migrate-handbook-from-notion.ts
git commit -m "feat: add Notion → Supabase handbook migration script (KO only, status=draft)"
```

---

## Task 11: Run migration and verify data

**Prerequisite:** `.env` must have `NOTION_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `NOTION_WORDS_DB_ID`.

**Step 1: Run migration**

```bash
npx tsx scripts/migrate-handbook-from-notion.ts
```

Expected output:
```
Fetching Notion Words DB...
Found 10 terms.
  Inserting: LLM (llm)
  Inserting: RAG (rag)
  ...
Migration complete.
```

**Step 2: Verify in Supabase**

```sql
SELECT count(*) FROM handbook_terms;
-- Expected: matches Notion term count

SELECT term, slug, status, definition_ko IS NOT NULL as has_ko, definition_en IS NOT NULL as has_en
FROM handbook_terms ORDER BY term;
-- Expected: all has_ko = true, all has_en = false, all status = 'draft'
```

**Step 3: Verify via admin UI**

1. Navigate to `/admin/handbook/`
2. Confirm all terms appear with `Draft` status
3. Confirm KO: ✅, EN: ❌ badges

**No commit** — this is a data operation, not code.

---

## Task 12: QA verification

**Reference:** Design doc Section 6 (QA 체크리스트)

**Step 1: Build**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 2: Run all tests**

```bash
node frontend/tests/handbook-utils.test.cjs
node frontend/tests/handbook-nav.test.cjs
```
Expected: All pass

**Step 3: Manual checks**

After publishing at least 1 term via admin:

- [ ] `/en/handbook/` — list renders, cards visible
- [ ] `/ko/handbook/` — list renders, KO content shown
- [ ] Category filter works (click a category → only matching terms shown)
- [ ] Search: type "LLM" → matching term appears
- [ ] Search: type "대규모" → matching term appears (KO search)
- [ ] Search: no match → "No matching terms found" shown
- [ ] `/en/handbook/[slug]/` — detail page renders with infobox + body
- [ ] `/ko/handbook/[slug]/` — KO content shown
- [ ] EN page with missing EN content → KO fallback + "Translation in progress" banner
- [ ] Related Terms links work
- [ ] Back to Handbook link works
- [ ] Navigation: Handbook link between Log and Portfolio
- [ ] Language switcher: `/en/handbook/` ↔ `/ko/handbook/` works
- [ ] `/admin/handbook/` — list shows all terms with status badges
- [ ] Admin status filter tabs (All / Draft / Published)
- [ ] Admin edit page: KO/EN tab switch works
- [ ] Admin Save Draft saves without publishing
- [ ] Admin Publish validates required fields then publishes
- [ ] Mobile: responsive layout OK

**Step 4: Fix any issues found, commit**

```bash
git add -A
git commit -m "fix: QA fixes for handbook H1"
```

---

## Summary: Commit Sequence

| # | Commit | Files |
|---|--------|-------|
| 1 | `feat: create handbook_terms table with bilingual schema` | migration SQL |
| 2 | `feat: add handbook category + locale utility functions` | lib + test |
| 3 | `feat: add handbook i18n strings (en/ko)` | i18n |
| 4 | `feat: add handbook list pages (en/ko) with search + category filter` | pages |
| 5 | `feat: add handbook detail pages (en/ko) with infobox, related terms/articles` | pages |
| 6 | `feat: add Handbook link to navigation` | nav + test |
| 7 | `feat: add authenticated Supabase client helper for admin pages` | lib |
| 8 | `feat: add admin handbook list page with status filter + completeness badges` | admin page |
| 9 | `feat: add admin handbook edit page with KO/EN tabs and save/publish actions` | admin page |
| 10 | `feat: add Notion → Supabase handbook migration script (KO only, status=draft)` | script |
| 11 | Data migration (no commit) | — |
| 12 | `fix: QA fixes for handbook H1` | varies |
