import type { APIRoute } from 'astro';

export const prerender = false;

/**
 * Session summary for client hydration of CDN-cached public pages.
 * Middleware (zone 2) has already validated the token and loaded
 * isAdmin + profile into locals; unauthenticated callers get 401 there.
 */
export const GET: APIRoute = async ({ locals }) => {
  const user = locals.user;
  if (!user) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json', 'Cache-Control': 'private, no-store' },
    });
  }

  const profile = locals.profile;
  const body = {
    authenticated: true,
    isAdmin: Boolean(locals.isAdmin),
    displayName: profile?.display_name || user.user_metadata?.full_name || user.email || '',
    avatarUrl: profile?.avatar_url || user.user_metadata?.avatar_url || null,
    persona: profile?.persona || null,
    handbookLevel: profile?.handbook_level || null,
  };

  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'private, no-store' },
  });
};
