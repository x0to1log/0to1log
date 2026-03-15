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

async function forwardPipelineTrigger(env, mode = 'resume', targetDate = null) {
  const config = getPipelineConfig(env);
  if (!config) {
    return jsonResponse({ error: 'Missing configuration' }, 500);
  }

  try {
    const payload = { mode };
    if (targetDate) payload.target_date = targetDate;

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

    return jsonResponse(
      {
        ok: response.ok,
        status: response.status,
        data,
      },
      response.ok ? 200 : 502,
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

export async function handleAdminTriggerRequest(env, mode = 'resume', targetDate = null) {
  return forwardPipelineTrigger(env, mode, targetDate);
}
