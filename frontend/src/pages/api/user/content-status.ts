import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

const MAX_ITEMS = 200;
const ITEM_TYPES = new Set(['news', 'blog', 'term']);
const RESPONSE_HEADERS = {
  'Content-Type': 'application/json',
  'Cache-Control': 'private, no-store',
};

interface ContentStatusItem {
  item_type: string;
  item_id: string;
}

function itemKey(item: ContentStatusItem): string {
  return `${item.item_type}:${item.item_id}`;
}

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: RESPONSE_HEADERS,
    });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON body' }), {
      status: 400,
      headers: RESPONSE_HEADERS,
    });
  }

  const rawItems = (body as { items?: unknown })?.items;
  if (!Array.isArray(rawItems) || rawItems.length > MAX_ITEMS) {
    return new Response(JSON.stringify({ error: `items must contain at most ${MAX_ITEMS} entries` }), {
      status: 400,
      headers: RESPONSE_HEADERS,
    });
  }

  const uniqueItems = new Map<string, ContentStatusItem>();
  for (const rawItem of rawItems) {
    const item = rawItem as Partial<ContentStatusItem>;
    if (
      typeof item.item_id !== 'string'
      || item.item_id.length === 0
      || typeof item.item_type !== 'string'
      || !ITEM_TYPES.has(item.item_type)
    ) {
      return new Response(JSON.stringify({ error: 'Invalid content status item' }), {
        status: 400,
        headers: RESPONSE_HEADERS,
      });
    }
    uniqueItems.set(itemKey(item as ContentStatusItem), item as ContentStatusItem);
  }

  const items = [...uniqueItems.values()];
  if (items.length === 0) {
    return new Response(JSON.stringify({ bookmarks: {}, reads: {} }), {
      status: 200,
      headers: RESPONSE_HEADERS,
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${locals.accessToken}` } } },
  );
  const itemIds = [...new Set(items.map((item) => item.item_id))];
  const itemTypes = [...new Set(items.map((item) => item.item_type))];

  const [bookmarkResult, readResult] = await Promise.all([
    supabase
      .from('user_bookmarks')
      .select('item_type, item_id')
      .eq('user_id', locals.user.id)
      .in('item_type', itemTypes)
      .in('item_id', itemIds),
    supabase
      .from('reading_history')
      .select('item_type, item_id')
      .eq('user_id', locals.user.id)
      .in('item_type', itemTypes)
      .in('item_id', itemIds),
  ]);

  if (bookmarkResult.error || readResult.error) {
    const message = bookmarkResult.error?.message || readResult.error?.message || 'Content status lookup failed';
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: RESPONSE_HEADERS,
    });
  }

  const requestedKeys = new Set(items.map(itemKey));
  const bookmarks: Record<string, boolean> = {};
  const reads: Record<string, boolean> = {};
  for (const item of bookmarkResult.data ?? []) {
    const key = itemKey(item);
    if (requestedKeys.has(key)) bookmarks[key] = true;
  }
  for (const item of readResult.data ?? []) {
    const key = itemKey(item);
    if (requestedKeys.has(key)) reads[key] = true;
  }

  return new Response(JSON.stringify({ bookmarks, reads }), {
    status: 200,
    headers: RESPONSE_HEADERS,
  });
};
