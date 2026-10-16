// frontend/src/lib/pageData/termOfDay.ts
// Term of the day, shared by the home front page and the handbook index:
// published count (head only) -> termIndex(now, count) -> one row ordered by slug.
import type { SupabaseClient } from '@supabase/supabase-js';
import { termIndex } from '../homeFront.js';

export interface TermOfDay {
  term: string;
  slug: string;
  korean_name: string | null;
  definition: string | null;
  [column: string]: unknown;
}

export interface TermOfDayResult {
  term: TermOfDay | null;
  /** published term count (0 when a query failed) */
  total: number;
}

/**
 * @param extraColumns extra select columns, e.g. 'hero_news_context_ko'
 * Never throws: failures are logged and return { term: null, total: 0 }.
 */
export async function fetchTermOfDay(
  db: SupabaseClient | null,
  locale: 'en' | 'ko',
  now = new Date(),
  extraColumns = '',
): Promise<TermOfDayResult> {
  if (!db) return { term: null, total: 0 };
  const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';

  const countRes = await db
    .from('handbook_terms')
    .select('slug', { count: 'exact', head: true })
    .eq('status', 'published');
  if (countRes.error) {
    console.warn('[termOfDay] term count query failed', countRes.error.message);
    return { term: null, total: 0 };
  }

  const total = countRes.count ?? 0;
  const i = termIndex(now, total);
  if (i === null) return { term: null, total };

  const columns = `term, slug, korean_name, definition:${definitionField}${extraColumns ? `, ${extraColumns}` : ''}`;
  const termRes = await db
    .from('handbook_terms')
    .select(columns)
    .eq('status', 'published')
    .order('slug', { ascending: true })
    .range(i, i)
    .maybeSingle();
  if (termRes.error) {
    console.warn('[termOfDay] term query failed', termRes.error.message);
    return { term: null, total: 0 };
  }

  return { term: (termRes.data ?? null) as unknown as TermOfDay | null, total };
}
