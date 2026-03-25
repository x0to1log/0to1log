-- 00012_handbook_difficulty_levels.sql
-- Handbook difficulty-level content system: basic (기초) / advanced (심화)
-- Replaces single body_markdown + card fields with two content versions per language.
-- Merged from: 00013 (add columns + migrate data) + 00015 (drop legacy columns)

-- 1) Add new body columns for two difficulty levels
ALTER TABLE handbook_terms
  ADD COLUMN IF NOT EXISTS body_basic_ko TEXT,
  ADD COLUMN IF NOT EXISTS body_basic_en TEXT,
  ADD COLUMN IF NOT EXISTS body_advanced_ko TEXT,
  ADD COLUMN IF NOT EXISTS body_advanced_en TEXT;

-- 2) Migrate existing data:
--    body_markdown + plain_explanation + example_analogy → body_basic
--    technical_description → body_advanced (seed)
UPDATE handbook_terms SET
  body_basic_ko = COALESCE(body_markdown_ko, '')
    || CASE WHEN plain_explanation_ko IS NOT NULL AND plain_explanation_ko != ''
         THEN E'\n\n## 쉬운 설명\n' || plain_explanation_ko ELSE '' END
    || CASE WHEN example_analogy_ko IS NOT NULL AND example_analogy_ko != ''
         THEN E'\n\n## 예시·비유\n' || example_analogy_ko ELSE '' END,
  body_basic_en = COALESCE(body_markdown_en, '')
    || CASE WHEN plain_explanation_en IS NOT NULL AND plain_explanation_en != ''
         THEN E'\n\n## Plain Explanation\n' || plain_explanation_en ELSE '' END
    || CASE WHEN example_analogy_en IS NOT NULL AND example_analogy_en != ''
         THEN E'\n\n## Examples & Analogies\n' || example_analogy_en ELSE '' END,
  body_advanced_ko = CASE WHEN technical_description_ko IS NOT NULL AND technical_description_ko != ''
    THEN technical_description_ko ELSE NULL END,
  body_advanced_en = CASE WHEN technical_description_en IS NOT NULL AND technical_description_en != ''
    THEN technical_description_en ELSE NULL END;

-- 3) User preference for handbook difficulty level
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS handbook_level TEXT DEFAULT 'basic';

-- 4) Drop legacy columns (verified in production)
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
