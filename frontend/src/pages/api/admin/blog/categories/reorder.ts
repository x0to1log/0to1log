import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

export const POST: APIRoute = async ({ request, locals }) => {
  const accessToken = locals.accessToken;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  try {
    const { items } = await request.json() as {
      items: Array<{ id: string; sort_order: number; group_slug: string }>;
    };

    if (!Array.isArray(items) || items.length === 0) {
      return new Response(JSON.stringify({ error: 'Missing items' }), {
        status: 400, headers: { 'Content-Type': 'application/json' },
      });
    }

    for (const item of items) {
      const { error } = await supabase
        .from('blog_categories')
        .update({ sort_order: item.sort_order, group_slug: item.group_slug })
        .eq('id', item.id);

      if (error) {
        console.error('blog_categories reorder error:', error.message, 'id:', item.id);
        return new Response(JSON.stringify({ error: 'Failed to reorder categories' }), {
          status: 500, headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('categories/reorder unexpected error:', err);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};
