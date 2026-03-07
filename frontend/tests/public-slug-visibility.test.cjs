const fs = require('fs');
const path = require('path');

function read(filePath) {
  return fs.readFileSync(path.join(__dirname, '..', filePath), 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const layout = read('src/components/newsprint/NewsprintArticleLayout.astro');
assert(layout.includes('showSlug?: boolean;'), 'NewsprintArticleLayout must expose a showSlug prop');
assert(layout.includes('{showSlug && <span class="newsprint-tag">{slug}</span>}'), 'Slug chip must be gated by showSlug');

const enDetail = read('src/pages/en/log/[slug].astro');
const koDetail = read('src/pages/ko/log/[slug].astro');
const adminEdit = read('src/pages/admin/edit/[slug].astro');

assert(enDetail.includes('showSlug={false}'), 'EN public detail page must hide slug');
assert(koDetail.includes('showSlug={false}'), 'KO public detail page must hide slug');
assert(adminEdit.includes('showSlug={true}'), 'Admin edit preview must keep slug visible');
