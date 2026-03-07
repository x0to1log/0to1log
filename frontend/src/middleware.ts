import { defineMiddleware } from 'astro:middleware';
import { createClient } from '@supabase/supabase-js';

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
        path: '/', httpOnly: true, secure: true, sameSite: 'lax', maxAge: 3600,
      });
      cookies.set('sb-refresh-token', refreshData.session.refresh_token, {
        path: '/', httpOnly: true, secure: true, sameSite: 'lax', maxAge: 604800,
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

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;
  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;

  // Skip auth entirely if Supabase not configured
  if (!supabaseUrl || !supabaseAnonKey) {
    // Admin routes still need to redirect
    if (pathname.startsWith('/admin') && pathname !== '/admin/login') {
      return context.redirect('/admin/login');
    }
    return next();
  }

  // --- Zone 1: Admin-protected (/admin/* except /admin/login) ---
  if (pathname.startsWith('/admin') && pathname !== '/admin/login') {
    const result = await validateToken(context.cookies, supabaseUrl, supabaseAnonKey);
    if (!result) {
      return context.redirect('/admin/login');
    }

    // Verify user is an admin (check admin_users table via RLS)
    const adminSb = createClient(supabaseUrl, supabaseAnonKey, {
      global: { headers: { Authorization: `Bearer ${result.accessToken}` } },
    });
    const { data: adminRow } = await adminSb
      .from('admin_users')
      .select('id')
      .eq('email', result.user.email)
      .maybeSingle();

    if (!adminRow) {
      return context.redirect('/admin/login');
    }

    context.locals.user = result.user;
    context.locals.accessToken = result.accessToken;
    return next();
  }

  // --- Zone 2: User-protected (/api/user/*, /library) ---
  if (pathname.startsWith('/api/user/') || pathname.startsWith('/library')) {
    const result = await validateToken(context.cookies, supabaseUrl, supabaseAnonKey);
    if (!result) {
      // API routes → 401 JSON
      if (pathname.startsWith('/api/')) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      // Page routes → redirect to login
      const redirectTo = encodeURIComponent(pathname);
      return context.redirect(`/login?redirectTo=${redirectTo}`);
    }
    context.locals.user = result.user;
    context.locals.accessToken = result.accessToken;
    return next();
  }

  // --- Zone 3: Public (all other routes) ---
  // Silently try to extract user for optional features (read history, bookmark state)
  const accessToken = context.cookies.get('sb-access-token')?.value;
  if (accessToken) {
    const result = await validateToken(context.cookies, supabaseUrl, supabaseAnonKey);
    if (result) {
      context.locals.user = result.user;
      context.locals.accessToken = result.accessToken;
    }
  }

  return next();
});
