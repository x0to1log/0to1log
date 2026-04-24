-- Add LLM-as-judge quality scoring columns to product_generation_logs.
-- Populated by _score_profile() (gpt-5-nano) after generation completes.
-- quality_score: 0-100 integer (overall dimension average × 10).
-- quality_breakdown: jsonb with {specificity, grounding, voice, bilingual, top_issue}.

ALTER TABLE product_generation_logs
  ADD COLUMN IF NOT EXISTS quality_score integer,
  ADD COLUMN IF NOT EXISTS quality_breakdown jsonb;

-- Partial index — only rows with a score, sorted newest-first by score desc.
-- Used by "show me the worst-scoring recent generations" admin queries.
CREATE INDEX IF NOT EXISTS idx_product_gen_logs_quality
  ON product_generation_logs(quality_score DESC, created_at DESC)
  WHERE quality_score IS NOT NULL;
