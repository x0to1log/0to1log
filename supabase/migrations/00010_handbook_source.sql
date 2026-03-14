-- Add source column to track how handbook terms were created
ALTER TABLE handbook_terms
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual';

-- Existing rows stay as 'manual'. Values: 'manual', 'pipeline', 'ai-suggested'
