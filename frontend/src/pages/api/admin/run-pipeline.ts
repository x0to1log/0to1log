import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';
import { handleAdminTriggerRequest } from '../../../lib/admin/pipelineTrigger.js';

export const prerender = false;
const isSecure = import.meta.env.PROD;

function jsonResponse(payload: Record<string, unknown>, status: number): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

async function requireAdminFromCookies(
  cookies: APIRoute['cookies'],
): Promise<{ accessToken: string } | Response> {
  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    return jsonResponse({ error: 'Supabase not configured' }, 503);
  }

  const accessTokenCookie = cookies.get('sb-access-token')?.value;
  const refreshToken = cookies.get('sb-refresh-token')?.value;
  if (!accessTokenCookie) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const supabase = createClient(supabaseUrl, supabaseAnonKey);
  let accessToken = accessTokenCookie;
  let user: Awaited<ReturnType<typeof supabase.auth.getUser>>['data']['user'] | null = null;

  const userResult = await supabase.auth.getUser(accessToken);
  if (!userResult.error && userResult.data.user) {
    user = userResult.data.user;
  } else if (refreshToken) {
    const refreshResult = await supabase.auth.refreshSession({ refresh_token: refreshToken });
    if (!refreshResult.error && refreshResult.data.session) {
      accessToken = refreshResult.data.session.access_token;
      user = refreshResult.data.session.user;
      cookies.set('sb-access-token', refreshResult.data.session.access_token, {
        path: '/',
        httpOnly: true,
        secure: isSecure,
        sameSite: 'lax',
        maxAge: 3600,
      });
      cookies.set('sb-refresh-token', refreshResult.data.session.refresh_token, {
        path: '/',
        httpOnly: true,
        secure: isSecure,
        sameSite: 'lax',
        maxAge: 604800,
      });
    }
  }

  if (!user) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const authedSupabase = createClient(supabaseUrl, supabaseAnonKey, {
    global: { headers: { Authorization: `Bearer ${accessToken}` } },
  });

  const [byUserId, byEmail] = await Promise.all([
    authedSupabase
      .from('admin_users')
      .select('user_id')
      .eq('user_id', user.id)
      .eq('is_active', true)
      .maybeSingle(),
    user.email
      ? authedSupabase
          .from('admin_users')
          .select('email')
          .eq('email', user.email)
          .eq('is_active', true)
          .maybeSingle()
      : Promise.resolve({ data: null, error: null }),
  ]);

  if (byUserId.error || byEmail.error) {
    const message = byUserId.error?.message || byEmail.error?.message || 'Admin lookup failed';
    return jsonResponse({ error: 'Admin lookup failed', message }, 503);
  }

  if (!byUserId.data && !byEmail.data) {
    return jsonResponse({ error: 'Not an active admin user' }, 403);
  }

  return { accessToken };
}

export const POST: APIRoute = async ({ cookies, request }) => {
  const authResult = await requireAdminFromCookies(cookies);
  if (authResult instanceof Response) {
    return authResult;
  }

  if (!authResult.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  let mode = 'resume';
  try {
    const payload = await request.json();
    if (payload?.mode === 'force_refresh' || payload?.mode === 'resume') {
      mode = payload.mode;
    }
  } catch {}

  return handleAdminTriggerRequest(import.meta.env, mode);
};
