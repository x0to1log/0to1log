const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
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
  const sidebar = read('src/components/admin/AdminSidebar.astro');
  assertIncludes(sidebar, 'href="/admin/pipeline-runs"', 'sidebar pipeline runs link');
  assertIncludes(sidebar, 'Pipeline Runs', 'sidebar pipeline runs navigation');
  assertOrdered(
    sidebar,
    [
      '<span>Dashboard</span>',
      '<span>Pipeline Runs</span>',
      '<span>Pipeline Costs</span>',
      '<span>Site Analytics</span>',
      '<span>News</span>',
      '<span>Handbook</span>',
      '<span>Blog</span>',
      '<span>Products</span>',
      '<span>Webhooks</span>',
      '<span>Feedback</span>',
      '<span>Settings</span>',
    ],
    'admin sidebar navigation',
  );

  const listPage = read('src/pages/admin/pipeline-runs/index.astro');
  assertIncludes(listPage, 'Pipeline Runs', 'runs page heading');
  assertIncludes(listPage, "from('pipeline_runs')", 'runs page pipeline query');
  assertIncludes(listPage, 'fetchPipelineLogsForRuns', 'paginated pipeline logs fetch');
  assertIncludes(listPage, 'Execution Feed', 'runs page execution feed section');
  assertIncludes(listPage, 'Recent Runs', 'runs page summary metrics');
  assertNotIncludes(listPage, 'translateY(-1px)', 'lift hover transform');

  const detailPage = read('src/pages/admin/pipeline-runs/[runId].astro');
  assertIncludes(detailPage, "from('pipeline_logs')", 'detail page logs query');
  assertIncludes(detailPage, 'Run Snapshot', 'detail page summary hero');
  assertIncludes(detailPage, 'Run Mode', 'detail page run mode metric');
  assertIncludes(detailPage, 'Stage Timeline', 'detail page timeline title');
  assertIncludes(detailPage, '<details', 'detail page collapsible debug panels');
  assertIncludes(detailPage, 'raw_error', 'detail page raw error area');
  assertIncludes(detailPage, 'debug_meta', 'detail page debug metadata rendering');
  assertIncludes(detailPage, 'data-stage="beginner" data-category="research"', 'beginner research rerun option');
  assertIncludes(detailPage, 'Beginner only + QC: Both', 'beginner both rerun option');
  assertIncludes(detailPage, 'keeps expert/learner content intact', 'beginner rerun confirmation copy');
  assertIncludes(detailPage, 'data-stage="weekly-regen" data-persona="beginner"', 'weekly beginner regen option');
  assertIncludes(detailPage, 'Other persona versions stay intact.', 'weekly regen confirmation copy');
  assertIncludes(detailPage, 'data-stage="quiz" data-category="research"', 'quiz research rerun option');
  assertIncludes(detailPage, 'Quiz only: Both', 'quiz both rerun option');
  assertIncludes(detailPage, 'regenerates persona quizzes only', 'quiz rerun confirmation copy');
  assertNotIncludes(detailPage, 'Partial Artifacts', 'detail page should not have artifact section');
  assertNotIncludes(detailPage, 'pipeline_artifacts', 'detail page should not query artifacts');
  assertNotIncludes(detailPage, '(log.tokens_used ?? 0).toLocaleString()', 'forced zero tokens rendering');
  assertNotIncludes(detailPage, 'String(log.cost_usd ?? 0)', 'forced zero cost rendering');

  console.log('admin-pipeline-runs-structure.test: ok');
}

run();
