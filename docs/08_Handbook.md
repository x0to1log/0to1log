# 08_Handbook

> 문서 버전: v1.2
> 최종 수정: 2026-04-12
> 작성자: Amy (Solo)
> 상태: Active Spec
> 연관 문서: `01_Project_Overview.md`, `IMPLEMENTATION_PLAN.md`, `docs/plans/2026-03-07-handbook-feature.md`

---

## 1. 개요

`AI Glossary`는 0to1log의 용어 참조 레이어다. 목적은 단순 정의 사전이 아니라, AI News와 Blog를 읽다가 막히는 개념을 빠르게 이해하고 다시 본문으로 돌아가게 만드는 것이다.

핵심 역할:
- AI / CS / Infra / Math 관련 용어를 EN/KO로 제공
- 공개 상세 페이지에서 `definition + hero card + basic / advanced body + references` 구조 제공
- 뉴스/블로그 본문에서 handbook popup과 상세 링크로 연결
- 로그인 사용자의 저장, 읽기 기록, 학습 완료 흐름과 연결
- admin에서 용어 생성, 저장, 검토, 발행, 보완 요청 처리

Naming boundary:
- Public product language: `AI News`, `AI Glossary`, `My Library`
- Internal/admin language: `Posts`, `Handbook`
- Public route compatibility: `/{locale}/handbook/`

---

## 2. Canonical Runtime Source of Truth

이 문서는 2026-04-12 기준 현재 런타임 계약을 반영한다. 실제 구현의 최종 출처는 아래다.

- Schema / migrations:
  - `supabase/migrations/00003_handbook_terms.sql`
  - `supabase/migrations/00010_source_columns.sql`
  - `supabase/migrations/00012_handbook_difficulty_levels.sql`
  - `supabase/migrations/00019_handbook_term_names.sql`
  - `supabase/migrations/00024_handbook_view_count.sql`
  - `supabase/migrations/00028_handbook_queued_status.sql`
  - `supabase/migrations/00033_handbook_quality_scores.sql`
  - `supabase/migrations/00047_handbook_term_type_facets.sql`
  - `supabase/migrations/00048_handbook_redesign_columns.sql`
- Public pages:
  - `frontend/src/lib/pageData/handbookPage.ts`
  - `frontend/src/lib/pageData/handbookDetailPage.ts`
  - `frontend/src/pages/{en,ko}/handbook/*`
- Admin pages / APIs:
  - `frontend/src/pages/admin/handbook/*`
  - `frontend/src/pages/api/admin/handbook/*`
  - `frontend/src/pages/api/admin/ai/handbook-advise.ts`
- Backend AI pipeline:
  - `backend/routers/admin_ai.py`
  - `backend/services/agents/advisor.py`
  - `backend/services/agents/prompts_advisor.py`
  - `backend/models/advisor.py`

주의:
- 이 문서는 "원하는 미래 구조"가 아니라 "현재 코드가 실제로 쓰는 구조"를 설명한다.
- 핸드북 운영 흐름은 `docs/plans/2026-03-07-handbook-feature.md`를 함께 본다.

---

## 3. 현재 데이터 모델

### 3.1 canonical handbook_terms schema

현재 런타임 기준 handbook 주요 필드는 아래와 같다.

```sql
CREATE TABLE handbook_terms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  term TEXT NOT NULL,
  term_full TEXT,
  slug TEXT UNIQUE NOT NULL,
  korean_name TEXT,
  korean_full TEXT,

  categories TEXT[],
  related_term_slugs TEXT[],
  is_favourite BOOLEAN DEFAULT FALSE,
  source TEXT NOT NULL DEFAULT 'manual',

  definition_ko TEXT,
  definition_en TEXT,
  body_basic_ko TEXT,
  body_basic_en TEXT,
  body_advanced_ko TEXT,
  body_advanced_en TEXT,

  hero_news_context_ko TEXT,
  hero_news_context_en TEXT,
  references_ko JSONB,
  references_en JSONB,
  sidebar_checklist_ko TEXT,
  sidebar_checklist_en TEXT,

  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('queued', 'draft', 'published', 'archived')),
  notion_page_id TEXT,
  view_count INT DEFAULT 0,

  term_type TEXT,
  facet_intent TEXT[] DEFAULT '{}',
  facet_volatility TEXT DEFAULT 'stable',

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ
);
```

