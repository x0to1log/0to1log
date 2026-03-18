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

  const body = await request.json();
  const { id, label_en, label_ko, description_en, description_ko, icon, sort_order } = body;

  if (!id?.trim() || !label_en?.trim() || !label_ko?.trim()) {
    return new Response(JSON.stringify({ error: 'id, label_en, label_ko are required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const row = {
    id: id.trim(),
    label_en: label_en.trim(),
    label_ko: label_ko.trim(),
    description_en: description_en || null,
    description_ko: description_ko || null,
    icon: icon || null,
    sort_order: sort_order != null ? Number(sort_order) : 0,
  };

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  const { data, error } = await supabase
    .from('ai_product_categories')
    .upsert(row, { onConflict: 'id' })
    .select()
    .single();

  if (error) {
    console.error('category save error:', error.message);
    return new Response(JSON.stringify({ error: 'Failed to save category' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
