# AI 용어집 리디자인 구현 플랜

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 용어집 메인을 카테고리 프리뷰 모드로 리디자인 + 카테고리별 별도 페이지 생성

**Architecture:** Products 페이지 패턴(프리뷰 → "모두 보기" → 별도 페이지)을 용어집에 적용. 데이터 레이어를 `pageData/handbookPage.ts`로 분리하고, 메인 페이지는 카테고리별 4개 프리뷰 + 검색 시 전체 리스트 전환. 카테고리 페이지는 `[slug].astro` 동적 라우트.

**Tech Stack:** Astro v5, Supabase, CSS (global.css)

**설계 문서:** `vault/09-Implementation/plans/2026-03-16-handbook-redesign-design.md`

---

### Task 1: 카테고리 설명 데이터 추가

**Files:**
- Modify: `frontend/src/lib/handbookCategories.ts`

**Step 1:** `HANDBOOK_CATEGORY_LABELS`를 `HANDBOOK_CATEGORIES`로 확장하여 `description` 필드 추가

```ts
const HANDBOOK_CATEGORIES: Record<HandbookCategorySlug, {
  label: Record<Locale, string>;
  description: Record<Locale, string>;
}> = {
  'ai-ml': {
    label: { en: 'AI/ML & Algorithms', ko: 'AI/ML & 알고리즘' },
    description: {
      en: 'Machine learning models, neural networks, training techniques, and AI algorithms.',
      ko: '머신러닝 모델, 신경망, 학습 기법, AI 알고리즘을 다룹니다.',
    },
  },
  // ... 11개 카테고리 모두
};
```

**Step 2:** 기존 export 함수들이 깨지지 않도록 내부 구조만 변경, 새 함수 추가:
```ts
export function getHandbookCategoryDescription(locale: Locale, category: string): string | null
```

**Step 3:** 빌드 확인
```bash
cd frontend && npm run build
```

**Step 4:** 커밋
```bash
git add frontend/src/lib/handbookCategories.ts
git commit -m "feat: add descriptions to handbook categories"
```

---

### Task 2: 데이터 헬퍼 생성 (`handbookPage.ts`)

**Files:**
- Create: `frontend/src/lib/pageData/handbookPage.ts`

**Step 1:** `productsPage.ts`의 `getProductsPageData()` 패턴을 참고하여 생성:

```ts
// 반환 타입
interface HandbookPageData {
  allTerms: HandbookTermCard[];
  termsByCategory: Record<string, HandbookTermCard[]>;
  totalTerms: number;
  error: string | null;
}

interface HandbookTermCard {
  id: string;
  term: string;
  slug: string;
  korean_name: string | null;
  definition_ko: string | null;
  definition_en: string | null;
  categories: string[];
  is_favourite: boolean;
}
```

**Step 2:** `getHandbookPageData(locale)` 함수:
- `handbook_terms` WHERE `status = 'published'` ORDER BY `term ASC`
- `getHandbookCategories()` 순서로 `termsByCategory` 그룹핑
- 용어 하나가 여러 카테고리에 속할 수 있음 (`categories` 배열) → 각 카테고리에 중복 포함

**Step 3:** `getHandbookCategoryPageData(locale, categorySlug)` 함수:
- 같은 쿼리 + JS 필터: `term.categories.includes(categorySlug)`
- 반환: `{ terms, totalTerms, error }`

**Step 4:** 빌드 + 커밋
```bash
cd frontend && npm run build
git add frontend/src/lib/pageData/handbookPage.ts
git commit -m "feat: add handbookPage.ts data helper"
```

---

### Task 3: 카테고리 프리뷰 CSS 추가

**Files:**
- Modify: `frontend/src/styles/global.css`

**Step 1:** Products 프리뷰 패턴(`.product-category-preview`)을 참고하여 handbook용 추가:

```css
/* --- Handbook category preview --- */
.handbook-category-preview { ... }
.handbook-category-preview-header { display: flex; justify-content: space-between; align-items: center; }
.handbook-category-preview-title-group { display: flex; align-items: center; gap: 0.5rem; }
.handbook-category-preview-title { font-family: var(--font-display); font-size: 1.1rem; }
.handbook-category-preview-count { font-size: 0.8rem; color: var(--color-text-muted); }
.handbook-category-see-all { /* pill 스타일 버튼 */ }
.handbook-preview-grid { display: grid; grid-template-columns: 1fr; gap: 0.75rem; }

/* 반응형 */
@media (min-width: 640px) { .handbook-preview-grid { grid-template-columns: repeat(2, 1fr); } }
```

