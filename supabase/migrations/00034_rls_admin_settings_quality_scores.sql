-- 00034_rls_admin_settings_quality_scores.sql
-- Enable RLS on admin_settings and handbook_quality_scores tables.
-- Both were flagged as CRITICAL in Supabase security dashboard.

-- 1. admin_settings
ALTER TABLE admin_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY admin_settings_select ON admin_settings
FOR SELECT USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

CREATE POLICY admin_settings_admin_all ON admin_settings
FOR ALL USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

-- 2. handbook_quality_scores
ALTER TABLE handbook_quality_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY hqs_select ON handbook_quality_scores
FOR SELECT USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

CREATE POLICY hqs_admin_all ON handbook_quality_scores
FOR ALL USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);
