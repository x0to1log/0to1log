import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

function anonSupabase() {
  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
  );
}

function authSupabase(accessToken: string) {
  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );
}

// GET ?post_id=X → { liked: bool, count: number }
export const GET: APIRoute = async ({ locals, url }) => {
  const postId = url.searchParams.get('post_id');
  if (!postId) {
    return new Response(JSON.stringify({ error: 'Missing post_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = anonSupabase();

  // Count total likes
  const { count, error } = await supabase
    .from('post_likes')
    .select('id', { count: 'exact', head: true })
    .eq('post_id', postId);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  // Check if current user liked
  let liked = false;
  if (locals.user && locals.accessToken) {
    const authSb = authSupabase(locals.accessToken);
    const { data: existing } = await authSb
      .from('post_likes')
      .select('id')
      .eq('user_id', locals.user.id)
      .eq('post_id', postId)
      .maybeSingle();
    liked = !!existing;
  }

  return new Response(JSON.stringify({ liked, count: count ?? 0 }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};

// POST { post_id } → toggle like
export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json();
  const { post_id } = body;

  if (!post_id) {
    return new Response(JSON.stringify({ error: 'Missing post_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = authSupabase(locals.accessToken);

  // Check if already liked
  const { data: existing } = await supabase
    .from('post_likes')
    .select('id')
    .eq('user_id', locals.user.id)
    .eq('post_id', post_id)
    .maybeSingle();

  if (existing) {
    await supabase.from('post_likes').delete().eq('id', existing.id);
  } else {
    const { error } = await supabase.from('post_likes').insert({
      user_id: locals.user.id,
      post_id,
    });
    if (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  // Return updated count
  const anon = anonSupabase();
  const { count } = await anon
    .from('post_likes')
    .select('id', { count: 'exact', head: true })
    .eq('post_id', post_id);

  return new Response(JSON.stringify({ liked: !existing, count: count ?? 0 }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
