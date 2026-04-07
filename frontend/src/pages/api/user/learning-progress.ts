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

export const GET: APIRoute = async ({ locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = authSupabase(locals.accessToken);

  const { data, error } = await supabase
    .from('learning_progress')
    .select('id, term_id, status, read_at, learned_at')
    .eq('user_id', locals.user.id);

  if (error) {
    return new Response(JSON.stringify({ error: 'Database error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data ?? []), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};

// Auto-record: term visited → status='read'
export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json();
  const { term_id } = body;

  if (!term_id) {
    return new Response(JSON.stringify({ error: 'Missing term_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = authSupabase(locals.accessToken);

  const { error } = await supabase
    .from('learning_progress')
    .upsert({
      user_id: locals.user.id,
      term_id,
      status: 'read',
      read_at: new Date().toISOString(),
    }, { onConflict: 'user_id,term_id', ignoreDuplicates: true });

  if (error) {
    return new Response(JSON.stringify({ error: 'Database error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};

// Toggle learned status
export const PUT: APIRoute = async ({ request, locals, url }) => {
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

  const body = await request.json();
  const { status } = body;

  if (!status || !['read', 'learned'].includes(status)) {
    return new Response(JSON.stringify({ error: 'Invalid status' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = authSupabase(locals.accessToken);

  const updateData: Record<string, any> = { status };
  if (status === 'learned') {
    updateData.learned_at = new Date().toISOString();
  } else {
    updateData.learned_at = null;
  }

  const { data, error } = await supabase
    .from('learning_progress')
    .update(updateData)
    .eq('id', id)
    .eq('user_id', locals.user.id)
    .select()
    .single();

  if (error) {
    return new Response(JSON.stringify({ error: 'Database error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
