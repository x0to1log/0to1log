# AI Product Search Corpus Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 사용자가 의도 기반으로 검색("영상 만들고 싶어", "코드 리뷰 자동화")해도 적절한 AI 제품이 매칭되도록, GPT가 생성한 검색 키워드 코퍼스를 DB에 저장하고 클라이언트 검색에 통합한다.

**Architecture:** 제품 저장/AI 생성 시 GPT가 의도 문구·동의어·유사 표현을 포함한 `search_corpus` 텍스트를 생성 → DB `ai_products.search_corpus` 컬럼에 저장 → SSR 시 `buildSearchText()`에 포함 → 기존 클라이언트 `string.includes()` 필터링이 의도 매칭까지 커버.

**Tech Stack:** Supabase (PostgreSQL), FastAPI (OpenAI GPT-4o-mini), Astro SSR, client-side JS filtering

---

## Task 1: DB Migration — search_corpus 컬럼 추가

**Files:**
- Create: `supabase/migrations/00038_product_search_corpus.sql`

**Step 1: Write migration SQL**

```sql
-- 00038_product_search_corpus.sql
-- Add search_corpus column for AI-generated intent-based search keywords.

ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS search_corpus text;

COMMENT ON COLUMN ai_products.search_corpus
  IS 'AI-generated search keywords: intent phrases, synonyms, related terms (KO+EN mixed). Used for client-side text matching.';
```

**Step 2: Apply migration**

Run in Supabase SQL Editor or via CLI.

**Step 3: Commit**

```bash
git add supabase/migrations/00038_product_search_corpus.sql
git commit -m "feat(db): add search_corpus column to ai_products"
```

---

## Task 2: Backend — search_corpus 생성 프롬프트 + 액션 추가

**Files:**
- Modify: `backend/models/product_advisor.py` (action Literal에 `generate_search_corpus` 추가)
- Modify: `backend/services/agents/product_advisor.py` (프롬프트 + 핸들러 추가)

**Step 1: Add action to Pydantic model**

`backend/models/product_advisor.py` — `ProductGenerateRequest.action` Literal에 `"generate_search_corpus"` 추가.

**Step 2: Add SEARCH_CORPUS_SYSTEM prompt**

`backend/services/agents/product_advisor.py` — 새 프롬프트 상수 추가:

```python
SEARCH_CORPUS_SYSTEM = """You generate search keywords for an AI product directory.
Given a product's name, URL, category, tagline, description, features, and use cases,
produce a single block of space-separated keywords and short phrases that a user might type
when looking for this kind of tool.

## Requirements

1. Include ALL of these keyword types:
   - Product name variants: full name, abbreviations, common misspellings
   - Korean name/transliteration if applicable
   - Intent phrases (KO): "~하고 싶을 때", "~하는 방법", "~하려면", "~추천"
   - Intent phrases (EN): "how to ~", "best tool for ~", "~ alternative"
   - Action verbs (KO+EN): what the user DOES with this tool
   - Synonyms and related terms for core functionality
   - Target audience keywords: roles, industries, skill levels
   - Problem keywords: what pain point does this solve?
   - Comparison terms: "vs", "alternative to [competitor]"
   - Category and subcategory terms in both languages

2. Format: One continuous block of text. No JSON, no bullets, no line breaks.
   Just space-separated words and short phrases.

3. Length: 150-300 words. Be comprehensive but not repetitive.

4. Language: Mix Korean and English naturally. Korean users often search in mixed language.

## Example

For a product like "Runway" (video generation):
runway 런웨이 영상 생성 비디오 만들기 동영상 제작 AI영상 영상편집 영상만들고싶을때 동영상만들기 video generation video editing text to video 텍스트로영상 광고영상제작 뮤직비디오 숏폼 shorts 릴스 모션그래픽 motion graphics animate 애니메이션 영상AI추천 video ai tool 마케터 크리에이터 유튜버 콘텐츠제작 영상편집도구 무료영상편집 video creator alternative to premiere 프리미어대안 영상자동생성 ai video editor 영상제작방법 how to make ai video best video ai ...

Respond with the keyword text only — no explanation, no formatting."""
```

**Step 3: Add handler in `run_product_generate`**

`generate_search_corpus` 액션 분기 추가. 제품의 기존 필드들(name, tagline, description, features, use_cases, category, tags)을 컨텍스트로 전달:

