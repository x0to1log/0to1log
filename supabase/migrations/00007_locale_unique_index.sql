-- Migration: Add locale to posts unique index for EN/KO dual-row support
-- Context: Pipeline now creates EN (canonical) + KO (translated) rows per batch.
-- The old index only covered (pipeline_batch_id, post_type), which would conflict
-- when both EN and KO rows share the same batch_id and post_type.

DROP INDEX IF EXISTS uq_posts_daily_ai_type;

CREATE UNIQUE INDEX uq_posts_daily_ai_type
    ON posts(pipeline_batch_id, post_type, locale)
    WHERE category = 'ai-news' AND pipeline_batch_id IS NOT NULL;
