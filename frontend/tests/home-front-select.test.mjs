// frontend/tests/home-front-select.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { kstDay, selectFrontPage, termIndex } = await import(pathToFileURL(path.join(here, '../src/lib/homeFront.js')).href);

assert.equal(kstDay('2026-10-14T00:00:00Z'), '2026-10-14');
assert.equal(kstDay('2026-10-13T15:30:00Z'), '2026-10-14'); // KST 00:30
assert.equal(kstDay(null), null);

const news = [
  { slug: 'a', title: 'A', published_at: '2026-10-14T00:00:00Z' },
  { slug: 'b', title: 'B', published_at: '2026-10-14T00:00:00Z' },
  { slug: 'c', title: 'C', published_at: '2026-09-27T00:00:00Z' },
];
const terms = [{ slug: 'rag' }, { slug: 'bm25' }, { slug: 'agent' }];

// 오늘(KST) 기사 2건, 머리기사 a, 같은 날 한 줄 b
let r = selectFrontPage({ news, terms, now: new Date('2026-10-14T12:00:00+09:00') });
assert.equal(r.todayCount, 2);
assert.equal(r.lead.slug, 'a');
assert.equal(r.also.slug, 'b');

// 오늘 기사가 없으면 todayCount 0, 머리기사는 가장 최근 기사
r = selectFrontPage({ news: news.slice(2), terms, now: new Date('2026-10-14T12:00:00+09:00') });
assert.equal(r.todayCount, 0);
assert.equal(r.lead.slug, 'c');
assert.equal(r.also, null);

// 같은 날이 아니면 also 없음
r = selectFrontPage({ news: [news[0], news[2]], terms, now: new Date('2026-10-14T12:00:00+09:00') });
assert.equal(r.also, null);

// 오늘의 용어 인덱스: 호수 % 개수
assert.equal(termIndex(new Date('2026-10-14T12:00:00+09:00'), 3), 1); // 제211호, 211 % 3 = 1
assert.equal(termIndex(new Date('2026-10-14T23:00:00+09:00'), 3), 1); // same KST day
assert.equal(termIndex(new Date('2026-10-15T12:00:00+09:00'), 3), 2); // next day
assert.equal(termIndex(new Date('2026-10-14T12:00:00+09:00'), 0), null);

// term은 그대로 통과
const picked = { slug: 'rag' };
assert.equal(selectFrontPage({ news, term: picked, now: new Date('2026-10-14T12:00:00+09:00') }).term, picked);
assert.equal(selectFrontPage({ news, now: new Date('2026-10-14T12:00:00+09:00') }).term, null);

// 빈 입력
r = selectFrontPage({ news: [], now: new Date() });
assert.deepEqual(r, { lead: null, also: null, todayCount: 0, term: null });

console.log('home-front-select.test.mjs passed');
