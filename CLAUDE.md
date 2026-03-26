# 0to1log

AI news curation + AI glossary (Handbook) + IT blog platform. Solo project (Amy).

## Stack

- Frontend: Astro v5 + Tailwind CSS v4 + Vercel (`frontend/`)
- Backend: FastAPI + Railway (`backend/`)
- DB: Supabase (PostgreSQL + Auth + RLS)
- AI: OpenAI (gpt-4.1 / gpt-4.1-mini / o4-mini) + PydanticAI
- Search: Tavily API (semantic)

## Phase

Current phase: see `vault/09-Implementation/plans/ACTIVE_SPRINT.md`.

## Reference Rules

- `vault/` = project knowledge base (Obsidian vault). Specs, designs, plans, decisions all live here.
- `vault/09-Implementation/plans/` = design docs, implementation plans, sprint files.
- CLAUDE.md contains execution rules only. Do not duplicate spec content here.
- New design/plan documents go in `vault/09-Implementation/plans/YYYY-MM-DD-<topic>.md`.

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

## Python venv policy

- Use `backend/.venv` only for backend Python commands.
- Do not create or use `backend/venv`.

## Git Branch Policy

- Use a main-only workflow.
- Day-to-day implementation happens directly on `main`.
- Commit small, coherent groups of changes so the history stays readable.
- Push to `main` after local verification and when the checkpoint is stable.
- Feature branches are optional, not the default operating mode.

## Project Skills

- **0to1-prompt-audit**: Audit prompt files against P0/P1/P2 quality criteria.
  - Targets: `backend/services/agents/prompts_advisor.py`, `prompts_news_pipeline.py`, `prompts_handbook_types.py`
  - Criteria: `vault/09-Implementation/plans/2026-03-18-prompt-audit-fixes.md` (live reference)
  - Usage: `/prompt-audit [advisor|news|handbook]` (no args = audit all 3 files)

- **0to1-sprint-sync**: Sprint start/end synchronization.
  - Start mode: report on in-progress/final-verification/remaining tasks from ACTIVE_SPRINT.md + recommend next task.
  - End mode: mark completed tasks + identify vault notes to update + suggest commit.
  - Reference: `vault/09-Implementation/plans/ACTIVE_SPRINT.md`
