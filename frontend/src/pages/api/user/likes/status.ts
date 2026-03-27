import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { supabase as anonSupabase } from '../../../../lib/supabase';

export const prerender = false;

export const GET: APIRoute = async ({ url, locals }) => {
  const postId = url.searchParams.get('post_id');
  const type = url.searchParams.get('type') || 'news';
  if (!postId) {
    return new Response(JSON.stringify({ error: 'Missing post_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const likesTable = type === 'blog' ? 'blog_likes' : 'news_likes';

  const { count } = await anonSupabase!
    .from(likesTable)
    .select('id', { count: 'exact', head: true })
    .eq('post_id', postId);

  let liked = false;
  if (locals.user && locals.accessToken) {
    const supabase = createClient(
      import.meta.env.PUBLIC_SUPABASE_URL,
      import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
      { global: { headers: { Authorization: `Bearer ${locals.accessToken}` } } },
    );
    const { data } = await supabase
      .from(likesTable)
      .select('id')
      .eq('user_id', locals.user.id)
      .eq('post_id', postId)
      .maybeSingle();
    liked = !!data;
  }

  return new Response(JSON.stringify({ liked, count: count ?? 0 }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
