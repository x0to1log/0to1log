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

  const { action, ids } = await request.json();

  if (!['publish', 'unpublish'].includes(action) || !Array.isArray(ids) || ids.length === 0) {
    return new Response(JSON.stringify({ error: 'Invalid action or ids' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  if (ids.length > 50) {
    return new Response(JSON.stringify({ error: 'Too many ids (max 50)' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  let success = 0;
  let failed = 0;
  const errors: { id: string; reason: string }[] = [];

  const now = new Date().toISOString();

  if (action === 'publish') {
    const updateData: Record<string, any> = { status: 'published', published_at: now, updated_at: now };
    const { error } = await supabase
      .from('news_posts')
      .update(updateData)
      .in('id', ids);

    if (error) {
      failed = ids.length;
      errors.push({ id: 'bulk', reason: error.message });
    } else {
      success = ids.length;
    }
  } else if (action === 'unpublish') {
    const { error } = await supabase
      .from('news_posts')
      .update({ status: 'draft', updated_at: now })
      .in('id', ids);

    if (error) {
      failed = ids.length;
      errors.push({ id: 'bulk', reason: error.message });
    } else {
      success = ids.length;
    }
  }

  return new Response(JSON.stringify({ success, failed, errors }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
