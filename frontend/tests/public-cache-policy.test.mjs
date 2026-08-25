import assert from 'node:assert/strict';
import { resolvePublicCachePolicy } from '../src/lib/server/publicCachePolicy.ts';

const anonymousList = resolvePublicCachePolicy({
  kind: 'list',
  authenticated: false,
  preview: false,
  hasError: false,
});
assert.equal(anonymousList.cacheControl, 'public, max-age=0, must-revalidate');
assert.equal(
  anonymousList.vercelCacheControl,
  'public, s-maxage=300, stale-while-revalidate=3600, stale-if-error=86400',
);
assert.equal(anonymousList.vary, 'Cookie');

const anonymousDetail = resolvePublicCachePolicy({
  kind: 'detail',
  authenticated: false,
  preview: false,
  hasError: false,
});
assert.equal(
  anonymousDetail.vercelCacheControl,
  'public, s-maxage=3600, stale-while-revalidate=86400, stale-if-error=604800',
);

for (const input of [
  { kind: 'list', authenticated: true, preview: false, hasError: false },
  { kind: 'detail', authenticated: false, preview: true, hasError: false },
]) {
  const policy = resolvePublicCachePolicy(input);
  assert.equal(policy.cacheControl, 'private, no-store');
  assert.equal(policy.vercelCacheControl, 'private, no-store');
  assert.equal(policy.vary, undefined);
}

const errorPolicy = resolvePublicCachePolicy({
  kind: 'list',
  authenticated: false,
  preview: false,
  hasError: true,
});
assert.equal(errorPolicy.cacheControl, 'no-store');
assert.equal(errorPolicy.vercelCacheControl, 'no-store');

console.log('public-cache-policy.test.mjs passed');
