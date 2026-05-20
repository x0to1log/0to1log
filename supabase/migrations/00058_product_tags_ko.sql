-- Add Korean display tags for AI products.
-- tags remains the canonical English/search tag list; tags_ko is locale display copy.

ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS tags_ko text[];

CREATE INDEX IF NOT EXISTS idx_ai_products_tags_ko
  ON ai_products USING GIN (tags_ko);

COMMENT ON COLUMN ai_products.tags IS 'Canonical English product tags, 1-3 kebab-case labels';
COMMENT ON COLUMN ai_products.tags_ko IS 'Korean display product tags, 1-3 natural-language labels';
