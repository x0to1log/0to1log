import { defineMiddleware } from 'astro:middleware';
import { createClient } from '@supabase/supabase-js';

const isSecure = import.meta.env.PROD;

function buildCspHeader(nonce: string): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' https://www.googletagmanager.com https://*.clarity.ms`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "img-src 'self' data: https: https://*.google-analytics.com https://*.clarity.ms",
    "font-src 'self' https://fonts.gstatic.com",
    "connect-src 'self' *.supabase.co https://*.google-analytics.com https://*.analytics.google.com https://*.clarity.ms",
  ].join('; ');
}

function addNonceToScriptTags(html: string, nonce: string): string {
  return html.replace(/<script\b(?![^>]*\bnonce=)([^>]*)>/gi, `<script nonce="${nonce}"$1>`);
}

async function nextWithCsp(next: () => Promise<Response>, nonce: string): Promise<Response> {
  const response = await next();
  const contentType = response.headers.get('content-type') || '';

  if (!contentType.includes('text/html')) {
    response.headers.set('Content-Security-Policy', buildCspHeader(nonce));
    return response;
  }

  const rewrittenHtml = addNonceToScriptTags(await response.text(), nonce);
  const rewrittenResponse = new Response(rewrittenHtml, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
  });
  rewrittenResponse.headers.set('Content-Security-Policy', buildCspHeader(nonce));
  return rewrittenResponse;
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
      .select('display_name, username, username_changed_at, avatar_url, persona, preferred_locale, handbook_level, is_public, onboarding_completed')
      .eq('id', user.id)
      .maybeSingle(),
  ]);

  if (adminResult.error) {
    throw new Error(`Admin lookup failed: ${adminResult.error.message}`);
  }

  const profile = profileResult.data || {
    display_name: user.user_metadata?.full_name || null,
    username: null,
    username_changed_at: null,
    avatar_url: user.user_metadata?.avatar_url || null,
    persona: null,
    preferred_locale: 'ko',
    handbook_level: 'basic',
    is_public: false,
    onboarding_completed: false,
  };

  return { isAdmin: !!adminResult.data, profile };
}

/** Try to read cached user extras from cookie, returns null if missing/expired */
function getCachedExtras(
  cookies: any,
): { isAdmin: boolean; profile: App.Locals['profile'] } | null {
  const raw = cookies.get('user-extras-cache')?.value;
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/** Cache user extras in a short-lived cookie (5 min) */
function setCachedExtras(
  cookies: any,
  extras: { isAdmin: boolean; profile: App.Locals['profile'] },
  isSecureEnv: boolean,
): void {
  cookies.set('user-extras-cache', JSON.stringify(extras), {
    path: '/',
    httpOnly: true,
    secure: isSecureEnv,
    sameSite: 'lax',
    maxAge: 300,
  });
}

/** Fetch user extras, using cookie cache when available */
async function getOrFetchUserExtras(
  cookies: any,
  supabaseUrl: string,
  supabaseAnonKey: string,
  user: any,
  accessToken: string,
  isSecureEnv: boolean,
): Promise<{ isAdmin: boolean; profile: App.Locals['profile'] }> {
  const cached = getCachedExtras(cookies);
  if (cached) return cached;
  const extras = await fetchUserExtras(supabaseUrl, supabaseAnonKey, user, accessToken);
  setCachedExtras(cookies, extras, isSecureEnv);
  return extras;
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;
  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  const isSelfHandledAdminApiRoute = pathname === '/api/admin/run-pipeline';

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
    if ((pathname.startsWith('/admin') && pathname !== '/admin/login') || isSelfHandledAdminApiRoute) {
      return context.redirect('/admin/login');
    }
    return nextWithCsp(next, nonce);
  }

  // --- Zone 1: Admin-protected (/admin/*, /api/admin/* except /admin/login) ---
  const isAdminRoute = (
    (pathname.startsWith('/admin') && pathname !== '/admin/login')
    || pathname.startsWith('/api/admin/')
  ) && !isSelfHandledAdminApiRoute;
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

    // Admin routes always fetch fresh (no cache) for security
    let extras: { isAdmin: boolean; profile: App.Locals['profile'] };
    try {
      extras = await fetchUserExtras(supabaseUrl, supabaseAnonKey, result.user, result.accessToken);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Admin lookup failed';
      if (isApiRoute) {
        return new Response(JSON.stringify({ error: 'Admin lookup failed', message }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response('Admin verification unavailable', { status: 503 });
    }
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
    setCachedExtras(context.cookies, extras, isSecure);
    return nextWithCsp(next, nonce);
  }

  // --- Zone 2: User-protected (/api/user/*, /settings) ---
  // Exception: GET /api/user/comments is publicly readable (comments visible to all)
  const isPublicCommentRead = pathname === '/api/user/comments' && context.request.method === 'GET';
  if (!isPublicCommentRead && (pathname.startsWith('/api/user/') || pathname.startsWith('/settings'))) {
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

    const extras = await getOrFetchUserExtras(context.cookies, supabaseUrl, supabaseAnonKey, result.user, result.accessToken, isSecure);
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
      const extras = await getOrFetchUserExtras(context.cookies, supabaseUrl, supabaseAnonKey, result.user, result.accessToken, isSecure);
      context.locals.user = result.user;
      context.locals.accessToken = result.accessToken;
      context.locals.isAdmin = extras.isAdmin || undefined;
      context.locals.profile = extras.profile;
    }
  }

  return nextWithCsp(next, nonce);
});
