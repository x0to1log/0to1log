-- 00014_quality_columns.sql
-- Add quality_score and quality_flags columns to news_posts table.
-- Run manually: DO NOT apply automatically.
ALTER TABLE news_posts ADD COLUMN IF NOT EXISTS quality_score integer DEFAULT NULL;
ALTER TABLE news_posts ADD COLUMN IF NOT EXISTS quality_flags jsonb DEFAULT NULL;
