# Blog AI Advisor Redesign

> **Date:** 2026-03-11
> **Status:** Approved
> **Scope:** Blog editor AI Advisor — remove redundancy, add writing-stage features + translation

---

## 1. Overview

Blog editor의 AI Advisor를 News 에디터 복제에서 블로그 전용으로 재설계.

### Goals
- 글쓰기 전체 단계(시작 전 → 작성 중 → 완성 후)를 커버
- 불필요한 중복 제거 (SEO → Generate 흡수)
- 한/영 번역 기능 추가

### Architecture Decision
- **접근법 2 채택:** Blog 전용 엔드포인트 분리 (`/api/admin/blog-ai/`)
- News AI와 완전 독립 — 각자 진화 가능, 모델 오염 없음

---

## 2. Action Inventory

### Removed
| Action | Reason |
|--------|--------|
| SEO | Generate에 흡수 (excerpt, tags 중복) |

### New
| Action | Stage | Description |
|--------|-------|-------------|
| Outline | 글 시작 전 | 주제 → H2/H3 섹션 구조 제안 → 에디터 삽입 |
| Draft | 글 시작 전 (step 2) | 승인된 Outline → 각 섹션 초안 생성 |
| Rewrite | 글 쓰는 도중 | 섹션별 개선된 텍스트 제안 (diff 카드) |
| Suggest | 글 쓰는 도중 | 편집 가이드 — 추가/삭제/보강/구조변경 제안 |
| Translate | 글 완성 후 | 반대 언어 버전 생성 → 새 blog_posts row |

### Retained (unchanged)
| Action | Category | Description |
|--------|----------|-------------|
| Review | 공통 | 품질 점수 + 체크리스트 |
| Concept Check | study | 개념 정확성 검증 |
| Voice Check | career | 진정성/구체성/실행가능성 |
| Retro Check | project | 회고 품질 (결정, 교훈, 메트릭) |

### Modified
| Action | Change |
|--------|--------|
| Generate | + `title_suggestions` 필드 추가 (SEO 흡수) |

---

## 3. Final Action List per Category

```
Study:    [Outline] [Draft]  [Rewrite] [Suggest]
          [Review]  [Generate] [Concept Check]
          [Translate]

Career:   [Outline] [Draft]  [Rewrite] [Suggest]
          [Review]  [Generate] [Voice Check]
          [Translate]

Project:  [Outline] [Draft]  [Rewrite] [Suggest]
          [Review]  [Generate] [Retro Check]
          [Translate]
```

---

## 4. Endpoint Architecture

### New endpoints (Blog-only)

```
Frontend proxy:
  /api/admin/blog/ai/advise.ts     → backend /api/admin/blog-ai/advise
  /api/admin/blog/ai/translate.ts   → backend /api/admin/blog-ai/translate

Backend:
  POST /api/admin/blog-ai/advise     — outline, draft, rewrite, suggest, review,
                                       generate, conceptcheck, voicecheck, retrocheck
  POST /api/admin/blog-ai/translate  — translate + DB write
```

### Existing (unchanged)
```
  /api/admin/ai/advise              — News-only, no changes
```

---

## 5. Action Specifications

### 5.1 Outline

| Item | Detail |
|------|--------|
| **Input** | title + category (content can be empty) |
| **Output** | `{ sections: [{ heading, subsections: [], description }] }` |
| **Frontend** | Section cards → **"Apply"** inserts `## H2\n### H3\n\n` skeleton into editor |
| **Model** | gpt-4o |
| **Category-aware** | study → learning progression, career → narrative arc, project → build-log structure |

### 5.2 Draft

| Item | Detail |
|------|--------|
| **Input** | title + category + content (outline skeleton in editor) |
| **Output** | `{ content: "full draft markdown" }` |
| **Frontend** | Diff preview → **"Apply"** replaces editor content |
| **Condition** | Only active when editor has H2/H3 headings. Otherwise shows "Run Outline first" |
| **Model** | gpt-4o |