**Step 2:** 통계 배지 CSS:
```css
.handbook-hero-stats { display: flex; gap: 0.5rem; font-size: 0.85rem; color: var(--color-text-secondary); }
.handbook-hero-stats strong { font-size: 1.1rem; color: var(--color-text-primary); }
```

**Step 3:** 빌드 + 커밋

---

### Task 4: 메인 페이지 리디자인 (ko)

**Files:**
- Modify: `frontend/src/pages/ko/handbook/index.astro`

**Step 1:** import 변경 — `getHandbookPageData` 사용, 기존 inline supabase 쿼리 제거

**Step 2:** frontmatter에서 데이터 가져오기:
```ts
const { allTerms, termsByCategory, totalTerms, error } = await getHandbookPageData(locale);
```

**Step 3:** HTML 구조 변경:
1. masthead 유지 (NewsprintShell)
2. 통계 배지 추가: `{totalTerms}+ 용어 · {categories.length} 카테고리`
3. 검색창 유지
4. 카테고리 필터 pills 유지 (스크롤 앵커용)
5. **카테고리 프리뷰 섹션** (`#category-preview`):
   - 11개 카테고리 반복
   - 각각: 아이콘 + 이름 + 카운트 + "모두 보기 →" + 4개 용어 카드
6. **검색 결과 뷰** (`#search-results`, hidden):
   - 기존 전체 용어 카드 리스트 (검색 시 표시)

**Step 4:** JS 변경:
- 검색 입력 시: `#category-preview` 숨김 + `#search-results` 표시
- 검색 비우면: 프리뷰 모드로 복귀
- 카테고리 pill 클릭: 해당 프리뷰 섹션으로 스크롤 (`#handbook-cat-{slug}`)

**Step 5:** 빌드 + 커밋

---

### Task 5: 메인 페이지 리디자인 (en)

**Files:**
- Modify: `frontend/src/pages/en/handbook/index.astro`

**Step 1:** ko 페이지와 동일한 구조 적용 (locale 변수만 다름)

**Step 2:** 빌드 + 커밋

---

### Task 6: 카테고리 페이지 생성 (ko)

**Files:**
- Create: `frontend/src/pages/ko/handbook/category/[slug].astro`

**Step 1:** 동적 라우트 페이지 생성:
```ts
export const prerender = false;
// URL: /ko/handbook/category/ai-ml/
```

**Step 2:** 데이터:
```ts
const slug = Astro.params.slug;
const { terms, totalTerms, error } = await getHandbookCategoryPageData('ko', slug);
const categoryLabel = getHandbookCategoryLabel('ko', slug);
const categoryDesc = getHandbookCategoryDescription('ko', slug);
```

**Step 3:** HTML 구조:
1. `← 용어집` 뒤로가기 링크
2. 카테고리 아이콘 + 이름 + 설명 + 용어 수
3. 검색창 (이 카테고리 내에서 검색)
4. 용어 카드 리스트 (기존 `.handbook-card` 재사용)
5. 사이드바: 다른 카테고리 링크 목록

**Step 4:** JS: 카테고리 내 검색 필터링

**Step 5:** 빌드 + 커밋

---

### Task 7: 카테고리 페이지 생성 (en)

**Files:**
- Create: `frontend/src/pages/en/handbook/category/[slug].astro`

**Step 1:** ko 페이지와 동일한 구조, `locale = 'en'`

**Step 2:** 빌드 + 커밋

---

### Task 8: 통합 검증 + 최종 커밋

**Step 1:** 전체 빌드 확인
```bash
cd frontend && npm run build
```

**Step 2:** 수동 검증 체크리스트:
- [ ] 메인 → 11개 카테고리 프리뷰 섹션 표시
- [ ] 각 프리뷰에 용어 4개 + "모두 보기" 버튼
- [ ] "모두 보기" 클릭 → `/handbook/category/{slug}/` 이동
- [ ] 카테고리 페이지 → 해당 카테고리 전체 용어 표시
- [ ] 뒤로가기 → 메인으로 복귀
- [ ] 메인 검색 → 프리뷰 숨김 + 전체 리스트 표시
- [ ] 카테고리 pill 클릭 → 해당 섹션 스크롤
- [ ] 모바일 반응형 (375px, 768px)
- [ ] 다크/라이트 테마 확인

**Step 3:** 최종 커밋 + 푸시
```bash
git push
```
