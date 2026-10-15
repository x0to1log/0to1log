// frontend/tests/home-front-select.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { kstDay, selectFrontPage, termIndex, frontKeyword } = await import(pathToFileURL(path.join(here, '../src/lib/homeFront.js')).href);

assert.equal(kstDay('2026-10-14T00:00:00Z'), '2026-10-14');
assert.equal(kstDay('2026-10-13T15:30:00Z'), '2026-10-14'); // KST 00:30
assert.equal(kstDay(null), null);

const NOW = new Date('2026-10-14T12:00:00+09:00');
const news = [
  { slug: 'a', post_type: 'business', published_at: '2026-10-14T00:00:00Z', tags: ['Google', 'Gemini 4 Argon', 'LLM'] },
  { slug: 'b', post_type: 'research', published_at: '2026-10-14T00:00:00Z', tags: [] },
  { slug: 'c', post_type: 'business', published_at: '2026-09-27T00:00:00Z', tags: ['Microsoft'] },
  { slug: 'd', post_type: 'research', published_at: '2026-09-27T00:00:00Z', tags: null },
  { slug: 'e', post_type: 'business', published_at: '2026-09-26T00:00:00Z', tags: [] },
];

// 오늘 기사 2건: 1면 a, 같은 날 다른 유형 b, 지난 지면은 그보다 이른 기사 2건
let r = selectFrontPage({ news, now: NOW });
assert.equal(r.lead.slug, 'a');
assert.equal(r.leadIsToday, true);
assert.equal(r.sibling.slug, 'b');
assert.deepEqual(r.earlier.map((n) => n.slug), ['c', 'd']);
assert.equal(r.todayCount, 2);
assert.deepEqual(r.keyword, { small: 'Google', big: 'Gemini 4 Argon' });

// 오늘 기사가 없으면: 1면은 가장 최근 기사, leadIsToday false
r = selectFrontPage({ news: news.slice(2), now: NOW });
assert.equal(r.lead.slug, 'c');
assert.equal(r.leadIsToday, false);
assert.equal(r.sibling.slug, 'd');
assert.deepEqual(r.earlier.map((n) => n.slug), ['e']);
assert.equal(r.todayCount, 0);

// 같은 날이라도 유형이 같으면 짝 기사가 아님
r = selectFrontPage({ news: [news[0], { ...news[1], post_type: 'business' }], now: NOW });
assert.equal(r.sibling, null);

// 다른 날 기사는 짝 기사가 아님
r = selectFrontPage({ news: [news[0], news[2]], now: NOW });
assert.equal(r.sibling, null);
assert.deepEqual(r.earlier.map((n) => n.slug), ['c']);

// 키워드 판 규칙: 태그 2개 이상 / 1개 / 없음(→ KST 날짜 MM.DD)
assert.deepEqual(frontKeyword(news[0]), { small: 'Google', big: 'Gemini 4 Argon' });
assert.deepEqual(frontKeyword(news[2]), { small: null, big: 'Microsoft' });
assert.deepEqual(frontKeyword(news[1]), { small: null, big: '10.14' });
assert.deepEqual(frontKeyword(news[3]), { small: null, big: '09.27' });
assert.deepEqual(frontKeyword({ ...news[0], tags: ['  ', 'Gemini'] }), { small: null, big: 'Gemini' }); // 빈 태그는 무시
assert.equal(frontKeyword({ slug: 'x', published_at: null, tags: [] }), null);
assert.equal(frontKeyword(null), null);

// 오늘의 용어 인덱스: 호수 % 개수
assert.equal(termIndex(new Date('2026-10-14T12:00:00+09:00'), 3), 1); // 제211호, 211 % 3 = 1
assert.equal(termIndex(new Date('2026-10-14T23:00:00+09:00'), 3), 1); // same KST day
assert.equal(termIndex(new Date('2026-10-15T12:00:00+09:00'), 3), 2); // next day
assert.equal(termIndex(new Date('2026-10-14T12:00:00+09:00'), 0), null);

// term은 그대로 통과
const picked = { slug: 'rag' };
assert.equal(selectFrontPage({ news, term: picked, now: NOW }).term, picked);
assert.equal(selectFrontPage({ news, now: NOW }).term, null);

// 빈 입력
r = selectFrontPage({ news: [], now: new Date() });
assert.deepEqual(r, { lead: null, leadIsToday: false, sibling: null, earlier: [], todayCount: 0, term: null, keyword: null });

console.log('home-front-select.test.mjs passed');
