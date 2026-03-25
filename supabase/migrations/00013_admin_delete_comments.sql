-- 00013_admin_delete_comments.sql
-- Allow admins to delete any news/blog comment while preserving existing
-- "users can delete own comment" policies.

CREATE POLICY "Admins can delete any news comment" ON news_comments
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1
      FROM admin_users au
      WHERE au.user_id = auth.uid()
    )
  );

CREATE POLICY "Admins can delete any blog comment" ON blog_comments
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1
      FROM admin_users au
      WHERE au.user_id = auth.uid()
    )
  );
