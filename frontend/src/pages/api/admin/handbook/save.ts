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
  const {
    id,
    term,
    slug,
    korean_name,
    categories,
    difficulty,
    related_term_slugs,
    is_favourite,
    definition_ko,
    plain_explanation_ko,
    technical_description_ko,
    example_analogy_ko,
    body_markdown_ko,
    definition_en,
    plain_explanation_en,
    technical_description_en,
    example_analogy_en,
    body_markdown_en,
  } = body;

  if (!term) {
    return new Response(JSON.stringify({ error: 'term is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const finalSlug = slug || slugify(term);

  const row = {
    term,
    slug: finalSlug,
    korean_name: korean_name || null,
    categories: Array.isArray(categories) ? categories : (categories ? [categories] : []),
    difficulty: difficulty || null,
    related_term_slugs: related_term_slugs || [],
    is_favourite: is_favourite ?? false,
    definition_ko: definition_ko || null,
    plain_explanation_ko: plain_explanation_ko || null,
    technical_description_ko: technical_description_ko || null,
    example_analogy_ko: example_analogy_ko || null,
    body_markdown_ko: body_markdown_ko || null,
    definition_en: definition_en || null,
    plain_explanation_en: plain_explanation_en || null,
    technical_description_en: technical_description_en || null,
    example_analogy_en: example_analogy_en || null,
    body_markdown_en: body_markdown_en || null,
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

  // Insert new
  const { data, error } = await supabase
    .from('handbook_terms')
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
