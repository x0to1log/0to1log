ALTER TABLE pipeline_artifacts
    ADD COLUMN IF NOT EXISTS source_post_id UUID REFERENCES news_posts(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_source_post_resume
    ON pipeline_artifacts(batch_id, post_type, locale, source_post_id, updated_at DESC);
