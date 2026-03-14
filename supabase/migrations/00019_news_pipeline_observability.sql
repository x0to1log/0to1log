-- 00019_news_pipeline_observability.sql
-- Add content_analysis/fact_pack/source_cards to news_posts; add observability columns to pipeline_logs

ALTER TABLE news_posts
    ADD COLUMN IF NOT EXISTS content_analysis TEXT,
    ADD COLUMN IF NOT EXISTS fact_pack JSONB,
    ADD COLUMN IF NOT EXISTS source_cards JSONB;

ALTER TABLE pipeline_logs
    ADD COLUMN IF NOT EXISTS attempt INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS post_type TEXT,
    ADD COLUMN IF NOT EXISTS locale TEXT,
    ADD COLUMN IF NOT EXISTS debug_meta JSONB NOT NULL DEFAULT '{}'::jsonb;
