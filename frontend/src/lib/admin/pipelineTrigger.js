const JSON_HEADERS = { 'Content-Type': 'application/json' };

function jsonResponse(payload, status) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: JSON_HEADERS,
  });
}

function getPipelineConfig(env) {
  const cronSecret = env?.CRON_SECRET;
  const backendUrl = env?.FASTAPI_URL;

  if (!cronSecret || !backendUrl) {
    return null;
  }

  return { cronSecret, backendUrl };
}

async function forwardPipelineTrigger(env, mode = 'resume', targetDate = null, force = false, skipHandbook = false) {
  const config = getPipelineConfig(env);
  if (!config) {
    return jsonResponse({ error: 'Missing configuration' }, 500);
  }

  try {
    // Route handbook-extract to its own backend endpoint
    if (mode === 'handbook-extract' && targetDate) {
      const response = await fetch(`${config.backendUrl}/api/cron/handbook-extract`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-cron-secret': config.cronSecret,
        },
        body: JSON.stringify({ batch_id: targetDate }),
        signal: AbortSignal.timeout(8000),
      });

      const data = await response.json();
      const forwardStatus = response.ok ? 200
        : [409, 422].includes(response.status) ? response.status
        : 502;

      return jsonResponse(
        {
          ok: response.ok,
          status: response.status,
          data,
        },
        forwardStatus,
      );
    }

    const payload = { mode };
    if (targetDate) payload.target_date = targetDate;
    if (force) payload.force = true;
    if (skipHandbook) payload.skip_handbook = true;

    const response = await fetch(`${config.backendUrl}/api/cron/news-pipeline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-cron-secret': config.cronSecret,
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(8000),
    });

    const data = await response.json();

    // Pass through meaningful status codes (409=conflict, 422=published protection)
    const forwardStatus = response.ok ? 200
      : [409, 422].includes(response.status) ? response.status
      : 502;

    return jsonResponse(
      {
        ok: response.ok,
        status: response.status,
        data,
      },
      forwardStatus,
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return jsonResponse({ error: 'Backend request failed', message }, 502);
  }
}

export async function handleCronTriggerRequest(request, env) {
  const config = getPipelineConfig(env);
  if (!config) {
    return jsonResponse({ error: 'Missing configuration' }, 500);
  }

  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${config.cronSecret}`) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  return forwardPipelineTrigger(env, 'resume');
}

export async function handleAdminTriggerRequest(env, mode = 'resume', targetDate = null, force = false, skipHandbook = false) {
  return forwardPipelineTrigger(env, mode, targetDate, force, skipHandbook);
}

export async function handleCancelRequest(env, runId) {
  const config = getPipelineConfig(env);
  if (!config) {
    return jsonResponse({ error: 'Missing configuration' }, 500);
  }
  try {
    const response = await fetch(`${config.backendUrl}/api/cron/pipeline-cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-cron-secret': config.cronSecret },
      body: JSON.stringify({ run_id: runId }),
      signal: AbortSignal.timeout(8000),
    });
    const data = await response.json();
    return jsonResponse({ ok: response.ok, data }, response.ok ? 200 : 502);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return jsonResponse({ error: 'Cancel request failed', message }, 502);
  }
}
