const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

const layout = read('frontend/src/components/newsprint/NewsprintArticleLayout.astro');
const koDetail = read('frontend/src/pages/ko/news/[slug].astro');
const enDetail = read('frontend/src/pages/en/news/[slug].astro');

assert.ok(
  layout.includes('data-display={JSON.stringify(personaDisplayMap || {})}'),
  'detail layout must expose persona-specific title/excerpt display data to the switcher',
);
assert.ok(
  layout.includes("const displayMap: Record<string, { title?: string; excerpt?: string }> = JSON.parse(template.dataset.display || '{}');"),
  'switcher script must read persona-specific display data',
);
assert.ok(
  layout.includes("const leadTitle = document.querySelector<HTMLElement>('.newsprint-lead-title');"),
  'switcher must target the rendered article title',
);
assert.ok(
  layout.includes("document.querySelector<HTMLElement>('.newsprint-deck')"),
  'switcher must target the rendered article excerpt',
);
assert.ok(
  layout.includes("document.title = nextTitle ? `${nextTitle} | 0to1log` : '0to1log';"),
  'switcher must update browser tab title on persona change',
);
assert.ok(
  koDetail.includes('personaDisplayMap={personaDisplayMap}'),
  'KO detail page must pass persona display map into article layout',
);
assert.ok(
  enDetail.includes('personaDisplayMap={personaDisplayMap}'),
  'EN detail page must pass persona display map into article layout',
);

console.log('news-persona-title-switcher.test.cjs passed');
