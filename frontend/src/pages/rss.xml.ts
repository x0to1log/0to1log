export const prerender = false;

import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { supabase } from '../lib/supabase';
import { applyPublicCachePolicy } from '../lib/server/publicCachePolicy';

export async function GET(context: APIContext) {
  const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';

  let posts: any[] = [];

  if (supabase) {
    const { data } = await supabase
      .from('news_posts')
      .select('title, slug, excerpt, category, published_at')
      .eq('status', 'published')
      .eq('locale', 'en')
      .order('published_at', { ascending: false })
      .limit(20);

    posts = data ?? [];
  }

  const response = await rss({
    title: '0to1log — AI News & Insights',
    description: 'AI news curated and contextualized. From Void to Value.',
    site: siteUrl,
    items: posts.map((post) => ({
      title: post.title,
      link: `/en/news/${post.slug}/`,
      description: post.excerpt || '',
      pubDate: new Date(post.published_at),
      categories: post.category ? [post.category] : [],
    })),
  });

  // Outside /en|ko, so middleware doesn't cache it; feed readers poll this often.
  return applyPublicCachePolicy(response, {
    kind: 'list',
    pathname: '/en/rss.xml',
    preview: false,
    hasError: posts.length === 0,
  });
}
