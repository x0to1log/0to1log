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

  const cronRoute = read('src/pages/api/trigger-pipeline.ts');
  assertIncludes(cronRoute, 'export const GET', 'cron GET handler');
  assertIncludes(cronRoute, 'handleCronTriggerRequest', 'cron trigger helper usage');

  const adminRoute = read('src/pages/api/admin/run-pipeline.ts');
  assertIncludes(adminRoute, 'export const POST', 'admin POST handler');
  assertIncludes(adminRoute, 'requireAdminFromCookies', 'admin route cookie auth helper');
  assertIncludes(adminRoute, "error: 'Not an active admin user'", 'admin route explicit 403 reason');
  assertIncludes(adminRoute, 'handleAdminTriggerRequest', 'admin trigger helper usage');

  const middleware = read('src/middleware.ts');
  assertIncludes(middleware, "pathname.startsWith('/api/admin/')", 'admin API middleware protection');
  assertIncludes(middleware, "pathname === '/api/admin/run-pipeline'", 'run pipeline middleware exemption');
  assertIncludes(middleware, "error: 'Admin lookup failed'", 'admin lookup failure response');
  assertIncludes(adminIndex, "res.status === 503", 'admin pipeline 503 handling');

  console.log('admin-run-pipeline-structure.test: ok');
}

run();
