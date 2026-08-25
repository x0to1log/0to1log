import { supabase } from './supabase';

export interface SiteContentsResult {
  content: Record<string, string>;
  error: string | null;
}

export async function getSiteContentsResult(
  keys: string[],
  locale: 'en' | 'ko',
): Promise<SiteContentsResult> {
  if (!supabase) return { content: {}, error: 'Database unavailable.' };
  const col = locale === 'ko' ? 'value_ko' : 'value_en';
  const { data, error } = await supabase
    .from('site_content')
    .select(`key, ${col}`)
    .in('key', keys);
  if (error) return { content: {}, error: error.message };

  const content: Record<string, string> = {};
  (data ?? []).forEach((row: any) => {
    content[row.key] = row[col] || '';
  });
  return { content, error: null };
}

/**
 * Batch-fetch multiple site_content keys in a single query.
 * Returns a map of key → localized value (plain text or JSON string).
 */
export async function getSiteContents(
  keys: string[],
  locale: 'en' | 'ko',
): Promise<Record<string, string>> {
  return (await getSiteContentsResult(keys, locale)).content;
}

/** Parse a JSON array string, returning fallback on failure. */
export function parseJsonArray<T>(raw: string, fallback: T[]): T[] {
  if (!raw) return fallback;
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}
