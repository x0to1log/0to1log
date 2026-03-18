-- Explicitly grant execute on increment_product_view_count to anon and authenticated roles.
-- The function already restricts updates to published products only.
GRANT EXECUTE ON FUNCTION increment_product_view_count(uuid) TO anon, authenticated;
