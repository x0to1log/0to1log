import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
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
  const { id, title, title_learner, slug, category, tags, content_original, content_learner, content_expert, excerpt, post_type, locale, focus_items, og_image_url, guide_items_partial } = body;

  if (!title?.trim()) {
    return new Response(JSON.stringify({ error: 'title is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const row: Record<string, any> = {
    title,
    slug: slug || slugify(title),
    category: category || null,
    tags: normalizeTags(tags),
    content_original: content_original ?? null,
    updated_at: new Date().toISOString(),
  };

  if (excerpt !== undefined) row.excerpt = excerpt || null;
  // study/career/project categories require post_type to be NULL
  const nonTypedCategories = ['study', 'career', 'project'];
  if (nonTypedCategories.includes(row.category)) {
    row.post_type = null;
  } else if (post_type !== undefined) {
    row.post_type = post_type || null;
  }
  if (locale !== undefined) row.locale = locale || 'en';
  if (focus_items !== undefined) row.focus_items = Array.isArray(focus_items) ? focus_items : [];
  if (og_image_url !== undefined) row.og_image_url = og_image_url || null;
  if (content_learner !== undefined) row.content_learner = content_learner || null;
  if (content_expert !== undefined) row.content_expert = content_expert || null;
  if (title_learner !== undefined) row.title_learner = title_learner || null;

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  // Merge guide_items_partial into existing guide_items (preserves pipeline-set
  // fields like sources_expert, quiz_poll_*, etc. while updating only what admin edited)
  if (guide_items_partial && typeof guide_items_partial === 'object' && id) {
    const { data: existing } = await supabase
      .from('news_posts')
      .select('guide_items')
      .eq('id', id)
      .single();
    const merged: Record<string, any> = { ...(existing?.guide_items || {}) };
    for (const [key, value] of Object.entries(guide_items_partial)) {
      // Empty string clears the field; non-empty sets it
      if (value === '' || value === null) {
        delete merged[key];
      } else {
        merged[key] = value;
      }
    }
    row.guide_items = merged;
  } else if (guide_items_partial && typeof guide_items_partial === 'object') {
    // New post: just use the partial as-is (after stripping empty values)
    const cleaned: Record<string, any> = {};
    for (const [key, value] of Object.entries(guide_items_partial)) {
      if (value !== '' && value !== null) cleaned[key] = value;
    }
    if (Object.keys(cleaned).length > 0) row.guide_items = cleaned;
  }

  if (id) {
    // Update existing
    const { data, error } = await supabase
      .from('news_posts')
      .update(row)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      console.error('news_posts update error:', error.message);
      return new Response(JSON.stringify({ error: 'Failed to save post' }), {
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
    .from('news_posts')
    .insert(row)
    .select()
    .single();

  if (error) {
    console.error('news_posts insert error:', error.message);
    return new Response(JSON.stringify({ error: 'Failed to create post' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 201, headers: { 'Content-Type': 'application/json' },
  });
};
