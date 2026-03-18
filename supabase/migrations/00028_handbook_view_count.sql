-- 00028_handbook_view_count.sql
-- Add view_count to handbook_terms + RPC for anonymous increment
-- Pattern: same as ai_products (00021) + grant (00027)

-- 1. Column
ALTER TABLE handbook_terms ADD COLUMN IF NOT EXISTS view_count INT DEFAULT 0;

-- 2. Index (popular-terms query)
CREATE INDEX IF NOT EXISTS idx_handbook_view_count ON handbook_terms(view_count DESC);

-- 3. RPC: increment (anon + authenticated)
CREATE OR REPLACE FUNCTION increment_handbook_view_count(term_id uuid)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE handbook_terms
  SET view_count = view_count + 1
  WHERE id = term_id AND status = 'published';
$$;

GRANT EXECUTE ON FUNCTION increment_handbook_view_count(uuid) TO anon, authenticated;
