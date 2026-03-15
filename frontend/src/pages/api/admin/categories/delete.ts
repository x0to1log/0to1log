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

  const { id } = await request.json();

  if (!id) {
    return new Response(JSON.stringify({ error: 'id is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  // Reject if any product uses this as primary category
  const { count } = await supabase
    .from('ai_products')
    .select('id', { count: 'exact', head: true })
    .eq('primary_category', id);

  if (count && count > 0) {
    return new Response(JSON.stringify({
      error: `Cannot delete: ${count} product(s) use this as primary category`,
    }), {
      status: 409, headers: { 'Content-Type': 'application/json' },
    });
  }

  const { error } = await supabase
    .from('ai_product_categories')
    .delete()
    .eq('id', id);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ success: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
