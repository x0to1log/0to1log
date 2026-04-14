alter table public.handbook_terms
  add column if not exists summary_ko text,
  add column if not exists summary_en text;
