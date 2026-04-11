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

  if (!id || !['publish', 'unpublish', 'archive', 'approve'].includes(action)) {
    return new Response(JSON.stringify({ error: 'Invalid id or action' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  // For publish, validate required fields.
  // Publish gate mirrors the admin editor's "primary" fields: term/slug
  // identity, KO definition + body, categories, plus the hero_news_context
  // and references footer which are level-independent first-class content.
  // EN fields (definition_en / body_basic_en / body_advanced_en / hero_*_en /
  // references_en) are intentionally NOT required — a term may publish
  // bilingually-incomplete if only the KO side is ready.
  if (action === 'publish') {
    const { data: term } = await supabase
      .from('handbook_terms')
      .select(`
        term, slug, definition_ko, categories,
        body_basic_ko, body_advanced_ko,
        hero_news_context_ko, references_ko
      `)
      .eq('id', id)
      .single();

    if (!term) {
      return new Response(JSON.stringify({ error: 'Term not found' }), {
        status: 404, headers: { 'Content-Type': 'application/json' },
      });
    }

    const missing: string[] = [];
    if (!term.term) missing.push('term');
    if (!term.slug) missing.push('slug');
    if (!term.definition_ko) missing.push('definition_ko');
    if (!Array.isArray(term.categories) || term.categories.length === 0) missing.push('categories');
    if (!term.body_basic_ko && !term.body_advanced_ko) missing.push('body_basic_ko or body_advanced_ko');
    if (!term.hero_news_context_ko) missing.push('hero_news_context_ko');
    if (!Array.isArray(term.references_ko) || term.references_ko.length === 0) missing.push('references_ko');

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
    update.published_at = new Date().toISOString();
  } else if (action === 'unpublish') {
    update.status = 'draft';
  } else if (action === 'archive') {
    update.status = 'archived';
  } else if (action === 'approve') {
    update.status = 'draft';
  }

  const { data, error } = await supabase
    .from('handbook_terms')
    .update(update)
    .eq('id', id)
    .select('id, status')
    .single();

  if (error) {
    console.error('handbook_terms status error:', error.message);
    return new Response(JSON.stringify({ error: 'Failed to update term status' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  // Warm CDN cache for published terms (fire-and-forget, both locales)
  if (action === 'publish') {
    const { data: termMeta } = await supabase
      .from('handbook_terms')
      .select('slug')
      .eq('id', id)
      .single();
    if (termMeta?.slug) {
      const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';
      fetch(`${siteUrl}/ko/handbook/${termMeta.slug}/`).catch(() => {});
      fetch(`${siteUrl}/en/handbook/${termMeta.slug}/`).catch(() => {});
    }
  }

  return new Response(JSON.stringify(data), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
