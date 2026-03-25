/**
 * Dynamic SSR sitemap — always reflects the latest published content.
 * Replaces @astrojs/sitemap build-time generation.
 *
 * Cache: CDN caches for 1 hour, stale-while-revalidate for 6 hours.
 */
import type { APIRoute } from 'astro';
import { supabase } from '../lib/supabase';

export const prerender = false;

const SITE = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';
const LOCALES = ['en', 'ko'];

// Static pages that should always be in the sitemap
const STATIC_PATHS = [
  '', // home
  'news/',
  'blog/',
  'handbook/',
  'products/',
  'about/',
  'privacy/',
  'terms/',
];

function url(path: string, lastmod?: string): string {
  const loc = `${SITE}/${path}`;
  let entry = `  <url>\n    <loc>${loc}</loc>`;
  if (lastmod) entry += `\n    <lastmod>${lastmod}</lastmod>`;
  entry += '\n  </url>';
  return entry;
}

export const GET: APIRoute = async () => {
  const urls: string[] = [];

  // Static pages (both locales)
  for (const locale of LOCALES) {
    for (const path of STATIC_PATHS) {
      urls.push(url(`${locale}/${path}`));
    }
  }

  if (supabase) {
    // news_posts
    const { data: news } = await supabase
      .from('news_posts')
      .select('slug, locale, published_at')
      .eq('status', 'published');

    for (const p of news ?? []) {
      const lastmod = p.published_at ? p.published_at.split('T')[0] : undefined;
      urls.push(url(`${p.locale}/news/${p.slug}/`, lastmod));
    }

    // handbook_terms (no locale column)
    const { data: terms } = await supabase
      .from('handbook_terms')
      .select('slug, published_at')
      .eq('status', 'published');

    for (const t of terms ?? []) {
      const lastmod = t.published_at ? t.published_at.split('T')[0] : undefined;
      for (const locale of LOCALES) {
        urls.push(url(`${locale}/handbook/${t.slug}/`, lastmod));
      }
    }

    // blog_posts
    const { data: blogs } = await supabase
      .from('blog_posts')
      .select('slug, locale, published_at')
      .eq('status', 'published');

    for (const b of blogs ?? []) {
      const lastmod = b.published_at ? b.published_at.split('T')[0] : undefined;
      urls.push(url(`${b.locale}/blog/${b.slug}/`, lastmod));
    }

    // ai_products (no locale column)
    const { data: products } = await supabase
      .from('ai_products')
      .select('slug, updated_at')
      .eq('is_published', true);

    for (const p of products ?? []) {
      const lastmod = p.updated_at ? p.updated_at.split('T')[0] : undefined;
      for (const locale of LOCALES) {
        urls.push(url(`${locale}/products/${p.slug}/`, lastmod));
      }
    }
  }

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urls,
    '</urlset>',
  ].join('\n');

  return new Response(xml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=21600',
    },
  });
};