### 5.3 Rewrite

| Item | Detail |
|------|--------|
| **Input** | title + category + content |
| **Output** | `{ changes: [{ section, before, after, reason }] }` |
| **Frontend** | Section-level diff cards, each with **"Apply" / "Skip"** |
| **Model** | gpt-4o |
| **Category-aware** | study → accuracy/clarity, career → preserve authenticity, project → technical clarity |

### 5.4 Suggest

| Item | Detail |
|------|--------|
| **Input** | title + category + content |
| **Output** | `{ suggestions: [{ section, type: "add|remove|strengthen|restructure", message, priority: "high|medium|low" }] }` |
| **Frontend** | Priority-sorted list with type icons. No text generation — guidance only |
| **Model** | gpt-4o-mini |

### 5.5 Generate (enhanced)

| Item | Detail |
|------|--------|
| **Input** | title + content + category + tags + excerpt + slug |
| **Output** | `{ excerpt, slug, tags, focus_items, title_suggestions: ["alt1", "alt2", "alt3"] }` |
| **Frontend** | Existing + title suggestion cards with "Use" buttons |
| **Model** | gpt-4o |

### 5.6 Translate

| Item | Detail |
|------|--------|
| **Input** | Full source post data (title, content, excerpt, tags, category, locale) |
| **Output** | `{ title, content, excerpt, tags, slug, locale }` |
| **Frontend** | Translation preview → **"Create"** → API creates new blog_posts row → redirect to new post editor |
| **DB logic** | If source has no `translation_group_id`, generate new UUID. Both posts share same group_id. Set `source_post_id` on the translation |
| **Guard** | If opposite-locale version already exists, show "Translation already exists" + link |
| **Model** | gpt-4o |

### 5.7–5.10 Review, Concept Check, Voice Check, Retro Check

No changes from current implementation. Continue using existing backend `run_advise()` via the new blog-ai endpoint, or keep proxying to the shared endpoint.

---

## 6. Backend File Structure

```
backend/
  models/
    blog_advisor.py              ← BlogAdviseRequest, BlogAdviseResponse,
                                    OutlineResult, DraftResult, RewriteResult,
                                    SuggestResult, BlogTranslateRequest/Response
  services/agents/
    blog_advisor.py              ← run_blog_advise(), run_blog_translate()
    prompts_blog_advisor.py      ← Blog-specific prompts (outline, draft,
                                    rewrite, suggest, translate)
  routers/
    admin_blog_ai.py             ← POST /blog-ai/advise, POST /blog-ai/translate
```

## 7. Frontend File Structure

```
frontend/src/pages/api/admin/blog/ai/
  advise.ts                      ← Proxy → backend /api/admin/blog-ai/advise
  translate.ts                   ← Proxy → backend /api/admin/blog-ai/translate

frontend/src/pages/admin/blog/edit/
  [slug].astro                   ← Update: new CATEGORY_ACTIONS, new render
                                    functions, Translate UI
```

---

## 8. Design Decisions

| Decision | Rationale |
|----------|-----------|
| Blog-only endpoints (not shared with News) | Independent evolution, no model pollution |
| Draft requires Outline first | 2-step ensures structure before content |
| Rewrite gives per-section Apply/Skip | Preserves author control, especially for career/project (Authentic Voice) |
| Suggest is guidance-only, no text gen | Respects Content Strategy Type B: author voice |
| Translate creates new DB row | Matches existing schema (translation_group_id, source_post_id) |
| Generate absorbs SEO | Eliminates duplicate excerpt/tags generation |
| gpt-4o-mini only for Suggest | No text generation needed, cost efficiency |

## Related Plans

- [[plans/2026-03-11-blog-kb-design|Blog KB 설계]]
- [[plans/2026-03-10-ai-advisor-design|AI Advisor 설계]]
