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

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const body = await request.json();
  const { post_id, persona, selected, is_correct } = body;

  if (!post_id || !persona || !selected || typeof is_correct !== 'boolean') {
    return json({ error: 'Missing required fields' }, 400);
  }
  if (!['expert', 'learner'].includes(persona)) {
    return json({ error: 'Invalid persona' }, 400);
  }

  const supabase = authSupabase(locals.accessToken);

  const { data, error } = await supabase
    .from('quiz_responses')
    .upsert({
      user_id: locals.user.id,
      post_id,
      persona,
      selected,
      is_correct,
    }, { onConflict: 'user_id,post_id,persona' })
    .select('id, is_correct')
    .single();

  if (error) {
    return json({ error: 'Database error' }, 500);
  }

  return json(data);
};
