-- 00006_handbook_terms.sql
-- Handbook: Tech glossary terms (bilingual EN/KO)
-- Reference: docs/08_Handbook.md Section 4

-- ============================================================
-- 1. handbook_terms
-- ============================================================
CREATE TABLE IF NOT EXISTS handbook_terms (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Common meta (language-independent)
    term                    TEXT NOT NULL,
    slug                    TEXT UNIQUE NOT NULL,
    korean_name             TEXT,
    difficulty              TEXT CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    category                TEXT,
    related_term_slugs      TEXT[],
    is_favourite            BOOLEAN DEFAULT FALSE,

    -- Korean content
    definition_ko              TEXT,
    plain_explanation_ko       TEXT,
    technical_description_ko   TEXT,
    example_analogy_ko         TEXT,
    body_markdown_ko           TEXT,

    -- English content
    definition_en              TEXT,
    plain_explanation_en       TEXT,
    technical_description_en   TEXT,
    example_analogy_en         TEXT,
    body_markdown_en           TEXT,

    -- Workflow
    status                  TEXT NOT NULL DEFAULT 'draft'
                            CHECK (status IN ('draft', 'published', 'archived')),

    -- Migration tracking
    notion_page_id          TEXT,

    -- Timestamps
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    published_at            TIMESTAMPTZ
);

-- ============================================================
-- 2. Indexes
-- ============================================================
CREATE INDEX idx_handbook_category   ON handbook_terms(category);
CREATE INDEX idx_handbook_difficulty ON handbook_terms(difficulty);
CREATE INDEX idx_handbook_status     ON handbook_terms(status);

-- ============================================================
-- 3. RLS (same pattern as posts in 00001)
-- ============================================================
ALTER TABLE handbook_terms ENABLE ROW LEVEL SECURITY;

-- Public: anyone can read published; admin can read all
CREATE POLICY "handbook_read" ON handbook_terms FOR SELECT
    USING (
        status = 'published'
        OR EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );

-- Admin only: insert
CREATE POLICY "handbook_write" ON handbook_terms FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );

-- Admin only: update
CREATE POLICY "handbook_update" ON handbook_terms FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );

-- Admin only: delete
CREATE POLICY "handbook_delete" ON handbook_terms FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.email = auth.email()
        )
    );
