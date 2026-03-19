import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

function authSupabase(accessToken: string) {
  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );
}

// GET → { likedIds: string[] }  (로그인 사용자의 전체 찜 목록 product_id 배열)
export const GET: APIRoute = async ({ locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ likedIds: [] }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = authSupabase(locals.accessToken);
  const { data, error } = await supabase
    .from('ai_product_likes')
    .select('product_id');

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ likedIds: data.map((r) => r.product_id) }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};

// POST { product_id } → toggle, 반환 { liked: bool, like_count: number }
export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json() as { product_id?: string };
  const { product_id } = body;

  if (!product_id) {
    return new Response(JSON.stringify({ error: 'Missing product_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabase = authSupabase(locals.accessToken);

  // Check if already liked
  const { data: existing } = await supabase
    .from('ai_product_likes')
    .select('id')
    .eq('user_id', locals.user.id)
    .eq('product_id', product_id)
    .maybeSingle();

  if (existing) {
    await supabase.from('ai_product_likes').delete().eq('id', existing.id);
  } else {
    const { error } = await supabase.from('ai_product_likes').insert({
      user_id: locals.user.id,
      product_id,
    });
    if (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500, headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  // like_count는 트리거가 업데이트 — 현재 값 조회
  const { data: product } = await supabase
    .from('ai_products')
    .select('like_count')
    .eq('id', product_id)
    .maybeSingle();

  return new Response(JSON.stringify({
    liked: !existing,
    like_count: product?.like_count ?? 0,
  }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
