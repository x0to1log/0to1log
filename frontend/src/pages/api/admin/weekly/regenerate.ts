import type { APIRoute } from 'astro';

export const prerender = false;
// Weekly regen runs the full single-persona pipeline (5-10 min on flex tier).
// Vercel serverless functions need an explicit maxDuration to not cut off mid-request.
// 300s is the Pro-plan ceiling — if the backend takes longer, the proxy times out
// but the backend keeps running server-side. The client refreshes the page on
// either success or timeout to pick up the final DB state.
export const maxDuration = 300;

export const POST: APIRoute = async ({ request, locals }) => {
  const accessToken = (locals as any).accessToken;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!(locals as any).isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const backendUrl = import.meta.env.FASTAPI_URL;
  if (!backendUrl) {
    return new Response(JSON.stringify({ error: 'Backend not configured' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json();

  try {
    const res = await fetch(`${backendUrl}/api/admin/weekly/regenerate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch {
    return new Response(JSON.stringify({ error: 'Backend unreachable or timed out — it may still be running. Refresh in a few minutes.' }), {
      status: 504,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
