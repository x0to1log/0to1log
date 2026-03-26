# AI Products 데이터 채우기 — 단계적 발행 + AI 보강

> Date: 2026-03-16
> Status: Draft
> Feature: Products 페이지 데이터 채우기
> 선행: products-redesign (완료), seed data 156개 (00022 migration)

---

## 현황

- DB에 156개 제품 draft (`is_published = false`)
- 채워진 필드: `slug`, `name`, `url`, `tagline_ko`, `primary_category`
- **비어있는 필드:** `tagline` (EN), `description`, `description_ko`, `logo_url`, `thumbnail_url`, `demo_media`, `tags`, `platform`, `pricing`, `korean_support`, `released_at`
- 프론트엔드는 `is_published = true`만 쿼리 → 현재 0개 표시

---

## Phase 1: 즉시 발행 (화면 채우기)

**목표:** 있는 데이터만으로 156개 전부 publish. 빈 필드는 fallback UI가 처리.

### Task 1-1: Batch publish API 추가

**파일:** `frontend/src/pages/api/admin/products/batch-status.ts` (신규)

Admin 전용 API. body로 action + 필터 조건을 받아 일괄 상태 변경:

```json
POST /api/admin/products/batch-status
{ "action": "publish", "filter": "all_drafts" }
```

- `all_drafts` → `is_published = false`인 모든 제품을 `is_published = true`로
- 기존 `status.ts`의 인증/admin 검증 패턴 따름
- 응답: `{ updated: 156 }`

### Task 1-2: Admin UI에 "Publish All Drafts" 버튼

**파일:** `frontend/src/pages/admin/products/index.astro`

Draft 탭에 "Publish All Drafts" 버튼 추가. 클릭 시 batch-status API 호출.

### Task 1-3: 데이터 정리 — 중복/불량 제품 제거

seed 데이터 중 정리 필요:
- `suno`와 `suno-ai` 중복 → 하나 삭제
- 블로그 글/Reddit 링크가 제품으로 들어간 항목 → `is_published = false`로 되돌림
  - 예: `claude-code-is-a-beast` (Reddit 글), `antigravity` (블로그 글) 등
- `tagline_ko`가 NULL인 제품 확인 → 빈 채로 publish (fallback 처리)

**실행:** SQL 스크립트 또는 admin UI에서 수동 처리

---

## Phase 2: AI 보강 — 프롬프트 개선 + batch enrichment

**목표:** product_advisor 프롬프트 품질을 높이고, 발행된 제품들을 batch로 AI 보강.

### Task 2-1: Product Advisor 프롬프트 리라이트

**파일:** `backend/services/agents/product_advisor.py`

**현재 문제:**
- `GENERATE_FROM_URL_SYSTEM`: 너무 일반적. "punchy 1-sentence tagline"이라고만 하니 결과가 밋밋
- gpt-4o-mini 사용 (저품질)
- Tavily fetch가 `include_raw_content=False`라 페이지 콘텐츠가 빈약
- temperature 0.5로 너무 safe

**변경 방향:**

```python
GENERATE_FROM_URL_SYSTEM = """You are an editorial writer for 0to1log, an AI product curation magazine.

You write for builders and developers who are evaluating AI tools.

Given a product page's content, generate these fields:

1. **tagline** (EN): A sharp, specific tagline (max 12 words).
   - BAD: "AI-powered tool for developers" (vague, could be anything)
   - GOOD: "Turn any screenshot into production React code" (specific, shows value)
   - Lead with the core action/benefit, not the category

2. **tagline_ko** (KO): Natural Korean tagline — NOT a translation of EN.
   - Write as if explaining to a Korean developer friend
   - Use the format: "[핵심 기능] — [차별점 또는 대상]"
   - Example: "스크린샷 한 장으로 React 코드 생성 — 프론트엔드 속도 혁신"

3. **description_en** (EN, 2-3 sentences):
   - Sentence 1: What it does concretely (not "AI-powered platform that...")
   - Sentence 2: Who uses it and for what specific workflow
   - Sentence 3 (optional): Key differentiator vs alternatives

4. **description_ko** (KO, 2-3 sentences):
   - Same structure but naturally written for Korean readers
   - Use technical terms as-is (API, LLM, RAG) with brief context if needed

5. **pricing** (one of: "free", "freemium", "paid", "enterprise"):
   - Infer from the page content (free tier? pricing page mentions?)
   - Default to "freemium" if unclear

6. **platform** (array of applicable: "web", "ios", "android", "api", "desktop"):
   - Infer from download links, app store badges, API docs mentions

7. **korean_support** (boolean):
   - true if Korean language UI or Korean documentation exists

Respond with JSON only:
{
  "tagline": "...",
  "tagline_ko": "...",
  "description_en": "...",
  "description_ko": "...",
  "pricing": "freemium",
  "platform": ["web", "api"],
  "korean_support": false
}"""
```

