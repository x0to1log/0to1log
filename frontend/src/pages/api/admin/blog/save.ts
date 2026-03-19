import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { BLOG_CATEGORIES } from '../../../../lib/categories';
import { normalizeTags } from '../../../../lib/normalizeTags';

export const prerender = false;

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

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

  const body = await request.json();
  const { id, title, slug, category, tags, content, excerpt, locale, focus_items, og_image_url, source } = body;
  const resolvedCategory = category || 'study';

  if (!title?.trim()) {
    return new Response(JSON.stringify({ error: 'title is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  if (!BLOG_CATEGORIES.some((item) => item === resolvedCategory)) {
    return new Response(JSON.stringify({ error: 'invalid category' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const row: Record<string, any> = {
    title,
    slug: slug || slugify(title),
    category: resolvedCategory,
    tags: normalizeTags(tags),
    content: content ?? null,
    updated_at: new Date().toISOString(),
  };

  if (excerpt !== undefined) row.excerpt = excerpt || null;
  if (locale !== undefined) row.locale = locale || 'en';
  if (focus_items !== undefined) row.focus_items = Array.isArray(focus_items) ? focus_items : [];
  if (og_image_url !== undefined) row.og_image_url = og_image_url || null;
  if (source !== undefined) row.source = source;

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  if (id) {
    const { data, error } = await supabase
      .from('blog_posts')
      .update(row)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      console.error('blog_posts update error:', error.message);
      return new Response(JSON.stringify({ error: 'Failed to save blog post' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify(data), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }

  row.status = 'draft';
  const { data, error } = await supabase
    .from('blog_posts')
    .insert(row)
    .select()
    .single();

  if (error) {
    console.error('blog_posts insert error:', error.message);
    return new Response(JSON.stringify({ error: 'Failed to create blog post' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 201, headers: { 'Content-Type': 'application/json' },
  });
};
