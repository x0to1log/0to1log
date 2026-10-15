// frontend/tests/post-type-label.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { postTypeLabel } = await import(pathToFileURL(path.join(here, '../src/lib/postType.js')).href);

assert.equal(postTypeLabel('ko', 'business'), '비즈니스');
assert.equal(postTypeLabel('ko', 'research'), '리서치');
assert.equal(postTypeLabel('ko', 'weekly'), '주간 정리');
assert.equal(postTypeLabel('en', 'business'), 'Business');
assert.equal(postTypeLabel('en', 'research'), 'Research');
assert.equal(postTypeLabel('en', 'weekly'), 'Weekly');
assert.equal(postTypeLabel('ko', null), '');
assert.equal(postTypeLabel('ko', 'unknown'), '');
console.log('post-type-label.test.mjs passed');
