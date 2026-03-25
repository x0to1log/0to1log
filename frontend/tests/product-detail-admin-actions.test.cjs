const fs = require('fs');
const path = require('path');

function read(filePath) {
  return fs.readFileSync(path.join(__dirname, '..', filePath), 'utf8');
}

function assertIncludes(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const productDetail = read('src/components/products/ProductDetail.astro');
const productKo = read('src/pages/ko/products/[slug].astro');
const productEn = read('src/pages/en/products/[slug].astro');

assertIncludes(productDetail, 'isAdmin?: boolean;', 'product detail admin prop');
assertIncludes(productDetail, 'isAdmin = false', 'product detail admin default');
assertIncludes(productDetail, "const editHref = `/admin/products/edit/${product.slug}`;", 'product detail edit href');
assertIncludes(productDetail, "const unpublishApi = '/api/admin/products/status';", 'product detail unpublish api');
assertIncludes(productDetail, 'class="newsprint-admin-actions"', 'product detail admin action wrapper');
assertIncludes(productDetail, 'data-toolbar-api={unpublishApi}', 'product detail toolbar api binding');
assertIncludes(productDetail, 'class="newsprint-admin-action-btn">Edit</a>', 'product detail edit button');
assertIncludes(
  productDetail,
  'class="newsprint-admin-action-btn newsprint-admin-action-btn--unpublish">Unpublish</button>',
  'product detail unpublish button',
);
assertIncludes(productDetail, 'initProductAdminActions', 'product detail admin actions script');
assertIncludes(productDetail, "body: JSON.stringify({ id, action: 'unpublish' })", 'product detail unpublish request');

const adminIndex = productDetail.indexOf('newsprint-admin-actions');
const slotIndex = productDetail.indexOf('<slot />');
assert(adminIndex !== -1 && slotIndex !== -1 && adminIndex < slotIndex, 'Product detail admin actions must render before the page slot');

assertIncludes(productKo, 'isAdmin={!!Astro.locals.isAdmin}', 'KO product page admin prop');
assertIncludes(productEn, 'isAdmin={!!Astro.locals.isAdmin}', 'EN product page admin prop');

console.log('product-detail-admin-actions.test.cjs passed');
