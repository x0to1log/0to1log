import { defineMiddleware } from 'astro:middleware';
import { createClient } from '@supabase/supabase-js';

const isSecure = import.meta.env.PROD;

function buildCspHeader(nonce: string): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://*.clarity.ms`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "img-src 'self' data: https: https://*.google-analytics.com https://*.clarity.ms",
    "font-src 'self' https://fonts.gstatic.com",
    "connect-src 'self' *.supabase.co https://*.google-analytics.com https://*.analytics.google.com https://*.clarity.ms",
  ].join('; ');
}

async function nextWithCsp(next: () => Promise<Response>, nonce: string): Promise<Response> {
  const response = await next();
  response.headers.set('Content-Security-Policy', buildCspHeader(nonce));
  return response;
}
async function validateToken(
  cookies: any,
  supabaseUrl: string,
  supabaseAnonKey: string,
): Promise<{ user: any; accessToken: string } | null> {
  const accessToken = cookies.get('sb-access-token')?.value;
  const refreshToken = cookies.get('sb-refresh-token')?.value;

  if (!accessToken) return null;

  const supabase = createClient(supabaseUrl, supabaseAnonKey);
  const { data: { user }, error } = await supabase.auth.getUser(accessToken);

  if (!error && user) {
    return { user, accessToken };
  }

  // Try refresh
  if (refreshToken) {
    const { data: refreshData, error: refreshError } =
      await supabase.auth.refreshSession({ refresh_token: refreshToken });
    if (!refreshError && refreshData.session) {
      cookies.set('sb-access-token', refreshData.session.access_token, {
        path: '/', httpOnly: true, secure: isSecure, sameSite: 'lax', maxAge: 3600,
      });
      cookies.set('sb-refresh-token', refreshData.session.refresh_token, {
        path: '/', httpOnly: true, secure: isSecure, sameSite: 'lax', maxAge: 604800,
      });
      return {
        user: refreshData.session.user,
        accessToken: refreshData.session.access_token,
      };
    }
  }

  // Token invalid, clear cookies
  cookies.delete('sb-access-token', { path: '/' });
  cookies.delete('sb-refresh-token', { path: '/' });
  return null;
}

/** Fetch admin status + profile in parallel with one Supabase client */
async function fetchUserExtras(
  supabaseUrl: string,
  supabaseAnonKey: string,
  user: any,
  accessToken: string,
): Promise<{ isAdmin: boolean; profile: App.Locals['profile'] }> {
  const sb = createClient(supabaseUrl, supabaseAnonKey, {
    global: { headers: { Authorization: `Bearer ${accessToken}` } },
  });

  const [adminResult, profileResult] = await Promise.all([
    sb.from('admin_users').select('user_id').eq('user_id', user.id).maybeSingle(),
    sb.from('profiles')
      .select('display_name, username, username_changed_at, avatar_url, persona, preferred_locale, is_public, onboarding_completed')
      .eq('id', user.id)
      .maybeSingle(),
  ]);

  const profile = profileResult.data || {
    display_name: user.user_metadata?.full_name || null,
    username: null,
    username_changed_at: null,
    avatar_url: user.user_metadata?.avatar_url || null,
    persona: null,
    preferred_locale: 'ko',
    is_public: false,
    onboarding_completed: false,
  };

  return { isAdmin: !!adminResult.data, profile };
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;
  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;

  // Generate CSP nonce for every request
  const nonce = crypto.randomUUID().replace(/-/g, '');
  context.locals.cspNonce = nonce;

  // Track site locale via cookie for non-locale-prefixed pages
  const langParam = context.url.searchParams.get('lang');
  if (langParam === 'en' || langParam === 'ko') {
    context.cookies.set('site-locale', langParam, { path: '/', maxAge: 31536000, sameSite: 'lax' });
  } else if (pathname.startsWith('/en/')) {
    context.cookies.set('site-locale', 'en', { path: '/', maxAge: 31536000, sameSite: 'lax' });
  } else if (pathname.startsWith('/ko/')) {
    context.cookies.set('site-locale', 'ko', { path: '/', maxAge: 31536000, sameSite: 'lax' });
  }

  // Skip auth entirely if Supabase not configured
  if (!supabaseUrl || !supabaseAnonKey) {
    // Admin routes still need to redirect
    if (pathname.startsWith('/admin') && pathname !== '/admin/login') {
      return context.redirect('/admin/login');
    }
    return nextWithCsp(next, nonce);
  }

  // --- Zone 1: Admin-protected (/admin/*, /api/admin/* except /admin/login) ---
  const isAdminRoute = (pathname.startsWith('/admin') && pathname !== '/admin/login') || pathname.startsWith('/api/admin/');
  if (isAdminRoute) {
    const isApiRoute = pathname.startsWith('/api/');
    const result = await validateToken(context.cookies, supabaseUrl, supabaseAnonKey);
    if (!result) {
      if (isApiRoute) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return context.redirect('/admin/login');
    }

    const extras = await fetchUserExtras(supabaseUrl, supabaseAnonKey, result.user, result.accessToken);
    if (!extras.isAdmin) {
      if (isApiRoute) {
        return new Response(JSON.stringify({ error: 'Forbidden' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return context.redirect('/admin/login');
    }

    context.locals.user = result.user;
    context.locals.accessToken = result.accessToken;
    context.locals.isAdmin = true;
    context.locals.profile = extras.profile;
    return nextWithCsp(next, nonce);
  }

  // --- Zone 2: User-protected (/api/user/*, /library, /settings) ---
  if (pathname.startsWith('/api/user/') || pathname.startsWith('/library') || pathname.startsWith('/settings')) {
    const result = await validateToken(context.cookies, supabaseUrl, supabaseAnonKey);
    if (!result) {
      if (pathname.startsWith('/api/')) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      const redirectTo = encodeURIComponent(pathname);
      return context.redirect(`/login?redirectTo=${redirectTo}`);
    }

    const extras = await fetchUserExtras(supabaseUrl, supabaseAnonKey, result.user, result.accessToken);
    context.locals.user = result.user;
    context.locals.accessToken = result.accessToken;
    context.locals.isAdmin = extras.isAdmin || undefined;
    context.locals.profile = extras.profile;
    return nextWithCsp(next, nonce);
  }

  // --- Zone 3: Public (all other routes) ---
  // Silently try to extract user for optional features (read history, bookmark state)
  const accessToken = context.cookies.get('sb-access-token')?.value;
  if (accessToken) {
    const result = await validateToken(context.cookies, supabaseUrl, supabaseAnonKey);
    if (result) {
      const extras = await fetchUserExtras(supabaseUrl, supabaseAnonKey, result.user, result.accessToken);
      context.locals.user = result.user;
      context.locals.accessToken = result.accessToken;
      context.locals.isAdmin = extras.isAdmin || undefined;
      context.locals.profile = extras.profile;
    }
  }

  return nextWithCsp(next, nonce);
});
