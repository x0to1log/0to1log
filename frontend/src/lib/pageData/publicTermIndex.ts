import type { SupabaseClient } from '@supabase/supabase-js';

export interface PublicTermIndexEntry {
  term: string;
  slug: string;
  korean_name: string | null;
  term_full: string | null;
  categories: string[];
  summary: string | null;
  definition: string | null;
  basic_plain: string | null;
}

export async function fetchPublicTermIndex(
  db: SupabaseClient,
  locale: 'en' | 'ko',
  limit = 200,
): Promise<PublicTermIndexEntry[]> {
  const summaryField = locale === 'ko' ? 'summary_ko' : 'summary_en';
  const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';
  const basicField = locale === 'ko' ? 'body_basic_ko' : 'body_basic_en';
  const selectColumns = [
    'term',
    'slug',
    'korean_name',
    'term_full',
    'categories',
    `summary:${summaryField}`,
    `definition:${definitionField}`,
    `basic_plain:${basicField}`,
  ].join(', ');

  const { data, error } = await db
    .from('handbook_terms')
    .select(selectColumns)
    .eq('status', 'published')
    .limit(limit);

  if (error) {
    console.error('[public-term-index] Supabase error:', error.message);
    return [];
  }

  return ((data ?? []) as unknown as PublicTermIndexEntry[]).map((entry) => ({
    term: entry.term,
    slug: entry.slug,
    korean_name: entry.korean_name ?? null,
    term_full: entry.term_full ?? null,
    categories: entry.categories ?? [],
    summary: entry.summary ?? null,
    definition: entry.definition ?? null,
    basic_plain: entry.basic_plain ?? null,
  }));
}