```python
elif body.action == "generate_search_corpus":
    model = settings.openai_model_light
    context_parts = []
    if body.name:
        context_parts.append(f"Product: {body.name}")
    if body.url:
        context_parts.append(f"URL: {body.url}")
    if body.context:
        context_parts.append(f"Product details:\n{body.context}")
    user_content = "\n".join(context_parts) or "Generate search keywords for this AI product."

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SEARCH_CORPUS_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        max_tokens=800,
        temperature=0.7,
    )
    raw = response.choices[0].message.content or ""
    metrics = extract_usage_metrics(response, model)
    return raw.strip(), metrics["model_used"], metrics["tokens_used"]
```

이 분기는 기존 `run_product_generate` 함수의 `if body.action == "generate_from_url":` 블록과 개별 필드 생성 블록 사이에 `elif`로 삽입.

**Step 4: Also generate search_corpus within `generate_from_url` (3rd parallel call)**

`generate_from_url` 액션에서 프로필(call1) + 보강(call2) 결과가 나온 뒤, search_corpus도 자동 생성하여 result에 포함:

```python
# After merging call1 + call2 results, add search_corpus generation
if isinstance(result, dict) and result:
    corpus_context = "\n".join([
        f"Name: {result.get('tagline', '')}",
        f"Category: {result.get('primary_category', '')}",
        f"Tags: {', '.join(result.get('tags', []))}",
        f"Description: {result.get('description_en', '')}",
        f"Features: {'; '.join(result.get('features', []))}",
        f"Use cases: {'; '.join(result.get('use_cases', []))}",
    ])
    try:
        corpus_resp = await client.chat.completions.create(
            model=settings.openai_model_light,
            messages=[
                {"role": "system", "content": SEARCH_CORPUS_SYSTEM},
                {"role": "user", "content": f"Product: {product_name}\nURL: {body.url}\n\n{corpus_context}"},
            ],
            max_tokens=800,
            temperature=0.7,
        )
        corpus_metrics = extract_usage_metrics(corpus_resp, settings.openai_model_light)
        total_tokens += corpus_metrics["tokens_used"]
        result["search_corpus"] = (corpus_resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning("Search corpus generation failed: %s", e)
```

> 주의: 이 호출은 call1+call2 완료 후 순차 실행 (결과 데이터가 필요하므로). 지연 약 1-2초 추가.

**Step 5: Commit**

```bash
git add backend/models/product_advisor.py backend/services/agents/product_advisor.py
git commit -m "feat(ai): add search_corpus generation to product advisor"
```

---

## Task 3: Frontend — save API에 search_corpus 필드 추가

**Files:**
- Modify: `frontend/src/pages/api/admin/products/save.ts`

**Step 1: Add search_corpus to destructuring + row mapping**

`save.ts`의 body destructuring에 `search_corpus` 추가:
```typescript
const { ..., search_corpus } = body;
```

row 매핑에 추가:
```typescript
if (search_corpus !== undefined) row.search_corpus = search_corpus || null;
```

**Step 2: Commit**

```bash
git add frontend/src/pages/api/admin/products/save.ts
git commit -m "feat(admin): pass search_corpus field through save API"
```

---

## Task 4: Frontend — 어드민 에디터에 search_corpus UI 추가

**Files:**
- Modify: `frontend/src/pages/admin/products/edit/[slug].astro`

**Step 1: Add hidden input for search_corpus data**

기존 hidden inputs 영역(line ~108-120)에 추가:
```html
<input type="hidden" id="product-search-corpus" value={product?.search_corpus || ''} />
```

**Step 2: Add search_corpus textarea in editor form**

에디터 폼의 적절한 위치(pricing_detail 섹션 근처)에 추가:
```html
<div class="admin-editor-meta-row" style="align-items: flex-start;">
  <label class="admin-field-label" style="padding-top: 6px;">Search Keywords</label>
  <textarea class="admin-input" id="field-search-corpus" rows="4"
    placeholder="AI-generated search keywords (auto-filled)"
    style="font-size: 0.8rem; color: var(--color-text-muted);"
  >{product?.search_corpus || ''}</textarea>
</div>
```

**Step 3: Add "Generate Keywords" button to AI Advisor panel**

기존 AI 액션 버튼들(line ~466-487) 아래에 추가:
```html
<button class="admin-ai-action-btn" data-action="generate_search_corpus" type="button">
  <span>Search Keywords</span>
</button>
```

**Step 4: Wire up AI action handler for search_corpus**

1. `actionLabels` 맵에 추가:
```javascript
generate_search_corpus: 'Search Keywords',
```

2. `targetMap`에 추가:
```javascript
generate_search_corpus: 'field-search-corpus',
```

**Step 5: Wire up `generate_from_url` apply to include search_corpus**

`ai-apply-btn` 클릭 핸들러의 `generate_from_url` 분기에 추가:
```javascript
if (parsed.search_corpus) {
  const el = document.getElementById('field-search-corpus');
  if (el) el.value = parsed.search_corpus;
}
```

