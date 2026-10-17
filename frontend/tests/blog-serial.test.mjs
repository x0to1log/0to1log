// frontend/tests/blog-serial.test.mjs
// Blog list A (serial column): latest post, series per main field, episode order, short notes, KST dates.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { buildBlogFront, normalizeBlogCategory, formatBlogDate } = await import(
  pathToFileURL(path.join(here, '../src/lib/blogSerial.js')).href
);

// tech -> study, same rule as normalizeCategorySlug() in lib/categories.ts (node cannot import the .ts module)
assert.equal(normalizeBlogCategory('tech'), 'study');
assert.equal(normalizeBlogCategory('project'), 'project');
assert.equal(normalizeBlogCategory(null), null);
assert.equal(normalizeBlogCategory(''), null);
const categoriesTs = fs.readFileSync(path.join(here, '../src/lib/categories.ts'), 'utf8');
assert(
  categoriesTs.includes("return category === 'tech' ? 'study' : category;"),
  'lib/categories.ts normalizeCategorySlug changed: update normalizeBlogCategory in lib/blogSerial.js too',
);

const cat = (slug, group_slug, sort_order, extra = {}) => ({
  slug, group_slug, sort_order, is_visible: true, label_ko: slug, label_en: slug, ...extra,
});
// scrambled on purpose: series order must come from sort_order, not input order
const CATS = [
  cat('project', 'main', 1),
  cat('work-note', 'sub', 0),
  cat('study', 'main', 0),
  cat('career', 'main', 2),
  cat('daily', 'sub', 1),
  cat('secret', 'main', 3, { is_visible: false }),
  cat('hidden-note', 'sub', 2, { is_visible: false }),
  cat('archive', 'legacy', 0),
];
const post = (title, category, published_at) => ({ id: `id-${title}`, title, slug: title, category, published_at });
const POSTS = [
  post('note', 'work-note', '2026-03-11T15:26:58.354+00:00'),
  post('llm', 'tech', '2026-03-10T18:42:39.552+00:00'),
  post('cost', 'study', '2026-03-11T04:32:08.018+00:00'),
  post('undated', 'study', null),
  post('solo', 'project', '2026-03-10T09:42:35.438+00:00'),
  post('routine', 'project', '2026-03-10T09:37:44.626+00:00'),
  post('hidden-main', 'secret', '2026-03-12T00:00:00+00:00'),
  post('old', 'archive', '2026-03-09T00:00:00+00:00'),
  post('unknown', 'ghost', '2026-03-08T00:00:00+00:00'),
  post('walk', 'daily', '2026-03-01T00:00:00+00:00'),
  post('nocat', null, '2026-03-13T00:00:00+00:00'),
  post('hidden-sub', 'hidden-note', '2026-03-07T00:00:00+00:00'),
  post('broken-date', 'study', 'not a date'),
];
const titles = (list) => list.map((p) => p.title);

const front = buildBlogFront(POSTS, CATS);

// lead: newest published_at of all posts (any field); undated/invalid never lead
assert.equal(front.lead.title, 'nocat');
assert.equal(front.latestAt, '2026-03-13T00:00:00+00:00');
assert.equal(front.total, 13);

// series: visible main fields with posts, by sort_order (career has no posts, secret is hidden)
assert.deepEqual(front.series.map((s) => s.category.slug), ['study', 'project']);
// episodes: published_at ascending, undated last (input order kept among them)
assert.deepEqual(titles(front.series[0].posts), ['llm', 'cost', 'undated', 'broken-date']);
assert.deepEqual(titles(front.series[1].posts), ['routine', 'solo']);
assert.equal(front.series[0].posts[0].category, 'study', 'legacy tech post is normalized into the study series');
assert.equal(POSTS[1].category, 'tech', 'input posts are not mutated');

// short notes: visible sub fields (newest first), then everything else (newest first):
// hidden fields of any group, other groups, slugs missing from the DB, posts without a category
assert.deepEqual(titles(front.shortNotes), ['note', 'walk', 'nocat', 'hidden-main', 'old', 'unknown', 'hidden-sub']);
const placed = front.series.reduce((n, s) => n + s.posts.length, 0) + front.shortNotes.length;
assert.equal(placed, front.total, 'every post is listed exactly once outside the lead');

// the lead stays in its own series (intended duplicate)
const leadInSeries = buildBlogFront([post('a', 'study', '2026-03-01T00:00:00Z'), post('b', 'study', '2026-03-02T00:00:00Z')], CATS);
assert.equal(leadInSeries.lead.title, 'b');
assert.deepEqual(titles(leadInSeries.series[0].posts), ['a', 'b']);

// posts exist but none has published_at -> lead/latestAt null while total > 0 (the page guards with `front.lead &&`)
const undatedOnly = buildBlogFront([post('x', 'study', null)], CATS);
assert.equal(undatedOnly.lead, null);
assert.equal(undatedOnly.latestAt, null);
assert.equal(undatedOnly.total, 1);
assert.deepEqual(titles(undatedOnly.series[0].posts), ['x']);

// empty input
const empty = { lead: null, series: [], shortNotes: [], total: 0, latestAt: null };
assert.deepEqual(buildBlogFront([], []), empty);
assert.deepEqual(buildBlogFront(null, null), empty);
assert.deepEqual(titles(buildBlogFront([post('lone', 'study', null)], []).shortNotes), ['lone'], 'no categories: everything is a short note');

// KST dates: 18:42 UTC on Mar 10 is Mar 11 in Seoul
assert.equal(formatBlogDate('2026-03-10T18:42:39.552+00:00', 'ko'), '3월 11일');
assert.equal(formatBlogDate('2026-03-10T18:42:39.552+00:00', 'en'), 'Mar 11');
assert.equal(formatBlogDate('2026-03-10T09:42:35.438+00:00', 'ko'), '3월 10일');
assert.equal(formatBlogDate(null, 'ko'), '');
assert.equal(formatBlogDate('not a date', 'en'), '');

console.log('blog-serial.test.mjs passed');
