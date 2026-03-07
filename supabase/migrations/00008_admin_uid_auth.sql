-- 00008_admin_uid_auth.sql
-- Security hardening: switch admin auth from email to uid-based
-- Prevents email-change privilege escalation

-- ============================================================
-- 1. Add user_id to admin_users
-- ============================================================
ALTER TABLE admin_users ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- Backfill user_id from auth.users for existing admins
UPDATE admin_users
SET user_id = au.id
FROM auth.users au
WHERE admin_users.email = au.email;

-- ============================================================
-- 2. Update admin_users RLS: email → uid
-- ============================================================
DROP POLICY "admin_users_read_own" ON admin_users;
CREATE POLICY "admin_users_read_own" ON admin_users FOR SELECT
    USING (user_id = auth.uid());

-- ============================================================
-- 3. Update posts RLS: email → uid
-- ============================================================
DROP POLICY "posts_read" ON posts;
CREATE POLICY "posts_read" ON posts FOR SELECT
    USING (
        status = 'published'
        OR EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );

DROP POLICY "posts_write" ON posts;
CREATE POLICY "posts_write" ON posts FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );

DROP POLICY "posts_update" ON posts;
CREATE POLICY "posts_update" ON posts FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );

DROP POLICY "posts_delete" ON posts;
CREATE POLICY "posts_delete" ON posts FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );

-- ============================================================
-- 4. Update pipeline tables RLS: email → uid (skip if tables don't exist)
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'news_candidates') THEN
        DROP POLICY IF EXISTS "admin_full_news_candidates" ON news_candidates;
        CREATE POLICY "admin_full_news_candidates" ON news_candidates FOR ALL
            USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'pipeline_runs') THEN
        DROP POLICY IF EXISTS "admin_full_pipeline_runs" ON pipeline_runs;
        CREATE POLICY "admin_full_pipeline_runs" ON pipeline_runs FOR ALL
            USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'pipeline_logs') THEN
        DROP POLICY IF EXISTS "admin_full_pipeline_logs" ON pipeline_logs;
        CREATE POLICY "admin_full_pipeline_logs" ON pipeline_logs FOR ALL
            USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'admin_notifications') THEN
        DROP POLICY IF EXISTS "admin_full_admin_notifications" ON admin_notifications;
        CREATE POLICY "admin_full_admin_notifications" ON admin_notifications FOR ALL
            USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'point_transactions') THEN
        DROP POLICY IF EXISTS "admin_full_point_transactions" ON point_transactions;
        CREATE POLICY "admin_full_point_transactions" ON point_transactions FOR ALL
            USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
    END IF;
END $$;

-- ============================================================
-- 5. Update handbook_terms RLS: email → uid
-- ============================================================
DROP POLICY "handbook_read" ON handbook_terms;
CREATE POLICY "handbook_read" ON handbook_terms FOR SELECT
    USING (
        status = 'published'
        OR EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );

DROP POLICY "handbook_write" ON handbook_terms;
CREATE POLICY "handbook_write" ON handbook_terms FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );

DROP POLICY "handbook_update" ON handbook_terms;
CREATE POLICY "handbook_update" ON handbook_terms FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );

DROP POLICY "handbook_delete" ON handbook_terms;
CREATE POLICY "handbook_delete" ON handbook_terms FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM admin_users au
            WHERE au.user_id = auth.uid()
        )
    );
