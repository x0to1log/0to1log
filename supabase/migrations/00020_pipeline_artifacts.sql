-- 00020_pipeline_artifacts.sql
-- pipeline_artifacts table for resume support (merged from 20260313)

-- ============================================================
-- 1. pipeline_artifacts
-- ============================================================
CREATE TABLE IF NOT EXISTS pipeline_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    run_key TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    post_type TEXT NOT NULL,
    locale TEXT NOT NULL,
    candidate_title TEXT,
    candidate_url TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('partial', 'consumed', 'superseded')),
    completed_stages TEXT[] NOT NULL DEFAULT '{}',
    failed_stage TEXT,
    last_validation_error TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    resumed_from_artifact_id UUID REFERENCES pipeline_artifacts(id),
    source_post_id UUID REFERENCES news_posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_resume_lookup
    ON pipeline_artifacts(batch_id, post_type, locale, candidate_url, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_source_post_resume
    ON pipeline_artifacts(batch_id, post_type, locale, source_post_id, updated_at DESC);

-- ============================================================
-- 3. RLS
-- ============================================================
ALTER TABLE pipeline_artifacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_full_pipeline_artifacts" ON pipeline_artifacts FOR ALL
    USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
