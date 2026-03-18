import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

export const POST: APIRoute = async ({ request, locals }) => {
  const accessToken = locals.accessToken;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }

  const { id, action } = await request.json();

  if (!id || !['publish', 'unpublish'].includes(action)) {
    return new Response(JSON.stringify({ error: 'Invalid id or action' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  // For publish, validate required fields
  if (action === 'publish') {
    const { data: post } = await supabase
      .from('news_posts')
      .select('title, slug')
      .eq('id', id)
      .single();

    if (!post) {
      return new Response(JSON.stringify({ error: 'Post not found' }), {
        status: 404, headers: { 'Content-Type': 'application/json' },
      });
    }

    const missing = [];
    if (!post.title) missing.push('title');
    if (!post.slug) missing.push('slug');

    if (missing.length > 0) {
      return new Response(JSON.stringify({
        error: `Cannot publish: missing ${missing.join(', ')}`,
      }), {
        status: 400, headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  const update: Record<string, any> = { updated_at: new Date().toISOString() };

  if (action === 'publish') {
    update.status = 'published';
    // Only set published_at if not already set (pipeline sets it to batch_id date)
    const { data: existing } = await supabase.from('news_posts').select('published_at').eq('id', id).single();
    if (!existing?.published_at) {
      update.published_at = new Date().toISOString();
    }
  } else if (action === 'unpublish') {
    update.status = 'draft';
  }

  const { data, error } = await supabase
    .from('news_posts')
    .update(update)
    .eq('id', id)
    .select('id, status')
    .single();

  if (error) {
    console.error('news_posts status error:', error.message);
    return new Response(JSON.stringify({ error: 'Failed to update post status' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
