// frontend/tests/news-desks-select.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { buildDeskRows, deskDateParts, deskDayRange, addListBreaks, recentCutoff, monthLabel, RECENT_DAYS } = await import(pathToFileURL(path.join(here, '../src/lib/newsDesks.js')).href);

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

// KST 하루 범위 (짝 기사 쿼리용)
assert.deepEqual(deskDayRange('2026-10-15'), { start: '2026-10-14T15:00:00.000Z', end: '2026-10-15T15:00:00.000Z' });
assert.equal(deskDayRange(null), null);
assert.equal(deskDayRange('bad'), null);
assert.equal(deskDayRange('2026-13-40'), null);

// --- addListBreaks: 달 구분과 최근/이전 ---
const dayEntry = (day) => ({ kind: 'day', day, showDate: true, isToday: false, business: { slug: `b-${day}` }, research: null });
const pad = (n) => String(n).padStart(2, '0');

// 빈 입력
assert.deepEqual(addListBreaks([]), []);

// 한 달 안, 14일 이하 → 달 구분 없음, 전부 최근
let listed = addListBreaks([dayEntry('2026-11-21'), dayEntry('2026-11-20')]);
assert.deepEqual(listed.map((e) => [e.kind, e.older]), [['day', false], ['day', false]]);

// 달이 바뀌는 첫 항목 앞에 month 항목. 가장 최근 달 앞에는 없다
listed = addListBreaks([dayEntry('2026-11-13'), dayEntry('2026-10-27'), dayEntry('2026-10-26'), dayEntry('2026-09-30')]);
assert.deepEqual(listed.map((e) => (e.kind === 'month' ? `month:${e.month}` : e.day)), [
  '2026-11-13', 'month:2026-10', '2026-10-27', '2026-10-26', 'month:2026-09', '2026-09-30',
]);

// 해가 바뀌는 경우
listed = addListBreaks([dayEntry('2027-01-02'), dayEntry('2026-12-31')]);
assert.deepEqual(listed.map((e) => (e.kind === 'month' ? `month:${e.month}` : e.day)), ['2027-01-02', 'month:2026-12', '2026-12-31']);

// 최근/이전 경계: recentCutoff가 정한 날까지가 최근이다. month 항목은 뒤따르는 항목의 older를 따른다
const twenty = Array.from({ length: 20 }, (_, i) => dayEntry(i < 10 ? `2026-11-${pad(21 - i)}` : `2026-10-${pad(40 - i)}`));
const cutoff = recentCutoff(twenty.map((e) => e.day));
assert.ok(typeof cutoff === 'string' && twenty.some((e) => e.day === cutoff), 'cutoff is one of the listed days');
listed = addListBreaks(twenty);
for (const e of listed.filter((x) => x.kind === 'day')) assert.equal(e.older, e.day < cutoff, `older flag for ${e.day}`);
const firstOctober = listed.findIndex((e) => e.kind === 'month');
assert.equal(listed[firstOctober].older, listed[firstOctober + 1].older, 'month marker follows the entry after it');
assert.ok(listed.some((e) => e.older) && listed.some((e) => !e.older), '20 days: some shown, some folded');

// 접힌 구간 안에서 달이 바뀌면 그 month 항목도 접힌다
const longRun = Array.from({ length: RECENT_DAYS + 12 }, (_, i) => dayEntry(i < 20 ? `2026-11-${pad(21 - i)}` : `2026-10-${pad(51 - i)}`));
listed = addListBreaks(longRun);
const foldedMonth = listed.find((e) => e.kind === 'month');
assert.deepEqual([foldedMonth.month, foldedMonth.older], ['2026-10', true], 'a month divider inside the folded part is folded too');

// 같은 날의 주간 정리와 날짜 줄은 같은 쪽에 놓인다
listed = addListBreaks([{ kind: 'weekly', day: '2026-11-15', post: { slug: 'w' } }, dayEntry('2026-11-15')]);
assert.equal(listed[0].older, listed[1].older);

// 입력을 바꾸지 않는다
const frozen = [Object.freeze(dayEntry('2026-11-21'))];
addListBreaks(frozen);
assert.equal('older' in frozen[0], false);

assert.equal(Number.isInteger(RECENT_DAYS) && RECENT_DAYS > 0, true);
assert.equal(recentCutoff([]), null);

// --- monthLabel ---
assert.equal(monthLabel('2026-10', 'ko'), '2026년 10월');
assert.equal(monthLabel('2026-10', 'en'), 'October 2026');
assert.equal(monthLabel('2027-01', 'ko'), '2027년 1월');
console.log('news-desks-select.test.mjs passed');
