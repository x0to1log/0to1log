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

  const { id, permanent } = await request.json();

  if (!id) {
    return new Response(JSON.stringify({ error: 'id is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  if (permanent) {
    const { error } = await supabase
      .from('ai_products')
      .delete()
      .eq('id', id)
      .eq('archived', true);
    if (error) {
      return new Response(JSON.stringify({ error: 'Failed to permanently delete' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }
  } else {
    const { error } = await supabase
      .from('ai_products')
      .update({ archived: true })
      .eq('id', id);
    if (error) {
      return new Response(JSON.stringify({ error: 'Failed to archive product' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  return new Response(JSON.stringify({ success: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
