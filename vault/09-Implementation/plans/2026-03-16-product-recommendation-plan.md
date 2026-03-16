# AI Products 추천 알고리즘 — 계획

> Date: 2026-03-16
> Status: Planned (미구현)
> Priority: Phase 3+

---

## 현재 상태

`fetchAlternatives()` — 같은 `primary_category` + featured 우선 + sort_order순. 4개.
"비슷한 도구"라기보다 "같은 카테고리 도구"일 뿐.

## 개선 방향

### Option A: Tags 겹침 기반 (추천)

```sql
-- 현재 제품의 tags와 겹치는 tag 수가 많은 순으로 정렬
SELECT *, array_length(
  ARRAY(SELECT unnest(tags) INTERSECT SELECT unnest($current_tags)),
  1
) AS tag_overlap
FROM ai_products
WHERE is_published = true AND slug != $current_slug
ORDER BY tag_overlap DESC NULLS LAST, featured DESC
LIMIT 4;
```

- 장점: 카테고리를 넘어서 진짜 비슷한 도구 매칭 (예: ChatGPT → Claude, Gemini)
- 단점: tags가 비어있으면 작동 안 함 → fallback으로 같은 카테고리
- 구현 난이도: Supabase RPC 함수 1개

### Option B: secondary_categories 교집합

```sql
-- primary 또는 secondary_categories가 겹치는 제품
SELECT *
FROM ai_products
WHERE is_published = true
  AND slug != $current_slug
  AND (
    primary_category = $current_primary
    OR primary_category = ANY($current_secondary)
    OR $current_primary = ANY(secondary_categories)
  )
ORDER BY featured DESC, sort_order
LIMIT 4;
```

- 장점: tags 없어도 동작
- 단점: secondary_categories가 아직 대부분 비어있음

### Option C: 하이브리드 (A + B fallback)

1. Tags 겹침으로 4개 시도
2. 4개 미만이면 같은 category/secondary로 채움
3. 그래도 부족하면 featured 아무거나

## 구현 시 필요한 작업

1. Supabase RPC 함수: `get_similar_products(slug, limit)`
2. `productsPage.ts`의 `fetchAlternatives` → RPC 호출로 교체
3. tags 데이터가 충분히 채워져야 의미 있음 → AI Enrich 이후 구현

## 선행 조건

- [ ] 대부분의 제품에 tags가 3개 이상 채워져 있어야 함
- [ ] AI Enrich (Phase 2 batch)가 먼저 실행되어야 함
