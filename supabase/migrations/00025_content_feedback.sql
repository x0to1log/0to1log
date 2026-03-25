-- 00025_content_feedback.sql
-- Unified content feedback table (replaces term_feedback)

-- 1. Create table
CREATE TABLE content_feedback (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('news','handbook','blog','product')),
  source_id   UUID NOT NULL,
  locale      TEXT NOT NULL CHECK (locale IN ('ko','en')),
  reaction    TEXT NOT NULL CHECK (reaction IN ('positive','negative')),
  reason      TEXT,
  message     TEXT,
  archived    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, source_type, source_id, locale)
);

ALTER TABLE content_feedback ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_content_feedback_source ON content_feedback(source_type, source_id, locale);
CREATE INDEX idx_content_feedback_user ON content_feedback(user_id);
CREATE INDEX idx_content_feedback_archived ON content_feedback(archived);

-- 2. RLS policies — authenticated users own feedback
CREATE POLICY "cf_select_own" ON content_feedback FOR SELECT TO authenticated
  USING (auth.uid() = user_id);
CREATE POLICY "cf_insert_own" ON content_feedback FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);
CREATE POLICY "cf_update_own" ON content_feedback FOR UPDATE TO authenticated
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "cf_delete_own" ON content_feedback FOR DELETE TO authenticated
  USING (auth.uid() = user_id);

-- 3. RLS policies — admin read + update (for archiving)
CREATE POLICY "cf_admin_read_all" ON content_feedback FOR SELECT
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
CREATE POLICY "cf_admin_update_all" ON content_feedback FOR UPDATE
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

-- 4. Migrate data from term_feedback
INSERT INTO content_feedback (user_id, source_type, source_id, locale, reaction, reason, message, archived, created_at, updated_at)
SELECT user_id, 'handbook', term_id, locale,
  CASE reaction WHEN 'helpful' THEN 'positive' WHEN 'confusing' THEN 'negative' ELSE 'positive' END,
  CASE reaction WHEN 'confusing' THEN 'confusing' ELSE NULL END,
  message, FALSE, created_at, updated_at
FROM term_feedback
WHERE reaction IN ('helpful', 'confusing');

-- 5. Admin can read all profiles (moved from deleted 00030_admin_read_feedback)
CREATE POLICY "admin_read_all_profiles" ON profiles FOR SELECT
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
