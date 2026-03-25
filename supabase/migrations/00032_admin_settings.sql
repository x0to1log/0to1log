-- 00032_admin_settings.sql
-- Key-value settings table for admin-configurable pipeline behavior.

CREATE TABLE IF NOT EXISTS admin_settings (
  key text PRIMARY KEY,
  value jsonb NOT NULL DEFAULT 'true'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Default: handbook extraction enabled during cron runs
INSERT INTO admin_settings (key, value)
VALUES ('handbook_auto_extract', 'true'::jsonb)
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE admin_settings IS 'Admin-configurable key-value settings for pipeline behavior';
