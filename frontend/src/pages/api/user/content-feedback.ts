import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

/* ── validation constants ── */

const VALID_SOURCE_TYPES = ['news', 'handbook', 'blog', 'product'] as const;
const VALID_LOCALES = ['ko', 'en'] as const;
const VALID_REACTIONS = ['positive', 'negative'] as const;
const VALID_REASONS: Record<string, string[]> = {
  news: ['inaccurate', 'hard_to_understand', 'too_shallow', 'other'],
  handbook: ['confusing', 'lacks_examples', 'outdated', 'other'],
  blog: ['not_helpful', 'lacks_depth', 'other'],
  product: ['inaccurate_info', 'not_useful', 'other'],
};
const MAX_MESSAGE_LENGTH = 500;

/* ── helpers ── */

function authSupabase(accessToken: string) {
  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/* ── GET ── */

export const GET: APIRoute = async ({ locals, url }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const source_type = url.searchParams.get('source_type');
  const source_id = url.searchParams.get('source_id');
  const locale = url.searchParams.get('locale');

  if (
    !source_type ||
    !source_id ||
    !locale ||
    !VALID_SOURCE_TYPES.includes(source_type as (typeof VALID_SOURCE_TYPES)[number]) ||
    !VALID_LOCALES.includes(locale as (typeof VALID_LOCALES)[number])
  ) {
    return json({ error: 'Missing or invalid source_type / source_id / locale' }, 400);
  }

  const supabase = authSupabase(locals.accessToken);
  const { data, error } = await supabase
    .from('content_feedback')
    .select('reaction, reason, message')
    .eq('user_id', locals.user.id)
    .eq('source_type', source_type)
    .eq('source_id', source_id)
    .eq('locale', locale)
    .maybeSingle();

  if (error) {
    return json({ error: error.message }, 500);
  }

  return json({
    reaction: data?.reaction ?? null,
    reason: data?.reason ?? null,
    message: data?.message ?? null,
  });
};

/* ── POST ── */

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const body = await request.json();
  const { source_type, source_id, locale, reaction, reason, message } = body;

  // source_type
  if (
    !source_type ||
    !VALID_SOURCE_TYPES.includes(source_type as (typeof VALID_SOURCE_TYPES)[number])
  ) {
    return json({ error: 'Invalid source_type' }, 400);
  }

  // source_id
  if (!source_id) {
    return json({ error: 'Missing source_id' }, 400);
  }

  // locale
  if (!locale || !VALID_LOCALES.includes(locale as (typeof VALID_LOCALES)[number])) {
    return json({ error: 'Invalid locale' }, 400);
  }

  // reaction
  if (!reaction || !VALID_REACTIONS.includes(reaction as (typeof VALID_REACTIONS)[number])) {
    return json({ error: 'Invalid reaction' }, 400);
  }

  // reason validation
  if (reaction === 'positive' && reason) {
    return json({ error: 'Reason must be null for positive reaction' }, 400);
  }
  if (reaction === 'negative') {
    if (reason && !VALID_REASONS[source_type].includes(reason)) {
      return json({ error: 'Invalid reason for source_type' }, 400);
    }
  }

  // message validation
  if (message && typeof message === 'string' && message.length > MAX_MESSAGE_LENGTH) {
    return json({ error: `Message must be ${MAX_MESSAGE_LENGTH} characters or fewer` }, 400);
  }

  const supabase = authSupabase(locals.accessToken);
  const payload: Record<string, unknown> = {
    user_id: locals.user.id,
    source_type,
    source_id,
    locale,
    reaction,
    reason: reason || null,
    message: message || null,
    updated_at: new Date().toISOString(),
  };

  const { data, error } = await supabase
    .from('content_feedback')
    .upsert(payload, { onConflict: 'user_id,source_type,source_id,locale' })
    .select('reaction, reason, message')
    .single();

  if (error) {
    return json({ error: error.message }, 500);
  }

  return json({
    reaction: data.reaction,
    reason: data.reason,
    message: data.message,
  });
};

/* ── DELETE ── */

export const DELETE: APIRoute = async ({ locals, url }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const source_type = url.searchParams.get('source_type');
  const source_id = url.searchParams.get('source_id');
  const locale = url.searchParams.get('locale');

  if (
    !source_type ||
    !source_id ||
    !locale ||
    !VALID_SOURCE_TYPES.includes(source_type as (typeof VALID_SOURCE_TYPES)[number]) ||
    !VALID_LOCALES.includes(locale as (typeof VALID_LOCALES)[number])
  ) {
    return json({ error: 'Missing or invalid source_type / source_id / locale' }, 400);
  }

  const supabase = authSupabase(locals.accessToken);
  const { error } = await supabase
    .from('content_feedback')
    .delete()
    .eq('user_id', locals.user.id)
    .eq('source_type', source_type)
    .eq('source_id', source_id)
    .eq('locale', locale);

  if (error) {
    return json({ error: error.message }, 500);
  }

  return json({ success: true });
};
