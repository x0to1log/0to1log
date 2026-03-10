import { supabase } from './supabase';

/**
 * Batch-fetch multiple site_content keys in a single query.
 * Returns a map of key → localized value (plain text or JSON string).
 */
export async function getSiteContents(
  keys: string[],
  locale: 'en' | 'ko',
): Promise<Record<string, string>> {
  if (!supabase) return {};
  const col = locale === 'ko' ? 'value_ko' : 'value_en';
  const { data } = await supabase
    .from('site_content')
    .select(`key, ${col}`)
    .in('key', keys);
  const map: Record<string, string> = {};
  (data ?? []).forEach((row: any) => {
    map[row.key] = row[col] || '';
  });
  return map;
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
