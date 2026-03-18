import type { APIRoute } from 'astro';
import { handleCancelRequest } from '../../../lib/admin/pipelineTrigger.js';

export const prerender = false;

export const POST: APIRoute = async ({ request, locals }) => {
  const accessToken = locals.accessToken;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }

  let runId = '';
  try {
    const payload = await request.json();
    runId = payload?.run_id || '';
  } catch {}

  if (!runId) {
    return new Response(JSON.stringify({ error: 'Missing run_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const env = {
    CRON_SECRET: import.meta.env.CRON_SECRET,
    FASTAPI_URL: import.meta.env.FASTAPI_URL,
  };
  return handleCancelRequest(env, runId);
};
