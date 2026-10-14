import type { APIRoute } from 'astro';
import { invalidatePublicCache } from '../../lib/server/cacheInvalidation';
import { PUBLIC_CACHE_SECTIONS } from '../../lib/server/publicCachePolicy';

export const prerender = false;

const ALLOWED_TAGS = new Set<string>(['public', ...PUBLIC_CACHE_SECTIONS]);

/**
 * Manually invalidate cached public pages by tag.
 * Body: { "tags": ["news"] } — omitted or empty means every public page.
 */
export const POST: APIRoute = async ({ request }) => {
  const authHeader = request.headers.get('authorization');
  const secret = import.meta.env.REVALIDATE_SECRET;

  if (!secret || authHeader !== `Bearer ${secret}`) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  let requested: unknown = [];
  try {
    requested = ((await request.json()) as { tags?: unknown }).tags ?? [];
  } catch { /* empty body → all public pages */ }

  const tags = Array.isArray(requested) && requested.length > 0 ? requested : ['public'];
  if (!tags.every((tag) => typeof tag === 'string' && ALLOWED_TAGS.has(tag))) {
    return new Response(JSON.stringify({ error: 'Unknown tag', allowed: [...ALLOWED_TAGS] }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  await invalidatePublicCache(tags as Parameters<typeof invalidatePublicCache>[0]);
  return new Response(JSON.stringify({ revalidated: true, tags }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
