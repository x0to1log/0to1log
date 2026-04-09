import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { fireWebhooks } from '../../../lib/webhooks';

export const prerender = false;

/**
 * Internal endpoint called by backend pipeline after auto-publish.
 * Fires webhooks + warms CDN cache for the published post.
 * Auth: x-cron-secret header (same as pipeline triggers).
 */
export const POST: APIRoute = async ({ request }) => {
  const cronSecret = import.meta.env.CRON_SECRET;
  const secret = request.headers.get('x-cron-secret');
  if (!cronSecret || secret !== cronSecret) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const { slug } = await request.json();
  if (!slug) {
    return new Response(JSON.stringify({ error: 'slug required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.SUPABASE_SERVICE_KEY,
  );

  const { data: post } = await supabase
    .from('news_posts')
    .select('title, slug, locale, excerpt, post_type, published_at')
    .eq('slug', slug)
    .single();

  if (!post) {
    return new Response(JSON.stringify({ error: 'Post not found' }), {
      status: 404, headers: { 'Content-Type': 'application/json' },
    });
  }

  // Warm CDN cache
  const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';
  fetch(`${siteUrl}/${post.locale}/news/${post.slug}/`).catch(() => {});

  // Fire webhooks
  await fireWebhooks(supabase, post);

  return new Response(JSON.stringify({ ok: true, slug }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
