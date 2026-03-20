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
    const body = await request.json();
    const { original_slug, slug, label_ko, label_en, sort_order } = body;

    if (original_slug) {
      // UPDATE existing group
      const { data, error } = await supabase
        .from('category_groups')
        .update({ slug, label_ko, label_en, sort_order })
        .eq('slug', original_slug)
        .select()
        .single();

      if (error) {
        console.error('category_groups update error:', error.message);
        return new Response(JSON.stringify({ error: 'Failed to update group' }), {
          status: 500, headers: { 'Content-Type': 'application/json' },
        });
      }

      // If slug changed, update all categories that referenced the old slug
      if (slug !== original_slug) {
        const { error: catError } = await supabase
          .from('blog_categories')
          .update({ group_slug: slug })
          .eq('group_slug', original_slug);

        if (catError) {
          console.error('blog_categories group_slug update error:', catError.message);
          // Non-fatal: group was saved; log and continue
        }
      }

      return new Response(JSON.stringify(data), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    }

    // INSERT new group
    const { data, error } = await supabase
      .from('category_groups')
      .insert({ slug, label_ko, label_en, sort_order })
      .select()
      .single();

    if (error) {
      if (error.code === '23505') {
        return new Response(JSON.stringify({ error: '이미 사용 중인 슬러그입니다.' }), {
          status: 409, headers: { 'Content-Type': 'application/json' },
        });
      }
      console.error('category_groups insert error:', error.message);
      return new Response(JSON.stringify({ error: 'Failed to create group' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify(data), {
      status: 201, headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('category-groups/save unexpected error:', err);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};
