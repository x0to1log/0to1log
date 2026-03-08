-- 00002_pipeline_tables.sql
-- Pipeline infrastructure tables
-- Reference: docs/03_Backend_AI_Spec.md §3, docs/02_AI_Pipeline.md

-- ============================================================
-- 1. news_candidates (Tavily/HN/GitHub 수집 후보)
-- ============================================================
CREATE TABLE news_candidates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id        TEXT NOT NULL,
    title           TEXT NOT NULL,
    url             TEXT NOT NULL,
    snippet         TEXT,
    source          TEXT NOT NULL,
    assigned_type   TEXT CHECK (assigned_type IN (
                        'research', 'business_main', 'big_tech', 'industry_biz', 'new_tools'
                    )),
    relevance_score NUMERIC(3,2),
    ranking_reason  TEXT,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                        'pending', 'selected', 'rejected', 'published'
                    )),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_news_candidates_batch ON news_candidates(batch_id);

-- ============================================================
-- 2. pipeline_runs (중복 실행 방지 락)
-- ============================================================
CREATE TABLE pipeline_runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_key     TEXT UNIQUE NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    last_error  TEXT
);

-- ============================================================
-- 3. pipeline_logs (실행 로그 + 비용 추적)
-- ============================================================
CREATE TABLE pipeline_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID REFERENCES pipeline_runs(id),
    pipeline_type   TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN (
                        'started', 'success', 'failed', 'retried', 'no_news'
                    )),
    input_summary   TEXT,
    output_summary  TEXT,
    error_message   TEXT,
    duration_ms     INTEGER,
    model_used      TEXT,
    tokens_used     INTEGER,
    cost_usd        NUMERIC(8,4),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 4. admin_notifications (파이프라인 실패 알림)
-- ============================================================
CREATE TABLE admin_notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        TEXT NOT NULL,
    title       TEXT NOT NULL,
    message     TEXT,
    is_read     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 5. point_transactions (Phase 4 스텁)
-- ============================================================
CREATE TABLE point_transactions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    amount      INTEGER NOT NULL,
    reason      TEXT NOT NULL,
    event_key   TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, event_key)
);

-- ============================================================
-- RLS (uid-based)
-- ============================================================
ALTER TABLE news_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE point_transactions ENABLE ROW LEVEL SECURITY;

-- Admin: full access to pipeline tables
CREATE POLICY "admin_full_news_candidates" ON news_candidates FOR ALL
    USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

CREATE POLICY "admin_full_pipeline_runs" ON pipeline_runs FOR ALL
    USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

CREATE POLICY "admin_full_pipeline_logs" ON pipeline_logs FOR ALL
    USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

CREATE POLICY "admin_full_admin_notifications" ON admin_notifications FOR ALL
    USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

-- point_transactions: admin full + own SELECT
CREATE POLICY "admin_full_point_transactions" ON point_transactions FOR ALL
    USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

CREATE POLICY "own_point_transactions_read" ON point_transactions FOR SELECT
    USING (auth.uid() = user_id);
