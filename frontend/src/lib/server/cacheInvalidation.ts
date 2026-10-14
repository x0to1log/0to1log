import { invalidateByTag } from '@vercel/functions';
import type { PublicCacheSection } from './publicCachePolicy';

type InvalidationTag = PublicCacheSection | 'public';

const ADMIN_SECTION_PREFIXES: Array<[string, InvalidationTag]> = [
  ['/api/admin/posts/', 'news'],
  ['/api/admin/weekly/', 'news'],
  ['/api/admin/blog/', 'blog'],
  ['/api/admin/handbook/', 'handbook'],
  ['/api/admin/products/', 'products'],
  ['/api/admin/categories/', 'products'],
  ['/api/admin/site-content', 'public'],
];

/**
 * Which public cache tag an admin write affects. AI advisor routes only
 * draft suggestions, so they never invalidate anything.
 */
export function getAdminInvalidationTag(pathname: string, method: string): InvalidationTag | null {
  if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return null;
  if (/\/ai(?:\/|$)/.test(pathname)) return null;
  for (const [prefix, tag] of ADMIN_SECTION_PREFIXES) {
    if (pathname.startsWith(prefix)) return tag;
  }
  return null;
}

// Pages that render another section's content. The home front page shows
// today's lead story and the term of the day (homeFrontPage.ts).
const DEPENDENT_TAGS: Partial<Record<InvalidationTag, InvalidationTag[]>> = {
  news: ['home'],
  handbook: ['home'],
};

export function expandInvalidationTags(tags: InvalidationTag[]): InvalidationTag[] {
  return [...new Set(tags.flatMap((tag) => [tag, ...(DEPENDENT_TAGS[tag] ?? [])]))];
}

/**
 * Mark cached public pages stale (served stale once, refreshed in background).
 * Never throws: outside Vercel there is no cache to purge.
 */
export async function invalidatePublicCache(tags: InvalidationTag[]): Promise<void> {
  if (tags.length === 0) return;
  try {
    await invalidateByTag(expandInvalidationTags(tags));
  } catch (error) {
    console.warn('[cache] invalidateByTag failed', tags, error);
  }
}
