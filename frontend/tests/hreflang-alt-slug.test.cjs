const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const head = fs.readFileSync(path.join(src, 'components/Head.astro'), 'utf8');
const layout = fs.readFileSync(path.join(src, 'layouts/MainLayout.astro'), 'utf8');

// Paired KO/EN posts have different slugs (e.g. ...-business-digest-ko vs ...-business-digest).
// The hreflang alternate must use the paired slug, not the current one (was a 404, 2026-10-15).
assert(/altSlug\?: string;/.test(head), 'Head accepts altSlug');
assert(/<Head\b[^>]*\baltSlug=\{altSlug\}/.test(layout), 'MainLayout passes altSlug to Head');
assert(head.includes('const altUrl = altSlug'), 'Head builds the alternate URL from altSlug when present');
console.log('hreflang-alt-slug.test.cjs passed');
