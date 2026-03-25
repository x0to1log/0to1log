-- 00021_product_detail_content.sql
-- Add getting_started and pricing_detail columns for enriched detail pages

ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS getting_started jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS getting_started_ko jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS pricing_detail text,
  ADD COLUMN IF NOT EXISTS pricing_detail_ko text;

COMMENT ON COLUMN ai_products.getting_started IS 'Getting started steps (EN strings array, 3 steps)';
COMMENT ON COLUMN ai_products.getting_started_ko IS 'Getting started steps (KO strings array)';
COMMENT ON COLUMN ai_products.pricing_detail IS 'Detailed pricing info as markdown (EN)';
COMMENT ON COLUMN ai_products.pricing_detail_ko IS 'Detailed pricing info as markdown (KO)';
