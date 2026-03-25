-- 00033_handbook_quality_scores.sql
-- Dedicated table for handbook term quality scores.
-- Records from both pipeline and admin editor quality checks,
-- preserving history across re-generations.

CREATE TABLE handbook_quality_scores (
  id         uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  term_id    uuid REFERENCES handbook_terms(id) ON DELETE CASCADE,
  term_slug  text NOT NULL,
  score      integer NOT NULL CHECK (score BETWEEN 0 AND 100),
  breakdown  jsonb DEFAULT '{}'::jsonb,
  term_type  text,
  source     text NOT NULL DEFAULT 'pipeline' CHECK (source IN ('pipeline', 'manual')),
  created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_hqs_term_id ON handbook_quality_scores(term_id);
CREATE INDEX idx_hqs_created_at ON handbook_quality_scores(created_at DESC);
CREATE INDEX idx_hqs_source ON handbook_quality_scores(source);
