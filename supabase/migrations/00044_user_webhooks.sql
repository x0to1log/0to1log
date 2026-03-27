-- 00044_user_webhooks.sql
-- User self-service webhook subscriptions for news notifications.
-- Design doc: vault/09-Implementation/plans/2026-03-27-user-webhook-subscriptions.md

CREATE TABLE user_webhooks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  label         TEXT NOT NULL,
  url           TEXT NOT NULL,
  platform      TEXT NOT NULL CHECK (platform IN ('discord', 'slack', 'custom')),
  locale        TEXT NOT NULL DEFAULT 'all' CHECK (locale IN ('all', 'en', 'ko')),
  is_active     BOOLEAN NOT NULL DEFAULT true,
  fail_count    INTEGER NOT NULL DEFAULT 0,
  last_error    TEXT,
  last_fired_at TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_webhooks_user ON user_webhooks(user_id);
CREATE INDEX idx_user_webhooks_active ON user_webhooks(is_active) WHERE is_active = true;

ALTER TABLE user_webhooks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own webhooks"
  ON user_webhooks FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users insert own webhooks (max 5)"
  ON user_webhooks FOR INSERT WITH CHECK (
    auth.uid() = user_id
    AND (SELECT count(*) FROM user_webhooks WHERE user_id = auth.uid()) < 5
  );

CREATE POLICY "Users update own webhooks"
  ON user_webhooks FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users delete own webhooks"
  ON user_webhooks FOR DELETE USING (auth.uid() = user_id);
