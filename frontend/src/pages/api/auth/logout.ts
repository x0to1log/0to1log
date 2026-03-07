import type { APIRoute } from 'astro';

export const prerender = false;

export const POST: APIRoute = async ({ cookies, url }) => {
  cookies.delete('sb-access-token', { path: '/' });
  cookies.delete('sb-refresh-token', { path: '/' });

  const redirectTo = url.searchParams.get('redirectTo') || '/admin/login';
  return new Response(null, {
    status: 302,
    headers: { Location: redirectTo },
  });
};
