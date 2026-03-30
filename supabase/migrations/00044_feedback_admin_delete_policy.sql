-- 00044_feedback_admin_delete_policy.sql
-- Fix: admin could not delete feedback due to missing DELETE policy.
-- Only cf_delete_own existed (user can delete own), but no admin policy.

CREATE POLICY "cf_admin_delete_all"
  ON content_feedback FOR DELETE
  TO authenticated
  USING (EXISTS (SELECT 1 FROM admin_users WHERE admin_users.user_id = auth.uid()));
