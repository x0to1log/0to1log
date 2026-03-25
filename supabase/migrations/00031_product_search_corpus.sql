-- 00031_product_search_corpus.sql
-- Add search_corpus column for AI-generated intent-based search keywords.

ALTER TABLE ai_products
  ADD COLUMN IF NOT EXISTS search_corpus text;

COMMENT ON COLUMN ai_products.search_corpus
  IS 'AI-generated search keywords: intent phrases, synonyms, related terms (KO+EN mixed). Used for client-side text matching.';
