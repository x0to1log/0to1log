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

function run() {
  const adminIndex = read('frontend/src/pages/admin/index.astro');
  assertIncludes(adminIndex, '/admin/pipeline-runs', 'dashboard pipeline runs link');

  const sidebar = read('frontend/src/components/admin/AdminSidebar.astro');
  assertIncludes(sidebar, 'Pipeline Runs', 'sidebar pipeline runs navigation');

  const listPage = read('frontend/src/pages/admin/pipeline-runs/index.astro');
  assertIncludes(listPage, 'Pipeline Runs', 'runs page heading');
  assertIncludes(listPage, "from('pipeline_runs')", 'runs page pipeline query');

  const detailPage = read('frontend/src/pages/admin/pipeline-runs/[runId].astro');
  assertIncludes(detailPage, "from('pipeline_logs')", 'detail page logs query');
  assertIncludes(detailPage, 'raw_error', 'detail page raw error area');
  assertIncludes(detailPage, 'debug_meta', 'detail page debug metadata rendering');

  console.log('admin-pipeline-runs-structure.test: ok');
}

run();
