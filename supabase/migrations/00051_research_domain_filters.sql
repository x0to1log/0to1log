-- 00051_research_domain_filters.sql
-- Extend news_domain_filters with research_priority + research_blocklist
-- (Phase 2 of news-pipeline-hardening, 2026-04-16)
-- Background: 2026-04-16 production digest had 8/17 research source_urls
-- in low-quality/SEO-spam domains. This migration adds two new filter_types
-- to address source quality at collection/ranking time.

-- 1. Drop the existing CHECK constraint, recreate with 5 allowed types
alter table public.news_domain_filters
  drop constraint if exists news_domain_filters_filter_type_check;

alter table public.news_domain_filters
  add constraint news_domain_filters_filter_type_check
  check (filter_type in (
    'block_non_en',
    'official_priority',
    'media_tier',
    'research_priority',
    'research_blocklist'
  ));

-- 2. Seed research_priority — high-quality research sources
insert into public.news_domain_filters (domain, filter_type, notes) values
  ('arxiv.org', 'research_priority', 'arXiv preprints'),
  ('huggingface.co', 'research_priority', 'Hugging Face models/papers'),
  ('openreview.net', 'research_priority', 'OpenReview peer review'),
  ('paperswithcode.com', 'research_priority', 'Papers with Code'),
  ('aclanthology.org', 'research_priority', 'ACL Anthology'),
  ('proceedings.mlr.press', 'research_priority', 'PMLR conference proceedings'),
  ('proceedings.neurips.cc', 'research_priority', 'NeurIPS proceedings'),
  ('distill.pub', 'research_priority', 'Distill ML research articles'),
  ('ai.googleblog.com', 'research_priority', 'Google AI blog'),
  ('research.googleblog.com', 'research_priority', 'Google Research blog'),
  ('deepmind.google', 'research_priority', 'DeepMind research'),
  ('ai.meta.com', 'research_priority', 'Meta AI research'),
  ('machinelearning.apple.com', 'research_priority', 'Apple ML research'),
  ('research.microsoft.com', 'research_priority', 'Microsoft Research'),
  ('arxiv-vanity.com', 'research_priority', 'arXiv reformatted')
on conflict (domain) do nothing;

-- 3. Seed research_blocklist — domains observed producing low-quality research source_urls
--    (from 2026-04-16 production digest analysis)
insert into public.news_domain_filters (domain, filter_type, notes) values
  ('agent-wars.com', 'research_blocklist', '2026-04-16: low-tier rewrite/aggregator'),
  ('lilting.ch', 'research_blocklist', '2026-04-16: low-tier blog'),
  ('geektak.com', 'research_blocklist', '2026-04-16: SEO content farm'),
  ('areeblog.com', 'research_blocklist', '2026-04-16: SEO blog'),
  ('gist.science', 'research_blocklist', '2026-04-16: paper summary aggregator'),
  ('inbriefly.in', 'research_blocklist', '2026-04-16: SEO content farm'),
  ('ranksquire.com', 'research_blocklist', '2026-04-16: SEO content farm'),
  ('hongqinlab.blogspot.com', 'research_blocklist', '2026-04-16: low-tier personal blog')
on conflict (domain) do nothing;
