// frontend/src/lib/handbookShelves.js
// Pure helpers for the handbook index: shelves by field, A–Z index, display names, plain text. No I/O.

const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
const byTerm = (a, b) => String(a.term).localeCompare(String(b.term), 'en');

/** Definition as plain text: `**` removed, outer whitespace trimmed. */
export function plainDefinition(text) {
  return text ? String(text).replace(/\*\*/g, '').trim() : '';
}

/** First non-empty line of hero_news_context, without a leading "- " or "• " marker. */
export function firstNewsLine(text) {
  if (!text) return '';
  for (const raw of String(text).split(/\r?\n/)) {
    const line = raw.trim().replace(/^[-•](?:\s+|$)/, '').trim();
    if (line) return line;
  }
  return '';
}

/** KO: korean_name with the English term beside it (when different). EN: the term only. */
export function termNames(term, locale) {
  const korean = term.korean_name ? String(term.korean_name).trim() : '';
  if (locale === 'ko' && korean && korean !== term.term) return { name: korean, sub: term.term };
  return { name: term.term, sub: '' };
}

/**
 * @param {Array<{slug: string, term: string, categories?: string[]|null}>} terms
 * @param {string[]} categorySlugs canonical order (getHandbookCategories())
 * @param {string[]} [trendingSlugs] most viewed first
 * @returns {Array<{slug: string, count: number, wide: boolean, items: object[]}>}
 *   count = terms whose categories include the slug (same rule as the category page);
 *   items (target 6 wide / 4 other), each stage ordered trending first then A–Z by term:
 *     1. terms whose first canonical category is the slug;
 *     2. if short: other member terms not listed on any shelf yet (shelves filled in canonical order);
 *     3. if still short: member terms already listed on another shelf (duplicates).
 *   fields with count 0 are dropped; the largest count is wide (ties: earlier field).
 */
export function buildShelves(terms, categorySlugs, trendingSlugs = []) {
  const known = new Set(categorySlugs);
  const rank = new Map(trendingSlugs.map((slug, i) => [slug, i]));
  const rankOf = (t) => (rank.has(t.slug) ? rank.get(t.slug) : Number.MAX_SAFE_INTEGER);
  const order = (a, b) => rankOf(a) - rankOf(b) || byTerm(a, b);

  const shelves = categorySlugs
    .map((slug) => {
      const members = terms.filter((t) => (t.categories || []).includes(slug));
      return {
        slug,
        count: members.length,
        members,
        placed: terms.filter((t) => (t.categories || []).find((c) => known.has(c)) === slug),
      };
    })
    .filter((shelf) => shelf.count > 0);

  let wideSlug = null;
  let max = 0;
  for (const shelf of shelves) {
    if (shelf.count > max) {
      max = shelf.count;
      wideSlug = shelf.slug;
    }
  }

  // stage 1: first canonical category
  const built = shelves.map(({ slug, count, members, placed }) => {
    const wide = slug === wideSlug;
    const target = wide ? 6 : 4;
    return { slug, count, wide, target, members, items: [...placed].sort(order).slice(0, target) };
  });

  // stage 2: member terms not listed on any shelf yet
  const listed = new Set(built.flatMap((shelf) => shelf.items.map((t) => t.slug)));
  for (const shelf of built) {
    if (shelf.items.length >= shelf.target) continue;
    const extra = shelf.members
      .filter((t) => !listed.has(t.slug))
      .sort(order)
      .slice(0, shelf.target - shelf.items.length);
    for (const t of extra) listed.add(t.slug);
    shelf.items.push(...extra);
  }

  // stage 3: member terms already listed elsewhere (duplicates)
  for (const shelf of built) {
    if (shelf.items.length >= shelf.target) continue;
    const own = new Set(shelf.items.map((t) => t.slug));
    shelf.items.push(
      ...shelf.members
        .filter((t) => !own.has(t.slug))
        .sort(order)
        .slice(0, shelf.target - shelf.items.length),
    );
  }

  return built.map(({ slug, count, wide, items }) => ({ slug, count, wide, items }));
}

/** Index bucket of a term: its first letter A–Z, otherwise '#'. */
export function azLetter(term) {
  const first = String(term || '').trim().charAt(0).toUpperCase();
  return /^[A-Z]$/.test(first) ? first : '#';
}

/**
 * @returns {{letters: Array<{letter: string, anchor: string, has: boolean}>,
 *            groups: Array<{letter: string, anchor: string, items: object[]}>}}
 *   letters = A–Z + '#' (27); groups = letters that have terms, '#' last, items A–Z by term.
 *   anchor is the letter, or 'num' for '#' (ids stay plain: az-A, az-num).
 */
export function buildAzIndex(terms) {
  const buckets = new Map();
  for (const t of terms) {
    const letter = azLetter(t.term);
    if (!buckets.has(letter)) buckets.set(letter, []);
    buckets.get(letter).push(t);
  }
  const anchorOf = (letter) => (letter === '#' ? 'num' : letter);
  const keys = [...LETTERS, '#'];
  return {
    letters: keys.map((letter) => ({ letter, anchor: anchorOf(letter), has: buckets.has(letter) })),
    groups: keys
      .filter((letter) => buckets.has(letter))
      .map((letter) => ({ letter, anchor: anchorOf(letter), items: buckets.get(letter).sort(byTerm) })),
  };
}
