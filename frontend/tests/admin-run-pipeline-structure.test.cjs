const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function assertIncludes(source, needle, label) {
  if (!source.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

function run() {
  const adminIndex = read('src/pages/admin/index.astro');
  assertIncludes(adminIndex, "fetch('/api/admin/run-pipeline'", 'admin pipeline endpoint target');
  assertIncludes(adminIndex, "credentials: 'same-origin'", 'admin pipeline credentials');
  assertIncludes(adminIndex, 'Run Pipeline', 'pipeline button label');
  assertIncludes(adminIndex, "bindPipelineButton(pipelineBtn, 'Run Pipeline', 'resume')", 'resume request mode binding');
  assertIncludes(adminIndex, 'if (force) reqBody.force = true', 'force retry request flag');
  assertIncludes(adminIndex, 'Overwrite existing data?', 'duplicate run confirmation');
  assertIncludes(adminIndex, "res.status === 503", 'admin pipeline 503 handling');

  const cronRoute = read('src/pages/api/trigger-pipeline.ts');
  assertIncludes(cronRoute, 'export const GET', 'cron GET handler');
  assertIncludes(cronRoute, 'handleCronTriggerRequest', 'cron trigger helper usage');

  const adminRoute = read('src/pages/api/admin/run-pipeline.ts');
  assertIncludes(adminRoute, 'export const POST', 'admin POST handler');
  assertIncludes(adminRoute, 'locals.accessToken', 'admin route cookie auth local');
  assertIncludes(adminRoute, 'locals.isAdmin', 'admin route admin local');
  assertIncludes(adminRoute, "error: 'Forbidden'", 'admin route explicit 403 reason');
  assertIncludes(adminRoute, 'handleAdminTriggerRequest', 'admin trigger helper usage');
  assertIncludes(adminRoute, 'await request.json()', 'admin route body parsing');
  assertIncludes(adminRoute, 'force_refresh', 'admin route force refresh mode handling');
  assertIncludes(adminRoute, 'handbook-extract', 'admin route handbook mode handling');
  assertIncludes(adminRoute, 'weekly', 'admin route weekly mode handling');

  const middleware = read('src/middleware.ts');
  assertIncludes(middleware, "pathname.startsWith('/api/admin/')", 'admin API middleware protection');
  assertIncludes(middleware, 'context.locals.isAdmin = true', 'admin local set by middleware');
  assertIncludes(middleware, "error: 'Admin lookup failed'", 'admin lookup failure response');

  const helper = read('src/lib/admin/pipelineTrigger.js');
  assertIncludes(helper, 'const payload = { mode }', 'pipeline trigger mode body');
  assertIncludes(helper, 'if (force) payload.force = true', 'pipeline trigger force body');
  assertIncludes(helper, 'function forwardPipelineTrigger(env, mode =', 'pipeline trigger mode parameter');

  console.log('admin-run-pipeline-structure.test: ok');
}

run();
