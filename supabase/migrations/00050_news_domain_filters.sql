-- 00050_news_domain_filters.sql
-- Replace hardcoded domain lists in backend/services/news_collection.py
-- (Phase 1 of news-pipeline-hardening, 2026-04-15)

create table if not exists public.news_domain_filters (
  domain text primary key,
  filter_type text not null check (filter_type in ('block_non_en', 'official_priority', 'media_tier')),
  notes text,
  created_at timestamptz default now()
);

-- RLS: read-only public, write via service role only
alter table public.news_domain_filters enable row level security;

drop policy if exists "news_domain_filters_read_all" on public.news_domain_filters;
create policy "news_domain_filters_read_all"
  on public.news_domain_filters
  for select
  using (true);

-- Seed data — current hardcoded values from news_collection.py L18-73
insert into public.news_domain_filters (domain, filter_type, notes) values
  -- _NON_EN_DOMAINS (L18-22)
  ('landiannews.com', 'block_non_en', 'Chinese tech news aggregator'),
  ('36kr.com', 'block_non_en', 'Chinese tech media'),
  ('unifuncs.com', 'block_non_en', 'Chinese aggregator'),
  ('minimaxi.com', 'block_non_en', 'Chinese AI company blog'),
  ('ithome.com', 'block_non_en', 'Chinese tech news'),
  ('oschina.net', 'block_non_en', 'Chinese open source community'),
  ('csdn.net', 'block_non_en', 'Chinese developer community'),
  ('juejin.cn', 'block_non_en', 'Chinese developer community'),
  ('zhihu.com', 'block_non_en', 'Chinese Q&A site'),
  ('bilibili.com', 'block_non_en', 'Chinese video platform'),
  ('baidu.com', 'block_non_en', 'Chinese search engine'),
  ('idctop.com', 'block_non_en', 'Chinese hosting news'),

  -- _OFFICIAL_SITE_DOMAINS (L52-61)
  ('openai.com', 'official_priority', 'OpenAI official'),
  ('anthropic.com', 'official_priority', 'Anthropic official'),
  ('techcommunity.microsoft.com', 'official_priority', 'Microsoft tech community'),
  ('blog.google', 'official_priority', 'Google blog'),
  ('blogs.nvidia.com', 'official_priority', 'NVIDIA blog'),
  ('developer.nvidia.com', 'official_priority', 'NVIDIA developer'),
  ('blog.cloudflare.com', 'official_priority', 'Cloudflare blog'),
  ('developer.apple.com', 'official_priority', 'Apple developer'),

  -- _MEDIA_DOMAINS (L63-73)
  ('venturebeat.com', 'media_tier', 'tech media'),
  ('techcrunch.com', 'media_tier', 'tech media'),
  ('theverge.com', 'media_tier', 'tech media'),
  ('yahoo.com', 'media_tier', 'general media'),
  ('reuters.com', 'media_tier', 'wire service'),
  ('bloomberg.com', 'media_tier', 'business media'),
  ('wsj.com', 'media_tier', 'business media'),
  ('ft.com', 'media_tier', 'business media'),
  ('wired.com', 'media_tier', 'tech media')
on conflict (domain) do nothing;
