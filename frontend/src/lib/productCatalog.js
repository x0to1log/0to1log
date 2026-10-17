// frontend/src/lib/productCatalog.js
// Pure helpers for the AI products catalog (A: fields) and the product detail page. No I/O.
// Sections follow a fixed field order; picks are the featured products; labels live here once.

// A period right after one of these is not the end of a sentence.
const ABBREVIATIONS = ['e.g.', 'i.e.', 'etc.', 'Inc.', 'vs.', 'Mr.', 'Dr.'];

function endsWithAbbreviation(head) {
  return ABBREVIATIONS.some((abbr) => {
    if (!head.endsWith(abbr)) return false;
    const before = head.slice(0, head.length - abbr.length);
    return !/[A-Za-z]$/.test(before); // "devs." is a word, not "vs."
  });
}

/**
 * First sentence of `text`, at most `max` characters ("…" included).
 * Sentence end = first /[.!?。](?=\s|$)/ that is not an English abbreviation; none → the whole text.
 * Too long → cut at the last space within max − 1 characters (or at max − 1 when there is none) + "…".
 */
export function firstSentence(text, max = 90) {
  const source = String(text ?? '').trim();
  if (!source) return '';
  let end = source.length;
  const pattern = /[.!?。](?=\s|$)/g;
  let match;
  while ((match = pattern.exec(source)) !== null) {
    const head = source.slice(0, match.index + 1);
    if (endsWithAbbreviation(head)) continue;
    end = match.index + 1;
    break;
  }
  const sentence = source.slice(0, end).trim();
  if (sentence.length <= max) return sentence;
  const room = sentence.slice(0, max - 1);
  const space = room.lastIndexOf(' ');
  return `${(space > 0 ? room.slice(0, space) : room).trimEnd()}…`;
}

/** Difficulty labels shared by the catalog rows and the product detail page. */
export const DIFFICULTY_LABELS = {
  beginner: { ko: '초보자 OK', en: 'Beginner-friendly' },
  intermediate: { ko: '약간의 설정 필요', en: 'Some setup needed' },
  advanced: { ko: '기술 설정 필요', en: 'Technical setup' },
};

const has = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

export function difficultyLabel(locale, value) {
  if (typeof value !== 'string' || !has(DIFFICULTY_LABELS, value)) return '';
  return DIFFICULTY_LABELS[value][locale === 'ko' ? 'ko' : 'en'];
}

// Short field names for the jump bar (field ids are fixed; unknown ids fall back to the DB label).
const JUMP_LABELS = {
  ko: {
    assistant: '어시스턴트',
    image: '이미지',
    video: '영상',
    audio: '음성·음악',
    coding: '코딩',
    workflow: '워크플로우',
    builder: '앱 빌더',
    platform: '플랫폼',
    research: '리서치',
    community: '커뮤니티',
  },
  en: {
    assistant: 'Assistants',
    image: 'Image',
    video: 'Video',
    audio: 'Audio',
    coding: 'Coding',
    workflow: 'Workflow',
    builder: 'App builders',
    platform: 'Platforms',
    research: 'Research',
    community: 'Community',
  },
};

export function jumpLabel(locale, id, fallback) {
  const table = JUMP_LABELS[locale === 'ko' ? 'ko' : 'en'];
  if (typeof id === 'string' && has(table, id)) return table[id];
  return fallback || id || '';
}

const PICK_LIMIT = 5;

/** Editor's picks: featured only, featured_order ascending (null last), then brand name, at most 5. */
export function orderPicks(products) {
  const nameOf = (p) => String(p.name_original ?? p.name ?? '');
  return (Array.isArray(products) ? products : [])
    .filter((p) => p && p.featured)
    .sort((a, b) => {
      const oa = a.featured_order ?? null;
      const ob = b.featured_order ?? null;
      if (oa !== ob) {
        if (oa === null) return 1;
        if (ob === null) return -1;
        return oa - ob;
      }
      return nameOf(a).localeCompare(nameOf(b));
    })
    .slice(0, PICK_LIMIT);
}

/**
 * Catalog sections: fields in `order` first, fields missing from it after them (DB sort_order),
 * fields without products dropped. Each item: { category, products, lede, desc }
 * (desc = the locale description, lede = its first sentence).
 */
export function catalogSections(categories, productsByCategory, order = [], locale = 'ko') {
  const list = Array.isArray(categories) ? categories.filter(Boolean) : [];
  const known = list
    .filter((c) => order.includes(c.id))
    .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
  const rest = list
    .filter((c) => !order.includes(c.id))
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  return [...known, ...rest]
    .map((category) => {
      const products = (productsByCategory && productsByCategory[category.id]) || [];
      const desc = String((locale === 'ko' ? category.description_ko : category.description_en) ?? '').trim();
      return { category, products, lede: firstSentence(desc), desc };
    })
    .filter((section) => section.products.length > 0);
}
