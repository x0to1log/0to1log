import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeProductTags, resolveLocalizedProductTags } from './productTags';

test('normalizeProductTags keeps canonical English tags lowercase and capped at three', () => {
  assert.deepEqual(
    normalizeProductTags([' AI Coding ', '#Browser Automation', 'testing', 'extra'], {
      style: 'canonical',
    }),
    ['ai-coding', 'browser-automation', 'testing'],
  );
});

test('normalizeProductTags keeps Korean display tags readable and capped at three', () => {
  assert.deepEqual(
    normalizeProductTags([' AI 코딩 ', '#브라우저 자동화', '테스트 자동화', '코드 검증'], {
      style: 'display',
    }),
    ['AI 코딩', '브라우저 자동화', '테스트 자동화'],
  );
});

test('resolveLocalizedProductTags prefers Korean tags on Korean pages and falls back to canonical tags', () => {
  assert.deepEqual(
    resolveLocalizedProductTags(
      { tags: ['ai-coding', 'browser-automation'], tags_ko: ['AI 코딩', '브라우저 자동화'] },
      'ko',
    ),
    ['AI 코딩', '브라우저 자동화'],
  );
  assert.deepEqual(
    resolveLocalizedProductTags({ tags: ['ai-coding'], tags_ko: [] }, 'ko'),
    ['ai-coding'],
  );
  assert.deepEqual(
    resolveLocalizedProductTags(
      { tags: ['ai-coding'], tags_ko: ['AI 코딩'] },
      'en',
    ),
    ['ai-coding'],
  );
});
