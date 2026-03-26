# Products 콘텐츠 강화 — 설계

> AI 비전문가가 "우와 꿀팁이다, 저장해야지" 느끼는 Products 페이지 만들기

## 1. 문제

현재 Products 상세 페이지는 **"이 도구가 뭔지"** 설명 위주:
- description, features, use_cases, getting_started, pricing
- 콘텐츠 소스: 제품 공식 페이지 1개만 Tavily 크롤링
- 큐레이터(Amy)의 목소리가 없음 — AI 디렉토리와 차별점 부재

AI를 모르는 사람이 원하는 건 **"이걸로 내가 뭘 할 수 있는지"** + **"써본 사람의 솔직한 의견"**:
- 구체적 활용 시나리오, 솔직한 장단점, 난이도, 큐레이터 코멘트

## 2. 변경 범위

### A. 기존 프롬프트 품질 개선 (Call 1)

| 필드 | 현재 | 개선 |
|------|------|------|
| `description` | "What it does" 위주 | "내 일상이 어떻게 바뀌는지" 관점 추가 |
| `features` | "Supports...", "Generates..." 나열 | "[구체적 상황] → [결과]" 패턴 |
| `use_cases` | "[Who] + [when]" 짧음 | "[구체적 직업/상황]이 [구체적 작업]할 때" |
| `getting_started` Step 3 | "power-user tip" | "첫 번째 성공 경험" |

### B. 새 필드

| 필드 | DB 타입 | AI 생성 | 구조 | 프롬프트 |
|------|---------|---------|------|----------|
| `scenarios` / `scenarios_ko` | `jsonb` | Call 2 | `[{title, steps}]` × 5개 | 신규 |
| `pros_cons` / `pros_cons_ko` | `jsonb` | Call 2 (초안→검수) | `{pros: [str], cons: [str]}` 각 3개 | 신규 |
| `difficulty` | `text` | Call 2 | `beginner` / `intermediate` / `advanced` | 신규 |
| `editor_note` / `editor_note_ko` | `text` | ❌ 수동 | Amy의 한마디 | — |
| `official_resources` | `jsonb` | ❌ 수동 | `[{label, url}]` 0~5개 | — |
| `verified_at` | `date` | ❌ 수동 | 정보 최종 확인일 | — |
| `korean_quality_note` | `text` | ❌ 수동 | 한국어 지원 품질 코멘트 | — |

### C. Tavily 검색 강화

현재: `tavily.search(url, max_results=1)` — 공식 페이지 1개만 크롤링.

개선: 2종류 검색을 병렬 실행.

```
Tavily 1 (기존): tavily.search(url, max_results=1, include_raw_content=True)
  → 공식 페이지 콘텐츠 → Call 1에 전달

Tavily 2 (신규): tavily.search("{product_name} review use cases pros cons", max_results=3)
  → 리뷰/활용 사례/커뮤니티 반응 → Call 2에 전달
```

### D. 프롬프트 2단계 병렬 생성

품질 저하 방지를 위해 한 프롬프트에 20개+ 필드를 넣지 않고 분리.

```
[Generate] 버튼 클릭
  │
  ├─ Tavily 1 (공식 페이지) ─┬─ Call 1: 기본 프로필
  │                           │   tagline, description, pricing, platform,
  │                           │   korean_support, tags, categories, features,
  │                           │   use_cases, getting_started, pricing_detail
  │                           │   (기존 GENERATE_FROM_URL_SYSTEM 프롬프트)
  │
  ├─ Tavily 2 (리뷰/활용) ───┬─ Call 2: 활용 & 평가
  │                           │   scenarios (5개), pros_cons, difficulty
  │                           │   (신규 ENRICH_SYSTEM 프롬프트)
  │
  └─ 수동 입력: editor_note, official_resources, verified_at, korean_quality_note
```

- Call 1과 Call 2는 **병렬 실행** (asyncio.gather)
- 각 프롬프트가 자기 역할에 집중 → 품질 유지
- 각 Call의 필드 수: ~11개 (Call 1), ~7개 (Call 2) — 안전한 범위

## 3. 변경 파일

| # | 파일 | 변경 내용 |
|---|------|----------|
| 1 | `supabase/migrations/00036_product_enrichment.sql` | 신규 컬럼 추가 |
| 2 | `backend/services/agents/product_advisor.py` | 기존 프롬프트 개선 + ENRICH_SYSTEM 신규 + Tavily 리뷰 검색 + 병렬 생성 |
| 3 | `frontend/src/pages/admin/products/edit/[slug].astro` | 에디터 UI (scenarios, pros_cons, difficulty, editor_note, resources, verified_at, korean_quality_note) |
| 4 | `frontend/src/pages/api/admin/products/save.ts` | save에 새 필드 추가 |
| 5 | `frontend/src/lib/pageData/productsPage.ts` | 쿼리에 새 필드 포함 + 타입 정의 |
| 6 | `frontend/src/components/products/ProductDetail.astro` | 새 섹션 렌더링 |
| 7 | `frontend/src/styles/global.css` | 새 섹션 스타일 |

## 4. 프론트 상세 페이지 섹션 순서

