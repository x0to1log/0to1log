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

// --- crumb: desk + reading time ---
const shell = read('components/newsprint/NewsprintShell.astro');
assert(/crumbDesk\?: string;/.test(shell) && /crumbReading\?: string;/.test(shell), 'shell: optional crumb props');
assert(shell.includes('{crumbDesk && <span class="newsprint-crumb-desk">{crumbDesk}</span>}') && shell.includes('{crumbReading && <span>{crumbReading}</span>}'), 'shell: desk before the issue, reading time after the date');
assert(shell.includes('{crumbItems ? (') && shell.includes('issueLabel(locale, issueNumber(displayDate))'), 'shell: strings other tests assert are intact');

const pages = { ko: read('pages/ko/news/[slug].astro'), en: read('pages/en/news/[slug].astro') };
for (const [locale, page] of Object.entries(pages)) {
  assert(page.includes("import { postTypeLabel } from '../../../lib/postType.js';"), `${locale}: desk label from lib/postType.js`);
  assert(page.includes('crumbDesk={crumbDesk}') && page.includes('crumbReading={crumbReading}'), `${locale}: crumb props passed`);
}
assert(pages.ko.includes('`${deskBase} 데스크`') && pages.ko.includes('`읽는 데 ${post.reading_time_min}분`'), 'ko: crumb copy');
assert(pages.en.includes('`${deskBase} desk`') && pages.en.includes('`${post.reading_time_min} min read`'), 'en: crumb copy');

console.log('news-article-reading.test.cjs passed');
