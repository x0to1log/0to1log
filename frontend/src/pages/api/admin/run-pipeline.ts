import type { APIRoute } from 'astro';
import { handleAdminTriggerRequest } from '../../../lib/admin/pipelineTrigger.js';

export const prerender = false;

export const POST: APIRoute = async () => {
  return handleAdminTriggerRequest(import.meta.env);
};
