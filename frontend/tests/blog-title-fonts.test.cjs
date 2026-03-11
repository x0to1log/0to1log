const fs = require('fs');
const path = require('path');
const root = process.cwd();
const css = fs.readFileSync(path.join(root, 'frontend/src/styles/global.css'), 'utf8');
const head = fs.readFileSync(path.join(root, 'frontend/src/components/Head.astro'), 'utf8');

function mustInclude(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}
function mustNotInclude(haystack, needle, label) {
  if (haystack.includes(needle)) {
    throw new Error(`Unexpected ${label}: ${needle}`);
  }
}

mustInclude(head, 'IBM+Plex+Sans', 'IBM Plex Sans font import');
mustNotInclude(head, 'IBM+Plex+Serif', 'IBM Plex Serif font import');
mustInclude(css, "--font-blog-heading: 'IBM Plex Sans', 'IBM Plex Sans KR', sans-serif;", 'blog heading token');

const selectors = ['.blog-featured-card-title', '.blog-list-item-title', '.blog-article-title'];
for (const selector of selectors) {
  const escaped = selector.replace('.', '\\.');
  const match = css.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`));
  if (!match) throw new Error(`Missing ${selector} rule`);
  mustInclude(match[1], 'font-family: var(--font-blog-heading);', `${selector} blog heading font`);
}

console.log('blog-title-fonts.test.cjs passed');
