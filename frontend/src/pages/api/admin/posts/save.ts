import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

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

  const body = await request.json();
  const { id, title, slug, category, tags, content_original, content_beginner, content_learner, content_expert, excerpt, post_type, locale, focus_items, og_image_url } = body;

  if (!title?.trim()) {
    return new Response(JSON.stringify({ error: 'title is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const row: Record<string, any> = {
    title,
    slug: slug || slugify(title),
    category: category || null,
    tags: Array.isArray(tags) ? tags : [],
    content_original: content_original ?? null,
    updated_at: new Date().toISOString(),
  };

  if (excerpt !== undefined) row.excerpt = excerpt || null;
  if (post_type !== undefined) row.post_type = post_type || null;
  if (locale !== undefined) row.locale = locale || 'en';
  if (focus_items !== undefined) row.focus_items = Array.isArray(focus_items) ? focus_items : [];
  if (og_image_url !== undefined) row.og_image_url = og_image_url || null;
  if (content_beginner !== undefined) row.content_beginner = content_beginner || null;
  if (content_learner !== undefined) row.content_learner = content_learner || null;
  if (content_expert !== undefined) row.content_expert = content_expert || null;

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  if (id) {
    // Update existing
    const { data, error } = await supabase
      .from('posts')
      .update(row)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify(data), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }

  // Insert new
  row.status = 'draft';
  const { data, error } = await supabase
    .from('posts')
    .insert(row)
    .select()
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
