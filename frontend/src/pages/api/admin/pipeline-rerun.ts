import type { APIRoute } from 'astro';
import { handleRerunRequest } from '../../../lib/admin/pipelineTrigger.js';

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

  let payload: Record<string, unknown> = {};
  try {
    payload = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  if (!payload.run_id || !payload.from_stage || !payload.batch_id) {
    return new Response(JSON.stringify({ error: 'Missing run_id, from_stage, or batch_id' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const env = {
    CRON_SECRET: import.meta.env.CRON_SECRET,
    FASTAPI_URL: import.meta.env.FASTAPI_URL,
  };
  return handleRerunRequest(env, payload);
};
