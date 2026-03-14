import type { APIRoute } from 'astro';
import { handleCronTriggerRequest } from '../../lib/admin/pipelineTrigger.js';

export const prerender = false;

export const GET: APIRoute = async ({ request }) => {
  const env = {
    CRON_SECRET: import.meta.env.CRON_SECRET,
    FASTAPI_URL: import.meta.env.FASTAPI_URL,
  };
  return handleCronTriggerRequest(request, env);
};
