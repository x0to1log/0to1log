# 0to1log

AI news curation + AI glossary (Handbook) + IT blog platform. Solo project (Amy).

## Stack

- Frontend: Astro v5 + Tailwind CSS v4 + Vercel (`frontend/`)
- Backend: FastAPI + Railway (`backend/`)
- DB: Supabase (PostgreSQL + Auth + RLS)
- AI: OpenAI + PydanticAI. Production model names live in `backend/core/config.py` (single source of truth).
- Search: Tavily API (semantic)

## Phase

Current phase: see `vault/09-Implementation/plans/ACTIVE_SPRINT.md`.

## Reference Rules

- `vault/` = project knowledge base (Obsidian vault). Specs, designs, plans, decisions all live here.
- `vault/09-Implementation/plans/` = design docs, implementation plans, sprint files.
- AGENTS.md contains execution rules only. Do not duplicate spec content here.
- New design/plan documents go in `vault/09-Implementation/plans/YYYY-MM-DD-<topic>.md`.

## Directory

```
frontend/  → Vercel (Astro v5)
backend/   → Railway (FastAPI)
supabase/  → DB migrations
vault/     → Project knowledge base (specs, plans, decisions)
docs/      → Legacy spec files (modify only on explicit user request)
```

## Workflow

0. **Plan first.** All work requires a plan before implementation, except trivial code fixes (typos, 1-line changes) or vault doc sync. Use Plan mode or vault plan documents.
1. Session start: check `vault/` to understand current sprint/plan state.
2. Move exactly 1 task to `doing` → implement → pass completion criteria → mark `done` + `[x]`.
3. Keep the `Current Doing` table in sync with task status.
4. When marking `done`, include evidence links (PR/logs/screenshots).
5. After completing a plan: update related vault notes (changed architecture, new decisions, etc.).

## Vault Rules

- Write design/plan documents in `vault/09-Implementation/plans/`.
- After implementation: grep `vault/` for changed file/feature names → identify related notes → update only essential content.
- Move completed design/plan documents to `vault/90-Archive/YYYY-MM/plans-completed/` or `plans-archive/` (read-only).
- Keep only active plans in `vault/09-Implementation/plans/` (ACTIVE_SPRINT.md and current Phase files).

## Prohibitions (Global)

- No Framer Motion. Use `motion` (v11+) instead.
- Do not modify `docs/` legacy spec files without explicit user request.
- Do not advance to next Phase if sprint gate criteria are not met.
- Never commit `.env` files (commit `.env.example` only).
- Always commit `package-lock.json` (CI reproducibility).

## Commit

- Commit by feature unit. Messages: `feat:`, `fix:`, `chore:`, `docs:`.
- Separate code implementation sessions from review sessions.
- Group related changes into a single commit. E.g., 3 prompt tweaks for the same issue = 1 commit; a bug's root cause + fix = 1 commit.
- Before committing, ask: "Do these changes share a single intent?" If not, split them.
- Do NOT include `Co-Authored-By` in commit messages.

## Python venv policy

- Use `backend/.venv` only for backend Python commands.
- Do not create or use `backend/venv`.

## Git Branch Policy

- Use a main-only workflow.
- Day-to-day implementation happens directly on `main`.
- Commit small, coherent groups of changes so the history stays readable.
- Push to `main` after local verification and when the checkpoint is stable.
- Feature branches are optional, not the default operating mode.