추가 메모:
- `source` 값은 현재 `manual`, `pipeline`, `ai-suggested`를 사용한다.
- `hero_news_context_*`와 `references_*`는 2026-04 redesign 이후 공개 상세와 admin editor에서 실제 사용 중인 level-independent 필드다.
- `sidebar_checklist_*` 컬럼은 DB에는 존재하지만, 현재 런타임 기준으로는 handbook model / admin save / public render에 아직 연결되어 있지 않다.

### 3.2 auxiliary tables

#### profiles.handbook_level

```sql
ALTER TABLE profiles
ADD COLUMN handbook_level TEXT DEFAULT 'basic'
CHECK (handbook_level IN ('basic', 'advanced'));
```

의미:
- handbook 상세는 로그인 사용자 profile의 `handbook_level`을 우선 사용
- preview mode에서는 `previewLevel` query param이 우선
- 공개 페이지에서는 `basic / advanced` 스위처로 즉시 전환 가능

#### term_feedback

```sql
CREATE TABLE term_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  term_id UUID NOT NULL REFERENCES handbook_terms(id) ON DELETE CASCADE,
  locale TEXT NOT NULL CHECK (locale IN ('en', 'ko')),
  reaction TEXT NOT NULL CHECK (reaction IN ('helpful', 'confusing')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, term_id, locale)
);
```

의미:
- handbook 상세 하단의 `도움 됨 / 헷갈림` 반응 저장
- 댓글이 아니라 lightweight feedback 수집용
- authenticated user만 자기 row를 읽고 쓸 수 있음

#### handbook_quality_scores

```sql
CREATE TABLE handbook_quality_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  term_id UUID REFERENCES handbook_terms(id) ON DELETE CASCADE,
  term_slug TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
  breakdown JSONB DEFAULT '{}'::jsonb,
  term_type TEXT,
  source TEXT NOT NULL DEFAULT 'pipeline' CHECK (source IN ('pipeline', 'manual')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

의미:
- handbook generate 시 basic / advanced 품질 점수를 이력으로 기록
- pipeline과 manual generate를 같은 테이블에 저장

### 3.3 legacy compatibility

과거 handbook 초안에는 아래 필드가 사용됐다.
- `difficulty`
- `plain_explanation_*`
- `technical_description_*`
- `example_analogy_*`
- `body_markdown_*`

`00012_handbook_difficulty_levels.sql`에서 현재 구조로 마이그레이션하면서:
- `body_basic_*`는 기존 `body_markdown + plain_explanation + example_analogy`를 합친 본문으로 seed
- `body_advanced_*`는 기존 `technical_description_*`를 seed
- `profiles.handbook_level` 추가
- legacy column drop 완료

중요:
- 현재 canonical handbook schema에는 `difficulty`, `plain_explanation_*`, `technical_description_*`, `example_analogy_*`, `body_markdown_*`가 더 이상 포함되지 않는다.

### 3.4 status lifecycle

현재 코드가 전제하는 status는 아래 4개다.

- `queued`: pipeline이 제목/slug 중심으로 후보를 만든 상태. admin approve 전
- `draft`: admin이 편집 가능한 상태. save 가능, publish 전
- `published`: 공개 노출 상태
- `archived`: 보관 상태

admin action 의미:
- `approve`: `queued -> draft`
- `publish`: `draft -> published`
- `unpublish`: `published -> draft`
- `archive`: `draft/published -> archived`

---

## 4. 카테고리 체계

과거 문서의 넓은 `AI / CS / Infra` 프레이밍은 유지하되, 실제 저장과 필터링은 아래 9개 canonical slug를 사용한다.

- `products-platforms`: Products & Platforms
- `llm-genai`: LLM & Generative AI
- `deep-learning`: Deep Learning
- `ml-fundamentals`: ML Fundamentals
- `data-engineering`: Data Engineering
- `infra-hardware`: Infra & Hardware
- `safety-ethics`: AI Safety & Ethics
- `cs-fundamentals`: CS Fundamentals
- `math-statistics`: Math & Statistics

운영 규칙:
- editor에서는 1~4개 category를 선택한다
- public list / category pages / admin filters 모두 이 slug 집합을 canonical contract로 사용한다
- category label과 description의 최종 출처는 `frontend/src/lib/handbookCategories.ts`

---

## 5. 공개 페이지 구조

### 5.1 목록 페이지

경로:
- `/en/handbook/`
- `/ko/handbook/`

현재 목록 페이지 계약:
- published term만 노출
- 기본 정렬은 `term ASC`
- 검색창 1개
- category filter 제공
- 인기 용어(trending)는 `view_count DESC` 기준, 값이 없으면 `published_at DESC` 폴백
- category showcase cards 제공
- 카드 데이터는 아래 중심:
  - `term`
  - `korean_name`
  - localized `definition` excerpt
  - category pills
  - bookmark / reading state

우측 rail:
- glossary intro
- popular terms
- category browse 성격의 보조 정보

### 5.2 상세 페이지

경로:
- `/en/handbook/[slug]/`
- `/ko/handbook/[slug]/`

현재 상세 페이지는 아래 5개 렌더링 존을 가진다.

1. Hero Card
   - `definition`
   - `hero_news_context`
2. Level Switcher
   - `basic / advanced`
   - preview mode에서는 `previewLevel`로 초기 상태 지정 가능
3. Body
   - `body_basic`
   - `body_advanced`
   - markdown -> HTML 렌더링
4. References Footer
   - `references_*`
   - Basic / Advanced와 무관한 level-independent footer
5. Right Rail / Action Area
   - related terms
   - same category terms
   - related articles
   - bookmark / share / reading actions
   - content feedback

필드 선택 규칙:

```ts
const definition = localField(term, 'definition', locale);
const bodyBasic = localField(term, 'body_basic', locale);
const bodyAdvanced = localField(term, 'body_advanced', locale);
const heroNewsContext = localField(term, 'hero_news_context', locale);
const references =
  locale === 'ko' ? term.references_ko ?? term.references_en : term.references_en ?? term.references_ko;
