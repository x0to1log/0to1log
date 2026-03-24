const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function exists(relPath) {
  return fs.existsSync(path.join(root, relPath));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(
  exists('src/components/products/ProductSearchBar.astro'),
  'Product search UI should be extracted into a reusable ProductSearchBar component',
);

const productSearchBar = read('src/components/products/ProductSearchBar.astro');
assert(
  productSearchBar.includes('id="product-search"'),
  'ProductSearchBar should keep the shared product-search input id',
);
assert(
  productSearchBar.includes('data-placeholder-hints'),
  'ProductSearchBar should preserve rotating search placeholder hints',
);
assert(
  productSearchBar.includes('action={`/${locale}/products/`}'),
  'ProductSearchBar should submit back to the localized products index',
);

const filterBar = read('src/components/products/ProductFilterBar.astro');
assert(
  filterBar.includes("import ProductSearchBar from './ProductSearchBar.astro';"),
  'ProductFilterBar should reuse the shared ProductSearchBar component',
);
assert(
  filterBar.includes('<ProductSearchBar locale={locale} />'),
  'ProductFilterBar should render the extracted ProductSearchBar',
);

[
  'src/pages/en/products/[slug].astro',
  'src/pages/ko/products/[slug].astro',
].forEach((file) => {
  const source = read(file);
  assert(
    source.includes("import ProductSearchBar from '../../../components/products/ProductSearchBar.astro';"),
    `${file} should import the shared product search component`,
  );
  assert(
    source.includes('sticky={true}'),
    `${file} should render the search bar in sticky detail mode`,
  );
  assert(
    source.includes("import '../../../scripts/handbookSearchHints';"),
    `${file} should initialize the rotating product search hints on detail pages`,
  );
});

const globalCss = read('src/styles/global.css');
assert(
  globalCss.includes('.product-detail-search'),
  'Global styles should include a product detail search wrapper',
);
assert(
  globalCss.includes('.product-detail-search .handbook-search-input'),
  'Product detail search should reuse the shared handbook-style search input',
);
assert(
  globalCss.includes('.product-detail-search.handbook-search-sticky {\n  top: 0.75rem;'),
  'Product detail search should keep a visible top offset instead of sticking flush to the viewport',
);
assert(
  globalCss.includes('body:has(.site-header--fixed:not(.site-header--hidden)) .product-detail-search.handbook-search-sticky {\n  top: calc(var(--header-h, 4rem) + 0.75rem);'),
  'Product detail search should keep the same breathing room below the fixed header while scrolling',
);

console.log('product-detail-search-sticky.test.cjs passed');
