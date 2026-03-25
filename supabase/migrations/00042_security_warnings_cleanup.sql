-- 00042_security_warnings_cleanup.sql
-- Fix Supabase security dashboard warnings:
-- 1. Function Search Path Mutable on two functions
-- 2. Extension in Public (moddatetime)

-- Fix search_path on mutable functions
ALTER FUNCTION increment_product_view_count(product_id uuid)
SET search_path = public;

ALTER FUNCTION update_product_like_count()
SET search_path = public;

-- Move moddatetime extension from public to extensions schema
CREATE SCHEMA IF NOT EXISTS extensions;
DROP EXTENSION IF EXISTS moddatetime CASCADE;
CREATE EXTENSION moddatetime SCHEMA extensions;

-- Recreate triggers that depended on moddatetime
CREATE TRIGGER set_blog_categories_updated_at
BEFORE UPDATE ON blog_categories
FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

CREATE TRIGGER set_category_groups_updated_at
BEFORE UPDATE ON category_groups
FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);
