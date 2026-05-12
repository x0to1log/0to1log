const path = require('path');
const { pathToFileURL } = require('url');

const root = path.resolve(__dirname, '..');

async function run() {
  const { fetchPipelineLogsForRuns } = await import(
    pathToFileURL(path.join(root, 'src/lib/admin/pipelineRunLogs.js')).href
  );

  const pages = [
    Array.from({ length: 1000 }, (_, i) => ({ run_id: 'run-1', pipeline_type: `stage-${i}` })),
    Array.from({ length: 1000 }, (_, i) => ({ run_id: 'run-1', pipeline_type: `stage-${i + 1000}` })),
    Array.from({ length: 5 }, (_, i) => ({ run_id: 'run-1', pipeline_type: `stage-${i + 2000}` })),
  ];
  const ranges = [];
  const orders = [];
  let fromCalls = 0;

  const sb = {
    from(table) {
      fromCalls += 1;
      if (table !== 'pipeline_logs') {
        throw new Error(`Unexpected table: ${table}`);
      }
      return {
        select(columns) {
          if (!columns.includes('pipeline_type')) {
            throw new Error('pipeline_type must be selected');
          }
          return {
            in(column, ids) {
              if (column !== 'run_id') {
                throw new Error(`Unexpected in() column: ${column}`);
              }
              if (ids.length !== 2 || ids[0] !== 'run-1' || ids[1] !== 'run-2') {
                throw new Error(`Unexpected run ids: ${ids.join(',')}`);
              }
              return {
                order(column, options) {
                  orders.push([column, options?.ascending]);
                  return {
                    range(from, to) {
                      ranges.push([from, to]);
                      const pageIndex = ranges.length - 1;
                      return Promise.resolve({ data: pages[pageIndex] ?? [] });
                    },
                  };
                },
              };
            },
          };
        },
      };
    },
  };

  const logs = await fetchPipelineLogsForRuns(sb, ['run-1', 'run-2']);

  if (logs.length !== 2005) {
    throw new Error(`Expected all paginated logs, got ${logs.length}`);
  }
  const expectedRanges = JSON.stringify([[0, 999], [1000, 1999], [2000, 2999]]);
  if (JSON.stringify(ranges) !== expectedRanges) {
    throw new Error(`Unexpected ranges: ${JSON.stringify(ranges)}`);
  }
  const expectedOrders = JSON.stringify([
    ['created_at', true],
    ['created_at', true],
    ['created_at', true],
  ]);
  if (JSON.stringify(orders) !== expectedOrders) {
    throw new Error(`Unexpected ordering: ${JSON.stringify(orders)}`);
  }

  const emptyLogs = await fetchPipelineLogsForRuns(sb, []);
  if (emptyLogs.length !== 0) {
    throw new Error('Expected empty run list to return no logs');
  }
  if (fromCalls !== 3) {
    throw new Error(`Expected no query for empty run list, from() calls=${fromCalls}`);
  }

  console.log('pipeline-run-logs-pagination.test: ok');
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
