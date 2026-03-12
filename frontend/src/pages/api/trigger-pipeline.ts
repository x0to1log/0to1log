import type { APIRoute } from 'astro';
import { handleCronTriggerRequest } from '../../lib/admin/pipelineTrigger.js';

export const prerender = false;

export const GET: APIRoute = async ({ request }) => {
  return handleCronTriggerRequest(request, import.meta.env);
};
