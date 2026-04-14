import type { APIRoute } from 'astro';
import { handleAdminTriggerRequest } from '../../../lib/admin/pipelineTrigger.js';

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

  let mode: 'resume' | 'force_refresh' | 'handbook-extract' | 'weekly' = 'resume';
  let targetDate: string | null = null;
  let weekId: string | null = null;
  let force = false;
  let skipHandbook = false;
  try {
    const payload = await request.json();
    if (payload?.mode === 'force_refresh' || payload?.mode === 'resume' || payload?.mode === 'handbook-extract' || payload?.mode === 'weekly') {
      mode = payload.mode;
    }
    if (payload?.target_date && /^\d{4}-\d{2}-\d{2}$/.test(payload.target_date)) {
      targetDate = payload.target_date;
    }
    if (payload?.week_id && /^\d{4}-W\d{2}$/.test(payload.week_id)) {
      weekId = payload.week_id;
    }
    if (payload?.force === true) {
      force = true;
    }
    if (payload?.skip_handbook === true) {
      skipHandbook = true;
    }
  } catch {}

  const env = {
    CRON_SECRET: import.meta.env.CRON_SECRET,
    FASTAPI_URL: import.meta.env.FASTAPI_URL,
  };
  return handleAdminTriggerRequest(env, mode, targetDate, force, skipHandbook, weekId);
};
