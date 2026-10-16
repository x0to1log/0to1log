// frontend/tests/news-article-data.test.cjs
// News detail: same-day sibling (other desk) + briefing fallback flag.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = fs.readFileSync(path.join(__dirname, '..', 'src/lib/pageData/newsDetailPage.ts'), 'utf8');

assert(/export const NEWS_SIBLING_COLUMNS = 'id, slug, title, title_learner, title_beginner, excerpt, post_type, reading_time_min';/.test(src), 'sibling columns constant');
assert(/\.select\(NEWS_SIBLING_COLUMNS\)/.test(src), 'sibling query uses the constant');
assert(/import \{ deskDayRange \} from '\.\.\/newsDesks\.js';/.test(src) && /import \{ kstDay \} from '\.\.\/homeFront\.js';/.test(src), 'KST helpers reused');
assert(/siblingType && siblingRange\s*\?/.test(src), 'query only when a desk type and a valid KST range exist');
assert(/\.eq\('post_type', siblingType\)/.test(src) && /\.gte\('published_at', siblingRange\.start\)/.test(src) && /\.lt\('published_at', siblingRange\.end\)/.test(src), 'other desk, same KST day');
assert(/\.limit\(1\)\s*\.maybeSingle\(\)/.test(src), 'one row, no throw on empty');
assert(/resolveDisplayTitleExcerpt\(siblingRow, 'learner'\)/.test(src), 'sibling title is cache-neutral (learner)');
assert(!/siblingRes\.error[^\n]*503|503[^\n]*siblingRes/.test(src), 'sibling failure never changes the status');
assert(/focusItemsAreFallback/.test(src) && /sibling,/.test(src), 'returns sibling and focusItemsAreFallback');
console.log('news-article-data.test.cjs passed');
