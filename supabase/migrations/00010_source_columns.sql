-- 00010_source_columns.sql
-- Add source column to track how content was created
-- Merged from: 00010_handbook_source + 00012_blog_source

-- handbook_terms: Values: 'manual', 'pipeline', 'ai-suggested'
ALTER TABLE handbook_terms
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual';

-- blog_posts: Values: 'manual', 'pipeline', 'ai-translated', 'ai-drafted'
ALTER TABLE blog_posts
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual';
