-- 00043_webhooks.sql
-- Webhook endpoints for publish notifications (Discord, Slack, custom).

CREATE TABLE webhooks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  label         TEXT NOT NULL,
  url           TEXT NOT NULL,
  platform      TEXT NOT NULL CHECK (platform IN ('discord', 'slack', 'custom')),
  is_active     BOOLEAN NOT NULL DEFAULT true,
  fail_count    INTEGER NOT NULL DEFAULT 0,
  last_error    TEXT,
  last_fired_at TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;

CREATE POLICY webhooks_admin_select ON webhooks
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );

CREATE POLICY webhooks_admin_insert ON webhooks
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );

CREATE POLICY webhooks_admin_update ON webhooks
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );

CREATE POLICY webhooks_admin_delete ON webhooks
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
  );
