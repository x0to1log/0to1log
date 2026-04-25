import type { APIRoute } from 'astro';

export const prerender = false;

/**
 * Vercel cron target: Monday 01:00 UTC (= Mon 10:00 KST). Calls the FastAPI
 * weekly cron endpoint, which kicks off the weekly recap pipeline (5-10 min)
 * with auto-publish enabled when quality_score >= threshold (default 85).
 *
 * Daily runs at 22:00 UTC (07:00 KST) and finishes ~30 min later, so by
 * 10:00 KST Monday all 7 days of digests (Mon-Sun) are present and ready
 * for synthesis.
 */
export const GET: APIRoute = async ({ request }) => {
  const cronSecret = import.meta.env.CRON_SECRET;
  const backendUrl = import.meta.env.FASTAPI_URL;

  if (!cronSecret || !backendUrl) {
    return new Response(JSON.stringify({ error: 'Missing configuration' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${cronSecret}`) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const response = await fetch(`${backendUrl}/api/cron/weekly`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-cron-secret': cronSecret,
      },
      // Empty body → backend defaults to last week's ISO id (today - 7 days).
      body: JSON.stringify({}),
      // Backend returns 202 immediately and runs the pipeline in the background.
      // 8s is plenty for the trigger handshake.
      signal: AbortSignal.timeout(8000),
    });
    const data = await response.json();
    return new Response(JSON.stringify({ ok: response.ok, data }), {
      status: response.ok ? 200 : 502,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(JSON.stringify({ error: 'Backend request failed', message }), {
      status: 502, headers: { 'Content-Type': 'application/json' },
    });
  }
};