**추가 변경:**
- 모델: `openai_model_light` → `openai_model_main` (gpt-4o) 사용으로 변경
- Tavily: `include_raw_content=True` + content 제한 4000자로 확대
- temperature: 0.5 → 0.6 (약간 더 creative)
- max_tokens: 1024 → 1500
- `parse_ai_json` 결과에서 `pricing`, `platform`, `korean_support` 필드도 추출하여 DB 업데이트

### Task 2-2: Batch enrichment API

**파일:** `backend/routers/admin_product_ai.py` (수정)

Admin cron/수동 트리거 엔드포인트:

```
POST /admin/products/batch-enrich
{ "limit": 20, "filter": "missing_tagline" }
```

동작:
1. `tagline IS NULL` 또는 `description IS NULL`인 published 제품을 limit개 조회
2. 각 제품에 대해 `generate_from_url` 실행
3. 결과를 DB에 업데이트 (tagline, description, pricing, platform, korean_support)
4. rate limit: 제품 간 1초 sleep (API 부하 방지)
5. 결과 리포트: `{ processed: 20, success: 18, failed: 2, errors: [...] }`

**프론트엔드 연동:**
- Admin products 페이지에 "AI Enrich (missing fields)" 버튼
- 클릭 시 batch-enrich API 호출 (limit=20 단위로)
- 진행 상태 표시 (처리 중/완료)

### Task 2-3: 개별 필드 프롬프트도 리라이트

**파일:** `backend/services/agents/product_advisor.py`

`TAGLINE_EN_SYSTEM`, `TAGLINE_KO_SYSTEM`, `DESCRIPTION_EN_SYSTEM`, `DESCRIPTION_KO_SYSTEM` 모두 Task 2-1의 톤/가이드라인에 맞춰 리라이트. 개별 필드 생성 시에도 동일한 품질 기준 적용.

---

## Phase 3: 비주얼 보강 (로고 + 썸네일)

**목표:** 카드에 이미지를 채워서 Replicate-like 비주얼 완성.

### Task 3-1: Logo URL 자동 수집

방법: [Clearbit Logo API](https://logo.clearbit.com/) 또는 Google Favicon API 활용

```
https://logo.clearbit.com/{domain}
https://www.google.com/s2/favicons?domain={domain}&sz=128
```

- 각 제품의 `url`에서 도메인 추출 → logo URL 생성
- DB `logo_url` 필드에 저장
- Clearbit 실패 시 Google favicon fallback

### Task 3-2: Thumbnail/Screenshot 수집 전략

옵션:
- **A) 수동:** Admin에서 제품별로 이미지 URL 입력 (확실하지만 느림)
- **B) 자동 스크린샷:** Playwright/Puppeteer로 제품 사이트 캡처 → Supabase Storage에 업로드
- **C) 하이브리드:** 인기 제품은 수동 큐레이션, 나머지는 자동

→ Phase 3는 별도 설계 필요. 이 계획에서는 scope out.

---

## 실행 순서

```
Phase 1 (즉시, 30분)
  ├─ Task 1-1: batch-status API
  ├─ Task 1-2: Admin "Publish All" 버튼
  └─ Task 1-3: 중복/불량 제거

Phase 2 (1-2시간)
  ├─ Task 2-1: Advisor 프롬프트 리라이트
  ├─ Task 2-2: Batch enrich API
  └─ Task 2-3: 개별 프롬프트 리라이트

Phase 3 (별도 설계)
  ├─ Task 3-1: Logo 자동 수집
  └─ Task 3-2: Thumbnail 전략
```

---

## 영향 범위

| 파일 | 변경 |
|---|---|
| `frontend/src/pages/api/admin/products/batch-status.ts` | 신규 |
| `frontend/src/pages/admin/products/index.astro` | 버튼 추가 |
| `backend/services/agents/product_advisor.py` | 프롬프트 + 로직 리라이트 |
| `backend/routers/admin_product_ai.py` | batch-enrich 엔드포인트 |
| `backend/models/product_advisor.py` | response 모델 확장 |
