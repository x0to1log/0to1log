const fs = require('fs');
const path = require('path');

function read(rel) {
  return fs.readFileSync(path.join(process.cwd(), rel), 'utf8');
}

function expectIncludes(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

const api = read('frontend/src/pages/api/user/comments.ts');
expectIncludes(api, 'can_delete', 'comment API delete capability field');
expectIncludes(api, 'locals.isAdmin', 'admin branch in comment delete API');
expectIncludes(api, ".eq('id', id)", 'delete by id branch');

const script = read('frontend/src/scripts/comments.ts');
expectIncludes(script, 'c.can_delete', 'render delete button from API capability');
expectIncludes(script, 'data-delete-comment', 'delete button wiring remains');

const migration = read('supabase/migrations/00018_admin_delete_comments.sql');
expectIncludes(migration, 'news_comments', 'news comment admin delete policy');
expectIncludes(migration, 'blog_comments', 'blog comment admin delete policy');
expectIncludes(migration, 'FOR DELETE', 'delete policy action');
expectIncludes(migration, 'admin_users', 'admin policy join');

console.log('comments-admin-delete-contract.test.cjs passed');
