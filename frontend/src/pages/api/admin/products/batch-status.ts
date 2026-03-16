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

  const { action, filter } = await request.json();

  if (!action || !['publish', 'unpublish'].includes(action)) {
    return new Response(JSON.stringify({ error: 'Invalid action' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!filter || !['all_drafts', 'all_published'].includes(filter)) {
    return new Response(JSON.stringify({ error: 'Invalid filter' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  const isPublished = action === 'publish';
  const filterValue = filter === 'all_drafts' ? false : true;

  const { data, error } = await supabase
    .from('ai_products')
    .update({ is_published: isPublished, updated_at: new Date().toISOString() })
    .eq('is_published', filterValue)
    .select('id');

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ updated: data?.length ?? 0 }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
