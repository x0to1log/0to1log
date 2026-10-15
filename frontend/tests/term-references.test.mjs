import assert from 'node:assert/strict';
import { pickReferencedTerms } from '../src/lib/pageData/termReferences.ts';

const terms = {
  token: { term: 'Token' },
  'gemini-ai': { term: 'Gemini' },
  rlhf: { term: 'RLHF' },
  transformer: { term: 'Transformer' },
};

const learnerHtml = '<p>A <span class="handbook-term" data-slug="token" data-term="Token">token</span> is</p>';
const expertHtml = '<p>See <a href="/ko/handbook/rlhf/">RLHF</a> and <a href="/handbook/gemini-ai">Gemini</a>.</p>';

assert.deepEqual(
  Object.keys(pickReferencedTerms(terms, [learnerHtml, expertHtml])).sort(),
  ['gemini-ai', 'rlhf', 'token'],
);

// Unreferenced and unknown slugs are dropped; empty input stays empty.
assert.deepEqual(pickReferencedTerms(terms, ['<a href="/ko/handbook/unknown/">x</a>']), {});
assert.deepEqual(pickReferencedTerms(terms, ['', null, undefined]), {});

// Entries are passed through untouched.
assert.equal(pickReferencedTerms(terms, [learnerHtml]).token, terms.token);

console.log('term-references.test.mjs passed');
