# Rail Information Design

> **Date:** 2026-03-07  
> **Status:** Approved

## Context

The list page and article detail page should not share the same right-column information architecture.

- The list page is for discovery.
- The detail page is for context and next-step reading.
- Reusing one side-rail component for both created weak information scent and redundant labels.

## Decision

Split the list rail from the article rail.

- **List rail component:** `NewsprintListRail.astro`
- **Article rail component:** `NewsprintSideRail.astro`

This keeps the visual shell consistent while letting each page type serve a different user intent.

## Approved List Rail Labels

| Purpose | Korean | English |
|---|---|---|
| Editorial framing | 오늘의 편집 노트 | Editor's Note |
| Social / discovery | 지금 많이 읽는 글 | Most Read |
| Onboarding | 처음 읽는 분께 | Start Here |

## List Rail Content Model

### 1. 오늘의 편집 노트 / Editor's Note

Short editorial framing copy that explains what kind of reading flow the user is entering.

### 2. 지금 많이 읽는 글 / Most Read

Up to 4 article links in the rail.

Current implementation note:
- Until view-based popularity data exists, this block uses a **latest-published fallback**.
- The featured article should not be repeated here when a list page already has a featured card.

### 3. 처음 읽는 분께 / Start Here

Static guided entry points for the 4 core categories:

- AI News / AI 뉴스
- Study / 서재
- Career / 커리어
- Project / 프로젝트

Each item should include:
- section label
- one-line orientation copy
- link to `/[locale]/log/?category=<slug>`

## Approved Detail Rail Labels

| Purpose | Korean | English |
|---|---|---|
| Reading lens | 이 글의 초점 | Focus of This Article |
| Related reading | 같은 호에서 더 읽기 | More in This Issue |

## Detail Rail Content Model

### 1. 이 글의 초점 / Focus of This Article

Three short reading prompts that clarify how to read the current article.

Current implementation note:
- Until admin-authored focus notes exist, this block uses a **category-based template fallback**.
- The prompt set changes by `ai-news`, `study`, `career`, and `project`.

### 2. 같은 호에서 더 읽기 / More in This Issue

Up to 4 related article links for the same locale.

Current implementation note:
- This block uses the existing latest-published related-post fallback.
- It intentionally prioritizes continuity over strict topical matching for now.

## Deferred Implementation

The following items are intentionally deferred and should be implemented later:

1. **오늘의 편집 노트 / Editor's Note**
- Move from static copy to an admin-authored daily note, or one fixed note per day.

2. **지금 많이 읽는 글 / Most Read**
- Replace latest-published fallback with GA4-based or DB-aggregated popularity ranking.

3. **이 글의 초점 / Focus of This Article**
- Replace category template fallback with admin-authored focus notes per article.

4. **같은 호에서 더 읽기 / More in This Issue**
- Replace latest-published fallback with stricter related-reading logic based on category, tags, date, or editorial grouping.

## Scope Boundary

These deferred items are not required for the current frontend copy and layout pass.
The current implementation only fixes:

- approved rail labels
- list/detail rail separation
- safe fallback behavior until real curation and ranking data exist

## Related Plans

- [[plans/2026-03-07-article-nav-ux-design|Article Nav 설계]]
