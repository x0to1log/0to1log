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

  if (!id || !['publish', 'unpublish', 'feature', 'unfeature'].includes(action)) {
    return new Response(JSON.stringify({ error: 'Invalid id or action' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  if (action === 'publish') {
    const { data: product } = await supabase
      .from('ai_products')
      .select('name, slug, url, primary_category')
      .eq('id', id)
      .single();

    if (!product) {
      return new Response(JSON.stringify({ error: 'Product not found' }), {
        status: 404, headers: { 'Content-Type': 'application/json' },
      });
    }

    const missing = [];
    if (!product.name) missing.push('name');
    if (!product.slug) missing.push('slug');
    if (!product.url) missing.push('url');
    if (!product.primary_category) missing.push('primary_category');

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
    update.is_published = true;
  } else if (action === 'unpublish') {
    update.is_published = false;
  } else if (action === 'feature') {
    update.featured = true;
  } else if (action === 'unfeature') {
    update.featured = false;
  }

  const { data, error } = await supabase
    .from('ai_products')
    .update(update)
    .eq('id', id)
    .select('id, is_published, featured')
    .single();

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(data), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
