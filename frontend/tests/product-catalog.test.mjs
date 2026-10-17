// frontend/tests/product-catalog.test.mjs
// Products catalog A (fields): first sentences, difficulty / jump labels, editor's picks order, section order.
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { firstSentence, DIFFICULTY_LABELS, difficultyLabel, jumpLabel, orderPicks, catalogSections } = await import(
  pathToFileURL(path.join(here, '../src/lib/productCatalog.js')).href
);

// --- firstSentence ---
assert.equal(firstSentence('모르는 게 있으면 검색 대신 물어보세요. 논문 요약까지 합니다.'), '모르는 게 있으면 검색 대신 물어보세요.', 'Korean sentence end');
assert.equal(firstSentence('바로 시작할 수 있습니다. 다음 문장'), '바로 시작할 수 있습니다.', 'Korean "…니다. 다음"');
assert.equal(firstSentence('Stop searching, start asking. Summarize papers.'), 'Stop searching, start asking.', 'English ". "');
assert.equal(firstSentence('Line one.\nLine two.'), 'Line one.', '".\\n" ends a sentence');
assert.equal(firstSentence('Really? Yes.'), 'Really?', '"?" ends a sentence');
assert.equal(firstSentence('Bolt.new and v0 build apps. More here.'), 'Bolt.new and v0 build apps.', 'a period inside a word is not an end');
assert.equal(firstSentence('Tools, e.g. Zapier and n8n, automate work. Next.'), 'Tools, e.g. Zapier and n8n, automate work.', '"e.g. " is not an end');
assert.equal(firstSentence('Docs, i.e. guides, etc. are here. Next.'), 'Docs, i.e. guides, etc. are here.', '"i.e." and "etc." are not ends');
assert.equal(firstSentence('Big devs. Small teams.'), 'Big devs.', '"devs." is a word, not "vs."');
assert.equal(firstSentence('문장부호 없는 설명'), '문장부호 없는 설명', 'no sentence end → whole text');
assert.equal(firstSentence('  앞뒤 공백.  '), '앞뒤 공백.', 'trimmed');
const long = 'Worth trying if you want a single chat thread for drafting, debugging, and quick research with files and voice; best suited for creators.';
const cut = firstSentence(long);
assert(cut.length <= 90, `cut to at most 90 chars (got ${cut.length})`);
assert(cut.endsWith('…'), 'cut ends with an ellipsis');
assert.equal(cut, 'Worth trying if you want a single chat thread for drafting, debugging, and quick…');
assert.equal(firstSentence('abcdefghijklmnop', 10), 'abcdefghi…', 'no space → cut at max − 1');
assert.equal(firstSentence('one two three four', 12), 'one two…', 'cut at the last space');
assert.equal(firstSentence(''), '');
assert.equal(firstSentence(null), '');
assert.equal(firstSentence(undefined), '');

// --- labels ---
assert.deepEqual(Object.keys(DIFFICULTY_LABELS), ['beginner', 'intermediate', 'advanced']);
assert.equal(difficultyLabel('ko', 'beginner'), '초보자 OK');
assert.equal(difficultyLabel('ko', 'intermediate'), '약간의 설정 필요');
assert.equal(difficultyLabel('ko', 'advanced'), '기술 설정 필요');
assert.equal(difficultyLabel('en', 'beginner'), 'Beginner-friendly');
assert.equal(difficultyLabel('en', 'intermediate'), 'Some setup needed');
assert.equal(difficultyLabel('en', 'advanced'), 'Technical setup');
assert.equal(difficultyLabel('ko', 'expert'), '', 'unknown difficulty');
assert.equal(difficultyLabel('en', null), '');
assert.equal(difficultyLabel('en', 'toString'), '', 'no prototype keys');

assert.equal(jumpLabel('ko', 'assistant', 'AI 어시스턴트'), '어시스턴트');
assert.equal(jumpLabel('ko', 'audio', 'AI 음성/음악'), '음성·음악');
assert.equal(jumpLabel('ko', 'builder', 'AI 앱 빌더'), '앱 빌더');
assert.equal(jumpLabel('en', 'assistant', 'AI Assistants'), 'Assistants');
assert.equal(jumpLabel('en', 'builder', 'App Builders'), 'App builders');
assert.equal(jumpLabel('en', 'community', 'Communities & Resources'), 'Community');
assert.equal(jumpLabel('ko', 'robotics', '로보틱스'), '로보틱스', 'unknown id → DB label');
assert.equal(jumpLabel('en', 'robotics', ''), 'robotics', 'no label → id');

// --- orderPicks ---
const prod = (name, featured, featured_order = null) => ({ name: `${name} (ko)`, name_original: name, featured, featured_order });
const picks = orderPicks([
  prod('OpenClaw', true),
  prod('Zeta', false, 0),
  prod('ChatGPT', true, 1),
  prod('Hugging Face', true),
  prod('Google Antigravity', true),
  prod('Claude', true, 2),
  prod('Google Notebook LM', true),
]);
assert.deepEqual(
  picks.map((p) => p.name_original),
  ['ChatGPT', 'Claude', 'Google Antigravity', 'Google Notebook LM', 'Hugging Face'],
  'featured_order first (null last), then brand name, at most 5',
);
assert.deepEqual(orderPicks([prod('B', true, 3), prod('A', true, 3)]).map((p) => p.name_original), ['A', 'B'], 'same order → name');
assert.deepEqual(orderPicks([]), []);
assert.deepEqual(orderPicks(null), []);
const input = [prod('B', true), prod('A', true)];
orderPicks(input);
assert.deepEqual(input.map((p) => p.name_original), ['B', 'A'], 'input is not reordered');

// --- catalogSections ---
const cat = (id, sort_order, extra = {}) => ({ id, label_ko: `${id} ko`, label_en: `${id} en`, description_ko: null, description_en: null, sort_order, ...extra });
const CATS = [
  cat('robotics', 0),
  cat('video', 3, { description_ko: '텍스트 한 줄에서 동영상이 만들어집니다. 광고와 단편 영화까지.', description_en: 'A single sentence becomes a video. Ads too.' }),
  cat('assistant', 1),
  cat('empty', 2),
  cat('legal', -1),
];
const BY = { robotics: [{ id: 'r1' }], video: [{ id: 'v1' }, { id: 'v2' }], assistant: [{ id: 'a1' }], empty: [], legal: [{ id: 'l1' }] };
const ORDER = ['assistant', 'image', 'video', 'empty'];
const sections = catalogSections(CATS, BY, ORDER, 'ko');
assert.deepEqual(sections.map((s) => s.category.id), ['assistant', 'video', 'legal', 'robotics'], 'fixed order, unknown fields after in sort_order, empty fields dropped');
assert.deepEqual(sections[1].products.map((p) => p.id), ['v1', 'v2']);
assert.equal(sections[1].desc, '텍스트 한 줄에서 동영상이 만들어집니다. 광고와 단편 영화까지.');
assert.equal(sections[1].lede, '텍스트 한 줄에서 동영상이 만들어집니다.');
assert.deepEqual([sections[0].desc, sections[0].lede], ['', ''], 'no description → empty desc and lede');
const en = catalogSections(CATS, BY, ORDER, 'en');
assert.deepEqual([en[1].desc, en[1].lede], ['A single sentence becomes a video. Ads too.', 'A single sentence becomes a video.']);
assert.deepEqual(catalogSections(CATS, {}, ORDER, 'ko'), [], 'no products → no sections');
assert.deepEqual(catalogSections(null, BY, ORDER, 'ko'), []);

console.log('product-catalog.test.mjs passed');
