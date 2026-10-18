// frontend/src/lib/blogSerial.js
// Pure helpers for the blog list (A: serial column) and the blog post page (A: one column). No I/O.
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
 * @param {Array<{id?: string, title: string, slug: string, category?: string|null, published_at?: string|null}>} posts
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

/**
 * Where one post sits, for the blog post page. Uses buildBlogFront, so the episode number matches the list page
 * when both get the same posts (same query window and order).
 * @param {Array<{title: string, slug: string, category?: string|null, published_at?: string|null}>} posts
 * @param {Array<{slug: string, group_slug: string, sort_order?: number, is_visible: boolean}>} categories
 * @param {string} slug
 * @returns {{ series: {category: object, posts: object[]}|null, index: number, prev: object|null, next: object|null }}
 *   In a series: index (0-based) and the neighbouring episodes of that series.
 *   Otherwise series null, index -1, and the neighbours among every dated post (episodes included), oldest first;
 *   both null when the post itself is undated. A slug missing from posts (e.g. a draft preview) gives all nulls.
 */
export function locatePost(posts, categories, slug) {
  const none = { series: null, index: -1, prev: null, next: null };
  const list = (Array.isArray(posts) ? posts : []).map((post) => ({ ...post, category: normalizeBlogCategory(post.category) }));
  if (!slug || !list.some((post) => post.slug === slug)) return none;

  for (const series of buildBlogFront(list, categories).series) {
    const index = series.posts.findIndex((post) => post.slug === slug);
    if (index >= 0) {
      return { series, index, prev: series.posts[index - 1] ?? null, next: series.posts[index + 1] ?? null };
    }
  }

  const timeline = list.filter((post) => timeOf(post.published_at) !== null).sort(oldestFirst);
  const at = timeline.findIndex((post) => post.slug === slug);
  if (at < 0) return none;
  return { series: null, index: -1, prev: timeline[at - 1] ?? null, next: timeline[at + 1] ?? null };
}

/**
 * The `serial` prop of BlogArticleLayout, built once for the ko and en post pages.
 * @param {{ series: {category: object, posts: object[]}|null, index: number, prev: object|null, next: object|null }} located  locatePost() result
 * @param {Array<{slug: string, label_ko?: string, label_en?: string, color?: string|null, is_visible: boolean}>} categories
 * @param {'ko'|'en'} locale
 * @param {string|null} [category]  the post's own category: names the field when the post is not in a series
 *   (short notes, or a draft preview missing from the list)
 * @returns {{ categoryLabel: string|null, categoryHref: string|null, categoryColor: string|null, episode: number|null,
 *   total: number|null, episodes: {title: string, slug: string}[], prev: {title: string, slug: string}|null,
 *   next: {title: string, slug: string}|null }}
 *   categoryLabel null when the field is not in the DB; categoryHref null when the field is hidden.
 */
export function toSerialProps(located, categories, locale, category) {
  const cats = Array.isArray(categories) ? categories : [];
  const series = located && located.series ? located.series : null;
  const fieldSlug = series ? series.category.slug : normalizeBlogCategory(category);
  const field = fieldSlug ? cats.find((c) => c.slug === fieldSlug) || null : null;
  const link = (post) => (post ? { title: post.title, slug: post.slug } : null);

  return {
    categoryLabel: field ? (locale === 'ko' ? field.label_ko : field.label_en) || field.slug : null,
    categoryHref: field && field.is_visible ? `/${locale}/blog/category/${field.slug}/` : null,
    categoryColor: (field && field.color) || null,
    episode: series ? located.index + 1 : null,
    total: series ? series.posts.length : null,
    episodes: series ? series.posts.map(link) : [],
    prev: link(located ? located.prev : null),
    next: link(located ? located.next : null),
  };
}

/**
 * One field page (blog field A: series table of contents). Same posts and rules as the list page, so the
 * episode numbers match the list and post pages. The page checks that the field exists and is visible first.
 * @param {Array<{id?: string, title: string, slug: string, category?: string|null, published_at?: string|null, excerpt?: string|null}>} posts
 * @param {Array<{slug: string, group_slug: string|null, sort_order?: number, is_visible: boolean}>} categories
 * @param {string} slug
 * @returns {{ kind: 'series'|'notes', posts: object[], range: {first: string, last: string}|null, counts: Record<string, number> }}
 *   kind: 'series' for the 'main' group, 'notes' otherwise (sub, other groups, null, or a field missing from categories).
 *   series posts = this field's entry of buildBlogFront().series (oldest first; episode = index + 1), [] without posts.
 *   notes posts = posts whose normalized field is slug, newest first, undated last.
 *   range = earliest and latest published_at among the dated posts of this field (null when none).
 *   counts = number of loaded posts per normalized field (posts without a field are not counted).
 */
export function categoryPage(posts, categories, slug) {
  const list = (Array.isArray(posts) ? posts : []).map((post) => ({ ...post, category: normalizeBlogCategory(post.category) }));
  const cats = Array.isArray(categories) ? categories : [];
  const category = cats.find((c) => c.slug === slug) || null;
  const kind = category && category.group_slug === 'main' ? 'series' : 'notes';

  let own;
  if (kind === 'series') {
    const series = buildBlogFront(list, cats).series.find((s) => s.category.slug === slug);
    own = series ? series.posts : [];
  } else {
    own = list.filter((post) => post.category === slug).sort(newestFirst);
  }

  const dated = own.filter((post) => timeOf(post.published_at) !== null).sort(oldestFirst);
  const range = dated.length > 0 ? { first: dated[0].published_at, last: dated[dated.length - 1].published_at } : null;

  const counts = {};
  for (const post of list) {
    if (post.category) counts[post.category] = (counts[post.category] || 0) + 1;
  }

  return { kind, posts: own, range, counts };
}

/**
 * "3월 11일" / "Mar 11" in KST (the server runs in UTC). '' when undated.
 * { year: true } → "2026년 3월 11일" / "Mar 11, 2026" (blog post byline).
 */
export function formatBlogDate(value, locale, options = {}) {
  const t = timeOf(value);
  if (t === null) return '';
  return new Date(t).toLocaleDateString(locale === 'ko' ? 'ko-KR' : 'en-US', {
    timeZone: 'Asia/Seoul',
    ...(options.year ? { year: 'numeric' } : {}),
    month: 'short',
    day: 'numeric',
  });
}
