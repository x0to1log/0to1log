import assert from 'node:assert/strict';
import { expandInvalidationTags, getAdminInvalidationTag } from '../src/lib/server/cacheInvalidation.ts';

assert.equal(getAdminInvalidationTag('/api/admin/posts/status', 'POST'), 'news');
assert.equal(getAdminInvalidationTag('/api/admin/weekly/regenerate', 'POST'), 'news');
assert.equal(getAdminInvalidationTag('/api/admin/blog/save', 'POST'), 'blog');
assert.equal(getAdminInvalidationTag('/api/admin/blog/category-groups/save', 'POST'), 'blog');
assert.equal(getAdminInvalidationTag('/api/admin/handbook/bulk-action', 'POST'), 'handbook');
assert.equal(getAdminInvalidationTag('/api/admin/products/delete', 'DELETE'), 'products');
assert.equal(getAdminInvalidationTag('/api/admin/categories/save', 'POST'), 'products');
assert.equal(getAdminInvalidationTag('/api/admin/site-content', 'PUT'), 'public');

assert.equal(getAdminInvalidationTag('/api/admin/posts/list', 'GET'), null);
assert.equal(getAdminInvalidationTag('/api/admin/blog/ai/advise', 'POST'), null);
assert.equal(getAdminInvalidationTag('/api/admin/products/ai', 'POST'), null);
assert.equal(getAdminInvalidationTag('/api/admin/run-pipeline', 'POST'), null);
assert.equal(getAdminInvalidationTag('/api/admin/feedback/x', 'POST'), null);

// Home shows the lead story and term of the day, so those sections refresh it too.
assert.deepEqual(expandInvalidationTags(['news']), ['news', 'home']);
assert.deepEqual(expandInvalidationTags(['handbook', 'news']), ['handbook', 'home', 'news']);
assert.deepEqual(expandInvalidationTags(['blog']), ['blog']);

console.log('cache-invalidation.test.mjs passed');
