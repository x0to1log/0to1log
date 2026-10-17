// frontend/src/lib/blogSerial.js
// Pure helpers for the blog list (A: serial column). No I/O.
// Series = visible fields of the 'main' group (sort_order), episodes in published_at order.
// Short notes = visible 'sub' fields, then every post that fits nowhere else (both newest first).

/**
 * Same rule as normalizeCategorySlug() in lib/categories.ts ('tech' → 'study').
 * Copied because node tests cannot import the .ts module; blog-serial.test.mjs pins both sides.
 */
export function normalizeBlogCategory(category) {
  if (!category) return null;
  return category === 'tech' ? 'study' : category;
}

function timeOf(value) {
  if (!value) return null;
  const t = Date.parse(value);
  return Number.isNaN(t) ? null : t;
}

// Undated posts (published_at null or unparsable) always sort last; ties keep input order.
function byDate(direction) {
  return (a, b) => {
    const ta = timeOf(a.published_at);
    const tb = timeOf(b.published_at);
    if (ta === null || tb === null) return (ta === null ? 1 : 0) - (tb === null ? 1 : 0);
    return direction * (ta - tb);
  };
}

const oldestFirst = byDate(1);
const newestFirst = byDate(-1);

/**
 * @param {Array<{id: string, title: string, slug: string, category?: string|null, published_at?: string|null}>} posts
 * @param {Array<{slug: string, group_slug: string, sort_order?: number, is_visible: boolean}>} categories
 * @returns {{ lead: object|null, series: Array<{category: object, posts: object[]}>, shortNotes: object[], total: number, latestAt: string|null }}
 *   Posts come back as shallow copies with the normalized category.
 *   lead = newest dated post of any field (null when no post has a date); it also stays in its own series.
 *   Every post appears exactly once in series + shortNotes.
 */
export function buildBlogFront(posts, categories) {
  const list = (Array.isArray(posts) ? posts : []).map((post) => ({ ...post, category: normalizeBlogCategory(post.category) }));
  const cats = Array.isArray(categories) ? categories : [];

  const dated = list.filter((post) => timeOf(post.published_at) !== null);
  const lead = dated.length > 0 ? dated.sort(newestFirst)[0] : null;

  const mainCats = cats
    .filter((c) => c.group_slug === 'main' && c.is_visible)
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const series = mainCats
    .map((category) => ({ category, posts: list.filter((post) => post.category === category.slug).sort(oldestFirst) }))
    .filter((s) => s.posts.length > 0);

  const mainSlugs = new Set(mainCats.map((c) => c.slug));
  const subSlugs = new Set(cats.filter((c) => c.group_slug === 'sub' && c.is_visible).map((c) => c.slug));
  const notes = list.filter((post) => subSlugs.has(post.category)).sort(newestFirst);
  const rest = list.filter((post) => !mainSlugs.has(post.category) && !subSlugs.has(post.category)).sort(newestFirst);

  return { lead, series, shortNotes: [...notes, ...rest], total: list.length, latestAt: lead ? lead.published_at : null };
}

/** "3월 11일" / "Mar 11" in KST (the server runs in UTC). '' when undated. */
export function formatBlogDate(value, locale) {
  const t = timeOf(value);
  if (t === null) return '';
  return new Date(t).toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US', {
    timeZone: 'Asia/Seoul',
    month: 'short',
    day: 'numeric',
  });
}
