-- Add term type and facet columns for differentiated content presentation
-- type: 8 structural types (concept, model_architecture, etc.)
-- facet_intent: what the user wants to do (understand, compare, build, debug, evaluate)
-- facet_volatility: how fast this knowledge changes (stable, evolving, fast-changing)

ALTER TABLE handbook_terms
  ADD COLUMN IF NOT EXISTS term_type TEXT,
  ADD COLUMN IF NOT EXISTS facet_intent TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS facet_volatility TEXT DEFAULT 'stable';

-- Index for frontend queries filtering by type
CREATE INDEX IF NOT EXISTS idx_handbook_terms_term_type ON handbook_terms (term_type);
