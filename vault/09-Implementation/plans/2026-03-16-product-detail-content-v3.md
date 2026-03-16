# Product 상세페이지 콘텐츠 추가 — Getting Started + Pricing 상세 + 관련 뉴스

> Date: 2026-03-16
> Status: Approved

## 추가 섹션

### 1. Pricing 상세
- DB: `pricing_detail` (text, 마크다운) + `pricing_detail_ko`
- AI 생성 → 수동 수정
- 위치: Key Features 아래

### 2. Getting Started
- DB: `getting_started` (jsonb, EN string 배열) + `getting_started_ko`
- AI 생성 → 수동 수정
- 위치: Description 아래

### 3. Related News
- DB 변경 없음 — news_posts에서 source_urls/title 매칭 쿼리
- 위치: Use Cases 아래

## 페이지 흐름

1. Media Gallery
2. Hero
3. Meta Chips
4. Key Features
5. **Pricing 상세** ← NEW
6. Description
7. **Getting Started** ← NEW
8. Use Cases
9. **Related News** ← NEW
10. Similar Tools
11. FAQ
12. Bottom CTA

## 파일 변경

- `supabase/migrations/00025_product_detail_content.sql`
- `backend/services/agents/product_advisor.py`
- `frontend/src/lib/pageData/productsPage.ts`
- `frontend/src/components/products/ProductDetail.astro`
- `frontend/src/pages/admin/products/edit/[slug].astro`
- `frontend/src/pages/api/admin/products/save.ts`
