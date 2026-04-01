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
    return new Response(JSON.stringify({ error: 'Missing id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  if (permanent) {
    // Hard delete — only for archived terms
    const { error } = await supabase
      .from('handbook_terms')
      .delete()
      .eq('id', id)
      .eq('status', 'archived');
    if (error) {
      return new Response(JSON.stringify({ error: 'Failed to permanently delete' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }
  } else {
    // Soft delete — set status to archived
    const { error } = await supabase
      .from('handbook_terms')
      .update({ status: 'archived', updated_at: new Date().toISOString() })
      .eq('id', id);
    if (error) {
      return new Response(JSON.stringify({ error: 'Failed to archive term' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
