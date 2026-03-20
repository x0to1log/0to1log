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
    const {
      id,
      slug,
      label_ko,
      label_en,
      description_ko,
      description_en,
      color,
      icon,
      group_slug,
      sort_order,
      is_visible,
      write_mode,
      banner_url,
      guidelines,
    } = body;

    const row: Record<string, any> = {
      slug,
      label_ko,
      label_en,
      color,
      group_slug,
      sort_order,
      is_visible,
      write_mode,
    };

    if (description_ko !== undefined) row.description_ko = description_ko ?? null;
    if (description_en !== undefined) row.description_en = description_en ?? null;
    if (icon !== undefined) row.icon = icon ?? null;
    if (banner_url !== undefined) row.banner_url = banner_url ?? null;
    if (guidelines !== undefined) row.guidelines = guidelines ?? null;

    if (id) {
      const { data, error } = await supabase
        .from('blog_categories')
        .update(row)
        .eq('id', id)
        .select()
        .single();

      if (error) {
        if (error.code === '23505') {
          return new Response(JSON.stringify({ error: '이미 사용 중인 슬러그입니다.' }), {
            status: 409, headers: { 'Content-Type': 'application/json' },
          });
        }
        console.error('blog_categories update error:', error.message);
        return new Response(JSON.stringify({ error: 'Failed to update category' }), {
          status: 500, headers: { 'Content-Type': 'application/json' },
        });
      }

      return new Response(JSON.stringify(data), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    }

    const { data, error } = await supabase
      .from('blog_categories')
      .insert(row)
      .select()
      .single();

    if (error) {
      if (error.code === '23505') {
        return new Response(JSON.stringify({ error: '이미 사용 중인 슬러그입니다.' }), {
          status: 409, headers: { 'Content-Type': 'application/json' },
        });
      }
      console.error('blog_categories insert error:', error.message);
      return new Response(JSON.stringify({ error: 'Failed to create category' }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify(data), {
      status: 201, headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('categories/save unexpected error:', err);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};
