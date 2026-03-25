export const prerender = false;

import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const POST: APIRoute = async ({ request, locals }) => {
  const accessToken = locals.accessToken;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
  }
  if (!locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), { status: 403 });
  }

  const { action, ids } = await request.json();
  if (!action || !Array.isArray(ids) || ids.length === 0) {
    return new Response(JSON.stringify({ error: 'Invalid action or ids' }), { status: 400 });
  }

  const sb = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  let success = 0;
  let failed = 0;

  if (action === 'archive') {
    const { error } = await sb.from('content_feedback').update({ archived: true }).in('id', ids);
    if (error) { failed = ids.length; } else { success = ids.length; }
  } else if (action === 'restore') {
    const { error } = await sb.from('content_feedback').update({ archived: false }).in('id', ids);
    if (error) { failed = ids.length; } else { success = ids.length; }
  } else if (action === 'delete') {
    const { error } = await sb.from('content_feedback').delete().in('id', ids);
    if (error) { failed = ids.length; } else { success = ids.length; }
  } else {
    return new Response(JSON.stringify({ error: 'Unknown action' }), { status: 400 });
  }

  return new Response(JSON.stringify({ ok: true, action, success, failed }), { status: 200 });
};
