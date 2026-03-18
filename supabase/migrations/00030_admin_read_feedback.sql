-- 00030_admin_read_feedback.sql
-- Allow admin users to read all term_feedback and profiles for the feedback admin page

-- Admin can read all term_feedback (existing policy only allows own feedback)
CREATE POLICY "admin_read_all_feedback" ON term_feedback FOR SELECT
  USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );

-- Admin can read all profiles (existing policy only allows own + public)
CREATE POLICY "admin_read_all_profiles" ON profiles FOR SELECT
  USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );
