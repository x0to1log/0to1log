import type { Locale } from '../i18n/index';

type CategorySlug =
  | 'ai-news'
  | 'study'
  | 'career'
  | 'project'
  | 'work-note'
  | 'daily';

type LocalizedLabel = Record<Locale, string>;

const CATEGORY_LABELS: Record<CategorySlug, LocalizedLabel> = {
  'ai-news': { en: 'AI News', ko: 'AI 뉴스' },
  study: { en: 'Study', ko: '학습' },
  career: { en: 'Career', ko: '커리어' },
  project: { en: 'Project', ko: '프로젝트' },
  'work-note': { en: 'Work Notes', ko: '작업 메모' },
  daily: { en: 'Daily Life', ko: '일상' },
};

const CATEGORY_COLOR_VARS: Record<CategorySlug, string> = {
  'ai-news': 'var(--color-cat-ainews)',
  study: 'var(--color-cat-study)',
  career: 'var(--color-cat-career)',
  project: 'var(--color-cat-project)',
  'work-note': 'var(--color-cat-work-note)',
  daily: 'var(--color-cat-daily)',
};

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