```

fallback 규칙:
- text field는 `localField()` 기반 KO fallback 허용
- EN 상세에서 EN definition이 비어 있으면 translation pending notice를 보여줄 수 있음
- references는 locale 우선, 반대 locale JSONB를 폴백으로 사용

### 5.3 handbook popup

뉴스/블로그 본문에서 handbook popup은 현재 `definition` 중심으로 단순화되어 있다.

의도:
- 툴팁 안에 장문 본문을 넣지 않음
- 빠른 정의 확인 후 handbook 상세로 이동시키는 구조 유지

---

## 6. Admin 운영 구조

### 6.1 admin routes

- `/admin/handbook`
- `/admin/handbook/edit/[slug]`
- `/api/admin/handbook/save`
- `/api/admin/handbook/status`
- `/api/admin/handbook/bulk-action`
- `/api/admin/ai/handbook-advise`
- `/api/admin/ai/handbook-job/[jobId]`

### 6.2 admin list

admin handbook list는 아래 기능을 제공한다.

- status filter: `queued`, `draft`, `published`, `archived`, `all`
- source filter: `manual`, `pipeline`, `ai-suggested`
- search
- category filter
- bulk publish / unpublish / archive
- completeness dots:
  - KO Basic
  - KO Advanced
  - EN Basic
  - EN Advanced

참고:
- 현재 list completeness indicator는 hero / references 상태까지는 반영하지 않는다.

### 6.3 handbook editor current fields

현재 editor는 아래 필드를 직접 다룬다.

- `term`
- `slug`
- `term_full`
- `korean_name`
- `korean_full`
- `categories`
- `related_term_slugs`
- `is_favourite`
- `definition_ko`, `definition_en`
- `body_basic_ko`, `body_basic_en`
- `body_advanced_ko`, `body_advanced_en`
- `hero_news_context_ko`, `hero_news_context_en`
- `references_ko`, `references_en`

편집 구조:
- language tabs: KO / EN
- level tabs: Basic / Advanced
- level-independent redesign block: Hero / References
- sticky top action bar: Save / Preview / Publish / AI

editor에서 더 이상 핵심 입력 필드가 아닌 것:
- `difficulty`
- `plain_explanation_*`
- `technical_description_*`
- `example_analogy_*`
- `body_markdown_*`

### 6.4 save / publish current contract

#### Save

`/api/admin/handbook/save`는 아래를 저장한다.

- meta: `term`, `term_full`, `slug`, `korean_name`, `korean_full`
- taxonomy: `categories`, `related_term_slugs`, `is_favourite`, `source`
- content: `definition_*`, `body_basic_*`, `body_advanced_*`
- redesign: `hero_news_context_*`, `references_*`

#### Publish

현재 코드 기준 publish gate는 아래만 검증한다.

- `term`
- `slug`
- `definition_ko`
- `categories`
- `body_basic_ko` 또는 `body_advanced_ko`

즉, 현재 런타임 기준으로는 `hero_news_context_*`와 `references_*`가 비어 있어도 publish 자체는 가능하다. 이것은 현재 구현 계약이며, stricter gate는 별도 변경 작업으로 다룬다.

---

## 7. AI pipeline contract

핸드북 AI 작업은 아래 action을 가진다.

- `generate`
- `related_terms`
- `translate`
- `factcheck`
- `deepverify`

`generate` 결과의 canonical runtime 목적 필드는 아래다.

- meta / taxonomy:
  - `term_full`
  - `korean_name`
  - `korean_full`
  - `categories`
- public render content:
  - `definition_ko`, `definition_en`
  - `body_basic_ko`, `body_basic_en`
  - `body_advanced_ko`, `body_advanced_en`
  - `hero_news_context_ko`, `hero_news_context_en`
  - `references_ko`, `references_en`
- observability / quality:
  - `quality_score`
  - `basic_quality_score`
  - `term_type`
  - `facet_intent`
  - `facet_volatility`
  - internal `_search_sources`

상세 운영 흐름은 `docs/plans/2026-03-07-handbook-feature.md`를 따른다.

---

## 8. 검증 기준

핸드북 변경 시 최소 검증:
- public handbook list render 정상
- category filter 정상
- search 정상
- popular terms fallback 정상 (`view_count` 또는 `published_at`)
- detail page에서 Hero / Basic / Advanced / References 정상 렌더링
- level switcher 정상
- profile `handbook_level` 반영
- preview mode (`preview=1`, `previewLevel`) 정상
- handbook popup이 definition-only로 정상 동작
- feedback 버튼 반응 저장 정상
- admin handbook save / preview / publish 흐름 정상
- AI generate 후 editor diff apply 정상

SQL/데이터 검증 예시:

```sql
SELECT
  slug,
  status,
  source,
  categories,
  definition_ko,
  body_basic_ko,
  body_advanced_ko,
  hero_news_context_ko,
  references_ko,
  view_count,
  term_type,
  facet_intent,
  facet_volatility
