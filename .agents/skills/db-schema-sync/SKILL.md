---
description: Synchronize DB schema changes across backend, frontend, and data fetchers for 0to1log
---

# DB Schema Sync Skill

## Trigger
Use when the user asks to:
- "update the database schema for X"
- "the Supabase table changed"
- "add a column to X"

## Core Principle
When a database column is added, renamed, or deleted, you MUST update all corresponding layers to prevent type errors, data fetching bugs, or build failures.

## Sync Checklist

1. **Supabase Definition (Types)**
   - Check `frontend/src/lib/supabase.ts` or any manually managed type references (e.g. `interface Post`, `interface HandbookTerm`).
   - Add/update the field in TypeScript definitions. 

2. **Backend Models (SQLAlchemy / Pydantic)**
   - Check `backend/database/models.py`.
   - Update the SQLAlchemy table definition. Ensure `nullable` matches the DB schema.
   - Check `backend/api/schemas.py` or equivalent and update the Pydantic request/response models.

3. **Frontend Data Fetching**
   - Check `frontend/src/lib/pageData/` (e.g., `newsDetailPage.ts`, `handbookDetailPage.ts`).
   - If a SELECT query specifies columns, ensure the new column is included (e.g. `.select('id, title, NEW_COLUMN')`).

4. **Frontend UI Components**
   - Consider where this new data needs to appear. Find the Astro component mapping over the data and update the HTML structure if the user requests it.

## Best Practices
- Never assume `SELECT *` is used everywhere; explicit column selections are common.
- Make sure snake_case (DB/Python) to camelCase (JS/TS) mappings are handled correctly if the project enforces transformations. 
- Provide the user with a list of the exact files updated when complete.
