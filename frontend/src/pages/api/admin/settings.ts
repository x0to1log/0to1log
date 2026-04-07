export const prerender = false;

import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const POST: APIRoute = async ({ locals, request }) => {
  const accessToken = locals.accessToken;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
  }

  const body = await request.json().catch(() => null);
  if (!body?.key || body.value === undefined) {
    return new Response(JSON.stringify({ error: 'Missing key or value' }), { status: 400 });
  }

  const sb = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  const { error } = await sb
    .from('admin_settings')
    .upsert({ key: body.key, value: body.value, updated_at: new Date().toISOString() });

  if (error) {
    return new Response(JSON.stringify({ error: 'Database error' }), { status: 500 });
  }

  return new Response(JSON.stringify({ ok: true }), { status: 200 });
};
