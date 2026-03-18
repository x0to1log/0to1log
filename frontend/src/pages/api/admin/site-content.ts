import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

export const GET: APIRoute = async ({ locals }) => {
  if (!locals.user || !locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  const sb = createClient(supabaseUrl, supabaseAnonKey);

  const { data, error } = await sb.from('site_content').select('key, value_ko, value_en');
  if (error) {
    console.error('site_content read error:', error.message);
    return new Response(JSON.stringify({ error: 'Failed to load site content' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ rows: data }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken || !locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json();
  const { key, value_ko, value_en } = body;

  if (!key || typeof key !== 'string') {
    return new Response(JSON.stringify({ error: 'key is required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  const sb = createClient(supabaseUrl, supabaseAnonKey, {
    global: { headers: { Authorization: `Bearer ${locals.accessToken}` } },
  });

  const { error } = await sb
    .from('site_content')
    .upsert({ key, value_ko: value_ko || '', value_en: value_en || '', updated_at: new Date().toISOString() });

  if (error) {
    console.error('site_content save error:', error.message);
    return new Response(JSON.stringify({ error: 'Failed to save site content' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