```
① Hero (이름, 태그라인, 가격, 로고, 플랫폼, 난이도 배지)
② Tags (카테고리, 태그)
③ Media Gallery
④ About (description) ← 품질 개선
⑤ 에디터 한마디 (editor_note) ← NEW, 수동
⑥ Key Features ← 품질 개선
⑦ Use Cases ← 품질 개선
⑧ 이렇게 써보세요 (scenarios) ← NEW, AI
⑨ 장단점 (pros_cons) ← NEW, AI
⑩ Getting Started ← 품질 개선
⑪ Pricing
⑫ 한국어 지원 상세 (korean_quality_note) ← NEW, 수동 (있을 때만)
⑬ 참고 자료 (official_resources) ← NEW, 수동
⑭ Related News
⑮ Similar Tools
⑯ FAQ
⑰ Bottom CTA
   Footer: "Last verified: {verified_at}"
```

## 5. 프롬프트 정의

### Call 1: GENERATE_FROM_URL_SYSTEM (기존 개선)

기존 필드 유지 + 품질 지시 강화:
- description: "Sentence 1: 이 도구가 당신의 [일상 작업]을 어떻게 바꾸는지"
- features: "[상황] → [결과]" 패턴 강제
- use_cases: "[구체적 직업]이 [구체적 상황]에서 [구체적 작업]할 때"
- getting_started Step 3: "first success experience, not power-user tip"

### Call 2: ENRICH_SYSTEM (신규)

```
You are an editorial reviewer for 0to1log, an AI product curation magazine.
Given a product's basic profile and real user reviews, produce enrichment data
that helps AI beginners understand HOW to use this tool in their daily life.

## Input
- Product name, URL, basic profile (from Call 1)
- Reviews & user experiences (from Tavily search)

## Output (JSON)

1. **scenarios** (EN, array of 5 objects):
   Each: {title: string (max 10 words), steps: string (2-3 sentences)}
   - title: specific real-world task, not a category
   - steps: concrete workflow with → arrows between steps
   - Cover diverse situations: work, study, personal, creative, side-project
   - Target: someone who has NEVER used AI tools before

2. **scenarios_ko** (KO, array of 5 objects):
   - Same scenarios, naturally written in Korean

3. **pros_cons** (EN, object):
   {pros: [string × 3], cons: [string × 3]}
   - Each: one factual observation based on reviews/features
   - pros: specific, evidence-backed strengths
   - cons: honest limitations, NOT attacks on the product

4. **pros_cons_ko** (KO, object):
   - Same structure in Korean

5. **difficulty** (one of: "beginner", "intermediate", "advanced"):
   - beginner: sign up and use immediately, no technical knowledge needed
   - intermediate: some setup or learning curve, but no coding
   - advanced: requires API keys, coding, or technical configuration
```

## 6. Tavily 2단계 검색

```python
async def _fetch_product_context(name: str, url: str) -> tuple[str, str]:
    """Returns (page_content, review_content) — both Tavily searches run in parallel."""
    page_task = _fetch_page_content(url)  # 기존 함수

    async def _fetch_reviews() -> str:
        if not settings.tavily_api_key:
            return ""
        try:
            tavily = TavilyClient(api_key=settings.tavily_api_key)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: tavily.search(
                    f"{name} review use cases pros cons",
                    max_results=3,
                ),
            )
            parts = [r.get("content", "") for r in results.get("results", []) if r.get("content")]
            return "\n\n".join(parts)[:3000]
        except Exception as e:
            logger.warning("Tavily review search failed for %s: %s", name, e)
            return ""

    page_content, review_content = await asyncio.gather(page_task, _fetch_reviews())
    return page_content, review_content
```

## 7. 에디터 UI

### AI 생성 필드
- **Scenarios**: 5행 × (title input + steps textarea). AI 적용 시 자동 채움, 수동 수정 가능.
- **Pros & Cons**: Pros 3개 input + Cons 3개 input. AI 적용 시 자동 채움.
- **Difficulty**: select (beginner/intermediate/advanced). AI 적용 시 자동 선택.

### 수동 입력 필드
- **Editor Note**: textarea (EN) + textarea (KO). Amy의 코멘트.
- **Official Resources**: 동적 리스트 (label + url + 삭제 버튼 + "Add" 버튼).
- **Verified At**: date input.
- **Korean Quality Note**: textarea. "한국어 UI 지원, 번역 품질 양호" 등.

## 8. DB 마이그레이션

```sql
ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS scenarios jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS scenarios_ko jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS pros_cons jsonb,
  ADD COLUMN IF NOT EXISTS pros_cons_ko jsonb,
  ADD COLUMN IF NOT EXISTS difficulty text CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
  ADD COLUMN IF NOT EXISTS editor_note text,
  ADD COLUMN IF NOT EXISTS editor_note_ko text,
  ADD COLUMN IF NOT EXISTS official_resources jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS verified_at date,
  ADD COLUMN IF NOT EXISTS korean_quality_note text;
```

## 9. Verification

1. 에디터에서 URL 입력 → AI Generate → Call 1 + Call 2 병렬 → 모든 AI 필드 자동 채워짐
2. scenarios, pros_cons, difficulty 수동 수정 → Save → DB 반영
3. editor_note, official_resources, verified_at, korean_quality_note 수동 입력 → Save → DB 반영
4. 상세 페이지에서 모든 새 섹션 정상 렌더링 (EN/KO)
5. Tavily 리뷰 검색 실패 시 graceful fallback (Call 2는 빈 리뷰로 생성)
6. Call 1 또는 Call 2 단독 실패 시 나머지는 정상 적용
7. `npm run build` 0 errors
