// frontend/tests/term-of-day.test.cjs
// Term of the day: one shared query (published count + one row by slug) for the home and the handbook index.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const tod = read('lib/pageData/termOfDay.ts');
assert(tod.includes('export async function fetchTermOfDay('), 'shared helper is exported');
assert(/extraColumns = ''/.test(tod), 'extra columns are optional');
assert(/count: 'exact', head: true/.test(tod), 'count is head-only');
assert(/termIndex\(now, total\)/.test(tod), 'index = issue number % published count (lib/homeFront.js)');
assert(/\.order\('slug', \{ ascending: true \}\)/.test(tod), 'stable order by slug');
assert(/\.range\(i, i\)/.test(tod) && /\.maybeSingle\(\)/.test(tod), 'single row');
assert(tod.includes('definition:${definitionField}'), 'only the locale definition column');
assert(/return \{ term: null, total: 0 \}/.test(tod), 'errors degrade to an empty result, never throw');

const home = read('lib/pageData/homeFrontPage.ts');
assert(/fetchTermOfDay\(supabase, locale, now\)/.test(home), 'home uses the shared term of the day');
assert(/Promise\.all\(\[[\s\S]*?fetchTermOfDay\(supabase, locale, now\)/.test(home), 'term of the day runs in parallel with the news query');
assert(!/from\('handbook_terms'\)/.test(home), 'home owns no term query');

console.log('term-of-day.test.cjs passed');