FROM handbook_terms
LIMIT 5;
```

적어도 아래는 확인해야 한다.
- `categories`가 canonical slug 배열 형태로 저장됨
- `body_basic_*`, `body_advanced_*` 값 존재
- redesign 적용 term이면 `hero_news_context_*`, `references_*` 저장 가능
- `term_feedback` insert / upsert 가능
- `handbook_quality_scores` insert 가능

---

## 9. 현재 후속 과제 메모

현재 코드 기준에서 문서화해둘 운영 메모:
- `sidebar_checklist_*`는 DB에 있으나 아직 editor / public / AI model 계약에 연결되지 않음
- publish gate는 redesign 필드를 아직 강제하지 않음
- handbook quality scoring은 별도 테이블에 기록됨

---

## 10. 최종 Source of Truth 요약

- Schema: `supabase/migrations/00003, 00010, 00012, 00019, 00024, 00028, 00033, 00047, 00048`
- Public list/detail render: `frontend/src/lib/pageData/handbookPage.ts`, `frontend/src/lib/pageData/handbookDetailPage.ts`, `frontend/src/pages/{en,ko}/handbook/*`
- Admin save/publish/editor: `frontend/src/pages/admin/handbook/*`, `frontend/src/pages/api/admin/handbook/*`
- AI pipeline: `backend/routers/admin_ai.py`, `backend/services/agents/advisor.py`, `backend/services/agents/prompts_advisor.py`, `backend/models/advisor.py`
