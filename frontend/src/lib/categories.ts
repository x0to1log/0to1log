import type { Locale } from '../i18n/index';

export type CategorySlug =
  | 'ai-news'
  | 'study'
  | 'career'
  | 'project'
  | 'work-note'
  | 'daily';
export type BlogCategorySlug = Exclude<CategorySlug, 'ai-news'>;
export type BlogCategoryGroupSlug = 'main' | 'sub';
export type LegacyCategorySlug = CategorySlug | 'tech';

type LocalizedLabel = Record<Locale, string>;

interface BlogCategoryGroup {
  slug: BlogCategoryGroupSlug;
  categories: BlogCategorySlug[];
}

const CATEGORY_LABELS: Record<CategorySlug, LocalizedLabel> = {
  'ai-news': { en: 'AI News', ko: 'AI 뉴스' },
  study: { en: 'Study', ko: '학습' },
  career: { en: 'Career', ko: '커리어' },
  project: { en: 'Project', ko: '프로젝트' },
  'work-note': { en: 'Work Notes', ko: '작업 메모' },
  daily: { en: 'Daily Life', ko: '일상' },
};

const BLOG_SIDEBAR_LABELS: Record<BlogCategorySlug, LocalizedLabel> = {
  study: { en: 'Study Notes', ko: '학습 노트' },
  project: { en: 'Project Log', ko: '프로젝트 기록' },
  career: { en: 'Career Thoughts', ko: '커리어 생각' },
  'work-note': { en: 'Work Notes', ko: '작업 메모' },
  daily: { en: 'Daily Life', ko: '일상' },
};

const BLOG_GROUP_LABELS: Record<BlogCategoryGroupSlug, LocalizedLabel> = {
  main: { en: 'Main Posts', ko: '주요 기록' },
  sub: { en: 'Small Notes', ko: '작은 노트' },
};

const CATEGORY_COLOR_VARS: Record<CategorySlug, string> = {
  'ai-news': 'var(--color-cat-ainews)',
  study: 'var(--color-cat-study)',
  career: 'var(--color-cat-career)',
  project: 'var(--color-cat-project)',
  'work-note': 'var(--color-cat-work-note)',
  daily: 'var(--color-cat-daily)',
};

export const BLOG_MAIN_CATEGORIES: BlogCategorySlug[] = ['study', 'project', 'career'];
export const BLOG_SUB_CATEGORIES: BlogCategorySlug[] = ['work-note', 'daily'];
export const BLOG_CATEGORIES: BlogCategorySlug[] = [...BLOG_MAIN_CATEGORIES, ...BLOG_SUB_CATEGORIES];
export const NEWS_CATEGORY: CategorySlug = 'ai-news';

export const BLOG_CATEGORY_GROUPS: BlogCategoryGroup[] = [
  { slug: 'main', categories: BLOG_MAIN_CATEGORIES },
  { slug: 'sub', categories: BLOG_SUB_CATEGORIES },
];

const POST_TYPE_LABELS: Record<string, Record<Locale, string>> = {
  research: { en: 'Research', ko: '리서치' },
  business: { en: 'Business', ko: '비즈니스' },
};

export function normalizeCategorySlug(category?: string | null): string | null {
  if (!category) return null;
  return category === 'tech' ? 'study' : category;
}

export function getCategoryLabel(locale: Locale, category?: string | null): string | null {
  const normalized = normalizeCategorySlug(category);
  if (!normalized) return null;
  return CATEGORY_LABELS[normalized as CategorySlug]?.[locale] ?? normalized;
}

export function getBlogSidebarLabel(locale: Locale, category?: string | null): string | null {
  const normalized = normalizeCategorySlug(category);
  if (!normalized) return null;
  return BLOG_SIDEBAR_LABELS[normalized as BlogCategorySlug]?.[locale] ?? getCategoryLabel(locale, normalized);
}

export function getBlogCategoryGroupLabel(locale: Locale, group: BlogCategoryGroupSlug): string {
  return BLOG_GROUP_LABELS[group][locale];
}

export function getCategoryColorVar(category?: string | null): string {
  const normalized = normalizeCategorySlug(category);
  if (!normalized) return 'var(--color-border)';
  return CATEGORY_COLOR_VARS[normalized as CategorySlug] ?? 'var(--color-border)';
}

export function getPostTypeLabel(locale: Locale, postType: string): string {
  return POST_TYPE_LABELS[postType]?.[locale] ?? postType;
}

export function getDefaultCategories(): CategorySlug[] {
  return ['ai-news', 'study', 'project', 'career'];
}
