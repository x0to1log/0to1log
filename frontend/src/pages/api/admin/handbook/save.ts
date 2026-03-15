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
  if (!locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json();
  const {
    id,
    term,
    term_full,
    slug,
    korean_name,
    korean_full,
    categories,
    related_term_slugs,
    is_favourite,
    definition_ko,
    body_basic_ko,
    body_advanced_ko,
    definition_en,
    body_basic_en,
    body_advanced_en,
    source,
  } = body;

  if (!term) {
    return new Response(JSON.stringify({ error: 'term is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const finalSlug = slug || slugify(term);

  const row = {
    term,
    term_full: term_full || null,
    slug: finalSlug,
    korean_name: korean_name || null,
    korean_full: korean_full || null,
    categories: Array.isArray(categories) ? categories : (categories ? [categories] : []),
    related_term_slugs: related_term_slugs || [],
    is_favourite: is_favourite ?? false,
    definition_ko: definition_ko || null,
    body_basic_ko: body_basic_ko || null,
    body_advanced_ko: body_advanced_ko || null,
    definition_en: definition_en || null,
    body_basic_en: body_basic_en || null,
    body_advanced_en: body_advanced_en || null,
    updated_at: new Date().toISOString(),
  };

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  if (id) {
    // Update existing
    const { data, error } = await supabase
      .from('handbook_terms')
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

  // Insert new — include source if provided (manual/pipeline/ai-suggested)
  const insertRow = source ? { ...row, source } : row;
  const { data, error } = await supabase
    .from('handbook_terms')
    .insert(insertRow)
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
