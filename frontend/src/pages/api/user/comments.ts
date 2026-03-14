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

export const GET: APIRoute = async ({ url, locals }) => {
  const postId = url.searchParams.get('post_id');
  if (!postId) {
    return new Response(JSON.stringify({ error: 'Missing post_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const contentType = url.searchParams.get('type') || 'news';
  const commentsTable = contentType === 'blog' ? 'blog_comments' : 'news_comments';

  const supabase = anonSupabase();

  const { data, error } = await supabase
    .from(commentsTable)
    .select('id, user_id, body, created_at')
    .eq('post_id', postId)
    .order('created_at', { ascending: true });

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  const userIds = [...new Set((data || []).map((c) => c.user_id))];
  const profileMap: Record<string, { display_name: string; avatar_url: string | null }> = {};

  if (userIds.length > 0) {
    const { data: profiles } = await supabase
      .from('profiles')
      .select('id, display_name, avatar_url')
      .in('id', userIds);

    for (const p of profiles || []) {
      profileMap[p.id] = { display_name: p.display_name || 'Anonymous', avatar_url: p.avatar_url };
    }
  }

  const comments = (data || []).map((c) => ({
    id: c.id,
    body: c.body,
    created_at: c.created_at,
    user_id: c.user_id,
    can_delete: !!locals.user && (locals.isAdmin || c.user_id === locals.user.id),
    user: profileMap[c.user_id] || { display_name: 'Anonymous', avatar_url: null },
  }));

  return new Response(JSON.stringify(comments), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const payload = await request.json();
  const { post_id, body, type: contentType = 'news' } = payload;

  if (!post_id || !body || typeof body !== 'string') {
    return new Response(JSON.stringify({ error: 'Missing post_id or body' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const trimmed = body.trim();
  if (trimmed.length === 0 || trimmed.length > 2000) {
    return new Response(JSON.stringify({ error: 'Body must be 1-2000 characters' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const commentsTable = contentType === 'blog' ? 'blog_comments' : 'news_comments';
  const supabase = authSupabase(locals.accessToken);

  const { data, error } = await supabase
    .from(commentsTable)
    .insert({
      user_id: locals.user.id,
      post_id,
      body: trimmed,
    })
    .select('id, body, created_at')
    .single();

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 201, headers: { 'Content-Type': 'application/json' },
  });
};

export const DELETE: APIRoute = async ({ locals, url }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const id = url.searchParams.get('id');
  if (!id) {
    return new Response(JSON.stringify({ error: 'Missing id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const contentType = url.searchParams.get('type') || 'news';
  const commentsTable = contentType === 'blog' ? 'blog_comments' : 'news_comments';

  const supabase = authSupabase(locals.accessToken);
  let deleteQuery = supabase
    .from(commentsTable)
    .delete()
    .eq('id', id);

  if (!locals.isAdmin) {
    deleteQuery = deleteQuery.eq('user_id', locals.user.id);
  }

  const { data, error } = await deleteQuery.select('id');

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  if (!data || data.length === 0) {
    return new Response(JSON.stringify({ error: 'Comment not found or not authorized' }), {
      status: 404, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
