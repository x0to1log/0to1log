-- 00036_product_enrichment.sql
-- Add enrichment columns for scenarios, pros/cons, editorial, and metadata fields.

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

COMMENT ON COLUMN ai_products.scenarios IS 'Real-world usage scenarios (EN, array of {title, steps})';
COMMENT ON COLUMN ai_products.scenarios_ko IS 'Real-world usage scenarios (KO)';
COMMENT ON COLUMN ai_products.pros_cons IS 'Pros and cons (EN, {pros: [...], cons: [...]})';
COMMENT ON COLUMN ai_products.pros_cons_ko IS 'Pros and cons (KO)';
COMMENT ON COLUMN ai_products.difficulty IS 'Accessibility level: beginner, intermediate, advanced';
COMMENT ON COLUMN ai_products.editor_note IS 'Editor personal comment (EN)';
COMMENT ON COLUMN ai_products.editor_note_ko IS 'Editor personal comment (KO)';
COMMENT ON COLUMN ai_products.official_resources IS 'Official links (array of {label, url})';
COMMENT ON COLUMN ai_products.verified_at IS 'Date when product info was last verified';
COMMENT ON COLUMN ai_products.korean_quality_note IS 'Note on Korean language support quality';
