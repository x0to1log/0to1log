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

for (const w of ['Regular', 'Medium', 'SemiBold', 'Bold']) {
  assert(css.includes(`Pretendard-${w}.woff2`), `Pretendard ${w} must be loaded`);
}
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
console.log('font-roles.test.cjs passed');
