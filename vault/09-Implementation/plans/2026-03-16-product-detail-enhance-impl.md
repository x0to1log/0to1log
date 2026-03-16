# Product 상세페이지 강화 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Product 상세페이지에 Key Features, Use Cases, Alternatives, FAQ 섹션 추가 + AI 프롬프트 Few-shot/CoT 개선

**Architecture:** DB에 features/use_cases 컬럼 추가 → AI 프롬프트에 Few-shot + CoT → 상세페이지 컴포넌트 확장 → Admin 에디터 확장

**Tech Stack:** Astro v5, Supabase (PostgreSQL jsonb), OpenAI gpt-4o, vanilla JS

**Design doc:** `vault/09-Implementation/plans/2026-03-16-product-detail-enhance-design.md`

---

## Task 1: DB 마이그레이션 — features, use_cases 컬럼

**Files:**
- Create: `supabase/migrations/00024_product_features_usecases.sql`

```sql
ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS features jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS use_cases jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN ai_products.features IS 'Key feature bullets (EN strings array)';
COMMENT ON COLUMN ai_products.use_cases IS 'Use case scenarios (EN strings array)';
```

**Commit:**
```bash
git add supabase/migrations/00024_product_features_usecases.sql
git commit -m "feat: add features and use_cases columns to ai_products"
```

---

## Task 2: AI 프롬프트 리라이트 — Few-shot + CoT + 새 필드

**Files:**
- Modify: `backend/services/agents/product_advisor.py`

**변경 내용:**

### Step 1: GENERATE_FROM_URL_SYSTEM 전면 리라이트

프롬프트 구조:
1. Role & audience
2. Chain-of-Thought instruction (제품 분석 먼저, JSON 생성 후)
3. 필드 정의 (기존 8개 + features, features_ko, use_cases, use_cases_ko = 12개)
4. Few-shot 예시 4개 (ChatGPT, Cursor, Midjourney, n8n)
5. Self-verification checklist
6. Output JSON schema

### Step 2: 새 필드 정의 추가

```
9. **features** (EN, array of 3-5 strings):
   - Each: one specific capability in one sentence
   - Start with a verb: "Generates...", "Supports...", "Connects..."
   - BAD: "Advanced AI technology" (vague)
   - GOOD: "Generates unit tests from function signatures" (specific)

10. **features_ko** (KO, array of 3-5 strings):
    - Same features, naturally written in Korean

11. **use_cases** (EN, array of 2-3 strings):
    - Each: "[Who] + [when/what situation]"
    - BAD: "For developers" (too broad)
    - GOOD: "Frontend developers prototyping UI from design mockups" (specific)

12. **use_cases_ko** (KO, array of 2-3 strings):
    - Same use cases in Korean, "[대상]이 [상황]할 때" format
```

### Step 3: Few-shot 예시 4개 삽입

design doc에서 승인된 ChatGPT, Cursor, Midjourney, n8n 예시 사용. 각 예시에 features, use_cases 포함.

### Step 4: Chain-of-Thought instruction

```
Before generating JSON, silently analyze:
1. What category does this fit?
2. What is the ONE thing this product does best?
3. Who is the primary user?
4. What differentiates it from alternatives?
Do NOT output this analysis — use it to inform your JSON.
```

### Step 5: Self-verification

```
Before returning, verify:
- tagline ≤12 words, starts with verb/specific noun
- tagline does NOT contain: "AI-powered", "revolutionary", "cutting-edge", "innovative"
- description sentence 1 = concrete action, not category label
- features = specific capabilities, not vague benefits
- use_cases = real scenarios with real user types
- If data is not available from the page, use null or empty array — do NOT fabricate
```

**Commit:**
```bash
git add backend/services/agents/product_advisor.py
git commit -m "feat: rewrite product AI prompt with few-shot, CoT, features/use_cases"
```

---

## Task 3: Data Layer — ProductDetailData 확장 + fetchAlternatives

**Files:**
- Modify: `frontend/src/lib/pageData/productsPage.ts`

### Step 1: ProductDetailData 타입에 추가

```ts
features: string[];
features_ko: string[];
use_cases: string[];
use_cases_ko: string[];
```

### Step 2: getProductDetailData()에서 새 필드 매핑

```ts
features: (raw.features as string[]) ?? [],
features_ko: (raw.features_ko as string[]) ?? [],
use_cases: (raw.use_cases as string[]) ?? [],
use_cases_ko: (raw.use_cases_ko as string[]) ?? [],
```

참고: DB에는 features/use_cases만 있고 _ko는 없음. features_ko/use_cases_ko는 features/use_cases 안에 EN/KO를 분리 저장하거나, 단일 필드에 EN만 저장하고 locale별로 보여줌. → **단순화: features/use_cases는 EN 전용, KO는 AI가 같이 생성해서 별도 컬럼 없이 description_ko처럼 처리.**

**수정:** features_ko, use_cases_ko는 DB 컬럼 추가 대신, 프론트에서 locale === 'ko'일 때 features/use_cases를 그대로 표시 (영어 기능명은 한국어 독자도 이해 가능). 또는 Task 1 마이그레이션에 features_ko, use_cases_ko도 추가.

→ **결정: features_ko, use_cases_ko 컬럼도 추가.** AI가 한 번에 생성하므로 비용 차이 없고, 한국어 독자 경험 향상.

Task 1 마이그레이션 수정:
```sql
ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS features jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS features_ko jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS use_cases jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS use_cases_ko jsonb DEFAULT '[]'::jsonb;
```

### Step 3: fetchAlternatives 함수 추가

