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
  // Publish gate enforces bilingual completeness: both KO and EN sides
  // must have definition + body (basic or advanced) + hero news context +
  // at least 1 reference. Identity fields (term/slug/categories) are
  // language-independent.
  if (action === 'publish') {
    const { data: term } = await supabase
      .from('handbook_terms')
      .select(`
        term, slug, categories,
        definition_ko, body_basic_ko, body_advanced_ko,
        hero_news_context_ko, references_ko,
        definition_en, body_basic_en, body_advanced_en,
        hero_news_context_en, references_en
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
    if (!Array.isArray(term.categories) || term.categories.length === 0) missing.push('categories');

    // KO side
    if (!term.definition_ko) missing.push('definition_ko');
    if (!term.body_basic_ko && !term.body_advanced_ko) missing.push('body_basic_ko or body_advanced_ko');
    if (!term.hero_news_context_ko) missing.push('hero_news_context_ko');
    if (!Array.isArray(term.references_ko) || term.references_ko.length === 0) missing.push('references_ko');

    // EN side
    if (!term.definition_en) missing.push('definition_en');
    if (!term.body_basic_en && !term.body_advanced_en) missing.push('body_basic_en or body_advanced_en');
    if (!term.hero_news_context_en) missing.push('hero_news_context_en');
    if (!Array.isArray(term.references_en) || term.references_en.length === 0) missing.push('references_en');

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
