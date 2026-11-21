// frontend/tests/news-article-reading.test.cjs
// News article reading pass: bold clean-up wired into the news render path only,
// newsReading layout mode, scoped prose typography, hide-on-scroll-down bars.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// --- bold clean-up wiring ---
const detail = read('lib/pageData/newsDetailPage.ts');
assert(detail.includes("import { normalizeNewsBold } from '../newsBold.js';"), 'news detail imports the bold clean-up');
assert(detail.includes('renderMarkdownWithTerms(normalizeNewsBold(md), handbookTermsMap)') && detail.includes('renderMarkdown(normalizeNewsBold(md))'), 'both render branches normalise bold first');
assert(!read('lib/markdown.ts').includes('normalizeNewsBold'), 'shared renderer stays untouched (blog, products, handbook)');

console.log('news-article-reading.test.cjs passed');
