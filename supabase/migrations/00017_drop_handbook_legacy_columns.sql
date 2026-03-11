-- Drop legacy handbook columns after 00015 migration has been verified in production.
-- Safe to re-run: all drops use IF EXISTS.

DROP INDEX IF EXISTS idx_handbook_difficulty;

ALTER TABLE handbook_terms
  DROP COLUMN IF EXISTS plain_explanation_ko,
  DROP COLUMN IF EXISTS technical_description_ko,
  DROP COLUMN IF EXISTS example_analogy_ko,
  DROP COLUMN IF EXISTS body_markdown_ko,
  DROP COLUMN IF EXISTS plain_explanation_en,
  DROP COLUMN IF EXISTS technical_description_en,
  DROP COLUMN IF EXISTS example_analogy_en,
  DROP COLUMN IF EXISTS body_markdown_en,
  DROP COLUMN IF EXISTS difficulty;
