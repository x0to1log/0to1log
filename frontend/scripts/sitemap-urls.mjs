/**
 * Build-time script: fetches published content slugs from Supabase
 * and returns full URLs for the sitemap.
 *
 * Called from astro.config.mjs via top-level await.
 * Uses SUPABASE_URL + SUPABASE_ANON_KEY (same as PUBLIC_ variants).
 */

import { createClient } from '@supabase/supabase-js';
import { config } from 'dotenv';

// Load .env manually — astro.config.mjs runs in Node context, not Vite
config();

const SITE = 'https://0to1log.com';
const LOCALES = ['en', 'ko'];

/** @returns {Promise<string[]>} */
export async function fetchSitemapUrls() {
  const url = process.env.PUBLIC_SUPABASE_URL;
  const key = process.env.PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    console.warn('[sitemap] Supabase env vars missing — skipping dynamic URLs');
    return [];
  }

  const supabase = createClient(url, key);
  const urls = [];

  // news_posts
  const { data: news } = await supabase
    .from('news_posts')
    .select('slug, locale')
    .eq('status', 'published');

  for (const p of news ?? []) {
    urls.push(`${SITE}/${p.locale}/news/${p.slug}/`);
  }

  // handbook_terms (no locale column — same slug for both EN/KO)
  const { data: terms } = await supabase
    .from('handbook_terms')
    .select('slug')
    .eq('status', 'published');

  for (const t of terms ?? []) {
    for (const locale of LOCALES) {
      urls.push(`${SITE}/${locale}/handbook/${t.slug}/`);
    }
  }

  // blog_posts
  const { data: blogs } = await supabase
    .from('blog_posts')
    .select('slug, locale')
    .eq('status', 'published');

  for (const b of blogs ?? []) {
    urls.push(`${SITE}/${b.locale}/blog/${b.slug}/`);
  }

  // ai_products (no locale column — same slug for both EN/KO)
  const { data: products } = await supabase
    .from('ai_products')
    .select('slug')
    .eq('is_published', true);

  for (const p of products ?? []) {
    for (const locale of LOCALES) {
      urls.push(`${SITE}/${locale}/products/${p.slug}/`);
    }
  }

  console.log(`[sitemap] ${urls.length} dynamic URLs added`);
  return urls;
}
