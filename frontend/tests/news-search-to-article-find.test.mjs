// frontend/tests/news-search-to-article-find.test.mjs
// Searching the news list and opening a story carries the query to the article (?q=), where the
// matches are highlighted and the in-article find box is shown. Without a query the box stays
// hidden, so ordinary reading is unchanged.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const { withFindQuery } = await import(pathToFileURL(path.join(src, 'lib/newsSearchLink.js')).href);

// --- withFindQuery: pure link rewriting ---
assert.equal(withFindQuery('/ko/news/a-slug/', 'Gemini'), '/ko/news/a-slug/?q=Gemini', 'adds the query');
assert.equal(withFindQuery('/ko/news/a-slug/?q=Gemini', 'OpenAI'), '/ko/news/a-slug/?q=OpenAI', 'replaces an earlier query');
assert.equal(withFindQuery('/ko/news/a-slug/?q=Gemini', ''), '/ko/news/a-slug/', 'empty query removes it');
assert.equal(withFindQuery('/ko/news/a-slug/?q=Gemini', '   '), '/ko/news/a-slug/', 'blank query removes it');
assert.equal(withFindQuery('/ko/news/a-slug/', '  Gemini  '), '/ko/news/a-slug/?q=Gemini', 'trims the query');
assert.equal(withFindQuery('/ko/news/a-slug/?preview=1', 'Gemini'), '/ko/news/a-slug/?preview=1&q=Gemini', 'keeps other parameters');
assert.equal(withFindQuery('/ko/news/a-slug/?preview=1&q=x', ''), '/ko/news/a-slug/?preview=1', 'removes only q');
assert.equal(withFindQuery('/ko/news/a-slug/#comments', 'Gemini'), '/ko/news/a-slug/?q=Gemini#comments', 'keeps the hash after the query');
assert.equal(withFindQuery('/ko/news/a-slug/', '에이전트 결제'), '/ko/news/a-slug/?q=%EC%97%90%EC%9D%B4%EC%A0%84%ED%8A%B8+%EA%B2%B0%EC%A0%9C', 'encodes Korean and spaces');
assert.equal(new URLSearchParams(withFindQuery('/x/', 'a&b=c #d?').split('?')[1]).get('q'), 'a&b=c #d?', 'special characters survive a round trip');
assert.equal(withFindQuery('/ko/news/a-slug/', undefined), '/ko/news/a-slug/', 'missing query is treated as empty');
// applying it twice gives the same link (it runs on every search update)
assert.equal(withFindQuery(withFindQuery('/ko/news/a-slug/', 'Gemini'), 'Gemini'), '/ko/news/a-slug/?q=Gemini', 'idempotent');

// --- list search keeps story links in step with the search box ---
const search = read('scripts/newsListSearch.ts');
assert(search.includes("import { withFindQuery } from '../lib/newsSearchLink.js';"), 'list search uses the shared link helper');
assert(search.includes("'a.newsprint-card-stretched-link'") && search.includes('withFindQuery('), 'story links are rewritten');
assert(/function applySearch[\s\S]*?syncStoryLinks\(search\.value\);[\s\S]*?\n  \}/.test(search), 'links are synced on every search update, with the text as typed');

// --- article: the find box shows only when a query came in ---
const layout = read('components/newsprint/NewsprintArticleLayout.astro');
assert(layout.includes('<div class="newsprint-article-find" data-active={initialFindQuery ? \'true\' : undefined}>'), 'find box is marked active only with a query');
const css = read('styles/global.css');
const base = css.slice(css.indexOf('\n.newsprint-article-find {'), css.indexOf('}', css.indexOf('\n.newsprint-article-find {')));
assert(/display:\s*none/.test(base), 'find box is hidden by default');
assert(/\n\.newsprint-article-find\[data-active="true"\]\s*\{\s*display:\s*block;/.test(css), 'and shown when active');

console.log('news-search-to-article-find.test.mjs passed');
