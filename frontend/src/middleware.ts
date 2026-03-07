import { defineMiddleware } from 'astro:middleware';
import { createClient } from '@supabase/supabase-js';

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Only guard /admin/* routes (except login page)
  if (!pathname.startsWith('/admin') || pathname === '/admin/login') {
    return next();
  }

  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    return context.redirect('/admin/login');
  }

  const accessToken = context.cookies.get('sb-access-token')?.value;
  const refreshToken = context.cookies.get('sb-refresh-token')?.value;

  if (!accessToken) {
    return context.redirect('/admin/login');
  }

  const supabase = createClient(supabaseUrl, supabaseAnonKey);
  const { data: { user }, error } = await supabase.auth.getUser(accessToken);

  if (error || !user) {
    // Try refresh
    if (refreshToken) {
      const { data: refreshData, error: refreshError } =
        await supabase.auth.refreshSession({ refresh_token: refreshToken });
      if (refreshError || !refreshData.session) {
        context.cookies.delete('sb-access-token', { path: '/' });
        context.cookies.delete('sb-refresh-token', { path: '/' });
        return context.redirect('/admin/login');
      }
      // Update cookies with new tokens
      context.cookies.set('sb-access-token', refreshData.session.access_token, {
        path: '/', httpOnly: true, secure: true, sameSite: 'lax', maxAge: 3600,
      });
      context.cookies.set('sb-refresh-token', refreshData.session.refresh_token, {
        path: '/', httpOnly: true, secure: true, sameSite: 'lax', maxAge: 604800,
      });
      context.locals.user = refreshData.session.user;
      context.locals.accessToken = refreshData.session.access_token;
    } else {
      return context.redirect('/admin/login');
    }
  } else {
    context.locals.user = user;
    context.locals.accessToken = accessToken;
  }

  return next();
});
