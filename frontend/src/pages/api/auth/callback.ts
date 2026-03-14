import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;
const isSecure = import.meta.env.PROD;

/** Prevent open redirect: only allow relative paths starting with / (not //) */
function sanitizeRedirect(raw: string | null): string {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//')) return '/';
  return raw;
}

// OAuth code exchange (Supabase PKCE flow redirect)
export const GET: APIRoute = async ({ url, cookies }) => {
  const code = url.searchParams.get('code');
  const redirectTo = sanitizeRedirect(url.searchParams.get('redirectTo'));

  if (!code) {
    return new Response(null, {
      status: 302,
      headers: { Location: '/login?error=no_code' },
    });
  }

  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseKey) {
    return new Response(null, {
      status: 302,
      headers: { Location: '/login?error=config' },
    });
  }

  const supabase = createClient(supabaseUrl, supabaseKey);
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);

  if (error || !data.session) {
    return new Response(null, {
      status: 302,
      headers: { Location: '/login?error=exchange_failed' },
    });
  }

  cookies.set('sb-access-token', data.session.access_token, {
    path: '/',
    httpOnly: true,
    secure: isSecure,
    sameSite: 'lax',
    maxAge: 3600,
  });
  cookies.set('sb-refresh-token', data.session.refresh_token, {
    path: '/',
    httpOnly: true,
    secure: isSecure,
    sameSite: 'lax',
    maxAge: 604800,
  });
  // Clear stale user extras cache from previous session
  cookies.delete('user-extras-cache', { path: '/' });

  return new Response(null, {
    status: 302,
    headers: { Location: redirectTo },
  });
};

/** Detect default locale from Accept-Language header */
function detectLocale(request: Request): 'ko' | 'en' {
  const acceptLang = request.headers.get('accept-language') || '';
  return acceptLang.split(',').some(l => l.trim().startsWith('ko')) ? 'ko' : 'en';
}

// Email/password login (existing admin flow)
export const POST: APIRoute = async ({ request, cookies }) => {
  try {
    const { access_token, refresh_token } = await request.json();

    if (!access_token || !refresh_token) {
      return new Response(JSON.stringify({ error: 'Missing tokens' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    cookies.set('sb-access-token', access_token, {
      path: '/',
      httpOnly: true,
      secure: isSecure,
      sameSite: 'lax',
      maxAge: 3600, // 1 hour
    });

    cookies.set('sb-refresh-token', refresh_token, {
      path: '/',
      httpOnly: true,
      secure: isSecure,
      sameSite: 'lax',
      maxAge: 604800, // 7 days
    });
    // Clear stale user extras cache from previous session
    cookies.delete('user-extras-cache', { path: '/' });

    // Auto-create profile on first login (best-effort, never blocks login)
    try {
      const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
      const supabaseKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
      if (supabaseUrl && supabaseKey) {
        const sb = createClient(supabaseUrl, supabaseKey, {
          global: { headers: { Authorization: `Bearer ${access_token}` } },
        });
        const { data: { user } } = await sb.auth.getUser(access_token);
        if (user) {
          const { data: existing } = await sb
            .from('profiles')
            .select('id')
            .eq('id', user.id)
            .maybeSingle();

          if (!existing) {
            const meta = user.user_metadata || {};
            await sb.from('profiles').insert({
              id: user.id,
              display_name: meta.full_name || meta.name || user.email || null,
              avatar_url: meta.avatar_url || null,
              preferred_locale: detectLocale(request),
              onboarding_completed: false,
            });
          }
        }
      }
    } catch {
      // Profile creation failure must not block login
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid request' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
