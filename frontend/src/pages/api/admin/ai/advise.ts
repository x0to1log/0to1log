import type { APIRoute } from 'astro';

export const prerender = false;

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
    const res = await fetch(`${backendUrl}/api/admin/ai/advise`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120_000), // 120s for deep verify / factcheck
    });

    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    const isTimeout = e instanceof DOMException && e.name === 'TimeoutError';
    return new Response(JSON.stringify({ error: isTimeout ? 'Request timed out (120s)' : 'Backend unreachable' }), {
      status: isTimeout ? 504 : 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
