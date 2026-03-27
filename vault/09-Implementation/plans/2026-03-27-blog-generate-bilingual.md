# Blog Generate Bilingual Metadata — Implementation Plan

**Goal:** "Generate" 버튼 하나로 EN+KO 메타데이터를 동시 생성하고, KO row가 없으면 자동 생성. 초안이 EN이든 KO든 양방향 작동.

**Architecture:**
- 백엔드: `generate_bilingual` 액션 추가. Call 1(원본 언어 메타 추출) + Call 2(반대 언어 독립 생성) 병렬 실행
- 프론트: Generate 결과에 EN/KO 탭 표시. "Apply All" 시 현재 언어 필드 적용 + 반대 언어 row 자동 생성(save API 호출)

**흐름:**
```
EN 초안 작성 → [Generate EN+KO] 클릭
  ├─ Call 1 (병렬): EN 메타 추출 (excerpt, focus_items, tags, slug)
  └─ Call 2 (병렬): KO 메타 독립 생성 (번역이 아닌 한국어 네이티브)
→ 결과: { en: {...}, ko: {...} }
→ [Apply All]: EN 필드 적용 + KO row 생성/업데이트
```

KO 초안인 경우 반대로:
```
KO 초안 작성 → [Generate EN+KO] 클릭
  ├─ Call 1 (병렬): KO 메타 추출
  └─ Call 2 (병렬): EN 메타 독립 생성
→ [Apply All]: KO 필드 적용 + EN row 생성/업데이트
```

---

### Task 1: Backend — generate_bilingual 프롬프트 추가

**Files:**
- Modify: `backend/services/agents/prompts_blog_advisor.py`

프롬프트 2개 추가:
1. `GENERATE_SOURCE_PROMPT` — 원본 언어 메타 추출 (기존 generate와 동일)
2. `GENERATE_TARGET_PROMPT` — 반대 언어 메타 독립 생성

**GENERATE_TARGET_PROMPT 핵심:**
```
Given a blog post written in {source_lang}, generate metadata in {target_lang}.
Do NOT translate — write naturally in {target_lang} as if the article was originally written in that language.

Output JSON:
{
  "title": "Natural {target_lang} title",
  "excerpt": "100-200 char summary in {target_lang}",
  "focus_items": ["item1", "item2", "item3"],
  "tags": ["tag1", "tag2", "tag3"],
  "slug": "english-kebab-case-slug",
  "content": "Full translated content in {target_lang}"
}

Rules:
- title: Natural {target_lang}, NOT a literal translation
- excerpt: Written for {target_lang} audience
- tags: Mix of {target_lang} and English terms where natural
- slug: Always in English kebab-case
- content: Full article naturally rewritten in {target_lang}
```

---

### Task 2: Backend — generate_bilingual 액션 핸들러

**Files:**
- Modify: `backend/services/agents/blog_advisor.py`

새 함수: `run_blog_generate_bilingual(req) -> dict`

```python
async def run_blog_generate_bilingual(req: BlogAdviseRequest) -> tuple[dict, str, int]:
    source_locale = req.locale  # 'en' or 'ko'
    target_locale = 'ko' if source_locale == 'en' else 'en'

    # Call 1: source language metadata extraction
    # Call 2: target language independent generation (with content)
    # Run in parallel with asyncio.gather

    return {
        "source": { "excerpt": ..., "focus_items": ..., "tags": ..., "slug": ... },
        "target": { "title": ..., "excerpt": ..., "focus_items": ..., "tags": ..., "slug": ..., "content": ... },
        "source_locale": source_locale,
        "target_locale": target_locale,
    }, model, total_tokens
```

`BLOG_ACTION_CONFIG`에 추가:
```python
"generate_bilingual": {
    "handler": "custom",  # uses dedicated function instead of generic flow
}
```

`run_blog_advise()`에서 분기:
```python
if req.action == "generate_bilingual":
    return await run_blog_generate_bilingual(req)
```

---

### Task 3: Frontend — Generate 버튼을 Generate EN+KO로 변경

**Files:**
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro`

기존 `generate` 액션을 `generate_bilingual`로 변경:
```typescript
{ action: 'generate_bilingual', label: 'Generate EN+KO', model: 'gpt-4.1', wide: true },
```

기존 `generate` 액션은 제거하거나 `generate_bilingual`로 대체.

---

### Task 4: Frontend — renderGenerateBilingual 함수

**Files:**
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro`

새 함수: `renderGenerateBilingual(r)`

```
결과 표시:
┌─────────────────────────────────────┐
│ Generated Metadata (EN + KO)        │
│                                     │
│ ── Current (EN) ──                  │
│ Excerpt: "..."          [Use]       │
│ Slug: "..."             [Use]       │
│ Tags: "..."             [Use]       │
│ Focus Items: "..."      [Use]       │
│                                     │
│ ── Target (KO) ──                   │
│ Title: "..."                        │
│ Excerpt: "..."                      │
│ Tags: "..."                         │
│ Focus Items: "..."                  │
│ Content: (preview...)               │
│                                     │
│ [Apply All + Create KO Post]        │
└─────────────────────────────────────┘
```

"Apply All + Create KO Post" 클릭 시:
1. 현재 언어 필드에 source 메타 적용 (excerpt, slug, tags, focus_items)
2. 반대 언어 row 확인:
   - partner post 있으면 → save API로 update (메타 필드만)
   - partner post 없으면 → save API로 create (title, content, excerpt, tags, slug, focus_items, locale, translation_group_id)
3. translation_group_id 연결

---

### Task 5: Frontend — KO row 자동 생성 로직

**Files:**
- Modify: `frontend/src/pages/api/admin/blog/save.ts` (translation_group_id 지원 추가)
- Modify: `frontend/src/pages/admin/blog/edit/[slug].astro`

save API에 `translation_group_id` 필드 수락 추가:
```typescript
const { id, title, slug, category, tags, content, excerpt, locale,
        focus_items, og_image_url, source, translation_group_id } = body;
// ...
if (translation_group_id !== undefined) row.translation_group_id = translation_group_id;
```

프론트에서 Apply All 시:
```typescript
// 1. Apply source meta to current fields
// 2. Create/update target post
const targetBody = {
  title: r.target.title,
  slug: r.target.slug,
  content: r.target.content,
  excerpt: r.target.excerpt,
  tags: r.target.tags,
  focus_items: r.target.focus_items,
  locale: r.target_locale,
  category: categorySelect?.value || 'study',
  translation_group_id: currentTranslationGroupId || crypto.randomUUID(),
  source: 'ai-generated',
};

// If partner exists, include id for update
if (partnerPostId) targetBody.id = partnerPostId;

const res = await fetch('/api/admin/blog/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(targetBody),
});
```

---

### Task 6: Build + Test + Commit

**Step 1:** `cd frontend && npm run build` — 0 errors

**Step 2:** Manual test:
- EN 초안 작성 → Generate EN+KO → Apply All → KO row 생성 확인
- KO 초안 작성 → Generate EN+KO → Apply All → EN row 생성 확인
- Partner post가 이미 있을 때 → 업데이트만 (중복 생성 안 됨)

**Step 3:** Commit + push
