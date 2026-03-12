import { BLOG_SUB_CATEGORIES, normalizeCategorySlug } from '../categories.ts';

export interface SidebarPost {
  title: string;
  slug: string;
  category: string;
  publishedAt?: string | null;
}

export type BlogSidebarMode = 'index' | 'detail';

export const BLOG_SIDEBAR_VISIBLE_LIMIT = 3;
export const BLOG_SIDEBAR_SUB_VISIBLE_LIMIT = 1;
export const BLOG_DETAIL_ACTIVE_VISIBLE_LIMIT = 10;

function comparePublishedAtDesc(a?: string | null, b?: string | null): number {
  const aTime = a ? Date.parse(a) : Number.NEGATIVE_INFINITY;
  const bTime = b ? Date.parse(b) : Number.NEGATIVE_INFINITY;
  return bTime - aTime;
}

function normalizeSidebarPost(post: SidebarPost): SidebarPost {
  return {
    ...post,
    category: normalizeCategorySlug(post.category) ?? post.category,
  };
}

export function toSidebarPost(post: {
  title: string;
  slug: string;
  category: string;
  published_at?: string | null;
  publishedAt?: string | null;
}): SidebarPost {
  return normalizeSidebarPost({
    title: post.title,
    slug: post.slug,
    category: post.category,
    publishedAt: post.publishedAt ?? post.published_at ?? null,
  });
}

export function buildBlogSidebarDataset(
  posts: SidebarPost[],
  currentPost?: SidebarPost | null,
): SidebarPost[] {
  const candidates = [...posts];
  if (currentPost) {
    candidates.push(currentPost);
  }

  const sorted = candidates
    .filter((post) => post?.title && post?.slug && post?.category)
    .map((post, index) => ({ index, post: normalizeSidebarPost(post) }))
    .sort((a, b) => {
      const byDate = comparePublishedAtDesc(a.post.publishedAt, b.post.publishedAt);
      return byDate !== 0 ? byDate : a.index - b.index;
    });

  const deduped = new Map<string, SidebarPost>();
  for (const { post } of sorted) {
    if (!deduped.has(post.slug)) {
      deduped.set(post.slug, post);
    }
  }

  return Array.from(deduped.values());
}

export function getBlogSidebarCurrentCategory(
  posts: SidebarPost[],
  currentSlug?: string,
  currentCategory?: string | null,
): string | undefined {
  const explicitCurrentCategory = normalizeCategorySlug(currentCategory);
  if (explicitCurrentCategory) {
    return explicitCurrentCategory;
  }

  if (!currentSlug) {
    return undefined;
  }

  return normalizeCategorySlug(posts.find((post) => post.slug === currentSlug)?.category) ?? undefined;
}

export function getBlogSidebarGroupExpanded(
  groupCategories: string[],
  options: {
    mode: BlogSidebarMode;
    currentCategory?: string;
    groupCount: number;
  },
): boolean {
  const currentCategory = normalizeCategorySlug(options.currentCategory) ?? undefined;
  const hasCurrentCategory = !!currentCategory && groupCategories.includes(currentCategory);

  if (options.mode === 'detail') {
    return true;
  }

  return hasCurrentCategory || options.groupCount > 0;
}

export function getBlogSidebarCategoryState(
  categoryPosts: SidebarPost[],
  options: {
    mode: BlogSidebarMode;
    category: string;
    currentCategory?: string;
    currentSlug?: string;
  },
) {
  const category = normalizeCategorySlug(options.category) ?? options.category;
  const currentCategory = normalizeCategorySlug(options.currentCategory) ?? undefined;
  const isActiveCategory = currentCategory === category;
  const defaultVisibleLimit = BLOG_SUB_CATEGORIES.includes(category as any)
    ? BLOG_SIDEBAR_SUB_VISIBLE_LIMIT
    : BLOG_SIDEBAR_VISIBLE_LIMIT;
  const visibleLimit =
    options.mode === 'detail' && isActiveCategory ? BLOG_DETAIL_ACTIVE_VISIBLE_LIMIT : defaultVisibleLimit;

  let visiblePosts = categoryPosts.slice(0, visibleLimit);

  if (options.mode === 'detail' && isActiveCategory && options.currentSlug) {
    const currentPost = categoryPosts.find((post) => post.slug === options.currentSlug);
    if (currentPost && !visiblePosts.some((post) => post.slug === currentPost.slug)) {
      const initialVisible = categoryPosts.slice(0, visibleLimit - 1);
      const orderMap = new Map(categoryPosts.map((post, index) => [post.slug, index]));

      visiblePosts = [...initialVisible, currentPost].sort((a, b) => {
        return (orderMap.get(a.slug) ?? 0) - (orderMap.get(b.slug) ?? 0);
      });
    }
  }

  const visibleSlugs = new Set(visiblePosts.map((post) => post.slug));
  const extraPosts = categoryPosts.filter((post) => !visibleSlugs.has(post.slug));
  const expanded = options.mode === 'detail' ? isActiveCategory : isActiveCategory || categoryPosts.length > 0;

  return {
    expanded,
    extraPosts,
    isActiveCategory,
    visibleLimit,
    visiblePosts,
  };
}
