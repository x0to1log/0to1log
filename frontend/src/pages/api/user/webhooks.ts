import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { formatTestPayload } from '../../../lib/webhooks';

export const prerender = false;

const VALID_PLATFORMS = ['discord', 'slack', 'custom'];
const VALID_LOCALES = ['all', 'en', 'ko'];
const MAX_WEBHOOKS = 5;

/** Block SSRF: reject internal IPs, metadata endpoints, non-HTTPS */
function isSafeWebhookUrl(raw: string): boolean {
  if (!raw.startsWith('https://')) return false;
  try {
    const u = new URL(raw);
    const host = u.hostname.toLowerCase();
    // Block localhost variants
    if (host === 'localhost' || host === '127.0.0.1' || host === '::1' || host === '[::1]') return false;
    // Block cloud metadata
    if (host === '169.254.169.254' || host === 'metadata.google.internal') return false;
    // Block private IP ranges (10.x, 172.16-31.x, 192.168.x)
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

function authClient(token: string) {
  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${token}` } } },
  );
}

// GET — list user's webhooks
export const GET: APIRoute = async ({ locals }) => {
  if (!locals.user || !locals.accessToken) return json({ error: 'Unauthorized' }, 401);

  const sb = authClient(locals.accessToken);
  const { data, error } = await sb
    .from('user_webhooks')
    .select('*')
    .eq('user_id', locals.user.id)
    .order('created_at', { ascending: true });

  if (error) return json({ error: 'Database error' }, 500);
  return json(data);
};

// POST — create webhook
export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) return json({ error: 'Unauthorized' }, 401);

  const body = await request.json();
  const { label, url, platform, locale = 'all' } = body;

  if (!label?.trim()) return json({ error: 'Label is required' }, 400);
  if (!url?.trim() || !isSafeWebhookUrl(url.trim())) return json({ error: 'Invalid webhook URL' }, 400);
  if (!VALID_PLATFORMS.includes(platform)) return json({ error: 'Invalid platform' }, 400);
  if (!VALID_LOCALES.includes(locale)) return json({ error: 'Invalid locale' }, 400);

  const sb = authClient(locals.accessToken);

  // Check limit
  const { count } = await sb
    .from('user_webhooks')
    .select('id', { count: 'exact', head: true })
    .eq('user_id', locals.user.id);

  if ((count ?? 0) >= MAX_WEBHOOKS) {
    return json({ error: `Maximum ${MAX_WEBHOOKS} webhooks allowed` }, 400);
  }

  const { data, error } = await sb
    .from('user_webhooks')
    .insert({
      user_id: locals.user.id,
      label: label.trim(),
      url: url.trim(),
      platform,
      locale,
    })
    .select()
    .single();

  if (error) return json({ error: 'Database error' }, 500);
  return json(data, 201);
};

// PUT — update webhook
export const PUT: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) return json({ error: 'Unauthorized' }, 401);

  const body = await request.json();
  const { id, label, url, platform, locale, is_active } = body;

  if (!id) return json({ error: 'id is required' }, 400);
  if (url !== undefined && (!url.trim() || !isSafeWebhookUrl(url.trim()))) {
    return json({ error: 'Invalid webhook URL' }, 400);
  }
  if (platform !== undefined && !VALID_PLATFORMS.includes(platform)) {
    return json({ error: 'Invalid platform' }, 400);
  }
  if (locale !== undefined && !VALID_LOCALES.includes(locale)) {
    return json({ error: 'Invalid locale' }, 400);
  }

  const updates: Record<string, unknown> = {};
  if (label !== undefined) updates.label = label.trim();
  if (url !== undefined) updates.url = url.trim();
  if (platform !== undefined) updates.platform = platform;
  if (locale !== undefined) updates.locale = locale;
  if (is_active !== undefined) {
    updates.is_active = !!is_active;
    if (is_active) updates.fail_count = 0;
  }

  const sb = authClient(locals.accessToken);
  const { data, error } = await sb
    .from('user_webhooks')
    .update(updates)
    .eq('id', id)
    .eq('user_id', locals.user.id)
    .select()
    .single();

  if (error) return json({ error: 'Database error' }, 500);
  return json(data);
};

// DELETE — remove webhook
export const DELETE: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) return json({ error: 'Unauthorized' }, 401);

  const { id } = await request.json();
  if (!id) return json({ error: 'id is required' }, 400);

  const sb = authClient(locals.accessToken);
  const { error } = await sb
    .from('user_webhooks')
    .delete()
    .eq('id', id)
    .eq('user_id', locals.user.id);

  if (error) return json({ error: 'Database error' }, 500);
  return json({ success: true });
};
