import assert from 'node:assert/strict';

import {
  handleAdminTriggerRequest,
  handleCronTriggerRequest,
  handleRerunRequest,
} from '../src/lib/admin/pipelineTrigger.js';

async function readJson(response) {
  return JSON.parse(await response.text());
}

const env = {
  CRON_SECRET: 'secret-123',
  FASTAPI_URL: 'https://backend.example.com',
};

{
  const response = await handleCronTriggerRequest(
    new Request('https://frontend.example.com/api/trigger-pipeline'),
    env,
  );
  assert.equal(response.status, 401, 'Cron route should reject missing bearer token');
}

{
  let fetchArgs = null;
  globalThis.fetch = async (...args) => {
    fetchArgs = args;
    return new Response(JSON.stringify({ accepted: true, message: 'queued' }), {
      status: 202,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const response = await handleCronTriggerRequest(
    new Request('https://frontend.example.com/api/trigger-pipeline', {
      headers: { authorization: 'Bearer secret-123' },
    }),
    env,
  );
  const json = await readJson(response);

  assert.equal(response.status, 200, 'Cron route should normalize successful backend queueing');
  assert.equal(fetchArgs[0], 'https://backend.example.com/api/cron/news-pipeline');
  assert.equal(fetchArgs[1].method, 'POST');
  assert.equal(fetchArgs[1].headers['x-cron-secret'], 'secret-123');
  assert.equal(json.ok, true);
  assert.equal(json.status, 202);
}

{
  let fetchArgs = null;
  globalThis.fetch = async (...args) => {
    fetchArgs = args;
    return new Response(JSON.stringify({ accepted: true, message: 'queued' }), {
      status: 202,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const response = await handleAdminTriggerRequest(env);
  const json = await readJson(response);

  assert.equal(response.status, 200, 'Admin trigger should normalize successful backend queueing');
  assert.equal(fetchArgs[0], 'https://backend.example.com/api/cron/news-pipeline');
  assert.equal(fetchArgs[1].headers['x-cron-secret'], 'secret-123');
  assert.equal(json.ok, true);
  assert.equal(json.status, 202);
}

{
  const response = await handleAdminTriggerRequest({ FASTAPI_URL: '', CRON_SECRET: '' });
  const json = await readJson(response);
  assert.equal(response.status, 500, 'Missing env should surface as configuration error');
  assert.equal(json.error, 'Missing configuration');
}

{
  // RERUN-GUARD-01: the backend refuses reruns over published posts with 422;
  // the admin page needs that status and message, not a generic 502.
  const detail = { error: 'published_protected', message: 'Cannot rerun business: 2 published post(s) exist for 2026-10-18.' };
  globalThis.fetch = async () => new Response(JSON.stringify({ detail }), {
    status: 422,
    headers: { 'Content-Type': 'application/json' },
  });

  const response = await handleRerunRequest(env, { run_id: 'run-1', from_stage: 'write', batch_id: '2026-10-18' });
  const json = await readJson(response);
  assert.equal(response.status, 422, 'Rerun refusal should keep its 422 status');
  assert.equal(json.ok, false);
  assert.equal(json.data.detail.message, detail.message);
}

console.log('pipeline-trigger-helper.test.mjs passed');
