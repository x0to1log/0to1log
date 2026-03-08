import type { APIRoute } from 'astro';

export const prerender = false;

function logout(cookies: Parameters<APIRoute>[0]['cookies'], url: URL) {
  cookies.delete('sb-access-token', { path: '/' });
  cookies.delete('sb-refresh-token', { path: '/' });

  const redirectTo = url.searchParams.get('redirectTo') || '/';
  return new Response(null, {
    status: 302,
    headers: { Location: redirectTo },
  });
}

export const POST: APIRoute = async ({ cookies, url }) => logout(cookies, url);
export const GET: APIRoute = async ({ cookies, url }) => logout(cookies, url);
