import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ statuses: {} }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const { items } = await request.json();
  if (!Array.isArray(items) || items.length === 0) {
    return new Response(JSON.stringify({ statuses: {} }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${locals.accessToken}` } } },
  );

  const itemIds = items.map((i: any) => i.item_id);
  const { data } = await supabase
    .from('user_bookmarks')
    .select('item_id')
    .eq('user_id', locals.user.id)
    .in('item_id', itemIds);

  const statuses: Record<string, boolean> = {};
  for (const item of items) {
    statuses[item.item_id] = (data || []).some((d: any) => d.item_id === item.item_id);
  }

  return new Response(JSON.stringify({ statuses }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
