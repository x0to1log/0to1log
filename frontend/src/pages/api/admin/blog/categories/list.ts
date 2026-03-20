import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

export const GET: APIRoute = async ({ locals }) => {
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

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  try {
    const [categoriesResult, groupsResult] = await Promise.all([
      supabase
        .from('blog_categories')
        .select('*')
        .order('group_slug', { ascending: true })
        .order('sort_order', { ascending: true }),
      supabase
        .from('category_groups')
        .select('*')
        .order('sort_order', { ascending: true }),
    ]);

    if (categoriesResult.error) {
      console.error('blog_categories select error:', categoriesResult.error.message);
      return new Response(JSON.stringify({ error: 'Failed to fetch categories' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }
    if (groupsResult.error) {
      console.error('category_groups select error:', groupsResult.error.message);
      return new Response(JSON.stringify({ error: 'Failed to fetch groups' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    const categories = categoriesResult.data ?? [];
    const groups = groupsResult.data ?? [];

    // Count posts per category
    const postCountResults = await Promise.all(
      categories.map((cat) =>
        supabase
          .from('blog_posts')
          .select('id', { count: 'exact', head: true })
          .eq('category', cat.slug),
      ),
    );

    const categoriesWithCount = categories.map((cat, i) => ({
      ...cat,
      post_count: postCountResults[i].count ?? 0,
    }));

    return new Response(JSON.stringify({ categories: categoriesWithCount, groups }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('categories/list unexpected error:', err);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};
