@AGENTS.md

<!-- Shared project rules live in AGENTS.md (single source). Only Claude Code-specific notes go below. -->

## Project Skills (Claude Code)

- **0to1-prompt-audit**: Audit prompt files against P0/P1/P2 quality criteria.
  - Targets: `backend/services/agents/prompts_advisor.py`, `prompts_news_pipeline.py`, `prompts_handbook_types.py`
  - Criteria: `vault/09-Implementation/plans/2026-03-18-prompt-audit-fixes.md` (live reference)
  - Usage: `/prompt-audit [advisor|news|handbook]` (no args = audit all 3 files)

- **0to1-sprint-sync**: Sprint start/end synchronization.
  - Start mode: report on in-progress/final-verification/remaining tasks from ACTIVE_SPRINT.md + recommend next task.
  - End mode: mark completed tasks + identify vault notes to update + suggest commit.
  - Reference: `vault/09-Implementation/plans/ACTIVE_SPRINT.md`
