// frontend/tests/news-desks-select.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { buildDeskRows, deskDateParts } = await import(pathToFileURL(path.join(here, '../src/lib/newsDesks.js')).href);

const NOW = new Date('2026-10-15T12:00:00+09:00');
const p = (slug, post_type, published_at) => ({ slug, post_type, published_at });

// 2:2, 오늘 표시, KST 날짜 내림차순, 입력 순서 무관
let rows = buildDeskRows([
  p('r14', 'research', '2026-10-14T00:00:00+00:00'),
  p('b15', 'business', '2026-10-15T00:00:00+00:00'),
  p('r15', 'research', '2026-10-15T00:00:00+00:00'),
  p('b14', 'business', '2026-10-14T00:00:00+00:00'),
], NOW);
assert.deepEqual(rows.map((r) => [r.kind, r.day, r.showDate, r.isToday, r.business?.slug ?? null, r.research?.slug ?? null]), [
  ['day', '2026-10-15', true, true, 'b15', 'r15'],
  ['day', '2026-10-14', true, false, 'b14', 'r14'],
]);

// KST 경계: 2026-10-14T15:30Z = 10월 15일 00:30 KST
rows = buildDeskRows([p('late', 'business', '2026-10-14T15:30:00+00:00')], NOW);
assert.equal(rows[0].day, '2026-10-15');

// 2:1 → 같은 날 두 줄, 둘째 줄은 날짜 숨김, 짝 없는 쪽 null. 같은 유형은 최신이 먼저
rows = buildDeskRows([
  p('b-early', 'business', '2026-09-22T00:00:00+00:00'),
  p('b-late', 'business', '2026-09-22T06:00:00+00:00'),
  p('r', 'research', '2026-09-22T00:00:00+00:00'),
], NOW);
assert.deepEqual(rows.map((r) => [r.showDate, r.business?.slug ?? null, r.research?.slug ?? null]), [
  [true, 'b-late', 'r'],
  [false, 'b-early', null],
]);

// 0:1 → 비즈니스 칸 null
rows = buildDeskRows([p('only-r', 'research', '2026-09-21T00:00:00+00:00')], NOW);
assert.equal(rows[0].business, null);
assert.equal(rows[0].research.slug, 'only-r');

// 주간 정리는 같은 날 day row보다 앞
rows = buildDeskRows([
  p('b20', 'business', '2026-09-20T00:00:00+00:00'),
  p('w20', 'weekly', '2026-09-20T00:00:00+00:00'),
  p('r20', 'research', '2026-09-20T00:00:00+00:00'),
], NOW);
assert.deepEqual(rows.map((r) => [r.kind, r.kind === 'weekly' ? r.post.slug : r.business.slug]), [
  ['weekly', 'w20'],
  ['day', 'b20'],
]);

// 주간 정리만 있는 날은 day row가 없다
rows = buildDeskRows([p('w13', 'weekly', '2026-09-13T00:00:00+00:00')], NOW);
assert.deepEqual(rows.map((r) => r.kind), ['weekly']);

// null published_at 제외, 알 수 없는 유형은 비즈니스 칸
rows = buildDeskRows([p('nodate', 'business', null), p('odd', 'opinion', '2026-09-19T00:00:00+00:00')], NOW);
assert.equal(rows.length, 1);
assert.equal(rows[0].business.slug, 'odd');

assert.deepEqual(buildDeskRows([], NOW), []);

// 날짜 표기
const ko = deskDateParts('2026-10-15', 'ko');
assert.equal(ko.short, '10.15');
assert.equal(ko.issue, '제212호');
assert.equal(ko.weekday, '목');
const en = deskDateParts('2026-09-20', 'en');
assert.equal(en.short, '09.20');
assert.equal(en.issue, 'No. 187');
assert.equal(en.weekday, 'Sun');

console.log('news-desks-select.test.mjs passed');
