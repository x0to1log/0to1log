-- 00041_backfill_handbook_quality_scores.sql
-- Migrate existing handbook quality scores from pipeline_logs.debug_meta
-- into the dedicated handbook_quality_scores table.

INSERT INTO handbook_quality_scores (term_slug, score, breakdown, term_type, source, created_at)
SELECT
  COALESCE(debug_meta->>'term', 'unknown'),
  (debug_meta->>'quality_score')::integer,
  COALESCE(debug_meta - 'quality_score' - 'term' - 'term_type' - 'input_tokens' - 'output_tokens' - 'source', '{}'::jsonb),
  debug_meta->>'term_type',
  COALESCE(debug_meta->>'source', 'pipeline'),
  created_at
FROM pipeline_logs
WHERE pipeline_type = 'handbook.quality_check'
  AND debug_meta->>'quality_score' IS NOT NULL
  AND (debug_meta->>'quality_score')::integer BETWEEN 0 AND 100
ON CONFLICT DO NOTHING;
