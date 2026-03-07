import type { APIRoute } from 'astro';

export const prerender = false;

export const GET: APIRoute = async ({ request }) => {
  const cronSecret = import.meta.env.CRON_SECRET;
  const backendUrl = import.meta.env.FASTAPI_URL;

  if (!cronSecret || !backendUrl) {
    return new Response(JSON.stringify({ error: 'Missing configuration' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Require Authorization: Bearer <CRON_SECRET>
  // Vercel cron auto-sends this when CRON_SECRET env var is configured
  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${cronSecret}`) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const response = await fetch(`${backendUrl}/api/cron/news-pipeline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-cron-secret': cronSecret,
      },
      signal: AbortSignal.timeout(8000),
    });

    const data = await response.json();

    return new Response(JSON.stringify({
      ok: response.ok,
      status: response.status,
      data,
    }), {
      status: response.ok ? 200 : 502,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(JSON.stringify({ error: 'Backend request failed', message }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
