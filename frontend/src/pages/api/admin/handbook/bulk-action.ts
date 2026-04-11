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

  const { action, ids } = await request.json();

  if (!['publish', 'unpublish', 'archive'].includes(action) || !Array.isArray(ids) || ids.length === 0) {
    return new Response(JSON.stringify({ error: 'Invalid action or ids' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  if (ids.length > 50) {
    return new Response(JSON.stringify({ error: 'Too many ids (max 50)' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  let success = 0;
  let failed = 0;
  const errors: { id: string; reason: string }[] = [];

  if (action === 'publish') {
    // Fetch all terms to validate publish gate.
    // Same bilingual-complete policy as the single-item status endpoint:
    // both KO and EN must have definition + body + hero + references.
    const { data: terms } = await supabase
      .from('handbook_terms')
      .select(`
        id, term, slug, categories,
        definition_ko, body_basic_ko, body_advanced_ko,
        hero_news_context_ko, references_ko,
        definition_en, body_basic_en, body_advanced_en,
        hero_news_context_en, references_en
      `)
      .in('id', ids);

    const termsById = new Map((terms ?? []).map((t: any) => [t.id, t]));

    for (const id of ids) {
      const term = termsById.get(id);
      if (!term) {
        failed++;
        errors.push({ id, reason: 'Not found' });
        continue;
      }

      const missing: string[] = [];
      if (!term.term) missing.push('term');
      if (!term.slug) missing.push('slug');
      if (!Array.isArray(term.categories) || term.categories.length === 0) missing.push('categories');

      // KO side
      if (!term.definition_ko) missing.push('definition_ko');
      if (!term.body_basic_ko && !term.body_advanced_ko) missing.push('body_ko');
      if (!term.hero_news_context_ko) missing.push('hero_news_context_ko');
      if (!Array.isArray(term.references_ko) || term.references_ko.length === 0) missing.push('references_ko');

      // EN side
      if (!term.definition_en) missing.push('definition_en');
      if (!term.body_basic_en && !term.body_advanced_en) missing.push('body_en');
      if (!term.hero_news_context_en) missing.push('hero_news_context_en');
      if (!Array.isArray(term.references_en) || term.references_en.length === 0) missing.push('references_en');

      if (missing.length > 0) {
        failed++;
        errors.push({ id, reason: `Missing: ${missing.join(', ')}` });
        continue;
      }

      const { error } = await supabase
        .from('handbook_terms')
        .update({ status: 'published', published_at: new Date().toISOString(), updated_at: new Date().toISOString() })
        .eq('id', id);

      if (error) {
        failed++;
        console.error('handbook bulk publish error:', error.message);
        errors.push({ id, reason: 'Failed to publish' });
      } else {
        success++;
      }
    }
  } else if (action === 'unpublish') {
    const { error } = await supabase
      .from('handbook_terms')
      .update({ status: 'draft', updated_at: new Date().toISOString() })
      .in('id', ids);

    if (error) {
      failed = ids.length;
      console.error('handbook bulk unpublish error:', error.message);
      errors.push({ id: 'bulk', reason: 'Failed to unpublish' });
    } else {
      success = ids.length;
    }
  } else if (action === 'archive') {
    const { error } = await supabase
      .from('handbook_terms')
      .update({ status: 'archived', updated_at: new Date().toISOString() })
      .in('id', ids);

    if (error) {
      failed = ids.length;
      console.error('handbook bulk archive error:', error.message);
      errors.push({ id: 'bulk', reason: 'Failed to archive' });
    } else {
      success = ids.length;
    }
  }

  return new Response(JSON.stringify({ success, failed, errors }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
