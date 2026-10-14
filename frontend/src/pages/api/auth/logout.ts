import type { APIRoute } from 'astro';
import { clearSessionHint } from '../../../lib/sessionHint';

export const prerender = false;

function sanitizeRedirect(raw: string | null): string {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//')) return '/';
  return raw;
}

function logout(cookies: Parameters<APIRoute>[0]['cookies'], url: URL) {
  cookies.delete('sb-access-token', { path: '/' });
  cookies.delete('sb-refresh-token', { path: '/' });
  cookies.delete('user-extras-cache', { path: '/' });
  clearSessionHint(cookies);

  const redirectTo = sanitizeRedirect(url.searchParams.get('redirectTo'));
  return new Response(null, {
    status: 302,
    headers: { Location: redirectTo },
  });
}

export const POST: APIRoute = async ({ cookies, url }) => logout(cookies, url);
export const GET: APIRoute = async ({ cookies, url }) => logout(cookies, url);
