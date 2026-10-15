const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');
const head = fs.readFileSync(path.join(src, 'components/Head.astro'), 'utf8');

const SERIF_KO = "'Hahmlet', 'Pretendard', Georgia, serif";
const SANS = "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif";
const MAST = "'Newsreader', 'Hahmlet', Georgia, serif";
const expected = {
  '--font-masthead': MAST,
  '--font-display': SERIF_KO,
  '--font-heading': SERIF_KO,
  '--font-article-heading': SERIF_KO,
  '--font-blog-heading': SERIF_KO,
  '--font-blog-masthead': SERIF_KO,
  '--font-sans': SANS,
  '--font-body': SANS,
  '--font-ui': SANS,
  '--font-article-deck': SANS,
  '--font-blog-body': SANS,
  '--font-blog-ui': SANS,
};
for (const [token, value] of Object.entries(expected)) {
  assert(css.includes(`  ${token}: ${value};`), `${token} must be ${value}`);
}

// Pretendard: unicode-range dynamic subset (only the slices a page uses download).
// Full-Hangul woff2 faces were ~750 KB each (93% of an article's transfer, 2026-10-15).
assert(!/Pretendard-\w+\.woff2/.test(css), 'no full-Hangul Pretendard @font-face in global.css');
assert(head.includes('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.css'), 'Head loads the Pretendard dynamic-subset stylesheet');
assert(head.includes('family=Hahmlet:wght@400;600;700'), 'Head must load Hahmlet');
assert(head.includes('family=Newsreader:opsz,wght@6..72,500'), 'Head must load Newsreader');

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]);
}
const legacy = walk(src)
  .filter((f) => /\.(astro|ts|js|css)$/.test(f))
  .filter((f) => /\bLora\b|Playfair|Gowun/.test(fs.readFileSync(f, 'utf8')));
assert.deepStrictEqual(legacy, [], `legacy fonts still referenced:\n${legacy.join('\n')}`);

assert(/font-variant-numeric:\s*lining-nums/.test(css), 'masthead brand marks need lining numerals ("0to1" must not read "oto1")');
// Pretendard/Hahmlet have no italic faces: decks must stay upright (no faux-oblique Hangul).
for (const sel of ['.newsprint-deck', '.newsprint-headline-deck', '.handbook-definition']) {
  const escaped = sel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp('(?:^|\\n)' + escaped + '\\s*\\{([^}]*)\\}'));
  assert(m, `${sel} rule must exist`);
  assert(!/font-style:\s*italic/.test(m[1]), `${sel} must not use font-style: italic`);
}
// Hahmlet Hangul is wide: headings must not break Korean words mid-word.
const headingRule = css.match(/(?:^|\n)h1,\s*h2,\s*h3,\s*h4,\s*h5,\s*h6\s*\{([^}]*)\}/);
assert(headingRule, 'global heading rule (h1..h6) must exist');
assert(/word-break:\s*keep-all/.test(headingRule[1]), 'headings must use word-break: keep-all');
console.log('font-roles.test.cjs passed');
