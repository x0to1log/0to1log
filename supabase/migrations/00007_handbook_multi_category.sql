-- 00007_handbook_multi_category.sql
-- Migrate handbook_terms from single category to multi-category (1-4)

-- 1. Add categories array column
ALTER TABLE handbook_terms ADD COLUMN categories TEXT[];

-- 2. Migrate existing single category data
UPDATE handbook_terms SET categories = ARRAY[category] WHERE category IS NOT NULL;

-- 3. Drop old column and index
DROP INDEX IF EXISTS idx_handbook_category;
ALTER TABLE handbook_terms DROP COLUMN category;

-- 4. GIN index for array containment/overlap queries
CREATE INDEX idx_handbook_categories ON handbook_terms USING GIN (categories);