**Step 6: Include search_corpus in save payload**

save 버튼의 payload 구성 부분에 추가:
```javascript
search_corpus: document.getElementById('field-search-corpus')?.value || null,
```

**Step 7: Wire up standalone action — context 전달**

`generate_search_corpus` 액션일 때, 현재 폼의 기존 데이터를 `context`로 전달하도록 fetch body 수정:

AI 액션 버튼 클릭 핸들러에서 fetch body를 만드는 부분(line ~1202):
```javascript
const fetchBody = { action, url, name };
if (action === 'generate_search_corpus') {
  // Gather existing product details as context
  const contextParts = [
    `Category: ${document.getElementById('field-category')?.value || ''}`,
    `Tagline: ${document.getElementById('field-tagline')?.value || ''}`,
    `Tagline KO: ${document.getElementById('field-tagline-ko')?.value || ''}`,
    `Description: ${document.getElementById('field-description')?.value || ''}`,
    `Description KO: ${document.getElementById('field-description-ko')?.value || ''}`,
    `Tags: ${document.getElementById('field-tags')?.value || ''}`,
    `Platform: ${document.getElementById('field-platform')?.value || ''}`,
  ];
  // Features
  document.querySelectorAll('#features-list .string-list-input').forEach((el) => {
    if (el.value) contextParts.push(`Feature: ${el.value}`);
  });
  document.querySelectorAll('#usecases-list .string-list-input').forEach((el) => {
    if (el.value) contextParts.push(`Use case: ${el.value}`);
  });
  fetchBody.context = contextParts.join('\n');
}
```

**Step 8: Commit**

```bash
git add frontend/src/pages/admin/products/edit/[slug].astro
git commit -m "feat(admin): add search_corpus UI and AI generation to product editor"
```

---

## Task 5: Frontend — 공개 페이지 검색에 search_corpus 통합

**Files:**
- Modify: `frontend/src/lib/pageData/productsPage.ts` (CARD_COLUMNS에 `search_corpus` 추가)
- Modify: `frontend/src/pages/ko/products/index.astro` (buildSearchText에 포함)
- Modify: `frontend/src/pages/en/products/index.astro` (동일)

**Step 1: Add search_corpus to CARD_COLUMNS**

`productsPage.ts` line 117:
```typescript
const CARD_COLUMNS =
  'id, slug, name, name_ko, tagline, tagline_ko, logo_url, thumbnail_url, pricing, platform, korean_support, primary_category, featured, featured_order, demo_media, view_count, sort_order, tags, difficulty, search_corpus';
```

**Step 2: Update buildSearchText in ko/products/index.astro**

```typescript
const buildSearchText = (product: typeof allProducts[0]) =>
  [
    product.name,
    (product as any).name_ko,
    product.tagline,
    (product as any).tagline_ko,
    product.pricing,
    product.pricing ? pricingKo[product.pricing] : null,
    product.primary_category,
    categoryKo[product.primary_category],
    ...(product.platform ?? []),
    ...(product.tags ?? []),
    (product as any).search_corpus,
  ].filter(Boolean).join(' ').toLowerCase();
```

**Step 3: Same update in en/products/index.astro**

동일하게 `(product as any).search_corpus` 추가.

**Step 4: Commit**

```bash
git add frontend/src/lib/pageData/productsPage.ts frontend/src/pages/ko/products/index.astro frontend/src/pages/en/products/index.astro
git commit -m "feat(search): integrate search_corpus into client-side product filtering"
```

---

## Task 6: Build 확인 + 전체 커밋

**Step 1: Build check**

```bash
cd frontend && npm run build
```

0 errors 확인.

**Step 2: Manual verification**

1. 어드민 `/admin/products/edit/chatgpt/` → AI Advisor → "Search Keywords" 버튼 클릭 → 키워드 텍스트 생성 확인
2. 같은 페이지 → "Generate from URL" → Apply → search_corpus 필드에 자동 채워지는지 확인
3. Save → DB에 `search_corpus` 저장 확인
4. 공개 `/ko/products/` → 검색창에 "영상 만들고 싶어" 입력 → Runway 등 비디오 제품 노출 확인 (search_corpus가 채워진 제품에 한함)

---

## 향후 고려사항 (이번 범위 밖)

- **기존 144개 제품 일괄 생성**: 어드민에 "Batch Generate Keywords" 버튼 or 백엔드 cron
- **자동 재생성**: 제품 핵심 필드(description, features) 변경 시 search_corpus 자동 갱신
- **퍼지 매칭**: Levenshtein distance나 초성 검색 추가
