import type { SupabaseClient } from '@supabase/supabase-js';

/** Minimal row used to auto-link handbook terms inside rendered markdown. */
export interface PublicTermIndexEntry {
  term: string;
  slug: string;
  korean_name: string | null;
}

/** Popup data embedded in detail pages for terms the page actually links to. */
export interface TermPopupEntry {
  term: string;
  korean_name: string;
  term_full: string;
  categories: string[];
  summary: string;
  definition: string;
  basic_plain: string;
}

const CACHE_TTL_MS = 5 * 60 * 1000;
type CacheEntry = { expiresAt: number; promise: Promise<PublicTermIndexEntry[]> };
// Shared by detail loaders in a warm server instance, never across DB clients.
const caches = new WeakMap<SupabaseClient, Map<string, CacheEntry>>();

// The inline popup (handbook-popup.ts) reads `.handbook-term[data-slug]`
// spans and `/handbook/<slug>` links, and navigates to the term page when a
// slug has no embedded data.
const TERM_SLUG_PATTERNS = [
  /data-slug="([^"]+)"/g,
  /\/handbook\/([^/"?#\s]+)/g,
];

/** Slugs of the handbook terms the rendered HTML links to. */
export function collectReferencedSlugs(htmlParts: Array<string | null | undefined>): string[] {
  const referenced = new Set<string>();
  for (const html of htmlParts) {
    if (!html) continue;
    for (const pattern of TERM_SLUG_PATTERNS) {
      // Array.from: iterator for-of breaks when tests transpile to ES5.
      for (const match of Array.from(html.matchAll(pattern))) {
        // Skip category listing links (/handbook/category/...).
        if (match[1] !== 'category') referenced.add(match[1]);
      }
    }
  }
  return Array.from(referenced);
}

function popupExcerpt(markdown: string | null): string | null {
  if (!markdown) return null;
  const stripped = markdown.trim().replace(/^##\s+[^\n]*\n+/, '');
  const section = stripped.split(/\r?\n##\s/)[0].trim();
  return section.length > 1200 ? `${section.slice(0, 1200).trimEnd()}…` : section || null;
}

/**
 * Term names for linkification only (~9 KB for every published term).
 * It used to carry summaries, definitions and full basic bodies (~700 KB per
 * call); fetched on every detail-page render, that exhausted the Supabase
 * free egress quota in October 2026. Popup data now comes from fetchTermPopups.
 */
export async function fetchPublicTermIndex(
  db: SupabaseClient,
  locale: 'en' | 'ko',
  limit = 200,
): Promise<PublicTermIndexEntry[]> {
  limit = Math.max(1, Math.min(200, Math.floor(limit) || 200));
  let cache = caches.get(db);
  if (!cache) { cache = new Map(); caches.set(db, cache); }
  // The index has no localized columns today; locale stays in the key so the
  // signature and cache shape survive adding them back.
  const key = `${locale}:${limit}`;
  let entry = cache.get(key);
  if (!entry || entry.expiresAt <= Date.now()) {
    if (cache.size >= 10) cache.delete(cache.keys().next().value!);
    const next: CacheEntry = { expiresAt: Infinity, promise: Promise.resolve([]) };
    next.promise = loadPublicTermIndex(db, limit).then((rows) => {
      next.expiresAt = Date.now() + CACHE_TTL_MS;
      return rows;
    }).catch((error) => {
      if (cache.get(key) === next) cache.delete(key);
      console.error('[public-term-index] Supabase error:', error.message);
      return [];
    });
    cache.set(key, next);
    entry = next;
  }
  // Callers may filter or alter their own copy without poisoning the cache.
  return structuredClone(await entry.promise);
}

async function loadPublicTermIndex(db: SupabaseClient, limit: number): Promise<PublicTermIndexEntry[]> {
  const { data, error } = await db
    .from('handbook_terms')
    .select('term, slug, korean_name')
    .eq('status', 'published')
    .order('slug', { ascending: true })
    .limit(limit);

  if (error) throw error;

  return ((data ?? []) as unknown as PublicTermIndexEntry[]).map((entry) => ({
    term: entry.term,
    slug: entry.slug,
    korean_name: entry.korean_name ?? null,
  }));
}

/**
 * Popup data for the terms referenced in the rendered HTML (usually under
 * ten), keyed by slug. Terms without a summary fall back to an excerpt of
 * their basic body, fetched only for those slugs. Never throws.
 */
export async function fetchTermPopups(
  db: SupabaseClient,
  locale: 'en' | 'ko',
  htmlParts: Array<string | null | undefined>,
  excludeSlug?: string,
): Promise<Record<string, TermPopupEntry>> {
  const slugs = collectReferencedSlugs(htmlParts).filter((slug) => slug !== excludeSlug);
  if (slugs.length === 0) return {};

  const summaryField = locale === 'ko' ? 'summary_ko' : 'summary_en';
  const definitionField = locale === 'ko' ? 'definition_ko' : 'definition_en';
  const basicField = locale === 'ko' ? 'body_basic_ko' : 'body_basic_en';

  try {
    const { data, error } = await db
      .from('handbook_terms')
      .select(`term, slug, korean_name, term_full, categories, summary:${summaryField}, definition:${definitionField}`)
      .eq('status', 'published')
      .in('slug', slugs);
    if (error) throw error;

    const rows = (data ?? []) as unknown as Array<{
      term: string; slug: string; korean_name: string | null; term_full: string | null;
      categories: string[] | null; summary: string | null; definition: string | null;
    }>;

    const missing = rows.filter((row) => !row.summary?.trim()).map((row) => row.slug);
    const fallback = new Map<string, string | null>();
    if (missing.length) {
      // Legacy entries without summaries still need a learner-friendly fallback.
      const { data: bodies, error: bodyError } = await db.from('handbook_terms')
        .select(`slug, basic_plain:${basicField}`)
        .eq('status', 'published')
        .in('slug', missing);
      if (bodyError) throw bodyError;
      for (const body of (bodies ?? []) as Array<{ slug: string; basic_plain: string | null }>) {
        fallback.set(body.slug, popupExcerpt(body.basic_plain));
      }
    }

    const popups: Record<string, TermPopupEntry> = {};
    for (const row of rows) {
      popups[row.slug] = {
        term: row.term,
        korean_name: row.korean_name || '',
        term_full: row.term_full || '',
        categories: row.categories || [],
        summary: row.summary?.trim() || '',
        definition: row.definition || '',
        basic_plain: fallback.get(row.slug) || '',
      };
    }
    return popups;
  } catch (error) {
    console.error('[term-popups] Supabase error:', (error as Error).message);
    return {};
  }
}
