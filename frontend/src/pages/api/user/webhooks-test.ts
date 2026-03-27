import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { formatTestPayload } from '../../../lib/webhooks';

export const prerender = false;

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

// POST — send test webhook
export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) return json({ error: 'Unauthorized' }, 401);

  const { id } = await request.json();
  if (!id) return json({ error: 'id is required' }, 400);

  const sb = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${locals.accessToken}` } } },
  );

  const { data: hook, error } = await sb
    .from('user_webhooks')
    .select('id, url, platform, locale')
    .eq('id', id)
    .eq('user_id', locals.user.id)
    .single();

  if (error || !hook) return json({ error: 'Webhook not found' }, 404);

  const payload = formatTestPayload(hook.platform, hook.locale === 'all' ? 'en' : hook.locale);

  try {
    const res = await fetch(hook.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      return json({ success: false, error: `HTTP ${res.status}` });
    }

    await sb.from('user_webhooks').update({
      fail_count: 0,
      last_fired_at: new Date().toISOString(),
    }).eq('id', hook.id);

    return json({ success: true });
  } catch (err: any) {
    return json({ success: false, error: err?.message || 'Request failed' });
  }
};
