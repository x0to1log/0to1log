import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { formatTestPayload } from '../../../lib/webhooks';

export const prerender = false;

/** Block SSRF: reject internal IPs, metadata endpoints, non-HTTPS */
function isSafeWebhookUrl(raw: string): boolean {
  if (!raw.startsWith('https://')) return false;
  try {
    const u = new URL(raw);
    const host = u.hostname.toLowerCase();
    if (host === 'localhost' || host === '127.0.0.1' || host === '::1' || host === '[::1]') return false;
    if (host === '169.254.169.254' || host === 'metadata.google.internal') return false;
    const parts = host.split('.').map(Number);
    if (parts.length === 4 && !parts.some(isNaN)) {
      if (parts[0] === 10) return false;
      if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return false;
      if (parts[0] === 192 && parts[1] === 168) return false;
      if (parts[0] === 0) return false;
    }
    return true;
  } catch {
    return false;
  }
}

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
  if (!isSafeWebhookUrl(hook.url)) return json({ error: 'Invalid webhook URL' }, 400);

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
    return json({ success: false, error: 'Request failed' });
  }
};
