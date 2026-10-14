-- 00059_query_path_indexes.sql
-- Indexes for hot filters that had none (2026-10-14 Supabase load audit).
-- pipeline_logs had no indexes: admin pages filter by run_id / created_at,
-- reruns delete by run_id, and the daily retention prune filters created_at.
-- Public news lists filter status + locale and sort by published_at.

create index if not exists idx_pipeline_logs_run_id
  on public.pipeline_logs (run_id);

create index if not exists idx_pipeline_logs_created_at
  on public.pipeline_logs (created_at desc);

create index if not exists idx_pipeline_checkpoints_created_at
  on public.pipeline_checkpoints (created_at);

create index if not exists idx_news_posts_status_locale_published
  on public.news_posts (status, locale, published_at desc);
