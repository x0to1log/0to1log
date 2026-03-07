-- 00001_initial_schema.sql
-- Phase 1a: admin_users + posts + RLS
-- Reference: docs/03_Backend_AI_Spec.md §2 Authentication, §3 DB Schema

-- ============================================================
-- 1. admin_users (Admin single source of truth)
-- ============================================================
CREATE TABLE admin_users (
    email         TEXT PRIMARY KEY,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Initial admin (replace with real email in production)
INSERT INTO admin_users(email) VALUES ('admin@0to1log.com');

-- ============================================================
-- 2. posts
-- ============================================================
CREATE TABLE posts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    locale          TEXT NOT NULL DEFAULT 'en' CHECK (locale IN ('en', 'ko')),
    category        TEXT NOT NULL CHECK (category IN ('ai-news', 'study', 'career', 'project')),
    post_type       TEXT CHECK (post_type IN ('research', 'business')),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),

    -- Persona-specific content (Business Analyst posts)
    content_beginner    TEXT,
    content_learner     TEXT,
    content_expert      TEXT,

    -- Single content (Research Engineer posts / Type B career/project)
    content_original    TEXT,

    -- Prompt guide items (JSONB)
    guide_items         JSONB,

    -- Related news (Business Analyst posts, JSONB)
    related_news        JSONB,

    -- No-news notice (Research Engineer posts)
    no_news_notice      TEXT,
    recent_fallback     TEXT,

    -- Metadata
    source_urls         TEXT[],
    news_temperature    INTEGER CHECK (news_temperature BETWEEN 1 AND 5),
    reading_time_min    INTEGER,
    tags                TEXT[],
    og_image_url        TEXT,

    -- AI pipeline metadata
    pipeline_model      TEXT,
    pipeline_tokens     INTEGER,
    pipeline_cost       DECIMAL(10,6),
    prompt_version      TEXT,
    pipeline_batch_id   TEXT,

    -- Locale referential integrity (07-aligned)
    translation_group_id UUID,
    source_post_id       UUID REFERENCES posts(id),
    source_post_version  INTEGER,

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    published_at    TIMESTAMPTZ,

    -- Category-post_type constraint
    CONSTRAINT chk_post_type_by_category CHECK (
        (category = 'ai-news' AND post_type IN ('research', 'business'))
        OR
        (category IN ('study', 'career', 'project') AND post_type IS NULL)
    )
);

-- Indexes
CREATE INDEX idx_posts_locale ON posts(locale);
CREATE INDEX idx_posts_category ON posts(category);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_published ON posts(published_at DESC);
CREATE INDEX idx_posts_slug ON posts(slug);
CREATE INDEX idx_posts_batch ON posts(pipeline_batch_id);
CREATE UNIQUE INDEX uq_posts_daily_ai_type
    ON posts(pipeline_batch_id, post_type)
    WHERE category = 'ai-news' AND pipeline_batch_id IS NOT NULL;

-- ============================================================
-- 3. RLS (Row Level Security)
-- Reference: docs/03 §2 RLS policies
-- ============================================================
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

-- admin_users: authenticated users can check their own admin status (needed by posts RLS subquery)
CREATE POLICY "admin_users_read_own" ON admin_users FOR SELECT
    USING (email = auth.email());

-- admin_users: no public write access (managed via service_role only)
CREATE POLICY "admin_users_no_write" ON admin_users FOR INSERT
    WITH CHECK (false);
CREATE POLICY "admin_users_no_update" ON admin_users FOR UPDATE
    USING (false);
CREATE POLICY "admin_users_no_delete" ON admin_users FOR DELETE
    USING (false);

-- posts: anyone can read published, admin can read all
CREATE POLICY "posts_read" ON posts FOR SELECT
    USING (
        status = 'published'
        OR EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );

-- posts: admin only can insert
CREATE POLICY "posts_write" ON posts FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );

-- posts: admin only can update
CREATE POLICY "posts_update" ON posts FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );

-- posts: admin only can delete
CREATE POLICY "posts_delete" ON posts FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );
