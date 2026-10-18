// frontend/tests/blog-serial.test.mjs
// Blog list A (serial column): latest post, series per main field, episode order, short notes, KST dates.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { buildBlogFront, normalizeBlogCategory, formatBlogDate, locatePost, toSerialProps, categoryPage } = await import(
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

// --- blog post page (A: one column): where a post sits, serial props, dates with the year ---
const SERIAL_CATS = [
  cat('study', 'main', 0, { label_ko: '학습 노트', label_en: 'Study Notes', color: '#6E9682' }),
  cat('project', 'main', 1),
  cat('work-note', 'sub', 0, { label_ko: '작업 메모', label_en: 'Work Notes' }),
  cat('secret-note', 'sub', 1, { is_visible: false }),
];
// created_at desc order on purpose (like the query); timeline oldest first: s1, p1, s2, note-a, s3
const SERIAL = [
  post('s3', 'study', '2026-03-12T00:00:00Z'),
  post('note-a', 'work-note', '2026-03-11T12:00:00Z'),
  post('s2', 'study', '2026-03-11T00:00:00Z'),
  post('p1', 'project', '2026-03-10T12:00:00Z'),
  post('s1', 'tech', '2026-03-10T00:00:00Z'),
  post('undated-note', 'work-note', null),
  post('hidden', 'secret-note', '2026-03-09T00:00:00Z'),
  post('lost', 'ghost', '2026-03-08T00:00:00Z'),
];
const NONE = { series: null, index: -1, prev: null, next: null };

// in a series: index + neighbouring episodes of the same series
const s2 = locatePost(SERIAL, SERIAL_CATS, 's2');
assert.equal(s2.series.category.slug, 'study');
assert.deepEqual(titles(s2.series.posts), ['s1', 's2', 's3']);
assert.equal(s2.index, 1);
assert.equal(s2.prev.title, 's1');
assert.equal(s2.next.title, 's3');
const s1 = locatePost(SERIAL, SERIAL_CATS, 's1');
assert.equal(s1.index, 0, 'legacy tech post is episode 1 of the study series');
assert.equal(s1.prev, null, 'first episode has no previous');
assert.equal(s1.next.title, 's2');
assert.equal(s1.series.posts[0].category, 'study');
assert.equal(locatePost(SERIAL, SERIAL_CATS, 's3').next, null, 'last episode has no next');
const p1 = locatePost(SERIAL, SERIAL_CATS, 'p1');
assert.deepEqual([p1.series.category.slug, p1.index, p1.prev, p1.next], ['project', 0, null, null], 'one-episode series');

// not in a series: neighbours among every dated post, episodes included, oldest first
const noteA = locatePost(SERIAL, SERIAL_CATS, 'note-a');
assert.equal(noteA.series, null);
assert.equal(noteA.index, -1);
assert.equal(noteA.prev.title, 's2');
assert.equal(noteA.next.title, 's3');
const hidden = locatePost(SERIAL, SERIAL_CATS, 'hidden');
assert.deepEqual([hidden.series, hidden.prev && hidden.prev.title, hidden.next && hidden.next.title], [null, 'lost', 's1'], 'hidden field: short note, timeline neighbours');
assert.deepEqual(locatePost(SERIAL, SERIAL_CATS, 'undated-note'), NONE, 'undated short note: no neighbours');
assert.deepEqual(locatePost(SERIAL, SERIAL_CATS, 'draft-preview'), NONE, 'slug missing from the list');
assert.deepEqual(locatePost(null, null, 's1'), NONE);
assert.equal(SERIAL[4].category, 'tech', 'input posts are not mutated');

// serial props (one builder for the ko/en pages)
assert.deepEqual(toSerialProps(s2, SERIAL_CATS, 'ko'), {
  categoryLabel: '학습 노트',
  categoryHref: '/ko/blog/category/study/',
  categoryColor: '#6E9682',
  episode: 2,
  total: 3,
  episodes: [{ title: 's1', slug: 's1' }, { title: 's2', slug: 's2' }, { title: 's3', slug: 's3' }],
  prev: { title: 's1', slug: 's1' },
  next: { title: 's3', slug: 's3' },
});
const s2en = toSerialProps(s2, SERIAL_CATS, 'en', 'study');
assert.deepEqual([s2en.categoryLabel, s2en.categoryHref], ['Study Notes', '/en/blog/category/study/']);
assert.deepEqual(toSerialProps(noteA, SERIAL_CATS, 'ko', 'work-note'), {
  categoryLabel: '작업 메모',
  categoryHref: '/ko/blog/category/work-note/',
  categoryColor: null,
  episode: null,
  total: null,
  episodes: [],
  prev: { title: 's2', slug: 's2' },
  next: { title: 's3', slug: 's3' },
});
const hiddenProps = toSerialProps(hidden, SERIAL_CATS, 'ko', 'secret-note');
assert.deepEqual([hiddenProps.categoryLabel, hiddenProps.categoryHref], ['secret-note', null], 'hidden field: label without a link');
const lostProps = toSerialProps(locatePost(SERIAL, SERIAL_CATS, 'lost'), SERIAL_CATS, 'ko', 'ghost');
assert.deepEqual([lostProps.categoryLabel, lostProps.categoryHref, lostProps.categoryColor], [null, null, null], 'field missing from the DB: no label');
const draftProps = toSerialProps(NONE, SERIAL_CATS, 'ko', 'tech');
assert.deepEqual(draftProps, {
  categoryLabel: '학습 노트',
  categoryHref: '/ko/blog/category/study/',
  categoryColor: '#6E9682',
  episode: null,
  total: null,
  episodes: [],
  prev: null,
  next: null,
}, 'draft preview: field from the post itself (tech → study), no series, no neighbours');

// byline dates: KST with the year; without the option the list format is unchanged (asserted above)
assert.equal(formatBlogDate('2026-03-10T18:42:39.552+00:00', 'ko', { year: true }), '2026년 3월 11일');
assert.equal(formatBlogDate('2026-03-10T18:42:39.552+00:00', 'en', { year: true }), 'Mar 11, 2026');
assert.equal(formatBlogDate('2025-12-31T16:00:00Z', 'en', { year: true }), 'Jan 1, 2026', 'the year rolls over in KST');
assert.equal(formatBlogDate(null, 'ko', { year: true }), '');

// --- blog field page A (series table of contents): categoryPage ---
const FIELD_CATS = [
  cat('study', 'main', 0),
  cat('project', 'main', 1),
  cat('career', 'main', 2),
  cat('work-note', 'sub', 0),
  cat('daily', 'sub', 1),
  cat('odd', 'legacy', 0),
  cat('loose', null, 0),
];
// created_at desc on purpose (like the query)
const FIELD = [
  post('w2', 'work-note', '2026-03-12T00:00:00Z'),
  post('st3', 'study', '2026-03-11T05:12:41Z'),
  post('w-undated', 'work-note', null),
  post('st2', 'study', '2026-03-11T04:32:08Z'),
  post('w1', 'work-note', '2026-03-05T00:00:00Z'),
  post('st1', 'tech', '2026-03-10T18:42:39Z'),
  post('p1', 'project', '2026-03-10T09:37:44Z'),
  post('o1', 'odd', '2026-03-09T00:00:00Z'),
  post('l1', 'loose', '2026-03-08T00:00:00Z'),
  post('nocat', null, '2026-03-07T00:00:00Z'),
];
// counted over every loaded post by normalized field (tech → study); posts without a field are not counted
const COUNTS = { 'work-note': 3, study: 3, project: 1, odd: 1, loose: 1 };

// series: the study entry of buildBlogFront (oldest first, legacy tech included), so episode = index + 1 matches the list page
const study = categoryPage(FIELD, FIELD_CATS, 'study');
assert.equal(study.kind, 'series');
assert.deepEqual(titles(study.posts), ['st1', 'st2', 'st3']);
assert.deepEqual(study.posts, buildBlogFront(FIELD, FIELD_CATS).series.find((s) => s.category.slug === 'study').posts, 'same episodes as the list page');
assert.equal(study.posts[0].category, 'study', 'legacy tech post is normalized into the study series');
assert.deepEqual(study.range, { first: '2026-03-10T18:42:39Z', last: '2026-03-11T05:12:41Z' });
assert.deepEqual(study.counts, COUNTS);
assert.equal(FIELD[5].category, 'tech', 'input posts are not mutated');

// main field without posts: still a series, empty list, no range
assert.deepEqual(categoryPage(FIELD, FIELD_CATS, 'career'), { kind: 'series', posts: [], range: null, counts: COUNTS });

// sub field: short notes, newest first, undated last
const workNotes = categoryPage(FIELD, FIELD_CATS, 'work-note');
assert.equal(workNotes.kind, 'notes');
assert.deepEqual(titles(workNotes.posts), ['w2', 'w1', 'w-undated']);
assert.deepEqual(workNotes.range, { first: '2026-03-05T00:00:00Z', last: '2026-03-12T00:00:00Z' }, 'range skips undated posts');
assert.deepEqual(categoryPage(FIELD, FIELD_CATS, 'daily'), { kind: 'notes', posts: [], range: null, counts: COUNTS });

// groups other than main (unknown or null): short notes
const odd = categoryPage(FIELD, FIELD_CATS, 'odd');
assert.deepEqual([odd.kind, titles(odd.posts)], ['notes', ['o1']]);
const loose = categoryPage(FIELD, FIELD_CATS, 'loose');
assert.deepEqual([loose.kind, titles(loose.posts)], ['notes', ['l1']]);

// range: one dated post → first = last; only undated posts → null
assert.deepEqual(categoryPage([post('a', 'work-note', '2026-03-01T00:00:00Z')], FIELD_CATS, 'work-note').range, { first: '2026-03-01T00:00:00Z', last: '2026-03-01T00:00:00Z' });
const undatedSeries = categoryPage([post('u', 'study', null)], FIELD_CATS, 'study');
assert.deepEqual([undatedSeries.kind, titles(undatedSeries.posts), undatedSeries.range], ['series', ['u'], null]);

// empty input
assert.deepEqual(categoryPage(null, null, 'study'), { kind: 'notes', posts: [], range: null, counts: {} });

console.log('blog-serial.test.mjs passed');
