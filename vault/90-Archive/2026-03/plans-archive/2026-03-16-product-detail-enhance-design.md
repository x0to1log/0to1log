# Product 상세페이지 강화 + AI 프롬프트 개선 — 설계

> Date: 2026-03-16
> Status: Approved
> Feature: 상세페이지 Key Features, Use Cases, Alternatives, FAQ + 프롬프트 Few-shot

---

## 동기

현재 상세페이지: Header + Media + Description + Sidebar만 있어 정보가 빈약.
Toolify 참고하되 지저분한 요소(광고, 중복 CTA, SEO 과다) 제거하고 깔끔한 우리 스타일로.

---

## 상세페이지 섹션 구조

```
Header (로고, 이름, tagline, pricing, "Visit Site" CTA)   ← 기존 유지
Media Gallery (스크린샷/영상)                              ← 기존 유지
Description (markdown)                                    ← 기존 유지
Key Features (3-5개 bullet)                               ← 신규
Use Cases (2-3개 시나리오)                                 ← 신규
Sidebar (pricing, platform, tags, stats, korean)          ← 기존 유지 (위치는 Description 옆)
Alternatives (같은 카테고리 제품 4개 카드)                   ← 신규
FAQ (데이터 기반 자동 생성)                                 ← 신규
```

---

## 1. Key Features

- DB 필드: `features` (jsonb, default `[]`)
- AI Generate from URL 시 함께 생성
- 3-5개 bullet point, 각각 한 문장
- 예시:

```json
[
  "Real-time code completion with full project context",
  "Multi-file refactoring with a single prompt",
  "Supports Claude, GPT-4o, and custom models"
]
```

### 렌더링
- `<h2>Key Features</h2>` / `<h2>주요 기능</h2>`
- `<ul>` bullet list
- Description 아래, Sidebar 옆 main 영역에 배치

---

## 2. Use Cases

- DB 필드: `use_cases` (jsonb, default `[]`)
- AI Generate from URL 시 함께 생성
- 2-3개 시나리오, 각각 "[대상]이 [상황]할 때" 형식
- 예시:

```json
[
  "Developers refactoring legacy codebases across multiple files",
  "Teams prototyping new features with AI-assisted code generation",
  "Solo developers who want IDE-level AI without switching editors"
]
```

### 렌더링
- `<h2>Use Cases</h2>` / `<h2>이런 상황에 추천</h2>`
- Card 또는 bullet list
- Key Features 아래

---

## 3. Alternatives

- DB 변경 없음
- 같은 `primary_category`에서 현재 제품 제외, `is_published = true`, limit 4
- 기존 ProductCard 컴포넌트 재사용
- 쿼리: `productsPage.ts`에 `fetchAlternatives(category, excludeSlug)` 추가

### 렌더링
- `<h2>Similar Tools</h2>` / `<h2>비슷한 도구</h2>`
- 4열 그리드 (데스크탑), 2열 (모바일)
- 상세페이지 main+sidebar 아래, 풀폭

---

## 4. FAQ (템플릿 기반)

- DB 변경 없음, 기존 필드에서 자동 생성
- 컴포넌트 내에서 JS/Astro 조건부 렌더링

| 조건 | 질문 (EN) | 질문 (KO) | 답변 소스 |
|------|-----------|-----------|----------|
| 항상 | Is {name} free? | {name}은(는) 무료인가요? | pricing + pricing_note |
| korean_support 존재 | Does {name} support Korean? | {name}이(가) 한국어를 지원하나요? | korean_support boolean |
| platform 존재 | What platforms is {name} available on? | {name}은(는) 어떤 플랫폼에서 사용할 수 있나요? | platform 배열 |
| tags 존재 | What is {name} used for? | {name}은(는) 어떤 용도로 쓰이나요? | tags + tagline 조합 |

### 렌더링
- `<h2>FAQ</h2>` / `<h2>자주 묻는 질문</h2>`
- `<details><summary>` 아코디언
- Alternatives 아래

---

## 5. AI 프롬프트 개선

### GENERATE_FROM_URL_SYSTEM 변경

**추가 필드:**
- `features`: 3-5개 영어 bullet strings
- `features_ko`: 3-5개 한국어 bullet strings
- `use_cases`: 2-3개 영어 시나리오 strings
- `use_cases_ko`: 2-3개 한국어 시나리오 strings

**Few-shot 예시 4개 추가 (프롬프트 내):**
- ChatGPT (assistant) — 가장 범용적
- Cursor (coding) — 개발자 타겟
- Midjourney (image) — 크리에이티브
- n8n (workflow) — 오픈소스/자동화

**Chain-of-Thought 추가:**
```
Before generating JSON, analyze the product:
1. What category does this fit? (assistant/image/video/audio/coding/workflow/builder/platform/research/community)
2. What is the ONE thing this product does best?
3. Who is the primary user?
4. What makes it different from alternatives?

Then generate the JSON.
```

**Self-verification 추가:**
```
Before returning, verify:
- tagline is ≤12 words and starts with a verb or specific noun
- tagline does NOT contain "AI-powered", "revolutionary", or "cutting-edge"
- description_en sentence 1 describes a concrete action, not a category
- features are specific capabilities, not vague benefits
- use_cases describe real scenarios with real users
```

---

## 6. DB 스키마 변경

```sql
ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS features jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS use_cases jsonb DEFAULT '[]'::jsonb;
```

---

## 7. Admin 에디터 변경

- features 에디터: bullet list (add/remove rows, 텍스트 입력)
- use_cases 에디터: 동일 패턴
- AI Apply 시 features, use_cases도 자동 채움

---

## 8. 영향 범위

| 파일 | 변경 |
|------|------|
| `supabase/migrations/00024_product_features_usecases.sql` | 신규: features, use_cases 컬럼 |
| `backend/services/agents/product_advisor.py` | 프롬프트 리라이트 (Few-shot + CoT + features/use_cases) |
| `frontend/src/components/products/ProductDetail.astro` | Key Features, Use Cases, Alternatives, FAQ 섹션 추가 |
| `frontend/src/lib/pageData/productsPage.ts` | ProductDetailData 타입 + fetchAlternatives 함수 |
| `frontend/src/pages/en/products/[slug].astro` | alternatives 데이터 전달 |
| `frontend/src/pages/ko/products/[slug].astro` | 동일 |
| `frontend/src/pages/admin/products/edit/[slug].astro` | features/use_cases 에디터 + AI Apply 확장 |
| `frontend/src/styles/global.css` | 새 섹션 CSS |
