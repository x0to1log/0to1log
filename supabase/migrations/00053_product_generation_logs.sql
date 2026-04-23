-- Product generation audit log
create table if not exists product_generation_logs (
  id uuid primary key default gen_random_uuid(),
  product_slug text,
  action text not null,
  prompt_version text not null,
  model_used text,
  tokens_used integer,
  duration_ms integer,
  success boolean not null default true,
  error_message text,
  facts jsonb,
  validation_warnings jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_product_gen_logs_slug on product_generation_logs(product_slug, created_at desc);
create index if not exists idx_product_gen_logs_version on product_generation_logs(prompt_version, created_at desc);

-- RLS: admin-only (service role bypasses anyway)
alter table product_generation_logs enable row level security;
