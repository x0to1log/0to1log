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
    const { slug } = await request.json();

    if (!slug) {
      return new Response(JSON.stringify({ error: 'Missing slug' }), {
        status: 400, headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check if any categories belong to this group
    const { count, error: countError } = await supabase
      .from('blog_categories')
      .select('id', { count: 'exact', head: true })
      .eq('group_slug', slug);

    if (countError) {
      console.error('blog_categories count error:', countError.message);
      return new Response(JSON.stringify({ error: 'Failed to check categories' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    if (count && count > 0) {
      return new Response(
        JSON.stringify({
          error: `이 그룹에 ${count}개의 카테고리가 있습니다. 카테고리를 다른 그룹으로 이동한 후 삭제해주세요.`,
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      );
    }

    const { error: deleteError } = await supabase
      .from('category_groups')
      .delete()
      .eq('slug', slug);

    if (deleteError) {
      console.error('category_groups delete error:', deleteError.message);
      return new Response(JSON.stringify({ error: 'Failed to delete group' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('category-groups/delete unexpected error:', err);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};
