import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

function authSupabase(accessToken: string) {
  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );
}

export const GET: APIRoute = async ({ locals, url }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const type = url.searchParams.get('type'); // 'post' | 'term' | null (all)
  const supabase = authSupabase(locals.accessToken);

  let query = supabase
    .from('reading_history')
    .select('id, item_type, item_id, read_at')
    .eq('user_id', locals.user.id)
    .order('read_at', { ascending: false });

  if (type === 'news' || type === 'blog' || type === 'term') {
    query = query.eq('item_type', type);
  }

  const { data, error } = await query;

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json();
  const { item_type, item_id } = body;

  if (!item_type || !item_id || !['news', 'blog', 'term'].includes(item_type)) {
    return new Response(JSON.stringify({ error: 'Invalid item_type or item_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = authSupabase(locals.accessToken);

  // Upsert — ON CONFLICT DO NOTHING via upsert with ignoreDuplicates
  const { error } = await supabase
    .from('reading_history')
    .upsert({
      user_id: locals.user.id,
      item_type,
      item_id,
      read_at: new Date().toISOString(),
    }, { onConflict: 'user_id,item_type,item_id', ignoreDuplicates: true });

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};

export const DELETE: APIRoute = async ({ locals, url }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const id = url.searchParams.get('id');
  if (!id) {
    return new Response(JSON.stringify({ error: 'Missing id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = authSupabase(locals.accessToken);
  const { error } = await supabase
    .from('reading_history')
    .delete()
    .eq('id', id)
    .eq('user_id', locals.user.id);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
