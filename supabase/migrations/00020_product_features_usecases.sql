-- 00020_product_features_usecases.sql
-- Add features and use_cases columns for enriched product detail pages

ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS features jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS features_ko jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS use_cases jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS use_cases_ko jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN ai_products.features IS 'Key feature bullets (EN strings array)';
COMMENT ON COLUMN ai_products.features_ko IS 'Key feature bullets (KO strings array)';
COMMENT ON COLUMN ai_products.use_cases IS 'Use case scenarios (EN strings array)';
COMMENT ON COLUMN ai_products.use_cases_ko IS 'Use case scenarios (KO strings array)';
