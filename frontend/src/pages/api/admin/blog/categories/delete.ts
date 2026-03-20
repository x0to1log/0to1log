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

  const supabase = createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );

  try {
    const { id } = await request.json();

    if (!id) {
      return new Response(JSON.stringify({ error: 'Missing id' }), {
        status: 400, headers: { 'Content-Type': 'application/json' },
      });
    }

    // Look up the category to get its slug
    const { data: category, error: fetchError } = await supabase
      .from('blog_categories')
      .select('slug')
      .eq('id', id)
      .single();

    if (fetchError || !category) {
      console.error('blog_categories fetch error:', fetchError?.message);
      return new Response(JSON.stringify({ error: 'Category not found' }), {
        status: 404, headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check if any posts use this category
    const { count, error: countError } = await supabase
      .from('blog_posts')
      .select('id', { count: 'exact', head: true })
      .eq('category', category.slug);

    if (countError) {
      console.error('blog_posts count error:', countError.message);
      return new Response(JSON.stringify({ error: 'Failed to check posts' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    if (count && count > 0) {
      return new Response(
        JSON.stringify({
          error: `이 카테고리에 ${count}개의 글이 있습니다. 글을 다른 카테고리로 이동한 후 삭제해주세요.`,
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    const { error: deleteError } = await supabase
      .from('blog_categories')
      .delete()
      .eq('id', id);

    if (deleteError) {
      console.error('blog_categories delete error:', deleteError.message);
      return new Response(JSON.stringify({ error: 'Failed to delete category' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('categories/delete unexpected error:', err);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};
