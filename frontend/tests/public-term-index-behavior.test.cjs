const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const ts = require('typescript');

async function load() {
  const source = fs.readFileSync(require('node:path').join(__dirname, '../src/lib/pageData/publicTermIndex.ts'), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
}

function database(rows, bodies = [], failAt = 0) {
  const calls = [];
  return {
    calls,
    from(table) {
      const call = { table };
      calls.push(call);
      const query = {
        select(columns) { call.columns = columns; return query; },
        eq(field, value) { call.filter = [field, value]; return query; },
        in(field, values) { call.ids = [field, values]; return query; },
        order() { return query; },
        limit(value) { call.limit = value; return query; },
        then(resolve, reject) {
          const isBodies = /basic_plain/.test(call.columns || '');
          return Promise.resolve(calls.length === failAt
            ? { data: null, error: { message: 'temporary failure' } }
            : { data: isBodies ? bodies : rows, error: null }).then(resolve, reject);
        },
      };
      return query;
    },
  };
}

// The index fed every detail-page render; with summaries and full basic
// bodies it was ~700 KB per call and exhausted Supabase egress (2026-10).
test('index selects only linkification columns', async () => {
  const { fetchPublicTermIndex } = await load();
  const db = database([{ term: 'A', slug: 'a', korean_name: '에이' }]);
  const rows = await fetchPublicTermIndex(db, 'ko');
  assert.equal(db.calls[0].columns, 'term, slug, korean_name');
  assert.deepEqual(rows, [{ term: 'A', slug: 'a', korean_name: '에이' }]);
});

test('warm and simultaneous requests reuse data but locales and clients stay isolated', async () => {
  const { fetchPublicTermIndex } = await load();
  const db = database([{ term: 'A', slug: 'a', korean_name: null }]);
  const [a, b] = await Promise.all([fetchPublicTermIndex(db, 'ko'), fetchPublicTermIndex(db, 'ko')]);
  a[0].term = 'changed by caller';
  assert.equal(b[0].term, 'A');
  await fetchPublicTermIndex(db, 'ko');
  assert.equal(db.calls.length, 1);
  await fetchPublicTermIndex(db, 'en');
  await fetchPublicTermIndex(db, 'ko', 10);
  assert.equal(db.calls.length, 3);
  const other = database([]);
  await fetchPublicTermIndex(other, 'ko');
  assert.equal(other.calls.length, 1);
});

test('expired entries refresh; database failures are not cached', async () => {
  const { fetchPublicTermIndex } = await load();
  const db = database([]);
  const original = Date.now;
  let now = original();
  Date.now = () => now;
  try {
    await fetchPublicTermIndex(db, 'ko');
    now += 300001;
    await fetchPublicTermIndex(db, 'ko');
    assert.equal(db.calls.length, 2);
  } finally { Date.now = original; }
  const failed = database([{ term: 'A', slug: 'a', korean_name: null }], [], 1);
  assert.deepEqual(await fetchPublicTermIndex(failed, 'ko'), []);
  assert.equal((await fetchPublicTermIndex(failed, 'ko')).length, 1);
});

test('popups query only referenced slugs; missing summaries get a short body excerpt', async () => {
  const { fetchTermPopups } = await load();
  const db = database([
    { term: 'A', slug: 'a', korean_name: null, term_full: null, categories: null, summary: 'Short summary', definition: 'Def A' },
    { term: 'B', slug: 'b', korean_name: '비', term_full: 'Bee', categories: ['x'], summary: '  ', definition: 'Def B' },
  ], [{ slug: 'b', basic_plain: '## Intro\n\nFriendly explanation\n\n## Details\n' + 'x'.repeat(5000) }]);
  const html = '<span class="handbook-term" data-slug="a">A</span> <a href="/ko/handbook/b/">B</a> <a href="/ko/handbook/category/llm-genai/">c</a>';
  const popups = await fetchTermPopups(db, 'ko', [html, null]);
  assert.deepEqual(db.calls[0].ids, ['slug', ['a', 'b']]);
  assert.match(db.calls[0].columns, /summary:summary_ko, definition:definition_ko/);
  assert.doesNotMatch(db.calls[0].columns, /body_basic/);
  assert.deepEqual(db.calls[1].ids, ['slug', ['b']]);
  assert.equal(popups.a.summary, 'Short summary');
  assert.equal(popups.a.basic_plain, '');
  assert.equal(popups.b.basic_plain, 'Friendly explanation');
  assert.equal(popups.b.korean_name, '비');
});

test('popups skip the query when nothing is linked, exclude the current term, and never throw', async () => {
  const { fetchTermPopups } = await load();
  const empty = database([]);
  assert.deepEqual(await fetchTermPopups(empty, 'en', ['<p>no terms</p>']), {});
  assert.equal(empty.calls.length, 0);

  const self = database([]);
  await fetchTermPopups(self, 'en', ['<span data-slug="rlhf"></span><span data-slug="ppo"></span>'], 'rlhf');
  assert.deepEqual(self.calls[0].ids, ['slug', ['ppo']]);

  const failing = database([], [], 1);
  assert.deepEqual(await fetchTermPopups(failing, 'en', ['<span data-slug="a"></span>']), {});
});

test('long first sections are bounded', async () => {
  const { fetchTermPopups } = await load();
  const db = database(
    [{ term: 'B', slug: 'b', summary: null }],
    [{ slug: 'b', basic_plain: 'x'.repeat(5000) }],
  );
  const popups = await fetchTermPopups(db, 'ko', ['<span data-slug="b"></span>']);
  assert.ok(popups.b.basic_plain.length <= 1201);
});
