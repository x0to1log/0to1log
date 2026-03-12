import type { APIRoute } from 'astro';
import { handleAdminTriggerRequest } from '../../../lib/admin/pipelineTrigger.js';

export const prerender = false;

export const POST: APIRoute = async ({ locals }) => {
  if (!locals.accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  if (!locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  return handleAdminTriggerRequest(import.meta.env);
};
