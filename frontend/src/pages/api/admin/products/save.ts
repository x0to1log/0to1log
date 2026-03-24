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
  const {
    id, name, name_ko, url, slug,
    primary_category, secondary_categories,
    tagline, tagline_ko, description, description_ko,
    logo_url, thumbnail_url, demo_media,
    pricing, pricing_note,
    platform, tags,
    korean_support, released_at,
    featured, featured_order, sort_order,
    features, features_ko, use_cases, use_cases_ko,
    getting_started, getting_started_ko, pricing_detail, pricing_detail_ko,
    scenarios, scenarios_ko, pros_cons, pros_cons_ko,
    difficulty, editor_note, editor_note_ko,
    official_resources, verified_at, korean_quality_note,
    search_corpus,
  } = body;

  if (!name?.trim()) {
    return new Response(JSON.stringify({ error: 'name is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const row: Record<string, any> = {
    name: name.trim(),
    slug: slug?.trim() || slugify(name),
    updated_at: new Date().toISOString(),
  };

  if (name_ko !== undefined) row.name_ko = name_ko || null;
  if (url !== undefined) row.url = url || null;
  if (primary_category !== undefined) row.primary_category = primary_category || null;
  if (secondary_categories !== undefined) row.secondary_categories = Array.isArray(secondary_categories) ? secondary_categories : [];
  if (tagline !== undefined) row.tagline = tagline || null;
  if (tagline_ko !== undefined) row.tagline_ko = tagline_ko || null;
  if (description !== undefined) row.description = description || null;
  if (description_ko !== undefined) row.description_ko = description_ko || null;
  if (logo_url !== undefined) row.logo_url = logo_url || null;
  if (thumbnail_url !== undefined) row.thumbnail_url = thumbnail_url || null;
  if (pricing !== undefined) row.pricing = pricing || null;
  if (pricing_note !== undefined) row.pricing_note = pricing_note || null;
  if (platform !== undefined) row.platform = Array.isArray(platform) ? platform : [];
  if (tags !== undefined) row.tags = normalizeTags(tags);
  if (korean_support !== undefined) row.korean_support = Boolean(korean_support);
  if (released_at !== undefined) row.released_at = released_at || null;
  if (featured !== undefined) row.featured = Boolean(featured);
  if (featured_order !== undefined) row.featured_order = featured_order != null ? Number(featured_order) : null;
  if (sort_order !== undefined) row.sort_order = sort_order != null ? Number(sort_order) : 0;
  if (demo_media !== undefined) row.demo_media = Array.isArray(demo_media) ? demo_media : [];
  if (features !== undefined) row.features = Array.isArray(features) ? features : [];
  if (features_ko !== undefined) row.features_ko = Array.isArray(features_ko) ? features_ko : [];
  if (use_cases !== undefined) row.use_cases = Array.isArray(use_cases) ? use_cases : [];
  if (use_cases_ko !== undefined) row.use_cases_ko = Array.isArray(use_cases_ko) ? use_cases_ko : [];
  if (getting_started !== undefined) row.getting_started = Array.isArray(getting_started) ? getting_started : [];
  if (getting_started_ko !== undefined) row.getting_started_ko = Array.isArray(getting_started_ko) ? getting_started_ko : [];
  if (pricing_detail !== undefined) row.pricing_detail = pricing_detail || null;
  if (pricing_detail_ko !== undefined) row.pricing_detail_ko = pricing_detail_ko || null;
  if (scenarios !== undefined) row.scenarios = Array.isArray(scenarios) ? scenarios : [];
  if (scenarios_ko !== undefined) row.scenarios_ko = Array.isArray(scenarios_ko) ? scenarios_ko : [];
  if (pros_cons !== undefined) row.pros_cons = pros_cons || null;
  if (pros_cons_ko !== undefined) row.pros_cons_ko = pros_cons_ko || null;
  if (difficulty !== undefined) row.difficulty = ['beginner', 'intermediate', 'advanced'].includes(difficulty) ? difficulty : null;
  if (editor_note !== undefined) row.editor_note = editor_note || null;
  if (editor_note_ko !== undefined) row.editor_note_ko = editor_note_ko || null;
  if (official_resources !== undefined) row.official_resources = Array.isArray(official_resources) ? official_resources : [];
  if (verified_at !== undefined) row.verified_at = verified_at || null;
  if (korean_quality_note !== undefined) row.korean_quality_note = korean_quality_note || null;
  if (search_corpus !== undefined) row.search_corpus = search_corpus || null;

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  if (id) {
    const { data, error } = await supabase
      .from('ai_products')
      .update(row)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      console.error('ai_products update error:', error.message);
      return new Response(JSON.stringify({ error: 'Failed to save product' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify(data), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }

  row.is_published = false;
  const { data, error } = await supabase
    .from('ai_products')
    .insert(row)
    .select()
    .single();

  if (error) {
    console.error('ai_products insert error:', error.message);
    return new Response(JSON.stringify({ error: 'Failed to create product' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 201, headers: { 'Content-Type': 'application/json' },
  });
};
