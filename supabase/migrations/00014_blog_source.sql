-- Add source column to track how blog posts were created
-- Values: 'manual', 'pipeline', 'ai-translated', 'ai-drafted'
ALTER TABLE blog_posts
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual';
