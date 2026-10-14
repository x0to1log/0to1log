// frontend/tests/issue-number.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { ISSUE_EPOCH, issueNumber, issueLabel } = await import(pathToFileURL(path.join(here, '../src/lib/issue.js')).href);

assert.equal(ISSUE_EPOCH, '2026-03-18');

// 창간일 = 1호 (KST 기준)
assert.equal(issueNumber(new Date('2026-03-18T00:00:00+09:00')), 1);
assert.equal(issueNumber(new Date('2026-03-18T23:59:59+09:00')), 1);
assert.equal(issueNumber(new Date('2026-03-19T00:00:00+09:00')), 2);
// UTC로는 전날이어도 KST 날짜를 따른다
assert.equal(issueNumber(new Date('2026-03-18T15:30:00Z')), 2); // KST 3/19 00:30
assert.equal(issueNumber(new Date('2026-10-14T12:00:00+09:00')), 211);
// 창간일 이전 날짜는 1호로 고정
assert.equal(issueNumber(new Date('2026-01-01T12:00:00+09:00')), 1);
// 잘못된 날짜는 null
assert.equal(issueNumber(new Date('invalid')), null);

assert.equal(issueLabel('ko', 211), '제211호');
assert.equal(issueLabel('en', 211), 'No. 211');
assert.equal(issueLabel('ko', null), '');

console.log('issue-number.test.mjs passed');
