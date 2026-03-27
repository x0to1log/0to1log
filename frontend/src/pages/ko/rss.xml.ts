export const prerender = false;

import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { supabase } from '../../lib/supabase';

export async function GET(context: APIContext) {
  const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';

  let posts: any[] = [];

  if (supabase) {
    const { data } = await supabase
      .from('news_posts')
      .select('title, slug, excerpt, category, published_at')
      .eq('status', 'published')
      .eq('locale', 'ko')
      .order('published_at', { ascending: false })
      .limit(20);

    posts = data ?? [];
  }

  return rss({
    title: '0to1log — AI 뉴스',
    description: 'AI 뉴스를 매일 큐레이션합니다. From Void to Value.',
    site: siteUrl,
    items: posts.map((post) => ({
      title: post.title,
      link: `/ko/news/${post.slug}/`,
      description: post.excerpt || '',
      pubDate: new Date(post.published_at),
      categories: post.category ? [post.category] : [],
    })),
    customData: '<language>ko</language>',
  });
}
