-- 00014_term_feedback.sql
-- User feedback on handbook terms (helpful / confusing reactions)

CREATE TABLE term_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  term_id UUID NOT NULL REFERENCES handbook_terms(id) ON DELETE CASCADE,
  locale TEXT NOT NULL CHECK (locale IN ('en', 'ko')),
  reaction TEXT NOT NULL CHECK (reaction IN ('helpful', 'confusing')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, term_id, locale)
);

CREATE INDEX IF NOT EXISTS idx_term_feedback_term_locale
  ON term_feedback (term_id, locale);

CREATE INDEX IF NOT EXISTS idx_term_feedback_user
  ON term_feedback (user_id);

ALTER TABLE term_feedback ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "term_feedback_select_own" ON term_feedback;
CREATE POLICY "term_feedback_select_own"
  ON term_feedback
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "term_feedback_insert_own" ON term_feedback;
CREATE POLICY "term_feedback_insert_own"
  ON term_feedback
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "term_feedback_update_own" ON term_feedback;
CREATE POLICY "term_feedback_update_own"
  ON term_feedback
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "term_feedback_delete_own" ON term_feedback;
CREATE POLICY "term_feedback_delete_own"
  ON term_feedback
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
