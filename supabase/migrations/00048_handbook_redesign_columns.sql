-- Handbook Basic section redesign (2026-04-10)
-- Adds level-independent fields for hero card, references footer, and sidebar checklist.
-- Related plan: vault/09-Implementation/plans/2026-04-09-handbook-section-redesign.md
-- Implementation plan: vault/09-Implementation/plans/2026-04-10-handbook-save-and-render.md

ALTER TABLE handbook_terms
  ADD COLUMN IF NOT EXISTS hero_news_context_ko text,
  ADD COLUMN IF NOT EXISTS hero_news_context_en text,
  ADD COLUMN IF NOT EXISTS references_ko jsonb,
  ADD COLUMN IF NOT EXISTS references_en jsonb,
  ADD COLUMN IF NOT EXISTS sidebar_checklist_ko text,
  ADD COLUMN IF NOT EXISTS sidebar_checklist_en text;

-- No RLS changes — existing handbook_terms policies already cover all columns.

COMMENT ON COLUMN handbook_terms.hero_news_context_ko IS
  'Hero card: 3-line news quote block shown above Basic/Advanced level switcher';
COMMENT ON COLUMN handbook_terms.hero_news_context_en IS
  'Hero card: 3-line news quote block (EN), shown above Basic/Advanced level switcher';
COMMENT ON COLUMN handbook_terms.references_ko IS
  'References footer: JSON array of {title, authors, year, venue, type, url, tier, annotation}';
COMMENT ON COLUMN handbook_terms.references_en IS
  'References footer (EN): same JSON shape as references_ko';
COMMENT ON COLUMN handbook_terms.sidebar_checklist_ko IS
  'Sidebar understanding-check block shown in right rail during Basic view';
COMMENT ON COLUMN handbook_terms.sidebar_checklist_en IS
  'Sidebar understanding-check block (EN) shown in right rail during Basic view';
