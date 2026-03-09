# Phase 3-Intelligence: AI Advisor Design

> **Date:** 2026-03-10
> **Author:** Amy (Solo)
> **Status:** Approved

## Overview

Admin Editor의 AI 패널 placeholder를 실제 기능으로 교체. 글 작성 시 4개 독립 버튼으로 AI 지원.

## Features

| # | Button | Model | Function | Result Type |
|---|--------|-------|----------|-------------|
| 1 | Generate | gpt-4o | content → guide_items, excerpt, tags, slug | Apply |
| 2 | SEO | gpt-4o-mini | Title suggestions, tag/excerpt optimization | Apply |
| 3 | Review | gpt-4o-mini | Structure/length/readability/markdown checklist | Read-only |
| 4 | Fact-check | gpt-4o | Claim-source matching, missing labels, link validity | Read-only |

**Trigger:** On-demand button click only. No automatic execution.

## API

```
POST /api/admin/ai/advise
Auth: require_admin | Rate limit: 5/min
Body: { action, post_id, title, content, category, tags, excerpt, slug, post_type, guide_items }
```

Frontend sends live editor state (not DB state).

## Scope

- Posts editor only (Log)
- Handbook AI support deferred to separate mini-sprint

## Files

**New:**
- `backend/models/advisor.py`
- `backend/services/agents/prompts_advisor.py`
- `backend/services/agents/advisor.py`
- `backend/routers/admin_ai.py`
- `frontend/src/pages/api/admin/ai/advise.ts`

**Modified:**
- `backend/main.py` — router registration
- `frontend/src/pages/admin/edit/[slug].astro` — AI panel UI + script
- `frontend/src/styles/global.css` — AI panel CSS
