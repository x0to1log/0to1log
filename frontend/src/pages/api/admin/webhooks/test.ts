import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { formatTestPayload } from '../../../../lib/webhooks';

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

  const { id } = await request.json();

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

  const { data: hook, error: fetchErr } = await supabase
    .from('webhooks')
    .select('url, platform')
    .eq('id', id)
    .single();

  if (fetchErr || !hook) {
    return new Response(JSON.stringify({ error: 'Webhook not found' }), {
      status: 404, headers: { 'Content-Type': 'application/json' },
    });
  }

  const payload = formatTestPayload(hook.platform);

  try {
    const res = await fetch(hook.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      await supabase.from('webhooks').update({
        fail_count: 0,
        last_fired_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }).eq('id', id);

      return new Response(JSON.stringify({ success: true }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    }

    const errText = await res.text().catch(() => '');
    return new Response(JSON.stringify({
      success: false,
      error: `HTTP ${res.status}: ${errText.slice(0, 200)}`,
    }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    return new Response(JSON.stringify({
      success: false,
      error: err.message || 'Network error',
    }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }
};
