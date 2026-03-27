import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

export const POST: APIRoute = async ({ request, locals }) => {
  const accessToken = (locals as any).accessToken;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!(locals as any).isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json();
  const { id, label, url, platform, locale, is_active } = body;

  if (!label || !url || !platform) {
    return new Response(JSON.stringify({ error: 'label, url, and platform are required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  if (!['discord', 'slack', 'custom'].includes(platform)) {
    return new Response(JSON.stringify({ error: 'Invalid platform' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  if (!url.startsWith('https://')) {
    return new Response(JSON.stringify({ error: 'URL must start with https://' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  const now = new Date().toISOString();

  if (id) {
    const { data, error } = await supabase
      .from('webhooks')
      .update({
        label, url, platform, updated_at: now,
        ...(locale ? { locale } : {}),
        ...(typeof is_active === 'boolean' ? { is_active } : {}),
        ...(is_active === true ? { fail_count: 0, last_error: null } : {}),
      })
      .eq('id', id)
      .select()
      .single();

    if (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }
    return new Response(JSON.stringify(data), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }

  const { data, error } = await supabase
    .from('webhooks')
    .insert({ label, url, platform, ...(locale ? { locale } : {}) })
    .select()
    .single();

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 201, headers: { 'Content-Type': 'application/json' },
  });
};
