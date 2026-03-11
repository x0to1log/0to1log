import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

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

export const GET: APIRoute = async ({ locals, url }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const term_id = url.searchParams.get('term_id');
  const locale = url.searchParams.get('locale');

  if (!term_id || !locale || !['en', 'ko'].includes(locale)) {
    return json({ error: 'Missing or invalid term_id / locale' }, 400);
  }

  const supabase = authSupabase(locals.accessToken);
  const { data, error } = await supabase
    .from('term_feedback')
    .select('reaction')
    .eq('user_id', locals.user.id)
    .eq('term_id', term_id)
    .eq('locale', locale)
    .maybeSingle();

  if (error) {
    return json({ error: error.message }, 500);
  }

  return json({ reaction: data?.reaction ?? null });
};

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const body = await request.json();
  const { term_id, locale, reaction } = body;

  if (!term_id || !locale || !['en', 'ko'].includes(locale)) {
    return json({ error: 'Missing or invalid term_id / locale' }, 400);
  }

  if (!reaction || !['helpful', 'confusing'].includes(reaction)) {
    return json({ error: 'Invalid reaction' }, 400);
  }

  const supabase = authSupabase(locals.accessToken);
  const payload = {
    user_id: locals.user.id,
    term_id,
    locale,
    reaction,
    updated_at: new Date().toISOString(),
  };

  const { data, error } = await supabase
    .from('term_feedback')
    .upsert(payload, { onConflict: 'user_id,term_id,locale' })
    .select('reaction')
    .single();

  if (error) {
    return json({ error: error.message }, 500);
  }

  return json({ reaction: data.reaction });
};