```ts
export async function fetchAlternatives(
  category: string,
  excludeSlug: string,
  limit = 4,
): Promise<ProductCardData[]> {
  const db = getPublicSupabase();
  if (!db) return [];
  const { data } = await db
    .from('ai_products')
    .select(CARD_COLUMNS)
    .eq('primary_category', category)
    .eq('is_published', true)
    .neq('slug', excludeSlug)
    .order('featured', { ascending: false })
    .order('sort_order')
    .limit(limit);
  return (data ?? []) as ProductCardData[];
}
```

**Commit:**
```bash
git add frontend/src/lib/pageData/productsPage.ts
git commit -m "feat: add features/use_cases to ProductDetailData + fetchAlternatives"
```

---

## Task 4: ProductDetail 컴포넌트 — 4개 새 섹션

**Files:**
- Modify: `frontend/src/components/products/ProductDetail.astro`

### Step 1: Props에 alternatives 추가

```ts
interface Props {
  product: ProductDetailData;
  htmlDescription: string;
  locale: 'en' | 'ko';
  alternatives: ProductCardData[];  // NEW
}
```

### Step 2: Key Features 섹션 (Description 아래, main 영역)

```astro
{features.length > 0 && (
  <section class="product-detail-features">
    <h2>{locale === 'ko' ? '주요 기능' : 'Key Features'}</h2>
    <ul>
      {features.map((f) => <li>{f}</li>)}
    </ul>
  </section>
)}
```

### Step 3: Use Cases 섹션

```astro
{useCases.length > 0 && (
  <section class="product-detail-usecases">
    <h2>{locale === 'ko' ? '이런 상황에 추천' : 'Use Cases'}</h2>
    <ul>
      {useCases.map((u) => <li>{u}</li>)}
    </ul>
  </section>
)}
```

### Step 4: Alternatives 섹션 (main+sidebar 아래, 풀폭)

```astro
{alternatives.length > 0 && (
  <section class="product-detail-alternatives">
    <h2>{locale === 'ko' ? '비슷한 도구' : 'Similar Tools'}</h2>
    <div class="product-grid product-grid--preview">
      {alternatives.map((alt) => (
        <ProductCard ... />
      ))}
    </div>
  </section>
)}
```

### Step 5: FAQ 섹션 (템플릿 기반)

```astro
<section class="product-detail-faq">
  <h2>FAQ</h2>
  <!-- pricing FAQ -->
  <details>
    <summary>{locale === 'ko' ? `${name}은(는) 무료인가요?` : `Is ${name} free?`}</summary>
    <p>{pricingAnswer}</p>
  </details>
  <!-- platform FAQ (조건부) -->
  <!-- korean_support FAQ (조건부) -->
  <!-- usage FAQ from tags+tagline (조건부) -->
</section>
```

**Commit:**
```bash
git add frontend/src/components/products/ProductDetail.astro
git commit -m "feat: add Key Features, Use Cases, Alternatives, FAQ to product detail"
```

---

## Task 5: [slug].astro 페이지 — alternatives 데이터 전달

**Files:**
- Modify: `frontend/src/pages/en/products/[slug].astro`
- Modify: `frontend/src/pages/ko/products/[slug].astro`

getProductDetailData() + fetchAlternatives() 호출 → ProductDetail에 alternatives prop 전달.

**Commit:**
```bash
git add frontend/src/pages/en/products/[slug].astro frontend/src/pages/ko/products/[slug].astro
git commit -m "feat: pass alternatives data to product detail pages"
```

---

## Task 6: CSS — 새 섹션 스타일

**Files:**
- Modify: `frontend/src/styles/global.css`

```css
.product-detail-features { ... }
.product-detail-features ul { ... }
.product-detail-usecases { ... }
.product-detail-alternatives { ... }
.product-detail-faq { ... }
.product-detail-faq details { ... }
.product-detail-faq summary { ... }
```

기존 product-detail 스타일 패턴 따름. 모든 테마에서 동작.

**Commit:**
```bash
git add frontend/src/styles/global.css
git commit -m "feat: add CSS for product detail features/usecases/alternatives/faq"
```

---

## Task 7: Admin 에디터 — features/use_cases 에디터 + AI Apply 확장

**Files:**
- Modify: `frontend/src/pages/admin/products/edit/[slug].astro`

### Step 1: features/use_cases 에디터 UI
- demo_media 에디터와 동일 패턴 (add/remove rows)
- features: 텍스트 입력 row × N, + Add Feature 버튼
- use_cases: 동일 패턴, + Add Use Case 버튼

### Step 2: getPayload()에 features/use_cases 추가

### Step 3: AI Apply에서 features/use_cases 채움

**Commit:**
```bash
git add frontend/src/pages/admin/products/edit/[slug].astro
git commit -m "feat: add features/use_cases editor + AI apply to admin"
```

---

## Task 8: 최종 빌드 + QA

- `npm run build` 0 errors 확인
- 상세페이지 렌더링 확인 (features, use_cases, alternatives, FAQ)
- Admin에서 AI Generate → features/use_cases 채워지는지 확인
- 4개 테마 확인

---

## 실행 순서

```
Task 1: DB migration (features, use_cases, features_ko, use_cases_ko)
Task 2: AI 프롬프트 리라이트 (Few-shot + CoT + 새 필드)
Task 3: Data layer (타입 확장 + fetchAlternatives)
Task 4: ProductDetail 컴포넌트 (4개 새 섹션)
Task 5: [slug].astro 페이지 (alternatives 전달)
Task 6: CSS
Task 7: Admin 에디터 (features/use_cases + AI Apply)
Task 8: 빌드 + QA
```
