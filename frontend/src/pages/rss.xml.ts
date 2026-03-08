export const prerender = false;

import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { supabase } from '../lib/supabase';

export async function GET(context: APIContext) {
  const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';

  let posts: any[] = [];

  if (supabase) {
    const { data } = await supabase
      .from('posts')
      .select('title, slug, excerpt, category, published_at')
      .eq('status', 'published')
      .eq('locale', 'en')
      .order('published_at', { ascending: false })
      .limit(20);

    posts = data ?? [];
  }

  return rss({
    title: '0to1log — AI News & Insights',
    description: 'AI news curated and contextualized. From Void to Value.',
    site: siteUrl,
    items: posts.map((post) => ({
      title: post.title,
      link: `/en/log/${post.slug}/`,
      description: post.excerpt || '',
      pubDate: new Date(post.published_at),
      categories: post.category ? [post.category] : [],
    })),
  });
}
