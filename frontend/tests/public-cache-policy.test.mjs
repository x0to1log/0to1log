import assert from 'node:assert/strict';
import {
  getPublicCacheTags,
  resolvePublicCachePolicy,
} from '../src/lib/server/publicCachePolicy.ts';

const list = resolvePublicCachePolicy({ kind: 'list', preview: false, hasError: false });
assert.equal(list.cacheControl, 'public, max-age=0, must-revalidate');
assert.equal(
  list.vercelCacheControl,
  'public, s-maxage=300, stale-while-revalidate=3600, stale-if-error=86400',
);
// Vercel never caches a response that varies on Cookie (high-cardinality header),
// which silently disabled the CDN from 2026-08 until this fix.
assert.equal(list.vary, undefined);

const detail = resolvePublicCachePolicy({ kind: 'detail', preview: false, hasError: false });
assert.equal(
  detail.vercelCacheControl,
  'public, s-maxage=3600, stale-while-revalidate=86400, stale-if-error=604800',
);
assert.equal(detail.vary, undefined);

const preview = resolvePublicCachePolicy({ kind: 'detail', preview: true, hasError: false });
assert.equal(preview.cacheControl, 'private, no-store');
assert.equal(preview.vercelCacheControl, 'private, no-store');

const errorPolicy = resolvePublicCachePolicy({ kind: 'list', preview: false, hasError: true });
assert.equal(errorPolicy.cacheControl, 'no-store');
assert.equal(errorPolicy.vercelCacheControl, 'no-store');

assert.deepEqual(getPublicCacheTags('/ko/news/some-slug/'), ['public', 'news']);
assert.deepEqual(getPublicCacheTags('/en/handbook/category/llm/'), ['public', 'handbook']);
assert.deepEqual(getPublicCacheTags('/en/blog/'), ['public', 'blog']);
assert.deepEqual(getPublicCacheTags('/ko/products/x/'), ['public', 'products']);
assert.deepEqual(getPublicCacheTags('/ko/'), ['public', 'home']);
assert.deepEqual(getPublicCacheTags('/en/about/'), ['public', 'pages']);
assert.deepEqual(getPublicCacheTags('/ko/rss.xml'), ['public', 'news']);

console.log('public-cache-policy.test.mjs passed');
