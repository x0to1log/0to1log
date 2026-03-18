-- 00031_term_feedback_archived.sql
-- Add archived flag to term_feedback for admin workflow
ALTER TABLE term_feedback ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_term_feedback_archived ON term_feedback(archived);

-- Admin can update any term_feedback (for archiving)
CREATE POLICY "admin_update_all_feedback" ON term_feedback FOR UPDATE
  USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );
