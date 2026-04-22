import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

// Lightweight polling endpoint for the news editor's 'Save & re-run quality' flow.
// Client polls every 5s until updated_at crosses the trigger threshold.
export const GET: APIRoute = async ({ url, locals }) => {
  const accessToken = locals.accessToken;
  if (!accessToken || !locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }

  const slug = url.searchParams.get('slug');
  if (!slug) {
    return new Response(JSON.stringify({ error: 'Missing slug' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const sb = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );
  const { data, error } = await sb
    .from('news_posts')
    .select('slug,updated_at,quality_score')
    .eq('slug', slug)
    .single();

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 404, headers: { 'Content-Type': 'application/json' },
    });
  }
  return new Response(JSON.stringify(data), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
