import type { APIRoute } from 'astro';

export const prerender = false;

export const POST: APIRoute = async ({ locals }) => {
  const accessToken = (locals as any).accessToken;
  if (!(locals as any).isAdmin || !accessToken) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const fastapiUrl = import.meta.env.FASTAPI_URL;
  if (!fastapiUrl) {
    return new Response(JSON.stringify({ error: 'Backend not configured' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const res = await fetch(`${fastapiUrl}/api/admin/suggest-topics`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    const data = await res.json().catch(() => ({}));
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch {
    return new Response(JSON.stringify({ error: 'Backend unreachable' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
