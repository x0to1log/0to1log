import assert from 'node:assert/strict';

import { renderMarkdownWithTerms } from '../src/lib/markdown.ts';

const termsMap = new Map([
  ['openai', { slug: 'openai', term: 'OpenAI' }],
]);

const html = await renderMarkdownWithTerms('OpenAI builds models.', termsMap as any);

assert.match(
  html,
  /<span class="handbook-term"[^>]*data-slug="openai"[^>]*data-term="OpenAI"[^>]*>OpenAI<\/span>/,
  'inline handbook term markup should keep slug + term data attributes for popup lookup',
);

console.log('handbook popup render test passed');
