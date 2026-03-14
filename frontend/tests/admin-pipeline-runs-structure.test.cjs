const fs = require('fs');
const path = require('path');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

function assertIncludes(source, needle, label) {
  if (!source.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

function assertNotIncludes(source, needle, label) {
  if (source.includes(needle)) {
    throw new Error(`Unexpected ${label}: ${needle}`);
  }
}

function assertOrdered(source, items, label) {
  let previous = -1;
  for (const item of items) {
    const index = source.indexOf(item);
    if (index === -1) {
      throw new Error(`Missing ${label} item: ${item}`);
    }
    if (index <= previous) {
      throw new Error(`Unexpected ${label} order around: ${item}`);
    }
    previous = index;
  }
}

function run() {
  const adminIndex = read('frontend/src/pages/admin/index.astro');
  assertIncludes(adminIndex, '/admin/pipeline-runs', 'dashboard pipeline runs link');

  const sidebar = read('frontend/src/components/admin/AdminSidebar.astro');
  assertIncludes(sidebar, 'Pipeline Runs', 'sidebar pipeline runs navigation');
  assertOrdered(
    sidebar,
    ['Pipeline Runs', 'News', 'Handbook', 'Blog', 'Settings'],
    'admin sidebar navigation',
  );

  const listPage = read('frontend/src/pages/admin/pipeline-runs/index.astro');
  assertIncludes(listPage, 'Pipeline Runs', 'runs page heading');
  assertIncludes(listPage, "from('pipeline_runs')", 'runs page pipeline query');
  assertIncludes(listPage, 'Execution Feed', 'runs page execution feed section');
  assertIncludes(listPage, 'Recent Runs', 'runs page summary metrics');
  assertIncludes(listPage, '—', 'legacy metric placeholder');
  assertNotIncludes(listPage, 'translateY(-1px)', 'lift hover transform');

  const detailPage = read('frontend/src/pages/admin/pipeline-runs/[runId].astro');
  assertIncludes(detailPage, "from('pipeline_logs')", 'detail page logs query');
  assertIncludes(detailPage, 'Run Snapshot', 'detail page summary hero');
  assertIncludes(detailPage, 'Reuse Signals', 'detail page reuse signals section');
  assertIncludes(detailPage, 'Run mode', 'detail page run mode metric');
  assertIncludes(detailPage, 'Reused candidates', 'detail page reused candidates signal');
  assertIncludes(detailPage, 'Resumed saved EN', 'detail page saved EN signal');
  assertIncludes(detailPage, 'Stage Timeline', 'detail page timeline title');
  assertNotIncludes(detailPage, 'Partial Artifacts', 'detail page should not have artifact section (v4)');
  assertNotIncludes(detailPage, 'pipeline_artifacts', 'detail page should not query artifacts (v4)');
  assertIncludes(detailPage, '<details', 'detail page collapsible debug panels');
  assertIncludes(detailPage, '—', 'detail legacy metric placeholder');
  assertIncludes(detailPage, 'raw_error', 'detail page raw error area');
  assertIncludes(detailPage, 'debug_meta', 'detail page debug metadata rendering');
  assertNotIncludes(detailPage, '(log.tokens_used ?? 0).toLocaleString()', 'forced zero tokens rendering');
  assertNotIncludes(detailPage, 'String(log.cost_usd ?? 0)', 'forced zero cost rendering');

  console.log('admin-pipeline-runs-structure.test: ok');
}

run();
